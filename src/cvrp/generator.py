"""MediDrone Istanbul instance generator (Task 2b) and tiny instances (Task 2c).

Rules from the assignment:
  * depot at the centre of a 1000 x 1000 square
  * European side x < 500, Asian side x >= 500
  * n = 100 customers in 4-6 clusters spread over both sides + ~20% uniform
  * demands uniform integers in [1, 30], Q = 100, K = ceil(sum q / Q) + 1
  * d(i, j) = Euclidean(i, j) + P if i, j on different sides, P = 150
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .instance import Instance, euc2d_matrix

SIZE = 1000.0
BORDER = 500.0
PENALTY = 150.0
ROOT = Path(__file__).resolve().parents[2]


def team_seed(team_file: str | Path = ROOT / "team.json") -> tuple[int, str]:
    """Seed = sum of the last four digits of every member's student ID,
    read as a 4-digit number each (e.g. ...1234 contributes 1234)."""
    cfg = json.loads(Path(team_file).read_text())
    ids = [str(s) for s in cfg.get("student_ids", []) if str(s).strip()]
    if not ids:
        return int(cfg.get("fallback_seed", 2026)), "fallback (no student IDs in team.json)"
    parts = [int(s[-4:]) for s in ids]
    return sum(parts), " + ".join(f"{p:04d}" for p in parts) + f" = {sum(parts)}"


def side_of(coords: np.ndarray) -> np.ndarray:
    return (coords[:, 0] >= BORDER).astype(np.int64)


def bosphorus_matrix(coords: np.ndarray, penalty: float = PENALTY) -> tuple[np.ndarray, np.ndarray]:
    side = side_of(coords)
    D = euc2d_matrix(coords, rounded=False)
    D = D + penalty * (side[:, None] != side[None, :])
    return D, side


def make_instance(name: str, coords: np.ndarray, demand: np.ndarray, Q: int, K: int,
                  penalty: float = PENALTY) -> Instance:
    D, side = bosphorus_matrix(coords, penalty)
    return Instance(name=name, n=len(coords) - 1, Q=Q, K=K, demand=demand,
                    D=D, coords=coords, side=side)


def generate_medidrone(seed: int, n: int = 100, Q: int = 100,
                       random_frac: float = 0.2, name: str | None = None) -> Instance:
    rng = np.random.default_rng(seed)
    n_rand = int(round(random_frac * n))
    n_clu = n - n_rand
    m = int(rng.integers(4, 7))                     # 4..6 clusters
    # Cluster centres: alternate sides so both sides are guaranteed to be used.
    centres = []
    for c in range(m):
        if c % 2 == 0:
            x = rng.uniform(100, 430)
        else:
            x = rng.uniform(570, 900)
        centres.append((x, rng.uniform(100, 900)))
    centres = np.array(centres)
    sigma = rng.uniform(40, 80, size=m)
    assign = rng.integers(0, m, size=n_clu)
    pts = centres[assign] + rng.normal(0, 1, size=(n_clu, 2)) * sigma[assign, None]
    pts = np.clip(pts, 0, SIZE)
    uni = rng.uniform(0, SIZE, size=(n_rand, 2))
    cust = np.vstack([pts, uni])
    cust = cust[rng.permutation(n)]
    coords = np.vstack([[SIZE / 2, SIZE / 2], cust])
    demand = np.concatenate([[0], rng.integers(1, 31, size=n)]).astype(np.int64)
    K = math.ceil(demand.sum() / Q) + 1
    inst = make_instance(name or f"MediDrone-n{n}-s{seed}", coords, demand, Q, K)
    inst.extra = {"seed": seed, "clusters": m, "centres": centres.tolist()}
    return inst


def generate_tiny(n: int, seed: int, Q: int = 60) -> Instance:
    """Tiny MediDrone-style instance (with Bosphorus penalty) for exact ground truth.
    Q = 60 with demands in [1, 30] forces several routes (about 4 customers each)."""
    rng = np.random.default_rng(seed)
    coords = np.vstack([[SIZE / 2, SIZE / 2], rng.uniform(0, SIZE, size=(n, 2))])
    demand = np.concatenate([[0], rng.integers(1, 31, size=n)]).astype(np.int64)
    K = math.ceil(demand.sum() / Q) + 1
    return make_instance(f"tiny-n{n}", coords, demand, Q, K)


def save_instance(inst: Instance, path: str | Path) -> None:
    """Write an instance as JSON (coordinates, demands, Q, K, penalty)."""
    data = {"name": inst.name, "n": inst.n, "Q": inst.Q, "K": inst.K,
            "penalty": PENALTY, "coords": inst.coords.tolist(),
            "demand": inst.demand.tolist(), "bks": inst.bks,
            "extra": getattr(inst, "extra", {})}
    Path(path).write_text(json.dumps(data, indent=1))


def load_instance(path: str | Path) -> Instance:
    data = json.loads(Path(path).read_text())
    inst = make_instance(data["name"], np.array(data["coords"]), np.array(data["demand"], dtype=np.int64),
                         data["Q"], data["K"], data.get("penalty", PENALTY))
    inst.bks = data.get("bks")
    inst.extra = data.get("extra", {})
    return inst
