"""Testes do save da campanha (game/campaign.py: Campaign.save/load/sanitize/load_status). Sem pygame.

Rodar da raiz: .venv/bin/python tests/test_campaign_save.py [teste ...]
Stores em memoria (campaign._store_*); garage/career/store.write falham se chamados indevidamente.
O unico teste de arquivo real usa tempfile.mkdtemp (removido ao final).
"""
import copy
import json
import os
import random
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import campaign as cm  # noqa: E402
import career  # noqa: E402
import garage as gm  # noqa: E402
import store  # noqa: E402
import story  # noqa: E402

PASS, FAIL = [], []
FORBIDDEN = []
ORIG = {"get": cm._store_get, "set": cm._store_set, "bad": cm._store_set_bad}
ORIG_PATH = cm.SAVE_PATH
MEM = {}


def _boom(*a, **k):
    FORBIDDEN.append(a)
    raise AssertionError("acesso proibido a store de garage/career")


for _m, _n in ((gm, "_store_get"), (gm, "_store_set"), (gm, "_store_set_bad"),
               (career, "_store_get"), (career, "_store_set")):
    if hasattr(_m, _n):
        setattr(_m, _n, _boom)


def use_mem():
    """Stores da campanha em memoria; MEM["main"] / MEM["bad"] / MEM["writes"]."""
    MEM.clear()
    MEM.update({"main": None, "bad": None, "writes": 0, "bad_writes": 0})
    cm._store_get = lambda: MEM["main"]

    def _set(text):
        MEM["main"] = text
        MEM["writes"] += 1
        return True

    def _bad(text):
        MEM["bad"] = text
        MEM["bad_writes"] += 1
        return True
    cm._store_set, cm._store_set_bad = _set, _bad


def new(seed=1):
    return cm.new_campaign(random.Random(seed))


def play_scenes(c, pick=0):
    for _ in range(80):
        a = c.next_action()
        if a["kind"] != "scene":
            return a
        has_choice = any(isinstance(i, dict) for i in c.scene_lines(a["id"]))
        c.finish_scene(a["id"], pick if has_choice else None)
    raise AssertionError("cenas sem fim")


def to_cap1(c):
    a = play_scenes(c)
    assert a["tournament"] == "t_p_treino"
    c.record_match(3, 0)
    a = play_scenes(c)
    assert a["kind"] == "chapter_end"
    assert c.advance_chapter() == "1"
    a = play_scenes(c)
    assert a["stage"] == "G1", a["stage"]
    return a


def mid_tour(seed=3):
    """Campanha no meio do torneio do Cap.1 (G1 e G2 jogados, G3 pendente)."""
    c = new(seed)
    to_cap1(c)
    c.record_match(3, 0)
    a = play_scenes(c)
    assert a["stage"] == "G2"
    c.record_match(2, 1)
    a = play_scenes(c)
    assert a["stage"] == "G3" and len(c.tour["results"]) == 2
    return c


def after_lost_final(seed=4):
    """Perdeu a final: pity 1, loses 1, done com '#'."""
    c = new(seed)
    to_cap1(c)
    for st in ("G1", "G2", "G3", "SF"):
        a = play_scenes(c)
        assert a["stage"] == st
        c.record_match(3, 0)
    a = play_scenes(c)
    assert a["stage"] == "F"
    c.record_match(0, 2)
    a = play_scenes(c)
    assert a["stage"] == "F" and c.pity == 1 and c.tour["loses"] == 1
    assert any("#" in k for k in c.done), c.done
    return c


def chapter_end_cap1(seed=5):
    """Cap.1 fechado: recompensa aplicada (recruta Gambiarra, pecas), parado no chapter_end."""
    c = new(seed)
    to_cap1(c)
    for st in ("G1", "G2", "G3", "SF", "F"):
        a = play_scenes(c)
        assert a["stage"] == st
        c.record_match(3, 0)
    a = play_scenes(c)
    assert a["kind"] == "chapter_end", a["kind"]
    assert "reward:rw_1" in c.done
    return c


def raw_of(c):
    use_mem()
    assert c.save() is True
    return MEM["main"]


