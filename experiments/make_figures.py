"""Build every table and figure of the report from the raw results.

    python experiments/make_figures.py

Inputs : results/runs.csv, results/runs/*.json, results/scaling.json,
         results/param_study.csv, results/bosphorus.json (if present)
Outputs: results/summary.csv, results/stats.csv, results/scaling_table.csv,
         figures/*.png
"""
from __future__ import annotations

import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from common import BENCHMARKS, FIGURES, MEDIDRONE, RESULTS, TINY, load

COL = {"GA": "#2563eb", "TS": "#dc2626", "CW": "#6b7280"}
ORDER = TINY + BENCHMARKS + [MEDIDRONE]
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def load_runs():
    df = pd.read_csv(RESULTS / "runs.csv")
    df["instance"] = pd.Categorical(df["instance"], ORDER, ordered=True)
    # Reference value for instances without a BKS (MediDrone): best cost found by any run.
    ref = df.groupby("instance", observed=True)["cost"].min()
    df["ref"] = [b if not pd.isna(b) else ref[i] for i, b in zip(df["instance"], df["bks"])]
    df["rel_pct"] = 100 * (df["cost"] - df["ref"]) / df["ref"]
    return df


def summary(df):
    rows = []
    for (inst, algo), g in df.groupby(["instance", "algo"], observed=True):
        bks = g["bks"].iloc[0]
        r = {"instance": inst, "n": int(g["n"].iloc[0]), "algo": algo, "runs": len(g),
             "best": g["cost"].min(), "mean": g["cost"].mean(), "std": g["cost"].std(ddof=1) if len(g) > 1 else 0.0,
             "bks": bks if not pd.isna(bks) else "",
             "best_gap_pct": 100 * (g["cost"].min() - bks) / bks if not pd.isna(bks) else "",
             "mean_gap_pct": g["gap_pct"].mean() if not pd.isna(bks) else "",
             "mean_runtime_s": g["runtime_s"].mean(), "mean_time_to_best_s": g["time_to_best_s"].mean(),
             "mean_iterations": g["iterations"].mean(), "all_feasible": bool(g["feasible"].all()),
             "hits_optimum": int((abs(g["cost"] - bks) < 1e-6 * bks).sum()) if not pd.isna(bks) else "",
             "routes_best": int(g.loc[g["cost"].idxmin(), "routes"]), "K": int(g["K"].iloc[0])}
        rows.append(r)
    s = pd.DataFrame(rows)
    s.to_csv(RESULTS / "summary.csv", index=False, float_format="%.2f")
    return s


def statistics(df):
    rows, pairs = [], []
    for inst in BENCHMARKS + [MEDIDRONE]:
        ga = df[(df.instance == inst) & (df.algo == "GA")].sort_values("seed")
        ts = df[(df.instance == inst) & (df.algo == "TS")].sort_values("seed")
        if len(ga) < 2 or len(ts) < 2:
            continue
        if np.allclose(ga.cost.values, ts.cost.values[0]) and np.allclose(ts.cost.values, ts.cost.values[0]):
            p = 1.0
        else:
            p = stats.mannwhitneyu(ga.cost, ts.cost, alternative="two-sided").pvalue
        rows.append({"instance": inst, "test": "Mann-Whitney U (Wilcoxon rank-sum)", "GA_median": ga.cost.median(),
                     "TS_median": ts.cost.median(), "p_value": p})
        pairs += list(zip(ga.rel_pct.values, ts.rel_pct.values))
    if pairs:
        a, b = np.array(pairs).T
        diff = a - b
        p = stats.wilcoxon(a, b).pvalue if np.any(diff != 0) else 1.0
        rows.append({"instance": "all (paired by instance, seed)", "test": "Wilcoxon signed-rank",
                     "GA_median": float(np.median(a)), "TS_median": float(np.median(b)), "p_value": p,
                     "n_pairs": len(a), "TS_better": int((diff > 0).sum()), "GA_better": int((diff < 0).sum()),
                     "ties": int((diff == 0).sum())})
    s = pd.DataFrame(rows)
    s.to_csv(RESULTS / "stats.csv", index=False)
    return s


def run_json(name, algo, seed):
    tag = f"{name}_{algo}_{seed if algo != 'CW' else 'det'}"
    return json.loads((RESULTS / "runs" / f"{tag}.json").read_text())


