"""
Nagini C Backend
Generates C code and compiles to native machine code using gcc/clang.
Future versions will support direct LLVM IR generation.
"""

import sys
from typing import Dict, Optional
from .ir import (
    NaginiIR, FunctionIR, StmtIR, ExprIR,
    ConstantIR, VariableIR, BinOpIR, UnaryOpIR, CallIR, AttributeIR,
    AssignIR, ReturnIR, IfIR, WhileIR, ForIR, ExprStmtIR
)
from .parser import ClassInfo, FieldInfo


class LLVMBackend:
    """
    C backend for Nagini compiler (LLVM backend planned for future).
    Generates C code and compiles to native machine code using gcc/clang.
    """
    
    def __init__(self, ir: NaginiIR):
        self.ir = ir
        self.output_code = []
        self.declared_vars = set()  # Track declared variables
        
    def generate(self) -> str:
        """
        Generate target code (C for initial implementation).
        Returns the generated C code as a string.
        """
        self.output_code = []
        
        # Generate headers
        self._gen_headers()
        
        # Generate hash table implementation
        self._gen_hash_table()
        
        # Generate pool allocators
        self._gen_pools()
        
        # Generate base Object class with hash table
        self._gen_base_object()
        
        # Generate built-in types
        self._gen_builtins()
        
        # Generate class structs
        for class_name, class_info in self.ir.classes.items():
            self._gen_class_struct(class_info)
        
        # Generate functions
        for func in self.ir.functions:
            self._gen_function(func)
        
        return '\n'.join(self.output_code)
    
    def _gen_headers(self):
        """Generate necessary C headers"""
        self.output_code.append('#include <stdio.h>')
        self.output_code.append('#include <stdlib.h>')
        self.output_code.append('#include <stdint.h>')
        self.output_code.append('#include <string.h>')
        self.output_code.append('#include <math.h>')
        self.output_code.append('')
        self.output_code.append('/* Forward declarations */')
        self.output_code.append('typedef struct HashTable HashTable;')
        self.output_code.append('typedef struct Object Object;')
        self.output_code.append('typedef struct DynamicPool DynamicPool;')
        self.output_code.append('typedef struct StaticPool StaticPool;')
        self.output_code.append('')
    
    def _gen_pools(self):
        """Generate pool allocator structures"""
        # DynamicPool structure
        self.output_code.append('/* DynamicPool - auto-resizing memory pool */')
        self.output_code.append('typedef struct DynamicPool {')
        self.output_code.append('    void** blocks;')
        self.output_code.append('    int64_t capacity;')
        self.output_code.append('    int64_t used;')
        self.output_code.append('    double growth_factor;')
        self.output_code.append('} DynamicPool;')
        self.output_code.append('')
        
        # StaticPool structure
        self.output_code.append('/* StaticPool - fixed-size memory pool */')
        self.output_code.append('typedef struct StaticPool {')
        self.output_code.append('    void** blocks;')
        self.output_code.append('    int64_t capacity;')
        self.output_code.append('    int64_t used;')
        self.output_code.append('} StaticPool;')
        self.output_code.append('')
        
        # Global default pool
        self.output_code.append('/* Global default dynamic pool for primitives */')
        self.output_code.append('DynamicPool* _default_pool = NULL;')
        self.output_code.append('')
        
        # Pool functions
        self.output_code.append('/* Initialize a dynamic pool */')
        self.output_code.append('DynamicPool* create_dynamic_pool(int64_t initial_capacity, double growth_factor) {')
        self.output_code.append('    DynamicPool* pool = (DynamicPool*)malloc(sizeof(DynamicPool));')
        self.output_code.append('    pool->capacity = initial_capacity;')
        self.output_code.append('    pool->used = 0;')
        self.output_code.append('    pool->growth_factor = growth_factor;')
        self.output_code.append('    pool->blocks = (void**)malloc(sizeof(void*) * initial_capacity);')
        self.output_code.append('    return pool;')
        self.output_code.append('}')
        self.output_code.append('')
        
        self.output_code.append('/* Initialize a static pool */')
        self.output_code.append('StaticPool* create_static_pool(int64_t capacity) {')
        self.output_code.append('    StaticPool* pool = (StaticPool*)malloc(sizeof(StaticPool));')
        self.output_code.append('    pool->capacity = capacity;')
        self.output_code.append('    pool->used = 0;')
        self.output_code.append('    pool->blocks = (void**)malloc(sizeof(void*) * capacity);')
        self.output_code.append('    return pool;')
        self.output_code.append('}')
        self.output_code.append('')
        
        self.output_code.append('/* Allocate from dynamic pool (auto-grows) */')
        self.output_code.append('void* alloc_dynamic(DynamicPool* pool, size_t size) {')
        self.output_code.append('    if (pool->used >= pool->capacity) {')
        self.output_code.append('        /* Grow the pool */')
        self.output_code.append('        int64_t new_capacity = (int64_t)(pool->capacity * pool->growth_factor);')
        self.output_code.append('        pool->blocks = (void**)realloc(pool->blocks, sizeof(void*) * new_capacity);')
        self.output_code.append('        pool->capacity = new_capacity;')
        self.output_code.append('    }')
        self.output_code.append('    void* ptr = malloc(size);')
        self.output_code.append('    pool->blocks[pool->used++] = ptr;')
        self.output_code.append('    return ptr;')
        self.output_code.append('}')
        self.output_code.append('')
        
        self.output_code.append('/* Allocate from static pool (throws error if full) */')
        self.output_code.append('void* alloc_static(StaticPool* pool, size_t size) {')
        self.output_code.append('    if (pool->used >= pool->capacity) {')
        self.output_code.append('        fprintf(stderr, "StaticPool capacity exceeded: %lld/%lld\\n", pool->used, pool->capacity);')
        self.output_code.append('        exit(1);')
        self.output_code.append('    }')
        self.output_code.append('    void* ptr = malloc(size);')
        self.output_code.append('    pool->blocks[pool->used++] = ptr;')
        self.output_code.append('    return ptr;')
        self.output_code.append('}')
        self.output_code.append('')
        
        self.output_code.append('/* Get default pool (lazy initialization) */')
        self.output_code.append('DynamicPool* get_default_pool() {')
        self.output_code.append('    if (_default_pool == NULL) {')
        self.output_code.append('        _default_pool = create_dynamic_pool(1024, 2.0);')
        self.output_code.append('    }')
        self.output_code.append('    return _default_pool;')
        self.output_code.append('}')
        self.output_code.append('')
    
    def _gen_hash_table(self):
        """Generate hash table implementation for Object members"""
        self.output_code.append('/* Hash table for object members (symbol table based) */')
        self.output_code.append('typedef struct HashTableEntry {')
        self.output_code.append('    int64_t key;  /* Symbol ID */')
        self.output_code.append('    void* value;')
        self.output_code.append('    struct HashTableEntry* next;')
        self.output_code.append('} HashTableEntry;')
        self.output_code.append('')
        
        self.output_code.append('typedef struct HashTable {')
        self.output_code.append('    HashTableEntry** buckets;')
        self.output_code.append('    int64_t size;')
        self.output_code.append('} HashTable;')
        self.output_code.append('')
        
        self.output_code.append('/* Create a hash table */')
        self.output_code.append('HashTable* create_hash_table(int64_t size) {')
        self.output_code.append('    HashTable* ht = (HashTable*)malloc(sizeof(HashTable));')
        self.output_code.append('    ht->size = size;')
        self.output_code.append('    ht->buckets = (HashTableEntry**)calloc(size, sizeof(HashTableEntry*));')
        self.output_code.append('    return ht;')
        self.output_code.append('}')
        self.output_code.append('')
        
        self.output_code.append('/* Hash function */')
        self.output_code.append('int64_t hash(int64_t key, int64_t size) {')
        self.output_code.append('    return key % size;')
        self.output_code.append('}')
        self.output_code.append('')
        
        self.output_code.append('/* Set value in hash table */')
        self.output_code.append('void ht_set(HashTable* ht, int64_t key, void* value) {')
        self.output_code.append('    int64_t index = hash(key, ht->size);')
        self.output_code.append('    HashTableEntry* entry = (HashTableEntry*)malloc(sizeof(HashTableEntry));')
        self.output_code.append('    entry->key = key;')
        self.output_code.append('    entry->value = value;')
        self.output_code.append('    entry->next = ht->buckets[index];')
        self.output_code.append('    ht->buckets[index] = entry;')
        self.output_code.append('}')
        self.output_code.append('')
        
        self.output_code.append('/* Get value from hash table */')
        self.output_code.append('void* ht_get(HashTable* ht, int64_t key) {')
        self.output_code.append('    int64_t index = hash(key, ht->size);')
        self.output_code.append('    HashTableEntry* entry = ht->buckets[index];')
        self.output_code.append('    while (entry != NULL) {')
        self.output_code.append('        if (entry->key == key) return entry->value;')
        self.output_code.append('        entry = entry->next;')
        self.output_code.append('    }')
        self.output_code.append('    return NULL;')
        self.output_code.append('}')
        self.output_code.append('')
    
    def _gen_base_object(self):
        """Generate base Object class with hash table for members"""
        self.output_code.append('/* Base Object class - all Nagini objects inherit from this */')
        self.output_code.append('/* Members are stored in hash_table, accessed via symbol IDs */')
        self.output_code.append('typedef struct Object {')
        self.output_code.append('    HashTable* hash_table;  /* Contains all members, functions, metadata */')
        self.output_code.append('    int64_t __refcount__;   /* Reference counter (outside programmer control) */')
        self.output_code.append('} Object;')
        self.output_code.append('')
        
        self.output_code.append('/* Create a new Object */')
        self.output_code.append('Object* create_object() {')
        self.output_code.append('    Object* obj = (Object*)alloc_dynamic(get_default_pool(), sizeof(Object));')
        self.output_code.append('    obj->hash_table = create_hash_table(16);')
        self.output_code.append('    obj->__refcount__ = 1;')
        self.output_code.append('    return obj;')
        self.output_code.append('}')
        self.output_code.append('')
        
        # Generate retain function
        self.output_code.append('/* Increment reference count and return object */')
        self.output_code.append('void* retain(void* obj) {')
        self.output_code.append('    if (obj != NULL) {')
        self.output_code.append('        Object* o = (Object*)obj;')
        self.output_code.append('        o->__refcount__++;')
        self.output_code.append('    }')
        self.output_code.append('    return obj;')
        self.output_code.append('}')
        self.output_code.append('')
        
        # Generate release function
        self.output_code.append('/* Decrement reference count and free if zero */')
        self.output_code.append('void release(void* obj) {')
        self.output_code.append('    if (obj != NULL) {')
        self.output_code.append('        Object* o = (Object*)obj;')
        self.output_code.append('        o->__refcount__--;')
        self.output_code.append('        if (o->__refcount__ == 0) {')
        self.output_code.append('            /* TODO: Free hash table entries */')
        self.output_code.append('            free(obj);')
        self.output_code.append('        }')
        self.output_code.append('    }')
        self.output_code.append('}')
        self.output_code.append('')
    
    def _gen_builtins(self):
        """Generate built-in types (Int, Double, String, List) using hash table"""
        # Global symbol table for member names
        self.output_code.append('/* Global symbol table for member names */')
        self.output_code.append('enum SymbolIDs {')
        self.output_code.append('    SYM_value = 0,')
        self.output_code.append('    SYM_data = 1,')
        self.output_code.append('    SYM_length = 2,')
        self.output_code.append('    SYM_capacity = 3')
        self.output_code.append('};')
        self.output_code.append('')
        
        # Int class (64-bit integer) - stored in hash table
        self.output_code.append('/* Built-in Int class (64-bit integer) */')
        self.output_code.append('/* Members stored in hash_table */')
        self.output_code.append('typedef Object Int;')
        self.output_code.append('')
        
        self.output_code.append('Int* create_int(int64_t value) {')
        self.output_code.append('    Int* obj = create_object();')
        self.output_code.append('    int64_t* val_ptr = (int64_t*)malloc(sizeof(int64_t));')
        self.output_code.append('    *val_ptr = value;')
        self.output_code.append('    ht_set(obj->hash_table, SYM_value, val_ptr);')
        self.output_code.append('    return obj;')
        self.output_code.append('}')
        self.output_code.append('')
        
        # Double class (64-bit float) - stored in hash table
        self.output_code.append('/* Built-in Double class (64-bit float) */')
        self.output_code.append('/* Members stored in hash_table */')
        self.output_code.append('typedef Object Double;')
        self.output_code.append('')
        
        self.output_code.append('Double* create_double(double value) {')
        self.output_code.append('    Double* obj = create_object();')
        self.output_code.append('    double* val_ptr = (double*)malloc(sizeof(double));')
        self.output_code.append('    *val_ptr = value;')
        self.output_code.append('    ht_set(obj->hash_table, SYM_value, val_ptr);')
        self.output_code.append('    return obj;')
        self.output_code.append('}')
        self.output_code.append('')
        
        # String class - stored in hash table
        self.output_code.append('/* Built-in String class */')
        self.output_code.append('/* Members stored in hash_table */')
        self.output_code.append('typedef Object String;')
        self.output_code.append('')
        
        self.output_code.append('String* create_string(const char* data) {')
        self.output_code.append('    String* obj = create_object();')
        self.output_code.append('    char* str = strdup(data);')
        self.output_code.append('    int64_t* len = (int64_t*)malloc(sizeof(int64_t));')
        self.output_code.append('    *len = strlen(data);')
        self.output_code.append('    ht_set(obj->hash_table, SYM_data, str);')
        self.output_code.append('    ht_set(obj->hash_table, SYM_length, len);')
        self.output_code.append('    return obj;')
        self.output_code.append('}')
        self.output_code.append('')
        
        # List class - list of objects (any object type)
        self.output_code.append('/* Built-in List class */')
        self.output_code.append('/* List of objects - any object type can be inside */')
        self.output_code.append('/* Members stored in hash_table */')
        self.output_code.append('typedef Object List;')
        self.output_code.append('')
        
        self.output_code.append('List* create_list() {')
        self.output_code.append('    List* obj = create_object();')
        self.output_code.append('    Object** data = (Object**)malloc(sizeof(Object*) * 16);  /* Initial capacity */')
        self.output_code.append('    int64_t* len = (int64_t*)malloc(sizeof(int64_t));')
        self.output_code.append('    int64_t* cap = (int64_t*)malloc(sizeof(int64_t));')
        self.output_code.append('    *len = 0;')
        self.output_code.append('    *cap = 16;')
        self.output_code.append('    ht_set(obj->hash_table, SYM_data, data);')
        self.output_code.append('    ht_set(obj->hash_table, SYM_length, len);')
        self.output_code.append('    ht_set(obj->hash_table, SYM_capacity, cap);')
        self.output_code.append('    return obj;')
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
            self.output_code.append(f'/* Members stored in hash_table, accessed via symbol IDs */')
            self.output_code.append(f'typedef Object {class_info.name};')
            self.output_code.append('')
            
            # Generate constructor function
            self.output_code.append(f'{class_info.name}* create_{class_info.name.lower()}() {{')
            self.output_code.append(f'    {class_info.name}* obj = create_object();')
            
            # Initialize fields in hash table with default values
            for field in class_info.fields:
                self.output_code.append(f'    /* Initialize field: {field.name} */')
                if field.type_name == 'int':
                    self.output_code.append(f'    int64_t* {field.name}_ptr = (int64_t*)malloc(sizeof(int64_t));')
                    self.output_code.append(f'    *{field.name}_ptr = 0;')
                    self.output_code.append(f'    /* ht_set(obj->hash_table, SYM_{field.name}, {field.name}_ptr); */')
                elif field.type_name == 'float':
                    self.output_code.append(f'    double* {field.name}_ptr = (double*)malloc(sizeof(double));')
                    self.output_code.append(f'    *{field.name}_ptr = 0.0;')
                    self.output_code.append(f'    /* ht_set(obj->hash_table, SYM_{field.name}, {field.name}_ptr); */')
                elif field.type_name == 'bool':
                    self.output_code.append(f'    uint8_t* {field.name}_ptr = (uint8_t*)malloc(sizeof(uint8_t));')
                    self.output_code.append(f'    *{field.name}_ptr = 0;')
                    self.output_code.append(f'    /* ht_set(obj->hash_table, SYM_{field.name}, {field.name}_ptr); */')
                elif field.type_name == 'str':
                    self.output_code.append(f'    char* {field.name}_ptr = NULL;')
                    self.output_code.append(f'    /* ht_set(obj->hash_table, SYM_{field.name}, {field.name}_ptr); */')
            
            self.output_code.append(f'    return obj;')
            self.output_code.append(f'}}')
            self.output_code.append('')
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
        
    def _gen_function(self, func: FunctionIR):
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
        
        return result
    
    def _gen_expr(self, expr: ExprIR) -> str:
        """Generate C code for an expression IR node"""
        if isinstance(expr, ConstantIR):
            # Constant value
            if expr.type_name == 'str':
                # String literal
                return f'"{expr.value}"' if not expr.value.startswith('"') else expr.value
            elif expr.type_name == 'bool':
                return '1' if expr.value else '0'
            else:
                return str(expr.value)
        
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
            
            if expr.op == '**':
                # Power operation needs pow() function
                return f'pow({left_code}, {right_code})'
            else:
                return f'({left_code} {op} {right_code})'
        
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
            return f'{obj_code}.{expr.attr}'
        
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
