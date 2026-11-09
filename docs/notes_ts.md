# Clarke–Wright and Tabu Search: notes for the report

Code: `src/cvrp/clarke_wright.py`, `src/cvrp/moves.py`, `src/cvrp/tabu.py`.
Tests: `tests/test_cw.py`, `tests/test_tabu.py`.

Public API:

```python
from cvrp.clarke_wright import clarke_wright, extra_routes, reduce_routes, savings_list
clarke_wright(inst) -> list[list[int]]          # classical parallel savings, deterministic
extra_routes(inst, routes) -> int               # routes beyond K (0 if OK)
reduce_routes(inst, routes) -> routes           # separate repair: <= K routes (may overload)

from cvrp.tabu import solve, DEFAULT_PARAMS
solve(inst, time_limit=30.0, seed=0, params=None, init_routes=None, max_iters=None) -> Result

from cvrp.moves import delta_vs_full_benchmark, delta_cost, apply_move, move_arcs, random_move
delta_vs_full_benchmark(inst, n_samples=20000, seed=0) -> dict
```

---

## 1. Clarke–Wright savings (parallel version)

Clarke & Wright (1964). We follow the textbook description in Laporte & Semet (2002).

```
CLARKE-WRIGHT(I):
    for each customer i: route(i) <- [i]; load(route(i)) <- q_i      # n routes 0-i-0
    L <- [ (s_ij, i, j) for 1 <= i < j <= n  with  s_ij = d_0i + d_0j - d_ij > 0 ]
    sort L by decreasing s_ij (ties: (i, j) ascending)               # O(n^2 log n)
    for (s, i, j) in L:                                              # O(n^2) iterations
        A <- route(i); B <- route(j)
        if A = B or load(A) + load(B) > Q: continue
        if i is not an endpoint of A or j is not an endpoint of B: continue
        orient A so that i is last, B so that j is first (reverse if needed)
        merge: A + B   (the arcs i-0 and 0-j are replaced by i-j, saving s_ij)
    return all routes
```

**Why s_ij is the saving.** Routes `0 … i 0` and `0 j … 0` contain the arcs (i,0) and (0,j).
Merging them replaces those two arcs with (i,j), so the cost changes by d_ij − d_i0 − d_0j = −s_ij.

**Route reversal.** If i is the *first* customer of its route, we reverse the route so that i becomes last.
Since d is symmetric, reversing a route does not change its cost. All four endpoint cases are handled
(`last+first`, `first+last`, `last+last`, `first+first`).

**Complexity.** There are n(n−1)/2 savings, so building the list is O(n²) and sorting it is O(n² log n).
The scan does O(1) work per pair. There are at most n−1 merges. Each merge relabels only the customers
of the absorbed route, and the list concatenation is O(n), so all merges together cost O(n²).
The total is **O(n² log n)**, and the sort dominates it. Memory is O(n²) for the savings list.
CW runs in 0.4 ms (n=31) to 3 ms (n=79).

**Fleet size.** CW respects capacity but ignores K. On A-n45-k6 it produces 7 routes (K = 6), so
the checker rejects it as a CVRP solution. `reduce_routes` is a separate repair step and is not part
of CW. While there are more than K routes, it dissolves the route with the smallest load. It then
reinserts that route's customers, largest demand first, at the cheapest position that still has room.
If no route has room, it uses the position with the smallest overload. The result can therefore be
overloaded, and TS removes that overload through its penalty.

---

## 2. Neighbourhood and O(1) delta formulas

Notation: for customer u, `p_u` and `s_u` are its predecessor and successor. Either one may be the
depot 0. d is symmetric. A move is a tuple `(type, r1, i, r2, j)`, and `moves.py` documents every type.

| Move | What it does | Δ cost (all O(1)) |
|---|---|---|
| relocate | take u out, insert between a and b | d(a,u)+d(u,b)−d(a,b) − [d(p_u,u)+d(u,s_u)−d(p_u,s_u)] |
| swap (inter) | exchange u and v | d(p_u,v)+d(v,s_u)+d(p_v,u)+d(u,s_v) − d(p_u,u)−d(u,s_u)−d(p_v,v)−d(v,s_v) |
| 2-opt (intra) | reverse R[i..j] (a=R[i−1], b=R[j+1]) | d(a,R_j)+d(R_i,b) − d(a,R_i) − d(R_j,b) |
| 2-opt* A (inter) | R1[..u]+R2[v..], R2[..p_v]+R1[s_u..] | d(u,v)+d(p_v,s_u) − d(u,s_u) − d(p_v,v) |
| 2-opt* B (inter) | R1[..u]+rev(R2[..v]), rev(R1[s_u..])+R2[s_v..] | d(u,v)+d(s_u,s_v) − d(u,s_u) − d(v,s_v) |

