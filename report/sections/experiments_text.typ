#let ST = csv("../../results/stats.csv", row-type: dictionary)
#let r2(x) = if x == "" { "–" } else { str(calc.round(float(x), digits: 2)) }
*Observations.* Both metaheuristics are far ahead of the constructive baseline, which is 4–7% above the BKS. The memetic GA ends at the BKS in 38 of its 40 benchmark runs; the other two are A-n80-k10 runs that end at 1764 and 1766. The Tabu Search also reaches the BKS on A-n32-k5, A-n45-k6 and A-n60-k9 in all runs. On A-n80-k10 it reaches the BKS once in 10 runs (mean gap 0.25%). On the tiny instances both methods find the DP optimum in 10/10 runs (@tab:tiny), so neither is missing optimal solutions because of a bug in the search space or the decoder. Clarke–Wright happens to be optimal on tiny-n8.

On our MediDrone instance, all 10 GA runs converge to the *same* plan (cost 14 708.17, standard deviation 0). TS runs end between 14 722 and 14 762, at most 0.4% above it, and Clarke–Wright is 6.4% above. Ten independent runs agreeing to the last decimal, combined with the GA's record on the benchmarks, suggests that this plan is optimal or very close to it. We cannot prove this, because the instance is far too large for our exact DP.

== Convergence

#figure(image("../../figures/convergence_A-n80-k10.png", width: 82%), caption: [Best cost vs. time on A-n80-k10 (thin lines: individual runs; thick: median of 10). The symlog axis is linear below 1%.]) <fig:conv>

@fig:conv shows a typical picture. The first 3 s look alike, because both methods start from Clarke–Wright (4.4%) and both quickly remove its obvious defects. After that the GA's median drops below 0.5% within 6 s and reaches the BKS after about 26 s. TS keeps improving in small steps and its median ends at 0.17%. TS performs about 60 times more iterations than the GA performs generations, but each iteration is a single move, whereas a GA generation runs 25 complete decodings and about 12 local searches. Convergence plots for the other instances are in `figures/`.

== Statistical comparison (bonus)

#figure(
  table(columns: 5, align: (left, left, right, right, right),
    [*Instance*], [*Test*], [*GA median*], [*TS median*], [*p-value*],
    ..ST.map(r => (r.instance, r.test, r2(r.GA_median), r2(r.TS_median),
      if float(r.p_value) < 0.001 { str(calc.round(float(r.p_value), digits: 6)) } else { str(calc.round(float(r.p_value), digits: 4)) })).flatten()),
  caption: [Two-sided Mann–Whitney U test per instance (10 vs. 10 runs) and Wilcoxon signed-rank test @wilcoxon1945 on the relative gaps of all benchmark and MediDrone runs, paired by (instance, seed). For the paired test the "median" columns show the median gap in %.]
) <tab:stats>

On the three smaller benchmarks the two methods are statistically indistinguishable, because both always find the BKS ($p = 1$). On A-n80-k10 ($p approx 0.002$) and on MediDrone ($p < 10^(-4)$) the GA is significantly better. Across all 50 paired runs the GA wins 18, TS wins 1 and 31 are ties. The signed-rank test rejects equality ($p approx 2.5 dot 10^(-4)$).

== The MediDrone plans and the Bosphorus

#figure(image("../../figures/routes_medidrone.png", width: 100%), caption: [Best plans on our MediDrone instance (depot = red square, Bosphorus = blue line).]) <fig:routes>

#figure(image("../../figures/bosphorus_effect.png", width: 88%), caption: [Best of three TS runs (60 s each) on the same customers with $P = 0$ and with $P = 150$.]) <fig:bos>
