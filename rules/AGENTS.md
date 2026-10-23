# cppBridge Directives

1. **Directory-First Scope**: Translate entire C/C++ directories/codebases by default via `python3 ~/.gemini/config/plugins/cppbridge/scripts/cpp_bridge_cli.py <dir> [--pybind11 --module-name <name>] --out-dir <out>`. Delegate multi-file porting to `cpp-to-python-architect` (`Model: "pro"`).
2. **Modernization Standards**: Convert raw pointers (`T*`, `malloc`, `new[]`) to NumPy arrays/slices, C structs/classes to `@dataclass` + `np.dtype`, scalar loops to vectorized NumPy or `@njit(parallel=True)` (`prange` for OpenMP), and Eigen/BLAS/Boost.Math to `numpy.linalg`/`scipy.linalg`/`scipy.special`.
3. **Closed-Loop Verification**: Verify numerical equivalence ($L_2 < 10^{-12}$) against C/C++ reference outputs via `scripts/cpp_python_verifier.py`.
