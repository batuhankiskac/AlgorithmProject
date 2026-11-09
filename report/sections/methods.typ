#let algo(title, body) = figure(kind: "algorithm", supplement: [Algorithm], caption: title,
  block(width: 100%, stroke: 0.5pt + luma(170), inset: 7pt, radius: 2pt, align(left, text(8.4pt, body))))

= Methodology <sec:methods>

All three methods share one representation: a solution is a list of routes, each a list of customers without the depot. Distances live in a precomputed $(n+1) times (n+1)$ matrix, with CVRPLIB distances rounded with `nint`. We validated our parser by loading the published optimal solutions of all four benchmarks. They evaluate to exactly 784, 944, 1354 and 1763. An *independent feasibility checker* recomputes every reported solution from the raw coordinates and the Bosphorus rule, without reusing the solvers' distance matrix. It checks that every customer is served exactly once, that every load is at most $Q$, that there are at most $K$ routes, and that the reported cost is correct.

== Constructive baseline: Clarke–Wright savings

We use the classical *parallel* savings algorithm @clarke1964. It starts from $n$ routes $0 -> i -> 0$ and computes $s(i,j) = d(0,i) + d(0,j) - d(i,j)$ for all pairs. Merging a route that ends in $i$ with a route that starts in $j$ replaces the arcs $(i,0)$ and $(0,j)$ by $(i,j)$, which saves exactly $s(i,j)$. The pairs are scanned in decreasing order of saving. A merge is performed if $i$ and $j$ are endpoints of different routes and the combined load fits. A route is reversed when needed; this is free because $d$ is symmetric.

*Complexity.* There are $n(n-1)\/2$ savings. Computing them takes $O(n^2)$ and sorting takes $O(n^2 log n)$. The scan does $O(1)$ work per pair. At most $n-1$ merges happen; each relabels the customers of one route and concatenates two lists in $O(n)$, so $O(n^2)$ in total. Overall *$O(n^2 log n)$ time and $O(n^2)$ memory*, dominated by the sort. Clarke–Wright respects capacity but *ignores the fleet limit $K$*. On A-n45-k6 it returns 7 routes for $K = 6$, a concrete instance of the hidden Bin Packing problem of @sec:feasibility. The metaheuristics therefore never trust the start solution to be $K$-feasible.

== Genetic Algorithm with giant tours and Split

Following Prins @prins2004, a chromosome is a *giant tour*: a permutation $T = (T_1, dots, T_n)$ of the customers without route delimiters. Every permutation is a valid chromosome, so standard permutation crossovers can be used without repair. The routes are recovered by an exact decoder.

*Split as a shortest path.* Build a DAG $H$ with nodes $0, 1, dots, n$, where node $i$ means "the first $i$ customers of $T$ are served". There is an arc $(i,j)$ for $i < j$ iff $sum_(k=i+1)^j q_(T_k) <= Q$. Its cost is the cost of the trip $0 -> T_(i+1) -> dots -> T_j -> 0$. Each $0$–$n$ path is a segmentation of $T$ into feasible routes, and vice versa. Since arcs only go forward, Bellman's recurrence on the DAG solves it in one pass:
$ V(0) = 0, quad V(j) = min_(i < j, (i,j) in A) { V(i) + c(i,j) }, $
and the answer is $V(n)$, with routes recovered from the predecessor of each node.

*Complexity.* For a fixed $i$, the trip $(i, j+1)$ is obtained from $(i,j)$ in $O(1)$: $c(i,j+1) = c(i,j) - d(T_j, 0) + d(T_j, T_(j+1)) + d(T_(j+1), 0)$. The inner loop *stops at the first $j$ whose load exceeds $Q$*, because demands are positive, so every longer trip is infeasible too. If a route holds at most $L$ customers, each of the $n$ outer iterations does at most $L$ inner steps, giving $O(n L)$. In general $L <= n$, so $O(n^2)$. For our data $L approx Q \/ macron(q) approx 6.5$, and Split is effectively linear. To respect the fleet limit we also implement the *layered* version $V_k (j) = min_i {V_(k-1) (i) + c(i,j)}$ (exactly $k$ routes), which costs $O(K n L)$.

