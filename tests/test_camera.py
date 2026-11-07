"""Testes da CAMERA DE ESTADIO (game/crowd.py: Layout/VENUES_WIDE/CAM_*; soccer.py: mundo reduzido, toda
partida comeca em ESTADIO, tecla C na pausa so para a partida atual, o jogo nunca troca a camera sozinho). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_camera.py [teste ...]

NUNCA toca ~/.soccerpy_*.json: prefs/campaign/garage/career usam stores em memoria (trocados ANTES de
criar o Game) e store.write e uma sentinela que FALHA se chamada. Screenshots so se SOCCERPY_SHOTS_DIR
estiver definido (bairro, ginasio, estadio, mundial com gol e confete em ESTADIO; o Amistoso tambem).
"""
import json
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
        raise AssertionError("%s chamada pelos testes da camera" % name)
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
VIS_ORDER = ("bairro", "quadra", "ginasio", "arena", "estadio", "mundial")


def set_prefs(level="ALTA", camera=None):
    """Torcida no nivel pedido. camera: camera de INICIO das proximas partidas (Game.camera_start; None =
    a do jogo, ESTADIO). Nada disso vai para as prefs: a camera nao e mais uma preferencia gravada."""
    PREFS["raw"] = json.dumps({"v": 1, "crowd": level})
    prefs.reset_cache()
    g.camera_start = camera or soccer.CAMERA_START


def cfg(name, color, ovr=65):
    return {"name": name, "color": color, "squad": [("J%d" % i, ovr) for i in range(5)]}


def start(venue="arena", level="ALTA", seed=0, camera=None):
    set_prefs(level, camera)
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


def key(k):
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))


# --- toda partida comeca em ESTADIO ------------------------------------------------------------------
def test_every_match_starts_in_estadio():
    set_prefs("ALTA")
    assert soccer.CAMERA_START == "ESTADIO" and g.camera_start == "ESTADIO"
    assert prefs.load() == {"crowd": "ALTA", "sfx_vol": "2", "music_vol": "2", "mute": "0"}
    assert start("arena").b.camera == "ESTADIO" and g.camera_on()          # carreira
    for mode in (1, 2):                                      # amistoso com humano tambem
        g.new_match(mode, crowd.FRIENDLY_VENUE)
        assert g.crowd.b.camera == "ESTADIO" and g.camera_mode() == "ESTADIO" and g.camera_on(), mode
    called = []                                              # Modo Robos / campanha
    g.start_robot_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), called.append, venue="bairro")
    assert g.crowd.b.camera == "ESTADIO"
    g.start_robot_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), called.append,
                        return_state="campaign", venue="mundial")
    assert g.crowd.b.camera == "ESTADIO"
    g.match_sink = None
    g.start_demo()                                           # demo do menu
    assert g.crowd.b.camera == "ESTADIO"
    g.stop_demo()
    # torcida desligada: nao ha estadio (campo cheio, sem arquibancada); o modo continua ESTADIO
    assert start("mundial", "OFF") is None and not g.camera_on() and g.camera_mode() == "ESTADIO"
    g.new_match(1, crowd.FRIENDLY_VENUE)
    assert g.crowd is None
    # a antiga pref "camera" (JSON de quem ja jogou) e ignorada e some no proximo save
    for raw in ('{"v": 1, "crowd": "ALTA", "camera": "PERTO"}', '{"v": 1, "camera": "LONGE"}'):
        PREFS["raw"] = raw
        prefs.reset_cache()
        assert prefs.get("camera") is None and "camera" not in prefs.load(), raw
        assert start("arena").b.camera == "ESTADIO", raw
    assert prefs.set("crowd", "MEDIA") and "camera" not in json.loads(PREFS["raw"])
    assert not prefs.set("camera", "PERTO") and "camera" not in json.loads(PREFS["raw"])
    g.state = "menu"


