"""Testes da Carreira com robôs: nomes de robô (game/robot_names.py), elenco de 5 a 10, mercado, temporadas e a
migração dos saves antigos (nomes de pessoa, elencos de 12-20). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_career.py [teste ...]

NUNCA toca ~/.soccerpy_*.json: os stores de garage, carreira e campanha vão para dicts em memória, trocados
ANTES de criar o Game.
"""
import copy
import json
import os
import random
import statistics
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
os.chdir(os.path.join(ROOT, "game"))

import pygame  # noqa: E402

import campaign as cm  # noqa: E402
import career as C  # noqa: E402
import garage as gm  # noqa: E402

MEM = {}
WRITES = []
gm._store_get = lambda: MEM.get("g")
gm._store_set = lambda t: MEM.__setitem__("g", t) or True
gm._store_set_bad = lambda t: MEM.__setitem__("gbad", t) or True
C._store_get = lambda: MEM.get("c")
C._store_set = lambda t: WRITES.append(t) or MEM.__setitem__("c", t) or True
cm._store_get = lambda: MEM.get("cp")
cm._store_set = lambda t: MEM.__setitem__("cp", t) or True
cm._store_set_bad = lambda t: MEM.__setitem__("cpbad", t) or True

import robot_names as RN  # noqa: E402
import soccer  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "career_v1_mid_season.json")
# nomes de pessoa da carreira antiga (career.FIRST/LAST até a troca para robôs): nenhum pode sobrar
LEGACY_FIRST = {"Rafael", "Lucas", "Pedro", "Gabriel", "Mateus", "Bruno", "Diego", "Thiago", "Caio", "André",
                "Felipe", "Rodrigo", "João", "Vitor", "Marcos", "Leandro", "Danilo", "Igor", "Renan", "Paulo",
                "Henrique", "Samuel", "Otávio", "Murilo"}
LEGACY_LAST = {"Silva", "Souza", "Costa", "Santos", "Oliveira", "Pereira", "Lima", "Alves", "Rocha", "Ribeiro",
               "Carvalho", "Gomes", "Martins", "Araújo", "Barbosa", "Nunes", "Moreira", "Cardoso", "Teixeira",
               "Dias", "Freitas", "Mendes"}
LEGACY = LEGACY_FIRST | LEGACY_LAST

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)


def has_person(text):
    words = set(str(text).replace(".", " ").replace("-", " ").split())
    return bool(words & LEGACY)


def all_players(c):
    return [p for cl in c.clubs for p in cl["squad"]]


def check_squads(c, lo=C.MIN_SQUAD, hi=C.MAX_SQUAD):
    for i, cl in enumerate(c.clubs):
        n = len(cl["squad"])
        assert lo <= n <= hi, (cl["name"], n)
        names = [p["name"] for p in cl["squad"]]
        assert len(set(names)) == len(names), (cl["name"], names)
        assert any(p["pos"] == "GK" for p in cl["squad"]), cl["name"]
        ids = {p["id"] for p in cl["squad"]}
        assert len(cl["lineup"]) == 5 and len(set(cl["lineup"])) == 5 and set(cl["lineup"]) <= ids, cl["name"]
        for p in cl["squad"]:
            assert isinstance(p["name"], str) and 0 < len(p["name"]) <= RN.NAME_MAX
            assert not has_person(p["name"]), p["name"]
            p["name"].encode("latin-1")


# ------------------------------------------------------------------ nomes
def test_robot_name_catalog():
    assert len(RN.BASE) >= 300 and len(set(RN.BASE)) == len(RN.BASE)
    assert len(RN.NAMES) >= 3000 and len(set(RN.NAMES)) == len(RN.NAMES)
    for nm in RN.NAMES:
        assert 0 < len(nm) <= RN.NAME_MAX, nm
        nm.encode("latin-1")
        assert not has_person(nm), nm
    # os nomes do estilo dos outros modos estao no catalogo
    for nm in ("Zumbido", "Rodinha", "Faísca", "Turbo", "Vassoura"):
        assert nm in RN.BASE
    assert any(n.endswith(" Mk2") for n in RN.NAMES) and any(n.startswith("RX-") for n in RN.NAMES)
    # deterministico, sem RNG (nem global, nem privado)
    assert "random" not in vars(RN)
    st = random.getstate()
    a = [RN.name_for(i) for i in range(1, 500)]
    assert random.getstate() == st and a == [RN.name_for(i) for i in range(1, 500)]
    assert len(set(RN.name_for(i) for i in range(1, len(RN.NAMES) + 1))) == len(RN.NAMES)   # sem repetir
    assert all(RN.name_for(i) in RN.BASE for i in range(1, len(RN.BASE) + 1))   # carreira nova: nomes-base
    assert RN.name_for("lixo") == RN.name_for(1) and RN.name_for(None) == RN.name_for(1)
    taken = {RN.name_for(7)}
    alt = RN.unique_name(7, taken)
    assert alt != RN.name_for(7) and alt not in taken and RN.unique_name(7, set()) == RN.name_for(7)


