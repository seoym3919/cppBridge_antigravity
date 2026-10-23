---
name: convert-cpp-to-python
description: Converts C/C++ codebases into vectorized scientific Python packages (NumPy/SciPy/Numba/Dataclasses) or pybind11 C-extensions.
---

# /convert-cpp-to-python

Translates entire C/C++ codebase directories, repositories, or individual source files into modern, typed Python using NumPy arrays, Python dataclasses, and vectorized expressions or native pybind11 C-extensions.
Bundled sub-skills live at `../<name>/SKILL.md` (`bind-pybind11`, `benchmark-cpp-python`, `decompile-printf`, `decompile-stl`, `depointerize`, `link-cpp-project`, `modernize-boost`, `modernize-linalg`, `struct-to-dataclass`, `transpile-openmp`, `vectorize-loops`, `verify-cpp-python`).

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
4. **Hybrid Static + Semantic LLM Code Synthesis**:
   - Run `scripts/cpp_bridge_cli.py` to generate the topological Python package scaffold (`__init__.py`) or `pybind11` module (`bindings.cpp` + `setup.py`), `@dataclass` / `np.dtype` models, and pointer hazard reports.
   - Refine complex mathematical kernels semantically (via `cpp-to-python-architect` on Opus 5.5 / Sonnet 5.5 / Gemini 4) rather than relying solely on regex line-by-line transpilation, replacing scalar loops with vectorized NumPy/SciPy or `@njit(parallel=True)` (`prange`) kernels.
5. **Package Generation & Closed-Loop Verification**:
   Emit `CODEBASE_TRANSLATION_REPORT.md` and verify $L_2 < 10^{-12}$ numerical equivalence against the C/C++ reference via `scripts/cpp_python_verifier.py`.
