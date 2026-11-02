# -*- coding: utf-8 -*-
"""Fase 4 / Onda B (B1, B2, B4): catalogo novo de pecas, loja, sets, reliquias e modulos. Sem pygame.

Rodar da raiz: .venv/bin/python tests/test_parts_v2.py [nome_do_teste ...]
"""
import copy
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import garage as gm  # noqa: E402
import parts  # noqa: E402
import robots  # noqa: E402
import skills  # noqa: E402

PASS, FAIL = [], []

# os 14 modelos da v1, na ordem do dict original (o stream do RNG depende dela)
V1_MODELS = ("Motor Escovado", "Turbina", "Célula Longa", "Célula Rápida", "Borracha", "Blindado",
             "Solenoide", "Canhão de Plasma", "Escova de Sucção", "Vácuo Turbo", "Infravermelho",
             "Radar LiDAR", "Chip de CPU", "Chip Neural")
# tabela da spec (secao 1): modelo -> (slot, pesos, heat, tipo, set)
SPEC_NEW = {
    "Servo Ágil": ("motor", {"ace": 1.0, "vel": 0.4}, 0.0, "equilibrado", "Faxineiro"),
    "Ímã Linear": ("motor", {"vel": 1.5, "ace": 0.5}, 0.45, "agressivo", "Plasma"),
    "Célula Solar": ("bateria", {"bat": 1.2, "vel": 0.1}, 0.0, "equilibrado", "Faxineiro"),
    # decisao do dev (B6-B9): Fusao virou sidegrade de pico (spec: bat 1,5 ace 0,4 def 0,2, que dominava)
    "Célula Fusão": ("bateria", {"bat": 1.1, "ace": 0.8}, 0.5, "agressivo", "Plasma"),
    "Espuma Viscoelástica": ("parachoque", {"def": 0.7, "ctr": 0.7}, 0.0, "especialista", "Faxineiro"),
    "Placa Reativa": ("parachoque", {"def": 1.5, "ctr": 0.3}, 0.4, "agressivo", "Titã"),
    "Mola Dupla": ("chutador", {"chu": 0.8, "vis": 0.4, "ctr": 0.2}, 0.0, "especialista", "Dojo"),
    "Railgun de Bolso": ("chutador", {"chu": 1.6, "ctr": 0.3}, 0.45, "agressivo", "Plasma"),
    "Escova Dupla": ("succao", {"ctr": 0.8, "vel": 0.3, "def": 0.3}, 0.0, "especialista", "Faxineiro"),
    "Vórtice": ("succao", {"ctr": 1.5, "def": 0.3}, 0.35, "agressivo", "Titã"),
    "Câmera Dupla": ("sensor", {"vis": 0.7, "qi": 0.5, "ctr": 0.2}, 0.0, "especialista", "Dojo"),
    "Sonar Quântico": ("sensor", {"vis": 1.5, "qi": 0.3}, 0.35, "agressivo", "Plasma"),
    "Chip Tático": ("chip", {"qi": 0.8, "ctr": 0.5}, 0.0, "equilibrado", "Dojo"),
    "Chip Zero": ("chip", {"qi": 1.6, "vis": 0.4}, 0.4, "agressivo", "Limpex"),
    "Motor Torque": ("motor", {"vel": 0.6, "ace": 0.6, "def": 0.3}, 0.0, "especialista", "Titã"),
    "Solenoide Duplo": ("chutador", {"chu": 1.1, "ctr": 0.3}, 0.15, "meio-termo", "Limpex"),
}
SPEC_SETS = {
    "Faxineiro": {"Servo Ágil", "Célula Solar", "Espuma Viscoelástica", "Escova Dupla", "Escova de Sucção",
                  "Borracha"},
    "Plasma": {"Ímã Linear", "Célula Fusão", "Railgun de Bolso", "Sonar Quântico", "Canhão de Plasma", "Turbina"},
    "Titã": {"Placa Reativa", "Vórtice", "Motor Torque", "Blindado", "Vácuo Turbo"},
    "Dojo": {"Mola Dupla", "Câmera Dupla", "Chip Tático", "Chip de CPU", "Infravermelho"},
    "Limpex": {"Chip Zero", "Solenoide Duplo", "Radar LiDAR", "Célula Rápida"},
}
# (set) -> (faixa 2, faixa 3, passiva da faixa 4); faixas 2/3/4 (decisao do dev: com 1 peca por slot as
# faixas 4/6 da spec eram inalcancaveis). Magnitudes: 2 = 2 da spec, 3 = 4 da spec, 4 = 3 + passiva.
SPEC_SET_BONUS = {
    "Faxineiro": ({"ctr": 2}, {"ctr": 3, "bat": 3}, "faxina_total"),
    "Plasma": ({"chu": 2}, {"chu": 3, "vel": 3}, "sobrecarga"),
    "Titã": ({"def": 3}, {"def": 4, "ctr": 3}, "muralha_aco"),
    "Dojo": ({"qi": 2}, {"qi": 3, "vis": 3}, "mente_zen"),
    "Limpex": ({"vel": 2}, {"vel": 3, "ace": 3}, "impecavel"),
}
# Regra "sidegrade, nunca estritamente melhor": vale para TODOS os modelos novos (a excecao da Celula
# Fusao foi removida por decisao do dev: ela virou sidegrade de pico, ACE alta com BAT liquida baixa).
SIDEGRADE_EXCEPTIONS = set()


