# Genetic Algorithm (giant tour + Split) — integration notes

Code: `src/cvrp/split.py`, `src/cvrp/ga.py`. Tests: `tests/test_split.py`, `tests/test_ga.py`.
Main reference: C. Prins (2004), *A simple and effective evolutionary algorithm for the
vehicle routing problem*, Computers & Operations Research 31:1985–2002. Two ideas are
taken from T. Vidal, T. G. Crainic, M. Gendreau, N. Lahrichi, W. Rei (2012), *A hybrid
genetic algorithm for multidepot and periodic vehicle routing problems*, Operations
Research 60(3):611–624: penalized capacity violations with an adaptive penalty, and
granular neighbour lists in the local search. All code is our own.

## Public API

```python
from cvrp.split import split, split_unlimited, split_limited
split(inst, tour, K=None, fleet_penalty=None) -> (cost, routes)
split_unlimited(inst, tour) -> (cost, routes)
split_limited(inst, tour, K, overload_penalty=None, max_load=None) -> (cost, routes | None)

from cvrp import ga
ga.solve(inst, time_limit, seed, params=None, init_routes=None, max_generations=None) -> Result
ga.DEFAULT_PARAMS                       # dict of defaults; params overrides individual keys
ga.ox_crossover(p1, p2, rng), ga.mutate(tour, kind, rng), ga.LocalSearch(inst, g).run(...)
```

`Result.routes` always passes `check()` when any feasible solution was found (in all our
runs it was). `Result.history` = (elapsed s, best feasible cost) at every improvement;
the first entry is the best solution of the initial population. `Result.iterations` =
number of completed generations. `Result.extra` holds `params`, `seed`,
`generations_per_s`, `diversity` (one value per generation), `feasible_rate` (one per
generation), `final_penalty`, and counters `ls_calls`, `repairs`,
`rejected_duplicates`, `restarts`, `offspring`.

## 1. Split

### Auxiliary graph
Giant tour T = (T₁, …, Tₙ), a permutation of the customers (no depot).
DAG H = (V, A):

* nodes V = {0, 1, …, n}; node i means "the first i customers of T are served";
* arc (i, j), 0 ≤ i < j ≤ n, exists iff the customers T_{i+1}, …, T_j fit in one
  vehicle: Σ_{k=i+1..j} q(T_k) ≤ Q;
* cost of arc (i, j) = cost of the trip 0 → T_{i+1} → … → T_j → 0
  = d(0,T_{i+1}) + Σ_{k=i+1..j-1} d(T_k,T_{k+1}) + d(T_j,0).

Each 0→n path is a segmentation of T into feasible routes (one arc = one route), and every
segmentation that keeps the order of T is such a path. Hence the shortest 0→n path is the
optimal split.

### DP recurrence (Bellman on a DAG)
V(0) = 0,  V(j) = min_{i<j, (i,j)∈A} V(i) + c(i,j),  answer V(n), predecessor P(j) = argmin.
Nodes are already in topological order (arcs only go from smaller to larger index), so one
pass i = 0, …, n−1 relaxing all arcs leaving i is enough.

### Complexity
For a fixed i the inner loop extends j = i+1, i+2, … while the load fits, and **breaks**
at the first j whose load exceeds Q (all longer trips are infeasible too, because demands
are positive). The trip cost is updated in O(1) when j grows
(cost(i,j+1) = cost(i,j) − d(T_j,0) + d(T_j,T_{j+1}) + d(T_{j+1},0)).
Let L = maximal number of customers that fit in one vehicle (L ≤ n). Then the inner loop
runs at most L times for each of the n values of i: **O(n·L)** time; since L ≤ n this is
**O(n²)** in general (L = n when all customers fit in one vehicle). Memory O(n).
Route extraction by following P from n back to 0 is O(n).

### Limited fleet (≤ K routes)
Layered DP: V_k(j) = min cost of serving T₁..T_j with exactly k routes.
V_0(0) = 0, V_0(j>0) = ∞, V_k(j) = min_{i<j,(i,j)∈A} V_{k−1}(i) + c(i,j), answer
min_{k≤K} V_k(n). Each layer is one O(n·L) pass, so **O(K·n·L)** time
(O(K·n²) in general), O(K·n) memory for the predecessors.

