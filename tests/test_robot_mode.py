"""Testes do caminho do motor para o modo robos (atributos diretos, tuning por robo, sink de partida).

Rodar da raiz: .venv/bin/python tests/test_robot_mode.py (SDL dummy).
"""
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
os.chdir(os.path.join(ROOT, "game"))

import pygame  # noqa: E402

import robots  # noqa: E402
import soccer  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)

SEEDS = range(8)
ROLES = [r for r, _fx, _fy in soccer.FORMATION]     # GK, DEF, MID, MID, ATT


def classic_cfg(name, ovr=65):
    return {"name": name, "color": (50, 120, 255) if name == "A" else (235, 65, 65),
            "squad": [("x%d" % i, ovr) for i in range(5)]}


def robot_cfg(name, ovr=65, pid0=0):
    squad = []
    for i, role in enumerate(ROLES):
        ch = robots.ROLE_CHASSIS[role]
        squad.append({"name": "x%d" % i, "chassis": ch, "pid": pid0 + i, "paint": None,
                      "attrs": robots.from_overall(ovr, role, ch)})
    return {"name": name, "color": (50, 120, 255) if name == "A" else (235, 65, 65), "squad": squad}


def run_match():
    steps = 0
    while g.state != "over":
        g.step(1 / 60)
        steps += 1
    return list(g.score), list(g.events), steps


class engine_mode:
    def __init__(self, tuning, battery=True):
        self.new = (tuning, battery)

    def __enter__(self):
        self.old = (soccer.ACTIVE_TUNING, soccer.BATTERY_ON)
        soccer.ACTIVE_TUNING, soccer.BATTERY_ON = self.new

    def __exit__(self, *a):
        soccer.ACTIVE_TUNING, soccer.BATTERY_ON = self.old


def classic(seed):
    random.seed(seed)
    g.start_career_match(classic_cfg("A"), classic_cfg("B"))
    return run_match()


def robot(seed, on_done=None, tuning=robots.TUNING):
    random.seed(seed)
    g.start_robot_match(robot_cfg("A", pid0=0), robot_cfg("B", pid0=10), on_done or (lambda s, e: None),
                        tuning=tuning)
    return run_match()


def test_parity_with_classic():
    with engine_mode(robots.TUNING):
        for seed in SEEDS:
            sc, ev_c, st_c = classic(seed)
            sr, ev_r, st_r = robot(seed)
            assert sc == sr, (seed, sc, sr)
            assert len(ev_c) == len(ev_r), seed
            assert st_c == st_r, seed
            assert [(e["min"], e["team"], e["name"]) for e in ev_c] == \
                   [(e["min"], e["team"], e["name"]) for e in ev_r], seed


def test_tuning_from_argument_not_global():
    with engine_mode(robots.LEGACY_TUNING, False):          # global diferente: o robo ignora
        random.seed(1)
        g.start_robot_match(robot_cfg("A"), robot_cfg("B"), lambda s, e: None, tuning=robots.TUNING_ROBOTS)
        before = (soccer.ACTIVE_TUNING, soccer.BATTERY_ON)
        for t in g.teams:
            for p in t.players:
                assert p.tuning is robots.TUNING_ROBOTS
                exp = robots.factors(p.robot, robots.TUNING_ROBOTS)
                for n in ("speed", "kick_pow", "tackle", "gk_save"):
                    assert getattr(p.f, n) == getattr(exp, n), n
        assert p.robot == robots.from_overall(65, "ATT", "Velocista")
    # sem tuning explicito vale TUNING_ROBOTS (padrao de start_robot_match)
    g.start_robot_match(robot_cfg("A"), robot_cfg("B"), lambda s, e: None)
    assert g.teams[0].players[0].tuning is robots.TUNING_ROBOTS
    assert soccer.ACTIVE_TUNING is robots.TUNING and soccer.BATTERY_ON is True
    assert before == (robots.LEGACY_TUNING, False)


