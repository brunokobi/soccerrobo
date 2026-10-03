"""Testes de garage.py / parts.py / robot_league.py (passos 4, 6 e 7). Sem pygame.

Rodar da raiz: .venv/bin/python tests/test_garage.py [nome_do_teste ...]
Alvos numericos sao SOFT: imprime "[ALVO OK]" / "[ALVO NAO ATINGIDO]" (calibragem = passo 8).
"""
import copy
import os
import random
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import garage as gm  # noqa: E402
import parts  # noqa: E402
import robot_league as rl  # noqa: E402
import robots  # noqa: E402

PASS, FAIL = [], []


def soft(name, value, target, ok):
    print("%-44s %s  (alvo: %s)  %s" % (name, value, target, "[ALVO OK]" if ok else "[ALVO NAO ATINGIDO]"))


def fresh(seed=1):
    return gm.new_game(random.Random(seed))


def bare_robot(**kw):
    g = fresh()
    r = copy.deepcopy(g.robots[2])
    r["slots"] = {s: None for s in parts.SLOTS}
    r.update(kw)
    return r


# ----------------------------------------------------------------- catalogo
def test_catalog():
    assert len(parts.PARTS) == 14
    for slot in parts.SLOTS:
        assert len(parts.models_for_slot(slot)) == 2, slot
    for m, d in parts.PARTS.items():
        assert d["slot"] in parts.SLOTS, m
        assert d["w"] and all(a in robots.ATTRS for a in d["w"]), m
        prim = max(d["w"].values())
        # heat so em agressivos (peso primario > 1.0)
        assert (d["heat"] > 0) == (prim > 1.0), m
    assert len(parts.RARITIES) == 4
    assert parts.PRICE == (60, 220, 700, 2200) and parts.POWER == (4, 8, 12, 19)
    for m in parts.PARTS:
        for rar in range(4):
            for lvl in range(parts.MAX_UP):
                b0, b1 = parts.part_bonus(m, rar, lvl), parts.part_bonus(m, rar, lvl + 1)
                assert all(b1[a] >= b0[a] for a in b0)
                assert parts.part_heat(m, rar, lvl + 1) >= parts.part_heat(m, rar, lvl)
        for lvl in range(parts.MAX_UP + 1):
            for rar in range(3):
                lo, hi = parts.part_bonus(m, rar, lvl), parts.part_bonus(m, rar + 1, lvl)
                assert all(hi[a] >= lo[a] for a in lo)
    assert parts.part_bonus("Turbina", 1, 0) == {"vel": 10, "ace": 5}
    assert parts.part_heat("Motor Escovado", 3, 5) == 0
    assert abs(parts.part_heat("Turbina", 0, 0) - 1.4) < 1e-9
    assert parts.upgrade_cost(1, 0) == 66 and parts.upgrade_cost(1, 4) == 330
    assert parts.upgrade_cost(0, parts.MAX_UP) is None
    assert parts.sell_price({"rar": 2}) == 350
    assert parts.part_name({"model": "Turbina", "rar": 2, "lvl": 3}) == "Turbina Épica +3"
    parts.part_name({"model": "Chip Neural", "rar": 3, "lvl": 0}).encode("latin-1")


