---
name: modernize-boost
description: Translates Boost C++ libraries (boost::math special functions, boost::multi_array, boost::random, boost::filesystem) into Python, SciPy, and NumPy equivalents.
disable-model-invocation: true
---

# /modernize-boost

Translates Boost C++ libraries into standard Scientific Python equivalents using SciPy, NumPy, and standard library modules.

## Usage

Modernize Boost libraries in C++ source:
```text
/modernize-boost special_functions.cpp
```

## Boost Modernization Mappings

| Boost Component | Modern Python / SciPy / NumPy Equivalent |
|---|---|
| `boost::math::cyl_bessel_j(nu, x)` | `scipy.special.jv(nu, x)` |
| `boost::math::cyl_bessel_y(nu, x)` | `scipy.special.yv(nu, x)` |
| `boost::math::tgamma(x)` | `scipy.special.gamma(x)` |
| `boost::math::lgamma(x)` | `scipy.special.gammaln(x)` |
| `boost::math::erf(x)` | `scipy.special.erf(x)` |
| `boost::math::legendre_p(n, x)` | `scipy.special.legendre(n)(x)` |
| `boost::math::beta(a, b)` | `scipy.special.beta(a, b)` |
| `boost::multi_array<double, 3>` | `np.zeros((n1, n2, n3), dtype=np.float64)` |
| `boost::random::mt19937` | `np.random.default_rng()` |
| `boost::filesystem::path` | `pathlib.Path` |
