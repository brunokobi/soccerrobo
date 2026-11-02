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


def test_robot_art_module_matches_game():
    # Fase 4, passo 0.4: a arte dos robos mora em robot_art.py; Game so delega
    import robot_art
    assert robot_art.PR == soccer.PR
    assert soccer.led_color is robot_art.led_color and soccer.scale_color is robot_art.scale_color
    g.new_match(1)
    g.warm_sprites()
    t = g.teams[0]
    ch, led, gk = g.sprite_key(t, t.players[0])
    assert (ch, led, gk) == robot_art.sprite_key(t, t.players[0])
    assert g.get_sprite(ch, led, gk, True) is robot_art.get_sprite(g.sprites, ch, led, gk, True)
    assert g.build_robot_sprite(ch, led, gk, False).get_size() == (64, 64)


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


# ------------------------------------------------------------------ B13: cosmeticos (so visuais)
class FakeTime:
    """Substitui soccer.time: relogio que avanca 1/60 s por quadro (rastro deterministico)."""

    def __init__(self, t=500.0):
        self.t = t

    def perf_counter(self):
        return self.t


def cosmetic_cfgs(look=True):
    """(casa, fora) do Modo Robos; com look, cada robo usa adesivo/antena/rastro/comemoracao distintos."""
    import garage as gm
    import parts
    out = []
    for seed in (4, 5):
        gg = gm.new_game(random.Random(seed))
        if look:
            for cid in sorted(parts.COSMETICS):
                gg.grant_cosmetic(cid)
            for i, rid in enumerate(gg.lineup):
                for kind in ("decal", "antenna", "trail", "celebration"):
                    ids = parts.LOOK_KINDS[kind]
                    assert gg.equip_look(rid, ids[(i + seed) % len(ids)])[0]
        out.append(gg.match_cfg())
    return out


def test_cosmetics_do_not_change_the_match():
    import robot_art
    out = []
    for look in (True, False):
        home, away = cosmetic_cfgs(look)
        random.seed(13)
        g.start_robot_match(home, away, lambda s, e: None)
        assert bool(g.trail_players) == look
        n = 0
        while g.state != "over":
            g.step(1 / 60)
            n += 1
            if n % 40 == 0:
                g.draw()                       # desenho (rastro/comemoracao) no meio: nao pode influir
        out.append((list(g.score), [(e["team"], e["min"], e["name"]) for e in g.events]))
        g.match_sink = None
    assert out[0] == out[1], out
    assert robot_art.TRAIL_N == 6
    g.state = "menu"


def test_cosmetics_sprites_trail_and_celebration():
    import robot_art
    old = soccer.time
    clock = soccer.time = FakeTime()
    real = pygame.Surface
    try:
        home, away = cosmetic_cfgs(True)
        random.seed(2)
        g.start_robot_match(home, away, lambda s, e: None)
        g.state = "play"
        players = [p for t in g.teams for p in t.players]
        assert len(g.trail_players) == 10
        for p in players:                                   # adesivo/antena no atlas; rastro pronto no cache
            lk = p.vis["look"]
            assert p.art.atlas.key[4] == (lk["decal"], lk["antenna"])
            assert p.art.trail is g.sprites[("trail", lk["trail"])] and len(p.art.trail) == robot_art.TRAIL_N
        # todos correndo: rastro enche ate TRAIL_N; zero Surface por quadro depois do warm
        for k, p in enumerate(players):
            p.vel = soccer.V(300, 0) if k % 2 else soccer.V(0, -300)
        for _ in range(5):
            clock.t += 1 / 60
            g.draw()
        count = [0]

        class Counting(real):
            def __init__(self, *a, **kw):
                count[0] += 1
                super().__init__(*a, **kw)

        pygame.Surface = Counting
        st = random.getstate()
        for _ in range(60):
            clock.t += 1 / 60
            for k, p in enumerate(players):
                p.pos += p.vel / 60.0
            g.draw()
        pygame.Surface = real
        assert count[0] == 0, count[0]
        assert random.getstate() == st
        assert all(p.trail_n == robot_art.TRAIL_N for p in players)
        g.world_dirty.clear()
        g.world_mark()
        assert len(g.world_dirty) >= 10 * robot_art.TRAIL_N
        # pausa: congela; MAX: nao amostra nem desenha
        snap = [(p.trail_n, p.trail_h) for p in players]
        g.paused = True
        for _ in range(20):
            clock.t += 1 / 60
            g.draw()
        assert snap == [(p.trail_n, p.trail_h) for p in players]
        g.paused = False
        g.speed_idx = 3
        for _ in range(20):
            clock.t += 1 / 60
            g.draw()
        assert snap == [(p.trail_n, p.trail_h) for p in players]
        g.speed_idx = 0
        # parados: o rastro some aos poucos
        for p in players:
            p.vel = soccer.V()
        for _ in range(40):
            clock.t += 1 / 60
            g.draw()
        assert all(p.trail_n == 0 for p in players)
        # comemoracao do autor do gol: so particulas no fx_rng (random global intacto); gol contra nao
        scorer = g.teams[0].players[4]
        cel = scorer.vis["look"]["celebration"]
        g.fx.clear()
        g.last_owner = scorer
        st = random.getstate()
        g.goal(0)
        assert random.getstate() == st
        n_goal = soccer.FX_KINDS["goal"][0]
        n_cel = sum(1 for p in g.fx if p[6] in robot_art.CELEBRATION_COLORS[cel])
        assert len(g.fx) > n_goal and n_cel > 0, (len(g.fx), n_cel)
        g.fx.clear()
        g.state = "play"
        g.last_owner = g.teams[1].players[4]              # gol do time 0 com o ultimo toque do rival
        g.goal(0)
        assert len(g.fx) == n_goal
        g.fx.clear()
        g.speed_idx = 3                                     # MAX: nenhuma particula
        g.state = "play"
        g.last_owner = scorer
        g.goal(0)
        assert g.fx == []
        g.speed_idx = 0
        # icones da galeria e sprite da UI com o visual: prontos e cacheados
        for cid in sorted(__import__("parts").COSMETICS):
            ic = robot_art.cosmetic_icon(g.sprites, cid)
            assert ic.get_size() == (robot_art.ICON_SIZE,) * 2 and ic.get_bounding_rect().w > 0
            assert robot_art.cosmetic_icon(g.sprites, cid) is ic
        rb = {"chassis": "Disco", "paint": (0, 200, 255), "role": "MID", "look": {"decal": "raio"}}
        plain = dict(rb, look={})
        assert g.robot_sprite(rb) is g.robot_sprite(rb) and g.robot_sprite(rb) is not g.robot_sprite(plain)
        g.match_sink = None
    finally:
        pygame.Surface = real
        soccer.time = old
        g.paused = False
        g.speed_idx = 0
        g.state = "menu"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok", t.__name__)
    print(len(tests), "testes passaram")
