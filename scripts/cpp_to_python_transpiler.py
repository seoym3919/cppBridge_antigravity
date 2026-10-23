#!/usr/bin/env python3
r"""
cpp_to_python_transpiler.py - Master C/C++ to Modern Python / NumPy Transpiler.

Converts a structured subset of C/C++ (free functions, structs, loops, conditionals):
- C/C++ functions -> typed Python functions (qualifiers such as const/unsigned handled)
- malloc / calloc / new[] -> np.zeros; local arrays `double a[N][M];` -> np.zeros((N, M))
- Structs & Classes -> Python @dataclass models
- printf / std::cout -> Python f-strings
- Operators (&&, ||, !, ->, ?:, ++/--, compound assignment) -> Python equivalents
- Integer division: C truncates; `/` between int-typed operands becomes `int(a / b)`
- Math calls (sqrt, pow, fabs, floor, ...) -> math / numpy; M_PI -> math.pi
- Pointer arithmetic -> indexing / slicing; `double *out` scalar outputs -> 1-element arrays
  (`*out = v` -> `out[0] = v`); by-reference scalars (`double &x`) are rewritten to `x[0]`
- for / while / do-while / if / else-if, with or without braces; `#pragma omp parallel for` ->
  numba `prange` + `@njit(parallel=True)`

Every emitted statement is validated with Python's parser. A statement that cannot be translated
(switch/goto, unsupported expressions, ...) becomes `raise NotImplementedError(...)` at that point,
so the result is always syntactically valid and never silently wrong about what it skipped.
Known limit: C loop bounds are re-evaluated every iteration, Python `range` evaluates them once.
"""

from __future__ import annotations

import ast
import re
from typing import Dict, List, Optional, Set, Tuple

from struct_transpiler import parse_structs_and_classes, ParsedStruct
from printf_decompiler import decompile_printf_call, decompile_cout_stream
from pointer_analyzer import analyze_pointer_allocations, decompile_pointer_arithmetic
from stl_decompiler import decompile_stl_methods
from linalg_modernizer import modernize_linalg_expressions
from boost_modernizer import modernize_boost_code

INDENT = "    "
INT_TYPES = {"int", "long", "short", "size_t", "ssize_t", "char", "unsigned", "uint8_t", "uint16_t", "uint32_t",
             "uint64_t", "int8_t", "int16_t", "int32_t", "int64_t", "ptrdiff_t", "long long", "unsigned int",
             "unsigned long", "unsigned long long", "unsigned char", "unsigned short", "signed", "signed int"}
FLOAT_TYPES = {"double", "float", "long double"}
QUALIFIERS = {"const", "static", "volatile", "register", "restrict", "__restrict", "__restrict__", "extern",
              "inline", "constexpr", "struct", "mutable", "virtual"}
MATH_FNS = ("sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "exp", "log", "log10", "log2", "hypot",
            "floor", "ceil", "fmod", "sinh", "cosh", "tanh", "log1p", "expm1", "erf", "tgamma", "lgamma", "trunc",
            "copysign", "isnan", "isinf")
MATH_CONSTS = {"M_PI": "math.pi", "M_E": "math.e", "INFINITY": "math.inf", "NAN": "math.nan",
               "M_SQRT2": "math.sqrt(2.0)", "M_PI_2": "(math.pi / 2)", "M_LN2": "math.log(2.0)"}


class FunctionContext:
    """Per-function type knowledge used for integer-division semantics and by-reference scalars."""

    def __init__(self):
        self.int_names: Set[str] = set()
        self.int_arrays: Set[str] = set()
        self.ref_scalars: Set[str] = set()
        self.struct_names: Set[str] = set()


# --------------------------------------------------------------------------------------------
# expression conversion
# --------------------------------------------------------------------------------------------

def _is_name_int(node: ast.AST, ctx: FunctionContext) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, int) and not isinstance(node.value, bool)
    if isinstance(node, ast.Name):
        return node.id in ctx.int_names
    if isinstance(node, ast.Subscript):
        base = node.value
        return isinstance(base, ast.Name) and (base.id in ctx.int_arrays or (base.id in ctx.ref_scalars and base.id in ctx.int_names))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _is_name_int(node.operand, ctx)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod)):
        return _is_name_int(node.left, ctx) and _is_name_int(node.right, ctx)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("int", "len"):
        return True
    return False


class _IntDivision(ast.NodeTransformer):
    """a / b with int-typed operands -> int(a / b) (C truncation toward zero)."""

    def __init__(self, ctx: FunctionContext):
        self.ctx = ctx

    def visit_BinOp(self, node: ast.BinOp):
        self.generic_visit(node)
        if isinstance(node.op, ast.Div) and _is_name_int(node.left, self.ctx) and _is_name_int(node.right, self.ctx):
            return ast.Call(func=ast.Name(id="int", ctx=ast.Load()), args=[node], keywords=[])
        return node


