import itertools
import math

import numpy as np
import pytest

from cvrp.checker import check
from cvrp.exact import solve_exact
from cvrp.generator import bosphorus_matrix, generate_medidrone, generate_tiny
from cvrp.instance import DATA_DIR, load_benchmark, parse_sol
from cvrp.solution import total_cost

BENCH = ["A-n32-k5", "A-n45-k6", "A-n60-k9", "A-n80-k10"]


@pytest.mark.parametrize("name", BENCH)
def test_parser_reproduces_bks(name):
    """Loading the published optimal solution must give exactly the BKS,
    which proves our parsing, re-indexing and nint rounding are right."""
    inst = load_benchmark(name)
    routes, cost = parse_sol(DATA_DIR / "cvrplib" / f"{name}.sol")
    assert total_cost(inst, routes) == cost == inst.bks
    ok, problems, rc = check(inst, routes, cost)
    assert ok, problems
    assert rc == cost


def test_checker_detects_errors():
    inst = load_benchmark("A-n32-k5")
    routes, _ = parse_sol(DATA_DIR / "cvrplib" / "A-n32-k5.sol")
    bad = [r[:] for r in routes]
    bad[0].append(bad[1][0])                       # duplicate customer
    assert not check(inst, bad)[0]
    bad = [r[:] for r in routes]
    bad[0].pop()                                   # missing customer
    assert not check(inst, bad)[0]
    merged = [routes[0] + routes[1]] + routes[2:]  # overload
    assert not check(inst, merged)[0]
    split = [[c] for r in routes for c in r]       # too many routes
    assert not check(inst, split)[0]
    assert not check(inst, routes, reported_cost=783)[0]


def test_medidrone_rules():
    inst = generate_medidrone(1234)
    assert inst.n == 100 and inst.Q == 100
    assert tuple(inst.coords[0]) == (500.0, 500.0)
    assert inst.K == math.ceil(inst.total_demand / 100) + 1
    assert inst.demand[1:].min() >= 1 and inst.demand[1:].max() <= 30
    assert 4 <= inst.extra["clusters"] <= 6
    assert set(inst.side.tolist()) == {0, 1}
    # penalty applied exactly to cross-side pairs
    E = np.sqrt(((inst.coords[:, None] - inst.coords[None]) ** 2).sum(-1))
    diff = inst.D - E
    cross = inst.side[:, None] != inst.side[None, :]
    assert np.allclose(diff[cross], 150) and np.allclose(diff[~cross], 0)


def test_bosphorus_metric_empirically():
    rng = np.random.default_rng(0)
    pts = rng.uniform(0, 1000, size=(60, 2))
    D, _ = bosphorus_matrix(pts)
    # d(i,k) <= d(i,j) + d(j,k) for all triples
    lhs = D[:, None, :]
    rhs = D[:, :, None] + D[None, :, :]
    assert (lhs <= rhs + 1e-9).all()


def _brute_force(inst):
    """Independent exact method: all permutations x all cut positions."""
    n, best = inst.n, math.inf
    for perm in itertools.permutations(range(1, n + 1)):
        for mask in range(1 << (n - 1)):
            routes, cur = [], [perm[0]]
            for i in range(1, n):
                if (mask >> (i - 1)) & 1:
                    routes.append(cur)
                    cur = []
                cur.append(perm[i])
            routes.append(cur)
            if len(routes) > inst.K or any(sum(inst.q[c] for c in r) > inst.Q for r in routes):
                continue
            best = min(best, total_cost(inst, routes))
    return best


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_exact_dp_matches_brute_force(seed):
    inst = generate_tiny(6, seed)
    cost, routes = solve_exact(inst)
    ok, problems, rc = check(inst, routes, cost)
    assert ok, problems
    assert cost == pytest.approx(_brute_force(inst))
