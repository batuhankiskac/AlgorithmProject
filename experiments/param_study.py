"""Parameter sensitivity studies (Task 7).

    python experiments/param_study.py

  1. TS tabu tenure vs. gap on A-n80-k10 (tenure drawn from [t/3, t])
  2. GA mutation rate vs. gap and population diversity on A-n80-k10
  3. GA ablation: memetic local search on/off on A-n60-k9
Each setting: 5 seeds x 20 s, 4 runs in parallel.
"""
from __future__ import annotations

import csv
import multiprocessing as mp

from common import RESULTS, load, run_solver

SEEDS = [11, 23, 37, 41, 53]
T = 20.0
STUDIES = [
    ("TS tenure", "A-n80-k10", "TS", "tenure_max", [3, 7, 15, 30, 60]),
    ("GA mutation rate", "A-n80-k10", "GA", "p_mut", [0.0, 0.1, 0.2, 0.5, 0.9]),
    ("GA memetic ablation", "A-n60-k9", "GA", "memetic", [0, 1]),
]


def params_for(algo, param, value):
    if param == "tenure_max":
        return {"tenure_min": max(1, value // 3), "tenure_max": value}
    if param == "memetic":
        return {"memetic": bool(value)}
    return {param: value}


def job(args):
    study, name, algo, param, value, seed = args
    from cvrp.checker import check
    from cvrp.solution import clean
    inst = load(name)
    res = run_solver(algo, inst, T, seed, params=params_for(algo, param, value))
    routes = clean(res.routes)
    ok, probs, rc = check(inst, routes, res.cost)
    div = res.extra.get("diversity") if res.extra else None
    final_div = float(sum(div[-10:]) / len(div[-10:])) if div else ""
    return {"study": study, "instance": name, "algo": algo, "param": param, "value": value, "seed": seed,
            "cost": rc, "gap_pct": 100 * (rc - inst.bks) / inst.bks, "feasible": ok,
            "iterations": res.iterations, "diversity": final_div}


def main():
    jobs = [(s, n, a, p, v, seed) for s, n, a, p, vals in STUDIES for v in vals for seed in SEEDS]
    print(f"{len(jobs)} runs, ~{len(jobs) * T / 4 / 60:.1f} min", flush=True)
    out = RESULTS / "param_study.csv"
    with out.open("w", newline="") as f, mp.get_context("spawn").Pool(4, maxtasksperchild=1) as pool:
        w = None
        for row in pool.imap_unordered(job, jobs):
            if w is None:
                w = csv.DictWriter(f, fieldnames=list(row))
                w.writeheader()
            w.writerow(row); f.flush()
            print(row, flush=True)


if __name__ == "__main__":
    main()
