"""Split: optimal segmentation of a giant tour into CVRP routes.

Adapted from the published pseudocode of
    C. Prins (2004), "A simple and effective evolutionary algorithm for the
    vehicle routing problem", Computers & Operations Research 31, 1985-2002,
    Section 3 (procedure SPLIT), and the limited-fleet extension discussed in
    the same paper / in Prins, Lacomme & Prodhon (2014), "Order-first
    split-second methods for vehicle routing problems: A review".
The code below is our own implementation of that pseudocode.

Giant tour T = (T[0], ..., T[n-1]) is a permutation of the customers 1..n.

Auxiliary DAG H:
  * nodes 0, 1, ..., n   (node i = "the first i customers of T are served")
  * arc (i, j) for i < j exists iff the customers T[i..j-1] fit in one
    vehicle:  q(T[i]) + ... + q(T[j-1]) <= Q
  * arc cost = cost of the route  0 -> T[i] -> ... -> T[j-1] -> 0
A shortest 0 -> n path in H is an optimal segmentation (each arc = one route).
H is acyclic and its nodes are already topologically ordered, so Bellman's
algorithm needs one pass over the nodes in index order.

Complexity: from node i the inner loop extends j while the load fits and
breaks at the first overflow, so it scans at most L+1 customers, where L is
the maximal number of customers in one route (L <= n). Every arc is
evaluated in O(1) (incremental route cost), so unlimited Split is O(n*L),
i.e. O(n^2) in general.  The limited-fleet version repeats the relaxation
for every route count k = 1..K, so it is O(K*n*L).
"""
from __future__ import annotations

from .instance import Instance

INF = float("inf")


def split_unlimited(inst: Instance, tour: list[int]) -> tuple[float, list[list[int]]]:
    """Optimal segmentation with an unlimited number of vehicles.

    Returns (cost, routes). Always feasible as long as every q_i <= Q.
    """
    d = inst.d
    d0 = d[0]
    q = inst.q
    Q = inst.Q
    n = len(tour)
    V = [INF] * (n + 1)          # V[j] = cost of best split of T[0..j-1]
    P = [0] * (n + 1)            # P[j] = start index of the last route
    V[0] = 0
    for i in range(n):           # nodes in topological order
        vi = V[i]
        load = 0
        path = 0                 # cost depot -> T[i] -> ... -> T[j], no return
        prev = 0
        for j in range(i, n):
            c = tour[j]
            load += q[c]
            if load > Q:         # all longer routes from i are infeasible too
                break
            path += d[prev][c]
            cand = vi + path + d0[c]   # + return to the depot
            if cand < V[j + 1]:
                V[j + 1] = cand
                P[j + 1] = i
            prev = c
    return V[n], _extract(tour, P)


def _extract(tour, P):
    routes = []
    j = len(tour)
    while j > 0:
        i = P[j]
        routes.append(tour[i:j])
        j = i
    routes.reverse()
    return routes


