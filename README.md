# Nagini Programming Language

**Version:** 0.2.0  
**Status:** Early Development  

Nagini is a compiled, Python-inspired, fully object-oriented/data-oriented programming language with hybrid memory management, designed for game development, blockchain, ECS (Entity Component System), AI, and high-performance systems.

## Features

- **Pythonic Syntax** – Easy to read and write, minimal boilerplate
- **Compiled to Native Code** – Maximum runtime speed via C/LLVM backend
- **Everything is an Object** – Hash table based Object with dynamic member access
- **Flexible Memory Management** – DynamicPool (auto-resize) and StaticPool (fixed) allocators
- **GC by Default** – Reference counting with DynamicPool as default strategy
- **Object & Data Paradigms** – Choose between hash table objects or direct struct data
- **Built-in Types** – Int, Double, String, and List with hash table storage
- **Lists of Objects** – Lists can contain any object type
- **Symbol Table** – Member names converted to integers for fast access
- **FFI Ready** – Memory layout compatible with C/C++ for seamless interoperability

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Hammurabi/Nagini.git
cd Nagini

# The compiler is written in Python 3.8+
# No additional dependencies required for basic usage
```

### Hello World

Create a file `hello.nag`:

```python
# Nagini Hello World
# The compiler will generate a simple hello world program
```

Compile and run:

```bash
python3 -m nagini.cli compile hello.nag
./hello
```

Output:
```
Hello, World!
```

### Example with Class

Create a file `example.nag`:

```python
@property(malloc_strategy='pool', layout='cpp', paradigm='object')
class Vec3:
    x: float
    y: float
    z: float
```

Compile:

```bash
python3 -m nagini.cli compile example.nag -v
./example
```

## Language Syntax

### Base Object Class

All Nagini classes inherit from the base `Object` class by default:

```python
class Object:
    hash_table: dict  # Hash table for all members, functions, metadata
    __refcount__: int  # 8-byte reference counter (outside programmer control)
```

**C Structure:**
```c
typedef struct Object {
    HashTable* hash_table;  /* Contains all members, functions, metadata */
    int64_t __refcount__;   /* Reference counter (outside programmer control) */
} Object;
```

**Member Access:**
- Member names convert to integers via a global symbol table
- Members accessed via `object[member_symbol]` → hash table lookup
- Reference count lives outside programmer control

**Reference Counting Functions:**

```python
def retain(obj: Object) -> Object:
    """Increment reference count"""
    obj.__refcount__ += 1
    return obj

def release(obj: Object):
    """Decrement reference count and free if zero"""
    obj.__refcount__ -= 1
    if obj.__refcount__ == 0:
        del obj
```

### Memory Pool Allocators

Nagini provides two pool allocator types:

- **DynamicPool** – Auto-resizing memory pool
  - Automatically grows when capacity is reached
  - Used as default for primitives and GC strategy
  - Growth factor configurable (default: 2.0)

- **StaticPool** – Fixed-size memory pool
  - Throws error when trying to allocate beyond capacity
  - Used with explicit pool strategy
  - Faster, predictable memory usage

### Built-in Types

Nagini provides built-in wrapper classes that inherit from Object:

- **Int** – 64-bit integer stored in hash table
- **Double** – 64-bit floating point stored in hash table
- **String** – String class with automatic memory management
- **List** – Dynamic list of objects (any object type can be inside)

All built-in types use hash tables for member storage.

### Class Declaration

```python
@property(malloc_strategy='gc', layout='cpp', paradigm='object')
class Name(Object):
    x: int
    y: float
```

**Properties:**

- `malloc_strategy`: `pool` | `gc` (default) | `heap`
  - `pool`: StaticPool (fixed size, throws error when full)
  - `gc`: DynamicPool (auto-resize, reference counting) - **DEFAULT**
  - `heap`: Manual allocation/deallocation

- `layout`: `cpp` | `std430` | `custom`
  - Controls memory layout for C/C++ interoperability

- `paradigm`: `object` | `data`
  - `object`: Hash table based, reference counting, dynamic member access
  - `data`: Direct struct, no hash table, no overhead

### Object Allocation (Future)

```python
# Default allocation (uses class malloc_strategy)
obj = Name(1, 2.0)

# Explicit manual allocation
obj = alloc(Name, 1, 2.0)

# Explicit GC allocation
obj = galloc(Name, 1, 2.0)
```

## Compiler Usage

```bash
# Compile a Nagini source file
python3 -m nagini.cli compile <file.nag>

# Specify output name
python3 -m nagini.cli compile <file.nag> -o myprogram

