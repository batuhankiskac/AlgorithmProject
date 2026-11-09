"""Task 6: empirical validation of the per-iteration complexity.

    python experiments/scaling.py

For n in N_VALUES we generate MediDrone-style instances (Q = 100, demands
U[1,30], so a route holds L ~ 6.5 customers on average and L <= 100 always)
and measure
  * time per GA generation and per TS iteration, by running each solver
    for a small and a large iteration count and taking the difference
    (t(b) - t(a)) / (b - a), which cancels the one-off set-up cost;
  * time of one Split decoding, one OX crossover and the CW baseline;
  * delta evaluation vs. full re-evaluation of a move.
Then the slope of log(time) vs log(n) is fitted by least squares.
"""
from __future__ import annotations

import time

import numpy as np

from common import RESULTS, save_json
from cvrp.clarke_wright import clarke_wright
from cvrp.generator import generate_medidrone

N_VALUES = [25, 50, 100, 200, 400, 800]
REPEATS = 3


def per_iter(solve, inst, init, key, a, b, seed):
    times = []
    for r in range(REPEATS):
        ta = time.perf_counter(); solve(inst, 1e9, seed + r, init_routes=init, **{key: a}); ta = time.perf_counter() - ta
        tb = time.perf_counter(); solve(inst, 1e9, seed + r, init_routes=init, **{key: b}); tb = time.perf_counter() - tb
        times.append(max(tb - ta, 1e-9) / (b - a))
    return float(np.median(times))


def slope(ns, ts):
    k, c = np.polyfit(np.log(ns), np.log(ts), 1)
    return float(k), float(c)


def main():
    from cvrp import ga, moves, tabu
    from cvrp.split import split
    rows = []
    for n in N_VALUES:
        inst = generate_medidrone(1000 + n, n=n, name=f"scale-n{n}")
        t = time.perf_counter(); init = clarke_wright(inst); t_cw = time.perf_counter() - t
        tour = [c for r in init for c in r]
        t = time.perf_counter()
        for _ in range(20):
            split(inst, tour)
        t_split = (time.perf_counter() - t) / 20
        ga_gen = per_iter(ga.solve, inst, init, "max_generations", 3, 13, 1)
        ts_it = per_iter(tabu.solve, inst, init, "max_iters", 50, 550, 1)
        dv = moves.delta_vs_full_benchmark(inst, 5000, 0)
        row = {"n": n, "K": inst.K, "cw_s": t_cw, "split_s": t_split, "ga_gen_s": ga_gen, "ts_iter_s": ts_it,
               "delta_vs_full": dv}
        rows.append(row)
        print(f"n={n:4d} CW={t_cw*1e3:8.2f}ms split={t_split*1e3:7.3f}ms GA/gen={ga_gen*1e3:8.2f}ms "
              f"TS/iter={ts_it*1e3:7.3f}ms delta/full={dv}", flush=True)
    ns = [r["n"] for r in rows]
    fits = {k: slope(ns, [r[k] for r in rows]) for k in ("cw_s", "split_s", "ga_gen_s", "ts_iter_s")}
    for k, (s, _) in fits.items():
        print(f"log-log slope {k}: {s:.2f}")
    save_json({"rows": rows, "fits": fits, "n_values": N_VALUES}, RESULTS / "scaling.json")


if __name__ == "__main__":
    main()
