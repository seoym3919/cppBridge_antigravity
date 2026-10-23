# cppBridge Antigravity Directives

1. **Subagent Routing**:
   - Master C/C++ translation & architecture: `invoke_subagent` (`TypeName`: `"cpp-to-python-architect"`, `Model`: `"pro"`).
   - NumPy array vectorization & loop optimization: `invoke_subagent` (`TypeName`: `"numpy-vectorizer"`, `Model`: `"flash"`).
   - Memory de-pointerization & slice safety: `invoke_subagent` (`TypeName`: `"memory-de-pointer"`, `Model`: `"flash"`).
   - Struct & class modernizer (Dataclasses, OOP): `invoke_subagent` (`TypeName`: `"oop-modernizer"`, `Model`: `"flash"`).

2. **Translation & Porting Standards**:
   - **Directory-First & Codebase-Wide Scope**: `cppBridge` operates on directories and whole codebases by default. It recursively discovers all C/C++ source and header files, constructs the internal `#include` dependency DAG, topologically sorts translation order, and emits fully structured Python packages (with `__init__.py`) or native pybind11 C-extensions (with `setup.py`).
   - **Pointer Elimination**: Convert raw pointers (`T*`, `malloc`, `new[]`) into NumPy arrays (`np.ndarray`) and slices. Never keep raw address manipulation or integer pointer casts in Python.
   - **Dataclass Encapsulation**: Map C `struct` and `typedef struct` directly into Python `@dataclass` models and companion NumPy `np.dtype` structured arrays.
   - **Loop Vectorization**: Replace scalar array element loops with single-instruction NumPy vector expressions (`a * b + c`). For complex recurrences that cannot be vectorized, use Numba `@njit`.
   - **OpenMP Parallelization**: Modernize `#pragma omp parallel for` into `@njit(parallel=True)` with `numba.prange`.
   - **C++ STL Containers**: Map `std::vector<double>` to 1D contiguous NumPy arrays or typed Python lists, `std::map` to `dict`, `std::pair` to `tuple`, and methods (`.push_back()` $\to$ `.append()`, `.size()` $\to$ `len()`).
   - **Linear Algebra**: Standardize BLAS (`dgemm`, `ddot`, `dnrm2`) and C++ Eigen (`MatrixXd`, `Vector3d`, `.cross()`, `.solve()`) into `numpy.linalg` and `scipy.linalg`. Respect numerical stability: never use explicit matrix inversion (`inv(A) @ b`); always use `np.linalg.solve(A, b)`.
   - **Boost Libraries**: Modernize `boost::math` special functions (Bessel, Gamma, erf, Legendre, Beta) into `scipy.special`, `boost::multi_array` into `np.ndarray`, and `boost::random` into `np.random.default_rng()`.
   - **Format String Modernization**: Transform all `printf`, `sprintf`, `fprintf`, and `std::cout` statements into Python 3 f-strings with matching width and precision specifiers.
   - **Closed-Loop Verification**: Always verify translated code with `scripts/cpp_python_verifier.py` to confirm mathematical output equivalence ($L_2 < 10^{-12}$).
