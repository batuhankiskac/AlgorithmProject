#let sc = json("../../results/scaling.json")
#let fit(k) = calc.round(sc.fits.at(k).at(0), digits: 2)
#let ms(x) = str(calc.round(x * 1000, digits: 3))

= Complexity Analysis of Our Own Code <sec:complexity>

We use $n$ for the number of customers, $K$ for the fleet size and $L$ for the maximum number of customers on one route; for our data $L approx Q\/macron(q) approx 6.5$. The GA has population $mu$ and $lambda_"off"$ children per generation. The local search and the Tabu Search use $g = k = 20$ granular neighbours.

== One GA generation

One generation creates $lambda_"off"$ children and then performs replacement. Per child:

- two binary tournaments: $O(1)$
- OX crossover and inversion: $O(n)$ each
- soft layered Split: $O(K n L')$ with $L' approx 1.5 L$
- duplicate test: $O(mu + lambda_"off")$

Once per generation, the penalty update, $(mu+lambda_"off")$ truncation (a sort) and the diversity measurement (pairwise edge-set distance) cost $O((mu+lambda_"off") log(mu+lambda_"off") + mu^2 n)$. For the plain GA
$ T_"gen" = O(lambda_"off" (K n L + mu + lambda_"off") + mu^2 n), $
which is $O(lambda_"off" K n^2)$ in the worst case $L = n$. In our setting $K approx n \/ 6.5$ and $L$ is constant, so the Split term behaves like $Theta(n^2)$ but with a small constant, and the diversity term is linear in $n$. The memetic GA adds, for a fraction $p_"ls"$ of the children, a local search that costs $Theta(n g)$ per pass over all customers, plus $O(L)$ per applied move. The number of passes is not bounded polynomially a priori, since each applied move only has to decrease $f$, but empirically it is a small constant. We therefore predict per-generation growth between $n^1$ (local-search dominated) and $n^2$ (Split dominated).

== One TS iteration

One iteration scans every customer $u$ and its $k$ candidates. Each pair yields at most five moves, and each is evaluated in $O(1)$: an arc delta, a load update from prefix loads, and a tabu-matrix lookup. Applying the chosen move and rebuilding the position, predecessor, successor and prefix-load arrays of the two touched routes costs $O(n)$, and the tabu and $lambda$ updates cost $O(1)$. Hence
$ T_"iter" = Theta(n k) + O(n) = Theta(n) quad "for fixed" k. $
Without the candidate list, the full relocate/swap neighbourhood has $Theta(n^2)$ moves, so an iteration would cost $Theta(n^2)$ even with delta evaluation. Without delta evaluation each move costs $Theta(n)$, giving $Theta(n^3)$.

== What delta evaluation saves

Re-evaluating a neighbour from scratch costs $Theta(n)$: copying and changing the routes, then summing $n + K$ arcs. A delta costs $O(1)$. With about $5 n k$ candidate moves per iteration, delta evaluation turns $Theta(n^2 k)$ work into $Theta(n k)$, a factor of $Theta(n)$. We measured both methods on 5,000 random moves of all types (`moves.delta_vs_full_benchmark`). The function also asserts that the two methods agree.

#figure(
  table(columns: 5, align: (right, right, right, right, right),
    [*$n$*], [*delta (µs/move)*], [*full re-evaluation (µs/move)*], [*speed-up*], [*recompute cost only*],
    ..sc.rows.map(r => {
      let d = r.delta_vs_full
      (str(r.n), str(calc.round(d.delta_us_per_move, digits: 2)), str(calc.round(d.full_us_per_move, digits: 1)),
       str(calc.round(d.speedup, digits: 1)) + "×", str(calc.round(d.full_cost_only_us_per_move, digits: 1)) + " µs")
    }).flatten()),
  caption: [Delta evaluation vs. full re-evaluation of a move. The delta cost stays flat while full evaluation grows linearly with $n$.]) <tab:delta>

== Empirical validation

We generated MediDrone-style instances with $n in {25, 50, 100, 200, 400, 800}$ ($Q = 100$, demands $U[1,30]$). For each we timed a solver run of $a$ and of $b$ iterations from the same Clarke–Wright start. We took $(t_b - t_a)\/(b - a)$ as the time per iteration, which cancels the set-up cost, and used the median of three repetitions. @fig:scaling shows the results on a log–log scale. The fitted slopes are:

- GA generation: *#fit("ga_gen_s")*
- TS iteration: *#fit("ts_iter_s")*
- Split: *#fit("split_s")*
- Clarke–Wright: *#fit("cw_s")*

#figure(image("../../figures/scaling_loglog.png", width: 78%), caption: [Measured time per unit of work vs. $n$ (log–log) with least-squares slopes.]) <fig:scaling>

#include "complexity_discussion.typ"
