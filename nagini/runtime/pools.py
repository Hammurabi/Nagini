"""
Nagini Memory Pool Allocators

This module defines two types of memory pool allocators for efficient memory
management in Nagini:

1. DynamicPool - Automatically grows when capacity is reached (default)
2. StaticPool - Fixed capacity, throws error when full (predictable performance)

Memory pools are pre-allocated chunks of memory that allow fast allocation
and deallocation without calling malloc/free for every object. They're
particularly useful for:
- Game objects that are created/destroyed frequently
- Entity Component Systems (ECS)
- High-performance systems requiring predictable latency

Note: This is Python prototype code. The actual implementation is in C
(see nagini/compiler/c/pool.h).

Design Trade-offs:
    DynamicPool: More flexible, handles growth automatically
    StaticPool: More predictable, better for real-time systems
"""


class DynamicPool:
    """
    Dynamic memory pool that automatically grows when capacity is reached.
    
    This is the default pool allocator used for Nagini primitives and
    objects with 'gc' malloc_strategy. When the pool fills up, it
    automatically allocates more memory and continues serving requests.
    
    Characteristics:
    - Initial capacity: 1024 objects (default)
    - Growth factor: 2.0x (doubles in size each time)
    - No errors on allocation
    - Slight overhead when growing
    
    Example:
        pool = DynamicPool(initial_capacity=1024, growth_factor=2.0)
        obj1 = pool.allocate(size=32)  # First allocation
        # ... allocate 1023 more objects ...
        obj1024 = pool.allocate(size=32)  # Triggers growth to 2048 capacity
    """
    
    def __init__(self, initial_capacity: int = 1024, growth_factor: float = 2.0):
        """
        Initialize a dynamic pool.
        
        Args:
            initial_capacity: Initial number of blocks in the pool (default 1024)
            growth_factor: Multiplier for capacity when growing (default 2.0)
                          - 2.0 means double the capacity each time
                          - 1.5 means grow by 50% each time
        """
        self.capacity = initial_capacity
        self.growth_factor = growth_factor
        self.used = 0  # Number of blocks currently allocated
        self.blocks = None  # Pointer to memory blocks (in C implementation)
        
    def allocate(self, size: int) -> object:
        """
        Allocate memory from the pool.
        
        If the pool is full, it automatically grows by the growth factor.
        This ensures allocation never fails (unless we run out of system memory).
        
        Args:
            size: Size in bytes to allocate
            
        Returns:
            Pointer to allocated memory block
        """
        if self.used >= self.capacity:
            # Pool is full - grow it automatically
            self._grow()
        
        # Allocate from the pool and return pointer
        block = None  # Actual allocation logic implemented in C
        self.used += 1
        return block
    
    def deallocate(self, ptr: object):
        """
        Return memory to the pool for reuse.
        
        The memory is not freed to the system, but rather marked
        as available for future allocations. This makes deallocation
        very fast (O(1)).
        
        Args:
            ptr: Pointer to memory block to deallocate
        """
        self.used -= 1
        # Mark block as available for reuse
        
    def _grow(self):
        """
        Grow the pool by the growth factor.
        
        This is called automatically when the pool is full.
        Process:
        1. Calculate new capacity (old_capacity * growth_factor)
        2. Allocate new memory block
        3. Copy existing data to new block
        4. Update capacity
        
        Cost: O(n) where n is the number of allocated objects
        """
        new_capacity = int(self.capacity * self.growth_factor)
        # Reallocate pool with new capacity (implemented in C)
        self.capacity = new_capacity


class StaticPool:
    """
    Static memory pool with fixed capacity.
    
    This pool has a hard limit on capacity and throws an error when
    trying to allocate beyond that limit. Used with 'pool' malloc_strategy.
    
    Characteristics:
    - Fixed capacity set at creation
    - Fast allocation (no growth overhead)
    - Predictable memory usage
    - Errors if capacity exceeded
    
    Use cases:
    - Real-time systems requiring bounded memory
    - Game engines with fixed object counts
    - Safety-critical systems
    
    Example:
        pool = StaticPool(capacity=100)
        for i in range(100):
            obj = pool.allocate(size=32)  # OK
        pool.allocate(size=32)  # Raises MemoryError
    """
    
    def __init__(self, capacity: int):
        """
        Initialize a static pool with fixed capacity.
        
        Args:
            capacity: Maximum number of blocks the pool can hold
        """
        self.capacity = capacity
        self.used = 0  # Number of blocks currently allocated
        self.blocks = None  # Pointer to memory blocks (in C implementation)
        
    def allocate(self, size: int) -> object:
        """
        Allocate memory from the pool.
        
        Unlike DynamicPool, this will raise an error if the pool is full.
        This makes memory usage predictable and errors explicit.
        
        Args:
            size: Size in bytes to allocate
            
        Returns:
            Pointer to allocated memory block
            
        Raises:
            MemoryError: If pool capacity is exceeded
        """
        if self.used >= self.capacity:
            raise MemoryError(f"StaticPool capacity exceeded: {self.used}/{self.capacity}")
        
        # Allocate from the pool and return pointer
        block = None  # Actual allocation logic implemented in C
        self.used += 1
        return block
    
    def deallocate(self, ptr: object):
        """
        Return memory to the pool for reuse.
        
        Same as DynamicPool - marks memory as available without
        freeing to the system.
        
        Args:
            ptr: Pointer to memory block to deallocate
        """
        self.used -= 1
        # Mark block as available for reuse


# ============================================================
# Global Default Pool
# ============================================================
# This is the default pool used for primitive types (Int, Double, etc.)
# and objects that use the 'gc' malloc strategy
_default_pool = DynamicPool(initial_capacity=1024, growth_factor=2.0)


def get_default_pool() -> DynamicPool:
    """
    Get the global default dynamic pool.
    
    This pool is used for:
    - Primitive wrapper objects (Int, Double, String, List)
    - User-defined classes with malloc_strategy='gc' (default)
    
    Returns:
        The global DynamicPool instance
    """
    return _default_pool
