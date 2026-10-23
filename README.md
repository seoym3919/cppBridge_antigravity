# cppBridge: C/C++ to Scientific Python Modernization Engine

[![Antigravity Plugin](https://img.shields.io/badge/Antigravity-Plugin%20v0.2.0-blue.svg)](https://github.com/seoym3919/cppBridge_antigravity)
[![Agent Plugins 1.0.0](https://img.shields.io/badge/Agent%20Plugins-1.0.0%20Compliant-brightgreen.svg)](https://agent-plugins.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**cppBridge** is an Antigravity plugin engineered to **translate and modernize legacy and modern C/C++ (C89, C99, C11, C++11, C++17, C++20) scientific algorithms and systems code into idiomatic, vectorized scientific Python (NumPy, SciPy, Numba, Dataclasses) or accelerated pybind11 C-extensions.**

It automates the most complex aspects of C/C++ to Python migration:
- **Raw Pointer De-Pointerization**: `malloc`, `calloc`, and `new[]` $\to$ `np.zeros` / `np.empty`.
- **Pointer Arithmetic Decompilation**: `*(ptr + i)` $\to$ `ptr[i]`, `&arr[i]` $\to$ `arr[i:]`.
- **Struct & Class Modernization**: C `struct` and C++ `class` $\to$ `@dataclass` + contiguous `np.dtype`.
- **OpenMP Multithreading**: `#pragma omp parallel for` $\to$ `@njit(parallel=True)` + `numba.prange`.
- **C++ STL Containers**: `std::vector`, `std::array`, `std::map`, `std::pair` $\to$ NumPy / Python native types.
- **Linear Algebra**: BLAS (`dgemm`, `ddot`, `dnrm2`), LAPACK (`dgesv`), and Eigen (`MatrixXd`, `Vector3d`, `.solve()`) $\to$ `numpy.linalg` / `scipy.linalg`.
- **Boost C++ Libraries**: `boost::math` special functions $\to$ `scipy.special`, `boost::multi_array` $\to$ `np.ndarray`, `boost::random` $\to$ `np.random`.
- **Formatted I/O Decompilation**: `printf`, `sprintf`, `fprintf`, and `std::cout` $\to$ Python 3 f-strings.
- **Multi-File Include Linker**: DAG include dependency analysis, topological sort, and `__init__.py` generation.
- **Closed-Loop Verification**: Validating equivalence within machine precision ($L_2 < 10^{-12}$).

---

## Architecture & Translation Pipeline

```
   C / C++ Source (C89 / C99 / C11 / C++11 / C++17 / C++20)
              │
              ├──► [cpp_to_python_transpiler] ──► AST, Function Headers & Control Flow
              │
              ├──► [pointer_analyzer]         ──► malloc/calloc/new[] -> np.zeros / np.empty
              │                                   *(ptr + i) -> ptr[i], &arr[i] -> arr[i:]
              │
              ├──► [struct_transpiler]        ──► struct / class -> @dataclass & np.dtype
              │
              ├──► [openmp_transpiler]        ──► #pragma omp -> @njit(parallel=True) + prange
              │
              ├──► [stl_decompiler]           ──► std::vector/map/pair -> NumPy / dict / tuple
              │
              ├──► [linalg_modernizer]        ──► BLAS / LAPACK / Eigen -> numpy.linalg
              │
              ├──► [boost_modernizer]         ──► boost::math/multi_array -> scipy.special
              │
              ├──► [loop_vectorizer_engine]   ──► Scalar loops -> Vectorized NumPy / Numba
              │
              ├──► [header_linker]            ──► #include DAG Linker & Python Package Generator
              │
              ├──► [pybind11_generator]       ──► Native C++ Pybind11 Zero-Copy NumPy Wrappers
              │
              ├──► [cpp_python_benchmarker]   ──► Scalar vs. NumPy vs. Numba Performance Profiler
              │
              ├──► [cpp_python_verifier]      ──► Closed-Loop Equivalence: L_2, L_inf < 1e-12
              │
              └──► Modern Scientific Python Module (.py) / Native C-Extension (.so)
```

---

## Specialized Subagents

| Subagent | Recommended Model | Primary Role |
|---|---|---|
| [`cpp-to-python-architect`](./agents/cpp-to-python-architect.md) | `Model: "pro"` (`claude-opus-4-6-thinking`) | Lead translation architect. Directs codebase decomposition, determines pure Python vs. pybind11 pathways, and coordinates subagents. |
| [`numpy-vectorizer`](./agents/numpy-vectorizer.md) | `Model: "flash"` (`gemini-3.8-flash-high`) | Scientific Python optimization specialist. Replaces scalar loops with NumPy vector operations, broadcasting, and Numba JIT kernels. |
| [`memory-de-pointer`](./agents/memory-de-pointer.md) | `Model: "flash"` (`gemini-3.8-flash-high`) | Memory safety specialist. Audits raw pointers, converts heap allocations to NumPy, and eliminates dangling memory hazards. |
| [`oop-modernizer`](./agents/oop-modernizer.md) | `Model: "flash"` (`gemini-3.8-flash-high`) | Object-oriented modernizer. Converts structs, unions, and classes into Python `@dataclass` models and structured `np.dtype` arrays. |

---

## Skills & Slash Commands (13 Skills)

1. **`/convert-cpp-to-python`**: Master translation command for C/C++ files.
2. **`/depointerize`**: Audits pointer allocations, dereferences, and slice views.
3. **`/vectorize-loops`**: Eliminates scalar loops and maps element-wise mutations to NumPy / Numba.
4. **`/struct-to-dataclass`**: Converts structs and classes into Python `@dataclass` and `np.dtype`.
5. **`/transpile-openmp`**: Converts `#pragma omp parallel for` into Numba `prange`.
6. **`/decompile-stl`**: Maps `std::vector`, `std::map`, and STL algorithms to Python / NumPy.
7. **`/modernize-linalg`**: Maps BLAS/LAPACK and Eigen to `numpy.linalg` and `scipy.linalg`.
8. **`/modernize-boost`**: Maps `boost::math`, `boost::multi_array`, and `boost::random` to SciPy / NumPy.
9. **`/link-cpp-project`**: Analyzes multi-file include DAGs and generates Python packages.
10. **`/decompile-printf`**: Converts `printf`, `sprintf`, `fprintf`, and `std::cout` to f-strings.
11. **`/bind-pybind11`**: Generates zero-copy `pybind11` C++ wrappers and `setup.py`.
12. **`/benchmark-cpp-python`**: Measures speedups across scalar Python, NumPy, and Numba JIT.
13. **`/verify-cpp-python`**: Asserts continuous numerical output equivalence ($L_2 < 10^{-12}$).

---

## CLI Usage

```bash
# Run full 12-subsystem test suite
python3 scripts/cpp_bridge_cli.py --self-test

# Transpile C code to Python with full modernization report
python3 scripts/cpp_bridge_cli.py -i examples/nbody_simulation.c -o examples/nbody_simulation.py --report examples/translation_report.md

# Generate pybind11 native wrapper and setup.py
python3 scripts/cpp_bridge_cli.py -i examples/nbody_simulation.c --pybind11 --module-name nbody_native

# Link a multi-file C/C++ project into a Python package
python3 scripts/cpp_bridge_cli.py --link /path/to/cpp_project

# Run performance micro-benchmarks
python3 scripts/cpp_bridge_cli.py --benchmark

# Run closed-loop numerical verifier
python3 scripts/cpp_python_verifier.py --self-test
```

---

## Installation & Strict Validation

```bash
# Strict validation (Agent Plugins 1.0.0)
agy plugin validate /path/to/cppBridge_antigravity --strict

# Install globally
agy plugin install /path/to/cppBridge_antigravity
```

---

## License

MIT License. Designed and maintained by `seoym3919` as part of the Antigravity scientific ecosystem alongside `scienceStack`, `theoryReverse`, and `fortranBridge`.
