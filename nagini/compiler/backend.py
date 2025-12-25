"""
Nagini C Backend
Generates C code and compiles to native machine code using gcc/clang.
Future versions will support direct LLVM IR generation.
"""

import os
import sys
from typing import Dict, Optional
from .parser import ClassInfo, FieldInfo, FunctionInfo
from .ir import (
    NaginiIR, FunctionIR, StmtIR, ExprIR,
    ConstantIR, VariableIR, BinOpIR, UnaryOpIR, CallIR, AttributeIR,
    AssignIR, ReturnIR, IfIR, WhileIR, ForIR, ExprStmtIR,
    ConstructorCallIR, LambdaIR, BoxIR, UnboxIR, SubscriptIR
)

def load_c_from_file(filename: str) -> str:
    """Utility function to load C code from a file"""
    """
        load from c/filename
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    c_path = os.path.join(base_path, 'c', filename)
    with open(c_path, 'r') as f:
        return f.read()

class LLVMBackend:
    """
    C backend for Nagini compiler (LLVM backend planned for future).
    Generates C code and compiles to native machine code using gcc/clang.
    """
    
    def __init__(self, ir: NaginiIR):
        self.ir = ir
        self.output_code = []
        self.declared_vars = set()  # Track declared variables
        self.main_function: Optional[FunctionIR] = None
        
    def generate(self) -> str:
        """
        Generate target code (C for initial implementation).
        Returns the generated C code as a string.
        """
        print("Generating C code from Nagini IR...")
        self.output_code = []
        
        # Generate hash table implementation
        self._gen_hmap()
        
        # Generate pool allocators
        self._gen_pools()
        
        # Generate base Object class with hash table
        self._gen_base_object()
        
        # Generate symbol table enum FIRST (needed by FunctionObject)
        self._gen_symbol_table()
        
        # Generate FunctionObject (needs symbols)
        self._gen_function_object()
        
        # Generate class structs and their methods
        for class_name, class_info in self.ir.classes.items():
            # Generate methods for this class
            for method in class_info.methods:
                self._gen_class_method(class_info, method)
            self._gen_class_struct(class_info)
        
        # Generate functions
        for func in self.ir.functions:
            self._gen_function(func)

        
        print("Generating main function...")
        # generate main function if not present
        if not self.main_function:
            raise RuntimeError("No main function defined in the program.")
        output_code = []
        # Generate headers
        self._gen_headers(output_code)
        self._gen_function(self.main_function)
        print("C code generation complete.")

        self.output_code = output_code + self.output_code
        return '\n'.join(self.output_code)
    
    def _gen_headers(self, output_code):
        """Generate necessary C headers"""
        output_code.append('#include <stdio.h>')
        output_code.append('#include <stdlib.h>')
        output_code.append('#include <stdint.h>')
        output_code.append('#include <string.h>')
        output_code.append('#include <stdbool.h>')
        output_code.append('#include <math.h>')
        output_code.append('#include <assert.h>')
        output_code.append('#include <limits.h>')
        if sys.platform == 'win32':
            output_code.append('#include <windows.h>')
            output_code.append('#include <bcrypt.h>')
        elif sys.platform == 'linux':
            output_code.append('#include <unistd.h>')
            output_code.append('#include <sys/random.h>')
        output_code.append('')
        output_code.append('/* Nagini Constants */')
        output_code.append(f'#define CONST_COUNT {self.ir.const_count}')
        output_code.append('')
        output_code.append('/* Forward declarations */')
        output_code.append('typedef struct HashTable HashTable;')
        output_code.append('typedef struct Object Object;')
        output_code.append('typedef struct DynamicPool DynamicPool;')
        output_code.append('typedef struct StaticPool StaticPool;')
        output_code.append('typedef struct Dict Dict;')
        output_code.append('typedef struct Runtime Runtime;')
        output_code.append('typedef struct Function Function;')
        output_code.append('typedef struct Set Set;')
        output_code.append('')
    
    def _gen_pools(self):
        self.output_code.append(load_c_from_file('pool.h'))
    
    def _gen_hmap(self):
        """Generate hash table implementation for Object members"""
        self.output_code.append(load_c_from_file('hmap.h'))
    
    def _gen_base_object(self):
        self.output_code.append(load_c_from_file('builtin.h'))
    
    def _gen_symbol_table(self):
        pass
    
    def _gen_function_object(self):
        """Generate FunctionObject structure for first-class functions"""
        # self.output_code.append('/* FunctionObject - first-class function representation */')
        # self.output_code.append('typedef struct FunctionObject {')
        # self.output_code.append('    HashTable* hmap;  /* Inherited from Object */')
        # self.output_code.append('    int64_t __refcount__;   /* Reference counter */')
        # self.output_code.append('    void* func_ptr;         /* Pointer to actual function */')
        # self.output_code.append('    int64_t param_count;    /* Number of parameters */')
        # self.output_code.append('    char** param_names;     /* Parameter names */')
        # self.output_code.append('    char** param_types;     /* Parameter types (NULL for untyped) */')
        # self.output_code.append('    uint8_t* strict_flags;  /* 1 if parameter has strict typing, 0 otherwise */')
        # self.output_code.append('    char* return_type;      /* Return type name */')
        # self.output_code.append('    uint8_t has_varargs;    /* 1 if function accepts *args */')
        # self.output_code.append('    uint8_t has_kwargs;     /* 1 if function accepts **kwargs */')
        # self.output_code.append('} FunctionObject;')
        # self.output_code.append('')
        
        # Type checking helper function
        self.output_code.append('/* Runtime type checking for strict parameters */')
        self.output_code.append('void check_param_type(Runtime* runtime, const char* param_name, Object* obj, const char* expected_type) {')
        self.output_code.append('    if (expected_type == NULL) return;  /* Untyped parameter */')
        self.output_code.append('    if (obj == NULL) {')
        self.output_code.append('        fprintf(stderr, "Runtime Error: Parameter \'%s\' is NULL but expected type \'%s\'\\n", param_name, expected_type);')
        self.output_code.append('        exit(1);')
        self.output_code.append('    }')
        self.output_code.append('    /* Get type name from symbol table using typename ID */')
        self.output_code.append('    char* actual_type = (char*)hmap_get(runtime->symbol_table, obj->__typename__);')
        self.output_code.append('    if (actual_type != NULL && strcmp(actual_type, expected_type) != 0) {')
        self.output_code.append('        fprintf(stderr, "Runtime Error: Parameter \'%s\' has type \'%s\' but expected \'%s\'\\n", param_name, actual_type, expected_type);')
        self.output_code.append('        exit(1);')
        self.output_code.append('    }')
        self.output_code.append('}')
        self.output_code.append('')
        
        # Argument count checking
        self.output_code.append('/* Check argument count for function calls */')
        self.output_code.append('void check_arg_count(Runtime* runtime, const char* func_name, int64_t expected, int64_t actual, uint8_t has_varargs) {')
        self.output_code.append('    if (!has_varargs && actual != expected) {')
        self.output_code.append('        fprintf(stderr, "Runtime Error: Function \'%s\' expects %lld arguments but got %lld\\n", func_name, expected, actual);')
        self.output_code.append('        exit(1);')
        self.output_code.append('    } else if (has_varargs && actual < expected) {')
        self.output_code.append('        fprintf(stderr, "Runtime Error: Function \'%s\' expects at least %lld arguments but got %lld\\n", func_name, expected, actual);')
        self.output_code.append('        exit(1);')
        self.output_code.append('    }')
        self.output_code.append('}')
        self.output_code.append('')
    
    def _gen_class_struct(self, class_info: ClassInfo):
        """Generate C struct for a Nagini class using hash table for members"""
        self.output_code.append(f'/* Class: {class_info.name} */')
        self.output_code.append(f'/* malloc_strategy: {class_info.malloc_strategy} */')
        self.output_code.append(f'/* layout: {class_info.layout} */')
        self.output_code.append(f'/* paradigm: {class_info.paradigm} */')
        self.output_code.append(f'/* parent: {class_info.parent} */')
        
        if class_info.paradigm == 'object':
            # Object paradigm uses hash table for members
            self.output_code.append(f'Object* def_class_{class_info.name}(Runtime* runtime) {{')
            self.output_code.append(f'    /* Create class {class_info.name} inheriting from {class_info.parent} */')
            self.output_code.append(f'    Object* cls = alloc_instance("{class_info.name}");')
            self.output_code.append(f'    /* {class_info.methods} Methods */')
            num_instance_methods = sum(1 for m in class_info.methods if not m.is_static and m.name != '__init__')
            current_method_index = 0
            if num_instance_methods > 0:
                self.output_code.append(f'    Object* instance_methods[{num_instance_methods}];')
            has_init = False
            for field in class_info.methods:
                self.output_code.append(f'    /* Method: {field.name} */')
                if field.name == '__init__':
                    has_init = True
                    self.output_code.append(f'    {{')
                    # Object* alloc_function(Runtime* runtime, const char* name, int32_t line, size_t arg_count, void* native_ptr)
                    self.output_code.append(f'        Object* member_name = alloc_string(runtime, "{field.name}");')
                    self.output_code.append(f'        Object* member = alloc_function(runtime, "{field.name}", {field.line_no}, {len(field.params)}, (void*)&{class_info.name}_{field.name}_{field.line_no});')
                    self.output_code.append(f'        NgSetMember(runtime, cls, member_name, member);')
                    self.output_code.append(f'')
                    for field2 in class_info.methods:
                        if field2.name == '__init__' or field2.is_static:
                            continue
                        self.output_code.append(f'        /* Initialize method: {field2.name} */')
                        self.output_code.append(f'        Object* method_str_{field2.name} = alloc_string(runtime, "{field2.name}");')
                        self.output_code.append(f'        Object* method_{field2.name} = alloc_function(runtime, "{field2.name}", {field2.line_no}, {len(field2.params)}, (void*)&{class_info.name}_{field2.name}_{field2.line_no});')
                        self.output_code.append(f'        NgSetMember(runtime, cls, method_str_{field2.name}, method_{field2.name});')
                        # self.output_code.append(f'        /* Initialize field: {field2.name} of type {field2.type_name} */')
                        # self.output_code.append(f'        Object* field_name = alloc_string(runtime, "{field2.name}");')
                        # self.output_code.append(f'        Object* default_value = alloc_default_value(runtime, "{field2.type_name}");')
                        # self.output_code.append(f'        NgSetMember(runtime, cls, field_name, default_value);')
                    self.output_code.append(f'    }}')
                elif field.is_static:
                    self.output_code.append(f'    {{')
                    self.output_code.append(f'        Object* member_name = alloc_string(runtime, "{field.name}");')
                    self.output_code.append(f'        Object* member = alloc_function(runtime, "{field.name}", {field.line_no}, {len(field.params)}, (void*)&{class_info.name}_{field.name}_{field.line_no});')
                    self.output_code.append(f'        NgSetMember(runtime, cls, member_name, member);')
                    self.output_code.append(f'    }}')
            self.output_code.append(f'    return cls;')
            self.output_code.append(f'}}')
        else:
            # Data paradigm uses direct struct (no hash table, no refcount)
            self.output_code.append(f'typedef struct {{')
            
            # Add fields directly (no hash table for data paradigm)
            if class_info.fields:
                self.output_code.append('    /* Fields (direct access) */')
                for field in class_info.fields:
                    c_type = self._map_type_to_c(field.type_name)
                    self.output_code.append(f'    {c_type} {field.name};')
            
            self.output_code.append(f'}} {class_info.name};')
            self.output_code.append('')
    
    def _gen_class_method(self, class_info: ClassInfo, method_info: FunctionInfo):
        """Generate a method for a class"""
        # Get the cached method IR (already converted during IR generation)
        cache_key = (class_info.name, method_info.name, method_info.line_no)
        if cache_key in self.ir.method_ir_cache:
            method_ir = self.ir.method_ir_cache[cache_key]
        else:
            # Fallback: convert if not in cache (shouldn't happen)
            method_ir = self.ir._convert_function_to_ir(method_info)
        
        # Track declared variables for this method
        self.declared_vars = set()
        
        # Add self and other parameters to declared vars
        for param_name, _ in method_ir.params:
            self.declared_vars.add(param_name)
        
        # Generate method signature
        # Methods take a pointer to the class instance as first parameter
        return_type = 'Object*'
        
        # Build parameter list with self pointer
        params_list = ['Runtime* runtime', f'Object* self'] if not method_info.is_static else ['Runtime* runtime']
        param_types = [class_info.name]
        for param_name, param_type in method_ir.params:
            if param_name != 'self':  # Skip self in params
                # params_list.append(f'{self._map_type_to_c(param_type) if param_type else "int64_t"} {param_name}')
                params_list.append(f'Object* {param_name}')
                param_types.append(param_type)
        
        params_str = ', '.join(params_list)
        
        self.output_code.append('')
        self.output_code.append(f'/* Parameter types for method {class_info.name}.{method_ir.name} */')
        # self.output_code.append(f'/* Types: {", ".join(param_types)} */')
        # Method name is ClassName_methodname
        method_name = f'{class_info.name}_{method_ir.name}_{method_info.line_no}'
        
        self.output_code.append(f'/* Method: {class_info.name}.{method_ir.name} */')
        self.output_code.append(f'{return_type} {method_name}({params_str}) {{')
        
        # Verify hmap_get(self.hmap, symbol_id) against expected types for strict parameters (symbol_id should be of '__typename__' convention)
            
        # Generate method body
        for stmt in method_ir.body:
            stmt_code = self._gen_stmt(stmt, indent=1)
            self.output_code.extend(stmt_code)

        # check if return statement is present
        has_return = any(isinstance(stmt, ReturnIR) for stmt in method_ir.body)
        if not has_return:
            self.output_code.append('    return NULL;')
        
        self.output_code.append('}')
        self.output_code.append('')
        
    def _gen_function(self, func: FunctionIR):
        if func.name == 'main' and not self.main_function:
            self.main_function = func
            return

        """Generate C function from IR"""
        # Track declared variables for this function
        self.declared_vars = set()
        
        # Add parameters to declared vars
        for param_name, _ in func.params:
            self.declared_vars.add(param_name)
        
        # Generate function signature
        return_type = self._map_type_to_c(func.return_type)
        
        # Special case for main - always return int
        if func.name == 'main':
            return_type = 'int'
        
        # Build parameter list
        params_str = ', '.join([
            f'{self._map_type_to_c(t) if t else "int64_t"} {n}' 
            for n, t in func.params
        ]) if func.params else 'void'
        
        self.output_code.append(f'{return_type} {func.name}({params_str}) {{')
        
        # Add runtime type checks for strict parameters at function entry
        # Only check for object types (classes), not primitives like int, float, bool, str
        if func.strict_params:
            for param_name, param_type in func.params:
                if param_name in func.strict_params and param_type:
                    # Check if this is a custom class (not a primitive type)
                    if param_type not in ['int', 'float', 'bool', 'str', 'void']:
                        self.output_code.append(f'    /* Runtime type check for strict parameter: {param_name} */')
                        self.output_code.append(f'    check_param_type("{param_name}", {param_name}, "{param_type}");')
        
        # Init main function body
        if func.name == 'main':
            self.output_code.append('    /* Runtime and Symbol table */')
            self.output_code.append('    Runtime* runtime = init_runtime();')
            self.output_code.append('')
            self.output_code.append('    /*')
            self.output_code.append(f'    total constants: {self.ir.const_count}')
            self.output_code.append('    */')
            for k, v in self.ir.consts.items():
                a, b = v
                self.output_code.append(f'    runtime->constants[{k}] = {b}(runtime, {a});')
            self.output_code.append('')
            self.output_code.append('    /* Initialize built-in classes and functions */')
            self.output_code.append('    /* Initialize user-defined classes */')
            for class_name in self.ir.classes.keys():
                self.output_code.append(f'    Object* class_{class_name} = def_class_{class_name}(runtime);')
            for func_name in self.ir.classes.keys():
                self.output_code.append(f'    dict_set(runtime, runtime->classes, runtime->constants[{self.ir.classes[func_name].name_id}], class_{func_name});')

        # Generate function body
        for stmt in func.body:
            stmt_code = self._gen_stmt(stmt, indent=1)
            self.output_code.extend(stmt_code)
        
        # Add default return for main or void functions
        if func.name == 'main':
            self.output_code.append('    return 0;')
        
        self.output_code.append('}')
        self.output_code.append('')
    
    def _gen_stmt(self, stmt: StmtIR, indent: int = 0) -> list:
        """Generate C code for a statement IR node"""
        ind = '    ' * indent
        result = []
        
        if isinstance(stmt, AssignIR):
            # Variable assignment
            expr_code = self._gen_expr(stmt.value)
            # Check if variable is already declared
            if stmt.target in self.declared_vars:
                # Already declared, just assign
                result.append(f'{ind}{stmt.target} = {expr_code};')
            else:
                # First declaration
                result.append(f'{ind}int64_t {stmt.target} = {expr_code};')
                self.declared_vars.add(stmt.target)
        
        elif isinstance(stmt, ReturnIR):
            # Return statement
            if stmt.value:
                expr_code = self._gen_expr(stmt.value)
                result.append(f'{ind}return {expr_code};')
            else:
                result.append(f'{ind}return;')
        
        elif isinstance(stmt, IfIR):
            # If statement
            cond_code = self._gen_expr(stmt.condition)
            result.append(f'{ind}if ({cond_code}) {{')
            for body_stmt in stmt.then_body:
                result.extend(self._gen_stmt(body_stmt, indent + 1))
            
            # Handle elif
            for elif_cond, elif_body in stmt.elif_parts:
                result.append(f'{ind}}} else if ({self._gen_expr(elif_cond)}) {{')
                for body_stmt in elif_body:
                    result.extend(self._gen_stmt(body_stmt, indent + 1))
            
            # Handle else
            if stmt.else_body:
                result.append(f'{ind}}} else {{')
                for body_stmt in stmt.else_body:
                    result.extend(self._gen_stmt(body_stmt, indent + 1))
            
            result.append(f'{ind}}}')
        
        elif isinstance(stmt, WhileIR):
            # While loop
            cond_code = self._gen_expr(stmt.condition)
            result.append(f'{ind}while ({cond_code}) {{')
            for body_stmt in stmt.body:
                result.extend(self._gen_stmt(body_stmt, indent + 1))
            result.append(f'{ind}}}')
        
        elif isinstance(stmt, ForIR):
            # For loop (simplified - assume range-like iteration)
            iter_code = self._gen_expr(stmt.iter_expr)
            # For now, handle simple range() calls
            result.append(f'{ind}/* For loop: for {stmt.target} in {iter_code} */')
            result.append(f'{ind}/* TODO: Implement full for loop support */')
        
        elif isinstance(stmt, ExprStmtIR):
            # Expression statement (e.g., function call)
            expr_code = self._gen_expr(stmt.expr)
            result.append(f'{ind}{expr_code};')

        # elif 
        
        return result
    
    def _gen_expr(self, expr: ExprIR) -> str:
        """Generate C code for an expression IR node"""
        if isinstance(expr, ConstantIR):
            if expr.type_name == 'int':
                return f'runtime->constants[{expr.value}]'
            elif expr.type_name == 'float':
                return f'runtime->constants[{expr.value}]'
            elif expr.type_name == 'bool':
                return f'runtime->constants[{expr.value}]'
            elif expr.type_name == 'str':
                return f'runtime->constants[{expr.value}]'
            elif expr.type_name == 'bytes':
                return f'runtime->constants[{expr.value}]'
            else:
                raise ValueError(f'Unknown constant type: {expr.type_name}')
        
        elif isinstance(expr, VariableIR):
            # Variable reference
            return expr.name
        
        elif isinstance(expr, BinOpIR):
            # Binary operation
            left_code = self._gen_expr(expr.left)
            right_code = self._gen_expr(expr.right)
            
            # Map operators
            op_map = {
                'and': '&&',
                'or': '||',
                '**': 'pow',  # Will need to handle specially
            }
            op = op_map.get(expr.op, expr.op)
            op_funcs = {
                '+': 'NgAdd',
                '-': 'NgSub',
                '*': 'NgMul',
                '/': 'NgDiv',
                '%': 'NgMod',
                '==': 'NgEq',
                '!=': 'NgNeq',
                '<': 'NgLt',
                '<=': 'NgLeq',
                '>': 'NgGt',
                '>=': 'NgGeq',
                'and': 'NgAnd',
                'or': 'NgOr',
            }
            
            if expr.op == '**':
                # Power operation needs pow() function
                return f'NgPow(runtime, {left_code}, {right_code})'
            else:
                return f'{op_funcs[op]}(runtime, {left_code}, {right_code})'
        
        elif isinstance(expr, UnaryOpIR):
            # Unary operation
            operand_code = self._gen_expr(expr.operand)
            op_map = {
                'not': '!',
                '-': '-',
                '+': '+',
            }
            op = op_map.get(expr.op, expr.op)
            return f'{op}({operand_code})'
        
        elif isinstance(expr, CallIR):
            # Function/method call
            if expr.is_method:
                # Method call - for now, treat as function
                obj_code = self._gen_expr(expr.obj)
                args_code = ', '.join([self._gen_expr(arg) for arg in expr.args])
                return f'{obj_code}.{expr.func_name}({args_code})'
            else:
                # Regular function call
                args_code = ', '.join([self._gen_expr(arg) for arg in expr.args])
                
                # Map special functions
                if expr.func_name == 'print':
                    # Map print to printf with proper formatting
                    if not expr.args:
                        return 'printf("\\n")'
                    
                    # Build format string and arguments
                    format_parts = []
                    args_list = []
                    for arg in expr.args:
                        arg_code = self._gen_expr(arg)
                        # Determine format specifier based on arg type
                        if isinstance(arg, ConstantIR):
                            if arg.type_name == 'str':
                                format_parts.append('%s')
                                args_list.append(arg_code)
                            elif arg.type_name == 'int':
                                format_parts.append('%lld')
                                args_list.append(arg_code)
                            elif arg.type_name == 'float':
                                format_parts.append('%f')
                                args_list.append(arg_code)
                            else:
                                format_parts.append('%s')
                                args_list.append(arg_code)
                        elif isinstance(arg, VariableIR):
                            # Assume int64_t for variables
                            format_parts.append('%lld')
                            args_list.append(arg_code)
                        else:
                            # Default to int format
                            format_parts.append('%lld')
                            args_list.append(arg_code)
                    
                    format_str = ' '.join(format_parts)
                    if args_list:
                        return f'printf("{format_str}\\n", {", ".join(args_list)})'
                    else:
                        return 'printf("\\n")'
                
                return f'{expr.func_name}({args_code})'
        
        elif isinstance(expr, AttributeIR):
            # Member access
            obj_code = self._gen_expr(expr.obj)
            # For InstanceObject, use dict_get with the __dict__
            # For now, we'll use a simplified approach
            # if isinstance(expr.obj, VariableIR) and expr.obj.name in self.declared_vars:
                # Accessing member on a known variable (possibly self)
                # Cast to InstanceObject and access via __dict__
                # return f'dict_get(runtime, ((InstanceObject* ){obj_code})->__dict__, runtime->builtin_names.{expr.attr})'
            return f'NgGetMember(runtime, {obj_code}, runtime->constants[{expr.attr}])'
            # return f'{obj_code}.{expr.attr}'
        
        elif isinstance(expr, SubscriptIR):
            # Subscript access (obj[index])
            obj_code = self._gen_expr(expr.obj)
            index_code = self._gen_expr(expr.index)
            return f'{obj_code}[{index_code}]'
        
        elif isinstance(expr, ConstructorCallIR):
            # Constructor call (ClassName(...))
            # Generate call to create_classname() function
            func_name = f'{expr.class_name}___init__'
            args_code = ', '.join([self._gen_expr(arg) for arg in expr.args])
            return f'{func_name}({args_code})'
        
        elif isinstance(expr, LambdaIR):
            # Lambda expression - generate as inline anonymous function
            # For now, we'll generate a comment noting lambda support is limited
            # Full lambda support requires generating a static function and returning a function pointer
            params_str = ', '.join([f'{name}' for name, _ in expr.params])
            body_code = self._gen_expr(expr.body)
            return f'/* lambda({params_str}): {body_code} - TODO: Full lambda support */'
        
        elif isinstance(expr, BoxIR):
            # Box a primitive value into an object
            inner_code = self._gen_expr(expr.expr)
            if expr.target_type == 'Int':
                return f'box_int({inner_code})'
            elif expr.target_type == 'Double':
                return f'box_double({inner_code})'
            return inner_code
        
        elif isinstance(expr, UnboxIR):
            # Unbox an object to a primitive value
            inner_code = self._gen_expr(expr.expr)
            if expr.source_type == 'Int':
                return f'unbox_int({inner_code})'
            elif expr.source_type == 'Double':
                return f'unbox_double({inner_code})'
            return inner_code
        
        return '/* unknown expr */'
    
    def _map_type_to_c(self, nagini_type: str) -> str:
        """Map Nagini types to C types"""
        type_map = {
            'int': 'int64_t',
            'float': 'double',
            'bool': 'uint8_t',
            'str': 'char*',
            'void': 'void',
        }
        return type_map.get(nagini_type, 'void*')
    
    def compile_to_executable(self, output_path: str, c_code: str) -> bool:
        """
        Compile generated C code to executable using gcc/clang.
        
        Args:
            output_path: Path to output executable
            c_code: Generated C code
            
        Returns:
            True if compilation successful, False otherwise
        """
        import tempfile
        import subprocess
        import os
        
        # Write C code to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(c_code)
            c_file = f.name
        
        try:
            # Try to compile with gcc (or clang as fallback)
            compilers = ['gcc', 'clang', 'cc']
            for compiler in compilers:
                try:
                    result = subprocess.run(
                        [compiler, c_file, '-o', output_path],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        return True
                    else:
                        print(f"Compilation error with {compiler}:")
                        print(result.stderr)
                except FileNotFoundError:
                    continue
            
            print("No C compiler found. Please install gcc or clang.")
            return False
            
        finally:
            # Clean up temporary file
            if os.path.exists(c_file):
                os.unlink(c_file)
