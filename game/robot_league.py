# -*- coding: utf-8 -*-
"""Liga do modo robos: 6 times, ida e volta (10 rodadas), oponentes gerados.

Modulo puro: sem pygame e sem random global (RNG sempre injetado).
league = {"tier","teams":[{name,color,ovr,seed}],"fixtures":[[[h,a],..],..],
          "round":int,"results":[[round,h,a,hg,ag],..]}. teams[0] e o usuario.
"""
import math

import garage as gm
import robots

N_TEAMS = 6
ROUNDS = 2 * (N_TEAMS - 1)
USER = 0
SIM_K = 1.85           # calibrado contra o motor (tests/calib_robots.py): +-10 pts de V em -20..+20
GOALS_AVG = 1.34       # gols medios por time com forcas iguais (~2.7 por jogo, como o motor)
SIM_SLOPE = 0.04       # sensibilidade do lambda por ponto de rating (x SIM_K)
OFFSET_RANGE = 6
PRIZE_BASE = (250, 150, 80, 30)      # 1o, 2o, 3o, demais
ADVANCE_POS = 3                      # precisa de 3o ou melhor
ROLES = gm.LINEUP_SLOTS

TEAM_NAMES = (
    "Parafusos FC", "Sucata United", "Clube dos Cabos", "Fusíveis do Norte",
    "Engrenagem Atlética", "Real Capacitor", "Curto-Circuito SC", "Os Rolimãs",
    "Atlético Bateria", "Dínamo Pampulha", "Voltagem EC", "Bobinas da Serra",
    "Lataria Jr.", "Transistor FC", "Parachoque Rovers", "Ferro-Velho City",
)
TEAM_COLORS = (
    (230, 60, 60), (255, 140, 40), (255, 215, 60), (110, 220, 90),
    (30, 190, 150), (60, 120, 255), (140, 90, 255), (230, 90, 220),
    (240, 240, 240), (255, 110, 150), (120, 200, 255), (200, 255, 80),
    (255, 170, 90), (170, 120, 255), (90, 230, 200), (220, 70, 120),
)


# --- oponentes ----------------------------------------------------------------------
def opponent_team(name, color, ovr, seed):
    """Time oponente independente da liga: {name,color,ovr,seed,squad:[5 dicts]}."""
    squad = []
    for i, role in enumerate(ROLES):
        ch = robots.ROLE_CHASSIS[role]
        squad.append({"name": "%s %d" % (name.split()[0][:8], i + 1), "role": role,
                      "chassis": ch, "pid": None, "paint": None,
                      "attrs": robots.from_overall(ovr, role, ch, seed=seed * 10 + i)})
    return {"name": name, "color": tuple(color), "ovr": ovr, "seed": seed, "squad": squad}


def match_cfg(team):
    """Formato de Game.start_robot_match: {name,color,squad:[5 dicts {name,attrs,chassis,pid,paint}]}."""
    t = team if "squad" in team else opponent_team(team["name"], team["color"],
                                                   team["ovr"], team["seed"])
    return {"name": t["name"], "color": tuple(t["color"]),
            "squad": [{"name": e["name"], "attrs": dict(e["attrs"]), "chassis": e["chassis"],
                       "pid": None, "paint": e["paint"]} for e in t["squad"]]}


