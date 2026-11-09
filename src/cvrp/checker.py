"""Independent feasibility checker.

Deliberately does NOT reuse solution.py: it recomputes every distance from
the raw coordinates (and side penalty) so that a bug in the shared distance
matrix or in the solvers' cost bookkeeping cannot hide itself.
"""
from __future__ import annotations

import math

from .instance import Instance


def _dist(inst: Instance, a: int, b: int, rounded: bool, penalty: float) -> float:
    (x1, y1), (x2, y2) = inst.coords[a], inst.coords[b]
    e = math.hypot(x1 - x2, y1 - y2)
    if rounded:
        return int(e + 0.5)
    if inst.side is not None and inst.side[a] != inst.side[b]:
        e += penalty
    return e


def check(inst: Instance, routes, reported_cost: float | None = None,
          penalty: float = 150.0, tol: float = 1e-6) -> tuple[bool, list[str], float]:
    """Validate a solution. Returns (ok, list of problems, recomputed cost)."""
    problems: list[str] = []
    rounded = inst.side is None          # CVRPLIB instances use nint distances
    seen: dict[int, int] = {}
    nonempty = [r for r in routes if len(r) > 0]
    if len(nonempty) > inst.K:
        problems.append(f"uses {len(nonempty)} routes > K={inst.K}")
    cost = 0.0
    for ri, r in enumerate(nonempty):
        load = 0
        for v in r:
            if not isinstance(v, (int,)) and not hasattr(v, "__index__"):
                problems.append(f"route {ri}: non-integer vertex {v!r}")
                continue
            v = int(v)
            if v == 0:
                problems.append(f"route {ri}: depot inside route")
            elif not 1 <= v <= inst.n:
                problems.append(f"route {ri}: unknown vertex {v}")
            else:
                seen[v] = seen.get(v, 0) + 1
                load += int(inst.demand[v])
        if load > inst.Q:
            problems.append(f"route {ri}: load {load} > Q={inst.Q}")
        path = [0] + [int(v) for v in r] + [0]
        cost += sum(_dist(inst, a, b, rounded, penalty) for a, b in zip(path, path[1:]))
    missing = [v for v in range(1, inst.n + 1) if v not in seen]
    dup = [v for v, c in seen.items() if c > 1]
    if missing:
        problems.append(f"customers not served: {missing[:10]}{'...' if len(missing) > 10 else ''}")
    if dup:
        problems.append(f"customers served more than once: {dup[:10]}")
    if reported_cost is not None and abs(cost - reported_cost) > tol * max(1.0, abs(cost)):
        problems.append(f"reported cost {reported_cost} != recomputed {cost}")
    return (not problems), problems, cost
