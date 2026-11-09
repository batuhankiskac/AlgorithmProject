// Presentation (10-15 min). Build: python report/build.py
#set page(width: 25.4cm, height: 14.29cm, margin: (x: 1.4cm, top: 1.2cm, bottom: 0.9cm),
  footer: context [#set text(8pt, fill: luma(130)); CMP 3005 · MediDrone Istanbul #h(1fr) #counter(page).display()])
#set text(font: ("New Computer Modern Sans", "New Computer Modern", "Libertinus Serif"), size: 15pt)
#set par(justify: false)
#show heading.where(level: 1): it => block(below: 0.6em, text(22pt, weight: "bold", fill: rgb("#1e3a8a"), it.body))
#show table: set text(10.5pt)
#set table(stroke: (x, y) => if y == 0 { (bottom: 0.7pt) } else { none }, inset: (x: 5pt, y: 3pt))
#let slide(title, body) = { pagebreak(weak: true); heading(level: 1, title); body }
#let S = csv("../results/summary.csv", row-type: dictionary)
#let get(i, a) = S.find(r => r.instance == i and r.algo == a)
#let r2(x) = if x == "" { "–" } else { str(calc.round(float(x), digits: 2)) }
#let inst = json("../data/medidrone/medidrone.json")
#let sc = json("../results/scaling.json")
#let bos = json("../results/bosphorus.json")

// ---------- title ----------
#align(center + horizon)[
  #text(28pt, weight: "bold", fill: rgb("#1e3a8a"))[Drones, Deadlines and NP-Hardness] \
  #v(0.2em)
  #text(17pt)[Metaheuristics for a Capacitated Medical Delivery Network] \
  #v(0.8em)
  #text(13pt)[#include "../report/sections/team.typ"] \
  #text(11pt, fill: luma(100))[CMP 3005 – Analysis of Algorithms · Fall 2026–27 · Dr. Günet Eroğlu]
]

#slide[The problem: MediDrone Istanbul][
  #grid(columns: (1.1fr, 1fr), gutter: 14pt,
  [
  - A central lab (depot) and clinics on both sides of the Bosphorus
  - Each drone carries at most $Q$; every clinic is served *exactly once*; at most $K$ drones
  - Minimise the total flight distance
  - Crossing the strait costs $+P = 150$
  - This is the *Capacitated Vehicle Routing Problem (CVRP)*

  Our team instance: seed #inst.extra.seed_calculation · $n = #inst.n$, $Q = #inst.Q$, $K = #inst.K$
  ],
  image("../figures/medidrone_instance.png", height: 9.5cm))
]

#slide[Why is it hard? Two NP-hard problems in one][
  - *CVRP-DEC ∈ NP*: certificate = the routes, verified in $O(n)$
  - *Reduction chain*: Hamiltonian Cycle $<=_p$ metric TSP (weights 1/2 keep the triangle inequality) $<=_p$ CVRP ($K = 1$, $q_i = 1$, $Q = n$)
  - Composing polynomial reductions is polynomial $=>$ CVRP is NP-complete
  - *Hidden problem*: "do the customers fit into $K$ vehicles?" = *Bin Packing* $=>$ strongly NP-complete
    - even *finding a feasible solution* is hard: our benchmarks are 92–99 % full
    - Clarke–Wright returns 7 routes on A-n45-k6 ($K = 6$)!
  - *Bosphorus penalty keeps the metric*: a crossing path $i -> j -> k$ crosses at least once (it is a sum of two metrics)
]

#slide[Three algorithms, all our own code][
  #grid(columns: (1fr, 1fr, 1fr), gutter: 12pt,
  [*Clarke–Wright*
  #set text(12pt)
  - savings $s_(i j) = d_(0 i) + d_(0 j) - d_(i j)$
  - greedy merges in decreasing order
  - $O(n^2 log n)$, deterministic
  - start solution for GA and TS],
  [*Memetic GA*
  #set text(12pt)
  - giant tour + *Split* DP (shortest path in a DAG, $O(n L)$)
  - fleet-limited, soft-capacity Split
  - OX, inversion, tournament, $(mu + lambda)$, no clones
  - granular local search on 50 % of the children],
  [*Tabu Search*
  #set text(12pt)
  - relocate, swap, 2-opt, 2-opt\*
  - $O(1)$ delta evaluation
  - 20 nearest-neighbour candidate list
  - arc tabu list, aspiration
  - adaptive penalty $lambda dot "overload"$])
]

