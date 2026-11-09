"""Granular Tabu Search for the CVRP (own implementation).

Ideas taken from the literature (pseudocode / descriptions only, no code):
  * granular neighbourhoods  -- P. Toth, D. Vigo, "The granular tabu search and
    its application to the vehicle-routing problem", INFORMS J. Computing 15(4), 2003;
  * penalised capacity violation with a self-adjusting weight -- J.-F. Cordeau,
    G. Laporte, A. Mercier, "A unified tabu search heuristic for vehicle routing
    problems with time windows", JORS 52, 2001 (also Gendreau, Hertz, Laporte,
    "TABUROUTE", Management Science 40, 1994);
  * 2-opt* -- J.-Y. Potvin, J.-M. Rousseau, "An exchange heuristic for routeing
    problems with time windows", JORS 46, 1995.

Search space
------------
Exactly K route slots (some may be empty), so a solution never uses more than K
vehicles.  Capacity may be violated; the search minimises the penalised cost

        f(S) = c(S) + λ · Σ_r max(0, load_r − Q)

and keeps the best *feasible* solution seen (that is what ``solve`` returns).

One iteration
-------------
For every customer u and every v in N_k(u) (the k nearest customers of u)
evaluate, in O(1) each, the moves that put u next to v:
  * v in another route:  relocate u after v, relocate u before v, swap u<->v,
                         2-opt* tail exchange (u→v), 2-opt* with reversal (u→v);
  * v in the same route: relocate u after v, relocate u before v,
                         two 2-opt segment reversals creating the arc (u, v);
plus "relocate u into an empty route" when an empty slot exists.  The best
admissible move (lowest Δf, not tabu or satisfying the aspiration criterion) is
applied, even if it worsens f.  Cost per iteration: Θ(n·k) evaluations + O(n)
for applying the move and refreshing positions / prefix loads.

Tabu attribute
--------------
Arcs (undirected customer pairs, including depot arcs).  When a move removes
arc {a, b}, re-inserting {a, b} is forbidden until iteration it + θ, θ drawn
uniformly in [tenure_min, tenure_max].  A move is tabu if any arc it creates is
tabu.  Aspiration: a tabu move is allowed if it yields a feasible solution
cheaper than the best feasible one found so far.

Penalty weight λ  (Cordeau et al. 2001 rule)
--------------------------------------------
After each iteration: λ ← λ·(1+δ) if the current solution is overloaded,
otherwise λ ← λ/(1+δ); λ is clamped to [λ0/100, λ0·1000].

Diversification
---------------
If the best feasible solution has not improved for ``stall_iters`` iterations,
restart from it after a random "ruin and recreate" perturbation: remove a random
fraction (perturb_min_frac..perturb_max_frac) of the customers and reinsert them
in random order at their cheapest penalised position; the tabu list is cleared.
"""
from __future__ import annotations

import random
import time

from .clarke_wright import clarke_wright, reduce_routes
from .instance import Instance
from .moves import (RELOCATE, SWAP, TWO_OPT, STAR_A, STAR_B, MOVE_NAMES,
                    apply_move, move_arcs)
from .solution import Result, Routes, total_cost

DEFAULT_PARAMS = {
    "k_neighbours": 20,        # size of the granular candidate list N_k(u)
    "tenure_min": 5,           # tabu tenure drawn uniformly from [min, max]
    "tenure_max": 15,
    "lambda_init": None,       # None -> c(S0) / total demand (distance per unit of demand)
    "lambda_delta": 0.5,       # λ multiplied / divided by (1 + δ) each iteration
    "stall_iters": None,       # None -> 40 * n iterations without best-improvement
    "perturb_min_frac": 0.10,  # fraction of customers removed by a perturbation
    "perturb_max_frac": 0.25,
    "resync_every": 1000,      # recompute c(S) from scratch (float drift guard)
    "debug_check": False,      # verify every applied delta against a full recomputation
}

