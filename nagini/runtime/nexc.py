"""
Nagini Native Execution Context (nexc)

This module provides a native execution context for high-performance computing.
Code within a nexc block is compiled to native C code with:
- Statically typed operations
- Contiguous memory layouts
- No Python object overhead
- Direct CPU/GPU execution (GPU support coming in future versions)

Example usage:
    with nexc('cpu') as optim:
        array = optim.array(300, type=float)
        for i in range(100):
            array[i] = 1.0 * 5353 + i * 23.0
"""

from typing import Union, Tuple, Type


class NativeArray:
    """
    Native array type for nexc context.
    
    Represents a contiguous block of memory with a specific type.
    All operations on NativeArrays are compiled to native C code.
    """
    
    def __init__(self, size: Union[int, Tuple[int, ...]], element_type: Type):
        """
        Create a native array.
        
        Args:
            size: Size of the array (int or tuple for multidimensional)
            element_type: Type of elements (int, float, bool, or custom struct)
        """
        self.size = size if isinstance(size, tuple) else (size,)
        self.element_type = element_type
        self._data = None  # Will be allocated in C
    
    def __getitem__(self, index):
        """Get element at index"""
        # This will be compiled to C array access
        pass
    
    def __setitem__(self, index, value):
        """Set element at index"""
        # This will be compiled to C array assignment
        pass


class NativeList:
    """
    Native list type for nexc context.
    
    Similar to NativeArray but specifically for lists of structs.
    """
    
    def __init__(self, size: int, element_type: Type):
        """
        Create a native list.
        
        Args:
            size: Number of elements
            element_type: Type of elements (must be a struct type)
        """
        self.size = size
        self.element_type = element_type
        self._data = None  # Will be allocated in C


class NativeStruct:
    """
    Native struct type for nexc context.
    
    Represents a C struct with named fields.
    """
    
    def __init__(self, **fields):
        """
        Define a struct type.
        
        Example:
            MyStruct = nexc.struct(a=float, b=float, c=int)
        """
        self.fields = fields


class NativeType:
    """
    Marker class for native types in nexc context.
    
    Used to represent type attributes like optim.fp32, optim.int64, etc.
    """
    
    def __init__(self, type_name: str):
        """
        Create a native type marker.
        
        Args:
            type_name: Name of the native type (e.g., 'fp32', 'int64')
        """
        self.type_name = type_name
    
    def __repr__(self):
        return f"NativeType({self.type_name})"


