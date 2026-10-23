#!/usr/bin/env python3
r"""
cpp_bridge_cli.py - Master CLI Driver for cppBridge.
Codebase-Wide & Directory-First Multi-File C/C++ Modernization Engine.

Modernizes and translates C/C++ (C89, C99, C11, C++11, C++17, C++20) into
idiomatic, high-performance Scientific Python (NumPy, SciPy, Numba, Dataclasses)
or high-speed pybind11 C++ extension modules.

Usage:
    # 1. Modernize entire C/C++ codebase directory:
    python3 scripts/cpp_bridge_cli.py /path/to/cpp_repo
    python3 scripts/cpp_bridge_cli.py /path/to/cpp_repo --out-dir modernized_pkg --report CODEBASE_REPORT.md

    # 2. Modernize entire codebase to native pybind11 extension:
    python3 scripts/cpp_bridge_cli.py /path/to/cpp_repo --pybind11 --module-name my_native_pkg

    # 3. Modernize a single C/C++ file:
    python3 scripts/cpp_bridge_cli.py -i solver.c -o solver.py --report report.md
"""

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

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


def generate_single_file_report(source_path: str, c_text: str, py_text: str) -> str:
    r"""Generate a detailed markdown report on the translation of a single file."""
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
    lines.append(f"> python3 scripts/cpp_python_verifier.py --self-test")
    lines.append("> ```")

    return "\n".join(lines)


def modernize_cpp_codebase(
    target_dir: str | Path,
    out_dir: Optional[str | Path] = None,
    report_path: Optional[str | Path] = None,
    use_pybind11: bool = False,
    module_name: Optional[str] = None
) -> Dict[str, Any]:
    r"""
    Modernize an entire C/C++ codebase directory:
    - Recursively discovers all C/C++ sources and headers
    - Computes topological dependency DAG via CppProjectLinker
    - Translates each module into pure Python/NumPy or pybind11 native bindings
    - Generates package __init__.py or setup.py
    - Emits a comprehensive CODEBASE_TRANSLATION_REPORT.md
    """
    root = Path(target_dir).resolve()
    print("================================================================================")
    print(f" [cppBridge] Scanning C/C++ Codebase Directory: {root}")
    print("================================================================================")

    linker = header_linker.CppProjectLinker(root)
    linker.scan()

    if not linker.files:
        print("No C/C++ source or header files (.c, .cpp, .h, .hpp) found in directory.")
        return {"files": 0}

    compile_order = linker.topological_sort()
    print(f"Discovered C/C++ files: {len(linker.files)}")
    print(f"Topological include dependency translation sequence:")
    for idx, fname in enumerate(compile_order, 1):
        print(f"  {idx}. {fname}")

    # Destination directory
    destination = Path(out_dir) if out_dir else (root / "modernized_python")
    destination.mkdir(parents=True, exist_ok=True)

    all_structs: List[Any] = []
    all_allocs: List[Dict[str, Any]] = []
    total_c_lines = 0
    total_py_lines = 0

    if use_pybind11:
        pkg_name = module_name or f"{root.name}_native"
        print(f"Generating unified pybind11 native module: {pkg_name}...")
        combined_c_text = []
        for fname in compile_order:
            p = linker.files[fname]
            combined_c_text.append(p.read_text(encoding="utf-8", errors="replace"))
        full_c = "\n\n".join(combined_c_text)

        cpp_wrapper = generate_pybind11_module(full_c, pkg_name)
        setup_code = generate_setup_py(pkg_name, f"{pkg_name}_pybind11.cpp")

        out_cpp = destination / f"{pkg_name}_pybind11.cpp"
        out_setup = destination / "setup.py"
        out_cpp.write_text(cpp_wrapper, encoding="utf-8")
        out_setup.write_text(setup_code, encoding="utf-8")
        print(f"Generated pybind11 wrapper: {out_cpp}")
        print(f"Generated setuptools script: {out_setup}")

    else:
        # Pure Scientific Python Modernization
        for fname in compile_order:
            src_path = linker.files[fname]
            c_text = src_path.read_text(encoding="utf-8", errors="replace")
            total_c_lines += len(c_text.splitlines())

            structs = parse_structs_and_classes(c_text)
            all_structs.extend(structs)

            allocs = analyze_pointer_allocations(c_text)
            for a in allocs:
                a_copy = dict(a)
                a_copy["file"] = fname
                all_allocs.append(a_copy)

            py_code = transpile_cpp_to_python(c_text)
            total_py_lines += len(py_code.splitlines())

            stem = src_path.stem
            out_py = destination / f"{stem}.py"
            out_py.write_text(py_code, encoding="utf-8")

        # Generate __init__.py
        init_code = linker.generate_init_py(compile_order)
        init_path = destination / "__init__.py"
        init_path.write_text(init_code, encoding="utf-8")
        print(f"Generated Python package descriptor: {init_path}")

    # Codebase Modernization Report
    rep_lines = [
        f"# Codebase C/C++ Modernization Report: `{root.name}`",
        "",
        "## 1. Executive Summary",
        f"- **Codebase Root**: `{root}`",
        f"- **C/C++ Files Modernized**: {len(linker.files)}",
        f"- **Original C/C++ Lines**: {total_c_lines}",
        f"- **Generated Python Lines**: {total_py_lines}",
        f"- **Target Architecture**: {'pybind11 Native C++ Extension' if use_pybind11 else 'Idiomatic Scientific Python (NumPy, SciPy, Numba)'}",
        f"- **Output Package Directory**: `{destination}`",
        "",
        "## 2. Topological Dependency Build Sequence",
        "Headers and implementations were sorted topologically according to internal `#include` dependencies:",
        ""
    ]
    for idx, fname in enumerate(compile_order, 1):
        rep_lines.append(f"{idx}. `{fname}`")

    if all_allocs:
        rep_lines.extend([
            "",
            "## 3. Memory Architecture & De-Pointerization",
            "Manual heap allocations (`malloc`, `calloc`, `new[]`) were decompiled into bounded NumPy buffers:",
            "",
            "| File | Pointer Variable | Allocation Primitive | Transpiled Python Structure |",
            "|---|---|---|---|"
        ])
        for a in all_allocs[:25]:
            rep_lines.append(f"| `{a.get('file', '-')}` | `{a['name']}` | `{a['kind']}` | `{a['python_code']}` |")
        if len(all_allocs) > 25:
            rep_lines.append(f"\n*...and {len(all_allocs) - 25} additional pointer allocations.*")

    if all_structs:
        rep_lines.extend([
            "",
            "## 4. Struct & Class Modernization",
            "C structs and C++ classes were modernized into `@dataclass` state objects and contiguous `np.dtype` definitions:",
            "",
            "| C/C++ Type | Struct Name | Python Class | NumPy Dtype |",
            "|---|---|---|---|"
        ])
        for s in all_structs:
            rep_lines.append(f"| `{s.kind}` | `{s.name}` | `@dataclass class {s.name}` | `{s.name.lower()}_dtype` |")

    rep_lines.extend([
        "",
        "## 5. Numerical Equivalence & Benchmarks",
        "> [!TIP]",
        "> Verify continuous mathematical output equivalence across parameter sweeps:",
        "> ```bash",
        "> python3 scripts/cpp_python_verifier.py --self-test",
        "> python3 scripts/cpp_bridge_cli.py --benchmark",
        "> ```"
    ])

    full_report = "\n".join(rep_lines)
    rep_out = Path(report_path) if report_path else (root / "CODEBASE_TRANSLATION_REPORT.md")
    rep_out.write_text(full_report, encoding="utf-8")
    print(f"Codebase modernization report written to: {rep_out}")
    print("================================================================================")

    return {
        "files": len(linker.files),
        "destination": destination,
        "report": rep_out
    }


