/* --- Flags layout ---
 * Bit 0      : allocation type (0 = pool, 1 = manual)
 * Bits 1-4   : object type (4 bits, values 0-15)
 * Bits 5-7   : reserved (3 bits)
 */

/* Forward declarations */
typedef struct Runtime Runtime;
typedef struct Function Function;
typedef struct Set Set;

/* Masks */
#define OBJ_ALLOC_MASK    0x01  // 0000 0001
#define OBJ_TYPE_MASK     0x1E  // 0001 1110
#define OBJ_RESERVED_MASK 0xE0  // 1110 0000

typedef enum {
    OBJ_TYPE_BASE      = 0,
    OBJ_TYPE_INSTANCE  = 1,
    OBJ_TYPE_INT       = 2,
    OBJ_TYPE_FLOAT     = 3,
    OBJ_TYPE_BYTES     = 4,
    OBJ_TYPE_STRING    = 5,
    OBJ_TYPE_TUPLE     = 6,
    OBJ_TYPE_LIST      = 7,
    OBJ_TYPE_DICT      = 8,
    OBJ_TYPE_SET       = 9,
    OBJ_TYPE_FUNCTION  = 10,
} ObjectType;

typedef enum {
    ALLOC_TYPE_POOL   = 0,
    ALLOC_TYPE_MANUAL = 1
} AllocationType;

#if defined(__linux__) || defined(__APPLE__) || defined(__unix__) || defined(__darwin__)
void siphash_random_key(uint8_t key[16]) {
    if (getrandom(key, 16, 0) != 16) {
        _exit(1);
    }
}
#else
void siphash_random_key(uint8_t key[16]) {
    if (BCryptGenRandom(
            NULL,
            key,
            16,
            BCRYPT_USE_SYSTEM_PREFERRED_RNG) != 0) {
        ExitProcess(1);
    }
}
#endif

#define PY_HASH_INF ((long)0x345678UL)  // some fixed arbitrary value

typedef struct { uint32_t codepoint; size_t bytes; } UTF8DecodeResult;

/* Decode one UTF-8 code point */
static UTF8DecodeResult utf8_decode(const char* s) {
    unsigned char c = (unsigned char)s[0];
    UTF8DecodeResult r = {0, 1};

    if (c <= 0x7F) {         // 1-byte ASCII
        r.codepoint = c;
    } else if ((c & 0xE0) == 0xC0) { // 2-byte
        r.codepoint = ((c & 0x1F) << 6) | (s[1] & 0x3F);
        r.bytes = 2;
    } else if ((c & 0xF0) == 0xE0) { // 3-byte
        r.codepoint = ((c & 0x0F) << 12) | ((s[1] & 0x3F) << 6) | (s[2] & 0x3F);
        r.bytes = 3;
    } else if ((c & 0xF8) == 0xF0) { // 4-byte
        r.codepoint = ((c & 0x07) << 18) | ((s[1] & 0x3F) << 12) | ((s[2] & 0x3F) << 6) | (s[3] & 0x3F);
        r.bytes = 4;
    }
    return r;
}


static inline uint64_t rotl(uint64_t x, int b) {
    return (x << b) | (x >> (64 - b));
}

#define SIPROUND            \
    do {                    \
        v0 += v1;           \
        v1 = rotl(v1, 13);  \
        v1 ^= v0;           \
        v0 = rotl(v0, 32);  \
        v2 += v3;           \
        v3 = rotl(v3, 16);  \
        v3 ^= v2;           \
        v0 += v3;           \
        v3 = rotl(v3, 21);  \
        v3 ^= v0;           \
        v2 += v1;           \
        v1 = rotl(v1, 17);  \
        v1 ^= v2;           \
        v2 = rotl(v2, 32);  \
    } while (0)

uint64_t siphash24(const uint8_t *data, size_t len, const uint8_t key[16]) {
    uint64_t k0, k1;
    memcpy(&k0, key, 8);
    memcpy(&k1, key + 8, 8);

    uint64_t v0 = 0x736f6d6570736575ULL ^ k0;
    uint64_t v1 = 0x646f72616e646f6dULL ^ k1;
    uint64_t v2 = 0x6c7967656e657261ULL ^ k0;
    uint64_t v3 = 0x7465646279746573ULL ^ k1;

    const uint8_t *end = data + (len & ~7ULL);
    uint64_t m;

    for (; data != end; data += 8) {
        memcpy(&m, data, 8);
        v3 ^= m;
        SIPROUND;
        SIPROUND;
        v0 ^= m;
    }

    uint64_t b = ((uint64_t)len) << 56;
    switch (len & 7) {
        case 7: b |= ((uint64_t) data[6]) << 48;
        case 6: b |= ((uint64_t) data[5]) << 40;
        case 5: b |= ((uint64_t) data[4]) << 32;
        case 4: b |= ((uint64_t) data[3]) << 24;
        case 3: b |= ((uint64_t) data[2]) << 16;
        case 2: b |= ((uint64_t) data[1]) << 8;
        case 1: b |= ((uint64_t) data[0]);
    }

    v3 ^= b;
    SIPROUND;
    SIPROUND;
    v0 ^= b;

    v2 ^= 0xff;
    SIPROUND;
    SIPROUND;
    SIPROUND;
    SIPROUND;

    return v0 ^ v1 ^ v2 ^ v3;
}

uint64_t siphash_cstr(const char *s, const uint8_t key[16]) {
    return siphash24((const uint8_t *)s, strlen(s), key);
}

typedef union NgObjectValue {
    int64_t i;
    uint64_t u;
    double  f;
    void*   ptr;
} NgObjectValue;

/* Base Object class - all Nagini objects inherit from this */
typedef struct Object {
    /*
        1 bit:  allocation type (pool/manual)
        3 bits: object type (base, instance, primitive, tuple, list, dict, set) as a 3 bit integer
        4 bits: reserved
    */
    struct {
        uint8_t type:5;        // ObjectType enum
        uint8_t boolean:1;    // Just a bool flag
        uint8_t reserved:2;    // Just 4 values
    } __flags__;
    struct {
        uint8_t is_manual:1;    // 0 = pool, 1 = manual
        uint8_t pool_id:6;      // Pool ID for pooled allocations (0-31)
        uint8_t boolean:1;
    } __allocation__;
    int8_t          __padding__[6]; /* Padding for alignment */
    int32_t         __typename__;   /* Type name symbol ID */
    int32_t         __refcount__;   /* Reference counter (outside programmer control) */
} Object;

typedef struct IntObject {
    Object base;
    int64_t       __value__;
} IntObject;

typedef struct FloatObject {
    Object base;
    double        __value__;
} FloatObject;

typedef struct InstanceObject {
    Object base;
    Dict*  __dict__;
} InstanceObject;

typedef struct StringObject {
    InstanceObject base;
    int64_t        hash;
    size_t         size;
} StringObject;

typedef struct UnicodeObject {
    StringObject    string;
    char            data[1];
} UnicodeObject;

typedef struct UnicodeObject16 {
    StringObject    string;
    uint16_t       data[1];
} UnicodeObject16;

typedef struct UnicodeObject32 {
    StringObject    string;
    uint32_t        data[1];
} UnicodeObject32;

typedef struct BytesObject {
    InstanceObject base;
    int64_t        hash;
    size_t         size;
    char           data[1];
} BytesObject;

