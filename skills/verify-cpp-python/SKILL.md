---
name: verify-cpp-python
description: Closed-loop numerical equivalence testing engine comparing C/C++ outputs against translated Python routines across parameter sweeps, asserting L_2 and L_infinity norms < 1e-12.
---

# /verify-cpp-python

Numerically verifies the mathematical equivalence of translated Python routines against the original C/C++ reference outputs across multidimensional parameter sweeps.

## Usage

Run verification:
```text
/verify-cpp-python --ref ref_c_output.npy --test py_output.npy --tol 1e-12
```

Run CLI verifier with Markdown report:
```bash
python3 scripts/cpp_python_verifier.py --ref ref_c_output.npy --test py_output.npy --tol 1e-12 --report verification_report.md
```

## Error Metric Formulations

1. **Max Absolute Error ($L_\infty$ Norm)**:
   $$L_\infty = \max_i |y_{\mathrm{cpp}, i} - y_{\mathrm{py}, i}|$$

2. **Root-Mean-Square Error ($L_2$ Norm)**:
   $$L_2 = \sqrt{\frac{1}{N} \sum_{i=1}^N |y_{\mathrm{cpp}, i} - y_{\mathrm{py}, i}|^2}$$

3. **Relative Error Norm**:
   $$\text{Rel } L_2 = \frac{\|y_{\mathrm{cpp}} - y_{\mathrm{py}}\|_2}{\|y_{\mathrm{cpp}}\|_2 + \epsilon} \le 10^{-12}$$
