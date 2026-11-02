# -*- coding: utf-8 -*-
"""Fase 4 / Onda B (B5): game/skills.py - dados, compile_factors, gatilhos, tatica, PH, arvore,
effective_skills e skill_force (provisorio). Puro: sem pygame (e confere que skills.py nao o importa).

Rodar da raiz: .venv/bin/python tests/test_skills.py [nome_do_teste ...]
"""
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import garage as gm  # noqa: E402
import parts  # noqa: E402
import robots  # noqa: E402
import skills as S  # noqa: E402

PASS, FAIL = [], []
SPEC_IDS = ("arrancada", "succao", "curva", "muralha", "leitura", "poupanca", "recarga", "overclock",
            "blindagem", "drible", "elastica", "pressao", "choque", "matador", "lancador", "lider")
# (tipo, dur, cd, bat) da tabela 7.2 da spec
SPEC_TIMING = {"arrancada": ("A", 1.2, 9, 0.10), "succao": ("A", 1.5, 12, 0.08), "curva": ("A", 0.8, 10, 0.06),
               "muralha": ("A", 2.0, 11, 0.08), "leitura": ("P", 0, 0, 0), "poupanca": ("P", 0, 0, 0),
               "recarga": ("A", 1.5, 20, 0), "overclock": ("A", 6.0, 25, 0), "blindagem": ("A", 1.5, 10, 0.05),
               "drible": ("A", 0.5, 8, 0.07), "elastica": ("A", 1.0, 6, 0), "pressao": ("A", 3.0, 15, 0.10),
               "choque": ("A", 0, 12, 0.05), "matador": ("C", 0, 0, 0), "lancador": ("P", 0, 0, 0),
               "lider": ("P", 0, 0, 0)}


def base_factors(ovr=60, role="MID"):
    return robots.factors(robots.from_overall(ovr, role, seed=3), robots.TUNING_ROBOTS)


def fdict(f):
    return {n: getattr(f, n) for n in robots.Factors.__slots__}


# ----------------------------------------------------------------- dados
def test_catalog_shape():
    assert S.SKILL_IDS == SPEC_IDS and len(S.SKILLS) == 16
    for sid, s in S.SKILLS.items():
        kind, dur, cd, bat = SPEC_TIMING[sid]
        assert s["kind"] == kind and s["dur"] == dur and s["cd"] == cd and s["bat"] == bat, sid
        assert s["name"].encode("latin-1") and len(s["name"]) <= 18, s["name"]
        assert s["text"].encode("latin-1") and len(s["text"]) <= 60, s["text"]
        assert s["trigger"] in S.TRIGGERS and s["cat"] in ("atk", "def", "neutro")
        assert s["load"] == (2 if kind == "A" else 1)
        assert set(s["roles"]) <= {"GK", "DEF", "MID", "ATT"} and s["roles"]
        assert s["src"] and set(s["src"]) <= {"modulo", "arvore", "historia"}
        assert ("modulo" in s["src"]) == (sid in parts.MODULE_SKILLS), sid
        assert len(S.SKILL_FORCE[sid]) == 3
        for name, (op, v) in s["mods"].items():
            assert name in S.MOD_NAMES and op in ("mul", "add") and math.isfinite(v), (sid, name)
        for c in s.get("cost", ()):
            assert c in s["mods"]
    for sid, s in S.SPECIAL.items():
        assert s["trigger"] in S.TRIGGERS and s["name"].encode("latin-1") and len(s["name"]) <= 18
        assert len(s["text"]) <= 60 and s["text"].encode("latin-1")
        for name, (op, v) in s["mods"].items():
            assert name in S.MOD_NAMES and op in ("mul", "add")
    assert not set(S.SKILLS) & set(S.SPECIAL)
    assert sum(1 for s in S.SKILLS.values() if s.get("aura")) == 1 and S.SKILLS["lider"]["aura"]
    # a spec cita 11 especiais: 6 de reliquia e 5 de set
    assert sum("reliquia" in s["src"] for s in S.SPECIAL.values()) == 6
    assert sum("set" in s["src"] for s in S.SPECIAL.values()) == 5
    for it in S.ITEMS.values():
        assert it["name"].encode("latin-1") and it["force"] > 0 and it["scope"] in ("team", "gk", "one")
    assert len(S.ITEMS) == 6


