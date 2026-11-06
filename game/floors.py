# -*- coding: utf-8 -*-
"""Pisos do campo: o "neon" original e pisos de casa (cozinha, tacos, porcelanato, ladrilho
hidraulico, cimento queimado). Afinal, sao robos aspiradores jogando bola dentro de casa.

Desenho so no inicio da partida (Game.build_arena), por pygame.draw, com RNG proprio por piso
(semente fixa: o mesmo piso sai sempre igual). Os pisos claros recebem um veu escuro para a bola
branca, os robos e as linhas neon continuarem legiveis.
"""
import random

import pygame

FLOORS = ("neon", "cozinha", "tacos", "porcelanato", "hidraulico", "cimento")
LABELS = {"neon": "ARENA NEON", "cozinha": "PISO DE COZINHA", "tacos": "TACOS DE MADEIRA",
          "porcelanato": "PORCELANATO", "hidraulico": "LADRILHO HIDRÁULICO", "cimento": "CIMENTO QUEIMADO"}
VEIL = {"cozinha": 120, "tacos": 95, "porcelanato": 125, "hidraulico": 115, "cimento": 105}
SEEDS = {f: 9100 + i for i, f in enumerate(FLOORS)}


def _jit(c, rng, k):
    """Variacao de tom (mesmo deslocamento nos 3 canais: clareia/escurece sem mudar a cor)."""
    d = rng.uniform(-k, k)
    return tuple(max(0, min(255, int(v + d))) for v in c)


def _cozinha(s, r, rng):
    """Xadrez preto e creme de cozinha antiga, rejunte fino."""
    t = 40
    light, dark = (214, 206, 186), (46, 50, 60)
    for j, y in enumerate(range(r.top, r.bottom, t)):
        for i, x in enumerate(range(r.left, r.right, t)):
            base = light if (i + j) % 2 == 0 else dark
            pygame.draw.rect(s, _jit(base, rng, 6), (x, y, t, t))
    for x in range(r.left, r.right + 1, t):
        pygame.draw.line(s, (120, 116, 108), (x, r.top), (x, r.bottom))
    for y in range(r.top, r.bottom + 1, t):
        pygame.draw.line(s, (120, 116, 108), (r.left, y), (r.right, y))


def _tacos(s, r, rng):
    """Tacos de madeira em fileiras com emendas desencontradas e veios."""
    h = 20
    browns = ((150, 96, 52), (166, 108, 60), (134, 84, 44), (176, 120, 70), (122, 76, 40))
    for y in range(r.top, r.bottom, h):
        x = r.left - rng.randrange(0, 120)
        while x < r.right:
            w = rng.randrange(90, 210)
            c = _jit(rng.choice(browns), rng, 8)
            rect = pygame.Rect(x, y, w, h).clip(r)
            if rect.w > 0:
                pygame.draw.rect(s, c, rect)
                for _ in range(2):                  # veios
                    vy = rect.top + rng.randrange(3, h - 3)
                    pygame.draw.line(s, tuple(int(v * 0.85) for v in c), (rect.left + 4, vy),
                                     (rect.right - 4, vy + rng.choice((-1, 0, 1))))
                pygame.draw.line(s, (70, 42, 22), rect.topleft, (rect.left, rect.bottom - 1))
            x += w
        pygame.draw.line(s, (78, 48, 26), (r.left, y), (r.right, y))


def _porcelanato(s, r, rng):
    """Placas grandes bege-acinzentadas, rejunte claro e um leve brilho diagonal."""
    t = 80
    for y in range(r.top, r.bottom, t):
        for x in range(r.left, r.right, t):
            pygame.draw.rect(s, _jit((178, 170, 158), rng, 7), (x, y, t, t))
            for k in range(3):                      # brilho
                pygame.draw.line(s, (196, 190, 180), (x + 10 + k * 6, y + t - 10), (x + t - 10, y + 10 + k * 6))
    for x in range(r.left, r.right + 1, t):
        pygame.draw.line(s, (222, 218, 210), (x, r.top), (x, r.bottom), 2)
    for y in range(r.top, r.bottom + 1, t):
        pygame.draw.line(s, (222, 218, 210), (r.left, y), (r.right, y), 2)


