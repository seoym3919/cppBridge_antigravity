#include <stdio.h>
#include <stdlib.h>
#include <math.h>

typedef struct {
    double x, y, z;
    double vx, vy, vz;
    double mass;
} Body;

void compute_gravitational_forces(
    const double* pos,
    const double* mass,
    double* acc,
    int n,
    double softening
) {
    for (int i = 0; i < n; ++i) {
        double ax = 0.0;
        double ay = 0.0;
        double az = 0.0;

        for (int j = 0; j < n; ++j) {
            if (i != j) {
                double dx = pos[j * 3] - pos[i * 3];
                double dy = pos[j * 3 + 1] - pos[i * 3 + 1];
                double dz = pos[j * 3 + 2] - pos[i * 3 + 2];
                double dist_sq = dx * dx + dy * dy + dz * dz + softening * softening;
                double dist = sqrt(dist_sq);
                double inv_dist3 = 1.0 / (dist * dist * dist);
                double f = mass[j] * inv_dist3;

                ax += f * dx;
                ay += f * dy;
                az += f * dz;
            }
        }

        acc[i * 3] = ax;
        acc[i * 3 + 1] = ay;
        acc[i * 3 + 2] = az;
    }
}

void leapfrog_integrate(
    double* pos,
    double* vel,
    const double* mass,
    int n,
    double dt,
    int steps,
    double softening
) {
    double* acc = (double*)malloc(n * 3 * sizeof(double));

    for (int step = 0; step < steps; ++step) {
        compute_gravitational_forces(pos, mass, acc, n, softening);

        for (int i = 0; i < n; ++i) {
            vel[i * 3] += acc[i * 3] * dt;
            vel[i * 3 + 1] += acc[i * 3 + 1] * dt;
            vel[i * 3 + 2] += acc[i * 3 + 2] * dt;

            pos[i * 3] += vel[i * 3] * dt;
            pos[i * 3 + 1] += vel[i * 3 + 1] * dt;
            pos[i * 3 + 2] += vel[i * 3 + 2] * dt;
        }

        if (step % 10 == 0) {
            printf("Step %4d complete. Primary body pos: [%8.4f, %8.4f, %8.4f]\n", step, pos[0], pos[1], pos[2]);
        }
    }

    free(acc);
}
