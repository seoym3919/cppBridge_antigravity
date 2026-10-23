---
name: benchmark-cpp-python
description: Benchmarks execution runtimes across scalar Python, vectorized NumPy, and Numba JIT, generating speedup metrics and Markdown comparison tables.
disable-model-invocation: true
---

# /benchmark-cpp-python

Runs micro-benchmarks comparing scalar Python baseline execution against vectorized NumPy and Numba JIT kernels across increasing problem dimensions ($N=10^3, 10^4, 10^6$).

## Usage

Run benchmarks:
```text
/benchmark-cpp-python
```

Run CLI benchmark:
```bash
python3 scripts/cpp_bridge_cli.py --benchmark
```

## Metrics Output

Outputs formatted Markdown tables with:
- Problem size ($N$)
- Scalar execution time (ms/s)
- Vectorized execution time (ms/s)
- Speedup multiplier ($50\times$--$300\times$)