# ----------------------------------------------------------------- atributos efetivos
def test_effective_attrs():
    r = bare_robot()
    base = copy.deepcopy(r["base"])
    snap = copy.deepcopy(r)
    eff = gm.effective_attrs(r, {})
    assert list(eff) == list(robots.ATTRS) and eff == base
    assert r == snap, "nao deve mutar"
    r["level"] = 6
    eff = gm.effective_attrs(r, {})
    assert all(eff[a] == int(round(base[a] + 5 * gm.LEVEL_STEP)) for a in base if base[a] + 5 * gm.LEVEL_STEP <= 99)
    r["level"] = 1
    # clamp
    r["base"] = {a: 98 for a in robots.ATTRS}
    r["level"] = 10
    assert all(v == 99 for v in gm.effective_attrs(r, {}).values())
    r["base"] = {a: 21 for a in robots.ATTRS}
    r["level"], r["oc"] = 1, 2
    assert gm.effective_attrs(r, {})["bat"] == 20
    # pecas, oc e calor
    r = bare_robot()
    r["base"] = {a: 50 for a in robots.ATTRS}
    pcs = {1: {"id": 1, "model": "Turbina", "rar": 1, "lvl": 0},
           2: {"id": 2, "model": "Célula Longa", "rar": 1, "lvl": 0}}
    r["slots"]["motor"], r["slots"]["bateria"] = 1, 2
    e0 = gm.effective_attrs(r, pcs)
    assert e0["vel"] == 60 and e0["ace"] == 55
    assert e0["bat"] == round(50 + 8 - 0.35 * 8)
    r["oc"] = 2
    e2 = gm.effective_attrs(r, pcs)
    assert e2["vel"] > e0["vel"] and e2["ace"] > e0["ace"]
    assert e2["bat"] == round(50 + 8 - 0.35 * 8 - gm.OC_BAT[2]) and e2["bat"] < e0["bat"]
    # peca no slot errado / inexistente e ignorada
    r["slots"]["chip"] = 1
    r["slots"]["sensor"] = 999
    assert gm.effective_attrs(r, pcs) == e2
    # consumivel pelo motor
    for t in (robots.TUNING, robots.TUNING_ROBOTS):
        f = robots.factors(e2, t)
        assert f.speed > 0
    # match_entry
    g = fresh()
    ent = gm.match_entry(g.robots[0], g.pieces_by_id())
    assert set(ent) == {"name", "attrs", "chassis", "pid", "paint"}
    assert ent["pid"] == g.robots[0]["id"] and list(ent["attrs"]) == list(robots.ATTRS)
    assert ent["attrs"] == g.attrs_of(g.robots[0])
    assert len(g.match_cfg()["squad"]) == 5
    assert gm.team_rating([], {}) == 0
    rr = g.rating()
    assert 40 <= rr <= 52, rr


# ----------------------------------------------------------------- new_game
def test_new_game():
    g = fresh()
    assert g.scrap == 150 and len(g.robots) == 5 and len(g.inventory) == 5
    assert [r["role"] for r in g.robots] == ["GK", "DEF", "MID", "MID", "ATT"]
    assert all(r["chassis"] == "Disco" and r["level"] == 1 for r in g.robots)
    assert all(p["rar"] == 0 for p in g.inventory)
    assert g.lineup == [r["id"] for r in g.robots] and g.unlocked == ["Disco"]
    assert len({r["name"] for r in g.robots}) == 5
    stock = g.shop["stock"]
    assert [p["rar"] for p in stock].count(0) == 6 and [p["rar"] for p in stock].count(1) == 1
    ids = [r["id"] for r in g.robots] + [p["id"] for p in g.inventory] + [p["id"] for p in stock]
    assert len(set(ids)) == len(ids) and g.next_id > max(ids)
    d = g.to_dict()
    assert d["v"] == 1 and all(f in d for f in gm.FIELDS)
    d["scrap"] = 0
    assert g.scrap == 150, "to_dict deve copiar"
    # deterministico
    assert fresh(3).to_dict() == fresh(3).to_dict()


# ----------------------------------------------------------------- operacoes
def test_equip_upgrade_buy_sell():
    g = fresh()
    r = g.robots[0]
    free = parts_free = g.free_pieces()
    assert free == []                      # tudo equipado no kit inicial
    pid = g.robots[1]["slots"]["bateria"]
    ok, msg = g.equip(r["id"], pid)
    assert not ok and "já equipada" in msg
    assert not g.equip(999, pid)[0] and not g.equip(r["id"], 999)[0]
    assert g.unequip(g.robots[1]["id"], "bateria")[0]
    assert not g.unequip(g.robots[1]["id"], "bateria")[0]       # vazio
    assert not g.unequip(g.robots[1]["id"], "xyz")[0]
    ok, msg = g.equip(r["id"], pid, slot="motor")
    assert not ok and "slot" in msg.lower()
    ok, _ = g.equip(r["id"], pid, slot="bateria")
    assert ok and r["slots"]["bateria"] == pid
    # substituicao libera a antiga
    new = g.new_piece("Célula Rápida", 0)
    g.inventory.append(new)
    assert g.equip(r["id"], new["id"])[0] and r["slots"]["bateria"] == new["id"]
    assert pid in [p["id"] for p in g.free_pieces("bateria")]
    # venda
    s0 = g.scrap
    assert not g.sell_part(new["id"])[0]                         # equipada
    assert g.sell_part(pid)[0] and g.scrap == s0 + 30 and g.piece(pid) is None
    assert not g.sell_part(pid)[0]
    # upgrade
    p = g.piece(new["id"])
    g.scrap = 1000
    cost = parts.upgrade_cost(0, 0)
    ok, _ = g.upgrade(p["id"])
    assert ok and p["lvl"] == 1 and g.scrap == 1000 - cost
    for _ in range(4):
        assert g.upgrade(p["id"])[0]
    assert p["lvl"] == parts.MAX_UP
    s = g.scrap
    ok, msg = g.upgrade(p["id"])
    assert not ok and g.scrap == s and p["lvl"] == parts.MAX_UP
    g.scrap = 0
    q = g.new_piece("Turbina", 1)
    g.inventory.append(q)
    assert not g.upgrade(q["id"])[0] and q["lvl"] == 0
    assert not g.upgrade(12345)[0]
    # compra
    stock = g.shop["stock"]
    rare = next(x for x in stock if x["rar"] == 1)
    assert not g.buy_part(rare["id"])[0] and rare in stock        # sem sucata
    g.scrap = 220
    n = len(g.inventory)
    assert g.buy_part(rare["id"])[0] and g.scrap == 0 and len(g.inventory) == n + 1
    assert rare not in g.shop["stock"] and not g.buy_part(rare["id"])[0]
    g.scrap = 10**6
    g.inventory.extend({"id": 10**6 + i, "model": "Turbina", "rar": 0, "lvl": 0}
                       for i in range(gm.MAX_INVENTORY))
    assert not g.buy_part(g.shop["stock"][0]["id"])[0]


