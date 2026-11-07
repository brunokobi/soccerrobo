"""Testes da NARRACAO (game/narration.py + ganchos em soccer.Game): narrador (Tonho) e comentarista (Cleide)
numa faixa de TV no lugar dos letreiros da torcida. Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_narration.py [teste ...]

NUNCA toca ~/.soccerpy_*.json (stores em memoria; store.write e uma sentinela que falha). Capturas so com
SOCCERPY_SHOTS_DIR definido.
"""
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

import campaign as cm  # noqa: E402
import career  # noqa: E402
import garage as gm  # noqa: E402
import prefs  # noqa: E402
import store  # noqa: E402

FORBIDDEN = []


def _forbid(name):
    def f(*a, **k):
        FORBIDDEN.append(name)
        raise AssertionError("%s chamada pelos testes da narracao" % name)
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
import narration as nr  # noqa: E402
import soccer  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)
SHOTS_DIR = os.environ.get("SOCCERPY_SHOTS_DIR")
EVENTS = ("start", "chance", "save", "post", "goal", "equalize", "turn", "own", "steal", "dribble", "skill",
          "end_win", "end_draw")


def set_level(level="ALTA", camera=None):
    PREFS["raw"] = json.dumps({"v": 1, "crowd": level})
    prefs.reset_cache()
    g.camera_start = camera or soccer.CAMERA_START


def cfg(name, color, ovr=65, prefix="Robo"):
    return {"name": name, "color": color, "squad": [("%s%d" % (prefix, i), ovr) for i in range(5)]}


def start(venue="arena", level="ALTA", camera=None, seed=0):
    set_level(level, camera)
    random.seed(seed)
    g.start_career_match(cfg("POEIRA FC", (50, 120, 255), prefix="Zeca"), cfg("RODO UNITED", (235, 65, 65)),
                         venue=venue)
    g.state = "play"
    return g.narr


class SurfaceCounter:
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


def text_of(imgs, n):
    """Reconstroi o texto de uma fala a partir das imagens (pelos dicionarios da Narration)."""
    rev = {}
    for k, v in nr._FRAG.items():
        rev[id(v)] = k[0]
    for i, img in enumerate(n.team_img):
        rev[id(img)] = "<T%d>" % i
    for t in range(2):
        for k, img in enumerate(n.robot_img[t]):
            rev[id(img)] = "<R%d.%d>" % (t, k)
    for sid, img in n.skill_img.items():
        rev[id(img)] = "<K:%s>" % sid
    return "".join(rev.get(id(im), "?") for im in imgs)


# --- catalogo ------------------------------------------------------------------------------------
def test_catalog_variety_tokens_and_latin1():
    for ev in EVENTS:
        assert len(nr.LINES[ev]["N"]) >= 6, ev                  # >= 6 falas do narrador por lance
        assert len(nr.LINES[ev]["C"]) >= 4, ev                  # varias da comentarista
    assert len(nr.LINES["idle"]["N"]) >= 6 and len(nr.LINES["idle"]["C"]) >= 6
    assert len(nr.LINES["score"]["C"]) >= 4 and len(nr.LINES["stat"]["C"]) >= 4
    for kind, spk, line in nr.all_lines():
        line.encode("latin-1")
        for k, s in nr.parse(line):
            if k == "k":
                assert s in nr.TOKENS, (kind, line, s)
        assert len(line) <= 60, line
    for s in nr.all_strings():
        s.encode("latin-1")
    with open(os.path.join(ROOT, "game", "narration.py"), encoding="utf-8") as f:
        f.read().encode("latin-1")
    assert nr.parse("Gol do {T}!") == [("t", "Gol do "), ("k", "T"), ("t", "!")]


def test_lines_fit_band_with_long_names():
    teams = [("PANO DE CHÃO EC", (60, 60, 200), ["Escovão Supremo", "Turbinho Neto", "Bocal", "Rodinha", "Zé"]),
             ("VASSOURAS UNIDAS", (200, 60, 60), ["Pano Lento Jr", "Ciclone", "Suga-Pó", "Esfregão", "X"])]
    n = nr.Narration(teams, g.text_img, seed=1, skill_names={"drible": "Drible Giratório"})
    over = []
    for (kind, spk), opts in n.parts.items():
        ctx = n._ctx(kind, 0, 0, "drible")
        for parts in opts:
            w = sum((img if img is not None else ctx[key]).get_width() for img, key in parts)
            if w > nr.MAX_TEXT_W:
                over.append((kind, spk, w))
    # com nomes longos poucas falas passam da faixa; o sorteio pula essas (sempre ha uma que cabe)
    assert len(over) <= 12, over
    for (kind, spk) in n.parts:
        for _ in range(6):
            imgs, w = n._line(kind, spk, n._ctx(kind, 1, 2, "drible"))
            assert w <= nr.MAX_TEXT_W, (kind, spk, w)


