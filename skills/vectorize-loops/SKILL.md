---
name: vectorize-loops
description: Transforms scalar C/C++ loops and array mutations into vectorized NumPy expressions, SciPy operations, and Numba JIT accelerated kernels.
disable-model-invocation: true
---

# /vectorize-loops

Transforms slow scalar iteration patterns from C/C++ into high-speed vectorized NumPy operations and Numba JIT compiled kernels.

## Usage

Transform loop constructs:
```text
/vectorize-loops loop_kernel.cpp
```

## Vectorization Patterns

1. **Element-wise Arithmetic**:
   ```c
   for (int i = 0; i < n; ++i) {
       y[i] = a * x[i] + y[i];
   }
   ```
   Vectorizes to:
   ```python
   y = a * x + y
   ```

2. **Reduction Operations**:
   ```c
   double sum = 0.0;
   for (int i = 0; i < n; ++i) {
       sum += arr[i] * arr[i];
   }
   ```
   Vectorizes to:
   ```python
   sum_val = np.sum(arr ** 2)
   ```

3. **Complex Recurrences (Numba JIT)**:
   For state-dependent loop recurrences that cannot be expressed as NumPy primitives, emits:
   ```python
   import numba

   @numba.njit(fastmath=True, nogil=True)
   def kernel(arr: np.ndarray) -> np.ndarray:
       ...
   ```
