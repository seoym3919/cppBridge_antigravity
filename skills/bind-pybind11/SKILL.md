---
name: bind-pybind11
description: Generates turnkey pybind11 C++ extension wrappers and setup.py with zero-copy NumPy array support (py::array_t) for high-performance native execution.
disable-model-invocation: true
---

# /bind-pybind11

Generates native C++ `pybind11` binding files and turnkey `setup.py` build scripts for C/C++ scientific kernels, enabling direct compilation into Python C-extension modules with zero-copy NumPy buffer integration.

## Usage

Generate pybind11 wrapper:
```text
/bind-pybind11 solver.h --module-name solver_native
```

Compile the generated extension:
```bash
pip install .
# or
python3 setup.py build_ext --inplace
```

## Features

- **Zero-Copy NumPy Arrays**: Maps raw C pointers (`double*`) to `py::array_t<double>` with `unchecked<1>()` (const) or `mutable_unchecked<1>()` (mutable).
- **Turnkey `setup.py`**: Configured with `-O3 -march=native -std=c++20`.
- **Dual Speed Path**: Allows scientists to choose between pure Python or maximum compiled speed.
