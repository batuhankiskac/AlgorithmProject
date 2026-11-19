= Contribution table

The last four digits of each member's student ID are shown in brackets; they define our MediDrone seed. The work was organised in four workstreams with separate file ownership. The split below follows that plan; the oral defense covers every part for every member.
#table(columns: (auto, 1fr, auto), align: (left, left, center),
  [*Member*], [*Main responsibilities*], [*Share*],
  [Batuhan Kıskaç (···6936)], [Workstream A, core library: CVRPLIB parser, MediDrone generator, evaluation, independent feasibility checker, exact DP for tiny instances], [25%],
  [Dilara Uyar (···2546)], [Workstream B, Genetic Algorithm: Split DP, operators, memetic local search; GA sections of the report], [25%],
  [Demir Demirbilek (···6698)], [Workstream C, Clarke–Wright and Tabu Search: moves, delta evaluation, penalty adaptation; TS sections of the report], [25%],
  [Demirkan Çevik (···4959)], [Workstream D, theory chapter (reductions, Bin Packing, metric proof); experiment scripts, statistics, figures; slides], [25%],
)

= AI-tool usage statement

*Tools.* We used two AI tools: _Claude Code_ (Anthropic, Claude Opus models) as a programming and writing assistant throughout the project, and _omp_ (the oh-my-pi coding agent with a DeepSeek model) once, to audit the finished project against the assignment.

*What the AI did and did not do.* The algorithmic design is ours. We chose the giant-tour representation with an exact Split decoder, soft capacity with an adaptive penalty in both metaheuristics, the move set and arc-based tabu attributes of the Tabu Search, the granular candidate lists and the experimental protocol. The AI assisted us in these decisions by explaining concepts and the relevant literature and by discussing alternatives with us. With the instructor's permission, we also used it for help with writing code: it helped implement and refactor our designs, write unit tests and experiment scripts, and find bugs. Finally, it helped improve the English wording of the report. The personal reflection is written by us alone.

#table(columns: (auto, 1fr), align: left,
  [*Part*], [*How AI was used*],
  [Theory (Task 1)], [Explaining reductions; checking our proof sketches for gaps; wording],
  [Algorithm design (Tasks 3–5)], [Explaining Split, OX, tabu attributes and penalty schemes; discussing alternatives. Final design decisions are ours],
  [Implementation and tests], [Help writing and refactoring code, writing unit tests, debugging (e.g. the delta-formula edge cases)],
  [Experiments and figures], [Help writing the experiment, statistics and plotting scripts; all runs were executed by us],
  [Report and slides], [Improving language and structure; checking consistency between text and results],
)

*Example prompts* (translated from Turkish):
+ "What does the instructor ask for in this project? Can you prepare a detailed roadmap?"
+ "Here is the updated version of the assignment. According to it, is anything still missing in our project? List everything."

*Responsibility.* We did not take the AI's output on trust. We checked it against independent evidence: the parser against the published optimal solutions, every delta formula against full recomputation, the exact DP against brute force, and every reported solution with the independent feasibility checker. All experiments were run by us on our own machine, and the numbers in this report are read directly from those raw results. Every member can explain every part of the code and the report.

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

= Sources and own work

All algorithms (parser, generator, Clarke–Wright, Split, GA, Tabu Search, exact DP, checker) were implemented by us for this project, with the AI assistance described in Appendix B. We used no routing or metaheuristic library. Published pseudocode served as a starting point: Clarke–Wright @clarke1964, giant tour + Split and the GA design @prins2004, and Tabu Search concepts @glover1997. Source comments mark where an implementation follows one of these. Benchmark instances and best-known solutions come from CVRPLIB @cvrplib. Standard libraries only were used for numerics (NumPy), plotting (Matplotlib), statistics (SciPy) and typesetting (Typst).
