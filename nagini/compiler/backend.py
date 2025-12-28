"""
Nagini C Backend
Generates C code and compiles to native machine code using gcc/clang.
Future versions will support direct LLVM IR generation.
"""

import os
import sys
from typing import Dict, Optional
from .parser import ClassInfo, FieldInfo, FunctionInfo
import secrets
import string
from .ir import (
    NaginiIR, FunctionIR, StmtIR, ExprIR,
    ConstantIR, VariableIR, BinOpIR, UnaryOpIR, CallIR, AttributeIR,
    AssignIR, SubscriptAssignIR, ReturnIR, IfIR, WhileIR, ForIR, ExprStmtIR, WithIR,
    ConstructorCallIR, LambdaIR, BoxIR, UnboxIR, SubscriptIR,
    SetAttrIR, JoinedStrIR, FormattedValueIR, AugAssignIR, MultiAssignIR, SliceIR,
    TupleIR, ListIR, DictIR
)

fun_ids = {}

def parse_func_call_args_kwargs(self, expr):
    num_args = len(expr.args)
    args = []
    kwargs = []
    for arg in expr.args:
        if isinstance(arg, AssignIR):
            # Keyword argument
            kw_name = arg.target
            kw_value_code = f'{arg.value}'
            # kwargs.append(f'{{runtime->constants[{kw_name}], {kw_value_code}}}')
            raise NotImplementedError("Keyword arguments in function calls not yet implemented.")
        else:
            arg_code = self._gen_expr(arg)
            args.append(arg_code)
    args_code = ', '.join(args)
    atuple = f'alloc_tuple(runtime, {num_args}, (Object*[]) {{{args_code}}})' if num_args > 0 else 'NULL'
    return atuple, 'NULL'  # kwargs not implemented yet