def fresh_load(text):
    use_mem()
    MEM["main"] = text
    return cm.Campaign.load()


# --- ida e volta ------------------------------------------------------------------------
def test_roundtrip_mid_tournament():
    use_mem()
    c = mid_tour()
    assert c.save() is True and MEM["writes"] == 1
    c2 = cm.Campaign.load()
    assert c2 is not None and not c2.repaired and c2.warnings == []
    assert c2.to_dict() == c.to_dict()
    assert c2.tour["results"] == [["G1", 3, 0, 0, 0], ["G2", 2, 1, 0, 0]]
    assert c2.stats["ev"] == c.stats["ev"] > 0
    assert cm.Campaign.load_status() == "ok" and cm.Campaign.has_save()
    assert MEM["bad_writes"] == 0 and MEM["writes"] == 1          # load nao grava


def test_roundtrip_done_hash_and_reward_flags_recruits():
    use_mem()
    c = after_lost_final()
    c.garage.flags["denuncia"] = 1
    assert any("#" in k for k in c.done) and "reward:rw_P" in c.done
    assert c.save()
    c2 = cm.Campaign.load()
    assert c2.to_dict() == c.to_dict() and c2.garage.flags.get("denuncia") == 1
    c = chapter_end_cap1()
    assert any(r["name"] == "Gambiarra" for r in c.garage.robots)
    assert c.save()
    c2 = cm.Campaign.load()
    assert c2.to_dict() == c.to_dict()
    assert any(r["name"] == "Gambiarra" for r in c2.garage.robots)
    assert len(c2.garage.inventory) == len(c.garage.inventory) and "reward:rw_1" in c2.done
    assert c2.garage.unlocked == c.garage.unlocked and c2.garage.tier_done == c.garage.tier_done


def test_deterministic_after_reload_mid_tournament():
    c = mid_tour(9)
    text = raw_of(c)
    c2 = fresh_load(text)
    assert c2.to_dict() == c.to_dict()
    a1, a2 = c.next_action(), c2.next_action()
    assert [e["name"] for e in a1["opp"]["squad"]] == [e["name"] for e in a2["opp"]["squad"]]
    assert a1["O"] == a2["O"] and a1["opp"]["name"] == a2["opp"]["name"]
    assert a1["opp"] == a2["opp"] and a1["home"] == a2["home"]
    assert c.group_table() == c2.group_table()
    outs = []
    for cc in (c, c2):
        seq = []
        for _ in range(4):
            act = play_scenes(cc)
            if act["kind"] != "match":
                break
            r = cc.simulate_current()
            seq.append((act["stage"], act["opp"]["name"], act["O"], r["my"], r["opp"], r["pen"],
                        r["outcome"]))
        outs.append((seq, cc.to_dict()))
    assert outs[0] == outs[1] and len(outs[0][0]) >= 2


# --- ausencia / chaves desconhecidas -------------------------------------------------------
def test_absent_is_none():
    use_mem()
    assert cm.Campaign.load_status() == "none" and cm.Campaign.load() is None
    assert not cm.Campaign.has_save() and MEM["writes"] == 0 and MEM["bad_writes"] == 0


def test_unknown_keys_ignored_methods_intact():
    c = mid_tour()
    d = copy.deepcopy(c.to_dict())
    evil = {"save": 1, "load": 2, "sanitize": 3, "next_action": 4, "to_dict": 5, "from_dict": 6,
            "garage": 7, "__class__": 8, "_rng": 9, "stats": 10}
    for k, v in evil.items():
        if k not in ("garage", "stats"):
            d[k] = v
            d["c"][k] = v
    d["c"]["extra"] = {"a": [1, 2]}
    d["garage"]["save"] = "x"
    c2 = cm.Campaign.from_dict(d)
    assert c2 is not None and not c2.repaired
    assert c2.to_dict() == c.to_dict()
    for k in ("save", "load", "sanitize", "next_action", "to_dict", "_rng"):
        assert callable(getattr(c2, k)), k
    assert callable(cm.Campaign.load) and callable(cm.Campaign.sanitize)
    assert c2.next_action()["kind"] in ("scene", "match")
    assert "save" not in vars(c2) and "next_action" not in vars(c2)