def test_key_c_menu_and_pause():
    set_prefs("ALTA")
    g.state = "menu"
    raw = PREFS["raw"]
    btns = [r.copy() for r in g.menu_btns] + [g.continue_btn.copy(), g.robots_btn(), g.campaign_btn()]
    for _ in range(3):                                       # menu: C nao faz nada (nao ha mais escolha)
        key(pygame.K_c)
        g.text_cache.clear()
        g.draw()
        assert ("F11: tela cheia  |  T: torcida ALTA", 22, (120, 160, 185)) in g.text_cache
        assert not any("câmera" in k[0] for k in g.text_cache)
    assert PREFS["raw"] == raw
    assert [r.copy() for r in g.menu_btns] + [g.continue_btn.copy(), g.robots_btn(), g.campaign_btn()] == btns
    # pausa da partida assistida: alterna SO esta partida e aplica na hora (re-warm no evento)
    cr = start("mundial")
    assert cr.b.camera == "ESTADIO"
    key(pygame.K_c)                                          # fora da pausa: nada
    assert g.crowd is cr
    key(pygame.K_p)
    key(pygame.K_c)
    assert g.camera_mode() == "PERTO" and g.crowd.b.camera == "PERTO" and PREFS["raw"] == raw
    g.text_cache.clear()
    g.draw()
    assert ("C: câmera PERTO", 28, (255, 230, 120)) in g.text_cache
    assert any(k[0].startswith("T: torcida") for k in g.text_cache)
    key(pygame.K_c)
    assert g.camera_mode() == "ESTADIO" and g.crowd.b.camera == "ESTADIO" and g.camera_on()
    with SurfaceCounter() as c:                              # pausado em ESTADIO: nada por quadro
        for _ in range(30):
            g.draw()
    assert c.n == 0
    key(pygame.K_c)                                          # deixa em PERTO...
    key(pygame.K_p)
    assert not g.paused and g.camera_mode() == "PERTO"
    assert start("mundial").b.camera == "ESTADIO"            # ...e a partida seguinte volta ao ESTADIO
    # amistoso sem torcida: a pausa nao oferece camera
    g.new_match(1)
    g.state = "play"
    g.paused = True
    key(pygame.K_c)
    assert g.camera_mode() == "ESTADIO"
    g.text_cache.clear()
    g.draw()
    assert not any(k[0].startswith("C: câmera") for k in g.text_cache)
    g.paused = False
    # amistoso com torcida (menu): comeca em ESTADIO; a pausa oferece e aplica; o proximo volta
    g.state = "menu"
    key(pygame.K_1)
    assert g.crowd.b.camera == "ESTADIO"
    g.paused = True
    key(pygame.K_c)
    assert g.crowd.b.camera == "PERTO" and PREFS["raw"] == raw
    g.paused = False
    g.state = "over"
    key(pygame.K_RETURN)                                     # jogar de novo
    assert g.crowd.b.camera == "ESTADIO"
    g.state = "menu"


# --- geometria larga ----------------------------------------------------------------------------------
def _seg_rects(b):
    for s in b.segs:
        w, h = s.imgs[0].get_size()
        for dx, dy in ((0, 0), s.jump):
            yield s, pygame.Rect(s.x + dx, s.y + dy, w, h)


