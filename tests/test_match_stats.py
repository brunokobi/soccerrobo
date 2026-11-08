"""Testes das estatisticas da partida e do MELHOR DO JOGO (game/match_stats.py, ganchos do motor, SIMULAR,
acumulados nos saves e telas). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_match_stats.py [teste ...]

NUNCA toca ~/.soccerpy_*.json: os stores de garage, carreira e campanha vao para dicts em memoria, trocados
ANTES de criar o Game.
"""
import copy
import json
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
os.chdir(os.path.join(ROOT, "game"))

import pygame  # noqa: E402
from pygame import Vector2 as V  # noqa: E402

import campaign as cm  # noqa: E402
import career  # noqa: E402
import garage as gm  # noqa: E402

MEM = {}
gm._store_get = lambda: MEM.get("g")
gm._store_set = lambda t: MEM.__setitem__("g", t) or True
gm._store_set_bad = lambda t: MEM.__setitem__("gbad", t) or True
career._store_get = lambda: MEM.get("c")
career._store_set = lambda t: MEM.__setitem__("c", t) or True
cm._store_get = lambda: MEM.get("cp")
cm._store_set = lambda t: MEM.__setitem__("cp", t) or True
cm._store_set_bad = lambda t: MEM.__setitem__("cpbad", t) or True

import match_stats as MS  # noqa: E402
import narration  # noqa: E402
import robot_league as RL  # noqa: E402
import soccer  # noqa: E402
import stats_ui  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)
SK_LOADOUT = {"GK": (("elastica", 1), ("lancador", 1), ("poupanca", 1)),
              "DEF": (("muralha", 1), ("choque", 1), ("blindagem", 1)),
              "MID": (("succao", 1), ("pressao", 1), ("leitura", 1)),
              "ATT": (("arrancada", 1), ("curva", 1), ("matador", 1))}


def career_cfg(name, ovr):
    return {"name": name, "color": (50, 120, 255) if name == "A" else (235, 65, 65),
            "squad": [("%s%d" % (name, i), ovr, 100 + i if name == "A" else 200 + i, pos)
                      for i, pos in enumerate(("GK", "DEF", "MID", "MID", "ATT"))]}


def robot_cfg(name, ovr, seed, with_skills=True):
    cfg = RL.match_cfg(RL.opponent_team(name, (50, 120, 255) if name == "A" else (235, 65, 65), ovr, seed))
    if with_skills:
        for e, role in zip(cfg["squad"], RL.ROLES):
            e["skills"] = tuple(SK_LOADOUT[role])
    return cfg


def fresh_match():
    """Partida da carreira montada e no estado "play" (sem passos): para os lances construidos a mao."""
    random.seed(1)
    g.start_career_match(career_cfg("A", 65), career_cfg("B", 65))
    g.state = "play"
    g.speed_idx = 3                     # MAX: sem som/torcida/narracao nos ganchos
    return g.teams


def own(p):
    """p domina a bola (como em ball_interactions)."""
    g.ball.owner = p
    g.last_owner = p
    g.st_gain(p)


# --------------------------------------------------------------------- ganchos do motor
def test_assist_from_pass():
    t0, t1 = fresh_match()
    mid, att = t0.players[2], t0.players[4]
    own(mid)
    g.kick(mid, V(1, 0), 300)                       # qualquer chute que nao e finalizacao = passe
    assert mid.st.pa == 1 and g.st_pass is mid
    own(att)                                        # o companheiro domina: passe certo
    assert mid.st.pc == 1 and g.st_ast[0] is mid and g.st_ast[1] is att
    g.time_left -= 4.0
    g.goal(0)
    assert att.st.g == 1 and att.st.sh == 1 and att.st.sot == 1     # gol sem chute registrado conta o chute
    assert mid.st.a == 1
    assert g.events[-1]["ast"] == mid.name and g.events[-1]["apid"] == mid.pid
    assert g.events[-1]["pid"] == att.pid           # carreira: o id do jogador vai no evento