def test_robot_ops():
    g = fresh()
    r = g.robots[0]
    assert g.rename(r["id"], "  Zeca  ")[0] and r["name"] == "Zeca"
    assert not g.rename(r["id"], "")[0] and not g.rename(r["id"], "x" * 13)[0]
    assert not g.rename(r["id"], "日本")[0] and not g.rename(r["id"], "a\nb")[0]
    assert not g.rename(99, "ok")[0]
    assert g.set_paint(r["id"], (1, 2, 3))[0] and r["paint"] == [1, 2, 3]
    for bad in ((1, 2), (1, 2, 3, 4), (256, 0, 0), (-1, 0, 0), ("a", 0, 0), None):
        assert not g.set_paint(r["id"], bad)[0], bad
    assert g.set_oc(r["id"], 2)[0] and r["oc"] == 2 and not g.set_oc(r["id"], 3)[0]
    assert "bateria" in g.set_oc(r["id"], 1)[1]
    # lineup
    a, b = g.lineup[0], g.lineup[1]
    assert g.swap_lineup(0, b)[0] and g.lineup[:2] == [b, a]
    assert not g.swap_lineup(0, b)[0] and not g.swap_lineup(9, b)[0] and not g.swap_lineup(0, 99)[0]
    g.scrap = 10**5
    g.unlocked.append("Tanque")
    assert not g.buy_robot("Velocista")[0]                       # bloqueado
    s = g.scrap
    ok, _ = g.buy_robot("Tanque", rng=random.Random(1))
    assert ok and len(g.robots) == 6 and g.scrap == s - 150
    nr = g.robots[-1]
    assert nr["role"] == "DEF" and nr["level"] == 1 and nr["id"] not in g.lineup
    assert g.swap_lineup(4, nr["id"])[0] and nr["id"] in g.lineup
    g.buy_robot("Tanque"), g.buy_robot("Tanque")
    assert len(g.robots) == 8 and not g.buy_robot("Tanque")[0]
    g2 = fresh()
    g2.scrap = 10
    assert not g2.buy_robot("Disco")[0]
    # auto_lineup: 5 distintos, papel respeitado entre iguais
    g.auto_lineup()
    assert len(set(g.lineup)) == 5 and all(g.robot(i) for i in g.lineup)
    # robo muito forte entra
    big = g.robots[-1]
    big["base"] = {k: 90 for k in robots.ATTRS}
    g.auto_lineup()
    assert big["id"] in g.lineup
    # loja por tier
    rng = random.Random(5)
    n_ep = n_lg = 0
    for _ in range(200):
        st = g.refresh_shop(0, rng)
        assert all(p["rar"] < 2 for p in st)
        st = g.refresh_shop(3, rng)
        assert [p["rar"] for p in st].count(0) == 6 and [p["rar"] for p in st].count(1) == 1
        n_ep += any(p["rar"] == 2 for p in st)
        n_lg += any(p["rar"] == 3 for p in st)
        st = g.refresh_shop(1, rng)
        assert all(p["rar"] < 3 for p in st)
    assert 30 <= n_ep <= 70 and 5 <= n_lg <= 40, (n_ep, n_lg)


