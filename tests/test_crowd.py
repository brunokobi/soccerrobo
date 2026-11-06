"""Testes da torcida (game/crowd.py + hooks/UI em soccer.py; Fase 4, passos A1-A7). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_crowd.py [teste ...]

NUNCA toca ~/.soccerpy_*.json: prefs/campaign/garage/career usam stores em memoria (trocados ANTES de
criar o Game) e store.write e uma sentinela que FALHA se chamada. Screenshots so se SOCCERPY_SHOTS_DIR
estiver definido.
"""
import os
import random
import sys
import time

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

FORBIDDEN = []


def _forbid(name):
    def f(*a, **k):
        FORBIDDEN.append(name)
        raise AssertionError("%s chamada pelos testes da torcida" % name)
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

import crowd  # noqa: E402
import soccer  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)
SHOTS_DIR = os.environ.get("SOCCERPY_SHOTS_DIR")
LEVELS = ("ALTA", "MEDIA")


def set_level(level, camera="PERTO"):
    """Nivel da torcida + camera EXPLICITA: os testes deste arquivo conferem a geometria PERTO (campo em
    tela cheia); a camera ESTADIO (padrao AUTO das partidas assistidas) fica em tests/test_camera.py."""
    PREFS["raw"] = '{"v": 1, "crowd": "%s", "camera": "%s"}' % (level, camera)
    prefs.reset_cache()


def cfg(name, color, ovr=65):
    return {"name": name, "color": color, "squad": [("J%d" % i, ovr) for i in range(5)]}


def start(venue="arena", level="ALTA", seed=0):
    set_level(level)
    random.seed(seed)
    g.start_career_match(cfg("CASA", (50, 120, 255)), cfg("FORA", (235, 65, 65)), venue=venue)
    return g.crowd


class Clock:
    def __init__(self, t=100.0):
        self.t = t

    def __call__(self):
        return self.t


class SurfaceCounter:
    """Troca pygame.Surface por uma subclasse que conta construcoes (helper de zero Surface)."""

    def __enter__(self):
        self.real = pygame.Surface
        count = self.count = [0]
        real = self.real

        class Counting(real):
            def __init__(self, *a, **k):
                count[0] += 1
                super().__init__(*a, **k)

        pygame.Surface = Counting
        return self

    def __exit__(self, *a):
        pygame.Surface = self.real

    @property
    def n(self):
        return self.count[0]


# --- A1: locais, atomo, segmentos, atlas -----------------------------------------------------------
def test_venues_from_spec():
    # contagens da spec 2.5 revistas na correcao de visibilidade: os locais pequenos subiram (bairro 30 -> 85,
    # quadra 30 -> 110, ginasio 90 -> 140, dojo/aeroporto 40 -> 90) porque agora ocupam as laterais visiveis
    # (antes so a frente, quase toda atras do rodape). Hierarquia mantida.
    spec = {"bairro": 85, "quadra": 110, "ginasio": 140, "arena": 220, "estadio": 360, "superliga": 360,
            "mundial": 520, "coliseu": 520, "laboratorio": 100, "fabrica": 100, "dojo": 90, "aeroporto": 90}
    assert set(crowd.VENUES) == set(spec)
    for v, n in spec.items():
        assert crowd.people_count(v, "ALTA") == n, (v, crowd.people_count(v, "ALTA"))
        assert crowd.people_count(v, "MEDIA") < n
        assert crowd.VENUES[v]["style"] in crowd.STYLES
        assert crowd.VENUES[v]["sides"] == "LR", v           # todo local tem as duas laterais (visiveis)
    pc = crowd.people_count
    assert pc("bairro") < min(pc("quadra"), pc("ginasio")) <= max(pc("quadra"), pc("ginasio")) < pc("arena")
    assert pc("arena") < pc("estadio") < pc("mundial") == pc("coliseu")
    assert crowd.resolve_venue(None) == crowd.DEFAULT_VENUE == "arena"
    assert crowd.resolve_venue("nao-existe") == crowd.DEFAULT_VENUE


def test_atom_poses_differ():
    look = (crowd.SKINS[0], crowd.HAIRS[0], (50, 120, 255), (50, 120, 255))
    imgs = []
    for back in (False, True):
        for pose in crowd.POSES:
            s = pygame.Surface((crowd.AW, crowd.AH), pygame.SRCALPHA)
            crowd.draw_person(s, 0, 0, look, pose, back)
            imgs.append(pygame.image.tobytes(s, "RGBA"))
    assert len(set(imgs)) == len(imgs)            # cada pose/vista desenha algo diferente
    s = pygame.Surface((crowd.AW, crowd.AH), pygame.SRCALPHA)
    crowd.draw_robot_fan(s, 0, 0, ((120, 130, 146), (50, 120, 255), None), crowd.UP, False)
    assert pygame.image.tobytes(s, "RGBA") != bytes(crowd.AW * crowd.AH * 4)


def _seg_rects(b):
    for s in b.segs:
        w, h = s.imgs[0].get_size()
        for dx, dy in ((0, 0), s.jump):
            yield s, pygame.Rect(s.x + dx, s.y + dy, w, h)


def test_layout_free_space_only():
    hud = pygame.Rect(0, 0, soccer.W, 88)
    nets = [pygame.Rect(soccer.PITCH.left - soccer.GOAL_DEPTH, soccer.CY - soccer.GOAL_HALF, soccer.GOAL_DEPTH,
                        soccer.GOAL_HALF * 2),
            pygame.Rect(soccer.PITCH.right, soccer.CY - soccer.GOAL_HALF, soccer.GOAL_DEPTH, soccer.GOAL_HALF * 2)]
    screen_r = pygame.Rect(0, 0, soccer.W, soccer.H)
    for v in crowd.VENUES:
        b = crowd.warm_crowd(v, (50, 120, 255), (235, 65, 65), "ALTA", base=g.pitch_surf)
        assert b.segs, v
        for s, r in _seg_rects(b):
            assert not r.colliderect(soccer.PITCH), (v, s.zone, r)
            assert not r.colliderect(hud), (v, s.zone, r)
            assert not any(r.colliderect(n) for n in nets), (v, s.zone, r)
            assert screen_r.contains(r.clip(screen_r)) and r.clip(screen_r).w > 0, (v, r)
        fids = {s.fid for s in b.segs}
        assert "home" in fids and "away" in fids, (v, fids)
        for s in b.segs:                          # casa na esquerda, visitante na direita
            if s.fid == "home":
                assert s.cx < soccer.CX, (v, s.cx)
            elif s.fid == "away":
                assert s.cx > soccer.CX, (v, s.cx)


