"""Generate the team MediDrone instance, the tiny instances and their exact optima.

    python experiments/make_data.py
"""
from __future__ import annotations

import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import DATA, FIGURES, save_json
from cvrp.checker import check
from cvrp.exact import solve_exact
from cvrp.generator import generate_medidrone, generate_tiny, save_instance, team_seed

TINY_SEEDS = {7: 7, 8: 8, 9: 9}


def plot_instance(inst, path, title):
    fig, ax = plt.subplots(figsize=(6.2, 6.2))
    ax.axvline(500, color="#3b82f6", lw=2, alpha=0.6, label="Bosphorus (x = 500)")
    ax.axvspan(0, 500, color="#fde68a", alpha=0.15)
    ax.axvspan(500, 1000, color="#bbf7d0", alpha=0.15)
    xy = inst.coords
    sc = ax.scatter(xy[1:, 0], xy[1:, 1], c=inst.demand[1:], cmap="viridis", s=14 + 1.5 * inst.demand[1:],
                    edgecolor="k", lw=0.3, zorder=3)
    ax.scatter([xy[0, 0]], [xy[0, 1]], marker="s", s=120, c="red", edgecolor="k", zorder=4, label="Depot (lab)")
    ax.text(250, 1015, "European side", ha="center", fontsize=9)
    ax.text(750, 1015, "Asian side", ha="center", fontsize=9)
    fig.colorbar(sc, ax=ax, shrink=0.75, label="demand $q_i$")
    ax.set_xlim(0, 1000); ax.set_ylim(0, 1040); ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    FIGURES.mkdir(exist_ok=True)
    seed, calc = team_seed()
    inst = generate_medidrone(seed, name="MediDrone")
    inst.extra["seed_calculation"] = calc
    save_instance(inst, DATA / "medidrone" / "medidrone.json")
    print(f"MediDrone seed: {calc}; n={inst.n}, K={inst.K}, total demand={inst.total_demand}, "
          f"clusters={inst.extra['clusters']}, Asian side customers={int(inst.side[1:].sum())}")
    plot_instance(inst, FIGURES / "medidrone_instance.png",
                  f"MediDrone instance (seed {seed}): n={inst.n}, Q={inst.Q}, K={inst.K}")

    summary = []
    for n, s in TINY_SEEDS.items():
        t = generate_tiny(n, s)
        t0 = time.perf_counter()
        opt, routes = solve_exact(t)
        el = time.perf_counter() - t0
        ok, problems, rc = check(t, routes, opt)
        assert ok, problems
        t.bks = opt
        t.extra = {"seed": s, "optimal_routes": routes, "exact_time_s": el, "method": "Held-Karp + set partition DP"}
        save_instance(t, DATA / "tiny" / f"tiny-n{n}.json")
        summary.append({"instance": t.name, "n": n, "K": t.K, "opt": opt, "routes": routes, "time_s": el})
        print(f"{t.name}: optimum {opt:.2f} with {len(routes)} routes in {el:.3f}s -> {routes}")
    save_json(summary, DATA / "tiny" / "optima.json")


if __name__ == "__main__":
    main()
