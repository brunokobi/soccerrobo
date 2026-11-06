# -*- coding: utf-8 -*-
"""Fase 4 / Onda C (C2): Campaign v2 - migracao de saves v1/sv1 REAIS da campanha.

Os saves campaign_v1_{mid_cap5,chapter_end_cap5,epilogue_cap5,finished}.json de tests/fixtures/ foram
gerados SEM edicao pelo codigo do commit 076d6ab (campanha v1, roteiro 1: o epilogo era o no 4 do
cap. 5), jogando a campanha com simulate_current e parando: no meio do cap. 5 (antes da semifinal), no
chapter_end do cap. 5, no epilogo (cena ainda nao jogada) e com a campanha terminada.

Regras (docs/specs/campanha-expandida.md, secao 9): v 1->2 adiciona side/ng/endings/tower; sv 1->2 move
quem estava no epilogo ou depois (ch "5", node >= 4) para ch "6", node 0; ninguem volta no Ato 1.
Nada aqui grava em ~/.soccerpy_*: os stores sao trocados por dicionarios em memoria.

Rodar da raiz: .venv/bin/python tests/test_campaign_migration.py [nome_do_teste ...]
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import campaign as cm  # noqa: E402
import garage as gm  # noqa: E402
import story  # noqa: E402

PASS, FAIL = [], []


def is_campaign_end(c, a):
    """Fim do conteudo: "em breve" no 1o rascunho (se ainda houver) ou um dos finais de story.ENDINGS."""
    if any(x.get("draft") for x in story.CHAPTERS):
        return a == {"kind": "end", "draft": True} and bool(c.chapter().get("draft"))
    firsts = [e[1] if isinstance(e[1], str) else e[1][0] for e in story.ENDINGS]
    return a["kind"] == "end" and a.get("draft") is False and a.get("ending") in firsts


def last_chapter():
    return next((x["id"] for x in story.CHAPTERS if x.get("draft")), story.CHAPTERS[-1]["id"])


def n_titles():
    return sum(1 for r in story.REWARDS.values() if r.get("title"))
FIX = os.path.join(ROOT, "tests", "fixtures")
V1_COMMIT = "076d6ab"                    # ultimo commit com campanha v1 / roteiro 1
V2_COMMIT = "fd1686a"                    # ultimo commit com campanha v2 (Onda C publicada)
NAMES = ("mid_cap5", "chapter_end_cap5", "epilogue_cap5", "finished")
MEM = {}


def use_mem():
    MEM.clear()
    MEM.update({"main": None, "bad": None, "writes": 0})
    cm._store_get = lambda: MEM["main"]
    cm._store_set = lambda t: (MEM.__setitem__("main", t), MEM.__setitem__("writes", MEM["writes"] + 1),
                               True)[-1]
    cm._store_set_bad = lambda t: (MEM.__setitem__("bad", t), True)[-1]


def raw(name):
    with open(os.path.join(FIX, "campaign_v1_%s.json" % name), encoding="utf-8") as f:
        return f.read()


def v1(name):
    return json.loads(raw(name))


def load(name):
    """Carrega o save v1 pelo caminho real do jogo (store -> load)."""
    use_mem()
    MEM["main"] = raw(name)
    assert cm.Campaign.load_status() == cm.SAVE_OK, name
    c = cm.Campaign.load()
    assert c is not None and MEM["bad"] is None and MEM["writes"] == 0, name
    return c


def play_to_end(c, max_steps=400):
    """Joga ate {"kind":"end"}; devolve as cenas jogadas."""
    scenes = []
    for _ in range(max_steps):
        a = c.next_action()
        k = a["kind"]
        if k == "scene":
            scenes.append(a["id"])
            has = any(isinstance(i, dict) for i in c.scene_lines(a["id"]))
            c.finish_scene(a["id"], 0 if has else None)
        elif k == "match":
            c.record_match(2, 0)
        elif k == "chapter_end":
            assert c.advance_chapter() is not None
        elif k == "end":
            assert is_campaign_end(c, a), a
            return scenes
    raise AssertionError("nao chegou ao fim")


# --- fixtures --------------------------------------------------------------------------------
def test_fixtures_are_real_v1():
    for n in NAMES:
        d = v1(n)
        assert d["v"] == 1 and d["sv"] == 1 and d["garage"]["v"] == 2, n          # garage ja v2 (Onda B)
        assert set(d["c"]) == {"ch", "node", "done", "tour", "pity", "hero", "stats", "seed"}, n
        assert d["c"]["ch"] == "5", n
    assert v1("mid_cap5")["c"]["tour"]["stage"] == "SF"
    assert v1("chapter_end_cap5")["c"]["node"] == 3
    assert v1("epilogue_cap5")["c"]["node"] == 4 and "e1_epilogo" not in v1("epilogue_cap5")["c"]["done"]
    assert v1("finished")["c"]["node"] == 4 and "e1_epilogo" in v1("finished")["c"]["done"]


# --- regras comuns -----------------------------------------------------------------------------
def test_no_rewind_and_defaults_for_every_fixture():
    for n in NAMES:
        old = v1(n)
        c = load(n)
        assert not c.repaired and c.warnings == [], (n, c.warnings)
        assert c.done == old["c"]["done"], n                       # nada do Ato 1 e desfeito
        assert c.hero == old["c"]["hero"] and c.seed == old["c"]["seed"], n
        assert c.stats == dict(old["c"]["stats"], sides=0), n
        assert (c.side, c.ng, c.endings, c.tower) == (None, 0, [], None), n
        g = c.garage
        assert g.scrap == old["garage"]["scrap"] and g.stats == old["garage"]["stats"], n
        d = c.to_dict()
        assert d["v"] == cm.VERSION == 3 and d["sv"] == story.STORY_VERSION == 2, n
        assert c.save() is True and MEM["writes"] == 1, n          # salva sem reparo
        saved = json.loads(MEM["main"])
        assert saved["v"] == 3 and saved["sv"] == 2 and saved["garage"]["v"] == 2, n
        c2 = cm.Campaign.load()
        assert c2 is not None and not c2.repaired and c2.to_dict() == d, n


def test_migration_does_not_mutate_input():
    for n in NAMES:
        d = v1(n)
        before = copy.deepcopy(d)
        assert cm.Campaign.from_dict(d) is not None
        assert d == before, n


# --- cada ponto do cap. 5 ----------------------------------------------------------------------
def test_mid_cap5_keeps_tournament():
    old = v1("mid_cap5")
    c = load("mid_cap5")
    assert c.ch == "5" and c.node == old["c"]["node"] and c.tour == old["c"]["tour"]
    assert c.pity == old["c"]["pity"]
    a = c.next_action()
    assert a["kind"] == "match" and a["stage"] == "SF"
    scenes = play_to_end(c)
    assert scenes.count("e1_epilogo") == 1 and "c6_nestor" in scenes
    assert c.ch == last_chapter()
    assert c.garage.stats["titles"] == old["garage"]["stats"]["titles"] + n_titles()   # Mundial + Copa
    assert "reward:rw_5" in c.done and c.garage.mod_on() and c.garage.cap == gm.CAMPAIGN_CAP


def test_chapter_end_cap5_goes_to_cap6_epilogue():
    old = v1("chapter_end_cap5")
    c = load("chapter_end_cap5")
    assert c.ch == "5" and c.node == 3
    titles = c.garage.stats["titles"]
    a = c.next_action()
    assert a["kind"] == "chapter_end" and a["chapter"] == "5"
    assert a["report"]["applied"] is ("reward:rw_5" not in old["c"]["done"])
    assert c.advance_chapter() == "6" and c.node == 0
    a = c.next_action()
    assert a["kind"] == "scene" and a["id"] == "e1_epilogo"
    c.finish_scene("e1_epilogo")
    assert c.next_action()["id"] == "c6_nestor"                   # o Ato 2 segue
    assert c.garage.stats["titles"] == max(titles, 1)              # titulo do Mundial uma vez so


def test_epilogue_cap5_moves_to_cap6_and_plays_epilogue():
    c = load("epilogue_cap5")
    assert (c.ch, c.node, c.tour, c.pity) == ("6", 0, None, 0)
    a = c.next_action()
    assert a["kind"] == "scene" and a["id"] == "e1_epilogo"
    c.finish_scene("e1_epilogo")
    assert c.next_action()["id"] == "c6_nestor"


def test_finished_moves_to_cap6_and_skips_epilogue():
    old = v1("finished")
    c = load("finished")
    assert (c.ch, c.node, c.tour, c.pity) == ("6", 0, None, 0)
    a = c.next_action()                                           # epilogo ja jogado: nao repete
    assert a["kind"] == "scene" and a["id"] == "c6_nestor"       # quem terminou o Ato 1 entra no Ato 2
    assert c.done == old["c"]["done"] and c.garage.stats["titles"] == 1
    g = c.garage
    assert g.mod_on() and g.cap == gm.CAMPAIGN_CAP                # Ato 2 liberado (nivel 15, modulo)
    for r in g.robots:                                            # PH retroativos (migracao do garage)
        assert r["skills"]["pts"] >= 0


# --- migracoes isoladas ------------------------------------------------------------------------
def test_sv1_only_moves_cap5_from_node4():
    base = v1("mid_cap5")
    for ch, node, moved in (("5", 0, False), ("5", 3, False), ("5", 4, True), ("5", 9, True),
                            ("4", 4, False), ("5", True, False), ("5", "4", False)):
        d = copy.deepcopy(base)
        d["c"].update(ch=ch, node=node, tour={"x": 1}, pity=2)
        out = cm._migrate_sv1(copy.deepcopy(d))
        assert out["sv"] == 2
        if moved:
            assert (out["c"]["ch"], out["c"]["node"], out["c"]["tour"], out["c"]["pity"]) == ("6", 0, None, 0)
        else:
            assert out["c"] == d["c"], (ch, node)


def test_v1_migration_defaults_and_bad_c():
    d = v1("finished")
    out = cm._migrate_v1(copy.deepcopy(d))
    assert out["v"] == 2 and out["c"]["side"] is None and out["c"]["ng"] == 0
    assert out["c"]["endings"] == [] and out["c"]["tower"] is None
    for bad_c in (None, [], "x", 3):                               # `c` invalido continua "bad"
        d2 = v1("finished")
        d2["c"] = bad_c
        assert cm.Campaign.from_dict(d2) is None


# --- sanitize dos campos novos ------------------------------------------------------------------
def test_v2_fields_sanitize():
    good = load("finished").to_dict()
    cases = [
        ("side", {"id": "s_nope", "seed": 1, "loses": 0}, None, True),   # SIDES ainda vazio
        ("side", "x", None, True),
        ("side", None, None, False),
        ("ng", 2, 2, False), ("ng", 9, 0, True), ("ng", True, 0, True), ("ng", "1", 0, True),
        ("endings", ["e1_epilogo"], ["e1_epilogo"], False),
        ("endings", ["e1_epilogo", "e1_epilogo"], [], True),
        ("endings", ["nope"], [], True), ("endings", "x", [], True),
        ("endings", ["e1_epilogo", "c1_intro", "c2_intro", "c3_intro"], [], True),
        ("tower", {"floor": 3, "best": 7}, {"floor": 3, "best": 7}, False),
        ("tower", {"floor": 8, "best": 7}, None, True),
        ("tower", {"floor": 3, "best": 41}, None, True),
        ("tower", {"floor": 3, "best": 7, "x": 1}, {"floor": 3, "best": 7}, False),
    ]
    for key, val, want, warn in cases:
        d = copy.deepcopy(good)
        d["c"][key] = val
        c = cm.Campaign.from_dict(d)
        assert c is not None, (key, val)
        assert getattr(c, key) == want, (key, val, getattr(c, key))
        assert c.repaired is warn, (key, val, c.warnings)
        assert (c.ch, c.node) == ("6", 0), (key, val)              # campo novo invalido nao faz rewind


def test_side_and_done_keys_with_registered_side():
    orig = dict(story.SIDES)
    story.SIDES["s_teste"] = {}
    try:
        d = load("finished").to_dict()
        d["c"]["side"] = {"id": "s_teste", "seed": 5, "loses": 2}
        d["c"]["done"] = d["c"]["done"] + ["side:s_teste", "side:s_outro", "side:"]
        c = cm.Campaign.from_dict(d)
        assert c.side == {"id": "s_teste", "seed": 5, "loses": 2} and not c.repaired
        assert "side:s_teste" in c.done and "side:s_outro" not in c.done and "side:" not in c.done
        assert cm.Campaign.from_dict(c.to_dict()).to_dict() == c.to_dict()
    finally:
        story.SIDES.clear()
        story.SIDES.update(orig)


# --- build antigo ------------------------------------------------------------------------------
_OLD_CHECK = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import campaign as cm
assert cm.VERSION == 1
text = open(sys.argv[2], encoding="utf-8").read()
mem = {"main": text, "bad": None, "writes": 0}
cm._store_get = lambda: mem["main"]
def _set(t):
    mem["main"] = t
    mem["writes"] += 1
    return True
cm._store_set = _set
cm._store_set_bad = lambda t: (mem.__setitem__("bad", t), True)[-1]
status = cm.Campaign.load_status()
c = cm.Campaign.load()
print(json.dumps({"status": status, "none": c is None, "same": mem["main"] == text,
                  "bad_same": mem["bad"] == text, "writes": mem["writes"]}))
'''


def test_old_build_reads_campaign_v2_as_bad():
    tmp = tempfile.mkdtemp(prefix="soccerpy_oldcamp_")
    try:
        try:
            arc = subprocess.run(["git", "-C", ROOT, "archive", V1_COMMIT, "game"], capture_output=True,
                                 timeout=60, check=True).stdout
            subprocess.run(["tar", "-x", "-C", tmp], input=arc, check=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as ex:
            print("  [PULADO] sem git/tar para extrair o build v1:", ex)
            return
        c = load("finished")
        sp = os.path.join(tmp, "camp_v2.json")
        with open(sp, "w", encoding="utf-8") as f:
            f.write(c.to_json())
        script = os.path.join(tmp, "check.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(_OLD_CHECK)
        env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
        out = subprocess.run([sys.executable, "-I", script, os.path.join(tmp, "game"), sp],
                             capture_output=True, text=True, timeout=120, cwd=tmp, env=env)
        assert out.returncode == 0, out.stderr
        res = json.loads(out.stdout.strip().splitlines()[-1])
        assert res == {"status": "bad", "none": True, "same": True, "bad_same": True, "writes": 0}, res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- Onda D: v2 -> v3 ------------------------------------------------------------------------------
def test_v2_finished_save_migrates_to_v3_and_starts_ng():
    """Um save v2 TERMINADO (no "end" do cap. 13, final na galeria) vira v3 sem rewind e libera NG+/Torre."""
    c = load("finished")
    play_to_end(c)
    assert c.endings and c.finished()
    d = json.loads(c.to_json())
    d["v"] = 2                                                  # o formato v2 tinha os mesmos campos
    out = cm._migrate_v2(copy.deepcopy(d))
    assert out["v"] == 3 and out["c"] == d["c"]
    c2 = cm.Campaign.from_dict(copy.deepcopy(d))
    assert c2 is not None and not c2.repaired, c2 and c2.warnings
    assert (c2.ch, c2.node, c2.done, c2.endings) == (c.ch, c.node, c.done, c.endings)
    assert c2.next_action() == c.next_action() and c2.next_action()["kind"] == "end"
    assert c2.can_start_ng() and c2.tower_unlocked() and c2.tower_cfg()["tower"] == 1
    assert c2.start_ng() == 1 and c2.next_action()["id"] == story.NG_REVANCHE["1"]
    for bad_c in (None, [], "x"):                               # `c` invalido continua "bad"
        d2 = copy.deepcopy(d)
        d2["c"] = bad_c
        assert cm.Campaign.from_dict(d2) is None


def test_old_build_v2_reads_campaign_v3_as_bad():
    """Build v2 em cache abrindo um save v3 (com Mitica e chaves do NG+): "bad", preservado em .bad."""
    tmp = tempfile.mkdtemp(prefix="soccerpy_oldcamp2_")
    try:
        try:
            arc = subprocess.run(["git", "-C", ROOT, "archive", V2_COMMIT, "game"], capture_output=True,
                                 timeout=60, check=True).stdout
            subprocess.run(["tar", "-x", "-C", tmp], input=arc, check=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as ex:
            print("  [PULADO] sem git/tar para extrair o build v2:", ex)
            return
        c = load("finished")
        play_to_end(c)
        c.start_ng()
        g = c.garage
        g.inventory.append(g.new_piece("Turbina", 4))
        sp = os.path.join(tmp, "camp_v3.json")
        with open(sp, "w", encoding="utf-8") as f:
            f.write(c.to_json())
        script = os.path.join(tmp, "check.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(_OLD_CHECK.replace("assert cm.VERSION == 1", "assert cm.VERSION == 2"))
        env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
        out = subprocess.run([sys.executable, "-I", script, os.path.join(tmp, "game"), sp],
                             capture_output=True, text=True, timeout=120, cwd=tmp, env=env)
        assert out.returncode == 0, out.stderr
        res = json.loads(out.stdout.strip().splitlines()[-1])
        assert res == {"status": "bad", "none": True, "same": True, "bad_same": True, "writes": 0}, res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    names = [n for n in globals() if n.startswith("test_")]
    want = sys.argv[1:]
    if want:
        names = [n for n in names if n in want or n[5:] in want]
    saved = (cm._store_get, cm._store_set, cm._store_set_bad)
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
        cm._store_get, cm._store_set, cm._store_set_bad = saved
    print("\n%d ok, %d falhas" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
