# Nagini Programming Language

**Version:** 0.2.0  
**Status:** Early Development  

Nagini is a compiled, Python-inspired, fully object-oriented/data-oriented programming language with hybrid memory management, designed for game development, blockchain, ECS (Entity Component System), AI, and high-performance systems.

## Features

- **Pythonic Syntax** – Easy to read and write, minimal boilerplate
- **Compiled to Native Code** – Maximum runtime speed via C/LLVM backend
- **Everything is an Object** – Base Object class with reference counting built-in
- **Flexible Memory Management** – Supports pool, GC (default), and manual heap allocation
- **Object & Data Paradigms** – Choose between full objects or lightweight data containers
- **Built-in Types** – Int, Double, String, and List classes with automatic reference counting
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
    __refcount__: int  # 8-byte reference counter
```

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

### Built-in Types

Nagini provides built-in wrapper classes that inherit from Object:

- **Int** – 64-bit integer with reference counting
- **Double** – 64-bit floating point with reference counting  
- **String** – String class with automatic memory management
- **List** – Dynamic list with automatic memory management

### Class Declaration

```python
@property(malloc_strategy='gc', layout='cpp', paradigm='object')
class Name(Object):
    x: int
    y: float
```

**Properties:**

- `malloc_strategy`: `pool` | `gc` (default) | `heap`
  - `pool`: Pre-allocated memory pool (fastest, automatic deallocation)
  - `gc`: Garbage collected (automatic reference counting) - **DEFAULT**
  - `heap`: Manual allocation/deallocation

- `layout`: `cpp` | `std430` | `custom`
  - Controls memory layout for C/C++ interoperability

- `paradigm`: `object` | `data`
  - `object`: Full object with reference counting inherited from Object
  - `data`: Lightweight data container, no overhead

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
│   ├── __init__.py       # Runtime support
│   └── builtins.py       # Base Object and built-in types
└── examples/
    ├── hello.nag              # Simple hello world
    ├── hello_class.nag        # Example with class
    ├── memory_example.nag     # Memory strategies demo
    └── object_inheritance.nag # Object inheritance demo
```

## Current Status (v0.2)

✅ **Implemented:**
- AST parsing with Python's built-in parser
- Base `Object` class with reference counting (8-byte `__refcount__`)
- Built-in types: `Int`, `Double`, `String`, `List` (all inherit from Object)
- `retain()` and `release()` functions for reference counting
- Class inheritance support (all classes inherit from Object by default)
- Class definition parsing with `@property` decorators
- Field extraction with type annotations
- Default GC strategy (reference counting)
- IR generation
- C code generation for classes/structs with inheritance
- Object header generation for `paradigm='object'`
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
