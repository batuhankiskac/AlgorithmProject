"""Shared helpers for all experiment scripts."""
from __future__ import annotations

import json
import platform
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
DATA = ROOT / "data"

BENCHMARKS = ["A-n32-k5", "A-n45-k6", "A-n60-k9", "A-n80-k10"]
TINY = ["tiny-n7", "tiny-n8", "tiny-n9"]
MEDIDRONE = "MediDrone"
SEEDS = [11, 23, 37, 41, 53, 67, 79, 83, 97, 101]   # recorded seeds, 10 runs


def load(name: str):
    from cvrp.generator import load_instance
    from cvrp.instance import load_benchmark
    if name in BENCHMARKS:
        return load_benchmark(name)
    if name in TINY:
        return load_instance(DATA / "tiny" / f"{name}.json")
    if name == MEDIDRONE:
        return load_instance(DATA / "medidrone" / "medidrone.json")
    raise KeyError(name)


def budget(inst) -> float:
    """Equal wall-clock budget for GA and TS (assignment: 30 s for n <= 50, 60 s above)."""
    if inst.n <= 10:
        return 2.0
    return 30.0 if inst.n <= 50 else 60.0


def run_solver(algo: str, inst, time_limit: float, seed: int, params=None, **kw):
    """Uniform entry point. GA and TS are seeded with the Clarke-Wright solution."""
    from cvrp.clarke_wright import clarke_wright
    from cvrp.solution import Result, total_cost
    if algo == "CW":
        t = time.perf_counter()
        routes = clarke_wright(inst)
        el = time.perf_counter() - t
        return Result(routes=routes, cost=total_cost(inst, routes), history=[(el, total_cost(inst, routes))],
                      iterations=1, elapsed=el)
    init = clarke_wright(inst)
    if algo == "GA":
        from cvrp import ga
        return ga.solve(inst, time_limit, seed, params=params, init_routes=init, **kw)
    if algo == "TS":
        from cvrp import tabu
        return tabu.solve(inst, time_limit, seed, params=params, init_routes=init, **kw)
    raise KeyError(algo)


def hardware() -> dict:
    def sh(cmd):
        try:
            return subprocess.check_output(cmd, shell=True, text=True).strip()
        except Exception:
            return "?"
    return {"cpu": sh("sysctl -n machdep.cpu.brand_string"),
            "cores": sh("sysctl -n hw.ncpu"),
            "perf_cores": sh("sysctl -n hw.perflevel0.physicalcpu"),
            "memory_gb": round(int(sh("sysctl -n hw.memsize") or 0) / 2**30, 1),
            "os": platform.platform(), "python": platform.python_version()}


def save_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1))
