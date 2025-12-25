/* The Pool Structure */
typedef struct {
    size_t block_size;
    size_t capacity;
    void* memory_block; // The actual big chunk of memory
    void* free_head;    // Pointer to the first free block
} static_pool_t;

/* initialization */
static_pool_t* static_pool_create(size_t block_size, size_t capacity) {
    // 1. Ensure block size can hold a pointer (for the free list)
    if (block_size < sizeof(void*)) {
        block_size = sizeof(void*);
    }
    
    // 2. Allocate the pool structure
    static_pool_t* pool = (static_pool_t*)malloc(sizeof(static_pool_t));
    if (!pool) return NULL;

    pool->block_size = block_size;
    pool->capacity = capacity;

    // 3. Allocate the actual contiguous memory
    pool->memory_block = malloc(block_size * capacity);
    if (!pool->memory_block) {
        free(pool);
        return NULL;
    }

    // 4. Thread the free list through the memory block
    // We treat each block as a void* pointer that points to the next block.
    uint8_t* ptr = (uint8_t*)pool->memory_block;
    for (size_t i = 0; i < capacity - 1; i++) {
        void** current_node = (void**)ptr;
        // Point current node to the next node
        *current_node = (ptr + block_size); 
        ptr += block_size;
    }
    
    // Last block points to NULL
    *((void**)ptr) = NULL;

    // Head points to the start
    pool->free_head = pool->memory_block;

    return pool;
}

/* Allocate: O(1) */
void* static_pool_alloc(static_pool_t* pool) {
    if (pool->free_head == NULL) {
        return NULL; // Pool is full
    }

    // Pop head from the free list
    void* block = pool->free_head;
    
    // The first bytes of 'block' currently contain the pointer to the NEXT free block.
    // We update free_head to that next block.
    pool->free_head = *(void**)block;

    return block;
}

/* Free: O(1) */
void static_pool_free(static_pool_t* pool, void* ptr) {
    if (!ptr) return;

    // Push 'ptr' onto the head of the free list
    // 1. Write the current head address into the memory of 'ptr'
    *(void**)ptr = pool->free_head;
    
    // 2. Make 'ptr' the new head
    pool->free_head = ptr;
}

void static_pool_destroy(static_pool_t* pool) {
    if (pool) {
        free(pool->memory_block);
        free(pool);
    }
}

/// DYNAMIC POOL IMPLEMENTATION

/* Forward declaration */
typedef struct pool_page_t pool_page_t;

/* * The Page Structure 
 * Manages a chunk of memory containing N blocks.
 */
struct pool_page_t {
    pool_page_t* next;  // Doubly linked list for fast removal
    pool_page_t* prev;
    size_t used_count;  // How many blocks are currently active?
    void* free_head;    // Local free list for this specific page
};

/* * The Block Header
 * Hidden before the pointer returned to the user.
 * Allows us to find the parent Page from any object pointer.
 */
typedef struct {
    pool_page_t* page;
} block_header_t;

typedef struct {
    size_t block_payload_size; // Size the user requested
    size_t block_total_size;   // Size + Header + Alignment padding
    size_t blocks_per_page;
    
    pool_page_t* partial_pages; // Pages with available slots
    pool_page_t* full_pages;    // Pages that are completely full
} dynamic_pool_t;


/* --- Helper: List Management --- */

static void _unlink_page(pool_page_t** list_head, pool_page_t* page) {
    if (page->prev) page->prev->next = page->next;
    if (page->next) page->next->prev = page->prev;
    if (*list_head == page) *list_head = page->next;
    
    page->next = NULL;
    page->prev = NULL;
}

static void _push_page(pool_page_t** list_head, pool_page_t* page) {
    page->next = *list_head;
    page->prev = NULL;
    if (*list_head) (*list_head)->prev = page;
    *list_head = page;
}

/* --- API Implementation --- */