def gen_uuid(length=16):
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return ''.join(secrets.choice(characters) for _ in range(length))

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
        self._zero_const_id: Optional[int] = None
        self._one_const_id: Optional[int] = None
        
    def generate(self) -> str:
        """
        Generate target code (C for initial implementation).
        Returns the generated C code as a string.
        """
        print("Generating C code from Nagini IR...")
        self.output_code = []

        # Register all classes
        for class_name, class_info in self.ir.classes.items():
            self.ir.classes[class_name].name_id = self.ir.register_string_constant(class_name)
            self.ir.register_class_constant(class_info)

        # Ensure commonly used loop constants exist before headers are emitted
        self._pre_register_loop_constants()
        
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
            if func.name != 'main':
                ident = fun_ids.get(func.name)
                if ident is None:
                    ident = gen_uuid(16)
                    fun_ids[func.name] = ident
                func.name = f'{func.name}_{ident}'
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

    def _ensure_int_const(self, value: int) -> int:
        """Ensure an int constant is registered and return its id."""
        key = ('int', value)
        if key in self.ir.consts_dict:
            return int(self.ir.consts_dict[key])
        ident_int = int(self.ir.register_int_constant(value))
        self.ir.consts_dict[key] = ident_int
        return ident_int

    def _pre_register_loop_constants(self):
        """Pre-register int constants needed by for-range lowering (0 and 1)."""
        need_zero = False
        need_one = False

        def scan_stmts(stmts):
            nonlocal need_zero, need_one
            for stmt in stmts:
                if isinstance(stmt, ForIR) and isinstance(stmt.iter_expr, CallIR) and stmt.iter_expr.func_name == 'range':
                    argc = len(stmt.iter_expr.args)
                    if argc == 1:
                        need_zero = True
                        need_one = True
                    elif argc >= 2:
                        need_one = True
                # Recurse into nested bodies
                if isinstance(stmt, IfIR):
                    scan_stmts(stmt.then_body)
                    for _, body in stmt.elif_parts:
                        scan_stmts(body)
                    if stmt.else_body:
                        scan_stmts(stmt.else_body)
                elif isinstance(stmt, WhileIR):
                    scan_stmts(stmt.body)
                elif isinstance(stmt, ForIR):
                    scan_stmts(stmt.body)
                elif isinstance(stmt, WithIR):
                    scan_stmts(stmt.body)

        # Scan functions
        for func in self.ir.functions:
            scan_stmts(func.body)
        # Scan cached methods
        for _, method_ir in self.ir.method_ir_cache.items():
            scan_stmts(method_ir.body)

        if need_zero and self._zero_const_id is None:
            self._zero_const_id = self._ensure_int_const(0)
        if need_one and self._one_const_id is None:
            self._one_const_id = self._ensure_int_const(1)
    
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
        output_code.append('typedef struct InstanceObject InstanceObject;')
        output_code.append('typedef struct StringObject StringObject;')
        output_code.append('typedef struct DynamicPool DynamicPool;')
        output_code.append('typedef struct StaticPool StaticPool;')
        output_code.append('typedef struct Dict Dict;')
        output_code.append('typedef struct Runtime Runtime;')
        output_code.append('typedef struct Function Function;')
        output_code.append('typedef struct Set Set;')
        output_code.append('typedef struct Tuple Tuple;')
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
        self.output_code.append('        fprintf(stderr, "Runtime Error: Function \'%s\' expects %ld arguments but got %ld\\n", func_name, expected, actual);')
        self.output_code.append('        exit(1);')
        self.output_code.append('    } else if (has_varargs && actual < expected) {')
        self.output_code.append('        fprintf(stderr, "Runtime Error: Function \'%s\' expects at least %ld arguments but got %ld\\n", func_name, expected, actual);')
        self.output_code.append('        exit(1);')
        self.output_code.append('    }')
        self.output_code.append('}')
        self.output_code.append('')

        # Basic slice helper (placeholder for future full implementation)
        self.output_code.append('Object* NgSlice(Runtime* runtime, void* obj, void* start, void* stop, void* step) {')
        self.output_code.append('    (void)runtime; (void)obj; (void)start; (void)stop; (void)step;')
        self.output_code.append('    /* TODO: Implement slicing semantics */')
        self.output_code.append('    return (Object*)obj;')
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
            # same args as __init__
            prms = ''
            args = ''
            for field in class_info.methods:
                if field.name == '__init__':
                    for param_name, param_type in field.params:
                        if param_name == 'self':
                            continue
                        args += f', {param_name}'
                        prms += f', Object* {param_name}'

            self.output_code.append(f'Object* NgAlloc{class_info.name}(Runtime* runtime, Tuple* args, Dict* kwargs) {{')
            self.output_code.append(f'    /* Allocate instance of {class_info.name} */')
                
            self.output_code.append(f'    Object* self = alloc_instance(runtime);')
            self.output_code.append(f'    args = (Tuple*) NgPrependTuple(runtime, self, args);')
            self.output_code.append(f'    {class_info.name}___init__(runtime, args, kwargs);')
            self.output_code.append(f'    /* Set class */')

            # self.ir.classes[class_name].name_id = self.ir.register_string_constant(class_name)
            # self.ir.register_class_constant(class_info)
            self.output_code.append(f'    NgSetMember(runtime, self, runtime->builtin_names.__class__, runtime->constants[{self.ir.register_class_constant(class_info)}]);')

            for method in class_info.methods:
                if method.name == '__init__' or method.is_static:
                    continue
                self.output_code.append(f'    /* Initialize method: {method.name} */')
                self.output_code.append(f'    NgSetMember(runtime, self, runtime->constants[{method.name_id}], runtime->constants[{method.func_id}]);')
            self.output_code.append(f'    return self;')
            self.output_code.append(f'}}')
            self.output_code.append('')
            self.output_code.append(f'Object* def_class_{class_info.name}(Runtime* runtime) {{')
            self.output_code.append(f'    /* Create class {class_info.name} inheriting from {class_info.parent} */')
            self.output_code.append(f'    Object* cls = alloc_instance(runtime);')
            self.output_code.append(f'    NgSetMember(runtime, cls, runtime->builtin_names.__typename__, runtime->constants[{class_info.name_id}]);')
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
                    self.output_code.append(f'        NgSetMember(runtime, cls, runtime->constants[{field.name_id}], runtime->constants[{field.func_id}]);')
                    self.output_code.append(f'')
                    for field2 in class_info.methods:
                        if field2.name == '__init__' or field2.is_static:
                            continue
                        self.output_code.append(f'        /* Initialize method: {field2.name} */')
                        self.output_code.append(f'        NgSetMember(runtime, cls, runtime->constants[{field2.name_id}], runtime->constants[{field2.func_id}]);')
                        # self.output_code.append(f'        /* Initialize field: {field2.name} of type {field2.type_name} */')
                        # self.output_code.append(f'        Object* field_name = alloc_string(runtime, "{field2.name}");')
                        # self.output_code.append(f'        Object* default_value = alloc_default_value(runtime, "{field2.type_name}");')
                        # self.output_code.append(f'        NgSetMember(runtime, cls, field_name, default_value);')
                    self.output_code.append(f'    }}')
                elif field.is_static:
                    self.output_code.append(f'    {{')
                    self.output_code.append(f'        NgSetMember(runtime, cls, runtime->constants[{field.name_id}], runtime->constants[{field.func_id}]);')
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
        method_name = f'{class_info.name}_{method_ir.name}'
        
        self.output_code.append(f'/* Method: {class_info.name}.{method_ir.name} */')
        self.output_code.append(f'{return_type} {method_name}(Runtime* runtime, Tuple* args, Dict* kwargs) {{')
        self.output_code.append(f'    if (args->size < {len(method_ir.params)}) {{')
        self.output_code.append(f'        fprintf(stderr, "Runtime Error: Method \'{class_info.name}.{method_ir.name}\' expects at least {len(method_ir.params)} arguments but got %zu\\n", args->size);')
        self.output_code.append(f'        exit(1);')
        self.output_code.append(f'    }}')
        self.output_code.append('')
        for i, (param_name, param_type) in enumerate(method_ir.params):
            self.output_code.append(f'    /* Extract parameter: {param_name} */')
            self.output_code.append(f'    Object* {param_name} = args->items[{i}];')
            if param_type:
                self.output_code.append(f'    char pName_{param_name}[64];')
                self.output_code.append(f'    NgGetTypeName(runtime, {param_name}, pName_{param_name}, sizeof(pName_{param_name}));')
                self.output_code.append(f'    if (strcmp("{param_type}", pName_{param_name}) != 0) {{')
                self.output_code.append(f'        fprintf(stderr, "Runtime Error: Received wrong type for parameter \'{param_name}\' in method \'{class_info.name}.{method_ir.name}\'.\\n Expected type: {param_type}, got: %s\\n", pName_{param_name});')
                self.output_code.append(f'        exit(1);')
                self.output_code.append(f'    }}')
            
        
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
        # return_type = self._map_type_to_c(func.return_type)
        
        # Special case for main - always return int
        if func.name == 'main':
            return_type = 'int'
            declared_vars = set()
        else:
            return_type = 'Object*'
        
        # Build parameter list
        params_str = 'Runtime* runtime, Tuple* args, Dict* kwargs' if not func.name == 'main' else 'void'
        self.output_code.append(f'{return_type} {func.name}({params_str}) {{')
        if not func.name == 'main':
            self.output_code.append(f'    if (args->size < {len(func.params)}) {{')
            self.output_code.append(f'        fprintf(stderr, "Runtime Error: Function \'{func.name}\' expects at least {len(func.params)} arguments but got %zu\\n", args->size);')
            self.output_code.append(f'        exit(1);')
            self.output_code.append(f'    }}')
        for param_name, _ in func.params:
            self.output_code.append(f'    /* Extract parameter: {param_name} */')
            self.output_code.append(f'    Object* {param_name} = args->items[{len(self.declared_vars) - len(func.params) + func.params.index((param_name, _))}];')
            if _:
                self.output_code.append(f'    char pName_{param_name}[64];')
                self.output_code.append(f'    NgGetTypeName(runtime, {param_name}, pName_{param_name}, sizeof(pName_{param_name}));')
                self.output_code.append(f'    if (strcmp("{_}", pName_{param_name}) != 0) {{')
                self.output_code.append(f'        fprintf(stderr, "Runtime Error: Received wrong type for parameter \'{param_name}\' in function \'{func.name}\'.\\n Expected type: {_}, got: %s\\n", pName_{param_name});')
                self.output_code.append(f'        exit(1);')
                self.output_code.append(f'    }}')
        
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
                if isinstance(v, ClassInfo):
                    self.output_code.append(f'    runtime->constants[{k}] = def_class_{v.name}(runtime);')
                    self.output_code.append(f'    dict_set(runtime, runtime->classes, runtime->constants[{v.name_id}], runtime->constants[{k}]);')
                elif isinstance(v, FunctionInfo):
                    self.output_code.append(f'    runtime->constants[{k}] = alloc_function(runtime, "{v.name}", {v.line_no}, {len(v.params)}, (void*)&{v.full_name});')
                else:
                    a, b = v
                    self.output_code.append(f'    runtime->constants[{k}] = {b}(runtime, {a});')
            self.output_code.append('')

        # Generate function body
        for stmt in func.body:
            stmt_code = self._gen_stmt(stmt, indent=1)
            self.output_code.extend(stmt_code)

        # if no return statement, add default return
        has_return = any(isinstance(stmt, ReturnIR) for stmt in func.body)
        
        # Add default return for main or void functions
        if func.name == 'main':
            self.output_code.append('    return 0;')
        elif not has_return:
            if return_type == 'Object*':
                self.output_code.append('    return NULL;')
        
        self.output_code.append('}')
        self.output_code.append('')
    
    def _gen_stmt(self, stmt: StmtIR, indent: int = 0) -> list:
        """Generate C code for a statement IR node"""
        ind = '    ' * indent
        result = []

        if isinstance(stmt, SetAttrIR):
            # Set attribute on object
            obj_code = self._gen_expr(stmt.obj)
            value_code = self._gen_expr(stmt.value)
            result.append(f'{ind}NgSetMember(runtime, {obj_code}, runtime->constants[{stmt.attr}], {value_code});')
        
        elif isinstance(stmt, AugAssignIR):
            # Augmented assignment (e.g., x += y)
            target_code = self._gen_expr(stmt.target)
            value_code = self._gen_expr(stmt.value)
            op = stmt.op
            result.append(f'{ind}{target_code} = NgBinaryOp(runtime, {target_code}, {value_code}, "{op}");')
        
        elif isinstance(stmt, SubscriptAssignIR):
            # Subscript assignment (obj[index] = value)
            obj_code = self._gen_expr(stmt.obj)
            index_code = self._gen_expr(stmt.index)
            value_code = self._gen_expr(stmt.value)
            result.append(f'{ind}NgSetItem(runtime, {obj_code}, {index_code}, {value_code});')

        elif isinstance(stmt, MultiAssignIR):
            result.extend(self._emit_multi_assign(stmt, indent, self._gen_stmt))

        elif isinstance(stmt, AssignIR):
            # Variable assignment
            expr_code = self._gen_expr(stmt.value)
            # Check if variable is already declared
            if stmt.target in self.declared_vars:
                # Already declared, just assign
                result.append(f'{ind}{stmt.target} = {expr_code};')
            else:
                # First declaration
                result.append(f'{ind}Object* {stmt.target} = {expr_code};')
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
            cond_expr = self._gen_expr(stmt.condition)
            cond_code = f'NgCastToInt(runtime, {cond_expr})'
            result.append(f'{ind}while ({cond_code}) {{')
            for body_stmt in stmt.body:
                result.extend(self._gen_stmt(body_stmt, indent + 1))
            result.append(f'{ind}}}')
        
        elif isinstance(stmt, ForIR):
            # For loop (simplified - assume range-like iteration)
            if isinstance(stmt.iter_expr, CallIR) and stmt.iter_expr.func_name == 'range':
                if self._zero_const_id is None:
                    self._zero_const_id = self._ensure_int_const(0)
                if self._one_const_id is None:
                    self._one_const_id = self._ensure_int_const(1)
                args = stmt.iter_expr.args
                # Determine start, end, step
                if len(args) == 1:
                    start_expr = ConstantIR(self._zero_const_id, 'int')
                    end_expr = args[0]
                    step_expr = ConstantIR(self._one_const_id, 'int')
                elif len(args) == 2:
                    start_expr = args[0]
                    end_expr = args[1]
                    step_expr = ConstantIR(self._one_const_id, 'int')
                elif len(args) >= 3:
                    start_expr = args[0]
                    end_expr = args[1]
                    step_expr = args[2]
                else:
                    return result

                start_code = f'NgCastToInt(runtime, {self._gen_expr(start_expr)})'
                end_code = f'NgCastToInt(runtime, {self._gen_expr(end_expr)})'
                step_code = f'NgCastToInt(runtime, {self._gen_expr(step_expr)})'

                if stmt.target not in self.declared_vars:
                    result.append(f'{ind}Object* {stmt.target} = NULL;')
                    self.declared_vars.add(stmt.target)

                temp_id = gen_uuid(16)
                result.append(f'{ind}{{')
                result.append(f'{ind}    int64_t __start{temp_id} = {start_code};')
                result.append(f'{ind}    int64_t __end{temp_id} = {end_code};')
                result.append(f'{ind}    int64_t __step{temp_id} = {step_code};')
                result.append(f'{ind}    if (__step{temp_id} == 0) {{ fprintf(stderr, "Runtime Error: range() step argument must not be zero.\\n"); exit(1); }}')
                result.append(f'{ind}    for (int64_t __i{temp_id} = __start{temp_id}; (__step{temp_id} > 0) ? (__i{temp_id} < __end{temp_id}) : (__i{temp_id} > __end{temp_id}); __i{temp_id} += __step{temp_id}) {{')
                result.append(f'{ind}        if ({stmt.target}) DECREF(runtime, {stmt.target});')
                result.append(f'{ind}        {stmt.target} = alloc_int(runtime, __i{temp_id});')

                for body_stmt in stmt.body:
                    result.extend(self._gen_stmt(body_stmt, indent + 2))

                result.append(f'{ind}    }}')
                result.append(f'{ind}}}')
            else:
                iter_code = self._gen_expr(stmt.iter_expr)
                result.append(f'{ind}/* For loop: for {stmt.target} in {iter_code} (unsupported iterator) */')
        
        elif isinstance(stmt, ExprStmtIR):
            # Expression statement (e.g., function call)
            expr_code = self._gen_expr(stmt.expr)
            result.append(f'{ind}{expr_code};')
        
        elif isinstance(stmt, WithIR):
            # With statement (context manager)
            # Special handling for nexc() calls
            if isinstance(stmt.context_expr, CallIR) and stmt.context_expr.func_name == 'nexc':
                # This is a nexc block - generate optimized native C code
                result.extend(self._gen_nexc_block(stmt, indent))
            else:
                # Generic context manager (not yet implemented)
                result.append(f'{ind}/* TODO: Generic context manager support */')
                # For now, just execute the body without context manager
                for body_stmt in stmt.body:
                    result.extend(self._gen_stmt(body_stmt, indent))

        # elif 
        
        return result
    
    def _gen_nexc_block(self, stmt: WithIR, indent: int = 0) -> list:
        """Generate optimized native C code for nexc block"""
        ind = '    ' * indent
        result = []
        
        # Extract target name from nexc() call
        target_platform = 'cpu'  # default
        if stmt.context_expr.args:
            # Get the target platform from the first argument
            arg = stmt.context_expr.args[0]
            if isinstance(arg, ConstantIR) and arg.type_name == 'str':
                # Will need to get actual string value from constants
                pass
        
        result.append(f'{ind}{{')
        result.append(f'{ind}    /* Native Execution Context (nexc) - {target_platform} target */')
        
        # Track native arrays and their types for this nexc block
        nexc_arrays = {}
        
        # Process the body to find array allocations and generate native code
        for body_stmt in stmt.body:
            result.extend(self._gen_nexc_stmt(body_stmt, indent + 1, nexc_arrays, stmt.target))
        
        result.append(f'{ind}}}')
        return result
    
    def _gen_nexc_stmt(self, stmt: StmtIR, indent: int, nexc_arrays: dict, context_var: str) -> list:
        """Generate native C code for statements inside nexc block"""
        ind = '    ' * indent
        result = []
        
        if isinstance(stmt, SubscriptAssignIR):
            # Array element assignment (array[i] = value)
            obj_code = self._gen_nexc_expr(stmt.obj, nexc_arrays)
            index_code = self._gen_nexc_expr(stmt.index, nexc_arrays)
            value_code = self._gen_nexc_expr(stmt.value, nexc_arrays)
            result.append(f'{ind}{obj_code}[{index_code}] = {value_code};')
            return result

        elif isinstance(stmt, MultiAssignIR):
            result.extend(self._emit_multi_assign(stmt, indent, lambda s, i: self._gen_nexc_stmt(s, i, nexc_arrays, context_var)))
            return result
        
        elif isinstance(stmt, AssignIR):
            # Check if this is a native array allocation
            if isinstance(stmt.value, CallIR):
                call = stmt.value
                # Check for optim.array(), optim.zeros(), optim.ones()
                if isinstance(call.obj, VariableIR) and call.obj.name == context_var:
                    method_name = call.func_name
                    if method_name in ['array', 'zeros', 'ones']:
                        # This is a native array allocation
                        size_expr = call.args[0] if call.args else ConstantIR(0, 'int')
                        size_code = self._gen_nexc_expr(size_expr, nexc_arrays)
                        
                        # Get type from kwargs
                        array_type = 'double'  # default
                        if call.kwargs and 'type' in call.kwargs:
                            type_expr = call.kwargs['type']
                            # Check if type is an attribute (e.g., optim.fp32)
                            if isinstance(type_expr, AttributeIR):
                                # Get the type name from the attribute
                                type_name = self._get_type_name_from_attr(type_expr)
                                array_type = self._map_nexc_type_to_c(type_name)
                            elif isinstance(type_expr, VariableIR):
                                # Fallback to default for now
                                array_type = 'double'
                        
                        # Generate native C array
                        init_value = ''
                        if method_name == 'zeros':
                            init_value = ' = {0}'
                        elif method_name == 'ones':
                            result.append(f'{ind}{array_type} {stmt.target}[{size_code}];')
                            result.append(f'{ind}for(int __i_{stmt.target} = 0; __i_{stmt.target} < {size_code}; __i_{stmt.target}++) {{')
                            init_val = '1.0' if 'double' in array_type or 'float' in array_type else '1'
                            result.append(f'{ind}    {stmt.target}[__i_{stmt.target}] = {init_val};')
                            result.append(f'{ind}}}')
                            nexc_arrays[stmt.target] = {'type': array_type, 'size': size_code}
                            return result
                        
                        result.append(f'{ind}{array_type} {stmt.target}[{size_code}]{init_value};')
                        nexc_arrays[stmt.target] = {'type': array_type, 'size': size_code}
                        return result
            
            # Check if this is an array element assignment
            if isinstance(stmt.value, BinOpIR) or isinstance(stmt.value, ConstantIR) or isinstance(stmt.value, VariableIR):
                # Regular assignment inside nexc - use native types
                value_code = self._gen_nexc_expr(stmt.value, nexc_arrays)
                if stmt.target in nexc_arrays:
                    # Already declared
                    result.append(f'{ind}{stmt.target} = {value_code};')
                else:
                    # New variable - use native type
                    result.append(f'{ind}double {stmt.target} = {value_code};')
                    nexc_arrays[stmt.target] = {'type': 'double', 'size': 1}
                return result
        
        elif isinstance(stmt, ExprStmtIR):
            # Expression statement - might be subscript assignment
            if isinstance(stmt.expr, SetAttrIR):
                # This shouldn't happen in nexc
                pass
            else:
                expr_code = self._gen_nexc_expr(stmt.expr, nexc_arrays)
                result.append(f'{ind}{expr_code};')
            return result
        
        elif isinstance(stmt, ForIR):
            # For loop - generate native C for loop
            # Assume range-based iteration for now
            if isinstance(stmt.iter_expr, CallIR) and stmt.iter_expr.func_name == 'range':
                # range(n) loop
                if stmt.iter_expr.args:
                    end_expr = stmt.iter_expr.args[0]
                    end_code = self._gen_nexc_expr(end_expr, nexc_arrays)
                    result.append(f'{ind}for(int {stmt.target} = 0; {stmt.target} < {end_code}; {stmt.target}++) {{')
                    
                    # Generate body
                    for body_stmt in stmt.body:
                        result.extend(self._gen_nexc_stmt(body_stmt, indent + 1, nexc_arrays, context_var))
                    
                    result.append(f'{ind}}}')
                return result
        
        elif isinstance(stmt, IfIR):
            # If statement
            cond_code = self._gen_nexc_expr(stmt.condition, nexc_arrays)
            result.append(f'{ind}if ({cond_code}) {{')
            for body_stmt in stmt.then_body:
                result.extend(self._gen_nexc_stmt(body_stmt, indent + 1, nexc_arrays, context_var))
            if stmt.else_body:
                result.append(f'{ind}}} else {{')
                for body_stmt in stmt.else_body:
                    result.extend(self._gen_nexc_stmt(body_stmt, indent + 1, nexc_arrays, context_var))
            result.append(f'{ind}}}')
            return result
        
        elif isinstance(stmt, WhileIR):
            # While loop
            cond_code = self._gen_nexc_expr(stmt.condition, nexc_arrays)
            result.append(f'{ind}while ({cond_code}) {{')
            for body_stmt in stmt.body:
                result.extend(self._gen_nexc_stmt(body_stmt, indent + 1, nexc_arrays, context_var))
            result.append(f'{ind}}}')
            return result
        
        # Fallback: generate standard statement
        result.extend(self._gen_stmt(stmt, indent))
        return result

    def _emit_multi_assign(self, stmt: MultiAssignIR, indent: int, emitter) -> list:
        """Helper to expand MultiAssignIR using provided emitter."""
        expanded = []
        for assign_stmt in stmt.assignments:
            expanded.extend(emitter(assign_stmt, indent))
        return expanded
    
    def _gen_nexc_expr(self, expr: ExprIR, nexc_arrays: dict) -> str:
        """Generate native C expression for nexc block"""
        if isinstance(expr, ConstantIR):
            # For nexc, we use literal values instead of Object wrappers
            if expr.type_name == 'int':
                # Get the actual value from the constant table
                const_id = expr.value
                if const_id in self.ir.consts:
                    actual_value, _ = self.ir.consts[const_id]
                    return str(actual_value)
                return str(expr.value)
            elif expr.type_name == 'float':
                # Get the actual value from the constant table
                const_id = expr.value
                if const_id in self.ir.consts:
                    actual_value, _ = self.ir.consts[const_id]
                    return str(actual_value)
                return str(expr.value)
            elif expr.type_name == 'bool':
                return '1' if expr.value else '0'
            else:
                # Fallback to regular generation
                return self._gen_expr(expr)
        
        elif isinstance(expr, VariableIR):
            return expr.name
        
        elif isinstance(expr, BinOpIR):
            left = self._gen_nexc_expr(expr.left, nexc_arrays)
            right = self._gen_nexc_expr(expr.right, nexc_arrays)
            return f'({left} {expr.op} {right})'
        
        elif isinstance(expr, UnaryOpIR):
            operand = self._gen_nexc_expr(expr.operand, nexc_arrays)
            return f'({expr.op}{operand})'
        
        elif isinstance(expr, SubscriptIR):
            # Array subscript
            obj = self._gen_nexc_expr(expr.obj, nexc_arrays)
            index = self._gen_nexc_expr(expr.index, nexc_arrays)
            return f'{obj}[{index}]'
        
        elif isinstance(expr, AttributeIR):
            # Attribute access (e.g., v.x)
            # Check if obj is a native variable (in nexc_arrays) or external Nagini object
            if isinstance(expr.obj, VariableIR):
                var_name = expr.obj.name
                # If the variable is NOT in nexc_arrays, it's from outside the nexc block
                # and we need to use NgGetMember
                if var_name not in nexc_arrays:
                    # External Nagini object - use runtime function
                    attr_const_id = expr.attr
                    return f'NgGetMember(runtime, {var_name}, runtime->constants[{attr_const_id}])'
            
            # Native variable attribute access (or fallback)
            obj = self._gen_nexc_expr(expr.obj, nexc_arrays)
            # Get the attribute name from constants
            if expr.attr in self.ir.consts:
                const_value, _ = self.ir.consts[expr.attr]
                attr_name = const_value.strip('"') if isinstance(const_value, str) else str(const_value)
                return f'{obj}.{attr_name}'
            return f'{obj}.attr_{expr.attr}'
        
        elif isinstance(expr, CallIR):
            # Function call
            if expr.func_name == 'range':
                # range() is handled in for loops
                if expr.args:
                    return self._gen_nexc_expr(expr.args[0], nexc_arrays)
            elif expr.func_name == 'cast' and isinstance(expr.obj, VariableIR):
                # Handle optim.cast(type, value)
                if len(expr.args) >= 2:
                    target_type_expr = expr.args[0]
                    value_expr = expr.args[1]
                    
                    # Get the target type name
                    type_name = 'float'
                    c_type = 'double'
                    if isinstance(target_type_expr, AttributeIR):
                        type_name = self._get_type_name_from_attr(target_type_expr)
                        c_type = self._map_nexc_type_to_c(type_name)
                    
                    # Check if the value being cast is from a Nagini object (NgGetMember result)
                    # If it's an attribute access on an external object, use NgCastTo* functions
                    if isinstance(value_expr, AttributeIR) and isinstance(value_expr.obj, VariableIR):
                        var_name = value_expr.obj.name
                        if var_name not in nexc_arrays:
                            # This is accessing a Nagini object from outside nexc
                            # Use NgGetMember + NgCastTo* functions
                            member_access = f'NgGetMember(runtime, {var_name}, runtime->constants[{value_expr.attr}])'
                            
                            # Determine which cast function to use based on target type
                            if type_name in ['float', 'fp64', 'fp32', 'fp16', 'fp8', 'fp4']:
                                # Use NgCastToFloat which returns double
                                cast_result = f'NgCastToFloat(runtime, {member_access})'
                                # If target is fp32, cast the double to float
                                if type_name == 'fp32':
                                    return f'((float){cast_result})'
                                return cast_result
                            else:
                                # Use NgCastToInt for integer types
                                cast_result = f'NgCastToInt(runtime, {member_access})'
                                # Cast to specific int type if needed
                                if c_type != 'int64_t':
                                    return f'(({c_type}){cast_result})'
                                return cast_result
                    
                    # For other values, generate normal cast
                    value_code = self._gen_nexc_expr(value_expr, nexc_arrays)
                    return f'(({c_type}){value_code})'
            # Fallback
            return self._gen_expr(expr)
        
        # Fallback to regular expression generation
        return self._gen_expr(expr)
    
    def _get_type_name_from_attr(self, attr_expr: AttributeIR) -> str:
        """Extract type name from attribute expression (e.g., optim.fp32 -> 'fp32')"""
        # The attr field in AttributeIR contains the constant ID for the attribute name
        # We need to look it up in the IR's constant table
        if attr_expr.attr in self.ir.consts:
            const_value, _ = self.ir.consts[attr_expr.attr]
            # Remove quotes from string constant
            if isinstance(const_value, str):
                return const_value.strip('"')
        return 'float'  # default fallback
    
    def _map_nexc_type_to_c(self, type_name: str) -> str:
        """Map nexc type names to C type names"""
        type_map = {
            'int': 'int64_t',
            'int64': 'int64_t',
            'int32': 'int32_t',
            'int16': 'int16_t',
            'int8': 'int8_t',
            'int2': 'int8_t',
            'uint': 'uint64_t',
            'uint64': 'uint64_t',
            'uint32': 'uint32_t',
            'uint16': 'uint16_t',
            'uint8': 'uint8_t',
            'uint2': 'uint8_t',
            'float': 'double',
            'fp64': 'double',
            'fp32': 'float',
            'fp16': 'uint16_t',  # Half precision (needs conversion)
            'fp8': 'uint8_t',    # 8-bit float (needs conversion)
            'fp4': 'uint8_t',    # 4-bit float (needs conversion)
            'bool': 'uint8_t',   # Boolean as 1 byte
        }
        return type_map.get(type_name, 'double')
    
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
        
        elif isinstance(expr, AugAssignIR):
            # Augmented assignment (e.g., x += y)
            target_code = self._gen_expr(expr.target)
            value_code = self._gen_expr(expr.value)
            op = expr.op
            if op == '//':
                op = 'FloorDiv'
            elif op == '**':
                op = 'Pow'
            elif op == '/':
                op = 'TrueDiv'
            elif op == '%':
                op = 'Mod'
            elif op == '+':
                op = 'Add'
            elif op == '-':
                op = 'Sub'
            elif op == '*':
                op = 'Mul'
            
            return f'{target_code} = Ng{op}(runtime, {target_code}, {value_code})'
        
        elif isinstance(expr, JoinedStrIR):
            return f'NgJoinedStr(runtime, (void*[]) {{' + ', '.join([self._gen_expr(value) for value in expr.parts]) + f'}}, {len(expr.parts)})'
        
        elif isinstance(expr, FormattedValueIR):
            format_spec = self._gen_expr(expr.format_spec) if expr.format_spec else 'NULL'
            return f'NgFormattedValue(runtime, {self._gen_expr(expr.value)}, {format_spec})'

        elif isinstance(expr, VariableIR):
            # Variable reference
            return expr.name

        elif isinstance(expr, TupleIR):
            elements_code = [self._gen_expr(e) for e in expr.elements]
            if elements_code:
                return f'alloc_tuple(runtime, {len(elements_code)}, (Object*[]) {{{", ".join(elements_code)}}})'
            return 'alloc_tuple(runtime, 0, NULL)'
        
        elif isinstance(expr, ListIR):
            elements_code = [self._gen_expr(e) for e in expr.elements]
            if elements_code:
                return f'alloc_list_prefill(runtime, {len(elements_code)}, (Object*[]) {{{", ".join(elements_code)}}})'
            return 'alloc_list(runtime)'
        
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
                args = expr.args  # Prepend object as first arg
                args_code = ', '.join([self._gen_expr(arg) for arg in args])
                if args_code:
                    args_code = f'{obj_code}, {args_code}'
                else:
                    args_code = f'{obj_code}'
                getmember = f'NgGetMember(runtime, {obj_code}, runtime->constants[{expr.func_id}])'
                return f'NgCall(runtime, {getmember}, alloc_tuple(runtime, {len(args) + 1}, (Object*[]) {{{args_code}}}), NULL)'
            else:
                # Regular function call
                args_code = ', '.join([self._gen_expr(arg) for arg in expr.args])
                tup, kwa = parse_func_call_args_kwargs(self, expr)
                
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
                            format_parts.append('%s')
                            args_list.append(f'NgToCString(runtime, {arg_code})')
                        elif isinstance(arg, VariableIR):
                            # Assume int64_t for variables
                            format_parts.append('%s')
                            args_list.append(f'NgToCString(runtime, {arg_code})')
                        else:
                            format_parts.append('%s')
                            args_list.append(f'NgToCString(runtime, {arg_code})')
                    
                    format_str = ' '.join(format_parts)
                    if args_list:
                        return f'printf("{format_str}\\n", {", ".join(args_list)})'
                    else:
                        return 'printf("\\n")'
                elif expr.func_name == 'len':
                    # Map len() to NgLen
                    if expr.args:
                        arg_code = self._gen_expr(expr.args[0])
                        return f'NgLen(runtime, (Tuple*) alloc_tuple(runtime, 1, (Object*[]) {{{arg_code}}}), NULL)'
                    else:
                        raise ValueError('len() requires one argument')
                ident = fun_ids.get(expr.func_name)
                if not ident:
                    ident = gen_uuid(16)
                    fun_ids[expr.func_name] = ident
                return f'{expr.func_name}_{ident}(runtime, (Tuple*){tup}, (Dict*){kwa})'
        
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
            if isinstance(expr.index, SliceIR):
                start_code = self._gen_expr(expr.index.start) if expr.index.start else 'NULL'
                stop_code = self._gen_expr(expr.index.stop) if expr.index.stop else 'NULL'
                step_code = self._gen_expr(expr.index.step) if expr.index.step else 'NULL'
                return f'NgSlice(runtime, {obj_code}, {start_code}, {stop_code}, {step_code})'
            index_code = self._gen_expr(expr.index)
            return f'NgGetItem(runtime, {obj_code}, {index_code})'
        
        elif isinstance(expr, ConstructorCallIR): # TODO:
            # Constructor call (ClassName(...))
            # Generate call to create_classname() function
            func_name = f'NgAlloc{expr.class_name}'
            args_code = ', '.join([self._gen_expr(arg) for arg in expr.args])
            return f'{func_name}(runtime, (Tuple*) alloc_tuple(runtime, {len(expr.args)}, (Object* []) {{{args_code}}}), NULL)'
        
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
                        [compiler, c_file, '-o', output_path, '-lm'],
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