def test_no_assist_after_window_or_rival_possession():
    t0, t1 = fresh_match()
    mid, att = t0.players[2], t0.players[4]
    own(mid)
    g.kick(mid, V(1, 0), 300)
    own(att)
    g.time_left -= MS.ASSIST_WINDOW + 0.5           # passou da janela
    g.goal(0)
    assert att.st.g == 1 and mid.st.a == 0 and "ast" not in g.events[-1]
    # posse do rival no meio
    t0, t1 = fresh_match()
    mid, att = t0.players[2], t0.players[4]
    own(mid)
    g.kick(mid, V(1, 0), 300)
    own(att)
    own(t1.players[1])                              # o rival toma a bola
    own(att)                                        # e o atacante recupera (sem passe)
    g.goal(0)
    assert att.st.g == 1 and mid.st.a == 0


def test_pass_to_rival_and_own_goal():
    t0, t1 = fresh_match()
    mid = t0.players[2]
    own(mid)
    g.kick(mid, V(1, 0), 300)
    own(t1.players[2])                              # interceptado: passe errado
    assert mid.st.pa == 1 and mid.st.pc == 0 and g.st_ast is None
    # gol contra: nao e gol do robo nem gera assistencia
    t0, t1 = fresh_match()
    a2, b1 = t0.players[2], t1.players[1]
    own(a2)
    g.kick(a2, V(1, 0), 300)
    own(b1)
    g.goal(0)                                       # o ultimo a dominar foi do time 1: gol contra
    assert g.events[-1]["own"] and b1.st.og == 1 and b1.st.g == 0 and a2.st.a == 0
    st = g.st_finish()
    assert st["teams"][0]["g"] == 1 and st["teams"][1]["g"] == 0     # o gol contra conta no placar do time 0
    assert st["score"] == [1, 0]


def test_shot_save_and_goal_after_parry():
    t0, t1 = fresh_match()
    att, gk = t0.players[4], t1.players[0]
    own(att)
    g.kick(att, V(1, 0), 650)
    g.st_shot_by(att)                               # ai_shoot: o chute vira finalizacao
    assert att.st.sh == 1 and att.st.pa == 0
    own(gk)                                         # o goleiro segura: defesa e chute no gol
    assert gk.st.sv == 1 and att.st.sot == 1
    # espalmou e entrou: nao e defesa
    t0, t1 = fresh_match()
    att, gk = t0.players[4], t1.players[0]
    own(att)
    g.kick(att, V(1, 0), 650)
    g.st_shot_by(att)
    g.st_touch(gk)
    assert gk.st.sv == 1 and att.st.sot == 1
    g.goal(0)
    assert gk.st.sv == 0 and att.st.sot == 1 and att.st.sh == 1 and att.st.g == 1


def _play(cfgs, seed, tuning, on):
    soccer.STATS_ON = on
    try:
        random.seed(seed)
        g.start_robot_match(cfgs[0], cfgs[1], lambda s, e: None, tuning=tuning) if tuning else \
            g.start_career_match(cfgs[0], cfgs[1])
        n = 0
        while g.state != "over":
            g.step(1 / 60)
            n += 1
        g.match_sink = None
        evs = [{k: v for k, v in e.items() if k not in ("ast", "apid")} for e in g.events]
        pos = [(round(p.pos.x, 6), round(p.pos.y, 6), round(p.bat, 6)) for t in g.teams for p in t.players]
        return (tuple(g.score), evs, n, pos, (round(g.ball.pos.x, 6), round(g.ball.pos.y, 6)),
                random.random(), g.last_stats)
    finally:
        soccer.STATS_ON = True


