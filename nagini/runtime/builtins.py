"""
Nagini Built-in Types and Base Object Class
Defines the base Object class and built-in types (Int, Double, String, List)
"""

# Base Object class - all Nagini classes inherit from this
class Object:
    """
    Base class for all Nagini objects.
    Contains reference counting functionality.
    """
    __refcount__: int  # 8 bytes
    
    def __init__(self):
        self.__refcount__ = 1


# Built-in value types that inherit from Object
class Int(Object):
    """64-bit integer wrapper class"""
    value: int  # 8 bytes
    
    def __init__(self, value: int = 0):
        super().__init__()
        self.value = value


class Double(Object):
    """64-bit floating point wrapper class"""
    value: float  # 8 bytes
    
    def __init__(self, value: float = 0.0):
        super().__init__()
        self.value = value


class String(Object):
    """String class with reference counting"""
    data: str  # pointer to char array
    length: int  # length of string
    
    def __init__(self, data: str = ""):
        super().__init__()
        self.data = data
        self.length = len(data)


class List(Object):
    """Dynamic list class"""
    data: object  # pointer to array
    length: int  # number of elements
    capacity: int  # allocated capacity
    
    def __init__(self):
        super().__init__()
        self.data = None
        self.length = 0
        self.capacity = 0


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