def test_static_arena_and_memory():
    for v in crowd.VENUES:
        b = crowd.warm_crowd(v, (50, 120, 255), (235, 65, 65), "ALTA", base=g.pitch_surf)
        assert b.static.get_size() == (soccer.W, soccer.H)
        assert crowd.stands_static(v, (50, 120, 255), (235, 65, 65), base=g.pitch_surf) is b.static
        assert b.nbytes <= 4 * 1024 * 1024, (v, b.nbytes)
        # o campo continua igual ao pitch_surf (a estrutura so ocupa as margens)
        inner = soccer.PITCH.inflate(-24, -24)
        for p in ((inner.left, inner.top), inner.center, (inner.right - 1, inner.bottom - 1)):
            assert b.static.get_at(p) == g.pitch_surf.get_at(p), (v, p)
        assert b.tarja.get_size() == (soccer.W, soccer.H - crowd.TARJA_Y)


def test_warm_time_budget():
    worst = 0.0
    for v in crowd.VENUES:
        crowd.clear_cache()
        t = time.perf_counter()
        crowd.warm_crowd(v, (50, 120, 255), (235, 65, 65), "ALTA", base=g.pitch_surf)
        ms = (time.perf_counter() - t) * 1000
        worst = max(worst, ms)
        assert ms <= 200, (v, ms)                 # limite duro folgado (meta da spec: 60 ms)
    print("   warm_crowd: pior local %.1f ms (meta <= 60 ms)%s" % (worst, "" if worst <= 60 else "  [ACIMA DA META]"))


def test_lru_cache_of_3():
    crowd.clear_cache()
    keys = [((50, 120, 255), (235, 65, 65)), ((255, 255, 255), (0, 0, 0)), ((10, 200, 10), (200, 10, 200)),
            ((240, 200, 40), (40, 40, 240))]
    first = crowd.warm_crowd("arena", *keys[0], base=g.pitch_surf)
    n0 = crowd.STATS["builds"]
    with SurfaceCounter() as c:                   # mesma chave: nada e reconstruido
        again = crowd.warm_crowd("arena", *keys[0], base=g.pitch_surf)
    assert again is first and c.n == 0 and crowd.STATS["builds"] == n0
    for k in keys[1:]:
        crowd.warm_crowd("arena", *k, base=g.pitch_surf)
    assert len(crowd._CACHE) == crowd.CACHE_MAX == 3
    assert ("arena", keys[0][0], keys[0][1], "ALTA") not in crowd._CACHE      # a 1a chave saiu
    assert crowd.warm_crowd("arena", *keys[0], base=g.pitch_surf) is not first
    assert crowd.STATS["builds"] == n0 + 4


def test_build_does_not_touch_global_rng():
    crowd.clear_cache()
    st = random.getstate()
    for v in ("bairro", "mundial", "fabrica"):
        crowd.warm_crowd(v, (50, 120, 255), (235, 65, 65), "MEDIA", base=g.pitch_surf)
    assert random.getstate() == st


# --- A2: arena composta na partida, menu intacto ---------------------------------------------------
def test_match_uses_composite_and_menu_intact():
    menu_bg = g.menu_bg
    cr = start("estadio")
    assert cr is not None and g.crowd is cr and cr.b.venue == "estadio"
    g.state = "play"
    g.draw()
    p = (5, 85)                                    # canto (refletor): fora do HUD e das faixas
    assert cr.b.static.get_at(p) != g.pitch_surf.get_at(p)
    assert screen.get_at(p) == cr.b.static.get_at(p)          # a partida desenha a arena composta
    g.state = "menu"
    f = cr.frame
    g.draw()
    assert cr.frame == f and g.menu_bg is menu_bg
    assert screen.get_at((5, 5)) == menu_bg.get_at((5, 5))
    g.new_match(1)                                 # amistoso: sem torcida
    assert g.crowd is None


def test_default_venue_and_param():
    assert start(None).b.venue == crowd.DEFAULT_VENUE
    assert start("mundial").b.venue == "mundial"
    set_level("ALTA")
    called = []
    g.start_robot_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), lambda s, e: called.append(s),
                        venue="bairro")
    assert g.crowd.b.venue == "bairro" and g.match_sink is not None
    g.start_robot_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), lambda s, e: None)
    assert g.crowd.b.venue == crowd.DEFAULT_VENUE
    g.match_sink = None


def test_ui_drawn_over_crowd():
    """Botoes de velocidade e placar ficam por cima da torcida (mesmos pixels com e sem torcida)."""
    pts = [r.center for r in g.speed_rects()] + [(r.left + 3, r.centery) for r in g.speed_rects()]
    shots = {}
    for level in ("OFF", "ALTA"):
        start("mundial", level)
        g.state = "play"
        g.ball.pos = soccer.V(soccer.CX, soccer.CY)
        g.draw()
        shots[level] = [screen.get_at(p) for p in pts]
    assert shots["OFF"] == shots["ALTA"]


# --- zero Surface por quadro --------------------------------------------------------------------
def test_zero_surface_300_frames_every_venue_and_level():
    for level in LEVELS:
        for v in crowd.VENUES:
            cr = start(v, level, seed=3)
            for _ in range(3):                    # aquecimento (texto do HUD)
                g.step(1 / 60)
                g.draw()
            with SurfaceCounter() as c:
                for n in range(300):
                    g.step(1 / 60)
                    if n == 40:
                        g.crowd_event("goal", 0)
                    elif n == 150:
                        g.crowd_event("save", 1)
                    elif n == 200:
                        g.crowd_event("end", 1)
                    g.draw()
            assert c.n == 0, (v, level, c.n)
            assert cr.frame >= 300


# --- A3: reacoes ---------------------------------------------------------------------------------
def _crowd(venue="arena", level="ALTA", t=100.0, seed=7):
    b = crowd.warm_crowd(venue, (50, 120, 255), (235, 65, 65), level, base=g.pitch_surf)
    clk = Clock(t)
    return crowd.Crowd(b, clock=clk, seed=seed), clk


