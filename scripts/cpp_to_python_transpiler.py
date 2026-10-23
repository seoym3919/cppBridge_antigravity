#!/usr/bin/env python3
r"""
cpp_to_python_transpiler.py - Master C/C++ to Modern Python / NumPy Transpiler.

Converts:
- C/C++ functions -> typed Python functions
- malloc / calloc / new[] -> np.zeros / np.empty
- Structs & Classes -> Python @dataclass models
- printf / std::cout -> Python f-strings
- C operators (&&, ||, !, ->) -> Python operators (and, or, not, .)
- Math calls (sqrt, pow, fabs, sin, cos) -> math / numpy equivalents
- Pointer arithmetic -> array indexing & slicing
- Loops & conditionals -> Python loops and if/elif/else blocks
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Set, Tuple

from struct_transpiler import parse_structs_and_classes, ParsedStruct
from printf_decompiler import decompile_printf_call, decompile_cout_stream
from pointer_analyzer import analyze_pointer_allocations, decompile_pointer_arithmetic
from stl_decompiler import decompile_stl_methods, decompile_stl_types
from linalg_modernizer import modernize_linalg_expressions
from boost_modernizer import modernize_boost_code
from openmp_transpiler import decompile_openmp_pragmas
from loop_vectorizer_engine import analyze_and_vectorize_loop


def convert_cpp_expression_to_python(expr: str) -> Tuple[str, Set[str]]:
    r"""
    Convert a C/C++ scalar or array expression to Python.
    """
    imports = set()
    e = expr.strip()

    # STL methods (push_back, size, empty, front, back, etc.)
    e = decompile_stl_methods(e)

    # BLAS / LAPACK / Eigen expressions
    e, linalg_imps = modernize_linalg_expressions(e)
    imports.update(linalg_imps)

    # Boost functions & objects
    e, boost_imps = modernize_boost_code(e)
    imports.update(boost_imps)

    # Arrow operator: obj->field -> obj.field
    e = re.sub(r'->', '.', e)

    # Logical operators
    e = re.sub(r'&&', ' and ', e)
    e = re.sub(r'\|\|', ' or ', e)
    e = re.sub(r'!(?!=)', ' not ', e)

    # Booleans and Null
    e = re.sub(r'\btrue\b', 'True', e)
    e = re.sub(r'\bfalse\b', 'False', e)
    e = re.sub(r'\b(NULL|nullptr)\b', 'None', e)

    # Casts: (double)x -> float(x), (int)x -> int(x)
    e = re.sub(r'\(\s*(?:double|float)\s*\)\s*([A-Za-z0-9_]+)', r'float(\1)', e)
    e = re.sub(r'\(\s*(?:int|long|size_t)\s*\)\s*([A-Za-z0-9_]+)', r'int(\1)', e)

    # Pointer arithmetic: *(ptr + i) -> ptr[i], &arr[i] -> arr[i:]
    e = decompile_pointer_arithmetic(e)

    # Math function mapping
    # Math prefix replacement: sqrt( -> math.sqrt(, sin( -> math.sin(, etc.
    math_fns = ("sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "exp", "log", "log10", "hypot")
    for fn in math_fns:
        if re.search(rf'\b{fn}\s*\(', e):
            imports.add("math")
            e = re.sub(rf'\b{fn}\s*\(', f'math.{fn}(', e)

    # fabs -> abs
    e = re.sub(r'\bfabs\s*\(', 'abs(', e)

    # pow(a, 2) simplification if present
    e = re.sub(r'\bpow\s*\(\s*([^,()]+)\s*,\s*2\s*\)', r'(\1 * \1)', e)
    # Generic pow(a, b) -> pow(a, b) (Python built-in pow works out of the box)

    return e, imports


def transpile_cpp_to_python(code_text: str) -> str:
    r"""Transpile complete C/C++ source into idiomatic Python."""
    imports = {"numpy as np", "math"}
    python_lines: List[str] = []

    # 0. Preprocess OpenMP pragmas and STL container types
    code_text, omp_imps = decompile_openmp_pragmas(code_text)
    imports.update(omp_imps)
    code_text = decompile_stl_types(code_text)

    # 1. Parse and emit structs as dataclasses
    structs = parse_structs_and_classes(code_text)
    if structs:
        imports.add("from dataclasses import dataclass, field")
        python_lines.append("# ============================================================================")
        python_lines.append("# Data Models & Structs (Converted from C/C++)")
        python_lines.append("# ============================================================================\n")
        for s in structs:
            python_lines.append(s.emit_dataclass())
            python_lines.append("")
            python_lines.append(s.emit_numpy_dtype())
            python_lines.append("")

    # 2. Line-by-line parsing with multi-line accumulation and brace tracking
    raw_lines = code_text.splitlines()
    in_function = False
    brace_depth = 0

    def ind() -> str:
        return "    " * max(1, brace_depth)

    body_lines: List[str] = []

    func_def_pat = re.compile(
        r'^\s*(?:extern\s+"C"\s+)?(?:static\s+|inline\s+)?([A-Za-z0-9_:*&<>\s]+?)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*(\{)?'
    )

    idx = 0
    total_lines = len(raw_lines)

    while idx < total_lines:
        line = raw_lines[idx].strip()
        idx += 1

        if not line:
            if in_function:
                body_lines.append("")
            continue

        # Skip preprocessor includes
        if line.startswith("#include"):
            continue

        # Preprocessor defines
        m_def = re.match(r'^#define\s+([A-Za-z0-9_]+)\s+(.*)$', line)
        if m_def:
            c_name = m_def.group(1)
            c_val = m_def.group(2).strip()
            if re.match(r'^[0-9.eE+-]+$', c_val):
                body_lines.append(f"{c_name}: float = {c_val}")
            continue

        # Skip comments
        if line.startswith("//") or line.startswith("/*") or line.endswith("*/"):
            continue

        # Function definition detection (when outside function)
        if not in_function:
            # Multi-line function header accumulation: ret_type func(arg1,\n arg2)
            if "(" in line and ")" not in line and not line.startswith(("if", "for", "while")):
                while idx < total_lines and ")" not in line:
                    next_l = raw_lines[idx].strip()
                    next_l = re.sub(r'//.*$', '', next_l)
                    line += " " + next_l
                    idx += 1

            # Check if opening brace is on subsequent line
            if ")" in line and "{" not in line and idx < total_lines:
                peek_l = raw_lines[idx].strip()
                if peek_l == "{":
                    line += " {"
                    idx += 1

            m_func = func_def_pat.match(line)
            if m_func and m_func.group(2) not in ("if", "for", "while", "switch", "return"):
                in_function = True
                ret_type = m_func.group(1).strip()
                fn_name = m_func.group(2).strip()
                params_raw = m_func.group(3).strip()
                has_brace = m_func.group(4) is not None

                brace_depth = 1 if has_brace else 0

                # Parse parameters
                py_params = []
                if params_raw and params_raw != "void":
                    for p in params_raw.split(','):
                        p_clean = p.strip()
                        is_ptr = "*" in p_clean or "[]" in p_clean
                        clean_tokens = p_clean.replace('*', '').replace('[]', '').replace('&', '').strip().split()
                        if len(clean_tokens) >= 2:
                            p_t = clean_tokens[0]
                            p_n = clean_tokens[-1]
                        else:
                            p_t = "double"
                            p_n = clean_tokens[0] if clean_tokens else "arg"

                        if is_ptr:
                            py_params.append(f"{p_n}: np.ndarray")
                        elif p_t in ("double", "float"):
                            py_params.append(f"{p_n}: float")
                        elif p_t in ("int", "long", "size_t"):
                            py_params.append(f"{p_n}: int")
                        elif p_t == "bool":
                            py_params.append(f"{p_n}: bool")
                        else:
                            py_params.append(f"{p_n}: {p_t}")

                body_lines.append(f"def {fn_name}({', '.join(py_params)}):")
                body_lines.append(f'    r"""Converted from C/C++ {fn_name}."""')
                continue
            else:
                continue

        # If inside function but brace_depth == 0 (waiting for opening { of function)
        if in_function and brace_depth == 0:
            if "{" in line:
                brace_depth = 1
            continue

        # Handle brace changes for lines starting with '}'
        if line.startswith("}"):
            brace_depth -= 1
            if brace_depth <= 0:
                in_function = False
                brace_depth = 0
                body_lines.append("")
                continue

            # Check if this line is "} else if (...) {" or "} else {"
            if "else if" in line:
                m_elif = re.search(r'else\s+if\s*\((.*)\)', line)
                if m_elif:
                    cond_py, imp = convert_cpp_expression_to_python(m_elif.group(1))
                    imports.update(imp)
                    body_lines.append(f"{ind()}elif {cond_py}:")
                    brace_depth += 1
                    continue
            elif "else" in line:
                body_lines.append(f"{ind()}else:")
                brace_depth += 1
                continue

            # Pure closing brace
            if line == "}":
                continue

        # Dynamic memory allocations: malloc, calloc, new[]
        alloc_match = analyze_pointer_allocations(line)
        if alloc_match:
            for a in alloc_match:
                body_lines.append(f"{ind()}{a['python_code']}")
            continue

        # free / delete
        if re.match(r'^(?:free\s*\([^)]+\)|delete\[\]\s*[A-Za-z0-9_]+|delete\s+[A-Za-z0-9_]+)\s*;', line):
            continue

        # Printf & cout
        if line.startswith("printf") or line.startswith("sprintf") or line.startswith("fprintf"):
            py_print = decompile_printf_call(line)
            body_lines.append(f"{ind()}{py_print}")
            continue

        if re.search(r'(?:std::)?cout\s*<<', line):
            py_cout = decompile_cout_stream(line)
            body_lines.append(f"{ind()}{py_cout}")
            continue

        # For loops: for (int i = 0; i < n; ++i)
        m_for = re.match(
            r'^for\s*\(\s*(?:int|size_t)?\s*([A-Za-z0-9_]+)\s*=\s*([^;]+);\s*\1\s*<\s*([^;]+);\s*(?:\+\+\1|\1\+\+)\s*\)\s*\{?',
            line
        )
        if m_for:
            var_name = m_for.group(1)
            start_val = m_for.group(2).strip()
            end_val = m_for.group(3).strip()
            if start_val == "0":
                body_lines.append(f"{ind()}for {var_name} in range(int({end_val})):")
            else:
                body_lines.append(f"{ind()}for {var_name} in range(int({start_val}), int({end_val})):")
            brace_depth += 1
            continue

        # C++11 Range-based for: for (const auto& item : items)
        m_range_for = re.match(r'^for\s*\(\s*(?:const\s+)?(?:auto|double|int|[A-Za-z0-9_]+)[*&]?\s+([A-Za-z0-9_]+)\s*:\s*([^)]+)\)\s*\{?', line)
        if m_range_for:
            var_n = m_range_for.group(1).strip()
            iter_n = m_range_for.group(2).strip()
            body_lines.append(f"{ind()}for {var_n} in {iter_n}:")
            brace_depth += 1
            continue

        # While loops: while (cond)
        m_while = re.match(r'^while\s*\((.*)\)\s*\{?', line)
        if m_while:
            cond_py, imp = convert_cpp_expression_to_python(m_while.group(1))
            imports.update(imp)
            body_lines.append(f"{ind()}while {cond_py}:")
            brace_depth += 1
            continue

        # If statement: if (cond)
        m_if = re.match(r'^if\s*\((.*)\)\s*\{?', line)
        if m_if:
            cond_py, imp = convert_cpp_expression_to_python(m_if.group(1))
            imports.update(imp)
            body_lines.append(f"{ind()}if {cond_py}:")
            brace_depth += 1
            continue

        # Else statement without preceding brace: else {
        if re.match(r'^else\s*\{?', line):
            # Indent at previous level
            body_lines.append(f"{'    ' * max(1, brace_depth - 1)}else:")
            continue

        # Return statement
        m_ret = re.match(r'^return(?:\s+(.*))?\s*;$', line)
        if m_ret:
            if m_ret.group(1):
                ret_expr, imp = convert_cpp_expression_to_python(m_ret.group(1))
                imports.update(imp)
                body_lines.append(f"{ind()}return {ret_expr}")
            else:
                body_lines.append(f"{ind()}return")
            continue

        # Standard assignments / statements
        clean_stmt = line.rstrip(';')
        # Strip C type declaration prefixes: double x = ... -> x = ...
        clean_stmt = re.sub(
            r'^\s*(?:const\s+)?(?:double|float|int|long|size_t|bool|auto|[A-Za-z0-9_]+)\s*(\*+|\&)?\s*([A-Za-z0-9_]+)\s*=',
            r'\2 =',
            clean_stmt
        )
        # Strip standalone uninitialized declarations: double x; -> x = 0.0
        m_decl_only = re.match(r'^(?:const\s+)?(double|float|int|long|size_t|bool)\s+([A-Za-z0-9_]+)$', clean_stmt)
        if m_decl_only:
            t = m_decl_only.group(1)
            v = m_decl_only.group(2)
            default_val = "0.0" if t in ("double", "float") else ("0" if t in ("int", "long", "size_t") else "False")
            body_lines.append(f"{ind()}{v} = {default_val}")
            continue

        expr_py, imp = convert_cpp_expression_to_python(clean_stmt)
        imports.update(imp)
        body_lines.append(f"{ind()}{expr_py}")

    # Assemble complete Python module
    res = []
    res.append("# ============================================================================")
    res.append("# Transpiled from C/C++ to Modern Python / NumPy by cppBridge")
    res.append("# ============================================================================")
    res.append("from __future__ import annotations")
    for imp in sorted(imports):
        if imp.startswith("from"):
            res.append(imp)
        else:
            res.append(f"import {imp}")
    res.append("\n")
    res.extend(python_lines)
    res.extend(body_lines)

    return "\n".join(res)


if __name__ == "__main__":
    sample_c = """
    #include <stdio.h>
    #include <stdlib.h>
    #include <math.h>

    typedef struct {
        double x, y, z;
        double vx, vy, vz;
        double mass;
    } Body;

    void step_bodies(double* pos, double* vel, int n, double dt) {
        for (int i = 0; i < n; ++i) {
            double r = sqrt(pow(pos[i*3], 2) + pow(pos[i*3+1], 2) + pow(pos[i*3+2], 2));
            if (r > 0.001) {
                vel[i*3] += dt * pos[i*3] / (r * r * r);
            }
        }
        printf("Step completed successfully for %d bodies.\\n", n);
    }
    """
    print("[cpp_to_python_transpiler] Testing transpilation:")
    py_out = transpile_cpp_to_python(sample_c)
    print(py_out)