typedef struct Tuple {
    Object          base;
    size_t          size;
    Object*         items[1];
} Tuple;

/// LIST
typedef struct List {
    Object          base;
    size_t          size;
    size_t          capacity;
    Object**        items;
} List;

/* * Initialize the list. 
 * Note: You likely have an 'allocator' for InstanceObjects, 
 * but here is the logic for the List internals.
 */
void list_init(List* list, size_t initial_capacity) {
    list->size = 0;
    list->capacity = (initial_capacity > 0) ? initial_capacity : 4;
    list->items = (Object**)malloc(sizeof(Object*) * list->capacity);
}

/* * Append: Grows the list geometrically (2x) 
 */
int list_append(List* list, Object* item) {
    if (list->size >= list->capacity) {
        size_t new_capacity = list->capacity * 2;
        Object** new_items = (Object**)realloc(list->items, sizeof(Object*) * new_capacity);
        if (!new_items) return -1; // Allocation failed

        list->items = new_items;
        list->capacity = new_capacity;
    }

    list->items[list->size++] = item;
    return 0;
}

/* * Find: Returns index or -1 
 */
int64_t list_find(List* list, Object* item) {
    for (size_t i = 0; i < list->size; i++) {
        if (list->items[i] == item) {
            return (int64_t)i;
        }
    }
    return -1;
}

/* * Remove: Shifts items to maintain order
 */
Object* list_remove(List* list, size_t index) {
    if (index >= list->size) return NULL;

    Object* removed_item = list->items[index];

    size_t num_to_move = list->size - index - 1;
    if (num_to_move > 0) {
        // memmove handles overlapping memory regions safely
        memmove(&list->items[index], &list->items[index + 1], sizeof(Object*) * num_to_move);
    }

    list->size--;
    return removed_item;
}

/* * Add (Concatenate): Efficiently joins two lists
 */
int list_add(List* list, List* other) {
    size_t total_needed = list->size + other->size;

    if (total_needed > list->capacity) {
        size_t new_capacity = list->capacity;
        while (new_capacity < total_needed) new_capacity *= 2;

        Object** new_items = (Object**)realloc(list->items, sizeof(Object*) * new_capacity);
        if (!new_items) return -1;

        list->items = new_items;
        list->capacity = new_capacity;
    }

    // Bulk copy the pointers from the other list
    memcpy(&list->items[list->size], other->items, sizeof(Object*) * other->size);
    list->size += other->size;
    
    return 0;
}


// Configuration
#define DICT_INITIAL_CAPACITY 2 // Must be power of 2
#define DICT_LOAD_FACTOR 85

/* * The Dictionary Entry
 * Stores the Key Object, Value Object, and the Cached Hash.
 * Padded to typically 32 bytes on 64-bit systems.
 */
typedef struct {
    Object* key;
    Object* value;
    int64_t hash;    // Cached hash to avoid re-computing
    uint32_t psl;    // Probe Sequence Length
} dict_entry_t;

typedef struct Dict {
    InstanceObject base; // Your base object header
    
    dict_entry_t* entries;
    size_t capacity;
    size_t count;
    size_t mask;
    size_t threshold;
    struct {
        uint8_t is_manual:1;    // 0 = pool, 1 = manual
        uint8_t pool_id:6;      // Pool ID for pooled allocations (0-31)
        uint8_t boolean:1;
    } __allocation__;
    int8_t          __padding__[7]; /* Padding for alignment */
} Dict;

// Helper: Check if two keys are effectively equal
static inline bool ObjectsEqual(Object* k1, Object* k2) {
    if (k1 == k2) return true;
    
    return false; 
}



int64_t hash_float(FloatObject* fobj) {
    double v = fobj->__value__;

    // Handle zero: +0.0 and -0.0 hash to 0
    if (v == 0.0) return 0;

    // Handle infinity
    if (!isfinite(v)) return v > 0 ? PY_HASH_INF : -PY_HASH_INF;

    // If value is integer-valued and fits in int64_t, hash like integer
    double intpart;
    if (modf(v, &intpart) == 0.0) {
        // exact integer
        if (intpart == -1.0) return -2;   // mimic Python int -1 special case
        return (int64_t)intpart;
    }

    // For general float: decompose v = m * 2**e
    int exp;
    double m = frexp(v, &exp);  // v = m * 2^exp, 0.5 <= |m| < 1

    // Scale mantissa to integer
    int64_t mantissa = (int64_t)ldexp(fabs(m), 53);  // 53-bit precision
    if (v < 0) mantissa = -mantissa;

    // Combine with exponent
    int64_t hash = mantissa ^ exp;

    // Avoid -1 as a hash result
    if (hash == -1) hash = -2;

    return hash;
}

Dict* alloc_dict(Runtime* runtime) {
    Dict* d = (Dict*) dynamic_pool_alloc(runtime->pool->dict);
    if (!d) return NULL;

    // Initialize Base Object (Assuming you have an init function)
    // object_init((Object*)d, OBJ_TYPE_DICT); 
    d->base.base.__flags__.type = OBJ_TYPE_DICT;
    d->base.base.__refcount__ = 1;
    
    d->capacity = DICT_INITIAL_CAPACITY;
    d->count = 0;
    d->mask = d->capacity - 1;
    d->threshold = (d->capacity * DICT_LOAD_FACTOR) / 100;
    
    bool is_manual = false;
    int pool_id = 0;
    d->entries = (dict_entry_t*) alloc(runtime, d->capacity * sizeof(dict_entry_t), &is_manual, &pool_id, true);
    d->__allocation__.is_manual = is_manual ? 1 : 0;
    d->__allocation__.pool_id = pool_id;
    if (!d->entries) {
        dynamic_pool_free(runtime->pool->dict, d);
        return NULL;
    }
    
    return d;
}

static bool _dict_resize(Dict* d, size_t new_capacity) {
    dict_entry_t* old_entries = d->entries;
    size_t old_capacity = d->capacity;

    dict_entry_t* new_entries = (dict_entry_t*)calloc(new_capacity, sizeof(dict_entry_t));
    if (!new_entries) return false;

    d->entries = new_entries;
    d->capacity = new_capacity;
    d->mask = new_capacity - 1;
    d->threshold = (new_capacity * DICT_LOAD_FACTOR) / 100;
    d->count = 0; // Will re-increment

    for (size_t i = 0; i < old_capacity; ++i) {
        if (old_entries[i].psl > 0) {
            dict_entry_t entry = old_entries[i];
            entry.psl = 1; // Reset PSL
            
            size_t idx = (size_t)entry.hash & d->mask;
            
            while (true) {
                if (d->entries[idx].psl == 0) {
                    d->entries[idx] = entry;
                    d->count++;
                    break;
                }
                
                if (entry.psl > d->entries[idx].psl) {
                    dict_entry_t temp = d->entries[idx];
                    d->entries[idx] = entry;
                    entry = temp;
                }
                
                idx = (idx + 1) & d->mask;
                entry.psl++;
            }
        }
    }

    free(old_entries);
    return true;
}

