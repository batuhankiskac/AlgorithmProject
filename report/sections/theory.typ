// Theory chapter: problem modelling and computational complexity.
// Included from report/main.typ; no page setup or title here.

#let thm(kind, name, body) = block(
  width: 100%,
  inset: (left: 10pt, y: 6pt),
  stroke: (left: 1.5pt + rgb("#3b6ea5")),
  [*#kind*#if name != none [ (#name)]. #emph(body)],
)
#let pf(body) = block(width: 100%, inset: (left: 10pt))[
  _Proof._ #body #h(1fr) $square$
]
#let step(name) = [*#name.*]

= Problem Modelling and Complexity <sec:theory>

In this chapter we pin down exactly which problem we are solving, show that its
decision version is NP-complete, point out a second, less obvious NP-hard problem
hidden inside it, and check that the "Bosphorus twist" of our MediDrone instance
does not break any of the assumptions the theory relies on. We close with a short
look at what is known about approximation algorithms for the CVRP.

== Formal model

An instance of the Capacitated Vehicle Routing Problem (CVRP) is a tuple
$I = (G, d, q, Q, K)$ where

- $G = (V, E)$ is a complete undirected graph with $V = {0, 1, dots, n}$; vertex $0$
  is the _depot_ (for us: the MediDrone laboratory) and $V_c = {1, dots, n}$ are the
  _customers_ (the clinics);
- $d : E -> RR^+$ assigns a distance to every edge and satisfies the triangle
  inequality $d(i, k) <= d(i, j) + d(j, k)$ for all $i, j, k in V$; we write
  $d(i,j) = d(j,i)$ since the graph is undirected;
- $q_i in ZZ^+$ is the demand of customer $i$, with $q_i <= Q$;
- $Q in ZZ^+$ is the capacity of one vehicle (the drone payload) and $K in ZZ^+$ is the
  number of identical vehicles available.

A _route_ is a sequence $R = (0, v_1, v_2, dots, v_m, 0)$ of distinct customers
$v_1, dots, v_m$ that starts and ends at the depot. Its load and cost are
$
  q(R) = sum_(t=1)^m q_(v_t), quad
  c(R) = d(0, v_1) + sum_(t=1)^(m-1) d(v_t, v_(t+1)) + d(v_m, 0).
$
A _feasible solution_ is a set $S = {R_1, dots, R_r}$ of routes such that
(i) $r <= K$, (ii) every customer belongs to exactly one route, and it appears there exactly once, and
(iii) $q(R_k) <= Q$ for every $k$. Its cost is the sum of its route costs,
$c(S) = sum_(k=1)^r c(R_k)$.

- *Optimisation version (CVRP-OPT).* Given $I$, find a feasible solution $S$ that
  minimises $c(S)$.
- *Decision version (CVRP-DEC).* Given $I$ and a bound $B$, does a feasible solution
  $S$ with $c(S) <= B$ exist?

The two versions are closely linked: an algorithm for CVRP-OPT answers CVRP-DEC
by comparing the optimum with $B$, so CVRP-OPT is at least as hard as CVRP-DEC.
This is why it is enough to study the complexity of the decision version.

A remark on number representation: when distances are Euclidean, they are
generally irrational square roots, and comparing a sum of square roots with $B$
exactly is a famously delicate question. Like CVRPLIB @cvrplib and most of the
literature @toth2014, we assume that the input distances are rational numbers
(CVRPLIB rounds them to integers), given either as a matrix or computable in
constant time from the input. All complexity statements below are made under
this standard convention.

== CVRP-DEC is in NP

#thm("Lemma 1", "membership", [CVRP-DEC $in$ NP.])