def test_global_rng_order_preserved():
    # construir times por dict nao consome RNG alem do random() de Player.think
    random.seed(3)
    soccer.Team(0, "A", (1, 2, 3), (4, 5, 6), None, robot_cfg("A")["squad"], robots.TUNING)
    a = random.random()
    random.seed(3)
    soccer.Team(0, "A", (1, 2, 3), (4, 5, 6), None, classic_cfg("A")["squad"])
    assert random.random() == a


def test_goal_event_has_pid():
    with engine_mode(robots.TUNING):
        found = False
        for seed in range(40):
            _s, evs, _n = robot(seed)
            goals = [e for e in evs if not e["own"]] + [e for e in evs if e["own"]]
            if not evs:
                continue
            found = True
            for e in goals:
                assert "pid" in e
                # nome "x<i>" do time A tem pid i, do time B pid 10+i; o ultimo dono fez o gol
                # (gol contra: pid do adversario que tocou por ultimo)
                owner_team = e["team"] if not e["own"] else 1 - e["team"]
                assert e["pid"] == (0 if owner_team == 0 else 10) + int(e["name"][1:]), e
            break
        assert found, "nenhuma seed com gol em 40 partidas"
    # partida classica: pid None
    with engine_mode(robots.TUNING):
        for seed in range(40):
            _s, evs, _n = classic(seed)
            if evs:
                assert all(e["pid"] is None for e in evs)
                break


def test_robot_match_calls_sink_and_returns_state():
    with engine_mode(robots.TUNING):
        got = []
        robot(2, on_done=lambda s, e: got.append((s, e, g.state)))
        assert g.match_sink == ("robots", g.match_sink[1])
        score = list(g.score)
        g.finish_career_match()
        assert len(got) == 1
        s, e, state_at_call = got[0]
        assert s == score and isinstance(e, list)
        assert state_at_call == "robots" and g.state == "robots"
        assert g.match_sink is None and g.career_match is False
        assert soccer.ACTIVE_TUNING is robots.TUNING
        g.state = "menu"


def test_robots_state_without_ui_does_not_break():
    assert getattr(g, "robots_ui", None) is None
    g.state = "robots"
    g.draw()
    g.state = "robots"
    g.update(1 / 60)
    assert g.state == "menu"
    g.state = "robots"
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))
    assert g.state == "menu"


def test_paint_sets_led_and_sprite():
    cfg = robot_cfg("A")
    cfg["squad"][4]["paint"] = (255, 0, 200)
    g.start_robot_match(cfg, robot_cfg("B"), lambda s, e: None)
    p = g.teams[0].players[4]
    ch, led, gk = g.sprite_key(g.teams[0], p)
    assert led == soccer.led_color((255, 0, 200)) and not gk
    ch2, led2, _ = g.sprite_key(g.teams[0], g.teams[0].players[3])
    assert led2 == soccer.led_color(g.teams[0].color)
    spr = g.get_sprite(ch, led, gk, False)
    assert g.get_sprite(ch, led, gk, False) is spr
    g.draw()
    g.state = "menu"


def test_career_match_still_works_and_clears_sink():
    g.start_robot_match(robot_cfg("A"), robot_cfg("B"), lambda s, e: None)
    assert g.match_sink is not None
    with engine_mode(robots.TUNING):
        random.seed(5)
        g.start_career_match(classic_cfg("A"), classic_cfg("B"))
        assert g.match_sink is None
        assert g.teams[0].players[0].tuning is soccer.ACTIVE_TUNING
        run_match()
    called = []
    orig = g.career_ui.match_done
    g.career_ui.match_done = lambda s, e: called.append((s, e))
    try:
        g.finish_career_match()
    finally:
        g.career_ui.match_done = orig
    assert len(called) == 1 and g.state == "career"
    g.state = "menu"
    # partida amistosa tambem limpa o sink
    g.start_robot_match(robot_cfg("A"), robot_cfg("B"), lambda s, e: None)
    g.new_match(1)
    assert g.match_sink is None
    g.state = "menu"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok", t.__name__)
    print(len(tests), "testes passaram")
