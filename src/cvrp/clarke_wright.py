"""Clarke–Wright savings heuristic (parallel version) and a fleet-size repair.

Reference: G. Clarke and J. W. Wright, "Scheduling of vehicles from a central
depot to a number of delivery points", Operations Research 12(4), 1964.
The parallel-savings pseudocode follows the standard textbook description
(e.g. Laporte & Semet, "Classical heuristics for the CVRP", in Toth & Vigo,
The Vehicle Routing Problem, SIAM 2002). Implementation is our own.

Algorithm
---------
1. Start with one route 0-i-0 per customer i.
2. Compute the saving s(i, j) = d(0, i) + d(0, j) - d(i, j) for every pair i < j.
   (Merging routes ...-i-0 and 0-j-... into ...-i-j-... saves exactly s(i, j).)
3. Sort the savings in decreasing order.
4. Scan the list once. For (i, j) with s(i, j) > 0, merge the routes of i and j if
   * i and j are in different routes,
   * both i and j are endpoints (first or last customer) of their routes,
   * the merged load does not exceed Q.
   Orientation is fixed so that i and j become adjacent (routes are reversed
   when needed; reversing a route does not change its cost because d is
   symmetric).

Complexity: n(n-1)/2 savings, sorting them is O(n^2 log n); the scan is O(n^2)
pair checks, each O(1), plus at most n-1 merges.  Each merge relabels only the
customers of the absorbed route, and the list concatenation is O(n) in the worst
case, so merges cost O(n^2) in total.  Overall O(n^2 log n), dominated by the sort.
"""
from __future__ import annotations

from .instance import Instance
from .solution import Routes


def savings_list(inst: Instance) -> list[tuple[float, int, int]]:
    """All positive savings (s, i, j), i < j, sorted by decreasing s.
    Ties are broken by (i, j) ascending so that the result is deterministic."""
    d = inst.d
    n = inst.n
    d0 = d[0]
    out = []
    for i in range(1, n + 1):
        di = d[i]
        d0i = d0[i]
        for j in range(i + 1, n + 1):
            s = d0i + d0[j] - di[j]
            if s > 0:
                out.append((-s, i, j))
    out.sort()                                  # O(n^2 log n)
    return [(-s, i, j) for s, i, j in out]


def clarke_wright(inst: Instance) -> Routes:
    """Classical parallel Clarke–Wright savings.  Deterministic.

    Returns a list of routes (customers only).  Every route respects the
    capacity Q, but the number of routes may exceed inst.K (see
    ``extra_routes`` / ``reduce_routes``)."""
    n, Q, q = inst.n, inst.Q, inst.q
    # route id of every customer; routes stored as lists, None when absorbed
    rid = list(range(n + 1))                    # rid[i] = i initially (route 0-i-0)
    routes: list[list[int] | None] = [[i] for i in range(n + 1)]
    routes[0] = None
    load = [q[i] for i in range(n + 1)]

    for _s, i, j in savings_list(inst):
        ri, rj = rid[i], rid[j]
        if ri == rj:
            continue
        Ri, Rj = routes[ri], routes[rj]
        if load[ri] + load[rj] > Q:
            continue
        # i and j must be endpoints of their routes (interior customers cannot
        # be linked to another route without breaking their current route)
        i_first, i_last = Ri[0] == i, Ri[-1] == i
        j_first, j_last = Rj[0] == j, Rj[-1] == j
        if not (i_first or i_last) or not (j_first or j_last):
            continue
        # Orient so that the result is  ... i  j ...
        if i_last and j_first:
            merged = Ri + Rj
        elif i_first and j_last:
            merged = Rj + Ri                    # ... j i ...  (same arc i-j)
        elif i_last and j_last:
            merged = Ri + Rj[::-1]
        else:                                    # i_first and j_first
            merged = Ri[::-1] + Rj
        # keep the id of the larger route, relabel the smaller one
        keep, drop = (ri, rj) if len(Ri) >= len(Rj) else (rj, ri)
        for c in routes[drop]:
            rid[c] = keep
        routes[keep] = merged
        routes[drop] = None
        load[keep] += load[drop]
    return [r for r in routes if r]


def extra_routes(inst: Instance, routes: Routes) -> int:
    """How many routes the solution uses beyond the fleet size K (0 if OK)."""
    return max(0, sum(1 for r in routes if r) - inst.K)


def cheapest_insertion(inst: Instance, routes: Routes, loads: list[int], c: int,
                       allow_overload: bool) -> tuple[int, int, float] | None:
    """Cheapest position (route index, position, added cost) for customer c.
    If allow_overload is False, only routes with enough residual capacity are
    considered; returns None if there is none."""
    d, q, Q = inst.d, inst.q, inst.Q
    best = None
    dc = d[c]
    for r, R in enumerate(routes):
        if not allow_overload and loads[r] + q[c] > Q:
            continue
        prev = 0
        for pos in range(len(R) + 1):
            nxt = R[pos] if pos < len(R) else 0
            add = dc[prev] + dc[nxt] - d[prev][nxt]
            if best is None or add < best[2]:
                best = (r, pos, add)
            prev = nxt
    return best


def reduce_routes(inst: Instance, routes: Routes) -> Routes:
    """Repair for solutions with more than K routes (separate from CW itself).

    While there are more than K routes: dissolve the route with the smallest
    load and re-insert its customers (largest demand first) at the cheapest
    position of a route that still has room; if no route has room, at the
    cheapest position overall (the result may then be overloaded -- the tabu
    search's capacity penalty is responsible for repairing that)."""
    routes = [list(r) for r in routes if r]
    q = inst.q
    while len(routes) > inst.K:
        loads = [sum(q[c] for c in R) for R in routes]
        victim = min(range(len(routes)), key=lambda r: (loads[r], len(routes[r]), r))
        custs = sorted(routes.pop(victim), key=lambda c: (-q[c], c))
        loads.pop(victim)
        for c in custs:
            ins = cheapest_insertion(inst, routes, loads, c, allow_overload=False)
            if ins is None:
                # minimise overload first, then cost
                best = None
                for r, R in enumerate(routes):
                    over = max(0, loads[r] + q[c] - inst.Q)
                    one = cheapest_insertion(inst, [R], [0], c, allow_overload=True)
                    key = (over, one[2])
                    if best is None or key < best[0]:
                        best = (key, r, one[1])
                _, r, pos = best
            else:
                r, pos, _ = ins
            routes[r].insert(pos, c)
            loads[r] += q[c]
    return routes
