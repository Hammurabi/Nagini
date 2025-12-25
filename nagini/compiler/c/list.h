#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    void** data;      // Array of pointers to values
    size_t capacity;  // Allocated slots
    size_t size;      // Currently used slots
} list_t;

/* Initialize a new list */
list_t* list_create(size_t initial_capacity) {
    list_t* list = (list_t*)malloc(sizeof(list_t));
    if (!list) return NULL;

    if (initial_capacity == 0) initial_capacity = 4;
    
    list->data = (void**)malloc(sizeof(void*) * initial_capacity);
    if (!list->data) {
        free(list);
        return NULL;
    }

    list->capacity = initial_capacity;
    list->size = 0;
    return list;
}

/* Internal: Resize the list capacity */
static bool _list_resize(list_t* list, size_t new_capacity) {
    void** new_data = (void**)realloc(list->data, sizeof(void*) * new_capacity);
    if (!new_data) return false;

    list->data = new_data;
    list->capacity = new_capacity;
    return true;
}

/* Append: O(1) Amortized */
int list_append(list_t* list, void* value) {
    if (list->size >= list->capacity) {
        // Double the capacity
        if (!_list_resize(list, list->capacity * 2)) return -1;
    }
    list->data[list->size++] = value;
    return 0;
}

/* Find: O(n) 
 * Returns the index of the first occurrence, or -1 if not found.
 */
int64_t list_find(list_t* list, void* value) {
    for (size_t i = 0; i < list->size; i++) {
        if (list->data[i] == value) {
            return (int64_t)i;
        }
    }
    return -1;
}

/* Remove: O(n) 
 * Removes the element at index and shifts subsequent elements left.
 */
void* list_remove(list_t* list, size_t index) {
    if (index >= list->size) return NULL;

    void* removed_value = list->data[index];

    // Shift elements after index to the left
    size_t num_to_move = list->size - index - 1;
    if (num_to_move > 0) {
        memmove(&list->data[index], &list->data[index + 1], sizeof(void*) * num_to_move);
    }

    list->size--;
    
    // Optional: Shrink if size is 1/4 of capacity to save memory
    if (list->size > 0 && list->size <= list->capacity / 4 && list->capacity > 4) {
        _list_resize(list, list->capacity / 2);
    }

    return removed_value;
}

/* Add: O(m) 
 * Appends all elements from 'other' list to 'list'.
 */
int list_add_list(list_t* list, list_t* other) {
    size_t required_size = list->size + other->size;
    
    if (required_size > list->capacity) {
        // Ensure we have enough space in one resize
        size_t new_cap = list->capacity;
        while (new_cap < required_size) new_cap *= 2;
        if (!_list_resize(list, new_cap)) return -1;
    }

    // Bulk copy pointers
    memcpy(&list->data[list->size], other->data, sizeof(void*) * other->size);
    list->size += other->size;
    return 0;
}

void list_destroy(list_t* list) {
    if (list) {
        free(list->data);
        free(list);
    }
}