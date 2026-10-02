"""Testes da persistencia do modo robos (passo 5): store.py + Garage.save/load/sanitize.

Sem pygame. NUNCA toca ~/.soccerpy_*.json: o store e trocado por um dict em memoria
(e, nos testes de arquivo, por caminhos no scratchpad). Rodar da raiz:
    .venv/bin/python tests/test_robot_save.py [nome_do_teste ...]
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

import garage as gm  # noqa: E402
import parts  # noqa: E402
import robot_league as rl  # noqa: E402
import robots  # noqa: E402
import store  # noqa: E402

SCRATCH = tempfile.mkdtemp(prefix="soccerpy_save_test_")      # removido ao final (main)
PASS, FAIL = [], []
KEY = gm.SAVE_KEY
BAD = KEY + ".bad"
CAREER_KEY = "soccerpy_career_v1"
CAREER_SENTINEL = '{"play_round": 3, "user": null, "season": 9}'

MEM = {}
LOG = []                      # (op, key)
_REAL = (store.read, store.write, gm.SAVE_PATH)


def _read(key, path):
    LOG.append(("r", key))
    return MEM.get(key)


def _write(key, path, text):
    LOG.append(("w", key))
    MEM[key] = text
    return True


def setup():
    """Store em memoria zerado, com a carreira como sentinela."""
    MEM.clear()
    LOG.clear()
    MEM[CAREER_KEY] = CAREER_SENTINEL
    store.read, store.write = _read, _write
    gm.SAVE_PATH = os.path.join(SCRATCH, "robots_never_used.json")


def teardown():
    store.read, store.write, gm.SAVE_PATH = _REAL


def played_game(seed=3):
    """Garage com liga em andamento, loja, flags, pecas equipadas, upgrade e oc."""
    g = gm.new_game(random.Random(seed))
    g.scrap = 777
    g.team["name"] = "Aspiradores"
    g.robots[1]["oc"] = 2
    g.robots[2]["level"], g.robots[2]["xp"] = 4, 33
    g.robots[3]["paint"] = [1, 2, 3]
    g.robots[3]["name"] = "Faíscão"
    g.inventory.append(g.new_piece("Turbina", 2, 3))
    g.equip(g.robots[0]["id"], g.inventory[-1]["id"])
    g.flags = {"tutorial": 1, "visit": 12}
    g.stats = {"played": 3, "w": 2, "d": 0, "l": 1, "titles": 1}
    g.unlocked.append("Tanque")
    g.tier_done = 0
    rl.new_league(g, 1, random.Random(5))
    lg = g.league
    for _ in range(3):
        rl.advance_round(lg, g, random.Random(9))
    return g


def valid_dict():
    return played_game().to_dict()


def put(d):
    MEM[KEY] = json.dumps(d)


def put_raw(text):
    MEM[KEY] = text


def check_invariants(g):
    """Garage carregado e consistente e utilizavel."""
    assert gm.MIN_SQUAD <= len(g.robots) <= gm.MAX_SQUAD
    ids = [r["id"] for r in g.robots]
    assert len(set(ids)) == len(ids)
    assert len(g.lineup) == 5 and len(set(g.lineup)) == 5 and set(g.lineup) <= set(ids)
    assert len(g.inventory) <= gm.MAX_INVENTORY and len(g.flags) <= gm.MAX_FLAGS
    assert 0 <= g.scrap <= gm.SCRAP_MAX
    used = []
    for r in g.robots:
        assert 1 <= r["level"] <= 10 and r["xp"] >= 0 and 0 <= r["oc"] <= 2
        assert len(r["name"]) <= gm.NAME_MAX_ROBOT and len(r["paint"]) == 3
        assert all(isinstance(c, int) and 0 <= c <= 255 for c in r["paint"])
        assert r["chassis"] in robots.CHASSIS and r["role"] in gm.ROLES
        assert set(r["base"]) == set(robots.ATTRS)
        assert all(20 <= v <= 99 for v in r["base"].values())
        for s, pid in r["slots"].items():
            if pid is not None:
                pc = g.piece(pid)
                assert pc is not None and parts.part_slot(pc) == s
                used.append(pid)
    assert len(used) == len(set(used))
    assert len(g.team["name"]) <= gm.NAME_MAX_TEAM
    for r in g.robots:
        g.attrs_of(r)
        g.entry(r)
    g.rating()
    g.match_cfg()
    assert gm.Garage.sanitize(g.to_dict()) is not None
    json.dumps(g.to_dict())


def expect_none_and_bad(raw=None, expect_bad=True):
    """load() devolve None, nao sobrescreve a chave e (opcionalmente) grava .bad."""
    before = MEM.get(KEY)
    n_writes = [k for op, k in LOG if op == "w" and k == KEY]
    assert gm.Garage.load_status() == gm.SAVE_BAD
    assert gm.Garage.load() is None
    assert MEM.get(KEY) == before, "save invalido foi sobrescrito"
    assert [k for op, k in LOG if op == "w" and k == KEY] == n_writes
    if expect_bad:
        assert MEM.get(BAD) == before, ".bad nao foi gravado"
    assert MEM[CAREER_KEY] == CAREER_SENTINEL


def run_with_store(fn):
    def wrapper():
        setup()
        try:
            fn()
        finally:
            teardown()
    wrapper.__name__ = fn.__name__
    return wrapper


# ------------------------------------------------------------------ ida e volta / ausencia
@run_with_store
def test_roundtrip():
    g = played_game()
    assert g.league is not None and g.league["round"] == 3 and g.shop["stock"] and g.flags
    assert gm.Garage.has_save() is False
    assert g.save() is True
    assert gm.Garage.has_save() is True
    assert gm.Garage.load_status() == gm.SAVE_OK
    h = gm.Garage.load()
    assert h is not None
    assert h.to_dict() == g.to_dict()
    assert h.league == g.league and h.shop == g.shop and h.flags == g.flags
    assert h.to_json() == g.to_json()
    check_invariants(h)
    # o recarregado continua jogavel (liga, equip, metodos)
    assert h.equip(h.robots[1]["id"], h.free_pieces("motor")[0]["id"] if h.free_pieces("motor") else -1)[0] in (True, False)
    assert rl.next_fixture(h.league) is not None
    h.save()
    assert gm.Garage.load().to_dict() == h.to_dict()


@run_with_store
def test_fresh_game_roundtrip_and_no_league():
    g = gm.new_game(random.Random(11))
    assert g.save()
    h = gm.Garage.load()
    assert h.to_dict() == g.to_dict() and h.league is None
    check_invariants(h)


@run_with_store
def test_absence():
    assert gm.Garage.has_save() is False
    assert gm.Garage.load() is None
    assert gm.Garage.load_status() == gm.SAVE_NONE
    assert BAD not in MEM and KEY not in MEM


@run_with_store
def test_status_ok_bad_none():
    assert gm.Garage.load_status() == gm.SAVE_NONE
    played_game().save()
    assert gm.Garage.load_status() == gm.SAVE_OK
    put_raw("{{{")
    assert gm.Garage.load_status() == gm.SAVE_BAD
    assert BAD not in MEM          # load_status nao tem efeitos
    assert gm.Garage.load() is None and MEM[BAD] == "{{{"


# ------------------------------------------------------------------ chaves desconhecidas / metodos
@run_with_store
def test_unknown_keys_and_method_names_ignored():
    d = valid_dict()
    for k in ("equip", "save", "upgrade", "load", "to_dict", "sanitize", "from_dict",
              "robot", "piece", "__class__", "__dict__", "FIELDS", "rating", "hack", "__init__"):
        d[k] = "pwn"
    d["team"]["extra"] = 1
    d["robots"][0]["equip"] = "x"
    d["robots"][0]["__class__"] = 1
    put(d)
    g = gm.Garage.load()
    assert g is not None
    for k in ("equip", "save", "upgrade", "load", "robot", "piece", "rating", "to_dict"):
        assert callable(getattr(g, k)), k
        assert k not in g.__dict__, k
    assert "hack" not in g.__dict__ and "__init__" not in g.__dict__
    assert gm.Garage.FIELDS == gm.FIELDS
    assert set(g.to_dict()) == {"v"} | set(gm.FIELDS)
    assert "equip" not in g.robots[0] and "extra" not in g.team
    ok, _ = g.equip(g.robots[0]["id"], g.inventory[0]["id"])   # ainda chamavel
    assert isinstance(ok, bool)
    assert g.save() is True and MEM[KEY] != "pwn"
    assert "pwn" not in MEM[KEY]
    check_invariants(g)


# ------------------------------------------------------------------ corrompidos
@run_with_store
def test_invalid_json_and_roots():
    for raw in ("", "   ", "{not json", "[1,2,3]", "[]", "null", "42", '"str"', "true",
                "{" * 5000, "[" * 5000, '{"v":1', "\x00\x01"):
        setup_keep = dict(MEM)
        put_raw(raw)
        if raw == "":
            # texto vazio existe mas nao e save
            assert gm.Garage.load() is None
            assert gm.Garage.load_status() == gm.SAVE_BAD
            assert MEM[KEY] == "" and MEM[BAD] == ""
        else:
            expect_none_and_bad()
        MEM.clear()
        MEM.update(setup_keep)
        MEM.pop(KEY, None)
        MEM.pop(BAD, None)


@run_with_store
def test_version_problems():
    for mut in ("missing", None, "1", 0, -1, 2, 99, 1.5, True, [1], {"a": 1}):
        d = valid_dict()
        if mut == "missing":
            del d["v"]
        else:
            d["v"] = mut
        put(d)
        expect_none_and_bad()
        MEM.pop(BAD, None)


@run_with_store
def test_future_version_and_migration_hook():
    d = valid_dict()
    d["v"] = gm.VERSION + 1
    put(d)
    expect_none_and_bad()
    # v antiga sem migracao registrada -> None; com migracao -> aplicada
    saved = dict(gm.MIGRATIONS)
    try:
        old_v = gm.VERSION
        gm.VERSION = 2
        d = valid_dict()
        d["v"] = 1
        d["scrap"] = 10
        put(d)
        MEM.pop(BAD, None)
        assert gm.Garage.load() is None and BAD in MEM        # sem migracao
        gm.MIGRATIONS[1] = lambda x: dict(x, v=2, scrap=x["scrap"] + 1)
        g = gm.Garage.load()
        assert g is not None and g.scrap == 11
        gm.MIGRATIONS[1] = lambda x: 1 / 0                    # migracao quebrada -> None
        assert gm.Garage.load() is None
    finally:
        gm.VERSION = old_v
        gm.MIGRATIONS.clear()
        gm.MIGRATIONS.update(saved)


@run_with_store
def test_structural_corruptions_return_none():
    cases = []

    def mk(label, fn):
        d = valid_dict()
        fn(d)
        cases.append((label, d))
    mk("robots string", lambda d: d.__setitem__("robots", "abc"))
    mk("robots dict", lambda d: d.__setitem__("robots", {"a": 1}))
    mk("robots null", lambda d: d.__setitem__("robots", None))
    mk("robots ausente", lambda d: d.pop("robots"))
    mk("<5 robos", lambda d: d.__setitem__("robots", d["robots"][:4]))
    mk("robos nao-dict", lambda d: d.__setitem__("robots", [1, "a", None, [], 2.5, True]))
    mk("todos chassis ruins", lambda d: [r.__setitem__("chassis", "Foguete") for r in d["robots"]])
    mk("3 robos descartados", lambda d: [d["robots"][i].__setitem__("role", "XYZ") for i in range(4)])
    mk("base ausente", lambda d: [r.pop("base") for r in d["robots"][:2]] and d["robots"].__delitem__(slice(2, 5)))
    mk("ids duplicados", lambda d: [r.__setitem__("id", 1) for r in d["robots"]])
    for label, d in cases:
        MEM.pop(BAD, None)
        put(d)
        expect_none_and_bad()


def _loaded_after(mutator):
    d = valid_dict()
    mutator(d)
    put(d)
    g = gm.Garage.load()
    return d, g


@run_with_store
def test_unknown_chassis_robot_dropped():
    d, g = _loaded_after(lambda d: d["robots"][5:].__len__() or None)
    base_n = len(g.robots)
    # com 8 robos, descartar 1 por chassis desconhecido
    d = valid_dict()
    g0 = gm.Garage.from_dict(d)
    g0.robots.append(g0.make_robot("Extra", "MID", "Disco"))
    g0.robots.append(g0.make_robot("Extra2", "MID", "Disco"))
    dd = g0.to_dict()
    dd["robots"][-1]["chassis"] = "Foguete"
    dd["robots"][-2]["role"] = "BOSS"
    put(dd)
    g = gm.Garage.load()
    assert g is not None and len(g.robots) == base_n
    check_invariants(g)


@run_with_store
def test_base_values_clamped_or_dropped():
    def m(d):
        d["robots"][0]["base"]["vel"] = 5000
        d["robots"][0]["base"]["ace"] = -40
        d["robots"][1]["base"]["vel"] = 19.2
        d["robots"][1]["base"]["def"] = 99.7
        d["robots"][2]["base"]["vel"] = "alto"        # nao numerico -> descartado
        d["robots"][3]["base"]["qi"] = None           # idem
        d["robots"][4]["base"].pop("bat")              # incompleta -> descartado
    d = valid_dict()
    g0 = gm.Garage.from_dict(d)
    g0.robots.append(g0.make_robot("E1", "ATT", "Disco"))
    g0.robots.append(g0.make_robot("E2", "ATT", "Disco"))
    g0.robots.append(g0.make_robot("E3", "ATT", "Disco"))
    dd = g0.to_dict()
    m(dd)
    put(dd)
    g = gm.Garage.load()
    assert g is not None and len(g.robots) == 8 - 3
    r0 = g.robot(dd["robots"][0]["id"])
    assert r0["base"]["vel"] == 99 and r0["base"]["ace"] == 20
    r1 = g.robot(dd["robots"][1]["id"])
    assert r1["base"]["vel"] == 20 and r1["base"]["def"] == 99
    assert g.robot(dd["robots"][2]["id"]) is None and g.robot(dd["robots"][4]["id"]) is None
    check_invariants(g)
    # nan/inf no base (via texto cru)
    raw = json.dumps(valid_dict()).replace('"vel": ', '"vel": NaN, "x": ', 1)
    put_raw(raw)
    check_invariants_or_none(gm.Garage.load())


def check_invariants_or_none(g):
    if g is not None:
        check_invariants(g)


@run_with_store
def test_numeric_ranges():
    def m(d):
        d["scrap"] = -500
        d["robots"][0]["level"] = -3
        d["robots"][1]["level"] = 10 ** 30
        d["robots"][2]["xp"] = -9
        d["robots"][3]["xp"] = 10 ** 40
        d["robots"][4]["oc"] = 77
        d["tier_done"] = 99
        d["next_id"] = -5
        d["stats"]["w"] = -4
    d, g = _loaded_after(m)
    assert g is not None
    ids = [r["id"] for r in d["robots"]]
    assert g.scrap == 0
    assert g.robot(ids[0])["level"] == 1
    assert g.robot(ids[1])["level"] == 10 and g.robot(ids[1])["xp"] == 0
    assert g.robot(ids[2])["xp"] == 0
    assert g.robot(ids[3])["xp"] < gm.xp_need(g.robot(ids[3])["level"])
    assert g.robot(ids[4])["oc"] == 2
    assert g.tier_done == 3 and g.stats["w"] == 0
    assert g.next_id > max(ids)
    check_invariants(g)
    d, g = _loaded_after(lambda d: d.__setitem__("scrap", 10 ** 15))
    assert g.scrap == gm.SCRAP_MAX
    d, g = _loaded_after(lambda d: d.__setitem__("scrap", float("inf")))
    assert g is not None and g.scrap == 0
    d, g = _loaded_after(lambda d: d.__setitem__("scrap", "123"))
    assert g.scrap == 123
    d, g = _loaded_after(lambda d: d.__setitem__("scrap", [1]))
    assert g.scrap == 0
    d, g = _loaded_after(lambda d: d.__setitem__("scrap", True))
    assert g.scrap == 0


@run_with_store
def test_paint_and_team_color():
    def m(d):
        d["robots"][0]["paint"] = [1, 2, 3, 4]
        d["robots"][1]["paint"] = [999, -1, 5]
        d["robots"][2]["paint"] = "red"
        d["robots"][3]["paint"] = [1.5, 2.9, 3]
        d["team"]["color"] = [1, 2]
    d, g = _loaded_after(m)
    assert g is not None
    ids = [r["id"] for r in d["robots"]]
    assert g.team["color"] == list(gm.TEAM_COLOR)
    assert g.robot(ids[0])["paint"] == list(gm.TEAM_COLOR)    # 4 valores -> reparo
    assert g.robot(ids[1])["paint"] == [255, 0, 5]
    assert g.robot(ids[2])["paint"] == list(gm.TEAM_COLOR)
    assert g.robot(ids[3])["paint"] == [1, 2, 3]
    check_invariants(g)


@run_with_store
def test_strings_truncated_and_latin1():
    def m(d):
        d["team"]["name"] = "T" * 10000
        d["robots"][0]["name"] = "A" * 10000
        d["robots"][1]["name"] = "中文\U0001f600Zeta"
        d["robots"][2]["name"] = "\x00\x07\n\t"
        d["robots"][3]["name"] = "Ação ok"
        d["robots"][4]["name"] = 12345
    d, g = _loaded_after(m)
    assert g is not None
    ids = [r["id"] for r in d["robots"]]
    assert g.team["name"] == "T" * gm.NAME_MAX_TEAM
    assert g.robot(ids[0])["name"] == "A" * gm.NAME_MAX_ROBOT
    assert g.robot(ids[1])["name"] == "Zeta"
    assert g.robot(ids[2])["name"] == "Robô %d" % ids[2]
    assert g.robot(ids[3])["name"].encode("latin-1") and g.robot(ids[3])["name"].startswith("Ação")
    assert g.robot(ids[4])["name"] == "Robô %d" % ids[4]
    for r in g.robots:
        r["name"].encode("latin-1")
        assert r["name"].isprintable() and 0 < len(r["name"]) <= gm.NAME_MAX_ROBOT
    check_invariants(g)


@run_with_store
def test_pieces_slots_repairs():
    d = valid_dict()
    g0 = gm.Garage.from_dict(d)
    inv = g0.inventory
    motor = next(p for p in inv if parts.part_slot(p) == "motor")
    chip = next(p for p in inv if parts.part_slot(p) == "chip")
    dd = g0.to_dict()
    r = dd["robots"]
    r[0]["slots"]["motor"] = motor["id"]
    r[1]["slots"]["motor"] = motor["id"]           # mesma peca em 2 robos
    r[2]["slots"]["sensor"] = chip["id"]           # peca de slot errado
    r[3]["slots"]["chip"] = 987654                 # inexistente
    r[4]["slots"]["bateria"] = "abc"               # lixo
    r[4]["slots"]["slot_falso"] = motor["id"]      # slot inexistente
    dd["inventory"].append({"id": 5000, "model": "ModeloFantasma", "rar": 1, "lvl": 0})
    dd["inventory"].append({"id": 5001, "model": "Turbina", "rar": 99, "lvl": -4})
    dd["inventory"].append({"id": motor["id"], "model": "Turbina", "rar": 3, "lvl": 5})  # id dup
    dd["inventory"].append("lixo")
    r[0]["slots"]["motor"] = motor["id"]
    r[2]["slots"]["parachoque"] = 5000             # peca descartada
    put(dd)
    g = gm.Garage.load()
    assert g is not None
    ids = [x["id"] for x in dd["robots"]]
    holders = [rb["id"] for rb in g.robots if g.robot(rb["id"])["slots"]["motor"] == motor["id"]]
    assert holders == [ids[0]], holders             # so o primeiro fica
    assert g.robot(ids[1])["slots"]["motor"] is None
    assert g.robot(ids[2])["slots"]["sensor"] is None
    assert g.robot(ids[3])["slots"]["chip"] is None
    assert g.robot(ids[4])["slots"]["bateria"] is None
    assert "slot_falso" not in g.robot(ids[4])["slots"]
    assert g.piece(5000) is None
    p = g.piece(5001)
    assert p is not None and p["rar"] == 3 and p["lvl"] == 0
    assert g.robot(ids[2])["slots"]["parachoque"] is None
    check_invariants(g)


@run_with_store
def test_lineup_repairs():
    for lu in ([999, 998, 997, 996, 995], [1, 1, 1, 1, 1], "abc", None, [], [1, 2],
               ["a", "b", "c", "d", "e"], [None] * 5, {"a": 1}, "SPECIAL_DUP", "SPECIAL_SIX"):
        d = valid_dict()
        ids = [r["id"] for r in d["robots"]]
        if lu == "SPECIAL_DUP":
            lu = [ids[0], ids[0], ids[1], ids[2], ids[3]]
        elif lu == "SPECIAL_SIX":
            lu = ids[:5] + [ids[0]]
        d["lineup"] = lu
        put(d)
        g = gm.Garage.load()
        assert g is not None, lu
        assert len(g.lineup) == 5 and len(set(g.lineup)) == 5
        assert set(g.lineup) <= {r["id"] for r in g.robots}
        check_invariants(g)
    d = valid_dict()
    d.pop("lineup")
    put(d)
    assert len(gm.Garage.load().lineup) == 5
    # lineup valido e preservado (inclusive reserva diferente)
    d = valid_dict()
    d["lineup"] = list(reversed(d["lineup"]))
    put(d)
    assert gm.Garage.load().lineup == d["lineup"]


@run_with_store
def test_too_many_robots_and_giant_inventory():
    g0 = gm.Garage.from_dict(valid_dict())
    for i in range(30):
        g0.robots.append(g0.make_robot("R%d" % i, "MID", "Disco"))
    put(g0.to_dict())
    g = gm.Garage.load()
    assert g is not None and len(g.robots) == gm.MAX_SQUAD
    assert [r["id"] for r in g.robots] == [r["id"] for r in g0.robots[:gm.MAX_SQUAD]]
    check_invariants(g)
    d = valid_dict()
    d["inventory"] = [{"id": 10000 + i, "model": "Turbina", "rar": 0, "lvl": 0}
                      for i in range(8000)]
    d["flags"] = {"f%d" % i: i for i in range(5000)}
    d["unlocked"] = ["Tanque"] * 1000
    put(d)
    g = gm.Garage.load()
    assert g is not None and len(g.inventory) == gm.MAX_INVENTORY
    assert len(g.flags) == gm.MAX_FLAGS and g.unlocked.count("Tanque") == 1
    check_invariants(g)
    # texto gigante (> limite) -> bad, sem parse
    put_raw('{"v":1,"pad":"' + "x" * (gm.MAX_SAVE_CHARS + 10) + '"}')
    assert gm.Garage.load() is None and gm.Garage.load_status() == gm.SAVE_BAD


@run_with_store
def test_flags_sanitized():
    d = valid_dict()
    d["flags"] = {"ok": 5, "": 1, "longa" * 50: 2, "bool": True, "lista": [1], "str": "7",
                  "grande": 10 ** 30, "中": 3, "neg": -4, "ç": 1}
    put(d)
    g = gm.Garage.load()
    assert g.flags["ok"] == 5 and "" not in g.flags and "bool" not in g.flags
    assert "lista" not in g.flags and g.flags["str"] == 7 and g.flags["grande"] == gm.ID_MAX
    assert g.flags["neg"] == -4 and g.flags["ç"] == 1
    assert all(len(k) <= gm.FLAG_KEY_MAX and isinstance(v, int) for k, v in g.flags.items())
    d["flags"] = [1, 2]
    put(d)
    assert gm.Garage.load().flags == {}


@run_with_store
def test_league_sanitized_or_none():
    base = valid_dict()
    assert base["league"] is not None

    def lg(fn):
        d = copy.deepcopy(base)
        fn(d["league"])
        put(d)
        g = gm.Garage.load()
        assert g is not None                         # liga ruim nao derruba o save
        check_invariants(g)
        return g.league
    assert lg(lambda L: None) == base["league"]
    assert lg(lambda L: L.__setitem__("teams", L["teams"][:3])) is None
    assert lg(lambda L: L.__setitem__("fixtures", "x")) is None
    assert lg(lambda L: L["fixtures"][0].__setitem__(0, [0, 0])) is None
    assert lg(lambda L: L["fixtures"][1].__setitem__(0, [9, 1])) is None
    assert lg(lambda L: L.__setitem__("round", 99)) is None
    assert lg(lambda L: L.__setitem__("round", -1)) is None
    assert lg(lambda L: L.__setitem__("tier", 7)) is None
    assert lg(lambda L: L["results"].append([0, 0, 0, 1, 1])) is None
    assert lg(lambda L: L["results"].append([9, 1, 2, 1, 1])) is None
    assert lg(lambda L: L["results"].append("x")) is None
    assert lg(lambda L: L["results"][0].__setitem__(3, -5)) is None
    assert lg(lambda L: L["teams"][1].__setitem__("ovr", "x")) is None
    assert lg(lambda L: L.__setitem__("results", L["results"] * 50)) is None
    d = copy.deepcopy(base)
    d["league"] = "lixo"
    put(d)
    assert gm.Garage.load().league is None
    d["league"] = None
    put(d)
    assert gm.Garage.load().league is None
    L = lg(lambda L: L["teams"][2].__setitem__("name", "N" * 999))
    assert L is not None and len(L["teams"][2]["name"]) <= gm.NAME_MAX_LEAGUE_TEAM


@run_with_store
def test_all_generated_league_names_survive():
    assert max(len(n) for n in rl.TEAM_NAMES) <= gm.NAME_MAX_LEAGUE_TEAM
    for seed in range(20):
        g = gm.new_game(random.Random(seed))
        rl.new_league(g, seed % 4, random.Random(seed))
        assert gm.Garage.from_dict(g.to_dict()).league == g.league


@run_with_store
def test_shop_sanitized():
    d = valid_dict()
    d["shop"] = {"stock": [{"id": 77, "model": "Turbina", "rar": 1, "lvl": 0}, "x",
                           {"id": d["inventory"][0]["id"], "model": "Turbina", "rar": 0, "lvl": 0},
                           {"id": 78, "model": "Nada", "rar": 0, "lvl": 0}] * 50, "seed": "abc"}
    put(d)
    g = gm.Garage.load()
    assert g is not None and [p["id"] for p in g.shop["stock"]] == [77]
    assert g.shop["seed"] == 0
    d["shop"] = None
    put(d)
    g = gm.Garage.load()
    assert g.shop == {"stock": [], "seed": 0}


@run_with_store
def test_next_id_above_all_ids():
    d = valid_dict()
    d["next_id"] = 1
    put(d)
    g = gm.Garage.load()
    top = max([r["id"] for r in g.robots] + [p["id"] for p in g.inventory + g.shop["stock"]])
    assert g.next_id > top
    pc = g.new_piece("Turbina", 0)
    assert g.piece(pc["id"]) is None


# ------------------------------------------------------------------ nao sobrescreve / .bad / isolamento
@run_with_store
def test_bad_save_never_overwritten_and_bad_written():
    raw = '{"v": 1, "robots": "naoéumalista"}'
    put_raw(raw)
    assert gm.Garage.load() is None
    assert MEM[KEY] == raw and MEM[BAD] == raw
    assert gm.Garage.load() is None and MEM[KEY] == raw
    assert gm.Garage.load_status() == gm.SAVE_BAD
    # a unica forma de substituir e um save explicito de um Garage valido
    g = played_game()
    assert g.save() and gm.Garage.load() is not None
    assert MEM[BAD] == raw          # .bad preservado


@run_with_store
def test_save_only_valid_garage():
    g = played_game()
    g.robots = g.robots[:3]                       # < 5 robos
    assert g.save() is False and KEY not in MEM
    g = played_game()
    g.robots[0]["chassis"] = "Foguete"
    g.robots = g.robots[:]                        # sobram 4 validos -> invalido
    assert g.save() is False and KEY not in MEM
    g = played_game()
    g.scrap = "x"
    assert g.save() in (True, False)              # coagivel/inofensivo: nao levanta
    g = played_game()
    g.team = None
    assert g.save() in (True, False)
    g = played_game()
    g.flags = {1: object()}
    assert g.save() is False or MEM.get(KEY) is not None   # nao-serializavel nao levanta


@run_with_store
def test_only_robots_key_touched_never_career():
    g = played_game()
    g.save()
    gm.Garage.load()
    gm.Garage.has_save()
    gm.Garage.load_status()
    put_raw("lixo")
    gm.Garage.load()
    for _ in range(20):
        gm.Garage.load()
    keys = {k for _op, k in LOG}
    assert keys <= {KEY, BAD}, keys
    assert {k for op, k in LOG if op == "w"} <= {KEY, BAD}
    assert MEM[CAREER_KEY] == CAREER_SENTINEL
    assert CAREER_KEY not in keys
    assert gm.SAVE_KEY == "soccerpy_robots_v1" and gm.SAVE_KEY != CAREER_KEY
    assert gm.SAVE_PATH.endswith(".soccerpy_robots.json") or "never_used" in gm.SAVE_PATH
    import career
    assert career.SAVE_KEY == CAREER_KEY      # carreira intacta, nao refatorada


@run_with_store
def test_garage_level_monkeypatch():
    """_store_get/_store_set no nivel do modulo podem ser trocados (como em career)."""
    box = {}
    og, os_ = gm._store_get, gm._store_set
    gm._store_get = lambda: box.get("t")
    gm._store_set = lambda text: box.__setitem__("t", text) or True
    try:
        g = played_game()
        assert g.save() and "t" in box
        assert gm.Garage.load().to_dict() == g.to_dict()
        assert gm.Garage.has_save() is True
    finally:
        gm._store_get, gm._store_set = og, os_
    assert KEY not in MEM


def test_store_module_file_roundtrip_and_errors():
    p = os.path.join(SCRATCH, "store_test.json")
    for f in (p, p + ".tmp"):
        if os.path.exists(f):
            os.remove(f)
    assert store.read("k", p) is None
    assert store.write("k", p, "olá ç") is True
    assert store.read("k", p) == "olá ç"
    assert store.write("k", p, "novo") is True and store.read("k", p) == "novo"
    assert not os.path.exists(p + ".tmp")
    # erro de escrita (diretorio inexistente) -> False, sem excecao
    assert store.write("k", "/nonexistent_dir_xyz/a.json", "x") is False
    assert store.read("k", "/nonexistent_dir_xyz/a.json") is None
    os.remove(p)


def test_store_read_distinguishes_absent_from_error():
    p = os.path.join(SCRATCH, "store_err.json")
    for f in (p, p + ".tmp"):
        if os.path.exists(f):
            os.remove(f)
    assert store.read("k", p) is None                      # ausente
    os.makedirs(p)                                         # existe mas nao e arquivo -> erro de leitura
    try:
        assert store.read("k", p) is store.ERROR
    finally:
        os.rmdir(p)
    with open(p, "wb") as f:
        f.write(b"ab\xff\xfecd")
    t = store.read("k", p)
    assert isinstance(t, store.InvalidText) and t.startswith("ab") and t.endswith("cd")
    os.remove(p)


@run_with_store
def test_save_refuses_when_league_would_be_dropped():
    g = played_game()
    assert g.league is not None and g.save()
    prev = MEM[KEY]
    g.league["results"].append(list(g.league["results"][0]))      # resultado repetido: sanitize rejeita a liga
    assert g.save() is False
    assert MEM[KEY] == prev                                       # save anterior preservado


def test_unreadable_save_is_bad_not_none():
    og, os_ = gm._store_get, gm._store_set
    try:
        gm._store_get = lambda: store.ERROR
        assert gm.Garage.load_status() == gm.SAVE_BAD
        assert gm.Garage.load() is None
        assert gm.Garage.has_save() is True
        gm._store_get = lambda: None
        assert gm.Garage.load_status() == gm.SAVE_NONE
    finally:
        gm._store_get, gm._store_set = og, os_


def test_file_with_invalid_utf8_is_bad_and_copied():
    p = os.path.join(SCRATCH, "robots_utf8.json")
    for f in (p, p + ".bad", p + ".tmp"):
        if os.path.exists(f):
            os.remove(f)
    old = gm.SAVE_PATH
    gm.SAVE_PATH = p
    try:
        # gravacao real (store.read/write originais), nunca em ~
        store.read, store.write = _REAL[0], _REAL[1]
        g = played_game()
        assert g.save()
        raw = open(p, "rb").read()
        bad = raw[:100] + b"\xff\xfe" + raw[100:]
        with open(p, "wb") as f:
            f.write(bad)
        assert gm.Garage.load_status() == gm.SAVE_BAD
        assert gm.Garage.load() is None
        assert open(p, "rb").read() == bad               # original intacto
        assert os.path.exists(p + ".bad")
        assert "\ufffd" in open(p + ".bad", encoding="utf-8").read()
    finally:
        gm.SAVE_PATH = old
        for f in (p, p + ".bad", p + ".tmp"):
            if os.path.exists(f):
                os.remove(f)


def test_real_file_save_load_bad_in_scratch():
    """store real (arquivo) apontado para o scratchpad: save, load, .bad."""
    p = os.path.join(SCRATCH, "robots_file_test.json")
    for f in (p, p + ".bad", p + ".tmp"):
        if os.path.exists(f):
            os.remove(f)
    old = gm.SAVE_PATH
    gm.SAVE_PATH = p
    try:
        assert gm.Garage.load() is None and gm.Garage.load_status() == gm.SAVE_NONE
        g = played_game()
        assert g.save() and os.path.exists(p)
        assert gm.Garage.load().to_dict() == g.to_dict()
        with open(p, "w", encoding="utf-8") as f:
            f.write("{quebrado")
        assert gm.Garage.load() is None
        with open(p, encoding="utf-8") as f:
            assert f.read() == "{quebrado"
        with open(p + ".bad", encoding="utf-8") as f:
            assert f.read() == "{quebrado"
    finally:
        gm.SAVE_PATH = old
        for f in (p, p + ".bad", p + ".tmp"):
            if os.path.exists(f):
                os.remove(f)


# ------------------------------------------------------------------ fuzz
JUNK = [None, True, False, 0, -1, 7, 10 ** 30, -10 ** 30, 1.5, float("nan"), float("inf"),
        "", "abc", "A" * 5000, "中\U0001f600", "\x00", [], [1, 2, 3], [[]], {}, {"a": 1},
        {"id": "x"}, ["x"] * 50, "equip", "123", 2 ** 63]


def _paths(node, prefix=()):
    out = [prefix]
    if isinstance(node, dict):
        for k, v in node.items():
            out += _paths(v, prefix + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += _paths(v, prefix + (i,))
    return out


def _get(root, path):
    for k in path:
        root = root[k]
    return root


def _mutate(d, rng):
    for _ in range(rng.randint(1, 4)):
        paths = [p for p in _paths(d) if p]
        path = rng.choice(paths)
        parent = _get(d, path[:-1])
        key = path[-1]
        op = rng.randrange(5)
        if op == 0:
            if isinstance(parent, dict):
                del parent[key]
            else:
                del parent[key]
        elif op == 1:
            parent[key] = copy.deepcopy(rng.choice(JUNK))
        elif op == 2 and isinstance(parent, dict) and len(parent) > 1:
            k2 = rng.choice(list(parent))
            parent[key], parent[k2] = parent[k2], parent[key]
        elif op == 3:
            other = _get(d, rng.choice(paths))
            parent[key] = copy.deepcopy(other)
        else:
            if isinstance(parent, dict):
                parent[rng.choice(["equip", "save", "upgrade", "__class__", "x"])] = rng.choice(JUNK)
            elif isinstance(parent, list):
                parent.append(copy.deepcopy(rng.choice(JUNK)))
    return d


@run_with_store
def test_fuzz_mutations_no_exception():
    base = valid_dict()
    rng = random.Random(20260702)
    n_ok = n_none = 0
    for i in range(400):
        d = _mutate(copy.deepcopy(base), rng)
        try:
            text = json.dumps(d)
        except (ValueError, TypeError):
            continue
        if rng.random() < 0.1:                # tambem corta o texto no meio
            text = text[:rng.randrange(1, len(text))]
        MEM[KEY] = text
        MEM.pop(BAD, None)
        st = gm.Garage.load_status()
        g = gm.Garage.load()                  # nao pode levantar
        assert st in (gm.SAVE_OK, gm.SAVE_BAD)
        assert (g is not None) == (st == gm.SAVE_OK)
        if g is None:
            n_none += 1
            assert MEM[KEY] == text and MEM[BAD] == text
        else:
            n_ok += 1
            check_invariants(g)
            assert MEM.get(BAD) is None
            assert g.save() is True
            h = gm.Garage.load()
            assert h is not None and h.to_dict() == g.to_dict()   # sanitize idempotente
            # tudo que o jogo faz continua sem excecao
            g.auto_lineup()
            for r in g.robots:
                g.set_oc(r["id"], 1)
                g.rename(r["id"], "X")
            if g.league is not None:
                rl.table(g.league)
                rl.user_position(g.league)
                rl.next_fixture(g.league)
    assert MEM[CAREER_SENTINEL and CAREER_KEY] == CAREER_SENTINEL
    print("fuzz: %d carregaram, %d rejeitados" % (n_ok, n_none))
    assert n_ok > 50 and n_none > 20          # o fuzz exercita os dois caminhos


@run_with_store
def test_fuzz_sanitize_direct_never_raises():
    rng = random.Random(7)
    base = valid_dict()
    for _ in range(300):
        d = _mutate(copy.deepcopy(base), rng)
        out = gm.Garage.sanitize(d)
        assert out is None or set(out) == {"v"} | set(gm.FIELDS)
        gm.Garage.from_dict(d)
    for junk in JUNK:
        assert gm.Garage.sanitize(junk) is None
        assert gm.Garage.from_dict(junk) is None


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
    shutil.rmtree(SCRATCH, ignore_errors=True)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
