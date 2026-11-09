"""Genetic Algorithm for the CVRP: giant-tour chromosome + Split decoder.

Based on C. Prins (2004), "A simple and effective evolutionary algorithm
for the vehicle routing problem", Computers & Operations Research 31,
1985-2002 (giant-tour encoding, OX crossover, Split, local search as
mutation, fitness spacing for diversity, partial restarts). We use his
published description as a starting point; all code is our own.
Two further ideas are borrowed (and re-implemented) from
T. Vidal et al. (2012), "A hybrid genetic algorithm for multidepot and
periodic vehicle routing problems", Operations Research 60(3):
  * capacity violations are allowed during the search with an adaptive
    penalty lambda * overload (needed: A-n45-k6 is 98.8% full, random
    giant tours almost never have a hard-feasible split with <= K routes);
  * granular neighbourhoods (only the g nearest customers of u are tried
    as move partners in the local search).

Chromosome  : giant tour = permutation of the customers 1..n (no depot).
Decoder     : limited-fleet Split (<= K routes) with penalized overload,
              see split.py.
Fitness     : distance + lambda * total overload (lower is better);
              feasible individuals have overload 0 so fitness = distance.

ONE GENERATION (this is what Result.iterations counts):
    produce lambda_ = params["n_offspring"] children; for each child
        2 binary tournaments                         O(1)
        OX crossover (prob. p_cx, else copy p1)      O(n)
        mutation (prob. p_mut)                       O(n)
        Split decoding                               O(K n L)
        [memetic] local search (prob. p_ls)          O(P n g)  (P passes)
        duplicate test against pop + offspring       O(mu + lambda)
    then survivor selection on mu + lambda individuals O((mu+lambda) log(mu+lambda)),
    lambda adaptation O(1), diversity measurement O(mu^2 n).
"""
from __future__ import annotations

import math
import random
import time

from .instance import Instance
from .solution import Result, total_cost
from .split import split, split_limited

DEFAULT_PARAMS = {
    "pop_size": 25,            # mu: population size kept after replacement
    "n_offspring": 25,         # lambda: children created per generation
    "p_cx": 0.9,               # probability of OX crossover (else clone parent 1)
    "p_mut": 0.2,              # probability of mutating a child
    "mutation": "inversion",   # "inversion" | "swap" | "insertion"
    "tournament": 2,           # tournament size (2 = binary tournament)
    "replacement": "plus",     # "plus" = (mu+lambda) truncation, "generational" = elitist generational
    "elite": 2,                # elites kept by generational replacement and by restarts
    "min_gap": 0.5,            # near-duplicate threshold on fitness (Prins' spacing Delta)
    "memetic": True,           # apply local search to offspring
    "p_ls": 0.5,               # probability of local search per child (memetic mode)
    "granular": 20,            # g: size of the neighbour lists in the local search
    "p_repair": 0.5,           # prob. to repair an infeasible LS result with 10x penalty
    "target_feasible": 0.4,    # adaptive penalty: target share of feasible children
    "max_load_factor": 1.5,    # soft Split: routes may carry up to 1.5 Q (penalized)
    "restart_after": 60,       # generations without improvement before a partial restart
    "init_sweep_frac": 0.3,    # share of the initial population built from sweep orders
    "diversity": True,         # record mean pairwise edge distance per generation
}


# ---------------------------------------------------------------- operators

def ox_crossover(p1: list[int], p2: list[int], rng: random.Random) -> list[int]:
    """Order Crossover (OX), Prins (2004) version.

    Copy the slice p1[i..j] into the child at the same positions, then fill
    the remaining positions (circularly, starting after j) with the
    customers of p2 in the order they appear in p2 starting after j.
    O(n) time with a boolean 'used' array.
    """
    n = len(p1)
    i = rng.randrange(n)
    j = rng.randrange(n)
    if i > j:
        i, j = j, i
    child = [0] * n
    used = [False] * (n + 1)
    for k in range(i, j + 1):
        c = p1[k]
        child[k] = c
        used[c] = True
    pos = (j + 1) % n
    for k in range(n):
        c = p2[(j + 1 + k) % n]
        if not used[c]:
            child[pos] = c
            pos = (pos + 1) % n
    return child