dynamic_pool_t* dynamic_pool_create(size_t block_size, size_t blocks_per_page) {
    dynamic_pool_t* pool = (dynamic_pool_t*)malloc(sizeof(dynamic_pool_t));
    if (!pool) return NULL;

    pool->block_payload_size = block_size;
    
    // Ensure payload is large enough to hold a 'next' pointer for the free list
    size_t required_payload = (block_size < sizeof(void*)) ? sizeof(void*) : block_size;
    
    // Total size = Header (to find page) + Payload
    pool->block_total_size = sizeof(block_header_t) + required_payload;
    
    pool->blocks_per_page = blocks_per_page;
    pool->partial_pages = NULL;
    pool->full_pages = NULL;

    return pool;
}

/* Internal: Allocate a new page from OS and set it up */
static int _expand_pool(dynamic_pool_t* pool) {
    size_t data_size = pool->block_total_size * pool->blocks_per_page;
    size_t total_alloc = sizeof(pool_page_t) + data_size;

    uint8_t* buffer = (uint8_t*)malloc(total_alloc);
    if (!buffer) return -1;

    pool_page_t* page = (pool_page_t*)buffer;
    page->used_count = 0;
    
    // Memory starts right after the Page struct
    uint8_t* data_start = buffer + sizeof(pool_page_t);
    page->free_head = data_start;

    // Initialize the free list inside this new page
    for (size_t i = 0; i < pool->blocks_per_page; i++) {
        uint8_t* curr_block = data_start + (i * pool->block_total_size);
        
        // 1. Set the Hidden Header (Pointer back to Page)
        block_header_t* header = (block_header_t*)curr_block;
        header->page = page;

        // 2. Set the Free List Pointer (inside the payload area)
        void** next_ptr_loc = (void**)(curr_block + sizeof(block_header_t));
        
        if (i < pool->blocks_per_page - 1) {
            *next_ptr_loc = curr_block + pool->block_total_size;
        } else {
            *next_ptr_loc = NULL; // End of list
        }
    }

    // New pages always start in the partial list
    _push_page(&pool->partial_pages, page);
    return 0;
}

void* dynamic_pool_alloc(dynamic_pool_t* pool) {
    // If no pages have space, create a new one
    if (!pool->partial_pages) {
        if (_expand_pool(pool) != 0) return NULL;
    }

    pool_page_t* page = pool->partial_pages;
    
    // 1. Pop block from page's free list
    uint8_t* raw_block = (uint8_t*)page->free_head;
    
    // The "Next Free" pointer is stored just after the header
    void** next_ptr_loc = (void**)(raw_block + sizeof(block_header_t));
    page->free_head = *next_ptr_loc;
    
    page->used_count++;

    // 2. If page is now full, move from Partial -> Full list
    // This removes it from consideration for future allocs until space opens up
    if (page->free_head == NULL) {
        _unlink_page(&pool->partial_pages, page);
        _push_page(&pool->full_pages, page);
    }

    // 3. Return pointer to the payload (hiding the header)
    return (void*)(raw_block + sizeof(block_header_t));
}

void dynamic_pool_free(dynamic_pool_t* pool, void* ptr) {
    if (!ptr) return;

    // 1. Recover the Hidden Header to find the Page
    uint8_t* payload = (uint8_t*)ptr;
    uint8_t* raw_block = payload - sizeof(block_header_t);
    block_header_t* header = (block_header_t*)raw_block;
    
    pool_page_t* page = header->page;

    // 2. If page was Full, it is now Partial (because we are freeing a slot)
    if (page->free_head == NULL) {
        _unlink_page(&pool->full_pages, page);
        _push_page(&pool->partial_pages, page);
    }

    // 3. Add block back to the Page's local free list
    void** next_ptr_loc = (void**)(raw_block + sizeof(block_header_t));
    *next_ptr_loc = page->free_head;
    page->free_head = raw_block;

    page->used_count--;

    // 4. SHRINK: If page is completely empty, return memory to OS
    if (page->used_count == 0) {
        _unlink_page(&pool->partial_pages, page);
        free(page);
    }
}

void dynamic_pool_destroy(dynamic_pool_t* pool) {
    if (!pool) return;

    // Helper to free a list of pages
    pool_page_t* lists[] = { pool->partial_pages, pool->full_pages };
    
    for (int i = 0; i < 2; i++) {
        pool_page_t* curr = lists[i];
        while (curr) {
            pool_page_t* next = curr->next;
            free(curr);
            curr = next;
        }
    }
    
    free(pool);
}