def _hidraulico(s, r, rng):
    """Ladrilho hidraulico: quartos de circulo nos cantos formam flores entre 4 ladrilhos."""
    t = 40
    base, petal, core, ring = (214, 200, 170), (180, 82, 58), (40, 110, 110), (150, 140, 120)
    sub = pygame.Surface((t, t)).convert()
    sub.fill(base)
    for cx, cy in ((0, 0), (t, 0), (0, t), (t, t)):
        pygame.draw.circle(sub, petal, (cx, cy), t // 2 - 2)
        pygame.draw.circle(sub, core, (cx, cy), t // 5)
    pygame.draw.circle(sub, ring, (t // 2, t // 2), t // 6, 2)
    pygame.draw.rect(sub, ring, (t // 2 - 2, t // 2 - 2, 4, 4))
    for y in range(r.top, r.bottom, t):
        for x in range(r.left, r.right, t):
            s.blit(sub, (x, y))
    for x in range(r.left, r.right + 1, t):
        pygame.draw.line(s, (170, 160, 140), (x, r.top), (x, r.bottom))
    for y in range(r.top, r.bottom + 1, t):
        pygame.draw.line(s, (170, 160, 140), (r.left, y), (r.right, y))


def _cimento(s, r, rng):
    """Cimento queimado: cinza manchado, pintas, juntas de dilatacao e umas trincas."""
    pygame.draw.rect(s, (138, 140, 142), r)
    for _ in range(90):                             # manchas
        c = _jit((138, 140, 142), rng, 14)
        rad = rng.randrange(14, 50)
        pygame.draw.circle(s, c, (rng.randrange(r.left, r.right), rng.randrange(r.top, r.bottom)), rad)
    for _ in range(2600):                           # pintas
        c = _jit((120, 122, 124), rng, 30)
        s.set_at((rng.randrange(r.left, r.right), rng.randrange(r.top, r.bottom)), c)
    pygame.draw.rect(s, (110, 112, 114), r, 3)      # rodape
    for x in range(r.left + 140, r.right, 140):     # juntas
        pygame.draw.line(s, (96, 98, 100), (x, r.top), (x, r.bottom), 2)
    for y in range(r.top + 140, r.bottom, 140):
        pygame.draw.line(s, (96, 98, 100), (r.left, y), (r.right, y), 2)
    for _ in range(5):                              # trincas
        x, y = rng.randrange(r.left, r.right), rng.randrange(r.top, r.bottom)
        for _ in range(rng.randrange(4, 9)):
            nx, ny = x + rng.randrange(-24, 25), y + rng.randrange(-24, 25)
            pygame.draw.line(s, (92, 92, 94), (x, y), (nx, ny))
            x, y = nx, ny


DRAW = {"cozinha": _cozinha, "tacos": _tacos, "porcelanato": _porcelanato, "hidraulico": _hidraulico,
        "cimento": _cimento}


def draw(s, floor, rect):
    """Pinta o piso `floor` (exceto "neon", feito pelo jogo) dentro de `rect` e escurece com o veu."""
    fn = DRAW.get(floor)
    if fn is None:
        return False
    r = pygame.Rect(rect)
    clip = s.get_clip()
    s.set_clip(r)                                   # nada vaza para fora do campo
    try:
        fn(s, r, random.Random(SEEDS[floor]))
    finally:
        s.set_clip(clip)
    veil = pygame.Surface(r.size, pygame.SRCALPHA)
    veil.fill((6, 10, 24, VEIL[floor]))
    s.blit(veil, r.topleft)
    return True


def pick(rng, last=None):
    """Sorteia um piso diferente do anterior."""
    opts = [f for f in FLOORS if f != last]
    return rng.choice(opts)
