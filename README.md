# Nagini Programming Language

<div align="center">

**Python's Simplicity • C's Performance • Maximum Flexibility**

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/Hammurabi/Nagini)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

*A compiled, Python-inspired programming language with hybrid memory management for high-performance systems*

[Features](#-features) • [Quick Start](#-quick-start) • [Examples](#-examples) • [Documentation](#-documentation) • [Architecture](#-architecture)

</div>

---

## 🎯 What is Nagini?

Nagini is a **compiled programming language** that combines the elegant, readable syntax of Python with the raw performance of native machine code. It's designed for developers who want:

- **Pythonic ergonomics** for rapid development
- **Native speed** through ahead-of-time compilation
- **Flexible memory control** with multiple allocation strategies
- **Zero-overhead FFI** for seamless C/C++ interoperability

Perfect for game development, blockchain, ECS (Entity Component System), AI, and any high-performance system where speed matters.

## ✨ Features

### Core Language Features

🐍 **Python-Inspired Syntax**
- Familiar, clean syntax with minimal boilerplate
- Type annotations for safety and performance
- Classes, methods, and functions

⚡ **Compiled to Native Code**
- Generates optimized C code
- Compiles to native executables via gcc/clang
- No interpreter overhead at runtime

🎨 **Flexible Object Model**
- **Object Paradigm**: Dynamic hash table-based objects with reflection
- **Data Paradigm**: Plain structs with zero overhead
- Choose the right model for each class

### Memory Management

🔄 **Hybrid Memory Strategies**
- **GC (Default)**: Automatic reference counting with DynamicPool
- **Pool**: Fixed-size StaticPool for predictable performance
- **Heap**: Manual allocation for fine-grained control

📊 **Built-in Pool Allocators**
- **DynamicPool**: Auto-resizing, perfect for general use
- **StaticPool**: Fixed capacity, ideal for real-time systems

### Advanced Features

🔧 **Everything is an Object**
- Base `Object` class with hash table for dynamic members
- Built-in types: `Int`, `Double`, `String`, `List`
- Reference counting for automatic memory management

🎯 **Symbol Table**
- Member names converted to integers for blazing-fast lookups
- Efficient hash table access pattern

🌉 **FFI Ready**
- Memory layouts compatible with C/C++
- Direct struct interoperability
- Multiple layout strategies (cpp, std430, custom)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Hammurabi/Nagini.git
cd Nagini

# Nagini compiler requires Python 3.8+
python3 --version  # Should be 3.8 or higher

# For compilation, you need a C compiler
gcc --version      # or clang --version
```

### Your First Program

Create a file `hello.nag`:

```python
# Simple Hello World
# Top-level statements become the main function
print("Hello from Nagini!")
```

Compile and run:

```bash
# Compile to executable
python3 -m nagini.cli compile hello.nag

# Run the executable
./hello
```

Output:
```
Hello from Nagini!
```

### Class Example

Create `vector.nag`:

```python
# Define a 3D vector class with object paradigm
@property(malloc_strategy='gc', layout='cpp', paradigm='object')
class Vec3:
    x: float
    y: float
    z: float
    
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z
    
    def magnitude(self) -> float:
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5

# Use the class
if __name__ == "__main__":
    v = Vec3(3.0, 4.0, 0.0)
    print("Vector magnitude:", v.magnitude())
```

Compile with verbose output to see all phases:

```bash
python3 -m nagini.cli compile vector.nag -v
./vector
```

## 📚 Examples

### Example 1: Functions with Type Annotations

```python
# functions.nag - Type-safe functions
def add(a: int, b: int) -> int:
    return a + b

def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

if __name__ == "__main__":
    print("5 + 3 =", add(5, 3))
    print("Factorial of 5 =", factorial(5))
```

### Example 2: Memory Pool Allocation

```python
# Preallocated pool for game objects
@property(malloc_strategy='pool', layout='cpp', paradigm='data')
class Entity:
    id: int
    health: int
    x: float
    y: float

# The 'pool' strategy uses a StaticPool with fixed capacity
# Perfect for games where you know max entity count
```

### Example 3: Object vs Data Paradigm

```python
# Object paradigm: Dynamic, flexible, has metadata
@property(paradigm='object')
class GameObject:
    name: str
    health: int
    # Can dynamically add members at runtime
    # Has reflection capabilities
    # Reference counted

# Data paradigm: Lightweight, no overhead
@property(paradigm='data')
class Component:
    x: float
    y: float
    # Just a plain C struct
    # No hash table, no ref counting
    # Perfect for ECS components
```

### Example 4: Control Flow

```python
def fibonacci(n: int) -> int:
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

if __name__ == "__main__":
    print("Fibonacci(10) =", fibonacci(10))
```

## 🏗️ Architecture

### Compilation Pipeline

Nagini uses a **4-phase compilation pipeline**:

```
┌─────────────┐      ┌──────────┐      ┌──────────┐      ┌────────────┐
│ .nag Source │  →   │   AST    │  →   │    IR    │  →   │  C Code    │  →  Executable
│   (Python   │      │ (Parse)  │      │ (Analyze)│      │ (Backend)  │
│   Syntax)   │      │          │      │          │      │            │
└─────────────┘      └──────────┘      └──────────┘      └────────────┘
     Phase 0             Phase 1          Phase 2            Phase 3        Phase 4
```

#### Phase 1: AST Parsing (`parser.py`)
- Uses Python's built-in `ast.parse()` to create Abstract Syntax Tree
- Extracts class definitions, methods, fields, and decorators
- Parses type annotations and function signatures
- **Output**: `ClassInfo` and `FunctionInfo` metadata objects

#### Phase 2: IR Generation (`ir.py`)
- Transforms AST into Nagini's Intermediate Representation
- Converts expressions and statements to IR nodes
- Handles type inference and constant folding
- **Output**: `NaginiIR` object with structured program representation

#### Phase 3: C Code Generation (`backend.py`)
- Generates optimized C code from IR
- Creates struct definitions for classes
- Maps Nagini types to C types
- Generates runtime support code
- **Output**: Complete C program as string

#### Phase 4: Native Compilation
- Invokes system C compiler (gcc/clang)
- Produces platform-specific executable
- **Output**: Native binary ready to run

### Memory Architecture

#### Base Object Structure

All Nagini objects inherit from the `Object` class:

```c
typedef struct Object {
    HashTable* hash_table;   // Dynamic member storage
    int64_t __refcount__;    // Reference counter (runtime-managed)
} Object;
```

**Member Access Pattern**:
```
Member Name → Symbol Table → Integer ID → Hash Lookup → Value
    "x"     →   global map   →    0      →  O(1) lookup → 42
```

#### Memory Strategies

| Strategy | Type | Allocation | Deallocation | Use Case |
|----------|------|------------|--------------|----------|
| `gc` (default) | DynamicPool | Auto-resizing | Ref counting | General purpose |
| `pool` | StaticPool | Fixed capacity | Manual/scope | Real-time systems |
| `heap` | malloc/free | System heap | Manual | Long-lived objects |

#### Paradigm Trade-offs

| Feature | Object Paradigm | Data Paradigm |
|---------|----------------|---------------|
| Memory overhead | 16+ bytes | 0 bytes |
| Member access | Hash lookup O(1) | Direct access O(1) |
| Reflection | ✅ Yes | ❌ No |
| Dynamic members | ✅ Yes | ❌ No |
| FFI compatible | ⚠️ With care | ✅ Perfect |
| Best for | OOP, dynamic | ECS, performance |

## 📖 Documentation

### Language Reference

#### Class Declaration

```python
@property(malloc_strategy='gc', layout='cpp', paradigm='object')
class MyClass(ParentClass):
    field1: int
    field2: float
    
    def method(self, param: int) -> int:
        return param * 2
```

**Decorator Options**:
- `malloc_strategy`: `'gc'` (default) | `'pool'` | `'heap'`
- `layout`: `'cpp'` (default) | `'std430'` | `'custom'`
- `paradigm`: `'object'` (default) | `'data'`

#### Type System

**Primitive Types**:
- `int`: 64-bit signed integer (maps to `int64_t`)
- `float`: 64-bit floating point (maps to `double`)
- `bool`: Boolean (maps to `uint8_t`)
- `str`: String (maps to `char*`)

**Built-in Classes**:
- `Int`: Object wrapper for int
- `Double`: Object wrapper for float
- `String`: Managed string class
- `List`: Dynamic array of objects

#### Function Definitions

```python
# Type-annotated parameters (strict checking for objects)
def func(a: int, b: float) -> int:
    return int(a + b)

# Mixed strict and loose typing
def mixed(name: str, age) -> int:
    return age  # 'age' has no type annotation

# Variable arguments
def varargs(*args):
    pass

# Keyword arguments
def kwargs(**kwargs):
    pass
```

### Compiler Usage

```bash
# Basic compilation
python3 -m nagini.cli compile myfile.nag

# Specify output name
python3 -m nagini.cli compile myfile.nag -o myapp

# Generate C code only (don't compile to executable)
python3 -m nagini.cli compile myfile.nag --emit-c

# Verbose output (show all phases)
python3 -m nagini.cli compile myfile.nag -v
```

### Project Structure

```
Nagini/
├── nagini/                      # Main package
│   ├── __init__.py              # Package initialization
│   ├── cli.py                   # Command-line interface
│   ├── compiler/                # Compiler implementation
│   │   ├── __init__.py
│   │   ├── parser.py            # Phase 1: AST parsing
│   │   ├── ir.py                # Phase 2: IR generation
│   │   ├── backend.py           # Phase 3: C code generation
│   │   └── c/                   # C runtime headers
│   │       ├── hmap.h           # Hash table implementation
│   │       ├── pool.h           # Memory pool allocators
│   │       ├── builtin.h        # Built-in types and Object
│   │       └── list.h           # List implementation
│   ├── runtime/                 # Runtime support (Python prototypes)
│   │   ├── __init__.py
│   │   ├── builtins.py          # Base Object and built-in types
│   │   └── pools.py             # Pool allocator prototypes
│   └── examples/                # Example programs
│       ├── hello.nag            # Hello world
│       ├── hello_class.nag      # Class example
│       ├── test_functions.nag   # Function examples
│       └── ...
├── README.md                    # This file
├── DOCUMENTATION.md             # Detailed documentation
├── ARCHITECTURE.md              # Architecture deep dive
├── LICENSE                      # License information
└── setup.py                     # Python package setup
```

## 🎯 Current Status (v0.2.0)

### ✅ Implemented

- [x] Python AST parsing for Nagini syntax
- [x] Class definitions with `@property` decorators
- [x] Field extraction with type annotations
- [x] Method definitions (including `__init__`)
- [x] Function definitions with type annotations
- [x] Base `Object` class with hash table
- [x] Global symbol table for member access
- [x] Built-in types: `Int`, `Double`, `String`, `List`
- [x] Reference counting (`retain`/`release`)
- [x] IR generation for statements and expressions
- [x] C code generation
- [x] Native executable compilation
- [x] CLI interface
- [x] Expression evaluation (binary ops, unary ops, comparisons)
- [x] Control flow (if/elif/else, while)
- [x] Function calls
- [x] Constructor calls (IR representation)
- [x] Member access (IR representation)
- [x] Lambda expressions (IR representation)
- [x] Strict vs loose typing support
- [x] *args/**kwargs signatures

### 🚧 In Progress

- [ ] Full lambda closure capture
- [ ] Constructor instantiation syntax
- [ ] For loops with iterators
- [ ] List operations and iteration
- [ ] String operations
- [ ] Dictionary type
- [ ] Module system

### 📋 Planned (v0.3+)

- [ ] LLVM IR backend (direct generation)
- [ ] Optimization passes
- [ ] Generic types and constraints
- [ ] Type inference improvements
- [ ] Standard library
- [ ] Package manager
- [ ] REPL/interactive mode
- [ ] IDE support (LSP)
- [ ] Debugger integration

## 🤝 Contributing

Nagini is in early development. Contributions, bug reports, and suggestions are welcome!

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Areas We Need Help

- 🐛 Bug reports and testing
- 📖 Documentation improvements
- 🎨 Example programs
- 🔧 Runtime optimizations
- 🌉 FFI/C++ interoperability
- 📦 Standard library functions

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Python** for the elegant syntax and powerful AST parser
- **C** for the performance and universal compatibility
- **LLVM** for inspiring the compiler architecture
- The open-source community for tools and inspiration

## 🔗 Links

- **Documentation**: [DOCUMENTATION.md](DOCUMENTATION.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Implementation Details**: [IMPLEMENTATION_DETAILS.md](IMPLEMENTATION_DETAILS.md)
- **GitHub Repository**: https://github.com/Hammurabi/Nagini
- **Issue Tracker**: https://github.com/Hammurabi/Nagini/issues

---

<div align="center">

**Made with ❤️ by the Nagini Development Team**

*Bringing Python's elegance to native performance*

</div>
