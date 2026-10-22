---
name: decompile-printf
description: Decompiles legacy C printf/sprintf/fprintf format descriptors and C++ std::cout stream chains into Python 3 f-strings with precision specifiers.
---

# /decompile-printf

Decompiles C formatted I/O (`printf`, `sprintf`, `fprintf`) and C++ `std::cout` stream pipelines into clean, modern Python 3 f-strings.

## Usage

Decompile format strings:
```text
/decompile-printf io_routines.c
```

## Supported Format Conversions

| C / C++ Statement | Transpiled Python Equivalent |
|---|---|
| `printf("Energy: %12.6f\n", energy);` | `print(f"Energy: {energy:12.6f}")` |
| `sprintf(buf, "%s_%04d.dat", name, frame);` | `buf = f"{name}_{frame:04d}.dat"` |
| `fprintf(stderr, "Error %d\n", code);` | `import sys; print(f"Error {code}", file=sys.stderr)` |
| `std::cout << "Step: " << i << std::endl;` | `print(f"Step: {i}")` |

All precision modifiers (`.6f`, `.12e`), field width padding (`10d`, `05d`), and alignment flags are preserved.