/* Set Item: d[key] = value */
int dict_set(Runtime* runtime, Dict* d, Object* key, Object* value) {
    // 1. Check Load Factor
    if (d->count >= d->threshold) {
        if (!_dict_resize(d, d->capacity * 2)) return -1;
    }

    // 2. Compute Hash once
    int64_t h = hash(runtime, key);
    size_t idx = (size_t)h & d->mask;
    uint32_t psl = 1;

    dict_entry_t entry = { .key = key, .value = value, .hash = h, .psl = psl };

    while (true) {
        dict_entry_t* curr = &d->entries[idx];

        // Case A: Empty Slot -> Insert
        if (curr->psl == 0) {
            *curr = entry;
            d->count++;
            return 0;
        }

        // Case B: Key Match -> Update
        // We check Hash first (fast), then Equality (slower)
        if (curr->hash == h && ObjectsEqual(curr->key, key)) {
            curr->value = value;
            return 0;
        }

        // Case C: Robin Hood Swap
        if (entry.psl > curr->psl) {
            dict_entry_t temp = *curr;
            *curr = entry;
            entry = temp;
        }

        idx = (idx + 1) & d->mask;
        entry.psl++;
    }
}

/* Get Item: value = d[key] */
Object* dict_get(Runtime* runtime, Dict* d, Object* key) {
    int64_t h = hash(runtime, key);
    size_t idx = (size_t)h & d->mask;
    uint32_t psl = 1;

    while (true) {
        dict_entry_t* curr = &d->entries[idx];

        if (curr->psl == 0) return NULL; // Not found

        // Optimization: Check hash first, then object equality
        if (curr->hash == h && ObjectsEqual(curr->key, key)) {
            return curr->value;
        }

        // Early Exit optimization
        if (curr->psl < psl) return NULL;

        idx = (idx + 1) & d->mask;
        psl++;
    }
}

/* Remove Item */
bool dict_del(Runtime* runtime, Dict* d, Object* key) {
    int64_t h = hash(runtime, key);
    size_t idx = (size_t)h & d->mask;
    uint32_t psl = 1;

    while (true) {
        dict_entry_t* curr = &d->entries[idx];

        if (curr->psl == 0 || psl > curr->psl) return false;

        if (curr->hash == h && ObjectsEqual(curr->key, key)) {
            d->count--;
            // Backward Shift
            while (true) {
                size_t next_idx = (idx + 1) & d->mask;
                dict_entry_t* next = &d->entries[next_idx];

                if (next->psl <= 1) {
                    d->entries[idx].psl = 0;
                    d->entries[idx].key = NULL;
                    d->entries[idx].value = NULL;
                    break;
                }

                d->entries[idx] = *next;
                d->entries[idx].psl--;
                idx = next_idx;
            }
            return true;
        }

        idx = (idx + 1) & d->mask;
        psl++;
    }
}

void dict_destroy(Runtime* runtime, Dict* d) {
    if (!d) return;

    // Decrement refcounts for all items
    for (size_t i = 0; i < d->capacity; i++) {
        if (d->entries[i].psl > 0) {
            DECREF(runtime, d->entries[i].key);
            DECREF(runtime, d->entries[i].value);
        }
    }
    
    free(d->entries);
    free(d);
}

Object* NgGetMember(Runtime* runtime, InstanceObject* instance, StringObject* member) {
    Dict* dict = instance->__dict__;
    if (!dict) return NULL;

    return dict_get(runtime, dict, (Object*)member);
}

void NgSetMember(Runtime* runtime, InstanceObject* instance, StringObject* member, Object* value) {
    Dict* dict = instance->__dict__;
    if (!dict) {
        dict = alloc_dict(runtime);
        instance->__dict__ = dict;
    }

    dict_set(runtime, dict, (Object*)member, value);
}

void NgDelMember(Runtime* runtime, InstanceObject* instance, StringObject* member) {
    Dict* dict = instance->__dict__;
    if (!dict) return;

    dict_del(runtime, dict, (Object*)member);
}










typedef struct Set {
    InstanceObject  base;
} Set;

typedef struct Function {
    Object  base;
    int32_t line;
    char*   name;
    size_t  arg_count;
    void*   native_ptr;
} Function;

typedef struct PoolCollection {
    dynamic_pool_t* base;
    dynamic_pool_t* instance;
    dynamic_pool_t* ints;
    dynamic_pool_t* floats;
    dynamic_pool_t* list;
    dynamic_pool_t* dict;
    dynamic_pool_t* set;
    dynamic_pool_t* functions;
    dynamic_pool_t* powers_of_two[64];
} PoolCollection;

typedef struct BuiltinNames {
    /* -------------------------------------------------------------------------
     * 1. Object Lifecycle & Memory Management
     * ------------------------------------------------------------------------- */
    StringObject* __new__;
    StringObject* __init__;
    StringObject* __del__;

    /* -------------------------------------------------------------------------
     * 2. String/Bytes Representation & Formatting
     * ------------------------------------------------------------------------- */
    StringObject* __repr__;
    StringObject* __str__;
    StringObject* __bytes__;
    StringObject* __format__;

    /* -------------------------------------------------------------------------
     * 3. Comparison & Hashing
     * ------------------------------------------------------------------------- */
    StringObject* __hash__;
    StringObject* __eq__;
    StringObject* __ne__;
    StringObject* __lt__;
    StringObject* __le__;
    StringObject* __gt__;
    StringObject* __ge__;
    
    /* -------------------------------------------------------------------------
     * 4. Attribute Access & Descriptors
     * ------------------------------------------------------------------------- */
    StringObject* __getattr__;
    StringObject* __getattribute__;
    StringObject* __setattr__;
    StringObject* __delattr__;
    StringObject* __dir__;

    // Descriptors
    StringObject* __get__;
    StringObject* __set__;
    StringObject* __delete__;
    StringObject* __set_name__;
    StringObject* __objclass__;
    StringObject* __slots__;
    StringObject* __dict__;
    StringObject* __weakref__;

    /* -------------------------------------------------------------------------
     * 5. Class Structure & Imports
     * ------------------------------------------------------------------------- */
    StringObject* __doc__;
    StringObject* __name__;
    StringObject* __qualname__;
    StringObject* __module__;
    StringObject* __package__;
    StringObject* __file__;
    StringObject* __path__;
    StringObject* __loader__;
    StringObject* __spec__;
    StringObject* __annotations__;

    StringObject* __class__;
    StringObject* __bases__;
    StringObject* __mro__;
    StringObject* __subclasses__;
    StringObject* __init_subclass__;
    StringObject* __class_getitem__;
    StringObject* __mro_entries__;

    /* -------------------------------------------------------------------------
     * 6. Containers (Sequences, Mappings)
     * ------------------------------------------------------------------------- */
    StringObject* __len__;
    StringObject* __length_hint__;
    StringObject* __getitem__;
    StringObject* __setitem__;
    StringObject* __delitem__;
    StringObject* __iter__;
    StringObject* __next__;
    StringObject* __reversed__;
    StringObject* __contains__;
    StringObject* __missing__;

    /* -------------------------------------------------------------------------
     * 7. Callable & Context Managers
     * ------------------------------------------------------------------------- */
    StringObject* __call__;
    StringObject* __enter__;
    StringObject* __exit__;

    /* -------------------------------------------------------------------------
     * 8. Asynchronous Programming
     * ------------------------------------------------------------------------- */
    StringObject* __await__;
    StringObject* __aiter__;
    StringObject* __anext__;
    StringObject* __aenter__;
    StringObject* __aexit__;

    /* -------------------------------------------------------------------------
     * 9. Numeric Types & Coercion
     * ------------------------------------------------------------------------- */
    StringObject* __bool__;
    StringObject* __int__;
    StringObject* __float__;
    StringObject* __complex___;
    StringObject* __index__;
    StringObject* __round__;
    StringObject* __trunc__;
    StringObject* __floor__;
    StringObject* __ceil__;

    /* -------------------------------------------------------------------------
     * 10. Arithmetic Operators (Binary)
     * ------------------------------------------------------------------------- */
    StringObject* __add__;
    StringObject* __sub__;
    StringObject* __mul__;
    StringObject* __matmul__;       // @ operator
    StringObject* __truediv__;
    StringObject* __floordiv__;
    StringObject* __mod__;
    StringObject* __divmod__;
    StringObject* __pow__;

    // Bitwise
    StringObject* __lshift__;
    StringObject* __rshift__;
    StringObject* __and__;
    StringObject* __xor__;
    StringObject* __or__;

    /* -------------------------------------------------------------------------
     * 11. Arithmetic Operators (Reflected / Swapped)
     * ------------------------------------------------------------------------- */
    StringObject* __radd__;
    StringObject* __rsub__;
    StringObject* __rmul__;
    StringObject* __rmatmul__;
    StringObject* __rtruediv__;
    StringObject* __rfloordiv__;
    StringObject* __rmod__;
    StringObject* __rdivmod__;
    StringObject* __rpow__;

    // Bitwise Reflected
    StringObject* __rlshift__;
    StringObject* __rrshift__;
    StringObject* __rand__;
    StringObject* __rxor__;
    StringObject* __ror__;

    /* -------------------------------------------------------------------------
     * 12. Arithmetic Operators (In-Place)
     * ------------------------------------------------------------------------- */
    StringObject* __iadd__;
    StringObject* __isub__;
    StringObject* __imul__;
    StringObject* __imatmul__;
    StringObject* __itruediv__;
    StringObject* __ifloordiv__;
    StringObject* __imod__;
    StringObject* __ipow__;

    // Bitwise In-Place
    StringObject* __ilshift__;
    StringObject* __irshift__;
    StringObject* __iand__;
    StringObject* __ixor__;
    StringObject* __ior__;

    /* -------------------------------------------------------------------------
     * 13. Unary Operators
     * ------------------------------------------------------------------------- */
    StringObject* __neg__;
    StringObject* __pos__;
    StringObject* __abs__;
    StringObject* __invert__;

    /* -------------------------------------------------------------------------
     * 14. Pickling, Copying & Serialization
     * ------------------------------------------------------------------------- */
    StringObject* __copy__;
    StringObject* __deepcopy__;
    StringObject* __reduce__;
    StringObject* __reduce_ex__;
    StringObject* __getstate__;
    StringObject* __setstate__;
    StringObject* __getnewargs__;
    StringObject* __getnewargs_ex__;
    StringObject* __sizeof__;

} BuiltinNames;

