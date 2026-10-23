# cppBridge: C/C++ to Scientific Python Modernization Engine

[![Antigravity Plugin](https://img.shields.io/badge/Antigravity-Plugin%20v0.2.0-blue.svg)](https://github.com/seoym3919/cppBridge_antigravity)
[![Agent Plugins 1.0.0](https://img.shields.io/badge/Agent%20Plugins-1.0.0%20Compliant-brightgreen.svg)](https://agent-plugins.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**cppBridge** is an Antigravity plugin engineered to **translate and modernize legacy and modern C/C++ codebases, directories, and routines (C89, C99, C11, C++11, C++17, C++20) into idiomatic, vectorized scientific Python (NumPy, SciPy, Numba, Dataclasses) or accelerated pybind11 C-extensions.**

It operates on entire codebase directories by default, automating the most complex aspects of C/C++ to Python migration:
- **Directory-Wide Include DAG Linking**: Resolves internal `#include` dependencies and generates complete Python packages (`__init__.py`).
- **Raw Pointer De-Pointerization**: `malloc`, `calloc`, and `new[]` $\to$ `np.zeros` / `np.empty`.
- **Pointer Arithmetic Decompilation**: `*(ptr + i)` $\to$ `ptr[i]`, `&arr[i]` $\to$ `arr[i:]`.
- **Struct & Class Modernization**: C `struct` and C++ `class` $\to$ `@dataclass` + contiguous `np.dtype`.
- **OpenMP Multithreading**: `#pragma omp parallel for` $\to$ `@njit(parallel=True)` + `numba.prange`.
- **C++ STL Containers**: `std::vector`, `std::array`, `std::map`, `std::pair` $\to$ NumPy / Python native types.
- **Linear Algebra**: BLAS (`dgemm`, `ddot`, `dnrm2`), LAPACK (`dgesv`), and Eigen (`MatrixXd`, `Vector3d`, `.solve()`) $\to$ `numpy.linalg` / `scipy.linalg`.
- **Boost C++ Libraries**: `boost::math` special functions $\to$ `scipy.special`, `boost::multi_array` $\to$ `np.ndarray`, `boost::random` $\to$ `np.random`.
- **Formatted I/O Decompilation**: `printf`, `sprintf`, `fprintf`, and `std::cout` $\to$ Python 3 f-strings.
- **Closed-Loop Verification**: Validating equivalence within machine precision ($L_2 < 10^{-12}$).

---

## 1. Installation & How to Use

### Installation

Install `cppBridge` globally or locally in Google Antigravity:

```bash
# 1. Validate compliance with Agent Plugins 1.0.0 (Strict mode)
agy plugin validate /home/seo3919/AI_skills/cppBridge_antigravity --strict

# 2. Install globally in Antigravity
agy plugin install /home/seo3919/AI_skills/cppBridge_antigravity

# Or install from GitHub:
# agy plugin install seoym3919/cppBridge_antigravity
```

Verify installation status:
```bash
agy plugin list
# - cppbridge (enabled, 0.2.0)
#   Components: 13 skills, 4 agents, 1 rule
```

---

### How to Use

#### Method A: Interactive Slash Commands in Antigravity

In the Antigravity chat, interact directly with C/C++ modernization skills targeting directories or files:

| Command | Action & Modernization Capability | Example Prompt |
| :--- | :--- | :--- |
| **`/convert-cpp-to-python`** | **Master codebase-wide command**: translates an entire C/C++ directory or file into a structured Python package with full reports. | `/convert-cpp-to-python [directory] --out-dir modernized_pkg` |
| **`/link-cpp-project`** | Analyzes `#include` DAGs, computes topological build order, and generates a packaged Python library. | `/link-cpp-project /path/to/cpp_src/` |
| **`/bind-pybind11`** | Generates zero-copy C++ `pybind11` extension wrappers (`py::array_t`) and `setup.py` across codebase. | `/bind-pybind11 src/ --module-name native_solver` |
| **`/depointerize`** | Audits raw pointers (`malloc`, `free`, `*ptr`) and converts them to safe NumPy arrays and slices. | `/depointerize src/` |
| **`/vectorize-loops`** | Converts scalar for-loops and mutations into vectorized NumPy expressions or Numba `@njit`. | `/vectorize-loops src/kernels/` |
| **`/struct-to-dataclass`** | Converts C structs and C++ classes into Python `@dataclass` models and companion `np.dtype`. | `/struct-to-dataclass include/types.h` |
| **`/transpile-openmp`** | Maps `#pragma omp parallel for` directly into `@njit(parallel=True)` with `numba.prange`. | `/transpile-openmp src/` |
| **`/decompile-stl`** | Maps STL containers (`vector`, `array`, `map`, `pair`) and algorithms to Python/NumPy. | `/decompile-stl src/` |
| **`/modernize-linalg`** | Maps BLAS/LAPACK and Eigen matrix routines to `numpy.linalg` and `scipy.linalg`. | `/modernize-linalg src/math/` |
| **`/modernize-boost`** | Maps `boost::math` special functions and `boost::multi_array` to SciPy and NumPy. | `/modernize-boost src/special_functions/` |
| **`/decompile-printf`** | Converts `printf`, `sprintf`, `fprintf`, and `std::cout` chains into Python 3 f-strings. | `/decompile-printf src/logger.cpp` |
| **`/benchmark-cpp-python`** | Measures speedups and benchmarks scalar Python vs. vectorized NumPy vs. Numba JIT. | `/benchmark-cpp-python solver.py` |
| **`/verify-cpp-python`** | Closed-loop equivalence tester asserting output differences satisfy $L_2, L_\infty < 10^{-12}$. | `/verify-cpp-python solver.c solver.py` |

#### Method B: Subagent Autonomous Orchestration

Antigravity automatically delegates tasks across 4 specialized subagents:
- **`cpp-to-python-architect`** (`Model: "pro"`): Master translation coordinator. Ingests entire directories, coordinates multi-file DAG linking, and oversees architecture.
- **`numpy-vectorizer`** (`Model: "flash"`): High-performance NumPy array vectorization and Numba specialist.
- **`memory-de-pointer`** (`Model: "flash"`): Memory de-pointerization and slice-safety specialist.
- **`oop-modernizer`** (`Model: "flash"`): Struct, class, and data model modernizer.

#### Method C: Standalone Zero-Token CLI (Offline Execution)

Modernize codebases directly in your terminal at zero LLM token cost:

```bash
# 1. Modernize entire C/C++ codebase directory into structured Python package
python3 scripts/cpp_bridge_cli.py /path/to/cpp_repo

# 2. Modernize entire codebase to native pybind11 extension module with zero-copy NumPy buffers
python3 scripts/cpp_bridge_cli.py /path/to/cpp_repo --pybind11 --module-name my_native_pkg

# 3. Modernize an individual C/C++ file with modernization report
python3 scripts/cpp_bridge_cli.py -i examples/nbody_simulation.c -o examples/nbody_simulation.py --report examples/translation_report.md

# 4. Analyze multi-file include DAG and build topological sequence
python3 scripts/header_linker.py /path/to/cpp_project

# 5. Run full 12-subsystem verification suite
python3 scripts/cpp_bridge_cli.py --self-test
```

---

## 2. Architecture & Translation Pipeline

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

## 3. Specialized Subagents

| Subagent | Recommended Model | Primary Role |
|---|---|---|
| [`cpp-to-python-architect`](./agents/cpp-to-python-architect.md) | `Model: "pro"` (`claude-opus-4-6-thinking`) | Lead translation architect. Directs codebase decomposition, determines pure Python vs. pybind11 pathways, and coordinates subagents. |
| [`numpy-vectorizer`](./agents/numpy-vectorizer.md) | `Model: "flash"` (`gemini-3.8-flash-high`) | Scientific Python optimization specialist. Replaces scalar loops with NumPy vector operations, broadcasting, and Numba JIT kernels. |
| [`memory-de-pointer`](./agents/memory-de-pointer.md) | `Model: "flash"` (`gemini-3.8-flash-high`) | Memory safety specialist. Audits raw pointers, converts heap allocations to NumPy, and eliminates dangling memory hazards. |
| [`oop-modernizer`](./agents/oop-modernizer.md) | `Model: "flash"` (`gemini-3.8-flash-high`) | Object-oriented modernizer. Converts structs, unions, and classes into Python `@dataclass` models and structured `np.dtype` arrays. |

---

## 4. License

MIT License. Designed and maintained by `seoym3919` as part of the Antigravity scientific ecosystem alongside `scienceStack`, `theoryReverse`, and `fortranBridge`.
