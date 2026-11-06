"""Testes dos modificadores de arena da Torre do Po (Onda D, game/soccer.py): opt-in por partida, desligados
em todos os modos existentes (os goldens 80/80 cobrem o caminho legado), efeito de cada um e desenho sem
Surface por quadro.

Rodar da raiz: SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_arena.py
Nao grava em nenhum ~/.soccerpy_*.json (so o motor; nenhum save e aberto).
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
from pygame import Vector2 as V  # noqa: E402

import campaign as cm  # noqa: E402
import prefs  # noqa: E402
import robots  # noqa: E402
import soccer  # noqa: E402

prefs._store_get = lambda: '{"v": 1, "crowd": "OFF"}'    # torcida OFF: o warm nao muda a simulacao
prefs._store_set = lambda t: True
prefs.reset_cache()

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)
PASS, FAIL = [], []
ROLES = [r for r, _fx, _fy in soccer.FORMATION]


def robot_cfg(name, ovr=65, pid0=0):
    squad = []
    for i, role in enumerate(ROLES):
        ch = robots.ROLE_CHASSIS[role]
        squad.append({"name": "x%d" % i, "chassis": ch, "pid": pid0 + i, "paint": None,
                      "attrs": robots.from_overall(ovr, role, ch)})
    return {"name": name, "color": (50, 120, 255) if name == "A" else (235, 65, 65), "squad": squad}


def start(arena=None, seed=3, **kw):
    random.seed(seed)
    g.start_robot_match(robot_cfg("A", 70), robot_cfg("B", 70, 10), lambda s, e: None, arena=arena, **kw)


def run(arena, seed=3):
    """Partida inteira: (placar, trilha da bola amostrada)."""
    start(arena, seed)
    trail = []
    n = 0
    while g.state != "over":
        g.step(1 / 60)
        n += 1
        if n % 90 == 0:
            trail.append((round(g.ball.pos.x, 3), round(g.ball.pos.y, 3)))
    return tuple(g.score), trail


def test_default_off_everywhere():
    g.new_match(1)
    assert g.arena is None
    g.start_career_match(robot_cfg("A"), robot_cfg("B"))
    assert g.arena is None
    start()
    assert g.arena is None
    start("nao_existe")
    assert g.arena is None                                    # id desconhecido nunca liga nada
    for m in soccer.ARENA_MODS:
        start(m)
        assert g.arena == m
    g.finish_career_match()
    assert g.arena is None
    assert set(soccer.ARENA_MODS) == set(cm.TOWER_MOD_CYCLE) == set(cm.ARENA_SIM_DF) == set(soccer.ARENA_LABELS)


def test_deterministic_and_each_modifier_changes_the_match():
    base = run(None)
    assert run(None) == base                                  # mesmo seed, mesma partida
    for m in soccer.ARENA_MODS:
        assert run(m) != base, m
        assert run(m) == run(m), m


def test_heavy_ball_drag():
    for arena, keep in ((None, 0.35), ("bola_pesada", soccer.ARENA_BALL_DRAG)):
        start(arena)
        b = g.ball
        b.owner = None
        b.pos, b.vel = V(soccer.CX, soccer.CY - 150), V(300, 0)
        for t in g.teams:                                    # ninguem perto da bola
            for p in t.players:
                p.pos = V(soccer.CX, soccer.CY + 200)
        g.update_ball(0.5)
        assert abs(b.vel.x - 300 * keep ** 0.5) < 1e-6, (arena, b.vel)


def test_short_battery_drain():
    out = {}
    for arena in (None, "bateria_curta"):
        start(arena)
        p = g.teams[0].players[2]
        p.bat = 1.0
        p.vel = V(soccer.PLAYER_SPEED * p.spd, 0)
        g.tick_battery(p, 0.5)
        out[arena] = 1.0 - p.bat
    assert out[None] > 0 and abs(out["bateria_curta"] - out[None] * soccer.ARENA_BAT_DRAIN) < 1e-9


def test_giant_goalkeeper_reach_only_rival():
    for arena, owned in ((None, False), ("goleiro_gigante", True)):
        start(arena)
        gk = g.teams[1].players[0]
        assert gk.role == "GK"
        for t in g.teams:
            for p in t.players:
                if p is not gk:
                    p.pos = V(soccer.CX, soccer.CY + 250)
                p.cd = 0.0
        b = g.ball
        b.owner, b.vel, b.air = None, V(0, 0), 0.0
        b.pos = gk.pos + V(0, soccer.PR + soccer.BR + 12 + soccer.ARENA_GK_REACH - 2)
        g.ball_interactions()
        assert (b.owner is gk) is owned, arena
    start("goleiro_gigante")                                  # o goleiro do usuario (lado 0) nao cresce
    gk = g.teams[0].players[0]
    for t in g.teams:
        for p in t.players:
            if p is not gk:
                p.pos = V(soccer.CX, soccer.CY + 250)
            p.cd = 0.0
    g.ball.owner, g.ball.vel = None, V(0, 0)
    g.ball.pos = gk.pos + V(0, soccer.PR + soccer.BR + 12 + soccer.ARENA_GK_REACH - 2)
    g.ball_interactions()
    assert g.ball.owner is None


def test_hud_label_and_zero_surface_per_frame():
    start("goleiro_gigante", venue="coliseu")
    g.state = "play"
    for _ in range(5):
        g.update(1 / 60)
        g.draw()
    real = pygame.Surface
    count = [0]

    class Counting(real):
        def __init__(self, *a, **k):
            count[0] += 1
            super().__init__(*a, **k)

    pygame.Surface = Counting
    try:
        for _ in range(60):
            g.update(1 / 60)
            g.draw()
    finally:
        pygame.Surface = real
    assert count[0] == 0, count[0]
    assert any("GOLEIRO GIGANTE" in k[0] for k in g.text_cache)
    shots = os.environ.get("SOCCERPY_SHOTS_DIR")
    if shots:
        os.makedirs(shots, exist_ok=True)
        pygame.image.save(g.screen, os.path.join(shots, "d2_torre_partida_goleiro_gigante.png"))
    g.finish_career_match()


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