typedef struct Runtime {
    hmap_t*         symbol_table;
    PoolCollection* pool;
    int64_t         trace_size;
    char*           function_trace[4096];
    uint8_t         siphash_key[16];
    BuiltinNames    builtin_names;
} Runtime;

/* Function prototypes that depend on Runtime */
void* alloc(Runtime* runtime, size_t size, bool* is_manual, int* pool_id, bool zeroed);
void del(Runtime* runtime, void* ptr, bool is_manual, int pool_id);
Object* alloc_str(Runtime* runtime, const char* data);
Object* alloc_int(Runtime* runtime, int64_t value);
Object* alloc_double(Runtime* runtime, double value);
Object* alloc_bytes(Runtime* runtime, const char* data, size_t len);
Object* alloc_function(Runtime* runtime, const char* name, int32_t line, size_t arg_count, void* native_ptr);
Object* alloc_tuple(Runtime* runtime, size_t size, Object** objects);
Object* alloc_list(Runtime* runtime);
Object* alloc_instance(Runtime* runtime);
Object* alloc_object(Runtime* runtime, int32_t typename);
Dict* alloc_dict(Runtime* runtime);
int dict_set(Runtime* runtime, Dict* d, Object* key, Object* value);
Object* dict_get(Runtime* runtime, Dict* d, Object* key);
bool dict_del(Runtime* runtime, Dict* d, Object* key);
void dict_destroy(Runtime* runtime, Dict* d);
void DECREF(Runtime* runtime, void* obj);
void* INCREF(void* obj);
int64_t hash(Runtime* runtime, Object* obj);

