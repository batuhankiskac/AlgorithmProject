# AlgorithmProject

CMP 3005 – Analysis of Algorithms, Fall 2026–27 term project.

**Drones, Deadlines and NP-Hardness: Metaheuristics for a Capacitated Medical Delivery Network**

We solve the Capacitated Vehicle Routing Problem (CVRP) with three algorithms written from scratch in Python:

- **Clarke–Wright savings**: a deterministic constructive baseline, O(n² log n).
- **Memetic Genetic Algorithm**: giant-tour chromosomes with exact Split DP decoding (Prins 2004), soft capacity with an adaptive penalty, OX crossover, inversion mutation, (μ+λ) replacement with duplicate rejection, and granular local search.
- **Tabu Search**: relocate, swap, 2-opt and 2-opt* moves with O(1) delta evaluation, a granular candidate list, an arc-based tabu list with aspiration, an adaptive capacity penalty and ruin-and-recreate diversification.

Instances:

- the CVRPLIB Augerat Set A benchmarks A-n32-k5, A-n45-k6, A-n60-k9 and A-n80-k10;
- our team MediDrone Istanbul instance: n = 100 customers, Bosphorus-crossing penalty P = 150, seed 6936 + 2546 + 6698 + 4949 = 21129;
- three tiny instances whose exact optimum we compute with dynamic programming.

| Deliverable | File |
|---|---|
| Final report (PDF) | [`report/report.pdf`](report/report.pdf) |
| Milestone 1 | [`report/milestone1.pdf`](report/milestone1.pdf) |
| Slides | [`slides/slides.pdf`](slides/slides.pdf) |
| Raw results (every run) | [`results/runs.csv`](results/runs.csv), `results/runs/*.json` (routes and convergence history) |

## Setup

Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Reproducing every table and figure

Run these from the repository root, in this order. The times are for an Apple M-series laptop.

| Step | Command | Output | Time |
|---|---|---|---|
| 1 | `python experiments/make_data.py` | `data/medidrone/medidrone.json` (seed from `team.json`), `data/tiny/*.json` with exact optima, `figures/medidrone_instance.png` | 1 s |
| 2 | `python experiments/run_experiments.py` | `results/runs.csv` and `results/runs/*.json`: 10 seeds × {GA, TS} plus CW on all 8 instances. Resumable. `--quick` gives a 1-minute smoke test | ~25 min |
| 3 | `python experiments/param_study.py` | `results/param_study.csv`: TS tenure, GA mutation rate, memetic ablation | ~6 min |
| 4 | `python experiments/bosphorus.py` | `results/bosphorus.json`: routes with P = 0 vs. P = 150 | ~2 min |
| 5 | `python experiments/scaling.py` | `results/scaling.json`: Task 6 timings, log–log slopes, delta vs. full evaluation | ~5 min |
| 6 | `python experiments/make_figures.py` | `results/summary.csv`, `results/stats.csv`, `results/scaling_table.csv`, every figure in `figures/` | 10 s |
| 7 | `python report/build.py` | `report/report.pdf`, `report/milestone1.pdf`, `slides/slides.pdf` (Typst, installed by `requirements.txt`) | 5 s |

The report reads its tables directly from the CSV and JSON files in `results/`. After rerunning the experiments, rebuild it with step 7 and the numbers update automatically.

Tests (parser against the published optimal solutions, checker, exact DP vs. brute force, Split vs. brute force, every delta formula vs. full recomputation, solver feasibility):

```bash
pytest
```

## Code layout

```
src/cvrp/
  instance.py       CVRPLIB/TSPLIB parser (nint rounding), Instance class         [instance parsing]
  generator.py      MediDrone generator (team seed, clusters, Bosphorus metric)  [instance generation]
  solution.py       route/solution cost, Bosphorus crossings, Result type        [representation & evaluation]
  checker.py        independent feasibility checker (recomputes from coordinates) [validation]
  exact.py          exact DP (Held–Karp + set partition) for tiny instances      [ground truth]
  clarke_wright.py  Clarke–Wright savings (+ route-count repair)                 [baseline]
  split.py          Split DP: unlimited O(nL), fleet-limited O(KnL), soft capacity [GA decoder]
  ga.py             memetic GA                                                   [GA]
  moves.py          move definitions, O(1) delta formulas, delta-vs-full benchmark [TS]
  tabu.py           Tabu Search                                                   [TS]
experiments/        scripts for every table and figure (see above)
tests/              pytest suite
data/               benchmark .vrp/.sol files + BKS, team instance, tiny instances
results/            raw CSV/JSON results
figures/            generated plots
report/             Typst sources of the report and Milestone 1
slides/             Typst source of the presentation
docs/               design notes for the GA and the TS
```

## Team seed

`team.json` holds the last four digits of each member's student ID. The MediDrone seed is their sum, each read as a 4-digit number: 6936 + 2546 + 6698 + 4949 = **21129**.

## Rules we follow

- We use no VRP or metaheuristic solver libraries (OR-Tools routing, VROOM, HGS-CVRP, PyVRP, jMetal). Every algorithm is our own implementation. Where an implementation follows published pseudocode (Clarke & Wright 1964; Prins 2004; Vidal et al. 2012; Toth & Vigo 2003; Cordeau et al. 2001), the module docstring says so.
- The exact ground truth for the tiny instances comes from our own DP; no ILP solver is needed.
- CVRPLIB distances are rounded to the nearest integer, as CVRPLIB does. `tests/test_core.py` checks that the published optimal solutions evaluate exactly to the BKS.
- Benchmark files come from CVRPLIB (http://vrp.galgos.inf.puc-rio.br), downloaded through public mirrors (VROOM-Project/vroom-scripts, vidalt/CVRPLIB) because the CVRPLIB site was unreachable.
