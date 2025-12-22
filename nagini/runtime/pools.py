"""
Nagini Memory Pool Allocators
Provides DynamicPool (auto-resize) and StaticPool (fixed size) allocators
"""


class DynamicPool:
    """
    Dynamic memory pool that automatically grows when capacity is reached.
    Used as the default pool for primitives.
    """
    
    def __init__(self, initial_capacity: int = 1024, growth_factor: float = 2.0):
        """
        Initialize a dynamic pool.
        
        Args:
            initial_capacity: Initial number of blocks in the pool
            growth_factor: Factor by which to grow when full (default 2.0)
        """
        self.capacity = initial_capacity
        self.growth_factor = growth_factor
        self.used = 0
        self.blocks = None  # Pointer to memory blocks
        
    def allocate(self, size: int) -> object:
        """
        Allocate memory from the pool.
        Automatically grows if capacity is reached.
        """
        if self.used >= self.capacity:
            self._grow()
        # Allocate and return pointer
        block = None  # Actual allocation logic
        self.used += 1
        return block
    
    def deallocate(self, ptr: object):
        """
        Return memory to the pool.
        """
        self.used -= 1
        # Return block to pool
        
    def _grow(self):
        """
        Grow the pool by the growth factor.
        """
        new_capacity = int(self.capacity * self.growth_factor)
        # Reallocate pool with new capacity
        self.capacity = new_capacity


class StaticPool:
    """
    Static memory pool with fixed capacity.
    Throws error when trying to allocate beyond capacity.
    """
    
    def __init__(self, capacity: int):
        """
        Initialize a static pool with fixed capacity.
        
        Args:
            capacity: Maximum number of blocks in the pool
        """
        self.capacity = capacity
        self.used = 0
        self.blocks = None  # Pointer to memory blocks
        
    def allocate(self, size: int) -> object:
        """
        Allocate memory from the pool.
        Raises error if capacity is exceeded.
        """
        if self.used >= self.capacity:
            raise MemoryError(f"StaticPool capacity exceeded: {self.used}/{self.capacity}")
        
        # Allocate and return pointer
        block = None  # Actual allocation logic
        self.used += 1
        return block
    
    def deallocate(self, ptr: object):
        """
        Return memory to the pool.
        """
        self.used -= 1
        # Return block to pool


# Global default pool for primitives
_default_pool = DynamicPool(initial_capacity=1024, growth_factor=2.0)


def get_default_pool() -> DynamicPool:
    """Get the default dynamic pool used for primitives."""
    return _default_pool
