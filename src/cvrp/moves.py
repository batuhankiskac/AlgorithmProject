"""Neighbourhood moves for the tabu search: definitions, O(1) delta formulas,
application, and the arcs each move removes / adds.

A solution is a list of routes (customers only, the depot 0 is implicit at both
ends).  Positions outside a route mean "the depot": ``at(R, -1) == at(R, len(R)) == 0``.
The distance matrix d must be symmetric (true for EUC_2D and for MediDrone).

A move is a tuple ``(mtype, r1, i, r2, j)``:

RELOCATE  remove customer u = R1[i] and insert it into route r2 in the *gap* j,
          i.e. between R2[j-1] and R2[j] (j in 0..len(R2); indices refer to
          the route before the removal).  r1 == r2 is an intra-route relocate
          (then j not in {i, i+1}, which would be a no-op).  r2 may be empty.
              Δ = d(a,u) + d(u,b) - d(a,b)  -  [d(p,u) + d(u,s) - d(p,s)]
          with p, s the neighbours of u and (a, b) = (R2[j-1], R2[j]).
SWAP      exchange u = R1[i] and v = R2[j], r1 != r2.
              Δ = d(pu,v) + d(v,su) + d(pv,u) + d(u,sv)
                - d(pu,u) - d(u,su) - d(pv,v) - d(v,sv)
TWO_OPT   intra-route (r1 == r2): reverse the segment R[i..j], i < j.
              Δ = d(a, R[j]) + d(R[i], b) - d(a, R[i]) - d(R[j], b),
          a = R[i-1], b = R[j+1].
STAR_A    2-opt* "tail exchange": R1' = R1[:i+1] + R2[j:],  R2' = R2[:j] + R1[i+1:]
              Δ = d(u,v) + d(pv,su) - d(u,su) - d(pv,v)
          with u = R1[i], su = R1[i+1], v = R2[j], pv = R2[j-1].
STAR_B    2-opt* "head/tail exchange with reversal":
          R1' = R1[:i+1] + reversed(R2[:j+1]),  R2' = reversed(R1[i+1:]) + R2[j+1:]
              Δ = d(u,v) + d(su,sv) - d(u,su) - d(v,sv)

All five formulas only touch a constant number of matrix entries, so Δ is O(1).
"""
from __future__ import annotations

import random
import time

from .instance import Instance
from .solution import Routes, total_cost

RELOCATE, SWAP, TWO_OPT, STAR_A, STAR_B = range(5)
MOVE_NAMES = {RELOCATE: "relocate", SWAP: "swap", TWO_OPT: "2-opt",
              STAR_A: "2-opt*A", STAR_B: "2-opt*B"}


def at(R: list[int], k: int) -> int:
    """Customer at position k of route R, or the depot 0 if k is outside R."""
    return R[k] if 0 <= k < len(R) else 0


# --------------------------------------------------------------------------
# O(1) delta evaluation
# --------------------------------------------------------------------------
def delta_cost(d, routes: Routes, move) -> float:
    """Change of total distance caused by ``move`` -- O(1)."""
    t, r1, i, r2, j = move
    R1, R2 = routes[r1], routes[r2]
    if t == RELOCATE:
        u, p, s = R1[i], at(R1, i - 1), at(R1, i + 1)
        a, b = at(R2, j - 1), at(R2, j)
        return d[a][u] + d[u][b] - d[a][b] - (d[p][u] + d[u][s] - d[p][s])
    if t == SWAP:
        u, pu, su = R1[i], at(R1, i - 1), at(R1, i + 1)
        v, pv, sv = R2[j], at(R2, j - 1), at(R2, j + 1)
        return (d[pu][v] + d[v][su] + d[pv][u] + d[u][sv]
                - d[pu][u] - d[u][su] - d[pv][v] - d[v][sv])
    if t == TWO_OPT:
        a, x, y, b = at(R1, i - 1), R1[i], R1[j], at(R1, j + 1)
        return d[a][y] + d[x][b] - d[a][x] - d[y][b]
    if t == STAR_A:
        u, su = at(R1, i), at(R1, i + 1)
        pv, v = at(R2, j - 1), at(R2, j)
        return d[u][v] + d[pv][su] - d[u][su] - d[pv][v]
    if t == STAR_B:
        u, su = at(R1, i), at(R1, i + 1)
        v, sv = at(R2, j), at(R2, j + 1)
        return d[u][v] + d[su][sv] - d[u][su] - d[v][sv]
    raise ValueError(t)


