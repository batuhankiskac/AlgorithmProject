"""Main experiment (Task 7): every algorithm x instance x seed.

    python experiments/run_experiments.py              # full protocol (~25 min with 4 workers)
    python experiments/run_experiments.py --quick      # smoke test (short budgets, 2 seeds)

Protocol: GA and TS get the same wall-clock budget (2 s tiny, 30 s n <= 50,
60 s otherwise), 10 recorded seeds each; Clarke-Wright is deterministic and
runs once. Each run is executed in its own process, at most --workers at a
time (default 4 = number of performance cores on our machine, so runs do
not compete for a core). Every solution is validated by the independent
checker before it is written. The script is resumable: runs already present
in results/runs.csv are skipped.
"""
from __future__ import annotations

import argparse
import csv
import multiprocessing as mp
import time

from common import BENCHMARKS, MEDIDRONE, RESULTS, SEEDS, TINY, budget, hardware, load, run_solver, save_json

FIELDS = ["instance", "n", "algo", "seed", "budget_s", "cost", "bks", "gap_pct", "runtime_s",
          "time_to_best_s", "iterations", "routes", "K", "feasible", "cross_arcs", "cross_routes"]


def one_run(job):
    from cvrp.checker import check
    from cvrp.solution import clean, crossings
    name, algo, seed, quick = job
    inst = load(name)
    tl = budget(inst) if not quick else min(budget(inst), 3.0)
    t0 = time.perf_counter()
    res = run_solver(algo, inst, tl, seed)
    wall = time.perf_counter() - t0
    routes = clean(res.routes)
    ok, problems, rc = check(inst, routes, res.cost)
    arcs, rcross = crossings(inst, routes)
    gap = 100.0 * (rc - inst.bks) / inst.bks if inst.bks else ""
    row = {"instance": name, "n": inst.n, "algo": algo, "seed": seed if algo != "CW" else "",
           "budget_s": tl if algo != "CW" else "", "cost": round(rc, 4), "bks": inst.bks,
           "gap_pct": round(gap, 4) if gap != "" else "", "runtime_s": round(res.elapsed or wall, 4),
           "time_to_best_s": round(res.history[-1][0], 4) if res.history else "",
           "iterations": res.iterations, "routes": len(routes), "K": inst.K, "feasible": ok,
           "cross_arcs": arcs, "cross_routes": rcross}
    if not ok:
        print(f"!! INFEASIBLE {name} {algo} {seed}: {problems}", flush=True)
    tag = f"{name}_{algo}_{seed if algo != 'CW' else 'det'}"
    save_json({"row": row, "routes": routes, "history": res.history,
               "extra": {k: v for k, v in (res.extra or {}).items() if k != "diversity"}},
              RESULTS / ("runs_quick" if quick else "runs") / f"{tag}.json")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--instances", nargs="*")
    args = ap.parse_args()
    instances = args.instances or (TINY + BENCHMARKS + [MEDIDRONE])
    seeds = SEEDS[:2] if args.quick else SEEDS
    out = RESULTS / ("runs_quick.csv" if args.quick else "runs.csv")
    done = set()
    if out.exists():
        with out.open() as f:
            for r in csv.DictReader(f):
                done.add((r["instance"], r["algo"], r["seed"]))
    jobs = []
    for name in instances:
        if (name, "CW", "") not in done:
            jobs.append((name, "CW", 0, args.quick))
        for algo in ("GA", "TS"):
            for s in seeds:
                if (name, algo, str(s)) not in done:
                    jobs.append((name, algo, s, args.quick))
    # Longest jobs first for better packing.
    jobs.sort(key=lambda j: -budget(load(j[0])) if j[1] != "CW" else 0)
    est = sum(budget(load(j[0])) for j in jobs if j[1] != "CW") / args.workers
    print(f"{len(jobs)} runs to do, ~{est/60:.1f} min with {args.workers} workers", flush=True)
    save_json(hardware() | {"workers": args.workers}, RESULTS / "hardware.json")
    new = not out.exists()
    with out.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        ctx = mp.get_context("spawn")
        with ctx.Pool(args.workers, maxtasksperchild=1) as pool:
            for row in pool.imap_unordered(one_run, jobs):
                w.writerow(row)
                f.flush()
                print(f"{row['instance']:>10} {row['algo']} seed={row['seed']!s:>4} cost={row['cost']:.2f} "
                      f"gap={row['gap_pct']}% feasible={row['feasible']}", flush=True)


if __name__ == "__main__":
    main()