*Soft capacity.* On tight instances almost no permutation has a capacity-feasible split into $<= K$ routes. We measured 0% of random tours on A-n45-k6 (fill 98.8%) and 22% on A-n80-k10. The GA therefore decodes with a soft layered Split: trips may carry up to $1.5 Q$, and overload costs $lambda$ per unit. $lambda$ is adapted after every generation so that about 40% of the children are feasible (multiplied by 1.2 below 35%, by 0.85 above 45%). This follows Vidal et al.'s penalty idea @vidal2012. The exact hard Split is applied again to every feasible local-search result.

*Operators.*
- *Initial population.* The Clarke–Wright giant tour, 30% *sweep* orders (customers sorted by polar angle around the depot), and random permutations. Clones are rejected.
- *Selection.* Binary tournament: $O(1)$, mild pressure, no fitness scaling needed.
- *Crossover.* Order Crossover (OX) with $p_"cx" = 0.9$. It copies a slice of parent 1 (consecutive customers, i.e. partial routes) and fills the rest in parent 2's relative order, in $O(n)$.
- *Mutation.* Segment inversion with $p_"mut" = 0.2$. It changes only two adjacencies of the tour (a 2-opt move), so it perturbs without destroying route structure.
- *Memetic local search* (extra credit). Applied to a child with probability $p_"ls" = 0.5$. It uses the same move types as the Tabu Search (relocate, swap, 2-opt, both 2-opt\* variants) on a granular neighbourhood of the 20 nearest customers, with first improvement and $O(1)$ deltas. An overloaded result is repaired with probability 0.5 by re-running the search with $10 lambda$ and then $100 lambda$.
- *Replacement and diversity.* $(mu + lambda)$ truncation with $mu = lambda_"off" = 25$, which is elitist by construction. A child whose fitness is within $Delta = 0.5$ of an existing individual is rejected (Prins' spacing rule). After 60 generations without improvement, all but the 2 best individuals are replaced by new random ones.

== Tabu Search

The Tabu Search works directly on routes. It always keeps exactly $K$ route slots, some possibly empty, so the fleet limit can never be violated; capacity may be. The search starts from Clarke–Wright. If that uses more than $K$ routes, the routes with the smallest load are dissolved and their customers reinserted at the cheapest position, accepting overload.

*Objective and capacity handling.* We minimise $f(S) = c(S) + lambda dot sum_r max(0, L_r - Q)$, where $L_r$ is the load of route $r$. We chose to *allow* infeasible moves. @sec:feasibility shows that feasibility itself is NP-hard, and on 92–99% full instances a feasible-only search gets trapped between few feasible regions. $lambda$ adapts every iteration, as in Cordeau et al. @cordeau2001: it is multiplied by $1.5$ if the current solution is overloaded and divided by $1.5$ otherwise. It starts at $c(S_0)\/sum q$. The search thus oscillates around the feasibility border; about half of the iterations end feasible. The best *feasible* solution is returned.

*Neighbourhood and candidate list.* Four move families are used: relocate (inside a route or to another route, including an empty one), swap (between routes), 2-opt (inside a route) and 2-opt\* (exchanging route tails, in both orientations). To keep iterations fast we use a *granular* candidate list @toth2003: for each customer $u$ and each of its $k = 20$ nearest neighbours $v$, only moves that make $u$ adjacent to $v$ are evaluated. The best admissible move is applied even if it worsens $f$.

*Delta evaluation.* Every move changes a constant number of arcs, so its cost change is computed in $O(1)$. For relocating $u$ (between $p$ and $s$) to a position between $a$ and $b$:
$ Delta_"reloc" = underbrace(d(a,u) + d(u,b) - d(a,b), "insertion cost") - underbrace((d(p,u) + d(u,s) - d(p,s)), "removal saving"). $
The other formulas are analogous. A 2-opt move reversing $R[i..j]$ costs $d(R_(i-1), R_j) + d(R_i, R_(j+1)) - d(R_(i-1), R_i) - d(R_j, R_(j+1))$; the same holds for 2-opt\* and swap. Load changes are also $O(1)$: we maintain route loads and per-customer prefix loads, so a 2-opt\* tail exchange gives $L'_1 = P(u) + L_2 - P(p_v)$. Unit tests compare every formula against full recomputation on thousands of random and edge-case moves.

*Tabu list and aspiration.* The attribute is an *arc*. When a move removes the undirected arc ${a,b}$, recreating it is tabu for $theta tilde U[5,15]$ iterations, drawn per arc. A move is tabu if any arc it creates is tabu. Arcs work uniformly for all move types; a "(customer, route)" attribute would be ambiguous after a 2-opt\* tail exchange. Tabu status is stored in an $(n+1)^2$ matrix of expiry iterations, so checking is $O(1)$. *Aspiration*: a tabu move is allowed if it yields a feasible solution better than the best found so far.

*Diversification and stopping.* After $40 n$ iterations without a new best, the search restarts from the best solution with a ruin-and-recreate step. It removes 10–25% of the customers and reinserts them at their cheapest penalised position. The search stops at the wall-clock budget.

#grid(columns: (1fr, 1fr), gutter: 8pt,
algo([Split (Prins) with capacity cut-off])[```
SPLIT(T):                       // T = giant tour
  V[0] = 0; V[1..n] = INF
  for i = 0 .. n-1:
    load = 0; j = i + 1
    while j <= n:
      load += q[T_j]
      if load > Q: break        // => O(n L)
      cost = (j == i+1) ? d(0,T_j) + d(T_j,0)
           : cost - d(T_{j-1},0)
             + d(T_{j-1},T_j) + d(T_j,0)
      if V[i] + cost < V[j]:
        V[j] = V[i] + cost; P[j] = i
      j += 1
  return V[n], routes read from P
```],
algo([Clarke–Wright savings])[```
CW(I):
  each customer i: route {i}
  S = [(d0i + d0j - dij, i, j) : i < j]
  sort S by decreasing saving   // O(n^2 log n)
  for (s, i, j) in S:
    A = route(i); B = route(j)
    if A == B or load(A)+load(B) > Q:
      continue
    if i, j not endpoints: continue
    orient A to end in i, B to start in j
    merge A + B
  return routes
```]
)
#grid(columns: (1fr, 1fr), gutter: 8pt,
algo([Memetic GA])[```
GA(I, T_max):
  P = decode(CW tour, sweep tours, random tours)
  while time < T_max:                 // one generation
    C = {}
    repeat lambda_off times:
      p1, p2 = TOURNAMENT(P), TOURNAMENT(P)
      t = OX(p1, p2) w.p. p_cx else copy(p1)
      INVERT random segment of t  w.p. p_mut
      x = SOFT-SPLIT(t, K, lambda)
      w.p. p_ls: x = LOCAL-SEARCH(x); re-split
      if x not within Delta of P u C: C += x
    adapt lambda to 40% feasible children
    P = mu best of P u C               // elitist
    if 60 gens w/o improvement: restart
  return best feasible solution seen
```],
algo([Tabu Search])[```
TS(I, T_max):
  S = CW(I); reduce to <= K routes
  lambda = c(S)/sum q; best = S if feasible
  while time < T_max:                 // one iteration
    m* = argmin over u, v in N_k(u), moves
         creating arc (u,v):  dc(m) + lambda*do(m)
         s.t. not tabu(m) or aspiration(m)
    make arcs removed by m* tabu
       for U[5,15] iterations
    S = S + m*                         // O(n)
    lambda *= 1.5 if overloaded else /= 1.5
    if feasible and c(S) < c(best): best = S
    if 40n iterations w/o improvement:
      S = RUIN-RECREATE(best)
  return best
```]
)
