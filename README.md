# cppBridge: C/C++ to Scientific Python Modernization Engine

[![Antigravity Plugin](https://img.shields.io/badge/Antigravity-Plugin%20v0.1.0-blue.svg)](https://github.com/seoym3919/cppBridge_antigravity)
[![Agent Plugins 1.0.0](https://img.shields.io/badge/Agent%20Plugins-1.0.0%20Compliant-brightgreen.svg)](https://agent-plugins.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**cppBridge** is an Antigravity plugin engineered to **translate and modernize legacy and modern C/C++ (C89, C99, C11, C++11, C++17, C++20) scientific algorithms and systems code into idiomatic, vectorized scientific Python (NumPy, SciPy, Numba, Dataclasses) or accelerated pybind11 C-extensions.**

It automates the most tedious and error-prone aspects of C/C++ to Python migration: **raw pointer de-pointerization (`malloc`, `calloc`, `new[]` -> NumPy arrays), pointer arithmetic deconstruction (`*(ptr + i)` -> `ptr[i]`, `&arr[i]` -> `arr[i:]`), struct and class encapsulation into Python `@dataclass` models and contiguous `np.dtype` structured arrays, formatted I/O decompilation (`printf`, `std::cout` -> Python 3 f-strings), and closed-loop floating-point equivalence verification ($L_2 < 10^{-12}$).**

---

## The Challenge of C/C++ Modernization

Scientific computing, orbital dynamics, numerical linear algebra, and computational physics contain millions of lines of legacy C and C++ code. Porting this code manually to Python introduces subtle bugs:
- **Pointer Arithmetic & Buffer Overflows**: C code relies heavily on raw pointers (`double* pos`), pointer increments (`ptr++`), and manual memory buffers (`malloc`/`free`). In Python, these must map cleanly to bounded NumPy arrays and zero-copy views.
- **Output Parameters via Pointers**: C functions frequently return multiple results through pointer arguments (`void solve(double in, double* out1, double* out2)`). In Python, these should be idiomatic return tuples.
- **Scalar Iteration Overhead**: Translating C `for` loops directly to Python `for` loops results in a 50x-200x slowdown. Loops must be vectorized with NumPy or compiled via Numba/pybind11.
- **Complex Structs & Objects**: C `typedef struct` and C++ `class` definitions need clean representation as modern `@dataclass` objects and companion NumPy dtypes for array-of-structures operations.
- **I/O Formatting Rot**: Decades of `printf` and `std::cout` stream expressions must be converted into clean, maintainable Python f-strings.

**cppBridge automates and solves each of these challenges.**

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
              ├──► [printf_decompiler]        ──► printf / cout -> Python 3 f-Strings
              │
              ├──► [pybind11_generator]       ──► Native C++ Pybind11 Zero-Copy NumPy Wrappers
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

## Skills & Slash Commands

### 1. Master Translation: `/convert-cpp-to-python`
Translates an entire C/C++ source file or routine into modern, typed Scientific Python:
```bash
/convert-cpp-to-python solver.c --out solver.py --report report.md
```

### 2. De-Pointerization: `/depointerize`
Audits pointer allocations, dereferences, and slice views:
```bash
/depointerize memory_kernel.c
```

### 3. Loop Vectorization: `/vectorize-loops`
Eliminates scalar iteration and maps element-wise mutations to NumPy / Numba:
```bash
/vectorize-loops loop_kernel.cpp
```

### 4. Struct & Dataclass Modernization: `/struct-to-dataclass`
Converts C `struct`, `typedef struct`, and C++ `class` to Python `@dataclass` and `np.dtype`:
```bash
/struct-to-dataclass types.h
```

### 5. Format Decompiler: `/decompile-printf`
Converts `printf`, `sprintf`, `fprintf`, and `std::cout` to Python f-strings:
```bash
/decompile-printf format_strings.c
```

### 6. Turnkey pybind11 Generator: `/bind-pybind11`
Generates zero-copy NumPy array wrappers (`py::array_t`) and `setup.py` for compiled execution speed:
```bash
/bind-pybind11 solver.h --module-name solver_native
```

### 7. Closed-Loop Numerical Verifier: `/verify-cpp-python`
Asserts continuous numerical output equivalence within machine precision:
```bash
/verify-cpp-python --ref ref_c_output.npy --test py_output.npy --tol 1e-12
```

---

## CLI Usage

The plugin provides a standalone, zero-dependency CLI driver:

```bash
# Run full self-test suite across all subsystems
python3 scripts/cpp_bridge_cli.py --self-test

# Transpile C code to Python with full report
python3 scripts/cpp_bridge_cli.py -i examples/nbody_simulation.c -o examples/nbody_simulation.py --report examples/translation_report.md

# Generate pybind11 native wrapper and setup.py
python3 scripts/cpp_bridge_cli.py -i examples/nbody_simulation.c --pybind11 --module-name nbody_native

# Run closed-loop numerical verifier
python3 scripts/cpp_python_verifier.py --self-test
```

---

## Installation

### In Antigravity CLI
Install directly into your global Antigravity plugins directory:
```bash
agy plugin install /path/to/cppBridge_antigravity
# or via GitHub
agy plugin install https://github.com/seoym3919/cppBridge_antigravity
```

### Verification
Verify that the plugin is strictly compliant with the Agent Plugins 1.0.0 specification:
```bash
agy plugin validate /path/to/cppBridge_antigravity --strict
```

---

## License

MIT License. Designed and maintained by `seoym3919` as part of the Antigravity scientific ecosystem alongside `scienceStack`, `theoryReverse`, and `fortranBridge`.
