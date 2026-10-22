#!/usr/bin/env python3
r"""
pointer_analyzer.py - Distinguishes C/C++ Pointer Usages and De-pointerizes to Python.

Classifies pointers into:
1. ARRAY_BUFFER: malloc / calloc / new -> np.zeros / np.empty
2. SCALAR_OUT_PARAM: double* out_val -> function return tuple
3. SLICE_VIEW: ptr + offset or &arr[i] -> array slice arr[i:]
4. MEMORY_FREE: free(ptr) / delete[] -> Python garbage collection
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple, Optional


class PointerUsage:
    def __init__(self, name: str, ptr_type: str = "ARRAY_BUFFER"):
        self.name = name.lower()
        self.ptr_type = ptr_type  # ARRAY_BUFFER, SCALAR_OUT, SLICE_VIEW
        self.element_type = "double"
        self.shape: Optional[str] = None

    def to_python_init(self) -> str:
        r"""Emit Python initialization."""
        if self.ptr_type == "ARRAY_BUFFER":
            shape_str = self.shape if self.shape else "n"
            py_type = "np.float64" if self.element_type in ("double", "float") else "np.int32"
            return f"{self.name} = np.zeros({shape_str}, dtype={py_type})"
        return f"{self.name} = 0.0"


def analyze_pointer_allocations(code_text: str) -> List[Dict[str, Any]]:
    r"""Detect malloc, calloc, and new expressions and decompile to NumPy allocations."""
    results = []

    # 1. malloc: type* ptr = (type*)malloc(size * sizeof(type));
    malloc_pat = re.compile(
        r'([A-Za-z0-9_]+)\s*\*\s*([A-Za-z0-9_]+)\s*=\s*(?:\([A-Za-z0-9_ *]+\))?\s*malloc\s*\((.*)\)\s*;',
        re.IGNORECASE
    )
    for m in malloc_pat.finditer(code_text):
        elem_t = m.group(1).strip()
        var_name = m.group(2).strip()
        size_expr = m.group(3).strip()

        # Simplify size: strip '* sizeof(type)'
        clean_size = re.sub(r'\s*\*\s*sizeof\s*\([^)]+\)', '', size_expr, flags=re.IGNORECASE).strip()
        results.append({
            "name": var_name,
            "kind": "malloc",
            "element_type": elem_t,
            "size_expr": clean_size,
            "python_code": f"{var_name} = np.zeros({clean_size}, dtype=np.{'float64' if elem_t in ('double', 'float') else 'int32'})"
        })

    # 2. calloc: type* ptr = (type*)calloc(num, sizeof(type));
    calloc_pat = re.compile(
        r'([A-Za-z0-9_]+)\s*\*\s*([A-Za-z0-9_]+)\s*=\s*(?:\([A-Za-z0-9_ *]+\))?\s*calloc\s*\(\s*([^,]+)\s*,\s*([^)]+)\)',
        re.IGNORECASE
    )
    for m in calloc_pat.finditer(code_text):
        elem_t = m.group(1).strip()
        var_name = m.group(2).strip()
        num_expr = m.group(3).strip()
        results.append({
            "name": var_name,
            "kind": "calloc",
            "element_type": elem_t,
            "size_expr": num_expr,
            "python_code": f"{var_name} = np.zeros({num_expr}, dtype=np.{'float64' if elem_t in ('double', 'float') else 'int32'})"
        })

    # 3. C++ new: type* ptr = new type[size];
    new_pat = re.compile(
        r'([A-Za-z0-9_]+)\s*\*\s*([A-Za-z0-9_]+)\s*=\s*new\s+[A-Za-z0-9_]+\s*\[([^\]]+)\]',
        re.IGNORECASE
    )
    for m in new_pat.finditer(code_text):
        elem_t = m.group(1).strip()
        var_name = m.group(2).strip()
        size_expr = m.group(3).strip()
        results.append({
            "name": var_name,
            "kind": "new[]",
            "element_type": elem_t,
            "size_expr": size_expr,
            "python_code": f"{var_name} = np.zeros({size_expr}, dtype=np.{'float64' if elem_t in ('double', 'float') else 'int32'})"
        })

    return results


def decompile_pointer_arithmetic(expr: str) -> str:
    r"""
    Convert pointer arithmetic to Python array indexing or slicing:
    - *(ptr + i) -> ptr[i]
    - ptr[i] -> ptr[i]
    - &arr[i] -> arr[i:]
    - *ptr (unary dereference) -> ptr[0]
    """
    e = expr.strip()
    # Dereference with addition: *(ptr + i) -> ptr[i]
    e = re.sub(r'\*\s*\(\s*([A-Za-z0-9_]+)\s*\+\s*([^)]+)\)', r'\1[\2]', e)
    # Address-of slice: &arr[i] -> arr[i:]
    e = re.sub(r'&\s*([A-Za-z0-9_]+)\s*\[\s*([^\]]+)\s*\]', r'\1[\2:]', e)
    # Unary dereference: *ptr -> ptr[0] (only when preceded by operator or start of line, not word or ])
    deref_pat = r'(^|[(=,+\-/<>;{:!])\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)'
    e = re.sub(deref_pat, r'\1 \2[0]', e)
    return e


if __name__ == "__main__":
    c_sample = """
    double* pos = (double*)malloc(N * sizeof(double));
    int* indices = (int*)calloc(N, sizeof(int));
    double* vel = new double[N * 3];

    double x = *(pos + 5);
    double* slice = &vel[i];
    free(pos);
    delete[] vel;
    """
    print("[pointer_analyzer] Detected dynamic memory allocations:")
    allocs = analyze_pointer_allocations(c_sample)
    for a in allocs:
        print(f"  {a['kind']:6s} -> Python: {a['python_code']}")

    print("\nDecompiled Pointer Expressions:")
    print("  *(pos + 5) ->", decompile_pointer_arithmetic("*(pos + 5)"))
    print("  &vel[i]    ->", decompile_pointer_arithmetic("&vel[i]"))
    print("  *ptr       ->", decompile_pointer_arithmetic("*ptr"))