def test_pure_no_pygame():
    src = open(os.path.join(ROOT, "game", "skills.py"), encoding="utf-8").read()
    assert "import pygame" not in src and "random." not in src


# ----------------------------------------------------------------- compile_factors
def test_each_skill_compiles_valid_and_limited():
    for role in ("GK", "DEF", "MID", "ATT"):
        for ovr in (30, 60, 95):
            base = base_factors(ovr, role)
            before = fdict(base)
            for sid in list(S.SKILLS) + list(S.SPECIAL):
                for rank in (1, 2, 3):
                    for up in (0, 5):
                        out = S.compile_factors(base, [(sid, rank, up)])
                        assert fdict(base) == before, "nao muta a base"
                        assert "_base" in out
                        kind = S.ALL[sid]["kind"]
                        assert (sid in out) == (kind in ("A", "C")), sid
                        for f in out.values():
                            for n in S.FACTOR_NAMES:
                                v = getattr(f, n)
                                assert math.isfinite(v), (sid, n)
                                lo, hi = S._LIMITS.get(n, (None, None))
                                assert lo is None or v >= lo - 1e-9, (sid, n, v)
                                assert hi is None or v <= hi + 1e-9, (sid, n, v)
                            assert f.g_chu == base.g_chu


def test_passive_and_active_effects():
    base = base_factors()
    out = S.compile_factors(base, [("leitura", 1), ("arrancada", 1)])
    b = out["_base"]
    assert abs(b.pass_range - min(1600.0, base.pass_range * 1.15)) < 1e-6
    assert abs(b.dec_err - base.dec_err * 0.7) < 1e-9
    a = out["arrancada"]                              # variante = base (com passivas) + ativa
    assert abs(a.speed - b.speed * 1.35) < 1e-9 and abs(a.accel - b.accel * 1.6) < 1e-9
    assert abs(a.pass_range - b.pass_range) < 1e-9
    # drible: shield x0
    assert S.compile_factors(base, [("drible", 1)])["drible"].shield == 0.0
    # elastica: gk_save +0,25 com teto 0,95
    gk = base_factors(99, "GK")
    e = S.compile_factors(gk, [("elastica", 3)])["elastica"]
    assert e.gk_save == min(0.95, gk.gk_save + 0.25 * 1.5)
    # lider (aura) nao entra no robo; aura_mods pega 1 so (maior rank)
    assert fdict(S.compile_factors(base, [("lider", 3)])["_base"]) == fdict(base)
    am = S.aura_mods([[("lider", 1)], [("lider", 2)], [("arrancada", 3)]])
    assert abs(am["speed"][1] - (1 + 0.02 * 1.25)) < 1e-12
    assert S.aura_mods([[("leitura", 1)]]) == {}
    # ids desconhecidos ignorados
    assert set(S.compile_factors(base, [("xyz", 1), ("curva", 9)])) == {"_base", "curva"}