# ----------------------------------------------------------------- XP
def test_xp():
    needs = [gm.xp_need(l) for l in range(1, gm.MAX_LEVEL)]
    assert needs[:4] == [40, 70, 110, 160] and needs[-1] == 560
    assert all(b > a for a, b in zip(needs, needs[1:]))
    assert sum(needs) == 2280
    r = bare_robot(level=1, xp=0)
    assert gm.xp_to_next(r) == 40
    assert gm.add_xp(r, 39) == 0 and r["level"] == 1 and gm.xp_to_next(r) == 1
    assert gm.add_xp(r, 1) == 1 and r["level"] == 2 and r["xp"] == 0
    r = bare_robot(level=1, xp=0)
    assert gm.add_xp(r, 40 + 70 + 110 + 5) == 3 and r["level"] == 4 and r["xp"] == 5
    r = bare_robot(level=1, xp=0)
    assert gm.add_xp(r, 2279) == 8 and r["level"] == 9
    assert gm.add_xp(r, 1) == 1 and r["level"] == 10 and gm.xp_to_next(r) == 0
    assert gm.add_xp(r, 10**6) == 0 and r["level"] == 10 and r["xp"] == 0
    r = bare_robot(level=1, xp=0)
    assert gm.add_xp(r, 10**6) == 9 and r["level"] == 10
    assert gm.add_xp(bare_robot(level=1, xp=0), -5) == 0


def test_match_rewards():
    g = fresh()
    pid0 = g.lineup[0]
    res = gm.match_rewards(g, 3, 1, [pid0, pid0, g.lineup[4], None, 777], 0, random.Random(0))
    assert res["result"] == "w" and res["scrap"] == 50 + 15
    assert g.scrap == 150 + 65 and g.stats["played"] == 1 and g.stats["w"] == 1
    assert res["xp"][pid0] == 20 + 15 + 20 and res["xp"][g.lineup[1]] == 35
    assert g.robot(pid0)["level"] == 2 and res["levels"][pid0] == 1
    g = fresh()
    g.unlocked.append("Tanque")
    g.scrap = 10**5
    g.buy_robot("Tanque")
    bench = g.robots[-1]
    res = gm.match_rewards(g, 0, 0, [], 2, random.Random(0))
    assert res["result"] == "d" and res["scrap"] == int(round(30 * 2.2))
    assert res["xp"][bench["id"]] == int((20 + 7) * 0.3) and res["drop"] is None
    res = gm.match_rewards(g, 0, 2, [], 3, random.Random(0))
    assert res["result"] == "l" and res["scrap"] == int(round(15 * 3.2)) and g.stats["l"] == 1
    res = gm.match_rewards(g, 9, 0, [], 0, random.Random(0))
    assert res["scrap"] == 50 + 25                                # teto de 5 gols
    # drop ~20% so em vitorias
    rng, drops, n0 = random.Random(7), 0, len(g.inventory)
    for _ in range(500):
        drops += gm.match_rewards(g, 1, 0, [], 0, rng)["drop"] is not None
    assert 60 <= drops <= 140 and len(g.inventory) == n0 + drops
    assert all(p["rar"] == 0 for p in g.inventory[n0:])
    # puro: mesmos inputs + seed -> mesmo resultado e mesmo estado
    outs = []
    for _ in range(2):
        gg = fresh(4)
        rng = random.Random(99)
        rs = [gm.match_rewards(gg, i % 4, 1, [gg.lineup[i % 5]], i % 4, rng) for i in range(30)]
        outs.append((rs, gg.to_dict()))
    assert outs[0] == outs[1]