def test_new_career_robot_names_and_squads():
    for seed in range(12):
        random.seed(seed)
        c = C.Career.new()
        assert c.ver == C.VERSION
        check_squads(c, 7, 10)
        for cl in c.clubs:
            assert sum(p["pos"] == "GK" for p in cl["squad"]) >= 2          # goleiro reserva
            assert all(p["name"] == RN.name_for(p["id"]) for p in cl["squad"])
        names = [p["name"] for p in all_players(c)] + [e["p"]["name"] for e in c.market if e["club"] < 0]
        assert len(set(names)) == len(names)                                  # nenhum nome repetido na liga
        cfg = c.match_cfg(0)
        lp = c.lineup_players(c.clubs[0])
        assert [e[0] for e in cfg["squad"]] == [p["name"] for p in lp]       # partida mostra o nome do robo
        assert C.short_name("Turbo Mk2") == "Turbo Mk2"


def test_cpu_starters_as_strong_as_old_generation():
    """A peneira de 15 mantem a forca dos titulares da geracao antiga (15 jogadores): media por divisao medida na
    versao antiga (elencos de 15) com as mesmas sementes = 72.43 / 62.58 / 52.41 (tolerancia 0.8)."""
    by_div = [[], [], []]
    for seed in range(60):
        random.seed(1000 + seed)
        c = C.Career.new()
        for d in range(3):
            by_div[d].append(statistics.mean(c.rating(c.clubs[i]) for i in c.divs[d]))
    means = [statistics.mean(v) for v in by_div]
    for got, ref in zip(means, (72.43, 62.58, 52.41)):
        assert abs(got - ref) <= 0.8, means


# --------------------------------------------------------------- mercado
def _career(seed=3, user=10):
    random.seed(seed)
    c = C.Career.new()
    c.user = user
    c.market_refresh()
    c.clubs[user]["money"] = 50_000_000
    return c


def test_market_limits_5_to_10():
    c = _career()
    u = c.clubs[c.user]
    while len(u["squad"]) < C.MAX_SQUAD:
        k = next(k for k, e in enumerate(c.market) if e["club"] < 0) if any(
            e["club"] < 0 for e in c.market) else 0
        ok, msg = c.buy(k)
        assert ok, msg
        if not c.market:
            c.market_refresh()
    c.market_refresh()
    before = (len(u["squad"]), u["money"], len(c.market))
    ok, msg = c.buy(0)
    assert not ok and "10" in msg and "robôs" in msg
    assert (len(u["squad"]), u["money"], len(c.market)) == before
    # vende ate o minimo de 5 (goleiro: precisa de pelo menos 1)
    while True:
        cand = [p for p in u["squad"] if p["pos"] != "GK" or sum(q["pos"] == "GK" for q in u["squad"]) > 1]
        ok, msg = c.sell(cand[0]["id"])
        if not ok:
            break
    assert len(u["squad"]) == C.MIN_SQUAD and "5" in msg and "robôs" in msg
    assert sum(p["pos"] == "GK" for p in u["squad"]) >= 1
    check_squads(c)


def test_buy_from_cpu_keeps_sizes_and_unique_names():
    c = _career(seed=8)
    u = c.clubs[c.user]
    for _ in range(4):
        c.market_refresh()
        k = next(k for k, e in enumerate(c.market) if e["club"] >= 0)
        src = c.market[k]["club"]
        n_src = len(c.clubs[src]["squad"])
        if len(u["squad"]) >= C.MAX_SQUAD:
            bench = [p for p in u["squad"] if p["id"] not in u["lineup"] and p["pos"] != "GK"]
            assert c.sell(bench[0]["id"])[0]
        ok, msg = c.buy(k)
        assert ok, msg
        assert len(c.clubs[src]["squad"]) == n_src                    # a CPU repoe o robo (junior)
    check_squads(c)
    # robo sem clube com o mesmo nome de um do elenco: ao entrar, ganha um nome livre
    c.market_refresh()
    k = next(k for k, e in enumerate(c.market) if e["club"] < 0)
    c.market[k]["p"]["name"] = u["squad"][0]["name"]
    if len(u["squad"]) >= C.MAX_SQUAD:
        assert c.sell(next(p["id"] for p in u["squad"] if p["id"] not in u["lineup"]))[0]
    ok, msg = c.buy(k)
    assert ok, msg
    check_squads(c)