Worked example for the report, relocate. Take u out of route r₁, where it sits between p and s.
Insert it into route r₂ between the consecutive vertices a and b:

$$
\Delta_{\text{reloc}}(u;a,b) \;=\; \underbrace{d_{a u} + d_{u b} - d_{a b}}_{\text{insertion cost}} \;-\; \underbrace{\big(d_{p u} + d_{u s} - d_{p s}\big)}_{\text{removal saving}}
$$

Only the three arcs at the removal point and the three arcs at the insertion point change, so Δ
costs 6 matrix look-ups no matter how long the routes are. A full re-evaluation costs O(n).
Intra-route edge cases: inserting right after p (or right before s) is a no-op, and we skip it.
Inserting right after s still satisfies the formula, because the arc (s, s_s) survives the removal.
Tests cover these cases exhaustively.

**Loads in O(1).** We keep each route's load L_r and each customer's prefix load
P(c) = Σ q over the route from its start up to and including c.

- relocate: L₁ − q_u, L₂ + q_u
- swap: L₁ − q_u + q_v, L₂ − q_v + q_u
- 2-opt* A: L₁' = P(u) + L₂ − (P(v) − q_v), L₂' = L₁ + L₂ − L₁'
- 2-opt* B: L₁' = P(u) + P(v), L₂' = L₁ + L₂ − L₁'