def net_vec(model, rar, lvl=0):
    b = parts.part_bonus(model, rar, lvl)
    v = {a: float(b.get(a, 0)) for a in robots.ATTRS}
    v["bat"] -= parts.part_heat(model, rar, lvl)
    return v


def bare_robot():
    g = gm.new_game(random.Random(1))
    r = copy.deepcopy(g.robots[2])
    r["slots"] = {s: None for s in parts.SLOTS}
    return r


def pieces(*models, rar=0):
    out = {}
    for i, m in enumerate(models):
        out[1000 + i] = {"id": 1000 + i, "model": m, "rar": rar, "lvl": 0}
    return out


def equip_all(r, pb):
    for pid, pc in pb.items():
        r["slots"][parts.part_slot(pc)] = pid
    return r


# ----------------------------------------------------------------- catalogo (B1)
def test_catalog_counts_and_spec_table():
    assert parts.CORE_MODELS == V1_MODELS and parts.MODELS == V1_MODELS
    assert tuple(parts.PARTS)[:14] == V1_MODELS, "ordem do dict original preservada"
    assert len(parts.NEW_MODELS) == 16 and len(parts.ALL_MODELS) == 30
    assert set(parts.NEW_MODELS) == set(SPEC_NEW)
    assert parts.ALL_MODELS[:14] == V1_MODELS
    for m, (slot, w, heat, kind, st) in SPEC_NEW.items():
        d = parts.PARTS[m]
        assert d["slot"] == slot and d["w"] == w and d["heat"] == heat, m
        assert d["kind"] == kind and d["set"] == st, m
    assert parts.PARTS["Chip Zero"].get("legend_only") is True
    assert parts.GEAR_SLOTS == parts.SLOTS[:7] and parts.SLOTS[7] == "modulo" and len(parts.SLOTS) == 8
    for slot in parts.GEAR_SLOTS:
        assert len(parts.models_for_slot(slot, parts.ALL_MODELS)) >= 4, slot
    for m in parts.PARTS:
        m.encode("latin-1")
        parts.part_name({"model": m, "rar": 3, "lvl": 5}).encode("latin-1")
        parts.bonus_text({"model": m, "rar": 0, "lvl": 0}).encode("latin-1")
    for s in parts.SLOT_NAMES.values():
        s.encode("latin-1")


def test_weights_follow_design_rules():
    for m in parts.NEW_MODELS:
        d = parts.PARTS[m]
        sw = sum(d["w"].values())
        assert all(a in robots.ATTRS for a in d["w"]), m
        if d["kind"] in ("equilibrado", "especialista"):
            assert 1.3 - 1e-9 <= sw <= 1.5 + 1e-9 and d["heat"] == 0.0, (m, sw)
        elif d["kind"] == "agressivo":
            # spec: "Sigma w 1,6-1,9"; a propria tabela traz Ima 2,0, Fusao 2,1 e Chip Zero 2,0 (reportado)
            assert 1.6 - 1e-9 <= sw <= 2.1 + 1e-9 and 0.25 <= d["heat"] <= 0.5, (m, sw)
        else:
            assert d["kind"] == "meio-termo" and 0 < d["heat"] < 0.25, m
    # poder LIQUIDO (pesos - calor) de todo o equipamento fica na faixa dos originais (1,2..1,6)
    for m in parts.ALL_MODELS:
        d = parts.PARTS[m]
        net = sum(d["w"].values()) - d["heat"]
        assert 1.2 - 1e-9 <= net <= 1.6 + 1e-9, (m, net)
    # monotonia: raridade e upgrade nunca pioram o bonus
    for m in parts.ALL_MODELS + parts.RELIC_MODELS:
        for rar in range(4):
            for lvl in range(parts.MAX_UP):
                b0, b1 = parts.part_bonus(m, rar, lvl), parts.part_bonus(m, rar, lvl + 1)
                assert all(b1[a] >= b0[a] for a in b0), m