EPS = 1e-9


def _excess(L: int, Q: int) -> int:
    return L - Q if L > Q else 0


def _scan(order, nbrs, route_of, pos_of, pred, succ, cum, size, load, d, q, Q,
          lam, it, tabu, cur_cost, cur_over, best_feas, empty_r):
    """Return the best admissible move (move, Δcost, Δoverload) of the
    granular neighbourhood, or None if every candidate is tabu.

    Notation (for u in route r1 at position i, v in route r2 at position j):
    pu/su = predecessor/successor of u (0 = depot), pv/sv likewise for v,
    L1/L2 = route loads, P1 = cum[u] = load of R1[0..i] (prefix load).
    pred/succ/cum/route_of/pos_of are per-customer arrays kept up to date by
    _State.refresh, so every lookup below is O(1)."""
    best_f = float("inf")
    best = None
    target = best_feas - EPS - cur_cost      # aspiration: feasible and Δc < target
    for u in order:
        r1 = route_of[u]
        i = pos_of[u]
        pu = pred[u]
        su = succ[u]
        du = d[u]
        dpu = d[pu]
        d_pu_u = du[pu]
        d_u_su = du[su]
        rem = d_pu_u + d_u_su - dpu[su]       # saving of taking u out of R1
        qu = q[u]
        L1 = load[r1]
        ex1 = L1 - Q if L1 > Q else 0
        L1m = L1 - qu                          # load of R1 without u
        ex1m = L1m - Q if L1m > Q else 0
        P1 = cum[u]
        tu = tabu[u]
        tpu = tabu[pu]

        # --- relocate u into an empty route:  0-u-0
        if empty_r >= 0 and size[r1] > 1:
            dc = du[0] + du[0] - rem
            do = ex1m + (qu - Q if qu > Q else 0) - ex1
            f = dc + lam * do
            if f < best_f and (not (tu[0] > it or tpu[su] > it)
                               or (cur_over + do == 0 and dc < target)):
                best_f, best = f, ((RELOCATE, r1, i, empty_r, 0), dc, do)

        for v in nbrs[u]:
            r2 = route_of[v]
            j = pos_of[v]
            pv = pred[v]
            sv = succ[v]
            dv = d[v]
            duv = du[v]
            if r2 != r1:
                L2 = load[r2]
                exb = ex1 + (L2 - Q if L2 > Q else 0)
                # ---- relocate u into R2 (loads L1-qu, L2+qu)
                L2p = L2 + qu
                do = ex1m + (L2p - Q if L2p > Q else 0) - exb
                pen = lam * do
                ok_asp = cur_over + do == 0
                tps = tpu[su] > it
                #   after v:   ... v u sv ...
                dc = duv + du[sv] - dv[sv] - rem
                f = dc + pen
                if f < best_f and (not (tps or tu[v] > it or tu[sv] > it)
                                   or (ok_asp and dc < target)):
                    best_f, best = f, ((RELOCATE, r1, i, r2, j + 1), dc, do)
                #   before v:  ... pv u v ...
                dc = du[pv] + duv - dv[pv] - rem
                f = dc + pen
                if f < best_f and (not (tps or tu[pv] > it or tu[v] > it)
                                   or (ok_asp and dc < target)):
                    best_f, best = f, ((RELOCATE, r1, i, r2, j), dc, do)
                # ---- swap u <-> v
                qv = q[v]
                a = L1m + qv
                b = L2 - qv + qu
                do = (a - Q if a > Q else 0) + (b - Q if b > Q else 0) - exb
                dc = (dpu[v] + dv[su] + du[pv] + du[sv]
                      - d_pu_u - d_u_su - dv[pv] - dv[sv])
                f = dc + lam * do
                if f < best_f:
                    tv = tabu[v]
                    if (not (tpu[v] > it or tv[su] > it or tu[pv] > it or tu[sv] > it)
                            or (cur_over + do == 0 and dc < target)):
                        best_f, best = f, ((SWAP, r1, i, r2, j), dc, do)
                # ---- 2-opt* A:  R1[..u] + R2[v..],  R2[..pv] + R1[su..]
                P2m = cum[v] - q[v]            # load of R2[0..j-1]
                a = P1 + L2 - P2m
                b = P2m + L1 - P1
                do = (a - Q if a > Q else 0) + (b - Q if b > Q else 0) - exb
                dc = duv + d[pv][su] - d_u_su - dv[pv]
                f = dc + lam * do
                if f < best_f and (not (tu[v] > it or tabu[pv][su] > it)
                                   or (cur_over + do == 0 and dc < target)):
                    best_f, best = f, ((STAR_A, r1, i, r2, j), dc, do)
                # ---- 2-opt* B:  R1[..u] + rev(R2[..v]),  rev(R1[su..]) + R2[sv..]
                a = P1 + cum[v]
                b = L1 + L2 - a
                do = (a - Q if a > Q else 0) + (b - Q if b > Q else 0) - exb
                dc = duv + d[su][sv] - d_u_su - dv[sv]
                f = dc + lam * do
                if f < best_f and (not (tu[v] > it or tabu[su][sv] > it)
                                   or (cur_over + do == 0 and dc < target)):
                    best_f, best = f, ((STAR_B, r1, i, r2, j), dc, do)
            else:
                # ---- intra-route relocate (load unchanged, Δoverload = 0)
                ok_asp = cur_over == 0
                tps = tpu[su] > it
                if v != pu:                       # after v (v == pu is a no-op)
                    dc = duv + du[sv] - dv[sv] - rem
                    if dc < best_f and (not (tps or tu[v] > it or tu[sv] > it)
                                        or (ok_asp and dc < target)):
                        best_f, best = dc, ((RELOCATE, r1, i, r1, j + 1), dc, 0)
                if v != su:                       # before v (v == su is a no-op)
                    dc = du[pv] + duv - dv[pv] - rem
                    if dc < best_f and (not (tps or tu[pv] > it or tu[v] > it)
                                        or (ok_asp and dc < target)):
                        best_f, best = dc, ((RELOCATE, r1, i, r1, j), dc, 0)
                # ---- 2-opt: reversals that create the arc (u, v)
                if i < j:
                    p, s, x, y, sx, sy, px, py = i, j, u, v, su, sv, pu, pv
                else:
                    p, s, x, y, sx, sy, px, py = j, i, v, u, sv, su, pv, pu
                if s - p >= 2:
                    dxy = duv
                    # reverse R[p+1..s]:  x y ... sx sy
                    dc = dxy + d[sx][sy] - d[x][sx] - d[y][sy]
                    if dc < best_f and (not (tu[v] > it or tabu[sx][sy] > it)
                                        or (ok_asp and dc < target)):
                        best_f, best = dc, ((TWO_OPT, r1, p + 1, r1, s), dc, 0)
                    # reverse R[p..s-1]:  px py ... x y
                    dc = d[px][py] + dxy - d[px][x] - d[py][y]
                    if dc < best_f and (not (tu[v] > it or tabu[px][py] > it)
                                        or (ok_asp and dc < target)):
                        best_f, best = dc, ((TWO_OPT, r1, p, r1, s - 1), dc, 0)
    return best