def mutate(tour: list[int], kind: str, rng: random.Random) -> None:
    """In-place mutation of a giant tour, O(n).

    inversion: reverse a random segment (= a 2-opt move on the giant tour:
               only 2 adjacencies change, so most route structure survives).
    swap:      exchange two customers (4 adjacencies change).
    insertion: remove a customer and reinsert it elsewhere (3 change).
    """
    n = len(tour)
    if n < 2:
        return
    i = rng.randrange(n)
    j = rng.randrange(n)
    while j == i:
        j = rng.randrange(n)
    if kind == "swap":
        tour[i], tour[j] = tour[j], tour[i]
    elif kind == "insertion":
        c = tour.pop(i)
        tour.insert(j, c)
    else:
        if i > j:
            i, j = j, i
        tour[i:j + 1] = tour[i:j + 1][::-1]


# ---------------------------------------------------------------- local search

class LocalSearch:
    """Granular first-improvement local search on a set of routes.

    Objective: distance + lam * sum_r max(0, load_r - Q).
    Moves for every customer u and every v among the g nearest customers of u:
      relocate u after v / before v, swap u and v,
      2-opt inside a route, 2-opt* between two routes (both variants),
      and relocate u into an empty route when fewer than K routes are used.
    Every move is evaluated in O(1) from prev/next customers and prefix loads;
    applying a move costs O(L) (rebuild positions of the two routes).
    'Route stamps' skip pairs (u, v) whose two routes did not change since u
    was last examined, so later passes are much cheaper than the first.
    Distances must be symmetric (true for EUC_2D and MediDrone).
    """

    def __init__(self, inst: Instance, granular: int):
        self.inst = inst
        d = inst.d
        n = inst.n
        g = min(granular, n - 1)
        self.nn = [[]] + [
            sorted((v for v in range(1, n + 1) if v != u), key=lambda v: d[u][v])[:g]
            for u in range(1, n + 1)
        ]

    def run(self, routes, K, lam, rng):
        inst = self.inst
        d = inst.d
        q = inst.q
        Q = inst.Q
        n = inst.n
        nn = self.nn
        routes = [list(r) for r in routes if r]
        while len(routes) < K:
            routes.append([])
        R = len(routes)
        rid = [0] * (n + 1)
        pos = [0] * (n + 1)
        load = [0] * R
        pre = [None] * R          # pre[r][k] = load of routes[r][0..k]
        stamp = [0] * R
        counter = 1

        def update(r):
            rr = routes[r]
            acc = 0
            p = []
            for k, c in enumerate(rr):
                rid[c] = r
                pos[c] = k
                acc += q[c]
                p.append(acc)
            pre[r] = p
            load[r] = acc
            stamp[r] = counter

        for r in range(R):
            update(r)

        def ex(x):
            return x - Q if x > Q else 0

        tested = [-1] * (n + 1)
        order = list(range(1, n + 1))
        improved = True
        while improved:
            improved = False
            rng.shuffle(order)
            for u in order:
                last = tested[u]
                tested[u] = counter
                du = d[u]
                qu = q[u]
                for v in nn[u]:
                    ru = rid[u]
                    rv = rid[v]
                    if stamp[ru] <= last and stamp[rv] <= last:
                        continue
                    Ru = routes[ru]
                    Rv = routes[rv]
                    i = pos[u]
                    j = pos[v]
                    pu = Ru[i - 1] if i else 0
                    nu = Ru[i + 1] if i + 1 < len(Ru) else 0
                    pv = Rv[j - 1] if j else 0
                    nv = Rv[j + 1] if j + 1 < len(Rv) else 0
                    dv = d[v]
                    lu = load[ru]
                    lv = load[rv]
                    same = ru == rv
                    rem = d[pu][u] + du[nu] - d[pu][nu]   # gain of removing u
                    # Penalty terms written inline (no function call: this is
                    # the hottest loop of the whole GA). ex(x) = max(0, x - Q).
                    base = (lu - Q if lu > Q else 0) + (lv - Q if lv > Q else 0)
                    if same:
                        pen_move = 0
                    else:
                        a1 = lu - qu
                        b1 = lv + qu
                        pen_move = lam * ((a1 - Q if a1 > Q else 0)
                                          + (b1 - Q if b1 > Q else 0) - base)

                    # 1) relocate u right after v
                    if pu != v:
                        delta = dv[u] + du[nv] - dv[nv] - rem + pen_move
                        if delta < -1e-9:
                            Ru.pop(i)
                            jj = pos[v] - 1 if (same and i < j) else j
                            Rv.insert(jj + 1, u)
                            counter += 1
                            update(ru)
                            if not same:
                                update(rv)
                            improved = True
                            continue
                    # 2) relocate u right before v
                    if nu != v:
                        delta = d[pv][u] + du[v] - d[pv][v] - rem + pen_move
                        if delta < -1e-9:
                            Ru.pop(i)
                            jj = j - 1 if (same and i < j) else j
                            Rv.insert(jj, u)
                            counter += 1
                            update(ru)
                            if not same:
                                update(rv)
                            improved = True
                            continue
                    # 3) swap u and v (non-adjacent)
                    if nu != v and pu != v:
                        qv = q[v]
                        delta = (d[pu][v] + dv[nu] - rem - d[pu][nu]
                                 + d[pv][u] + du[nv] - d[pv][v] - dv[nv])
                        if not same:
                            a1 = lu - qu + qv
                            b1 = lv - qv + qu
                            delta += lam * ((a1 - Q if a1 > Q else 0)
                                            + (b1 - Q if b1 > Q else 0) - base)
                        if delta < -1e-9:
                            Ru[i] = v
                            Rv[j] = u
                            counter += 1
                            update(ru)
                            if not same:
                                update(rv)
                            improved = True
                            continue
                    if same:
                        # 4) 2-opt inside the route: reverse the part between
                        if i < j:
                            a, b, na, nb, ia, ib = u, v, nu, nv, i, j
                        else:
                            a, b, na, nb, ia, ib = v, u, nv, nu, j, i
                        delta = d[a][b] + d[na][nb] - d[a][na] - d[b][nb]
                        if delta < -1e-9:
                            Ru[ia + 1:ib + 1] = Ru[ia + 1:ib + 1][::-1]
                            counter += 1
                            update(ru)
                            improved = True
                        continue
                    # 5) 2-opt* (a): tails exchanged  u->nv , v->nu
                    pu_load = pre[ru][i]
                    pv_load = pre[rv][j]
                    la = pu_load + lv - pv_load
                    lb = pv_load + lu - pu_load
                    delta = (du[nv] + dv[nu] - du[nu] - dv[nv]
                             + lam * ((la - Q if la > Q else 0)
                                      + (lb - Q if lb > Q else 0) - base))
                    if delta < -1e-9:
                        A = Ru[:i + 1] + Rv[j + 1:]
                        B = Rv[:j + 1] + Ru[i + 1:]
                        routes[ru] = A
                        routes[rv] = B
                        counter += 1
                        update(ru)
                        update(rv)
                        improved = True
                        continue
                    # 6) 2-opt* (b): u->v and nu->nv (heads/tails reversed)
                    la = pu_load + pv_load
                    lb = lu - pu_load + lv - pv_load
                    delta = (du[v] + d[nu][nv] - du[nu] - dv[nv]
                             + lam * ((la - Q if la > Q else 0)
                                      + (lb - Q if lb > Q else 0) - base))
                    if delta < -1e-9:
                        A = Ru[:i + 1] + Rv[:j + 1][::-1]
                        B = Ru[i + 1:][::-1] + Rv[j + 1:]
                        routes[ru] = A
                        routes[rv] = B
                        counter += 1
                        update(ru)
                        update(rv)
                        improved = True
                        continue
                # 7) relocate u into an empty route (if one is available)
                ru = rid[u]
                if len(routes[ru]) > 1:
                    for re in range(R):
                        if not routes[re]:
                            Ru = routes[ru]
                            i = pos[u]
                            pu = Ru[i - 1] if i else 0
                            nu = Ru[i + 1] if i + 1 < len(Ru) else 0
                            lu = load[ru]
                            delta = (2 * du[0] - (d[pu][u] + du[nu] - d[pu][nu])
                                     + lam * (ex(lu - qu) - ex(lu) + ex(qu)))
                            if delta < -1e-9:
                                Ru.pop(i)
                                routes[re].append(u)
                                counter += 1
                                update(ru)
                                update(re)
                                improved = True
                            break
        out = [r for r in routes if r]
        overload = sum(ex(load[r]) for r in range(R))
        return out, total_cost(inst, out), overload