Runtime* init_runtime() {
    Runtime* runtime = (Runtime*) malloc(sizeof(Runtime));
    runtime->symbol_table = hmap_create();
    runtime->pool = (PoolCollection*) malloc(sizeof(PoolCollection));

    // Initialize dynamic pools for different object types
    runtime->pool->base = dynamic_pool_create(sizeof(Object), 1024);
    runtime->pool->instance = dynamic_pool_create(sizeof(InstanceObject), 512);
    runtime->pool->ints = dynamic_pool_create(sizeof(IntObject), 2048);
    runtime->pool->floats = dynamic_pool_create(sizeof(FloatObject), 2048);
    runtime->pool->list = dynamic_pool_create(sizeof(List), 256);
    runtime->pool->dict = dynamic_pool_create(sizeof(Dict), 256);
    runtime->pool->set = dynamic_pool_create(sizeof(Set), 256);
    runtime->pool->functions = dynamic_pool_create(sizeof(Function), 512);
    
    size_t block_sizes[64] = { 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 144, 160, 176, 192, 208, 224, 240, 256, 272, 288, 304, 320, 336, 352, 368, 384, 416, 448, 480, 512, 576, 640, 704, 768, 832, 896, 960, 1024, 1152, 1280, 1408, 1536, 1664, 1792, 1920, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608 };
    size_t block_prpge[64] = { 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 32, 32, 32, 32, 16, 16, 16, 16, 16, 16, 16, 16, 8, 8, 8, 8, 8, 8, 8, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4 };

    for (int i = 0; i < 64; i++) {
        runtime->pool->powers_of_two[i] = dynamic_pool_create(block_sizes[i], block_prpge[i]);
    }

    runtime->trace_size = 0;

    // Generate a random SIPHASH key
    siphash_random_key(runtime->siphash_key);

    // -------------------------------------------------------------------------
    // 1. Object Lifecycle & Memory Management
    // -------------------------------------------------------------------------
    runtime->builtin_names.__new__  = (StringObject*) alloc_str(runtime, "__new__");
    runtime->builtin_names.__init__ = (StringObject*) alloc_str(runtime, "__init__");
    runtime->builtin_names.__del__  = (StringObject*) alloc_str(runtime, "__del__");

    // -------------------------------------------------------------------------
    // 2. String/Bytes Representation & Formatting
    // -------------------------------------------------------------------------
    runtime->builtin_names.__repr__   = (StringObject*) alloc_str(runtime, "__repr__");
    runtime->builtin_names.__str__    = (StringObject*) alloc_str(runtime, "__str__");
    runtime->builtin_names.__bytes__  = (StringObject*) alloc_str(runtime, "__bytes__");
    runtime->builtin_names.__format__ = (StringObject*) alloc_str(runtime, "__format__");

    // -------------------------------------------------------------------------
    // 3. Comparison & Hashing
    // -------------------------------------------------------------------------
    runtime->builtin_names.__hash__ = (StringObject*) alloc_str(runtime, "__hash__");
    runtime->builtin_names.__eq__   = (StringObject*) alloc_str(runtime, "__eq__");
    runtime->builtin_names.__ne__   = (StringObject*) alloc_str(runtime, "__ne__");
    runtime->builtin_names.__lt__   = (StringObject*) alloc_str(runtime, "__lt__");
    runtime->builtin_names.__le__   = (StringObject*) alloc_str(runtime, "__le__");
    runtime->builtin_names.__gt__   = (StringObject*) alloc_str(runtime, "__gt__");
    runtime->builtin_names.__ge__   = (StringObject*) alloc_str(runtime, "__ge__");

    // -------------------------------------------------------------------------
    // 4. Attribute Access & Descriptors
    // -------------------------------------------------------------------------
    runtime->builtin_names.__getattr__      = (StringObject*) alloc_str(runtime, "__getattr__");
    runtime->builtin_names.__getattribute__ = (StringObject*) alloc_str(runtime, "__getattribute__");
    runtime->builtin_names.__setattr__      = (StringObject*) alloc_str(runtime, "__setattr__");
    runtime->builtin_names.__delattr__      = (StringObject*) alloc_str(runtime, "__delattr__");
    runtime->builtin_names.__dir__          = (StringObject*) alloc_str(runtime, "__dir__");
    
    // Descriptors
    runtime->builtin_names.__get__      = (StringObject*) alloc_str(runtime, "__get__");
    runtime->builtin_names.__set__      = (StringObject*) alloc_str(runtime, "__set__");
    runtime->builtin_names.__delete__   = (StringObject*) alloc_str(runtime, "__delete__");
    runtime->builtin_names.__set_name__ = (StringObject*) alloc_str(runtime, "__set_name__");
    runtime->builtin_names.__objclass__ = (StringObject*) alloc_str(runtime, "__objclass__");
    runtime->builtin_names.__slots__    = (StringObject*) alloc_str(runtime, "__slots__");
    runtime->builtin_names.__dict__     = (StringObject*) alloc_str(runtime, "__dict__");
    runtime->builtin_names.__weakref__  = (StringObject*) alloc_str(runtime, "__weakref__");

    // -------------------------------------------------------------------------
    // 5. Class Structure & Imports
    // -------------------------------------------------------------------------
    runtime->builtin_names.__doc__         = (StringObject*) alloc_str(runtime, "__doc__");
    runtime->builtin_names.__name__        = (StringObject*) alloc_str(runtime, "__name__");
    runtime->builtin_names.__qualname__    = (StringObject*) alloc_str(runtime, "__qualname__");
    runtime->builtin_names.__module__      = (StringObject*) alloc_str(runtime, "__module__");
    runtime->builtin_names.__package__     = (StringObject*) alloc_str(runtime, "__package__");
    runtime->builtin_names.__file__        = (StringObject*) alloc_str(runtime, "__file__");
    runtime->builtin_names.__path__        = (StringObject*) alloc_str(runtime, "__path__");
    runtime->builtin_names.__loader__      = (StringObject*) alloc_str(runtime, "__loader__");
    runtime->builtin_names.__spec__        = (StringObject*) alloc_str(runtime, "__spec__");
    runtime->builtin_names.__annotations__ = (StringObject*) alloc_str(runtime, "__annotations__");

    runtime->builtin_names.__class__         = (StringObject*) alloc_str(runtime, "__class__");
    runtime->builtin_names.__bases__         = (StringObject*) alloc_str(runtime, "__bases__");
    runtime->builtin_names.__mro__           = (StringObject*) alloc_str(runtime, "__mro__");
    runtime->builtin_names.__subclasses__    = (StringObject*) alloc_str(runtime, "__subclasses__");
    runtime->builtin_names.__init_subclass__ = (StringObject*) alloc_str(runtime, "__init_subclass__");
    runtime->builtin_names.__class_getitem__ = (StringObject*) alloc_str(runtime, "__class_getitem__");
    runtime->builtin_names.__mro_entries__   = (StringObject*) alloc_str(runtime, "__mro_entries__");

    // -------------------------------------------------------------------------
    // 6. Containers (Sequences, Mappings)
    // -------------------------------------------------------------------------
    runtime->builtin_names.__len__         = (StringObject*) alloc_str(runtime, "__len__");
    runtime->builtin_names.__length_hint__ = (StringObject*) alloc_str(runtime, "__length_hint__");
    runtime->builtin_names.__getitem__     = (StringObject*) alloc_str(runtime, "__getitem__");
    runtime->builtin_names.__setitem__     = (StringObject*) alloc_str(runtime, "__setitem__");
    runtime->builtin_names.__delitem__     = (StringObject*) alloc_str(runtime, "__delitem__");
    runtime->builtin_names.__iter__        = (StringObject*) alloc_str(runtime, "__iter__");
    runtime->builtin_names.__next__        = (StringObject*) alloc_str(runtime, "__next__");
    runtime->builtin_names.__reversed__    = (StringObject*) alloc_str(runtime, "__reversed__");
    runtime->builtin_names.__contains__    = (StringObject*) alloc_str(runtime, "__contains__");
    runtime->builtin_names.__missing__     = (StringObject*) alloc_str(runtime, "__missing__");

    // -------------------------------------------------------------------------
    // 7. Callable & Context Managers
    // -------------------------------------------------------------------------
    runtime->builtin_names.__call__  = (StringObject*) alloc_str(runtime, "__call__");
    runtime->builtin_names.__enter__ = (StringObject*) alloc_str(runtime, "__enter__");
    runtime->builtin_names.__exit__  = (StringObject*) alloc_str(runtime, "__exit__");

    // -------------------------------------------------------------------------
    // 8. Asynchronous Programming
    // -------------------------------------------------------------------------
    runtime->builtin_names.__await__  = (StringObject*) alloc_str(runtime, "__await__");
    runtime->builtin_names.__aiter__  = (StringObject*) alloc_str(runtime, "__aiter__");
    runtime->builtin_names.__anext__  = (StringObject*) alloc_str(runtime, "__anext__");
    runtime->builtin_names.__aenter__ = (StringObject*) alloc_str(runtime, "__aenter__");
    runtime->builtin_names.__aexit__  = (StringObject*) alloc_str(runtime, "__aexit__");

    // -------------------------------------------------------------------------
    // 9. Numeric Types & Coercion
    // -------------------------------------------------------------------------
    runtime->builtin_names.__bool__    = (StringObject*) alloc_str(runtime, "__bool__");
    runtime->builtin_names.__int__     = (StringObject*) alloc_str(runtime, "__int__");
    runtime->builtin_names.__float__   = (StringObject*) alloc_str(runtime, "__float__");
    runtime->builtin_names.__complex___= (StringObject*) alloc_str(runtime, "__complex__");
    runtime->builtin_names.__index__   = (StringObject*) alloc_str(runtime, "__index__");
    runtime->builtin_names.__round__   = (StringObject*) alloc_str(runtime, "__round__");
    runtime->builtin_names.__trunc__   = (StringObject*) alloc_str(runtime, "__trunc__");
    runtime->builtin_names.__floor__   = (StringObject*) alloc_str(runtime, "__floor__");
    runtime->builtin_names.__ceil__    = (StringObject*) alloc_str(runtime, "__ceil__");

    // -------------------------------------------------------------------------
    // 10. Arithmetic Operators (Binary)
    // -------------------------------------------------------------------------
    runtime->builtin_names.__add__      = (StringObject*) alloc_str(runtime, "__add__");
    runtime->builtin_names.__sub__      = (StringObject*) alloc_str(runtime, "__sub__");
    runtime->builtin_names.__mul__      = (StringObject*) alloc_str(runtime, "__mul__");
    runtime->builtin_names.__matmul__   = (StringObject*) alloc_str(runtime, "__matmul__");
    runtime->builtin_names.__truediv__  = (StringObject*) alloc_str(runtime, "__truediv__");
    runtime->builtin_names.__floordiv__ = (StringObject*) alloc_str(runtime, "__floordiv__");
    runtime->builtin_names.__mod__      = (StringObject*) alloc_str(runtime, "__mod__");
    runtime->builtin_names.__divmod__   = (StringObject*) alloc_str(runtime, "__divmod__");
    runtime->builtin_names.__pow__      = (StringObject*) alloc_str(runtime, "__pow__");

    // Bitwise
    runtime->builtin_names.__lshift__ = (StringObject*) alloc_str(runtime, "__lshift__");
    runtime->builtin_names.__rshift__ = (StringObject*) alloc_str(runtime, "__rshift__");
    runtime->builtin_names.__and__    = (StringObject*) alloc_str(runtime, "__and__");
    runtime->builtin_names.__xor__    = (StringObject*) alloc_str(runtime, "__xor__");
    runtime->builtin_names.__or__     = (StringObject*) alloc_str(runtime, "__or__");

    // -------------------------------------------------------------------------
    // 11. Arithmetic Operators (Reflected / Swapped)
    // -------------------------------------------------------------------------
    runtime->builtin_names.__radd__      = (StringObject*) alloc_str(runtime, "__radd__");
    runtime->builtin_names.__rsub__      = (StringObject*) alloc_str(runtime, "__rsub__");
    runtime->builtin_names.__rmul__      = (StringObject*) alloc_str(runtime, "__rmul__");
    runtime->builtin_names.__rmatmul__   = (StringObject*) alloc_str(runtime, "__rmatmul__");
    runtime->builtin_names.__rtruediv__  = (StringObject*) alloc_str(runtime, "__rtruediv__");
    runtime->builtin_names.__rfloordiv__ = (StringObject*) alloc_str(runtime, "__rfloordiv__");
    runtime->builtin_names.__rmod__      = (StringObject*) alloc_str(runtime, "__rmod__");
    runtime->builtin_names.__rdivmod__   = (StringObject*) alloc_str(runtime, "__rdivmod__");
    runtime->builtin_names.__rpow__      = (StringObject*) alloc_str(runtime, "__rpow__");

    // Bitwise Reflected
    runtime->builtin_names.__rlshift__ = (StringObject*) alloc_str(runtime, "__rlshift__");
    runtime->builtin_names.__rrshift__ = (StringObject*) alloc_str(runtime, "__rrshift__");
    runtime->builtin_names.__rand__    = (StringObject*) alloc_str(runtime, "__rand__");
    runtime->builtin_names.__rxor__    = (StringObject*) alloc_str(runtime, "__rxor__");
    runtime->builtin_names.__ror__     = (StringObject*) alloc_str(runtime, "__ror__");

    // -------------------------------------------------------------------------
    // 12. Arithmetic Operators (In-Place)
    // -------------------------------------------------------------------------
    runtime->builtin_names.__iadd__      = (StringObject*) alloc_str(runtime, "__iadd__");
    runtime->builtin_names.__isub__      = (StringObject*) alloc_str(runtime, "__isub__");
    runtime->builtin_names.__imul__      = (StringObject*) alloc_str(runtime, "__imul__");
    runtime->builtin_names.__imatmul__   = (StringObject*) alloc_str(runtime, "__imatmul__");
    runtime->builtin_names.__itruediv__  = (StringObject*) alloc_str(runtime, "__itruediv__");
    runtime->builtin_names.__ifloordiv__ = (StringObject*) alloc_str(runtime, "__ifloordiv__");
    runtime->builtin_names.__imod__      = (StringObject*) alloc_str(runtime, "__imod__");
    runtime->builtin_names.__ipow__      = (StringObject*) alloc_str(runtime, "__ipow__");

    // Bitwise In-Place
    runtime->builtin_names.__ilshift__ = (StringObject*) alloc_str(runtime, "__ilshift__");
    runtime->builtin_names.__irshift__ = (StringObject*) alloc_str(runtime, "__irshift__");
    runtime->builtin_names.__iand__    = (StringObject*) alloc_str(runtime, "__iand__");
    runtime->builtin_names.__ixor__    = (StringObject*) alloc_str(runtime, "__ixor__");
    runtime->builtin_names.__ior__     = (StringObject*) alloc_str(runtime, "__ior__");

    // -------------------------------------------------------------------------
    // 13. Unary Operators
    // -------------------------------------------------------------------------
    runtime->builtin_names.__neg__    = (StringObject*) alloc_str(runtime, "__neg__");
    runtime->builtin_names.__pos__    = (StringObject*) alloc_str(runtime, "__pos__");
    runtime->builtin_names.__abs__    = (StringObject*) alloc_str(runtime, "__abs__");
    runtime->builtin_names.__invert__ = (StringObject*) alloc_str(runtime, "__invert__");

    // -------------------------------------------------------------------------
    // 14. Pickling, Copying & Serialization
    // -------------------------------------------------------------------------
    runtime->builtin_names.__copy__         = (StringObject*) alloc_str(runtime, "__copy__");
    runtime->builtin_names.__deepcopy__     = (StringObject*) alloc_str(runtime, "__deepcopy__");
    runtime->builtin_names.__reduce__       = (StringObject*) alloc_str(runtime, "__reduce__");
    runtime->builtin_names.__reduce_ex__    = (StringObject*) alloc_str(runtime, "__reduce_ex__");
    runtime->builtin_names.__getstate__     = (StringObject*) alloc_str(runtime, "__getstate__");
    runtime->builtin_names.__setstate__     = (StringObject*) alloc_str(runtime, "__setstate__");
    runtime->builtin_names.__getnewargs__   = (StringObject*) alloc_str(runtime, "__getnewargs__");
    runtime->builtin_names.__getnewargs_ex__= (StringObject*) alloc_str(runtime, "__getnewargs_ex__");
    runtime->builtin_names.__sizeof__       = (StringObject*) alloc_str(runtime, "__sizeof__");

    return runtime;
}