# ----------------------------------------------------------------- economia gulosa
def _econ_run(seed):
    """Guloso: compra 2 Comuns assim que possivel, depois junta para a 1a Rara.
    Devolve (partidas ate a 1a Comum, partidas ate a 1a Rara)."""
    rng = random.Random(seed)
    g = gm.new_game(rng)
    first_common = first_rare = None
    commons = 0
    for n in range(40):
        # compra antes da partida n (n partidas jogadas)
        st = list(g.shop["stock"])
        if commons < 2:
            c = next((p for p in st if p["rar"] == 0 and g.scrap >= parts.PRICE[0]), None)
            if c and g.buy_part(c["id"])[0]:
                commons += 1
                if first_common is None:
                    first_common = n
                _equip_any(g, c)
        elif first_rare is None:
            c = next((p for p in st if p["rar"] == 1), None)
            if c and g.buy_part(c["id"])[0]:
                first_rare = n
                _equip_any(g, c)
                break
        opp = 42 + rng.randint(-6, 6)
        hg, ag = rl.quick_sim(g.rating(), opp, rng)
        scorers = [rng.choice(g.lineup) for _ in range(hg)]
        gm.match_rewards(g, hg, ag, scorers, 0, rng)
        g.refresh_shop(0, rng)
    return first_common, first_rare


def _equip_any(g, piece):
    slot = parts.part_slot(piece)
    for r in g.lineup_robots():
        if r["slots"][slot] is None:
            g.equip(r["id"], piece["id"])
            return


def test_economy_greedy():
    runs = [_econ_run(s) for s in range(60)]
    commons = [c for c, _r in runs]
    rares = [r for _c, r in runs]
    assert None not in commons and None not in rares
    assert statistics.median(commons) <= 2 and max(commons) <= 2
    med = statistics.median(rares)
    assert med <= 8 and max(rares) <= 12, (med, max(rares))
    soft("1a Comum (partidas, mediana)", statistics.median(commons), "<=2",
         statistics.median(commons) <= 2)
    soft("1a Rara (partidas, mediana)", "%s (media %.1f, max %d)" % (med, statistics.mean(rares),
                                                                     max(rares)),
         "4-6 soft / <=8 duro", 4 <= med <= 6)


# ----------------------------------------------------------------- liga
def test_fixtures_and_opponents():
    rng = random.Random(3)
    fx = rl.make_fixtures(range(6), rng)
    assert len(fx) == 10 and all(len(rd) == 3 for rd in fx)
    seen = {}
    for rd in fx:
        assert sorted(x for pr in rd for x in pr) == list(range(6))   # cada time 1x por rodada
        for h, a in rd:
            seen[(h, a)] = seen.get((h, a), 0) + 1
    assert len(seen) == 30 and set(seen.values()) == {1}              # todos os mandos
    t1 = rl.opponent_team("Parafusos FC", (230, 60, 60), 50, 123)
    t2 = rl.opponent_team("Parafusos FC", (230, 60, 60), 50, 123)
    assert t1 == t2 and len(t1["squad"]) == 5
    assert [e["role"] for e in t1["squad"]] == ["GK", "DEF", "MID", "MID", "ATT"]
    cfg = rl.match_cfg({"name": "X", "color": [1, 2, 3], "ovr": 50, "seed": 9})
    assert len(cfg["squad"]) == 5 and cfg["name"] == "X"
    for i, (e, role) in enumerate(zip(cfg["squad"], gm.LINEUP_SLOTS)):
        ch = robots.ROLE_CHASSIS[role]
        assert e["chassis"] == ch and e["pid"] is None
        assert e["attrs"] == robots.from_overall(50, role, ch, seed=9 * 10 + i)
        assert list(e["attrs"]) == list(robots.ATTRS)
    assert rl.match_cfg(t1)["squad"][0]["attrs"] == t1["squad"][0]["attrs"]
    assert len(set(rl.TEAM_NAMES)) == len(rl.TEAM_NAMES) >= 16
    assert all(len(n) <= gm.NAME_MAX_TEAM + 4 for n in rl.TEAM_NAMES)
    for n in rl.TEAM_NAMES:
        n.encode("latin-1")


def test_quick_sim():
    rng = random.Random(1)
    n = 4000
    eq = [rl.quick_sim(50, 50, rng) for _ in range(n)]
    mg = sum(h + a for h, a in eq) / (2 * n)
    assert abs(mg - rl.GOALS_AVG) < 0.1, mg
    wins = sum(h > a for h, a in (rl.quick_sim(60, 50, rng) for _ in range(n))) / n
    loses = sum(h < a for h, a in (rl.quick_sim(60, 50, rng) for _ in range(n))) / n
    assert wins > loses + 0.05
    assert rl.quick_sim(55, 50, random.Random(5)) == rl.quick_sim(55, 50, random.Random(5))


