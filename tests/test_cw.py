"""Tests for the Clarke–Wright savings heuristic."""
import pytest

from cvrp.checker import check
from cvrp.clarke_wright import clarke_wright, extra_routes, reduce_routes, savings_list
from cvrp.generator import generate_medidrone, generate_tiny
from cvrp.instance import load_benchmark
from cvrp.solution import route_load, total_cost

BENCH = ["A-n32-k5", "A-n45-k6", "A-n60-k9", "A-n80-k10"]


def _covers_all(inst, routes):
    flat = sorted(c for r in routes for c in r)
    return flat == list(range(1, inst.n + 1))


@pytest.mark.parametrize("name", BENCH)
def test_cw_capacity_and_coverage(name):
    inst = load_benchmark(name)
    routes = clarke_wright(inst)
    assert _covers_all(inst, routes)
    assert all(route_load(inst, r) <= inst.Q for r in routes)
    ok, problems, cost = check(inst, routes, total_cost(inst, routes))
    # the only problem CW may legitimately have is using more than K routes
    assert all("routes > K" in p for p in problems)
    assert (len(routes) > inst.K) == (not ok)
    assert extra_routes(inst, routes) == max(0, len(routes) - inst.K)
    assert cost >= inst.bks          # cannot beat the best known solution


def test_cw_known_values():
    # deterministic values of our implementation (regression test)
    expected = {"A-n32-k5": (842, 5), "A-n45-k6": (997, 7), "A-n60-k9": (1408, 9),
                "A-n80-k10": (1840, 10)}
    for name, (cost, nr) in expected.items():
        inst = load_benchmark(name)
        routes = clarke_wright(inst)
        assert total_cost(inst, routes) == cost
        assert len(routes) == nr


def test_cw_deterministic():
    inst = generate_medidrone(2026)
    assert clarke_wright(inst) == clarke_wright(inst)


def test_savings_sorted_and_correct():
    inst = generate_tiny(8, 3)
    d = inst.d
    sav = savings_list(inst)
    assert all(a[0] >= b[0] for a, b in zip(sav, sav[1:]))
    for s, i, j in sav:
        assert i < j and s > 0
        assert abs(s - (d[0][i] + d[0][j] - d[i][j])) < 1e-9


def test_cw_merges_everything_when_capacity_is_huge():
    # With unlimited capacity and positive savings everywhere, parallel CW must
    # end with a single route (a TSP tour).
    inst = load_benchmark("A-n32-k5")
    inst.Q = 10 ** 9
    routes = clarke_wright(inst)
    assert len(routes) == 1 and _covers_all(inst, routes)


def test_cw_no_merge_when_capacity_is_tight():
    # If Q equals the largest demand and no two customers fit together, CW
    # must keep the n initial routes 0-i-0.
    inst = generate_tiny(6, 0)
    inst.Q = max(inst.q)
    q = sorted(inst.q[1:])
    if q[0] + q[1] > inst.Q:
        assert len(clarke_wright(inst)) == inst.n


def test_reduce_routes_reaches_K():
    inst = load_benchmark("A-n45-k6")
    routes = clarke_wright(inst)
    assert len(routes) > inst.K
    red = reduce_routes(inst, routes)
    assert len(red) <= inst.K and _covers_all(inst, red)
