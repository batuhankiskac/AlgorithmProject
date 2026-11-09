"""Tests for the Split decoder: compare against brute-force segmentation."""
import itertools
import math
import random

import pytest

from cvrp.generator import generate_tiny
from cvrp.instance import load_benchmark
from cvrp.solution import route_cost, route_load
from cvrp.split import split, split_limited, split_unlimited


def brute_force_split(inst, tour, K=None, lam=None, max_load=None):
    """Try every set of cut positions (2^(n-1) segmentations)."""
    n = len(tour)
    cap = inst.Q if lam is None else (max_load if max_load is not None else math.inf)
    best = math.inf
    for mask in range(1 << (n - 1)):
        routes, start = [], 0
        for g in range(n - 1):
            if mask >> g & 1:
                routes.append(tour[start:g + 1])
                start = g + 1
        routes.append(tour[start:])
        if K is not None and len(routes) > K:
            continue
        cost, ok = 0.0, True
        for r in routes:
            load = route_load(inst, r)
            if load > cap:
                ok = False
                break
            cost += route_cost(inst, r)
            if lam is not None and load > inst.Q:
                cost += lam * (load - inst.Q)
        if ok and cost < best:
            best = cost
    return best


def check_routes(inst, tour, routes, cost, K=None, soft=False):
    assert [c for r in routes for c in r] == list(tour)       # order preserved
    if K is not None:
        assert len(routes) <= K
    if not soft:
        assert all(route_load(inst, r) <= inst.Q for r in routes)
        assert sum(route_cost(inst, r) for r in routes) == pytest.approx(cost)


@pytest.mark.parametrize("seed", range(12))
def test_unlimited_split_matches_brute_force(seed):
    n = 7 + seed % 5                       # 7..11 customers
    inst = generate_tiny(n, seed)
    rng = random.Random(seed)
    for _ in range(5):
        tour = list(range(1, n + 1))
        rng.shuffle(tour)
        cost, routes = split_unlimited(inst, tour)
        assert cost == pytest.approx(brute_force_split(inst, tour))
        check_routes(inst, tour, routes, cost)


@pytest.mark.parametrize("seed", range(12))
def test_limited_split_matches_brute_force(seed):
    n = 7 + seed % 5
    inst = generate_tiny(n, 100 + seed)
    rng = random.Random(seed)
    for _ in range(5):
        tour = list(range(1, n + 1))
        rng.shuffle(tour)
        for K in range(1, n + 1):
            bf = brute_force_split(inst, tour, K=K)
            cost, routes = split_limited(inst, tour, K)
            if bf == math.inf:
                assert routes is None and cost == math.inf
            else:
                assert cost == pytest.approx(bf)
                check_routes(inst, tour, routes, cost, K=K)


@pytest.mark.parametrize("seed", range(6))
def test_soft_split_matches_brute_force(seed):
    n = 8
    inst = generate_tiny(n, 200 + seed)
    rng = random.Random(seed)
    tour = list(range(1, n + 1))
    rng.shuffle(tour)
    for K in (1, 2, 3):
        for lam in (0.5, 5.0, 50.0):
            bf = brute_force_split(inst, tour, K=K, lam=lam, max_load=1.5 * inst.Q)
            cost, routes = split_limited(inst, tour, K, overload_penalty=lam, max_load=1.5 * inst.Q)
            if bf == math.inf:
                assert routes is None
            else:
                assert cost == pytest.approx(bf)
                check_routes(inst, tour, routes, cost, K=K, soft=True)


def test_split_wrapper_respects_K_and_penalizes():
    inst = generate_tiny(9, 7)
    rng = random.Random(3)
    for _ in range(30):
        tour = list(range(1, 10))
        rng.shuffle(tour)
        for K in range(1, 6):
            cost, routes = split(inst, tour, K)
            bf = brute_force_split(inst, tour, K=K)
            if bf < math.inf:
                assert len(routes) <= K and cost == pytest.approx(bf)
            else:
                # documented fallback: unlimited split + fleet penalty
                assert len(routes) > K
                true = sum(route_cost(inst, r) for r in routes)
                assert cost > true


def test_unlimited_is_lower_bound_of_limited():
    inst = load_benchmark("A-n32-k5")
    rng = random.Random(0)
    for _ in range(20):
        tour = list(range(1, inst.n + 1))
        rng.shuffle(tour)
        cu, _ = split_unlimited(inst, tour)
        cl, rl = split_limited(inst, tour, inst.K)
        if rl is not None:
            assert cl >= cu


def test_identity_on_known_solution():
    """Concatenating the BKS routes gives a tour whose split costs <= BKS."""
    from cvrp.instance import DATA_DIR, parse_sol
    inst = load_benchmark("A-n32-k5")
    routes, bks = parse_sol(DATA_DIR / "cvrplib" / "A-n32-k5.sol")
    tour = [c for r in routes for c in r]
    cost, r2 = split(inst, tour, inst.K)
    assert len(r2) <= inst.K
    assert cost <= bks