def _is_int_call(py: str) -> bool:
    """True if the expression is exactly one int(...) call."""
    try:
        body = ast.parse(py, mode="eval").body
    except SyntaxError:
        return False
    return isinstance(body, ast.Call) and isinstance(body.func, ast.Name) and body.func.id == "int"


def _split_top(text: str, sep: str) -> List[str]:
    parts, depth, cur, quote = [], 0, [], None
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    parts.append("".join(cur).strip())
    return parts


def _find_assign(text: str) -> int:
    """Index of the first top-level '=' that is a plain/compound assignment, else -1."""
    depth, quote = 0, None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "=" and depth == 0:
            prev = text[i - 1] if i else ""
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if nxt == "=" or prev in "=!<>" and prev != "" and not (prev in "<>" and text[i - 2:i] in ("<<", ">>")):
                continue
            return i
    return -1


def convert_ternary(e: str) -> str:
    """cond ? a : b -> (a if cond else b), recursively, for one expression without assignment."""
    depth, q_idx = 0, -1
    for i, ch in enumerate(e):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "?" and depth == 0:
            q_idx = i
            break
    if q_idx < 0:
        return e
    depth, nested, c_idx = 0, 0, -1
    for i in range(q_idx + 1, len(e)):
        ch = e[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "?" and depth == 0:
            nested += 1
        elif ch == ":" and depth == 0:
            if nested == 0:
                c_idx = i
                break
            nested -= 1
    if c_idx < 0:
        return e
    cond, a, b = e[:q_idx].strip(), e[q_idx + 1:c_idx].strip(), e[c_idx + 1:].strip()
    return f"({convert_ternary(a)} if {cond} else {convert_ternary(b)})"


def convert_cpp_expression_to_python(expr: str, ctx: Optional[FunctionContext] = None) -> Tuple[str, Set[str]]:
    r"""Convert a C/C++ scalar or array expression to Python (best effort; caller validates)."""
    imports: Set[str] = set()
    ctx = ctx or FunctionContext()
    e = expr.strip()

    e = decompile_stl_methods(e)
    e, linalg_imps = modernize_linalg_expressions(e)
    imports.update(linalg_imps)
    e, boost_imps = modernize_boost_code(e)
    imports.update(boost_imps)

    e = e.replace("->", ".")
    e = re.sub(r"&&", " and ", e)
    e = re.sub(r"\|\|", " or ", e)
    e = re.sub(r"!(?!=)", " not ", e)
    e = re.sub(r"\btrue\b", "True", e)
    e = re.sub(r"\bfalse\b", "False", e)
    e = re.sub(r"\b(NULL|nullptr)\b", "None", e)

    # casts: (double)(expr) / (double)x[i] / (int)x
    ident = r"[A-Za-z_][A-Za-z0-9_.]*(?:\[[^\]]*\])*"
    e = re.sub(r"\(\s*(?:double|float|long double)\s*\)\s*\(", "float(", e)
    e = re.sub(rf"\(\s*(?:double|float|long double)\s*\)\s*({ident}|\d[\d.eE+-]*)", r"float(\1)", e)
    e = re.sub(r"\(\s*(?:unsigned\s+)?(?:int|long|short|size_t|long long)\s*\)\s*\(", "int(", e)
    e = re.sub(rf"\(\s*(?:unsigned\s+)?(?:int|long|short|size_t|long long)\s*\)\s*({ident}|\d[\d.eE+-]*)", r"int(\1)", e)

    e = decompile_pointer_arithmetic(e).strip()
    for name in sorted(ctx.ref_scalars):
        e = re.sub(rf"(?<![\w.]){re.escape(name)}\b(?!\s*\[)", f"{name}[0]", e)

    for const, repl in MATH_CONSTS.items():
        if re.search(rf"\b{const}\b", e):
            imports.add("math")
            e = re.sub(rf"\b{const}\b", repl, e)
    for fn in MATH_FNS:
        pat = rf"(?<![\w.]){fn}\s*\("
        if re.search(pat, e):
            imports.add("math")
            e = re.sub(pat, f"math.{fn}(", e)
    e = re.sub(r"(?<![\w.])(?:fabs|labs|llabs)\s*\(", "abs(", e)
    e = re.sub(r"(?<![\w.])fmax\s*\(", "max(", e)
    e = re.sub(r"(?<![\w.])fmin\s*\(", "min(", e)
    if re.search(r"(?<![\w.])cbrt\s*\(", e):
        imports.add("numpy as np")
        e = re.sub(r"(?<![\w.])cbrt\s*\(", "np.cbrt(", e)
    e = re.sub(r"(?<![\w.])pow\s*\(\s*([A-Za-z0-9_\[\]]+)\s*,\s*2\s*\)", r"(\1 * \1)", e)
    for omp, repl in (("omp_get_thread_num()", "numba.get_thread_id()"), ("omp_get_num_threads()", "numba.get_num_threads()")):
        if omp in e:
            imports.add("numba")
            e = e.replace(omp, repl)

    # ternary (only on the right-hand side when the text is an assignment)
    if "?" in e:
        k = _find_assign(e)
        e = (e[:k + 1] + " " + convert_ternary(e[k + 1:].strip())) if k >= 0 else convert_ternary(e)
    e = re.sub(r"\s+", " ", e).strip()

    # integer division semantics (needs a parseable expression)
    if "/" in e and (ctx.int_names or ctx.int_arrays):
        k = _find_assign(e)
        lhs, rhs = (e[:k + 1], e[k + 1:].strip()) if k >= 0 else ("", e)
        try:
            tree = ast.parse(rhs, mode="eval")
            tree = ast.fix_missing_locations(_IntDivision(ctx).visit(tree))
            new_rhs = ast.unparse(tree.body)
            e = (lhs + " " + new_rhs).strip() if lhs else new_rhs
        except SyntaxError:
            pass
    return e, imports


# --------------------------------------------------------------------------------------------
# tokenizer
# --------------------------------------------------------------------------------------------

def tokenize(src: str) -> List[Tuple[str, str]]:
    r"""Split C/C++ source into ('pp' | 'head' | 'stmt' | 'open' | 'close', text) tokens."""
    toks: List[Tuple[str, str]] = []
    cur: List[str] = []
    depth = 0
    in_block_comment = False
    lines = src.splitlines()
    li = 0
    while li < len(lines):
        line = lines[li]
        li += 1
        if not in_block_comment and not "".join(cur).strip() and line.lstrip().startswith("#"):
            text = line.strip()
            while text.endswith("\\") and li < len(lines):
                text = text[:-1] + " " + lines[li].strip()
                li += 1
            toks.append(("pp", text))
            continue
        i, n = 0, len(line)
        while i < n:
            ch = line[i]
            if in_block_comment:
                end = line.find("*/", i)
                if end < 0:
                    i = n
                else:
                    in_block_comment = False
                    i = end + 2
                continue
            two = line[i:i + 2]
            if two == "//":
                break
            if two == "/*":
                in_block_comment = True
                i += 2
                continue
            if ch in "\"'":
                j = i + 1
                while j < n and line[j] != ch:
                    j += 2 if line[j] == "\\" else 1
                cur.append(line[i:j + 1])
                i = j + 1
                continue
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth = max(0, depth - 1)
            if depth == 0 and ch == ";":
                text = "".join(cur).strip()
                if text:
                    toks.append(("stmt", text))
                cur = []
            elif depth == 0 and ch == "{":
                text = "".join(cur).strip()
                if re.search(r"=\s*$", text):                     # initializer list: keep as text
                    j, braces = i, 0
                    buf = []
                    while True:
                        c = lines[li - 1][j] if j < len(lines[li - 1]) else "\n"
                        buf.append(c if c != "\n" else " ")
                        if c == "{":
                            braces += 1
                        elif c == "}":
                            braces -= 1
                            if braces == 0:
                                break
                        j += 1
                        if j >= len(lines[li - 1]):
                            if li >= len(lines):
                                break
                            lines[li - 1] = lines[li - 1] + " " + lines[li].strip()
                            lines.pop(li)
                    cur.append("".join(buf))
                    line = lines[li - 1]
                    n = len(line)
                    i = j + 1
                    continue
                if text:
                    toks.append(("head", text))
                toks.append(("open", ""))
                cur = []
            elif depth == 0 and ch == "}":
                text = "".join(cur).strip()
                if text:
                    toks.append(("stmt", text))
                toks.append(("close", ""))
                cur = []
            else:
                cur.append(ch)
            i += 1
        cur.append(" ")
    tail = "".join(cur).strip()
    if tail:
        toks.append(("stmt", tail))
    return toks


# --------------------------------------------------------------------------------------------
# translation
# --------------------------------------------------------------------------------------------

FUNC_RE = re.compile(
    r"^(?:extern\s+\"C\"\s+)?(?P<ret>[A-Za-z_][\w:<>,\s\*&]*?[\s\*&])(?P<name>[A-Za-z_]\w*)\s*\((?P<params>.*)\)\s*(?:const)?\s*(?:noexcept)?\s*$",
    re.S,
)
_NOT_FUNCS = {"if", "for", "while", "switch", "return", "else", "do", "sizeof", "catch"}


class Frame:
    def __init__(self, kind: str, start: int, chain: bool = False):
        self.kind = kind          # def | if | else | for | while | do | block | skip | ns
        self.start = start        # len(lines) after the header
        self.chain = chain        # closes together with the next inner frame


def _valid_stmt(py: str) -> bool:
    text = py.strip()
    if not text:
        return True
    try:
        if text.startswith(("else:", "elif ")):             # only valid after an `if`
            ast.parse("if x:\n    pass\n" + text + ("\n    pass" if text.endswith(":") else ""))
        else:
            ast.parse(text + ("\n    pass" if text.endswith(":") else ""))
        return True
    except SyntaxError:
        return False


class CppToPython:
    def __init__(self, structs: List[ParsedStruct]):
        self.out: List[str] = []
        self.imports: Set[str] = {"numpy as np", "math"}
        self.level = 0
        self.frames: List[Frame] = []
        self.ctx = FunctionContext()
        self.ctx.struct_names = {s.name for s in structs}
        self.module_ctx = self.ctx
        self.pending_prange = False
        self.pending_do_while = False
        self.uses_prange = False
        self.def_index: Optional[int] = None
        self.skip_depth = 0

    # ---------------------------------------------------------------- output helpers
    def emit(self, text: str, extra: int = 0) -> None:
        self.out.append(f"{INDENT * (self.level + extra)}{text}" if text else "")

    def emit_checked(self, py: str, raw: str, extra: int = 0) -> None:
        if _valid_stmt(py):
            self.emit(py, extra)
        else:
            self.emit(f"raise NotImplementedError({('cppBridge: untranslated C/C++ statement: ' + raw.strip())!r})", extra)

    def unsupported(self, why: str, raw: str, extra: int = 0) -> None:
        self.emit(f"raise NotImplementedError({('cppBridge: ' + why + ': ' + raw.strip())!r})", extra)

    # ---------------------------------------------------------------- driver
    def run(self, toks: List[Tuple[str, str]]) -> List[str]:
        i = 0
        while i < len(toks):
            kind, text = toks[i]
            nxt = toks[i + 1][0] if i + 1 < len(toks) else None
            if self.skip_depth:
                if kind == "open":
                    self.skip_depth += 1
                elif kind == "close":
                    self.skip_depth -= 1
                i += 1
                continue
            if kind == "pp":
                self.preprocessor(text)
            elif kind == "head":
                i += self.head(text)
                continue
            elif kind == "open":
                self.frames.append(Frame("block", len(self.out)))
                self.emit("if True:")
                self.level += 1
            elif kind == "close":
                self.close()
            else:
                self.statement(text, has_block=(nxt == "open"))
            i += 1
        return self.out

    # ---------------------------------------------------------------- top level
    def preprocessor(self, text: str) -> None:
        m = re.match(r"^#\s*define\s+([A-Za-z_]\w*)\s+(.+)$", text)
        if m and not text.startswith("#define " + m.group(1) + "("):
            val = m.group(2).strip()
            if re.match(r"^[0-9.eE+\-xXa-fA-FuUlL]+$", val):
                self.emit(f"{m.group(1)} = {re.sub(r'[uUlL]+$', '', val)}")
            else:
                expr, imp = convert_cpp_expression_to_python(val, self.ctx)
                self.imports.update(imp)
                if _valid_stmt(f"{m.group(1)} = {expr}"):
                    self.emit(f"{m.group(1)} = {expr}")
        elif re.match(r"^#\s*pragma\s+omp\s+parallel\s+for", text):
            self.pending_prange = True
        elif re.match(r"^#\s*pragma\s+omp\s+critical", text):
            self.emit("# OpenMP critical region (executed serially in Python)")
        elif re.match(r"^#\s*pragma\s+omp", text):
            self.emit(f"# {text}")

    def head(self, text: str) -> int:
        """Handle a header token (text before '{'); returns tokens consumed (head + its '{')."""
        t = re.sub(r"^template\s*<[^>]*>\s*", "", text.strip())
        if self.frames and any(f.kind in ("def", "block") for f in self.frames) or self.level > 0:
            if self.control(t, has_block=True):
                return 2
            self.unsupported("unsupported block header", t)
            self.emit("if False:")
            self.frames.append(Frame("block", len(self.out)))
            self.level += 1
            return 2
        m = FUNC_RE.match(t)
        if m and m.group("name") not in _NOT_FUNCS and not re.match(r"^(typedef|struct|class|enum|union|namespace)\b", t):
            self.begin_function(m)
            return 2
        if re.match(r"^(namespace\b|extern\s+\"C\")", t):
            self.frames.append(Frame("ns", len(self.out)))
            return 2
        self.skip_depth = 1            # struct / class / enum / union body: handled by the dataclass pass
        return 2

    def begin_function(self, m: "re.Match") -> None:
        name = m.group("name")
        params_raw = m.group("params").strip()
        self.ctx = FunctionContext()
        self.ctx.struct_names = self.module_ctx.struct_names
        py_params = []
        if params_raw and params_raw != "void":
            for p in _split_top(params_raw, ","):
                p = re.sub(r"=.*$", "", p).strip()
                if p == "...":
                    continue
                is_ptr = "*" in p or bool(re.search(r"\[\s*\w*\s*\]", p))
                is_ref = "&" in p and not is_ptr
                is_const = bool(re.search(r"\bconst\b", p))
                tokens = [t for t in re.sub(r"[*&]|\[[^\]]*\]", " ", p).split() if t not in QUALIFIERS]
                if len(tokens) >= 2:
                    ptype, pname = " ".join(tokens[:-1]), tokens[-1]
                else:
                    ptype, pname = "double", (tokens[0] if tokens else "arg")
                if is_ptr:
                    py_params.append(f"{pname}: np.ndarray")
                    if ptype in INT_TYPES:
                        self.ctx.int_arrays.add(pname)
                elif is_ref and not is_const and (ptype in INT_TYPES or ptype in FLOAT_TYPES or ptype == "bool"):
                    py_params.append(f"{pname}: np.ndarray")
                    self.ctx.ref_scalars.add(pname)
                    if ptype in INT_TYPES:
                        self.ctx.int_names.add(pname)
                elif ptype in FLOAT_TYPES:
                    py_params.append(f"{pname}: float")
                elif ptype in INT_TYPES:
                    py_params.append(f"{pname}: int")
                    self.ctx.int_names.add(pname)
                elif ptype == "bool":
                    py_params.append(f"{pname}: bool")
                else:
                    py_params.append(f"{pname}: {ptype}")
        self.def_index = len(self.out)
        self.emit(f"def {name}({', '.join(py_params)}):")
        self.frames.append(Frame("def", len(self.out)))
        self.level += 1
        doc = f"Converted from C/C++ {name}."
        if self.ctx.ref_scalars:
            doc += (f" By-reference scalars ({', '.join(sorted(self.ctx.ref_scalars))}) and pointer outputs "
                    f"are 1-element/NumPy arrays: read/write element [0].")
        self.emit(f'r"""{doc}"""')
        self.frames[-1].start = len(self.out)

    # ---------------------------------------------------------------- blocks
    def close(self) -> None:
        if not self.frames:
            return
        frame = self.frames.pop()
        if frame.kind in ("ns", "skip"):
            return
        if len(self.out) == frame.start:
            self.emit("pass")
        if frame.kind == "def":
            if self.uses_prange and self.def_index is not None:
                self.out.insert(self.def_index, "@njit(parallel=True)")
                self.uses_prange = False
            self.level = 0
            self.emit("")
            self.emit("")
            self.ctx = self.module_ctx
            self.def_index = None
            return
        self.level -= 1
        if frame.kind == "do":
            self.pending_do_while = True
        while self.frames and self.frames[-1].chain:
            outer = self.frames.pop()
            if len(self.out) == outer.start:
                self.emit("pass")
            self.level -= 1

    # ---------------------------------------------------------------- statements
    def statement(self, text: str, has_block: bool = False) -> None:
        t = text.strip()
        if not t:
            return
        if self.level == 0 and not self.frames:
            if re.match(r"^(typedef|struct|class|enum|union|using|friend)\b", t) or re.match(r"^[A-Za-z_]\w*$", t):
                return
        if self.pending_do_while:
            self.pending_do_while = False
            m = re.match(r"^while\s*\((.*)\)$", t, re.S)
            if m:
                cond = self.expr(m.group(1))
                self.emit_checked(f"if not ({cond}):", t, extra=1)       # inside the loop body
                self.emit("break", extra=2)
                return
        m_label = re.match(r"^(?!case\b|default\b)([A-Za-z_]\w*)\s*:(?!:)\s*(.*)$", t, re.S)
        if m_label and not re.match(r"^(?:public|private|protected)$", m_label.group(1)):
            self.emit(f"# label {m_label.group(1)}:")
            t = m_label.group(2).strip()
            if not t:
                return
        if self.control(t, has_block):
            return
        for py in self.simple(t):
            self.emit_checked(py, t)

    def expr(self, text: str) -> str:
        e, imp = convert_cpp_expression_to_python(text, self.ctx)
        self.imports.update(imp)
        return e

    def control(self, t: str, has_block: bool) -> bool:
        """Emit a control-flow header (and, without braces, its single-statement body). True if handled."""
        m_else_if = re.match(r"^else\s+if\s*\(", t)
        m_kw = re.match(r"^(if|while|for|switch)\s*\(", t)
        m_else = re.match(r"^else\b", t)
        m_do = re.match(r"^do\b", t)
        if not (m_else_if or m_kw or m_else or m_do):
            return False
        kind = "else"
        rest = ""
        header = ""
        if m_else_if or m_kw:
            start = t.index("(")
            depth, end = 0, -1
            for k in range(start, len(t)):
                if t[k] == "(":
                    depth += 1
                elif t[k] == ")":
                    depth -= 1
                    if depth == 0:
                        end = k
                        break
            if end < 0:
                self.unsupported("unbalanced parentheses", t)
                return True
            inner, rest = t[start + 1:end], t[end + 1:].strip()
            word = "elif" if m_else_if else m_kw.group(1)
            kind = "if" if word in ("if", "elif") else word
            if word == "switch":
                self.unsupported("switch statements are not translated", t)
                header = "if False:"
            elif word in ("if", "elif"):
                header = f"{word} {self.expr(inner)}:"
            elif word == "while":
                header = f"while {self.expr(inner)}:"
            else:
                header = self.for_header(inner, t)
        elif m_else:
            rest = t[4:].strip()
            header = "else:"
        else:
            rest = t[2:].strip()
            header = "while True:"
            kind = "do"
        if not _valid_stmt(header):
            self.unsupported("untranslated control-flow header", t)
            header = "if False:"
        # `else` / `elif` belong to the preceding if-block: emit at the same level
        self.emit(header)
        chain_frames: List[Frame] = []
        if has_block:
            frame = Frame(kind, len(self.out), chain=bool(rest))
            self.frames.append(frame)
            self.level += 1
            if rest:
                frame.start = len(self.out)
                self.control(rest, has_block=True) or self.statement(rest)
            return True
        # brace-less body: a single statement
        self.level += 1
        start = len(self.out)
        if rest:
            self.statement(rest)
        if len(self.out) == start:
            self.emit("pass")
        self.level -= 1
        return True

    def for_header(self, inner: str, raw: str) -> str:
        parts = _split_top(inner, ";")
        if len(parts) == 1:                                   # range-based for
            m = re.match(r"^(?:const\s+)?(?:auto|[\w:<>]+)\s*[&*]*\s*(\w+)\s*:\s*(.+)$", inner.strip())
            if m:
                return f"for {m.group(1)} in {self.expr(m.group(2))}:"
            self.unsupported("unsupported range-for", raw)
            return "if False:"
        if len(parts) != 3:
            self.unsupported("unsupported for header", raw)
            return "if False:"
        init, cond, incr = (p.strip() for p in parts)
        m_i = re.match(r"^(?:(?:const\s+)?(?:unsigned\s+)?(?:int|long|size_t|short|long long|auto)\s+)?(\w+)\s*=\s*(.+)$", init)
        if not m_i:
            self.unsupported("unsupported for-loop initialiser", raw)
            return "if False:"
        var, start = m_i.group(1), m_i.group(2).strip()
        if re.match(r"^(?:const\s+)?(?:unsigned\s+)?(?:int|long|size_t|short|long long|auto)\b", init):
            self.ctx.int_names.add(var)
        m1 = re.match(rf"^{re.escape(var)}\s*(<=|<|>=|>|!=)\s*(.+)$", cond)
        if m1:
            op, bound = m1.group(1), m1.group(2)
        else:                                                  # `n > i` form
            m2 = re.match(rf"^(.+?)\s*(<=|<|>=|>)\s*{re.escape(var)}$", cond)
            if not m2:
                self.unsupported("unsupported for-loop condition", raw)
                return "if False:"
            bound, op = m2.group(1), {"<": ">", "<=": ">=", ">": "<", ">=": "<="}[m2.group(2)]
        step = None
        for pat, val in ((rf"^(?:\+\+{var}|{var}\+\+)$", "1"), (rf"^(?:--{var}|{var}--)$", "-1"),
                         (rf"^{var}\s*\+=\s*(.+)$", None), (rf"^{var}\s*-=\s*(.+)$", "neg"),
                         (rf"^{var}\s*=\s*{var}\s*\+\s*(.+)$", None), (rf"^{var}\s*=\s*{var}\s*-\s*(.+)$", "neg")):
            mm = re.match(pat, incr)
            if mm:
                if val is None:
                    step = self.expr(mm.group(1))
                elif val == "neg":
                    s = self.expr(mm.group(1))
                    step = "-" + (s if re.fullmatch(r"\w+", s) else f"({s})")
                else:
                    step = val
                break
        if step is None:
            self.unsupported("unsupported for-loop increment", raw)
            return "if False:"
        start_py, bound_py = self.expr(start), self.expr(bound)
        ascending = op in ("<", "<=", "!=")
        if ascending and step.startswith("-") or (not ascending and not step.startswith("-")):
            self.unsupported("for-loop direction does not match its increment", raw)
            return "if False:"
        if op == "<=":
            bound_py = f"{bound_py} + 1"
        elif op == ">=":
            bound_py = f"{bound_py} - 1"
        fn = "range"
        if self.pending_prange:
            fn = "prange"
            self.pending_prange = False
            self.uses_prange = True
            self.imports.add("from numba import njit, prange")
        step_arg = "" if step == "1" else f", {step}"
        if start_py == "0" and step_arg == "":
            return f"for {var} in {fn}(int({bound_py})):"
        return f"for {var} in {fn}(int({start_py}), int({bound_py}){step_arg}):"

    # ---------------------------------------------------------------- simple statements
    def simple(self, t: str) -> List[str]:
        lines: List[str] = []
        if re.match(r"^(?:break|continue)$", t):
            return [t]
        m_ret = re.match(r"^return\b\s*(.*)$", t, re.S)
        if m_ret:
            return [f"return {self.expr(m_ret.group(1))}" if m_ret.group(1).strip() else "return"]
        if re.match(r"^goto\b", t):
            return [f"raise NotImplementedError({('cppBridge: goto is not translated: ' + t)!r})"]
        if re.match(r"^(case\b.*|default)\s*:", t) or re.match(r"^[A-Za-z_]\w*\s*:$", t):
            return [f"raise NotImplementedError({('cppBridge: switch/label is not translated: ' + t)!r})"]

        allocs = analyze_pointer_allocations(t + ";")
        if allocs:
            return [a["python_code"] for a in allocs]
        if re.match(r"^(?:free\s*\(|delete\b)", t):
            return []
        if re.match(r"^(?:printf|sprintf|fprintf)\b", t):
            return [decompile_printf_call(t + ";")]
        if re.search(r"(?:std::)?cout\s*<<", t):
            return [decompile_cout_stream(t + ";")]

        m_inc = re.match(r"^(?:(\+\+|--)\s*(.+)|(.+?)\s*(\+\+|--))$", t)
        if m_inc and "=" not in t:
            target = self.expr(m_inc.group(2) or m_inc.group(3))
            op = m_inc.group(1) or m_inc.group(4)
            return [f"{target} {'+=' if op == '++' else '-='} 1"]

        decl = self.declaration(t)
        if decl is not None:
            return decl

        k = _find_assign(t)
        if k >= 0:
            op_end = k
            lhs, rhs = t[:k], t[k + 1:].strip()
            m_op = re.search(r"([+\-*/%&|^]|<<|>>)$", lhs)
            aug = m_op.group(1) if m_op else ""
            lhs_core = lhs[:len(lhs) - len(aug)].strip()
            lhs_py = self.expr(lhs_core)
            rhs_py = self.expr(rhs)
            if self.is_int_target(lhs_core):
                if aug == "/":
                    return [f"{lhs_py} = int({lhs_py} / ({rhs_py}))"]
                if not aug and re.search(r"[./]|math\.|float\(", rhs_py) and not _is_int_call(rhs_py):
                    rhs_py = f"int({rhs_py})"
            # chained assignment a = b = 0 stays valid Python
            return [f"{lhs_py} {aug}= {rhs_py}"]
        return [self.expr(t)]

    def is_int_target(self, lhs: str) -> bool:
        m = re.match(r"^\*?\s*([A-Za-z_]\w*)\s*(\[.*\])?$", lhs.strip())
        if not m:
            return False
        name, sub = m.group(1), m.group(2)
        return (name in self.ctx.int_arrays) if sub else (name in self.ctx.int_names)

    DECL_RE = re.compile(
        r"^(?:(?:static|const|volatile|register|extern|constexpr|mutable)\s+)*"
        r"(?P<type>(?:unsigned\s+|signed\s+)?(?:long\s+long|long\s+double|long|short|int|char|double|float|bool|size_t|ssize_t|"
        r"u?int(?:8|16|32|64)_t|ptrdiff_t|auto|struct\s+\w+|std::[\w:]+(?:<[^;=()]*>)?|[A-Za-z_]\w*))\s*"
        r"(?P<rest>[*&\s]*[A-Za-z_]\w*\s*(?:\[.*|=.*|,.*|\(.*)?)$", re.S)

    def declaration(self, t: str) -> Optional[List[str]]:
        m = self.DECL_RE.match(t)
        if not m:
            return None
        ctype = re.sub(r"\s+", " ", m.group("type")).strip()
        base = ctype.replace("struct ", "")
        known = (ctype in INT_TYPES or ctype in FLOAT_TYPES or ctype in ("bool", "auto") or base in self.ctx.struct_names
                 or ctype.startswith("std::") or re.match(r"^u?int\d+_t$", ctype))
        if not known:
            return None
        if re.match(r"^(return|else|goto|new|delete|throw|sizeof)\b", ctype):
            return None
        rest = m.group("rest")
        if ctype.startswith("std::") is False and re.match(r"^[*&\s]*\w+\s*\(", rest) and not rest.lstrip("*& ").startswith("("):
            # `type name(args)` is a constructor call only for std:: types / structs
            if base not in self.ctx.struct_names:
                return None
        out: List[str] = []
        for decl in _split_top(rest, ","):
            d = decl.strip()
            if not d:
                continue
            md = re.match(r"^([*&\s]*)([A-Za-z_]\w*)\s*((?:\[[^\]]*\])*)\s*(?:=\s*(.+)|\((.*)\))?$", d, re.S)
            if not md:
                return None
            stars, name, dims, init, ctor = md.group(1), md.group(2), md.group(3), md.group(4), md.group(5)
            is_ptr = "*" in stars
            integral = ctype in INT_TYPES or bool(re.match(r"^u?int\d+_t$", ctype))
            np_dtype = "np.int64" if integral else "np.float64"
            if dims:
                sizes = [self.expr(s) for s in re.findall(r"\[([^\]]*)\]", dims)]
                shape = sizes[0] if len(sizes) == 1 else "(" + ", ".join(sizes) + ")"
                if base in self.ctx.struct_names:
                    out.append(f"{name} = [{base}() for _ in range({sizes[0]})]")
                elif init and init.strip().startswith("{"):
                    items = self.expr(init.strip()[1:-1])
                    out.append(f"{name} = np.array([{items}], dtype={np_dtype})")
                else:
                    out.append(f"{name} = np.zeros({shape}, dtype={np_dtype})")
                if integral:
                    self.ctx.int_arrays.add(name)
                continue
            if ctype.startswith("std::vector"):
                elem = re.search(r"<\s*([^>]+?)\s*>", ctype)
                eint = bool(elem and elem.group(1) in INT_TYPES)
                dt = "np.int64" if eint else "np.float64"
                if ctor is not None and ctor.strip():
                    args = _split_top(ctor, ",")
                    size = self.expr(args[0])
                    out.append(f"{name} = np.full({size}, {self.expr(args[1])}, dtype={dt})" if len(args) > 1
                               else f"{name} = np.zeros({size}, dtype={dt})")
                elif init and init.strip().startswith("{"):
                    out.append(f"{name} = np.array([{self.expr(init.strip()[1:-1])}], dtype={dt})")
                else:
                    out.append(f"{name} = []")
                if eint:
                    self.ctx.int_arrays.add(name)
                continue
            if ctype.startswith("std::array"):
                mm = re.search(r"<\s*([^,>]+)\s*,\s*([^>]+?)\s*>", ctype)
                dt = "np.int64" if mm and mm.group(1).strip() in INT_TYPES else "np.float64"
                out.append(f"{name} = np.zeros({self.expr(mm.group(2))}, dtype={dt})" if mm else f"{name} = None")
                continue
            if ctype.startswith("std::map") or ctype.startswith("std::unordered_map"):
                out.append(f"{name} = {{}}")
                continue
            if ctype == "std::string":
                out.append(f"{name} = {self.expr(init) if init else repr('')}")
                continue
            if base in self.ctx.struct_names:
                out.append(f"{name} = {base}()" if not is_ptr or init is None else f"{name} = {self.expr(init)}")
                continue
            if init is not None:
                value = self.expr(init)
                if integral and not is_ptr and re.search(r"[./]|math\.|float\(", value) and not _is_int_call(value):
                    value = f"int({value})"
                out.append(f"{name} = {value}")
            elif is_ptr:
                out.append(f"{name} = None")
            else:
                out.append(f"{name} = {'0' if integral else 'False' if ctype == 'bool' else '0.0'}")
            if integral and not is_ptr:
                self.ctx.int_names.add(name)
        return out


def transpile_cpp_to_python(code_text: str) -> str:
    r"""Transpile complete C/C++ source into idiomatic Python."""
    structs = parse_structs_and_classes(code_text)
    py_structs: List[str] = []
    imports = {"numpy as np", "math"}
    if structs:
        imports.add("from dataclasses import dataclass, field")
        py_structs.append("# ============================================================================")
        py_structs.append("# Data Models & Structs (Converted from C/C++)")
        py_structs.append("# ============================================================================\n")
        for s in structs:
            py_structs.append(s.emit_dataclass())
            py_structs.append("")
            py_structs.append(s.emit_numpy_dtype())
            py_structs.append("")

    tr = CppToPython(structs)
    body = tr.run(tokenize(code_text))
    imports |= tr.imports

    res = [
        "# ============================================================================",
        "# Transpiled from C/C++ to Modern Python / NumPy by cppBridge",
        "# Scaffold: review every `raise NotImplementedError` (constructs that were not",
        "# translated) and verify numerically against the C/C++ reference before use.",
        "# ============================================================================",
        "from __future__ import annotations",
    ]
    for imp in sorted(imports):
        res.append(imp if imp.startswith(("from ", "import ")) else f"import {imp}")
    res.append("\n")
    res.extend(py_structs)
    res.extend(body)
    return "\n".join(res).rstrip() + "\n"


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
    print(transpile_cpp_to_python(sample_c))