def test_rank_scales_magnitude_and_cooldown():
    assert S.RANK_MUL == (1.0, 1.25, 1.5) and S.RANK_CD == (1.0, 0.9, 0.8)
    for sid in S.SKILL_IDS:
        cds = [S.cooldown(sid, r) for r in (1, 2, 3)]
        assert cds[0] >= cds[1] >= cds[2]
        m1, m2, m3 = (S.scaled_mods(sid, r) for r in (1, 2, 3))
        cost = {("speed" if c == "spd" else c) for c in S.SKILLS[sid].get("cost", ())}
        for n in m1:
            d1, d2, d3 = (abs((m[n][1] - (1.0 if m[n][0] == "mul" else 0.0))) for m in (m1, m2, m3))
            if n in cost:
                assert d1 == d2 == d3, (sid, n)          # o lado ruim nao escala
            elif d1 > 0 and not (m1[n][0] == "mul" and m3[n][1] == 0.0):
                assert d1 < d2 < d3, (sid, n, d1, d2, d3)
                assert abs(d2 - 1.25 * d1) < 1e-9 and abs(d3 - 1.5 * d1) < 1e-9
    # upgrade do modulo aumenta a magnitude, nao o rank
    assert S.magnitude(1, 5) > S.magnitude(1, 0) and S.magnitude(1, 99) == S.magnitude(1, parts.MAX_UP)
    m0, m5 = S.scaled_mods("arrancada", 1, 0), S.scaled_mods("arrancada", 1, 5)
    assert m5["speed"][1] > m0["speed"][1]
    assert S.scaled_extra("succao", 3)["pull"] == 120.0 * 1.5
    assert S.scaled_extra("overclock", 3)["fatigue"] == (3.0, 0.9)
    assert S.scaled_extra("rolando", 3)["uses"] == 1


# ----------------------------------------------------------------- gatilhos
def test_triggers():
    T = S.check_trigger
    assert T("arrancada", {"has_ball": True, "opp_ahead": 100, "bat": 0.5})
    assert not T("arrancada", {"has_ball": True, "opp_ahead": 60, "bat": 0.5})
    assert not T("arrancada", {"has_ball": True, "opp_ahead": 100, "bat": 0.3})
    assert T("succao", {"ball_free": True, "ball_dist": 50, "ball_speed": 100, "is_chaser": True})
    assert not T("succao", {"ball_free": True, "ball_dist": 50, "ball_speed": 300, "is_chaser": True})
    assert T("curva", {"kicking": True, "dist_opp_goal": 300, "shoot_range": 400, "gk_off_line": True})
    assert not T("curva", {"kicking": True, "dist_opp_goal": 300, "shoot_range": 400})
    assert T("muralha", {"ball_goal_dist": 200, "opp_ball_zone": True})
    assert T("leitura", {}) and T("lider", {})
    assert T("recarga", {"bat": 0.2, "vel_frac": 0.1}) and not T("recarga", {"bat": 0.2, "vel_frac": 0.5})
    assert T("overclock", {"score_diff": 0, "minute": 61}) and not T("overclock", {"score_diff": 1, "minute": 80})
    assert T("overclock", {"score_diff": 2, "bat": 0.8, "ball_third": "att"})
    assert T("blindagem", {"has_ball": True, "opp_near": 50}) and not T("blindagem", {"has_ball": False, "opp_near": 5})
    assert T("drible", {"has_ball": True, "opp_near": 40}) and not T("drible", {"has_ball": True, "opp_near": 50})
    assert T("elastica", {"shot_speed": 500, "ball_goal_dist": 200, "ball_toward_goal": True})
    assert not T("elastica", {"shot_speed": 400, "ball_goal_dist": 200, "ball_toward_goal": True})
    assert T("pressao", {"opp_has_ball": True, "ball_third": "att"})
    assert T("choque", {"won_ball": True}) and not T("choque", {})
    assert T("matador", {"dist_opp_goal": 150}) and not T("matador", {"dist_opp_goal": 200})
    assert T("remendo", {"lost_ball": True}) and T("chinelada", {"kicking": True, "dist_opp_goal": 1, "shoot_range": 2})
    # contexto vazio/estranho: neutro, nunca levanta
    for sid in S.ALL:
        T(sid, {})
        T(sid, {"bat": None, "opp_near": "x", "has_ball": [1]})
    assert T("nada", {}) is False
    # todo gatilho declarado e usado e tem funcao
    used = {s["trigger"] for s in S.ALL.values()}
    assert used <= set(S.TRIGGERS)


