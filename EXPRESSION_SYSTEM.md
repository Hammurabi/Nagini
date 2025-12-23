# Expression System Extensions

This document describes the extended expression system features added to Nagini v0.2+.

## Overview

The expression system has been extended to support:
- Function calls with typed parameters
- Constructor calls for object instantiation
- Member access on objects
- Lambda definitions (partial support)
- Primitive vs Object optimization
- Runtime type enforcement

## Function Object Representation

Functions are now first-class objects represented by the `FunctionObject` struct:

```c
typedef struct FunctionObject {
    HashTable* hash_table;  /* Inherited from Object */
    int64_t __refcount__;   /* Reference counter */
    void* func_ptr;         /* Pointer to actual function */
    int64_t param_count;    /* Number of parameters */
    char** param_names;     /* Parameter names */
    char** param_types;     /* Parameter types (NULL for untyped) */
    uint8_t* strict_flags;  /* 1 if parameter has strict typing, 0 otherwise */
    char* return_type;      /* Return type name */
    uint8_t has_varargs;    /* 1 if function accepts *args */
    uint8_t has_kwargs;     /* 1 if function accepts **kwargs */
} FunctionObject;
```

## Typed Parameters

### Strict vs Loose Typing

Nagini supports both strict and loose typing for parameters:

**Strict Typing** - Parameters with type annotations:
```python
def add(a: int, b: int) -> int:
    return a + b
```

**Loose Typing** - Parameters without type annotations:
```python
def add(a, b) -> int:
    return a + b
```

### Type Enforcement

- **Strict parameters** with primitive types (int, float, bool, str) are statically typed in C
- **Strict parameters** with object types trigger runtime type checks
- **Loose parameters** accept any type (no runtime checks)

## Varargs and Kwargs Support

Functions can accept variable arguments:

```python
# Accept variable number of positional arguments
def sum_all(*args) -> int:
    total = 0
    # ... iterate over args
    return total

# Accept variable number of keyword arguments
def configure(**kwargs) -> None:
    # ... process kwargs
    pass

# Mix regular parameters with varargs/kwargs
def complex_func(required: int, *args, **kwargs) -> int:
    # required is a strict typed parameter
    # args is a list of additional positional arguments
    # kwargs is a dict of keyword arguments
    return required
```

## Primitive vs Object Optimization

### Local Primitives

Local calculations use native C primitives for performance:

```python
def calculate() -> int:
    x = 2 + 3        # Uses primitive int64_t in C
    y = x * 2        # Still primitive
    return y         # Returns primitive
```

Generated C code:
```c
int64_t calculate() {
    int64_t x = (2 + 3);
    int64_t y = (x * 2);
    return y;
}
```

### Boxing and Unboxing

Values are converted to objects when:
- Stored as object members
- Escaping local scope
- Passed where an object is required

**Boxing Functions:**
```c
Int* box_int(int64_t value);      // int -> Int object
Double* box_double(double value);  // double -> Double object
```

**Unboxing Functions:**
```c
int64_t unbox_int(Int* obj);      // Int object -> int
double unbox_double(Double* obj);  // Double object -> double
```

## Runtime Type Checking

Type checks occur at runtime for strict object parameters:

```python
@property(malloc_strategy='gc', layout='cpp', paradigm='object')
class Point:
    x: int
    y: int

def process_point(p: Point) -> int:
    # Runtime check ensures p is actually a Point object
    return 100
```

Generated runtime check:
```c
void process_point(Point* p) {
    /* Runtime type check for strict parameter: p */
    check_param_type("p", (void*)p, "Point");
    // ... function body
}
```

### Type Metadata

Every object stores its type information:

```c
enum SymbolIDs {
    SYM_value = 0,
    SYM_data = 1,
    SYM_length = 2,
    SYM_capacity = 3,
    SYM_type_id = 998,      /* Type ID for runtime type checking */
    SYM_type_name = 999     /* Type name string for runtime type checking */
};
```

Objects created with type metadata:
```c
Int* create_int(int64_t value) {
    Int* obj = create_object();
    // Store value
    int64_t* val_ptr = (int64_t*)malloc(sizeof(int64_t));
    *val_ptr = value;
    ht_set(obj->hash_table, SYM_value, val_ptr);
    
    // Store type metadata
    int64_t* type_id = (int64_t*)malloc(sizeof(int64_t));
    *type_id = 1;  /* Type ID for Int */
    ht_set(obj->hash_table, SYM_type_id, type_id);
    ht_set(obj->hash_table, SYM_type_name, strdup("Int"));
    
    return obj;
}
```