def split_limited(inst: Instance, tour: list[int], K: int,
                  overload_penalty: float | None = None,
                  max_load: float | None = None) -> tuple[float, list[list[int]] | None]:
    """Optimal segmentation using at most K routes (layered DP).

    V[k][j] = min cost of serving T[0..j-1] with exactly k routes.
    V[k][j] = min_{i<j, arc (i,j) in H} V[k-1][i] + cost(i, j).
    Answer = min_{k<=K} V[k][n].  Returns (INF, None) when no segmentation
    with <= K routes exists. Complexity O(K*n*L).

    Soft-capacity mode (used by the GA, idea from Vidal et al. 2012 HGS):
    if ``overload_penalty`` (lambda) is given, a route may carry up to
    ``max_load`` (> Q) and its arc cost becomes
        distance + lambda * max(0, load - Q).
    With overload_penalty=None this is the exact hard-capacity Split.
    """
    d = inst.d
    d0 = d[0]
    q = inst.q
    Q = inst.Q
    n = len(tour)
    if overload_penalty is not None:
        return _split_limited_soft(d, d0, q, Q, tour, K, overload_penalty,
                                   max_load if max_load is not None else INF)
    Vprev = [INF] * (n + 1)
    Vprev[0] = 0
    preds = []                    # preds[k-1][j] = start of the k-th route
    best, best_k = INF, 0
    for k in range(1, K + 1):
        V = [INF] * (n + 1)
        P = [-1] * (n + 1)
        any_finite = False
        for i in range(n):
            vi = Vprev[i]
            if vi == INF:
                continue
            any_finite = True
            load = 0
            path = 0
            prev = 0
            for j in range(i, n):
                c = tour[j]
                load += q[c]
                if load > Q:
                    break
                path += d[prev][c]
                cand = vi + path + d0[c]
                if cand < V[j + 1]:
                    V[j + 1] = cand
                    P[j + 1] = i
                prev = c
        preds.append(P)
        if V[n] < best:
            best, best_k = V[n], k
        if not any_finite:
            break
        Vprev = V
    return _extract_layers(tour, preds, best, best_k)


def _extract_layers(tour, preds, best, best_k):
    if best == INF:
        return INF, None
    # Walk back through the layers: layer k gives the start of the k-th route.
    routes = []
    j = len(tour)
    for k in range(best_k, 0, -1):
        i = preds[k - 1][j]
        routes.append(tour[i:j])
        j = i
    routes.reverse()
    return best, routes


def _split_limited_soft(d, d0, q, Q, tour, K, lam, max_load):
    """Same layered DP as split_limited, with penalized overload.
    The inner loop breaks when load > max_load instead of > Q."""
    n = len(tour)
    Vprev = [INF] * (n + 1)
    Vprev[0] = 0
    preds = []
    best, best_k = INF, 0
    for k in range(1, K + 1):
        V = [INF] * (n + 1)
        P = [-1] * (n + 1)
        any_finite = False
        for i in range(n):
            vi = Vprev[i]
            if vi == INF:
                continue
            any_finite = True
            load = 0
            path = 0
            prev = 0
            for j in range(i, n):
                c = tour[j]
                load += q[c]
                if load > max_load:
                    break
                path += d[prev][c]
                cand = vi + path + d0[c]
                if load > Q:
                    cand += lam * (load - Q)
                if cand < V[j + 1]:
                    V[j + 1] = cand
                    P[j + 1] = i
                prev = c
        preds.append(P)
        if V[n] < best:
            best, best_k = V[n], k
        if not any_finite:
            break
        Vprev = V
    return _extract_layers(tour, preds, best, best_k)


def split(inst: Instance, tour: list[int], K: int | None = None,
          fleet_penalty: float | None = None) -> tuple[float, list[list[int]]]:
    """Split a giant tour.

    * K is None  -> unlimited fleet, returns the optimal (cost, routes).
    * K given    -> the optimal segmentation with at most K routes.
      Shortcut: if the unlimited optimum already uses <= K routes it is also
      optimal for the limited problem, so the O(K*n*L) DP runs only when the
      unlimited optimum uses too many routes.
      If NO segmentation with <= K routes exists (possible on tight
      instances such as A-n80-k10), we return the unlimited split together
      with a PENALIZED cost:
          true_cost + fleet_penalty * (number_of_routes - K)
      so the caller can recognise it with ``len(routes) > K`` and rank it
      below feasible solutions. fleet_penalty defaults to
      2 * max_i d(0, i), the price of an extra out-and-back trip.
    """
    cost, routes = split_unlimited(inst, tour)
    if K is None or len(routes) <= K:
        return cost, routes
    lcost, lroutes = split_limited(inst, tour, K)
    if lroutes is not None:
        return lcost, lroutes
    if fleet_penalty is None:
        fleet_penalty = default_fleet_penalty(inst)
    return cost + fleet_penalty * (len(routes) - K), routes


def default_fleet_penalty(inst: Instance) -> float:
    return 2.0 * max(inst.d[0])