def test_wide_layout_free_space_and_fidelity():
    scr_r = pygame.Rect(0, 0, soccer.W, soccer.H)
    assert crowd.CAM_RECT.size == crowd.CAM_SIZE and crowd.CAM_RECT.top >= crowd.UI_HUD_WIDE.bottom + 40
    assert crowd.CAM_RECT.bottom <= crowd.UI_PAUSE.top - 50 and crowd.CAM_RECT.left >= 100
    assert 0.78 <= crowd.CAM_SCALE <= 0.85
    for v in crowd.VENUES:
        b = crowd.warm_crowd(v, (50, 120, 255), (235, 65, 65), "ALTA", base=g.pitch_surf, camera="ESTADIO",
                             txt=g.text_img)
        assert b.camera == "ESTADIO" and b.segs and b.static.get_size() == (soccer.W, soccer.H)
        for s, r in _seg_rects(b):
            assert not r.colliderect(crowd.CAM_RECT.inflate(4, 4)), (v, s.zone, r)
            assert not r.colliderect(crowd.UI_HUD_WIDE.inflate(0, -24)), (v, s.zone, r)   # no maximo meio atras
            assert scr_r.contains(r), (v, r)
        zones = {s.zone for s in b.segs}
        assert {"L", "R", "F", "T"} <= zones, (v, zones)
        for s in b.segs:                                     # casa na esquerda, visitante na direita
            if s.fid == "home":
                assert s.cx < soccer.CX, (v, s.cx)
            elif s.fid == "away":
                assert s.cx > soccer.CX, (v, s.cx)
        for story in (True, False):                          # faixas: fora do campo e da UI
            for img, pos in b.banners[story]:
                r = img.get_rect(topleft=pos)
                assert not r.colliderect(crowd.CAM_RECT) and crowd.visible_frac(r, crowd.UI_ALL_WIDE) == 1.0
        for imgs, x, y, fid, _ in b.flags:
            assert not imgs[0].get_rect(topleft=(x, y)).colliderect(crowd.CAM_RECT), v
        lx, ly, lw, lh = b.lay.led
        assert pygame.Rect(lx, ly, lw, lh).bottom <= crowd.CAM_RECT.top and ly >= crowd.UI_HUD_WIDE.bottom
    assert len(crowd._CACHE) <= crowd.CACHE_MAX                            # cache limitado
    for a, c in zip(VIS_ORDER, VIS_ORDER[1:]):
        assert crowd.people_count(a, camera="ESTADIO") < crowd.people_count(c, camera="ESTADIO"), (a, c)


# --- zero Surface por quadro em ESTADIO -----------------------------------------------------------------
def test_zero_surface_300_frames_estadio_every_venue_and_level():
    for level in LEVELS:
        for v in crowd.VENUES:
            cr = start(v, level, seed=3)
            assert cr.b.camera == "ESTADIO"
            for _ in range(3):                               # aquecimento (texto do HUD)
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
                    g.paused = 250 <= n < 260
                    g.draw()
            g.paused = False
            assert c.n == 0, (v, level, c.n)
            assert cr.frame >= 300 and g.crowd is cr and g.camera_on()
    # o mundo reduzido aparece na tela (centro do campo = pixel do world_dst)
    p = crowd.cam_point(soccer.CX, soccer.CY + 200)
    assert screen.get_at(p) == g.world_dst.get_at((p[0] - crowd.CAM_POS[0], p[1] - crowd.CAM_POS[1]))


def test_max_in_estadio_draws_the_minimum():
    cr = start("mundial")
    g.state = "play"
    g.draw()
    calls = []
    real = g.cam_scale
    g.cam_scale = lambda *a: calls.append(1) or real(*a)
    try:
        g.speed_idx = 3
        with SurfaceCounter() as c:
            for _ in range(30):
                g.update(1 / 60)
                g.draw()
        f = cr.frame
        g.draw()
        assert cr.frame == f and not calls and c.n == 0      # sem torcida e sem escala
        for p in ((5, 680), (20, 200), (1090, 500), (soccer.CX, 95)):
            assert screen.get_at(p) == g.pitch_surf.get_at(p), p
        g.speed_idx = 0
        g.draw()
        assert calls and cr.frame == f + 1                   # volta ao estadio
    finally:
        g.cam_scale = real
        g.speed_idx = 0


# --- simulacao identica (so desenho) ---------------------------------------------------------------------
def _play(seed, camera, level="ALTA", draw_every=7):
    start("estadio", level, seed=seed, camera=camera)
    g.state = "play"
    k = 0
    while g.state != "over":
        g.step(1 / 60)
        k += 1
        if k % draw_every == 0:
            g.draw()
    return list(g.score), [dict(e) for e in g.events], random.getstate()


