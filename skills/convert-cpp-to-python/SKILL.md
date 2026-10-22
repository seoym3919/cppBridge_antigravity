---
name: convert-cpp-to-python
description: Master translation command to convert legacy and modern C/C++ files or code routines into idiomatic scientific Python with NumPy, SciPy, and Dataclasses.
---

# /convert-cpp-to-python

Translates entire C or C++ source files or functions into modern, typed Python using NumPy arrays, Python dataclasses, and vectorized expressions.

## Usage

Translate a single C/C++ file:
```text
/convert-cpp-to-python solver.c --out solver.py
```

Translate with an architectural modernization report:
```text
/convert-cpp-to-python simulation.cpp --out simulation.py --report report.md
```

Translate via CLI:
```bash
python3 scripts/cpp_bridge_cli.py -i simulation.c -o simulation.py --report translation_report.md
```

## Workflow

1. **AST & Interface Deconstruction**:
   Identifies functions, parameters, pointer indicators, and structs.
2. **De-Pointerization**:
   Replaces `malloc`, `calloc`, and `new[]` with `np.zeros` or `np.empty` via [`pointer_analyzer.py`](../../scripts/pointer_analyzer.py).
3. **Compound Type Modernization**:
   Transforms C `struct` / `typedef struct` into Python `@dataclass` and `np.dtype` via [`struct_transpiler.py`](../../scripts/struct_transpiler.py).
4. **Format & Stream Decompilation**:
   Converts `printf`, `sprintf`, `fprintf`, and `std::cout` into clean Python f-strings via [`printf_decompiler.py`](../../scripts/printf_decompiler.py).
5. **Code Emission & Verification**:
   Outputs PEP 8 compliant, typed Python 3.10+ code and verifies numerical equivalence via [`cpp_python_verifier.py`](../../scripts/cpp_python_verifier.py).