class NexcContext:
    """
    Native execution context manager.
    
    Provides methods for creating native data structures and manages
    the compilation of code blocks to native C.
    """
    
    # Type mappings for native types
    TYPE_MAP = {
        'int': 'int64_t',
        'int64': 'int64_t',
        'int32': 'int32_t',
        'int16': 'int16_t',
        'int8': 'int8_t',
        'int2': 'int8_t',  # 2-bit stored as 8-bit
        'uint': 'uint64_t',
        'uint64': 'uint64_t',
        'uint32': 'uint32_t',
        'uint16': 'uint16_t',
        'uint8': 'uint8_t',
        'uint2': 'uint8_t',  # 2-bit stored as 8-bit
        'float': 'double',
        'fp64': 'double',
        'fp32': 'float',
        'fp16': 'uint16_t',  # Half precision (needs conversion)
        'fp8': 'uint8_t',    # 8-bit float (needs conversion)
        'fp4': 'uint8_t',    # 4-bit float (needs conversion)
        'bool': 'uint8_t',   # Boolean as 1 byte
    }
    
    def __init__(self, target: str = 'cpu'):
        """
        Initialize native execution context.
        
        Args:
            target: Target platform ('cpu' or 'gpu' - GPU support coming soon)
        """
        if target not in ('cpu', 'gpu'):
            raise ValueError(f"Invalid target: {target}. Must be 'cpu' or 'gpu'")
        
        self.target = target
        self._variables = {}  # Track variables in this context
        self._arrays = {}     # Track arrays in this context
        
        # Type attributes for use in nexc blocks
        self.int = NativeType('int')
        self.int64 = NativeType('int64')
        self.int32 = NativeType('int32')
        self.int16 = NativeType('int16')
        self.int8 = NativeType('int8')
        self.int2 = NativeType('int2')
        self.uint = NativeType('uint')
        self.uint64 = NativeType('uint64')
        self.uint32 = NativeType('uint32')
        self.uint16 = NativeType('uint16')
        self.uint8 = NativeType('uint8')
        self.uint2 = NativeType('uint2')
        self.float = NativeType('float')
        self.fp64 = NativeType('fp64')
        self.fp32 = NativeType('fp32')
        self.fp16 = NativeType('fp16')
        self.fp8 = NativeType('fp8')
        self.fp4 = NativeType('fp4')
        self.bool = NativeType('bool')
        
        if target == 'gpu':
            raise NotImplementedError("GPU support is not yet implemented")
    
    def __enter__(self):
        """Enter the native execution context"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the native execution context"""
        # Cleanup happens automatically in C
        return False
    
    def array(self, size: Union[int, Tuple[int, ...]], type: Type = float) -> NativeArray:
        """
        Create a native array with uninitialized memory.
        
        Args:
            size: Size of the array (int or tuple for multidimensional)
            type: Element type (int, float, bool, or custom)
        
        Returns:
            NativeArray instance
        
        Example:
            array = optim.array(300, type=float)
            matrix = optim.array((10, 20), type=int)
        """
        return NativeArray(size, type)
    
    def zeros(self, size: Union[int, Tuple[int, ...]], type: Type = float) -> NativeArray:
        """
        Create a native array initialized to zero.
        
        Args:
            size: Size of the array (int or tuple for multidimensional)
            type: Element type (int, float, bool, or custom)
        
        Returns:
            NativeArray initialized to zero
        
        Example:
            array = optim.zeros(300, type=float)
        """
        array = NativeArray(size, type)
        # Will be initialized to 0 in generated C code
        return array
    
    def ones(self, size: Union[int, Tuple[int, ...]], type: Type = float) -> NativeArray:
        """
        Create a native array initialized to one.
        
        Args:
            size: Size of the array (int or tuple for multidimensional)
            type: Element type (int, float, bool, or custom)
        
        Returns:
            NativeArray initialized to one
        
        Example:
            array = optim.ones(300, type=float)
        """
        array = NativeArray(size, type)
        # Will be initialized to 1 in generated C code
        return array
    
    def struct(self, **fields) -> Type[NativeStruct]:
        """
        Define a native struct type.
        
        Args:
            **fields: Field definitions (name=type)
        
        Returns:
            A struct type that can be used with list() or array()
        
        Example:
            MyStruct = optim.struct(a=float, b=float, c=int)
            data = optim.list(100, type=MyStruct)
        """
        return type('NativeStruct', (NativeStruct,), {'_fields': fields})
    
    def list(self, size: int, type: Type) -> NativeList:
        """
        Create a native list of structs.
        
        Args:
            size: Number of elements
            type: Element type (must be a struct type)
        
        Returns:
            NativeList instance
        
        Example:
            MyStruct = optim.struct(a=float, b=float, c=int)
            data = optim.list(100, type=MyStruct)
        """
        return NativeList(size, type)
    
    def cast(self, target_type: Union[Type, NativeType], value):
        """
        Cast a value to a specific native type.
        
        This function generates the appropriate C cast for type conversion
        in native execution contexts.
        
        Args:
            target_type: Target type to cast to (NativeType or Python type)
            value: Value to cast
        
        Returns:
            Casted value (will be compiled to C cast)
        
        Example:
            result = optim.cast(optim.fp32, v.x)
            result = optim.cast(optim.int32, 3.14)
        """
        # This will be compiled to C cast in the backend
        # For now, return the value as-is (actual casting happens in C)
        return value


def nexc(target: str = 'cpu') -> NexcContext:
    """
    Create a native execution context.
    
    Args:
        target: Target platform ('cpu' or 'gpu')
    
    Returns:
        NexcContext that can be used with 'with' statement
    
    Example:
        with nexc('cpu') as optim:
            array = optim.array(300, type=float)
            for i in range(100):
                array[i] = 1.0 * 5353 + i * 23.0
    """
    return NexcContext(target)