def test_stats_do_not_change_the_match():
    """A mesma partida com e sem a coleta: placar, eventos, passos, posicoes, bateria e o RNG global iguais."""
    cases = [((career_cfg("A", 65), career_cfg("B", 60)), None),
             ((robot_cfg("A", 65, 11), robot_cfg("B", 65, 22)), soccer.robots.TUNING_ROBOTS)]
    for cfgs, tuning in cases:
        for seed in (3, 8):
            a = _play(cfgs, seed, tuning, True)
            b = _play(cfgs, seed, tuning, False)
            assert a[:6] == b[:6], (seed, a[0], b[0])
            assert a[6] is not None and b[6] is None
            st = a[6]
            assert st["score"] == list(a[0])
            for t in (0, 1):
                assert st["teams"][t]["g"] == a[0][t]
            assert sum(st["teams"][t]["poss"] for t in (0, 1)) == 100


def test_engine_stats_coherent():
    _sc, evs, _n, _pos, _b, _r, st = _play((robot_cfg("A", 70, 5, False), robot_cfg("B", 60, 6, False)), 4,
                                           soccer.robots.TUNING_ROBOTS, True)
    for p in st["players"]:
        assert 0 <= p["sot"] <= p["sh"] and 0 <= p["pc"] <= p["pa"] and p["g"] <= p["sot"], p
        assert all(p[k] >= 0 for k in MS.PKEYS)
        assert 0.0 <= p["nota"] <= 10.0
    assert sum(p["a"] for p in st["players"]) == sum(1 for e in g.events if "ast" in e)   # _play tira "ast"
    assert st["players"][st["mvp"]] is MS.mvp_row(st)
    assert sum(p["g"] for p in st["players"]) == sum(1 for e in evs if not e["own"])


def test_cost_per_step_negligible():
    """Ganchos so somam inteiros: o passo com coleta fica dentro do ruido (< +10%)."""
    import time
    cfgs = (career_cfg("A", 65), career_cfg("B", 65))

    def ms(on):
        best = 1e9
        for _ in range(3):
            t0 = time.perf_counter()
            r = _play(cfgs, 2, None, on)
            best = min(best, (time.perf_counter() - t0) / r[2] * 1000)
        return best
    off, on = ms(False), ms(True)
    print("  ms/step sem %.4f com %.4f (%+.1f%%)" % (off, on, (on / off - 1) * 100))
    assert on < off * 1.10 + 0.002


# --------------------------------------------------------------------- MVP
def test_mvp_deterministic_and_tiebreak():
    rows = [dict(team=0, idx=0, g=1), dict(team=1, idx=0, g=1), dict(team=1, idx=1, sv=1, tk=1)]
    for r in rows:
        for k in MS.PKEYS:
            r.setdefault(k, 0)
    # empate de pontos (gol = 30 cada): o time vencedor leva
    assert MS.pick_mvp(rows, (1, 2)) == 1
    assert MS.pick_mvp(rows, (2, 1)) == 0
    # empate no placar: lado da casa (determinístico)
    assert MS.pick_mvp(rows, (1, 1)) == 0
    assert all(MS.pick_mvp(copy.deepcopy(rows), (1, 1)) == 0 for _ in range(5))
    assert MS.pick_mvp([], (0, 0)) is None
    # nota
    assert MS.nota({"g": 2, "a": 1}) == round(5 + (60 + 20) / 30.0, 1)
    assert MS.nota({"og": 9}) == 0.0 and MS.nota({"g": 20}) == 10.0


