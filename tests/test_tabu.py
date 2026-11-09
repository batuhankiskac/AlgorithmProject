"""Tests for the move deltas and the tabu search."""
import itertools
import random
from collections import Counter

import pytest

from cvrp.checker import check
from cvrp.clarke_wright import clarke_wright, reduce_routes
from cvrp.generator import generate_medidrone, generate_tiny
from cvrp.instance import load_benchmark
from cvrp.moves import (RELOCATE, SWAP, TWO_OPT, STAR_A, STAR_B, apply_move, delta_cost,
                        delta_vs_full_benchmark, move_arcs, new_loads, random_move)
from cvrp.solution import route_load, total_cost
from cvrp.tabu import solve

BENCH = ["A-n32-k5", "A-n45-k6", "A-n60-k9", "A-n80-k10"]


# ---------------------------------------------------------------- deltas
def _arcs(routes):
    c = Counter()
    for R in routes:
        path = [0] + R + [0]
        for a, b in zip(path, path[1:]):
            c[(min(a, b), max(a, b))] += 1
    return c


def _check_move(inst, routes, move):
    d, q = inst.d, inst.q
    before = total_cost(inst, routes)
    delta = delta_cost(d, routes, move)
    loads = new_loads(q, routes, move)
    rem, add = move_arcs(routes, move)
    arcs_before = _arcs(routes)
    nb = [list(r) for r in routes]
    apply_move(nb, move)
    assert sorted(c for r in nb for c in r) == list(range(1, inst.n + 1))
    assert abs(total_cost(inst, nb) - before - delta) < 1e-6, move
    for r, L in loads.items():
        assert route_load(inst, nb[r]) == L, move
    arcs_after = _arcs(nb)
    assert Counter(rem) == arcs_before - arcs_after, move
    assert Counter(add) == arcs_after - arcs_before, move


@pytest.mark.parametrize("inst", [load_benchmark("A-n32-k5"), generate_medidrone(2026),
                                  generate_tiny(7, 5)], ids=["A-n32", "MediDrone", "tiny"])
def test_random_moves_delta_equals_full_difference(inst):
    rng = random.Random(0)
    routes = reduce_routes(inst, clarke_wright(inst)) + [[]]      # include an empty route
    for _ in range(3000):
        m = random_move(rng, routes)
        _check_move(inst, routes, m)
        if rng.random() < 0.3:                                      # walk to new solutions
            apply_move(routes, m)
            routes = [r for r in routes if r] + [[]]


def test_delta_edge_cases_exhaustive():
    """Every move of every type on a small solution: adjacent positions,
    route ends, single-customer routes, empty target route, merges."""
    inst = generate_tiny(7, 11)
    routes = [[1, 2, 3, 4], [5], [6, 7], []]
    moves = []
    for r1, R1 in enumerate(routes):
        for r2, R2 in enumerate(routes):
            for i in range(len(R1)):
                for j in range(len(R2) + 1):
                    if not (r1 == r2 and j in (i, i + 1)):
                        moves.append((RELOCATE, r1, i, r2, j))
                    if j < len(R2):
                        if r1 != r2:
                            moves += [(SWAP, r1, i, r2, j), (STAR_A, r1, i, r2, j),
                                      (STAR_B, r1, i, r2, j)]
                        elif i < j:
                            moves.append((TWO_OPT, r1, i, r1, j))
                    elif r1 != r2:
                        moves.append((STAR_A, r1, i, r2, j))   # j = len: append nothing
    assert len(moves) > 150
    for m in moves:
        _check_move(inst, routes, m)


def test_tabu_internal_deltas_match_full_recomputation():
    # debug_check asserts after every applied move that the incrementally
    # maintained cost and overload equal a from-scratch recomputation; this
    # validates the inlined formulas in tabu._scan (incl. prefix-load 2-opt*).
    for inst in (load_benchmark("A-n32-k5"), generate_medidrone(2026)):
        res = solve(inst, time_limit=60, seed=3, params={"debug_check": True}, max_iters=1500)
        assert res.iterations == 1500
        assert check(inst, res.routes, res.cost)[0]


def test_delta_vs_full_benchmark_runs():
    out = delta_vs_full_benchmark(load_benchmark("A-n45-k6"), n_samples=2000, seed=1)
    assert out["max_abs_diff"] < 1e-6
    assert out["speedup"] > 1