# Generate C code only (don't compile to executable)
python3 -m nagini.cli compile <file.nag> --emit-c

# Verbose output
python3 -m nagini.cli compile <file.nag> -v
```

## Architecture

The Nagini compiler consists of four main phases:

1. **Parser** – Uses Python's built-in AST parser to parse Nagini syntax
2. **IR Generation** – Creates intermediate representation with type and allocation info
3. **Backend** – Generates C code (or LLVM IR in future)
4. **Compilation** – Compiles to native executable using gcc/clang

### Directory Structure

```
nagini/
├── __init__.py           # Package initialization
├── cli.py                # Command-line interface
├── compiler/
│   ├── __init__.py       # Compiler package
│   ├── parser.py         # AST parser
│   ├── ir.py             # Intermediate representation
│   └── backend.py        # Code generation backend
├── runtime/
│   ├── __init__.py        # Runtime support
│   ├── builtins.py        # Base Object and built-in types
│   └── pools.py           # Pool allocators (DynamicPool, StaticPool)
└── examples/
    ├── hello.nag                 # Simple hello world
    ├── hello_class.nag           # Example with class
    ├── memory_example.nag        # Memory strategies demo
    ├── object_inheritance.nag    # Object inheritance demo
    └── pools_and_hashtable.nag  # Pools and hash table demo
```

## Current Status (v0.2)

✅ **Implemented:**
- AST parsing with Python's built-in parser
- Base `Object` class with hash table for members
  - `HashTable* hash_table` for dynamic member storage
  - `int64_t __refcount__` outside programmer control
- Global symbol table for member name → integer conversion
- Member access via `object[member_symbol]` → hash table lookup
- DynamicPool allocator (auto-resizing, default for primitives)
- StaticPool allocator (fixed size, throws error when full)
- Built-in types using hash table: `Int`, `Double`, `String`, `List`
- Lists are lists of objects (any object type)
- `retain()` and `release()` functions for reference counting
- Class inheritance support (all classes inherit from Object by default)
- Class definition parsing with `@property` decorators
- Field extraction with type annotations
- Default GC strategy with DynamicPool
- IR generation
- C code generation with hash tables and pools
- Object paradigm uses hash table
- Data paradigm uses direct struct (no hash table)
- Basic main function generation
- CLI compiler interface
- Compilation to native executable

🚧 **In Progress:**
- Object allocation functions (`alloc`, `galloc`)
- Memory pool management
- Garbage collection runtime implementation
- Function definitions and calls
- Expression evaluation
- Control flow (if, while, for)

📋 **Planned:**
- Full language features (functions, expressions, statements)
- Runtime memory management (pool, gc, heap)
- FFI/C++ interoperability layer
- Multi-level inheritance and polymorphism
- Standard library
- LLVM IR backend
- Optimization passes
- REPL/interactive mode

## Development

### Requirements

- Python 3.8 or higher
- GCC or Clang (for compilation to executable)

### Running Tests

```bash
# Test the hello world example
python3 -m nagini.cli compile nagini/examples/hello.nag -v
./hello

# Test with class example
python3 -m nagini.cli compile nagini/examples/hello_class.nag -v
./hello_class
```

## Design Philosophy

Nagini aims to provide:

1. **Pythonic ergonomics** – Familiar syntax for rapid development
2. **Native performance** – Compiled to machine code, no interpreter overhead
3. **Flexible memory control** – Choose the right allocation strategy for each use case
4. **Zero-cost FFI** – Direct C/C++ interoperability without wrappers
5. **Modern features** – Reflection, meta-programming, and type safety

## License

See LICENSE file for details.

## Contributing

This is an early-stage project. Contributions, suggestions, and feedback are welcome!

## Roadmap

### Phase 1: Core Compiler ✅ (Current)
- [x] AST parsing
- [x] Class definition support
- [x] Basic IR generation
- [x] C code generation
- [x] CLI interface

### Phase 2: Language Features
- [ ] Function definitions
- [ ] Expression evaluation
- [ ] Control flow statements
- [ ] Object instantiation
- [ ] Method calls

### Phase 3: Memory Management
- [ ] Pool allocator runtime
- [ ] Reference counting GC
- [ ] Manual heap allocation
- [ ] Smart pointer support

### Phase 4: Advanced Features
- [ ] Inheritance and polymorphism
- [ ] FFI/C++ interop layer
- [ ] Standard library
- [ ] Optimization passes

### Phase 5: Tooling
- [ ] LLVM IR backend
- [ ] REPL/interactive mode
- [ ] Package manager
- [ ] IDE support

---

**Nagini** – Python's simplicity, C's performance, maximum flexibility.