# --- corrompidos -----------------------------------------------------------------------------
def _mut(fn):
    d = copy.deepcopy(mid_tour().to_dict())
    fn(d)
    return d


def _bad_cases():
    cases = {}
    cases["root_list"] = lambda d: [d]
    cases["root_str"] = lambda d: "oi"
    cases["root_none"] = lambda d: None
    for name, val in (("v_absent", ...), ("v_zero", 0), ("v_neg", -1), ("v_future", 99), ("v_str", "1"),
                      ("v_bool", True), ("v_float", 1.0)):
        def f(d, val=val):
            if val is ...:
                del d["v"]
            else:
                d["v"] = val
            return d
        cases[name] = f
    for name, val in (("sv_absent", ...), ("sv_future", story.STORY_VERSION + 1), ("sv_zero", 0),
                      ("sv_str", "1")):
        def f(d, val=val):
            if val is ...:
                del d["sv"]
            else:
                d["sv"] = val
            return d
        cases[name] = f
    cases["garage_absent"] = lambda d: (d.pop("garage"), d)[1]
    cases["garage_str"] = lambda d: (d.__setitem__("garage", "x"), d)[1]
    cases["garage_few_robots"] = lambda d: (d["garage"].__setitem__("robots", d["garage"]["robots"][:2]), d)[1]
    cases["garage_v_future"] = lambda d: (d["garage"].__setitem__("v", 99), d)[1]
    cases["c_absent"] = lambda d: (d.pop("c"), d)[1]
    cases["c_list"] = lambda d: (d.__setitem__("c", []), d)[1]
    cases["done_str"] = lambda d: (d["c"].__setitem__("done", "abc"), d)[1]
    cases["done_huge"] = lambda d: (d["c"].__setitem__("done", ["p1_garagem"] * 5000), d)[1]
    return cases


def test_bad_cases_return_none():
    for name, fn in _bad_cases().items():
        d = copy.deepcopy(mid_tour().to_dict())
        d = fn(d)
        assert cm.Campaign.sanitize(d) is None, name
        assert cm.Campaign.from_dict(d) is None, name
        text = json.dumps(d)
        c = fresh_load(text)
        assert c is None and cm.Campaign.load_status() == "bad", name
        assert MEM["main"] == text and MEM["bad"] == text and MEM["writes"] == 0, name


def test_repair_cases_rewind():
    ch1 = mid_tour()
    cases = {
        "ch_unknown": lambda d: d["c"].__setitem__("ch", "zzz"),
        "ch_draft": lambda d: d["c"].__setitem__("ch", "2"),
        "ch_type": lambda d: d["c"].__setitem__("ch", 7),
        "node_big": lambda d: d["c"].__setitem__("node", 99),
        "node_neg": lambda d: d["c"].__setitem__("node", -1),
        "node_str": lambda d: d["c"].__setitem__("node", "1"),
        "node_mismatch": lambda d: d["c"].__setitem__("node", 0),
        "tour_id_unknown": lambda d: d["c"]["tour"].__setitem__("id", "nada"),
        "tour_id_other": lambda d: d["c"]["tour"].__setitem__("id", "t_p_treino"),
        "tour_id_type": lambda d: d["c"]["tour"].__setitem__("id", ["x"]),
        "tour_stage_bad": lambda d: d["c"]["tour"].__setitem__("stage", "Z9"),
        "tour_stage_qf": lambda d: d["c"]["tour"].__setitem__("stage", "QF"),
        "tour_not_dict": lambda d: d["c"].__setitem__("tour", [1]),
        "score_huge": lambda d: d["c"]["tour"]["results"][0].__setitem__(1, 5000),
        "score_neg": lambda d: d["c"]["tour"]["results"][0].__setitem__(2, -1),
        "pen_huge": lambda d: d["c"]["tour"]["results"][0].__setitem__(3, 100),
        "results_many": lambda d: d["c"]["tour"].__setitem__("results", [["G1", 1, 0, 0, 0]] * 40),
        "results_short": lambda d: d["c"]["tour"]["results"][0].pop(),
        "results_order": lambda d: d["c"]["tour"]["results"].reverse(),
        "results_future": lambda d: d["c"]["tour"]["results"].append(["SF", 1, 0, 0, 0]),
        "attempt_huge": lambda d: d["c"]["tour"].__setitem__("attempt", 5000),
        "attempt_float": lambda d: d["c"]["tour"].__setitem__("attempt", 1.5),
        "tour_seed_str": lambda d: d["c"]["tour"].__setitem__("seed", "9"),
        "loses_huge": lambda d: d["c"]["tour"].__setitem__("loses", 10 ** 9),
        "pity_huge": lambda d: d["c"].__setitem__("pity", 10 ** 12),
        "pity_neg": lambda d: d["c"].__setitem__("pity", -2),
        "pity_str": lambda d: d["c"].__setitem__("pity", "2"),
    }
    for name, fn in cases.items():
        d = copy.deepcopy(ch1.to_dict())
        fn(d)
        c = cm.Campaign.from_dict(d)
        assert c is not None, name
        assert c.repaired and c.warnings, name
        assert c.node == 0 and c.tour is None and c.pity == 0, (name, c.node, c.tour, c.pity)
        assert c.ch in ("P", "1"), name
        if name in ("ch_unknown", "ch_draft", "ch_type"):
            assert c.ch == "1", (name, c.ch)           # recompensa de P ja em done -> capitulo 1
        else:
            assert c.ch == "1"
        assert c.stats["ev"] == ch1.stats["ev"] and c.garage.to_dict() == ch1.garage.to_dict(), name
        assert c.next_action()["kind"] in ("scene", "match"), name