#pf[
  #step("Certificate") A certificate is the solution itself: a list of at most $K$
  routes, each written as its sequence of customer indices. Every customer appears
  in at most one place of an honest certificate, so the certificate contains at
  most $n$ customer indices of $O(log n)$ bits plus at most $K$ route separators.
  Without loss of generality $K <= n$ (more than $n$ routes would need empty routes,
  which are useless), so the certificate has size $O(n log n)$ bits, polynomial in
  the input size. If a claimed certificate is longer than this bound, the verifier
  rejects it immediately.

  #step("Verifier") Given $I$, $B$ and the certificate, the verifier:
  + checks that the number of routes $r$ is at most $K$;
  + creates a Boolean array `seen[1..n]`, initialised to false;
  + walks through every route; for each customer index $v$ it checks
    $1 <= v <= n$ and `seen[v] = false`, then sets `seen[v] = true`, adds $q_v$ to
    the route load and adds the distance from the previous vertex (the depot at
    the start) to the running cost; at the end of the route it adds the
    distance back to the depot and checks that the route load is $<= Q$;
  + checks that `seen[v] = true` for all $v$ (every customer is served);
  + accepts if and only if all checks passed and the total cost is $<= B$.

  Steps 3 and 4 together guarantee that each customer is visited exactly once,
  so the verifier accepts exactly the feasible solutions with cost at most $B$.

  #step("Running time") Each customer index is handled once with $O(1)$ work (one
  array lookup, one demand addition, one distance lookup and addition), each route
  adds $O(1)$ work for its two depot edges and the load check, and step 4 is one
  pass over the array. The total is $O(n + K) = O(n)$ arithmetic operations on
  numbers whose bit length is polynomial in the input size, hence polynomial time.
]

== CVRP-DEC is NP-hard: the reduction chain

We show NP-hardness through the chain
$
  "Hamiltonian Cycle" quad scripts(<=)_p quad "TSP-DEC (metric)" quad scripts(<=)_p quad "CVRP-DEC".
$
Hamiltonian Cycle (HC: does an undirected graph $H$ contain a cycle through every
vertex exactly once?) is one of Karp's classical NP-complete problems @karp1972
@garey1979. TSP-DEC asks, for a complete graph with edge weights $w$ and a bound
$B$, whether there is a tour (Hamiltonian cycle of the complete graph) of total
weight at most $B$.

=== Step A: Hamiltonian Cycle $scripts(<=)_p$ metric TSP-DEC

#thm("Lemma 2", none, [HC reduces in polynomial time to TSP-DEC restricted to
  instances whose weights satisfy the triangle inequality.])

#pf[
  #step("Construction") Let $H = (U, F)$ be an HC instance with $m = |U| >= 3$
  vertices. Build the complete graph on $U$ with weights
  $
    w(u, v) = cases(1 & "if" {u, v} in F, 2 & "otherwise,")
  $
  and set the bound $B = m$.

  #step("Metric") Every weight is $1$ or $2$, so for any three vertices
  $w(u, x) <= 2 = 1 + 1 <= w(u, v) + w(v, x)$. Hence $w$ satisfies the triangle
  inequality, and it is symmetric and strictly positive. This matters for us:
  our CVRP definition _requires_ a metric, so Step B can only start from a metric
  TSP instance. Reducing to general (non-metric) TSP would not be enough.

  #step("Correctness") A tour has exactly $m$ edges, each of weight at least $1$, so
  every tour weighs at least $m$, with equality if and only if all its edges have
  weight $1$.
  ($arrow.r.double$) If $H$ has a Hamiltonian cycle, the same cyclic order is a tour
  that uses only edges of $F$, so its weight is $m = B$.
  ($arrow.l.double$) If some tour has weight $<= m$, its weight is exactly $m$, so all
  of its $m$ edges have weight $1$, i.e. they all lie in $F$. That tour is
  therefore a Hamiltonian cycle of $H$.

  #step("Running time") We write $binom(m, 2) = O(m^2)$ weights, each found by one
  adjacency lookup, so the reduction runs in $O(m^2)$ time and its output has
  polynomial size.
]

=== Step B: metric TSP-DEC $scripts(<=)_p$ CVRP-DEC

#thm("Lemma 3", none, [Metric TSP-DEC reduces in polynomial time to CVRP-DEC.])