def test_sidegrade_never_strictly_better():
    found = set()
    for m in parts.NEW_MODELS:
        for c in parts.CORE_MODELS:
            if parts.PARTS[c]["slot"] != parts.PARTS[m]["slot"]:
                continue
            for rar in range(4):
                a, b = net_vec(m, rar), net_vec(c, rar)
                if all(a[k] >= b[k] - 1e-9 for k in a) and any(a[k] > b[k] + 1e-9 for k in a):
                    found.add((m, c))
    assert found == SIDEGRADE_EXCEPTIONS == set(), sorted(found)


# ----------------------------------------------------------------- loja (B1)
def _old_refresh_shop(g, tier, rng):
    """Copia literal do refresh_shop da v1 (commit ca98e1f)."""
    seed = rng.getrandbits(31)
    r = random.Random(seed)
    stock = [g.new_piece(r.choice(V1_MODELS), 0) for _ in range(gm.SHOP_COMMONS)]
    stock.append(g.new_piece(r.choice(V1_MODELS), 1))
    if tier >= gm.EPIC_MIN_TIER and r.random() < gm.EPIC_CHANCE:
        stock.append(g.new_piece(r.choice(V1_MODELS), 2))
    if tier >= gm.LEGEND_MIN_TIER and r.random() < gm.LEGEND_CHANCE:
        stock.append(g.new_piece(r.choice(V1_MODELS), 3))
    g.shop = {"stock": stock, "seed": seed}
    return stock


def test_shop_rng_stream_identical_to_v1_up_to_tier3():
    for tier in range(4):
        for seed in range(150):
            g1, g2 = gm.Garage(), gm.Garage()
            r1, r2 = random.Random(seed), random.Random(seed)
            for _ in range(3):
                a = g1.refresh_shop(tier, r1)
                b = _old_refresh_shop(g2, tier, r2)
                assert a == b and g1.shop == g2.shop, (tier, seed)
            assert r1.random() == r2.random(), "o RNG externo consome o mesmo"
    # new_game (usa refresh_shop do tier 0) e match_rewards (drop) seguem o mesmo stream
    for seed in range(30):
        g = gm.new_game(random.Random(seed))
        assert all(p["model"] in V1_MODELS for p in g.inventory + g.shop["stock"])
        for k in range(20):
            rng = random.Random(seed * 100 + k)
            rng_ref = random.Random(seed * 100 + k)
            out = gm.match_rewards(g, 2, 0, [], 1, rng)
            if out["drop"] is not None:
                rng_ref.random()
                assert out["drop"]["model"] == rng_ref.choice(V1_MODELS)


def test_shop_pools_by_tier():
    for tier in range(parts.SHOP_ALL_TIER):
        for rar in range(4):
            assert parts.shop_models(tier, rar) == parts.CORE_MODELS
    pool_c = parts.shop_models(4, 0)
    pool_l = parts.shop_models(4, 3)
    assert "Chip Zero" not in pool_c and "Chip Zero" in pool_l
    assert set(pool_l) == set(parts.ALL_MODELS)
    for pool in (pool_c, pool_l):
        assert not set(pool) & set(parts.RELIC_MODELS) and not set(pool) & set(parts.MODULE_MODELS)
    # tier 4 sorteia modelos novos (frequencia ~ uniforme)
    g = gm.Garage()
    seen = {}
    rng = random.Random(7)
    for _ in range(400):
        for p in g.refresh_shop(4, rng):
            seen[p["model"]] = seen.get(p["model"], 0) + 1
            assert p["model"] != "Chip Zero" or p["rar"] == 3
    assert set(parts.NEW_MODELS) - {"Chip Zero"} <= set(seen)
    assert not set(seen) - set(parts.ALL_MODELS)


# ----------------------------------------------------------------- sets (B2)
def test_set_membership_matches_spec():
    got = {}
    for m, d in parts.PARTS.items():
        if d.get("set"):
            got.setdefault(d["set"], set()).add(m)
    assert got == SPEC_SETS
    assert set(parts.SETS) == set(SPEC_SETS)