def _at_frame(cr, clk, t0, frame):
    clk.t = t0 + frame / 60.0
    cr.update()
    return cr.fid_pose("home"), cr.fid_pose("away")


def test_chant_in_quiet_moments_with_sound():
    cr, clk = _crowd("estadio")
    t0 = clk.t
    chants, poses = [], set()
    for f in range(0, 60 * 45, 3):                     # 45 s sem lance
        clk.t = t0 + f / 60.0
        cr.update()
        r = cr.react.get("home") or cr.react.get("away")
        for fid in ("home", "away"):
            rr = cr.react.get(fid)
            if rr and rr[0] == "chant" and clk.t < rr[1] + rr[2]:
                poses.add(cr.fid_pose(fid))
        chants += [x for x in cr.pop_sounds() if x == "crowd_chant"]
    kinds = {f for f in ("home", "away") if cr.react.get(f) and cr.react[f][0] == "chant"}
    assert chants, "a torcida nunca puxou o coro"
    assert kinds == {"home", "away"}                   # as duas torcidas se revezam
    assert crowd.UP in poses and (crowd.FLAG_A in poses or crowd.FLAG_B in poses), poses
    cr.event("goal", 0)                                # um lance interrompe o coro
    assert cr.react["home"][0] == "party"
    assert cr.pop_sounds() == []


def test_fans_have_variety():
    b = crowd.warm_crowd("mundial", (50, 120, 255), (235, 65, 65), "ALTA", base=g.pitch_surf)
    rng = random.Random(3)
    v = crowd.VENUES["mundial"]
    seats = crowd._seats(v)
    looks = crowd._looks(v, "mundial", seats, list(range(len(seats))), (50, 120, 255), (235, 65, 65), rng)
    people = [lk for kind, lk in looks.values() if kind == "pessoa"]
    assert len({p[0] for p in people}) >= 5            # tons de pele
    assert len({p[1] for p in people}) >= 10           # cabelos/chapeus/bones
    assert {p[4] for p in people} >= {None, "listra", "cachecol", "oculos"}
    for acc in crowd.ACCS:                             # todos desenham sem erro, nas 5 poses, frente e costas
        for pose in crowd.POSES:
            for back in (False, True):
                srf = pygame.Surface((crowd.AW, crowd.AH), pygame.SRCALPHA)
                crowd.draw_person(srf, 0, 0, ((200, 150, 110), ("chapeu", (210, 190, 120)), (50, 120, 255),
                                              None, acc), pose, back)
    big = [f for f in b.flags if f[0][0].get_width() > 22]
    assert big and len(b.flags) >= 6                   # bandeiroes no meio das bandeiras


def test_goal_poses_by_fidelity_frames():
    for team, mine, other in ((0, "home", "away"), (1, "away", "home")):
        cr, clk = _crowd()
        cr.waves = False                           # sem calmaria/ola: so a reacao do gol
        t0 = clk.t
        cr.event("goal", team)
        poses = {}
        for f in (0, 30, 90, 200, 300, 480):
            h, a = _at_frame(cr, clk, t0, f)
            poses[f] = {"home": h, "away": a}
        assert poses[30][mine] == crowd.UP and poses[90][mine] == crowd.UP, poses
        assert poses[200][mine] == crowd.UP, poses                          # ainda pulando (festa)
        assert poses[300][mine] in (crowd.FLAG_A, crowd.FLAG_B), poses      # depois agita as bandeiras
        assert poses[0][other] == crowd.SAD and poses[90][other] == crowd.SAD, poses
        assert poses[200][other] == crowd.SIT, poses
        assert poses[480][mine] == crowd.SIT and poses[480][other] == crowd.SIT, poses
        # pulo: a torcida que marcou sobe (deslocamento) em algum quadro da comemoracao
        jumped = False
        for f in range(10, 120, 3):
            clk.t = t0 + f / 60.0
            cr.update()
            jumped = jumped or any(o != (0, 0) for s, o in zip(cr.segs, cr.offs) if s.fid == mine)
            assert all(o == (0, 0) for s, o in zip(cr.segs, cr.offs) if s.fid == other)
        assert jumped


def test_goal_wave_starts_at_the_goal():
    cr, clk = _crowd("mundial")
    cr.waves = False
    t0 = clk.t
    cr.event("goal", 0)                            # casa marca no gol da direita: onda vem da direita
    clk.t = t0 + 0.33                              # x > 400 ja levantou (~0,29 s); x < 100 ainda nao (>= 0,42 s)
    cr.update()
    home = [(s.cx, p) for s, p in zip(cr.segs, cr.poses) if s.fid == "home"]
    near = [p for x, p in home if x > 400]
    far = [p for x, p in home if x < 100]
    assert crowd.UP in near and all(p == crowd.SIT for p in far), (near, far)


def test_other_events():
    cr, clk = _crowd()
    cr.waves = False
    t0 = clk.t
    cr.event("save", 1)                            # visitante defendeu: visitante comemora, casa lamenta
    assert _at_frame(cr, clk, t0, 10) == (crowd.SAD, crowd.UP)
    assert _at_frame(cr, clk, t0, 80) == (crowd.SIT, crowd.SIT)
    t0 = clk.t
    cr.event("chance", 0)
    assert _at_frame(cr, clk, t0, 5)[0] == crowd.UP
    t0 = clk.t + 2
    clk.t = t0
    cr.event("kickoff")
    assert _at_frame(cr, clk, t0, 2)[0] in (crowd.FLAG_A, crowd.FLAG_B)
    t0 = clk.t + 3
    clk.t = t0
    cr.event("post")
    assert _at_frame(cr, clk, t0, 6) == (crowd.UP, crowd.UP)
    t0 = clk.t + 3
    clk.t = t0
    cr.event("end", 0)                             # vitoria da casa: casa pula, visitante lamenta
    assert _at_frame(cr, clk, t0, 60) == (crowd.UP, crowd.SAD)
    # um lance menor nao interrompe a comemoracao de gol
    t0 = clk.t + 20
    clk.t = t0
    cr.event("goal", 1)
    cr.event("chance", 0)
    assert _at_frame(cr, clk, t0, 30) == (crowd.SAD, crowd.UP)
    n = cr.n_events
    cr.event("nao-existe")
    assert cr.n_events == n + 1 and _at_frame(cr, clk, t0, 31) == (crowd.SAD, crowd.UP)


