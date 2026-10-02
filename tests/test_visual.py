"""Testes da camada visual/estado (rodar: .venv/bin/python tests/test_visual.py, com SDL dummy)."""
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
os.chdir(os.path.join(ROOT, "game"))

import pygame  # noqa: E402

import soccer  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)


def cfg(name, color):
    return {"name": name, "color": color, "squad": [("J%d" % i, 65) for i in range(5)]}


def test_led_color_dark_is_lightened():
    lum = lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    assert lum(soccer.led_color((40, 40, 50))) >= 120


def test_clash_uses_led_colors():
    # Corsários (40,40,50) x Lobos (90,100,110): iguais depois de clarear -> visitante muda de cor
    g.start_career_match(cfg("A", (40, 40, 50)), cfg("B", (90, 100, 110)))
    a, b = (soccer.led_color(t.color) for t in g.teams)
    assert sum(abs(x - y) for x, y in zip(a, b)) >= 130, (a, b)


def test_fx_cap_and_noop():
    g.new_match(1)
    for _ in range(500):
        g.fx_emit("goal", soccer.V(500, 300))
    assert len(g.fx) <= soccer.FX_MAX
    g.reset_fx()
    g.speed_idx = 3
    g.fx_emit("goal", soccer.V(500, 300))
    assert g.fx == []
    g.speed_idx = 0


def test_draw_and_fx_do_not_touch_global_rng():
    g.new_match(1)
    st = random.getstate()
    g.fx_emit("goal", soccer.V(500, 300))
    for _ in range(5):
        g.draw()
    assert random.getstate() == st


def test_trail_frozen_when_paused():
    g.new_match(1)
    g.state = "play"
    g.ball.vel = soccer.V(500, 0)
    g.paused = True
    for _ in range(10):
        g.draw()
    assert len(g.trail) == 0
    g.paused = False


def test_load_ignores_unknown_keys():
    import career
    career._store_get = lambda: '{"play_round": 1, "user": null, "season": 3}'
    c = career.Career.load()
    assert c is not None and c.season == 3 and callable(c.play_round)
    career._store_get = lambda: '{"user": 5, "clubs": []}'
    assert career.Career.load() is None


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok", t.__name__)
    print(len(tests), "testes passaram")
