# AlgorithmProject

CMP 3005 – Analysis of Algorithms, Fall 2026–27 term project.

**Drones, Deadlines and NP-Hardness: Metaheuristics for a Capacitated Medical Delivery Network**

We solve the Capacitated Vehicle Routing Problem (CVRP) with:

- **Clarke–Wright savings**, a deterministic constructive baseline
- **Genetic Algorithm** using a giant-tour representation and Split dynamic programming (Prins, 2004)
- **Tabu Search** with relocate, swap, 2-opt and 2-opt* moves and O(1) delta evaluation

We evaluate on CVRPLIB Augerat Set A (A-n32-k5, A-n45-k6, A-n60-k9, A-n80-k10), on our team-specific MediDrone Istanbul instance (n = 100, with a Bosphorus-crossing penalty), and on tiny instances with exact optima.

## Repository layout

```
src/cvrp/       core library: parsing, generation, evaluation, checker, algorithms
experiments/    scripts that produce every table and figure
tests/          unit tests (pytest)
data/cvrplib/   benchmark instances (.vrp) and BKS values
data/medidrone/ our generated team instance
data/tiny/      n = 7, 8, 9 instances and their exact optima
results/        raw CSV results of all runs
figures/        generated plots
report/         final report sources
slides/         presentation
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Reproducing results

We will add exact commands here for every table and figure as the experiment scripts are written.

## Rules we follow

- No VRP or metaheuristic solver libraries (OR-Tools routing, VROOM, HGS-CVRP, PyVRP, jMetal). Every algorithm is our own implementation.
- An ILP solver is used only to get ground truth on the tiny instances.
- Distances on CVRPLIB instances are rounded to the nearest integer, as CVRPLIB does.
- An independent feasibility checker validates every reported solution.
- External sources are cited in the report, and adapted code is marked in comments.

See [ROADMAP.md](ROADMAP.md) for the plan and the division of work.