/* Global runtime instance */
static Runtime* runtime = NULL;

/* Get or create symbol ID for a string */
int32_t get_symbol_id(const char* name) {
    if (!runtime) {
        fprintf(stderr, "Runtime Error: Runtime not initialized\n");
        exit(1);
    }
    
    // Hash the string name
    uint64_t hash = siphash_cstr(name, runtime->siphash_key);
    int64_t key = (int64_t)hash;
    
    // Check if symbol already exists
    void* existing = hmap_get(runtime->symbol_table, key);
    if (existing != NULL) {
        return key;
    }
    
    // Add new symbol
    char* name_copy = strdup(name);
    hmap_put(runtime->symbol_table, key, name_copy);
    return key;
}

/* Allocate memory from a pool or manually */
void* alloc(Runtime* runtime, size_t size, bool* is_manual, int* pool_id, bool zeroed) {
    if (!runtime || !runtime->pool) return NULL;

    int id = -1;
    for (int i = 0; i < 64; i++) {
        if (size <= runtime->pool->powers_of_two[i]->block_payload_size) {
            id = i;
            break;
        }
    }

    if (id == -1) {
        *is_manual = true;
        *pool_id = 0;
        void* ptr = malloc(size);
        if (zeroed) memset(ptr, 0, size);
        return ptr;
    }

    *is_manual = false;
    *pool_id = id;

    void* ptr = dynamic_pool_alloc(runtime->pool->powers_of_two[id]);
    if (zeroed) memset(ptr, 0, size);
    return ptr;
}