def test_ola_and_calm():
    cr, clk = _crowd("arena", "ALTA")
    t0 = clk.t
    seen_up = 0
    for f in range(0, 60 * 30, 3):                 # 30 s sem lances: calmaria e depois a ola
        clk.t = t0 + f / 60.0
        cr.update()
        seen_up = max(seen_up, sum(1 for p in cr.poses if p == crowd.UP))
    assert cr.last_ola > t0                        # a ola saiu (~25 s de calmaria)
    assert seen_up >= 4                            # a ola levanta varias faixas ao mesmo tempo
    # MEDIA: sem ondas (nem ola nem calmaria) -> todos sentados sem lances
    cr, clk = _crowd("arena", "MEDIA")
    t0 = clk.t
    for f in range(0, 60 * 30, 6):
        clk.t = t0 + f / 60.0
        cr.update()
        assert all(p == crowd.SIT for p in cr.poses)
    # local sem ola (bairro): so calmaria
    cr, clk = _crowd("bairro", "ALTA")
    for f in range(0, 60 * 30, 3):
        clk.t = 100 + f / 60.0
        cr.update()
    assert cr.last_ola == 100.0


def test_determinism_with_injected_clock():
    runs = []
    for _ in range(2):
        cr, clk = _crowd("mundial", seed=11)
        trace = []
        for f in range(0, 60 * 40, 3):
            clk.t = 100 + f / 60.0
            if f == 300:
                cr.event("goal", 0)
            elif f == 900:
                cr.event("save", 0)
            elif f == 2000:
                cr.event("end", None)
            cr.update()
            trace.append((tuple(cr.poses), tuple(cr.offs)))
        runs.append(trace)
    assert runs[0] == runs[1]
    assert len({t[0] for t in runs[0]}) > 10       # e a torcida realmente mudou de pose


def test_update_every_n_frames():
    for level, every in (("ALTA", 3), ("MEDIA", 6)):
        cr, clk = _crowd("arena", level)
        calls = []
        orig = cr.update
        cr.update = lambda now=None: calls.append(1) or orig(now)
        for _ in range(60):
            cr.draw(screen)
        assert len(calls) == 60 // every, (level, len(calls))
        n = len(calls)
        for _ in range(30):
            cr.draw(screen, paused=True)           # pausado: congela (nao recalcula)
        assert len(calls) == n


def test_global_rng_untouched_by_draw_and_events():
    start("mundial", "ALTA", seed=5)
    g.state = "play"
    st = random.getstate()
    for k in range(200):
        if k % 20 == 0:
            g.crowd_event(("goal", "chance", "save", "post", "kickoff", "end")[k // 20 % 6], k % 2)
        g.draw()
    g.crowd.update()
    assert random.getstate() == st


def test_simulation_identical_with_crowd_on_off():
    for seed in range(20):
        res = []
        for level in ("OFF", "ALTA"):
            set_level(level)
            random.seed(seed)
            g.start_career_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), venue="mundial")
            assert (g.crowd is None) == (level == "OFF")
            while g.state != "over":
                g.step(1 / 60)
            res.append((list(g.score), [dict(e) for e in g.events], random.random()))
        assert res[0] == res[1], (seed, res)


def test_hooks_fire_during_match():
    kinds = []
    for seed in range(4):
        cr = start("arena", "ALTA", seed=seed)
        orig = cr.event
        cr.event = lambda kind, team=None, x=None, o=orig: kinds.append(kind) or o(kind, team, x)
        while g.state != "over":
            g.step(1 / 60)
    for k in ("kickoff", "goal", "chance", "save", "end"):
        assert k in kinds, (k, sorted(set(kinds)))


def test_max_and_off_do_not_draw_crowd():
    cr = start("mundial", "ALTA")
    g.state = "play"
    g.speed_idx = 3
    n = cr.n_events
    g.crowd_event("goal", 0)                       # hooks sao no-op em MAX
    assert cr.n_events == n
    f = cr.frame
    g.ball.pos = soccer.V(soccer.CX, soccer.CY)
    g.draw()
    assert cr.frame == f
    seg = [s for s in cr.segs if s.zone == "F" and 150 < s.x < 500][-1]     # fora dos textos/botoes
    p = (seg.x + 4, seg.y + 8)
    assert screen.get_at(p) == cr.b.static.get_at(p)     # so a arena composta (sem faixas nem tarja)
    g.speed_idx = 0
    with SurfaceCounter() as c:                    # no MAX tambem nenhuma Surface por quadro
        g.speed_idx = 3
        for _ in range(30):
            g.update(1 / 60)
            g.draw()
    g.speed_idx = 0
    assert c.n == 0
    cr = start("mundial", "OFF")                   # OFF: nem torcida nem arena composta
    assert cr is None and g.crowd is None
    g.state = "play"
    g.draw()
    for p in ((5, 680), (20, 200), (1090, 500)):
        assert screen.get_at(p) == g.pitch_surf.get_at(p)


def test_draw_ms_budget_full_crowd():
    crowd.clear_cache()
    cr = start("mundial", "ALTA")
    g.state = "play"
    g.crowd_event("goal", 0)
    for _ in range(10):
        g.draw()
    n = 300
    t = time.perf_counter()
    for _ in range(n):
        g.draw()
    ms = (time.perf_counter() - t) / n * 1000
    set_level("OFF")
    start("mundial", "OFF")
    g.state = "play"
    t = time.perf_counter()
    for _ in range(n):
        g.draw()
    ms_off = (time.perf_counter() - t) / n * 1000
    print("   draw_ms mundial ALTA %.3f ms (sem torcida %.3f; meta <= 1,5 ms)" % (ms, ms_off))
    assert cr.b.people == 520
    assert ms <= 6.0, ms                           # duro folgado


def test_latin1_source():
    with open(os.path.join(ROOT, "game", "crowd.py"), encoding="utf-8") as f:
        f.read().encode("latin-1")


