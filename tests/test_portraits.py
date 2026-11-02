"""Testes dos retratos e cenarios por codigo (game/portraits.py). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_portraits.py
Screenshots (grade de retratos, matriz de humores, piscar/falar, estilos novos, colagem de cenarios)
so se SOCCERPY_SHOTS_DIR estiver definido.
"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import pygame  # noqa: E402

import portraits as P  # noqa: E402
import story  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((1100, 700))
SHOTS = os.environ.get("SOCCERPY_SHOTS_DIR")
NEW_MOODS = ("determinado", "maravilhado", "malicioso", "sonolento", "chorando", "gritando", "piscando", "euforico")
NEW_BGS = ("praca", "laboratorio", "aeroporto", "dojo", "fabrica", "coliseu", "lanchonete", "cabine")
FRAMES = [(b, m) for b in (False, True) for m in (0, 1)]          # (piscando?, boca aberta?)


def save(name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        pygame.image.save(screen, os.path.join(SHOTS, name + ".png"))


class SurfaceCounter:
    def __enter__(self):
        self.real = pygame.Surface
        self.n = 0
        outer = self

        class Counting(self.real):
            def __init__(self, *a, **k):
                outer.n += 1
                super().__init__(*a, **k)
        pygame.Surface = Counting
        return self

    def __exit__(self, *a):
        pygame.Surface = self.real


def snap(fn, size=(170, 190)):
    s = pygame.Surface(size)
    s.fill((20, 30, 50))
    fn(s)
    return pygame.image.tobytes(s, "RGB")


def test_story_data_is_covered():
    assert set(P._DRAWERS) == set(story.BGS)
    assert set(P._ANIMS) == set(story.BGS)                         # todo cenario tem animacao leve
    assert set(P._FRONTS) <= set(story.BGS)
    for m in NEW_MOODS:
        assert m in story.MOODS
    for b in NEW_BGS:
        assert b in story.BGS
    for cid, ch in story.CHARACTERS.items():
        assert ch["hair"][0] in story.HAIR_STYLES and ch["outfit"][0] in story.OUTFITS, cid
        for a in ch["acc"]:
            assert a in story.ACCESSORIES, (cid, a)
    for m in story.MOODS:
        assert m in P._LED, m                                       # o Ze tem LED para todo humor


def test_identity_of_current_characters_kept():
    c = story.CHARACTERS
    assert c["teo"]["hair"][0] == "espetado" and c["teo"]["outfit"] == ("moletom", (220, 50, 50))
    assert c["vivi"]["hair"][0] == "longo" and c["vivi"]["outfit"][0] == "blazer"
    assert c["kenji"]["outfit"][0] == "kimono" and c["ze"]["outfit"][0] == "robo"


def test_every_character_mood_frame_matrix_no_exception_no_surface():
    """Matriz completa: TODOS os personagens x TODOS os humores x quadros (piscar x boca)."""
    screen.fill((8, 14, 24))
    n = 0
    with SurfaceCounter() as c:
        for cid in story.CHARACTERS:
            for mood in story.MOODS:
                for blink, mouth in FRAMES:
                    for k in (1.0, 0.5):
                        P.draw_character(screen, cid, mood, 550, 470, 40, k, bob=-2, blink=blink, mouth=mouth, t=1.0)
                    P.draw_bust(screen, (46, 490, 150, 166), cid, mood, blink=blink, mouth=mouth, t=2.0)
                    P.draw_character(screen, cid, mood, 100, 100, 30, 1.0, 0, bust=True, blink=blink, mouth=mouth)
                    n += 1
                for t in (0.0, 0.13, 1.7, 3.49):                    # relogio real (falando e calado)
                    P.draw_character(screen, cid, mood, 550, 470, 40, 1.0, 0, t=t, talking=True)
                    P.draw_bust(screen, (46, 490, 150, 166), cid, mood, t=t, talking=False)
    assert c.n == 0
    assert n == len(story.CHARACTERS) * len(story.MOODS) * len(FRAMES)
    P.draw_character(screen, "inexistente", "neutro")           # id desconhecido nao quebra
    P.draw_bust(screen, (0, 0, 150, 166), "inexistente", "zzz")
    P.draw_character(screen, "teo", "humor_invalido", blink=True, mouth=1)


def test_anim_frame_blink_and_talk_are_deterministic():
    for cid in ("teo", "vivi", "ze"):
        blinks, opened = 0, 0
        prev = False
        for i in range(700):                                     # 7 s a 100 Hz
            b, m = P.anim_frame(cid, i / 100.0, talking=True)
            if b and not prev:
                blinks += 1
            prev = b
            opened += m
        assert blinks == 2, (cid, blinks)                        # 7 s / 3,5 s
        assert 300 <= opened <= 400, opened                      # boca alterna ~metade do tempo
        assert P.anim_frame(cid, 1.234, True) == P.anim_frame(cid, 1.234, True)
        assert all(P.anim_frame(cid, i / 50.0, talking=False)[1] == 0 for i in range(300))
    assert P.anim_frame("teo", None, True) == (False, 0)
    assert P._phase("teo") != P._phase("vivi")                   # piscam em momentos diferentes


def test_blink_and_mouth_frames_change_the_drawing():
    for cid in story.CHARACTERS:
        if cid == "narrador":
            continue
        for mood in story.MOODS:
            base = snap(lambda s: P.draw_bust(s, (0, 0, 170, 190), cid, mood, blink=False, mouth=0))
            talk = snap(lambda s: P.draw_bust(s, (0, 0, 170, 190), cid, mood, blink=False, mouth=1))
            assert base != talk, (cid, mood)                      # 2 quadros de fala sempre diferentes
            if mood not in P._CLOSED_EYES:
                blink = snap(lambda s: P.draw_bust(s, (0, 0, 170, 190), cid, mood, blink=True, mouth=0))
                assert base != blink, (cid, mood)


def test_moods_change_the_face():
    imgs = {}
    for mood in story.MOODS:
        s = pygame.Surface((180, 180))
        s.fill((20, 30, 50))
        P.draw_character(s, "vivi", mood, 90, 90, 46, 1.0, 0, bust=True)
        imgs[mood] = pygame.image.tobytes(s, "RGB")
    distinct = len(set(imgs.values()))
    assert distinct >= len(story.MOODS) - 2, distinct          # neutro=robo e convencida=convencido em humanos
    robo = {}
    for mood in story.MOODS:
        robo[mood] = snap(lambda s: P.draw_bust(s, (0, 0, 170, 190), "ze", mood))
    for m in NEW_MOODS:
        assert robo[m] != robo["neutro"], m


def test_new_styles_draw_and_differ():
    base = {"name": "X", "color": (90, 160, 255), "skin": (225, 185, 150), "hair": ("curto", (60, 40, 30)),
            "acc": [], "outfit": ("camiseta", (60, 120, 200))}
    ref = snap(lambda s: P.draw_look(s, base, "neutro", 85, 185, 24))
    news = [("hair", (h, (60, 40, 30))) for h in ("trancas", "coque", "moicano")]
    news += [("outfit", (o, (60, 120, 200))) for o in ("avental", "colete")]
    news += [("acc", [a]) for a in ("bone", "bengala", "avental", "tiara", "cachecol")]
    for key, val in news:
        ch = dict(base)
        ch[key] = val
        assert val[0] in (story.HAIR_STYLES + story.OUTFITS + story.ACCESSORIES)
        surf = pygame.Surface((170, 190))
        surf.fill((20, 30, 50))
        with SurfaceCounter() as c:
            P.draw_look(surf, ch, "feliz", 85, 180, 24, blink=True, mouth=1, t=1.0)
            P.draw_look(surf, ch, "neutro", 85, 60, 30, bust=True)
        assert c.n == 0
        full = snap(lambda s: P.draw_look(s, ch, "neutro", 85, 185, 24))
        assert full != ref, (key, val)
    every = dict(base, hair=("moicano", (200, 60, 90)), outfit=("colete", (80, 60, 120)),
                 acc=list(story.ACCESSORIES))                       # tudo junto nao quebra
    snap(lambda s: P.draw_look(s, every, "euforico", 85, 470, 24, blink=True, mouth=1, t=2.0))


def test_dimmed_is_darker():
    a = pygame.Surface((200, 300))
    b = pygame.Surface((200, 300))
    P.draw_character(a, "teo", "neutro", 100, 280, 30, 1.0)
    P.draw_character(b, "teo", "neutro", 100, 280, 30, 0.5)
    assert pygame.transform.average_color(b)[0] < pygame.transform.average_color(a)[0]


def test_every_background_draws_and_is_cached_once():
    for bg in story.BGS:
        s = P.get_background(bg)
        assert s.get_size() == (P.STAGE_W, P.STAGE_H)
        with SurfaceCounter() as c:
            assert P.get_background(bg) is s
            screen.blit(s, (0, 0))
            P.get_foreground(bg)
        assert c.n == 0
        assert len(P._BG_CACHE) <= P.BG_CACHE_MAX
    unk = pygame.Surface((P.STAGE_W, P.STAGE_H))
    P.draw_background(unk, "nao_existe")
    P.draw_scene_anim(unk, "nao_existe", 1.0)
    P.draw_foreground(unk, "nao_existe")


def test_backgrounds_are_distinct():
    sig = {}
    for bg in story.BGS:
        s = P.get_background(bg)
        key = tuple(s.get_at((x, y))[:3] for x in range(50, 1100, 150) for y in range(30, 470, 90))
        assert key not in sig.values(), bg
        sig[bg] = key


def test_every_background_animates_n_frames_zero_surface():
    """Todos os cenarios (antigos e novos) por 180 quadros com animacao e frente: zero Surface
    depois do aquecimento (get_background) e a animacao muda a imagem ao longo do tempo."""
    for bg in story.BGS:
        P.get_background(bg)                                    # aquecimento (build + sprites + frente)
        imgs = set()
        with SurfaceCounter() as c:
            for i in range(180):
                t = i / 60.0
                screen.blit(P.get_background(bg), (0, 0))
                P.draw_scene_anim(screen, bg, t)
                P.draw_character(screen, "teo", "feliz", 550, 466, 40, 1.0, 0, t=t, talking=True)
                P.draw_foreground(screen, bg)
                if i % 45 == 0:
                    imgs.add(pygame.image.tobytes(screen.subsurface((0, 0, P.STAGE_W, P.STAGE_H)), "RGB"))
        assert c.n == 0, (bg, c.n)
        assert len(imgs) >= 2, bg                                # algo se mexe


def test_foreground_is_small_and_at_the_corners():
    for bg in story.BGS:
        fg = P.get_foreground(bg)
        if fg is None:
            continue
        surf, (x, y) = fg
        w, h = surf.get_size()
        assert y >= 250 and y + h <= P.STAGE_H, bg               # so a parte de baixo do palco
        mid = pygame.Rect(190, 0, 720, P.STAGE_H)                 # nao cobre o centro (onde ficam os personagens)
        for px in range(mid.x, mid.right, 20):
            for py in range(max(y, 300), y + h, 10):
                if x <= px < x + w:
                    assert surf.get_at((px - x, py - y))[:3] == P.KEY, (bg, px, py)


def test_background_build_time():
    out = {}
    for bg in story.BGS:
        s = pygame.Surface((P.STAGE_W, P.STAGE_H))
        t0 = time.perf_counter()
        P.draw_background(s, bg)
        out[bg] = (time.perf_counter() - t0) * 1000
    print("build_ms:", {k: round(v, 1) for k, v in out.items()})
    for k, v in out.items():
        if v > 60:
            print("AVISO: build de cenario lento (informativo):", k, round(v, 1), "ms")
        assert v < 400, (k, v)


def test_lru_keeps_at_most_n_backgrounds():
    for bg in story.BGS:
        P.get_background(bg)
    assert len(P._BG_CACHE) == P.BG_CACHE_MAX
    assert list(P._BG_CACHE)[-1] == story.BGS[-1]
    first = story.BGS[0]
    assert first not in P._BG_CACHE and first not in P._FG_CACHE      # descartado junto com a frente


def test_dialog_like_frame_draw_time():
    out = {}
    for bg in story.BGS:
        P.get_background(bg)
        for i in range(5):
            screen.blit(P.get_background(bg), (0, 0))
        t0 = time.perf_counter()
        for i in range(100):
            t = i / 60.0
            screen.blit(P.get_background(bg), (0, 0))
            P.draw_scene_anim(screen, bg, t)
            for j, cid in enumerate(("teo", "vivi", "ze")):
                P.draw_character(screen, cid, "feliz", 190 + j * 360, 466, 40, 1.0 if j == 1 else 0.5, 0,
                                 t=t, talking=j == 1)
            P.draw_foreground(screen, bg)
            P.draw_bust(screen, (46, 490, 150, 166), "vivi", "euforico", t=t, talking=True)
        out[bg] = (time.perf_counter() - t0) / 100 * 1000
    print("dialog_ms:", {k: round(v, 2) for k, v in out.items()})
    for k, v in out.items():
        if v >= 3.0:
            print("AVISO: dialogo lento (informativo):", k, round(v, 2), "ms")
        assert v < 25.0, (k, v)


def test_screenshots():
    if not SHOTS:
        return
    screen.fill((8, 14, 24))
    for i, c in enumerate(story.CHARACTERS):
        P.draw_bust(screen, ((i % 6) * 180 + 10, (i // 6) * 190 + 10, 170, 170), c, NEW_MOODS[i % len(NEW_MOODS)])
    for i, c in enumerate(story.CHARACTERS):
        P.draw_character(screen, c, "neutro", 60 + i * 90, 690, 17)
    save("portraits_grid")
    screen.fill((8, 14, 24))
    for i, m in enumerate(story.MOODS):
        cid = ("teo", "vivi", "bia", "ze")[i % 4]
        P.draw_bust(screen, ((i % 8) * 136 + 6, (i // 8) * 176 + 6, 130, 150), cid, m, t=0.5)
    save("portraits_moods")
    screen.fill((8, 14, 24))
    for row, cid in enumerate(("teo", "helena", "ze")):
        for col, (b, m, lab) in enumerate(((False, 0, "aberto"), (True, 0, "piscando"), (False, 0, "fala 1"),
                                           (False, 1, "fala 2"))):
            P.draw_bust(screen, (20 + col * 270, 20 + row * 225, 190, 210), cid, "neutro",
                        blink=b, mouth=m)
    save("portraits_blink_talk")
    screen.fill((8, 14, 24))
    base = {"name": "X", "color": (90, 160, 255), "skin": (225, 185, 150), "hair": ("curto", (60, 40, 30)),
            "acc": [], "outfit": ("camiseta", (60, 120, 200))}
    looks = [dict(base, hair=("trancas", (40, 30, 30))), dict(base, hair=("coque", (120, 60, 40)), acc=["tiara"]),
             dict(base, hair=("moicano", (230, 60, 110)), acc=["bone"]),
             dict(base, hair=("calvo", (200, 200, 200)), acc=["bengala", "cachecol", "bigode"], outfit=("colete", (90, 60, 50))),
             dict(base, outfit=("avental", (200, 60, 70))), dict(base, acc=["avental"], outfit=("camiseta", (70, 70, 80)))]
    for i, ch in enumerate(looks):
        P.draw_look(screen, ch, NEW_MOODS[i], 100 + i * 180, 460, 34)
        P.draw_look(screen, ch, "neutro", 100 + i * 180, 580, 44, bust=True)
    save("portraits_new_styles")
    cols = 4
    rows = (len(story.BGS) + cols - 1) // cols
    sw, sh = 1100 // cols, int(1100 // cols * P.STAGE_H / P.STAGE_W)
    big = pygame.Surface((P.STAGE_W, P.STAGE_H))
    sheet = pygame.Surface((1100, rows * (sh + 2)))
    for i, b in enumerate(story.BGS):
        big.blit(P.get_background(b), (0, 0))
        P.draw_scene_anim(big, b, 1.3)
        P.draw_foreground(big, b)
        sheet.blit(pygame.transform.smoothscale(big, (sw, sh)), ((i % cols) * sw, (i // cols) * (sh + 2)))
    pygame.image.save(sheet, os.path.join(SHOTS, "backgrounds_collage.png"))


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items(), key=lambda kv: kv[1].__code__.co_firstlineno
                                       if callable(kv[1]) and hasattr(kv[1], "__code__") else 0)
             if k.startswith("test_")]
    for k, t in tests:
        t()
        print("ok", k)
    print(len(tests), "testes passaram")
