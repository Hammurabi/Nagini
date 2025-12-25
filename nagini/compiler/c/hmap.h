/* * CONFIGURATION 
 * INITIAL_CAPACITY: Must be a power of 2.
 * LOAD_FACTOR_PERCENT: Threshold to resize (85-90% is safe for Robin Hood).
 */
#define HMAP_INITIAL_CAPACITY 2
#define HMAP_LOAD_FACTOR_PERCENT 85

typedef struct {
    int64_t key;
    void* value;
    /* * PSL (Probe Sequence Length): 
     * 0 = Empty slot
     * 1 = Item is at its ideal hash index
     * >1 = Item was shifted due to collision
     */
    uint32_t psl; 
} hmap_entry_t;

typedef struct {
    hmap_entry_t* entries;
    size_t capacity;     // Total slots available
    size_t count;        // Active items
    size_t mask;         // capacity - 1 (for fast modulo)
    size_t threshold;    // Count at which we resize
} hmap_t;

/* --- Hashing Helper --- 
 * SplitMix64-style mixer. Invertible and high entropy.
 * Crucial for int64 keys to prevent patterns in pointers/ints from causing collisions.
 */
static inline uint64_t _hmap_hash(int64_t k) {
    uint64_t x = (uint64_t)k;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    x = x ^ (x >> 31);
    return x;
}

/* --- API Implementation --- */

/* Initialize the map. Returns NULL on allocation failure. */
hmap_t* hmap_create(void) {
    hmap_t* map = (hmap_t*)malloc(sizeof(hmap_t));
    if (!map) return NULL;

    map->capacity = HMAP_INITIAL_CAPACITY;
    map->count = 0;
    map->mask = map->capacity - 1;
    map->threshold = (map->capacity * HMAP_LOAD_FACTOR_PERCENT) / 100;
    
    // Calloc ensures all PSLs are 0 (EMPTY)
    map->entries = (hmap_entry_t*)calloc(map->capacity, sizeof(hmap_entry_t));
    
    if (!map->entries) {
        free(map);
        return NULL;
    }
    
    return map;
}

void hmap_destroy(hmap_t* map) {
    if (map) {
        free(map->entries);
        free(map);
    }
}

/* Internal function to resize and rehash */
static bool _hmap_resize(hmap_t* map, size_t new_capacity) {
    hmap_entry_t* old_entries = map->entries;
    size_t old_capacity = map->capacity;

    hmap_entry_t* new_entries = (hmap_entry_t*)calloc(new_capacity, sizeof(hmap_entry_t));
    if (!new_entries) return false;

    map->entries = new_entries;
    map->capacity = new_capacity;
    map->mask = new_capacity - 1;
    map->threshold = (new_capacity * HMAP_LOAD_FACTOR_PERCENT) / 100;
    map->count = 0; // We will re-increment this via put

    // Rehash all existing items
    for (size_t i = 0; i < old_capacity; ++i) {
        if (old_entries[i].psl > 0) {
            // We use a simplified put logic here as we know keys are unique
            hmap_entry_t entry = old_entries[i];
            entry.psl = 1; // Reset PSL for new sizing
            
            size_t idx = _hmap_hash(entry.key) & map->mask;
            
            while (true) {
                if (map->entries[idx].psl == 0) {
                    map->entries[idx] = entry;
                    map->count++;
                    break;
                }
                
                // Robin Hood Swap
                if (entry.psl > map->entries[idx].psl) {
                    hmap_entry_t temp = map->entries[idx];
                    map->entries[idx] = entry;
                    entry = temp;
                }
                
                idx = (idx + 1) & map->mask;
                entry.psl++;
            }
        }
    }

    free(old_entries);
    return true;
}

/* * Insert or Update.
 * Returns 0 on success, -1 on allocation failure. 
 */
int hmap_put(hmap_t* map, int64_t key, void* value) {
    if (map->count >= map->threshold) {
        if (!_hmap_resize(map, map->capacity * 2)) {
            return -1;
        }
    }

    size_t idx = _hmap_hash(key) & map->mask;
    uint32_t current_psl = 1;
    
    hmap_entry_t entry_to_insert = { .key = key, .value = value, .psl = current_psl };

    while (true) {
        hmap_entry_t* curr = &map->entries[idx];

        // 1. Found empty slot: Insert
        if (curr->psl == 0) {
            *curr = entry_to_insert;
            map->count++;
            return 0;
        }

        // 2. Found existing key: Update value
        if (curr->key == key) {
            curr->value = value;
            return 0;
        }

        // 3. Robin Hood: Steal the slot if our probe length is richer (larger)
        if (entry_to_insert.psl > curr->psl) {
            hmap_entry_t temp = *curr;
            *curr = entry_to_insert;
            entry_to_insert = temp;
        }

        // Continue probing
        idx = (idx + 1) & map->mask;
        entry_to_insert.psl++;
    }
}

/* * Lookup.
 * Returns value if found, NULL if not found. 
 * Note: If you store NULL values, you need a different signature (bool return).
 */
void* hmap_get(hmap_t* map, int64_t key) {
    size_t idx = _hmap_hash(key) & map->mask;
    uint32_t current_psl = 1;

    while (true) {
        hmap_entry_t* curr = &map->entries[idx];

        // Slot is empty -> Key definitely not in map
        if (curr->psl == 0) {
            return NULL;
        }

        // Key matches
        if (curr->key == key) {
            return curr->value;
        }

        /* * Optimization (Early Exit):
         * If the current element has a smaller PSL than our current probe distance,
         * it means our key *would* have been here if it existed (because of the swap logic).
         * Since it's not here, it's nowhere.
         */
        if (curr->psl < current_psl) {
            return NULL;
        }

        idx = (idx + 1) & map->mask;
        current_psl++;
    }
}

/*
 * Remove a key.
 * Uses backward-shifting to maintain Robin Hood invariant without tombstones.
 * Returns true if removed, false if not found.
 */
bool hmap_remove(hmap_t* map, int64_t key) {
    size_t idx = _hmap_hash(key) & map->mask;
    uint32_t current_psl = 1;

    while (true) {
        hmap_entry_t* curr = &map->entries[idx];

        if (curr->psl == 0 || current_psl > curr->psl) {
            return false; // Not found
        }

        if (curr->key == key) {
            // Found it. Now backward shift to close the gap.
            map->count--;
            
            while (true) {
                size_t next_idx = (idx + 1) & map->mask;
                hmap_entry_t* next = &map->entries[next_idx];
                
                // Stop if next slot is empty or next item is at its ideal position (PSL 1)
                if (next->psl <= 1) {
                    map->entries[idx].psl = 0; // Mark current as empty
                    map->entries[idx].value = NULL;
                    map->entries[idx].key = 0;
                    break;
                }
                
                // Shift next item back into current slot
                map->entries[idx] = *next;
                map->entries[idx].psl--; // It's now closer to its home
                idx = next_idx;
            }
            return true;
        }

        idx = (idx + 1) & map->mask;
        current_psl++;
    }
}