class _State:
    """Current solution with the auxiliary arrays needed for O(1) deltas."""

    def __init__(self, inst: Instance, routes: Routes, K: int):
        self.inst = inst
        self.routes = [list(r) for r in routes] + [[] for _ in range(K - len(routes))]
        n = inst.n
        self.route_of = [0] * (n + 1)
        self.pos_of = [0] * (n + 1)
        self.pred = [0] * (n + 1)              # predecessor of c (0 = depot)
        self.succ = [0] * (n + 1)              # successor of c (0 = depot)
        self.cum = [0] * (n + 1)               # prefix load: Σ q over R[0..pos_of[c]]
        self.size = [0] * K                    # number of customers in route r
        self.load = [0] * K
        for r in range(K):
            self.refresh(r)
        self.cost = total_cost(inst, self.routes)
        self.over = self.overload()

    def refresh(self, r: int) -> None:
        q = self.inst.q
        route_of, pos_of, pred, succ, cum = self.route_of, self.pos_of, self.pred, self.succ, self.cum
        R = self.routes[r]
        acc = 0
        prev = 0
        for k, c in enumerate(R):
            route_of[c] = r
            pos_of[c] = k
            acc += q[c]
            cum[c] = acc
            pred[c] = prev
            if prev:
                succ[prev] = c
            prev = c
        if prev:
            succ[prev] = 0
        self.size[r] = len(R)
        self.load[r] = acc

    def overload(self) -> int:
        Q = self.inst.Q
        return sum(L - Q for L in self.load if L > Q)

    def empty_slot(self) -> int:
        for r, R in enumerate(self.routes):
            if not R:
                return r
        return -1


