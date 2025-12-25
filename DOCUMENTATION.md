# Nagini Programming Language - Complete Documentation

**Version**: 0.2.0  
**Last Updated**: December 2024

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Language Reference](#3-language-reference)
4. [Type System](#4-type-system)
5. [Memory Management](#5-memory-management)
6. [Object Model](#6-object-model)
7. [Compiler Architecture](#7-compiler-architecture)
8. [Runtime System](#8-runtime-system)
9. [C Interoperability](#9-c-interoperability)
10. [Advanced Topics](#10-advanced-topics)
11. [API Reference](#11-api-reference)
12. [Examples and Tutorials](#12-examples-and-tutorials)
13. [Performance Guide](#13-performance-guide)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Introduction

### 1.1 What is Nagini?

Nagini is a compiled programming language that bridges the gap between high-level productivity and low-level performance. It combines:

- **Python's elegant syntax** for developer happiness
- **C's raw performance** for production efficiency
- **Flexible memory management** for diverse use cases

### 1.2 Design Philosophy

Nagini is built on four core principles:

1. **Pythonic Ergonomics**: Code should be easy to write and read
2. **Native Performance**: No interpreter overhead, pure machine code
3. **Flexible Control**: Choose the right tool for each task
4. **Zero-Cost FFI**: Direct interoperability with C/C++ libraries

### 1.3 Use Cases

Nagini excels in domains requiring both productivity and performance:

- **Game Development**: Fast iteration with native performance
- **Systems Programming**: High-level abstractions, low-level control
- **ECS (Entity Component System)**: Zero-overhead components
- **Blockchain**: Performance-critical with complex logic
- **AI/ML**: Fast prototyping with production speed
- **Real-Time Systems**: Predictable memory and timing

---

## 2. Getting Started

### 2.1 Installation

#### Prerequisites

- **Python 3.8 or higher** (for the compiler)
- **C Compiler** (gcc, clang, or cc)
- **Operating System**: Linux, macOS, or Windows (with gcc/clang)

#### Installation Steps

```bash
# Clone the repository
git clone https://github.com/Hammurabi/Nagini.git
cd Nagini

# Verify Python version
python3 --version  # Should be 3.8+

# Verify C compiler
gcc --version  # or clang --version

# (Optional) Install as package
pip install -e .

# Test installation
python3 -m nagini.cli --help
```

### 2.2 Hello World

Create your first Nagini program:

**File**: `hello.nag`
```python
# This is a comment
print("Hello, World!")
print("Welcome to Nagini!")
```

Compile and run:
```bash
python3 -m nagini.cli compile hello.nag
./hello
```

Expected output:
```
Hello, World!
Welcome to Nagini!
```

### 2.3 Understanding the Compilation Process

Nagini transforms your code through four phases:

```
Source Code (.nag)
    ↓ Phase 1: Parse
AST (Abstract Syntax Tree)
    ↓ Phase 2: IR Generation
Intermediate Representation
    ↓ Phase 3: C Code Generation
C Source Code (.c)
    ↓ Phase 4: Native Compilation
Executable Binary
```

To see this process in action:

```bash
# Verbose compilation (shows all phases)
python3 -m nagini.cli compile hello.nag -v

# Generate C code only (skip compilation)
python3 -m nagini.cli compile hello.nag --emit-c
cat hello.c  # View generated C code
```

---

## 3. Language Reference

### 3.1 Basic Syntax

Nagini uses Python-compatible syntax:

```python
# Variables (type inferred)
x = 42
name = "Nagini"
pi = 3.14159

# Type-annotated variables
count: int = 100
ratio: float = 0.5
```

### 3.2 Functions

#### Simple Functions

```python
def greet(name: str):
    print("Hello,", name)

def add(a: int, b: int) -> int:
    return a + b
```

#### Advanced Function Features

```python
# Optional parameters (loose typing)
def flexible(x, y: int) -> int:
    # 'x' has no type annotation, 'y' is strictly typed
    return y * 2

# Variable arguments
def sum_all(*numbers):
    total = 0
    for n in numbers:
        total = total + n
    return total

# Keyword arguments
def configure(**options):
    # Process keyword arguments
    pass

# Mixed parameters
def complex_func(required: int, *args, **kwargs):
    pass
```

### 3.3 Classes

#### Basic Class Definition

```python
@property(malloc_strategy='gc', layout='cpp', paradigm='object')
class Point:
    x: float
    y: float
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def distance(self) -> float:
        return (self.x**2 + self.y**2) ** 0.5
```

#### Class Decorator Options

**`malloc_strategy`**: How instances are allocated
- `'gc'` (default): Automatic garbage collection with DynamicPool
- `'pool'`: Fixed-size StaticPool allocation
- `'heap'`: Manual malloc/free

**`layout`**: Memory layout strategy
- `'cpp'` (default): C++ compatible struct layout
- `'std430'`: GPU shader buffer layout (tight packing)
- `'custom'`: User-defined offsets

**`paradigm`**: Object model
- `'object'` (default): Hash table + metadata + reflection
- `'data'`: Plain C struct (zero overhead)

#### Paradigm Comparison

```python
# Object paradigm: Full-featured OOP
@property(paradigm='object')
class GameObject:
    name: str
    health: int
    
    # Benefits:
    # - Dynamic member access
    # - Reflection capabilities
    # - Reference counting
    # - Can add members at runtime
    
    # Cost:
    # - 16+ bytes overhead per object
    # - Hash table lookup for members

# Data paradigm: Lightweight structs
@property(paradigm='data')
class Component:
    x: float
    y: float
    
    # Benefits:
    # - Zero overhead
    # - Direct memory access
    # - Perfect for FFI
    # - Cache-friendly
    
    # Cost:
    # - No dynamic features
    # - No reflection
```

### 3.4 Control Flow

#### Conditionals

```python
def check_value(x: int) -> str:
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"
```

#### Loops

```python
# While loop
def countdown(n: int):
    while n > 0:
        print(n)
        n = n - 1

# For loop (iterator support coming)
def sum_range(n: int) -> int:
    total = 0
    i = 0
    while i < n:
        total = total + i
        i = i + 1
    return total
```

### 3.5 Expressions

#### Arithmetic Operators

```python
a + b    # Addition
a - b    # Subtraction
a * b    # Multiplication
a / b    # Division
a // b   # Floor division
a % b    # Modulo
a ** b   # Exponentiation
```

#### Comparison Operators

```python
a == b   # Equal
a != b   # Not equal
a < b    # Less than
a <= b   # Less than or equal
a > b    # Greater than
a >= b   # Greater than or equal
```

#### Logical Operators

```python
a and b  # Logical AND
a or b   # Logical OR
not a    # Logical NOT
```

#### Operator Precedence

From highest to lowest:
1. `**` (exponentiation)
2. `-x`, `+x`, `not x` (unary operators)
3. `*`, `/`, `//`, `%` (multiplication, division)
4. `+`, `-` (addition, subtraction)
5. `==`, `!=`, `<`, `<=`, `>`, `>=` (comparisons)
6. `not` (logical NOT)
7. `and` (logical AND)
8. `or` (logical OR)

---

## 4. Type System

### 4.1 Primitive Types

Nagini provides four primitive types:

| Nagini Type | C Type | Size | Range/Notes |
|-------------|--------|------|-------------|
| `int` | `int64_t` | 8 bytes | -2^63 to 2^63-1 |
| `float` | `double` | 8 bytes | IEEE 754 double precision |
| `bool` | `uint8_t` | 1 byte | 0 (false) or 1 (true) |
| `str` | `char*` | 8 bytes | Pointer to null-terminated string |

### 4.2 Built-in Object Types

Wrapper classes that box primitives into objects:

#### Int

```python
# Conceptual definition
class Int(Object):
    value: int  # Stored in hash table
```

#### Double

```python
class Double(Object):
    value: float  # Stored in hash table
```

#### String

```python
class String(Object):
    data: str      # String content
    length: int    # Number of characters
```

#### List

```python
class List(Object):
    data: list     # Array of Object references
    length: int    # Number of elements
    capacity: int  # Allocated capacity
```

### 4.3 Type Annotations

#### Function Parameter Typing

```python
# Strict typing (type checked for object types)
def process(obj: MyClass) -> int:
    return obj.value

# Loose typing (no type checking)
def flexible(x, y):
    return x + y

# Mixed
def mixed(name: str, age) -> int:
    # 'name' is strictly typed, 'age' is loose
    return age
```

#### Variable Typing

```python
# Type inference (recommended)
x = 42          # Inferred as int
name = "Alice"  # Inferred as str

# Explicit annotation
count: int = 0
ratio: float = 0.5

# Annotated without initialization
result: int  # Default initialized to 0
```

### 4.4 Type Checking

Nagini uses a hybrid typing approach:

**Compile-Time Checking**:
- Primitive type mismatches caught by C compiler
- Syntax errors caught by parser

**Runtime Checking**:
- Object parameter types verified for strict parameters
- Only checks object types, not primitives (for performance)

```python
@property(paradigm='object')
class Point:
    x: float
    y: float

def process_point(p: Point) -> float:
    # Runtime check: Is 'p' actually a Point object?
    return p.x + p.y

# This will error at runtime if wrong type passed
```

---

## 5. Memory Management

### 5.1 Memory Strategies

Nagini provides three allocation strategies:

#### GC Strategy (Default)

```python
@property(malloc_strategy='gc')
class MyClass:
    # Automatically garbage collected
    # Uses DynamicPool with reference counting
    pass
```

**Characteristics**:
- Automatic memory management
- DynamicPool auto-resizes as needed
- Reference counting tracks object lifetime
- No manual cleanup required
- Best for: General-purpose code

#### Pool Strategy

```python
@property(malloc_strategy='pool')
class Entity:
    # Allocated from StaticPool
    # Fixed capacity set at pool creation
    pass
```

**Characteristics**:
- Pre-allocated fixed-size pool
- Fast allocation/deallocation (O(1))
- Errors if capacity exceeded
- Predictable memory usage
- Best for: Real-time systems, games

#### Heap Strategy

```python
@property(malloc_strategy='heap')
class Resource:
    # Manual malloc/free
    # Programmer controls lifetime
    pass
```

**Characteristics**:
- Direct system malloc/free
- Complete control over lifetime
- Must manually free resources
- Best for: Long-lived objects, resources

### 5.2 Reference Counting

Nagini uses automatic reference counting for memory management:

```python
# Conceptual example (happens automatically)
obj = create_object()  # refcount = 1
retain(obj)            # refcount = 2
release(obj)           # refcount = 1
release(obj)           # refcount = 0, object deallocated
```

**Automatic Reference Counting**:
- Assignment: Increments refcount
- Scope exit: Decrements refcount
- When refcount reaches 0: Object is freed

**Manual Control**:
```python
# These are low-level functions
# Usually you don't need to use them
obj = retain(obj)   # Keep object alive
release(obj)        # Release reference
```

### 5.3 Memory Pools

#### DynamicPool

```python
# Created automatically for 'gc' strategy
# Configuration in C:
# - initial_capacity: 1024 (default)
# - growth_factor: 2.0 (doubles when full)
```

**Growth Behavior**:
```
Initial: 1024 objects
After 1024: 2048 objects
After 2048: 4096 objects
...
```

**Performance**:
- Allocation: O(1) amortized
- Deallocation: O(1)
- Growth: O(n) when resizing

#### StaticPool

```python
# Used with 'pool' strategy
# Fixed capacity set at creation
```

**Behavior**:
```python
pool = StaticPool(capacity=1000)
# Can allocate up to 1000 objects
# 1001st allocation raises error
```

**Performance**:
- Allocation: O(1) always
- Deallocation: O(1)
- No resizing overhead

### 5.4 Memory Layout Strategies

#### CPP Layout (Default)

```python
@property(layout='cpp')
class Example:
    a: int    # 8 bytes
    b: bool   # 1 byte + 7 bytes padding
    c: int    # 8 bytes
    # Total: 24 bytes (with padding)
```

Standard C++ struct alignment for compatibility.

#### STD430 Layout

```python
@property(layout='std430')
class Uniform:
    # Tight packing for GPU buffers
    # Minimal padding
    pass
```

Used for OpenGL/Vulkan shader buffers.

#### Custom Layout

```python
@property(layout='custom')
class Special:
    # User-defined field offsets
    # For special requirements
    pass
```

---

## 6. Object Model

### 6.1 Base Object Class

All Nagini objects inherit from `Object`:

```c
// C representation
typedef struct Object {
    HashTable* hash_table;   // Dynamic member storage
    int64_t __refcount__;    // Reference counter
} Object;
```

### 6.2 Symbol Table

Member names are converted to integer IDs for fast lookup:

```python
# Symbol table (conceptual)
"x"      → 0
"y"      → 1
"value"  → 2
"name"   → 3
```

**Member Access**:
```
obj.x
  ↓
get_symbol_id("x") → 0
  ↓
hash_table_lookup(obj.hash_table, 0) → value
```

**Performance**: O(1) hash lookup instead of O(n) string comparison

### 6.3 Hash Table Implementation

Nagini uses Robin Hood hashing for the hash table:

**Features**:
- Open addressing with linear probing
- PSL (Probe Sequence Length) tracking
- Auto-resizes at 85% load factor
- SplitMix64 hash function

**Performance**:
- Average case: O(1)
- Worst case: O(n) (very rare with good hash function)
- Memory overhead: ~40% empty slots

### 6.4 Object Paradigm vs Data Paradigm

#### Object Paradigm Example

```python
@property(paradigm='object')
class GameEntity:
    name: str
    health: int
    
    # Memory layout:
    # +0:  HashTable* (8 bytes)
    # +8:  __refcount__ (8 bytes)
    # +16: Hash table data...
    
    # 'name' and 'health' stored in hash table
    # Access: hash_lookup(get_symbol_id("name"))
```

**Use When**:
- Need dynamic member addition
- Want reflection/introspection
- Using inheritance
- Need reference counting

#### Data Paradigm Example

```python
@property(paradigm='data')
class Transform:
    x: float
    y: float
    rotation: float
    
    # Memory layout:
    # +0:  x (8 bytes)
    # +8:  y (8 bytes)
    # +16: rotation (8 bytes)
    # Total: 24 bytes (no overhead!)
    
    # Direct field access
    # Access: *(obj_ptr + 0) for x
```

**Use When**:
- Performance critical (tight loops)
- Fixed structure (no dynamic features)
- FFI/C interoperability
- ECS components

---

## 7. Compiler Architecture

### 7.1 Overview

The Nagini compiler consists of four independent phases:

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Parser  │ ──→ │    IR    │ ──→ │ Backend  │ ──→ │    C     │
│ (AST)    │     │(Analyze) │     │(Generate)│     │ Compiler │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
   Phase 1          Phase 2          Phase 3         Phase 4
```

### 7.2 Phase 1: Parser

**File**: `nagini/compiler/parser.py`

**Responsibility**: Transform source code into structured metadata

**Process**:
1. Read Nagini source code
2. Use Python's `ast.parse()` to create AST
3. Walk AST nodes to extract:
   - Class definitions and decorators
   - Function definitions and signatures
   - Type annotations
   - Top-level statements
4. Build `ClassInfo` and `FunctionInfo` objects
5. Calculate field offsets and sizes

**Key Classes**:
- `NaginiParser`: Main parser
- `ClassInfo`: Class metadata
- `FunctionInfo`: Function metadata
- `FieldInfo`: Field metadata

**Example**:
```python
# Input
@property(paradigm='object')
class Vec3:
    x: float
    y: float
    z: float

# Output
ClassInfo(
    name='Vec3',
    fields=[
        FieldInfo(name='x', type='float', offset=8, size=8),
        FieldInfo(name='y', type='float', offset=16, size=8),
        FieldInfo(name='z', type='float', offset=24, size=8),
    ],
    malloc_strategy='gc',
    paradigm='object',
    ...
)
```

### 7.3 Phase 2: IR Generation

**File**: `nagini/compiler/ir.py`

**Responsibility**: Transform AST into Intermediate Representation

**IR Node Types**:

**Expressions**:
- `ConstantIR`: Literal values (42, 3.14, "hello")
- `VariableIR`: Variable references
- `BinOpIR`: Binary operations (+, -, *, /)
- `UnaryOpIR`: Unary operations (-, not, +)
- `CallIR`: Function/method calls
- `AttributeIR`: Member access (obj.member)
- `SubscriptIR`: Array access (obj[index])
- `ConstructorCallIR`: Object creation
- `LambdaIR`: Lambda expressions
- `BoxIR`/`UnboxIR`: Primitive ↔ Object conversion

**Statements**:
- `AssignIR`: Variable assignment
- `ReturnIR`: Return statement
- `IfIR`: Conditional (if/elif/else)
- `WhileIR`: While loop
- `ForIR`: For loop
- `ExprStmtIR`: Expression as statement

**Functions**:
- `FunctionIR`: Complete function representation

**Process**:
1. Convert AST statements to IR statements
2. Convert AST expressions to IR expressions
3. Register string/int/float constants
4. Track variable declarations
5. Build control flow structures
6. Create main function if needed

### 7.4 Phase 3: C Code Generation

**File**: `nagini/compiler/backend.py`

**Responsibility**: Generate C code from IR

**Generation Order**:
1. C headers (`#include` statements)
2. Forward declarations
3. Hash table implementation
4. Memory pool implementation
5. Base Object class
6. Symbol table
7. Built-in types (Int, Double, String, List)
8. User-defined class structs
9. Class methods
10. Functions
11. Main function

**Type Mapping**:
```
Nagini → C
int    → int64_t
float  → double
bool   → uint8_t
str    → char*
void   → void
```

**Class Generation**:

For Object paradigm:
```c
// Nagini
@property(paradigm='object')
class Point:
    x: float
    y: float

// Generated C
Object* def_class_Point(Runtime* runtime) {
    Object* cls = alloc_instance("Point");
    // Initialize methods...
    return cls;
}
```

For Data paradigm:
```c
// Nagini
@property(paradigm='data')
class Point:
    x: float
    y: float

// Generated C
typedef struct {
    double x;
    double y;
} Point;
```

### 7.5 Phase 4: Native Compilation

**Responsibility**: Compile C code to executable

**Process**:
1. Write generated C code to temporary file
2. Try compilers in order: gcc, clang, cc
3. Invoke compiler: `gcc temp.c -o output`
4. Check compilation result
5. Clean up temporary file

**Compiler Options**:
- Standard compilation: No special flags
- Future: Optimization flags (-O2, -O3)
- Future: Debug symbols (-g)

---

## 8. Runtime System

### 8.1 Runtime Components

The Nagini runtime is implemented in C:

**Files**:
- `nagini/compiler/c/hmap.h`: Hash table
- `nagini/compiler/c/pool.h`: Memory pools
- `nagini/compiler/c/builtin.h`: Base Object and built-ins
- `nagini/compiler/c/list.h`: List implementation

### 8.2 Hash Table (Robin Hood Hashing)

**Features**:
- Open addressing with linear probing
- PSL (Probe Sequence Length) variance reduction
- Automatic resizing at 85% load factor
- SplitMix64 hash function

**Operations**:
```c
hmap_t* map = hmap_create();           // Create
hmap_put(map, key, value);             // Insert/Update
void* val = hmap_get(map, key);        // Lookup
bool found = hmap_remove(map, key);    // Delete
hmap_destroy(map);                     // Cleanup
```

**Performance**:
- Average case: O(1)
- Worst case: O(n) (extremely rare)
- Load factor: 85% before resize

### 8.3 Memory Pools

#### DynamicPool Implementation

```c
typedef struct {
    void** blocks;          // Array of free blocks
    size_t capacity;        // Total capacity
    size_t used;            // Currently allocated
    size_t block_size;      // Size of each block
    double growth_factor;   // Growth multiplier
} DynamicPool;

DynamicPool* pool_create(size_t initial_capacity, double growth_factor);
void* pool_allocate(DynamicPool* pool, size_t size);
void pool_deallocate(DynamicPool* pool, void* ptr);
void pool_destroy(DynamicPool* pool);
```

#### StaticPool Implementation

```c
typedef struct {
    void** blocks;          // Array of free blocks
    size_t capacity;        // Fixed capacity
    size_t used;            // Currently allocated
    size_t block_size;      // Size of each block
} StaticPool;

StaticPool* static_pool_create(size_t capacity, size_t block_size);
void* static_pool_allocate(StaticPool* pool);  // May return NULL
void static_pool_deallocate(StaticPool* pool, void* ptr);
void static_pool_destroy(StaticPool* pool);
```

### 8.4 Reference Counting

```c
// Increment reference count
Object* retain(Object* obj) {
    if (obj) {
        obj->__refcount__++;
    }
    return obj;
}

// Decrement reference count, free if zero
void release(Object* obj) {
    if (obj) {
        obj->__refcount__--;
        if (obj->__refcount__ == 0) {
            // Cleanup and free
            hmap_destroy(obj->hash_table);
            free(obj);
        }
    }
}
```

### 8.5 Built-in Type Implementation

#### Object

```c
typedef struct {
    HashTable* hash_table;
    int64_t __refcount__;
} Object;

Object* alloc_object() {
    Object* obj = malloc(sizeof(Object));
    obj->hash_table = hmap_create();
    obj->__refcount__ = 1;
    return obj;
}
```

#### Int

```c
// Int is Object with 'value' in hash table
Object* box_int(int64_t value) {
    Object* obj = alloc_object();
    int64_t value_sym = get_symbol_id("value");
    hmap_put(obj->hash_table, value_sym, (void*)value);
    return obj;
}

int64_t unbox_int(Object* obj) {
    int64_t value_sym = get_symbol_id("value");
    return (int64_t)hmap_get(obj->hash_table, value_sym);
}
```

---

## 9. C Interoperability

### 9.1 Memory Layout Compatibility

Nagini's data paradigm generates structs compatible with C:

```python
# Nagini
@property(paradigm='data', layout='cpp')
class Point3D:
    x: float
    y: float
    z: float
```

```c
// Equivalent C
typedef struct {
    double x;
    double y;
    double z;
} Point3D;
```

### 9.2 Calling C Functions

(Planned feature - not yet implemented)

```python
# Declare C function
@extern("c")
def sqrt(x: float) -> float:
    pass

# Use it
result = sqrt(16.0)
```

### 9.3 Exposing Nagini to C

(Planned feature - not yet implemented)

```python
# Export to C
@export("c")
def compute(x: int, y: int) -> int:
    return x * y + 42
```

---

## 10. Advanced Topics

### 10.1 Performance Optimization

#### Use Data Paradigm for Performance-Critical Code

```python
# Slow: Object paradigm (hash table lookup)
@property(paradigm='object')
class ParticleObj:
    x: float
    y: float
    velocity_x: float
    velocity_y: float

# Fast: Data paradigm (direct access)
@property(paradigm='data')
class ParticleData:
    x: float
    y: float
    velocity_x: float
    velocity_y: float

# In tight loops, data paradigm is 2-5x faster
```

#### Use Static Pools for Predictable Performance

```python
# Variable allocation times with gc
@property(malloc_strategy='gc')
class Entity:
    pass

# Consistent allocation times with pool
@property(malloc_strategy='pool')
class Entity:
    pass

# Perfect for real-time systems
```

#### Minimize Boxing/Unboxing

```python
# Inefficient: Boxing/unboxing in loop
def sum_inefficient(n: int) -> int:
    result = Int(0)  # Box to object
    i = Int(0)       # Box to object
    while unbox_int(i) < n:
        result = box_int(unbox_int(result) + unbox_int(i))
        i = box_int(unbox_int(i) + 1)
    return unbox_int(result)

# Efficient: Use primitives
def sum_efficient(n: int) -> int:
    result = 0
    i = 0
    while i < n:
        result = result + i
        i = i + 1
    return result
```

### 10.2 Memory Management Patterns

#### RAII Pattern

```python
@property(malloc_strategy='heap')
class Resource:
    handle: int
    
    def __init__(self, filename: str):
        self.handle = open_file(filename)
    
    def __del__(self):
        close_file(self.handle)

# Resource automatically cleaned up
def use_resource():
    res = Resource("data.txt")
    # Use resource...
# __del__ called here, handle closed
```

#### Object Pooling

```python
@property(malloc_strategy='pool')
class Bullet:
    x: float
    y: float
    active: bool

# Create pool of 1000 bullets
# Reuse instead of allocate/deallocate
```

### 10.3 Debug Strategies

#### Use --emit-c to Inspect Generated Code

```bash
python3 -m nagini.cli compile myfile.nag --emit-c
cat myfile.c  # Examine generated C code
```

#### Use Verbose Mode

```bash
python3 -m nagini.cli compile myfile.nag -v
# Shows:
# - Classes found
# - Functions found
# - IR generation
# - Generated C code
```

#### Add Debug Prints

```python
def debug_func(x: int) -> int:
    print("debug: x =", x)
    result = x * 2
    print("debug: result =", result)
    return result
```

---

## 11. API Reference

### 11.1 Compiler API

#### NaginiParser

```python
from nagini.compiler.parser import NaginiParser

parser = NaginiParser()
classes, functions, top_level = parser.parse(source_code)
```

**Methods**:
- `parse(source_code: str)`: Parse source code, returns (classes, functions, statements)

#### NaginiIR

```python
from nagini.compiler.ir import NaginiIR

ir = NaginiIR(classes, functions, top_level)
ir.generate()
```

**Methods**:
- `generate()`: Generate IR from parsed structures
- `register_string_constant(value: str)`: Register string constant
- `register_int_constant(value: int)`: Register int constant

#### LLVMBackend

```python
from nagini.compiler.backend import LLVMBackend

backend = LLVMBackend(ir)
c_code = backend.generate()
success = backend.compile_to_executable("output", c_code)
```

**Methods**:
- `generate()`: Generate C code from IR
- `compile_to_executable(output_path: str, c_code: str)`: Compile to executable

### 11.2 Runtime API

#### Reference Counting

```python
# Usually called automatically by compiler-generated code
obj = retain(obj)    # Increment refcount
release(obj)         # Decrement refcount
```

#### Memory Pools

```python
from nagini.runtime.pools import DynamicPool, StaticPool

# Create pools
dynamic = DynamicPool(initial_capacity=1024, growth_factor=2.0)
static = StaticPool(capacity=1000)

# Allocate
ptr = dynamic.allocate(size=32)
ptr2 = static.allocate(size=32)

# Deallocate
dynamic.deallocate(ptr)
static.deallocate(ptr2)
```

---

## 12. Examples and Tutorials

### 12.1 Tutorial: Building a Simple Calculator

```python
# calculator.nag

def add(a: int, b: int) -> int:
    return a + b

def subtract(a: int, b: int) -> int:
    return a - b

def multiply(a: int, b: int) -> int:
    return a * b

def divide(a: int, b: int) -> int:
    if b == 0:
        print("Error: Division by zero")
        return 0
    return a // b

def main():
    print("Calculator")
    print("-----------")
    
    x = 10
    y = 3
    
    print("x =", x)
    print("y =", y)
    print()
    
    print("x + y =", add(x, y))
    print("x - y =", subtract(x, y))
    print("x * y =", multiply(x, y))
    print("x / y =", divide(x, y))
```

Compile and run:
```bash
python3 -m nagini.cli compile calculator.nag
./calculator
```

### 12.2 Tutorial: Point Class with Methods

```python
# point.nag

@property(paradigm='object')
class Point:
    x: float
    y: float
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def distance_from_origin(self) -> float:
        return (self.x**2 + self.y**2) ** 0.5
    
    def add(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

def main():
    p1 = Point(3.0, 4.0)
    p2 = Point(1.0, 2.0)
    
    print("p1 distance:", p1.distance_from_origin())
    print("p2 distance:", p2.distance_from_origin())
    
    p3 = p1.add(p2)
    print("p3 distance:", p3.distance_from_origin())
```

### 12.3 Tutorial: Recursive Fibonacci

```python
# fibonacci.nag

def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def fibonacci_iterative(n: int) -> int:
    if n <= 1:
        return n
    
    a = 0
    b = 1
    i = 2
    
    while i <= n:
        temp = a + b
        a = b
        b = temp
        i = i + 1
    
    return b

def main():
    print("Fibonacci numbers:")
    
    i = 0
    while i <= 10:
        print("fibonacci(", i, ") =", fibonacci(i))
        i = i + 1
```

### 12.4 Complete Example: Game Entity System

```python
# entities.nag

# Data paradigm for performance
@property(paradigm='data', malloc_strategy='pool')
class Transform:
    x: float
    y: float
    rotation: float

# Object paradigm for flexibility
@property(paradigm='object', malloc_strategy='gc')
class Entity:
    name: str
    health: int
    transform: Transform
    
    def __init__(self, name: str, x: float, y: float):
        self.name = name
        self.health = 100
        self.transform = Transform()
        self.transform.x = x
        self.transform.y = y
        self.transform.rotation = 0.0
    
    def take_damage(self, amount: int):
        self.health = self.health - amount
        if self.health < 0:
            self.health = 0
    
    def is_alive(self) -> bool:
        return self.health > 0

def main():
    player = Entity("Player", 0.0, 0.0)
    enemy = Entity("Enemy", 10.0, 10.0)
    
    print("Player health:", player.health)
    print("Enemy health:", enemy.health)
    
    enemy.take_damage(30)
    print("Enemy health after damage:", enemy.health)
    print("Enemy alive:", enemy.is_alive())
```

---

## 13. Performance Guide

### 13.1 Benchmarking

To benchmark your code:

```python
# benchmark.nag

def benchmark(n: int):
    i = 0
    while i < n:
        # Your code here
        i = i + 1

def main():
    # Time this with external tools
    benchmark(1000000)
```

Benchmark with time:
```bash
python3 -m nagini.cli compile benchmark.nag
time ./benchmark
```

### 13.2 Performance Tips

1. **Use Data Paradigm for Performance-Critical Classes**
   - 2-5x faster than object paradigm
   - Zero memory overhead

2. **Use StaticPool for Fixed-Size Collections**
   - Predictable allocation time
   - No resizing overhead

3. **Keep Primitives as Primitives**
   - Don't box unnecessarily
   - Let compiler optimize

4. **Minimize Function Calls in Hot Paths**
   - Inline critical code
   - Use direct operations

5. **Profile Before Optimizing**
   - Use `--emit-c` to see generated code
   - Identify bottlenecks first

### 13.3 Memory Usage

Estimate memory usage:

```python
# Object paradigm
@property(paradigm='object')
class ObjExample:
    x: int  # 8 bytes
    y: int  # 8 bytes
    # Overhead:
    # - hash_table pointer: 8 bytes
    # - refcount: 8 bytes
    # - hash table data: ~40 bytes
    # Total: ~72 bytes per instance

# Data paradigm
@property(paradigm='data')
class DataExample:
    x: int  # 8 bytes
    y: int  # 8 bytes
    # Total: 16 bytes per instance
```

---

## 14. Troubleshooting

### 14.1 Common Errors

#### Error: "File not found"

```bash
Error: File 'myfile.nag' not found.
```

**Solution**: Check file path and current directory.

#### Error: "No C compiler found"

```bash
No C compiler found. Please install gcc or clang.
```

**Solution**: Install gcc or clang:
```bash
# Ubuntu/Debian
sudo apt-get install gcc

# macOS
xcode-select --install

# Windows
# Install MinGW or Cygwin
```

#### Error: "Compilation failed"

**Solution**: Use `--emit-c` to see generated C code:
```bash
python3 -m nagini.cli compile myfile.nag --emit-c
cat myfile.c  # Check for issues
```

#### Error: "StaticPool capacity exceeded"

```python
# Your code
@property(malloc_strategy='pool')
class Entity:
    pass

# Too many instances created
```

**Solution**: 
- Use `malloc_strategy='gc'` instead
- Or increase pool capacity (requires C code modification)

### 14.2 Debugging Tips

1. **Use Verbose Mode**
   ```bash
   python3 -m nagini.cli compile myfile.nag -v
   ```

2. **Examine Generated C Code**
   ```bash
   python3 -m nagini.cli compile myfile.nag --emit-c
   ```

3. **Add Debug Prints**
   ```python
   def debug_func(x: int) -> int:
       print("DEBUG: x =", x)
       return x * 2
   ```

4. **Start Simple**
   - Test with minimal examples first
   - Add complexity incrementally

5. **Check Type Annotations**
   - Ensure types match expected
   - Use verbose mode to see type info

### 14.3 Getting Help

- **GitHub Issues**: https://github.com/Hammurabi/Nagini/issues
- **Documentation**: This file
- **Examples**: `nagini/examples/` directory
- **Source Code**: Well-commented for understanding

---

## Appendix A: Grammar Reference

(Simplified EBNF-style grammar)

```
program = statement*

statement = 
    | class_def
    | function_def
    | assign_stmt
    | if_stmt
    | while_stmt
    | for_stmt
    | return_stmt
    | expr_stmt

class_def = 
    decorator* "class" NAME ["(" NAME ")"] ":" 
    INDENT (field_def | method_def)* DEDENT

function_def = 
    "def" NAME "(" params ")" ["->" type] ":" 
    INDENT statement* DEDENT

expr = 
    | constant
    | NAME
    | expr binop expr
    | unaryop expr
    | expr "(" args ")"
    | expr "." NAME
    | expr "[" expr "]"
```

---

## Appendix B: Built-in Functions

Currently supported:
- `print(*args)`: Print values to stdout

Planned:
- `len(obj)`: Get length
- `range(n)`: Create range iterator
- `str(obj)`: Convert to string
- `int(obj)`: Convert to int
- `float(obj)`: Convert to float

---

## Appendix C: Compiler Flags

```bash
# Current flags
-o, --output NAME     # Specify output filename
--emit-c              # Generate C code only
-v, --verbose         # Verbose output

# Planned flags
-O0, -O1, -O2, -O3    # Optimization levels
-g                    # Debug symbols
--target ARCH         # Target architecture
--emit-llvm           # Generate LLVM IR
```

---

## Appendix D: Roadmap

### Version 0.3 (Q1 2025)
- [ ] Complete for loop support
- [ ] List operations
- [ ] String manipulation
- [ ] Module system basics

### Version 0.4 (Q2 2025)
- [ ] LLVM IR backend
- [ ] Optimization passes
- [ ] Standard library v1

### Version 0.5 (Q3 2025)
- [ ] Generic types
- [ ] Type inference improvements
- [ ] Package manager

### Version 1.0 (Q4 2025)
- [ ] Production-ready compiler
- [ ] Complete standard library
- [ ] IDE support
- [ ] Comprehensive documentation

---

**End of Documentation**

For more information, see:
- [README.md](README.md) - Quick start guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Compiler architecture
- [IMPLEMENTATION_DETAILS.md](IMPLEMENTATION_DETAILS.md) - Implementation notes