def play_league(g, rng, tier):
    lg = rl.new_league(g, tier, rng)
    while not rl.is_finished(lg):
        fx = rl.next_fixture(lg)
        assert fx is not None
        r, h, a = fx
        assert r == lg["round"] and rl.USER in (h, a)
        hg, ag = rl.quick_sim(rl.team_strength(lg, h, g), rl.team_strength(lg, a, g), rng)
        rl.record(lg, h, a, hg, ag)
        my, op = (hg, ag) if h == rl.USER else (ag, hg)
        gm.match_rewards(g, my, op, [], tier, rng)
        assert rl.advance_round(lg, g, rng)
    return lg


def test_league_full():
    rng = random.Random(11)
    g = fresh(2)
    lg = play_league(g, rng, 0)
    assert lg["round"] == 10 and len(lg["results"]) == 30
    assert rl.next_fixture(lg) is None and not rl.advance_round(lg, g, rng)
    tb = rl.table(lg)
    assert len(tb) == 6
    for row in tb:
        assert row["p"] == 10 and row["w"] + row["d"] + row["l"] == 10
        assert row["pts"] == 3 * row["w"] + row["d"] and row["gd"] == row["gf"] - row["ga"]
    assert sum(r["gf"] for r in tb) == sum(r["ga"] for r in tb)
    assert sum(r["w"] for r in tb) == sum(r["l"] for r in tb)
    keys = [(-r["pts"], -r["gd"], -r["gf"]) for r in tb]
    assert keys == sorted(keys)
    assert g.stats["played"] == 10 and sum(g.stats[k] for k in "wdl") == 10
    # nomes distintos, 5 oponentes na faixa do tier
    names = [t["name"] for t in lg["teams"]]
    assert len(set(names)) == 6
    assert all(36 <= t["ovr"] <= 48 for t in lg["teams"][1:])
    pos = rl.user_position(lg)
    scrap0 = g.scrap
    info = rl.finish_league(g, rng)
    assert info["pos"] == pos and info["tier"] == 0
    assert info["prize"] == (250, 150, 80, 30, 30, 30)[pos - 1]
    assert g.scrap == scrap0 + info["prize"] and g.league is None
    assert "Tanque" in g.unlocked and info["unlocked"] == ["Tanque"]
    assert info["advanced"] == (pos <= 3)
    assert g.tier_done == (0 if pos <= 3 else -1)
    assert info["next_tier"] == g.tier() == (1 if pos <= 3 else 0)
    assert g.shop["stock"] and g.stats["titles"] == (1 if pos == 1 else 0)
    assert rl.finish_league(g, rng) is None


def test_league_progression():
    rng = random.Random(21)
    g = fresh(5)
    # time dominante: sempre 1o -> desbloqueios e tiers conforme CHASSIS_UNLOCK
    for rb in g.robots:
        rb["base"] = {a: 99 for a in robots.ATTRS}
    expected = []
    for tier in range(4):
        assert g.tier() == tier
        lg = play_league(g, rng, tier)
        assert rl.user_position(lg) == 1
        info = rl.finish_league(g, rng)
        assert info["advanced"] and g.tier_done == tier
        expected += list(gm.CHASSIS_UNLOCK[tier])
        assert g.unlocked == ["Disco"] + expected, (tier, g.unlocked)
        assert info["prize"] == int(round(250 * gm.TIER_MUL[tier]))
    assert set(g.unlocked) == {"Disco", "Tanque", "Velocista", "Goleiro", "Orbital", "Titã"}
    assert g.tier() == 3 and g.stats["titles"] == 4
    assert g.robot_price() == 650
    # time pessimo: ultimo, nao avanca, mas desbloqueia o chassis do tier
    g2 = fresh(6)
    for rb in g2.robots:
        rb["base"] = {a: 20 for a in robots.ATTRS}
    lg = play_league(g2, rng, 0)
    info = rl.finish_league(g2, rng)
    assert info["pos"] >= 4 and not info["advanced"] and g2.tier_done == -1
    assert g2.tier() == 0 and "Tanque" in g2.unlocked
    # liga so com tier alto ainda funciona e nao sorteia nomes repetidos
    for s in range(20):
        lg = rl.new_league(g2, 3, random.Random(s))
        assert len({t["name"] for t in lg["teams"]}) == 6


def test_no_global_rng():
    """Nada deve consumir o RNG global."""
    random.seed(1234)
    expected = random.random()
    random.seed(1234)
    g = fresh(8)
    play_league(g, random.Random(2), 0)
    rl.finish_league(g, random.Random(3))
    assert random.random() == expected


