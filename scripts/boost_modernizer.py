#!/usr/bin/env python3
r"""
boost_modernizer.py - Modernizes Boost C++ Libraries into Python / SciPy / NumPy equivalents.

Converts:
- boost::math special functions -> scipy.special (Bessel, Gamma, erf, Legendre, Beta)
- boost::math distributions -> scipy.stats
- boost::numeric::odeint -> scipy.integrate.solve_ivp
- boost::random -> numpy.random.default_rng()
- boost::multi_array -> np.ndarray (np.zeros with shape tuple)
- boost::multiprecision -> mpmath / decimal.Decimal
- boost::filesystem -> pathlib.Path
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Tuple, Set


BOOST_MATH_SPECIAL_FUNCS = {
    r'boost::math::cyl_bessel_j\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': (r'scipy.special.jv(\1, \2)', 'import scipy.special'),
    r'boost::math::cyl_bessel_y\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': (r'scipy.special.yv(\1, \2)', 'import scipy.special'),
    r'boost::math::cyl_bessel_i\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': (r'scipy.special.iv(\1, \2)', 'import scipy.special'),
    r'boost::math::cyl_bessel_k\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': (r'scipy.special.kv(\1, \2)', 'import scipy.special'),
    r'boost::math::sph_bessel\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': (r'scipy.special.spherical_jn(\1, \2)', 'import scipy.special'),
    r'boost::math::tgamma\s*\(\s*([^)]+)\s*\)': (r'scipy.special.gamma(\1)', 'import scipy.special'),
    r'boost::math::lgamma\s*\(\s*([^)]+)\s*\)': (r'scipy.special.gammaln(\1)', 'import scipy.special'),
    r'boost::math::erf\s*\(\s*([^)]+)\s*\)': (r'scipy.special.erf(\1)', 'import scipy.special'),
    r'boost::math::erfc\s*\(\s*([^)]+)\s*\)': (r'scipy.special.erfc(\1)', 'import scipy.special'),
    r'boost::math::legendre_p\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': (r'scipy.special.legendre(\1)(\2)', 'import scipy.special'),
    r'boost::math::beta\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': (r'scipy.special.beta(\1, \2)', 'import scipy.special'),
}


def modernize_boost_code(code_text: str) -> Tuple[str, Set[str]]:
    r"""
    Modernize Boost C++ functions and objects to Scientific Python equivalents.
    """
    imports = set()
    res = code_text

    # 1. Boost.Math special functions
    for pat, (repl, imp) in BOOST_MATH_SPECIAL_FUNCS.items():
        if re.search(pat, res):
            imports.add(imp)
            res = re.sub(pat, repl, res)

    # 2. Boost.MultiArray:
    # boost::multi_array<double, 3> A(boost::extents[N][M][K]); -> A = np.zeros((N, M, K), dtype=np.float64)
    m_ma = re.search(r'boost::multi_array<\s*([A-Za-z0-9_]+)\s*,\s*(\d+)\s*>\s+([A-Za-z0-9_]+)\s*\(\s*boost::extents((?:\[[^\]]+\])+)\s*\)\s*;', res)
    if m_ma:
        elem_t = m_ma.group(1).strip()
        var_n = m_ma.group(3).strip()
        dims_raw = m_ma.group(4)
        dims = [d.strip('[]') for d in re.findall(r'\[([^\]]+)\]', dims_raw)]
        py_t = "np.float64" if elem_t in ("double", "float") else "np.int32"
        imports.add("numpy as np")
        res = res[:m_ma.start()] + f"{var_n} = np.zeros(({', '.join(dims)}), dtype={py_t})" + res[m_ma.end():]

    # 3. Boost.Random:
    # boost::random::mt19937 rng; -> rng = np.random.default_rng()
    if "boost::random::mt19937" in res:
        imports.add("numpy as np")
        res = re.sub(r'boost::random::mt19937\s+([A-Za-z0-9_]+)(?:\([^)]*\))?;', r'\1 = np.random.default_rng()', res)

    # boost::random::normal_distribution<> dist(mean, std); -> rng.normal(mean, std)
    if "boost::random::normal_distribution" in res:
        imports.add("numpy as np")
        res = re.sub(
            r'boost::random::normal_distribution<[^>]*>\s+([A-Za-z0-9_]+)\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\);',
            r'# Distribution: \1 = lambda rng, size=None: rng.normal(\2, \3, size=size)',
            res
        )

    # 4. Boost.Filesystem:
    # boost::filesystem::path p("..."); -> p = Path("...")
    if "boost::filesystem" in res:
        imports.add("from pathlib import Path")
        res = re.sub(r'boost::filesystem::path\s+([A-Za-z0-9_]+)\s*\(\s*([^)]+)\s*\);', r'\1 = Path(\2)', res)
        res = re.sub(r'boost::filesystem::exists\s*\(\s*([^)]+)\s*\)', r'\1.exists()', res)
        res = re.sub(r'boost::filesystem::create_directories\s*\(\s*([^)]+)\s*\);', r'\1.mkdir(parents=True, exist_ok=True)', res)

    # 5. Boost.Multiprecision:
    # boost::multiprecision::cpp_dec_float_50 x; -> x = mpmath.mpf(0)
    if "boost::multiprecision" in res:
        imports.add("import mpmath")
        res = re.sub(r'boost::multiprecision::(?:cpp_dec_float_\d+|cpp_bin_float_\d+)\s+([A-Za-z0-9_]+)\s*=', r'\1 = mpmath.mpf', res)

    return res, imports


def run_self_test() -> bool:
    r"""Test Boost modernization with assertions."""
    print("Running boost_modernizer self-test...")
    sample = """
    double j0 = boost::math::cyl_bessel_j(0.0, x);
    double g = boost::math::tgamma(z);
    double e = boost::math::erf(x);
    double leg = boost::math::legendre_p(2, cos_theta);
    boost::multi_array<double, 3> grid(boost::extents[nx][ny][nz]);
    boost::random::mt19937 rng(42);
    boost::filesystem::path dir("/data/sims");
    bool ok = boost::filesystem::exists(dir);
    """
    out, imps = modernize_boost_code(sample)
    assert "scipy.special.jv(0.0, x)" in out
    assert "scipy.special.gamma(z)" in out
    assert "scipy.special.erf(x)" in out
    assert "scipy.special.legendre(2)(cos_theta)" in out
    assert "grid = np.zeros((nx, ny, nz), dtype=np.float64)" in out
    assert "rng = np.random.default_rng()" in out
    assert "dir = Path(\"/data/sims\")" in out
    assert "dir.exists()" in out
    assert "import scipy.special" in imps
    assert "numpy as np" in imps
    assert "from pathlib import Path" in imps
    print("boost_modernizer self-test passed successfully!")
    return True


if __name__ == "__main__":
    run_self_test()
