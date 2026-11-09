"""How does the Bosphorus penalty change the routes? (Task 7 discussion)

    python experiments/bosphorus.py

Solves the MediDrone instance twice with Tabu Search (best of 3 seeds,
60 s each): once with the real penalty P = 150 and once with P = 0 (same
coordinates and demands), then counts crossing arcs/routes and the pure
Euclidean length of both plans.
"""
from __future__ import annotations

import math
import multiprocessing as mp

from common import MEDIDRONE, RESULTS, load, run_solver, save_json

SEEDS = [11, 23, 37]
T = 60.0


def job(args):
    penalty, seed = args
    from cvrp.generator import make_instance
    base = load(MEDIDRONE)
    inst = make_instance(f"MediDrone-P{penalty}", base.coords, base.demand, base.Q, base.K, penalty=penalty)
    res = run_solver("TS", inst, T, seed)
    return penalty, seed, res.cost, res.routes


def euclid(inst, routes):
    xy = inst.coords
    tot = 0.0
    for r in routes:
        p = [0] + r + [0]
        tot += sum(math.dist(xy[a], xy[b]) for a, b in zip(p, p[1:]))
    return tot


def main():
    from cvrp.checker import check
    from cvrp.generator import make_instance
    from cvrp.solution import clean, crossings
    base = load(MEDIDRONE)
    with mp.get_context("spawn").Pool(4) as pool:
        out = pool.map(job, [(p, s) for p in (0.0, 150.0) for s in SEEDS])
    res = {}
    for penalty in (0.0, 150.0):
        runs = [o for o in out if o[0] == penalty]
        _, seed, cost, routes = min(runs, key=lambda o: o[2])
        routes = clean(routes)
        inst = make_instance("x", base.coords, base.demand, base.Q, base.K, penalty=penalty)
        ok, probs, rc = check(inst, routes, cost, penalty=penalty)
        assert ok, probs
        arcs, rcross = crossings(inst, routes)
        key = f"P{int(penalty)}"
        res[key] = {"penalty": penalty, "seed": seed, "cost": rc, "routes_n": len(routes), "cross_arcs": arcs,
                    "cross_routes": rcross, "euclid": euclid(inst, routes), "routes": routes,
                    "all_costs": [o[2] for o in runs]}
        print(key, {k: v for k, v in res[key].items() if k != "routes"})
    save_json(res, RESULTS / "bosphorus.json")


if __name__ == "__main__":
    main()
