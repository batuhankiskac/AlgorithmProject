= Contribution table

// TEAM: replace names and percentages with the real split before submitting.
#table(columns: (auto, 1fr, auto), align: (left, left, center),
  [*Member*], [*Main responsibilities*], [*Share*],
  [Member 1], [Core library: CVRPLIB parser, MediDrone generator, evaluation, independent feasibility checker, exact DP for tiny instances], [25%],
  [Member 2], [Genetic Algorithm: Split DP, operators, memetic local search; GA sections of the report], [25%],
  [Member 3], [Clarke–Wright and Tabu Search: moves, delta evaluation, penalty adaptation; TS sections of the report], [25%],
  [Member 4], [Theory chapter (reductions, Bin Packing, metric proof); experiment scripts, statistics, figures; slides], [25%],
)

= Reproducing every table and figure

All commands are run from the repository root after `pip install -e .`; see `README.md` for details.
#table(columns: (auto, 1fr), align: left,
  [*Command*], [*Produces*],
  [`python experiments/make_data.py`], [MediDrone instance (seed from `team.json`), tiny instances, exact optima, Fig. of the instance],
  [`python experiments/run_experiments.py`], [`results/runs.csv` and one JSON per run (routes and convergence history)],
  [`python experiments/scaling.py`], [`results/scaling.json` (Task 6 timings, delta vs. full evaluation)],
  [`python experiments/param_study.py`], [`results/param_study.csv` (parameter sensitivity)],
  [`python experiments/bosphorus.py`], [`results/bosphorus.json` (P = 0 vs. P = 150)],
  [`python experiments/make_figures.py`], [`results/summary.csv`, `results/stats.csv`, all figures],
  [`python report/build.py`], [this report as PDF],
  [`pytest`], [unit tests (parser, checker, exact DP, Split, GA, CW, TS, delta formulas)],
)

= Sources, own work and tools

All algorithms (parser, generator, Clarke–Wright, Split, GA, Tabu Search, exact DP, checker) are our own implementations. We used no routing or metaheuristic library. Published pseudocode served as a starting point: Clarke–Wright @clarke1964, giant tour + Split and the GA design @prins2004, and Tabu Search concepts @glover1997. Source comments mark where an implementation follows one of these. Benchmark instances and best-known solutions come from CVRPLIB @cvrplib. Standard libraries only were used for numerics (NumPy), plotting (Matplotlib), statistics (SciPy) and typesetting (Typst).
// TEAM: state here, in your own words, any use of AI assistants (e.g. for code review, drafting or debugging), as required by the course rules on citing external help.