# --------------------------------------------------------------------- SIMULAR
def test_simulated_stats_coherent_and_deterministic():
    home, away = robot_cfg("A", 70, 1, False), robot_cfg("B", 55, 2, False)
    for seed in range(40):
        sc = (seed % 5, (seed * 3) % 4)
        a = MS.sim_cfgs(random.Random(MS.seed_of("t", seed)), sc, home, away)
        b = MS.sim_cfgs(random.Random(MS.seed_of("t", seed)), sc, home, away)
        assert a == b and a["sim"]
        assert a["score"] == list(sc)
        for t in (0, 1):
            tm = a["teams"][t]
            assert tm["g"] == sc[t]
            assert sum(p["a"] for p in a["players"] if p["team"] == t) <= sc[t]
            assert tm["sv"] == a["teams"][1 - t]["sot"] - sc[1 - t]
            assert 30 <= tm["poss"] <= 70
        for p in a["players"]:
            assert p["g"] <= p["sot"] <= p["sh"] and p["pc"] <= p["pa"]
            assert p["role"] != "GK" or p["sh"] == 0
        assert 0 <= a["mvp"] < 10
    # carreira (squad em tuplas, com o overall)
    c = MS.sim_cfgs(random.Random(1), (2, 1), career_cfg("A", 70), career_cfg("B", 50))
    assert c["teams"][0]["g"] == 2 and all(p["pid"] for p in c["players"])


def test_sim_never_touches_results_or_rng():
    """SIMULAR: as estatisticas usam RNG proprio; a liga/campanha seguem exatamente como antes."""
    gg = gm.new_game(random.Random(4), "Teste")
    RL.new_league(gg, 0, random.Random(4))
    lg = gg.league
    rng = random.Random(9)
    st0 = rng.getstate()
    s = RL.sim_stats(lg, 0, 1, 2, 1, gg)
    assert rng.getstate() == st0 and s["score"] == [2, 1]
    RL.advance_round(lg, gg, random.Random(1))
    before = copy.deepcopy(lg["results"])
    RL.sim_round_stats(lg, 0, gg)
    assert lg["results"] == before and lg.get("ps")
    # campanha: o mesmo SIMULAR com e sem estatisticas -> mesmo placar, recompensas, contador de eventos
    outs = []
    orig = MS.sim_cfgs
    for stub in (False, True):
        c = cm.new_campaign(random.Random(2))
        a = c.next_action()
        while a["kind"] == "scene":
            c.finish_scene(a["id"], 0 if any(isinstance(i, dict) for i in c.scene_lines(a["id"])) else None)
            a = c.next_action()
        assert a["kind"] == "match"
        if stub:
            cm.MS.sim_cfgs = lambda *x, **k: None
        try:
            out = c.simulate_current()
        finally:
            cm.MS.sim_cfgs = orig
        outs.append((out["my"], out["opp"], out["result"], out["rewards"]["scrap"], c.stats["ev"], c.garage.scrap,
                     json.dumps(out["rewards"]["xp"], sort_keys=True)))
        if not stub:
            assert c.last_mstats is not None and c.last_mstats["sim"]
            assert sum(r["cs"]["j"] for r in c.garage.robots) == 5
    assert outs[0] == outs[1], outs


