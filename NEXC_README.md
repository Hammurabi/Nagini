# Native Execution Context (nexc) for Nagini

## Overview

The Native Execution Context (nexc) is a high-performance feature in Nagini that allows blocks of code to be compiled and executed as native low-level C code, bypassing Python object semantics in favor of statically typed, contiguous, high-performance operations.

## Usage

### Basic Syntax

```python
with nexc('cpu') as optim:
    # Native code block
    array = optim.array(300, type=float)
    for i in range(100):
        array[i] = 1.0 * 5353 + i * 23.0
```

### Available Methods

#### `optim.array(size, type=float)`
Creates a native array with uninitialized memory.

```python
with nexc('cpu') as optim:
    data = optim.array(100, type=float)
    for i in range(100):
        data[i] = i * 2.5
```

#### `optim.zeros(size, type=float)`
Creates a native array initialized to zero.

```python
with nexc('cpu') as optim:
    zeros = optim.zeros(50, type=float)
    # All elements are 0.0
```

#### `optim.ones(size, type=float)`
Creates a native array initialized to one.

```python
with nexc('cpu') as optim:
    ones = optim.ones(50, type=float)
    # All elements are 1.0
```

#### `optim.struct(**fields)`
Defines a native struct type (future feature).

```python
with nexc('cpu') as optim:
    Point = optim.struct(x=float, y=float, z=float)
    # Use with optim.list()
```

#### `optim.list(size, type)`
Creates a native list of structs (future feature).

```python
with nexc('cpu') as optim:
    Point = optim.struct(x=float, y=float)
    points = optim.list(100, type=Point)
```

## Supported Types

### Integer Types
- `int` / `int64` - 64-bit signed integer
- `int32` - 32-bit signed integer
- `int16` - 16-bit signed integer
- `int8` - 8-bit signed integer
- `int2` - 2-bit integer (stored as 8-bit)

### Unsigned Integer Types
- `uint` / `uint64` - 64-bit unsigned integer
- `uint32` - 32-bit unsigned integer
- `uint16` - 16-bit unsigned integer
- `uint8` - 8-bit unsigned integer
- `uint2` - 2-bit unsigned integer (stored as 8-bit)

### Floating Point Types
- `float` / `fp64` - 64-bit double precision (default)
- `fp32` - 32-bit single precision
- `fp16` - 16-bit half precision
- `fp8` - 8-bit float (requires conversion)
- `fp4` - 4-bit float (requires conversion)

### Boolean Type
- `bool` - Boolean (stored as 1 byte)

## Features

### Native Operations
All operations inside a nexc block are compiled to native C code:
- Arithmetic operations: `+`, `-`, `*`, `/`
- Loops: `for`, `while`
- Conditionals: `if`, `else`
- Array indexing: `array[i]`

### Performance Benefits
- No Python object overhead
- Direct memory access
- Contiguous memory layout
- Cache-friendly access patterns
- Compiler optimizations

### Memory Layout
- All arrays are one-dimensional in C
- Multidimensional arrays use row-major (C) layout
- Minimum allocation sizes:
  - Boolean array: 1 byte (8 bools minimum)
  - int2 array: 1 byte (4 ints minimum)

## Target Platforms

### CPU (Available)
```python
with nexc('cpu') as optim:
    # CPU-optimized native code
```

### GPU (Future)
```python
with nexc('gpu') as optim:
    # GPU-accelerated computation
```

## Examples

### Example 1: Vector Operations
```python
with nexc('cpu') as optim:
    a = optim.array(1000, type=float)
    b = optim.array(1000, type=float)
    c = optim.array(1000, type=float)
    
    for i in range(1000):
        a[i] = i * 1.5
        b[i] = i * 2.0
        c[i] = a[i] + b[i]
```

### Example 2: Matrix Operations
```python
with nexc('cpu') as optim:
    result = optim.zeros(100, type=float)
    
    for i in range(100):
        sum = 0.0
        for j in range(100):
            sum = sum + i * j
        result[i] = sum
```

### Example 3: Complex Calculations
```python
with nexc('cpu') as optim:
    output = optim.array(500, type=float)
    
    for i in range(500):
        x = i * 0.01
        # Polynomial evaluation
        output[i] = x * x * x - 2.0 * x * x + x + 1.0
```

## Implementation Details

### Compilation Process
1. Nagini parser detects `with nexc()` statements
2. IR generator creates WithIR nodes
3. Backend generates optimized C code:
   - Native C arrays instead of Object wrappers
   - Direct arithmetic instead of NgAdd/NgMul
   - Native loops instead of interpreted loops

### Generated C Code Example

**Nagini Code:**
```python
with nexc('cpu') as optim:
    array = optim.array(10, type=float)
    for i in range(10):
        array[i] = i * 2.0
```

**Generated C Code:**
```c
{
    /* Native Execution Context (nexc) - cpu target */
    double array[10];
    for(int i = 0; i < 10; i++) {
        array[i] = (i * 2.0);
    }
}
```

## Limitations (Current Version)

1. **No mixing of nexc and Nagini objects**: Variables from outside nexc blocks cannot be used inside nexc blocks
2. **CPU target only**: GPU support planned for future release
3. **Limited type support**: Currently supports int and float types
4. **No struct support yet**: Struct and list features are placeholders
5. **One-dimensional arrays**: Multidimensional arrays mapped to 1D

## Future Enhancements

- GPU acceleration support
- Struct and list support
- Multidimensional array syntax
- Additional numeric types (fp16, fp8, etc.)
- SIMD vectorization
- Parallel execution
- Memory persistence between nexc blocks

## Safety Considerations

The nexc context provides a "safe pocket" for native computation by:
- Enforcing type consistency
- Bounds checking in debug mode
- Isolated memory contexts
- Compile-time validation

Any Nagini object referenced from outside the nexc block will cause the code to fall back to standard Nagini object semantics for that operation.