`split(inst, tour, K)` first runs the unlimited split; if it uses ≤ K routes it is also
optimal for the limited problem (it is the optimum of a relaxation), so the K-layer DP runs
only when needed. **No ≤K split exists** (common for random tours on tight instances):
`split` returns the unlimited split with cost = true cost + fleet_penalty × (#routes − K),
fleet_penalty = 2·max_i d(0,i) by default; callers detect it with `len(routes) > K`.
`split_limited` returns `(inf, None)` in that case.

### Soft-capacity variant (used inside the GA)
`split_limited(..., overload_penalty=λ, max_load=1.5Q)`: same layered DP, arcs allowed up
to load 1.5Q, arc cost = trip distance + λ·max(0, load − Q). The inner loop breaks at
load > 1.5Q, so it is still O(K·n·L′) with L′ ≈ 1.5·L. With this decoder every giant
tour has a ≤K segmentation, which is essential on A-n45-k6 (demand 593/600) and
A-n80-k10 (942/1000), where almost no random permutation has a hard-feasible ≤K split
(measured: 0% of random tours on A-n45-k6, 22% on A-n80-k10).

### Pseudocode
```
SPLIT(T, K):                         // T = giant tour, 1-based
    V[0] ← 0; V[1..n] ← ∞
    for i ← 0 to n−1:
        load ← 0; cost ← 0; j ← i+1
        while j ≤ n:
            load ← load + q(T_j)
            if load > Q: break                      // capacity cut-off → O(n·L)
            if j = i+1: cost ← d(0,T_j) + d(T_j,0)
            else:       cost ← cost − d(T_{j−1},0) + d(T_{j−1},T_j) + d(T_j,0)
            if V[i] + cost < V[j]: V[j] ← V[i] + cost; P[j] ← i
            j ← j+1
    routes ← extract by following P from n down to 0
    if K = nil or |routes| ≤ K: return V[n], routes
    return SPLIT-LIMITED(T, K)   // or unlimited + fleet penalty if that is infeasible

SPLIT-LIMITED(T, K):                 // layered version, O(K·n·L)
    W[0][0] ← 0; W[0][j>0] ← ∞
    for k ← 1 to K:
        W[k][·] ← ∞
        for i ← 0 to n−1 with W[k−1][i] < ∞:
            (same inner loop as above, relaxing W[k][j] from W[k−1][i], P[k][j] ← i)
    k* ← argmin_k W[k][n]; return W[k*][n] and the routes read from P[k*], P[k*−1], …
```

## 2. GA design

| Component | Choice | Why |
|---|---|---|
| Chromosome | giant tour (permutation of 1..n) | every permutation decodes to a solution; classic crossovers work; Split is optimal for the given order (Prins 2004) |
| Decoder / fitness | soft limited Split → distance + λ·overload | lower = better; feasible individuals have fitness = distance |
| Initial population | `init_routes` tour (e.g. Clarke–Wright, concatenated routes), 30% sweep orders (polar angle from a random start angle, random direction), rest random permutations; all improved by LS in memetic mode; duplicates rejected | sweep orders split into compact routes; random tours give diversity |
| Selection | binary tournament on fitness | O(1), mild selection pressure, no scaling needed |
| Crossover | OX (Prins' version), p_cx = 0.9 | keeps a slice of parent 1 as is (= consecutive customers ⇒ routes) and the relative order of parent 2; O(n) |
| Mutation | inversion of a random segment, p_mut = 0.2 (swap and insertion available) | inversion = 2-opt on the giant tour: changes only 2 adjacencies, so it perturbs without destroying the route structure; swap changes 4, insertion 3 |
| Local search (memetic) | granular first-improvement LS with probability p_ls = 0.5 on each child (always on initial individuals): relocate (after/before), swap, 2-opt (intra), 2-opt* (both variants), move to empty route; g = 20 nearest neighbours; penalized objective | the plain GA alone is ≈25–30% above BKS at n = 80; LS brings it below 1%. p_ls = 0.5 beat 1.0 (more generations, more recombination) and 0.3 in our tuning |
| Repair | infeasible LS result: with prob. 0.5 rerun LS with 10×λ, then 100×λ | Vidal et al. 2012; makes feasible solutions frequent on tight instances |
| Re-split | after a feasible LS result, concatenate routes and run the exact `split` again; keep if cheaper | Prins 2004; can only keep or improve |
| Penalty λ | start max d / max q; after each generation ×1.2 if < 35% of children feasible, ×0.85 if > 45% | keeps the search near the feasibility border |
| Replacement | (μ+λ) truncation: merge parents and children, keep the μ best with distinct fitness | elitist by construction (the best can never be lost); `replacement="generational"` keeps `elite` parents + best children instead |
| Diversity | a child whose fitness is within `min_gap` = 0.5 of a population member is rejected (Prins' spacing Δ; on integer CVRPLIB costs this means "same cost"); duplicates are also skipped in replacement | cheap O(μ) test, prevents clones taking over |
| Restart | after `restart_after` = 60 generations without improvement of the best feasible cost, keep the `elite` = 2 best and refill with new random individuals (+LS) | Prins' partial replacement; escapes premature convergence |
| Stopping | wall-clock `time_limit` (checked before every child) or `max_generations` | |

### Local-search objective and move evaluation
f(S) = Σ route distances + λ·Σ_r max(0, load_r − Q). For customer u at position i of route
r_u with predecessor p_u and successor n_u (depot 0 at both ends), and v ∈ N_g(u):

* relocate u after v: Δ = d(v,u) + d(u,n_v) − d(v,n_v) − [d(p_u,u) + d(u,n_u) − d(p_u,n_u)] + λ·Δoverload
* swap u, v: replace the 4 incident edges
* 2-opt (same route): Δ = d(u,v) + d(n_u,n_v) − d(u,n_u) − d(v,n_v)
* 2-opt* (a): tails exchanged, Δ = d(u,n_v) + d(v,n_u) − d(u,n_u) − d(v,n_v); new loads from prefix loads
* 2-opt* (b): u→v, n_u→n_v (one head and one tail reversed); Δ = d(u,v) + d(n_u,n_v) − d(u,n_u) − d(v,n_v)

Every Δ is O(1) (prefix loads are stored per route). Applying a move rebuilds the
positions/prefix loads of the ≤ 2 changed routes: O(L). "Route stamps" skip (u,v) pairs
whose two routes did not change since u was last examined. Distances must be symmetric
(true for all our instances).

### Definition of ONE generation and its cost
One generation = the creation of λ_off = `n_offspring` children (each: 2 tournaments,
OX with prob. p_cx, mutation with prob. p_mut, decoding, optional LS, duplicate test),
followed by the penalty update, (μ+λ) replacement and the diversity measurement.
`Result.iterations` counts completed generations.

Per child:

| step | cost |
|---|---|
| 2 binary tournaments | O(1) |
| OX | O(n) |
| mutation | O(n) |
| soft limited Split | O(K·n·L′) |
| LS (prob. p_ls) | O(P·n·g + M·L) for P passes and M applied moves |
| repair (≤ 2 more LS runs) + exact re-split | same order as LS + O(K·n·L) |
| duplicate test | O(μ + λ_off) |

Per generation additionally: fitness refresh O(μ+λ_off), sort O((μ+λ_off)·log(μ+λ_off)),
duplicate filtering O((μ+λ_off)·μ), diversity O(μ²·n) (μ(μ−1)/2 set intersections of
O(n) edges).

**Plain GA** (memetic = False):
T_gen = O(λ_off·(K·n·L + μ + λ_off) + μ²·n), i.e. O(λ_off·K·n²) in the worst case L = n.
**Memetic GA**: T_gen = O(λ_off·(K·n·L′ + p_ls·(P·n·g + M·L)) + μ²·n + (μ+λ_off)²). P and
M are not bounded by a polynomial a priori (each applied move strictly decreases f, so the
LS terminates); empirically P is a small constant (≈3–8 passes, later ones cheap thanks to
the stamps) so one LS costs Θ(n·g) per pass in practice.
With the defaults (μ = λ_off = 25, K ≈ 10, L ≈ 10, g = 20) the Split term (~25·10·80·15 ≈ 3·10⁵
basic steps at n = 80) and the LS term dominate; the diversity term (300 set intersections)
is negligible.

### Pseudocode
```
GA(inst, time_limit, max_gen):
    λ ← max d / max q                                   // overload penalty
    P ← ∅
    seeds ← [tour(init_routes)] + sweep orders + random permutations
    while |P| < μ: x ← DECODE(next seed, LS = on); if not DUPLICATE(x, P): P ← P ∪ {x}
    gen ← 0
    while time < time_limit and gen < max_gen:
        C ← ∅
        repeat λ_off times:
            p1 ← TOURNAMENT(P); p2 ← TOURNAMENT(P)
            t ← OX(p1.tour, p2.tour) with prob p_cx, else copy of p1.tour
            with prob p_mut: INVERT a random segment of t
            x ← DECODE(t, LS with prob p_ls)
            if not DUPLICATE(x, P ∪ C): C ← C ∪ {x}
        update λ from the share of feasible children; recompute fitness of P ∪ C
        P ← the μ best of P ∪ C with pairwise fitness gap ≥ Δ        // elitist
        record diversity(P); gen ← gen + 1
        if no improvement for R generations: keep 2 best, refill P with random individuals
    return best feasible solution ever decoded

DECODE(t, ls):
    (f, S) ← SOFT-SPLIT-LIMITED(t, K, λ, 1.5Q)
    if ls: S ← LOCAL-SEARCH(S, λ)
           if S overloaded, with prob 0.5: S ← LOCAL-SEARCH(S, 10λ) (then 100λ)
           t ← concatenation of the routes of S
           if S feasible: S ← better of S and SPLIT(t, K)
    fitness ← dist(S) + λ·overload(S); update best feasible
```

## 3. Recommended parameters (`DEFAULT_PARAMS`)

```python
DEFAULT_PARAMS = {
    "pop_size": 25, "n_offspring": 25,        # mu and lambda_off
    "p_cx": 0.9, "p_mut": 0.2, "mutation": "inversion",
    "tournament": 2, "replacement": "plus", "elite": 2, "min_gap": 0.5,
    "memetic": True, "p_ls": 0.5, "granular": 20, "p_repair": 0.5,
    "target_feasible": 0.4, "max_load_factor": 1.5,
    "restart_after": 60, "init_sweep_frac": 0.3, "diversity": True,
}
```
The memetic configuration is the recommended one. Tuning (3 seeds × 30 s on A-n60-k9,
A-n80-k10 and MediDrone, machine under heavy load): p_ls = 0.5 beat 1.0 and 0.3;
g = 20 beat g = 12; μ = λ_off = 40 was not better than 25 (fewer generations);
restart_after = 30 vs 60 made no clear difference. For a parameter study the cheap knobs are
`pop_size`, `p_ls` (0 = plain GA with soft Split), `p_mut`/`mutation`, `replacement`, and
`extra["diversity"]` shows how fast the population converges.

## 4. Results

Default parameters, random + sweep initial population (no Clarke–Wright seeding),
seeds 1, 2, 3; time limit 30 s for n ≤ 50 and 60 s for n > 50. All solutions pass `check`
and use ≤ K routes. **Machine was shared with ~7 other runs and other jobs (load average
30–40 on 10 cores), so generations/s are pessimistic** — rerun on an idle machine for the
report's timing figures.

| Instance | BKS | time | costs (3 seeds) | best | mean | gap best | gap mean | gens/s | time to best (s) |
|---|---|---|---|---|---|---|---|---|---|
| A-n32-k5 | 784 | 30 s | 784, 784, 784 | 784 | 784.0 | 0.00% | 0.00% | 14.5 | 0.2, 0.05, 0.01 |
| A-n45-k6 | 944 | 30 s | 944, 944, 944 | 944 | 944.0 | 0.00% | 0.00% | 11.4 | 4.3, 10.5, 1.9 |
| A-n60-k9 | 1354 | 60 s | 1354, 1354, 1354 | 1354 | 1354.0 | 0.00% | 0.00% | 8.8 | 21.7, 0.9, 4.2 |
| A-n80-k10 | 1763 | 60 s | 1763, 1763, 1763 | 1763 | 1763.0 | 0.00% | 0.00% | 6.3 | 42.9, 9.4, 6.8 |
| MediDrone (seed 2026, n = 100, K = 16) | – | 60 s | 16666.41, 16666.41, 16665.26 | 16665.26 | 16666.03 | – | – | 4.5 | 30.9, 24.6, 5.3 |

Ablation, plain GA (`memetic=False`, same soft Split, no LS), 30 s:

| Instance | costs (3 seeds) | best | mean | gap best | gap mean | gens/s |
|---|---|---|---|---|---|---|
| A-n32-k5 | 788, 785, 831 | 785 | 801.3 | 0.13% | 2.21% | 88.9 |
| A-n80-k10 | 2319, 2060, 2180 | 2060 | 2186.3 | 16.8% | 24.0% | 16.5 |

The plain GA does ~5–15× more generations per second but is far worse on larger
instances: OX + Split alone cannot fine-tune route order; the local search is what makes
the GA competitive (memetic = extra-credit configuration, recommended).

## 5. Known limitations / notes for the integrator

* Pure Python: one LS call on n = 80 costs ≈ 5–15 ms, so the memetic GA does only a few
  thousand LS calls per minute. Generations/s depends strongly on machine load; our table
  was produced while other jobs were running on the same machine.
* The LS assumes a symmetric distance matrix (true for EUC_2D and for MediDrone, whose
  Bosphorus penalty is symmetric).
* Feasibility: the GA returns the best *feasible* solution ever decoded. If none was found
  (never happened in our runs) it tries the exact `split` of every individual, then
  `init_routes`, and finally returns the least-violating individual (which then fails the
  checker; the caller should look at `check`).
* `init_routes` may use more than K routes; it is only used as a giant tour (re-split).
* Reproducibility: all randomness comes from `random.Random(seed)`; with `max_generations`
  and a generous `time_limit` two runs with the same seed give identical results (tested).
  Under a pure time limit the number of generations depends on machine speed.
* The plain GA (`memetic=False`) is kept for the comparison/ablation: it is fast in
  generations/s but far from the BKS; the memetic configuration is the recommended one.
