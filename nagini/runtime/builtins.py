"""
Nagini Built-in Types and Base Object Class

This module defines the conceptual runtime system for Nagini, including:
- The base Object class that all Nagini objects inherit from
- Built-in value wrapper types (Int, Double, String, List)
- Reference counting functions (retain/release)
- Global symbol table for member name resolution

Note: This is Python prototype code that documents the design. The actual
runtime is implemented in C (see nagini/compiler/c/builtin.h).

Architecture:
    All Nagini objects have:
    - A hash table for dynamic member storage
    - A reference counter for automatic memory management
    
    Member access pattern:
    - Member names → integers via global symbol table
    - Access: object[member_symbol] → hash table lookup
"""

# ============================================================
# Global Symbol Table
# ============================================================
# Converts member/field names to unique integer IDs for fast hash lookups.
# Example: "x" → 0, "y" → 1, "value" → 2
_symbol_table = {}
_next_symbol_id = 0


def get_symbol_id(name: str) -> int:
    """
    Convert a member name to a unique integer ID.
    
    This is used to implement efficient member lookup. Instead of
    hashing strings every time we access a member, we hash the
    string once to get an integer ID, then use that ID for all
    subsequent lookups.
    
    Example:
        x_id = get_symbol_id("x")  # Returns 0 (first call)
        y_id = get_symbol_id("y")  # Returns 1 (second call)
        x_id2 = get_symbol_id("x") # Returns 0 (cached)
    
    Args:
        name: Member name as a string
        
    Returns:
        Unique integer ID for this name
    """
    global _next_symbol_id
    if name not in _symbol_table:
        _symbol_table[name] = _next_symbol_id
        _next_symbol_id += 1
    return _symbol_table[name]


# ============================================================
# Base Object Class
# ============================================================
class Object:
    """
    Base class for all Nagini objects.
    
    In Nagini, all classes inherit from Object by default. This provides:
    - Dynamic member storage via hash table
    - Automatic reference counting
    - Uniform memory management
    
    Memory Layout (C struct):
        typedef struct Object {
            HashTable* hash_table;   // Dynamic member storage
            int64_t __refcount__;    // Reference counter (managed by runtime)
        } Object;
    
    Member Access:
        Members are accessed via symbol IDs, not strings:
        1. Convert name to symbol: id = get_symbol_id("x")
        2. Access via hash table: value = object[id]
    
    Reference Counting:
        The __refcount__ field is managed by the runtime and is
        outside programmer control. Use retain() and release()
        functions to manipulate reference counts.
    """
    __refcount__: int  # 8 bytes, managed by runtime
    hash_table: dict   # Hash table for all members, functions, and metadata
    
    def __init__(self):
        """Initialize a new Object with reference count of 1."""
        self.__refcount__ = 1
        self.hash_table = {}
    
    def __getitem__(self, member_symbol: int):
        """
        Access member by symbol ID: object[member_symbol]
        
        This is the fundamental member access pattern in Nagini.
        Instead of obj.x, we use obj[symbol_id_of_x].
        """
        return self.hash_table.get(member_symbol)
    
    def __setitem__(self, member_symbol: int, value):
        """
        Set member by symbol ID: object[member_symbol] = value
        
        This is how we assign to object members dynamically.
        """
        self.hash_table[member_symbol] = value


# ============================================================
# Built-in Value Types
# ============================================================
# These wrapper classes box primitive values into objects.
# They all inherit from Object and use the hash table for storage.

class Int(Object):
    """
    64-bit integer wrapper class.
    
    Wraps a primitive int64_t value into an Object for uniform handling.
    The actual value is stored in the hash table under the 'value' key.
    
    Example:
        x = Int(42)
        value = x[get_symbol_id('value')]  # Returns 42
    """
    
    def __init__(self, value: int = 0):
        super().__init__()
        value_symbol = get_symbol_id('value')
        self[value_symbol] = value


class Double(Object):
    """
    64-bit floating point wrapper class.
    
    Wraps a primitive double value into an Object.
    Used when we need to treat numbers as first-class objects.
    
    Example:
        pi = Double(3.14159)
        value = pi[get_symbol_id('value')]  # Returns 3.14159
    """
    
    def __init__(self, value: float = 0.0):
        super().__init__()
        value_symbol = get_symbol_id('value')
        self[value_symbol] = value


class String(Object):
    """
    String class with automatic memory management.
    
    Stores string data and length in the hash table.
    Reference counting ensures strings are cleaned up automatically.
    
    Storage:
        - 'data': The actual string content
        - 'length': Number of characters
    """
    
    def __init__(self, data: str = ""):
        super().__init__()
        data_symbol = get_symbol_id('data')
        length_symbol = get_symbol_id('length')
        self[data_symbol] = data
        self[length_symbol] = len(data)


class List(Object):
    """
    Dynamic list class for storing sequences of objects.
    
    Lists in Nagini are heterogeneous - they can contain any object type.
    All elements are Objects (either wrapper types or user-defined classes).
    
    Storage:
        - 'data': Python list holding Object references
        - 'length': Current number of elements
        - 'capacity': Allocated capacity (for future growth)
    
    Example:
        lst = List()
        lst.append(Int(1))
        lst.append(Double(2.5))
        lst.append(String("hello"))
    """
    
    def __init__(self):
        super().__init__()
        data_symbol = get_symbol_id('data')
        length_symbol = get_symbol_id('length')
        capacity_symbol = get_symbol_id('capacity')
        self[data_symbol] = []  # List of Object references
        self[length_symbol] = 0
        self[capacity_symbol] = 0
    
    def append(self, obj: Object):
        """
        Append an object to the list.
        
        Automatically retains a reference to the object (reference count +1).
        
        Args:
            obj: Any Object-derived instance
        """
        data_symbol = get_symbol_id('data')
        length_symbol = get_symbol_id('length')
        data = self[data_symbol]
        data.append(obj)
        self[length_symbol] = len(data)


# ============================================================
# Reference Counting Functions
# ============================================================
# Manual reference count management for advanced use cases

def retain(obj: Object) -> Object:
    """
    Increment the reference count of an object.
    
    Use this when you want to keep an object alive beyond its normal scope.
    Every retain() must be balanced with a release().
    
    Args:
        obj: Object to retain
        
    Returns:
        The same object (for chaining)
        
    Example:
        obj = retain(create_object())  # Keep alive
        # ... use obj ...
        release(obj)  # Balance the retain
    """
    if obj is not None:
        obj.__refcount__ += 1
    return obj


def release(obj: Object):
    """
    Decrement the reference count of an object.
    
    When the reference count reaches zero, the object is automatically
    deallocated. This is the core of Nagini's memory management.
    
    Args:
        obj: Object to release
        
    Example:
        obj = create_object()  # refcount = 1
        retain(obj)            # refcount = 2
        release(obj)           # refcount = 1
        release(obj)           # refcount = 0, object deallocated
    """
    if obj is not None:
        obj.__refcount__ -= 1
        if obj.__refcount__ == 0:
            # Reference count reached zero - deallocate
            del obj

