# -*- coding: utf-8 -*-
"""Desenho por codigo dos CENARIOS e RETRATOS da Campanha (passo 9; Fase 4 A12/A13). Modulo de
desenho PURO (so pygame.draw; nenhuma imagem externa; nenhuma Surface criada por quadro).

Cenarios (A13)
- Cada cenario tem camadas: fundo distante (ceu, cidade, estadio ao longe), meio (moveis, paredes,
  arquibancadas) e luz (feixes/brilhos aditivos e vinheta), tudo composto UMA vez numa Surface
  estatica (get_background, cache LRU de BG_CACHE_MAX cenarios).
- Frente (get_foreground / draw_foreground): pecas nos cantos (plantas, caixas, tambores) numa 2a
  Surface pequena com colorkey, blitada DEPOIS dos personagens (profundidade; +1 blit).
- Animacao leve (draw_scene_anim): luzes piscando (2 quadros de brilho aditivo pre-renderizado),
  telao, bandeirinhas, poeira, bolhas, esteiras... so pygame.draw e blits de sprites ja prontos
  (o aquecimento acontece em get_background).
Personagens (A12)
- draw_character() (corpo inteiro, no palco) e draw_bust() (retrato da caixa de dialogo). Humores
  em story.MOODS (inclui determinado, maravilhado, malicioso, sonolento, chorando, gritando,
  piscando, euforico). `k` (0..1) escurece as cores (personagens "esmaecidos") sem alpha.
- Animacao por relogio passado pela UI (t em segundos, sem RNG): piscar a cada BLINK_PERIOD s
  (BLINK_DUR s, fase por personagem), boca em 2 quadros (TALK_FRAME s) durante a fala, respiracao
  de 1 px. Quadros explicitos: blink=True/False, mouth=0/1.
- "ze" (Ze Poeira) e roupas "robo" viram robo-aspirador (LED por humor, pisca e "fala" pelo LED);
  "narrador" vira moldura/icone de narracao.
Dados vem de story.CHARACTERS / HAIR_STYLES / ACCESSORIES / OUTFITS / MOODS / BGS.
"""
import math
import os
import random
from collections import OrderedDict

import pygame

import story

STAGE_W, STAGE_H = 1100, 478          # area do palco (acima da caixa de dialogo)
NEON = (0, 230, 255)
GOLD = (255, 214, 90)
INK = (30, 24, 40)
WHITE = (250, 250, 255)
SHADE_BASE = (10, 16, 30)
PANTS = (28, 36, 64)
MOUTH = (120, 40, 50)
TONGUE = (235, 110, 125)
TEAR = (120, 200, 255)
KEY = (255, 0, 255)                   # colorkey da camada de frente

BLINK_PERIOD = 3.5                    # s entre piscadas
BLINK_DUR = 0.12                      # s de olho fechado
TALK_FRAME = 0.12                     # s por quadro de boca durante a fala
BG_CACHE_MAX = 6                      # LRU de cenarios (cada um ~2 MB)
# Estilo dos personagens: "classico" (formas lisas, desenhado por quadro) ou "pixel" (prototipo em
# pixel art com cache, game/portraits_pixel.py; so os personagens de portraits_pixel.SPECS - os demais
# continuam no classico). SOCCERPY_PORTRAITS=pixel liga o prototipo sem mexer no codigo.
STYLE = os.environ.get("SOCCERPY_PORTRAITS", "classico")


# ---------------------------------------------------------------------------------- cores
def shade(c, k):
    """Mistura c com o fundo escuro: k=1 cor original, k=0 fundo."""
    if k >= 0.999:
        return (c[0], c[1], c[2])
    b = SHADE_BASE
    return (int(b[0] + (c[0] - b[0]) * k), int(b[1] + (c[1] - b[1]) * k), int(b[2] + (c[2] - b[2]) * k))


def lerp(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def darker(c, f=0.78):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))


def lighter(c, f=0.25):
    return (int(c[0] + (255 - c[0]) * f), int(c[1] + (255 - c[1]) * f), int(c[2] + (255 - c[2]) * f))


def scale(c, f):
    return (min(255, int(c[0] * f)), min(255, int(c[1] * f)), min(255, int(c[2] * f)))


# ================================================================================ PRIMITIVAS
def _vgrad(s, rect, c1, c2):
    x, y, w, h = rect
    for i in range(h):
        pygame.draw.line(s, lerp(c1, c2, i / max(1, h - 1)), (x, y + i), (x + w - 1, y + i))


def _hgrad(s, rect, c1, c2):
    x, y, w, h = rect
    for i in range(w):
        pygame.draw.line(s, lerp(c1, c2, i / max(1, w - 1)), (x + i, y), (x + i, y + h - 1))


def _glow(s, center, r, col, base, steps=7):
    """Brilho redondo por circulos concentricos opacos (sem alpha)."""
    for i in range(steps):
        t = i / (steps - 1.0)
        pygame.draw.circle(s, lerp(base, col, t * t), center, int(r * (1 - t * 0.85)))


_SPRITES = {}                          # sprites pequenos pre-renderizados (brilhos, placas, quadros)


def glow_sprite(r, col, steps=8):
    """Brilho radial sobre preto para blit com BLEND_RGB_ADD (criado uma vez por (r, cor))."""
    key = ("glow", r, col, steps)
    sp = _SPRITES.get(key)
    if sp is None:
        sp = pygame.Surface((2 * r, 2 * r))
        sp.fill((0, 0, 0))
        for i in range(steps):
            t = i / (steps - 1.0)
            pygame.draw.circle(sp, scale(col, 0.06 + 0.94 * t * t), (r, r), max(1, int(r * (1 - 0.9 * t))))
        _SPRITES[key] = sp
    return sp


def _sprite(key, size, painter, colorkey=None):
    """Sprite generico cacheado: painter(surface) desenha uma vez."""
    sp = _SPRITES.get(key)
    if sp is None:
        sp = pygame.Surface(size)
        sp.fill(colorkey if colorkey is not None else (0, 0, 0))
        painter(sp)
        if colorkey is not None:
            sp.set_colorkey(colorkey)
        _SPRITES[key] = sp
    return sp