# ----------------------------------------------------------------- opponent_team (kwargs aditivos)
def _old_opponent_team(name, color, ovr, seed):
    """Copia congelada da implementacao anterior (antes dos kwargs names/chassis/jitter/attr_override)."""
    squad = []
    for i, role in enumerate(rl.ROLES):
        ch = robots.ROLE_CHASSIS[role]
        squad.append({"name": "%s %d" % (name.split()[0][:8], i + 1), "role": role,
                      "chassis": ch, "pid": None, "paint": None,
                      "attrs": robots.from_overall(ovr, role, ch, seed=seed * 10 + i)})
    return {"name": name, "color": tuple(color), "ovr": ovr, "seed": seed, "squad": squad}


OPP_CASES = [("Turma 3B", (10, 20, 30), 38, 7), ("Fundao FC", (200, 100, 50), 39, 12345),
             ("Clube do Xadrez", (1, 2, 3), 36, 1), ("Sakura Vacuum Club", (255, 0, 9), 55, 99)]
OPP_FROZEN_SHA = "ce6900af4e0d60b4f4f30ddc128c9c71ae299525db57e387cdc0dae9292789d3"   # gerado ANTES da mudanca


def test_opponent_team_default_identical():
    import hashlib
    got = [rl.opponent_team(*a) for a in OPP_CASES]
    assert hashlib.sha256(repr(got).encode()).hexdigest() == OPP_FROZEN_SHA
    for a in OPP_CASES:
        old = _old_opponent_team(*a)
        assert rl.opponent_team(*a) == old
        assert rl.opponent_team(*a, names=None, chassis=None, jitter=True, attr_override=None) == old
        cfg = rl.match_cfg(old)
        assert rl.match_cfg({"name": a[0], "color": a[1], "ovr": a[2], "seed": a[3]}) == cfg
        assert [e["pid"] for e in cfg["squad"]] == [None] * 5 and set(cfg["squad"][0]) == {
            "name", "attrs", "chassis", "pid", "paint"}


def test_opponent_team_new_kwargs():
    names = ["LX-01", "LX-02", "LX-03", "LX-04", "LX-05"]
    chs = ["Goleiro", "Tanque", "Disco", "Orbital", "Velocista"]
    t = rl.opponent_team("Limpex", (255, 255, 255), 63, 5, names=names, chassis=chs)
    assert [e["name"] for e in t["squad"]] == names and [e["chassis"] for e in t["squad"]] == chs
    assert rl.opponent_team("Limpex", (1, 2, 3), 63, 5)["squad"][0]["name"] == "Limpex 1"
    # jitter=False: identico entre seeds, igual a from_overall sem seed
    a = rl.opponent_team("Limpex", (1, 2, 3), 63, 1, jitter=False)
    b = rl.opponent_team("Limpex", (1, 2, 3), 63, 999, jitter=False)
    assert [e["attrs"] for e in a["squad"]] == [e["attrs"] for e in b["squad"]]
    for e, role in zip(a["squad"], rl.ROLES):
        assert e["attrs"] == robots.from_overall(63, role, e["chassis"])
    assert [e["attrs"] for e in a["squad"]] != [e["attrs"] for e in rl.opponent_team("Limpex", (1, 2, 3), 63, 1)["squad"]]
    # attr_override com clamp 20..99
    o = rl.opponent_team("Limpex", (1, 2, 3), 63, 1, attr_override={"bat": 150, "vel": 5})
    assert all(e["attrs"]["bat"] == 99 and e["attrs"]["vel"] == 20 for e in o["squad"])
    assert o["squad"][0]["attrs"]["def"] == rl.opponent_team("Limpex", (1, 2, 3), 63, 1)["squad"][0]["attrs"]["def"]
    # match_cfg propaga nomes/chassis do time
    cfg = rl.match_cfg(t)
    assert [e["name"] for e in cfg["squad"]] == names and [e["chassis"] for e in cfg["squad"]] == chs


def main():
    names = [n for n in globals() if n.startswith("test_")]
    want = sys.argv[1:]
    if want:
        names = [n for n in names if n in want or n[5:] in want]
    for n in names:
        try:
            globals()[n]()
            PASS.append(n)
            print("OK   %s" % n)
        except Exception as e:
            import traceback
            FAIL.append(n)
            print("FAIL %s: %r" % (n, e))
            traceback.print_exc()
    print("\n%d ok, %d falhas" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
