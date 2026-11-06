# -*- coding: utf-8 -*-
"""Fase 4 / Onda B (B3): Garage v2 - migracao v1 -> v2 com saves v1 REAIS, sanitize dos campos novos,
fuzz, ida e volta, campanha com garage embutido e build antigo (v1) lendo save v2 -> "bad".

Os saves v1 de tests/fixtures/ foram gerados com o codigo do commit ca98e1f (garage v1), sem edicao.
Nada aqui grava em ~/.soccerpy_*: os stores sao trocados por dicionarios em memoria.

Rodar da raiz: .venv/bin/python tests/test_garage_v2.py [nome_do_teste ...]
"""
import copy
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import campaign as cm  # noqa: E402
import garage as gm  # noqa: E402
import parts  # noqa: E402
import robot_league as rl  # noqa: E402
import skills  # noqa: E402

PASS, FAIL = [], []
FIX = os.path.join(ROOT, "tests", "fixtures")
V1_COMMIT = "ca98e1f"                     # ultimo commit com garage v1
V1_FIELDS = ("scrap", "next_id", "team", "robots", "lineup", "inventory", "unlocked",
             "tier_done", "league", "shop", "stats", "flags")
V1_ROBOT_KEYS = ("id", "name", "chassis", "role", "level", "xp", "paint", "base", "oc")
MEM = {}


def use_mem():
    MEM.clear()
    MEM.update({"main": None, "bad": None, "writes": 0})
    gm._store_get = lambda: MEM["main"]
    gm._store_set = lambda t: (MEM.__setitem__("main", t), MEM.__setitem__("writes", MEM["writes"] + 1),
                               True)[-1]
    gm._store_set_bad = lambda t: (MEM.__setitem__("bad", t), True)[-1]
    cm._store_get = lambda: MEM["main"]
    cm._store_set = gm._store_set
    cm._store_set_bad = gm._store_set_bad


