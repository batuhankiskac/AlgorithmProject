"""CVRP instance representation and CVRPLIB/TSPLIB parsing (own implementation).

Conventions used everywhere in this project:
  * vertex 0 is the depot, customers are 1..n
  * ``D`` is the full (n+1)x(n+1) distance matrix as a numpy array
  * ``d`` is the same matrix as a list of lists (much faster for scalar
    access inside pure-Python inner loops)
  * ``demand[0] == 0``
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Instance:
    name: str
    n: int                      # number of customers
    Q: int                      # vehicle capacity
    K: int                      # fleet size (max number of routes)
    demand: np.ndarray          # shape (n+1,), demand[0] = 0
    D: np.ndarray               # shape (n+1, n+1)
    coords: np.ndarray          # shape (n+1, 2)
    side: np.ndarray | None = None   # 0 = European, 1 = Asian (MediDrone only)
    bks: float | None = None         # best-known solution value, if any
    extra: dict = field(default_factory=dict)
    d: list = field(init=False, repr=False)
    q: list = field(init=False, repr=False)

    def __post_init__(self):
        self.d = self.D.tolist()
        self.q = [int(x) for x in self.demand]

    @property
    def total_demand(self) -> int:
        return int(self.demand.sum())


def nint(x: float) -> int:
    """TSPLIB 'nint': round to nearest integer (half up), as CVRPLIB does."""
    return int(x + 0.5)


def euc2d_matrix(coords: np.ndarray, rounded: bool) -> np.ndarray:
    diff = coords[:, None, :] - coords[None, :, :]
    E = np.sqrt((diff ** 2).sum(axis=2))
    if rounded:
        return np.floor(E + 0.5).astype(np.int64)
    return E


def parse_vrp(path: str | Path, bks: float | None = None) -> Instance:
    """Parse a CVRPLIB file in TSPLIB format (EUC_2D, single depot)."""
    path = Path(path)
    header: dict[str, str] = {}
    coords: dict[int, tuple[float, float]] = {}
    demands: dict[int, int] = {}
    depots: list[int] = []
    section = None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line == "EOF":
            continue
        if line.endswith("SECTION"):
            section = line
            continue
        if section is None and ":" in line:
            k, v = line.split(":", 1)
            header[k.strip().upper()] = v.strip()
            continue
        parts = line.split()
        if section == "NODE_COORD_SECTION":
            coords[int(parts[0])] = (float(parts[1]), float(parts[2]))
        elif section == "DEMAND_SECTION":
            demands[int(parts[0])] = int(parts[1])
        elif section == "DEPOT_SECTION":
            v = int(parts[0])
            if v != -1:
                depots.append(v)
    if header.get("EDGE_WEIGHT_TYPE", "EUC_2D") != "EUC_2D":
        raise ValueError("only EUC_2D instances are supported")
    dim = int(header["DIMENSION"])
    Q = int(header["CAPACITY"])
    depot = depots[0] if depots else 1
    # Re-index so that the depot becomes 0 and customers keep their order.
    order = [depot] + [i for i in range(1, dim + 1) if i != depot]
    xy = np.array([coords[i] for i in order], dtype=float)
    dem = np.array([demands.get(i, 0) for i in order], dtype=np.int64)
    dem[0] = 0
    name = header.get("NAME", path.stem)
    # Fleet size: from the name suffix "-kX" if present, else lower bound.
    K = None
    if "-k" in name:
        try:
            K = int(name.rsplit("-k", 1)[1])
        except ValueError:
            K = None
    if K is None:
        K = math.ceil(dem.sum() / Q)
    return Instance(name=name, n=dim - 1, Q=Q, K=K, demand=dem,
                    D=euc2d_matrix(xy, rounded=True), coords=xy, bks=bks)


def parse_sol(path: str | Path) -> tuple[list[list[int]], float]:
    """Parse a CVRPLIB .sol file. Customer ids in .sol files are 1..n,
    which matches our re-indexing when the depot is node 1 in the .vrp."""
    routes, cost = [], None
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line.lower().startswith("route"):
            routes.append([int(x) for x in line.split(":", 1)[1].split()])
        elif line.lower().startswith("cost"):
            cost = float(line.split()[1])
    return routes, cost


def load_bks(csv_path: str | Path) -> dict[str, float]:
    out = {}
    lines = Path(csv_path).read_text().strip().splitlines()[1:]
    for line in lines:
        parts = line.split(",")
        out[parts[0]] = float(parts[-1])
    return out


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_benchmark(name: str) -> Instance:
    bks = load_bks(DATA_DIR / "cvrplib" / "bks.csv").get(name)
    return parse_vrp(DATA_DIR / "cvrplib" / f"{name}.vrp", bks=bks)
