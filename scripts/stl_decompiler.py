#!/usr/bin/env python3
r"""
stl_decompiler.py - Decompiles C++ Standard Template Library (STL) Containers & Algorithms to Python.

Converts:
- std::vector<T> -> np.ndarray / list
- std::array<T, N> -> np.ndarray (shape (N,))
- std::map<K, V>, std::unordered_map<K, V> -> dict
- std::set<T>, std::unordered_set<T> -> set
- std::pair<T1, T2> -> tuple
- std::string -> str
- Methods: .push_back, .size(), .empty(), .resize(), .front(), .back()
- Algorithms: std::sort, std::reverse, std::clamp, std::min, std::max
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Tuple, Set


STL_TYPE_MAP = {
    r'std::vector<\s*double\s*>': 'np.ndarray',
    r'std::vector<\s*float\s*>': 'np.ndarray',
    r'std::vector<\s*int\s*>': 'np.ndarray',
    r'std::vector<\s*size_t\s*>': 'np.ndarray',
    r'std::vector<\s*([A-Za-z0-9_]+)\s*>': r'list[\1]',
    r'std::array<\s*double\s*,\s*(\d+)\s*>': r'np.ndarray',
    r'std::array<\s*([A-Za-z0-9_]+)\s*,\s*(\d+)\s*>': r'list[\1]',
    r'std::map<\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*>': r'dict[\1, \2]',
    r'std::unordered_map<\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*>': r'dict[\1, \2]',
    r'std::set<\s*([A-Za-z0-9_]+)\s*>': r'set[\1]',
    r'std::unordered_set<\s*([A-Za-z0-9_]+)\s*>': r'set[\1]',
    r'std::pair<\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*>': r'tuple[\1, \2]',
    r'std::string': 'str',
    r'std::unique_ptr<\s*([A-Za-z0-9_]+)\s*>': r'\1',
    r'std::shared_ptr<\s*([A-Za-z0-9_]+)\s*>': r'\1',
}


def decompile_stl_types(code_text: str) -> str:
    r"""Replace C++ STL type signatures with Python types."""
    res = code_text
    for pat, repl in STL_TYPE_MAP.items():
        res = re.sub(pat, repl, res)
    return res


def decompile_stl_methods(expr: str) -> str:
    r"""Decompile C++ STL method calls to Python operations."""
    e = expr.strip()

    # vec.push_back(val) / vec.emplace_back(val) -> vec.append(val)
    e = re.sub(r'([A-Za-z0-9_.]+)\.(?:push_back|emplace_back)\s*\(([^)]+)\)', r'\1.append(\2)', e)

    # vec.pop_back() -> vec.pop()
    e = re.sub(r'([A-Za-z0-9_.]+)\.pop_back\s*\(\)', r'\1.pop()', e)

    # vec.size() / str.length() -> len(vec)
    e = re.sub(r'([A-Za-z0-9_.]+)\.(?:size|length)\s*\(\)', r'len(\1)', e)

    # vec.empty() -> (len(vec) == 0)
    e = re.sub(r'([A-Za-z0-9_.]+)\.empty\s*\(\)', r'(len(\1) == 0)', e)

    # vec.front() -> vec[0], vec.back() -> vec[-1]
    e = re.sub(r'([A-Za-z0-9_.]+)\.front\s*\(\)', r'\1[0]', e)
    e = re.sub(r'([A-Za-z0-9_.]+)\.back\s*\(\)', r'\1[-1]', e)

    # vec.clear() -> vec.clear()
    # vec.resize(n) -> vec = [0.0] * n (or np.resize)
    e = re.sub(r'([A-Za-z0-9_.]+)\.resize\s*\(([^)]+)\)', r'\1 = [0.0] * int(\2)', e)

    # Algorithms
    # std::sort(v.begin(), v.end()) -> v.sort()
    e = re.sub(r'std::sort\s*\(\s*([A-Za-z0-9_.]+)\.begin\(\)\s*,\s*\1\.end\(\)\s*\)', r'\1.sort()', e)

    # std::reverse(v.begin(), v.end()) -> v.reverse()
    e = re.sub(r'std::reverse\s*\(\s*([A-Za-z0-9_.]+)\.begin\(\)\s*,\s*\1\.end\(\)\s*\)', r'\1.reverse()', e)

    # std::min(a, b) -> min(a, b), std::max(a, b) -> max(a, b)
    e = re.sub(r'std::min\s*\(', 'min(', e)
    e = re.sub(r'std::max\s*\(', 'max(', e)

    # std::clamp(v, lo, hi) -> max(lo, min(v, hi))
    def clamp_repl(m):
        args = [a.strip() for a in m.group(1).split(',')]
        if len(args) == 3:
            return f"max({args[1]}, min({args[0]}, {args[2]}))"
        return m.group(0)

    e = re.sub(r'std::clamp\s*\(([^)]+)\)', clamp_repl, e)

    return e


def decompile_stl_source(code_text: str) -> str:
    r"""Decompile complete STL usage across a code string."""
    res = decompile_stl_types(code_text)
    lines = res.splitlines()
    out = []
    for l in lines:
        out.append(decompile_stl_methods(l))
    return "\n".join(out)


def run_self_test() -> bool:
    r"""Validate STL decompilation with assertions."""
    print("Running stl_decompiler self-test...")
    sample = """
    std::vector<double> velocities;
    velocities.push_back(1.5);
    int count = velocities.size();
    if (velocities.empty()) return;
    double first = velocities.front();
    double last = velocities.back();
    std::sort(velocities.begin(), velocities.end());
    std::reverse(velocities.begin(), velocities.end());
    double clamped = std::clamp(x, 0.0, 1.0);
    """
    out = decompile_stl_source(sample)
    assert "np.ndarray velocities;" in out, "Type mapping failed"
    assert "velocities.append(1.5)" in out, "push_back failed"
    assert "len(velocities)" in out, "size() failed"
    assert "len(velocities) == 0" in out, "empty() failed"
    assert "velocities[0]" in out, "front() failed"
    assert "velocities[-1]" in out, "back() failed"
    assert "velocities.sort()" in out, "std::sort failed"
    assert "velocities.reverse()" in out, "std::reverse failed"
    assert "max(0.0, min(x, 1.0))" in out, "std::clamp failed"
    print("stl_decompiler self-test passed successfully!")
    return True


if __name__ == "__main__":
    run_self_test()