# --- calendario ---------------------------------------------------------------------
def make_fixtures(members, rng):
    """Round-robin ida e volta (mesma logica de Career.make_fixtures, com RNG injetado)."""
    teams = list(members)
    rng.shuffle(teams)
    n = len(teams)
    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = teams[i], teams[n - 1 - i]
            pairs.append((a, b) if (r + i) % 2 == 0 else (b, a))
        rounds.append(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    return rounds + [[(b, a) for a, b in rd] for rd in rounds]


def new_league(garage, tier, rng):
    """Cria a liga do tier (5 oponentes distintos) e guarda em garage.league."""
    tier = gm.clamp(tier, 0, len(gm.TIER_OVR) - 1)
    names = rng.sample(TEAM_NAMES, N_TEAMS - 1)
    colors = rng.sample(TEAM_COLORS, N_TEAMS - 1)
    teams = [{"name": garage.team["name"], "color": list(garage.team["color"]),
              "ovr": 0, "seed": 0}]
    for nm, col in zip(names, colors):
        teams.append({"name": nm, "color": list(col),
                      "ovr": gm.TIER_OVR[tier] + rng.randint(-OFFSET_RANGE, OFFSET_RANGE),
                      "seed": rng.randrange(1, 100000)})
    fx = make_fixtures(range(N_TEAMS), rng)
    league = {"tier": tier, "teams": teams,
              "fixtures": [[[h, a] for h, a in rd] for rd in fx],
              "round": 0, "results": []}
    garage.league = league
    return league


def is_finished(league):
    return league["round"] >= ROUNDS


def next_fixture(league):
    """(rodada, casa, fora) do proximo jogo do usuario; None se a liga acabou."""
    if is_finished(league):
        return None
    for h, a in league["fixtures"][league["round"]]:
        if USER in (h, a):
            return league["round"], h, a
    return None


def team_strength(league, idx, garage):
    """Rating usado pelo Poisson: usuario = team_rating, demais = ovr."""
    if idx == USER:
        return garage.rating()
    return float(league["teams"][idx]["ovr"])


def opponent_of(league, fixture):
    _r, h, a = fixture
    idx = a if h == USER else h
    t = league["teams"][idx]
    return idx, opponent_team(t["name"], t["color"], t["ovr"], t["seed"])


# --- simulacao ----------------------------------------------------------------------
def poisson(lam, rng):
    """Amostra de Poisson (Knuth) com o RNG injetado."""
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def quick_sim(rating_h, rating_a, rng, k=None):
    """Placar (gols_casa, gols_fora) por Poisson; lambda ~ exp(+-K*slope*diff/2)."""
    k = SIM_K if k is None else k
    d = (rating_h - rating_a) * SIM_SLOPE * k / 2.0
    return poisson(GOALS_AVG * math.exp(d), rng), poisson(GOALS_AVG * math.exp(-d), rng)


def record(league, h, a, hg, ag):
    """Registra um resultado na rodada atual."""
    league["results"].append([league["round"], h, a, int(hg), int(ag)])


def _recorded(league, h, a):
    r = league["round"]
    return any(x[0] == r and x[1] == h and x[2] == a for x in league["results"])


def advance_round(league, garage, rng):
    """Simula (Poisson) os jogos da rodada atual ainda sem resultado e avanca a rodada.
    O jogo do usuario deve ter sido registrado antes (senao tambem e simulado)."""
    if is_finished(league):
        return False
    for h, a in league["fixtures"][league["round"]]:
        if not _recorded(league, h, a):
            hg, ag = quick_sim(team_strength(league, h, garage),
                               team_strength(league, a, garage), rng)
            record(league, h, a, hg, ag)
    league["round"] += 1
    return True


def table(league):
    """Classificacao ordenada (pts, saldo, gols pro): lista de dicts."""
    rows = [{"idx": i, "name": t["name"], "color": t["color"], "p": 0, "w": 0, "d": 0,
             "l": 0, "gf": 0, "ga": 0, "gd": 0, "pts": 0}
            for i, t in enumerate(league["teams"])]
    for _r, h, a, hg, ag in league["results"]:
        for idx, gf, ga in ((h, hg, ag), (a, ag, hg)):
            row = rows[idx]
            row["p"] += 1
            row["gf"] += gf
            row["ga"] += ga
            if gf > ga:
                row["w"] += 1
                row["pts"] += 3
            elif gf == ga:
                row["d"] += 1
                row["pts"] += 1
            else:
                row["l"] += 1
    for row in rows:
        row["gd"] = row["gf"] - row["ga"]
    rows.sort(key=lambda r: (-r["pts"], -r["gd"], -r["gf"], r["idx"]))
    return rows


def user_position(league):
    """Posicao (1..6) do usuario na tabela."""
    return next(i for i, r in enumerate(table(league)) if r["idx"] == USER) + 1


def finish_league(garage, rng):
    """Encerra a liga: premio por posicao (x TIER_MUL), desbloqueio de chassis do tier,
    tier_done (so com 3o ou melhor), limpa a liga e repoe a loja do proximo tier.

    Devolve {"pos","prize","unlocked":[novos],"advanced":bool,"tier","next_tier"}.
    """
    lg = garage.league
    if lg is None or not is_finished(lg):
        return None
    tier = lg["tier"]
    pos = user_position(lg)
    prize = int(round(PRIZE_BASE[min(pos, len(PRIZE_BASE)) - 1] * gm.TIER_MUL[tier]))
    garage.scrap += prize
    if pos == 1:
        garage.stats["titles"] += 1
    new = [c for c in gm.CHASSIS_UNLOCK.get(tier, ()) if c not in garage.unlocked]
    garage.unlocked.extend(new)
    advanced = pos <= ADVANCE_POS
    if advanced:
        garage.tier_done = max(garage.tier_done, tier)
    garage.league = None
    nxt = garage.tier()
    garage.refresh_shop(nxt, rng)
    return {"pos": pos, "prize": prize, "unlocked": new, "advanced": advanced,
            "tier": tier, "next_tier": nxt}
