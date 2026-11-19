#let hw = json("../../results/hardware.json")
#let S = csv("../../results/summary.csv", row-type: dictionary)
#let ST = csv("../../results/stats.csv", row-type: dictionary)
#let r2(x) = if x == "" { "–" } else { str(calc.round(float(x), digits: 2)) }
#let r1(x) = if x == "" { "–" } else { str(calc.round(float(x), digits: 1)) }
#let get(inst, algo) = S.find(r => r.instance == inst and r.algo == algo)
#let main-insts = ("A-n32-k5", "A-n45-k6", "A-n60-k9", "A-n80-k10", "MediDrone")
#let tiny-insts = ("tiny-n7", "tiny-n8", "tiny-n9")
#let md = json("../../data/medidrone/medidrone.json")

= Experiments <sec:experiments>

== Set-up

*Instances.* We use the CVRPLIB Augerat Set A instances A-n32-k5, A-n45-k6, A-n60-k9 and A-n80-k10 with their published best-known solutions, parsed by our own TSPLIB reader with `nint` distances. Our team instance follows the MediDrone rules: the depot is at $(500, 500)$ of a $1000 times 1000$ square, and the Bosphorus is the line $x = 500$. It has $n = #md.n$ customers, #md.extra.clusters Gaussian clusters spread over both sides plus 20% uniform customers, demands drawn uniformly from $[1, 30]$, $Q = #md.Q$ and $K = ceil(sum q_i \/ Q) + 1 = ceil(#md.demand.sum() \/ #md.Q) + 1 = #md.K$. Distances are Euclidean, plus $P = 150$ on every arc that crosses the strait. *Seed calculation:* the seed is the sum of the last four digits of the members' student IDs, #md.extra.seed_calculation, so our seed is #md.extra.seed. Finally, three tiny instances with $n = 7, 8, 9$ get exact optima from our DP (@tab:tiny).

*Hardware and software.* #hw.cpu (#hw.cores cores, of which #hw.perf_cores are performance cores) with #hw.memory_gb GB RAM, Python #hw.python with NumPy. All solvers are pure Python. Runs were executed #hw.workers at a time, each in its own process. The machine was also used for other work during the experiments, so absolute iteration counts are lower than on an idle machine. GA and TS ran interleaved under the same conditions, so the comparison stays fair.

*Protocol.* Each stochastic algorithm ran 10 times per instance with the recorded seeds 11, 23, 37, 41, 53, 67, 79, 83, 97, 101. GA and TS received *the same wall-clock budget*: 2 s for the tiny instances, 30 s for $n <= 50$ and 60 s for larger $n$. Both start from the Clarke–Wright solution, the GA as one individual of its initial population. We report the gap to the best-known solution (BKS) from CVRPLIB, $"Gap" = 100 dot ("Cost" - "BKS")\/"BKS"$. For our MediDrone instance no BKS exists, so gaps there are relative to the best cost found by any run. Every solution passed the independent checker; the only exception is noted in @tab:main. All parameters are listed in @sec:methods. Raw results for every run are in `results/runs.csv`.

== Results on the benchmarks and the team instance

#figure(
  text(8.5pt, table(columns: 11, align: (left, left, right, right, right, right, right, right, right, right, right),
    [*Instance*], [*Alg.*], [*Best*], [*Mean*], [*Std*], [*BKS*], [*Best gap %*], [*Mean gap %*], [*Runtime (s)*], [*Time to best (s)*], [*Iter.*],
    ..main-insts.map(i => ("CW", "GA", "TS").map(a => {
      let r = get(i, a)
      if r == none { () } else {
        (if a == "CW" { text(weight: "bold", i) } else { [] }, a, r2(r.best), r2(r.mean), r2(r.std), r1(r.bks),
         r2(r.best_gap_pct), r2(r.mean_gap_pct),
         if a == "CW" { "< 0.01" } else { r1(r.mean_runtime_s) },
         if a == "CW" { "–" } else { r1(r.mean_time_to_best_s) },
         if a == "CW" { "–" } else { str(int(float(r.mean_iterations))) })
      }
    }).flatten()).flatten())),
  caption: [Results over 10 runs, with a 30 s budget for $n <= 50$ and 60 s otherwise. "Std" is the sample standard deviation. "Runtime" is the mean wall-clock time per run (GA and TS always use their full budget); "Time to best" is when the final best solution was found. "Iter." is the mean number of GA generations or TS iterations. On A-n45-k6, Clarke–Wright uses 7 routes for $K = 6$, so it is not a feasible CVRP solution; its cost is listed for reference only.]
) <tab:main>

#figure(
  table(columns: 6, align: (left, right, right, right, right, right),
    [*Instance*], [*Optimum (DP)*], [*CW cost*], [*CW gap %*], [*GA hits optimum*], [*TS hits optimum*],
    ..tiny-insts.map(i => {
      let c = get(i, "CW"); let g = get(i, "GA"); let t = get(i, "TS")
      (i, r2(c.bks), r2(c.best), r2(c.best_gap_pct), g.hits_optimum + " / " + g.runs, t.hits_optimum + " / " + t.runs)
    }).flatten()),
  caption: [Tiny instances with exact optima (Held–Karp + set-partition DP), 2 s per run.]
) <tab:tiny>

#include "experiments_text.typ"
