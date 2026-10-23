---
name: link-cpp-project
description: Analyzes multi-file C/C++ project headers and source files, extracts include DAGs, computes topological sort order, and generates structured Python packages.
---

# /link-cpp-project

Scans multi-file C/C++ codebases, constructs the complete Directed Acyclic Graph (DAG) of `#include` dependencies, resolves circular dependencies, and builds an organized Python package with `__init__.py` and clean relative imports.

## Usage

Analyze and link a project directory:
```text
/link-cpp-project src/ --out pkg/
```

Run via CLI:
```bash
python3 scripts/cpp_bridge_cli.py --link /path/to/cpp_project
```

## Features

- **DAG Extraction**: Recursively discovers `.h`, `.hpp`, `.c`, and `.cpp` files.
- **Topological Sorting**: Guarantees that base data structures and types are transpiled and loaded before the algorithms that consume them.
- **Package Emission**: Creates an automated `__init__.py` file exposing all package classes and functions.