def convergence(df, name):
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    bks = df[df.instance == name]["ref"].iloc[0]
    for algo in ("GA", "TS"):
        seeds = df[(df.instance == name) & (df.algo == algo)]["seed"].astype(int).tolist()
        T = float(df[(df.instance == name) & (df.algo == algo)]["budget_s"].iloc[0])
        grid = np.linspace(0, T, 400)
        curves = []
        for s in seeds:
            h = run_json(name, algo, s)["history"]
            t = np.array([x[0] for x in h]); c = np.array([x[1] for x in h])
            idx = np.searchsorted(t, grid, side="right") - 1
            cur = np.where(idx >= 0, c[np.clip(idx, 0, None)], np.nan)
            curves.append(100 * (cur - bks) / bks)
            ax.step(grid, curves[-1], where="post", color=COL[algo], alpha=0.15, lw=0.8)
        ax.step(grid, np.nanmedian(np.array(curves), axis=0), where="post", color=COL[algo], lw=2,
                label=f"{algo} (median of {len(seeds)} runs)")
    ax.set_xlabel("time (s)"); ax.set_ylabel("gap to BKS (%)" if name != MEDIDRONE else "gap to best found (%)")
    ax.set_yscale("symlog", linthresh=1.0)
    ax.set_title(f"Convergence on {name}")
    ax.legend()
    fig.tight_layout(); fig.savefig(FIGURES / f"convergence_{name}.png", dpi=200); plt.close(fig)


def draw_routes(ax, inst, routes, title):
    xy = inst.coords
    if inst.side is not None:
        ax.axvline(500, color="#3b82f6", lw=2.5, alpha=0.35)
    cmap = plt.get_cmap("tab20")
    for k, r in enumerate(routes):
        p = [0] + r + [0]
        ax.plot(xy[p, 0], xy[p, 1], "-", color=cmap(k % 20), lw=1.3)
    ax.scatter(xy[1:, 0], xy[1:, 1], s=10, c="k", zorder=3)
    ax.scatter([xy[0, 0]], [xy[0, 1]], marker="s", s=70, c="red", edgecolor="k", zorder=4)
    ax.set_aspect("equal"); ax.set_title(title, fontsize=9); ax.set_xticks([]); ax.set_yticks([])


def route_figures(df):
    inst = load(MEDIDRONE)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.3))
    for ax, algo in zip(axes, ("CW", "GA", "TS")):
        g = df[(df.instance == MEDIDRONE) & (df.algo == algo)]
        best = g.loc[g.cost.idxmin()]
        js = run_json(MEDIDRONE, algo, int(best.seed) if algo != "CW" else None)
        draw_routes(ax, inst, js["routes"], f"{algo}: cost {best.cost:.1f}, {int(best.routes)} routes,\n"
                                            f"{int(best.cross_routes)} routes / {int(best.cross_arcs)} arcs cross the Bosphorus")
    fig.tight_layout(); fig.savefig(FIGURES / "routes_medidrone.png", dpi=200); plt.close(fig)
    # best overall MediDrone solution, large
    g = df[(df.instance == MEDIDRONE) & (df.algo != "CW")]
    best = g.loc[g.cost.idxmin()]
    js = run_json(MEDIDRONE, best.algo, int(best.seed))
    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    draw_routes(ax, inst, js["routes"], f"Best MediDrone plan ({best.algo}, seed {int(best.seed)}): cost {best.cost:.1f}, "
                                        f"{int(best.routes)} routes, {int(best.cross_routes)} cross the strait")
    fig.tight_layout(); fig.savefig(FIGURES / "routes_medidrone_best.png", dpi=200); plt.close(fig)
    # a benchmark too
    for name in ("A-n80-k10",):
        binst = load(name)
        g = df[(df.instance == name) & (df.algo != "CW")]
        best = g.loc[g.cost.idxmin()]
        js = run_json(name, best.algo, int(best.seed))
        fig, ax = plt.subplots(figsize=(5, 5))
        draw_routes(ax, binst, js["routes"],
                    f"{name}: best {best.algo} solution, cost {best.cost:.0f} (BKS {binst.bks:.0f})")
        fig.tight_layout(); fig.savefig(FIGURES / f"routes_{name}.png", dpi=200); plt.close(fig)


def gap_boxplot(df):
    names = BENCHMARKS + [MEDIDRONE]
    fig, ax = plt.subplots(figsize=(7, 3.4))
    pos = np.arange(len(names))
    for off, algo in ((-0.18, "GA"), (0.18, "TS")):
        data = [df[(df.instance == n) & (df.algo == algo)]["rel_pct"].values for n in names]
        b = ax.boxplot(data, positions=pos + off, widths=0.32, patch_artist=True, showfliers=True)
        for patch in b["boxes"]:
            patch.set_facecolor(COL[algo]); patch.set_alpha(0.45)
        ax.plot([], [], color=COL[algo], lw=6, alpha=0.45, label=algo)
    cw = [df[(df.instance == n) & (df.algo == "CW")]["rel_pct"].values[0] for n in names]
    ax.scatter(pos, cw, marker="x", color=COL["CW"], label="Clarke–Wright", zorder=3)
    ax.set_xticks(pos, names)
    ax.set_ylabel("gap (%)  [MediDrone: to best found]")
    ax.set_yscale("symlog", linthresh=1.0)
    ax.legend(ncol=3, fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "gaps_boxplot.png", dpi=200); plt.close(fig)