/* Free memory from a pool or manually */
void del(Runtime* runtime, void* ptr, bool is_manual, int pool_id) {
    if (is_manual) {
        free(ptr);
    } else {
        if (pool_id >= 0 && pool_id < 64) {
            dynamic_pool_free(runtime->pool->powers_of_two[pool_id], ptr);
        }
    }
}

/* Call a function object */
static inline Object* NgCall(Runtime* runtime, Function* func, Tuple* args, Dict* kwargs) {
    Object* (*native_func)(Runtime*, Tuple*, Dict*) = (Object* (*)(Runtime*, Tuple*, Dict*))func->native_ptr;
    return native_func(runtime, args, kwargs);
}

/* Hash an object */
static inline int64_t hash(Runtime* runtime, Object* obj) {
    int32_t obj_type = obj->__flags__.type;

    switch (obj_type) {
        case OBJ_TYPE_INT: {
            IntObject* int_obj = (IntObject*)obj;
            int64_t val = int_obj->__value__;
            if (val == -1) return -2;
            return val;
        }
        case OBJ_TYPE_FLOAT:
            return hash_float((FloatObject*)obj);
        case OBJ_TYPE_TUPLE: {
            Tuple* tuple = (Tuple*)obj;
            int64_t h = 17;
            for (size_t i = 0; i < tuple->size; i++) {
                h = h * 31 + hash(runtime, tuple->items[i]);
            }
            return h;
        }
        case OBJ_TYPE_STRING: {
            StringObject* str_obj = (StringObject*)obj;
            return str_obj->hash;
        }
        case OBJ_TYPE_BYTES: {
            BytesObject* bytes_obj = (BytesObject*)obj;
            return bytes_obj->hash;
        }
        case OBJ_TYPE_INSTANCE: {
            InstanceObject* inst = (InstanceObject*)obj;
            Function* hash_method = (Function*)dict_get(runtime, inst->__dict__, runtime->builtin_names.__hash__);
            if (hash_method) {
                Tuple* self_arg = (Tuple*) alloc_tuple(runtime, 1, &obj);
                Object* result = NgCall(runtime, hash_method, self_arg, NULL);
                DECREF(runtime, (Object*)self_arg);
                if (result && result->__flags__.type == OBJ_TYPE_INT) {
                    IntObject* int_result = (IntObject*) result;
                    int64_t h = int_result->__value__;
                    if (h == -1) h = -2;
                    return h;
                }
            }

            return (int64_t)(uintptr_t)obj; // placeholder
        }
        default:
            return (int64_t)(uintptr_t)obj;
    }
}

/* Create a new Object */
Object* alloc_object(Runtime* runtime, int32_t typename) {
    Object* obj = (Object*) dynamic_pool_alloc(runtime->pool->base);
    obj->__typename__ = typename;
    obj->__refcount__ = 1;
    obj->__allocation__.is_manual = 0;
    obj->__flags__.type = OBJ_TYPE_BASE;

    return obj;
}

/* Create a new Object */
Object* alloc_instance(Runtime* runtime) {
    InstanceObject* obj = (InstanceObject*) dynamic_pool_alloc(runtime->pool->instance);
    obj->base.__typename__ = get_symbol_id("object");
    obj->base.__refcount__ = 1;
    obj->__dict__ = alloc_dict(runtime);
    obj->base.__allocation__.is_manual = 0;
    obj->base.__flags__.type = OBJ_TYPE_INSTANCE;

    return (Object*)obj;
}

Object* alloc_int(Runtime* runtime, int64_t value) {
    IntObject* obj = (IntObject*) dynamic_pool_alloc(runtime->pool->ints);
    obj->base.__typename__ = get_symbol_id("int");
    obj->base.__refcount__ = 1;
    obj->__value__ = value;
    obj->base.__allocation__.is_manual = 0;
    obj->base.__flags__.type = OBJ_TYPE_INT;

    return (Object*)obj;
}

Object* alloc_double(Runtime* runtime, double value) {
    FloatObject* obj = (FloatObject*) dynamic_pool_alloc(runtime->pool->floats);
    obj->base.__typename__ = get_symbol_id("double");
    obj->base.__refcount__ = 1;
    obj->__value__ = value;
    obj->base.__allocation__.is_manual = 0;
    obj->base.__flags__.type = OBJ_TYPE_FLOAT;

    return (Object*)obj;
}

Object* alloc_str(Runtime* runtime, const char* data) {
    size_t len = strlen(data);

    bool is_ascii = true;
    unsigned int kind = 0;

    // First pass: determine kind, ASCII flag, and number of code points
    size_t real_length = 0;
    uint32_t max_cp = 0;
    size_t i = 0;
    while (i < len) {
        UTF8DecodeResult r = utf8_decode(data + i);
        if (r.codepoint > max_cp) max_cp = r.codepoint;
        if (r.codepoint > 0x7F) is_ascii = false;
        i += r.bytes;
        real_length++;
    }

    // Determine kind
    if (max_cp <= 0xFF) kind = 0;        // 1 byte
    else if (max_cp <= 0xFFFF) kind = 1; // 2 bytes
    else kind = 2;                        // 4 bytes

    bool is_manual = false;
    int pool_id = 0;
    StringObject* str_obj = NULL;
    Object* object = NULL;

    i = 0; // reset for second pass
    if (kind == 0) {
        UnicodeObject* uni_obj = (UnicodeObject*) alloc(runtime, sizeof(UnicodeObject) + real_length, &is_manual, &pool_id, true);
        str_obj = &uni_obj->string;
        object = (Object*) uni_obj;

        size_t j = 0;
        while (i < len) {
            UTF8DecodeResult r = utf8_decode(data + i);
            uni_obj->data[j++] = (char) r.codepoint;
            i += r.bytes;
        }
        uni_obj->data[real_length] = '\0';
    }
    else if (kind == 1) {
        UnicodeObject16* uni_obj = (UnicodeObject16*) alloc(runtime, sizeof(UnicodeObject16) + real_length * sizeof(uint16_t), &is_manual, &pool_id, true);
        str_obj = &uni_obj->string;
        object = (Object*) uni_obj;

        size_t j = 0;
        while (i < len) {
            UTF8DecodeResult r = utf8_decode(data + i);
            uni_obj->data[j++] = (uint16_t) r.codepoint;
            i += r.bytes;
        }
    }
    else { // kind == 2
        UnicodeObject32* uni_obj = (UnicodeObject32*) alloc(runtime, sizeof(UnicodeObject32) + real_length * sizeof(uint32_t), &is_manual, &pool_id, true);
        str_obj = &uni_obj->string;
        object = (Object*) uni_obj;

        size_t j = 0;
        while (i < len) {
            UTF8DecodeResult r = utf8_decode(data + i);
            uni_obj->data[j++] = r.codepoint;
            i += r.bytes;
        }
    }

    str_obj->base.base.__typename__ = get_symbol_id("str");
    str_obj->base.base.__refcount__ = 1;
    str_obj->size = real_length;
    str_obj->base.base.__allocation__.is_manual = is_manual ? 1 : 0;
    str_obj->base.base.__allocation__.pool_id = pool_id;
    str_obj->base.base.__flags__.type = OBJ_TYPE_STRING;

    str_obj->base.base.__flags__.boolean = is_ascii ? 1 : 0;
    str_obj->base.base.__flags__.reserved = kind;
    str_obj->hash = siphash_cstr(data, runtime->siphash_key);

    return (Object*)str_obj;
}