Intra-route moves do not change any load. Δoverload = Σ_affected max(0, L'−Q) − Σ max(0, L−Q).
After a move is applied, the two affected routes are rescanned in O(n). That rescan updates
`pred`, `succ`, `route_of`, `pos_of` and the prefix loads.

**Delta vs full evaluation (Task 6).** Measured with `delta_vs_full_benchmark(inst, 20000, seed=0)`.
It draws 20,000 random valid moves of all five types. Each move is evaluated (a) with the O(1)
formula and (b) by building the neighbour and recomputing the total cost from scratch. The
benchmark asserts that both give the same Δ (max |diff| = 0 on integer instances and 3e-12 on
MediDrone). Timings are pure Python, Apple Silicon, with other jobs running, so expect ±30% noise:

| instance | n | Δ formula (µs/move) | full: copy+apply+recompute (µs) | speed-up | recompute only (µs) | speed-up |
|---|---|---|---|---|---|---|
| A-n32-k5 | 31 | 0.62 | 7.5 | 12× | 4.9 | 8× |
| A-n45-k6 | 44 | 0.76 | 9.5 | 12× | 5.8 | 8× |
| A-n60-k9 | 59 | 0.59 | 15.6 | 26× | 14.1 | 24× |
| A-n80-k10 | 79 | 1.05 | 17.5 | 17× | 9.0 | 9× |
| MediDrone | 100 | 0.72 | 33.9 | 47× | 16.1 | 22× |

Delta evaluation is constant time. Full evaluation grows linearly in n. With about 10⁴ evaluations
per TS iteration (n·k·~5 moves), delta evaluation is what makes several hundred iterations per
second possible in Python.

---

## 3. Tabu search design

- **Search space.** There are always exactly K route slots, some of which may be empty, so the
  ≤ K constraint can never be violated. Capacity *may* be violated.
- **Objective.** f(S) = c(S) + λ · Σ_r max(0, L_r − Q). λ is adaptive: after every iteration,
  λ ← λ(1+δ) if S is overloaded, otherwise λ ← λ/(1+δ), with δ = 0.5 (Cordeau, Laporte &
  Mercier 2001). λ starts at c(S₀)/Σq, which is the distance per unit of demand, and is clamped
  to [λ₀/100, 1000·λ₀]. The rule makes the search oscillate around the capacity boundary, which
  feasible-only search cannot do. About 50% of iterations end feasible. Tight instances (A-n60-k9
  at 92% fill, A-n80-k10 at 94%) need this, because a feasible-only search gets stuck.
- **Candidate list (granular neighbourhood, Toth & Vigo 2003).** N_k(u) is the k = 20 nearest
  customers of u. For each pair (u, v ∈ N_k(u)) we evaluate only the moves that make u adjacent
  to v. If v is in another route, these are: relocate u after v, relocate u before v, swap,
  2-opt* A and 2-opt* B. If v is in the same route, they are: relocate after or before v, and the
  two 2-opt reversals that create the arc (u,v). We also evaluate "u into an empty route" whenever
  an empty slot exists.
- **Tabu attribute: arcs.** When a move *removes* the undirected arc {a,b}, recreating {a,b} is
  tabu until iteration it+θ, where θ ~ U[5, 15] is drawn per arc. Depot arcs count too, but
  {0,0} does not. A move is tabu if any arc it *creates* is tabu. Storage is an (n+1)×(n+1)
  matrix of expiry iterations, so a check costs O(1). Arcs were chosen because they work the
  same way for all five move types. A (customer, route) attribute would be ambiguous after
  2-opt*, which exchanges whole route tails.
- **Aspiration.** A tabu move is accepted if the resulting solution is feasible (current overload
  + Δoverload = 0) and its cost is below the best feasible cost found so far.
- **Move selection.** The best admissible move by Δf is applied even if Δf > 0. Customers are
  scanned in a random order each iteration, which gives random tie-breaking. If every candidate
  is tabu, the tabu list is cleared and the iteration is counted in `extra["tabu_blocked_iters"]`.
  This never happens on the n ≥ 31 instances. It does happen often on tiny instances (n ≤ 8),
  where the whole neighbourhood has only a few dozen moves.
- **Diversification.** After `stall_iters` = 40·n iterations without a new best feasible solution,
  the search restarts from the best feasible solution with a "ruin and recreate" perturbation.
  It removes 10–25% of the customers at random and reinserts them in random order at their
  cheapest penalised position. The tabu list is then cleared.
- **Returned solution.** The best feasible solution found. `Result.history` records
  (elapsed s, best feasible cost) for the first feasible solution and every improvement.
  If S₀ is feasible, this entry is at t≈0. If S₀ is overloaded after the K-repair, it is the
  first feasible solution found, usually within a few iterations. Stopping conditions are
  `time_limit` (time.perf_counter) or `max_iters`. All randomness comes from
  `random.Random(seed)`, so runs with `max_iters` are reproducible.

**One iteration and its cost.** One iteration does the following:

1. Scan all n customers and their k candidates. Each pair costs O(1) (at most 5 deltas, each with
   O(1) load and tabu checks). This takes Θ(n·k).
2. Apply the chosen move. This is O(n) (list slicing of two routes).
3. Refresh the per-customer arrays of the two affected routes and set at most 4 tabu entries.
   This is O(n).
4. Update λ and the best solution. Updating λ is O(1). Copying the routes on an improvement is O(n).

Total: **Θ(n·k)** per iteration, so Θ(n²) if k = n. The granular list is what reduces it from the
O(n²) of the full neighbourhood to O(n·k). With k = 20, k is a constant and the cost is linear in n.
A perturbation costs O(m·n) for m removed customers, but it happens only once every 40n iterations.
Measured throughput is in the table below: about 570 it/s at n=31 and about 280 it/s at n=100.

### Pseudocode

```
TABU-SEARCH(I, time_limit, seed):
    S <- CLARKE-WRIGHT(I);  if |S| > K: S <- REDUCE-ROUTES(I, S)        # <= K routes, maybe overloaded
    pad S with empty routes up to K;  λ <- c(S)/Σq;  T[a][b] <- 0 for all arcs
    N_k(u) <- k nearest customers of u, for all u
    best <- S if S is feasible else none;  it <- 0
    while time < time_limit and it < max_iters:
        it <- it + 1
        (m*, Δc*, Δo*) <- argmin over moves m in the granular neighbourhood of Δc(m) + λ·Δo(m)
                          such that  not tabu(m)  or  (o(S)+Δo(m) = 0 and c(S)+Δc(m) < c(best))
        for each arc {a,b} removed by m*:  T[a][b] <- it + U[θmin, θmax]
        S <- S ⊕ m*;  c(S) += Δc*;  o(S) += Δo*
        λ <- λ·(1+δ) if o(S) > 0 else λ/(1+δ)
        if o(S) = 0 and c(S) < c(best): best <- S
        if no improvement of best for 40n iterations:
            S <- RUIN-AND-RECREATE(best, 10–25% of customers);  clear T
    return best
```

### Recommended parameters (`DEFAULT_PARAMS`)

| param | value | notes |
|---|---|---|
| k_neighbours | 20 | k=12 or 30 was slightly worse at 15 s. k=30 runs about 2× fewer it/s |
| tenure_min / tenure_max | 5 / 15 | 10–25 was worse on A-n80 (1.2–1.4% vs 0.5%) |
| lambda_init | None → c(S₀)/Σq | |
| lambda_delta | 0.5 | 0.2 performs about the same |
| stall_iters | None → 40·n | |
| perturb_min_frac / max | 0.10 / 0.25 | |
| resync_every | 1000 | recomputes c(S) to stop float drift (MediDrone) |
| debug_check | False | True asserts every applied Δ against a full recomputation (slow) |

---

## 4. Results

Clarke–Wright (deterministic):

| instance | BKS | CW cost | gap | routes / K |
|---|---|---|---|---|
| A-n32-k5 | 784 | 842 | 7.40% | 5 / 5 |
| A-n45-k6 | 944 | 997 | 5.61% | **7 / 6 (infeasible for K)** |
| A-n60-k9 | 1354 | 1408 | 3.99% | 9 / 9 |
| A-n80-k10 | 1763 | 1840 | 4.37% | 10 / 10 |
| MediDrone-n100-s2026 | – | 17378.82 | – | 16 / 16 |

Tabu search, 3 seeds (1, 2, 3) × 30 s, default parameters. Five runs were executed in parallel on
a 10-core Apple Silicon machine. All 15 solutions pass `check` and use ≤ K routes.

| instance | BKS | best | mean | best gap | mean gap | iters/s | time to final best (s) |
|---|---|---|---|---|---|---|---|
| A-n32-k5 | 784 | 784 | 784.0 | 0.00% | 0.00% | ≈566 | 0.2–0.6 |
| A-n45-k6 | 944 | 944 | 944.0 | 0.00% | 0.00% | ≈470 | < 0.1 |
| A-n60-k9 | 1354 | 1354 | 1355.3 | 0.00% | 0.10% | ≈442 | 18–21 |
| A-n80-k10 | 1763 | 1771 | 1773.0 | 0.45% | 0.57% | ≈371 | 13–21 |
| MediDrone-n100-s2026 | – | 16800.87 | 16822.37 | (−3.33% vs CW) | (−3.20% vs CW) | ≈276 | 22–28 |

Individual runs (cost by seed 1/2/3): A-n60-k9 1354/1358/1354; A-n80-k10 1771/1777/1771;
MediDrone 16800.87/16818.35/16847.90.

Tiny instances (`generate_tiny`, n = 6–8): TS finds the exact optimum in every test case
(within 3000 iterations or 3 s). The exact optimum comes from a Held–Karp + set-partition DP in
`tests/test_tabu.py::exact_cvrp`, which is itself checked against brute force (all permutations +
optimal split).

---

## 5. Known limitations / notes for the integrator

- **Iteration speed depends on machine load.** Report iterations/s together with the hardware and
  the number of parallel runs.
- **History on overloaded starts.** If S₀ is infeasible (only possible after `reduce_routes`,
  e.g. A-n45-k6), the first history entry is the first feasible solution, not the CW cost.
  `Result.extra["initial_cost"]` holds the cost of the possibly-overloaded starting solution, and
  `extra["initial_routes"]` holds the number of routes CW (or `init_routes`) used.
- **`Result.extra`** contains: params, k, iters_per_sec, feasible_iter_fraction, perturbations,
  tabu_blocked_iters, move_counts (per move type), lambda_init and final_lambda, and feasible.
  `feasible` is False only if no feasible solution was ever found. In that case the current
  solution is returned, which has never happened in our runs.
- **Symmetric distances are assumed** (2-opt and 2-opt* B reverse segments). This holds for every
  instance in the project.
- **Not a deterministic stop.** With only `time_limit`, results depend on the machine.
  Use `max_iters` for reproducible runs.
- The TS evaluates the five formulas inline in `tabu._scan` for speed. The reference versions are
  in `moves.delta_cost`. Both are tested: the reference against full recomputation on random and
  exhaustive edge-case moves, and the inline code through `debug_check=True`, which recomputes the
  cost and overload after every applied move.