# --- comportamento da fila -------------------------------------------------------------------------
def test_queue_priorities_no_spam_and_idle():
    n = start("arena")
    assert n.cur is None and n.queue and n.queue[0][6] == "start"        # o pontape inicial e narrado
    n.tick(0.0)
    assert n.cur[0] == "N" and n.cur[6] == "start"
    # lances pequenos em rajada: no maximo 1 entra e a fila nunca passa do teto
    acc = 0
    for k in range(200):
        acc += bool(n.event("steal", k % 2, k % 5))
        n.event("dribble", 0, 1)
        assert len(n.queue) <= nr.QUEUE_MAX
    assert acc <= 1
    # gol corta o que estiver passando (inclusive o pequeno) e entra na frente
    n.tick(5.0)
    n.event("steal", 1, 2)
    assert n.event("goal", 0, 3, score=[1, 0], minute=12)
    n.tick(0.01)
    assert n.cur[6] == "goal" and n.cur[0] == "N"
    assert all(q[5] >= nr.PRIO["goal"] for q in n.queue)
    # depois de tudo: calmaria puxa assunto sozinha
    for _ in range(400):
        n.tick(0.1)
    kinds = set()
    for _ in range(600):
        c = n.tick(0.1)
        if c is not None:
            kinds.add(c[6])
    assert "idle" in kinds or "stat" in kinds, kinds
    # nunca a mesma fala duas vezes seguidas para o mesmo lance/falante
    seen = []
    for _ in range(30):
        imgs, _w = n._line("goal", "N", n._ctx("goal", 0, 1, None))
        seen.append(imgs)
    assert all(a != b for a, b in zip(seen, seen[1:]))
    # saco embaralhado: todas as falas do lance saem antes de alguma repetir
    n.used.clear()
    for kind in ("goal", "save", "chance"):
        k = len(nr.LINES[kind]["N"])
        picks = [n._line(kind, "N", n._ctx(kind, 0, 1, None))[0] for _ in range(k)]
        assert len(set(picks)) == k, kind


def test_names_of_real_match_in_lines():
    n = start("estadio", seed=3)
    g.events.append({"min": 10, "team": 0, "name": "Zeca2", "own": False, "pid": None})
    g.score = [1, 0]
    n.queue.clear()
    n.cur = None
    g.narr_hook("goal", 0, g.teams[0].players[2])
    n.tick(0.01)
    txt = text_of(n.cur[1], n)
    assert n.cur[6] == "goal", n.cur[6]
    assert "<R0.2>" in txt or "<T0>" in txt, txt              # o robo (Zeca2) ou o time que marcou
    assert g.teams[0].players[2].name == "Zeca2"
    # amistoso: time "VOCE" vira "SEU TIME" e robos sem nome ganham apelidos
    set_level()
    g.new_match(1, crowd.FRIENDLY_VENUE)
    n = g.narr
    assert n.team_img[0] is g.text_img("SEU TIME", nr.TEXT_SIZE, nr._light(soccer.led_color(g.teams[0].color)))
    assert n.robot_img[1][2] is g.text_img(nr.FALLBACK_ROBOTS[1][2], nr.TEXT_SIZE, nr.NAME_COL)


def test_goal_kinds_equalize_turn_own():
    start("arena", seed=4)
    kinds = []
    real = g.narr.event
    g.narr.event = lambda k, *a, **kw: kinds.append(k) or real(k, *a, **kw)
    seq = [(1, False), (0, False), (0, False), (1, True)]   # 0x1, 1x1 (empate), 2x1 (virada), 2x2 contra
    for team, own in seq:
        g.score[team] += 1
        g.events.append({"min": 5, "team": team, "name": "", "own": own, "pid": None})
        g.narr_hook("goal", team, None)
    assert kinds == ["goal", "equalize", "turn", "own"], kinds
    g.narr.event = real


# --- partida inteira: RNG, simulacao e Surface ------------------------------------------------------
def test_global_rng_untouched_and_scores_identical():
    def play(seed, narrate):
        set_level("OFF")
        random.seed(seed)
        g.start_career_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)))
        if not narrate:
            g.narr = None
        g.state = "play"
        k = 0
        while g.state != "over":
            g.step(1 / 60)
            k += 1
            if k % 5 == 0:
                g.draw()
        return list(g.score), random.getstate()
    for seed in range(3):
        assert play(seed, True) == play(seed, False), seed
    n = start("arena")
    st = random.getstate()
    for k in range(300):                                         # a narracao so usa o RNG privado
        n.event(EVENTS[k % len(EVENTS)], k % 2, k % 5, "drible", score=[k % 3, 1], minute=k % 90)
        n.tick(0.2)
        g.draw()
    assert random.getstate() == st


