"""Solution representation, evaluation and the common result type.

A solution is a list of routes; each route is a list of customer ids
(1..n) WITHOUT the depot. The depot 0 is implicit at both ends.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .instance import Instance

Routes = list[list[int]]


def route_cost(inst: Instance, route: list[int]) -> float:
    if not route:
        return 0
    d = inst.d
    c = d[0][route[0]] + d[route[-1]][0]
    for a, b in zip(route, route[1:]):
        c += d[a][b]
    return c


def route_load(inst: Instance, route: list[int]) -> int:
    q = inst.q
    return sum(q[i] for i in route)


def total_cost(inst: Instance, routes: Routes) -> float:
    return sum(route_cost(inst, r) for r in routes)


def clean(routes: Routes) -> Routes:
    """Drop empty routes."""
    return [list(r) for r in routes if r]


def crossings(inst: Instance, routes: Routes) -> tuple[int, int]:
    """(number of arcs crossing the Bosphorus, number of routes that cross)."""
    if inst.side is None:
        return 0, 0
    s = inst.side
    arcs = rcount = 0
    for r in routes:
        if not r:
            continue
        path = [0] + r + [0]
        c = sum(1 for a, b in zip(path, path[1:]) if s[a] != s[b])
        arcs += c
        rcount += c > 0
    return arcs, rcount


@dataclass
class Result:
    """Common return type of every solver's ``solve`` function."""
    routes: Routes
    cost: float
    history: list[tuple[float, float]] = field(default_factory=list)  # (elapsed s, best cost)
    iterations: int = 0
    elapsed: float = 0.0
    extra: dict = field(default_factory=dict)