def main():
    parser = argparse.ArgumentParser(
        description="cppBridge: Automated C/C++ to Scientific Python Modernizer (Codebase-Wide & Directory-First)"
    )
    parser.add_argument("target", nargs="?", default=".", help="Path to C/C++ codebase directory (default: '.') or source file (.c, .cpp, .h, .hpp)")
    parser.add_argument("-i", "--input", type=str, help="Explicit input file path (for backwards compatibility)")
    parser.add_argument("-o", "--output", type=str, help="Path to output Python file (.py) for single file translation")
    parser.add_argument("--out-dir", type=str, help="Path to output directory for codebase modernization")
    parser.add_argument("--pybind11", action="store_true", help="Generate high-performance pybind11 C++ bindings and setup.py")
    parser.add_argument("--module-name", type=str, help="Module name for pybind11")
    parser.add_argument("--report", type=str, help="Path to output markdown modernization report")
    parser.add_argument("--link", type=str, help="Scan directory and link C/C++ project (alias)")
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

    raw_target = args.link or args.input or args.target
    target_path = Path(raw_target)

    if not target_path.exists():
        print(f"Error: Target path '{raw_target}' not found.", file=sys.stderr)
        sys.exit(1)

    # DIRECTORY / CODEBASE MODE (PRIMARY MODE)
    if target_path.is_dir():
        modernize_cpp_codebase(
            target_path,
            out_dir=args.out_dir,
            report_path=args.report,
            use_pybind11=args.pybind11,
            module_name=args.module_name
        )
        return

    # SINGLE FILE MODE (FALLBACK)
    c_text = target_path.read_text(encoding="utf-8", errors="replace")
    mod_name = args.module_name or target_path.stem

    if args.pybind11:
        print(f"Generating pybind11 bindings for {target_path.name}...")
        cpp_wrapper = generate_pybind11_module(c_text, mod_name)
        setup_code = generate_setup_py(mod_name, f"{mod_name}_pybind11.cpp")

        out_cpp = target_path.parent / f"{mod_name}_pybind11.cpp"
        out_setup = target_path.parent / "setup.py"

        out_cpp.write_text(cpp_wrapper, encoding="utf-8")
        out_setup.write_text(setup_code, encoding="utf-8")

        print(f"  -> Generated {out_cpp}")
        print(f"  -> Generated {out_setup}")
        print("Build with: pip install . or python setup.py build_ext --inplace")
        return

    # Standard pure Python transpilation
    print(f"Transpiling {target_path.name} to Python / NumPy...")
    py_code = transpile_cpp_to_python(c_text)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(py_code, encoding="utf-8")
        print(f"Transpiled Python saved to: {out_path}")
    else:
        print("\n" + py_code)

    if args.report:
        report_md = generate_single_file_report(str(target_path), c_text, py_code)
        Path(args.report).write_text(report_md, encoding="utf-8")
        print(f"Modernization report saved to: {args.report}")


if __name__ == "__main__":
    main()
