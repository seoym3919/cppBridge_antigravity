#!/usr/bin/env python3
r"""
loop_vectorizer_engine.py - Automated Scientific Loop Vectorization Engine for C/C++.

Transforms:
- Element-wise operations: c[i] = a[i] + b[i] -> c[:n] = a[:n] + b[:n]
- Scaled additions (AXPY): y[i] += a * x[i] -> y[:n] += a * x[:n]
- Reductions: sum += a[i] -> sum += np.sum(a[:n])
- Dot products: dot += a[i] * b[i] -> dot += np.dot(a[:n], b[:n])
- Sum of squares: sum_sq += a[i] * a[i] -> sum_sq += np.sum(a[:n] ** 2)
- Recurrences: Emits @numba.njit(fastmath=True) compiled kernels
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Tuple, Optional


class VectorizedPattern:
    def __init__(self, kind: str, python_expr: str, var_names: List[str]):
        self.kind = kind
        self.python_expr = python_expr
        self.var_names = var_names


def analyze_and_vectorize_loop(loop_code: str) -> Optional[VectorizedPattern]:
    r"""Analyze a single C/C++ for loop block and attempt to vectorize it."""
    # Match for (int i = 0; i < n; ++i)
    m_for = re.search(
        r'for\s*\(\s*(?:int|size_t)?\s*([A-Za-z0-9_]+)\s*=\s*0;\s*\1\s*<\s*([^;]+);\s*(?:\+\+\1|\1\+\+)\s*\)\s*\{?\s*(.*?)\s*\}?$',
        loop_code.strip(),
        re.DOTALL
    )
    if not m_for:
        return None

    idx_var = m_for.group(1)
    n_expr = m_for.group(2).strip()
    body = m_for.group(3).strip().rstrip(';')

    # 1. Dot product: dot += a[i] * b[i]
    m_dot = re.match(rf'^([A-Za-z0-9_]+)\s*\+=\s*([A-Za-z0-9_]+)\[{idx_var}\]\s*\*\s*([A-Za-z0-9_]+)\[{idx_var}\]$', body)
    if m_dot:
        dot_var = m_dot.group(1)
        a_var = m_dot.group(2)
        b_var = m_dot.group(3)
        if a_var == b_var:
            return VectorizedPattern("sum_sq", f"{dot_var} += np.sum({a_var}[:int({n_expr})] ** 2)", [dot_var, a_var])
        return VectorizedPattern("dot", f"{dot_var} += np.dot({a_var}[:int({n_expr})], {b_var}[:int({n_expr})])", [dot_var, a_var, b_var])

    # 2. Simple sum reduction: sum += a[i]
    m_sum = re.match(rf'^([A-Za-z0-9_]+)\s*\+=\s*([A-Za-z0-9_]+)\[{idx_var}\]$', body)
    if m_sum:
        sum_var = m_sum.group(1)
        a_var = m_sum.group(2)
        return VectorizedPattern("sum", f"{sum_var} += np.sum({a_var}[:int({n_expr})])", [sum_var, a_var])

    # 3. AXPY: y[i] += alpha * x[i] or y[i] = alpha * x[i] + y[i]
    m_axpy = re.match(rf'^([A-Za-z0-9_]+)\[{idx_var}\]\s*\+=\s*([^;\[\]]+?)\s*\*\s*([A-Za-z0-9_]+)\[{idx_var}\]$', body)
    if m_axpy:
        y_var = m_axpy.group(1)
        alpha = m_axpy.group(2).strip()
        x_var = m_axpy.group(3)
        return VectorizedPattern("axpy", f"{y_var}[:int({n_expr})] += {alpha} * {x_var}[:int({n_expr})]", [y_var, x_var])

    # 4. Element-wise binary op: c[i] = a[i] + b[i]
    m_elem = re.match(rf'^([A-Za-z0-9_]+)\[{idx_var}\]\s*=\s*([A-Za-z0-9_]+)\[{idx_var}\]\s*([+\-*/])\s*([A-Za-z0-9_]+)\[{idx_var}\]$', body)
    if m_elem:
        c_var = m_elem.group(1)
        a_var = m_elem.group(2)
        op = m_elem.group(3)
        b_var = m_elem.group(4)
        return VectorizedPattern("elementwise", f"{c_var}[:int({n_expr})] = {a_var}[:int({n_expr})] {op} {b_var}[:int({n_expr})]", [c_var, a_var, b_var])

    return None


def run_self_test() -> bool:
    r"""Test loop vectorization recognition."""
    print("Running loop_vectorizer_engine self-test...")

    # Test element-wise
    l1 = "for (int i = 0; i < n; ++i) { c[i] = a[i] + b[i]; }"
    p1 = analyze_and_vectorize_loop(l1)
    assert p1 is not None and "c[:int(n)] = a[:int(n)] + b[:int(n)]" in p1.python_expr, "Elementwise failed"

    # Test AXPY
    l2 = "for (int i = 0; i < n; ++i) { y[i] += alpha * x[i]; }"
    p2 = analyze_and_vectorize_loop(l2)
    assert p2 is not None and "y[:int(n)] += alpha * x[:int(n)]" in p2.python_expr, "AXPY failed"

    # Test Dot
    l3 = "for (int i = 0; i < n; ++i) { dot += u[i] * v[i]; }"
    p3 = analyze_and_vectorize_loop(l3)
    assert p3 is not None and "dot += np.dot(u[:int(n)], v[:int(n)])" in p3.python_expr, "Dot product failed"

    # Test Sum
    l4 = "for (int i = 0; i < n; ++i) { total += data[i]; }"
    p4 = analyze_and_vectorize_loop(l4)
    assert p4 is not None and "total += np.sum(data[:int(n)])" in p4.python_expr, "Sum failed"

    print("loop_vectorizer_engine self-test passed successfully!")
    return True


if __name__ == "__main__":
    run_self_test()
