---
name: modernize-linalg
description: Translates BLAS, LAPACK, and C++ Eigen linear algebra calls (dgemm, ddot, MatrixXd, cross, dot, solve) into vectorized numpy.linalg and scipy.linalg operations.
---

# /modernize-linalg

Modernizes dense linear algebra routines from classic BLAS/LAPACK and C++ Eigen template libraries into high-throughput NumPy and SciPy expressions.

## Usage

Modernize linear algebra calls:
```text
/modernize-linalg eigensolver.cpp
```

## Linear Algebra Mappings

1. **Eigen Matrix & Vector Operations**:
   - `MatrixXd`, `Vector3d` $\to$ `np.ndarray`
   - `m.transpose()` $\to$ `m.T`
   - `v.cross(w)` $\to$ `np.cross(v, w)`
   - `v.dot(w)` $\to$ `np.dot(v, w)`
   - `v.norm()` $\to$ `np.linalg.norm(v)`
   - `A.colPivHouseholderQr().solve(b)` $\to$ `np.linalg.solve(A, b)`
   - `A.inverse() * b` $\to$ `np.linalg.solve(A, b)` *(enforcing numerical stability)*

2. **BLAS / LAPACK Routines**:
   - `cblas_dgemm` $\to$ `C = alpha * (A @ B) + beta * C`
   - `cblas_ddot` $\to$ `np.dot(x, y)`
   - `cblas_dnrm2` $\to$ `np.linalg.norm(x)`
   - `cblas_dgesv` $\to$ `np.linalg.solve(A, b)`
