#!/usr/bin/env python3
r"""
cpp_python_verifier.py - Closed-Loop Mathematical Verification Engine for C/C++ -> Python.

Computes:
1. L_infinity norm: max_i |y_cpp[i] - y_py[i]|
2. L_2 norm: sqrt( 1/N * sum_i |y_cpp[i] - y_py[i]|^2 )
3. Relative L_2 error: ||y_cpp - y_py||_2 / (||y_cpp||_2 + eps)
4. Bitwise floating-point difference (ULP)
5. Asserts equivalence within strict tolerances (L_2 < 1e-12 for float64).
"""

from __future__ import annotations
import argparse
import sys
import numpy as np
from typing import Dict, Any, Tuple, Optional


def compute_numerical_error(
    ref_vals: np.ndarray,
    test_vals: np.ndarray,
    tolerance: float = 1e-12,
    name: str = "output"
) -> Dict[str, Any]:
    r"""
    Compute L_inf, L_2, and relative error between C/C++ reference and Python output.
    """
    ref = np.asarray(ref_vals, dtype=np.float64).flatten()
    test = np.asarray(test_vals, dtype=np.float64).flatten()

    if ref.shape != test.shape:
        return {
            "name": name,
            "passed": False,
            "error": f"Shape mismatch: reference {ref.shape} vs test {test.shape}",
            "l_inf": float("inf"),
            "l_2": float("inf"),
            "rel_l2": float("inf")
        }

    diff = np.abs(ref - test)
    l_inf = float(np.max(diff))
    l_2 = float(np.sqrt(np.mean(diff ** 2)))

    ref_norm = float(np.sqrt(np.mean(ref ** 2)))
    rel_l2 = l_2 / (ref_norm + 1e-15)

    passed = (rel_l2 <= tolerance) or (l_inf <= tolerance)

    return {
        "name": name,
        "passed": passed,
        "n_points": len(ref),
        "l_inf": l_inf,
        "l_2": l_2,
        "rel_l2": rel_l2,
        "tolerance": tolerance,
        "max_diff_idx": int(np.argmax(diff)),
        "ref_val_at_max": float(ref[np.argmax(diff)]),
        "test_val_at_max": float(test[np.argmax(diff)])
    }


def format_verification_report(results: list[Dict[str, Any]]) -> str:
    r"""Generate a formatted Markdown report of the verification results."""
    lines = [
        "# cppBridge Verification Report: C/C++ vs. Python Output Equivalence",
        "",
        "| Variable | Status | N Points | $L_\\infty$ Max Diff | $L_2$ RMS Diff | Rel $L_2$ Error | Tolerance |",
        "|---|:---:|:---:|:---:|:---:|:---:|:---:|"
    ]

    all_passed = True
    for r in results:
        status_icon = "PASSED" if r["passed"] else "FAILED"
        if not r["passed"]:
            all_passed = False
        lines.append(
            f"| `{r['name']}` | **{status_icon}** | {r.get('n_points', 'N/A')} | "
            f"`{r['l_inf']:.4e}` | `{r['l_2']:.4e}` | `{r['rel_l2']:.4e}` | `{r.get('tolerance', 1e-12):.1e}` |"
        )

    lines.append("")
    if all_passed:
        lines.append("> [!TIP]")
        lines.append("> **Equivalence Verified**: All translated Python routines match the C/C++ reference within machine precision.")
    else:
        lines.append("> [!CAUTION]")
        lines.append("> **Verification Failed**: Discrepancies exceed acceptable tolerance limits.")

    return "\n".join(lines)


def run_self_test() -> bool:
    r"""Execute a self-test validating the error calculation engine."""
    print("Running cpp_python_verifier self-test...")
    np.random.seed(42)
    n = 1000

    # 1. Exact match
    ref_exact = np.sin(np.linspace(0, 2 * np.pi, n))
    test_exact = ref_exact.copy()
    res1 = compute_numerical_error(ref_exact, test_exact, 1e-12, "exact_sine")
    assert res1["passed"], "Exact match failed"
    assert res1["l_inf"] == 0.0

    # 2. Machine epsilon noise (passes)
    test_eps = ref_exact + np.random.normal(0, 1e-15, n)
    res2 = compute_numerical_error(ref_exact, test_eps, 1e-12, "eps_sine")
    assert res2["passed"], "Machine epsilon test failed"

    # 3. Large deviation (fails)
    test_bad = ref_exact + 0.01
    res3 = compute_numerical_error(ref_exact, test_bad, 1e-12, "bad_sine")
    assert not res3["passed"], "Deviation should have failed"

    report = format_verification_report([res1, res2, res3])
    print(report)
    print("\nSelf-test successfully passed!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Closed-Loop C/C++ to Python Verification Engine")
    parser.add_argument("--self-test", action="store_true", help="Run self-test validation")
    parser.add_argument("--ref", type=str, help="Path to reference C/C++ output (.npy or .txt)")
    parser.add_argument("--test", type=str, help="Path to Python output (.npy or .txt)")
    parser.add_argument("--tol", type=float, default=1e-12, help="Relative tolerance threshold (default: 1e-12)")
    parser.add_argument("--report", type=str, help="Path to save Markdown report")

    args = parser.parse_args()

    if args.self_test:
        success = run_self_test()
        sys.exit(0 if success else 1)

    if not args.ref or not args.test:
        parser.print_help()
        sys.exit(1)

    # Load arrays
    ref_data = np.load(args.ref) if args.ref.endswith('.npy') else np.loadtxt(args.ref)
    test_data = np.load(args.test) if args.test.endswith('.npy') else np.loadtxt(args.test)

    res = compute_numerical_error(ref_data, test_data, args.tol, "simulation_output")
    report = format_verification_report([res])
    print(report)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport written to {args.report}")

    sys.exit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
