---
name: decompile-stl
description: Decompiles C++ Standard Template Library (STL) containers (vector, array, map, set, pair) and algorithms (sort, reverse, clamp) into idiomatic Python and NumPy.
---

# /decompile-stl

Decompiles C++ STL container types and member methods into Python native types and NumPy arrays.

## Usage

Decompile STL containers:
```text
/decompile-stl containers.cpp
```

## Supported STL Mappings

| C++ STL Type / Call | Modern Python / NumPy Equivalent |
|---|---|
| `std::vector<double>` | `np.ndarray` |
| `std::vector<T>` | `list[T]` |
| `std::array<T, N>` | `np.ndarray` (shape `(N,)`) |
| `std::map<K, V>` | `dict[K, V]` |
| `std::set<T>` | `set[T]` |
| `std::pair<T1, T2>` | `tuple[T1, T2]` |
| `std::string` | `str` |
| `vec.push_back(x)` | `vec.append(x)` |
| `vec.size()` | `len(vec)` |
| `vec.empty()` | `len(vec) == 0` |
| `std::sort(v.begin(), v.end())` | `v.sort()` |
| `std::clamp(x, lo, hi)` | `max(lo, min(x, hi))` |