# --------------------------------------------------------------------- acumulados e saves
def test_garage_cs_and_league_ps_persist_and_migrate():
    gg = gm.new_game(random.Random(7), "Faxina")
    RL.new_league(gg, 0, random.Random(7))
    st = MS.sim_cfgs(random.Random(3), (3, 1), gg.match_cfg(), RL.team_cfg(gg.league, 1, gg))
    assert gg.add_match_stats(st, 0) == 5
    RL.credit_stats(gg.league, 0, 1, st)
    g_total = sum(r["cs"]["g"] for r in gg.robots)
    assert g_total == 3 and all(r["cs"]["j"] == 1 for r in gg.robots)
    back = gm.Garage.from_dict(json.loads(gg.to_json()))
    assert [r["cs"] for r in back.robots] == [r["cs"] for r in gg.robots]
    assert back.league["ps"] == gg.league["ps"]
    top = RL.top_scorers(back.league, 5)
    assert top and top[0][3] >= top[-1][3]
    # save antigo (sem os campos) -> zeros, sem "ps"; lixo -> zeros/descartado, liga continua valida
    d = json.loads(gg.to_json())
    for r in d["robots"]:
        r.pop("cs")
    d["league"].pop("ps")
    old = gm.Garage.from_dict(copy.deepcopy(d))
    assert all(r["cs"] == {"g": 0, "a": 0, "mvp": 0, "j": 0} for r in old.robots) and "ps" not in old.league
    d["robots"][0]["cs"] = {"g": "x", "a": -5, "mvp": 1e99, "j": True}
    d["league"]["ps"] = [[0, 1, "ok", 1, 0, 0], "lixo", [9, 1, "x", 1, 1, 1], [1, 2, "y", -1, 0, 0]]
    bad = gm.Garage.from_dict(d)
    assert bad is not None and bad.league is not None
    assert bad.robots[0]["cs"]["g"] == 0 and bad.robots[0]["cs"]["a"] == 0
    assert bad.league["ps"] == [[0, 1, "ok", 1, 0, 0], [1, 2, "y", 0, 0, 0]]     # negativo -> 0; lixo sai
    # um save v1 (sem v2 nem estatisticas) ainda migra
    v1 = json.loads(gg.to_json())
    v1["v"] = 1
    for r in v1["robots"]:
        for k in ("skills", "look", "cs"):
            r.pop(k, None)
        r["slots"].pop("modulo", None)
    assert gm.Garage.from_dict(v1) is not None


def test_campaign_tour_ps_persist():
    c = cm.new_campaign(random.Random(5))
    a = c.next_action()
    while a["kind"] == "scene":
        c.finish_scene(a["id"], 0 if any(isinstance(i, dict) for i in c.scene_lines(a["id"])) else None)
        a = c.next_action()
    st = c.sim_stats(a, 2, 0, "t")
    c.credit_stats(st, tour=True)
    assert c.tour.get("ps")
    clean = cm.Campaign.sanitize(c.to_dict())
    assert clean is not None and clean["c"]["tour"]["ps"] == c.tour["ps"]
    d = c.to_dict()
    d["c"]["tour"]["ps"] = [[0, "T", "R", 1, 2, 0], [5, "x"], [1, 3, "R", 1, 1, 1]]
    back = cm.Campaign.from_dict(d)
    assert back is not None and back.tour["ps"] == [[0, "T", "R", 1, 2, 0]]
    del d["c"]["tour"]["ps"]
    assert cm.Campaign.from_dict(d).tour.get("ps") is None
    assert c.tour_scorers(1)[0][2] >= 1


def test_career_player_stats_persist_and_season_reset():
    random.seed(12)
    c = career.Career.new()
    c.user = 3
    for _ in range(3):
        c.play_round(None)
        c.round_stats(None)
    rows = c.scorers(c.clubs[3]["div"], 10)
    assert rows and rows[0][3] >= rows[-1][3]
    total = sum(p.get("sg", 0) for idx in c.divs[0] for p in c.clubs[idx]["squad"])
    goals = sum(r["hg"] + r["ag"] for r in c.last_results if r["div"] == 0)
    assert total >= goals
    assert c.last_stats is not None and c.last_stats["sim"]
    text = c.to_json()
    MEM["c"] = text
    back = career.Career.load()
    assert back.scorers(0, 5) == c.scorers(0, 5)
    # lixo nos campos opcionais -> zero (o save continua valido); sem os campos -> zeros na leitura
    d = json.loads(text)
    d["clubs"][0]["squad"][0]["sg"] = "abc"
    d["clubs"][0]["squad"][1]["tg"] = -3
    MEM["c"] = json.dumps(d)
    back = career.Career.load()
    assert back is not None and back.clubs[0]["squad"][0]["sg"] == 0 and back.clubs[0]["squad"][1]["tg"] == 0
    for club in d["clubs"]:
        for p in club["squad"]:
            for k in career.PSTAT_KEYS:
                p.pop(k, None)
    MEM["c"] = json.dumps(d)
    back = career.Career.load()
    assert back.scorers(0, 5) == []
    # fim de temporada: zera a temporada, mantem a carreira
    while c.round < career.ROUNDS:
        c.play_round(None)
        c.round_stats(None)
    tg = {p["id"]: p.get("tg", 0) for cl in c.clubs for p in cl["squad"]}
    info = c.end_season()
    assert info["top_scorer"] is not None and info["top_scorer"][3] > 0
    assert all("sg" not in p for cl in c.clubs for p in cl["squad"])
    kept = [p for cl in c.clubs for p in cl["squad"] if p["id"] in tg]          # os que nao se aposentaram
    assert kept and all(p.get("tg", 0) == tg[p["id"]] for p in kept) and any(p.get("tg", 0) for p in kept)


