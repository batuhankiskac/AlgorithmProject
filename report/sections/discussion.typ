= Discussion and Reflection <sec:discussion>

== Which algorithm is better, and why?

Under equal time budgets the *memetic GA is the more robust method*. It reaches the BKS in 38 of 40 benchmark runs, and its ten MediDrone runs end within 0.4% of each other. Tabu Search is equally good on instances with $n <= 60$ and finds good solutions very early. On A-n80-k10 and MediDrone, however, it stalls 0.1–0.4% above the GA. We see three reasons in our data:

+ *Global vs. local structure.* OX crossover recombines whole route fragments from two good parents, and Split re-optimises where the routes are cut. TS changes at most two routes per iteration, so moving from one good arrangement of the fleet to a different one takes many deteriorating steps. The arc tabu list with tenure 5–15 only partly enables those steps.
+ *Variance.* TS outcomes depend on which basin the trajectory happens to enter (standard deviation 5.3 on A-n80-k10). A population of 25 solutions hedges against this.
+ *The GA contains our best local search.* @fig:param shows that without local search the GA is 4% above the BKS on A-n60-k9. That is worse than TS, even though it runs 3.7 times more generations. The strength of the GA therefore comes from the *combination* of recombination and an intensive, Tabu-like neighbourhood. This is exactly the hybrid that the literature recommends @vidal2012.

TS has its own strengths. It is simpler (one solution, no decoder), it is the fastest to a usable plan (on A-n80-k10 every TS run is within 2% of the BKS after at most 1.3 s, the GA needs up to 2.1 s), and an iteration is cheap enough to scale linearly in $n$ (@sec:complexity). If the CTO needed a plan in under a second, TS would be our choice.

== How did the Bosphorus penalty change the routes?

Less than we expected, and the reason is instructive. The penalty does change the routes, but only a little. Without it ($P = 0$), 10 routes cross the strait (20 crossing arcs); with $P = 150$, 9 routes do (18 arcs), and the Euclidean length rises from 17 200 to 17 217. The $P = 150$ plan in @fig:bos has 9 routes that serve only European clinics, 8 that serve only Asian clinics, and *none mixes the two sides*. The best GA plan in @fig:routes has one mixed route instead.

The explanation is geometric. The depot lies at $x = 500$, which is formally on the Asian side. Every route that visits Europe must cross at least once on the way out and once on the way back. A route visiting both sides also needs only these two crossings (depot $->$ Europe $->$ Asia $->$ depot). Hence, for *any* plan, the penalty equals $2P$ times the number of routes that visit Europe. With a European demand of 871 and $Q = 100$, at least $ceil(871\/100) = 9$ such routes are needed, so the penalty is at least $2 dot 150 dot 9 = 2700$. The $P = 150$ plan attains this bound, as the costs confirm: $19 916.6 - 17 216.6 = 2700$. In our instance the penalty therefore acts as a *fixed cost per European route*. The only incentive it creates is to pack the European clinics into as few, full routes as possible, and the European routes of that plan are indeed loaded to 86–100. It would shape the geometry of the routes much more if the depot were far from the strait.

== Parameter sensitivity

#figure(image("../../figures/param_study.png", width: 100%), caption: [Parameter studies, 5 seeds × 20 s per setting. Left: TS tenure range $[t\/3, t]$. Middle: GA mutation probability, with final population diversity (green, mean pairwise share of different arcs). Right: GA with and without local search.]) <fig:param>

- *Tabu tenure* shows the classic U-shape. With $t = 3$ the search cycles back into the same local optima (mean gap 1.4%). With $t >= 30$ too many moves are forbidden, and the search is pushed away from good regions (0.8–1.0%). The range 7–15 is best (about 0.2%), which confirms our default $[5, 15]$.
- *Mutation rate* matters much less. Every setting finds the BKS at least once, the mean gap varies only between 0.02% and 0.14%, and the minimum is at our default $p_"mut" = 0.2$. Final diversity stays at 0.27–0.34 for all rates. The spacing rule and the restarts, not mutation, are what keep the memetic GA diverse.
- *Memetic ablation.* Turning local search off raises the gap from 0% to 4%. At the same time the population diversity collapses from 0.36 to 0.14: without local search, OX + Split converges prematurely to one family of solutions.

== Theory vs. practice

@sec:theory proves that we cannot expect a polynomial algorithm with a guarantee of optimality. Approximation theory offers polynomial algorithms with *guaranteed* worst-case ratios. For CVRP with unsplittable demands, the classical iterated tour partitioning bound with Christofides' algorithm is about 3.5. That is a statement about the worst case: a dispatcher would accept 250% extra flight distance. Our metaheuristics give *no* guarantee at all; we could not even bound the number of local-search passes polynomially. Yet in every test where the optimum is known they are within 0–0.25% of it, and they produce a plan in seconds.

Industry accepts algorithms without guarantees for four reasons:

- the worst cases behind approximation ratios rarely look like real instances;
- performance can be *measured* on representative data, which is exactly what CVRPLIB is for;
- the time budget can be traded for quality;
- an independent checker guarantees what really matters operationally: feasibility.

Guarantees still have practical value. Lower bounds such as the radial bound tell us how far a plan *could* be from optimal, and approximation algorithms make safe fallbacks. In practice the two worlds complement each other.

// == Personal reflection
// TEAM: write this section yourselves (assignment, Task 7, "human part").
// Uncomment the heading above and answer the three questions:
// *What surprised us most.* ...
// *Hardest bug.* ... (what it was, and how you found it)
// *What we would try next.* ... (e.g. hybrid GA + TS, ALNS, time windows)
