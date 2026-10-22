#!/usr/bin/env python3
r"""
cpp_bridge_cli.py - Master CLI Driver for cppBridge.

Modernizes and translates C/C++ (C89, C99, C11, C++11, C++17, C++20) into
idiomatic, high-performance Scientific Python (NumPy, SciPy, Numba, Dataclasses)
or high-speed pybind11 C++ extension modules.
"""

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

from cpp_to_python_transpiler import transpile_cpp_to_python
from struct_transpiler import parse_structs_and_classes
from pointer_analyzer import analyze_pointer_allocations
from printf_decompiler import decompile_printf_call, decompile_cout_stream
from pybind11_generator import generate_pybind11_module, generate_setup_py
import cpp_python_verifier


def run_full_self_test() -> bool:
    r"""Run test suite across all cppBridge components."""
    print("======================================================================")
    print("cppBridge Full Self-Test Suite")
    print("======================================================================\n")

    # 1. Struct transpiler test
    print("[1/5] Testing Struct & Dataclass Transpiler...")
    c_struct = """
    typedef struct {
        double x, y, z;
        int id;
        bool active;
    } Particle;
    """
    structs = parse_structs_and_classes(c_struct)
    assert len(structs) == 1, "Struct parsing failed"
    dc = structs[0].emit_dataclass()
    assert "class Particle:" in dc, "Dataclass emission failed"
    print("  -> Passed!")

    # 2. Pointer analyzer test
    print("[2/5] Testing Pointer & Memory Analyzer...")
    c_mem = "double* data = (double*)malloc(n * sizeof(double));"
    allocs = analyze_pointer_allocations(c_mem)
    assert len(allocs) == 1, "Pointer allocation detection failed"
    assert "np.zeros(n" in allocs[0]["python_code"], "Allocation transpilation failed"
    print("  -> Passed!")

    # 3. Printf decompiler test
    print("[3/5] Testing Printf & Cout Decompiler...")
    p_stmt = 'printf("Energy: %12.6f, Iter: %04d\\n", e, iter);'
    py_p = decompile_printf_call(p_stmt)
    assert "print(f\"Energy: {e:12.6f}, Iter: {iter:04d}\")" in py_p, f"Printf decompilation mismatch: {py_p}"
    print("  -> Passed!")

    # 4. C++ Transpiler test
    print("[4/5] Testing Master C/C++ Transpiler...")
    c_code = """
    void saxpy(int n, double a, double* x, double* y) {
        for (int i = 0; i < n; ++i) {
            y[i] = a * x[i] + y[i];
        }
    }
    """
    py_code = transpile_cpp_to_python(c_code)
    assert "def saxpy(" in py_code, "Function transpilation failed"
    assert "for i in range(int(n)):" in py_code, "Loop transpilation failed"
    print("  -> Passed!")

    # 5. Closed-loop verifier self-test
    print("[5/5] Testing Closed-Loop Verifier...")
    cpp_python_verifier.run_self_test()
    print("  -> Passed!")

    print("\n======================================================================")
    print("All cppBridge Subsystems Successfully Verified!")
    print("======================================================================")
    return True


def generate_translation_report(source_path: str, c_text: str, py_text: str) -> str:
    r"""Generate a detailed markdown report on the translation."""
    structs = parse_structs_and_classes(c_text)
    allocs = analyze_pointer_allocations(c_text)

    lines = [
        f"# cppBridge Modernization Report: `{Path(source_path).name}`",
        "",
        "## 1. Executive Summary",
        f"- **Source File**: `{source_path}`",
        f"- **Source Lines**: {len(c_text.splitlines())}",
        f"- **Generated Python Lines**: {len(py_text.splitlines())}",
        f"- **Target**: Modern Scientific Python (NumPy, Dataclasses, Type Annotations)",
        "",
        "## 2. Memory Architecture & De-Pointerization",
    ]

    if allocs:
        lines.append("| Pointer Variable | C/C++ Allocation | Transpiled Python Structure |")
        lines.append("|---|---|---|")
        for a in allocs:
            lines.append(f"| `{a['name']}` | `{a['kind']}` | `{a['python_code']}` |")
    else:
        lines.append("No dynamic heap allocations detected. Array arguments mapped to `np.ndarray`.")

    lines.append("")
    lines.append("## 3. Data Model & Class Translations")
    if structs:
        lines.append("| C/C++ Type | Struct Name | Python Representation | NumPy Dtype |")
        lines.append("|---|---|---|---|")
        for s in structs:
            lines.append(f"| `{s.kind}` | `{s.name}` | `@dataclass class {s.name}` | `{s.name.lower()}_dtype` |")
    else:
        lines.append("No structured types detected.")

    lines.append("")
    lines.append("## 4. Numerical Correctness Directives")
    lines.append("> [!TIP]")
    lines.append("> To verify continuous equivalence within machine precision, run:")
    lines.append("> ```bash")
    lines.append(f"> python3 scripts/cpp_python_verifier.py --ref ref_output.npy --test py_output.npy --tol 1e-12")
    lines.append("> ```")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="cppBridge: Automated C/C++ to Scientific Python Modernizer & Transpiler"
    )
    parser.add_argument("-i", "--input", type=str, help="Path to input C/C++ file (.c, .cpp, .h, .hpp)")
    parser.add_argument("-o", "--output", type=str, help="Path to output Python file (.py)")
    parser.add_argument("--pybind11", action="store_true", help="Generate high-performance pybind11 C++ bindings and setup.py")
    parser.add_argument("--module-name", type=str, help="Module name for pybind11 (defaults to input file stem)")
    parser.add_argument("--report", type=str, help="Path to output markdown modernization report")
    parser.add_argument("--self-test", action="store_true", help="Run full self-test test suite")

    args = parser.parse_args()

    if args.self_test:
        success = run_full_self_test()
        sys.exit(0 if success else 1)

    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    c_text = input_path.read_text(encoding="utf-8")
    mod_name = args.module_name or input_path.stem

    if args.pybind11:
        # Generate pybind11 bindings
        print(f"Generating pybind11 bindings for {input_path.name}...")
        cpp_wrapper = generate_pybind11_module(c_text, mod_name)
        setup_code = generate_setup_py(mod_name, f"{mod_name}_pybind11.cpp")

        out_cpp = input_path.parent / f"{mod_name}_pybind11.cpp"
        out_setup = input_path.parent / "setup.py"

        out_cpp.write_text(cpp_wrapper, encoding="utf-8")
        out_setup.write_text(setup_code, encoding="utf-8")

        print(f"  -> Generated {out_cpp}")
        print(f"  -> Generated {out_setup}")
        print("Build with: pip install . or python setup.py build_ext --inplace")
        return

    # Standard pure Python transpilation
    print(f"Transpiling {input_path.name} to Python / NumPy...")
    py_code = transpile_cpp_to_python(c_text)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(py_code, encoding="utf-8")
        print(f"Transpiled Python saved to: {out_path}")
    else:
        print("\n" + py_code)

    if args.report:
        report_md = generate_translation_report(str(input_path), c_text, py_code)
        Path(args.report).write_text(report_md, encoding="utf-8")
        print(f"Modernization report saved to: {args.report}")


if __name__ == "__main__":
    main()