# ---------------------------------------------------------------- tabu search
@pytest.mark.parametrize("name", BENCH)
def test_tabu_benchmarks_feasible(name):
    inst = load_benchmark(name)
    res = solve(inst, time_limit=3, seed=1)
    ok, problems, cost = check(inst, res.routes, res.cost)
    assert ok, problems
    assert res.cost == cost
    assert len(res.routes) <= inst.K
    assert res.cost <= 1.05 * inst.bks
    assert res.history and res.history[-1][1] == res.cost
    assert all(a[1] > b[1] for a, b in zip(res.history, res.history[1:]))


def test_tabu_respects_max_iters_and_is_reproducible():
    inst = load_benchmark("A-n32-k5")
    a = solve(inst, time_limit=60, seed=7, max_iters=300)
    b = solve(inst, time_limit=60, seed=7, max_iters=300)
    assert a.iterations == 300 and a.routes == b.routes


def test_tabu_from_infeasible_start():
    # one route per customer (far more than K): must be brought down to K
    inst = load_benchmark("A-n60-k9")
    res = solve(inst, time_limit=3, seed=2, init_routes=[[c] for c in range(1, inst.n + 1)])
    assert check(inst, res.routes, res.cost)[0]


# ---------------------------------------------------------------- exact optimum
def exact_cvrp(inst):
    """Exact optimum by DP: Held–Karp TSP for every capacity-feasible subset,
    then set-partition DP over subsets with at most K routes.  n <= ~10."""
    n, d, q, Q, K = inst.n, inst.d, inst.q, inst.Q, inst.K
    full = (1 << n) - 1
    INF = float("inf")
    # Held-Karp: h[S][k] = shortest path 0 -> ... -> customer k+1 visiting S
    h = [[INF] * n for _ in range(full + 1)]
    for k in range(n):
        h[1 << k][k] = d[0][k + 1]
    for S in range(1, full + 1):
        for k in range(n):
            if not S >> k & 1 or h[S][k] == INF:
                continue
            for m in range(n):
                if S >> m & 1:
                    continue
                T = S | 1 << m
                v = h[S][k] + d[k + 1][m + 1]
                if v < h[T][m]:
                    h[T][m] = v
    route = [INF] * (full + 1)
    for S in range(1, full + 1):
        if sum(q[k + 1] for k in range(n) if S >> k & 1) <= Q:
            route[S] = min(h[S][k] + d[k + 1][0] for k in range(n) if S >> k & 1)
    # f[m][S] = min cost covering S with exactly m routes
    f = [[INF] * (full + 1) for _ in range(K + 1)]
    f[0][0] = 0.0
    for m in range(1, K + 1):
        for S in range(1, full + 1):
            low = S & -S                         # the route containing the lowest customer
            T = S
            best = INF
            while T:
                if T & low and route[T] < INF and f[m - 1][S ^ T] < INF:
                    best = min(best, route[T] + f[m - 1][S ^ T])
                T = (T - 1) & S
            f[m][S] = best
    return min(f[m][full] for m in range(1, K + 1))


def _brute_force_check(inst):
    """Independent brute force for very small n: all permutations, optimal split."""
    n, d, q, Q = inst.n, inst.d, inst.q, inst.Q
    best = float("inf")
    for perm in itertools.permutations(range(1, n + 1)):
        # Split DP (shortest path over the permutation, <= K routes)
        V = [[float("inf")] * (inst.K + 1) for _ in range(n + 1)]
        V[0][0] = 0
        for a in range(n):
            load, cost = 0, 0.0
            for b in range(a, n):
                load += q[perm[b]]
                if load > Q:
                    break
                cost = (d[0][perm[a]] if b == a else cost - d[perm[b - 1]][0] + d[perm[b - 1]][perm[b]]) \
                    + d[perm[b]][0]
                for m in range(inst.K):
                    if V[a][m] + cost < V[b + 1][m + 1]:
                        V[b + 1][m + 1] = V[a][m] + cost
        best = min(best, min(V[n]))
    return best


def test_exact_solver_agrees_with_brute_force():
    for seed in range(3):
        inst = generate_tiny(6, seed)
        assert abs(exact_cvrp(inst) - _brute_force_check(inst)) < 1e-6


@pytest.mark.parametrize("n,seed", [(6, 0), (7, 1), (7, 2), (8, 3), (8, 4), (8, 5)])
def test_tabu_finds_exact_optimum_on_tiny(n, seed):
    inst = generate_tiny(n, seed)
    opt = exact_cvrp(inst)
    res = solve(inst, time_limit=3, seed=seed, max_iters=3000)
    assert check(inst, res.routes, res.cost)[0]
    assert res.cost == pytest.approx(opt, abs=1e-6)
