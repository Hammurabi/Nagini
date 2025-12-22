# Nagini Compiler Architecture

## Overview

Nagini is a compiled programming language that transforms Python-like syntax into native machine code. The compiler is implemented in Python and generates C code as an intermediate step before compilation to native executables.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Nagini Source Code                       │
│                            (.nag files)                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 1: AST Parser                           │
│                  (nagini/compiler/parser.py)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ - Uses Python's built-in ast.parse()                      │   │
│  │ - Extracts class definitions                              │   │
│  │ - Parses @property decorators                             │   │
│  │ - Extracts field types and annotations                    │   │
│  │ - Calculates memory offsets                               │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼ ClassInfo objects
┌─────────────────────────────────────────────────────────────────┐
│              Phase 2: IR Generation (Intermediate)               │
│                    (nagini/compiler/ir.py)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ - Transforms parsed classes into IR                       │   │
│  │ - Generates function IR                                   │   │
│  │ - Manages allocation strategies                           │   │
│  │ - Creates main function                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼ NaginiIR object
┌─────────────────────────────────────────────────────────────────┐
│                Phase 3: Backend Code Generation                  │
│                  (nagini/compiler/backend.py)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ - Generates C code from IR                                │   │
│  │ - Creates struct definitions                              │   │
│  │ - Adds object headers for paradigm='object'               │   │
│  │ - Maps Nagini types to C types                            │   │
│  │ - Generates functions                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼ C Source Code
┌─────────────────────────────────────────────────────────────────┐
│                 Phase 4: Native Compilation                      │
│                  (gcc/clang compiler)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ - Compiles C code to native executable                    │   │
│  │ - Uses system C compiler (gcc/clang)                      │   │
│  │ - Produces platform-specific binary                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Native Executable                          │
│                     (Platform-specific)                          │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Parser (nagini/compiler/parser.py)

**Purpose:** Transform Nagini source code into structured class information.

**Key Classes:**
- `NaginiParser`: Main parser class
- `ClassInfo`: Stores class metadata
- `FieldInfo`: Stores field information

**Process:**
1. Parse source code using Python's `ast.parse()`
2. Walk AST tree looking for class definitions
3. Extract `@property` decorator values
4. Parse field annotations (type hints)
5. Calculate memory offsets based on types
6. Return dictionary of ClassInfo objects

**Type Sizes:**
- `int`: 8 bytes (64-bit)
- `float`: 8 bytes (64-bit)
- `bool`: 1 byte
- `str`: 8 bytes (pointer)

**Object Header (32 bytes):**
- `type_id`: 8 bytes
- `alloc_type`: 4 bytes
- `ref_count`: 4 bytes
- `parent_ptr`: 8 bytes

### 2. IR Generator (nagini/compiler/ir.py)

**Purpose:** Create an intermediate representation suitable for code generation.

**Key Classes:**
- `NaginiIR`: Main IR container
- `FunctionIR`: Function representation
- `AllocationIR`: Allocation instruction

**Current Implementation:**
- Stores parsed class information
- Generates basic main function
- Provides class layout queries

**Future Plans:**
- Full expression trees
- Control flow graphs
- Optimization passes
- Type checking

### 3. Backend (nagini/compiler/backend.py)

**Purpose:** Generate target code (C) from IR.

**Key Class:**
- `LLVMBackend`: Code generator (currently generates C)

**Generation Process:**
1. Generate C headers
2. For each class:
   - Generate struct definition
   - Add object header if `paradigm='object'`
   - Add fields with proper C types
3. Generate functions:
   - Translate IR statements to C
   - Handle main function specially
4. Output complete C program

**Type Mapping:**
```
Nagini → C
int    → int64_t
float  → double
bool   → uint8_t
str    → char*
```

**Future Plans:**
- Direct LLVM IR generation via llvmlite
- Optimization passes
- Multiple backend targets

### 4. CLI (nagini/cli.py)

**Purpose:** Command-line interface for the compiler.

**Commands:**
- `compile`: Compile a .nag file