#slide[Split: decoding a giant tour optimally][
  #grid(columns: (1fr, 1fr), gutter: 14pt,
  [
  - Node $i$ = "first $i$ customers served"
  - Arc $(i, j)$ = one trip $T_(i+1) dots T_j$ if it fits in $Q$
  - Shortest $0 -> n$ path = optimal cut
  - $V(j) = min_i V(i) + c(i, j)$
  - Stop extending $j$ once load $> Q$: $O(n L)$ instead of $O(n^2)$
  - Layered version for $<= K$ routes: $O(K n L)$
  ],
  [
  #set text(11pt)
  ```
  for i = 0..n-1:
    load = 0
    for j = i+1..n:
      load += q[T_j]
      if load > Q: break
      cost = update in O(1)
      V[j] = min(V[j], V[i] + cost)
  ```
  ])
]

#slide[Complexity: theory vs. measurement][
  #grid(columns: (1fr, 1.05fr), gutter: 12pt,
  [
  - TS iteration: $Theta(n k)$ scan + $O(n)$ apply $=> Theta(n)$
    - measured slope *#calc.round(sc.fits.ts_iter_s.at(0), digits: 2)*
  - GA generation: Split $Theta(K n L)$ + local search $Theta(n g)$
    - measured slope *#calc.round(sc.fits.ga_gen_s.at(0), digits: 2)*
  - Delta evaluation: $O(1)$ vs. $Theta(n)$
    - #calc.round(sc.rows.last().delta_vs_full.speedup, digits: 0)× faster at $n = #sc.rows.last().n$
  ],
  image("../figures/scaling_loglog.png", height: 8.6cm))
]

#slide[Results (10 seeds, equal time budget)][
  #table(columns: 7, align: (left, right, right, right, right, right, right),
    [*Instance*], [*BKS*], [*CW gap %*], [*GA best / mean gap %*], [*TS best / mean gap %*], [*GA std*], [*TS std*],
    ..("A-n32-k5", "A-n45-k6", "A-n60-k9", "A-n80-k10").map(i => {
      let c = get(i, "CW"); let g = get(i, "GA"); let t = get(i, "TS")
      (i, r2(c.bks), r2(c.best_gap_pct), r2(g.best_gap_pct) + " / " + r2(g.mean_gap_pct),
       r2(t.best_gap_pct) + " / " + r2(t.mean_gap_pct), r2(g.std), r2(t.std))
    }).flatten())
  #v(0.3em)
  #grid(columns: (1fr, 1fr), gutter: 10pt,
    image("../figures/gaps_boxplot.png", height: 4.6cm),
    [#set text(12pt)
    - Tiny instances: both methods reach the DP optimum in all runs
    - Every reported solution passes the independent checker
    - Full table, convergence and statistics are in the report])
]

#slide[Convergence][
  #align(center, image("../figures/convergence_A-n80-k10.png", height: 10cm))
]

#slide[MediDrone plans and the Bosphorus][
  #grid(columns: (1.5fr, 1fr), gutter: 10pt,
  image("../figures/bosphorus_effect.png", height: 8.8cm),
  [#set text(13pt)
  - With $P = 0$: #bos.P0.cross_routes routes cross the strait (#bos.P0.cross_arcs crossing arcs)
  - With $P = 150$: #bos.P150.cross_routes routes cross (#bos.P150.cross_arcs arcs)
  - The penalty splits the fleet into European and Asian routes; the depot sits on the border, so the remaining crossings are mostly depot arcs
  ])
]

#slide[Parameter sensitivity][
  #align(center, image("../figures/param_study.png", height: 9.8cm))
]

#slide[Takeaways][
  - CVRP is NP-hard twice over (TSP *and* Bin Packing), yet good plans take seconds
  - Delta evaluation and candidate lists are what make Python fast enough
  - Allowing infeasibility with an adaptive penalty is essential on nearly full instances
  - Memetic GA (Split + local search) is the most robust; TS is very fast early on
  - No optimality guarantee, but ≤ 1 % from the best-known solutions, checked independently
  - Next steps: hybrid GA + TS, adaptive large neighbourhood search, time windows for vaccine deliveries
  #v(1em)
  #align(center, text(18pt, weight: "bold")[Thank you — questions?])
]
