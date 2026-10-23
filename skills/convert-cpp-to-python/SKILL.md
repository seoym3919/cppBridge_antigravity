---
name: convert-cpp-to-python
description: Master translation command to convert legacy and modern C/C++ codebases, directories, or files into idiomatic scientific Python with NumPy, SciPy, and Dataclasses.
---

# /convert-cpp-to-python

Translates entire C/C++ codebase directories, repositories, or individual source files into modern, typed Python using NumPy arrays, Python dataclasses, and vectorized expressions or native pybind11 C-extensions.

## Usage

Modernize an entire C/C++ codebase directory to a Python package:
```text
/convert-cpp-to-python [directory] --out-dir modernized_pkg
```

Modernize an entire C/C++ codebase directory to pybind11 native extensions:
```text
/convert-cpp-to-python [directory] --pybind11 --module-name my_native_pkg
```

Translate an individual C/C++ file:
```text
/convert-cpp-to-python solver.c --out solver.py --report report.md
```

## Codebase Workflow

1. **Directory-Wide Ingestion & Header Linker**:
   Recursively discovers all `.c`, `.cpp`, `.cc`, `.h`, and `.hpp` files across the codebase directory.
2. **Multi-File Topological Dependency DAG**:
   Builds the `#include` Directed Acyclic Graph via `scripts/header_linker.py`, ensuring header structures and core types are transpiled before numerical kernels and solvers.
3. **Automated De-Pointerization & Memory Architecture**:
   Replaces `malloc`, `calloc`, and `new[]` with contiguous `np.zeros` or `np.empty` buffers via `scripts/pointer_analyzer.py`.
4. **Compound Type Modernization**:
   Transforms C `struct` and C++ `class` models into Python `@dataclass` classes and companion `np.dtype` definitions.
5. **Package Generation & Verification**:
   Generates a structured Python package with `__init__.py` and emits `CODEBASE_TRANSLATION_REPORT.md`. Verifies numerical equivalence via `scripts/cpp_python_verifier.py`.
