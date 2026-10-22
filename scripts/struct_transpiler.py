#!/usr/bin/env python3
r"""
struct_transpiler.py - Transpiles C/C++ Structs and Classes into Python Dataclasses and NumPy Dtypes.

Converts:
1. C struct / typedef struct -> Python @dataclass
2. C++ class with member variables & methods -> Python class with __init__
3. Memory Layout -> Optional NumPy structured dtype for vectorized array-of-structures
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple, Optional


C_TYPE_TO_PYTHON = {
    "double": "float",
    "float": "float",
    "int": "int",
    "long": "int",
    "long long": "int",
    "short": "int",
    "char": "str",
    "bool": "bool",
    "size_t": "int",
    "uint32_t": "int",
    "uint64_t": "int",
    "int32_t": "int",
    "int64_t": "int",
    "unsigned int": "int",
    "unsigned long": "int"
}

C_TYPE_TO_NUMPY = {
    "double": "np.float64",
    "float": "np.float32",
    "int": "np.int32",
    "long": "np.int64",
    "long long": "np.int64",
    "short": "np.int16",
    "char": "'S1'",
    "bool": "np.bool_",
    "size_t": "np.uint64",
    "uint32_t": "np.uint32",
    "uint64_t": "np.uint64",
    "int32_t": "np.int32",
    "int64_t": "np.int64"
}


class StructField:
    def __init__(self, name: str, c_type: str, array_size: Optional[str] = None):
        self.name = name.strip()
        self.c_type = c_type.strip()
        self.array_size = array_size.strip() if array_size else None

    @property
    def py_type(self) -> str:
        base = C_TYPE_TO_PYTHON.get(self.c_type, "Any")
        if self.array_size:
            return "np.ndarray"
        return base

    @property
    def py_default(self) -> str:
        if self.array_size:
            np_t = C_TYPE_TO_NUMPY.get(self.c_type, "np.float64")
            return f"field(default_factory=lambda: np.zeros({self.array_size}, dtype={np_t}))"
        if self.c_type in ("double", "float"):
            return "0.0"
        elif self.c_type == "bool":
            return "False"
        elif self.c_type == "char":
            return '""'
        return "0"

    def to_dataclass_line(self) -> str:
        return f"    {self.name}: {self.py_type} = {self.py_default}"

    def to_numpy_dtype_tuple(self) -> str:
        np_t = C_TYPE_TO_NUMPY.get(self.c_type, "np.float64")
        if self.array_size:
            return f"('{self.name}', {np_t}, ({self.array_size},))"
        return f"('{self.name}', {np_t})"


class ParsedStruct:
    def __init__(self, name: str, is_class: bool = False):
        self.name = name
        self.is_class = is_class
        self.fields: List[StructField] = []

    @property
    def kind(self) -> str:
        return "class" if self.is_class else "struct"

    def add_field(self, name: str, c_type: str, array_size: Optional[str] = None):
        self.fields.append(StructField(name, c_type, array_size))

    def emit_dataclass(self) -> str:
        lines = [
            "@dataclass",
            f"class {self.name}:"
        ]
        if not self.fields:
            lines.append("    pass")
        for f in self.fields:
            lines.append(f.to_dataclass_line())
        return "\n".join(lines)

    def emit_numpy_dtype(self) -> str:
        lines = [
            f"{self.name.lower()}_dtype = np.dtype(["
        ]
        for f in self.fields:
            lines.append(f"    {f.to_numpy_dtype_tuple()},")
        lines.append("])")
        return "\n".join(lines)


def parse_structs_and_classes(code_text: str) -> List[ParsedStruct]:
    r"""Extract all struct and class definitions from C/C++ code."""
    structs = []

    # Strip block comments
    clean_code = re.sub(r'/\*.*?\*/', '', code_text, flags=re.DOTALL)
    # Strip line comments
    clean_code = re.sub(r'//.*$', '', clean_code, flags=re.MULTILINE)

    # 1. Match typedef struct { ... } Name;
    typedef_pat = re.compile(r'typedef\s+struct\s*(?:[A-Za-z0-9_]+)?\s*\{([^}]+)\}\s*([A-Za-z0-9_]+)\s*;')
    for m in typedef_pat.finditer(clean_code):
        body = m.group(1)
        name = m.group(2)
        ps = ParsedStruct(name)
        _parse_fields(body, ps)
        structs.append(ps)

    # 2. Match struct Name { ... };
    struct_pat = re.compile(r'\bstruct\s+([A-Za-z0-9_]+)\s*\{([^}]+)\}\s*;')
    for m in struct_pat.finditer(clean_code):
        name = m.group(1)
        body = m.group(2)
        # Avoid duplicate if already matched by typedef
        if not any(s.name == name for s in structs):
            ps = ParsedStruct(name)
            _parse_fields(body, ps)
            structs.append(ps)

    # 3. Match class Name { ... };
    class_pat = re.compile(r'\bclass\s+([A-Za-z0-9_]+)(?:\s*:\s*[^{]+)?\s*\{([^}]+)\}\s*;')
    for m in class_pat.finditer(clean_code):
        name = m.group(1)
        body = m.group(2)
        if not any(s.name == name for s in structs):
            ps = ParsedStruct(name, is_class=True)
            _parse_fields(body, ps)
            structs.append(ps)

    return structs


def _parse_fields(body: str, ps: ParsedStruct):
    r"""Parse variable declarations inside struct/class body."""
    statements = [s.strip() for s in body.split(';') if s.strip()]
    type_pat = re.compile(r'^(unsigned\s+(?:int|long|short|char)|long\s+long|double|float|int|short|char|bool|size_t|[A-Za-z0-9_]+)\s+(.*)$')

    for stmt in statements:
        if any(stmt.startswith(kw) for kw in ("public:", "private:", "protected:", "friend")):
            continue
        if '(' in stmt and ')' in stmt:
            continue

        m = type_pat.match(stmt)
        if m:
            c_type = m.group(1).strip()
            vars_list = [v.strip() for v in m.group(2).split(',')]
            for vd in vars_list:
                m_arr = re.match(r'^([A-Za-z0-9_]+)\s*\[([^\]]+)\]$', vd)
                if m_arr:
                    ps.add_field(m_arr.group(1), c_type, m_arr.group(2))
                else:
                    ps.add_field(vd, c_type)


if __name__ == "__main__":
    sample = """
    typedef struct {
        double x, y, z;
        double vx, vy, vz;
        double mass;
        int id;
        double history[10];
    } Particle;

    struct SimulationConfig {
        double dt;
        double softening;
        int total_steps;
        bool enable_gravity;
    };
    """
    print("[struct_transpiler] Parsing C structs:")
    parsed = parse_structs_and_classes(sample)
    for s in parsed:
        print("\n" + "=" * 60)
        print(s.emit_dataclass())
        print("\n" + s.emit_numpy_dtype())