Object* alloc_bytes(Runtime* runtime, const char* data, size_t len) {
    BytesObject* bytes_obj = (BytesObject*) malloc(sizeof(BytesObject) + len);

    bytes_obj->base.base.__typename__ = get_symbol_id("bytes");
    bytes_obj->base.base.__refcount__ = 1;
    bytes_obj->size = len;
    memcpy(bytes_obj->data, data, len);
    bytes_obj->base.base.__allocation__.is_manual = 1;
    bytes_obj->base.base.__flags__.type = OBJ_TYPE_BYTES;

    bytes_obj->hash = siphash24((const uint8_t*) data, len, runtime->siphash_key);
    return (Object*) bytes_obj;
}

Object* alloc_function(Runtime* runtime, const char* name, int32_t line, size_t arg_count, void* native_ptr) {
    Function* func = (Function*) dynamic_pool_alloc(runtime->pool->functions);
    func->base.__typename__ = get_symbol_id("function");
    func->base.__refcount__ = 1;
    func->line = line;
    func->name = strdup(name);
    func->arg_count = arg_count;
    func->native_ptr = native_ptr;
    func->base.__allocation__.is_manual = 0;
    func->base.__flags__.type = OBJ_TYPE_FUNCTION;

    return (Object*) func;
}

Object* alloc_tuple(Runtime* runtime, size_t size, Object** objects) {
    Tuple* tuple = (Tuple*) malloc(sizeof(Tuple) + (size - 1) * sizeof(Object*));

    tuple->base.__typename__ = get_symbol_id("tuple");
    tuple->base.__refcount__ = 1;
    tuple->size = size;
    tuple->base.__allocation__.is_manual = 1;
    tuple->base.__flags__.type = OBJ_TYPE_TUPLE;

    for (size_t i = 0; i < size; i++) {
        tuple->items[i] = objects[i];
    }

    return (Object*) tuple;
}

Object* alloc_list(Runtime* runtime) {
    List* list = (List*) dynamic_pool_alloc(runtime->pool->list);
    list->base.__typename__ = get_symbol_id("list");
    list->base.__refcount__ = 1;
    list->base.__allocation__.is_manual = 0;
    list->base.__flags__.type = OBJ_TYPE_LIST;

    list_init(list, 1);
    return (Object*)list;
}

void* INCREF(void* obj) {
    if (obj != NULL) {
        Object* o = (Object*)obj;
        o->__refcount__++;
    }
    return obj;
}

/* Decrement reference count and free if zero */
void DECREF(Runtime* runtime, void* obj) {
    if (obj != NULL) {
        Object* o = (Object*)obj;
        o->__refcount__--;
        if (o->__refcount__ == 0) {
            int32_t obj_type = o->__flags__.type;
            bool is_manual = o->__allocation__.is_manual == 1;
            switch (obj_type) {
                case OBJ_TYPE_BASE:
                    if (is_manual) {
                        del(runtime, o, is_manual, o->__allocation__.pool_id);
                    } else {
                        dynamic_pool_free(runtime->pool->base, o);
                    }
                    break;
                case OBJ_TYPE_INSTANCE: {
                    InstanceObject* inst = (InstanceObject*)o;
                    DECREF(runtime, inst->__dict__);
                    if (is_manual) {
                        del(runtime, o, is_manual, o->__allocation__.pool_id);
                    } else {
                        dynamic_pool_free(runtime->pool->instance, o);
                    }
                    break;
                }
                case OBJ_TYPE_INT: {
                    if (is_manual) {
                        del(runtime, o, is_manual, o->__allocation__.pool_id);
                    } else {
                        dynamic_pool_free(runtime->pool->ints, o);
                    }
                    break;
                }
                case OBJ_TYPE_FLOAT: {
                    if (is_manual) {
                        del(runtime, o, is_manual, o->__allocation__.pool_id);
                    } else {
                        dynamic_pool_free(runtime->pool->floats, o);
                    }
                    break;
                }
                case OBJ_TYPE_TUPLE: {
                    Tuple* tuple = (Tuple*)o;
                    for (size_t i = 0; i < tuple->size; i++) {
                        DECREF(runtime, tuple->items[i]);
                    }
                    if (!is_manual) {
                        fprintf(stderr, "DECREF: Tuple should be manually allocated\n");
                    }
                    del(runtime, o, is_manual, o->__allocation__.pool_id);
                    break;
                }
                case OBJ_TYPE_STRING: {
                    StringObject* str_obj = (StringObject*)o;
                    if (!is_manual) {
                        fprintf(stderr, "DECREF: String should be manually allocated\n");
                    }
                    del(runtime, o, is_manual, o->__allocation__.pool_id);
                    break;
                }
                case OBJ_TYPE_BYTES: {
                    BytesObject* bytes_obj = (BytesObject*)o;
                    if (!is_manual) {
                        fprintf(stderr, "DECREF: Bytes should be manually allocated\n");
                    }
                    del(runtime, o, is_manual, o->__allocation__.pool_id);
                    break;
                }
                case OBJ_TYPE_DICT: {
                    Dict* dict = (Dict*)o;
                    dict_destroy(runtime, dict);
                    break;
                }
                case OBJ_TYPE_LIST: {
                    List* list = (List*)o;
                    for (size_t i = 0; i < list->size; i++) {
                        DECREF(runtime, list->items[i]);
                    }
                    free(list->items);
                    if (is_manual) {
                        del(runtime, o, is_manual, o->__allocation__.pool_id);
                    } else {
                        dynamic_pool_free(runtime->pool->list, o);
                    }
                    break;
                }
                case OBJ_TYPE_FUNCTION: {
                    Function* func = (Function*)o;
                    free(func->name);
                    if (is_manual) {
                        del(runtime, o, is_manual, o->__allocation__.pool_id);
                    } else {
                        dynamic_pool_free(runtime->pool->functions, o);
                    }
                    break;
                }
                case OBJ_TYPE_SET: {
                    Set* set = (Set*)o;
                    if (is_manual) {
                        del(runtime, o, is_manual, o->__allocation__.pool_id);
                    } else {
                        dynamic_pool_free(runtime->pool->set, o);
                    }
                    break;
                }
                default:
                    if (is_manual) {
                        del(runtime, o, is_manual, o->__allocation__.pool_id);
                    } else {
                        fprintf(stderr, "DECREF: Unknown object type %d\n", obj_type);
                        exit(1);
                    }
                    break;
            }
        }
    }
}