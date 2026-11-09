"""Tests for the Genetic Algorithm (giant tour + Split, Prins 2004)."""
import itertools
import random

import pytest

from cvrp import ga
from cvrp.checker import check
from cvrp.generator import generate_tiny
from cvrp.instance import load_benchmark
from cvrp.solution import total_cost
from cvrp.split import split

BENCHMARKS = ["A-n32-k5", "A-n45-k6", "A-n60-k9", "A-n80-k10"]


def exact_optimum(inst):
    """Brute force: every permutation + optimal limited-fleet Split.
    Every CVRP solution is the split of some permutation, so this is exact."""
    best = float("inf")
    for perm in itertools.permutations(range(1, inst.n + 1)):
        c, r = split(inst, list(perm), inst.K)
        if len(r) <= inst.K and c < best:
            best = c
    return best


def test_ox_is_permutation_and_keeps_slice():
    rng = random.Random(1)
    for n in (2, 5, 30):
        for _ in range(200):
            p1 = list(range(1, n + 1))
            p2 = p1[:]
            rng.shuffle(p1)
            rng.shuffle(p2)
            c = ga.ox_crossover(p1, p2, rng)
            assert sorted(c) == list(range(1, n + 1))


@pytest.mark.parametrize("kind", ["inversion", "swap", "insertion"])
def test_mutation_keeps_permutation(kind):
    rng = random.Random(2)
    t = list(range(1, 41))
    for _ in range(200):
        ga.mutate(t, kind, rng)
        assert sorted(t) == list(range(1, 41))


def test_local_search_never_worsens_and_keeps_customers():
    inst = load_benchmark("A-n45-k6")
    ls = ga.LocalSearch(inst, 12)
    rng = random.Random(5)
    for _ in range(5):
        tour = list(range(1, inst.n + 1))
        rng.shuffle(tour)
        _, routes = split(inst, tour)                 # feasible, maybe > K routes
        before = total_cost(inst, routes)
        out, dist, over = ls.run(routes, len(routes), 1000.0, rng)
        assert sorted(c for r in out for c in r) == list(range(1, inst.n + 1))
        assert dist == pytest.approx(total_cost(inst, out))
        assert over == 0 and dist <= before


@pytest.mark.parametrize("name", BENCHMARKS)
@pytest.mark.parametrize("memetic", [True, False])
def test_ga_output_passes_checker(name, memetic):
    inst = load_benchmark(name)
    res = ga.solve(inst, time_limit=3.0, seed=1, params={"memetic": memetic})
    ok, problems, cost = check(inst, res.routes, res.cost)
    assert ok, problems
    assert res.history and res.history[-1][1] == pytest.approx(res.cost)
    assert res.iterations >= 1 or not memetic


@pytest.mark.parametrize("n,seed", [(6, 1), (7, 2), (7, 3), (8, 4)])
def test_ga_finds_exact_optimum_of_tiny_instances(n, seed):
    inst = generate_tiny(n, seed)
    opt = exact_optimum(inst)
    res = ga.solve(inst, time_limit=5.0, seed=seed, max_generations=30)
    ok, problems, cost = check(inst, res.routes, res.cost)
    assert ok, problems
    assert res.cost == pytest.approx(opt, abs=1e-6)


def test_ga_is_reproducible_with_max_generations():
    inst = load_benchmark("A-n32-k5")
    a = ga.solve(inst, time_limit=60, seed=7, max_generations=5)
    b = ga.solve(inst, time_limit=60, seed=7, max_generations=5)
    assert a.routes == b.routes and a.iterations == b.iterations == 5


def test_ga_uses_init_routes():
    inst = load_benchmark("A-n32-k5")
    from cvrp.instance import DATA_DIR, parse_sol
    routes, bks = parse_sol(DATA_DIR / "cvrplib" / "A-n32-k5.sol")
    res = ga.solve(inst, time_limit=5, seed=0, init_routes=routes, max_generations=1,
                   params={"memetic": False})
    assert res.cost <= bks