def new_loads(q, routes: Routes, move) -> dict[int, int]:
    """Loads of the affected routes after the move (reference version, O(n);
    the tabu search computes the same numbers in O(1) from prefix loads)."""
    t, r1, i, r2, j = move
    R1, R2 = routes[r1], routes[r2]
    L1, L2 = route_load_q(q, R1), route_load_q(q, R2)
    if r1 == r2:
        return {r1: L1}
    if t == RELOCATE:
        return {r1: L1 - q[R1[i]], r2: L2 + q[R1[i]]}
    if t == SWAP:
        return {r1: L1 - q[R1[i]] + q[R2[j]], r2: L2 - q[R2[j]] + q[R1[i]]}
    P1 = route_load_q(q, R1[:i + 1])
    if t == STAR_A:
        P2 = route_load_q(q, R2[:j])
        return {r1: P1 + L2 - P2, r2: P2 + L1 - P1}
    if t == STAR_B:
        P2 = route_load_q(q, R2[:j + 1])
        return {r1: P1 + P2, r2: (L1 - P1) + (L2 - P2)}
    raise ValueError(t)


def route_load_q(q, R) -> int:
    return sum(q[c] for c in R)


# --------------------------------------------------------------------------
# arcs removed / added (used for the tabu attributes)
# --------------------------------------------------------------------------
def _norm(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a <= b else (b, a)


def move_arcs(routes: Routes, move) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(removed arcs, added arcs) of a move, as undirected pairs (min, max).
    Arcs that appear on both sides cancel out (e.g. intra-route relocate of u
    just behind its own successor keeps the edge u–su)."""
    t, r1, i, r2, j = move
    R1, R2 = routes[r1], routes[r2]
    if t == RELOCATE:
        u, p, s = R1[i], at(R1, i - 1), at(R1, i + 1)
        a, b = at(R2, j - 1), at(R2, j)
        rem = [(p, u), (u, s), (a, b)]
        add = [(p, s), (a, u), (u, b)]
    elif t == SWAP:
        u, pu, su = R1[i], at(R1, i - 1), at(R1, i + 1)
        v, pv, sv = R2[j], at(R2, j - 1), at(R2, j + 1)
        rem = [(pu, u), (u, su), (pv, v), (v, sv)]
        add = [(pu, v), (v, su), (pv, u), (u, sv)]
    elif t == TWO_OPT:
        a, x, y, b = at(R1, i - 1), R1[i], R1[j], at(R1, j + 1)
        rem = [(a, x), (y, b)]
        add = [(a, y), (x, b)]
    elif t == STAR_A:
        u, su, pv, v = at(R1, i), at(R1, i + 1), at(R2, j - 1), at(R2, j)
        rem = [(u, su), (pv, v)]
        add = [(u, v), (pv, su)]
    elif t == STAR_B:
        u, su, v, sv = at(R1, i), at(R1, i + 1), at(R2, j), at(R2, j + 1)
        rem = [(u, su), (v, sv)]
        add = [(u, v), (su, sv)]
    else:
        raise ValueError(t)
    rem = [_norm(*e) for e in rem]
    add = [_norm(*e) for e in add]
    for e in list(rem):                       # cancel common arcs (multiset)
        if e in add:
            rem.remove(e)
            add.remove(e)
    return rem, add


# --------------------------------------------------------------------------
# application
# --------------------------------------------------------------------------
def apply_move(routes: Routes, move) -> list[int]:
    """Apply the move in place; returns the indices of the modified routes.
    Cost O(length of the affected routes)."""
    t, r1, i, r2, j = move
    R1, R2 = routes[r1], routes[r2]
    if t == RELOCATE:
        u = R1.pop(i)
        if r1 == r2 and j > i:
            j -= 1                            # gap index shifts after removal
        R2.insert(j, u)
    elif t == SWAP:
        R1[i], R2[j] = R2[j], R1[i]
    elif t == TWO_OPT:
        R1[i:j + 1] = R1[i:j + 1][::-1]
    elif t == STAR_A:
        routes[r1], routes[r2] = R1[:i + 1] + R2[j:], R2[:j] + R1[i + 1:]
    elif t == STAR_B:
        routes[r1], routes[r2] = R1[:i + 1] + R2[:j + 1][::-1], R1[i + 1:][::-1] + R2[j + 1:]
    else:
        raise ValueError(t)
    return [r1] if r1 == r2 else [r1, r2]


def random_move(rng: random.Random, routes: Routes):
    """A uniformly drawn *valid* move (used by tests and the benchmark).
    Covers edge cases: route ends, adjacent positions, empty target routes."""
    nonempty = [r for r, R in enumerate(routes) if R]
    while True:
        t = rng.randrange(5)
        r1 = rng.choice(nonempty)
        R1 = routes[r1]
        if t == RELOCATE:
            r2 = rng.randrange(len(routes))           # may be empty / same route
            i = rng.randrange(len(R1))
            j = rng.randrange(len(routes[r2]) + 1)
            if r1 == r2 and j in (i, i + 1):
                continue
            return (t, r1, i, r2, j)
        if t == TWO_OPT:
            if len(R1) < 2:
                continue
            i, j = sorted(rng.sample(range(len(R1)), 2))
            return (t, r1, i, r1, j)
        others = [r for r in nonempty if r != r1]
        if not others:
            continue
        r2 = rng.choice(others)
        i, j = rng.randrange(len(R1)), rng.randrange(len(routes[r2]))
        return (t, r1, i, r2, j)


# --------------------------------------------------------------------------
# Task 6: how much does delta evaluation save?
# --------------------------------------------------------------------------
def delta_vs_full_benchmark(inst: Instance, n_samples: int = 20000, seed: int = 0,
                            routes: Routes | None = None) -> dict:
    """Evaluate n_samples random moves twice:
      * delta:  O(1) formula ``delta_cost``;
      * full:   build the neighbour (copy + apply) and recompute its total cost
                from scratch, O(n);
    asserts that both give the same cost change and returns timings."""
    from .clarke_wright import clarke_wright, reduce_routes
    rng = random.Random(seed)
    if routes is None:
        routes = reduce_routes(inst, clarke_wright(inst))
    routes = [list(r) for r in routes] + [[]]        # one empty route for edge cases
    d = inst.d
    base = total_cost(inst, routes)
    moves = [random_move(rng, routes) for _ in range(n_samples)]

    t0 = time.perf_counter()
    deltas = [delta_cost(d, routes, m) for m in moves]
    t_delta = time.perf_counter() - t0

    t0 = time.perf_counter()
    fulls = []
    for m in moves:
        nb = [list(r) for r in routes]
        apply_move(nb, m)
        fulls.append(total_cost(inst, nb) - base)
    t_full = time.perf_counter() - t0

    # only the cost recomputation, without building the neighbour
    nbs = []
    for m in moves[:min(n_samples, 2000)]:
        nb = [list(r) for r in routes]
        apply_move(nb, m)
        nbs.append(nb)
    t0 = time.perf_counter()
    for nb in nbs:
        total_cost(inst, nb)
    t_cost_only = (time.perf_counter() - t0) / len(nbs) * n_samples

    worst = max(abs(a - b) for a, b in zip(deltas, fulls))
    assert worst <= 1e-6 * max(1.0, abs(base)), f"delta mismatch {worst}"
    return {
        "instance": inst.name, "n": inst.n, "samples": n_samples,
        "delta_us_per_move": 1e6 * t_delta / n_samples,
        "full_us_per_move": 1e6 * t_full / n_samples,
        "full_cost_only_us_per_move": 1e6 * t_cost_only / n_samples,
        "speedup": t_full / t_delta,
        "speedup_cost_only": t_cost_only / t_delta,
        "max_abs_diff": worst,
    }