def test_scores_identical_estadio_perto_off():
    for seed in range(6):
        a = _play(seed, "ESTADIO")
        b = _play(seed, "PERTO")
        c = _play(seed, None, "OFF")
        assert a == b == c, (seed, a[0], b[0], c[0])


# --- visibilidade: ESTADIO >> PERTO -------------------------------------------------------------------------
def _visible_people(cr, rects):
    """Espectadores desenhados AGORA na tela: caixa >= 50% fora da UI e a maioria dos pixels opacos da
    faixa batendo com a tela (nada desenhado por cima: campo, HUD, rodape)."""
    vis, by_zone = 0, {}
    for s, (img, (x, y)) in zip(cr.segs, cr.blits):
        key_c = img.get_colorkey()
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
                    if key_c is not None and c == key_c:
                        continue
                    opaque += 1
                    same += screen.get_at((px, py)) == c
            if opaque and same >= opaque * 0.5:
                vis += 1
                by_zone[s.zone] = by_zone.get(s.zone, 0) + 1
    return vis, by_zone


def _count(v, camera, level="ALTA"):
    cr = start(v, level, seed=4, camera=camera)
    for _ in range(30):
        g.step(1 / 60)
    g.state = "play"
    cr.react.clear()
    cr.next_upd = 0
    g.narr = None                                            # a faixa do narrador e passageira (cobre a frente)
    g.draw()
    g.draw()
    return _visible_people(cr, crowd.ui_rects_cam(True, camera))


def test_visible_estadio_much_more_than_perto():
    rows = {}
    for v in crowd.VENUES:
        near, _ = _count(v, "PERTO")
        wide, zones = _count(v, "ESTADIO")
        rows[v] = (near, wide)
        assert wide >= 1.8 * near and wide - near >= 80, (v, near, wide)
        assert zones.get("L", 0) >= 30 and zones.get("R", 0) >= 30, (v, zones)
        assert zones.get("F", 0) > 0 and zones.get("T", 0) > 0, (v, zones)
        med, _ = _count(v, "ESTADIO", "MEDIA")
        assert med < wide, (v, med, wide)
    for a, b in zip(VIS_ORDER, VIS_ORDER[1:]):               # lotacao cresce com o local
        assert rows[a][1] < rows[b][1], (a, b, rows[a], rows[b])
    # faixas na grade e bandeiroes cobrem de proposito alguns torcedores (eram >= 900 / 750 sem eles)
    assert rows["mundial"][1] >= 860 and rows["estadio"][1] >= 740, rows
    for v in crowd.VENUES:
        print("   %-11s visiveis PERTO %3d  ESTADIO %4d" % ((v,) + rows[v]))


# --- entrada: UI nao escalada, amistoso por teclado ----------------------------------------------------
def test_speed_buttons_click_in_estadio():
    start("mundial")
    g.state = "play"
    g.draw()
    for i, r in enumerate(g.speed_rects()):
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=r.center, button=1))
        assert g.speed_idx == i, (i, g.speed_idx)
        g.draw()
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=g.speed_rects()[0].center, button=1))
    assert g.speed_idx == 0
    g.draw()
    shots = {}                                              # botoes iguais com camera ESTADIO e PERTO
    pts = [r.center for r in g.speed_rects()] + [(r.left + 3, r.centery) for r in g.speed_rects()]
    for cam in ("ESTADIO", "PERTO"):
        start("mundial", camera=cam)
        g.state = "play"
        g.ball.pos = soccer.V(soccer.CX, soccer.CY)
        g.draw()
        shots[cam] = [screen.get_at(p) for p in pts]
    assert shots["ESTADIO"] == shots["PERTO"]


class Pressed:
    def __init__(self, keys):
        self.keys = set(keys)

    def __getitem__(self, k):
        return k in self.keys


