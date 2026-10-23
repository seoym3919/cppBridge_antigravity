---
name: transpile-openmp
description: Decompiles C/C++ OpenMP multithreading pragmas (#pragma omp parallel for, critical, atomic) into Python Numba prange and multithreaded runtime routines.
---

# /transpile-openmp

Translates shared-memory OpenMP directives from C and C++ codes into multithreaded Python using Numba `@njit(parallel=True)` with `numba.prange` or Python `threading` / `multiprocessing` constructs.

## Usage

Decompile OpenMP pragmas in a file:
```text
/transpile-openmp parallel_solver.cpp
```

## Supported Pragmas

| C/C++ OpenMP Directive | Modern Python / Numba Representation |
|---|---|
| `#pragma omp parallel for` | `@njit(parallel=True)` + `for i in prange(n):` |
| `#pragma omp critical` | `with _omp_lock:` (`threading.Lock()`) |
| `#pragma omp atomic` | Atomic in-place updates |
| `omp_get_thread_num()` | `numba.get_thread_id()` |
| `omp_get_num_threads()` | `numba.get_num_threads()` |
