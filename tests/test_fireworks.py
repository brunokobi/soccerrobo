"""Testes dos fogos do gol/vitoria (game/fireworks.py + hooks em soccer.py). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_fireworks.py [teste ...]

NUNCA toca ~/.soccerpy_*.json: stores em memoria e store.write e uma sentinela que FALHA se chamada.
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

import campaign as cm  # noqa: E402
import career  # noqa: E402
import garage as gm  # noqa: E402
import prefs  # noqa: E402
import store  # noqa: E402


def _forbid(name):
    def f(*a, **k):
        raise AssertionError("%s chamada pelos testes dos fogos" % name)
    return f


PREFS = {}
prefs._store_get = lambda: PREFS.get("raw")
prefs._store_set = lambda t: PREFS.__setitem__("raw", t) or True
cm._store_get = lambda: None
cm._store_set = _forbid("campaign._store_set")
gm._store_get = lambda: None
gm._store_set = _forbid("garage._store_set")
career._store_get = lambda: None
career._store_set = _forbid("career._store_set")
store.write = _forbid("store.write")

import fireworks as FW  # noqa: E402
import soccer  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
AREA = pygame.Rect(60, 90, 980, 560)


def _run(fw, t0, secs, surf=None, step=1 / 60):
    t = t0
    peak = 0
    while t < t0 + secs:
        t += step
        fw.draw(surf or screen, t)
        peak = max(peak, len(fw.sparks))
    return t, peak


def test_show_launches_bursts_and_ends():
    fw = FW.Fireworks(seed=3)
    assert not fw.active
    fw.show(100.0, 5, [(40, 120, 255)], AREA)
    assert fw.active and len(fw.queue) == 5
    fw.draw(screen, 100.0)                         # 1o quadro: lanca o primeiro foguete
    assert len(fw.rockets) == 1
    t, peak = _run(fw, 100.0, 3.0)
    assert peak > 20                               # estourou em faiscas
    for x, y, *_ in fw.sparks:
        assert -200 < x < 1300 and -200 < y < 900
    t, _ = _run(fw, t, 6.0)
    assert not fw.active                           # tudo some sozinho


def test_bursts_happen_above_the_pitch():
    fw = FW.Fireworks(seed=5)
    fw.show(0.0, 8, [(255, 255, 255)], AREA)
    t = 0.0
    seen = []
    while t < 6.0:
        t += 1 / 60
        fw.draw(screen, t)
        seen += [(f[0], f[1]) for f in fw.flashes]
    assert seen
    for x, y in seen:
        assert AREA.left <= x <= AREA.right and AREA.top - 30 <= y <= AREA.top + AREA.h * 0.6, (x, y)


def test_caps_and_queue_limit():
    fw = FW.Fireworks(seed=1)
    for _ in range(50):
        fw.show(0.0, 10, [(255, 0, 0)], AREA)      # partida simulada sem desenho: nao acumula
    assert len(fw.queue) <= FW.QUEUE_MAX
    _, peak = _run(fw, 0.0, 4.0, step=1 / 30)
    assert peak <= FW.SPARK_MAX and len(fw.rockets) <= FW.ROCKET_MAX


def test_paused_freezes_and_clear():
    fw = FW.Fireworks(seed=2)
    fw.show(0.0, 3, [(0, 200, 0)], AREA)
    _run(fw, 0.0, 1.2)
    snap = [list(p) for p in fw.sparks] + [list(r[:4]) for r in fw.rockets]
    fw.draw(screen, 1.5, paused=True)
    assert [list(p) for p in fw.sparks] + [list(r[:4]) for r in fw.rockets] == snap
    fw.clear()
    assert not fw.active


def test_deterministic_and_no_global_random():
    def trace():
        fw = FW.Fireworks(seed=9)
        fw.show(0.0, 6, [(10, 10, 60), (200, 200, 0)], AREA)   # cor escura e clareada
        out = []
        t = 0.0
        for _ in range(240):
            t += 1 / 60
            fw.draw(screen, t)
            out.append((len(fw.rockets), len(fw.sparks), round(sum(p[0] for p in fw.sparks), 3)))
        return out
    random.seed(123)
    a = trace()
    r1 = random.random()
    random.seed(123)
    b = trace()
    assert a == b and random.random() == r1
    assert max(FW._bright((10, 10, 60))) >= 160


def test_goal_triggers_fireworks_but_not_in_max_and_sim_identical():
    g = soccer.Game(screen)
    g.new_match(1, None)
    g.teams[0].human = None
    g.speed_idx = 0
    g.fireworks_show(soccer.GOAL_ROCKETS, (50, 120, 255))
    assert len(g.fw.queue) == soccer.GOAL_ROCKETS
    g.fw.clear()
    g.speed_idx = 3
    g.fireworks_show(soccer.GOAL_ROCKETS, (50, 120, 255))
    assert not g.fw.active                          # MAX: nada
    g.speed_idx = 0
    g.reset_fx()
    # a simulacao nao muda com os fogos (RNG proprio): mesmo placar/bola com e sem desenho
    def run(draw):
        random.seed(77)
        g.new_match(1, None)
        g.teams[0].human = None
        for i in range(2400):
            g.step(1 / 60)
            if draw and i % 4 == 0:
                g.draw()
        return list(g.score), round(g.ball.pos.x, 4), round(g.ball.pos.y, 4), random.random()
    assert run(False) == run(True)


def test_team_names_upper_in_hud():
    g = soccer.Game(screen)
    g.new_match(1, None)
    g.teams[0].name = "Poeira fc"
    g.text_cache.clear()
    g.draw_hud()
    assert any(k[0] == "POEIRA FC" for k in g.text_cache)
    assert not any(k[0] == "Poeira fc" for k in g.text_cache)


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