def test_set_bonus_table_2_3_4():
    assert parts.SET_TIERS == (2, 3, 4)
    for s, (b2, b3, passive) in SPEC_SET_BONUS.items():
        for n in range(0, 8):
            attrs, pas = parts.set_bonus({s: n})
            if n < 2:
                assert attrs == {} and pas == [], (s, n)
            elif n < 3:
                assert attrs == b2 and pas == [], (s, n)
            elif n < 4:
                assert attrs == b3 and pas == [], (s, n)
            else:
                assert attrs == b3 and pas == [passive], (s, n)
        assert passive in skills.SPECIAL
    # sets diferentes somam
    attrs, pas = parts.set_bonus({"Faxineiro": 2, "Titã": 2, "Plasma": 4})
    assert attrs == {"ctr": 2, "def": 3, "chu": 3, "vel": 3} and pas == ["sobrecarga"]


def test_set_bonus_in_effective_attrs():
    r = bare_robot()
    base = gm.effective_attrs(r, {})
    # 1 peca: sem bonus; 2 pecas Faxineiro: CTR +2 alem dos bonus das pecas
    pb1 = pieces("Borracha")
    one = gm.effective_attrs(equip_all(copy.deepcopy(r), pb1), pb1)
    assert one["ctr"] - base["ctr"] == parts.part_bonus("Borracha", 0, 0)["ctr"]
    pb2 = pieces("Borracha", "Escova de Sucção")
    two = gm.effective_attrs(equip_all(copy.deepcopy(r), pb2), pb2)
    exp = parts.part_bonus("Borracha", 0, 0)["ctr"] + parts.part_bonus("Escova de Sucção", 0, 0)["ctr"] + 2
    assert two["ctr"] - base["ctr"] == exp
    # 3 pecas Faxineiro (faixa 3): CTR +3 e BAT +3 (substitui o +2)
    pb3 = pieces("Borracha", "Escova de Sucção", "Servo Ágil")
    three = gm.effective_attrs(equip_all(copy.deepcopy(r), pb3), pb3)
    c3 = sum(parts.part_bonus(m, 0, 0).get("ctr", 0) for m in (p["model"] for p in pb3.values()))
    b3 = sum(parts.part_bonus(m, 0, 0).get("bat", 0) for m in (p["model"] for p in pb3.values()))
    assert three["ctr"] - base["ctr"] == c3 + 3 and three["bat"] - base["bat"] == b3 + 3
    # 4 pecas Faxineiro (faixa 4): CTR +3 e BAT +3 (substitui o +2) + passiva
    pb4 = pieces("Servo Ágil", "Célula Solar", "Espuma Viscoelástica", "Escova Dupla")
    rr = equip_all(copy.deepcopy(r), pb4)
    four = gm.effective_attrs(rr, pb4)
    ctr = sum(parts.part_bonus(m, 0, 0).get("ctr", 0) for m in (p["model"] for p in pb4.values()))
    bat = sum(parts.part_bonus(m, 0, 0).get("bat", 0) for m in (p["model"] for p in pb4.values()))
    assert four["ctr"] - base["ctr"] == ctr + 3 and four["bat"] - base["bat"] == bat + 3
    assert gm.robot_set_counts(rr, pb4) == {"Faxineiro": 4}
    # overclock multiplica o bonus das pecas, NAO o do set
    rr["oc"] = 2
    oc = gm.effective_attrs(rr, pb4)
    assert abs(oc["ctr"] - (base["ctr"] + round(gm.OC_MUL[2] * ctr) + 3)) <= 1
    # mistura de sets com 1 peca cada: nada
    pbm = pieces("Borracha", "Turbina", "Chip de CPU", "Radar LiDAR")
    assert parts.set_bonus(parts.set_counts(p["model"] for p in pbm.values())) == ({}, [])