# ---------------------------------------------------------------- GA helpers

def routes_to_tour(routes) -> list[int]:
    """Giant tour = concatenation of the routes (depot visits removed)."""
    return [c for r in routes for c in r]


def sweep_tour(inst: Instance, start_angle: float, reverse: bool) -> list[int]:
    """Customers sorted by polar angle around the depot (sweep order)."""
    x0, y0 = inst.coords[0]
    ang = {}
    for i in range(1, inst.n + 1):
        a = math.atan2(inst.coords[i][1] - y0, inst.coords[i][0] - x0) - start_angle
        ang[i] = a % (2 * math.pi)
    t = sorted(ang, key=ang.get)
    return t[::-1] if reverse else t


def overload_of(inst: Instance, routes) -> int:
    q, Q = inst.q, inst.Q
    s = 0
    for r in routes:
        l = sum(q[c] for c in r)
        if l > Q:
            s += l - Q
    return s


def edge_set(routes, n1: int) -> set:
    """Undirected edges of a solution (depot included), encoded a*(n+1)+b."""
    E = set()
    for r in routes:
        prev = 0
        for c in r + [0]:
            a, b = (prev, c) if prev < c else (c, prev)
            E.add(a * n1 + b)
            prev = c
    return E


class Individual:
    __slots__ = ("tour", "routes", "dist", "over", "fit", "_edges")

    def __init__(self, tour, routes, dist, over, lam):
        self.tour = tour
        self.routes = routes
        self.dist = dist
        self.over = over
        self.fit = dist + lam * over
        self._edges = None

    @property
    def feasible(self):
        return self.over == 0

    def edges(self, n1):
        if self._edges is None:
            self._edges = edge_set(self.routes, n1)
        return self._edges