# --------------------------------------------------------------------- narracao e telas
def test_narration_announces_mvp_once():
    n = narration.Narration([("A", (255, 0, 0), ["a1", "a2", "a3", "a4", "a5"]),
                             ("B", (0, 0, 255), ["b1", "b2", "b3", "b4", "b5"])], g.text_img, seed=1)
    n.event("end_win", 0, None, score=[1, 0], minute=90, mvp=(1, 2))
    kinds = [q[6] for q in n.queue]
    assert kinds == ["end_win", "mvp"], kinds
    assert all(s.encode("latin-1") for s in narration.all_strings())


def _count_surfaces(fn, frames=30):
    real = pygame.Surface
    count = [0]

    class Counting(real):
        def __init__(self, *a, **k):
            count[0] += 1
            super().__init__(*a, **k)
    fn()                                            # aquece caches (texto/sprite)
    pygame.Surface = Counting
    try:
        for _ in range(frames):
            fn()
    finally:
        pygame.Surface = real
    return count[0]


def test_screens_zero_surface_per_frame_and_latin1():
    for s in stats_ui.all_strings():
        s.encode("latin-1")
    # fim do amistoso (placar com o MVP e o painel ESTATISTICAS)
    random.seed(5)
    g.new_match(1)
    g.state = "kickoff"
    while g.state != "over":
        g.step(1 / 60)
    assert g.last_stats is not None
    assert _count_surfaces(g.draw) == 0
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0, unicode="\t"))
    assert g.stats_tab
    assert _count_surfaces(g.draw) == 0
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"))
    assert not g.stats_tab and g.last_stats is None          # revanche: zera
    # card do resumo do Modo Robos (simulado) nas duas vistas e a ARTILHARIA da liga
    ui = g.robots_ui
    ui.open()
    ui.garage = gm.new_game(random.Random(5), "Faxina FC")
    RL.new_league(ui.garage, 0, random.Random(5))
    ui.go("hub")
    ui.do_sim()
    assert ui.screen_id == "round" and ui.round_info["stats"]["sim"]
    assert _count_surfaces(g.draw) == 0
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0, unicode="\t"))
    assert ui.stats_view
    assert _count_surfaces(g.draw) == 0
    ui.round_continue()
    ui.set_hub_tab("scorers")
    assert _count_surfaces(g.draw) == 0
    ui.go("garage")
    assert _count_surfaces(g.draw) == 0
    ui.to_menu()
    # carreira: resultado com o MVP e o painel; artilharia e elenco
    cu = g.career_ui
    cu.open_new()
    cu.choose(8)
    cu.quick_sim()
    assert cu.round_info["stats"] is not None
    assert _count_surfaces(g.draw) == 0
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0, unicode="\t"))
    assert cu.stats_view
    assert _count_surfaces(g.draw) == 0
    cu.after_round()
    cu.set_tab("table")
    cu.table_mode = "scorers"
    assert _count_surfaces(g.draw) == 0
    cu.set_tab("squad")
    assert _count_surfaces(g.draw) == 0
    g.state = "menu"


def test_never_touched_real_store():
    for m, n in ((gm, "_store_get"), (career, "_store_get"), (cm, "_store_get")):
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