def test_seasons_keep_squads_in_range():
    """3 temporadas simuladas com compras/vendas: elencos 5-10 (CPU 7-10), nomes unicos, aposentados repostos."""
    c = _career(seed=21, user=17)
    u = c.clubs[c.user]
    retired = 0
    for season in range(3):
        while c.round < C.ROUNDS:
            if c.round % 3 == 0 and c.market:
                if len(u["squad"]) >= C.MAX_SQUAD:
                    bench = sorted((p for p in u["squad"] if p["id"] not in u["lineup"]), key=lambda p: p["ovr"])
                    c.sell(bench[0]["id"])
                c.buy(0)
            c.play_round(None)
            c.round_stats(None)
        info = c.end_season()
        retired += len(info["retired"])
        assert all(not has_person(n) for n in info["retired"])
        check_squads(c)
        for i, cl in enumerate(c.clubs):
            if i != c.user:
                assert 7 <= len(cl["squad"]) <= 10
    assert c.season == 4


# --------------------------------------------------------------- migração
def _load_fixture():
    with open(FIXTURE, encoding="utf-8") as f:
        return f.read()


def test_fixture_is_a_real_old_save():
    d = json.loads(_load_fixture())
    assert "ver" not in d
    sq = d["clubs"][d["user"]]["squad"]
    assert len(sq) == 20 and all(12 <= len(cl["squad"]) <= 20 for cl in d["clubs"])
    assert all(has_person(p["name"]) for cl in d["clubs"] for p in cl["squad"])
    assert any(p.get("tg") for cl in d["clubs"] for p in cl["squad"])        # com artilharia acumulada


def test_migration_old_save():
    text = _load_fixture()
    old = json.loads(text)
    MEM["c"] = text
    del WRITES[:]
    c = C.Career.load()
    assert c is not None and not WRITES and MEM["c"] == text               # carregar nao grava nada
    assert c.ver == C.VERSION and c.user == old["user"] and c.formation == old["formation"]
    assert (c.season, c.round, c.next_id) == (old["season"], old["round"], old["next_id"])
    check_squads(c)
    old_by_id = {p["id"]: p for cl in old["clubs"] for p in cl["squad"]}
    for i, (cl, ocl) in enumerate(zip(c.clubs, old["clubs"])):
        assert cl["lineup"] == ocl["lineup"]                               # titulares (e a ordem) mantidos
        assert len(cl["squad"]) == min(10, len(ocl["squad"]))
        kept = {p["id"] for p in cl["squad"]}
        bench_old = sorted((p for p in ocl["squad"] if p["id"] not in ocl["lineup"]),
                           key=lambda p: (-p["ovr"], -C.value(p), p["id"]))
        expect = set(ocl["lineup"]) | {p["id"] for p in bench_old[:10 - 5]}
        if not any(old_by_id[k]["pos"] == "GK" for k in expect):
            pass                                                          # (regra do goleiro: teste proprio)
        else:
            assert kept == expect, cl["name"]
        for p in cl["squad"]:                                              # estatisticas ligadas ao id
            o = old_by_id[p["id"]]
            for k in C.PSTAT_KEYS + ("ovr", "age", "pos"):
                assert p.get(k) == o.get(k), (k, p, o)
        if i != c.user:
            assert cl["money"] == ocl["money"]
    # clube do jogador: excedentes vendidos pelo valor de mercado
    ou = old["clubs"][old["user"]]
    gone = [p for p in ou["squad"] if p["id"] not in {q["id"] for q in c.clubs[c.user]["squad"]}]
    assert len(gone) == 10
    assert c.clubs[c.user]["money"] == ou["money"] + sum(C.value(p) for p in gone)
    # nomes: o de robo do id (sem repetir no clube); nada de nome de pessoa no save
    for cl in c.clubs:
        for p in cl["squad"]:
            assert p["name"] == RN.unique_name(p["id"], {q["name"] for q in cl["squad"] if q["id"] < p["id"]})
    out = c.to_json()
    assert not has_person(out.replace('"', " ").replace(",", " "))
    # mercado: robos de clube apontam para o elenco (quem saiu, sai do mercado); sem clube renomeados
    for e in c.market:
        if e["club"] >= 0:
            assert any(e["p"] is p for p in c.clubs[e["club"]]["squad"])
        else:
            assert e["p"]["name"] == RN.name_for(e["p"]["id"])
    assert any("vendidos" in line for line in c.log)
    # idempotente: salvo de novo (ver=2) e recarregado nao muda nada (dinheiro nao entra 2 vezes)
    MEM["c"] = out
    again = C.Career.load()
    assert again.to_json() == out
    # artilharia continua
    for d in range(3):
        assert c.scorers(d, 10) == again.scorers(d, 10)
    # e a carreira segue jogando
    again.play_round(None)
    again.round_stats(None)
    check_squads(again)
    k = next((k for k, e in enumerate(again.market) if e["club"] >= 0), None)
    if k is not None:
        u = again.clubs[again.user]
        u["money"] = 10 ** 8
        ok, msg = again.buy(k)
        assert not ok and "10" in msg                                      # elenco migrado ja esta cheio