#pf[
  #step("Construction") Let the TSP instance have cities ${c_0, c_1, dots, c_n}$
  ($n >= 2$), metric weights $w$ and bound $B$. Build the CVRP instance with
  depot $0 := c_0$, customers $i := c_i$ for $i = 1, dots, n$, distances
  $d(i,j) = w(c_i, c_j)$, unit demands $q_i = 1$, capacity $Q = n$, a single
  vehicle $K = 1$, and the same bound $B$. Since $w$ is a positive metric, $d$ is
  a valid CVRP distance function, and $q_i = 1 <= n = Q$.

  #step("Correctness")
  ($arrow.r.double$) Let $T = (c_0, c_(pi(1)), dots, c_(pi(n)), c_0)$ be a tour of
  weight $<= B$ (any tour can be rotated so that it starts at $c_0$). Then
  $R = (0, pi(1), dots, pi(n), 0)$ is a single route visiting every customer
  exactly once, with load $n <= Q$; so ${R}$ is feasible with $K = 1$, and
  $c(R) = w(T) <= B$.
  ($arrow.l.double$) Let $S$ be a feasible CVRP solution with $c(S) <= B$. Since
  $K = 1$ and there is at least one customer, $S$ consists of exactly one route
  $R = (0, v_1, dots, v_n, 0)$, which by feasibility contains every customer exactly
  once. Thus $(c_0, c_(v_1), dots, c_(v_n), c_0)$ visits every city exactly once,
  it is a TSP tour, and its weight is $c(R) <= B$.

  #step("Running time") We copy $O(n^2)$ distances and write $n$ demands and three
  numbers, so the reduction takes $O(n^2)$ time.
]

Note that the capacity constraint plays no role in this reduction ($Q$ is
large enough for everything); the hardness here comes entirely from the routing
part. @sec:feasibility shows that the capacity part is hard on its own.

=== Composing the reductions

Let $f$ (Step A) run in time $O(p(N))$ and $g$ (Step B) in time $O(r(N))$ for
polynomials $p$ and $r$, where $N$ is the size of the respective input. A
machine that runs in $p(N)$ steps cannot write more than $p(N)$ output symbols,
so $|f(x)| <= p(|x|)$. Running $g$ on $f(x)$ therefore takes
$O(r(p(|x|)))$ time, and the composition of two polynomials is again a
polynomial. So $g compose f$ is a polynomial-time reduction from HC to CVRP-DEC,
and it is correct because each step preserves yes- and no-answers:
$x in "HC" <=> f(x) in "TSP-DEC" <=> g(f(x)) in "CVRP-DEC"$.

This is exactly how NP-hardness "travels" along the chain. Every problem
$L in "NP"$ reduces to HC in polynomial time, $L scripts(<=)_p "HC"$, because HC is
NP-complete. Composing that reduction with $g compose f$ gives
$L scripts(<=)_p "CVRP-DEC"$ for every $L in "NP"$, which is the definition of
CVRP-DEC being NP-hard. If CVRP-DEC had a polynomial-time algorithm, we could
solve every problem in NP in polynomial time, i.e. P $=$ NP.

#thm("Theorem 1", none, [CVRP-DEC is NP-complete, and CVRP-OPT is NP-hard.])

#pf[
  Membership is Lemma 1; NP-hardness follows from Lemmas 2 and 3 and the
  composition argument. For the optimisation version: a polynomial-time algorithm
  for CVRP-OPT would decide CVRP-DEC in polynomial time (compute the optimum $c^*$
  and answer "yes" iff $c^* <= B$; if no feasible solution exists, answer "no").
]

Because the chain only produces instances with $K = 1$, the problem is hard even
for one vehicle. It also stays hard for _planar Euclidean_ distances, since
Euclidean TSP is NP-hard as well @papadimitriou1977; so our geometric MediDrone
setting does not hide an easy special case.

== The hidden second NP-hard problem: fleet feasibility <sec:feasibility>

The CVRP really combines two difficult problems. One is routing, which we
have just seen. The other is _packing_: before we even talk about distances, we
need to decide whether the customers can be split into at most $K$ groups whose
demands fit into the vehicles.

