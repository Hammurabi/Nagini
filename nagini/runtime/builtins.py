"""
Nagini Built-in Types and Base Object Class
Defines the base Object class with hash table for members and built-in types
"""

# Global symbol table for member names -> integers
_symbol_table = {}
_next_symbol_id = 0


def get_symbol_id(name: str) -> int:
    """
    Convert a member name to a unique integer ID.
    Uses a global symbol table.
    """
    global _next_symbol_id
    if name not in _symbol_table:
        _symbol_table[name] = _next_symbol_id
        _next_symbol_id += 1
    return _symbol_table[name]


# Base Object class - all Nagini classes inherit from this
class Object:
    """
    Base class for all Nagini objects.
    Uses a hash table to store members, functions, and metadata.
    Reference count lives outside programmer control.
    
    Structure:
        void* hash_table;  // Contains all members, functions, and metadata
        int64_t __refcount__;  // Reference counter (outside programmer control)
    """
    __refcount__: int  # 8 bytes
    hash_table: dict  # Hash table for all members
    
    def __init__(self):
        self.__refcount__ = 1
        self.hash_table = {}
    
    def __getitem__(self, member_symbol: int):
        """Access member by symbol ID: object[member_symbol]"""
        return self.hash_table.get(member_symbol)
    
    def __setitem__(self, member_symbol: int, value):
        """Set member by symbol ID: object[member_symbol] = value"""
        self.hash_table[member_symbol] = value


# Built-in value types that inherit from Object
class Int(Object):
    """64-bit integer wrapper class"""
    
    def __init__(self, value: int = 0):
        super().__init__()
        value_symbol = get_symbol_id('value')
        self[value_symbol] = value


class Double(Object):
    """64-bit floating point wrapper class"""
    
    def __init__(self, value: float = 0.0):
        super().__init__()
        value_symbol = get_symbol_id('value')
        self[value_symbol] = value


class String(Object):
    """String class with reference counting"""
    
    def __init__(self, data: str = ""):
        super().__init__()
        data_symbol = get_symbol_id('data')
        length_symbol = get_symbol_id('length')
        self[data_symbol] = data
        self[length_symbol] = len(data)


class List(Object):
    """
    Dynamic list class.
    Lists are lists of objects - any object type can be inside.
    """
    
    def __init__(self):
        super().__init__()
        data_symbol = get_symbol_id('data')
        length_symbol = get_symbol_id('length')
        capacity_symbol = get_symbol_id('capacity')
        self[data_symbol] = []  # List of objects
        self[length_symbol] = 0
        self[capacity_symbol] = 0
    
    def append(self, obj: Object):
        """Append an object to the list"""
        data_symbol = get_symbol_id('data')
        length_symbol = get_symbol_id('length')
        data = self[data_symbol]
        data.append(obj)
        self[length_symbol] = len(data)


# Reference counting functions
def retain(obj: Object) -> Object:
    """
    Increment the reference count of an object.
    Returns the object for chaining.
    """
    if obj is not None:
        obj.__refcount__ += 1
    return obj


def release(obj: Object):
    """
    Decrement the reference count of an object.
    If the count reaches zero, the object is deallocated.
    """
    if obj is not None:
        obj.__refcount__ -= 1
        if obj.__refcount__ == 0:
            # Deallocate the object
            del obj