def test_migration_keeps_a_goalkeeper():
    c = C.Career()
    sq = [{"id": i, "name": "Pedro Silva", "pos": "GK" if i in (1, 2) else ("DEF" if i < 7 else "MID"),
           "ovr": 40 if i in (1, 2) else 70 - i, "age": 25} for i in range(1, 16)]
    club = {"name": "X", "color": [1, 2, 3], "div": 0, "money": 0, "squad": sq,
            "lineup": [3, 4, 7, 8, 9], "stats": C.Career.blank_stats()}         # sem goleiro escalado
    out = C.Career.trim_squad(club)
    assert len(club["squad"]) == 10 and len(out) == 5
    assert sum(p["pos"] == "GK" for p in club["squad"]) == 1
    assert {3, 4, 7, 8, 9} <= {p["id"] for p in club["squad"]}
    small = {"squad": sq[:9], "lineup": [1, 3, 4, 7, 8]}
    assert C.Career.trim_squad(small) == [] and len(small["squad"]) == 9
    del c


def test_migration_invalid_saves_never_overwritten():
    base = json.loads(_load_fixture())
    bad = []
    d = copy.deepcopy(base)
    d["user"] = 99
    bad.append(json.dumps(d))
    d = copy.deepcopy(base)
    d["clubs"][3]["squad"][0]["ovr"] = "muito"
    bad.append(json.dumps(d))
    d = copy.deepcopy(base)
    d["clubs"][2]["lineup"] = "x"
    d["clubs"][2]["squad"] = 7
    bad.append(json.dumps(d))
    bad.append(_load_fixture()[:5000])
    for text in bad:
        MEM["c"] = text
        del WRITES[:]
        assert C.Career.load() is None
        assert MEM["c"] == text and not WRITES
        # a tela tambem nao grava por cima: Continuar com save invalido volta ao menu
        g.state = "menu"
        g.career_ui.open_saved()
        assert g.state == "menu" and MEM["c"] == text and not WRITES
    # nome lixo num save novo (ver=2) vira nome de robo do id
    MEM["c"] = _load_fixture()
    c = C.Career.load()
    d = json.loads(c.to_json())
    d["clubs"][0]["squad"][0]["name"] = 5
    MEM["c"] = json.dumps(d)
    back = C.Career.load()
    p = back.clubs[0]["squad"][0]
    assert p["name"] == RN.name_for(p["id"])


# ----------------------------------------------------------------- telas
def _count_surfaces(fn, frames=20):
    real = pygame.Surface
    count = [0]

    class Counting(real):
        def __init__(self, *a, **k):
            count[0] += 1
            super().__init__(*a, **k)
    fn()
    pygame.Surface = Counting
    try:
        for _ in range(frames):
            fn()
    finally:
        pygame.Surface = real
    return count[0]


def _texts(fn):
    seen = []
    orig = g.text

    def rec(s, *a, **k):
        seen.append(str(s))
        return orig(s, *a, **k)
    g.text = rec
    try:
        fn()
    finally:
        g.text = orig
    return seen


def test_ui_squad_and_market_tabs():
    random.seed(4)
    cu = g.career_ui
    cu.open_new()
    cu.choose(9)
    club = cu.career.clubs[9]
    cu.set_tab("squad")
    seen = _texts(g.draw)
    assert "Elenco: %d/10  (mín. 5)" % len(club["squad"]) in seen
    assert all(p["name"] in seen for p in club["squad"])
    assert "ROBÔ" in seen and not any(has_person(s) for s in seen)
    assert _count_surfaces(g.draw) == 0
    cu.set_tab("market")
    seen = _texts(g.draw)
    assert "ROBÔ" in seen and not any(has_person(s) for s in seen)
    assert _count_surfaces(g.draw) == 0
    for s in seen:
        s.encode("latin-1")
    # tela de escolha do clube
    cu.open_new()
    assert _count_surfaces(g.draw) == 0
    g.state = "menu"


def test_never_touched_real_store():
    for m, n in ((gm, "_store_get"), (C, "_store_get"), (cm, "_store_get")):
        assert getattr(m, n).__name__ == "<lambda>"


def main():
    names = sys.argv[1:] or [n for n in globals() if n.startswith("test_")]
    fails = 0
    for n in names:
        try:
            globals()[n]()
            print("ok %s" % n)
        except Exception:  # noqa: BLE001
            import traceback
            fails += 1
            print("FAIL %s" % n)
            traceback.print_exc()
    print("%d testes passaram" % (len(names) - fails) if not fails else "%d falhas" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
