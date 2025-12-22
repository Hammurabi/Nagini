# Nagini Language Quick Reference

## Class Declaration

```python
@property(malloc_strategy='pool', layout='cpp', paradigm='object')
class ClassName:
    field1: type1
    field2: type2
```

### Properties

| Property | Values | Description |
|----------|--------|-------------|
| `malloc_strategy` | `pool`, `gc`, `heap` | Memory allocation strategy |
| `layout` | `cpp`, `std430`, `custom` | Memory layout for FFI |
| `paradigm` | `object`, `data` | Full object vs lightweight data |

### malloc_strategy

- **pool**: Pre-allocated memory pool
  - Fastest allocation
  - Automatic deallocation on scope exit
  - Best for: Game objects, ECS components, temporary data

- **gc**: Garbage collected
  - Reference counting
  - Automatic memory management
  - Best for: General-purpose objects, shared data

- **heap**: Manual allocation
  - Explicit control via `alloc()` and `free()`
  - No automatic cleanup
  - Best for: Long-lived data, precise control needed

### layout

- **cpp**: C++ compatible struct layout
  - Standard field alignment
  - Compatible with most C++ code
  - Best for: General FFI

- **std430**: Shader Storage Buffer Object layout
  - Tight packing, minimal padding
  - GPU-compatible
  - Best for: GPU buffers, compute shaders

- **custom**: User-defined layout
  - Manual control over offsets
  - Best for: Special requirements

### paradigm

- **object**: Full object with metadata
  - Object header (32 bytes): type_id, alloc_type, ref_count, parent_ptr
  - Supports reflection and introspection
  - Can have methods (future)
  - Best for: OOP, polymorphism, reflection

- **data**: Lightweight data container
  - No object header
  - Fields only
  - Zero overhead
  - Best for: ECS, GPU data, pure data structures

## Types

| Nagini Type | C Type | Size |
|-------------|--------|------|
| `int` | `int64_t` | 8 bytes |
| `float` | `double` | 8 bytes |
| `bool` | `uint8_t` | 1 byte |
| `str` | `char*` | 8 bytes (pointer) |

## Memory Layout Examples

### Object Paradigm
```python
@property(malloc_strategy='pool', layout='cpp', paradigm='object')
class Player:
    x: float
    y: float
```

Memory layout:
```
[Object Header: 32 bytes]
  - type_id: 8 bytes
  - alloc_type: 4 bytes
  - ref_count: 4 bytes
  - parent_ptr: 8 bytes
[Fields]
  - x: 8 bytes
  - y: 8 bytes
Total: 56 bytes
```

### Data Paradigm
```python
@property(malloc_strategy='pool', layout='cpp', paradigm='data')
class Vec3:
    x: float
    y: float
    z: float
```

Memory layout:
```
[Fields]
  - x: 8 bytes
  - y: 8 bytes
  - z: 8 bytes
Total: 24 bytes
```

## Compiler Commands

```bash
# Compile to executable
nagini compile file.nag

# Specify output name
nagini compile file.nag -o myprogram

# Generate C code only
nagini compile file.nag --emit-c

# Verbose output
nagini compile file.nag -v
```

Or using Python module:

```bash
python3 -m nagini.cli compile file.nag
```

## Example Programs

### Hello World
```python
# hello.nag
# Empty file or comments only - compiler generates hello world
```

### Simple Class
```python
# game_object.nag
@property(malloc_strategy='pool', layout='cpp', paradigm='object')
class GameObject:
    id: int
    x: float
    y: float
    health: int
```

### Multiple Classes
```python
# entities.nag

# Full object with metadata
@property(malloc_strategy='gc', layout='cpp', paradigm='object')
class Player:
    name: str
    level: int
    score: int

# Lightweight data container
@property(malloc_strategy='pool', layout='cpp', paradigm='data')
class Component:
    active: bool
    type_id: int

# GPU-compatible data
@property(malloc_strategy='heap', layout='std430', paradigm='data')
class Vertex:
    x: float
    y: float
    z: float
```

## Generated C Code

The compiler generates C structs that match the specified layout and paradigm:

```c
/* Object paradigm - with header */
typedef struct {
    /* Object Header */
    uint64_t type_id;
    uint32_t alloc_type;
    uint32_t ref_count;
    void* parent_ptr;
    
    /* Fields */
    int64_t id;
    double x;
    double y;
} GameObject;

/* Data paradigm - no header */
typedef struct {
    /* Fields */
    double x;
    double y;
    double z;
} Vertex;
```

## Future Features

The following features are planned for future versions:

- Object allocation: `obj = ClassName(args)`
- Explicit allocation: `obj = alloc(ClassName, args)`
- GC allocation: `obj = galloc(ClassName, args)`
- Methods and functions
- Inheritance and polymorphism
- Control flow (if, while, for)
- Expression evaluation
- Runtime memory management
- FFI/C++ interop layer
- Standard library

## Use Cases

### Game Development
- Use `pool` allocation for game objects and components
- Use `data` paradigm for ECS components
- Use `object` paradigm for entities with behavior

### GPU Computing
- Use `std430` layout for GPU buffers
- Use `data` paradigm for pure data
- Use `heap` allocation for persistent buffers

### Systems Programming
- Use `heap` allocation for precise control
- Use `cpp` layout for C interop
- Use `object` paradigm for complex types

### AI/ML
- Use `pool` allocation for tensors
- Use `data` paradigm for matrix data
- Use `gc` allocation for model objects
