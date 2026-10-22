#!/usr/bin/env python3
r"""
printf_decompiler.py - Decompiles C printf/sprintf/fprintf and C++ std::cout to Python f-Strings.

Converts:
- printf("Value: %10.5f, ID: %d\n", val, id) -> print(f"Value: {val:10.5f}, ID: {id}")
- sprintf(buf, "%s_%04d.dat", prefix, frame) -> buf = f"{prefix}_{frame:04d}.dat"
- std::cout << "Energy: " << energy << " Step: " << step << std::endl;
  -> print(f"Energy: {energy} Step: {step}")
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple


def decompile_printf_format(format_str: str, args: List[str]) -> str:
    r"""
    Convert a printf format string and its argument tokens into a Python f-string body.
    """
    arg_idx = 0
    # Match standard C format specifiers: %[flags][width][.precision][length]specifier
    spec_pat = re.compile(r'%([+\- #0]*)(\d+)?(?:\.(\d+))?([hljztL]*)([diuoxXfFeEgGaAcsp%])')

    def spec_repl(match):
        nonlocal arg_idx
        flags = match.group(1) or ""
        width = match.group(2) or ""
        prec = match.group(3)
        spec = match.group(5)

        if spec == '%':
            return "%"

        if arg_idx < len(args):
            arg_name = args[arg_idx].strip()
            arg_idx += 1
        else:
            arg_name = f"arg{arg_idx}"
            arg_idx += 1

        # Build Python format specifier
        fmt_body = ""
        if flags or width or prec:
            fmt_body += ":"
            if '0' in flags:
                fmt_body += "0"
            if '-' in flags:
                fmt_body += "<"
            if '+' in flags:
                fmt_body += "+"
            if width:
                fmt_body += width
            if prec is not None:
                fmt_body += f".{prec}"

            # Type mapping
            if spec in ('d', 'i', 'u', 'x', 'X'):
                fmt_body += "d" if spec in ('d', 'i', 'u') else spec.lower()
            elif spec in ('f', 'F'):
                fmt_body += "f"
            elif spec in ('e', 'E'):
                fmt_body += "e"
            elif spec in ('g', 'G'):
                fmt_body += "g"
            elif spec == 's':
                fmt_body += "s"
        else:
            if spec in ('e', 'E'):
                fmt_body = ":e"
            elif spec in ('f', 'F'):
                fmt_body = ":f"
            elif spec in ('x', 'X'):
                fmt_body = f":{spec.lower()}"

        return f"{{{arg_name}{fmt_body}}}"

    res = spec_pat.sub(spec_repl, format_str)
    # Strip trailing \n if present for Python print()
    if res.endswith(r'\n'):
        res = res[:-2]
    elif res.endswith('\n'):
        res = res[:-1]
    return res


def decompile_printf_call(statement: str) -> str:
    r"""
    Decompile a complete C printf, sprintf, or fprintf statement.
    """
    s = statement.strip().rstrip(';')

    # 1. sprintf(buf, fmt, args...)
    m_sprintf = re.match(r'^sprintf\s*\(\s*([A-Za-z0-9_]+)\s*,\s*("[^"]*")(?:\s*,\s*(.*))?\)$', s)
    if m_sprintf:
        dest = m_sprintf.group(1)
        fmt = m_sprintf.group(2)[1:-1]
        args_raw = m_sprintf.group(3)
        args = [a.strip() for a in args_raw.split(',')] if args_raw else []
        fstr = decompile_printf_format(fmt, args)
        return f'{dest} = f"{fstr}"'

    # 2. printf(fmt, args...)
    m_printf = re.match(r'^printf\s*\(\s*("[^"]*")(?:\s*,\s*(.*))?\)$', s)
    if m_printf:
        fmt = m_printf.group(1)[1:-1]
        args_raw = m_printf.group(2)
        args = [a.strip() for a in args_raw.split(',')] if args_raw else []
        fstr = decompile_printf_format(fmt, args)
        return f'print(f"{fstr}")'

    # 3. fprintf(stderr, fmt, args...)
    m_fprintf = re.match(r'^fprintf\s*\(\s*(stderr|stdout)\s*,\s*("[^"]*")(?:\s*,\s*(.*))?\)$', s)
    if m_fprintf:
        stream = m_fprintf.group(1)
        fmt = m_fprintf.group(2)[1:-1]
        args_raw = m_fprintf.group(3)
        args = [a.strip() for a in args_raw.split(',')] if args_raw else []
        fstr = decompile_printf_format(fmt, args)
        if stream == "stderr":
            return f'import sys; print(f"{fstr}", file=sys.stderr)'
        return f'print(f"{fstr}")'

    return f"# {statement}"


def decompile_cout_stream(statement: str) -> str:
    r"""
    Decompile a C++ std::cout << a << " " << b << std::endl; statement.
    """
    s = statement.strip().rstrip(';')
    # Match std::cout << ...
    if not re.search(r'(?:std::)?cout\s*<<', s):
        return f"# {statement}"

    parts = re.split(r'\s*<<\s*', s)
    # Filter out 'cout' or 'std::cout'
    parts = [p for p in parts if not re.match(r'^(?:std::)?cout$', p)]

    fstring_tokens = []
    for p in parts:
        p_clean = p.strip()
        if p_clean in ("std::endl", "endl", "'\\n'", '"\\n"'):
            continue
        # String literal
        if (p_clean.startswith('"') and p_clean.endswith('"')) or (p_clean.startswith("'") and p_clean.endswith("'")):
            fstring_tokens.append(p_clean[1:-1])
        else:
            fstring_tokens.append(f"{{{p_clean}}}")

    body = "".join(fstring_tokens)
    return f'print(f"{body}")'


if __name__ == "__main__":
    p1 = 'printf("Energy: %12.6f J, Iteration: %05d, Delta: %e\\n", energy, step, delta);'
    print("C printf:")
    print(" Input: ", p1)
    print(" Output:", decompile_printf_call(p1))

    p2 = 'sprintf(filename, "%s_frame_%04d.dat", prefix, frame_id);'
    print("\nC sprintf:")
    print(" Input: ", p2)
    print(" Output:", decompile_printf_call(p2))

    p3 = 'std::cout << "Mass: " << mass << " Radius: " << r << std::endl;'
    print("\nC++ cout:")
    print(" Input: ", p3)
    print(" Output:", decompile_cout_stream(p3))