def test_ch_invalid_goes_to_first_unrewarded_chapter():
    c = new(2)
    d = c.to_dict()
    d["c"]["ch"] = "nope"
    d["c"]["node"] = 3
    r = cm.Campaign.from_dict(d)
    assert r.ch == "P" and r.node == 0 and r.repaired
    c = chapter_end_cap1()
    d = c.to_dict()
    d["c"]["ch"] = "2"
    r = cm.Campaign.from_dict(d)
    assert r.ch == "1" and r.repaired      # todos os jogaveis fechados -> ultimo jogavel


def test_hero_missing_uses_first_starter():
    c = mid_tour()
    d = c.to_dict()
    for bad in (999999, "x", None, True, 1.5):
        d["c"]["hero"] = bad
        r = cm.Campaign.from_dict(d)
        assert r.hero == r.garage.lineup[0] and r.garage.robot(r.hero) is not None
        assert r.repaired and r.tour == c.tour          # sem rewind por causa do heroi


def test_other_fields_repairs():
    c = mid_tour()
    d = c.to_dict()
    d["c"]["seed"] = "abc"
    d["c"]["stats"] = {"ev": -5, "matches": 10 ** 15, "sims": "x"}
    r = cm.Campaign.from_dict(d)
    assert r.seed == 1 and r.stats == {"ev": 0, "matches": 0, "sims": 0, "trained": 0} and r.repaired
    assert r.tour == c.tour
    d = c.to_dict()
    d["c"]["done"] = ["p1_garagem", "p1_garagem", "x", "nada#1", "p1_garagem#100", "p1_garagem#01",
                      "p1_garagem#-1", "reward:rw_P", "reward:zzz", 5, None, "c1_final_lose#2",
                      "reward:", "#1", "p1_garagem#"]
    r = cm.Campaign.from_dict(d)
    assert r.done == ["p1_garagem", "reward:rw_P", "c1_final_lose#2"] and not r.repaired
    assert r.tour == c.tour


def test_done_cap_keeps_rewards():
    keys = ["reward:rw_P", "reward:rw_1", "p1_garagem"]
    keys += ["c1_final_lose#%d" % i for i in range(100)] + ["c1_repescagem#%d" % i for i in range(100)]
    keys += ["c1_final_pre#%d" % i for i in range(100)] + ["c1_intro#%d" % i for i in range(100)]
    d = new().to_dict()
    d["c"]["done"] = keys
    r = cm.Campaign.from_dict(d)
    assert len(r.done) == cm.MAX_DONE and set(keys[:3]) <= set(r.done)
    assert cm.Campaign.sanitize(r.to_dict())["c"]["done"] == r.done