def test_zero_surface_per_frame_band_every_camera():
    for camera, level in (("ESTADIO", "ALTA"), ("PERTO", "ALTA"), (None, "OFF")):
        n = start("mundial", level, camera)
        for _ in range(3):
            g.step(1 / 60)
            g.draw()
        shown = 0
        with SurfaceCounter() as c:
            for k in range(400):
                g.step(1 / 60)
                if k == 20:
                    g.goal(0)
                elif k == 150:
                    g.crowd_event("save", 1, g.teams[1].players[0])
                elif k == 220:
                    g.narr_hook("steal", 0, g.teams[0].players[3])
                elif k == 300:
                    g.crowd_event("end", 0)
                g.paused = 260 <= k < 270
                n.tick(0.05)                                     # o relogio da narracao corre mais rapido
                g.draw()
                shown += n.cur is not None
        g.paused = False
        assert c.n == 0, (camera, level, c.n)
        assert shown > 100 and n.n_lines >= 4, (camera, shown, n.n_lines)


def test_band_position_never_over_the_game():
    n = start("estadio", camera="ESTADIO")
    n.tick(0.01)
    calls = []
    real = n.draw
    n.draw = lambda scr, x, y: calls.append((x, y)) or real(scr, x, y)
    g.draw()
    x, y = calls[-1]
    band = pygame.Rect(x, y, nr.BAND_W, nr.BAND_H)
    assert not band.colliderect(crowd.CAM_RECT) and band.bottom <= crowd.UI_PAUSE.top   # sob o campo, sobre o rodape
    # PERTO: a faixa fica no campo, do lado oposto ao da bola (e troca se a bola chegar)
    n = start("estadio", camera="PERTO")
    n.tick(0.01)
    n.draw = lambda scr, x, y: calls.append((x, y)) or real(scr, x, y)
    for by in (soccer.CY + 220, soccer.CY - 220, soccer.CY + 230):
        n.cur = None
        n.queue.clear()
        n.event("goal", 0, 1)
        g.ball.pos = soccer.V(soccer.CX, by)
        g.draw()
        x, y = calls[-1]
        band = pygame.Rect(x, y, nr.BAND_W, nr.BAND_H)
        assert soccer.PITCH.contains(band)
        assert abs((y + nr.BAND_H / 2) - by) > nr.BAND_H, (by, y)
    g.ball.pos = soccer.V(soccer.CX, soccer.PITCH.top + 30)    # a bola entra na faixa: ela troca de lado
    g.draw()
    assert calls[-1][1] > soccer.CY
    g.speed_idx = 3                                              # MAX: nada de narracao
    k = len(calls)
    g.draw()
    assert len(calls) == k
    assert g.narr_hook("goal", 0) is None
    g.speed_idx = 0


def test_no_crowd_words_on_screen():
    """Os letreiros da torcida sairam: nenhum texto deles entra no cache durante uma partida."""
    old = {"GOOOL!", "NÃOOO!", "VAAAI!", "OLÉ!", "UHHH!", "OOOH!", "CLANG!", "CLAP CLAP", "OLÉ, OLÉ!", "BIP BIP!",
           "BZZZT!", "OLÉ.EXE", "ERRO 404!", "CLIC CLIC"}
    g.text_cache.clear()
    start("mundial")
    for k in range(200):
        g.step(1 / 60)
        if k in (10, 90):
            g.goal(k // 90)
        g.draw()
    assert not [k for k in g.text_cache if k[0] in old]


def test_screenshots_optional():
    if not SHOTS_DIR:
        return
    os.makedirs(SHOTS_DIR, exist_ok=True)
    for camera in ("ESTADIO", "PERTO"):
        n = start("estadio", camera=camera, seed=5)
        for _ in range(120):
            g.step(1 / 60)
        g.goal(0)
        for name, adv in (("gol", 0.3), ("comentario", 3.6)):
            n.tick(adv)
            g.draw()
            pygame.image.save(screen, os.path.join(SHOTS_DIR, "narracao_%s_%s.png" % (camera.lower(), name)))
    g.state = "menu"


if __name__ == "__main__":
    only = sys.argv[1:]
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and (not only or k in only)]
    for name, t in tests:
        t()
        print("ok", name)
    assert not FORBIDDEN, FORBIDDEN
    print(len(tests), "testes passaram")
