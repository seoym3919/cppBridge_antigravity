# ============================================================================
# Transpiled from C/C++ to Modern Python / NumPy by cppBridge
# ============================================================================
from __future__ import annotations
from dataclasses import dataclass, field
import math
import numpy as np


# ============================================================================
# Data Models & Structs (Converted from C/C++)
# ============================================================================

@dataclass
class Body:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    mass: float = 0.0

body_dtype = np.dtype([
    ('x', np.float64),
    ('y', np.float64),
    ('z', np.float64),
    ('vx', np.float64),
    ('vy', np.float64),
    ('vz', np.float64),
    ('mass', np.float64),
])

def compute_gravitational_forces(pos: np.ndarray, mass: np.ndarray, acc: np.ndarray, n: int, softening: float):
    r"""Converted from C/C++ compute_gravitational_forces."""
    for i in range(int(n)):
        ax = 0.0
        ay = 0.0
        az = 0.0

        for j in range(int(n)):
            if i != j:
                dx = pos[j * 3] - pos[i * 3]
                dy = pos[j * 3 + 1] - pos[i * 3 + 1]
                dz = pos[j * 3 + 2] - pos[i * 3 + 2]
                dist_sq = dx * dx + dy * dy + dz * dz + softening * softening
                dist = math.sqrt(dist_sq)
                inv_dist3 = 1.0 / (dist * dist * dist)
                f = mass[j] * inv_dist3

                ax += f * dx
                ay += f * dy
                az += f * dz

        acc[i * 3] = ax
        acc[i * 3 + 1] = ay
        acc[i * 3 + 2] = az

def leapfrog_integrate(pos: np.ndarray, vel: np.ndarray, mass: np.ndarray, n: int, dt: float, steps: int, softening: float):
    r"""Converted from C/C++ leapfrog_integrate."""
    acc = np.zeros(n * 3, dtype=np.float64)

    for step in range(int(steps)):
        compute_gravitational_forces(pos, mass, acc, n, softening)

        for i in range(int(n)):
            vel[i * 3] += acc[i * 3] * dt
            vel[i * 3 + 1] += acc[i * 3 + 1] * dt
            vel[i * 3 + 2] += acc[i * 3 + 2] * dt

            pos[i * 3] += vel[i * 3] * dt
            pos[i * 3 + 1] += vel[i * 3 + 1] * dt
            pos[i * 3 + 2] += vel[i * 3 + 2] * dt

        if step % 10 == 0:
            print(f"Step {step:4d} complete. Primary body pos: [{pos[0]:8.4f}, {pos[1]:8.4f}, {pos[2]:8.4f}]")