def fixture(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


def v2_garage(seed=5):
    """Garage v2 rico: modulo, reliquia, skills aprendidas/equipadas, look, itens, cosmeticos, liga."""
    g = gm.new_game(random.Random(seed))
    g.scrap = 999
    g.flags = {"mod_on": 1, "ach_primeiro_gol": 1}
    m = g.new_piece("Módulo Curva", 2, 1)
    rel = g.new_piece("Meia do Prof. Ambrósio", 3)
    g.inventory += [m, rel, g.new_piece("Railgun de Bolso", 1, 2)]
    r = g.robots[4]
    assert g.equip(r["id"], m["id"])[0] and g.equip(r["id"], rel["id"])[0]
    r["skills"] = {"learned": {"curva": 2, "matador": 1, "leitura": 1}, "equipped": ["matador", "leitura"],
                   "pts": 4}
    r["look"] = {"decal": "raio", "trail": "fogo"}
    g.items = {"cera_turbo": 2, "cafe": 9}
    g.cosmetics = ["raio", "fogo", "bolo"]
    g.tactic = "ofensivo"
    rl.new_league(g, 0, random.Random(3))
    rl.advance_round(g.league, g, random.Random(4))
    return g


# ----------------------------------------------------------------- migracao v1 -> v2
def test_migrate_real_v1_robots_save_without_loss():
    raw = fixture("garage_v1_robots.json")
    v1 = json.loads(raw)
    assert v1["v"] == 1 and "items" not in v1 and "modulo" not in v1["robots"][0]["slots"]
    use_mem()
    MEM["main"] = raw
    assert gm.Garage.load_status() == gm.SAVE_OK
    g = gm.Garage.load()
    assert g is not None and MEM["bad"] is None and MEM["writes"] == 0
    d = g.to_dict()
    assert d["v"] == gm.VERSION == 2
    for f in V1_FIELDS:
        if f in ("robots", "flags"):
            continue
        assert d[f] == v1[f], f
    assert d["league"] is not None and d["league"] == v1["league"]
    assert d["shop"]["stock"] and d["shop"] == v1["shop"]
    # flags: todos preservados + mod_on (tier 1 ja concluido no Modo Robos)
    assert v1["tier_done"] >= gm.MOD_ON_TIER
    assert d["flags"] == dict(v1["flags"], mod_on=1)
    assert len(d["robots"]) == len(v1["robots"]) == 8
    for a, b in zip(v1["robots"], d["robots"]):
        for k in V1_ROBOT_KEYS:
            assert a[k] == b[k], (a["id"], k)
        assert b["slots"] == dict(a["slots"], modulo=None)
        assert b["skills"] == {"learned": {}, "equipped": [], "pts": skills.ph_for_level(a["level"])}
        assert b["look"] == {}
    assert d["items"] == {} and d["cosmetics"] == [] and d["cap"] == gm.MAX_LEVEL
    assert d["tactic"] == skills.DEFAULT_TACTIC
    assert max(r["level"] for r in d["robots"]) == 10
    # a migracao nao muta o dict de entrada
    v1b = json.loads(raw)
    gm.MIGRATIONS[1](v1b)
    assert v1b == json.loads(raw)
    # salva em v2 e volta identico (mesma chave)
    assert g.save() is True and MEM["writes"] == 1
    assert json.loads(MEM["main"])["v"] == 2
    g2 = gm.Garage.load()
    assert g2.to_dict() == d
    # garagem usavel: liga, recompensas, equipar
    g2.attrs_of(g2.robots[0])
    g2.rating()
    gm.match_rewards(g2, 2, 1, [g2.lineup[0]], 2, random.Random(1))


def test_migrate_tier_not_done_has_no_mod_on():
    v1 = json.loads(fixture("garage_v1_robots.json"))
    v1["tier_done"] = -1
    g = gm.Garage.from_dict(v1)
    assert g is not None and "mod_on" not in g.flags and not g.mod_on()


def test_campaign_real_v1_save_loads_and_saves_garage_v2():
    raw = fixture("campaign_v1_cap3.json")
    v1 = json.loads(raw)
    assert v1["v"] == 1 and v1["garage"]["v"] == 1
    use_mem()
    MEM["main"] = raw
    assert cm.Campaign.load_status() == cm.SAVE_OK
    c = cm.Campaign.load()
    assert c is not None and not c.repaired and c.warnings == [] and MEM["bad"] is None
    assert c.ch == v1["c"]["ch"] and c.node == v1["c"]["node"] and c.done == v1["c"]["done"]
    assert c.tour == v1["c"]["tour"] and c.stats == dict(v1["c"]["stats"], sides=0) and c.seed == v1["c"]["seed"]
    assert c.hero == v1["c"]["hero"] and c.pity == v1["c"]["pity"]
    g, gv1 = c.garage, v1["garage"]
    for f in V1_FIELDS:
        if f not in ("robots", "flags"):
            assert getattr(g, f) == gv1[f], f
    # campanha: mod_on e derivado de reward:rw_5 (nao do tier_done do garage) -> desligado no cap. 3
    assert gv1["tier_done"] >= 0 and "mod_on" not in g.flags and g.flags == gv1["flags"]
    assert g.cap == gm.MAX_LEVEL
    for a, b in zip(gv1["robots"], g.robots):
        assert all(a[k] == b[k] for k in V1_ROBOT_KEYS) and b["slots"] == dict(a["slots"], modulo=None)
    d = c.to_dict()
    assert d["v"] == cm.VERSION == 3 and d["garage"]["v"] == 2           # campanha v3 (Onda D), garage v2
    assert c.save() is True and MEM["writes"] == 1
    saved = json.loads(MEM["main"])
    assert saved["v"] == 3 and saved["garage"]["v"] == 2
    c2 = cm.Campaign.load()
    assert c2 is not None and c2.to_dict() == c.to_dict() and not c2.repaired
    # a campanha continua jogavel depois da migracao
    for _ in range(30):
        a = c2.next_action()
        if a["kind"] == "scene":
            has = any(isinstance(i, dict) for i in c2.scene_lines(a["id"]))
            c2.finish_scene(a["id"], 0 if has else None)
        elif a["kind"] == "match":
            c2.simulate_current()
        else:
            break


def test_campaign_unlocks_after_rw5():
    v1 = json.loads(fixture("campaign_v1_cap3.json"))
    v1["c"]["done"] = v1["c"]["done"] + ["reward:rw_5"]
    c = cm.Campaign.from_dict(v1)
    assert c is not None and c.garage.flags.get("mod_on") == 1 and c.garage.cap == gm.CAMPAIGN_CAP
    r = c.garage.robots[0]
    gm.add_xp(r, 10 ** 7, c.garage.cap)
    assert r["level"] == 15
    d = c.to_dict()
    c2 = cm.Campaign.from_dict(d)
    assert c2.garage.robots[0]["level"] == 15 and c2.to_dict() == d
    # sem o rw_5 o flag de sistema e removido (nunca liga antes do fim do Ato 1)
    v1 = json.loads(fixture("campaign_v1_cap3.json"))
    v1["garage"]["flags"]["mod_on"] = 1
    c3 = cm.Campaign.from_dict(v1)
    assert "mod_on" not in c3.garage.flags
    # apply_chapter_rewards do capitulo 5 liga (o caminho real do jogo)
    c4 = cm.Campaign.from_dict(json.loads(fixture("campaign_v1_cap3.json")))
    c4.done = [k for k in c4.done if k != "reward:rw_5"]
    c4.apply_chapter_rewards("5")
    assert c4.garage.mod_on() and c4.garage.cap == 15


def test_robot_mode_mod_on_on_tier1():
    g = gm.new_game(random.Random(8))
    assert not g.mod_on()
    rl.new_league(g, 0, random.Random(1))
    lg = g.league
    while not rl.is_finished(lg):
        rl.advance_round(lg, g, random.Random(2))
    pos = rl.user_position(lg)
    info = rl.finish_league(g, random.Random(3))
    assert g.mod_on() == info["advanced"] == (pos <= rl.ADVANCE_POS)


# ----------------------------------------------------------------- sanitize dos campos novos
def test_sanitize_invalid_ids_and_limits():
    g = v2_garage()
    d = g.to_dict()
    r0, r1 = d["robots"][0], d["robots"][1]
    r0["skills"] = {"learned": {"xyz": 1, "curva": 0, "leitura": 4, "muralha": "2", "matador": True,
                                "arrancada": 2, "rolando": 1, "lider": 3, 7: 1},
                    "equipped": ["arrancada", "arrancada", "nada", "leitura", "lider", None, "matador"],
                    "pts": 10 ** 9, "hack": 1}
    r0["look"] = {"decal": "fogo", "trail": "fogo", "antenna": "mola", "x": "raio"}
    r0["level"] = 14
    r1["skills"] = "lixo"
    r1["look"] = ["raio"]
    mid = d["inventory"][0]["id"]
    r1["slots"]["modulo"] = mid                                    # peca de outro slot no modulo
    d["items"] = {"cera_turbo": 50, "cafe": 0, "xyz": 3, "spray": -1, "fita_isolante": "3", "pilha_reserva": 2.7}
    d["cosmetics"] = ["raio", "raio", "nada", 3, "bolo", "fogo", "mola"]
    d["cap"] = 99
    d["tactic"] = "kamikaze"
    d["flags"] = dict({"f%d" % i: i for i in range(300)}, mod_on=1)
    c = gm.Garage.sanitize(d)
    assert c is not None
    s0 = c["robots"][0]["skills"]
    assert s0["learned"] == {"arrancada": 2, "lider": 3}
    assert s0["equipped"] == ["arrancada", "lider"] and s0["pts"] == skills.PTS_MAX
    assert c["robots"][0]["look"] == {"trail": "fogo", "antenna": "mola"}
    assert c["robots"][0]["level"] == 14 and c["cap"] == gm.CAMPAIGN_CAP
    assert c["robots"][1]["skills"] == skills.new_robot_skills() and c["robots"][1]["look"] == {}
    assert c["robots"][1]["slots"]["modulo"] is None
    assert c["items"] == {"cera_turbo": 9, "fita_isolante": 3, "pilha_reserva": 2}
    assert c["cosmetics"] == ["raio", "bolo", "fogo", "mola"]
    assert c["tactic"] == skills.DEFAULT_TACTIC
    assert len(c["flags"]) == gm.MAX_FLAGS == 128 and c["flags"]["mod_on"] == 1
    # cap 10 corta niveis acima; cap invalido -> 10
    d2 = g.to_dict()
    d2["robots"][0]["level"] = 15
    d2["robots"][0]["xp"] = 50
    d2["cap"] = "x"
    c2 = gm.Garage.sanitize(d2)
    assert c2["cap"] == 10 and c2["robots"][0]["level"] == 10 and c2["robots"][0]["xp"] == 0
    d2["cap"] = 15
    c3 = gm.Garage.sanitize(d2)
    assert c3["robots"][0]["level"] == 15 and c3["robots"][0]["xp"] == 0
    d2["robots"][0]["level"] = 12
    c4 = gm.Garage.sanitize(d2)
    assert c4["robots"][0]["level"] == 12 and c4["robots"][0]["xp"] == 50
    # carga: equipadas acima de LOAD_MAX sao cortadas na ordem
    d3 = g.to_dict()
    d3["robots"][0]["skills"] = {"learned": {"curva": 3, "muralha": 3, "leitura": 1}, "pts": 0,
                                 "equipped": ["curva", "muralha", "leitura"]}
    s = gm.Garage.sanitize(d3)["robots"][0]["skills"]
    assert s["equipped"] == ["curva", "muralha"] and sum(skills.load_of(k, 3) for k in s["equipped"]) == 6
    # modelo desconhecido / modulo em slot de equipamento
    d4 = g.to_dict()
    d4["inventory"].append({"id": 7777, "model": "Módulo Fantasma", "rar": 1, "lvl": 0})
    mod = next(p for p in d4["inventory"] if parts.PARTS[p["model"]]["slot"] == "modulo")
    d4["robots"][0]["slots"]["motor"] = mod["id"]
    c5 = gm.Garage.sanitize(d4)
    assert all(p["id"] != 7777 for p in c5["inventory"])
    assert c5["robots"][0]["slots"]["motor"] is None


def test_v2_roundtrip_and_idempotent():
    use_mem()
    g = v2_garage()
    d = g.to_dict()
    assert gm.Garage.sanitize(d) == d, "um garage v2 valido passa intacto no sanitize"
    assert g.save() is True
    g2 = gm.Garage.load()
    assert g2 is not None and g2.to_dict() == d
    assert g2.robots[4]["slots"]["modulo"] is not None and g2.items == {"cera_turbo": 2, "cafe": 9}
    assert g2.skills_of(g2.robots[4])[0] == ("curva", 2, 1)
    assert set(json.loads(MEM["main"])) == {"v"} | set(gm.FIELDS)
    assert len(gm.FIELDS) == len(V1_FIELDS) + 4


def test_fuzz_v2_mutations_never_raise():
    base = v2_garage().to_dict()
    rng = random.Random(2026)
    junk = [None, -1, 0, 1, 2, 15, 99, 10 ** 30, -10 ** 30, 1.5, float("nan"), float("inf"), True, "",
            "x" * 300, "arrancada", "mod_on", "\x00", [], [1, 2], {}, {"a": 1}, {"learned": {"curva": 9}},
            ["curva", "curva"], {"decal": "raio"}, "Módulo Curva", "Chip do Vovô"]

    def paths(o, pre=()):
        yield pre
        if isinstance(o, dict):
            for k, v in list(o.items()):
                yield from paths(v, pre + (k,))
        elif isinstance(o, list):
            for i, v in enumerate(o[:6]):
                yield from paths(v, pre + (i,))

    all_paths = [p for p in paths(base) if p]
    for it in range(2500):
        d = copy.deepcopy(base)
        for _ in range(rng.randint(1, 4)):
            p = rng.choice(all_paths)
            cur = d
            ok = True
            for k in p[:-1]:
                try:
                    cur = cur[k]
                except (KeyError, IndexError, TypeError):
                    ok = False
                    break
            if not ok:
                continue
            try:
                if rng.random() < 0.15 and isinstance(cur, dict):
                    cur.pop(p[-1], None)
                else:
                    cur[p[-1]] = rng.choice(junk)
            except (IndexError, TypeError):
                pass
        out = gm.Garage.sanitize(d)
        if out is None:
            continue
        assert set(out) == {"v"} | set(gm.FIELDS), it
        assert gm.Garage.sanitize(out) == out, ("sanitize idempotente", it)
        g = gm.Garage.from_dict(out)
        for r in g.robots:
            assert 1 <= r["level"] <= g.cap <= gm.CAMPAIGN_CAP
            g.attrs_of(r)
            g.skills_of(r)
            s = r["skills"]
            assert set(s["equipped"]) <= set(s["learned"]) and len(s["equipped"]) <= skills.MAX_EQUIPPED
        assert len(g.flags) <= gm.MAX_FLAGS and all(1 <= q <= skills.ITEM_MAX for q in g.items.values())
        # as mesmas mutacoes num save v1 (sem os campos novos) tambem nunca levantam
        d["v"] = 1
        gm.Garage.sanitize(d)
        cm.Campaign.sanitize({"v": 1, "sv": 1, "garage": d, "c": {}})


def test_invalid_v2_save_never_overwritten():
    use_mem()
    good = v2_garage()
    bad_texts = ['{"v": 2, "robots": "x"}', '{"v": 3}', "{oops", json.dumps(dict(good.to_dict(), v=99))]
    for raw in bad_texts:
        MEM.update({"main": raw, "bad": None, "writes": 0})
        assert gm.Garage.load_status() == gm.SAVE_BAD and MEM["bad"] is None
        assert gm.Garage.load() is None
        assert MEM["main"] == raw and MEM["bad"] == raw and MEM["writes"] == 0
    # save() so grava um estado valido; liga que nao sobreviveria ao sanitize -> nao grava
    MEM.update({"main": "{oops", "bad": None, "writes": 0})
    g = v2_garage()
    g.league = {"tier": 0}
    assert g.save() is False and MEM["main"] == "{oops"


# ----------------------------------------------------------------- build antigo (v1) lendo save v2
_OLD_CHECK = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import garage as gm, campaign as cm
text = open(sys.argv[2], encoding="utf-8").read()
camp = open(sys.argv[3], encoding="utf-8").read()
w = {"main": 0, "bad": None}
gm._store_get = lambda: text
gm._store_set = lambda t: w.__setitem__("main", w["main"] + 1) or True
gm._store_set_bad = lambda t: w.__setitem__("bad", t) or True
st = gm.Garage.load_status()
g = gm.Garage.load()
cm._store_get = lambda: camp
cm._store_set = gm._store_set
cbad = {}
cm._store_set_bad = lambda t: cbad.__setitem__("bad", t) or True
cst = cm.Campaign.load_status()
c = cm.Campaign.load()
print(json.dumps({"v": gm.VERSION, "status": st, "none": g is None, "bad_same": w["bad"] == text,
                  "writes": w["main"], "cstatus": cst, "cnone": c is None, "cbad_same": cbad.get("bad") == camp}))
'''


def test_old_build_reads_v2_as_bad():
    tmp = tempfile.mkdtemp(prefix="soccerpy_oldbuild_")
    try:
        try:
            arc = subprocess.run(["git", "-C", ROOT, "archive", V1_COMMIT, "game"], capture_output=True,
                                 timeout=60, check=True).stdout
            subprocess.run(["tar", "-x", "-C", tmp], input=arc, check=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as ex:
            print("  [PULADO] sem git/tar para extrair o build v1:", ex)
            return
        g = v2_garage()
        sp = os.path.join(tmp, "v2.json")
        with open(sp, "w", encoding="utf-8") as f:
            f.write(g.to_json())
        c = cm.Campaign.from_dict(json.loads(fixture("campaign_v1_cap3.json")))
        cp = os.path.join(tmp, "camp.json")
        with open(cp, "w", encoding="utf-8") as f:
            f.write(c.to_json())
        script = os.path.join(tmp, "check.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(_OLD_CHECK)
        out = subprocess.run([sys.executable, "-I", script, os.path.join(tmp, "game"), sp, cp],
                             capture_output=True, text=True, timeout=120, cwd=tmp)
        assert out.returncode == 0, out.stderr
        res = json.loads(out.stdout.strip().splitlines()[-1])
        assert res == {"v": 1, "status": "bad", "none": True, "bad_same": True, "writes": 0,
                       "cstatus": "bad", "cnone": True, "cbad_same": True}, res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_add_xp_cap_and_equip_rules():
    g = gm.new_game(random.Random(9))
    r = g.robots[0]
    assert gm.add_xp(r, 10 ** 7) == 9 and r["level"] == 10 and g.xp_to_next(r) == 0
    g.cap = gm.CAMPAIGN_CAP
    assert g.xp_to_next(r) == gm.xp_need(10)
    gm.match_rewards(g, 1, 0, [], 0, random.Random(1))
    assert r["xp"] > 0                               # cap 15: continua ganhando XP
    gm.add_xp(r, 10 ** 7, g.cap)
    assert r["level"] == 15 and g.xp_to_next(r) == 0
    m = g.new_piece("Módulo Recarga", 0)
    g.inventory.append(m)
    ok, msg = g.equip(r["id"], m["id"])
    assert not ok and "bloqueados" in msg
    g.flags["mod_on"] = 1
    ok, _ = g.equip(r["id"], m["id"])
    assert ok and r["slots"]["modulo"] == m["id"]
    ok, _ = g.equip(r["id"], m["id"], "motor")
    assert not ok
    assert g.unequip(r["id"], "modulo")[0] and r["slots"]["modulo"] is None


def test_cosmetics_buy_grant_equip_and_sanitize():
    """B13: cosmeticos so visuais - compra (1 vez, sucata), grant, equipar/desequipar por robo, sanitize
    do look (so ids conhecidos E desbloqueados) e `vis.look` aditivo (sem look o vis e o antigo)."""
    g = gm.new_game(random.Random(3))
    rb = g.robots[0]
    rid = rb["id"]
    pb = g.pieces_by_id()
    before = (gm.effective_attrs(rb, pb), g.rating(), gm.match_entry(rb, pb))
    assert set(before[2]["vis"]) == {"chassis", "paint", "parts", "hot"}
    g.scrap = 0
    assert g.buy_cosmetic("raio") == (False, "Sucata insuficiente (precisa de %d)." % parts.cosmetic_price("raio"))
    assert not g.buy_cosmetic("xyz")[0] and not g.equip_look(rid, "raio")[0]     # invalido / bloqueado
    g.scrap = 1000
    ok, msg = g.buy_cosmetic("raio")
    assert ok and g.scrap == 1000 - parts.COSMETIC_PRICE["decal"] and g.cosmetics == ["raio"]
    assert not g.buy_cosmetic("raio")[0] and g.scrap == 1000 - parts.COSMETIC_PRICE["decal"]
    assert g.grant_cosmetic("fogo") and not g.grant_cosmetic("fogo") and not g.grant_cosmetic("nada")
    assert g.grant_cosmetic("mola") and g.grant_cosmetic("fogos")
    for cid in ("raio", "fogo", "mola", "fogos"):
        assert g.equip_look(rid, cid)[0]
    assert rb["look"] == {"decal": "raio", "trail": "fogo", "antenna": "mola", "celebration": "fogos"}
    assert not g.equip_look(9999, "raio")[0]
    # so visual: atributos, rating e o resto da entrada da partida nao mudam
    e = gm.match_entry(rb, g.pieces_by_id())
    assert gm.effective_attrs(rb, pb) == before[0] and g.rating() == before[1]
    assert e["vis"]["look"] == rb["look"] and e["vis"]["look"] is not rb["look"]
    assert {k: v for k, v in e.items() if k != "vis"} == {k: v for k, v in before[2].items() if k != "vis"}
    assert g.unequip_look(rid, "trail")[0] and "trail" not in rb["look"]
    assert not g.unequip_look(rid, "trail")[0] and not g.unequip_look(rid, "xyz")[0]
    # ida e volta (save em memoria)
    use_mem()
    assert g.save()
    h = gm.Garage.load()
    assert h.robot(rid)["look"] == {"decal": "raio", "antenna": "mola", "celebration": "fogos"}
    assert h.cosmetics == ["raio", "fogo", "mola", "fogos"]
    # sanitize: look com id desbloqueado fica; bloqueado, de outro tipo ou desconhecido sai
    d = g.to_dict()
    d["robots"][0]["look"] = {"decal": "estrela", "antenna": "mola", "trail": "raio", "celebration": "fogos"}
    d["robots"][1]["look"] = {"decal": "raio", "trail": "fogo", "celebration": 5}
    d["cosmetics"] = ["raio", "fogo", "fogos"]
    c = gm.Garage.sanitize(d)
    assert c["robots"][0]["look"] == {"celebration": "fogos"}
    assert c["robots"][1]["look"] == {"decal": "raio", "trail": "fogo"}
    # ninguem desbloqueado: nenhum look sobrevive
    d["cosmetics"] = []
    assert all(r["look"] == {} for r in gm.Garage.sanitize(d)["robots"])


def test_mythic_pieces_and_reward_cosmetics():
    """Onda D: Mitica = Lendaria +2 de potencia; so equipamento (reliquia/modulo voltam a Lendaria no
    sanitize); loja e drops nunca a sorteiam; cosmeticos de recompensa nao se compram, so se ganham."""
    M, L = parts.MYTHIC, parts.LEGEND
    assert parts.RAR_NAMES[M] == "Mítica" and parts.POWER[M] == parts.POWER[L] + 2
    for m in ("Turbina", "Chip Zero", "Célula Longa"):
        assert parts.max_rarity(m) == M
        for lvl in range(parts.MAX_UP + 1):
            a, b = parts.part_bonus(m, M, lvl), parts.part_bonus(m, L, lvl)
            assert all(a[k] >= b[k] for k in a) and sum(a.values()) > sum(b.values())
    assert parts.max_rarity("Módulo Arrancada") == L and parts.max_rarity("Chip do Vovô") == L
    assert set(parts.MYTHIC_MODELS) <= set(parts.ALL_MODELS) and not set(parts.MYTHIC_MODELS) & set(parts.RELIC_MODELS)
    assert parts.part_name({"model": "Turbina", "rar": M, "lvl": 2}) == "Turbina Mítica +2"
    assert parts.upgrade_cost(M, 0) == 900 and parts.sell_price({"rar": M}) == 1500
    g = v2_garage(8)
    for tier in range(len(gm.TIER_MUL)):                     # loja nunca vende Mitica
        for k in range(40):
            g.refresh_shop(tier, random.Random(k))
            assert all(p["rar"] <= L for p in g.shop["stock"])
    pc, pm, pr = g.new_piece("Turbina", M), g.new_piece("Módulo Arrancada", M), g.new_piece("Chip do Vovô", M)
    g.inventory += [pc, pm, pr]
    g.shop["stock"].append(g.new_piece("Solenoide", M))
    d = json.loads(json.dumps(g.to_dict()))
    g2 = gm.Garage.from_dict(d)
    by = g2.pieces_by_id()
    assert by[pc["id"]]["rar"] == M and by[pm["id"]]["rar"] == L and by[pr["id"]]["rar"] == L
    assert all(p["rar"] <= L for p in g2.shop["stock"])
    rid = g2.lineup[0]
    assert g2.equip(rid, pc["id"])[0]
    g2.scrap = 10000
    ok, _msg = g2.upgrade(pc["id"])
    assert ok and g2.piece(pc["id"])["lvl"] == 1 and g2.scrap == 10000 - parts.upgrade_cost(M, 0)
    # cosmeticos finais
    rc = parts.REWARD_COSMETICS
    assert len(rc) == 7 and set(rc) <= parts.COSMETICS
    assert all(len(ids) <= 6 for ids in parts.LOOK_KINDS.values())
    assert all(parts.COSMETIC_NAMES[c] for c in parts.COSMETICS)
    for cid in rc:
        assert not parts.cosmetic_for_sale(cid)
        ok, msg = g2.buy_cosmetic(cid)
        assert not ok and "venda" in msg and cid not in g2.cosmetics and g2.scrap == 10000 - 900
        assert g2.grant_cosmetic(cid) and not g2.grant_cosmetic(cid)
        assert g2.equip_look(rid, cid)[0]
    assert parts.cosmetic_for_sale("raio") and not parts.cosmetic_for_sale("nope")


def main():
    saved = (gm._store_get, gm._store_set, gm._store_set_bad, cm._store_get, cm._store_set, cm._store_set_bad)
    names = [n for n in globals() if n.startswith("test_")]
    want = sys.argv[1:]
    if want:
        names = [n for n in names if n in want or n[5:] in want]
    try:
        for n in names:
            try:
                use_mem()
                globals()[n]()
                PASS.append(n)
                print("OK   %s" % n)
            except Exception as e:  # noqa: BLE001
                import traceback
                FAIL.append(n)
                print("FAIL %s: %r" % (n, e))
                traceback.print_exc()
    finally:
        (gm._store_get, gm._store_set, gm._store_set_bad, cm._store_get, cm._store_set,
         cm._store_set_bad) = saved
    print("\n%d ok, %d falhas" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