def test_sv_older_without_migration_rewinds(monkeypatch=None):
    old = story.STORY_VERSION
    try:
        story.STORY_VERSION = old + 1
        d = copy.deepcopy(mid_tour().to_dict())          # to_dict usa o STORY_VERSION atual
        d["sv"] = old
        c = cm.Campaign.from_dict(d)
        assert c is not None and c.repaired and c.node == 0 and c.tour is None
        cm.MIGRATIONS[("sv", old)] = lambda x: x
        try:
            c = cm.Campaign.from_dict(d)
            assert c is not None and not c.repaired and c.tour is not None
        finally:
            del cm.MIGRATIONS[("sv", old)]
    finally:
        story.STORY_VERSION = old


# --- store: leitura que falha / bytes invalidos -----------------------------------------------
def test_read_error_is_bad_not_none():
    use_mem()
    cm._store_get = lambda: store.ERROR
    assert cm.Campaign.load_status() == "bad" and cm.Campaign.has_save()
    assert cm.Campaign.load() is None
    assert MEM["bad_writes"] == 0 and MEM["writes"] == 0          # nada cru para guardar


def test_invalid_bytes_is_bad():
    use_mem()
    good = raw_of(mid_tour())
    use_mem()
    cm._store_get = lambda: store.InvalidText(good)               # pareceria JSON valido
    assert cm.Campaign.load_status() == "bad"
    assert cm.Campaign.load() is None
    assert MEM["bad"] == good and MEM["main"] is None and MEM["writes"] == 0


def test_real_file_invalid_utf8():
    tmp = tempfile.mkdtemp(prefix="soccerpy_cs_")
    try:
        cm._store_get, cm._store_set, cm._store_set_bad = ORIG["get"], ORIG["set"], ORIG["bad"]
        cm.SAVE_PATH = os.path.join(tmp, "campaign.json")
        assert cm.Campaign.load_status() == "none"
        good = raw_of_real(mid_tour())
        assert cm.Campaign.load_status() == "ok" and cm.Campaign.load().to_dict() == mid_tour().to_dict()
        with open(cm.SAVE_PATH, "wb") as f:
            f.write(good.encode("utf-8")[:50] + b"\xff\xfe\xfa" + good.encode("utf-8")[50:])
        assert cm.Campaign.load_status() == "bad"
        assert cm.Campaign.load() is None
        assert os.path.exists(cm.SAVE_PATH + ".bad")
        with open(cm.SAVE_PATH, "rb") as f:
            assert b"\xff\xfe\xfa" in f.read()                   # original intacto
        assert os.listdir(tmp)
        assert all(p.startswith("campaign.json") for p in os.listdir(tmp))
    finally:
        cm.SAVE_PATH = ORIG_PATH
        shutil.rmtree(tmp, ignore_errors=True)
        use_mem()


def raw_of_real(c):
    assert os.path.dirname(cm.SAVE_PATH) != os.path.expanduser("~")
    assert c.save() is True
    with open(cm.SAVE_PATH, encoding="utf-8") as f:
        return f.read()


# --- save invalido nao sobrescreve ------------------------------------------------------------
def test_bad_save_never_overwritten_and_raw_in_bad():
    good = raw_of(mid_tour())
    for text in ("{not json", "[]", json.dumps({"v": 1}), "", "null", "9" * 20,
                 good.replace('"sv":1', '"sv":99'), "[" * 5000 + "]" * 5000,
                 good + " " * (cm.MAX_SAVE_CHARS + 1)):
        use_mem()
        MEM["main"] = text
        assert cm.Campaign.load_status() == "bad", text[:30]
        assert MEM["bad_writes"] == 0
        assert cm.Campaign.load() is None
        assert MEM["main"] == text and MEM["writes"] == 0
        assert MEM["bad"] == text and MEM["bad_writes"] == 1
        assert cm.Campaign.load() is None and MEM["main"] == text


