// Milestone 1 (theory & data), 2-3 pages. Build: python report/build.py
#set page(paper: "a4", margin: 2.2cm, numbering: "1")
#set text(font: ("New Computer Modern", "Libertinus Serif"), size: 10.5pt)
#set par(justify: true)
#set heading(numbering: "1.")
#let inst = json("../data/medidrone/medidrone.json")
#let tiny = json("../data/tiny/optima.json")

#align(center)[
  #text(15pt, weight: "bold")[Milestone 1: Theory and Data] \
  CMP 3005 Term Project · MediDrone Istanbul · Team: #include "sections/team.typ"
]

= Problem definitions
*Instance.* A complete undirected graph $G=(V,E)$, $V={0,dots,n}$ with depot $0$; metric distances $d: E -> RR^+$; demands $q_i in ZZ^+$ with $q_i <= Q$; capacity $Q$; fleet size $K$. *Feasible solution*: at most $K$ routes, each starting and ending at the depot, every customer on exactly one route exactly once, and $sum_(i in R) q_i <= Q$ for every route $R$.

*Optimisation version:* minimise $sum_R (d(0,v_1) + sum_(t=1)^(m-1) d(v_t, v_(t+1)) + d(v_m, 0))$ over feasible solutions.
*Decision version (CVRP-DEC):* given $(G,d,q,Q,K)$ and $B$, is there a feasible solution of total distance $<= B$?

= Reduction sketches
- *CVRP-DEC $in$ NP.* Certificate: the list of routes ($<= n + K$ numbers). The verifier checks that each customer appears exactly once, each load is $<= Q$, there are $<= K$ routes and the total cost is $<= B$, in $O(n + K) = O(n)$ time.
- *Hamiltonian Cycle $<=_p$ TSP-DEC.* Given $H=(V,E_H)$, build a complete graph with $w(u,v)=1$ if $u v in E_H$, else $2$, and $B=|V|$. Building it takes $O(|V|^2)$. A Hamiltonian cycle gives a tour of cost $|V|$. Conversely, a tour of cost $<= |V|$ has $|V|$ edges of weight $>= 1$, so all have weight 1 and lie in $E_H$. Weights in ${1,2}$ satisfy the triangle inequality, so the target is *metric* TSP. Our CVRP definition requires a metric, so this matters.
- *TSP-DEC $<=_p$ CVRP-DEC.* City 1 becomes the depot and the others become customers with $q_i = 1$, $Q = n$, $K = 1$, same $d$ and $B$. A single route visiting all customers is exactly a Hamiltonian tour, and the costs are equal.
- *Composition.* The first reduction's output has polynomial size, so running the second on it is still polynomial. Hence HC $<=_p$ CVRP-DEC, so CVRP-DEC is NP-complete and the optimisation version is NP-hard.
- *Hidden problem: fleet feasibility.* Map Bin Packing (sizes $s_i$, capacity $C$, $k$ bins) to customers $q_i = s_i$, $Q = C$, $K = k$, with arbitrary metric distances. The customers fit into $K$ vehicles iff the items fit into $k$ bins. So "can all customers be served with $<= K$ vehicles?" is (strongly) NP-complete. Even *finding a feasible solution* can be hard, which is why our Tabu Search allows overloaded intermediate solutions with an adaptive penalty.
- *Bosphorus metric.* With $d'(i,j) = e(i,j) + P [s(i) != s(j)]$: if $i,k$ are on the same side, $d'(i,k) = e(i,k) <= e(i,j)+e(j,k) <= d'(i,j) + d'(j,k)$. If they are on different sides, $j$ is on one of the two sides, so exactly one of the legs crosses and the right-hand side contains $P$. Then $d'(i,k) = e(i,k) + P <= e(i,j) + e(j,k) + P = d'(i,j) + d'(j,k)$.

= Seed calculation and team instance
Seed $=$ sum of the last four digits of all members' student IDs: *#inst.extra.seed_calculation* → seed #inst.extra.seed.
// TEAM: put your student IDs into team.json and run `python experiments/make_data.py` again; this line updates automatically.

The instance has $n = #inst.n$ customers in #inst.extra.clusters clusters plus 20 uniformly random customers. Capacity is $Q = #inst.Q$ and $K = ceil(sum q_i \/ Q) + 1 = #inst.K$. Distances are Euclidean plus $P = 150$ when an arc crosses $x = 500$.

#figure(image("../figures/medidrone_instance.png", width: 62%), caption: [Our MediDrone instance. The depot is at the centre $(500,500)$ and the Bosphorus line is at $x = 500$.])

= Tiny instances with exact optima
#table(columns: 5, [*Instance*], [*n*], [*K*], [*Optimum*], [*Optimal routes*],
  ..tiny.map(t => (t.instance, str(t.n), str(t.K), str(calc.round(t.opt, digits: 2)), t.routes.map(r => "(" + r.map(str).join(" ") + ")").join(" "))).flatten())
We compute the exact optima with a Held–Karp DP for every capacity-feasible subset ($O(2^n n^2)$), followed by a set-partition DP over subsets with at most $K$ routes ($O(K 3^n)$). For $n = 6$ the result matches a brute-force enumeration of all permutations and cuts (unit test).
