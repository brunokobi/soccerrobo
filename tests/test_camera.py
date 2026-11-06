"""Testes da CAMERA DE ESTADIO (game/crowd.py: Layout/VENUES_WIDE/CAM_*; soccer.py: mundo reduzido, prefs
"camera", tecla C, LOD da camera). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_camera.py [teste ...]

NUNCA toca ~/.soccerpy_*.json: prefs/campaign/garage/career usam stores em memoria (trocados ANTES de
criar o Game) e store.write e uma sentinela que FALHA se chamada. Screenshots so se SOCCERPY_SHOTS_DIR
estiver definido (bairro, ginasio, estadio, mundial com gol e confete em ESTADIO; o Amistoso em PERTO).
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
    """camera None = AUTO (o jogador nunca escolheu: campo ausente do JSON)."""
    d = {"v": 1, "crowd": level}
    if camera is not None:
        d["camera"] = camera
    PREFS["raw"] = json.dumps(d)
    prefs.reset_cache()


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


# --- prefs e regra AUTO ------------------------------------------------------------------------------
def test_camera_rule_auto_and_explicit():
    set_prefs("ALTA")                                        # AUTO
    assert prefs.get("camera") is None and prefs.load() == {"crowd": "ALTA", "sfx_vol": "2", "music_vol": "2", "mute": "0"}
    assert start("arena").b.camera == "ESTADIO" and g.camera_on()          # assistida -> ESTADIO
    g.new_match(1, crowd.FRIENDLY_VENUE)                     # amistoso com humano -> PERTO
    assert g.crowd.b.camera == "PERTO" and not g.camera_on()
    g.new_match(2, crowd.FRIENDLY_VENUE)
    assert g.crowd.b.camera == "PERTO"
    set_prefs("ALTA", "PERTO")                               # escolhida: vale para tudo
    assert start("arena", camera="PERTO").b.camera == "PERTO"
    set_prefs("ALTA", "ESTADIO")
    g.new_match(1, crowd.FRIENDLY_VENUE)
    assert g.crowd.b.camera == "ESTADIO" and g.camera_on()
    called = []                                              # Modo Robos / campanha: assistidas
    set_prefs("ALTA")
    g.start_robot_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), called.append, venue="bairro")
    assert g.crowd.b.camera == "ESTADIO"
    g.start_robot_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)), called.append,
                        return_state="campaign", venue="mundial")
    assert g.crowd.b.camera == "ESTADIO"
    g.match_sink = None
    assert start("mundial", "OFF") is None and not g.camera_on()           # sem torcida: campo cheio
    # prefs: valores invalidos caem para AUTO; AUTO nao vai para o JSON
    for raw in ('{"v": 1, "camera": "LONGE"}', '{"v": 1, "camera": 1}', '{"v": 1, "camera": null}'):
        PREFS["raw"] = raw
        prefs.reset_cache()
        assert prefs.get("camera") is None and g.camera_pref() is None, raw
    set_prefs("ALTA")
    assert prefs.set("camera", "ESTADIO") and json.loads(PREFS["raw"])["camera"] == "ESTADIO"
    assert not prefs.set("camera", "LONGE") and prefs.get("camera") == "ESTADIO"
    assert prefs.unset("camera") and "camera" not in json.loads(PREFS["raw"]) and prefs.get("camera") is None
    assert not prefs.unset("crowd")                          # so campos opcionais
    g.state = "menu"


def test_key_c_menu_and_pause():
    set_prefs("ALTA")
    g.state = "menu"
    btns = [r.copy() for r in g.menu_btns] + [g.continue_btn.copy(), g.robots_btn(), g.campaign_btn()]
    seen = []
    for _ in range(3):                                       # AUTO -> ESTADIO -> PERTO -> AUTO
        key(pygame.K_c)
        seen.append(prefs.get("camera"))
        g.text_cache.clear()
        g.draw()
        assert ("F11: tela cheia  |  T: torcida ALTA", 22, (120, 160, 185)) in g.text_cache
        lab = "  |  C: câmera " + soccer.CAMERA_LABELS[seen[-1]]
        assert (lab, 22, (120, 160, 185)) in g.text_cache, lab
    assert seen == ["ESTADIO", "PERTO", None], seen
    assert "camera" not in json.loads(PREFS["raw"])
    assert [r.copy() for r in g.menu_btns] + [g.continue_btn.copy(), g.robots_btn(), g.campaign_btn()] == btns
    w = g.font(22).size("F11: tela cheia  |  T: torcida DESLIGADA  |  C: câmera ESTÁDIO")[0]
    assert w < soccer.W - 40
    # pausa da partida assistida: alterna e aplica na hora (re-warm no evento)
    cr = start("mundial")
    assert cr.b.camera == "ESTADIO"
    key(pygame.K_c)                                          # fora da pausa: nada
    assert g.crowd is cr and prefs.get("camera") is None
    key(pygame.K_p)
    key(pygame.K_c)
    assert prefs.get("camera") == "PERTO" and g.crowd.b.camera == "PERTO" and '"PERTO"' in PREFS["raw"]
    g.text_cache.clear()
    g.draw()
    assert ("C: câmera PERTO", 28, (255, 230, 120)) in g.text_cache
    assert any(k[0].startswith("T: torcida") for k in g.text_cache)
    key(pygame.K_c)
    assert prefs.get("camera") == "ESTADIO" and g.crowd.b.camera == "ESTADIO" and g.camera_on()
    with SurfaceCounter() as c:                              # pausado em ESTADIO: nada por quadro
        for _ in range(30):
            g.draw()
    assert c.n == 0
    key(pygame.K_p)
    assert not g.paused
    # amistoso sem torcida: a pausa nao oferece camera
    g.new_match(1)
    g.state = "play"
    g.paused = True
    key(pygame.K_c)
    assert prefs.get("camera") == "ESTADIO"
    g.text_cache.clear()
    g.draw()
    assert not any(k[0].startswith("C: câmera") for k in g.text_cache)
    g.paused = False
    # amistoso com torcida (menu): a pausa oferece e aplica
    set_prefs("ALTA")
    g.state = "menu"
    key(pygame.K_1)
    assert g.crowd.b.camera == "PERTO"
    g.paused = True
    key(pygame.K_c)
    assert g.crowd.b.camera == "ESTADIO" and prefs.get("camera") == "ESTADIO"
    g.paused = False
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
    set_prefs("ALTA", "ESTADIO")
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


# --- LOD da camera ---------------------------------------------------------------------------------------
def test_camera_lod_falls_to_perto():
    cr = start("mundial")
    g.state = "play"
    assert cr.b.camera == "ESTADIO" and not g.cam_fallback
    for _ in range(soccer.CAM_LOD_WINDOW - 1):
        g.cam_feed(soccer.CAM_LOD_MS + 5)
    assert g.crowd is cr                                     # janela incompleta: nada
    g.cam_feed(soccer.CAM_LOD_MS + 5)
    assert g.cam_fallback and g.crowd.b.camera == "PERTO" and g.camera_mode() == "PERTO"
    assert prefs.get("camera") is None                       # o LOD nao grava nada nas prefs
    with SurfaceCounter() as c:
        for _ in range(60):
            g.draw()
    assert c.n == 0
    # integracao: Game.draw mede o quadro (limite forcado para baixo)
    cr = start("estadio")
    assert cr.b.camera == "ESTADIO" and not g.cam_fallback   # partida nova: volta ao estadio
    old = soccer.CAM_LOD_MS
    soccer.CAM_LOD_MS = -1.0
    try:
        for _ in range(soccer.CAM_LOD_WINDOW + 1):
            g.draw()
    finally:
        soccer.CAM_LOD_MS = old
    assert g.cam_fallback and g.crowd.b.camera == "PERTO" and not g.camera_on()
    g.paused = True                                          # C na pausa: escolha explicita volta
    key(pygame.K_c)
    assert g.crowd.b.camera == "ESTADIO" and not g.cam_fallback
    g.paused = False
    # media abaixo do limite: nao cai
    start("estadio")
    for _ in range(soccer.CAM_LOD_WINDOW * 3):
        g.cam_feed(soccer.CAM_LOD_MS * 0.5)
    assert not g.cam_fallback and g.crowd.b.camera == "ESTADIO"


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
    pygame.image.save(screen, os.path.join(SHOTS_DIR, "camera_amistoso_perto.png"))
    g.state = "menu"


if __name__ == "__main__":
    only = sys.argv[1:]
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and (not only or k in only)]
    for name, t in tests:
        t()
        print("ok", name)
    assert not FORBIDDEN, FORBIDDEN
    print(len(tests), "testes passaram")