# ---------------------------------------------------------------- main solver

def solve(inst: Instance, time_limit: float, seed: int, params: dict | None = None,
          init_routes=None, max_generations: int | None = None) -> Result:
    """Run the (memetic) GA. Returns the best FEASIBLE solution found
    (<= K routes, every load <= Q) as a Result."""
    t0 = time.perf_counter()
    P = dict(DEFAULT_PARAMS)
    if params:
        P.update(params)
    rng = random.Random(seed)
    n, K, Q = inst.n, inst.K, inst.Q
    n1 = n + 1
    mu = P["pop_size"]
    lam_off = P["n_offspring"]
    max_load = P["max_load_factor"] * Q
    ls = LocalSearch(inst, P["granular"]) if P["memetic"] else None
    # Initial penalty (Vidal et al.): max distance / max demand, clamped.
    max_d = max(max(row) for row in inst.d)
    state = {"lam": max(0.1, min(1000.0, max_d / max(inst.q))),
             "feas_hist": []}

    best = {"routes": None, "cost": math.inf}
    history: list[tuple[float, float]] = []
    stats = {"ls_calls": 0, "repairs": 0, "rejected_duplicates": 0,
             "restarts": 0, "offspring": 0}

    def elapsed():
        return time.perf_counter() - t0

    def out_of_time():
        return elapsed() >= time_limit

    def record(ind):
        if ind.over == 0 and ind.dist < best["cost"] - 1e-9:
            best["cost"] = ind.dist
            best["routes"] = [list(r) for r in ind.routes]
            history.append((elapsed(), ind.dist))
            return True
        return False

    def decode(tour, force_ls=False):
        """Split (+ local search in memetic mode) -> Individual."""
        lam = state["lam"]
        cost, routes = split_limited(inst, tour, K, overload_penalty=lam, max_load=max_load)
        if routes is None:          # no <=K split even with 1.5Q: drop the load cap
            cost, routes = split_limited(inst, tour, K, overload_penalty=lam)
        if ls is not None and (force_ls or rng.random() < P["p_ls"]):
            stats["ls_calls"] += 1
            routes, dist, over = ls.run(routes, K, lam, rng)
            if over > 0 and rng.random() < P["p_repair"]:
                # Repair (Vidal et al.): rerun LS with a 10x (then 100x) penalty.
                stats["repairs"] += 1
                for mult in (10, 100):
                    routes2, dist2, over2 = ls.run(routes, K, lam * mult, rng)
                    if over2 == 0:
                        routes, dist, over = routes2, dist2, over2
                        break
            state["feas_hist"].append(over == 0)
            tour = routes_to_tour(routes)
            if over == 0:
                # Prins: re-split the concatenated routes; the exact limited
                # Split can only keep or improve the LS solution.
                c2, r2 = split(inst, tour, K)
                if len(r2) <= K and c2 < dist - 1e-9:
                    routes, dist = r2, c2
        else:
            over = overload_of(inst, routes)
            dist = total_cost(inst, routes)
            state["feas_hist"].append(over == 0)
        ind = Individual(tour, routes, dist, over, lam)
        record(ind)
        return ind

    def is_duplicate(ind, pool):
        g = P["min_gap"]
        f = ind.fit
        for o in pool:
            if abs(o.fit - f) < g:
                return True
        return False

    def random_individual():
        t = list(range(1, n + 1))
        rng.shuffle(t)
        return decode(t, force_ls=True)

    # -------- initial population
    pop: list[Individual] = []
    seeds = []
    if init_routes:
        seeds.append(routes_to_tour(init_routes))
    n_sweep = int(P["init_sweep_frac"] * mu)
    for _ in range(n_sweep):
        seeds.append(sweep_tour(inst, rng.uniform(0, 2 * math.pi), rng.random() < 0.5))
    attempts = 0
    while len(pop) < mu and attempts < 20 * mu:
        attempts += 1
        if seeds:
            ind = decode(seeds.pop(0), force_ls=True)
        else:
            ind = random_individual()
        if not is_duplicate(ind, pop):
            pop.append(ind)
        if out_of_time() and pop:
            break

    def tournament():
        k = P["tournament"]
        b = pop[rng.randrange(len(pop))]
        for _ in range(k - 1):
            c = pop[rng.randrange(len(pop))]
            if c.fit < b.fit:
                b = c
        return b

    diversity = []
    feas_rate = []
    gen = 0
    since_improve = 0
    while not out_of_time() and (max_generations is None or gen < max_generations):
        best_before = best["cost"]
        offspring: list[Individual] = []
        for _ in range(lam_off):
            if out_of_time():
                break
            p1 = tournament()
            p2 = tournament()
            if len(pop) > 1:
                tries = 0
                while p2 is p1 and tries < 5:
                    p2 = tournament()
                    tries += 1
            if rng.random() < P["p_cx"]:
                child = ox_crossover(p1.tour, p2.tour, rng)
            else:
                child = p1.tour[:]
            if rng.random() < P["p_mut"]:
                mutate(child, P["mutation"], rng)
            ind = decode(child)
            stats["offspring"] += 1
            if is_duplicate(ind, pop) or is_duplicate(ind, offspring):
                stats["rejected_duplicates"] += 1
                continue
            offspring.append(ind)
        if not offspring and out_of_time():
            break
        # ---- adaptive penalty: aim at target share of feasible children
        fh = state["feas_hist"][-lam_off:]
        if fh:
            rate = sum(fh) / len(fh)
            feas_rate.append(rate)
            if rate < P["target_feasible"] - 0.05:
                state["lam"] = min(state["lam"] * 1.2, 1e5)
            elif rate > P["target_feasible"] + 0.05:
                state["lam"] = max(state["lam"] * 0.85, 0.1)
        state["feas_hist"] = state["feas_hist"][-200:]
        lam = state["lam"]
        for ind in pop:                      # refresh fitness with new lambda
            ind.fit = ind.dist + lam * ind.over
        for ind in offspring:
            ind.fit = ind.dist + lam * ind.over
        # ---- replacement
        if P["replacement"] == "generational" and len(offspring) >= mu - P["elite"]:
            pop.sort(key=lambda x: x.fit)
            offspring.sort(key=lambda x: x.fit)
            new = pop[:P["elite"]]
            for o in offspring:
                if len(new) >= mu:
                    break
                if not is_duplicate(o, new):
                    new.append(o)
            pop = new
        else:                                # (mu + lambda) truncation: elitist
            merged = sorted(pop + offspring, key=lambda x: x.fit)
            new = []
            for o in merged:
                if len(new) >= mu:
                    break
                if not is_duplicate(o, new):
                    new.append(o)
            pop = new
        gen += 1
        # ---- diversity: mean pairwise edge (broken-pairs) distance
        if P["diversity"] and len(pop) > 1:
            tot, cnt = 0.0, 0
            for a in range(len(pop)):
                Ea = pop[a].edges(n1)
                for b in range(a + 1, len(pop)):
                    Eb = pop[b].edges(n1)
                    tot += 1.0 - len(Ea & Eb) / max(len(Ea), len(Eb))
                    cnt += 1
            diversity.append(tot / cnt)
        # ---- partial restart after stagnation (Prins 2004)
        if best["cost"] < best_before - 1e-9:
            since_improve = 0
        else:
            since_improve += 1
        if P["restart_after"] and since_improve >= P["restart_after"]:
            stats["restarts"] += 1
            since_improve = 0
            pop.sort(key=lambda x: x.fit)
            pop = pop[:P["elite"]]
            tries = 0
            while len(pop) < mu and not out_of_time() and tries < 20 * mu:
                tries += 1
                ind = random_individual()
                if not is_duplicate(ind, pop):
                    pop.append(ind)

    # -------- final answer: best feasible ever seen
    if best["routes"] is None:
        # Last resort: exact (hard) Split of every individual, then init_routes.
        for ind in sorted(pop, key=lambda x: x.fit):
            c, r = split(inst, ind.tour, K)
            if len(r) <= K:
                best["routes"], best["cost"] = r, c
                history.append((elapsed(), c))
                break
    if best["routes"] is None and init_routes and len([r for r in init_routes if r]) <= K \
            and overload_of(inst, init_routes) == 0:
        best["routes"] = [list(r) for r in init_routes if r]
        best["cost"] = total_cost(inst, best["routes"])
    if best["routes"] is None:   # infeasible fallback (checker will report it)
        b = min(pop, key=lambda x: x.fit)
        best["routes"], best["cost"] = b.routes, b.dist
    el = elapsed()
    return Result(
        routes=best["routes"],
        cost=total_cost(inst, best["routes"]),
        history=history,
        iterations=gen,
        elapsed=el,
        extra={
            "params": P,
            "seed": seed,
            "generations_per_s": gen / el if el > 0 else 0.0,
            "final_penalty": state["lam"],
            "diversity": diversity,
            "feasible_rate": feas_rate,
            **stats,
        },
    )