def test_friendly_keyboard_in_estadio():
    set_prefs("ALTA")
    random.seed(5)
    g.state = "menu"
    key(pygame.K_1)
    assert g.crowd.b.camera == "ESTADIO" and g.mode == 1
    g.state = "play"
    real = pygame.key.get_pressed
    try:
        for keys, axis, sign in (((pygame.K_d,), "x", 1), ((pygame.K_a,), "x", -1), ((pygame.K_s,), "y", 1)):
            pygame.key.get_pressed = lambda k=keys: Pressed(k)
            t = g.teams[0]
            g.step(1 / 60)
            p = t.ctrl
            x0 = getattr(p.pos, axis)
            for _ in range(20):
                g.step(1 / 60)
                g.draw()
            assert (getattr(p.pos, axis) - x0) * sign > 15, (keys, x0, getattr(p.pos, axis))
    finally:
        pygame.key.get_pressed = real
    key(pygame.K_p)
    assert g.paused
    key(pygame.K_p)
    key(pygame.K_ESCAPE)
    assert g.state == "menu"


# --- a camera nunca muda sozinha (nem no gol, nem com quadro pesado) ---------------------------------------
class SlowTime:
    """time do soccer com perf_counter que anda `step` s a cada chamada: todo quadro parece pesado."""

    def __init__(self, real, step):
        self.t = real.perf_counter()
        self.step = step

    def perf_counter(self):
        self.t += self.step
        return self.t


