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
import openmp_transpiler
import stl_decompiler
import linalg_modernizer
import boost_modernizer
import header_linker
import loop_vectorizer_engine
import cpp_python_benchmarker


def run_full_self_test() -> bool:
    r"""Run test suite across all 12 cppBridge subsystems."""
    print("======================================================================")
    print("cppBridge Full Self-Test Suite (12 Subsystems)")
    print("======================================================================\n")

    # 1. Struct transpiler test
    print("[1/12] Testing Struct & Dataclass Transpiler...")
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
    print("[2/12] Testing Pointer & Memory Analyzer...")
    c_mem = "double* data = (double*)malloc(n * sizeof(double));"
    allocs = analyze_pointer_allocations(c_mem)
    assert len(allocs) == 1, "Pointer allocation detection failed"
    assert "np.zeros(n" in allocs[0]["python_code"], "Allocation transpilation failed"
    print("  -> Passed!")

    # 3. Printf decompiler test
    print("[3/12] Testing Printf & Cout Decompiler...")
    p_stmt = 'printf("Energy: %12.6f, Iter: %04d\\n", e, iter);'
    py_p = decompile_printf_call(p_stmt)
    assert "print(f\"Energy: {e:12.6f}, Iter: {iter:04d}\")" in py_p, f"Printf decompilation mismatch: {py_p}"
    print("  -> Passed!")

    # 4. OpenMP transpiler test
    print("[4/12] Testing OpenMP Pragmas to Numba prange...")
    openmp_transpiler.run_self_test()
    print("  -> Passed!")

    # 5. C++ STL container decompiler
    print("[5/12] Testing C++ STL Container & Method Decompiler...")
    stl_decompiler.run_self_test()
    print("  -> Passed!")

    # 6. BLAS/LAPACK & Eigen linear algebra modernizer
    print("[6/12] Testing Linear Algebra Modernizer (BLAS/LAPACK & Eigen)...")
    linalg_modernizer.run_self_test()
    print("  -> Passed!")

    # 7. Boost C++ modernizer
    print("[7/12] Testing Boost C++ Library Modernizer...")
    boost_modernizer.run_self_test()
    print("  -> Passed!")

    # 8. Multi-file header dependency linker
    print("[8/12] Testing Multi-File Header Dependency Linker...")
    header_linker.run_self_test()
    print("  -> Passed!")

    # 9. Automated loop vectorizer engine
    print("[9/12] Testing Loop Vectorization Engine...")
    loop_vectorizer_engine.run_self_test()
    print("  -> Passed!")

    # 10. Performance benchmarker
    print("[10/12] Testing Performance Benchmarker...")
    cpp_python_benchmarker.run_self_test()
    print("  -> Passed!")

    # 11. Master C/C++ Transpiler test
    print("[11/12] Testing Master C/C++ Transpiler...")
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

    # 12. Closed-loop verifier self-test
    print("[12/12] Testing Closed-Loop Verifier...")
    cpp_python_verifier.run_self_test()
    print("  -> Passed!")

    print("\n======================================================================")
    print("All 12 cppBridge Subsystems Successfully Verified!")
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
    parser.add_argument("--link", type=str, help="Path to C/C++ project directory to analyze DAG and build Python package")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmark suite")
    parser.add_argument("--self-test", action="store_true", help="Run full 12-subsystem test suite")

    args = parser.parse_args()

    if args.self_test:
        success = run_full_self_test()
        sys.exit(0 if success else 1)

    if args.benchmark:
        res = cpp_python_benchmarker.run_benchmark_suite()
        tbl = cpp_python_benchmarker.format_benchmark_table(res)
        print(tbl)
        return

    if args.link:
        proj_dir = Path(args.link)
        if not proj_dir.is_dir():
            print(f"Error: Directory '{args.link}' not found.", file=sys.stderr)
            sys.exit(1)
        linker = header_linker.CppProjectLinker(proj_dir)
        linker.scan()
        order = linker.topological_sort()
        print(f"Discovered {len(linker.files)} C/C++ files. Topological compilation order:")
        for idx, f in enumerate(order, 1):
            print(f"  {idx}. {f}")
        init_code = linker.generate_init_py(order)
        init_path = proj_dir / "__init__.py"
        init_path.write_text(init_code, encoding="utf-8")
        print(f"Generated Python package descriptor: {init_path}")
        return

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