def _bring_to_K(inst: Instance, routes: Routes) -> Routes:
    routes = [list(r) for r in routes if r]
    if len(routes) > inst.K:
        routes = reduce_routes(inst, routes)
    return routes


def _perturb(inst: Instance, routes: Routes, rng: random.Random, frac: float,
             lam: float) -> Routes:
    """Ruin & recreate: remove ⌈frac·n⌉ random customers and reinsert each (in
    random order) at the position with the smallest penalised insertion cost."""
    d, q, Q = inst.d, inst.q, inst.Q
    routes = [list(r) for r in routes]
    m = max(1, int(round(frac * inst.n)))
    removed = set(rng.sample(range(1, inst.n + 1), m))
    routes = [[c for c in R if c not in removed] for R in routes]
    loads = [sum(q[c] for c in R) for R in routes]
    order = list(removed)
    rng.shuffle(order)
    for c in order:
        dc_row = d[c]
        best = None
        seen_empty = False
        for r, R in enumerate(routes):
            if not R:
                if seen_empty:
                    continue                    # all empty routes are equivalent
                seen_empty = True
            pen = lam * (_excess(loads[r] + q[c], Q) - _excess(loads[r], Q))
            prev = 0
            for pos in range(len(R) + 1):
                nxt = R[pos] if pos < len(R) else 0
                f = dc_row[prev] + dc_row[nxt] - d[prev][nxt] + pen
                if best is None or f < best[0]:
                    best = (f, r, pos)
                prev = nxt
        _, r, pos = best
        routes[r].insert(pos, c)
        loads[r] += q[c]
    return routes