# ----------------------------------------------------------------- tatica
def test_tactic_changes_only_priority():
    assert S.TACTICS == ("ofensivo", "equilibrado", "defensivo") and S.DEFAULT_TACTIC == "equilibrado"
    cand = ["muralha", "arrancada", "recarga"]
    assert S.pick_active(cand, "ofensivo") == "arrancada"
    assert S.pick_active(cand, "defensivo") == "muralha"
    assert S.pick_active(cand, "equilibrado") == "arrancada"     # empate: ordem do catalogo
    assert S.pick_active(["recarga"], "defensivo") == "recarga"  # nunca bloqueia: so ordena
    assert S.pick_active([], "ofensivo") is None and S.pick_active(["xyz"], "ofensivo") is None
    assert S.pick_active(cand, "invalida") == S.pick_active(cand, "equilibrado")
    for t in S.TACTICS:
        for c in (cand, ["drible", "blindagem"], ["elastica", "curva", "pressao"]):
            assert S.pick_active(c, t) in c
            assert S.pick_active(c, t) == S.pick_active(list(reversed(c)), t)
        assert S.TACTIC_NAMES[t].encode("latin-1")


# ----------------------------------------------------------------- PH, arvore, equipar
def test_ph_per_level():
    assert [S.ph_for_level(l) for l in range(1, 16)] == list(range(0, 15))
    assert S.ph_for_level("x") == 0 and S.ph_for_level(-3) == 0
    g = gm.new_game(random.Random(1))
    r = g.robots[0]
    assert r["skills"] == S.new_robot_skills()
    gained = gm.add_xp(r, 10 ** 6)                     # cap 10 (Modo Robos)
    assert gained == 9 and r["level"] == 10 and r["skills"]["pts"] == 9
    gained = gm.add_xp(r, 10 ** 6, gm.CAMPAIGN_CAP)    # campanha: ate 15
    assert gained == 5 and r["level"] == 15 and r["skills"]["pts"] == 14 == S.ph_for_level(15)
    assert gm.add_xp(r, 10 ** 6, gm.CAMPAIGN_CAP) == 0 and r["xp"] == 0
    r["skills"]["pts"] = S.PTS_MAX
    S.grant_pts(r, 5)
    assert r["skills"]["pts"] == S.PTS_MAX


def test_tree_learn_and_equip():
    assert set(S.TREE) == {"ATQ", "CTR", "DEF"} and all(len(b) == 4 for b in S.TREE.values())
    for n in S.NODES.values():
        assert n["skill"] in S.SKILLS and 1 <= n["cost"] <= 3 and n["rank"] in (1, 2, 3)
        assert all(q in S.NODES for q in n["needs"])
    r = {"skills": {"learned": {}, "equipped": [], "pts": 3}}
    assert S.node_state(r, "def1") == "open" and S.node_state(r, "def2") == "locked"
    ok, _ = S.learn_node(r, "def2")
    assert not ok
    assert S.learn_node(r, "def1")[0] and r["skills"]["learned"] == {"muralha": 1} and r["skills"]["pts"] == 2
    assert S.node_state(r, "def1") == "learned" and not S.learn_node(r, "def1")[0]
    assert S.learn_node(r, "def2")[0] and r["skills"]["pts"] == 0
    assert not S.learn_node(r, "def3")[0]               # sem PH
    S.grant_pts(r, 2)
    assert S.learn_node(r, "def3")[0] and r["skills"]["learned"]["muralha"] == 2
    assert not S.learn_node(r, "nada")[0]
    # equipar: aprendida, sem duplicata, max 3, carga <= 6
    assert S.equip_skill(r, "muralha")[0] and not S.equip_skill(r, "muralha")[0]
    assert not S.equip_skill(r, "curva")[0]             # nao aprendida
    S.learn_skill(r, "curva", 3)                         # rank 3 = carga 3
    assert S.equipped_load(r) == 2 and S.equip_skill(r, "blindagem")[0] and S.equipped_load(r) == 4
    assert not S.equip_skill(r, "curva")[0]             # 4 + 3 > 6
    S.learn_skill(r, "leitura", 1)
    assert S.equip_skill(r, "leitura")[0] and len(r["skills"]["equipped"]) == 3
    S.learn_skill(r, "poupanca", 1)
    assert not S.equip_skill(r, "poupanca")[0]          # max 3
    assert S.unequip_skill(r, "leitura")[0] and not S.unequip_skill(r, "leitura")[0]
    assert not S.learn_skill(r, "rolando")[0]           # especiais nao se aprendem
    assert S.load_of("leitura", 1) == 1 and S.load_of("arrancada", 2) == 2 and S.load_of("leitura", 3) == 3


