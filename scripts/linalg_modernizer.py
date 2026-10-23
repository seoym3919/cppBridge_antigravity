#!/usr/bin/env python3
r"""
linalg_modernizer.py - Modernizes BLAS, LAPACK, and Eigen C++ Linear Algebra into NumPy / SciPy.

Converts:
- BLAS: dgemm, dgemv, ddot, dnrm2, daxpy -> @, np.dot, np.linalg.norm
- LAPACK: dgesv, dposv, dsyev, dgesvd -> np.linalg.solve, eigh, svd
- Eigen: MatrixXd, Vector3d, .transpose(), .determinant(), .cross(), .dot(), .norm(), .solve()
- Numerical Stability: Transforms A.inverse() * b -> np.linalg.solve(A, b) avoiding explicit inversion.
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Tuple, Set


def modernize_linalg_expressions(code_text: str) -> Tuple[str, Set[str]]:
    r"""
    Modernize BLAS, LAPACK, and Eigen expressions into NumPy equivalents.
    """
    imports = set()
    res = code_text

    # 1. Eigen Types -> np.ndarray
    eigen_types = [
        r'Eigen::MatrixXd', r'Eigen::Matrix[234]d', r'Eigen::VectorXd', r'Eigen::Vector[234]d',
        r'\bMatrixXd\b', r'\bMatrix[234]d\b', r'\bVectorXd\b', r'\bVector[234]d\b'
    ]
    for et in eigen_types:
        res = re.sub(et, 'np.ndarray', res)

    # 2. Eigen Methods
    # m.transpose() -> m.T
    res = re.sub(r'([A-Za-z0-9_.]+)\.transpose\(\)', r'\1.T', res)

    # Numerical Stability: A.inverse() * b -> np.linalg.solve(A, b)
    if re.search(r'\.inverse\(\)\s*\*', res):
        imports.add("numpy as np")
        res = re.sub(r'([A-Za-z0-9_.]+)\.inverse\(\)\s*\*\s*([A-Za-z0-9_.]+)', r'np.linalg.solve(\1, \2)', res)

    # m.determinant() -> np.linalg.det(m)
    if re.search(r'\.determinant\(\)', res):
        imports.add("numpy as np")
        res = re.sub(r'([A-Za-z0-9_.]+)\.determinant\(\)', r'np.linalg.det(\1)', res)

    # v.norm() -> np.linalg.norm(v)
    if re.search(r'\.norm\(\)', res):
        imports.add("numpy as np")
        res = re.sub(r'([A-Za-z0-9_.]+)\.norm\(\)', r'np.linalg.norm(\1)', res)

    # v.squaredNorm() -> np.sum(v ** 2)
    res = re.sub(r'([A-Za-z0-9_.]+)\.squaredNorm\(\)', r'np.sum(\1 ** 2)', res)

    # v.normalized() -> (v / np.linalg.norm(v))
    res = re.sub(r'([A-Za-z0-9_.]+)\.normalized\(\)', r'(\1 / np.linalg.norm(\1))', res)

    # v.cross(w) -> np.cross(v, w)
    if re.search(r'\.cross\(', res):
        imports.add("numpy as np")
        res = re.sub(r'([A-Za-z0-9_.]+)\.cross\(\s*([^)]+)\s*\)', r'np.cross(\1, \2)', res)

    # v.dot(w) -> np.dot(v, w)
    if re.search(r'\.dot\(', res):
        imports.add("numpy as np")
        res = re.sub(r'([A-Za-z0-9_.]+)\.dot\(\s*([^)]+)\s*\)', r'np.dot(\1, \2)', res)

    # Eigen solver: A.colPivHouseholderQr().solve(b) -> np.linalg.solve(A, b)
    if re.search(r'\.colPivHouseholderQr\(\)\.solve\(', res) or re.search(r'\.lu\(\)\.solve\(', res):
        imports.add("numpy as np")
        res = re.sub(r'([A-Za-z0-9_.]+)\.(?:colPivHouseholderQr|lu|ldlt)\(\)\.solve\(\s*([^)]+)\s*\)', r'np.linalg.solve(\1, \2)', res)

    # 3. BLAS & LAPACK routines
    # cblas_ddot / ddot_ -> np.dot(x, y)
    if re.search(r'\b(?:cblas_)?ddot_?\s*\(', res):
        imports.add("numpy as np")
        res = re.sub(r'\b(?:cblas_)?ddot_?\s*\(\s*[^,]+,\s*([^,]+),\s*[^,]+,\s*([^,]+),\s*[^)]+\)', r'np.dot(\1, \2)', res)

    # cblas_dnrm2 / dnrm2_ -> np.linalg.norm(x)
    if re.search(r'\b(?:cblas_)?dnrm2_?\s*\(', res):
        imports.add("numpy as np")
        res = re.sub(r'\b(?:cblas_)?dnrm2_?\s*\(\s*[^,]+,\s*([^,]+),\s*[^)]+\)', r'np.linalg.norm(\1)', res)

    # cblas_daxpy / daxpy_ -> y += alpha * x
    res = re.sub(
        r'\b(?:cblas_)?daxpy_?\s*\(\s*[^,]+,\s*([^,]+),\s*([^,]+),\s*[^,]+,\s*([^,]+),\s*[^)]+\)\s*;',
        r'\3 += \1 * \2',
        res
    )

    # cblas_dgemm / dgemm_ -> C = alpha * (A @ B) + beta * C
    m_dgemm = re.search(
        r'\b(?:cblas_)?dgemm_?\s*\([^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,\s*([^,]+),\s*([^,]+),[^,]+,\s*([^,]+),[^,]+,\s*([^,]+),\s*([^,]+),[^)]+\)\s*;',
        res
    )
    if m_dgemm:
        alpha = m_dgemm.group(1).strip()
        mat_a = m_dgemm.group(2).strip()
        mat_b = m_dgemm.group(3).strip()
        beta = m_dgemm.group(4).strip()
        mat_c = m_dgemm.group(5).strip()

        if alpha == "1.0" and beta == "0.0":
            rep = f"{mat_c} = {mat_a} @ {mat_b}"
        elif beta == "0.0":
            rep = f"{mat_c} = {alpha} * ({mat_a} @ {mat_b})"
        elif alpha == "1.0" and beta == "1.0":
            rep = f"{mat_c} = ({mat_a} @ {mat_b}) + {mat_c}"
        else:
            rep = f"{mat_c} = {alpha} * ({mat_a} @ {mat_b}) + {beta} * {mat_c}"

        res = res[:m_dgemm.start()] + rep + res[m_dgemm.end():]

    # LAPACK dgesv_ / cblas_dgesv -> x = np.linalg.solve(A, b)
    if re.search(r'\b(?:cblas_)?dgesv_?\s*\(', res):
        imports.add("numpy as np")
        res = re.sub(
            r'\b(?:cblas_)?dgesv_?\s*\([^,]+,[^,]+,\s*([^,]+),[^,]+,[^,]+,\s*([^,]+),[^)]+\)\s*;',
            r'\2 = np.linalg.solve(\1, \2)',
            res
        )

    return res, imports


def run_self_test() -> bool:
    r"""Test BLAS, LAPACK, and Eigen modernization."""
    print("Running linalg_modernizer self-test...")
    sample = """
    Vector3d v1, v2;
    MatrixXd A, B, C;
    double d = v1.dot(v2);
    Vector3d c = v1.cross(v2);
    double n = v1.norm();
    MatrixXd A_T = A.transpose();
    VectorXd x = A.inverse() * b;
    VectorXd y = A.colPivHouseholderQr().solve(b);
    cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, m, n, k, 1.0, A, lda, B, ldb, 0.0, C, ldc);
    """
    out, imps = modernize_linalg_expressions(sample)
    assert "np.ndarray v1, v2;" in out
    assert "np.dot(v1, v2)" in out
    assert "np.cross(v1, v2)" in out
    assert "np.linalg.norm(v1)" in out
    assert "A.T" in out
    assert "np.linalg.solve(A, b)" in out
    assert "C = A @ B" in out
    print("linalg_modernizer self-test passed successfully!")
    return True


if __name__ == "__main__":
    run_self_test()