*CVRP-FEAS.* Given demands $q_1, dots, q_n in ZZ^+$, a capacity $Q$ and a fleet
size $K$: is there a partition of the customers into at most $K$ groups
$C_1, dots, C_r$ ($r <= K$) with $sum_(i in C_k) q_i <= Q$ for every $k$?

A CVRP instance has a feasible solution if and only if the answer to CVRP-FEAS
is "yes". Indeed, a feasible solution gives such a partition (its routes), and
conversely any valid partition becomes a feasible solution by visiting the
customers of each group in an arbitrary order. In particular, CVRP-FEAS is the
special case of CVRP-DEC where the bound $B$ is so large (for example, the sum of
all edge lengths) that the cost never matters.

=== Bin Packing $scripts(<=)_p$ CVRP-FEAS

*Bin Packing (decision).* Given item sizes $s_1, dots, s_n in ZZ^+$, a bin capacity
$C$ and a number $k$: can the items be packed into at most $k$ bins of capacity
$C$? This problem is NP-complete, and even _strongly_ NP-complete
@garey1979: it stays NP-complete when all numbers are bounded by a polynomial in
$n$ (equivalently, written in unary).

#thm("Theorem 2", none, [CVRP-FEAS is NP-complete (in fact strongly NP-complete).
  Consequently, deciding whether a CVRP instance has _any_ feasible solution is
  NP-complete.])

#pf[
  #step("Membership") The certificate is an assignment $a : {1, dots, n} -> {1, dots, K}$
  of customers to vehicles ($O(n log K)$ bits). The verifier adds every $q_i$ to the
  load of vehicle $a(i)$ and checks that no load exceeds $Q$, in $O(n + K)$ time.

  #step("Construction") Given a Bin Packing instance $(s_1, dots, s_n, C, k)$, we may
  assume $s_i <= C$ for all $i$ (otherwise the answer is trivially "no" and we
  output a fixed "no" instance). Create one customer per item with $q_i = s_i$, set
  $Q = C$ and $K = k$, and use any valid metric, for example $d(i, j) = 1$ for all
  $i != j$ (which clearly satisfies the triangle inequality, as $1 <= 1 + 1$).

  #step("Correctness") Customers correspond one-to-one to items, vehicles to bins, and
  the load constraint $sum_(i in C_k) q_i <= Q$ is literally the bin constraint
  $sum_(i in C_k) s_i <= C$. So a packing into at most $k$ bins is exactly a
  partition of the customers into at most $K$ groups of load at most $Q$, and vice
  versa.

  #step("Running time") $O(n)$ for the numbers, plus $O(n^2)$ if the unit distance
  matrix is written out explicitly. The reduction does not change any number, so
  it maps instances with polynomially bounded numbers to instances with
  polynomially bounded numbers; this transfers _strong_ NP-completeness.
]

Strong NP-completeness has a practical meaning: unless P $=$ NP, there is not
even a _pseudo-polynomial_ algorithm for CVRP-FEAS, i.e. one that is polynomial
in $n$ and in the numeric value of $Q$. So our small integer demands do not
help in the worst case. The special case $K = 2$ is already hard: Partition
(split integers with total $2 S$ into two halves of sum $S$ each) is the case
$Q = S$, $K = 2$. Partition is only weakly NP-complete, and indeed for a fixed
number of vehicles a subset-sum style dynamic program runs in pseudo-polynomial
time, which is consistent with the above.

*Consequences for approximation.* Since even deciding whether a feasible
solution with at most $K$ vehicles exists is NP-complete, no polynomial-time
algorithm can guarantee any finite approximation ratio for CVRP-OPT with a hard
fleet limit unless P $=$ NP: such an algorithm would in particular have to
output a feasible solution whenever one exists, which would decide CVRP-FEAS.
The approximation results in the last section therefore assume an unlimited
fleet.

=== What this means for our metaheuristics

For a local search or a genetic algorithm, Theorem 2 says that even _staying
feasible_ is a nontrivial combinatorial task. How hard it is in practice depends
on the _fill ratio_
$
  rho = (sum_(i=1)^n q_i) / (K Q),