def scaling_figure():
    p = RESULTS / "scaling.json"
    if not p.exists():
        return
    sc = json.loads(p.read_text())
    rows = sc["rows"]
    ns = np.array([r["n"] for r in rows])
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    labels = {"ga_gen_s": "GA: one generation", "ts_iter_s": "TS: one iteration", "split_s": "Split (one decoding)",
              "cw_s": "Clarke–Wright (total)"}
    marks = {"ga_gen_s": "o", "ts_iter_s": "s", "split_s": "^", "cw_s": "D"}
    table = []
    for k, lab in labels.items():
        t = np.array([r[k] for r in rows])
        s, c = sc["fits"][k]
        ax.loglog(ns, t, marks[k] + "-", label=f"{lab}  (slope {s:.2f})")
        table.append({"quantity": lab, "slope": round(s, 2), **{f"n={n}": f"{v*1e3:.3f} ms" for n, v in zip(ns, t)}})
    ax.set_xlabel("n (customers)"); ax.set_ylabel("time (s)")
    ax.legend(fontsize=8); ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout(); fig.savefig(FIGURES / "scaling_loglog.png", dpi=200); plt.close(fig)
    pd.DataFrame(table).to_csv(RESULTS / "scaling_table.csv", index=False)


def param_figures():
    p = RESULTS / "param_study.csv"
    if not p.exists():
        return
    ps = pd.read_csv(p)
    studies = list(ps["study"].unique())
    fig, axes = plt.subplots(1, len(studies), figsize=(4.2 * len(studies), 3.4))
    axes = np.atleast_1d(axes)
    for ax, st in zip(axes, studies):
        g = ps[ps.study == st]
        agg = g.groupby("value")["gap_pct"].agg(["mean", "std", "min"]).reset_index()
        ax.errorbar(agg["value"], agg["mean"], yerr=agg["std"], fmt="o-", capsize=3, label="mean ± sd gap")
        ax.plot(agg["value"], agg["min"], "v--", alpha=0.7, label="best gap")
        ax.set_xlabel(g["param"].iloc[0]); ax.set_ylabel("gap to BKS (%)")
        ax.set_title(f"{st} on {g['instance'].iloc[0]}")
        if "diversity" in g and g["diversity"].notna().any():
            ax2 = ax.twinx()
            dv = g.groupby("value")["diversity"].mean()
            ax2.plot(dv.index, dv.values, "s:", color="#16a34a", label="final diversity")
            ax2.set_ylabel("population diversity", color="#16a34a")
        if g["value"].min() > 0 and g["value"].max() / g["value"].min() > 20:
            ax.set_xscale("log")
        ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout(); fig.savefig(FIGURES / "param_study.png", dpi=200); plt.close(fig)


def bosphorus_figure():
    p = RESULTS / "bosphorus.json"
    if not p.exists():
        return
    b = json.loads(p.read_text())
    from cvrp.generator import load_instance, make_instance
    base = load(MEDIDRONE)
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.6))
    for ax, key in zip(axes, ("P0", "P150")):
        e = b[key]
        inst = make_instance("x", base.coords, base.demand, base.Q, base.K, penalty=e["penalty"])
        draw_routes(ax, inst, e["routes"], f"P = {e['penalty']:.0f}: {e['routes_n']} routes, "
                    f"{e['cross_routes']} routes / {e['cross_arcs']} arcs cross\n"
                    f"Euclidean length {e['euclid']:.0f}")
    fig.tight_layout(); fig.savefig(FIGURES / "bosphorus_effect.png", dpi=200); plt.close(fig)


def main():
    df = load_runs()
    s = summary(df)
    st = statistics(df)
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(s[["instance", "algo", "best", "mean", "std", "best_gap_pct", "mean_gap_pct", "hits_optimum",
                 "mean_iterations", "all_feasible"]].to_string(index=False))
        print(st.to_string(index=False))
    for name in ("A-n45-k6", "A-n60-k9", "A-n80-k10", MEDIDRONE):
        convergence(df, name)
    route_figures(df)
    gap_boxplot(df)
    scaling_figure()
    param_figures()
    bosphorus_figure()
    print("figures written to", FIGURES)


if __name__ == "__main__":
    main()
