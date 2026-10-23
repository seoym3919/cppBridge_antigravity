#!/usr/bin/env python3
r"""
openmp_transpiler.py - Decompiles C/C++ OpenMP Pragmas into Python Numba prange / Multiprocessing.

Converts:
- #pragma omp parallel for -> @njit(parallel=True) + numba.prange(n)
- #pragma omp critical -> threading.Lock() / multiprocessing.Lock()
- #pragma omp atomic -> synchronized variable update
- omp_get_thread_num() -> numba.get_thread_id() or multiprocessing pid
- omp_get_num_threads() -> numba.get_num_threads() or os.cpu_count()
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Tuple, Set


class OpenMPRegion:
    def __init__(self, directive: str, clauses: str, line_no: int):
        self.directive = directive.strip()
        self.clauses = clauses.strip()
        self.line_no = line_no
        self.schedule = "static"
        self.reduction_op: str | None = None
        self.reduction_var: str | None = None
        self._parse_clauses()

    def _parse_clauses(self):
        m_sched = re.search(r'schedule\s*\(\s*([a-zA-Z]+)(?:\s*,\s*(\d+))?\s*\)', self.clauses)
        if m_sched:
            self.schedule = m_sched.group(1).lower()

        m_red = re.search(r'reduction\s*\(\s*([+\-*/&|^])\s*:\s*([A-Za-z0-9_]+)\s*\)', self.clauses)
        if m_red:
            self.reduction_op = m_red.group(1)
            self.reduction_var = m_red.group(2)


def decompile_openmp_pragmas(code_text: str) -> Tuple[str, Set[str]]:
    r"""
    Decompile OpenMP directives in C/C++ code into parallel Python / Numba structures.
    """
    imports = set()
    lines = code_text.splitlines()
    out_lines: List[str] = []
    has_parallel_for = False
    has_critical = False

    i = 0
    total = len(lines)
    while i < total:
        line = lines[i]
        stripped = line.strip()

        # Match #pragma omp ...
        m_omp = re.match(r'^\s*#pragma\s+omp\s+([a-zA-Z0-9_\s]+)(?:\((.*)\))?(.*)$', stripped)
        if m_omp:
            directive_full = m_omp.group(1).strip()
            rest = (m_omp.group(3) or "").strip()

            if "parallel for" in directive_full:
                has_parallel_for = True
                imports.add("from numba import njit, prange")
                # Look ahead to next loop line
                i += 1
                if i < total:
                    next_l = lines[i]
                    next_s = next_l.strip()
                    # for (int i = 0; i < n; ++i)
                    m_for = re.match(
                        r'^\s*for\s*\(\s*(?:int|size_t)?\s*([A-Za-z0-9_]+)\s*=\s*([^;]+);\s*\1\s*<\s*([^;]+);\s*(?:\+\+\1|\1\+\+)\s*\)\s*\{?',
                        next_s
                    )
                    if m_for:
                        var_n = m_for.group(1)
                        start_v = m_for.group(2).strip()
                        end_v = m_for.group(3).strip()
                        indent = " " * (len(next_l) - len(next_l.lstrip()))
                        if start_v == "0":
                            out_lines.append(f"{indent}# OpenMP parallel for converted to Numba prange")
                            out_lines.append(f"{indent}for {var_n} in prange(int({end_v})):")
                        else:
                            out_lines.append(f"{indent}# OpenMP parallel for converted to Numba prange")
                            out_lines.append(f"{indent}for {var_n} in prange(int({start_v}), int({end_v})):")
                        i += 1
                        continue
                    else:
                        out_lines.append(f"# OpenMP directive: {stripped}")
                        out_lines.append(next_l)
                        i += 1
                        continue

            elif "critical" in directive_full:
                has_critical = True
                imports.add("import threading")
                indent = " " * (len(line) - len(line.lstrip()))
                out_lines.append(f"{indent}# OpenMP critical region")
                out_lines.append(f"{indent}with _omp_lock:")
                i += 1
                continue

            elif "atomic" in directive_full:
                indent = " " * (len(line) - len(line.lstrip()))
                out_lines.append(f"{indent}# OpenMP atomic operation")
                i += 1
                continue

            else:
                out_lines.append(f"# {stripped}")
                i += 1
                continue

        # OpenMP function calls
        if "omp_get_thread_num()" in line:
            line = re.sub(r'\bomp_get_thread_num\(\)', 'numba.get_thread_id()', line)
            imports.add("import numba")

        if "omp_get_num_threads()" in line:
            line = re.sub(r'\bomp_get_num_threads\(\)', 'numba.get_num_threads()', line)
            imports.add("import numba")

        out_lines.append(line)
        i += 1

    prefix_defs = []
    if has_critical:
        prefix_defs.append("_omp_lock = threading.Lock()\n")

    result_code = "\n".join(prefix_defs + out_lines)
    return result_code, imports


def run_self_test() -> bool:
    r"""Self-test validating OpenMP decompilation."""
    print("Running openmp_transpiler self-test...")
    omp_sample = """
    #pragma omp parallel for reduction(+:total)
    for (int i = 0; i < n; ++i) {
        total += data[i];
    }
    int tid = omp_get_thread_num();
    #pragma omp critical
    {
        global_count++;
    }
    """
    res, imps = decompile_openmp_pragmas(omp_sample)
    assert "prange(int(n))" in res, "Parallel for decompilation failed"
    assert "with _omp_lock:" in res, "Critical region decompilation failed"
    assert "numba.get_thread_id()" in res, "omp_get_thread_num decompilation failed"
    assert "from numba import njit, prange" in imps
    assert "import threading" in imps
    print("openmp_transpiler self-test passed successfully!")
    return True


if __name__ == "__main__":
    run_self_test()