$
the fraction of the total fleet capacity that the demand uses. When $rho$ is
close to $1$, there is almost no slack: only few partitions of the customers fit
into $K$ vehicles, and two such partitions can be far apart, with every path of
small moves between them passing through overloaded solutions. The feasible
region is then fragmented into many small "islands". Our two tight
CVRPLIB benchmarks @augerat1995 are exactly of this type: A-n60-k9 has
$rho = 829 slash 900 approx 92%$ and A-n80-k10 has $rho = 942 slash 1000 approx 94%$.

This is the theoretical reason behind two design decisions described in the
algorithm chapters. Our Tabu Search @glover1997 is allowed to visit
_infeasible_ intermediate solutions: it minimises $c(S) + lambda dot "overload"(S)$,
where $"overload"(S) = sum_k max(0, q(R_k) - Q)$ and the penalty weight $lambda$ is
adapted during the search (raised while the search keeps being infeasible,
lowered while it stays feasible), so that it can cross between islands instead of
being trapped in one. Our genetic algorithm decodes giant tours with a
_fleet-limited_ Split procedure in the spirit of Prins @prins2004, which only
accepts segmentations that use at most $K$ routes.

In our own MediDrone instance the situation is easier. The fleet is
$K = ceil(sum_i q_i slash Q) + 1$, so there is one full spare vehicle, i.e. at
least $Q$ units of unused capacity, and the demands ($q_i <= 30$) are small
compared with $Q = 100$. Feasibility is still NP-hard in the worst case, but for
such instances it is easy in practice: small items can be packed tightly, and
the spare vehicle absorbs whatever packing loss remains.

== The Bosphorus twist keeps the metric

Our MediDrone instance places all vertices in the square $[0, 1000]^2$. Let
$sigma(i) in {E, A}$ be the side of vertex $i$ ($E$, European, if $x_i < 500$,
otherwise $A$, Asian; the depot at $(500, 500)$ is on the Asian side). With
$e(i, j)$ the Euclidean distance and $P = 150$ the crossing penalty, the team
distance is
$
  d'(i, j) = e(i, j) + P dot [sigma(i) != sigma(j)],
$
where $[dot]$ is $1$ if the condition holds and $0$ otherwise. Since the CVRP
definition (and the reductions above, the shortcutting arguments used by
heuristics, and the approximation bounds below) all assume a metric, we have to
check that the penalty does not destroy this property.

#thm("Lemma 4", none, [$d'$ is symmetric, satisfies the triangle inequality, and
  $d'(i,j) > 0$ whenever $i$ and $j$ are at different locations.])

#pf[
  #step("Symmetry") Both $e$ and the condition $sigma(i) != sigma(j)$ are symmetric in
  $i$ and $j$.

  #step("Positivity") $d'(i,j) >= e(i,j) > 0$ for distinct locations. If two
  customers happened to share a location, $d'$ would be $0$ between them (they
  are then on the same side), so strictly speaking $d' : E -> RR^+$ needs distinct
  locations. With continuously distributed coordinates this essentially never
  happens, and even then $d'$ is still a pseudometric, which is all that our
  algorithms and the arguments below use.

  #step("Triangle inequality") Fix $i, j, k$. We must show
  $d'(i,k) <= d'(i,j) + d'(j,k)$. The Euclidean parts already satisfy
  $e(i,k) <= e(i,j) + e(j,k)$, so it suffices to show that the penalty on the left
  is at most the total penalty on the right.
  - _Case 1: $sigma(i) = sigma(k)$._ The left-hand side has no penalty, so
    $d'(i,k) = e(i,k) <= e(i,j) + e(j,k) <= d'(i,j) + d'(j,k)$ because penalties are
    non-negative.
  - _Case 2: $sigma(i) != sigma(k)$._ The left-hand side is $e(i,k) + P$. Vertex $j$
    lies on one of the two sides, so it differs from exactly one of $i$ and $k$:
    exactly one of the legs $i$–$j$ and $j$–$k$ crosses the Bosphorus. Hence the
    right-hand side equals $e(i,j) + e(j,k) + P >= e(i,k) + P$.
  In both cases the inequality holds.
]

