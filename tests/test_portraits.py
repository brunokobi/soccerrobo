"""Testes dos retratos e cenarios por codigo (game/portraits.py). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_portraits.py
Screenshots (grade de retratos, matriz de humores, colagem de cenarios) so se SOCCERPY_SHOTS_DIR estiver definido.
"""
import os
import sys

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


def test_story_data_is_covered():
    assert set(P._DRAWERS) == set(story.BGS)
    for cid, ch in story.CHARACTERS.items():
        assert ch["hair"][0] in story.HAIR_STYLES and ch["outfit"][0] in story.OUTFITS, cid
        for a in ch["acc"]:
            assert a in story.ACCESSORIES, (cid, a)


def test_every_character_mood_full_body_and_bust_no_exception_no_surface():
    screen.fill((8, 14, 24))
    with SurfaceCounter() as c:
        for cid in story.CHARACTERS:
            for mood in story.MOODS:
                for k in (1.0, 0.5):
                    P.draw_character(screen, cid, mood, 550, 470, 40, k, bob=-2)
                P.draw_bust(screen, (46, 490, 150, 166), cid, mood)
                P.draw_character(screen, cid, mood, 100, 100, 30, 1.0, 0, bust=True)
    assert c.n == 0
    P.draw_character(screen, "inexistente", "neutro")           # id desconhecido nao quebra
    P.draw_bust(screen, (0, 0, 150, 166), "inexistente", "zzz")
    P.draw_character(screen, "teo", "humor_invalido")


def test_every_background_draws_and_is_cached_once():
    for bg in story.BGS:
        s = P.get_background(bg)
        assert s.get_size() == (P.STAGE_W, P.STAGE_H)
        with SurfaceCounter() as c:
            assert P.get_background(bg) is s
            screen.blit(s, (0, 0))
        assert c.n == 0
    unk = pygame.Surface((P.STAGE_W, P.STAGE_H))
    P.draw_background(unk, "nao_existe")


def test_backgrounds_are_distinct():
    sig = {}
    for bg in story.BGS:
        s = P.get_background(bg)
        key = tuple(s.get_at((x, y))[:3] for x in range(50, 1100, 150) for y in range(30, 470, 90))
        assert key not in sig.values(), bg
        sig[bg] = key


def test_moods_change_the_face():
    imgs = {}
    for mood in story.MOODS:
        s = pygame.Surface((160, 160))
        s.fill((20, 30, 50))
        P.draw_character(s, "vivi", mood, 80, 80, 46, 1.0, 0, bust=True)
        imgs[mood] = pygame.image.tobytes(s, "RGB")
    distinct = len(set(imgs.values()))
    assert distinct >= len(story.MOODS) - 2, distinct          # "neutro" e "robo" coincidem em humanos


def test_dimmed_is_darker():
    a = pygame.Surface((200, 300))
    b = pygame.Surface((200, 300))
    P.draw_character(a, "teo", "neutro", 100, 280, 30, 1.0)
    P.draw_character(b, "teo", "neutro", 100, 280, 30, 0.5)
    assert pygame.transform.average_color(b)[0] < pygame.transform.average_color(a)[0]


def test_screenshots():
    if not SHOTS:
        return
    screen.fill((8, 14, 24))
    for i, c in enumerate(story.CHARACTERS):
        P.draw_bust(screen, ((i % 6) * 180 + 10, (i // 6) * 190 + 10, 170, 170), c, "neutro")
    save("portraits_grid")
    screen.fill((8, 14, 24))
    for i, m in enumerate(story.MOODS):
        P.draw_bust(screen, ((i % 7) * 150 + 10, (i // 7) * 170 + 10, 140, 140), "teo" if i < 7 else "vivi", m)
    save("portraits_moods")
    screen.fill((8, 14, 24))
    for i, b in enumerate(story.BGS):
        screen.blit(pygame.transform.smoothscale(P.get_background(b), (366, 159)), ((i % 3) * 367, (i // 3) * 165))
    save("backgrounds_collage")


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items(), key=lambda kv: kv[1].__code__.co_firstlineno
                                       if callable(kv[1]) and hasattr(kv[1], "__code__") else 0)
             if k.startswith("test_")]
    for k, t in tests:
        t()
        print("ok", k)
    print(len(tests), "testes passaram")
