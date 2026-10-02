"""Harness de simulacao headless do soccerpy.

Uso (da raiz do repo):
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/sim_harness.py golden --write
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/sim_harness.py golden --check
  ... tests/sim_harness.py golden-new --write|--check   (padrao novo: TUNING + bateria; regressao do balanco)
  ... tests/sim_harness.py run 80 50 40 [seed0] [legacy]

O golden confere o MODO LEGADO: ele aplica LEGACY_TUNING + BATTERY_ON=False explicitamente
(o padrao do jogo agora e TUNING + BATTERY_ON=True) e tem de ficar 80/80.
  ... tests/sim_harness.py draw
  ... tests/sim_harness.py shot out.png
"""
import json
import os
import random
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(os.path.dirname(HERE), "game")
sys.path.insert(0, GAME)
os.chdir(GAME)

import pygame  # noqa: E402
import soccer  # noqa: E402

GOLDEN_PATH = os.path.join(HERE, "baseline_golden.json")
GOLDEN_NEW_PATH = os.path.join(HERE, "baseline_golden_new.json")
MATCHUPS = [(65, 65), (80, 50), (50, 80), (70, 60)]
SEEDS = range(20)

pygame.init()
_scr = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(_scr)


class mode:
    """Contexto que fixa o modo do motor: legacy=True -> LEGACY_TUNING + BATTERY_ON=False."""

    def __init__(self, legacy):
        self.legacy = legacy

    def __enter__(self):
        self.old = (soccer.ACTIVE_TUNING, soccer.BATTERY_ON)
        if self.legacy:
            soccer.ACTIVE_TUNING, soccer.BATTERY_ON = soccer.robots.LEGACY_TUNING, False
        else:
            soccer.ACTIVE_TUNING, soccer.BATTERY_ON = soccer.robots.TUNING, True

    def __exit__(self, *a):
        soccer.ACTIVE_TUNING, soccer.BATTERY_ON = self.old


def cfg(name, ovr):
    color = (50, 120, 255) if name == "A" else (235, 65, 65)
    return {"name": name, "color": color, "squad": [("x%d" % i, ovr) for i in range(5)]}


def play(home_ovr, away_ovr, seed):
    """Uma partida completa; devolve (gols_casa, gols_fora, steps)."""
    random.seed(seed)
    g.start_career_match(cfg("A", home_ovr), cfg("B", away_ovr))
    steps = 0
    while g.state != "over":
        g.step(1 / 60)
        steps += 1
    return g.score[0], g.score[1], steps


def run(ovr_a, ovr_b, n, seed0=0, legacy=False):
    """n partidas, A mandante nas pares e visitante nas impares.
    Retorna dict: goals_per_game, wld (V/D/E de A), ms_step."""
    goals = 0
    wld = [0, 0, 0]
    steps = 0
    t0 = time.perf_counter()
    for i in range(n):
        with mode(legacy):
            if i % 2 == 0:
                ga, gb, s = play(ovr_a, ovr_b, seed0 + i)
            else:
                gb, ga, s = play(ovr_b, ovr_a, seed0 + i)
        steps += s
        goals += ga + gb
        wld[0 if ga > gb else 1 if gb > ga else 2] += 1
    dt = time.perf_counter() - t0
    return {"goals_per_game": goals / n, "wld": wld, "ms_step": dt / steps * 1000}


def _prep_play(mode=1, warm=120):
    random.seed(0)
    g.new_match(mode)
    g.state = "play"
    for _ in range(warm):
        g.step(1 / 60)


def shot(path, mode=1, warm=120):
    _prep_play(mode, warm)
    g.draw()
    pygame.image.save(_scr, path)
    return path


def draw_ms(n=300):
    _prep_play()
    t = time.perf_counter()
    for _ in range(n):
        g.draw()
    play_ms = (time.perf_counter() - t) / n * 1000
    g.state = "menu"
    t = time.perf_counter()
    for _ in range(100):
        g.draw()
    menu_ms = (time.perf_counter() - t) / 100 * 1000
    return {"draw_ms": play_ms, "menu_ms": menu_ms}


def golden_scores():
    out = {}
    for oa, ob in MATCHUPS:
        out["%dx%d" % (oa, ob)] = [list(play(oa, ob, s)[:2]) for s in SEEDS]
    return out


def golden(flag, legacy=True):
    path = GOLDEN_PATH if legacy else GOLDEN_NEW_PATH
    with mode(legacy):
        cur = golden_scores()
    if flag == "--write":
        with open(path, "w") as f:
            json.dump(cur, f, indent=1)
        print("golden gravado:", path, "(%d placares)" % sum(len(v) for v in cur.values()))
        return 0
    with open(path) as f:
        ref = json.load(f)
    bad = 0
    for k, v in cur.items():
        for s, (a, b) in enumerate(zip(v, ref.get(k, []))):
            if a != b:
                bad += 1
                print("DIFF", k, "seed", s, "atual", a, "golden", b)
    n = sum(len(v) for v in cur.values())
    print("golden%s %s: %d/%d placares identicos" % ("" if legacy else "-new", "OK" if not bad else "FALHOU", n - bad, n))
    return 1 if bad else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["golden"] and len(a) == 2 and a[1] in ("--write", "--check"):
        sys.exit(golden(a[1]))
    elif a[:1] == ["golden-new"] and len(a) == 2 and a[1] in ("--write", "--check"):
        sys.exit(golden(a[1], legacy=False))
    elif a[:1] == ["run"]:
        print(run(int(a[1]), int(a[2]), int(a[3]), int(a[4]) if len(a) > 4 and a[4].isdigit() else 0,
                  legacy="legacy" in a))
    elif a[:1] == ["draw"]:
        print(draw_ms())
    elif a[:1] == ["shot"]:
        print(shot(a[1]))
    else:
        print(__doc__)
        sys.exit(2)
