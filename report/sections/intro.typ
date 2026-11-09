= Introduction

MediDrone Istanbul flies blood samples, vaccines and urgent medication from one central laboratory to clinics on both sides of the city. Every morning the operations team has to answer the same question: which drone visits which clinics, and in which order? Each clinic orders a different amount, a drone can carry at most $Q$ units, every drone must come back to the lab, and crossing the Bosphorus costs extra because of the air-traffic corridor, wind and battery use. The CTO wants a good plan within seconds, not a proof of optimality, but also hard evidence that the method works and scales.

Stripped of the story, this is the *Capacitated Vehicle Routing Problem* (CVRP) @toth2014. It contains the Travelling Salesperson Problem (TSP) as the special case of one vehicle with unlimited capacity, and it contains Bin Packing as the question of whether the customers fit into $K$ vehicles at all. Both are NP-hard, so we do not expect an exact polynomial-time algorithm. In Section 2 we make this precise with a chain of reductions, Hamiltonian Cycle $<=_p$ TSP $<=_p$ CVRP. We also show that the feasibility question alone is NP-complete and that the Bosphorus penalty keeps the distance a metric.

Our answer to the CTO is a toolbox of three algorithms, all implemented from scratch in Python (Section 3):

- *Clarke–Wright savings* @clarke1964: a fast, deterministic constructive baseline, also used to start the other two methods.
- A *Genetic Algorithm* (GA) in the style of Prins @prins2004. Chromosomes are "giant tours" without route delimiters. An exact dynamic program (*Split*) cuts each one optimally into capacity-feasible routes.
- *Tabu Search* (TS) @glover1997 works directly on routes. It uses four move types with $O(1)$ delta evaluation, a granular candidate list and an adaptive penalty for capacity violations.

Because this is an algorithms course, we do not stop at measuring. In Section 4 we derive the asymptotic cost of one GA generation and one TS iteration and check the predicted exponents on a log–log plot. Section 5 compares the methods under a fair protocol: equal wall-clock budgets, ten recorded seeds and gaps to the best-known solutions of the Augerat benchmarks @augerat1995 @cvrplib. We also use tiny instances whose exact optimum we compute ourselves, and a team-specific MediDrone instance. Section 6 discusses what the data says, how the Bosphorus penalty shapes the routes, and the gap between proven approximation guarantees and what works in practice.