# --- A4-A7: extras, LED, onomatopeias, telao, LOD e opcao TORCIDA -------------------------------
def start_clk(venue="mundial", level="ALTA", seed=0):
    """Partida assistida com relogio injetado (1/60 s por quadro em frames())."""
    clk = Clock(500.0)
    g.crowd_clock = clk
    try:
        cr = start(venue, level, seed)
    finally:
        g.crowd_clock = None
    return cr, clk


def frames(clk, n, events=None, step=True):
    for k in range(n):
        clk.t += 1 / 60
        if step:
            g.step(1 / 60)
        if events and k in events:
            ev = events[k]
            g.crowd_event(*ev) if ev[0] != "kickoff" else g.crowd.event("kickoff")
        g.draw()


ALL_EVENTS = {5: ("goal", 0), 60: ("chance", 1), 90: ("save", 0), 120: ("post",), 150: ("goal", 1),
              200: ("kickoff",), 240: ("end", 0)}


def test_extras_zero_surface_every_venue_level_and_lod():
    for level in LEVELS:
        for v in crowd.VENUES:
            cr, clk = start_clk(v, level, seed=2)
            g.state = "play"
            frames(clk, 3, step=False)                    # aquecimento (texto do HUD)
            seen = {"confetti": 0, "flashes": 0, "smoke": 0, "onos": 0}
            with SurfaceCounter() as c:
                for lod in (2, 1, 0, 2):
                    cr.set_lod(lod)
                    for k in range(300):
                        clk.t += 1 / 60
                        if k in ALL_EVENTS:
                            ev = ALL_EVENTS[k]
                            cr.event(*ev) if ev[0] == "kickoff" else g.crowd_event(*ev)
                        g.paused = 100 <= k < 110            # pausado: congela, sem Surface tambem
                        g.draw()
                        for key in seen:
                            seen[key] = max(seen[key], len(getattr(cr, key)))
                g.paused = False
            assert c.n == 0, (v, level, c.n)
            ex = crowd.EXTRAS[v]
            assert seen["onos"] > 0, v
            assert (seen["confetti"] > 0) == ex["confetti"], (v, level, seen)
            assert (seen["flashes"] > 0) == ex["flashes"], (v, level, seen)
            assert (seen["smoke"] > 0) == (ex["flares"] and level == "ALTA"), (v, level, seen)
            assert len(cr.b.banners[True]) == len(cr.b.banners[False]) == 2, v      # uma faixa por lateral
            assert (cr.b.led_ads is not None) == crowd.STYLES[crowd.VENUES[v]["style"]]["board"], v


