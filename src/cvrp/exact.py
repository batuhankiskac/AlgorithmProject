"""Exact CVRP solver for tiny instances (Task 2c): dynamic programming.

Step 1 (route costs, Held-Karp): for every subset S of customers with
q(S) <= Q, the cheapest route depot -> S -> depot is computed with the
Held-Karp TSP recurrence
    h[S][j] = min_{i in S \\ {j}} h[S \\ {j}][i] + d(i, j),   h[{j}][j] = d(0, j)
    c(S)    = min_{j in S} h[S][j] + d(j, 0)
    time O(2^n n^2), memory O(2^n n).

Step 2 (set partitioning): the cheapest partition of all customers into at
most K feasible routes
    F[k][M] = min over S subseteq M with lowbit(M) in S, q(S) <= Q:
              c(S) + F[k-1][M \\ S]
    time O(K 3^n).

Fixing the lowest customer of M inside S avoids enumerating the same
partition in several orders. Practical up to n ~ 12-13.
"""
from __future__ import annotations

from .instance import Instance

INF = float("inf")


def _route_costs(inst: Instance):
    n, d, q, Q = inst.n, inst.d, inst.q, inst.Q
    full = 1 << n
    load = [0] * full
    for m in range(1, full):
        low = (m & -m).bit_length() - 1
        load[m] = load[m & (m - 1)] + q[low + 1]
    h = [[INF] * n for _ in range(full)]
    par = [[-1] * n for _ in range(full)]
    for j in range(n):
        h[1 << j][j] = d[0][j + 1]
    for m in range(1, full):
        if load[m] > Q:
            continue
        hm = h[m]
        for j in range(n):
            if not (m >> j) & 1 or hm[j] == INF:
                continue
            base = hm[j]
            dj = d[j + 1]
            for k in range(n):
                if (m >> k) & 1:
                    continue
                m2 = m | (1 << k)
                v = base + dj[k + 1]
                if v < h[m2][k]:
                    h[m2][k] = v
                    par[m2][k] = j
    cost = [INF] * full
    last = [-1] * full
    for m in range(1, full):
        if load[m] > Q:
            continue
        for j in range(n):
            if (m >> j) & 1 and h[m][j] < INF:
                v = h[m][j] + d[j + 1][0]
                if v < cost[m]:
                    cost[m], last[m] = v, j
    return cost, last, par, load


def _rebuild_route(m: int, last_j: int, par) -> list[int]:
    route = []
    j = last_j
    while m:
        route.append(j + 1)
        pj = par[m][j]
        m &= ~(1 << j)
        j = pj
    return route[::-1]


def solve_exact(inst: Instance, K: int | None = None) -> tuple[float, list[list[int]]]:
    """Return (optimal cost, optimal routes) using at most K routes."""
    n = inst.n
    if n > 14:
        raise ValueError("exact DP is only meant for tiny instances")
    K = inst.K if K is None else K
    cost, last, par, _ = _route_costs(inst)
    full = 1 << n
    # F[k][M]: best cost covering M with at most k routes
    F = [[INF] * full for _ in range(K + 1)]
    choice = [[0] * full for _ in range(K + 1)]
    for k in range(K + 1):
        F[k][0] = 0.0
    for k in range(1, K + 1):
        Fk, Fp = F[k], F[k - 1]
        for M in range(1, full):
            low = M & -M
            rest = M ^ low
            best, bs = INF, 0
            sub = rest
            while True:
                S = sub | low
                c = cost[S]
                if c < INF:
                    v = c + Fp[M ^ S]
                    if v < best:
                        best, bs = v, S
                if sub == 0:
                    break
                sub = (sub - 1) & rest
            Fk[M], choice[k][M] = best, bs
    if F[K][full - 1] == INF:
        return INF, []
    routes, M, k = [], full - 1, K
    while M:
        S = choice[k][M]
        routes.append(_rebuild_route(S, last[S], par))
        M ^= S
        k -= 1
    return F[K][full - 1], routes