## Constructor Calls

Constructor calls create new instances of classes:

```python
@property(malloc_strategy='gc', layout='cpp', paradigm='object')
class Point:
    x: int
    y: int

def main():
    # Constructor call (planned feature)
    p = Point(10, 20)
```

IR representation:
```python
ConstructorCallIR(
    class_name='Point',
    args=[ConstantIR(10, 'int'), ConstantIR(20, 'int')],
    kwargs=None
)
```

## Member Access

Member access on objects uses hash table lookups:

```python
@property(malloc_strategy='gc', layout='cpp', paradigm='object')
class Point:
    x: int
    y: int

def get_x(p: Point) -> int:
    return p.x  # Member access via hash table
```

IR representation:
```python
AttributeIR(
    obj=VariableIR('p'),
    attr='x'
)
```

## Lambda Expressions

Lambda expressions are partially supported:

```python
# Simple lambda
square = lambda x: x * x

# Lambda with type annotations
typed_lambda = lambda x: int, y: int: x + y
```

IR representation:
```python
LambdaIR(
    params=[('x', None)],
    body=BinOpIR(VariableIR('x'), '*', VariableIR('x')),
    capture_vars=None
)
```

## Runtime Error Messages

Clear runtime errors are generated for type violations:

### Argument Count Mismatch
```
Runtime Error: Function 'add' expects 2 arguments but got 3
```

### Type Mismatch
```
Runtime Error: Parameter 'p' has type 'Int' but expected 'Point'
```

### NULL Parameter
```
Runtime Error: Parameter 'p' is NULL but expected type 'Point'
```

## Examples

### Example 1: Strict Typing
```python
def add_strict(a: int, b: int) -> int:
    return a + b

def main():
    result = add_strict(5, 3)  # OK
    print("Result:", result)
```

### Example 2: Mixed Parameters
```python
def mixed_params(name: str, age, score: int) -> int:
    # name is strict (must be str)
    # age is loose (any type)
    # score is strict (must be int)
    return score

def main():
    result = mixed_params("Alice", 25, 100)
    print("Score:", result)
```

### Example 3: Object Parameters (Planned)
```python
@property(malloc_strategy='gc', layout='cpp', paradigm='object')
class Point:
    x: int
    y: int

def distance_squared(p: Point) -> int:
    # Runtime type check ensures p is a Point
    return p.x * p.x + p.y * p.y

def main():
    point = Point(3, 4)
    dist = distance_squared(point)
    print("Distance squared:", dist)
```

## Implementation Status

✅ **Completed:**
- FunctionObject structure definition
- Typed parameter parsing
- Strict vs loose typing tracking
- *args and **kwargs support in signatures
- Runtime type checking for object parameters
- Boxing/unboxing functions for primitives
- Type metadata storage in objects
- Constructor call IR representation
- Lambda expression IR representation
- Member access IR representation

🚧 **In Progress:**
- Full constructor call implementation
- Complete lambda closure capture
- Member access code generation for object paradigm
- Iterator support for *args

📋 **Planned:**
- Dynamic dispatch based on type metadata
- Type inference for untyped parameters
- Generic type constraints
- Interface/protocol checking

## Performance Characteristics

- **Primitive operations**: Zero overhead (native C types)
- **Object operations**: Hash table lookup overhead
- **Type checks**: O(1) lookup in hash table
- **Boxing/unboxing**: Single malloc + hash table insert/lookup

## Design Rationale

### Why Strict vs Loose Typing?

- **Flexibility**: Allows gradual typing - start loose, add types as needed
- **Performance**: Strict primitive types use native C operations
- **Safety**: Runtime checks catch type errors early

### Why Runtime Checking?

- **Dynamic nature**: Objects created at runtime need runtime checks
- **Clear errors**: Better error messages than segfaults
- **Extensibility**: Supports future dynamic features

### Why Boxing/Unboxing?

- **Performance**: Keep primitives as primitives in hot paths
- **Compatibility**: Bridge between primitive and object worlds
- **Explicit**: Makes conversion costs visible in IR

## Future Enhancements

1. **Compile-time Type Inference**: Infer types from usage patterns
2. **JIT Compilation**: Optimize hot paths with runtime profiling
3. **Type Specialization**: Generate specialized versions for common types
4. **Generic Functions**: Template-like functions with type parameters
5. **Algebraic Data Types**: Sum types and pattern matching