def test_particle_caps_and_decay():
    for level in LEVELS:
        cr, clk = start_clk("mundial", level)
        g.state = "play"
        peak = {"confetti": 0, "flashes": 0, "smoke": 0, "onos": 0}
        for k in range(900):                          # gols sem parar: o teto segura tudo
            clk.t += 1 / 60
            if k % 15 == 0:
                cr.event("goal", k // 15 % 2)
                cr.event("end", k // 15 % 2)
            cr.draw(screen)
            cr.draw_over(screen)
            for key in peak:
                peak[key] = max(peak[key], len(getattr(cr, key)))
        assert peak["confetti"] <= crowd.CONFETTI_MAX[level] and peak["confetti"] > 0, peak
        assert peak["flashes"] <= crowd.FLASH_MAX[level], peak
        assert peak["smoke"] <= crowd.SMOKE_MAX[level], peak
        assert peak["onos"] <= crowd.ONO_MAX, peak
        if level == "MEDIA":
            assert crowd.CONFETTI_MAX["MEDIA"] < crowd.CONFETTI_MAX["ALTA"]
            assert len(cr.b.flags) < len(crowd.warm_crowd("mundial", *cr.b.key[1:3], "ALTA",
                                                          base=g.pitch_surf).flags)
        for _ in range(60 * 10):                      # 10 s sem lances: tudo decai por tempo real
            clk.t += 1 / 60
            cr.draw(screen)
            cr.draw_over(screen)
        # flashes: so os raros da calmaria (0,6/s, vida <= 0,14 s) podem estar acesos; nada sobra dos gols
        assert not cr.confetti and not cr.smoke and not cr.onos
        assert all(f[2] - clk.t <= 0.15 for f in cr.flashes), (clk.t, cr.flashes)


def _hud_key(k):
    s = k[0]
    return s.endswith("'") and s[:-1].isdigit() or "  x  " in s


def test_text_cache_keys_stable_after_warmup():
    crowd_strings = crowd.all_strings()
    for v in ("mundial", "fabrica", "bairro"):
        cr, clk = start_clk(v, "ALTA")
        frames(clk, 5)
        before = set(g.text_cache)
        assert ("TONHO:", crowd.TELAO_SIZE, crowd.SPEAKERS[0][1]) in before    # telao pre-buscado
        called = []
        orig = g.text_img
        g.text_img = lambda s, size, color: called.append(s) or orig(s, size, color)
        try:
            for rep in range(2):
                frames(clk, 300, {k + rep: e for k, e in ALL_EVENTS.items()})
        finally:
            del g.text_img
        assert not [s for s in called if s in crowd_strings], v     # nada de texto da torcida por quadro
        new = set(g.text_cache) - before
        assert all(_hud_key(k) for k in new), (v, [k for k in new if not _hud_key(k)])


def test_telao_only_in_assisted_matches_and_modes_keep_hints():
    hints = {1: "WASD / Setas: mover   |   ESPAÇO (segure): chutar   |   SHIFT / X: passar   |   P: pausa",
             2: "J1: WASD + ESPAÇO chuta + SHIFT passa   |   J2: Setas + ENTER chuta + SHIFT DIR passa"}
    set_level("ALTA")
    for mode in (1, 2):
        g.new_match(mode)
        g.text_cache.clear()
        g.state = "play"
        for _ in range(5):
            g.draw()
        assert g.crowd is None
        assert (hints[mode], 24, (190, 225, 235)) in g.text_cache, mode
        assert not [k for k in g.text_cache if k[0] in crowd.all_strings()], mode
        p = crowd.TELAO.move(30, 4).topleft
        assert screen.get_at(p) != (4, 8, 16, 255)
    cr, clk = start_clk("arena")
    assert cr.telao_on and cr.cap is not None and cr.cap[0] == "kickoff"
    g.state = "play"
    frames(clk, 2)
    assert screen.get_at((crowd.TELAO.left + 1, crowd.TELAO.centery)) == cr.b.telao.get_at((1, crowd.TELAO.h // 2))
    g.text_cache.clear()
    frames(clk, 3)
    assert not any(k[0] == hints[1] for k in g.text_cache)
    set_level("ALTA")
    g.start_robot_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), lambda s, e: None, venue="bairro")
    assert g.crowd.telao_on
    g.match_sink = None
    # o telao nao cobre "P: pausa", "Velocidade (1-4):" nem os botoes
    lab = g.font(24).size("Velocidade (1-4):")
    vel = pygame.Rect(0, 0, *lab)
    vel.midright = (soccer.W - 342, soccer.H - 22)
    pau = pygame.Rect(0, 0, *g.font(24).size("P: pausa"))
    pau.midleft = (24, soccer.H - 22)
    for r in g.speed_rects() + [vel, pau]:
        assert not crowd.TELAO.colliderect(r), r
    # legendas cabem no telao
    for kind, variants in crowd.CAPTIONS.items():
        for pair in variants:
            for (name, _), line in zip(crowd.SPEAKERS, pair):
                w = g.font(crowd.TELAO_SIZE).size(name)[0] + 6 + g.font(crowd.TELAO_SIZE).size(line)[0]
                assert 22 + w <= crowd.TELAO.w - 6, (kind, line, w)


def test_led_scrolls_and_shows_goal():
    cr, clk = start_clk("estadio")
    g.state = "play"
    led = pygame.Rect(crowd.LED_X, crowd.LED_Y, crowd.LED_W, crowd.LED_H)
    frames(clk, 1, step=False)
    a = pygame.image.tobytes(screen.subsurface(led).copy(), "RGB")
    frames(clk, 30, step=False)
    b = pygame.image.tobytes(screen.subsurface(led).copy(), "RGB")
    assert a != b                                       # rolou
    cr.event("goal", 0)
    frames(clk, 1, step=False)
    assert cr.led_goal is not None and cr.led_goal[0] == "home"
    for s in crowd.LED_ADS + tuple(crowd.LED_HEAD.values()):
        s.encode("ascii")                               # placa de LED: sem acentos (estilo LED)
    for s in crowd.all_strings():
        s.encode("latin-1")


def test_mosaic_on_kickoff_and_win():
    cr, clk = start_clk("estadio")
    assert cr.has_mosaic and cr.n_kick == 1
    clk.t += 0.5
    cr.update()
    assert cr.fid_pose("home") == crowd.MOSAIC and cr.fid_pose("away") == crowd.MOSAIC
    clk.t += 4
    cr.update()
    assert cr.fid_pose("home") != crowd.MOSAIC
    t0 = clk.t
    cr.event("end", 1)
    clk.t = t0 + 1.0
    cr.update()
    assert cr.fid_pose("away") == crowd.UP
    clk.t = t0 + 4.0
    cr.update()
    assert cr.fid_pose("away") == crowd.MOSAIC and cr.fid_pose("home") == crowd.SAD
    cr2, _ = start_clk("arena")                         # arena: sem mosaico, kickoff = bandeiras
    assert not cr2.has_mosaic


def test_lod_reduces_and_recovers():
    cr, clk = start_clk("mundial")
    g.state = "play"
    assert cr.lod == 2
    for _ in range(crowd.LOD_WINDOW):
        cr.lod_feed(crowd.LOD_DOWN_MS + 3)
    assert cr.lod == 1
    cr.event("goal", 0)
    assert not cr.confetti                              # LOD 1: sem confete nem fumaca
    for _ in range(crowd.LOD_WINDOW):
        cr.lod_feed(crowd.LOD_DOWN_MS + 3)
    assert cr.lod == 0
    poses = list(cr.poses)
    assert all(p == crowd.SIT for p in poses)
    cr.event("goal", 1)
    frames(clk, 30, step=False)
    assert cr.poses == poses and not cr.flashes        # LOD 0: congelada
    for _ in range(crowd.LOD_WINDOW * (crowd.LOD_UP_WINDOWS - 1)):
        cr.lod_feed(0.5)
    assert cr.lod == 0                                  # histerese: precisa de LOD_UP_WINDOWS janelas
    for _ in range(crowd.LOD_WINDOW):
        cr.lod_feed(0.5)
    assert cr.lod == 1
    for _ in range(crowd.LOD_WINDOW * crowd.LOD_UP_WINDOWS):
        cr.lod_feed(0.5)
    assert cr.lod == 2
    cr.event("goal", 0)
    assert cr.confetti                                  # voltou a ter confete
    # janela entre os limites: nao muda
    for _ in range(crowd.LOD_WINDOW * 5):
        cr.lod_feed((crowd.LOD_DOWN_MS + crowd.LOD_UP_MS) / 2)
    assert cr.lod == 2
    # integracao: Game.draw mede o quadro e alimenta o LOD (limite forcado para baixo)
    old = crowd.LOD_DOWN_MS
    crowd.LOD_DOWN_MS = -1.0
    try:
        frames(clk, crowd.LOD_WINDOW * 2, step=False)
    finally:
        crowd.LOD_DOWN_MS = old
    assert cr.lod == 0
    g.paused = True                                     # pausado ou em MAX: nao mede
    n = cr._lod_n
    frames(clk, 10, step=False)
    g.paused = False
    g.speed_idx = 3
    frames(clk, 10, step=False)
    g.speed_idx = 0
    assert cr._lod_n == n


def key(k):
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))