def test_load_never_saves():
    d = json.loads(raw_of(mid_tour()))
    use_mem()
    d["c"]["ch"] = "2"
    MEM["main"] = json.dumps(d)
    before = MEM["main"]
    c = cm.Campaign.load()
    assert c is not None and c.repaired
    assert MEM["main"] == before and MEM["writes"] == 0 and MEM["bad_writes"] == 0
    assert c.save() is True                  # rewind ja aplicado em memoria: agora salva reparado
    assert MEM["writes"] == 1 and json.loads(MEM["main"])["c"]["node"] == 0


# --- so a chave da campanha -------------------------------------------------------------------
def test_only_campaign_key_touched():
    use_mem()
    del FORBIDDEN[:]
    c = after_lost_final()
    assert c.save()
    assert cm.Campaign.load() is not None
    assert cm.Campaign.load_status() == "ok" and cm.Campaign.has_save()
    MEM["main"] = "lixo"
    cm.Campaign.load()
    assert FORBIDDEN == []
    assert cm.SAVE_KEY == "soccerpy_campaign_v1" and cm.SAVE_KEY != gm.SAVE_KEY
    assert cm.SAVE_PATH.endswith(".soccerpy_campaign.json")
    assert cm.SAVE_PATH != gm.SAVE_PATH
    # as chamadas reais dos stores usam as chaves certas
    seen = []
    real_write, real_read = store.write, store.read
    store.write = lambda k, p, t: seen.append((k, p)) or True
    store.read = lambda k, p: seen.append((k, p))
    try:
        ORIG["set"]("x")
        ORIG["bad"]("x")
        ORIG["get"]()
    finally:
        store.write, store.read = real_write, real_read
    assert [k for k, _ in seen] == ["soccerpy_campaign_v1", "soccerpy_campaign_v1.bad",
                                    "soccerpy_campaign_v1"]
    assert all("robots" not in p and "career" not in p for _, p in seen)


def test_save_refuses_state_failing_sanitize():
    use_mem()
    c = mid_tour()
    assert c.save() and MEM["writes"] == 1
    kept = MEM["main"]
    bad_states = []
    for fn in (lambda c: setattr(c, "ch", "nope"), lambda c: setattr(c, "node", 77),
               lambda c: setattr(c, "pity", 50), lambda c: c.tour.__setitem__("stage", "X"),
               lambda c: setattr(c, "hero", -1), lambda c: setattr(c, "ch", "2"),
               lambda c: c.tour["results"].append(["G3", 999, 0, 0, 0]),
               lambda c: c.garage.robots.clear(), lambda c: setattr(c, "garage", None),
               lambda c: setattr(c, "done", None), lambda c: setattr(c, "stats", None),
               lambda c: c.stats.__setitem__("ev", -1)):
        cc = mid_tour()
        try:
            fn(cc)
        except Exception:  # noqa: BLE001
            pass
        bad_states.append(cc)
    for i, cc in enumerate(bad_states):
        assert cc.save() is False, i
    assert MEM["main"] == kept and MEM["writes"] == 1
    cm._store_set = lambda t: False                      # falha de escrita
    assert mid_tour().save() is False


def test_save_never_calls_garage_save():
    called = []
    orig = gm.Garage.save
    gm.Garage.save = lambda self: called.append(1) or True
    try:
        use_mem()
        c = mid_tour()
        c.save()
        cm.Campaign.load()
        c.apply_chapter_rewards()
        assert called == []
    finally:
        gm.Garage.save = orig


# --- sanitize: invariantes e fuzz ---------------------------------------------------------------
def _pick_paths(obj, path=()):
    out = [path]
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += _pick_paths(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:12]):
            out += _pick_paths(v, path + (i,))
    return out


def _set(obj, path, val):
    for k in path[:-1]:
        obj = obj[k]
    obj[path[-1]] = val


def _del(obj, path):
    for k in path[:-1]:
        obj = obj[k]
    if isinstance(obj, dict):
        obj.pop(path[-1], None)
    else:
        del obj[path[-1]]