def _add(scr, sp, center):
    w, h = sp.get_size()
    scr.blit(sp, (int(center[0] - w // 2), int(center[1] - h // 2)), special_flags=pygame.BLEND_RGB_ADD)


def _add_glow(s, center, r, col, steps=8):
    _add(s, glow_sprite(r, col, steps), center)


def _ellipse_glow(s, rect, col):
    """Brilho eliptico (reflexo no chao) - so no build."""
    x, y, w, h = [int(v) for v in rect]
    sp = pygame.transform.smoothscale(glow_sprite(64, col), (max(2, w), max(2, h)))
    s.blit(sp, (x, y), special_flags=pygame.BLEND_RGB_ADD)


def _cone(s, top, bottom, w_top, w_bot, col, steps=5, fade=0.12):
    """Feixe de luz aditivo de top=(x,y) ate bottom=(x,y), mais forte no eixo e no alto (so no build)."""
    tx, ty = top
    bx, by = bottom
    x0 = int(min(tx - w_top, bx - w_bot))
    x1 = int(max(tx + w_top, bx + w_bot)) + 1
    y0, y1 = int(ty), int(by) + 1
    w, h = max(2, x1 - x0), max(2, y1 - y0)
    tmp = pygame.Surface((w, h))
    tmp.fill((0, 0, 0))
    for i in range(steps):
        f = 1.0 - i / float(steps)
        c = scale(col, (i + 1) / float(steps))
        pts = [(tx - w_top * f - x0, 0), (tx + w_top * f - x0, 0), (bx + w_bot * f - x0, h - 1), (bx - w_bot * f - x0, h - 1)]
        pygame.draw.polygon(tmp, c, pts)
    g = pygame.Surface((w, h))
    v = int(255 * fade)
    _vgrad(g, (0, 0, w, h), (255, 255, 255), (v, v, v))
    tmp.blit(g, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    s.blit(tmp, (x0, y0), special_flags=pygame.BLEND_RGB_ADD)


_VIGN = {}


def _vignette(s, strength=0.5):
    """Escurece as bordas (multiplicativo; Surface criada uma vez por intensidade)."""
    v = _VIGN.get(strength)
    if v is None:
        v = pygame.Surface((STAGE_W, STAGE_H))
        hz = pygame.Surface((STAGE_W, STAGE_H))
        v.fill((255, 255, 255))
        hz.fill((255, 255, 255))
        band = 220
        for i in range(band):
            f = 1.0 - strength * (1.0 - i / float(band)) ** 2
            c = (int(255 * f),) * 3
            pygame.draw.line(v, c, (i, 0), (i, STAGE_H))
            pygame.draw.line(v, c, (STAGE_W - 1 - i, 0), (STAGE_W - 1 - i, STAGE_H))
        bh = 130
        for i in range(bh):
            f = 1.0 - strength * 0.8 * (1.0 - i / float(bh)) ** 2
            c = (int(255 * f),) * 3
            pygame.draw.line(hz, c, (0, i), (STAGE_W, i))
        v.blit(hz, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        _VIGN[strength] = v
    s.blit(v, (0, 0), special_flags=pygame.BLEND_RGB_MULT)


def _star4(scr, col, x, y, r):
    r = max(2, r)
    q = r * 0.28
    pygame.draw.polygon(scr, col, [(x, y - r), (x + q, y - q), (x + r, y), (x + q, y + q), (x, y + r),
                                   (x - q, y + q), (x - r, y), (x - q, y - q)])


def _stars(s, rng, n, y1, x0=0, x1=STAGE_W, col=(170, 190, 230), base=(40, 50, 80)):
    for _ in range(n):
        pygame.draw.circle(s, lerp(base, col, rng.random()), (rng.randint(x0, x1 - 1), rng.randint(0, y1)), 1)


def _skyline(s, rng, x0, x1, base, hmin, hmax, col, win_col, win_p=0.22):
    x = x0
    while x < x1:
        w = rng.randint(28, 70)
        h = rng.randint(hmin, hmax)
        pygame.draw.rect(s, col, (x, base - h, w, h))
        if rng.random() < 0.25:
            pygame.draw.line(s, col, (x + w // 2, base - h), (x + w // 2, base - h - rng.randint(8, 22)), 2)
        for wy in range(base - h + 6, base - 5, 9):
            for wx in range(x + 4, x + w - 5, 8):
                if rng.random() < win_p:
                    pygame.draw.rect(s, win_col, (wx, wy, 3, 4))
        x += w + rng.randint(0, 6)


def _catenary(s, a, b, sag, col, w=2, n=14):
    pts = []
    for i in range(n + 1):
        t = i / float(n)
        pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t + sag * 4 * t * (1 - t)))
    pygame.draw.lines(s, col, False, pts, w)


# ---- fonte de pixels 5x5 (letreiros desenhados por codigo; so Latin-1 maiusculo)
_FONT5 = {
    "A": (".###.", "#...#", "#####", "#...#", "#...#"), "B": ("####.", "#...#", "####.", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", ".####"), "D": ("####.", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "####.", "#....", "#####"), "F": ("#####", "#....", "####.", "#....", "#...."),
    "G": (".####", "#....", "#..##", "#...#", ".###."),
    "H": ("#...#", "#...#", "#####", "#...#", "#...#"), "I": ("#####", "..#..", "..#..", "..#..", "#####"),
    "K": ("#...#", "#..#.", "###..", "#..#.", "#...#"), "L": ("#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#"), "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", ".###."), "P": ("####.", "#...#", "####.", "#....", "#...."),
    "R": ("####.", "#...#", "####.", "#..#.", "#...#"), "S": (".####", "#....", ".###.", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#.."), "U": ("#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", ".#.#.", "..#.."), "X": ("#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", ".#.#.", "..#..", "..#..", "..#.."), "Z": ("#####", "...#.", "..#..", ".#...", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", ".###."), "1": ("..#..", ".##..", "..#..", "..#..", ".###."),
    "2": ("####.", "....#", ".###.", "#....", "#####"), "3": ("####.", "....#", ".###.", "....#", "####."),
    "4": ("#..#.", "#..#.", "#####", "...#.", "...#."), "5": ("#####", "#....", "####.", "....#", "####."),
    "6": (".###.", "#....", "####.", "#...#", ".###."), "7": ("#####", "....#", "...#.", "..#..", "..#.."),
    "8": (".###.", "#...#", ".###.", "#...#", ".###."), "9": (".###.", "#...#", ".####", "....#", ".###."),
    ":": (".....", "..#..", ".....", "..#..", "....."), "-": (".....", ".....", ".###.", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", ".....", "..#.."),
}


def pixtext_w(text, px, gap=1):
    return max(0, len(text) * (5 + gap) * px - gap * px)


def _pixtext(s, text, x, y, px, col, gap=1):
    cx = x
    for chr_ in text:
        g = _FONT5.get(chr_)
        if g is not None:
            for r, row in enumerate(g):
                for c, v in enumerate(row):
                    if v == "#":
                        pygame.draw.rect(s, col, (cx + c * px, y + r * px, px, px))
        cx += (5 + gap) * px
    return cx


# ---- animacao: helpers SEM Surface (pygame.draw / blit de sprite cacheado)
def _motes(scr, t, rect, n, col, seed=0, speed=9.0):
    """Poeira/vagalumes flutuando (n pontos com seno; deterministico pelo relogio)."""
    x, y, w, h = rect
    dim = darker(col, 0.55)
    for i in range(n):
        a = ((i * 7919 + seed * 104729) % 1000) / 1000.0
        b = ((i * 3571 + seed * 7717) % 1000) / 1000.0
        px = x + int(a * w + 10 * math.sin(t * 0.7 + i * 1.7))
        py = y + h - int((b * h + t * speed * (0.6 + 0.1 * (i % 5))) % h)
        pygame.draw.circle(scr, col if i % 3 else dim, (px, py), 2 if i % 4 == 0 else 1)


def _flashes(scr, t, pts, rate=0.9, duty=0.07, col=(255, 255, 255)):
    """Flashes de camera/luzinhas: cada ponto acende uma vez por ciclo em fase propria."""
    for i, (x, y) in enumerate(pts):
        ph = (t * rate * (1.0 + (i % 3) * 0.17) + i * 0.618) % 1.0
        if ph < duty:
            r = 5 if ph < duty * 0.5 else 3
            pygame.draw.line(scr, col, (x - r, y), (x + r, y), 1)
            pygame.draw.line(scr, col, (x, y - r), (x, y + r), 1)
            pygame.draw.circle(scr, col, (x, y), 2)


def _blink(t, period, duty, phase=0.0):
    return ((t + phase) % period) < duty * period


def _pts(seed, n, rect):
    rng = random.Random(seed)
    x, y, w, h = rect
    return [(x + rng.randint(0, w), y + rng.randint(0, h)) for _ in range(n)]


# ================================================================================ TORCEDORES
# TODO(A13/crowd): unificar com o atomo de espectador de game/crowd.py quando ele estiver pronto
# (hoje desenho proprio equivalente para nao acoplar com o trabalho em paralelo na torcida).
_SKINS = ((240, 200, 160), (215, 170, 130), (170, 120, 85), (110, 75, 55))
_HAIRS = ((40, 30, 25), (90, 60, 35), (20, 20, 25), (200, 170, 90), (150, 60, 40), (170, 170, 175))
_SHIRTS = ((220, 70, 70), (70, 130, 230), (240, 200, 80), (90, 210, 140), (190, 110, 230), (235, 235, 240),
           (255, 140, 60), (0, 200, 230))


def _spectator(s, x, base, h, rng, fade, bgc, shirts=_SHIRTS):
    """Torcedor estatico de altura h com os pes/assento em `base`; fade 0..1 = profundidade."""
    def f(c):
        return lerp(bgc, c, fade)
    skin = f(rng.choice(_SKINS))
    shirt_raw = rng.choice(shirts)
    shirt = f(shirt_raw)
    hair = f(rng.choice(_HAIRS))
    hr = max(2, int(h * 0.17))
    hy = base - int(h * 0.7)
    tw = max(4, int(h * 0.5))
    ty = base - int(h * 0.48)
    roll = rng.random()
    if roll < 0.035:                                        # faixa/cachecol erguido
        for sx in (-1, 1):
            pygame.draw.line(s, shirt, (x + sx * tw // 2, ty + 2), (x + sx * int(h * 0.4), hy - hr * 2), max(1, h // 10))
        pygame.draw.rect(s, f(lighter(shirt_raw, 0.2)), (x - int(h * 0.48), hy - hr * 2 - max(2, h // 6),
                                                         int(h * 0.96), max(3, h // 5)))
    elif roll < 0.13:                                       # bracos para cima
        for sx in (-1, 1):
            ex = x + sx * int(h * 0.34)
            pygame.draw.line(s, shirt, (x + sx * (tw // 2 - 1), ty + 2), (ex, hy - hr - 2), max(1, h // 9))
            pygame.draw.circle(s, skin, (ex, hy - hr - 3), max(1, h // 12))
    style = rng.randrange(5)
    if style == 1:                                          # cabelo comprido (atras)
        pygame.draw.rect(s, hair, (x - hr - 1, hy - hr, 2 * hr + 2, int(hr * 2.4)), border_radius=hr)
    pygame.draw.rect(s, shirt, (x - tw // 2, ty, tw, base - ty), border_top_left_radius=tw // 3,
                     border_top_right_radius=tw // 3)
    if style != 3:
        pygame.draw.circle(s, hair, (x, hy - 1), hr + 1)
    pygame.draw.circle(s, skin, (x, hy + 1), hr)
    if style == 2:                                          # coque
        pygame.draw.circle(s, hair, (x, hy - hr - 1), max(1, hr // 2))
    elif style == 4:                                        # bone na cor da camiseta
        pygame.draw.rect(s, f(darker(shirt_raw, 0.85)), (x - hr, hy - hr, 2 * hr, hr))
        pygame.draw.line(s, f(darker(shirt_raw, 0.7)), (x - hr, hy - 1), (x + hr + 2, hy - 1), 1)


def _bleachers(s, x0, x1, y0, rows, row_h, c1, c2, crowd=0, rng=None, shirts=_SHIRTS, empty=0.08):
    """Arquibancada em degraus com torcedores sentados (do fundo para a frente)."""
    for i in range(rows):
        y = y0 + i * row_h
        col = lerp(c1, c2, i / max(1, rows - 1))
        pygame.draw.rect(s, col, (x0, y, x1 - x0, row_h))
        pygame.draw.rect(s, darker(col, 0.7), (x0, y + row_h - 6, x1 - x0, 6))           # espelho do degrau
        pygame.draw.line(s, lighter(col, 0.12), (x0, y), (x1, y))
        if crowd and rng is not None:
            h = int(row_h * 1.05)
            fade = 0.34 + 0.28 * (i / max(1, rows - 1))
            step = max(7, int(h * 0.56))
            x = x0 + rng.randint(2, step)
            while x < x1 - 4:
                if rng.random() > empty:
                    _spectator(s, x + rng.randint(-2, 2), y + row_h - 5, h, rng, fade, col, shirts)
                x += step + rng.randint(-1, 2)


def _crowd_dots(s, rng, x0, x1, y0, y1, step, bgc, fade=0.5):
    """Torcida muito distante (2 primitivas por pessoa)."""
    for y in range(y0, y1, step):
        for x in range(x0 + rng.randint(0, step), x1, step):
            c = lerp(bgc, rng.choice(_SHIRTS), fade * (0.6 + 0.4 * rng.random()))
            pygame.draw.rect(s, c, (x - 2, y, 4, 4))
            pygame.draw.circle(s, lerp(bgc, rng.choice(_SKINS), fade), (x, y - 2), 2)


# ================================================================================ CENARIOS (estatico)
def _floor_lines(s, y0, col, n=7, spread=120, step=30):
    for i in range(-n, n + 1):
        pygame.draw.line(s, col, (550 + i * step, y0), (550 + i * spread, STAGE_H), 1)


def _window_night(s, rect, rng, moon=False):
    x, y, w, h = rect
    _vgrad(s, rect, (8, 14, 34), (26, 44, 86))
    _stars(s, rng, w // 10, y + h // 2, x, x + w)
    if moon:
        pygame.draw.circle(s, (230, 235, 210), (x + w - 22, y + 14), 8)
        pygame.draw.circle(s, (26, 40, 76), (x + w - 18, y + 11), 7)
    old = s.get_clip()
    s.set_clip(pygame.Rect(rect))
    _skyline(s, rng, x - 10, x + w + 10, y + h, h // 4, int(h * 0.7), (12, 20, 38), (240, 200, 110), 0.25)
    s.set_clip(old)


def _bg_garagem(s):
    rng = random.Random(1)
    _vgrad(s, (0, 0, 1100, 360), (14, 22, 40), (22, 34, 58))
    for row, y in enumerate(range(10, 356, 22)):                                     # tijolos (meio)
        pygame.draw.line(s, (19, 29, 50), (0, y), (1100, y), 1)
        for x in range(0 if row % 2 else 30, 1100, 60):
            pygame.draw.line(s, (19, 29, 50), (x, y), (x, y + 22), 1)
    _vgrad(s, (0, 360, 1100, 118), (34, 40, 58), (18, 22, 34))
    pygame.draw.line(s, NEON, (0, 360), (1100, 360), 2)
    pygame.draw.rect(s, (28, 42, 68), (330, 70, 430, 290))                         # portao
    for y in range(70, 360, 36):
        pygame.draw.line(s, (16, 26, 44), (330, y), (760, y), 3)
        pygame.draw.line(s, (50, 72, 104), (330, y + 3), (760, y + 3), 1)
    for i in range(4):                                                              # janelinhas: rua a noite
        r = (352 + i * 100, 112, 86, 30)
        _window_night(s, r, rng, moon=(i == 2))
        pygame.draw.rect(s, (60, 110, 150), r, 3)
    pygame.draw.rect(s, (60, 110, 150), (330, 70, 430, 290), 4)
    pygame.draw.rect(s, GOLD, (530, 330, 30, 8), border_radius=3)
    _catenary(s, (0, 30), (330, 52), 40, (30, 40, 62))                              # fios
    _catenary(s, (760, 50), (1100, 26), 46, (30, 40, 62))
    pygame.draw.rect(s, (26, 38, 62), (30, 90, 250, 170))                           # painel de ferramentas
    pygame.draw.rect(s, (60, 110, 150), (30, 90, 250, 170), 2)
    for x in range(44, 270, 22):
        for y in range(104, 250, 22):
            pygame.draw.circle(s, (38, 54, 84), (x, y), 2)
    pygame.draw.line(s, (170, 180, 195), (60, 130), (130, 200), 6)                  # chave
    pygame.draw.circle(s, (170, 180, 195), (56, 126), 14, 5)
    pygame.draw.line(s, (150, 110, 70), (170, 120), (170, 200), 7)                  # martelo
    pygame.draw.rect(s, (130, 140, 155), (148, 112, 46, 18), border_radius=3)
    pygame.draw.polygon(s, (190, 200, 210), [(220, 120), (262, 120), (262, 128), (230, 214), (220, 214)])
    pygame.draw.rect(s, (40, 56, 84), (40, 300, 230, 14), border_radius=3)          # bancada baixa
    pygame.draw.rect(s, (30, 42, 64), (52, 314, 12, 46))
    pygame.draw.rect(s, (30, 42, 64), (246, 314, 12, 46))
    pygame.draw.rect(s, (200, 60, 50), (70, 280, 60, 20), border_radius=4)          # maleta
    pygame.draw.rect(s, (90, 100, 116), (160, 284, 70, 16), border_radius=8)        # carcaca de aspirador
    for i, y in enumerate((150, 232, 314)):                                          # estantes e caixas
        pygame.draw.rect(s, (70, 90, 120), (800, y + 28, 270, 8))
        for j in range(3):
            w = 56 + (i * 13 + j * 17) % 30
            h = 34 + (i * 7 + j * 11) % 18
            x = 812 + j * 82
            col = lerp((90, 70, 50), (60, 90, 110), ((i + j) % 3) / 2.0)
            pygame.draw.rect(s, col, (x, y + 28 - h, w, h))
            pygame.draw.line(s, lighter(col, 0.3), (x + w // 2, y + 28 - h), (x + w // 2, y + 28), 3)
    pygame.draw.rect(s, (24, 34, 54), (780, 330, 26, 30), border_radius=4)          # tomada/doca do Ze
    pygame.draw.line(s, (40, 50, 70), (793, 360), (820, 420), 3)
    pygame.draw.line(s, (80, 90, 110), (550, 0), (550, 36), 3)                      # lampada
    pygame.draw.polygon(s, (70, 90, 120), [(520, 56), (580, 56), (566, 36), (534, 36)])
    _cone(s, (550, 56), (550, 478), 30, 300, (54, 70, 96))
    _ellipse_glow(s, (330, 396, 440, 80), (50, 60, 80))
    pygame.draw.ellipse(s, (14, 18, 28), (380, 410, 190, 40))                      # mancha de oleo
    pygame.draw.ellipse(s, (22, 28, 44), (400, 418, 120, 22))
    pygame.draw.line(s, (60, 80, 110), (418, 424), (470, 422), 1)
    _vignette(s, 0.55)


def _fg_garagem(s):
    for i, (y, w) in enumerate(((440, 104), (410, 100), (380, 96))):               # pneus empilhados
        pygame.draw.ellipse(s, (16, 18, 26), (6 + (104 - w) // 2, y, w, 34))
        pygame.draw.ellipse(s, (34, 38, 52), (6 + (104 - w) // 2, y, w, 34), 4)
        pygame.draw.ellipse(s, (8, 10, 16), (6 + (104 - w) // 2 + 30, y + 10, w - 60, 14))
    pygame.draw.rect(s, (110, 80, 52), (996, 404, 104, 74))                         # caixa
    pygame.draw.rect(s, (86, 60, 40), (996, 404, 104, 74), 3)
    pygame.draw.rect(s, (200, 190, 150), (1036, 404, 22, 74))
    _pixtext(s, "FRAGIL", 1004, 444, 2, (150, 40, 36))


def _anim_garagem(scr, t):
    flick = (t % 6.3) < 0.08 or 0.16 < (t % 6.3) < 0.22
    _add(scr, glow_sprite(44 if flick else 70, (30, 36, 44) if flick else (60, 70, 80)), (550, 64))
    pygame.draw.circle(scr, (150, 150, 140) if flick else (250, 245, 220), (550, 60), 8)
    _motes(scr, t, (420, 90, 260, 360), 14, (120, 140, 175), 1)
    pygame.draw.circle(scr, (80, 240, 130) if _blink(t, 1.6, 0.5) else (20, 70, 40), (793, 340), 3)


def _bg_oficina(s):
    rng = random.Random(2)
    _vgrad(s, (0, 0, 1100, 330), (12, 26, 44), (20, 40, 64))
    _vgrad(s, (0, 330, 1100, 148), (28, 38, 56), (14, 20, 32))
    for x in range(0, 1100, 44):                                                    # painel da parede
        pygame.draw.line(s, (16, 32, 52), (x, 0), (x, 330), 1)
    pygame.draw.line(s, NEON, (0, 330), (1100, 330), 2)
    for x in (110, 420, 730):                                                       # janelas: ceu e cidade
        pygame.draw.rect(s, (60, 120, 170), (x, 50, 240, 120))
        _vgrad(s, (x + 6, 56, 228, 108), (90, 160, 220), (170, 220, 245))
        for cxx, cyy in ((x + 50, 78), (x + 170, 70)):
            for dx, rr in ((0, 10), (12, 13), (26, 9)):
                pygame.draw.circle(s, (210, 235, 250), (cxx + dx, cyy), rr)
        old = s.get_clip()
        s.set_clip(pygame.Rect(x + 6, 56, 228, 108))
        _skyline(s, rng, x, x + 240, 164, 20, 60, (70, 110, 150), (120, 160, 200), 0.1)
        s.set_clip(old)
        pygame.draw.line(s, (20, 40, 64), (x + 120, 56), (x + 120, 164), 5)
        pygame.draw.line(s, (20, 40, 64), (x + 6, 110), (x + 234, 110), 5)
        pygame.draw.rect(s, (70, 110, 150), (x, 50, 240, 120), 4)
        _cone(s, (x + 120, 168), (x + 40, 330), 110, 150, (26, 40, 52), 4, 0.25)
    for x in (300, 820):                                                            # prateleiras de pecas
        pygame.draw.rect(s, (50, 70, 100), (x - 40, 200, 120, 6))
        for j in range(4):
            pygame.draw.rect(s, lerp((80, 110, 150), (150, 100, 70), j / 3.0), (x - 34 + j * 28, 180, 20, 20), border_radius=3)
    pygame.draw.rect(s, (60, 80, 110), (40, 330, 1020, 22), border_radius=4)       # bancada
    pygame.draw.line(s, NEON, (40, 330), (1060, 330), 2)
    for x in (70, 520, 990):
        pygame.draw.rect(s, (40, 56, 84), (x, 352, 18, 100))
    pygame.draw.rect(s, (24, 40, 70), (110, 262, 120, 68), border_radius=4)         # monitor
    pygame.draw.rect(s, (0, 120, 160), (118, 270, 104, 48))
    pygame.draw.line(s, NEON, (126, 300), (150, 284), 2)
    pygame.draw.line(s, NEON, (150, 284), (176, 306), 2)
    pygame.draw.line(s, NEON, (176, 306), (212, 280), 2)
    for i, x in enumerate((300, 340, 380)):                                         # pecas
        pygame.draw.circle(s, (150, 160, 175), (x, 316), 12 - i * 2)
        pygame.draw.circle(s, (40, 56, 84), (x, 316), 4)
    pygame.draw.rect(s, (230, 200, 160), (760, 296, 90, 34), border_radius=4)        # bolo
    pygame.draw.rect(s, (240, 120, 150), (760, 286, 90, 14), border_radius=6)
    pygame.draw.line(s, GOLD, (805, 270), (805, 286), 3)
    pygame.draw.rect(s, (200, 60, 50), (900, 292, 110, 38), border_radius=5)         # caixa de ferramentas
    pygame.draw.rect(s, (150, 40, 36), (900, 292, 110, 38), 2, border_radius=5)
    pygame.draw.rect(s, (200, 200, 205), (940, 282, 30, 10), 3, border_radius=4)
    _ellipse_glow(s, (100, 336, 900, 60), (30, 40, 50))
    _vignette(s, 0.5)


def _gear(scr, cx, cy, r, col, hole, ang):
    pygame.draw.circle(scr, col, (cx, cy), r)
    for i in range(12):
        a = ang + i * math.pi / 6
        pygame.draw.circle(scr, col, (int(cx + (r + 6) * math.cos(a)), int(cy + (r + 6) * math.sin(a))), 7)
    pygame.draw.circle(scr, hole, (cx, cy), r // 2)
    pygame.draw.line(scr, lighter(col, 0.15), (cx, cy), (int(cx + r * 0.45 * math.cos(ang)), int(cy + r * 0.45 * math.sin(ang))), 3)


def _fg_oficina(s):
    pygame.draw.polygon(s, (90, 56, 40), [(1006, 410), (1094, 410), (1084, 478), (1016, 478)])   # vaso
    pygame.draw.rect(s, (110, 70, 50), (1000, 402, 100, 14), border_radius=4)
    for a, l in ((-1.2, 90), (-1.6, 110), (-2.0, 86), (-0.8, 70), (-2.4, 70)):
        ex, ey = 1050 + int(l * math.cos(a)), 404 + int(l * math.sin(a))
        pygame.draw.line(s, (30, 110, 80), (1050, 404), (ex, ey), 4)
        pygame.draw.ellipse(s, (40, 150, 100), (ex - 14, ey - 7, 28, 14))


def _anim_oficina(scr, t):
    _gear(scr, 70, 250, 34, (40, 66, 98), (14, 26, 44), t * 0.6)
    _gear(scr, 1030, 230, 44, (40, 66, 98), (14, 26, 44), -t * 0.45)
    ph = (t * 0.5) % 1.0                                                            # ponto do grafico
    pts = ((126, 300), (150, 284), (176, 306), (212, 280))
    seg = min(2, int(ph * 3))
    f = ph * 3 - seg
    a, b = pts[seg], pts[seg + 1]
    pygame.draw.circle(scr, (220, 255, 255), (int(a[0] + (b[0] - a[0]) * f), int(a[1] + (b[1] - a[1]) * f)), 3)
    pygame.draw.circle(scr, (255, 150, 60) if _blink(t, 0.9, 0.6) else (255, 220, 120), (805, 266), 5)
    _motes(scr, t, (140, 180, 820, 150), 14, (150, 180, 200), 2, 6.0)


def _bg_escola(s):
    _vgrad(s, (0, 0, 1100, 340), (22, 36, 66), (30, 50, 84))
    _vgrad(s, (0, 340, 1100, 138), (44, 58, 86), (20, 28, 44))
    pygame.draw.rect(s, (36, 56, 92), (0, 240, 1100, 100))                           # barrado da parede
    pygame.draw.line(s, (60, 90, 130), (0, 240), (1100, 240), 3)
    pygame.draw.line(s, NEON, (0, 340), (1100, 340), 2)
    for x in (180, 460, 740):                                                        # luminarias do teto
        pygame.draw.rect(s, (60, 80, 110), (x, 4, 180, 10), border_radius=3)
        pygame.draw.rect(s, (200, 225, 245), (x + 6, 12, 168, 5))
        _cone(s, (x + 90, 16), (x + 90, 340), 84, 160, (22, 30, 40), 4, 0.1)
    for side in (0, 1):                                                              # armarios
        for i in range(7):
            x = 20 + i * 56 if side == 0 else 1100 - 20 - (i + 1) * 56
            col = lerp((40, 90, 140), (30, 60, 100), i / 6.0)
            pygame.draw.rect(s, col, (x, 70, 52, 270))
            pygame.draw.rect(s, lighter(col, 0.12), (x + 3, 73, 6, 264))
            pygame.draw.rect(s, (14, 24, 44), (x, 70, 52, 270), 2)
            for vy in (96, 104, 112):
                pygame.draw.line(s, (14, 24, 44), (x + 10, vy), (x + 42, vy), 2)
            pygame.draw.circle(s, (200, 210, 225), (x + 40, 200), 3)
    for x, c in ((52, (255, 120, 150)), (200, (255, 214, 90)), (930, (110, 220, 140))):   # adesivos
        pygame.draw.rect(s, c, (x, 150, 18, 14), border_radius=3)
    pygame.draw.rect(s, (60, 100, 150), (440, 100, 220, 240))                         # porta ao fundo
    pygame.draw.rect(s, (26, 44, 76), (452, 112, 196, 228))
    _vgrad(s, (500, 130, 100, 70), (130, 200, 240), (80, 140, 190))                   # corredor ao longe
    for i in range(4):
        pygame.draw.line(s, (60, 110, 160), (500, 200 - i * 4), (600, 200 - i * 4), 1)
    pygame.draw.polygon(s, (50, 100, 150), [(530, 200), (570, 200), (560, 160), (540, 160)])
    pygame.draw.rect(s, (220, 240, 255), (535, 136, 30, 6))
    pygame.draw.line(s, (26, 44, 76), (550, 130), (550, 200), 4)
    pygame.draw.circle(s, (235, 240, 245), (550, 66), 24)                             # relogio (ponteiros h/m)
    pygame.draw.circle(s, (30, 50, 80), (550, 66), 24, 3)
    pygame.draw.line(s, (30, 50, 80), (550, 66), (550, 50), 3)
    pygame.draw.line(s, (30, 50, 80), (550, 66), (562, 70), 3)
    for i in range(-6, 7):                                                            # piso em perspectiva
        pygame.draw.line(s, (60, 80, 112), (550 + i * 30, 340), (550 + i * 120, 478), 1)
    for y in (360, 390, 430):
        pygame.draw.line(s, (60, 80, 112), (0, y), (1100, y), 1)
    _ellipse_glow(s, (250, 350, 600, 70), (40, 50, 64))
    _vignette(s, 0.5)


def _fg_escola(s):
    pygame.draw.rect(s, (40, 60, 100), (14, 404, 84, 74), border_radius=14)           # mochila
    pygame.draw.rect(s, (60, 90, 150), (24, 430, 64, 34), border_radius=8)
    pygame.draw.arc(s, (30, 40, 70), (30, 384, 52, 44), 0.2, math.pi - 0.2, 5)
    pygame.draw.rect(s, (255, 214, 90), (50, 438, 12, 6))
    pygame.draw.polygon(s, (60, 70, 92), [(1010, 410), (1090, 410), (1080, 478), (1020, 478)])   # lixeira
    pygame.draw.rect(s, (80, 92, 120), (1004, 402, 92, 12), border_radius=4)
    for x in (1030, 1050, 1070):
        pygame.draw.line(s, (40, 50, 70), (x, 420), (x, 470), 2)


def _anim_escola(scr, t):
    a = -math.pi / 2 + (t % 60.0) / 60.0 * 2 * math.pi
    pygame.draw.line(scr, (220, 60, 60), (550, 66), (int(550 + 20 * math.cos(a)), int(66 + 20 * math.sin(a))), 2)
    pygame.draw.circle(scr, (220, 60, 60), (550, 66), 3)
    if (t % 4.7) < 0.1 or 0.18 < (t % 4.7) < 0.24:                                    # lampada falhando
        pygame.draw.rect(scr, (90, 110, 130), (746, 12, 168, 5))
    _motes(scr, t, (200, 40, 700, 280), 12, (140, 160, 190), 3, 5.0)


def _bg_cantina(s):
    _vgrad(s, (0, 0, 1100, 330), (24, 40, 62), (34, 54, 82))
    for y in range(176, 214, 12):                                                      # azulejos
        for x in range(0 if (y // 12) % 2 else 12, 1100, 24):
            pygame.draw.rect(s, (40, 62, 92), (x, y, 22, 10))
    _vgrad(s, (0, 330, 1100, 148), (50, 62, 88), (22, 30, 46))
    pygame.draw.line(s, NEON, (0, 330), (1100, 330), 2)
    pygame.draw.rect(s, (18, 52, 56), (150, 50, 420, 120), border_radius=6)           # lousa do cardapio
    pygame.draw.rect(s, (110, 90, 70), (150, 50, 420, 120), 5, border_radius=6)
    for i, w in enumerate((240, 180, 300, 210)):
        pygame.draw.line(s, (200, 230, 215), (176, 78 + i * 24), (176 + w, 78 + i * 24), 3)
        pygame.draw.circle(s, (255, 214, 90), (540, 78 + i * 24), 4)
    pygame.draw.rect(s, (40, 70, 110), (40, 30, 90, 120), border_radius=4)            # janelinha
    _vgrad(s, (46, 36, 78, 108), (60, 110, 170), (130, 190, 230))
    pygame.draw.line(s, (40, 70, 110), (85, 36), (85, 144), 4)
    pygame.draw.rect(s, (70, 92, 130), (60, 238, 980, 70))                            # balcao
    pygame.draw.rect(s, (110, 170, 215), (60, 214, 980, 28), 3)
    _vgrad(s, (64, 216, 972, 24), (50, 90, 130), (30, 60, 96))
    for x in range(80, 1040, 40):
        pygame.draw.line(s, (60, 82, 118), (x, 244), (x, 306), 1)
    for i, x in enumerate(range(100, 1000, 90)):                                       # salgados
        col = ((230, 170, 80), (210, 90, 70), (240, 220, 140))[i % 3]
        pygame.draw.circle(s, col, (x, 232), 11)
        pygame.draw.circle(s, darker(col), (x, 232), 11, 2)
        pygame.draw.circle(s, lighter(col, 0.4), (x - 4, 228), 3)
    for x in (650, 800, 950):                                                          # luminarias
        pygame.draw.line(s, (90, 100, 120), (x, 0), (x, 48), 2)
        _glow(s, (x, 62), 46, (240, 230, 170), (30, 48, 76), 5)
        pygame.draw.polygon(s, (60, 80, 110), [(x - 18, 56), (x + 18, 56), (x + 10, 46), (x - 10, 46)])
        pygame.draw.circle(s, (250, 245, 210), (x, 58), 10)
        _cone(s, (x, 60), (x, 330), 18, 90, (40, 38, 24), 4, 0.15)
    for x in (140, 360, 580, 800, 980):                                                # banquinhos
        pygame.draw.ellipse(s, (200, 70, 80), (x - 28, 380, 56, 20))
        pygame.draw.ellipse(s, (240, 110, 120), (x - 20, 382, 30, 8))
        pygame.draw.line(s, (130, 140, 160), (x, 396), (x, 450), 5)
        pygame.draw.ellipse(s, (60, 70, 92), (x - 26, 446, 52, 12))
    _vignette(s, 0.5)


def _fg_cantina(s):
    pygame.draw.polygon(s, (60, 80, 120), [(8, 420), (104, 420), (96, 478), (16, 478)])     # vaso com planta
    for a, l in ((-1.3, 100), (-1.7, 120), (-2.1, 96), (-0.9, 80)):
        ex, ey = 56 + int(l * math.cos(a)), 420 + int(l * math.sin(a))
        pygame.draw.line(s, (30, 120, 90), (56, 420), (ex, ey), 4)
        pygame.draw.ellipse(s, (50, 170, 110), (ex - 16, ey - 8, 32, 16))


def _anim_cantina(scr, t):
    for j, x in enumerate((190, 460, 730)):                                            # vapor dos salgados
        pts = [(x + int(6 * math.sin(t * 3 + i * 0.9 + j)), 216 - i * 9 - int((t * 14) % 9)) for i in range(6)]
        pygame.draw.lines(scr, (120, 150, 180), False, pts, 2)
    k = 0.9 + 0.1 * math.sin(t * 2.0)
    pygame.draw.circle(scr, scale((250, 245, 210), k), (800, 58), 10)


def _court_lines(s, y0, y1, col=(210, 235, 250)):
    cx = 550
    pygame.draw.line(s, col, (0, y0 + 14), (1100, y0 + 14), 3)
    pygame.draw.ellipse(s, col, (cx - 130, y0 + 20, 260, y1 - y0 - 30), 3)
    pygame.draw.line(s, col, (cx, y0 + 14), (cx, y1), 3)


def _bg_quadra(s):
    rng = random.Random(3)
    _vgrad(s, (0, 0, 1100, 300), (16, 28, 52), (26, 44, 76))
    _stars(s, rng, 40, 100)
    for x in (60, 1040):                                                               # postes de luz
        pygame.draw.rect(s, (40, 56, 84), (x - 4, 20, 8, 110))
        pygame.draw.rect(s, (30, 40, 60), (x - 24, 14, 48, 16), border_radius=3)
        _add_glow(s, (x, 22), 60, (90, 110, 120))
    for y in range(110, 300, 14):                                                      # alambrado ao fundo
        pygame.draw.line(s, (30, 48, 80), (300, y), (800, y), 1)
    for x in range(300, 800, 14):
        pygame.draw.line(s, (30, 48, 80), (x, 100), (x, 300), 1)
    _bleachers(s, 0, 300, 120, 5, 36, (36, 64, 104), (24, 44, 76), 1, rng)
    _bleachers(s, 800, 1100, 120, 5, 36, (36, 64, 104), (24, 44, 76), 1, rng)
    _vgrad(s, (0, 300, 1100, 178), (30, 78, 122), (18, 46, 80))                       # piso
    for y in range(306, 478, 14):
        pygame.draw.line(s, (22, 58, 96), (0, y), (1100, y), 1)
    pygame.draw.line(s, NEON, (0, 300), (1100, 300), 2)
    _court_lines(s, 300, 470)
    pygame.draw.rect(s, (230, 235, 245), (330, 130, 120, 80))                          # tabela
    pygame.draw.rect(s, (200, 60, 50), (370, 160, 40, 30), 3)
    pygame.draw.ellipse(s, (255, 130, 60), (362, 200, 56, 12), 3)
    for i in range(4):
        pygame.draw.line(s, (220, 220, 230), (366 + i * 14, 208), (370 + i * 12, 232), 1)
    pygame.draw.line(s, (120, 130, 150), (390, 210), (390, 300), 4)
    pygame.draw.rect(s, (40, 50, 70), (740, 230, 40, 70), border_radius=4)             # tambor da torcida
    pygame.draw.ellipse(s, (220, 220, 230), (740, 224, 40, 14))
    _ellipse_glow(s, (200, 320, 700, 120), (40, 60, 80))
    _vignette(s, 0.45)


_QUADRA_FLAGS = ((330, (220, 80, 80)), (480, NEON), (630, GOLD), (780, (110, 220, 120)))
_PTS_QUADRA = _pts(31, 8, (10, 120, 280, 170)) + _pts(32, 8, (810, 120, 280, 170))


def _anim_quadra(scr, t):
    for i, (x, col) in enumerate(_QUADRA_FLAGS):                                       # faixas balancando
        d = int(5 * math.sin(t * 2.2 + i * 1.3))
        pygame.draw.line(scr, (120, 130, 150), (x, 20), (x + 90, 20), 2)
        pygame.draw.polygon(scr, col, [(x, 20), (x + 90, 20), (x + 90 + d, 80), (x + 45 + d, 66), (x + d, 80)])
        pygame.draw.line(scr, darker(col), (x + 10 + d // 2, 36), (x + 80 + d // 2, 36), 3)
    _flashes(scr, t, _PTS_QUADRA, 0.5)


def _fg_quadra(s):
    pygame.draw.rect(s, (60, 70, 92), (1000, 420, 96, 50), border_radius=6)             # carrinho de bolas
    for i, x in enumerate(range(1012, 1090, 22)):
        pygame.draw.circle(s, ((255, 130, 60), (240, 240, 245), (255, 130, 60), (240, 240, 245))[i % 4], (x, 414), 12)
    pygame.draw.circle(s, (30, 34, 46), (1012, 472), 6)
    pygame.draw.circle(s, (30, 34, 46), (1084, 472), 6)


def _bg_ginasio(s):
    rng = random.Random(5)
    _vgrad(s, (0, 0, 1100, 320), (10, 18, 36), (20, 34, 62))
    for x in range(0, 1100, 110):                                                     # trelicas do teto
        pygame.draw.line(s, (24, 36, 60), (x, 0), (x + 55, 34), 2)
        pygame.draw.line(s, (24, 36, 60), (x + 110, 0), (x + 55, 34), 2)
    pygame.draw.line(s, (24, 36, 60), (0, 34), (1100, 34), 2)
    for x in range(40, 1100, 90):                                                     # refletores no teto
        pygame.draw.line(s, (50, 70, 100), (x, 0), (x, 14), 2)
        pygame.draw.circle(s, (230, 235, 200), (x, 22), 8)
        _glow(s, (x, 24), 22, (190, 200, 160), (14, 24, 44), 4)
    for x in (130, 400, 700, 970):
        _cone(s, (x, 24), (x, 320), 12, 120, (26, 30, 26), 4, 0.2)
    _bleachers(s, 0, 1100, 150, 5, 34, (34, 58, 96), (22, 38, 66), 1, rng)
    for x in range(0, 1100, 4):                                                       # grade da arquibancada
        if x % 40 == 0:
            pygame.draw.line(s, (90, 110, 140), (x, 300), (x, 320), 2)
    pygame.draw.line(s, (110, 130, 160), (0, 300), (1100, 300), 2)
    pygame.draw.rect(s, (14, 20, 34), (400, 40, 300, 90), border_radius=6)             # placar
    pygame.draw.rect(s, NEON, (400, 40, 300, 90), 3, border_radius=6)
    for i, x in enumerate((430, 480, 590, 640)):
        for dy in (52, 82, 112):
            pygame.draw.rect(s, (240, 90, 80), (x, dy - 8, 30, 5))
        pygame.draw.line(s, (240, 90, 80), (x, 52), (x, 108), 4)
        pygame.draw.line(s, (240, 90, 80), (x + 30, 52), (x + 30, 108), 4)
    _vgrad(s, (0, 320, 1100, 158), (34, 84, 128), (16, 42, 74))
    for y in range(326, 478, 12):
        pygame.draw.line(s, (20, 56, 94), (0, y), (1100, y), 1)
    pygame.draw.line(s, NEON, (0, 320), (1100, 320), 2)
    _court_lines(s, 320, 472)
    for x in (130, 400, 700, 970):
        _ellipse_glow(s, (x - 120, 400, 240, 50), (36, 44, 40))
    _vignette(s, 0.45)


_PTS_GIN = _pts(51, 14, (10, 150, 1080, 150))


def _anim_ginasio(scr, t):
    on = _blink(t, 1.0, 0.5)
    for y in (70, 100):
        pygame.draw.circle(scr, GOLD if on else (90, 70, 30), (545, y), 4)
    if (t % 5.3) < 0.07:
        pygame.draw.circle(scr, (110, 110, 100), (580, 22), 8)
    _flashes(scr, t, _PTS_GIN, 0.6)


def _bg_arena(s, gold=False):
    rng = random.Random(11)
    top = (6, 10, 26)
    acc = GOLD if gold else NEON
    _vgrad(s, (0, 0, 1100, 478), top, (14, 22, 52))
    _stars(s, rng, 50, 120, col=(120, 140, 200))
    for x0, x1 in ((120, 260), (980, 840), (360, 430), (740, 670)):                     # feixes dos refletores
        _cone(s, (x0, 0), (x1, 360), 14, 110, (24, 44, 90) if not gold else (60, 50, 26), 5, 0.2)
    for x in range(30, 1100, 120):                                                      # camarotes ao fundo
        pygame.draw.rect(s, (12, 18, 40), (x, 250, 90, 34))
        pygame.draw.rect(s, (40, 60, 110) if not gold else (90, 76, 40), (x + 6, 256, 78, 14))
    pygame.draw.rect(s, (8, 12, 28), (300, 36, 500, 220), border_radius=10)             # telao
    _vgrad(s, (310, 46, 480, 200), (30, 20, 90), (0, 70, 130))
    pygame.draw.rect(s, acc, (300, 36, 500, 220), 4, border_radius=10)
    for x in (300, 800):
        pygame.draw.line(s, (40, 50, 70), (x + (40 if x == 300 else -40), 0), (x + (40 if x == 300 else -40), 36), 4)
    if gold:                                                                             # globo (meridianos animados)
        pygame.draw.circle(s, (20, 80, 150), (550, 146), 70)
        pygame.draw.circle(s, (30, 110, 180), (530, 126), 40)
        pygame.draw.circle(s, GOLD, (550, 146), 70, 3)
        pygame.draw.line(s, GOLD, (480, 146), (620, 146), 2)
        pygame.draw.line(s, GOLD, (490, 116), (610, 116), 1)
        pygame.draw.line(s, GOLD, (490, 176), (610, 176), 1)
        pygame.draw.line(s, (60, 60, 70), (0, 2), (1100, 2), 2)
    else:
        for i in range(6):
            pygame.draw.line(s, (0, 150, 200), (310, 70 + i * 32), (790, 70 + i * 32), 1)
    _bleachers(s, 0, 1100, 292, 4, 28, (16, 28, 60), (10, 18, 40), 1, rng,
               shirts=((230, 200, 80), (240, 240, 245), (220, 70, 70), (70, 130, 230)) if gold else _SHIRTS)
    _vgrad(s, (0, 404, 1100, 74), (20, 34, 74), (10, 18, 40))
    pygame.draw.rect(s, (8, 12, 24), (0, 396, 1100, 12))                                 # faixa de LED
    pygame.draw.line(s, acc, (0, 404), (1100, 404), 3)
    for x in range(-200, 1400, 90):
        pygame.draw.line(s, (24, 50, 100), (550 + (x - 550) * 0.4, 408), (x, 478), 1)
    _ellipse_glow(s, (250, 410, 600, 60), (30, 50, 80) if not gold else (60, 50, 20))
    _vignette(s, 0.5)


_PTS_ARENA = _pts(111, 18, (10, 296, 1080, 96))


def _anim_telao(scr, t, acc):
    y = 46 + int((t * 60) % 200)                                                       # linha de varredura
    pygame.draw.line(scr, (60, 120, 200), (312, y), (788, y), 1)
    for i in range(14):                                                                 # equalizador
        h = int(14 + 26 * abs(math.sin(t * 3.1 + i * 0.7)))
        pygame.draw.rect(scr, lighter(acc, 0.1) if i % 2 else acc, (330 + i * 32, 236 - h, 20, h))


def _anim_ledband(scr, t, acc):
    for i in range(12):
        x = int((i * 96 + t * 140) % 1160) - 30
        pygame.draw.rect(scr, lighter(acc, 0.5), (x, 398, 30, 6))


def _anim_arena(scr, t):
    _anim_telao(scr, t, NEON)
    full = _blink(t, 1.2, 0.5)
    tri = [(520, 100), (600, 146), (520, 192)]
    if full:
        pygame.draw.polygon(scr, (0, 150, 200), tri)
    pygame.draw.polygon(scr, NEON, tri, 3)
    _anim_ledband(scr, t, NEON)
    _flashes(scr, t, _PTS_ARENA, 0.8)


_BUNT = [(x, ((220, 70, 70), (70, 130, 230), (240, 220, 90), (240, 240, 240))[(x // 54) % 4]) for x in range(30, 1100, 54)]
_CONF = [((i * 137) % 1100, (i * 71) % 400, ((220, 70, 70), (70, 130, 230), (240, 220, 90), (240, 240, 240))[i % 4])
         for i in range(26)]


def _drone(scr, x, y, t, i):
    pygame.draw.line(scr, (170, 190, 220), (x - 18, y - 6), (x + 18, y - 6), 3)
    pygame.draw.ellipse(scr, (90, 110, 150), (x - 10, y - 4, 20, 10))
    pygame.draw.circle(scr, GOLD if _blink(t, 0.8, 0.5, i * 0.3) else (220, 60, 60), (x, y + 4), 3)


def _anim_mundial(scr, t):
    _anim_telao(scr, t, GOLD)
    for j in range(2):                                                                   # globo girando
        w = int(140 * abs(math.cos(t * 0.8 + j * math.pi / 2)))
        if w > 4:
            pygame.draw.ellipse(scr, GOLD, (550 - w // 2, 76, w, 140), 2)
    for x, col in _BUNT:                                                                 # bandeirinhas
        d = int(4 * math.sin(t * 2.5 + x * 0.05))
        pygame.draw.polygon(scr, col, [(x, 2), (x + 30, 2), (x + 15 + d, 26)])
    for i, (x, y) in enumerate(((120, 120), (960, 150), (210, 70))):
        _drone(scr, x + int(10 * math.sin(t * 0.7 + i)), y + int(6 * math.sin(t * 1.9 + i * 2)), t, i)
    for i, (x, y, col) in enumerate(_CONF):                                              # confete
        yy = int((y + t * (40 + i % 5 * 8)) % 400)
        xx = x + int(8 * math.sin(t * 2 + i))
        pygame.draw.rect(scr, col, (xx, yy, 4 if i % 2 else 3, 3 if i % 2 else 5))
    _anim_ledband(scr, t, GOLD)
    _flashes(scr, t, _PTS_ARENA, 1.1)


def _bg_estadio(s):
    rng = random.Random(13)
    _vgrad(s, (0, 0, 1100, 300), (4, 8, 24), (20, 30, 66))
    for _ in range(70):
        pygame.draw.circle(s, (170, 190, 230), (rng.randint(0, 1099), rng.randint(0, 140)), 1)
    for x in (110, 990):                                                                 # torres de luz
        pygame.draw.rect(s, (40, 52, 80), (x - 6, 90, 12, 260))
        for yy in range(100, 340, 24):
            pygame.draw.line(s, (30, 40, 64), (x - 6, yy), (x + 6, yy + 12), 1)
        _glow(s, (x, 74), 120, (160, 210, 255), (14, 24, 54), 8)
        pygame.draw.rect(s, (20, 28, 50), (x - 46, 50, 92, 50))
        for i in range(3):
            for j in range(2):
                pygame.draw.circle(s, (250, 250, 235), (x - 30 + i * 30, 63 + j * 24), 8)
        _cone(s, (x, 80), (550 + (x - 550) // 4, 400), 40, 220, (22, 30, 44), 4, 0.15)
    for tier in range(4):                                                                # arquibancadas em degraus
        y = 190 + tier * 40
        col = lerp((28, 48, 92), (16, 30, 62), tier / 3.0)
        pygame.draw.polygon(s, col, [(0, y + 30), (550, y - 10), (1100, y + 30), (1100, y + 70), (0, y + 70)])
        pygame.draw.line(s, lighter(col, 0.15), (0, y + 30), (550, y - 10), 2)
        pygame.draw.line(s, lighter(col, 0.15), (550, y - 10), (1100, y + 30), 2)
        h = 13 + tier * 2
        fade = 0.38 + tier * 0.08
        for row in range(2):
            x = rng.randint(2, 8)
            while x < 1096:
                ye = y + 30 - 40 * (1 - abs(x - 550) / 550.0)
                if rng.random() > 0.06:
                    _spectator(s, x, int(ye + 18 + row * 16), h, rng, fade, col)
                x += int(h * 0.62) + rng.randint(0, 2)
    pygame.draw.rect(s, (14, 80, 80), (0, 392, 1100, 86))                                # gramado
    for i in range(0, 1100, 110):
        pygame.draw.rect(s, (10, 100, 96), (i, 392, 55, 86))
    pygame.draw.rect(s, (8, 14, 30), (0, 380, 1100, 12))                                 # placas LED
    pygame.draw.line(s, (210, 240, 245), (0, 404), (1100, 404), 3)
    pygame.draw.line(s, NEON, (0, 392), (1100, 392), 2)
    pygame.draw.ellipse(s, (210, 240, 245), (470, 420, 160, 40), 2)
    _vignette(s, 0.45)


_STARS_EST = _pts(131, 10, (0, 0, 1100, 140))
_PTS_EST = _pts(132, 20, (10, 200, 1080, 170))


def _anim_estadio(scr, t):
    for i, (x, y) in enumerate(_STARS_EST):
        if _blink(t, 2.0 + (i % 4) * 0.4, 0.3, i * 0.37):
            _star4(scr, (220, 230, 255), x, y, 3)
    big = _blink(t, 2.4, 0.5)
    for x in (110, 990):
        _add(scr, glow_sprite(26 if big else 20, (40, 50, 60)), (x, 74))
    _anim_ledband(scr, t, NEON)
    pygame.draw.rect(scr, (8, 14, 30), (0, 380, 1100, 12))
    for i in range(10):
        x = int((i * 118 + t * 90) % 1180) - 40
        pygame.draw.rect(scr, (0, 160, 200) if i % 2 else (255, 214, 90), (x, 383, 60, 6))
    _flashes(scr, t, _PTS_EST, 1.0)


def _bg_camarim(s):
    _vgrad(s, (0, 0, 1100, 360), (30, 22, 52), (40, 30, 70))
    for x in range(0, 1100, 36):                                                         # papel de parede
        pygame.draw.line(s, (36, 27, 62), (x, 0), (x, 360), 2)
    _vgrad(s, (0, 360, 1100, 118), (50, 40, 76), (22, 18, 40))
    pygame.draw.line(s, (255, 120, 200), (0, 360), (1100, 360), 2)
    for x in (100, 330, 560):                                                            # espelhos com lampadas
        pygame.draw.rect(s, (120, 150, 190), (x, 70, 190, 190))
        _vgrad(s, (x + 6, 76, 178, 178), (150, 190, 230), (90, 120, 170))
        pygame.draw.line(s, (220, 240, 255), (x + 20, 90), (x + 70, 240), 3)
        pygame.draw.line(s, (200, 225, 250), (x + 40, 90), (x + 80, 200), 1)
        pygame.draw.rect(s, (60, 40, 90), (x, 70, 190, 190), 5)
        for i in range(8):
            pygame.draw.circle(s, (180, 160, 120), (x + 12 + i * 24, 62), 6)
            pygame.draw.circle(s, (180, 160, 120), (x + 12 + i * 24, 268), 6)
    pygame.draw.rect(s, (70, 56, 100), (80, 290, 700, 18), border_radius=4)             # bancada
    for x, c in ((160, (255, 120, 170)), (220, (120, 200, 255)), (420, (255, 214, 90)), (640, (200, 160, 255))):
        pygame.draw.rect(s, c, (x, 276, 12, 14), border_radius=3)                        # potes e escovas
    pygame.draw.rect(s, (50, 38, 76), (110, 308, 14, 60))
    pygame.draw.rect(s, (50, 38, 76), (730, 308, 14, 60))
    pygame.draw.rect(s, (90, 50, 150), (100, 396, 520, 30), border_radius=8)             # banco
    pygame.draw.rect(s, (60, 36, 100), (100, 396, 520, 30), 2, border_radius=8)
    for x in (140, 560):
        pygame.draw.rect(s, (40, 30, 62), (x, 426, 12, 30))
    for i in range(5):                                                                    # armarios
        x = 840 + i * 50
        pygame.draw.rect(s, (60, 80, 130), (x, 90, 46, 270))
        pygame.draw.rect(s, (22, 24, 50), (x, 90, 46, 270), 2)
        for vy in (112, 120):
            pygame.draw.line(s, (22, 24, 50), (x + 8, vy), (x + 38, vy), 2)
        pygame.draw.circle(s, GOLD, (x + 36, 220), 3)
    pygame.draw.line(s, (180, 180, 200), (850, 88), (1080, 88), 3)                       # camisas penduradas
    for i, c in enumerate(((220, 50, 50), (60, 120, 230), (240, 200, 80))):
        x = 880 + i * 70
        pygame.draw.polygon(s, c, [(x - 22, 96), (x + 22, 96), (x + 30, 112), (x + 20, 116), (x + 18, 150),
                                   (x - 18, 150), (x - 20, 116), (x - 30, 112)])
        pygame.draw.line(s, (180, 180, 200), (x, 88), (x, 96), 2)
    _ellipse_glow(s, (100, 290, 640, 40), (60, 50, 40))
    _vignette(s, 0.5)


_CAM_BULBS = [(x + 12 + i * 24, y) for x in (100, 330, 560) for y in (62, 268) for i in range(8)]


def _anim_camarim(scr, t):
    step = int(t * 6)
    for i, (x, y) in enumerate(_CAM_BULBS):
        if (i + step) % 4 == 0:
            pygame.draw.circle(scr, (255, 245, 200), (x, y), 6)
            _add(scr, glow_sprite(12, (90, 80, 50)), (x, y))


def _bg_federacao(s):
    rng = random.Random(17)
    _vgrad(s, (0, 0, 1100, 330), (18, 26, 56), (30, 42, 80))
    pygame.draw.rect(s, (24, 34, 70), (300, 30, 500, 300))                                  # janelao com a cidade
    _vgrad(s, (310, 40, 480, 290), (10, 18, 44), (40, 60, 110))
    _stars(s, rng, 40, 150, 310, 790)
    old = s.get_clip()
    s.set_clip(pygame.Rect(310, 40, 480, 290))
    _skyline(s, rng, 300, 800, 330, 60, 190, (16, 26, 54), (240, 210, 120), 0.2)
    s.set_clip(old)
    for x in range(310, 790, 120):
        pygame.draw.line(s, (24, 34, 70), (x, 40), (x, 330), 4)
    for r in range(8):                                                                     # piso quadriculado
        for c in range(24):
            col = (46, 62, 100) if (r + c) % 2 else (34, 46, 78)
            pygame.draw.rect(s, col, (c * 46, 330 + r * 19, 46, 19))
    pygame.draw.polygon(s, (120, 30, 50), [(480, 330), (620, 330), (700, 478), (400, 478)])  # tapete
    pygame.draw.line(s, GOLD, (480, 330), (400, 478), 2)
    pygame.draw.line(s, GOLD, (620, 330), (700, 478), 2)
    pygame.draw.line(s, GOLD, (0, 330), (1100, 330), 2)
    for x in (60, 270, 830, 1040):                                                         # colunas
        pygame.draw.rect(s, (200, 210, 230), (x - 22, 90, 44, 240))
        pygame.draw.rect(s, (160, 172, 198), (x - 22, 90, 14, 240))
        for fx in (x - 4, x + 8):
            pygame.draw.line(s, (180, 190, 212), (fx, 94), (fx, 326), 1)
        pygame.draw.rect(s, (225, 232, 245), (x - 32, 72, 64, 20))
        pygame.draw.rect(s, (225, 232, 245), (x - 32, 326, 64, 12))
    pygame.draw.circle(s, (20, 36, 72), (550, 120), 62)                                     # selo
    pygame.draw.circle(s, GOLD, (550, 120), 62, 4)
    pygame.draw.circle(s, darker(GOLD, 0.7), (550, 120), 54, 1)
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = 40 if i % 2 == 0 else 17
        pts.append((550 + int(rr * math.cos(a)), 120 + int(rr * math.sin(a))))
    pygame.draw.polygon(s, GOLD, pts)
    for x in (380, 720):
        pygame.draw.line(s, (170, 150, 110), (x, 90), (x, 330), 5)
        pygame.draw.circle(s, GOLD, (x, 88), 6)
    for x in (165, 935):                                                                    # arandelas
        pygame.draw.rect(s, GOLD, (x - 6, 150, 12, 20), border_radius=3)
        _add_glow(s, (x, 146), 50, (90, 76, 40))
    pygame.draw.polygon(s, (60, 44, 34), [(190, 400), (910, 400), (990, 462), (110, 462)])  # mesa
    pygame.draw.polygon(s, (96, 70, 52), [(190, 400), (910, 400), (900, 410), (200, 410)])
    pygame.draw.line(s, GOLD, (110, 462), (990, 462), 2)
    pygame.draw.rect(s, (230, 230, 240), (420, 396, 60, 6))                                  # papeis
    pygame.draw.rect(s, (210, 220, 235), (600, 394, 50, 8))
    _vignette(s, 0.5)


def _fg_federacao(s):
    for x in (40, 1060):                                                                     # pedestais com corda
        pygame.draw.rect(s, GOLD, (x - 5, 380, 10, 90))
        pygame.draw.circle(s, GOLD, (x, 378), 9)
        pygame.draw.ellipse(s, darker(GOLD, 0.6), (x - 22, 464, 44, 14))
    pygame.draw.arc(s, (170, 30, 50), (40, 380, 90, 50), math.pi, 2 * math.pi, 6)
    pygame.draw.arc(s, (170, 30, 50), (970, 380, 90, 50), math.pi, 2 * math.pi, 6)


def _flag(scr, x, y, cols, t, ph):
    for j, c in enumerate(cols):
        top = y + j * 24
        pts = [(x, top)]
        for i in range(1, 5):
            pts.append((x + i * 18, top + int(4 * math.sin(t * 3 + ph + i * 0.9))))
        pts += [(x + i * 18, top + 24 + int(4 * math.sin(t * 3 + ph + i * 0.9))) for i in range(4, 0, -1)]
        pts.append((x, top + 24))
        pygame.draw.polygon(scr, c, pts)


def _anim_federacao(scr, t):
    _flag(scr, 380, 94, ((220, 70, 70), (240, 240, 240)), t, 0.0)
    _flag(scr, 720, 94, ((70, 130, 230), (240, 220, 90)), t, 1.3)
    a = t * 1.6
    if (t % 4.0) < 1.2:
        _star4(scr, (255, 250, 220), int(550 + 58 * math.cos(a)), int(120 + 58 * math.sin(a)), 6)


# ------------------------------------------------------------------------- cenarios novos (Atos 2 e 3)
def _tree(s, x, y, r, col, rng):
    pygame.draw.rect(s, darker(col, 0.45), (x - 6, y, 12, int(r * 1.6)))
    for _ in range(9):
        dx, dy = rng.randint(-r, r), rng.randint(-r // 2, r // 2)
        pygame.draw.circle(s, lerp(darker(col, 0.7), col, rng.random()), (x + dx, y + dy), rng.randint(r // 2, r))


def _bg_praca(s):
    rng = random.Random(21)
    _vgrad(s, (0, 0, 1100, 220), (14, 20, 54), (60, 60, 120))
    _vgrad(s, (0, 220, 1100, 90), (60, 60, 120), (110, 90, 140))
    _stars(s, rng, 60, 150)
    pygame.draw.circle(s, (240, 240, 220), (900, 70), 26)                                   # lua
    pygame.draw.circle(s, (200, 205, 190), (892, 64), 6)
    _add_glow(s, (900, 70), 90, (50, 50, 60))
    _skyline(s, rng, -10, 1110, 300, 50, 170, (22, 26, 58), (240, 200, 120), 0.18)           # cidade distante
    _skyline(s, rng, -20, 1110, 310, 20, 90, (30, 34, 70), (255, 220, 140), 0.12)
    _vgrad(s, (0, 300, 1100, 178), (30, 60, 60), (16, 34, 40))                              # gramado
    pygame.draw.polygon(s, (70, 76, 100), [(420, 300), (680, 300), (900, 478), (200, 478)])  # caminho de pedras
    for y in range(306, 478, 14):
        f = (y - 300) / 178.0
        x0, x1 = 420 - 220 * f, 680 + 220 * f
        for x in range(int(x0) + (y // 14) % 2 * 10, int(x1), 22):
            pygame.draw.ellipse(s, (84, 92, 120), (x, y, 18, 10))
    _tree(s, 90, 210, 60, (30, 110, 90), rng)
    _tree(s, 1010, 200, 70, (30, 110, 90), rng)
    _tree(s, 230, 240, 40, (36, 96, 90), rng)
    pygame.draw.ellipse(s, (60, 70, 100), (480, 262, 140, 40))                              # chafariz
    pygame.draw.ellipse(s, (90, 150, 210), (490, 266, 120, 26))
    pygame.draw.rect(s, (70, 80, 110), (540, 222, 20, 52))
    pygame.draw.ellipse(s, (80, 90, 120), (520, 214, 60, 16))
    pygame.draw.rect(s, (90, 60, 40), (250, 344, 200, 12), border_radius=3)                 # banco
    pygame.draw.rect(s, (90, 60, 40), (250, 322, 200, 10), border_radius=3)
    for x in (262, 438):
        pygame.draw.rect(s, (40, 44, 60), (x, 332, 8, 44))
    for x in (160, 850):                                                                     # postes
        pygame.draw.rect(s, (30, 36, 56), (x - 4, 170, 8, 200))
        pygame.draw.polygon(s, (40, 46, 70), [(x - 16, 170), (x + 16, 170), (x + 8, 156), (x - 8, 156)])
        pygame.draw.circle(s, (255, 236, 180), (x, 176), 8)
        _cone(s, (x, 176), (x, 400), 10, 90, (50, 44, 26), 4, 0.1)
        _ellipse_glow(s, (x - 90, 360, 180, 40), (50, 44, 30))
    _vignette(s, 0.5)


def _fg_praca(s):
    rng = random.Random(22)
    for cx in (40, 1060):                                                                    # arbustos
        for _ in range(14):
            dx, dy = rng.randint(-50, 50), rng.randint(-30, 40)
            pygame.draw.circle(s, lerp((14, 60, 50), (40, 130, 90), rng.random()), (cx + dx, 440 + dy), rng.randint(18, 30))
        for _ in range(5):
            pygame.draw.circle(s, (255, 140, 180), (cx + rng.randint(-40, 40), 430 + rng.randint(-20, 30)), 4)


def _anim_praca(scr, t):
    hop = int(abs(math.sin(t * 1.3)) * 4) if (t % 5.0) < 2.0 else 0                         # pombo-robo
    px, py = 700, 440 - hop
    pygame.draw.ellipse(scr, (130, 140, 160), (px - 18, py - 12, 36, 20))
    pygame.draw.ellipse(scr, (100, 110, 130), (px - 22, py - 8, 16, 10))
    peck = 4 if _blink(t, 1.6, 0.25) else 0
    pygame.draw.circle(scr, (150, 160, 180), (px + 16, py - 14 + peck), 8)
    pygame.draw.polygon(scr, GOLD, [(px + 23, py - 15 + peck), (px + 30, py - 12 + peck), (px + 23, py - 10 + peck)])
    pygame.draw.circle(scr, (255, 60, 60) if _blink(t, 1.1, 0.5) else (90, 20, 20), (px + 18, py - 16 + peck), 2)
    pygame.draw.line(scr, (80, 90, 110), (px - 4, py + 8), (px - 4, py + 14), 2)
    pygame.draw.line(scr, (80, 90, 110), (px + 6, py + 8), (px + 6, py + 14), 2)
    for i in range(5):                                                                        # agua do chafariz
        ph = (t * 1.4 + i * 0.2) % 1.0
        x = 550 + int((i - 2) * 16 * ph)
        y = 216 - int(30 * math.sin(ph * math.pi))
        pygame.draw.circle(scr, (150, 210, 255), (x, y), 2)
    _motes(scr, t, (60, 200, 980, 200), 12, (220, 240, 140), 4, 4.0)                          # vagalumes


def _bg_laboratorio(s):
    rng = random.Random(23)
    _vgrad(s, (0, 0, 1100, 340), (6, 16, 28), (12, 32, 48))
    for y in range(0, 340, 34):                                                               # paineis hexagonais
        for x in range((y // 34) % 2 * 30, 1100, 60):
            pts = [(x + 15 * math.cos(a) * 1.8, y + 17 + 15 * math.sin(a)) for a in [i * math.pi / 3 for i in range(6)]]
            pygame.draw.polygon(s, (14, 34, 52), pts, 1)
    _vgrad(s, (0, 340, 1100, 138), (20, 40, 56), (8, 16, 26))
    pygame.draw.line(s, (0, 255, 190), (0, 340), (1100, 340), 2)
    for x in range(0, 1100, 70):
        pygame.draw.line(s, (16, 34, 48), (x, 340), (550 + (x - 550) * 2, 478), 1)
    for x in (100, 900):                                                                       # fitas de luz no teto
        pygame.draw.rect(s, (180, 255, 240), (x, 6, 120, 4))
        _cone(s, (x + 60, 10), (x + 60, 340), 60, 120, (10, 36, 32), 4, 0.15)
    for i, x in enumerate((60, 150, 240, 860, 950)):                                          # tubos
        liq = ((0, 200, 160), (80, 220, 255), (150, 120, 255), (0, 200, 160), (255, 130, 200))[i]
        pygame.draw.rect(s, (30, 50, 70), (x - 30, 90, 60, 250), border_radius=26)
        _vgrad(s, (x - 24, 140, 48, 180), darker(liq, 0.5), darker(liq, 0.85))
        pygame.draw.rect(s, (120, 170, 200), (x - 30, 90, 60, 250), 3, border_radius=26)
        pygame.draw.line(s, (200, 240, 255), (x - 16, 110), (x - 16, 320), 2)
        pygame.draw.rect(s, (80, 100, 120), (x - 34, 80, 68, 16), border_radius=4)
        pygame.draw.rect(s, (80, 100, 120), (x - 34, 330, 68, 16), border_radius=4)
        _add_glow(s, (x, 230), 60, darker(liq, 0.2))
    pygame.draw.ellipse(s, (40, 60, 80), (470, 310, 160, 40))                                 # pedestal do holograma
    pygame.draw.ellipse(s, (0, 200, 200), (490, 316, 120, 24), 2)
    _cone(s, (550, 326), (550, 120), 50, 110, (0, 60, 70), 5, 0.3)
    for x, w in ((350, 90), (660, 120)):                                                       # consoles
        pygame.draw.polygon(s, (30, 46, 66), [(x, 290), (x + w, 290), (x + w + 10, 340), (x - 10, 340)])
        pygame.draw.rect(s, (8, 20, 30), (x + 8, 250, w - 16, 40), border_radius=4)
        pygame.draw.rect(s, (0, 180, 160), (x + 8, 250, w - 16, 40), 2, border_radius=4)
    for i in range(3):
        _catenary(s, (300 + i * 40, 340), (500 + i * 30, 340), 30 + i * 10, (20, 30, 44), 3)
    _vignette(s, 0.55)


_LAB_TUBES = ((60, (160, 255, 220)), (150, (180, 240, 255)), (240, (210, 200, 255)), (860, (160, 255, 220)),
              (950, (255, 200, 230)))


def _anim_laboratorio(scr, t):
    for j, (x, col) in enumerate(_LAB_TUBES):                                                  # bolhas
        for i in range(4):
            ph = (t * (0.35 + 0.05 * i) + i * 0.27 + j * 0.13) % 1.0
            pygame.draw.circle(scr, col, (x - 10 + (i * 7) % 20 + int(3 * math.sin(t * 3 + i)), int(318 - ph * 170)), 2 + i % 2)
    hy = 210 + int(6 * math.sin(t * 1.5))                                                       # holograma
    pygame.draw.circle(scr, (0, 230, 230), (550, hy), 46, 1)
    for j in range(2):
        w = int(92 * abs(math.cos(t * 0.9 + j * math.pi / 2)))
        if w > 3:
            pygame.draw.ellipse(scr, (0, 200, 220), (550 - w // 2, hy - 46, w, 92), 1)
    pygame.draw.ellipse(scr, (0, 200, 220), (504, hy - 10, 92, 20), 1)
    sy = hy - 46 + int((t * 50) % 92)
    pygame.draw.line(scr, (150, 255, 255), (510, sy), (590, sy), 1)
    for x, w in ((350, 90), (660, 120)):                                                       # telas dos consoles
        pts = [(x + 12 + i * (w - 24) // 7, 270 + int(10 * math.sin(t * 4 + i + x))) for i in range(8)]
        pygame.draw.lines(scr, (0, 255, 190), False, pts, 2)
        for i in range(4):
            on = _blink(t, 0.7 + i * 0.2, 0.5, i * 0.3 + x)
            pygame.draw.circle(scr, (255, 90, 90) if on else (60, 30, 30), (x + 6 + i * 12, 300), 3)


def _fg_laboratorio(s):
    pygame.draw.rect(s, (24, 36, 52), (0, 280, 52, 198))                                       # canos
    for x in (8, 30):
        pygame.draw.rect(s, (60, 80, 100), (x, 280, 14, 198))
        for y in (300, 380, 450):
            pygame.draw.rect(s, (90, 110, 130), (x - 3, y, 20, 8))
    pygame.draw.rect(s, (40, 56, 76), (1004, 400, 96, 10))                                      # suporte com frascos
    for i, c in enumerate(((0, 230, 180), (255, 130, 200), (120, 200, 255))):
        x = 1018 + i * 28
        pygame.draw.polygon(s, (150, 190, 210), [(x - 4, 360), (x + 4, 360), (x + 4, 372), (x + 12, 398), (x - 12, 398), (x - 4, 372)])
        pygame.draw.polygon(s, c, [(x - 8, 386), (x + 8, 386), (x + 11, 397), (x - 11, 397)])
    pygame.draw.rect(s, (30, 44, 62), (1010, 410, 10, 68))
    pygame.draw.rect(s, (30, 44, 62), (1080, 410, 10, 68))


def _bg_aeroporto(s):
    rng = random.Random(24)
    _vgrad(s, (0, 0, 1100, 300), (16, 22, 60), (90, 70, 130))                                  # ceu do entardecer
    _stars(s, rng, 30, 90)
    _skyline(s, rng, -10, 1110, 236, 10, 40, (30, 30, 70), (230, 200, 130), 0.1)
    pygame.draw.rect(s, (24, 26, 50), (0, 236, 1100, 64))                                         # pista
    for x in range(0, 1100, 30):
        pygame.draw.circle(s, (255, 200, 120), (x + 8, 262), 2)
        pygame.draw.circle(s, (120, 200, 255), (x + 20, 284), 2)
    pygame.draw.rect(s, (40, 40, 70), (130, 140, 22, 96))                                          # torre de controle
    pygame.draw.polygon(s, (50, 60, 100), [(112, 120), (170, 120), (162, 142), (120, 142)])
    pygame.draw.rect(s, (120, 200, 230), (120, 126, 42, 8))
    px, py = 760, 130                                                                              # aviao decolando
    for poly in ([(px - 90, py + 22), (px + 70, py - 18), (px + 90, py - 20), (px + 80, py - 10), (px - 80, py + 30)],
                 [(px - 10, py + 4), (px + 20, py - 4), (px - 30, py + 40), (px - 46, py + 40)],
                 [(px - 76, py + 22), (px - 60, py + 16), (px - 86, py - 6), (px - 96, py - 6)]):
        pygame.draw.polygon(s, (54, 58, 104), poly)
    for i in range(6):
        pygame.draw.circle(s, (255, 230, 160), (px - 50 + i * 18, py + 14 - i * 4), 1)
    pygame.draw.circle(s, (255, 70, 70), (px + 88, py - 18), 2)
    for x in range(0, 1101, 110):                                                                  # caixilhos do vidro
        pygame.draw.rect(s, (30, 40, 66), (x - 4, 0, 8, 300))
    pygame.draw.rect(s, (30, 40, 66), (0, 0, 1100, 10))
    pygame.draw.line(s, (60, 90, 140), (0, 300), (1100, 300), 3)
    for i in range(5):                                                                             # reflexos no vidro
        x = 60 + i * 230
        pygame.draw.line(s, (60, 70, 120), (x, 280), (x + 60, 20), 2)
    _vgrad(s, (0, 300, 1100, 178), (52, 64, 96), (24, 30, 48))                                     # piso brilhante
    for x in range(-400, 1500, 100):
        pygame.draw.line(s, (60, 74, 108), (550 + (x - 550) * 0.35, 300), (x, 478), 1)
    pygame.draw.rect(s, (12, 12, 20), (620, 30, 440, 140), border_radius=6)                       # painel de voos
    pygame.draw.rect(s, (60, 70, 100), (620, 30, 440, 140), 3, border_radius=6)
    _pixtext(s, "PARTIDAS", 640, 42, 3, (255, 200, 80))
    for i, (code, hh) in enumerate((("SF 101", "08:15"), ("LX 220", "09:40"), ("SL 007", "11:05"), ("CC 900", "13:30"))):
        y = 72 + i * 23
        pygame.draw.rect(s, (24, 24, 36), (636, y - 2, 408, 19))
        _pixtext(s, code.replace(" ", ""), 644, y + 2, 2, (255, 200, 80))
        _pixtext(s, hh, 760, y + 2, 2, (230, 230, 240))
        pygame.draw.rect(s, (90, 220, 120) if i % 2 == 0 else (255, 200, 80), (1000, y + 2, 34, 10))
    pygame.draw.rect(s, (40, 50, 70), (0, 352, 520, 34))                                           # esteira de bagagem
    pygame.draw.rect(s, (20, 24, 34), (0, 360, 520, 20))
    pygame.draw.rect(s, (80, 100, 130), (0, 352, 520, 6))
    pygame.draw.rect(s, (30, 36, 50), (0, 386, 520, 14))
    for x in (640, 720, 800, 880, 960):                                                            # cadeiras
        pygame.draw.rect(s, (40, 90, 160), (x, 340, 64, 28), border_radius=6)
        pygame.draw.rect(s, (30, 70, 130), (x + 4, 312, 56, 30), border_radius=6)
        pygame.draw.line(s, (100, 110, 130), (x + 32, 368), (x + 32, 396), 4)
    pygame.draw.rect(s, (90, 100, 120), (632, 394, 340, 6))
    _ellipse_glow(s, (100, 410, 900, 60), (40, 40, 60))
    _vignette(s, 0.45)


_BAGS = [((200, 60, 60), 46, 22), ((60, 120, 220), 36, 26), ((240, 200, 80), 52, 20), ((90, 200, 140), 40, 24),
         ((180, 120, 220), 44, 22)]


def _anim_aeroporto(scr, t):
    for i, (col, w, h) in enumerate(_BAGS):                                                       # malas na esteira
        x = int((i * 112 + t * 45) % 600) - 70
        if -w < x < 520:
            x0, x1 = max(0, x), min(520, x + w)
            if x1 > x0:
                pygame.draw.rect(scr, col, (x0, 360 - h + 6, x1 - x0, h), border_radius=4)
                pygame.draw.rect(scr, darker(col), (x0, 360 - h + 6, x1 - x0, h), 2, border_radius=4)
    for x in range(0, 1100, 30):                                                                  # luzes da pista em sequencia
        if (x // 30 - int(t * 8)) % 12 == 0:
            pygame.draw.circle(scr, (255, 255, 230), (x + 8, 262), 3)
            _add(scr, glow_sprite(8, (90, 80, 40)), (x + 8, 262))
    row = int(t / 1.6) % 4                                                                        # linha do painel trocando
    if (t % 1.6) < 0.25:
        y = 72 + row * 23
        pygame.draw.rect(scr, (24, 24, 36), (640, y - 2, 340, 19))
        for i in range(12):
            pygame.draw.rect(scr, (255, 200, 80) if (i + int(t * 20)) % 2 else (120, 90, 40), (644 + i * 20, y + 2, 10, 10))
    if _blink(t, 1.4, 0.5):
        pygame.draw.circle(scr, (255, 60, 60), (141, 136), 3)


def _fg_aeroporto(s):
    pygame.draw.polygon(s, (60, 70, 92), [(1010, 410), (1090, 410), (1080, 478), (1020, 478)])      # vaso com palmeira
    for a in (-0.4, -1.0, -1.6, -2.2, -2.7):
        ex, ey = 1050 + int(80 * math.cos(a)), 400 + int(60 * math.sin(a))
        pygame.draw.line(s, (40, 120, 90), (1050, 404), (ex, ey), 5)
        pygame.draw.polygon(s, (50, 160, 110), [(1050, 404), (ex, ey), (int(1050 + (ex - 1050) * 0.6), int(400 + (ey - 400) * 0.6) + 10)])
    pygame.draw.rect(s, (90, 100, 120), (6, 388, 92, 8))                                             # carrinho de malas
    pygame.draw.rect(s, (200, 60, 60), (16, 344, 50, 44), border_radius=5)
    pygame.draw.rect(s, (60, 120, 220), (30, 314, 40, 30), border_radius=5)
    pygame.draw.line(s, (110, 120, 140), (96, 392), (110, 320), 4)
    for x in (18, 86):
        pygame.draw.circle(s, (20, 22, 30), (x, 404), 9)


def _bg_dojo(s):
    rng = random.Random(25)
    _vgrad(s, (0, 0, 1100, 330), (40, 30, 34), (58, 44, 44))                                        # madeira escura
    for x in range(0, 1100, 18):
        pygame.draw.line(s, (48, 36, 40), (x, 0), (x, 330), 1)
    pygame.draw.rect(s, (30, 22, 24), (0, 30, 1100, 14))                                            # viga
    for i, x in enumerate(range(80, 1040, 120)):                                                     # biombos (shoji)
        if i == 4:                                                                                   # painel aberto: jardim a noite
            _vgrad(s, (x, 60, 110, 250), (10, 18, 44), (30, 50, 90))
            pygame.draw.circle(s, (240, 240, 220), (x + 70, 100), 16)
            for bx in (x + 14, x + 40, x + 88):
                pygame.draw.line(s, (20, 60, 50), (bx, 310), (bx + 4, 120), 4)
                for yy in range(140, 300, 30):
                    pygame.draw.line(s, (30, 90, 70), (bx + 2, yy), (bx + 18, yy - 10), 2)
        else:
            _vgrad(s, (x, 60, 110, 250), (200, 210, 230), (150, 165, 200))
            for gx in range(x, x + 111, 27):
                pygame.draw.line(s, (60, 44, 40), (gx, 60), (gx, 310), 2)
            for gy in range(60, 311, 36):
                pygame.draw.line(s, (60, 44, 40), (x, gy), (x + 110, gy), 2)
        pygame.draw.rect(s, (50, 36, 34), (x - 4, 56, 118, 258), 5)
    pygame.draw.rect(s, (230, 220, 190), (530, 70, 40, 200))                                        # pergaminho
    pygame.draw.rect(s, (60, 40, 30), (524, 64, 52, 8))
    pygame.draw.rect(s, (60, 40, 30), (524, 268, 52, 8))
    for i, ch in enumerate("GANBARE"):
        _pixtext(s, ch, 543, 80 + i * 26, 3, (30, 24, 30))
    _vgrad(s, (0, 330, 1100, 148), (150, 160, 110), (90, 100, 70))                                  # tatame
    for y in (330, 380, 440):
        pygame.draw.line(s, (40, 50, 34), (0, y), (1100, y), 4)
    for i in range(-5, 6):
        pygame.draw.line(s, (100, 110, 76), (550 + i * 110, 330), (550 + i * 230, 478), 2)
    pygame.draw.rect(s, (110, 30, 30), (0, 324, 1100, 8))
    pygame.draw.rect(s, (60, 40, 30), (40, 200, 110, 10))                                           # suporte de bokken
    for i in range(3):
        pygame.draw.line(s, (180, 140, 90), (52 + i * 34, 120), (52 + i * 34, 300), 5)
    pygame.draw.rect(s, (60, 40, 30), (40, 290, 110, 10))
    for x in (230, 870):                                                                              # lanternas (base)
        pygame.draw.line(s, (40, 30, 30), (x, 44), (x, 74), 2)
    _add_glow(s, (550, 200), 200, (24, 20, 14))
    _ellipse_glow(s, (200, 360, 700, 80), (40, 34, 20))
    _vignette(s, 0.55)


_PETALS = [((i * 151) % 1100, (i * 53) % 330) for i in range(16)]


def _anim_dojo(scr, t):
    for i, x in enumerate((230, 870)):                                                               # lanternas balancando
        d = int(4 * math.sin(t * 1.2 + i))
        _add(scr, glow_sprite(46, (70, 36, 18)), (x + d, 100))
        pygame.draw.ellipse(scr, (220, 70, 50), (x - 22 + d, 74, 44, 56))
        pygame.draw.ellipse(scr, (255, 140, 90), (x - 12 + d, 80, 24, 44))
        for yy in (86, 102, 118):
            pygame.draw.line(scr, (150, 40, 30), (x - 18 + d, yy), (x + 18 + d, yy), 1)
        pygame.draw.rect(scr, (40, 30, 30), (x - 10 + d, 70, 20, 6))
        pygame.draw.rect(scr, (40, 30, 30), (x - 10 + d, 128, 20, 6))
    for i, (x, y) in enumerate(_PETALS):                                                             # petalas caindo
        yy = int((y + t * (22 + i % 4 * 5)) % 470)
        xx = int((x + t * 12 + 18 * math.sin(t * 1.5 + i)) % 1100)
        pygame.draw.ellipse(scr, (255, 170, 200) if i % 2 else (255, 210, 225), (xx, yy, 6, 4))


def _fg_dojo(s):
    pygame.draw.rect(s, (90, 40, 30), (8, 400, 100, 70), border_radius=10)                            # taiko
    pygame.draw.ellipse(s, (230, 210, 170), (8, 388, 100, 26))
    pygame.draw.ellipse(s, (120, 60, 40), (8, 388, 100, 26), 3)
    for x in range(16, 104, 12):
        pygame.draw.circle(s, GOLD, (x, 412), 2)
    pygame.draw.rect(s, (60, 40, 30), (14, 466, 88, 10))
    pygame.draw.rect(s, (60, 40, 30), (1000, 430, 90, 40), border_radius=4)                          # bonsai
    pygame.draw.rect(s, (40, 70, 110), (1010, 414, 70, 22), border_radius=6)
    pygame.draw.line(s, (70, 50, 40), (1044, 414), (1030, 370), 6)
    pygame.draw.line(s, (70, 50, 40), (1036, 386), (1070, 360), 4)
    for cx, cy, r in ((1026, 362, 20), (1068, 352, 18), (1046, 340, 16)):
        pygame.draw.circle(s, (40, 120, 80), (cx, cy), r)
        pygame.draw.circle(s, (60, 150, 100), (cx - 4, cy - 4), r // 2)


def _bg_fabrica(s):
    rng = random.Random(26)
    _vgrad(s, (0, 0, 1100, 330), (14, 18, 30), (28, 34, 52))
    for x in range(0, 1100, 14):                                                                       # parede ondulada
        pygame.draw.line(s, (22, 28, 44) if (x // 14) % 2 else (32, 38, 58), (x, 60), (x, 330), 6)
    for x in range(60, 1100, 220):                                                                     # janelas altas
        pygame.draw.rect(s, (40, 60, 90), (x, 80, 120, 70))
        _vgrad(s, (x + 4, 84, 112, 62), (50, 80, 120), (90, 130, 170))
        pygame.draw.line(s, (30, 40, 60), (x + 60, 84), (x + 60, 146), 3)
        _cone(s, (x + 60, 150), (x + 20, 330), 56, 90, (24, 30, 40), 4, 0.2)
    pygame.draw.rect(s, (40, 46, 66), (0, 0, 1100, 50))                                                # trelica
    for x in range(0, 1100, 50):
        pygame.draw.line(s, (60, 70, 96), (x, 0), (x + 50, 50), 3)
        pygame.draw.line(s, (60, 70, 96), (x + 50, 0), (x, 50), 3)
    pygame.draw.rect(s, (70, 80, 106), (0, 46, 1100, 6))
    _vgrad(s, (0, 330, 1100, 148), (40, 44, 56), (18, 20, 28))
    for x in range(0, 1100, 40):                                                                       # faixa de perigo
        pygame.draw.polygon(s, (240, 190, 40), [(x, 410), (x + 20, 410), (x + 34, 420), (x + 14, 420)])
    pygame.draw.rect(s, (60, 66, 84), (0, 300, 1100, 18))                                              # esteira (base)
    pygame.draw.rect(s, (24, 26, 34), (0, 318, 1100, 22))
    for x in range(10, 1100, 60):
        pygame.draw.rect(s, (50, 56, 72), (x, 340, 10, 60))
    pygame.draw.rect(s, (110, 120, 140), (0, 298, 1100, 4))
    pygame.draw.rect(s, (50, 60, 80), (880, 120, 80, 180))                                             # maquina/braco base
    pygame.draw.rect(s, (240, 190, 40), (880, 120, 80, 12))
    for i in range(4):
        pygame.draw.circle(s, (20, 26, 36), (900 + i * 14, 200), 4)
    for x in (300, 700):                                                                                # sirenes (base)
        pygame.draw.rect(s, (40, 46, 60), (x - 14, 60, 28, 14))
    for x in (120, 520):                                                                                # canos
        pygame.draw.rect(s, (70, 80, 100), (x, 50, 16, 250))
        pygame.draw.rect(s, (90, 100, 120), (x - 4, 160, 24, 10))
    _vignette(s, 0.55)


def _anim_fabrica(scr, t):
    off = int(t * 60) % 30
    for x in range(-30 + off, 1100, 30):                                                               # esteira andando
        pygame.draw.line(scr, (40, 44, 56), (x, 304), (x, 316), 2)
    for i in range(7):                                                                                  # Zes na esteira
        x = int((i * 170 + t * 60) % 1200) - 60
        pygame.draw.ellipse(scr, (90, 100, 116), (x - 26, 282, 52, 16))
        pygame.draw.ellipse(scr, (150, 160, 175), (x - 26, 276, 52, 16))
        pygame.draw.circle(scr, (0, 230, 255) if (i + int(t * 2)) % 3 else (110, 240, 130), (x, 283), 3)
    a = 0.6 * math.sin(t * 1.3)                                                                         # braco robotico
    j1 = (920, 130)
    j2 = (int(j1[0] - 90 * math.cos(a + 0.6)), int(j1[1] + 70 + 40 * math.sin(a)))
    j3 = (j2[0] - 20, 270)
    pygame.draw.line(scr, (240, 190, 40), j1, j2, 10)
    pygame.draw.line(scr, (200, 160, 40), j2, j3, 8)
    pygame.draw.circle(scr, (60, 66, 84), j1, 9)
    pygame.draw.circle(scr, (60, 66, 84), j2, 7)
    pygame.draw.polygon(scr, (120, 130, 150), [(j3[0] - 10, j3[1]), (j3[0] + 10, j3[1]), (j3[0] + 6, j3[1] + 10), (j3[0] - 6, j3[1] + 10)])
    if _blink(t, 0.5, 0.4):                                                                              # faiscas
        for i in range(5):
            ang = t * 7 + i * 1.3
            pygame.draw.line(scr, (255, 220, 120), (j3[0], j3[1] + 10),
                             (int(j3[0] + 14 * math.cos(ang)), int(j3[1] + 12 + 10 * abs(math.sin(ang)))), 1)
    for i, x in enumerate((300, 700)):                                                                   # sirenes
        on = _blink(t, 1.0, 0.5, i * 0.5)
        pygame.draw.ellipse(scr, (255, 140, 30) if on else (110, 60, 20), (x - 12, 46, 24, 18))
        if on:
            _add(scr, glow_sprite(40, (90, 46, 10)), (x, 56))


def _fg_fabrica(s):
    for i, x in enumerate((8, 56)):                                                                      # barris
        pygame.draw.rect(s, (40, 90, 160) if i else (200, 70, 50), (x, 390, 46, 84), border_radius=6)
        for y in (406, 456):
            pygame.draw.line(s, (20, 26, 36), (x, y), (x + 46, y), 3)
    pygame.draw.rect(s, (110, 80, 50), (996, 396, 104, 82))                                              # caixote
    pygame.draw.rect(s, (80, 56, 34), (996, 396, 104, 82), 4)
    pygame.draw.line(s, (80, 56, 34), (996, 396), (1100, 478), 4)
    pygame.draw.line(s, (80, 56, 34), (1100, 396), (996, 478), 4)


def _bg_coliseu(s):
    rng = random.Random(27)
    _vgrad(s, (0, 0, 1100, 478), (4, 4, 12), (22, 18, 34))
    _stars(s, rng, 50, 100, col=(220, 200, 150))
    tiers = 5
    for i in range(tiers):                                                                              # aneis da arquibancada
        rx, ry = 820 - i * 70, 380 - i * 52
        col = (26, 22, 36) if i % 2 == 0 else (34, 28, 46)
        pygame.draw.ellipse(s, col, (550 - rx, 470 - ry, 2 * rx, 2 * ry))
        pygame.draw.ellipse(s, (120, 96, 40), (550 - rx, 470 - ry, 2 * rx, 2 * ry), 2)
    for x in range(-260, 1360, 44):                                                                     # arcos no topo
        ang = math.acos(max(-1.0, min(1.0, (x - 550) / 820.0)))
        y = 470 - 380 * math.sin(ang)
        pygame.draw.rect(s, (14, 12, 22), (x - 12, int(y) - 30, 24, 30), border_top_left_radius=12,
                         border_top_right_radius=12)
    for i in range(tiers):                                                                              # publico nos aneis
        rx, ry = 820 - i * 70 - 30, 380 - i * 52 - 20
        h = 12 + i * 2
        fade = 0.4 + i * 0.09
        n = int(rx * 2.2 / (h * 0.62))
        for j in range(n):
            a = math.pi * (j + rng.random() * 0.4) / n
            x = int(550 + rx * math.cos(a))
            y = int(470 - ry * math.sin(a))
            if 0 <= x < 1100 and y < 340 and rng.random() > 0.05:
                _spectator(s, x, y + h // 2, h, rng, fade, (30, 26, 40),
                           shirts=((30, 30, 34), (240, 200, 80), (200, 170, 70), (40, 40, 46), (230, 230, 235)))
    pygame.draw.rect(s, (16, 14, 22), (0, 330, 1100, 40))                                              # muro da arena
    pygame.draw.rect(s, GOLD, (0, 330, 1100, 4))
    pygame.draw.rect(s, (90, 70, 30), (0, 366, 1100, 4))
    w = pixtext_w("OMEGA", 7)
    pygame.draw.rect(s, (8, 8, 12), (550 - w // 2 - 16, 336, w + 32, 30 + 16), border_radius=4)
    _pixtext(s, "OMEGA", 550 - w // 2, 338, 7, (255, 70, 60))
    _vgrad(s, (0, 370, 1100, 108), (40, 34, 30), (16, 14, 14))                                         # areia escura
    for i in range(-6, 7):
        pygame.draw.line(s, (52, 44, 36), (550 + i * 60, 370), (550 + i * 200, 478), 1)
    for x in (80, 1020):                                                                                 # torres de refletor
        pygame.draw.rect(s, (30, 30, 40), (x - 5, 40, 10, 290))
        pygame.draw.rect(s, (20, 20, 28), (x - 36, 24, 72, 30))
        for i in range(3):
            pygame.draw.circle(s, (255, 240, 200), (x - 22 + i * 22, 39), 7)
        _cone(s, (x, 40), (550 + (x - 550) // 3, 470), 30, 200, (40, 34, 20), 5, 0.15)
    _ellipse_glow(s, (300, 380, 500, 90), (50, 40, 20))
    _vignette(s, 0.55)


_PTS_COL = _pts(271, 22, (40, 90, 1020, 230))
_GCONF = [((i * 173) % 1100, (i * 61) % 470, (255, 214, 90) if i % 2 else (40, 36, 44)) for i in range(22)]


def _anim_coliseu(scr, t):
    for i, x in enumerate((80, 1020)):
        big = _blink(t, 2.0, 0.5, i * 0.7)
        _add(scr, glow_sprite(48 if big else 36, (60, 50, 30)), (x, 39))
    _flashes(scr, t, _PTS_COL, 1.2)
    for i, (x, y, col) in enumerate(_GCONF):
        yy = int((y + t * (30 + i % 4 * 9)) % 470)
        pygame.draw.rect(scr, col, (x + int(6 * math.sin(t * 2 + i)), yy, 4, 3 if i % 3 else 5))
    if _blink(t, 1.0, 0.85):
        w = pixtext_w("OMEGA", 7)
        pygame.draw.rect(scr, (255, 70, 60), (550 - w // 2 - 16, 336, w + 32, 46), 2, border_radius=4)


def _bg_lanchonete(s):
    rng = random.Random(28)
    _vgrad(s, (0, 0, 1100, 330), (16, 28, 56), (26, 44, 80))
    for y in range(200, 330, 20):                                                                      # azulejos
        for x in range(0, 1100, 20):
            if ((x // 20) + (y // 20)) % 2:
                pygame.draw.rect(s, (30, 54, 90), (x, y, 20, 20))
    pygame.draw.rect(s, (40, 70, 110), (40, 50, 320, 220), border_radius=6)                            # janela: rua
    _window_night(s, (48, 58, 304, 204), rng)
    pygame.draw.rect(s, (40, 50, 70), (48, 230, 304, 32))
    pygame.draw.line(s, (240, 200, 90), (48, 246), (352, 246), 2)
    pygame.draw.line(s, (40, 70, 110), (200, 58), (200, 262), 5)
    pygame.draw.rect(s, (120, 160, 200), (40, 50, 320, 220), 4, border_radius=6)
    pygame.draw.rect(s, (12, 14, 24), (600, 40, 460, 140), border_radius=6)                             # cardapio
    pygame.draw.rect(s, (255, 120, 180), (600, 40, 460, 140), 3, border_radius=6)
    for i, (w, p) in enumerate(((180, "890"), (150, "1250"), (210, "690"), (120, "450"))):
        y = 58 + i * 28
        pygame.draw.rect(s, (220, 230, 245), (620, y + 4, w, 6), border_radius=3)
        _pixtext(s, p, 1040 - pixtext_w(p, 3), y, 3, (255, 214, 90))
    pygame.draw.rect(s, (60, 80, 120), (40, 290, 1020, 66))                                            # balcao
    pygame.draw.rect(s, (200, 210, 230), (34, 280, 1032, 12), border_radius=4)
    for x in range(60, 1060, 50):
        pygame.draw.rect(s, (70, 94, 140), (x, 300, 40, 50), 2, border_radius=4)
    pygame.draw.rect(s, (160, 170, 190), (880, 210, 110, 70), border_radius=6)                          # cafeteira
    pygame.draw.rect(s, (40, 50, 70), (896, 226, 78, 30), border_radius=4)
    pygame.draw.circle(s, (255, 80, 80), (970, 268), 4)
    for x, c in ((480, (255, 150, 190)), (540, (150, 220, 255))):                                       # milkshakes
        pygame.draw.polygon(s, (220, 230, 240), [(x - 14, 240), (x + 14, 240), (x + 8, 280), (x - 8, 280)])
        pygame.draw.polygon(s, c, [(x - 12, 248), (x + 12, 248), (x + 8, 278), (x - 8, 278)])
        pygame.draw.circle(s, (250, 250, 255), (x, 240), 10)
        pygame.draw.line(s, (255, 80, 80), (x + 4, 240), (x + 12, 214), 3)
    for i in range(-8, 9):                                                                              # piso xadrez
        pygame.draw.line(s, (60, 80, 120), (550 + i * 40, 356), (550 + i * 140, 478), 1)
    _vgrad(s, (0, 356, 1100, 122), (40, 54, 86), (20, 26, 44))
    for r in range(6):
        y = 360 + r * 20
        for c in range(-12, 13):
            if (r + c) % 2:
                f = 1.0 + r * 0.25
                x0 = 550 + int(c * 46 * f)
                pygame.draw.rect(s, (54, 70, 106), (x0, y, int(46 * f), 20))
    for x in (160, 330, 500, 670, 840):                                                                  # banquetas
        pygame.draw.ellipse(s, (220, 60, 90), (x - 30, 372, 60, 20))
        pygame.draw.ellipse(s, (255, 120, 150), (x - 22, 374, 30, 8))
        pygame.draw.rect(s, (170, 180, 200), (x - 3, 390, 6, 60))
        pygame.draw.ellipse(s, (120, 130, 150), (x - 22, 446, 44, 10))
    for x in (450, 750):                                                                                 # luminarias pendentes
        pygame.draw.line(s, (90, 100, 120), (x, 0), (x, 190), 2)
        pygame.draw.polygon(s, (255, 120, 180), [(x - 24, 206), (x + 24, 206), (x + 10, 188), (x - 10, 188)])
        _cone(s, (x, 206), (x, 356), 22, 120, (50, 34, 46), 4, 0.15)
    w = pixtext_w("LANCHES", 5)
    pygame.draw.rect(s, (14, 16, 30), (380, 30, w + 30, 50), border_radius=8)
    _vignette(s, 0.5)


def _neon_sign(sp, on):
    w = pixtext_w("LANCHES", 5)
    col = (255, 90, 170) if on else (90, 40, 70)
    if on:
        _pixtext(sp, "LANCHES", 13, 15, 5, (110, 30, 70))
        _pixtext(sp, "LANCHES", 17, 15, 5, (110, 30, 70))
    _pixtext(sp, "LANCHES", 15, 13, 5, col)
    pygame.draw.rect(sp, (0, 200, 230) if on else (20, 60, 70), (4, 4, w + 22, 42), 2, border_radius=8)


def _anim_lanchonete(scr, t):
    off = (t % 7.0) < 0.12 or 0.2 < (t % 7.0) < 0.26
    w = pixtext_w("LANCHES", 5)
    sp = _sprite(("neon", not off), (w + 30, 50), (lambda s_: _neon_sign(s_, True)) if not off else
                 (lambda s_: _neon_sign(s_, False)))
    scr.blit(sp, (380, 30), special_flags=pygame.BLEND_RGB_ADD)
    for i in range(3):                                                                                   # vapor da cafeteira
        pts = [(930 + i * 14 + int(5 * math.sin(t * 3 + j * 0.8 + i)), 206 - j * 8 - int((t * 16) % 8)) for j in range(6)]
        pygame.draw.lines(scr, (130, 150, 180), False, pts, 2)
    x = int((t * 140) % 520) - 100                                                                      # carro passando
    for dx in (0, 26):
        if 48 <= x + dx <= 346:
            pygame.draw.circle(scr, (255, 240, 180), (x + dx, 238), 4)
    if 48 <= x - 40 <= 346:
        pygame.draw.circle(scr, (255, 60, 60), (x - 40, 238), 3)


def _fg_lanchonete(s):
    pygame.draw.rect(s, (200, 60, 80), (990, 420, 110, 58))                                               # mesa e condimentos
    pygame.draw.rect(s, (220, 230, 240), (986, 412, 114, 10), border_radius=3)
    pygame.draw.rect(s, (220, 40, 40), (1010, 360, 18, 52), border_radius=5)
    pygame.draw.rect(s, (240, 200, 40), (1040, 366, 18, 46), border_radius=5)
    pygame.draw.rect(s, (200, 210, 230), (1068, 384, 26, 28), border_radius=3)


def _bg_cabine(s):
    rng = random.Random(29)
    _vgrad(s, (0, 0, 1100, 478), (12, 18, 36), (20, 28, 52))
    for x in range(0, 1100, 60):                                                                         # paineis acusticos
        for y in range(0, 330, 60):
            pygame.draw.rect(s, (18, 26, 48), (x + 2, y + 2, 56, 56), border_radius=4)
    wx, wy, ww, wh = 110, 50, 880, 250                                                                   # janelao: estadio
    _vgrad(s, (wx, wy, ww, wh), (6, 10, 30), (20, 30, 70))
    _stars(s, rng, 40, wy + 60, wx, wx + ww)
    old = s.get_clip()
    s.set_clip(pygame.Rect(wx, wy, ww, wh))
    pygame.draw.polygon(s, (24, 34, 70), [(wx, wy + 120), (wx + ww // 2, wy + 90), (wx + ww, wy + 120), (wx + ww, wy + 200), (wx, wy + 200)])
    _crowd_dots(s, rng, wx, wx + ww, wy + 112, wy + 196, 8, (24, 34, 70), 0.55)
    pygame.draw.rect(s, (14, 90, 86), (wx, wy + 196, ww, wh - 196))
    for i in range(0, ww, 80):
        pygame.draw.rect(s, (10, 106, 100), (wx + i, wy + 196, 40, wh - 196))
    pygame.draw.line(s, (210, 240, 245), (wx, wy + 210), (wx + ww, wy + 210), 2)
    pygame.draw.ellipse(s, (210, 240, 245), (wx + ww // 2 - 80, wy + 216, 160, 30), 2)
    for x in (wx + 60, wx + ww - 60):
        pygame.draw.rect(s, (40, 52, 80), (x - 4, wy + 30, 8, 90))
        pygame.draw.rect(s, (20, 28, 50), (x - 24, wy + 20, 48, 20))
        _add_glow(s, (x, wy + 30), 70, (60, 80, 100))
    s.set_clip(old)
    for i in range(4):                                                                                    # reflexos do vidro
        x = wx + 80 + i * 220
        pygame.draw.line(s, (40, 56, 90), (x, wy + wh), (x + 70, wy), 2)
    pygame.draw.rect(s, (40, 56, 90), (wx, wy, ww, wh), 8)
    pygame.draw.rect(s, (30, 40, 70), (0, 300, 1100, 50))                                                  # bancada
    pygame.draw.rect(s, (60, 80, 120), (0, 300, 1100, 8))
    pygame.draw.line(s, NEON, (0, 300), (1100, 300), 2)
    for x in (430, 670):                                                                                   # monitores
        pygame.draw.rect(s, (14, 20, 34), (x - 50, 240, 100, 62), border_radius=4)
        pygame.draw.rect(s, (60, 80, 120), (x - 50, 240, 100, 62), 2, border_radius=4)
    for x in (300, 800):                                                                                   # microfones de mesa
        pygame.draw.line(s, (90, 100, 120), (x, 300), (x, 250), 4)
        pygame.draw.ellipse(s, (60, 66, 84), (x - 12, 226, 24, 34))
        pygame.draw.ellipse(s, (120, 130, 150), (x - 12, 226, 24, 34), 2)
        pygame.draw.ellipse(s, (40, 44, 60), (x - 22, 296, 44, 10))
    _vgrad(s, (0, 350, 1100, 128), (26, 34, 58), (14, 18, 32))                                           # frente da bancada
    for x in range(0, 1100, 110):
        pygame.draw.rect(s, (30, 40, 66), (x + 6, 360, 98, 96), 2, border_radius=6)
    pygame.draw.rect(s, (0, 120, 150), (0, 352, 1100, 3))
    _ellipse_glow(s, (200, 300, 700, 40), (30, 40, 60))
    _vignette(s, 0.5)


_PTS_CAB = _pts(291, 18, (120, 165, 860, 80))


def _anim_cabine(scr, t):
    on = _blink(t, 1.6, 0.7)                                                                               # placa NO AR
    sp = _sprite(("noar", on), (110, 34), lambda s_: (pygame.draw.rect(s_, (200, 30, 40) if on else (60, 16, 20), (0, 0, 110, 34), border_radius=6),
                                                      _pixtext(s_, "NO AR", 12, 10, 3, (255, 240, 240) if on else (120, 80, 80))))
    scr.blit(sp, (495, 8))
    for i, x in enumerate((430, 670)):                                                                     # monitores
        pygame.draw.rect(scr, (0, 60, 90), (x - 44, 246, 88, 50))
        for j in range(6):
            h = int(6 + 18 * abs(math.sin(t * (2.5 + i) + j)))
            pygame.draw.rect(scr, (0, 230, 255) if j % 2 else (255, 214, 90), (x - 38 + j * 14, 292 - h, 9, h))
    for i, x in enumerate((300, 800)):                                                                     # VU dos microfones
        lv = int(4 * abs(math.sin(t * 6 + i * 1.7)))
        for j in range(4):
            pygame.draw.rect(scr, (90, 240, 120) if j < lv else (30, 50, 40), (x + 18, 286 - j * 8, 10, 6))
    _flashes(scr, t, _PTS_CAB, 1.3)


def _fg_cabine(s):
    pygame.draw.rect(s, (200, 200, 210), (8, 420, 90, 6))                                                  # papeis e caneca
    pygame.draw.rect(s, (230, 230, 240), (14, 412, 80, 8))
    pygame.draw.rect(s, (220, 70, 70), (40, 380, 36, 34), border_radius=5)
    pygame.draw.arc(s, (220, 70, 70), (68, 386, 20, 20), -math.pi / 2, math.pi / 2, 4)
    pygame.draw.rect(s, (30, 34, 46), (0, 426, 110, 52))
    pygame.draw.rect(s, (30, 34, 46), (990, 426, 110, 52))                                                 # fones pendurados
    pygame.draw.arc(s, (60, 66, 84), (1010, 360, 70, 60), 0, math.pi, 6)
    for x in (1010, 1070):
        pygame.draw.ellipse(s, (40, 44, 60), (x - 4, 388, 18, 30))


# Registro: estatico (fundo+meio+luz), animacao por quadro e camada de frente.
_DRAWERS = {"garagem": _bg_garagem, "oficina": _bg_oficina, "escola": _bg_escola, "cantina": _bg_cantina,
            "quadra": _bg_quadra, "ginasio": _bg_ginasio, "arena": _bg_arena, "camarim": _bg_camarim,
            "federacao": _bg_federacao, "estadio": _bg_estadio, "mundial": lambda s: _bg_arena(s, True),
            "praca": _bg_praca, "laboratorio": _bg_laboratorio, "aeroporto": _bg_aeroporto, "dojo": _bg_dojo,
            "fabrica": _bg_fabrica, "coliseu": _bg_coliseu, "lanchonete": _bg_lanchonete, "cabine": _bg_cabine}
_ANIMS = {"garagem": _anim_garagem, "oficina": _anim_oficina, "escola": _anim_escola, "cantina": _anim_cantina,
          "quadra": _anim_quadra, "ginasio": _anim_ginasio, "arena": _anim_arena, "camarim": _anim_camarim,
          "federacao": _anim_federacao, "estadio": _anim_estadio, "mundial": _anim_mundial,
          "praca": _anim_praca, "laboratorio": _anim_laboratorio, "aeroporto": _anim_aeroporto, "dojo": _anim_dojo,
          "fabrica": _anim_fabrica, "coliseu": _anim_coliseu, "lanchonete": _anim_lanchonete, "cabine": _anim_cabine}
_FRONTS = {"garagem": _fg_garagem, "oficina": _fg_oficina, "escola": _fg_escola, "cantina": _fg_cantina,
           "quadra": _fg_quadra, "federacao": _fg_federacao, "praca": _fg_praca, "laboratorio": _fg_laboratorio,
           "aeroporto": _fg_aeroporto, "dojo": _fg_dojo, "fabrica": _fg_fabrica, "lanchonete": _fg_lanchonete,
           "cabine": _fg_cabine}
_BG_CACHE = OrderedDict()
_FG_CACHE = {}
_SCRATCH = []


def draw_background(surf, bg):
    """Pinta as camadas estaticas do cenario `bg` em surf (STAGE_W x STAGE_H). Id desconhecido = fundo liso."""
    fn = _DRAWERS.get(bg)
    if fn is None:
        _vgrad(surf, (0, 0, STAGE_W, STAGE_H), (10, 18, 36), (20, 34, 62))
    else:
        fn(surf)
    pygame.draw.rect(surf, (6, 10, 20), (0, STAGE_H - 4, STAGE_W, 4))


def _warm(bg):
    """Aquece tudo que a animacao/frente usam (sprites e camada de frente) fora do laco de desenho."""
    get_foreground(bg)
    fn = _ANIMS.get(bg)
    if fn is not None:
        if not _SCRATCH:
            _SCRATCH.append(pygame.Surface((STAGE_W, STAGE_H)))
        for i in range(24):
            fn(_SCRATCH[0], i * 0.37)
        fn(_SCRATCH[0], 0.0)


def get_background(bg):
    """Surface estatica do cenario (criada UMA vez por cenario; LRU de BG_CACHE_MAX; convert() apos set_mode)."""
    s = _BG_CACHE.get(bg)
    if s is not None:
        _BG_CACHE.move_to_end(bg)
        return s
    s = pygame.Surface((STAGE_W, STAGE_H))
    try:
        s = s.convert()
    except pygame.error:
        pass
    draw_background(s, bg)
    _BG_CACHE[bg] = s
    _warm(bg)
    while len(_BG_CACHE) > BG_CACHE_MAX:
        old, _surf = _BG_CACHE.popitem(last=False)
        _FG_CACHE.pop(old, None)
    return s


def get_foreground(bg):
    """(Surface com colorkey, (x, y)) da camada de frente do cenario, ou None (cacheado)."""
    if bg in _FG_CACHE:
        return _FG_CACHE[bg]
    fn = _FRONTS.get(bg)
    fg = None
    if fn is not None:
        full = pygame.Surface((STAGE_W, STAGE_H))
        full.fill(KEY)
        fn(full)
        full.set_colorkey(KEY)
        r = full.get_bounding_rect()
        if r.w and r.h:
            piece = pygame.Surface(r.size)
            piece.fill(KEY)
            piece.blit(full, (0, 0), r)
            piece.set_colorkey(KEY, pygame.RLEACCEL)
            fg = (piece, r.topleft)
    _FG_CACHE[bg] = fg
    return fg


def draw_scene_anim(scr, bg, t):
    """Camada animada do cenario (por quadro; so pygame.draw/blits de sprites prontos)."""
    fn = _ANIMS.get(bg)
    if fn is not None:
        fn(scr, t)


def draw_foreground(scr, bg):
    """Camada de frente (depois dos personagens)."""
    fg = get_foreground(bg)
    if fg is not None:
        scr.blit(fg[0], fg[1])


# ================================================================================ PERSONAGENS
def _line(scr, col, a, b, w):
    pygame.draw.line(scr, col, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), max(1, int(w)))


def _arc(scr, col, rect, a0, a1, w):
    pygame.draw.arc(scr, col, pygame.Rect(int(rect[0]), int(rect[1]), max(2, int(rect[2])), max(2, int(rect[3]))),
                    a0, a1, max(1, int(w)))


def _phase(cid):
    return (sum(ord(c) for c in str(cid)) * 0.731) % BLINK_PERIOD


def anim_frame(cid, t, talking=False):
    """(blink, mouth) do personagem no instante t (deterministico; sem RNG)."""
    if t is None:
        return False, 0
    blink = ((t + _phase(cid)) % BLINK_PERIOD) < BLINK_DUR
    mouth = 1 if talking and int(t / TALK_FRAME) % 2 == 1 else 0
    return blink, mouth


_CLOSED_EYES = frozenset(("feliz", "calmo", "espirro", "sonolento", "chorando", "gritando", "euforico"))
_TALK_SCALE = {"gritando": 1.35, "euforico": 1.3, "susto": 1.1, "maravilhado": 1.1, "triste": 0.75,
               "chorando": 0.95, "sonolento": 0.6, "cansado": 0.7, "calmo": 0.75, "pensando": 0.7}


def _mood_decor(scr, mood, cx, cy, R, k, t):
    """Efeitos em volta da cabeca (zzz, brilhos, gritos, confete) - humanos e robo."""
    w = max(2, int(R * 0.06))
    if mood == "sonolento":
        col = shade((190, 215, 255), k)
        for i in range(3):
            sz = (0.16 + 0.07 * i) * R
            x = cx + (0.95 + 0.34 * i) * R
            y = cy - (0.9 + 0.48 * i) * R + math.sin(t * 2.0 + i) * 0.06 * R
            pygame.draw.lines(scr, col, False, [(int(x - sz), int(y - sz)), (int(x + sz), int(y - sz)),
                                                (int(x - sz), int(y + sz)), (int(x + sz), int(y + sz))], w)
    elif mood == "maravilhado":
        for i, (dx, dy) in enumerate(((-1.25, -0.9), (1.2, -1.05), (1.35, -0.2))):
            r = int(R * (0.15 + 0.05 * math.sin(t * 5 + i * 2)))
            _star4(scr, shade(GOLD if i % 2 == 0 else WHITE, k), cx + dx * R, cy + dy * R, r)
    elif mood == "euforico":
        cols = ((255, 90, 90), (90, 160, 255), (255, 214, 90), (110, 230, 140), (255, 140, 220), (0, 230, 255))
        for i, c in enumerate(cols):
            a = -math.pi * (0.1 + 0.8 * i / 5.0) + 0.15 * math.sin(t * 3 + i)
            x = cx + 1.45 * R * math.cos(a)
            y = cy - 0.2 * R + 1.25 * R * math.sin(a)
            pygame.draw.rect(scr, shade(c, k), (int(x), int(y), max(3, int(0.14 * R)), max(2, int(0.08 * R))))
    elif mood == "gritando":
        col = shade((255, 220, 120), k)
        for sx in (-1, 1):
            for j in (-1, 0, 1):
                a = j * 0.45
                x0 = cx + sx * (1.2 * R) * math.cos(a)
                y0 = cy - 0.1 * R + (1.2 * R) * math.sin(a)
                x1 = cx + sx * (1.55 * R) * math.cos(a)
                y1 = cy - 0.1 * R + (1.55 * R) * math.sin(a)
                _line(scr, col, (x0, y0), (x1, y1), w + 1)
    elif mood == "piscando":
        _star4(scr, shade(GOLD, k), cx - 1.05 * R, cy - 0.6 * R, int(R * (0.13 + 0.03 * math.sin(t * 6))))
    elif mood == "determinado":
        _star4(scr, shade(WHITE, k), cx + 1.05 * R, cy - 0.75 * R, int(R * 0.1))
        _line(scr, shade((255, 150, 60), k), (cx + 1.0 * R, cy - 1.15 * R), (cx + 1.2 * R, cy - 1.35 * R), w)


def draw_face(scr, cx, cy, R, mood, k=1.0, blink=False, mouth=0, t=0.0):
    """Sobrancelhas, olhos e boca (cx,cy = centro da cabeca; R = raio). blink=olhos fechados;
    mouth=1 boca aberta (quadro de fala)."""
    ink = shade(INK, k)
    white = shade(WHITE, k)
    mcol = shade(MOUTH, k)
    ex = 0.42 * R
    ey = cy - 0.02 * R
    er = max(2, int(0.12 * R))
    by = ey - 0.34 * R
    my = cy + 0.55 * R
    w = max(2, int(R * 0.07))
    lx, rx = cx - ex, cx + ex

    def dots(dx=0, dy=0):
        for x in (lx, rx):
            pygame.draw.circle(scr, ink, (int(x + dx), int(ey + dy)), er)
            if er >= 3:
                pygame.draw.circle(scr, white, (int(x + dx - er * 0.35), int(ey + dy - er * 0.4)), max(1, er // 3))

    def brows(l0, l1, r0, r1, ww=w):          # (dy externo, dy interno) por lado
        _line(scr, ink, (lx - 0.24 * R, by + l0 * R), (lx + 0.24 * R, by + l1 * R), ww)
        _line(scr, ink, (rx - 0.24 * R, by + r1 * R), (rx + 0.24 * R, by + r0 * R), ww)

    def happy_eye(x, size=0.2, ww=w):
        _arc(scr, ink, (x - size * R, ey - 0.12 * R, 2 * size * R, 2 * size * R), 0.2, math.pi - 0.2, ww)

    # ---- olhos
    if blink and mood not in _CLOSED_EYES:
        for x in (lx, rx):
            _arc(scr, ink, (x - 0.18 * R, ey - 0.12 * R, 0.36 * R, 0.22 * R), math.pi + 0.35, 2 * math.pi - 0.35, w)
    elif mood == "feliz":
        happy_eye(lx)
        happy_eye(rx)
    elif mood == "euforico":
        happy_eye(lx, 0.24, w + 1)
        happy_eye(rx, 0.24, w + 1)
    elif mood in ("susto", "maravilhado"):
        rr = int((0.2 if mood == "susto" else 0.23) * R)
        for x in (lx, rx):
            pygame.draw.circle(scr, white, (int(x), int(ey)), rr)
            pygame.draw.circle(scr, ink, (int(x), int(ey)), rr, 2)
            if mood == "susto":
                pygame.draw.circle(scr, ink, (int(x), int(ey)), max(2, int(0.07 * R)))
            else:
                _star4(scr, shade(GOLD, k), x, ey, int(0.15 * R))
                pygame.draw.circle(scr, white, (int(x - 0.07 * R), int(ey - 0.08 * R)), max(1, int(0.04 * R)))
    elif mood == "triste":
        dots(0, 0.05 * R)
    elif mood == "bravo":
        for x in (lx, rx):
            pygame.draw.ellipse(scr, ink, (int(x - 0.14 * R), int(ey - 0.04 * R), int(0.28 * R), int(0.16 * R)))
    elif mood == "determinado":
        for x in (lx, rx):
            pygame.draw.ellipse(scr, ink, (int(x - 0.13 * R), int(ey - 0.08 * R), int(0.26 * R), int(0.18 * R)))
            pygame.draw.circle(scr, white, (int(x - 0.04 * R), int(ey - 0.04 * R)), max(1, int(0.04 * R)))
    elif mood == "pensando":
        dots(0.1 * R, -0.08 * R)
    elif mood in ("convencida", "convencido"):
        for x in (lx, rx):
            pygame.draw.ellipse(scr, ink, (int(x - 0.14 * R), int(ey), int(0.28 * R), int(0.14 * R)))
            _line(scr, ink, (x - 0.2 * R, ey - 0.02 * R), (x + 0.2 * R, ey - 0.02 * R), w)
    elif mood == "malicioso":
        for i, x in enumerate((lx, rx)):
            pygame.draw.ellipse(scr, ink, (int(x - 0.06 * R), int(ey - 0.02 * R), int(0.24 * R), int(0.15 * R)))
            tilt = -0.06 if i == 0 else 0.04
            _line(scr, ink, (x - 0.2 * R, ey - 0.03 * R - tilt * R), (x + 0.2 * R, ey - 0.03 * R + tilt * R), w)
    elif mood == "corada":
        dots(0, 0.02 * R)
    elif mood == "espirro":
        for x, s_ in ((lx, 1), (rx, -1)):
            _line(scr, ink, (x - s_ * 0.2 * R, ey - 0.1 * R), (x + s_ * 0.16 * R, ey), w)
            _line(scr, ink, (x - s_ * 0.2 * R, ey + 0.1 * R), (x + s_ * 0.16 * R, ey), w)
    elif mood == "gritando":
        for x, s_ in ((lx, 1), (rx, -1)):
            _line(scr, ink, (x - s_ * 0.22 * R, ey - 0.16 * R), (x + s_ * 0.16 * R, ey), w + 1)
            _line(scr, ink, (x - s_ * 0.22 * R, ey + 0.12 * R), (x + s_ * 0.16 * R, ey), w + 1)
    elif mood == "calmo":
        for x in (lx, rx):
            _arc(scr, ink, (x - 0.2 * R, ey - 0.16 * R, 0.4 * R, 0.36 * R), math.pi + 0.2, 2 * math.pi - 0.2, w)
    elif mood == "sonolento":
        for x in (lx, rx):
            _arc(scr, ink, (x - 0.2 * R, ey - 0.06 * R, 0.4 * R, 0.22 * R), math.pi + 0.3, 2 * math.pi - 0.3, w)
            _line(scr, ink, (x - 0.22 * R, ey - 0.02 * R), (x + 0.22 * R, ey + 0.02 * R), max(1, w - 1))
    elif mood == "chorando":
        for x in (lx, rx):
            _arc(scr, ink, (x - 0.18 * R, ey - 0.06 * R, 0.36 * R, 0.3 * R), 0.35, math.pi - 0.35, w + 1)
    elif mood == "cansado":
        for x in (lx, rx):
            pygame.draw.ellipse(scr, ink, (int(x - 0.13 * R), int(ey + 0.02 * R), int(0.26 * R), int(0.14 * R)))
            _line(scr, ink, (x - 0.22 * R, ey), (x + 0.22 * R, ey), w)
            _arc(scr, shade((120, 100, 130), k), (x - 0.2 * R, ey + 0.1 * R, 0.4 * R, 0.24 * R), math.pi, 2 * math.pi, 1)
    elif mood == "piscando":
        happy_eye(lx)
        pygame.draw.circle(scr, ink, (int(rx), int(ey)), er)
        if er >= 3:
            pygame.draw.circle(scr, white, (int(rx - er * 0.35), int(ey - er * 0.4)), max(1, er // 3))
    else:                                   # neutro, suor (e "robo" em humanos)
        dots()

    # ---- sobrancelhas
    b = {"feliz": (0.0, -0.05, 0.0, -0.05), "euforico": (-0.16, -0.24, -0.16, -0.24),
         "susto": (-0.16, -0.26, -0.16, -0.26), "maravilhado": (-0.22, -0.3, -0.22, -0.3),
         "triste": (0.14, -0.1, 0.14, -0.1), "chorando": (0.2, -0.16, 0.2, -0.16),
         "bravo": (-0.06, 0.16, -0.06, 0.16), "convencida": (0.0, -0.06, 0.0, -0.06),
         "convencido": (0.0, -0.06, 0.0, -0.06), "corada": (0.04, -0.02, 0.04, -0.02),
         "suor": (0.12, -0.08, 0.12, -0.08), "espirro": (0.12, -0.04, 0.12, -0.04),
         "calmo": (0.0, 0.0, 0.0, 0.0), "sonolento": (0.1, 0.04, 0.1, 0.04), "cansado": (0.06, 0.1, 0.06, 0.1),
         "piscando": (0.08, 0.08, -0.14, -0.08), "malicioso": (-0.2, -0.08, 0.02, 0.12)}.get(mood)
    if mood == "pensando":
        _line(scr, ink, (lx - 0.24 * R, by + 0.02 * R), (lx + 0.24 * R, by + 0.02 * R), w)
        _line(scr, ink, (rx - 0.24 * R, by - 0.16 * R), (rx + 0.24 * R, by - 0.3 * R), w)
    elif mood == "determinado":
        brows(-0.04, 0.12, -0.04, 0.12, w + 1)
    elif mood == "gritando":
        brows(-0.12, 0.2, -0.12, 0.2, w + 1)
    elif b is not None:
        brows(*b)
    else:
        brows(0.0, 0.0, 0.0, 0.0)

    # ---- boca
    if mouth:
        sc = _TALK_SCALE.get(mood, 0.9)
        mw, mh = 0.36 * R * sc, 0.32 * R * sc
        rect = (cx - mw / 2, my - mh * 0.35, mw, mh)
        pygame.draw.ellipse(scr, mcol, rect)
        pygame.draw.ellipse(scr, shade(TONGUE, k), (cx - mw * 0.3, my + mh * 0.25, mw * 0.6, mh * 0.35))
        if mood in ("bravo", "determinado", "gritando", "euforico", "feliz"):
            pygame.draw.rect(scr, white, (cx - mw * 0.36, my - mh * 0.3, mw * 0.72, max(2, mh * 0.18)))
        pygame.draw.ellipse(scr, ink, rect, max(1, w - 1))
    elif mood == "feliz":
        pygame.draw.ellipse(scr, mcol, (cx - 0.34 * R, my - 0.2 * R, 0.68 * R, 0.5 * R))
        pygame.draw.rect(scr, white, (cx - 0.28 * R, my - 0.2 * R, 0.56 * R, 0.14 * R))
    elif mood == "euforico":
        pts = [(cx - 0.42 * R, my - 0.16 * R)]
        for i in range(11):
            a = i * math.pi / 10
            pts.append((cx - 0.42 * R * math.cos(a), my - 0.16 * R + 0.5 * R * math.sin(a)))
        pygame.draw.polygon(scr, mcol, pts)
        pygame.draw.ellipse(scr, shade(TONGUE, k), (cx - 0.2 * R, my + 0.1 * R, 0.4 * R, 0.22 * R))
        pygame.draw.rect(scr, white, (cx - 0.34 * R, my - 0.16 * R, 0.68 * R, 0.12 * R))
        pygame.draw.polygon(scr, ink, pts, max(1, w - 1))
    elif mood == "susto":
        pygame.draw.ellipse(scr, mcol, (cx - 0.16 * R, my - 0.12 * R, 0.32 * R, 0.5 * R))
        pygame.draw.ellipse(scr, ink, (cx - 0.16 * R, my - 0.12 * R, 0.32 * R, 0.5 * R), 2)
    elif mood == "maravilhado":
        rect = (cx - 0.17 * R, my - 0.1 * R, 0.34 * R, 0.34 * R)
        pygame.draw.ellipse(scr, mcol, rect)
        pygame.draw.ellipse(scr, shade(TONGUE, k), (cx - 0.1 * R, my + 0.08 * R, 0.2 * R, 0.12 * R))
        pygame.draw.ellipse(scr, ink, rect, 2)
    elif mood in ("triste", "bravo"):
        _arc(scr, ink, (cx - 0.3 * R, my + 0.02 * R, 0.6 * R, 0.4 * R), 0.4, math.pi - 0.4, w)
    elif mood == "chorando":
        rect = (cx - 0.28 * R, my - 0.04 * R, 0.56 * R, 0.34 * R)
        pygame.draw.ellipse(scr, mcol, rect)
        pygame.draw.ellipse(scr, shade(TONGUE, k), (cx - 0.14 * R, my + 0.14 * R, 0.28 * R, 0.12 * R))
        _arc(scr, ink, (cx - 0.3 * R, my - 0.06 * R, 0.6 * R, 0.4 * R), 0.3, math.pi - 0.3, w)
    elif mood == "determinado":
        rect = (cx - 0.24 * R, my - 0.06 * R, 0.48 * R, 0.17 * R)
        pygame.draw.rect(scr, white, rect, border_radius=max(1, int(0.05 * R)))
        _line(scr, ink, (cx - 0.22 * R, my + 0.025 * R), (cx + 0.22 * R, my + 0.025 * R), 1)
        for dx in (-0.08, 0.08):
            _line(scr, ink, (cx + dx * R, my - 0.05 * R), (cx + dx * R, my + 0.1 * R), 1)
        pygame.draw.rect(scr, ink, rect, max(1, w - 1), border_radius=max(1, int(0.05 * R)))
    elif mood == "gritando":
        rect = (cx - 0.3 * R, my - 0.2 * R, 0.6 * R, 0.6 * R)
        pygame.draw.ellipse(scr, mcol, rect)
        pygame.draw.ellipse(scr, shade(TONGUE, k), (cx - 0.18 * R, my + 0.16 * R, 0.36 * R, 0.2 * R))
        pygame.draw.rect(scr, white, (cx - 0.22 * R, my - 0.17 * R, 0.44 * R, 0.1 * R))
        pygame.draw.ellipse(scr, ink, rect, w)
    elif mood == "pensando":
        _line(scr, ink, (cx - 0.1 * R, my + 0.05 * R), (cx + 0.3 * R, my - 0.04 * R), w)
    elif mood in ("convencida", "convencido"):
        _line(scr, ink, (cx - 0.22 * R, my + 0.03 * R), (cx + 0.3 * R, my - 0.12 * R), w)
        pygame.draw.circle(scr, ink, (int(cx + 0.3 * R), int(my - 0.12 * R)), max(1, w // 2 + 1))
    elif mood == "malicioso":
        _arc(scr, ink, (cx - 0.34 * R, my - 0.34 * R, 0.68 * R, 0.46 * R), math.pi + 0.2, 2 * math.pi - 0.05, w)
        _line(scr, ink, (cx + 0.33 * R, my - 0.1 * R), (cx + 0.42 * R, my - 0.2 * R), w)
        pygame.draw.polygon(scr, white, [(int(cx + 0.12 * R), int(my + 0.08 * R)), (int(cx + 0.24 * R), int(my + 0.05 * R)),
                                         (int(cx + 0.19 * R), int(my + 0.18 * R))])
    elif mood == "corada":
        _arc(scr, ink, (cx - 0.2 * R, my - 0.12 * R, 0.4 * R, 0.3 * R), math.pi + 0.3, 2 * math.pi - 0.3, w)
    elif mood == "suor":
        pts = [(cx - 0.3 * R + i * 0.15 * R, my + (0.05 if i % 2 else -0.05) * R) for i in range(5)]
        pygame.draw.lines(scr, ink, False, [(int(a), int(b)) for a, b in pts], w)
    elif mood == "espirro":
        pygame.draw.ellipse(scr, mcol, (cx - 0.2 * R, my - 0.12 * R, 0.4 * R, 0.5 * R))
    elif mood == "calmo":
        _arc(scr, ink, (cx - 0.28 * R, my - 0.16 * R, 0.56 * R, 0.36 * R), math.pi + 0.35, 2 * math.pi - 0.35, w)
    elif mood == "sonolento":
        rect = (cx - 0.1 * R, my - 0.04 * R, 0.2 * R, 0.24 * R)
        pygame.draw.ellipse(scr, mcol, rect)
        pygame.draw.ellipse(scr, ink, rect, max(1, w - 1))
    elif mood == "cansado":
        _line(scr, ink, (cx - 0.2 * R, my + 0.04 * R), (cx + 0.2 * R, my + 0.04 * R), w)
    elif mood == "piscando":
        _arc(scr, ink, (cx - 0.3 * R, my - 0.26 * R, 0.6 * R, 0.42 * R), math.pi + 0.25, 2 * math.pi - 0.25, w + 1)
        pygame.draw.ellipse(scr, shade(TONGUE, k), (cx + 0.02 * R, my + 0.1 * R, 0.18 * R, 0.13 * R))
    else:                                   # neutro
        _line(scr, ink, (cx - 0.22 * R, my), (cx + 0.22 * R, my), w)

    # ---- extras do rosto
    if mood == "triste":
        pygame.draw.circle(scr, shade(TEAR, k), (int(lx - 0.1 * R), int(ey + 0.4 * R)), max(2, int(0.07 * R)))
    elif mood == "chorando":
        for i, x in enumerate((lx, rx)):
            pygame.draw.rect(scr, shade(TEAR, k), (int(x - 0.06 * R), int(ey + 0.08 * R), max(2, int(0.12 * R)), int(0.5 * R)),
                             border_radius=max(1, int(0.05 * R)))
            dy = ((t * 1.6 + i * 0.5) % 1.0) * 0.45 * R
            pygame.draw.circle(scr, shade(TEAR, k), (int(x + (0.1 if i else -0.1) * R), int(ey + 0.62 * R + dy)), max(2, int(0.07 * R)))
    elif mood == "bravo":
        _line(scr, shade((220, 60, 60), k), (cx + 0.9 * R, cy - 0.9 * R), (cx + 1.1 * R, cy - 0.7 * R), w)
        _line(scr, shade((220, 60, 60), k), (cx + 1.1 * R, cy - 0.9 * R), (cx + 0.9 * R, cy - 0.7 * R), w)
    elif mood == "pensando":
        for dx, dy, rr in ((1.15, -0.5, 0.07), (1.35, -0.85, 0.1), (1.6, -1.3, 0.16)):
            pygame.draw.circle(scr, white, (int(cx + dx * R), int(cy + dy * R)), max(2, int(rr * R)))
    if mood in ("corada", "euforico", "piscando"):
        f = 1.0 if mood == "corada" else 0.6
        for x in (cx - 0.72 * R, cx + 0.72 * R):
            pygame.draw.ellipse(scr, shade((255, 120, 150), k), (int(x - 0.22 * R * f), int(cy + 0.2 * R),
                                                                 int(0.44 * R * f), int(0.28 * R * f)))
    elif mood == "suor":
        dx, dy = cx + 1.0 * R, cy - 0.55 * R
        pygame.draw.polygon(scr, shade((100, 190, 255), k), [(int(dx), int(dy - 0.3 * R)), (int(dx - 0.18 * R), int(dy + 0.05 * R)),
                                                           (int(dx + 0.18 * R), int(dy + 0.05 * R))])
        pygame.draw.circle(scr, shade((100, 190, 255), k), (int(dx), int(dy + 0.06 * R)), max(2, int(0.18 * R)))
    elif mood == "espirro":
        for dx, dy in ((0.5, 0.35), (0.7, 0.55), (0.55, 0.75)):
            pygame.draw.circle(scr, white, (int(cx + dx * R), int(cy + dy * R)), max(2, int(0.07 * R)))
    _mood_decor(scr, mood, cx, cy, R, k, t)


def _cap_points(cx, cy, R, fringe, rr=1.0):
    pts = []
    for i in range(0, 13):
        a = math.pi + i * math.pi / 12
        pts.append((cx + rr * R * math.cos(a), cy + rr * R * math.sin(a)))
    pts.append((cx + R * 0.98, cy - fringe * R * 0.3))
    pts.append((cx + 0.35 * R, cy - fringe * R))
    pts.append((cx - 0.2 * R, cy - (fringe - 0.12) * R))
    pts.append((cx - R * 0.98, cy - fringe * R * 0.3))
    return [(int(a), int(b)) for a, b in pts]


def _hair_back(scr, cx, cy, R, style, col):
    if style == "longo":
        pygame.draw.rect(scr, col, (int(cx - 1.12 * R), int(cy - 0.9 * R), int(2.24 * R), int(3.0 * R)),
                         border_radius=int(0.7 * R))
    elif style == "coque":
        pygame.draw.circle(scr, col, (int(cx), int(cy - 1.02 * R)), int(0.44 * R))


_GLOSSY = frozenset(("curto", "espetado", "longo", "ondulado", "trancas", "coque"))


def _hair_front(scr, cx, cy, R, style, col, k=1.0):
    if style == "none":
        return
    if style == "calvo":
        for sx in (-1, 1):
            pygame.draw.ellipse(scr, col, (int(cx + sx * 0.9 * R - 0.18 * R), int(cy - 0.45 * R), int(0.36 * R), int(0.6 * R)))
        return
    if style == "raspado":
        pygame.draw.polygon(scr, col, _cap_points(cx, cy, R, 0.78, 1.0))
        return
    if style == "moicano":
        pygame.draw.polygon(scr, darker(col, 0.75), _cap_points(cx, cy, R, 0.84, 1.0))
        crest = [(-0.24, -0.6), (-0.36, -1.1), (-0.16, -1.75), (0.02, -1.42), (0.14, -1.95), (0.3, -1.5),
                 (0.38, -1.0), (0.24, -0.6)]
        pygame.draw.polygon(scr, col, [(int(cx + a * R), int(cy + b * R)) for a, b in crest])
        _line(scr, lighter(col, 0.3), (cx - 0.05 * R, cy - 0.7 * R), (cx + 0.08 * R, cy - 1.6 * R), max(1, int(R * 0.05)))
        return
    fr = {"curto": 0.62, "espetado": 0.55, "longo": 0.6, "ondulado": 0.5, "trancas": 0.58, "coque": 0.7}.get(style, 0.6)
    pygame.draw.polygon(scr, col, _cap_points(cx, cy, R, fr))
    if style == "espetado":
        spikes = [(-0.92, -0.55), (-0.95, -1.55), (-0.5, -0.9), (-0.3, -1.85), (0.0, -1.0), (0.32, -1.9),
                  (0.55, -0.92), (0.98, -1.6), (0.92, -0.55)]
        pygame.draw.polygon(scr, col, [(int(cx + a * R), int(cy + b * R)) for a, b in spikes])
    elif style == "ondulado":
        for i in range(7):
            a = math.pi + (i + 0.5) * math.pi / 7
            pygame.draw.circle(scr, col, (int(cx + 1.0 * R * math.cos(a)), int(cy + 1.0 * R * math.sin(a))), int(0.34 * R))
    elif style == "longo":
        for sx in (-1, 1):
            pygame.draw.rect(scr, col, (int(cx + sx * 0.98 * R - 0.2 * R), int(cy - 0.3 * R), int(0.4 * R), int(1.7 * R)),
                             border_radius=int(0.2 * R))
    elif style == "curto":
        for sx in (-1, 1):
            pygame.draw.circle(scr, col, (int(cx + sx * 0.92 * R), int(cy - 0.15 * R)), int(0.2 * R))
    elif style == "trancas":
        tie = shade((255, 110, 160), k)
        for sx in (-1, 1):
            for j in range(5):
                pygame.draw.circle(scr, col, (int(cx + sx * 1.0 * R), int(cy + 0.1 * R + j * 0.36 * R)), int(0.21 * R * (1 - j * 0.06)))
                _line(scr, darker(col, 0.7), (cx + sx * 1.0 * R - 0.12 * R, cy + 0.02 * R + j * 0.36 * R),
                      (cx + sx * 1.0 * R + 0.12 * R, cy + 0.14 * R + j * 0.36 * R), 1)
            pygame.draw.rect(scr, tie, (int(cx + sx * 1.0 * R - 0.12 * R), int(cy + 1.66 * R), int(0.24 * R), int(0.12 * R)))
    elif style == "coque":
        _line(scr, shade((255, 110, 160), k), (cx - 0.3 * R, cy - 0.66 * R), (cx + 0.3 * R, cy - 0.66 * R), max(2, int(R * 0.08)))
    if style in _GLOSSY:
        _arc(scr, lighter(col, 0.28), (cx - 0.78 * R, cy - 0.92 * R, 0.95 * R, 0.85 * R), 1.75, 2.55, max(2, int(R * 0.07)))


def _accessories(scr, cx, cy, R, acc, k, col=None):
    """Acessorios de cabeca/rosto (bengala/avental/cachecol ficam em _body_acc)."""
    w = max(2, int(R * 0.07))
    base = col or (80, 130, 255)
    for a in acc:
        if a == "oculos_redondos":
            rr = int(0.28 * R)
            for sx in (-1, 1):
                pygame.draw.circle(scr, shade((60, 60, 70), k), (int(cx + sx * 0.42 * R), int(cy - 0.02 * R)), rr, w)
            _line(scr, shade((60, 60, 70), k), (cx - 0.14 * R, cy - 0.04 * R), (cx + 0.14 * R, cy - 0.04 * R), w)
        elif a == "oculos_testa":
            for sx in (-1, 1):
                pygame.draw.circle(scr, shade((70, 70, 80), k), (int(cx + sx * 0.42 * R), int(cy - 0.72 * R)), int(0.22 * R), w)
            _line(scr, shade((70, 70, 80), k), (cx - 0.2 * R, cy - 0.74 * R), (cx + 0.2 * R, cy - 0.74 * R), w)
        elif a == "oculos_grandes":
            for sx in (-1, 1):
                pygame.draw.rect(scr, shade((30, 30, 40), k), (int(cx + sx * 0.44 * R - 0.34 * R), int(cy - 0.24 * R),
                                                               int(0.68 * R), int(0.5 * R)), w, border_radius=int(0.14 * R))
            _line(scr, shade((30, 30, 40), k), (cx - 0.1 * R, cy - 0.04 * R), (cx + 0.1 * R, cy - 0.04 * R), w)
        elif a == "headset":
            _arc(scr, shade((50, 55, 70), k), (cx - 1.1 * R, cy - 1.15 * R, 2.2 * R, 2.1 * R), 0.2, math.pi - 0.2, w + 1)
            for sx in (-1, 1):
                pygame.draw.circle(scr, shade((50, 55, 70), k), (int(cx + sx * 1.05 * R), int(cy - 0.05 * R)), int(0.22 * R))
                pygame.draw.circle(scr, shade((80, 230, 120), k), (int(cx + sx * 1.05 * R), int(cy - 0.05 * R)), int(0.1 * R))
            _line(scr, shade((50, 55, 70), k), (cx - 1.05 * R, cy + 0.05 * R), (cx - 0.5 * R, cy + 0.72 * R), w)
            pygame.draw.circle(scr, shade((50, 55, 70), k), (int(cx - 0.5 * R), int(cy + 0.72 * R)), int(0.1 * R))
        elif a == "bandana":
            c = shade((255, 150, 40), k)
            pygame.draw.polygon(scr, c, [(int(cx - 1.0 * R), int(cy - 0.45 * R)), (int(cx + 1.0 * R), int(cy - 0.45 * R)),
                                         (int(cx + 0.98 * R), int(cy - 0.15 * R)), (int(cx - 0.98 * R), int(cy - 0.15 * R))])
            pygame.draw.polygon(scr, c, [(int(cx + 0.95 * R), int(cy - 0.3 * R)), (int(cx + 1.4 * R), int(cy - 0.5 * R)),
                                         (int(cx + 1.3 * R), int(cy - 0.05 * R))])
            for i in range(-2, 3):
                pygame.draw.circle(scr, shade((255, 235, 190), k), (int(cx + i * 0.3 * R), int(cy - 0.3 * R)), max(1, int(0.04 * R)))
        elif a == "bigode":
            pygame.draw.ellipse(scr, shade((150, 150, 155), k), (int(cx - 0.4 * R), int(cy + 0.28 * R), int(0.4 * R), int(0.2 * R)))
            pygame.draw.ellipse(scr, shade((150, 150, 155), k), (int(cx), int(cy + 0.28 * R), int(0.4 * R), int(0.2 * R)))
        elif a == "graxa":
            for dx, dy in ((0.6, 0.3), (-0.55, 0.15), (0.2, 0.75)):
                pygame.draw.ellipse(scr, shade((40, 36, 36), k), (int(cx + dx * R), int(cy + dy * R), int(0.3 * R), int(0.16 * R)))
        elif a == "capacete":
            pygame.draw.polygon(scr, shade((250, 200, 60), k), _cap_points(cx, cy, R, 0.4, 1.1))
        elif a == "canetas":
            for i, c in enumerate(((60, 120, 240), (230, 70, 70), (60, 200, 110))):
                _line(scr, shade(c, k), (cx - 1.0 * R + i * 0.12 * R, cy + 1.75 * R), (cx - 1.0 * R + i * 0.12 * R, cy + 1.5 * R), w)
        elif a == "apito":
            _line(scr, shade((200, 200, 205), k), (cx - 0.3 * R, cy + 1.2 * R), (cx, cy + 2.0 * R), 1)
            pygame.draw.circle(scr, shade((240, 240, 250), k), (int(cx), int(cy + 2.0 * R)), int(0.14 * R))
        elif a == "bone":
            c = shade(base, k)
            pygame.draw.polygon(scr, c, _cap_points(cx, cy, R, 0.42, 1.06))
            pygame.draw.ellipse(scr, shade(darker(base, 0.7), k), (int(cx - 1.08 * R), int(cy - 0.62 * R), int(2.16 * R), int(0.34 * R)))
            pygame.draw.circle(scr, shade(lighter(base, 0.5), k), (int(cx), int(cy - 1.04 * R)), max(2, int(0.1 * R)))
            pygame.draw.circle(scr, shade(WHITE, k), (int(cx), int(cy - 0.78 * R)), max(2, int(0.13 * R)))
        elif a == "tiara":
            _arc(scr, shade(lighter(base, 0.25), k), (cx - 0.98 * R, cy - 1.02 * R, 1.96 * R, 1.5 * R), 0.42, math.pi - 0.42, w)
            _star4(scr, shade(GOLD, k), cx + 0.38 * R, cy - 0.9 * R, int(0.14 * R))


def _body_acc(scr, cx, cy, R, acc, k, top, bottom, col, bust):
    """Acessorios de corpo: avental (sobre o torso), cachecol (pescoco), bengala (so corpo inteiro)."""
    base = col or (80, 130, 255)
    for a in acc:
        if a == "avental":
            _apron(scr, cx, R, top, bottom, shade((120, 82, 52), k), k)
        elif a == "cachecol":
            c = shade(base, k)
            st = shade(lighter(base, 0.5), k)
            pygame.draw.rect(scr, c, (int(cx + 0.25 * R), int(cy + 1.0 * R), int(0.42 * R), int(1.35 * R)), border_radius=int(0.1 * R))
            for i in range(3):
                _line(scr, st, (cx + 0.27 * R, cy + 1.6 * R + i * 0.22 * R), (cx + 0.65 * R, cy + 1.6 * R + i * 0.22 * R), max(1, int(R * 0.05)))
            pygame.draw.ellipse(scr, c, (int(cx - 0.9 * R), int(cy + 0.72 * R), int(1.8 * R), int(0.55 * R)))
            _line(scr, st, (cx - 0.7 * R, cy + 0.98 * R), (cx + 0.7 * R, cy + 0.98 * R), max(1, int(R * 0.05)))
        elif a == "bengala" and not bust:
            hx, hy = cx + 1.5 * R, top + 2.5 * R
            wood = shade((130, 90, 55), k)
            _line(scr, wood, (hx + 0.1 * R, hy - 0.1 * R), (hx + 0.35 * R, cy + 5.95 * R), max(2, int(R * 0.12)))
            _arc(scr, wood, (hx - 0.25 * R, hy - 0.45 * R, 0.5 * R, 0.5 * R), 0.0, math.pi, max(2, int(R * 0.12)))
            pygame.draw.circle(scr, shade((40, 36, 40), k), (int(hx + 0.35 * R), int(cy + 5.95 * R)), max(2, int(0.08 * R)))


def _apron(scr, cx, R, top, bottom, c, k, long_=True):
    dark = darker(c, 0.75)
    bib = [(cx - 0.55 * R, top + 0.45 * R), (cx + 0.55 * R, top + 0.45 * R), (cx + 0.95 * R, top + 1.4 * R),
           (cx + 0.95 * R, bottom + (0.9 * R if long_ else 0)), (cx - 0.95 * R, bottom + (0.9 * R if long_ else 0)),
           (cx - 0.95 * R, top + 1.4 * R)]
    pygame.draw.polygon(scr, c, [(int(a), int(b)) for a, b in bib])
    for sx in (-1, 1):
        _line(scr, dark, (cx + sx * 0.5 * R, top + 0.45 * R), (cx + sx * 0.35 * R, top - 0.05 * R), max(2, int(R * 0.08)))
        _line(scr, dark, (cx + sx * 0.95 * R, top + 1.45 * R), (cx + sx * 1.2 * R, top + 1.5 * R), max(2, int(R * 0.06)))
    pygame.draw.rect(scr, dark, (int(cx - 0.4 * R), int(top + 1.7 * R), int(0.8 * R), int(0.45 * R)), max(1, int(R * 0.05)))


def _outfit_torso(scr, cx, cy, R, kind, col, k, top, bottom):
    """Torso + detalhes da roupa. top = y dos ombros; bottom = y do fim do torso."""
    c = shade(col, k)
    dark = shade(darker(col), k)
    hw = 1.25 * R
    rect = pygame.Rect(int(cx - hw), int(top), int(2 * hw), int(bottom - top))
    w = max(2, int(R * 0.06))
    if kind == "moletom":
        pygame.draw.ellipse(scr, dark, (int(cx - 0.8 * R), int(top - 0.25 * R), int(1.6 * R), int(0.6 * R)))
    raw = col
    if kind == "colete":
        raw = (236, 238, 244)
    elif kind == "avental":
        raw = lerp(col, (250, 250, 250), 0.75)
    pygame.draw.rect(scr, shade(raw, k), rect, border_radius=int(0.5 * R))
    sh = shade(darker(raw, 0.9), k)
    pygame.draw.rect(scr, sh, (int(cx + 0.92 * R), int(top + 0.45 * R), int(0.26 * R), int(bottom - top - 0.9 * R)),
                     border_radius=int(0.13 * R))                                    # sombra lateral (volume)
    if kind == "moletom":
        pygame.draw.rect(scr, dark, (int(cx - 0.6 * R), int(top + 1.2 * R), int(1.2 * R), int(0.7 * R)), 2, border_radius=int(0.2 * R))
        _line(scr, shade(lighter(col, 0.5), k), (cx - 0.25 * R, top + 0.3 * R), (cx - 0.25 * R, top + 0.9 * R), w)
        _line(scr, shade(lighter(col, 0.5), k), (cx + 0.25 * R, top + 0.3 * R), (cx + 0.25 * R, top + 0.9 * R), w)
        pygame.draw.rect(scr, dark, (int(cx - hw + 0.1 * R), int(bottom - 0.3 * R), int(2 * hw - 0.2 * R), int(0.22 * R)),
                         border_radius=int(0.1 * R))                                # barra do moletom
    elif kind in ("blazer", "terno"):
        shirt = shade((250, 250, 255) if kind == "terno" or col != (245, 245, 250) else (60, 80, 150), k)
        if kind == "blazer":
            shirt = shade((70, 100, 190), k)
        pygame.draw.polygon(scr, shirt, [(int(cx - 0.45 * R), int(top)), (int(cx + 0.45 * R), int(top)), (int(cx), int(top + 1.4 * R))])
        _line(scr, dark, (cx - 0.45 * R, top), (cx, top + 1.4 * R), w)
        _line(scr, dark, (cx + 0.45 * R, top), (cx, top + 1.4 * R), w)
        if kind == "terno":
            pygame.draw.polygon(scr, shade((0, 190, 220), k), [(int(cx), int(top + 0.25 * R)), (int(cx - 0.14 * R), int(top + 0.55 * R)),
                                                              (int(cx), int(top + 1.5 * R)), (int(cx + 0.14 * R), int(top + 0.55 * R))])
        pygame.draw.circle(scr, dark, (int(cx), int(top + 1.8 * R)), max(2, int(0.06 * R)))
        _line(scr, dark, (cx - 1.0 * R, top + 1.7 * R), (cx - 0.55 * R, top + 1.7 * R), max(1, w - 1))   # bolso
    elif kind == "jaleco":
        _line(scr, dark, (cx, top + 0.2 * R), (cx, bottom), w)
        _line(scr, dark, (cx - 0.5 * R, top), (cx - 0.1 * R, top + 0.8 * R), w)
        _line(scr, dark, (cx + 0.5 * R, top), (cx + 0.1 * R, top + 0.8 * R), w)
        pygame.draw.rect(scr, dark, (int(cx - 1.0 * R), int(top + 0.9 * R), int(0.6 * R), int(0.7 * R)), 2)
        for i in range(3):
            pygame.draw.circle(scr, dark, (int(cx + 0.12 * R), int(top + (1.1 + 0.5 * i) * R)), max(1, int(0.05 * R)))
    elif kind == "uniforme":
        pygame.draw.rect(scr, shade((240, 200, 70), k), (int(cx - hw), int(top + 1.0 * R), int(2 * hw), int(0.25 * R)))
        for sx in (-1, 1):
            pygame.draw.rect(scr, shade((240, 200, 70), k), (int(cx + sx * 1.0 * R - 0.2 * R), int(top), int(0.4 * R), int(0.2 * R)))
        _star4(scr, shade(GOLD, k), cx - 0.6 * R, top + 0.55 * R, int(0.16 * R))
    elif kind == "camiseta":
        _arc(scr, dark, (cx - 0.45 * R, top - 0.3 * R, 0.9 * R, 0.8 * R), math.pi, 2 * math.pi, w)
    elif kind == "kimono":
        _line(scr, dark, (cx - 0.55 * R, top), (cx + 0.2 * R, top + 1.6 * R), w + 1)
        _line(scr, dark, (cx + 0.55 * R, top), (cx - 0.2 * R, top + 1.6 * R), w + 1)
        pygame.draw.rect(scr, shade((40, 40, 60), k), (int(cx - hw), int(top + 1.7 * R), int(2 * hw), int(0.3 * R)))
    elif kind == "colete":
        for sx in (-1, 1):
            panel = [(cx + sx * hw, top + 0.3 * R), (cx + sx * 0.5 * R, top), (cx + sx * 0.06 * R, top + 1.2 * R),
                     (cx + sx * 0.06 * R, bottom - 0.1 * R), (cx + sx * hw, bottom - 0.1 * R)]
            pygame.draw.polygon(scr, c, [(int(a), int(b)) for a, b in panel])
            _line(scr, dark, (cx + sx * 0.5 * R, top), (cx + sx * 0.06 * R, top + 1.2 * R), w)
            _line(scr, dark, (cx + sx * 0.95 * R, top + 1.6 * R), (cx + sx * 0.5 * R, top + 1.6 * R), max(1, w - 1))
        for i in range(3):
            pygame.draw.circle(scr, shade(GOLD, k), (int(cx + 0.18 * R), int(top + (1.4 + 0.45 * i) * R)), max(1, int(0.06 * R)))
        _line(scr, shade((60, 70, 90), k), (cx, top + 0.1 * R), (cx, top + 1.2 * R), max(1, w - 1))
    elif kind == "avental":
        _apron(scr, cx, R, top, bottom, c, k)


def draw_look(scr, ch, mood="neutro", cx=550, feet_y=470, R=40, k=1.0, bob=0, bust=False, blink=False, mouth=0,
              t=0.0, breath=0):
    """Desenha um humano a partir do dict de visual (skin/hair/acc/outfit/color) - usado por draw_character."""
    cy = (feet_y if bust else feet_y - int(5.9 * R)) + bob
    raw_skin = ch["skin"]
    skin = shade(raw_skin, k)
    hstyle, hcol = ch["hair"]
    hc = shade(hcol, k)
    kind, ocol = ch["outfit"]
    acc = ch.get("acc", ())
    ucol = tuple(ch.get("color", (80, 130, 255)))
    if not bust:
        bottom0 = cy + 3.7 * R
        pc = shade(PANTS if kind != "kimono" else (50, 50, 74), k)
        for sx in (-1, 1):                                                       # pernas e sapatos
            pygame.draw.rect(scr, pc, (int(cx + sx * 0.55 * R - 0.42 * R), int(bottom0 - 0.2 * R), int(0.84 * R), int(2.2 * R)),
                             border_radius=int(0.2 * R))
            sx0 = int(cx + sx * 0.6 * R - 0.55 * R)
            pygame.draw.ellipse(scr, shade((30, 30, 40), k), (sx0, int(cy + 5.6 * R), int(1.1 * R), int(0.4 * R)))
            pygame.draw.line(scr, shade((90, 96, 120), k), (sx0 + int(0.2 * R), int(cy + 5.95 * R)),
                             (sx0 + int(0.9 * R), int(cy + 5.95 * R)), max(1, int(R * 0.05)))
    cy += breath
    top = cy + 1.1 * R
    bottom = cy + 3.7 * R
    _hair_back(scr, cx, cy, R, hstyle, hc)
    sleeve = ocol
    if kind == "colete":
        sleeve = (226, 228, 236)
    elif kind == "avental":
        sleeve = lerp(ocol, (250, 250, 250), 0.75)
    arm = shade(darker(sleeve, 0.86), k)
    cuff = shade(darker(sleeve, 0.7), k)
    for sx in (-1, 1):                                                           # bracos
        pygame.draw.rect(scr, arm, (int(cx + sx * 1.5 * R - 0.28 * R), int(top + 0.05 * R), int(0.56 * R), int(2.4 * R)),
                         border_radius=int(0.28 * R))
        pygame.draw.rect(scr, cuff, (int(cx + sx * 1.5 * R - 0.28 * R), int(top + 2.0 * R), int(0.56 * R), int(0.2 * R)))
        hand = shade((250, 250, 255), k) if "luvas" in acc else skin
        pygame.draw.circle(scr, hand, (int(cx + sx * 1.5 * R), int(top + 2.5 * R)), int(0.3 * R))
    pygame.draw.rect(scr, skin, (int(cx - 0.3 * R), int(cy + 0.7 * R), int(0.6 * R), int(0.6 * R)))     # pescoco
    pygame.draw.rect(scr, shade(darker(raw_skin, 0.82), k), (int(cx - 0.3 * R), int(cy + 0.86 * R), int(0.6 * R), int(0.14 * R)))
    _outfit_torso(scr, cx, cy, R, kind, ocol, k, top, bottom)
    _body_acc(scr, cx, cy, R, acc, k, top, bottom, ucol, bust)
    pygame.draw.circle(scr, skin, (int(cx - 1.0 * R), int(cy + 0.1 * R)), int(0.2 * R))                # orelhas
    pygame.draw.circle(scr, skin, (int(cx + 1.0 * R), int(cy + 0.1 * R)), int(0.2 * R))
    pygame.draw.circle(scr, skin, (int(cx), int(cy)), int(R))                                            # cabeca
    _arc(scr, shade(darker(raw_skin, 0.8), k), (cx - 0.09 * R, cy + 0.12 * R, 0.18 * R, 0.16 * R),      # nariz
         math.pi + 0.5, 2 * math.pi - 0.5, max(1, int(R * 0.05)))
    _hair_front(scr, cx, cy, R, hstyle, hc, k)
    draw_face(scr, cx, cy, R, mood, k, blink, mouth, t)
    _accessories(scr, cx, cy, R, acc, k, ucol)


def draw_character(scr, cid, mood="neutro", cx=550, feet_y=470, R=40, k=1.0, bob=0, bust=False, t=None,
                   talking=False, blink=None, mouth=None):
    """Desenha o personagem `cid` em pe (feet_y = chao). bust=True: so cabeca e ombros
    (feet_y passa a ser o y do CENTRO da cabeca). Humores: story.MOODS. t (s) anima piscar/fala/
    respiracao; blink/mouth forcam o quadro."""
    ch = story.CHARACTERS.get(cid)
    if ch is None or cid == "narrador":
        return
    b, m = anim_frame(cid, t, talking)
    if blink is not None:
        b = bool(blink)
    if mouth is not None:
        m = 1 if mouth else 0
    tt = t or 0.0
    if cid == "ze" or ch["outfit"][0] == "robo":
        return draw_robot(scr, cx, feet_y if not bust else feet_y + int(2.2 * R), R, mood, k, ch, bob, b, m, tt)
    breath = 0
    if t is not None and not talking and not bust:
        breath = -1 if math.sin(t * 2.2 + _phase(cid)) > 0.3 else 0
    if STYLE == "pixel":
        import portraits_pixel as PX
        if PX.supports(cid):
            return PX.draw(scr, cid, mood, cx, feet_y, R, k, bob, bust, b, m, tt, breath)
    draw_look(scr, ch, mood, cx, feet_y, R, k, bob, bust, b, m, tt, breath)


_LED = {"robo": (0, 230, 255), "neutro": (0, 230, 255), "feliz": (110, 240, 130), "susto": (255, 90, 80),
        "triste": (80, 120, 255), "bravo": (255, 90, 80), "pensando": (255, 214, 90), "suor": (255, 214, 90),
        "cansado": (255, 160, 60), "espirro": (255, 214, 90), "calmo": (110, 240, 130), "corada": (255, 120, 170),
        "convencida": (200, 130, 255), "convencido": (200, 130, 255),
        "determinado": (255, 130, 40), "maravilhado": (255, 236, 140), "malicioso": (190, 80, 255),
        "sonolento": (70, 90, 190), "chorando": (90, 170, 255), "gritando": (255, 50, 50),
        "piscando": (110, 240, 210), "euforico": (140, 255, 120)}


def draw_robot(scr, cx, base_y, R, mood="robo", k=1.0, ch=None, bob=0, blink=False, mouth=0, t=0.0):
    """Robo-aspirador (disco com LED, chinelo preso por fita). base_y = chao. blink = LED vira um
    traco; mouth = quadro de fala (LED claro + ondas de som). Variante (C8, Ze Perfeito): personagem
    robo SEM "chinelo" em acc sai sem chinelo e sem fita, com a tampa na cor da roupa."""
    led_raw = tuple(ch["led"]) if ch is not None and ch.get("led") else _LED.get(mood, (0, 230, 255))   # C10: LED fixo
    led = shade(led_raw, k)
    y = base_y + bob
    w = int(2.7 * R)
    pygame.draw.ellipse(scr, shade((10, 14, 26), k), (int(cx - w * 0.6), int(y - 0.18 * R), int(w * 1.2), int(0.3 * R)))   # sombra
    slipper = ch is None or "chinelo" in ch.get("acc", ())
    body = shade((150, 160, 175) if slipper else tuple(ch["outfit"][1]), k)
    pygame.draw.ellipse(scr, shade((90, 100, 116), k), (int(cx - w / 2), int(y - 0.95 * R), w, int(0.9 * R)))            # base
    for i in range(5):                                                                                                    # grade lateral
        x = cx - 0.8 * R + i * 0.4 * R
        _line(scr, shade((70, 78, 92), k), (x, y - 0.55 * R), (x, y - 0.3 * R), max(1, int(R * 0.05)))
    pygame.draw.ellipse(scr, body, (int(cx - w / 2), int(y - 1.35 * R), w, int(0.9 * R)))                                 # tampa
    top = (205, 212, 224) if slipper else lighter(tuple(ch["outfit"][1]), 0.25)
    pygame.draw.ellipse(scr, shade(top, k), (int(cx - w / 2 + 0.2 * R), int(y - 1.3 * R), int(w - 0.4 * R), int(0.4 * R)))
    pygame.draw.ellipse(scr, shade((34, 42, 62), k), (int(cx - 0.6 * R), int(y - 1.25 * R), int(1.2 * R), int(0.6 * R)))   # visor
    if blink:
        pygame.draw.rect(scr, led, (int(cx - 0.22 * R), int(y - 0.98 * R), int(0.44 * R), max(2, int(0.07 * R))))
    else:
        rr = max(3, int((0.25 if mouth else 0.2) * R))
        pygame.draw.circle(scr, lighter(led, 0.35) if mouth else led, (int(cx), int(y - 0.95 * R)), rr)
        pygame.draw.circle(scr, lighter(led, 0.6), (int(cx), int(y - 0.98 * R)), max(1, int(0.08 * R)))
    if mouth:
        for i in range(2):
            _arc(scr, led, (cx + 0.6 * R + i * 0.2 * R, y - 1.25 * R - i * 0.1 * R, 0.3 * R + i * 0.2 * R, 0.6 * R + i * 0.2 * R),
                 -1.0, 1.0, max(1, int(R * 0.06)))
    pygame.draw.ellipse(scr, led, (int(cx - w / 2), int(y - 1.35 * R), w, int(0.9 * R)), 2)
    for sx in (-1, 1):                                                                                                    # rodinhas
        pygame.draw.circle(scr, shade((30, 34, 46), k), (int(cx + sx * 0.95 * R), int(y - 0.12 * R)), max(2, int(0.2 * R)))
        pygame.draw.circle(scr, shade((90, 96, 110), k), (int(cx + sx * 0.95 * R), int(y - 0.12 * R)), max(1, int(0.07 * R)))
    if slipper:                                                                                                         # chinelo preso por fita
        cxl, cyl = cx + int(0.55 * R), y - 1.4 * R
        pygame.draw.ellipse(scr, shade((230, 190, 90), k), (int(cxl - 0.5 * R), int(cyl - 0.32 * R), int(1.0 * R), int(0.5 * R)))
        pygame.draw.ellipse(scr, shade((190, 70, 60), k), (int(cxl - 0.25 * R), int(cyl - 0.3 * R), int(0.5 * R), int(0.3 * R)), 2)
        _line(scr, shade((190, 190, 195), k), (cxl - 0.6 * R, cyl - 0.35 * R), (cxl + 0.55 * R, cyl + 0.2 * R), max(2, int(R * 0.1)))
        _line(scr, shade((190, 190, 195), k), (cx - 0.9 * R, y - 0.9 * R), (cx - 0.3 * R, y - 1.35 * R), max(2, int(R * 0.1)))
    pygame.draw.line(scr, shade((90, 100, 116), k), (int(cx - 0.4 * R), int(y - 1.35 * R)), (int(cx - 0.8 * R), int(y - 1.7 * R)), 2)
    pygame.draw.circle(scr, led, (int(cx - 0.8 * R), int(y - 1.72 * R)), max(2, int(0.1 * R)))
    if mood == "chorando":
        for i, sx in enumerate((-1, 1)):
            dy = ((t * 1.6 + i * 0.5) % 1.0) * 0.5 * R
            pygame.draw.circle(scr, shade(TEAR, k), (int(cx + sx * 0.5 * R), int(y - 0.7 * R + dy)), max(2, int(0.08 * R)))
    elif mood == "bravo":
        _line(scr, shade((220, 60, 60), k), (cx + 0.9 * R, y - 2.0 * R), (cx + 1.1 * R, y - 1.8 * R), max(2, int(R * 0.07)))
        _line(scr, shade((220, 60, 60), k), (cx + 1.1 * R, y - 2.0 * R), (cx + 0.9 * R, y - 1.8 * R), max(2, int(R * 0.07)))
    _mood_decor(scr, mood, cx, y - 1.5 * R, R * 0.85, k, t)


def draw_narrator_icon(scr, rect, k=1.0):
    """Moldura/icone de narracao (livro aberto com aspas) dentro de rect."""
    r = pygame.Rect(rect)
    cx, cy = r.center
    col = shade((150, 170, 200), k)
    pygame.draw.rect(scr, shade((18, 30, 56), k), r.inflate(-24, -40), border_radius=10)
    pygame.draw.rect(scr, col, r.inflate(-24, -40), 3, border_radius=10)
    pw = max(8, r.w // 4)
    ph = r.h // 3
    for sx in (-1, 1):
        page = [(cx, cy - ph // 2 + 4), (cx + sx * pw, cy - ph // 2 - 4), (cx + sx * pw, cy + ph // 2 - 4), (cx, cy + ph // 2 + 4)]
        pygame.draw.polygon(scr, shade((225, 235, 250), k), page)
        pygame.draw.polygon(scr, col, page, 2)
        for i in range(3):
            y = cy - ph // 2 + 12 + i * (ph // 4)
            _line(scr, shade((120, 140, 175), k), (cx + sx * 6, y + 2), (cx + sx * (pw - 6), y - 2), 2)
    pygame.draw.circle(scr, shade(GOLD, k), (cx, cy - ph // 2 - 14), 5)


def draw_bust(scr, rect, cid, mood, t=None, talking=False, blink=None, mouth=None):
    """Retrato da caixa de dialogo: moldura + fundo + busto do personagem (recortado)."""
    r = pygame.Rect(rect)
    ch = story.CHARACTERS.get(cid)
    col = tuple(ch["color"]) if ch else (150, 170, 200)
    pygame.draw.rect(scr, (14, 24, 46), r, border_radius=10)
    old = scr.get_clip()
    scr.set_clip(r.inflate(-6, -6).clip(old) if old else r.inflate(-6, -6))
    pygame.draw.circle(scr, lerp((14, 24, 46), col, 0.16), (r.centerx, r.centery + 10), int(r.w * 0.58))
    pygame.draw.circle(scr, lerp((14, 24, 46), col, 0.28), (r.centerx, r.centery + 10), int(r.w * 0.46))
    if cid == "narrador" or ch is None:
        draw_narrator_icon(scr, r)
    elif cid == "ze" or ch["outfit"][0] == "robo":
        b, m = anim_frame(cid, t, talking)
        if blink is not None:
            b = bool(blink)
        if mouth is not None:
            m = 1 if mouth else 0
        draw_robot(scr, r.centerx, r.bottom - 22, int(r.w * 0.27), mood, 1.0, ch, 0, b, m, t or 0.0)
    else:
        R = int(r.w * 0.29)
        draw_character(scr, cid, mood, r.centerx, r.y + int(R * 1.9), R, 1.0, 0, bust=True, t=t, talking=talking,
                       blink=blink, mouth=mouth)
    scr.set_clip(old)
    pygame.draw.rect(scr, col, r, 3, border_radius=10)
    pygame.draw.line(scr, lighter(col, 0.4), (r.x + 12, r.y + 2), (r.x + r.w // 3, r.y + 2), 1)