def test_key_t_menu_and_pause_change_prefs_and_effect():
    set_level("ALTA")
    g.state = "menu"
    btns = [r.copy() for r in g.menu_btns] + [g.continue_btn.copy(), g.robots_btn(), g.campaign_btn()]
    key(pygame.K_t)
    assert prefs.get("crowd") == "MEDIA" and '"MEDIA"' in PREFS["raw"]
    g.text_cache.clear()
    g.draw()
    assert ("F11: tela cheia  |  T: torcida MÉDIA", 22, (120, 160, 185)) in g.text_cache
    assert any(k[0].startswith("clique ou aperte") for k in g.text_cache)
    assert [r.copy() for r in g.menu_btns] + [g.continue_btn.copy(), g.robots_btn(), g.campaign_btn()] == btns
    w = g.font(22).size("F11: tela cheia  |  T: torcida DESLIGADA")[0]
    assert w < soccer.W - 40
    random.seed(0)
    g.start_career_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), venue="mundial")
    assert g.crowd.b.level == "MEDIA"                  # vale na proxima partida
    key(pygame.K_t)                                    # fora da pausa: T nao faz nada
    assert prefs.get("crowd") == "MEDIA"
    key(pygame.K_p)
    assert g.paused
    key(pygame.K_t)                                    # pausa: OFF na hora
    assert prefs.get("crowd") == "OFF" and g.crowd is None and '"OFF"' in PREFS["raw"]
    g.text_cache.clear()
    g.draw()
    assert ("T: torcida DESLIGADA", 28, (255, 230, 120)) in g.text_cache
    assert screen.get_at((5, 680)) == g.pitch_surf.get_at((5, 680))
    key(pygame.K_t)                                    # OFF -> ALTA: re-warm no evento, nao no desenho
    assert prefs.get("crowd") == "ALTA" and g.crowd is not None and g.crowd.b.level == "ALTA"
    assert g.crowd.b.venue == "mundial" and g.crowd.blits     # pausado, mas a torcida aparece
    with SurfaceCounter() as c:
        for _ in range(30):
            g.draw()
    assert c.n == 0
    assert ("T: torcida ALTA", 28, (255, 230, 120)) in g.text_cache
    key(pygame.K_p)
    assert not g.paused
    # amistoso: pausa sem a opcao (T nao muda nada)
    g.new_match(1)
    g.state = "play"
    g.paused = True
    key(pygame.K_t)
    assert prefs.get("crowd") == "ALTA"
    g.text_cache.clear()
    g.draw()
    assert not any(k[0].startswith("T: torcida") for k in g.text_cache)
    g.paused = False
    g.state = "menu"