def test_goal_never_changes_camera():
    assert not hasattr(g, "cam_feed") and not hasattr(soccer, "CAM_LOD_MS")   # nao ha LOD de camera
    for cam in ("ESTADIO", "PERTO"):
        cr = start("mundial", camera=cam)
        g.state = "play"
        assert g.camera_mode() == cam
        old = soccer.time
        soccer.time = SlowTime(old, 0.006)                   # ~12+ ms medidos por quadro (muito acima do LOD)
        try:
            for k in range(60 * 8):                          # 8 s: gols, fim de jogo, festa, fogos
                g.step(1 / 60)
                if k % 90 == 10:
                    g.goal(k // 90 % 2)
                if k == 400:
                    g.crowd_end()
                g.draw()
                assert g.camera_mode() == cam and g.crowd is cr and cr.b.camera == cam, (cam, k)
        finally:
            soccer.time = old
        assert cr.lod == 0 and g.fw.lod == 0                  # o que degrada: torcida e fogos
        assert sum(g.score) >= 4
    set_prefs("ALTA")
    # gol direto pelo hook, desenho normal: idem
    cr = start("estadio")
    g.state = "play"
    for _ in range(3):
        g.goal(0)
        for _ in range(200):
            g.step(1 / 60)
            g.draw()
    assert g.camera_mode() == "ESTADIO" and g.crowd is cr and g.camera_on()


def test_fireworks_degrade_with_crowd_lod():
    import fireworks
    fw = fireworks.Fireworks(seed=1)
    peaks = {}
    for lod in (2, 1, 0):
        fw.clear()
        fw.lod = lod
        t = 0.0
        fw.show(t, 10, [(255, 0, 0)], pygame.Rect(100, 100, 800, 400))
        peak = 0
        for _ in range(300):
            t += 1 / 60
            fw.update(t, 1 / 60)
            peak = max(peak, len(fw.sparks))
        peaks[lod] = peak
        assert peak <= int(fireworks.SPARK_MAX * fireworks.LOD_SPARKS[lod]), (lod, peak)
    assert peaks[2] > peaks[1] > peaks[0] > 0, peaks


# --- repintura parcial do mundo == repintura completa -------------------------------------------------------
class FakeTime:
    def __init__(self, t):
        self.t = t

    def perf_counter(self):
        return self.t


def test_world_dirty_restore_equals_full_repaint():
    cr = start("arena", seed=9)
    g.state = "play"
    for k in range(240):                                     # movimento, chutes, particulas
        g.step(1 / 60)
        if k == 100:
            g.fx_emit("goal", g.ball.pos)
        g.draw()
    assert g.world_dirty and g.fx                            # houve particulas no quadro anterior
    old = soccer.time
    soccer.time = FakeTime(old.perf_counter())
    g.paused = True                                          # congela rastro, halos e animacoes
    g.fx.clear()                                             # (o desenho das faiscas decai a cada quadro)
    try:
        g.draw()                                             # apaga as faiscas do quadro anterior (sujas)
        g.draw()
        a = pygame.image.tostring(g.world_dst, "RGB")
        g.world_full = True
        g.draw()
        b = pygame.image.tostring(g.world_dst, "RGB")
    finally:
        soccer.time = old
        g.paused = False
    assert a == b


# --- desempenho (informativo; limite duro 8 ms) ----------------------------------------------------------
def test_draw_ms_estadio_full_venue():
    out = {}
    for cam in ("PERTO", "ESTADIO"):
        crowd.clear_cache()
        clk = Clock(500.0)
        g.crowd_clock = clk
        try:
            cr = start("mundial", camera=cam)
        finally:
            g.crowd_clock = None
        g.state = "play"
        for t in g.teams:
            t.players[1].bat = 0.2                           # faiscas em um robo por time
        cr.event("goal", 0)
        cr.event("end", 0)
        for _ in range(10):
            g.draw()
        n = 300
        t0 = time.perf_counter()
        for k in range(n):
            clk.t += 1 / 60
            if k % 60 == 0:
                cr.event("goal", k // 60 % 2)
            g.draw()
        out[cam] = (time.perf_counter() - t0) / n * 1000
    print("   draw_ms mundial ALTA com extras: PERTO %.3f ms, ESTADIO %.3f ms (meta <= 2,5; duro 8)%s" % (
        out["PERTO"], out["ESTADIO"], "" if out["ESTADIO"] <= 2.5 else "  [ACIMA DA META]"))
    assert out["ESTADIO"] <= 8.0, out


def test_scale_api_with_dest():
    """A escala por quadro usa a assinatura f(src, size, dest) (pygame 2.6.1 e pygame-ce 2.5.7)."""
    src = g.world_src
    for f in soccer.CAM_SCALERS.values():
        assert f(src, crowd.CAM_SIZE, g.world_dst) is g.world_dst
    assert g.world_dst.get_size() == crowd.CAM_SIZE and g.world_src.get_size() == crowd.CAM_CROP.size


def test_latin1_source():
    for name in ("crowd.py", "soccer.py", "prefs.py"):
        with open(os.path.join(ROOT, "game", name), encoding="utf-8") as f:
            f.read().encode("latin-1")


def test_screenshots_optional():
    if not SHOTS_DIR:
        return
    os.makedirs(SHOTS_DIR, exist_ok=True)
    for v in ("bairro", "ginasio", "estadio", "mundial"):
        cr = start(v, "ALTA")
        for _ in range(150):
            g.step(1 / 60)
        g.state = "play"
        cr.react.clear()
        cr.next_upd = 0
        g.draw()
        pygame.image.save(screen, os.path.join(SHOTS_DIR, "camera_estadio_%s.png" % v))
        if v == "mundial":
            g.goal(0)
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < 0.6:
                g.draw()
            pygame.image.save(screen, os.path.join(SHOTS_DIR, "camera_estadio_mundial_gol.png"))
    set_prefs("ALTA")
    random.seed(2)
    g.new_match(1, crowd.FRIENDLY_VENUE)
    g.state = "play"
    for _ in range(90):
        g.step(1 / 60)
    g.draw()
    pygame.image.save(screen, os.path.join(SHOTS_DIR, "camera_amistoso_estadio.png"))
    g.state = "menu"


if __name__ == "__main__":
    only = sys.argv[1:]
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and (not only or k in only)]
    for name, t in tests:
        t()
        print("ok", name)
    assert not FORBIDDEN, FORBIDDEN
    print(len(tests), "testes passaram")
