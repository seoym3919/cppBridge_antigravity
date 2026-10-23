---
name: depointerize
description: Audits C/C++ raw pointers, pointer arithmetic, dynamic allocations (malloc/calloc/new), and out-parameters, converting them to safe NumPy arrays, slices, and Python return tuples.
disable-model-invocation: true
---

# /depointerize

Analyzes C/C++ pointer usage and translates low-level memory operations into safe, automatic Python garbage collection and NumPy memory models.

## Usage

Audit and convert pointers in a C/C++ file:
```text
/depointerize memory_kernel.c
```

## De-Pointerization Rules

1. **Heap Allocation**:
   - `type* ptr = (type*)malloc(n * sizeof(type));` -> `ptr = np.zeros(n, dtype=np.float64)`
   - `type* ptr = (type*)calloc(n, sizeof(type));` -> `ptr = np.zeros(n, dtype=np.float64)`
   - `type* ptr = new type[n];` -> `ptr = np.zeros(n, dtype=np.float64)`
   - `free(ptr);` and `delete[] ptr;` -> eliminated (Python GC).

2. **Pointer Arithmetic to Slicing**:
   - `*(ptr + i)` -> `ptr[i]`
   - `&arr[i]` -> `arr[i:]` (zero-copy array view)
   - `*ptr` -> `ptr[0]`

3. **Pass-by-Pointer Mutated Out Parameters**:
   - `void compute(double in, double* out1, double* out2)`
   - Transformed into clean multi-return: `return out1, out2`.