def test_draw_ms_all_extras_mundial():
    crowd.clear_cache()
    cr, clk = start_clk("mundial", "ALTA")
    g.state = "play"
    cr.event("goal", 0)
    cr.event("end", 0)
    frames(clk, 10, step=False)
    n = 300
    t = time.perf_counter()
    for k in range(n):
        clk.t += 1 / 60
        if k % 60 == 0:
            cr.event("goal", k // 60 % 2)
        g.draw()
    ms = (time.perf_counter() - t) / n * 1000
    print("   draw_ms mundial ALTA com todos os extras %.3f ms (meta <= 1,5 ms; duro 6 ms)" % ms)
    assert ms <= 6.0, ms


# --- visibilidade (a torcida nao pode ficar escondida atras da UI) --------------------------------------
VIS_MIN = {"bairro": 40, "dojo": 40, "aeroporto": 40, "quadra": 60, "ginasio": 90, "laboratorio": 60,
           "fabrica": 60, "arena": 120, "estadio": 140, "superliga": 140, "mundial": 150, "coliseu": 150}
VIS_ORDER = ("bairro", "quadra", "ginasio", "arena", "estadio", "mundial")


def _text_rect(s, size, **pos):
    return g.text_img(s, size, (255, 255, 255)).get_rect(**pos)


def test_ui_rects_cover_the_drawn_ui():
    """crowd.ui_rects (usados por _pick e pelo teste de visibilidade) cobrem a UI que soccer.py desenha."""
    H, W = soccer.H, soccer.W
    assisted = [_text_rect("P: pausa", 24, midleft=(24, H - 22)),
                _text_rect("Velocidade (1-4):", 24, midright=(W - 342, H - 22)), crowd.TELAO] + g.speed_rects()
    union = crowd.ui_rects(True)
    for r in assisted:
        assert crowd.visible_frac(r, union) == 0.0, r
    hints = [_text_rect(h, 24, center=(W // 2, H - 22)) for h in (
        "WASD / Setas: mover   |   ESPAÇO (segure): chutar   |   SHIFT / X: passar   |   P: pausa",
        "J1: WASD + ESPAÇO chuta + SHIFT passa   |   J2: Setas + ENTER chuta + SHIFT DIR passa")]
    for r in hints:
        assert crowd.visible_frac(r, crowd.ui_rects(False)) == 0.0, r
    assert crowd.visible_frac(pygame.Rect(0, 0, W, 78), union) == 0.0              # placar (hud_panel)
    assert crowd.visible_frac(pygame.Rect(0, 600, 10, 10)) == 1.0
    assert abs(crowd.visible_frac(pygame.Rect(0, 652, 20, 20), (pygame.Rect(0, 662, 20, 10),
                                                                 pygame.Rect(0, 660, 20, 4))) - 0.4) < 1e-9


def _visible_people(cr, rects):
    """(visiveis, por zona, pixels) dos espectadores desenhados AGORA na tela: caixa >= 50% fora da UI e
    a maioria dos pixels opacos da faixa batendo com a tela (nada desenhado por cima)."""
    vis, by_zone, pixels = 0, {"L": 0, "R": 0, "F": 0}, 0
    for s, (img, (x, y)) in zip(cr.segs, cr.blits):
        key = img.get_colorkey()
        dx, dy = x - s.x, y - s.y
        for box in s.boxes:
            r = box.move(dx, dy)
            if crowd.visible_frac(r, rects) < 0.5:
                continue
            opaque = same = 0
            for py in range(r.top, r.bottom):
                for px in range(r.left, r.right):
                    if any(u.collidepoint(px, py) for u in rects):
                        continue
                    c = img.get_at((px - x, py - y))
                    if key is not None and c == key:
                        continue
                    opaque += 1
                    same += screen.get_at((px, py)) == c
            if opaque and same >= opaque * 0.5:
                vis += 1
                by_zone[s.zone] += 1
                pixels += same
    return vis, by_zone, pixels


def test_crowd_visible_outside_the_ui_every_venue():
    """Cada local, partida assistida desenhada (apos o warm): gente suficiente fora da UI e nas DUAS
    laterais (casa e visitante). A frente (atras do rodape) so recebe o excedente."""
    rows = {}
    for level in LEVELS:
        dens = crowd.LEVELS[level]["density"]
        for v in crowd.VENUES:
            cr = start(v, level, seed=4)
            for _ in range(30):
                g.step(1 / 60)
            g.state = "play"
            cr.react.clear()
            cr.next_upd = 0
            g.draw()
            g.draw()
            vis, zones, px = _visible_people(cr, crowd.ui_rects(True))
            total = sum(s.n for s in cr.segs)
            assert vis >= int(VIS_MIN[v] * dens), (v, level, vis, VIS_MIN[v])
            assert zones["L"] >= 15 * dens and zones["R"] >= 15 * dens, (v, level, zones)
            fids = {s.fid for s in cr.segs if s.zone in "LR"}
            assert fids == {"home", "away"}, (v, fids)
            side_cap = sum(1 for se in crowd._seats(dict(crowd.VENUES[v])) if se[0] != "F"
                           and not crowd._banner_zone(se))
            hidden_front = sum(1 for s in cr.segs if s.zone == "F" for r in s.boxes
                               if crowd.visible_frac(r, crowd.UI_ALL) < 0.5)
            sides = sum(s.n for s in cr.segs if s.zone != "F")
            # gente escondida na frente so quando as laterais visiveis ja estao cheias (excedente)
            if hidden_front:
                assert sides >= side_cap, (v, level, sides, side_cap, hidden_front)
            rows[(v, level)] = (total, vis, px)
    for a, b in zip(VIS_ORDER, VIS_ORDER[1:]):                # cresce com o local
        assert rows[(a, "ALTA")][1] <= rows[(b, "ALTA")][1], (a, b, rows[(a, "ALTA")], rows[(b, "ALTA")])
    for v in crowd.VENUES:
        t, vis, px = rows[(v, "ALTA")]
        print("   %-11s ALTA: %3d desenhados, %3d visiveis (%5d px); MEDIA: %3d / %3d" % (
            v, t, vis, px, rows[(v, "MEDIA")][0], rows[(v, "MEDIA")][1]))


def test_friendly_crowd_visible_with_hints():
    """Amistoso (bairro leve, sem telao, com a linha de dicas): torcida visivel nas laterais."""
    set_level("ALTA")
    random.seed(1)
    g.new_match(1, crowd.FRIENDLY_VENUE)
    g.state = "play"
    cr = g.crowd
    cr.react.clear()
    cr.next_upd = 0
    g.draw()
    g.draw()
    vis, zones, _ = _visible_people(cr, crowd.ui_rects(False))
    assert vis >= VIS_MIN["bairro"] and zones["L"] >= 15 and zones["R"] >= 15, (vis, zones)
    g.state = "menu"


def test_banners_visible_and_generic_outside_campaign():
    """Faixas de pano: fora de toda a UI; fora da campanha frases genericas (sem Ze Poeira); na campanha
    as do local (a 1a, do lado da casa = jogador, pode citar o Ze Poeira)."""
    assert crowd.GENERIC_BANNERS and not any("ZÉ" in t for t in crowd.GENERIC_BANNERS)
    for t in crowd.GENERIC_BANNERS:
        t.encode("latin-1")
    for v in crowd.VENUES:
        for story in (False, True):
            texts = crowd.banner_texts(v, (50, 120, 255), (235, 65, 65), story)
            assert len(texts) == 2 and texts[0] != texts[1], (v, texts)
            if story:
                assert texts[0] == crowd.EXTRAS[v]["banners"][0] and texts[1] in crowd.EXTRAS[v]["banners"]
            else:
                assert all(t in crowd.GENERIC_BANNERS for t in texts) and not any("ZÉ" in t for t in texts)
        b = crowd.warm_crowd(v, (50, 120, 255), (235, 65, 65), "ALTA", base=g.pitch_surf, txt=g.text_img)
        for story in (False, True):
            for img, pos in b.banners[story]:
                r = img.get_rect(topleft=pos)
                assert crowd.visible_frac(r, crowd.UI_ALL) == 1.0, (v, r)
                assert not r.colliderect(soccer.PITCH) and r.h > r.w, (v, r)       # vertical, fora do campo
                nets = [pygame.Rect(soccer.PITCH.left - soccer.GOAL_DEPTH, soccer.CY - soccer.GOAL_HALF,
                                    soccer.GOAL_DEPTH, soccer.GOAL_HALF * 2),
                        pygame.Rect(soccer.PITCH.right, soccer.CY - soccer.GOAL_HALF, soccer.GOAL_DEPTH,
                                    soccer.GOAL_HALF * 2)]
                assert not any(r.colliderect(n) for n in nets), (v, r)
        # faixas na grade (horizontais): fora do campo e de toda a UI
        for story in (False, True):
            assert b.rails[story], (v, story)
            for img, pos in b.rails[story]:
                r = img.get_rect(topleft=pos)
                assert crowd.visible_frac(r, crowd.UI_ALL) == 1.0, (v, r)
                assert not r.colliderect(soccer.PITCH) and r.w > r.h, (v, r)
    # partidas reais: Modo Robos / carreira = genericas; campanha (return_state "campaign") = do local
    set_level("ALTA")
    g.start_robot_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), lambda s, e: None, venue="bairro")
    assert g.crowd.story is False
    g.start_robot_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), lambda s, e: None,
                        return_state="campaign", venue="bairro")
    assert g.crowd.story is True
    g.toggle_crowd()                                      # ALTA -> MEDIA: re-warm mantem as faixas da campanha
    assert g.crowd.story is True
    start("arena")
    assert g.crowd.story is False
    g.match_sink = None
    set_level("ALTA")


def test_screenshots_optional():
    if not SHOTS_DIR:
        return
    os.makedirs(SHOTS_DIR, exist_ok=True)
    for v in ("bairro", "arena", "mundial"):
        cr = start(v, "ALTA")
        for _ in range(120):
            g.step(1 / 60)
        g.state = "play"
        cr.react.clear()
        cr.next_upd = 0
        g.draw()
        pygame.image.save(screen, os.path.join(SHOTS_DIR, "test_crowd_%s.png" % v))
        g.goal(0)
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 0.45:
            g.draw()
        pygame.image.save(screen, os.path.join(SHOTS_DIR, "test_crowd_%s_gol.png" % v))


if __name__ == "__main__":
    only = sys.argv[1:]
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and (not only or k in only)]
    for name, t in tests:
        t()
        print("ok", name)
    assert not FORBIDDEN, FORBIDDEN
    print(len(tests), "testes passaram")
