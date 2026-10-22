---
name: struct-to-dataclass
description: Converts C structs, typedef structs, unions, and C++ classes into modern Python @dataclass definitions and companion contiguous NumPy structured dtypes.
---

# /struct-to-dataclass

Converts C/C++ compound types and structures into Python `@dataclass` models and companion NumPy structured `np.dtype` arrays.

## Usage

Extract and modernize structs:
```text
/struct-to-dataclass types.h
```

## Transformation Patterns

1. **C Typedef Struct to Dataclass**:
   ```c
   typedef struct {
       double x, y, z;
       double vx, vy, vz;
       double mass;
   } Body;
   ```
   Converts to:
   ```python
   from dataclasses import dataclass

   @dataclass
   class Body:
       x: float = 0.0
       y: float = 0.0
       z: float = 0.0
       vx: float = 0.0
       vy: float = 0.0
       vz: float = 0.0
       mass: float = 0.0
   ```

2. **Companion NumPy Structured Dtype (Array of Structs)**:
   ```python
   body_dtype = np.dtype([
       ('x', np.float64),
       ('y', np.float64),
       ('z', np.float64),
       ('vx', np.float64),
       ('vy', np.float64),
       ('vz', np.float64),
       ('mass', np.float64),
   ])
   ```

3. **C++ Class Methods & Operators**:
   - `operator[]` -> `__getitem__`
   - `operator()` -> `__call__`
   - `operator+` -> `__add__`