def test_set_max_equippable_and_text():
    # com 1 peca por slot, quantas pecas de cada set cabem num robo: com as faixas 2/3/4 a faixa 3 vale para
    # todos os sets e a 4 (passiva) para Faxineiro, Plasma e Limpex (Titã e Dojo so tem 3 slots)
    reach = {}
    for s, members in SPEC_SETS.items():
        reach[s] = len({parts.PARTS[m]["slot"] for m in members})
    assert reach == {"Faxineiro": 4, "Plasma": 4, "Titã": 3, "Dojo": 3, "Limpex": 4}, reach
    assert all(n >= parts.SET_TIERS[1] for n in reach.values())
    full = {s for s, n in reach.items() if n >= parts.SET_TIERS[-1]}
    assert full == {"Faxineiro", "Plasma", "Limpex"}, full
    print("  [AVISO] passiva de set (faixa 4) inalcancavel num robo para:", sorted(set(reach) - full))
    assert parts.set_bonus_text({}) == []
    assert parts.set_bonus_text({"Faxineiro": 1}) == ["Faxineiro 1/4"]
    assert parts.set_bonus_text({"Faxineiro": 2}) == ["Faxineiro 2/4: CTR+2"]
    assert parts.set_bonus_text({"Faxineiro": 3}) == ["Faxineiro 3/4: CTR+3 BAT+3"]
    assert parts.set_bonus_text({"Titã": 3}) == ["Titã 3/4: DEF+4 CTR+3"]
    assert parts.set_bonus_text({"Dojo": 4, "Plasma": 2}) == ["Plasma 2/4: CHU+2", "Dojo 4/4: QI+3 VIS+3 +passiva"]
    for line in parts.set_bonus_text({s: 4 for s in parts.SETS}):
        line.encode("latin-1")
        assert len(line) <= 40


# ----------------------------------------------------------------- reliquias e modulos
def test_relics_unique():
    assert len(parts.RELIC_MODELS) == 6
    slots = set()
    for m in parts.RELIC_MODELS:
        d = parts.PARTS[m]
        assert d["unique"] and d["power"] == parts.RELIC_POWER == 22 and d["heat"] == 0.0
        assert d["passive"] in skills.SPECIAL and "reliquia" in skills.SPECIAL[d["passive"]]["src"]
        assert parts.is_unique(m) and m not in parts.ALL_MODELS
        slots.add(d["slot"])
        assert parts.part_power(3, 0, m) == 22 > parts.part_power(3, 0)
        b = parts.part_bonus(m, 3, 0)
        assert b == {a: int(round(w * 22)) for a, w in d["w"].items()}
    assert slots == {"motor", "chip", "parachoque", "bateria", "succao", "sensor"}
    assert parts.PARTS["Rodinha Esquerda do Zé"]["w"] == {"vel": 1.2, "ace": 0.6}
    # nao vendaveis; sanitize: no maximo 1 de cada e sempre Lendaria
    g = gm.new_game(random.Random(2))
    rel = g.new_piece("Chip do Vovô", 0)
    g.inventory.append(rel)
    ok, msg = g.sell_part(rel["id"])
    assert not ok and "Relíquia" in msg
    d = g.to_dict()
    d["inventory"].append({"id": 9999, "model": "Chip do Vovô", "rar": 3, "lvl": 0})
    d["shop"]["stock"].append({"id": 9998, "model": "Chip do Vovô", "rar": 3, "lvl": 0})
    g2 = gm.Garage.from_dict(d)
    relics = [p for p in g2.inventory + g2.shop["stock"] if p["model"] == "Chip do Vovô"]
    assert len(relics) == 1 and relics[0]["id"] == rel["id"] and relics[0]["rar"] == 3


def test_modules():
    assert len(parts.MODULE_MODELS) == 12 == len(parts.MODULE_SKILLS)
    seen = set()
    for m in parts.MODULE_MODELS:
        d = parts.PARTS[m]
        assert d["slot"] == "modulo" and d["w"] == {} and d["heat"] == 0.0
        assert d["skill"] in skills.SKILLS and d["skill"] not in seen
        seen.add(d["skill"])
        assert [parts.part_skill({"model": m, "rar": r, "lvl": 0})[1] for r in range(4)] == [1, 1, 2, 3]
        assert parts.part_bonus(m, 3, 5) == {} and parts.part_heat(m, 3, 5) == 0
    assert parts.part_skill({"model": "Turbina", "rar": 3, "lvl": 0}) is None
    # modulo nao mexe em atributos
    r = bare_robot()
    pb = pieces("Módulo Arrancada", rar=3)
    assert gm.effective_attrs(equip_all(copy.deepcopy(r), pb), pb) == gm.effective_attrs(r, {})


def test_cosmetics_catalog():
    assert len(parts.DECALS) == 6 and len(parts.TRAILS) == 4 and len(parts.CELEBRATIONS) == 4
    assert len(parts.COSMETICS) == len(parts.DECALS) + len(parts.TRAILS) + len(parts.ANTENNAS) + 4
    for c in parts.COSMETICS:
        c.encode("ascii")


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