*A one-line alternative.* The indicator $delta(i,j) = [sigma(i) != sigma(j)]$ is
itself a pseudometric, the _cut metric_ of the partition $\{E, A\}$: it is
symmetric, $delta(i,i) = 0$, and its triangle inequality is exactly Case 2 above.
A non-negative combination of (pseudo)metrics is again a (pseudo)metric, because
the triangle inequalities can simply be added. Therefore
$d' = e + P dot delta$ is a metric. The same argument would work for any number
of regions and any non-negative crossing costs that themselves form a metric
on the regions.

Lemma 4 means that the MediDrone instance is a valid CVRP instance in the sense
of our formal model, so everything in this chapter applies to it. It also
justifies a property our local search relies on: removing a customer from a
route never increases that route's cost, because the shortcut $d'(u, w)$ is at
most $d'(u, v) + d'(v, w)$.

== Bonus: approximation algorithms for the CVRP

Since an exact polynomial algorithm is out of reach unless P $=$ NP, one can ask
for algorithms with a _guaranteed_ ratio to the optimum. In this section we assume
an unlimited fleet (see the remark after Theorem 2) and a metric $d$. Let
$"OPT"$ be the optimal CVRP cost and $"TSP"^*$ the optimal TSP tour length on
$V$ (depot included).

*Two lower bounds.* First, $"OPT" >= "TSP"^*$: concatenating all routes of an
optimal solution at the depot gives a closed walk that visits every vertex, and
shortcutting repeated depot visits (allowed by the triangle inequality) turns it
into a tour that is not longer. Second, the _radial bound_
$
  "OPT" >= 2 / Q sum_(i=1)^n q_i d(0, i).
$
To see this, take any route $R$ of an optimal solution and its farthest customer
$v$. By the triangle inequality, both the part of the route from the depot to $v$
and the part back are at least $d(0,v)$ long, so
$c(R) >= 2 max_(i in R) d(0,i) >= 2 sum_(i in R) (q_i / Q) d(0,i)$, where the last
step uses $sum_(i in R) q_i <= Q$ (a weighted average of the $d(0,i)$ with weights
$q_i slash Q$ is at most their maximum). Summing over all routes gives the bound.

*Iterated Tour Partitioning (ITP).* Haimovich and Rinnooy Kan @haimovich1985
proposed the following scheme: compute an $alpha$-approximate TSP tour through
the depot and all customers, then cut it into consecutive segments of load at
most $Q$, each served by a route from and back to the depot; the cutting point is
chosen as the best among the $Q$ possible offsets (or at random). The cost of
the extra depot connections can be charged against the radial bound, and the
tour itself against $"TSP"^* <= "OPT"$. For unit demands (equivalently, when
demands may be split between vehicles) this yields a ratio of
$1 + (1 - 1 slash Q) alpha$. For unsplittable demands, Altinkemer and Gavish
@altinkemer1987 showed a ratio of $2 + (1 - 2 slash Q) alpha$.

With Christofides' algorithm @christofides1976, $alpha = 3 slash 2$, this gives
about $2.5$ for unit demands and about $3.5$ for unsplittable demands. For many
years these were the best known bounds. Blauth, Traub and Vygen @blauth2022
showed that both can be improved by a small but fixed constant (that is, the
ratio becomes strictly below $alpha + 1$ and $alpha + 2$, respectively). On the
TSP side, Karlin, Klein and Oveis Gharan @karlin2021 gave the first algorithm
with a ratio slightly below $3 slash 2$ for metric TSP (the improvement is
tiny, on the order of $10^(-36)$), which can be plugged into the bounds above.

These guarantees are worst-case, and the constants are large compared with what
metaheuristics achieve on real benchmarks (typically within a few percent of
the best known solutions, see our experiments). Their value for us is
conceptual: the radial bound and $"TSP"^*$ give cheap lower bounds that tell us
how far from optimal a solution can be at most, and the "giant tour, then cut"
idea of ITP is exactly the principle behind the Split decoder in our genetic
algorithm.