JUNK = [None, True, False, 0, -1, 1, 99, 10 ** 30, -10 ** 30, 1.5, float("nan"), float("inf"), "", "x",
        "G1", "t_c1", "1", "P", "reward:rw_1", [], [[]], {}, {"a": 1}, [1, 2, 3], "ç中", "A" * 500,
        ["c1_intro", 5], {"id": "t_c1"}]


def test_fuzz_mutations_no_exception_and_invariants():
    rnd = random.Random(20260702)
    bases = [mid_tour(3).to_dict(), after_lost_final().to_dict(), chapter_end_cap1().to_dict(),
             new(8).to_dict()]
    loaded = bad = 0
    for n in range(400):
        d = copy.deepcopy(rnd.choice(bases))
        for _ in range(rnd.randint(1, 4)):
            paths = [p for p in _pick_paths(d) if p]
            if not paths:
                break
            p = rnd.choice(paths)
            try:
                if rnd.random() < 0.2:
                    _del(d, p)
                else:
                    _set(d, p, copy.deepcopy(rnd.choice(JUNK)))
            except Exception:  # noqa: BLE001
                pass
        # sanitize e from_dict nunca levantam
        s = cm.Campaign.sanitize(d)
        c = cm.Campaign.from_dict(d)
        assert (s is None) == (c is None), n
        if s is None:
            bad += 1
            continue
        loaded += 1
        assert s["v"] == cm.VERSION and s["sv"] == story.STORY_VERSION
        # idempotente
        assert cm.Campaign.sanitize(s) == s, n
        assert cm.Campaign.sanitize(c.to_dict()) == s, n
        # invariantes do carregado
        cd = s["c"]
        ch = next(x for x in story.CHAPTERS if x["id"] == cd["ch"])
        assert not ch.get("draft") and 0 <= cd["node"] < len(ch["nodes"])
        assert 0 <= cd["pity"] <= story.PITY_MAX and len(cd["done"]) <= cm.MAX_DONE
        assert cd["hero"] in [r["id"] for r in s["garage"]["robots"]]
        assert all(isinstance(cd["stats"][k], int) and cd["stats"][k] >= 0 for k in cm.STAT_KEYS)
        if cd["tour"] is not None:
            t = cd["tour"]
            assert t["id"] in story.TOURNAMENTS and len(t["results"]) <= cm.MAX_RESULTS
            assert all(0 <= x <= 99 for r in t["results"] for x in r[1:])
        # round-trip pelo texto + o jogo segue funcionando
        c2 = fresh_load(json.dumps(s))
        assert c2 is not None and c2.to_dict() == c.to_dict(), n
        act = c2.next_action()
        assert act["kind"] in ("scene", "match", "chapter_end", "end"), n
        if act["kind"] == "match":
            c2.simulate_current()
    assert loaded > 40 and bad > 20, (loaded, bad)


def test_fuzz_raw_text_never_raises():
    rnd = random.Random(7)
    good = raw_of(mid_tour())
    for n in range(200):
        t = list(good)
        for _ in range(rnd.randint(1, 6)):
            i = rnd.randrange(len(t))
            t[i] = rnd.choice(['"', "{", "}", "[", "x", "9", ",", ":", "\\", "\u0000", " "])
        text = "".join(t)
        use_mem()
        MEM["main"] = text
        st = cm.Campaign.load_status()
        c = cm.Campaign.load()
        assert st in ("ok", "bad") and (c is None) == (st == "bad"), n
        assert MEM["main"] == text and MEM["writes"] == 0
        if st == "bad":
            assert MEM["bad"] == text


def test_sanitize_never_raises_on_garbage():
    class Weird:
        def __getitem__(self, k):
            raise RuntimeError("x")
    deep = cur = []
    for _ in range(3000):
        nxt = []
        cur.append(nxt)
        cur = nxt
    for x in (None, 1, "s", [], Weird(), deep, {"v": 1, "sv": 1, "garage": deep, "c": deep},
              {"v": 1, "sv": 1, "garage": {}, "c": {}}, object(), float("nan")):
        assert cm.Campaign.sanitize(x) is None
        assert cm.Campaign.from_dict(x) is None


def main():
    names = sys.argv[1:] or [n for n in globals() if n.startswith("test_")]
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
    print("\n%d testes passaram, %d falhas" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