def solve(inst: Instance, time_limit: float = 30.0, seed: int = 0, params: dict | None = None,
          init_routes: Routes | None = None, max_iters: int | None = None) -> Result:
    """Granular tabu search.  Stops at ``time_limit`` seconds or ``max_iters``
    iterations, whichever comes first.  Returns the best feasible solution."""
    t0 = time.perf_counter()
    P = dict(DEFAULT_PARAMS)
    if params:
        P.update(params)
    rng = random.Random(seed)
    n, K, Q = inst.n, inst.K, inst.Q
    d, q = inst.d, inst.q

    # ---------------- initial solution
    init = clarke_wright(inst) if init_routes is None else init_routes
    init_n_routes = sum(1 for r in init if r)
    S = _State(inst, _bring_to_K(inst, init), K)
    init_cost = S.cost

    # ---------------- granular candidate lists: k nearest customers of each u
    k = min(P["k_neighbours"], n - 1)
    nbrs = [[]] + [sorted((v for v in range(1, n + 1) if v != u), key=lambda v: (d[u][v], v))[:k]
                   for u in range(1, n + 1)]

    lam0 = P["lambda_init"] or max(S.cost / max(1, inst.total_demand), 1e-6)
    lam, lam_min, lam_max = lam0, lam0 / 100.0, lam0 * 1000.0
    up = 1.0 + P["lambda_delta"]
    stall = P["stall_iters"] or 40 * n
    tmin, tmax = P["tenure_min"], P["tenure_max"]
    tabu = [[0] * (n + 1) for _ in range(n + 1)]   # tabu[a][b] = last tabu iteration (+1)

    best_cost = float("inf")
    best_routes = None
    history: list[tuple[float, float]] = []
    if S.over == 0:
        best_cost, best_routes = S.cost, [list(r) for r in S.routes]
        history.append((time.perf_counter() - t0, total_cost(inst, best_routes)))

    order = list(range(1, n + 1))
    it = 0
    last_improve = 0
    feasible_iters = 0
    n_perturb = 0
    n_tabu_blocked = 0
    move_count = {name: 0 for name in MOVE_NAMES.values()}
    debug = P["debug_check"]

    while True:
        if max_iters is not None and it >= max_iters:
            break
        if time.perf_counter() - t0 >= time_limit:
            break
        it += 1
        rng.shuffle(order)                         # random tie-breaking
        found = _scan(order, nbrs, S.route_of, S.pos_of, S.pred, S.succ, S.cum, S.size,
                      S.load, d, q, Q, lam, it, tabu, S.cost, S.over, best_cost, S.empty_slot())
        if found is None:                          # every candidate tabu: clear the list
            n_tabu_blocked += 1
            tabu = [[0] * (n + 1) for _ in range(n + 1)]
            continue
        move, dc, do = found
        removed, _added = move_arcs(S.routes, move)
        for r in apply_move(S.routes, move):
            S.refresh(r)
        for a, b in removed:                       # forbid re-inserting removed arcs
            if a or b:
                tabu[a][b] = tabu[b][a] = it + rng.randint(tmin, tmax)
        S.cost += dc
        S.over += do
        move_count[MOVE_NAMES[move[0]]] += 1
        if debug:
            true_cost = total_cost(inst, S.routes)
            assert abs(true_cost - S.cost) < 1e-6 * max(1.0, true_cost), (move, true_cost, S.cost)
            assert S.over == S.overload(), (move, S.over, S.overload())
        elif it % P["resync_every"] == 0:
            S.cost = total_cost(inst, S.routes)

        # ---- adaptive penalty weight
        if S.over > 0:
            lam = min(lam * up, lam_max)
        else:
            feasible_iters += 1
            lam = max(lam / up, lam_min)
            if S.cost < best_cost - EPS:
                best_cost = S.cost
                best_routes = [list(r) for r in S.routes]
                last_improve = it
                history.append((time.perf_counter() - t0, total_cost(inst, best_routes)))

        # ---- diversification
        if it - last_improve >= stall:
            frac = rng.uniform(P["perturb_min_frac"], P["perturb_max_frac"])
            base = best_routes if best_routes is not None else S.routes
            S = _State(inst, _perturb(inst, base, rng, frac, lam), K)
            tabu = [[0] * (n + 1) for _ in range(n + 1)]
            last_improve = it
            n_perturb += 1

    elapsed = time.perf_counter() - t0
    feasible = best_routes is not None
    if not feasible:                               # should not happen; return the current one
        best_routes = S.routes
    out = [list(r) for r in best_routes if r]
    cost = total_cost(inst, out)
    return Result(
        routes=out, cost=cost, history=history, iterations=it, elapsed=elapsed,
        extra={
            "params": P, "feasible": feasible, "k": k,
            "initial_cost": init_cost, "initial_routes": init_n_routes,
            "iters_per_sec": it / elapsed if elapsed > 0 else 0.0,
            "feasible_iter_fraction": feasible_iters / it if it else 0.0,
            "perturbations": n_perturb, "tabu_blocked_iters": n_tabu_blocked,
            "move_counts": move_count, "final_lambda": lam, "lambda_init": lam0,
        },
    )
