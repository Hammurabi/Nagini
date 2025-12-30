# Nagini Import System

The Nagini compiler supports importing classes and functions from other Nagini files.

## Import Syntax

Nagini supports standard Python import syntax:

```python
# Import entire module (all classes and functions)
import module_name

# Import specific items from a module
from module_name import ClassName, function_name
```

## Import Resolution

The import system searches for modules in the following order:

1. **Local Directory**: Looks for `{module_name}.nag` in the same directory as the source file
2. **Compiler NG Directory**: Looks for `{module_name}.ng` in `nagini/compiler/ng/`

## Examples

### Example 1: Local Import

**vec3.nag** (in the same directory):
```python
@property(paradigm='object')
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
```

**main.nag**:
```python
from vec3 import Vec3

if __name__ == "__main__":
    v = Vec3(3.0, 4.0, 0.0)
    print(v)
    print(f"Magnitude: {v.magnitude()}")
```

### Example 2: Import from Compiler NG Directory

**nagini/compiler/ng/builtin.ng**:
```python
@property(paradigm='object')
class Point:
    x: float
    y: float
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

def distance(p1, p2) -> float:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return (dx**2 + dy**2) ** 0.5
```

**main.nag**:
```python
from builtin import Point, distance

if __name__ == "__main__":
    p1 = Point(0.0, 0.0)
    p2 = Point(3.0, 4.0)
    print(f"Distance: {distance(p1, p2)}")
```

### Example 3: Multiple Imports

```python
from vec3 import Vec3
from builtin import Point, distance

if __name__ == "__main__":
    # Use both imported classes
    v = Vec3(1.0, 2.0, 3.0)
    p = Point(5.0, 12.0)
    
    print(v)
    print(p)
```

## Features

- **Circular Import Protection**: The import system tracks imported files to prevent circular imports
- **Automatic Merging**: Imported classes and functions are automatically merged into the compilation unit
- **Type Safety**: Imported classes maintain their type annotations and paradigm settings
- **Silent Fallback**: If a module is not found, the compiler continues without error (useful for Python built-ins)

## Compilation

The import system is transparent to compilation:

```bash
# Compile a file with imports
nagini compile main.nag

# The compiler automatically resolves and includes imported modules
./main
```

## Notes

- Imported files are parsed only once, even if imported multiple times
- All classes and functions from imported files become available in the compilation unit
- Import statements must be at the top level (before main code)