def test_effective_skills_sources():
    g = gm.new_game(random.Random(4))
    r = g.robots[0]
    assert g.skills_of(r) == [] and S.effective_skills(r, {}) == []
    mod = g.new_piece("Módulo Arrancada", 2, 3)
    rel = g.new_piece("Chip do Vovô", 3)
    g.inventory += [mod, rel]
    r["slots"]["modulo"] = mod["id"]
    r["slots"]["chip"] = rel["id"]
    pb = g.pieces_by_id()
    assert S.effective_skills(r, pb, mod_on=False) == [("instinto_vo", 1, 0)]
    assert S.effective_skills(r, pb) == [("arrancada", 2, 3), ("instinto_vo", 1, 0)]
    assert g.skills_of(r) == [("instinto_vo", 1, 0)]        # mod_on desligado no garage
    g.flags["mod_on"] = 1
    assert g.skills_of(r)[0] == ("arrancada", 2, 3)
    # aprendidas equipadas: a mesma do modulo com rank maior sobe o rank (sem duplicar)
    r["skills"] = {"learned": {"arrancada": 3, "leitura": 1, "muralha": 2, "poupanca": 1},
                   "equipped": ["arrancada", "leitura", "muralha", "poupanca"], "pts": 0}
    eff = S.effective_skills(r, pb)
    ids = [e[0] for e in eff]
    assert ids.count("arrancada") == 1 and ("arrancada", 3, 0) in eff
    learned_eq = [e for e in eff if e[0] in S.SKILLS]
    assert len(learned_eq) <= S.MAX_EQUIPPED
    assert sum(S.load_of(e[0], e[1]) for e in learned_eq) <= S.LOAD_MAX
    # set completo (6 pecas) -> passiva do set (contada direto pela tabela; 6 e inalcancavel com 7 slots)
    assert parts.set_bonus({"Plasma": 6})[1] == ["sobrecarga"]
    # robo bagunçado nunca levanta
    for bad in ({}, {"slots": None}, {"slots": {"modulo": 999}}, {"skills": {"equipped": ["x", None]}},
                {"skills": {"learned": {"leitura": "a"}, "equipped": ["leitura"]}}):
        S.effective_skills(bad, pb)


def test_skill_force_and_cap():
    assert S.skill_force([]) == 0.0
    f1 = S.skill_force([("arrancada", 1)])
    f3 = S.skill_force([("arrancada", 3)])
    assert 0 < f1 < f3 and f1 == S.SKILL_FORCE["arrancada"][0]
    for sid in S.SKILL_FORCE:
        a, b, c = S.SKILL_FORCE[sid]
        assert 0 < a <= b <= c <= 1.0, sid
    many = [(sid, 3) for sid in S.SKILL_IDS]
    assert S.skill_force(many) == S.ROBOT_SK_CAP
    assert S.team_skill_force([]) == 0.0
    assert S.team_skill_force([many] * 5) == S.SK_CAP == 4.0
    t = S.team_skill_force([[("arrancada", 1)], [], [], [], []])
    assert abs(t - f1 / 5) < 1e-12
    assert abs(S.item_force(["cera_turbo", "cafe", "xyz"]) - 1.4) < 1e-12
    assert S.skill_force([("xyz", 1), ("curva", "q")]) == S.SKILL_FORCE["curva"][0]


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
        except Exception as e:  # noqa: BLE001
            import traceback
            FAIL.append(n)
            print("FAIL %s: %r" % (n, e))
            traceback.print_exc()
    print("\n%d ok, %d falhas" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