**Options:**
- `-o, --output`: Specify output filename
- `--emit-c`: Generate C code only (don't compile)
- `-v, --verbose`: Show detailed compilation info

**Usage:**
```bash
python3 -m nagini.cli compile file.nag
```

## Memory Management Architecture

### Allocation Strategies

**Pool Allocation:**
- Pre-allocated memory pool per class
- Fast allocation/deallocation
- Automatic cleanup on scope exit
- Best for: Game objects, ECS components

**GC Allocation:**
- Reference counting or tracing GC
- Automatic memory management
- Tracks object references
- Best for: General-purpose objects

**Heap Allocation:**
- Manual malloc/free
- Programmer-controlled lifetime
- Explicit deallocation required
- Best for: Long-lived objects

### Object Paradigms

**Object Paradigm (`paradigm='object'`):**
```c
typedef struct {
    // 32-byte header
    uint64_t type_id;      // Class/type identifier
    uint32_t alloc_type;   // pool/gc/heap
    uint32_t ref_count;    // Reference counter
    void* parent_ptr;      // Parent class pointer
    
    // Fields follow
    int64_t field1;
    double field2;
} ClassName;
```

**Data Paradigm (`paradigm='data'`):**
```c
typedef struct {
    // No header - just fields
    int64_t field1;
    double field2;
} ClassName;
```

## Layout Strategies

### CPP Layout (`layout='cpp'`)
- Standard C++ struct alignment
- Compatible with most C/C++ code
- Platform-dependent padding

### STD430 Layout (`layout='std430'`)
- Tight packing for GPU compatibility
- Minimal padding
- Suitable for shader buffers

### Custom Layout (`layout='custom'`)
- User-defined offsets
- For special requirements

## Compilation Pipeline

### Step-by-Step Process

1. **Read Source File**
   ```
   Input: hello.nag
   Output: Source code string
   ```

2. **Parse**
   ```
   Input: Source code string
   Parser: ast.parse() → AST walk → Class extraction
   Output: Dict[str, ClassInfo]
   ```

3. **Generate IR**
   ```
   Input: Dict[str, ClassInfo]
   Process: Create function IR, allocation IR
   Output: NaginiIR object
   ```

4. **Generate C Code**
   ```
   Input: NaginiIR object
   Process: Template-based C code generation
   Output: C source code string
   ```

5. **Compile to Executable**
   ```
   Input: C source code
   Compiler: gcc/clang
   Output: Native executable
   ```

### Example Compilation

**Input (example.nag):**
```python
@property(malloc_strategy='pool', layout='cpp', paradigm='object')
class Vec3:
    x: float
    y: float
    z: float
```

**Generated C Code:**
```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

/* Class: Vec3 */
/* malloc_strategy: pool */
/* layout: cpp */
/* paradigm: object */
typedef struct {
    /* Object Header */
    uint64_t type_id;
    uint32_t alloc_type;
    uint32_t ref_count;
    void* parent_ptr;

    /* Fields */
    double x;
    double y;
    double z;
} Vec3;

int main() {
    printf("Hello, World!\n");
    return 0;
}
```

**Compiled Binary:**
- Native executable for the platform
- Directly runnable
- No runtime dependencies (except libc)

## Future Architecture

### Planned Features

1. **Full Language Support**
   - Function definitions
   - Expression evaluation
   - Control flow (if/while/for)
   - Method calls
   - Operators

2. **Runtime System**
   - Memory pool allocator
   - Reference counting GC
   - Heap allocator
   - Smart pointers

3. **LLVM Backend**
   - Direct LLVM IR generation
   - Optimization passes
   - JIT compilation support

4. **FFI Layer**
   - Automatic C/C++ binding generation
   - Struct marshalling
   - Function call wrappers

5. **Standard Library**
   - Core data structures
   - I/O operations
   - Math functions
   - String manipulation

## Performance Characteristics

### Current Implementation
- Parse time: O(n) where n = source code lines
- IR generation: O(c) where c = number of classes
- C code generation: O(c + f) where f = fields
- Compilation: Depends on C compiler

### Memory Usage
- Parser: Minimal (AST + ClassInfo objects)
- IR: Proportional to program size
- Backend: Generates strings, then discarded
- Runtime: Only compiled executable remains

### Future Optimizations
- Lazy parsing
- Incremental compilation
- Caching compiled modules
- Link-time optimization

## Design Decisions

### Why Python AST?
- Fast development
- No need to write custom parser
- Leverages Python's robust parsing
- Easy to extend

### Why C Backend First?
- Universal compatibility
- Leverage mature C compilers
- Easy debugging
- Later migration to LLVM IR

### Why Hybrid Memory Management?
- Flexibility for different use cases
- Performance where needed (pool)
- Convenience where desired (GC)
- Control when required (heap)

### Why Object vs Data Paradigm?
- ECS needs lightweight data (data)
- OOP needs metadata (object)
- Let developer choose trade-off
- Zero overhead when not needed

## Testing

### Test Suite
- `test_compiler.sh`: Automated test script
- Tests compilation of all examples
- Verifies executable output
- Checks C code generation

### Manual Testing
```bash
# Compile and run
python3 -m nagini.cli compile examples/hello.nag
./hello

# Generate C only
python3 -m nagini.cli compile examples/hello.nag --emit-c

# Verbose output
python3 -m nagini.cli compile examples/hello.nag -v
```

## Contributing

### Adding New Features

1. **New Language Feature**
   - Update parser to recognize syntax
   - Extend IR to represent feature
   - Add backend code generation
   - Add tests

2. **New Allocation Strategy**
   - Add to parser property values
   - Update backend generation
   - Implement runtime support

3. **New Type**
   - Add to TYPE_SIZES in parser
   - Add C mapping in backend
   - Test with examples

## References

- [Python AST Documentation](https://docs.python.org/3/library/ast.html)
- [LLVM Documentation](https://llvm.org/docs/)
- [C++ Memory Layout](https://en.cppreference.com/w/cpp/language/data_members)
- [GPU Buffer Layouts (std430)](https://www.khronos.org/opengl/wiki/Interface_Block_(GLSL))
