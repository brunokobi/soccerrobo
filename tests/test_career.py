"""Testes da Carreira com robôs: nomes de robô (game/robot_names.py), elenco de 5 a 10, mercado, temporadas, horas
de uso (fases, reciclagem, valor), REVISÃO e a migração dos saves antigos (v1: nomes de pessoa, elencos de 12-20;
v2: idade em anos -> horas de uso). Rodar da raiz:
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
# saves v2 (idade em anos) gravados pelo codigo da v2 (commit 14fb64b): o v1 acima carregado e salvo, e uma carreira
# jogada (semente 77, clube 20: 1 temporada + 5 rodadas com compras)
FIXTURE_V2_FROM_V1 = os.path.join(ROOT, "tests", "fixtures", "career_v2_from_v1.json")
FIXTURE_V2 = os.path.join(ROOT, "tests", "fixtures", "career_v2_season2.json")
SHOTS = os.environ.get("SOCCERPY_SHOTS_DIR")
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
                           key=lambda p: (-p["ovr"], -C._value_age(p), p["id"]))
        expect = set(ocl["lineup"]) | {p["id"] for p in bench_old[:10 - 5]}
        if not any(old_by_id[k]["pos"] == "GK" for k in expect):
            pass                                                          # (regra do goleiro: teste proprio)
        else:
            assert kept == expect, cl["name"]
        for p in cl["squad"]:                                              # estatisticas ligadas ao id
            o = old_by_id[p["id"]]
            for k in C.PSTAT_KEYS + ("ovr", "pos"):
                assert p.get(k) == o.get(k), (k, p, o)
            assert "age" not in p and p["hours"] == C.hours_from_age(o["age"], o["id"])
        if i != c.user:
            assert cl["money"] == ocl["money"]
    # clube do jogador: excedentes vendidos pelo valor de mercado
    ou = old["clubs"][old["user"]]
    gone = [p for p in ou["squad"] if p["id"] not in {q["id"] for q in c.clubs[c.user]["squad"]}]
    assert len(gone) == 10
    assert c.clubs[c.user]["money"] == ou["money"] + sum(C._value_age(p) for p in gone)   # vendidos como na v2
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
    # idempotente: salvo de novo (ver=3) e recarregado nao muda nada (dinheiro nao entra 2 vezes)
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


# ---------------------------------------------------------- horas de uso
def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_hours_helpers_and_phases():
    assert C.fmt_hours(0) == "0 h" and C.fmt_hours(850) == "850 h" and C.fmt_hours(999) == "999 h"
    assert C.fmt_hours(1000) == "1,0 mil h" and C.fmt_hours(7250) == "7,2 mil h" and C.fmt_hours(4999) == "4,9 mil h"
    assert C.fmt_hours(16000) == "16,0 mil h" and C.fmt_hours(-5) == "0 h"
    for h, name in ((0, "Amaciando"), (4999, "Amaciando"), (5000, "Auge"), (10999, "Auge"), (11000, "Desgaste"),
                    (15999, "Desgaste"), (16000, "Fim de vida"), (40000, "Fim de vida")):
        assert C.phase_name(h) == name, (h, name)
    for h in (0, 999, 5000, 12345, 16000):
        C.fmt_hours(h).encode("latin-1")
        C.phase_name(h).encode("latin-1")
    # idade antiga -> horas: (idade-18) x 1000 +- 300 pelo id, minimo 0, deterministico
    for pid in range(1, 400):
        v = C.hours_from_age(25, pid)
        assert 6700 <= v <= 7300 and v == 7000 + (pid * 37) % 600 - 300
        assert C.hours_from_age(18, pid) >= 0 and C.hours_from_age(17, pid) == 0
    assert C.hours_from_age(30, "x") == 12000


def test_value_by_hours():
    p = {"ovr": 70}
    base = C.base_value(p)
    for h, mult in ((0, 1.3), (4000, 1.3), (4001, 1.0), (10999, 1.0), (11000, 0.85), (13999, 0.85),
                    (14000, 0.6), (20000, 0.6)):
        p["hours"] = h
        assert C.value(p) == max(20_000, int(round(base * mult, -3))), (h, mult)
    assert C.value({"ovr": 28, "hours": 15000}) == 20_000
    # carreira nova: mesmo valor do elenco que a v2 (idade) dava, salvo na beirada das faixas (+-300 h)
    random.seed(5)
    c = C.Career.new()
    for p in all_players(c):
        assert "age" not in p and C._is_int(p["hours"]) and 0 <= p["hours"] <= 16300


def test_new_career_same_strength_as_v2():
    """As horas saem das idades sorteadas de sempre (sem RNG extra): com a mesma semente, a carreira nova tem os
    mesmos robos (id, posicao, overall, nome), caixas, escalacoes e mercado que a v2 (assinatura medida no codigo
    da v2, commit 14fb64b)."""
    import hashlib
    random.seed(77)
    c = C.Career.new()
    sig = ([(p["id"], p["pos"], p["ovr"], p["name"]) for cl in c.clubs for p in cl["squad"]]
           + [(cl["money"], tuple(cl["lineup"])) for cl in c.clubs]
           + [(e["club"], e["p"]["id"], e["p"]["ovr"]) for e in c.market])
    assert hashlib.sha1(repr(sig).encode()).hexdigest() == "8aec258f47436aed79d8d42c1ef0777efbadeb95"
    for p in all_players(c):
        assert 0 <= p["hours"] <= 16_300


def _play_season(c, rounds=C.ROUNDS):
    while c.round < rounds:
        c.play_round(None)


def test_hours_per_match_and_per_season():
    random.seed(11)
    c = C.Career.new()
    c.user = 5
    c.market_refresh()
    before = {p["id"]: p["hours"] for p in all_players(c)}
    starters = {pid for cl in c.clubs for pid in cl["lineup"]}
    c.play_round(None)                                    # todos os 24 clubes jogam (assistido ou simulado)
    for p in all_players(c):
        assert p["hours"] == before[p["id"]] + (C.HOURS_MATCH if p["id"] in starters else 0), p
    # jogo assistido pelo usuario tambem conta
    before = {p["id"]: p["hours"] for p in all_players(c)}
    c.play_round(user_score=(2, 1))
    u = c.clubs[c.user]
    for pid in u["lineup"]:
        assert c.player_by_id(c.user, pid)["hours"] == before[pid] + C.HOURS_MATCH
    for p in u["squad"]:
        if p["id"] not in u["lineup"]:
            assert p["hours"] == before[p["id"]]
    # temporada inteira de titular ~ +1000 h (14 x 50 + 300)
    random.seed(12)
    c = C.Career.new()
    c.user = 3
    c.market_refresh()
    st_ids = list(c.clubs[c.user]["lineup"])
    bench = [p["id"] for p in c.clubs[c.user]["squad"] if p["id"] not in st_ids]
    h0 = {p["id"]: p["hours"] for p in c.clubs[c.user]["squad"]}
    _play_season(c)
    random.seed(0)
    old_random = random.random
    random.random = lambda: 0.99                         # ninguem vai para a reciclagem pelo sorteio dos 40%
    try:
        c.end_season()
    finally:
        random.random = old_random
    for pid in st_ids:
        p = c.player_by_id(c.user, pid)
        if p is not None:
            assert p["hours"] == h0[pid] + C.ROUNDS * C.HOURS_MATCH + C.HOURS_SEASON == h0[pid] + 1000
    for pid in bench:
        p = c.player_by_id(c.user, pid)
        if p is not None:
            assert p["hours"] == h0[pid] + C.HOURS_SEASON


def test_phases_evolution_and_recycling():
    random.seed(3)
    c = C.Career.new()
    c.user = 0
    c.market_refresh()
    u = c.clubs[c.user]
    sq = u["squad"]
    # um robo por fase, overall 60; horas ja descontando as +300 da virada
    plan = [(0, (0, 4)), (6000, (-1, 2)), (12000, (-3, 0)), (15800, (-4, -1))]
    for p, (h, _) in zip(sq, plan):
        p["hours"], p["ovr"] = h, 60
    sq[4]["hours"] = 17_700                              # >= 18 mil depois da virada: reciclagem certa
    ids = [p["id"] for p in sq[:5]]
    names = [p["name"] for p in sq[:5]]
    _play_season(c)
    hours_after = {p["id"]: p["hours"] for p in sq[:5]}
    info = c.end_season()
    for pid, (h, (lo, hi)) in zip(ids, plan):
        p = c.player_by_id(c.user, pid)
        if p is None:                                    # o de fim de vida pode ir com 40%
            assert hours_after[pid] + C.HOURS_SEASON >= C.RECYCLE_MAYBE
            continue
        assert lo <= p["ovr"] - 60 <= hi, (h, p)
    assert c.player_by_id(c.user, ids[4]) is None and names[4] in info["retired"]
    assert any(line == "%s foi para a reciclagem." % names[4] for line in c.log)
    check_squads(c)
    # repostos chegam de fabrica (0-2000 h)
    new = [p for p in u["squad"] if p["id"] not in ids and p["id"] > max(ids)]
    assert new and all(0 <= p["hours"] <= 2000 for p in new if p["id"] >= c.next_id - 30)
    # 16 mil h: 40% (medido em muitos robos); abaixo de 16 mil nunca
    random.seed(9)
    gone = 0
    for _ in range(400):
        cl = {"squad": [{"id": 1, "name": "A", "pos": "GK", "ovr": 50, "hours": 15_700}] +
              [{"id": k, "name": "B%d" % k, "pos": "DEF", "ovr": 50, "hours": 15_699} for k in range(2, 6)],
              "lineup": [1, 2, 3, 4, 5]}
        c2 = C.Career()
        c2.clubs, c2.user, c2.next_id = [cl], 1, 100
        c2.age_players({"retired": []})
        ids2 = {p["id"] for p in cl["squad"]}
        assert {2, 3, 4, 5} <= ids2
        gone += 1 not in ids2
    assert 120 <= gone <= 200, gone


def test_hours_in_market_and_replacements():
    c = _career(seed=8)
    for e in c.market:
        assert C._is_int(e["p"]["hours"]) and "age" not in e["p"]
    k = next(k for k, e in enumerate(c.market) if e["club"] >= 0)
    src = c.market[k]["club"]
    ids = {p["id"] for p in c.clubs[src]["squad"]}
    u = c.clubs[c.user]
    if len(u["squad"]) >= C.MAX_SQUAD:
        assert c.sell(next(p["id"] for p in u["squad"] if p["id"] not in u["lineup"] and p["pos"] != "GK"))[0]
    ok, msg = c.buy(k)
    assert ok, msg
    repl = [p for p in c.clubs[src]["squad"] if p["id"] not in ids]
    assert len(repl) == 1 and 0 <= repl[0]["hours"] <= 2000


# --------------------------------------------------------------- revisão
def test_revision_rules_and_price():
    c = _career(seed=6, user=12)
    u = c.clubs[c.user]
    p = u["squad"][0]
    p["hours"], p["ovr"] = 12_400, 72
    price = C.revision_price(p)
    assert price == max(100_000, int(round(C.base_value(p) * 0.25, -3)))
    money, ovr = u["money"], p["ovr"]
    ok, msg = c.revise(p["id"])
    assert ok and p["hours"] == 9_400 and p["ovr"] == ovr and u["money"] == money - price
    assert p["rev_season"] == c.season and "revisado" in msg and c.log[0] == msg
    ok, msg = c.revise(p["id"])                          # 1 por temporada
    assert not ok and "temporada" in msg and p["hours"] == 9_400 and u["money"] == money - price
    c.season += 1                                        # na proxima temporada pode de novo, sem passar de 5 mil h
    ok, _ = c.revise(p["id"])
    assert ok and p["hours"] == 6_400
    c.season += 1
    ok, _ = c.revise(p["id"])
    assert ok and p["hours"] == 5_000                    # nao vira "novo": piso de 5 mil h
    c.season += 1
    ok, msg = c.revise(p["id"])
    assert not ok and p["hours"] == 5_000 and "5,0 mil h" in msg
    q = u["squad"][1]
    q["hours"] = 4_000
    assert not c.revise(q["id"])[0] and q["hours"] == 4_000
    # sem dinheiro
    q["hours"], q["ovr"] = 9_000, 40
    assert C.revision_price(q) == 100_000                # preco minimo
    u["money"] = 99_999
    ok, msg = c.revise(q["id"])
    assert not ok and "Dinheiro" in msg and q["hours"] == 9_000 and u["money"] == 99_999 and "rev_season" not in q
    u["money"] = 100_000
    assert c.revise(q["id"])[0] and u["money"] == 0
    # robo de outro clube: nao
    other = c.clubs[0]["squad"][0]
    assert not c.revise(other["id"])[0]


def test_revision_never_profits_with_sale():
    """Revisar e vender logo depois nunca rende mais do que vender sem revisar."""
    for ovr in range(28, 96):
        for h in range(5_001, 30_000, 97):
            p = {"ovr": ovr, "hours": h}
            sell_now = int(C.value(p) * 0.8)
            q = dict(p, hours=max(C.REV_FLOOR, h - C.REV_HOURS))
            assert int(C.value(q) * 0.8) - C.revision_price(p) < sell_now, (ovr, h)


def test_revision_saved_and_loaded():
    c = _career(seed=4, user=20)
    u = c.clubs[c.user]
    p = max(u["squad"], key=lambda q: q["hours"])
    p["hours"] = max(p["hours"], 8_000)
    assert c.revise(p["id"])[0]
    MEM["c"] = c.to_json()
    back = C.Career.load()
    bp = back.player_by_id(back.user, p["id"])
    assert bp["hours"] == p["hours"] and bp["rev_season"] == c.season
    assert not back.revise(p["id"])[0]
    d = json.loads(c.to_json())
    d["clubs"][c.user]["squad"][0]["rev_season"] = "x"
    MEM["c"] = json.dumps(d)
    assert "rev_season" not in C.Career.load().clubs[c.user]["squad"][0]


def test_cpu_never_revises():
    c = _career(seed=13, user=2)
    for _ in range(2):
        _play_season(c)
        c.end_season()
    for i, cl in enumerate(c.clubs):
        if i != c.user:
            assert all("rev_season" not in p for p in cl["squad"])


# ------------------------------------------------------- migração v2 -> v3
def test_fixtures_v2_are_real():
    for path in (FIXTURE_V2_FROM_V1, FIXTURE_V2):
        d = json.loads(_read(path))
        assert d["ver"] == 2
        ps = [p for cl in d["clubs"] for p in cl["squad"]]
        assert all(C._is_int(p["age"]) and "hours" not in p for p in ps)
        assert any(e["club"] < 0 and "age" in e["p"] for e in d["market"])


def test_migration_v2_to_v3():
    text = _read(FIXTURE_V2)
    old = json.loads(text)
    MEM["c"] = text
    del WRITES[:]
    c = C.Career.load()
    assert c is not None and not WRITES and MEM["c"] == text
    assert c.ver == 3 == C.VERSION
    assert (c.season, c.round, c.user, c.next_id) == (old["season"], old["round"], old["user"], old["next_id"])
    for cl, ocl in zip(c.clubs, old["clubs"]):
        assert cl["lineup"] == ocl["lineup"] and cl["money"] == ocl["money"]
        assert [p["id"] for p in cl["squad"]] == [p["id"] for p in ocl["squad"]]
        for p, o in zip(cl["squad"], ocl["squad"]):
            assert p["ovr"] == o["ovr"] and p["name"] == o["name"] and p["pos"] == o["pos"]   # overall igual
            assert "age" not in p and p["hours"] == max(0, (o["age"] - 18) * 1000 + (o["id"] * 37) % 600 - 300)
            for k in C.PSTAT_KEYS:
                assert p.get(k) == o.get(k)
    for e in c.market:
        assert "age" not in e["p"] and C._is_int(e["p"]["hours"])
        if e["club"] >= 0:
            assert any(e["p"] is p for p in c.clubs[e["club"]]["squad"])   # aponta para o robo do elenco
    assert len(c.market) == len(old["market"])
    assert "HORAS DE USO" in c.log[0]
    # idempotente e segue jogando (com horas)
    out = c.to_json()
    MEM["c"] = out
    again = C.Career.load()
    assert again.to_json() == out and '"age"' not in out
    _play_season(again)
    again.end_season()
    check_squads(again)


def test_migration_v1_goes_through_v2():
    """v1 -> v3 direto dá o mesmo que v1 -> v2 (gravado pelo código da v2) -> v3."""
    MEM["c"] = _load_fixture()
    a = C.Career.load()
    MEM["c"] = _read(FIXTURE_V2_FROM_V1)
    b = C.Career.load()
    assert a.ver == b.ver == 3
    assert a.to_json() == b.to_json()
    assert not any('"age"' in a.to_json() for _ in (0,))


def test_migration_v2_invalid_never_overwritten():
    base = json.loads(_read(FIXTURE_V2))
    bad = []
    d = copy.deepcopy(base)
    d["clubs"][4]["squad"][1]["age"] = "velho"
    bad.append(json.dumps(d))
    d = copy.deepcopy(base)
    del d["clubs"][0]["squad"][0]["age"]
    bad.append(json.dumps(d))
    d = copy.deepcopy(base)                               # v3 sem horas
    d["ver"] = 3
    bad.append(json.dumps(d))
    d = copy.deepcopy(base)
    d["clubs"][1]["squad"][2]["ovr"] = None
    bad.append(json.dumps(d))
    for text in bad:
        MEM["c"] = text
        del WRITES[:]
        assert C.Career.load() is None
        assert MEM["c"] == text and not WRITES
        g.state = "menu"
        g.career_ui.open_saved()
        assert g.state == "menu" and MEM["c"] == text and not WRITES
    # v3 com horas lixo no mercado sem clube: a entrada sai do mercado (nao quebra)
    MEM["c"] = _read(FIXTURE_V2)
    c = C.Career.load()
    d = json.loads(c.to_json())
    k = next(k for k, e in enumerate(d["market"]) if e["club"] < 0)
    d["market"][k]["p"]["hours"] = "x"
    MEM["c"] = json.dumps(d)
    back = C.Career.load()
    assert len(back.market) == len(d["market"]) - 1


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
    assert "USO" in seen and "IDADE" not in seen
    assert all(C.fmt_hours(p["hours"]) in seen for p in club["squad"])
    cu.set_tab("market")
    seen = _texts(g.draw)
    assert "ROBÔ" in seen and "USO" in seen and not any(has_person(s) for s in seen)
    assert _count_surfaces(g.draw) == 0
    for s in seen:
        s.encode("latin-1")
    # tela de escolha do clube
    cu.open_new()
    assert _count_surfaces(g.draw) == 0
    g.state = "menu"


def _colors_of(fn):
    seen = []
    orig = g.text

    def rec(s, size, color, *a, **k):
        seen.append((str(s), tuple(color)))
        return orig(s, size, color, *a, **k)
    g.text = rec
    try:
        fn()
    finally:
        g.text = orig
    return seen


def _shot(name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        pygame.image.save(g.screen, os.path.join(SHOTS, name))


def test_ui_hours_column_and_revision():
    import career_ui as CU
    random.seed(4)
    cu = g.career_ui
    cu.open_new()
    cu.choose(9)
    c = cu.career
    club = c.clubs[9]
    club["money"] = 3_000_000
    # um robo por fase no elenco, para a coluna USO colorida
    for p, h in zip(club["squad"], (850, 7_250, 12_400, 16_100, 3_300, 9_900, 14_200)):
        p["hours"] = h
    cu.set_tab("squad")
    seen = _colors_of(g.draw)
    cols = dict(seen)
    assert cols["850 h"] == CU.GREEN and cols["7,2 mil h"] == CU.TEXT
    assert cols["12,4 mil h"] == CU.PHASE_COLORS[2] and cols["16,1 mil h"] == CU.RED
    # seleciona o robo em desgaste: painel mostra uso + fase e o botao REVISAO com o preco
    p = next(q for q in club["squad"] if q["hours"] == 12_400)
    cu.pick_player(p["id"])
    seen = [s for s, _ in _colors_of(g.draw)]
    assert "Uso: 12,4 mil h  (Desgaste)" in seen
    _shot("carreira-elenco.png")
    price = C.revision_price(p)
    lab = "REVISÃO (%s)" % C.fmt_money(price)
    assert lab in seen
    for s in seen:
        s.encode("latin-1")
    assert _count_surfaces(g.draw) == 0
    g.draw()
    btn = next(r for r, fn, en in cu.buttons if getattr(fn, "__name__", "") == "do_revise")
    assert next(en for r, fn, en in cu.buttons if getattr(fn, "__name__", "") == "do_revise")
    money = club["money"]
    del WRITES[:]
    cu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=btn.center))
    assert p["hours"] == 9_400 and club["money"] == money - price and "revisado" in cu.msg and WRITES
    g.draw()
    seen = [s for s, _ in _colors_of(g.draw)]
    assert "Uso: 9,4 mil h  (Auge)" in seen and any("revisado" in s for s in seen)
    _shot("carreira-revisao.png")
    # de novo na mesma temporada: botao desabilitado e o motivo aparece
    cu.msg = ""
    seen = [s for s, _ in _colors_of(g.draw)]
    assert any("já foi revisado" in s for s in seen)
    assert not next(en for r, fn, en in cu.buttons if getattr(fn, "__name__", "") == "do_revise")
    assert _count_surfaces(g.draw) == 0
    # mercado: coluna USO
    cu.set_tab("market")
    g.draw()
    _shot("carreira-mercado.png")
    assert _count_surfaces(g.draw) == 0
    # fim de temporada com reciclagem
    cu.season_info = {"season": 1, "u_div": 1, "u_pos": 3, "champions": [c.clubs[0]["name"]] * 3, "prize": 1000,
                      "status": "", "retired": ["Zumbido", "Faísca"], "up": [], "down": [], "top_scorer": None}
    cu.screen_id = "season"
    seen = _texts(g.draw)
    assert any(s.startswith("Foram para a reciclagem: Zumbido, Faísca") for s in seen)
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
