# -*- coding: utf-8 -*-
"""Cenarios da Campanha em PIXEL ART (estilo padrao; portraits.SCENES = "pixel").

Tecnica (mesma familia dos personagens de game/portraits_pixel.py)
- Cada cenario e pintado numa tela LOGICA de LW x LH = 367 x 160 px (1/3 do palco 1100 x 478) e
  ampliado UMA vez por vizinho mais proximo (x3) no aquecimento (portraits.get_background ja faz o
  cache LRU da Surface final). Materiais com rampas de 4 tons (luz, base, sombra, sombra profunda;
  a luz puxa para o quente e a sombra para o roxo), contorno escuro, dithering ordenado (Bayer 2x2
  via PixelArray) nas transicoes de gradiente e texturas (tabuas, tijolos, azulejos, metal, tecido).
- Luz: brilhos aditivos em aneis (posterizados) e feixes, pintados na tela logica; vinheta
  multiplicativa logica. Tudo fica com "pixel grosso" de 3 px na tela final.
- Torcida: atlas pequeno de torcedores (rosto com olhos, cabelos, bones, camisas listradas, bracos
  erguidos, faixas) pre-renderizado com random.Random(semente fixa); cada arquibancada so faz blits
  do atlas (versoes ja escurecidas por profundidade).
- Frente (fg_*): pintada na mesma tela logica sobre o colorkey e ampliada x3.
- Animacao (anim_*): por quadro, so Surface.fill em blocos de 3 px (Q) e blits de sprites prontos
  (aquecidos em portraits._warm) - nenhuma Surface por quadro.
- Personagens ficam na faixa x 190..910 / pes em y 466 (logico ~155): o chao ali fica limpo e os
  fundos atras deles um pouco mais escuros/frios para manter o contraste.
Nada de random global: cada cenario usa random.Random(semente propria).
"""
import math
import random

import pygame

import portraits as P

LW, LH, S = 367, 160, 3                 # tela logica e escala (367*3 = 1101 >= 1100; 160*3 = 480 >= 478)
KEY = P.KEY
INK = (20, 16, 30)                      # contorno padrao

_SP = {}                                # sprites desta camada (brilhos em pixel, atlas da torcida)


# ================================================================================ cores
def lerp(a, b, t):
    return P.lerp(a, b, t)


def mul(c, f):
    return (max(0, min(255, int(c[0] * f))), max(0, min(255, int(c[1] * f))), max(0, min(255, int(c[2] * f))))


def ramp(c, warm=(255, 238, 205), cool=(34, 22, 64)):
    """(luz, base, sombra, sombra profunda) com desvio de matiz."""
    c = tuple(c)
    return (lerp(c, warm, 0.30), c, lerp(c, cool, 0.32), lerp(c, cool, 0.60))


# ================================================================================ primitivas logicas
def F(c, col, x, y, w=1, h=1):
    c.fill(col, (int(x), int(y), int(w), int(h)))


def outline_rect(c, col, x, y, w, h):
    pygame.draw.rect(c, col, (int(x), int(y), int(w), int(h)), 1)


_BAYER = ((0, 0, 0), (1, 1, 2), (2, 0, 1), (3, 1, 0))     # (ordem, dy, dx): limiar Bayer 2x2


def dith(c, rect, col, level):
    """Pinta `col` em level/4 dos pixels de rect (padrao Bayer 2x2 alinhado na tela)."""
    if level <= 0:
        return
    x, y, w, h = [int(v) for v in rect]
    if level >= 4:
        c.fill(col, (x, y, w, h))
        return
    r = pygame.Rect(x, y, w, h).clip(c.get_clip())            # PixelArray ignora o clip: recorta aqui
    if not r.w or not r.h:
        return
    x, y, x1, y1 = r.x, r.y, r.right, r.bottom
    m = c.map_rgb(col)
    pa = pygame.PixelArray(c)
    try:
        for order, dy, dx in _BAYER:
            if order < level:
                sx = x + ((dx - x) % 2)
                sy = y + ((dy - y) % 2)
                if sx < x1 and sy < y1:
                    pa[sx:x1:2, sy:y1:2] = m
    finally:
        pa.close()


def grad(c, rect, cols, dither=True):
    """Gradiente vertical por faixas (cols de cima para baixo) com 3 niveis de dithering entre elas."""
    x, y, w, h = [int(v) for v in rect]
    n = len(cols) - 1
    if n <= 0:
        c.fill(cols[0], (x, y, w, h))
        return
    for i in range(h):
        t = i * n / float(max(1, h - 1))
        k = min(n - 1, int(t))
        fr = t - k
        lv = int(fr * 5)
        if not dither:
            lv = 0 if fr < 0.5 else 4
        if lv >= 4:
            c.fill(cols[k + 1], (x, y + i, w, 1))
        else:
            c.fill(cols[k], (x, y + i, w, 1))
            if lv > 0:
                dith(c, (x, y + i, w, 1), cols[k + 1], lv)


def hgrad(c, rect, cols):
    x, y, w, h = [int(v) for v in rect]
    n = len(cols) - 1
    for i in range(w):
        t = i * n / float(max(1, w - 1))
        k = min(n - 1, int(t))
        fr = t - k
        lv = int(fr * 5)
        c.fill(cols[k + 1] if lv >= 4 else cols[k], (x + i, y, 1, h))
        if 0 < lv < 4:
            dith(c, (x + i, y, 1, h), cols[k + 1], lv)


def box(c, rect, rp, outline=INK, bevel=True):
    """Bloco com rampa: base, aresta de luz em cima/esquerda, sombra embaixo/direita, contorno."""
    x, y, w, h = [int(v) for v in rect]
    c.fill(rp[1], (x, y, w, h))
    if bevel and w > 2 and h > 2:
        c.fill(rp[0], (x, y, w, 1))
        c.fill(rp[0], (x, y, 1, h))
        c.fill(rp[2], (x, y + h - 1, w, 1))
        c.fill(rp[2], (x + w - 1, y, 1, h))
    if outline is not None:
        pygame.draw.rect(c, outline, (x - 1, y - 1, w + 2, h + 2), 1)


def speckle(c, rect, cols, n, rng):
    x, y, w, h = [int(v) for v in rect]
    for _ in range(n):
        c.fill(rng.choice(cols), (x + rng.randrange(max(1, w)), y + rng.randrange(max(1, h)), 1, 1))


def line(c, col, a, b):
    pygame.draw.line(c, col, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 1)


def text(c, s, x, y, col, shadow=None):
    if shadow is not None:
        P._pixtext(c, s, x + 1, y + 1, 1, shadow)
    return P._pixtext(c, s, x, y, 1, col)


def text_w(s):
    return P.pixtext_w(s, 1)


# ---------------------------------------------------------------------------- luz
def _glow_sp(r, col, steps):
    key = ("pglow", r, col, steps)
    sp = _SP.get(key)
    if sp is None:
        sp = pygame.Surface((2 * r + 1, 2 * r + 1))
        sp.fill((0, 0, 0))
        for i in range(steps):
            rr = r * (1.0 - i / float(steps))
            k = (i + 1) / float(steps)
            pygame.draw.circle(sp, mul(col, 0.18 + 0.82 * k * k), (r, r), max(1, int(rr)))
        # o anel externo sai mais fraco e "pontilhado" (dither) para nao ficar degrau duro
        _SP[key] = sp
    return sp


def glow(c, center, r, col, steps=4):
    """Brilho aditivo em aneis (posterizado) na tela logica."""
    sp = _glow_sp(int(r), tuple(col), steps)
    c.blit(sp, (int(center[0]) - int(r), int(center[1]) - int(r)), special_flags=pygame.BLEND_RGB_ADD)


def glow_ellipse(c, rect, col, steps=3):
    """Brilho eliptico (reflexo no chao) em faixas."""
    x, y, w, h = [int(v) for v in rect]
    sp = pygame.Surface((w, h))
    sp.fill((0, 0, 0))
    for i in range(steps):
        f = 1.0 - i / float(steps)
        k = (i + 1) / float(steps)
        ew, eh = max(2, int(w * f)), max(2, int(h * f))
        pygame.draw.ellipse(sp, mul(col, k), ((w - ew) // 2, (h - eh) // 2, ew, eh))
    c.blit(sp, (x, y), special_flags=pygame.BLEND_RGB_ADD)


def beam(c, top, bottom, w_top, w_bot, col, steps=3, fade=0.15):
    P._cone(c, top, bottom, w_top, w_bot, col, steps, fade)


def streak(c, x, y0, y1, w, col, steps=3):
    """Reflexo vertical (luz no piso encerado): faixa aditiva que afina e some para baixo."""
    h = int(y1 - y0)
    if h <= 1:
        return
    sp = pygame.Surface((int(w), h))
    sp.fill((0, 0, 0))
    for i in range(steps):
        f = 1.0 - i / float(steps)
        ww = max(1, int(w * f))
        sp.fill(mul(col, (i + 1) / float(steps)), ((int(w) - ww) // 2, 0, ww, h))
    g = pygame.Surface((int(w), h))
    grad(g, (0, 0, int(w), h), [(255, 255, 255), (150, 150, 150), (60, 60, 60), (0, 0, 0)])
    sp.blit(g, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    c.blit(sp, (int(x - w // 2), int(y0)), special_flags=pygame.BLEND_RGB_ADD)


_VIG = {}


def vignette(c, strength=0.5, top=0.6):
    v = _VIG.get((strength, top))
    if v is None:
        v = pygame.Surface((LW, LH))
        v.fill((255, 255, 255))
        band = 70
        for i in range(band):
            f = 1.0 - strength * (1.0 - i / float(band)) ** 2
            col = (int(255 * f),) * 3
            v.fill(col, (i, 0, 1, LH), special_flags=pygame.BLEND_RGB_MULT)
            v.fill(col, (LW - 1 - i, 0, 1, LH), special_flags=pygame.BLEND_RGB_MULT)
        bh = 40
        for i in range(bh):
            f = 1.0 - strength * top * (1.0 - i / float(bh)) ** 2
            v.fill((int(255 * f),) * 3, (0, i, LW, 1), special_flags=pygame.BLEND_RGB_MULT)
        _VIG[(strength, top)] = v
    c.blit(v, (0, 0), special_flags=pygame.BLEND_RGB_MULT)


def tint(c, rect, col):
    """Multiplica a area por col (sombra/clima)."""
    c.fill(col, pygame.Rect(rect), special_flags=pygame.BLEND_RGB_MULT)


def add(c, rect, col):
    c.fill(col, pygame.Rect(rect), special_flags=pygame.BLEND_RGB_ADD)


# ---------------------------------------------------------------------------- texturas
def bricks(c, rect, rp, bw=9, bh=4, rng=None, mortar=None, chip=0.08):
    """Parede de tijolos: argamassa escura, tijolo com tom variando, aresta de luz em cima."""
    x, y, w, h = [int(v) for v in rect]
    rng = rng or random.Random(7)
    mortar = mortar or rp[3]
    c.fill(mortar, (x, y, w, h))
    old = c.get_clip()
    c.set_clip(pygame.Rect(x, y, w, h))
    for r, yy in enumerate(range(y, y + h, bh)):
        off = 0 if r % 2 == 0 else -(bw // 2)
        for xx in range(x + off, x + w, bw):
            tone = rp[1] if rng.random() < 0.6 else (rp[2] if rng.random() < 0.6 else lerp(rp[1], rp[0], 0.5))
            c.fill(tone, (xx, yy, bw - 1, bh - 1))
            c.fill(lerp(tone, rp[0], 0.55), (xx, yy, bw - 1, 1))
            if rng.random() < chip:
                c.fill(rp[2], (xx + rng.randrange(bw - 1), yy + 1, 1, 1))
    c.set_clip(old)


def planks_v(c, rect, rp, pw=6, rng=None, grain=True):
    """Tabuas verticais (paredes de madeira)."""
    x, y, w, h = [int(v) for v in rect]
    rng = rng or random.Random(5)
    for i, xx in enumerate(range(x, x + w, pw)):
        tone = (rp[1], lerp(rp[1], rp[2], 0.5), lerp(rp[1], rp[0], 0.35))[rng.randrange(3)]
        c.fill(tone, (xx, y, pw, h))
        c.fill(rp[3], (xx + pw - 1, y, 1, h))
        c.fill(lerp(tone, rp[0], 0.45), (xx, y, 1, h))
        if grain:
            for _ in range(h // 9):
                gy = y + rng.randrange(h)
                c.fill(lerp(tone, rp[2], 0.6), (xx + 1 + rng.randrange(max(1, pw - 2)), gy, 1, rng.randint(2, 5)))


def tiles(c, rect, rp, tw=8, th=8, rng=None, grout=None, gloss=True, var=0.25):
    x, y, w, h = [int(v) for v in rect]
    rng = rng or random.Random(9)
    grout = grout or rp[2]
    c.fill(grout, (x, y, w, h))
    old = c.get_clip()
    c.set_clip(pygame.Rect(x, y, w, h))
    for yy in range(y, y + h, th):
        for xx in range(x, x + w, tw):
            tone = rp[1] if rng.random() > var else lerp(rp[1], rp[2], 0.35)
            c.fill(tone, (xx, yy, tw - 1, th - 1))
            if gloss:
                c.fill(rp[0], (xx, yy, 2, 1))
                c.fill(rp[0], (xx, yy, 1, 2))
    c.set_clip(old)


def corrugated(c, rect, rp, period=4):
    x, y, w, h = [int(v) for v in rect]
    seq = (rp[0], rp[1], rp[2], rp[1]) if period == 4 else (rp[0], rp[1], rp[1], rp[2], rp[2], rp[1])
    for i in range(w):
        c.fill(seq[(x + i) % len(seq)], (x + i, y, 1, h))


def rivets(c, xs, ys, rp):
    for xx in xs:
        for yy in ys:
            c.fill(rp[0], (xx, yy, 1, 1))
            c.fill(rp[3], (xx + 1, yy + 1, 1, 1))


# ---------------------------------------------------------------------------- piso em perspectiva
def floor_rows(y0, y1, n, gamma=1.55):
    """Linhas (y) das juntas de um piso em perspectiva: estreitas no fundo, largas na frente."""
    ys = []
    for i in range(n + 1):
        t = (i / float(n)) ** gamma
        ys.append(int(round(y0 + (y1 - y0) * t)))
    return ys


def persp_x(x_bottom, y, y0, y1, vx=LW / 2.0, depth=0.42):
    """x na altura y de uma linha que vai de (vx + (xb-vx)*depth, y0) ate (xb, y1)."""
    t = (y - y0) / float(max(1, y1 - y0))
    k = depth + (1.0 - depth) * t
    return vx + (x_bottom - vx) * k


def wood_floor(c, y0, y1, rp, rng, rows=11, seam=None, plank=(26, 70)):
    """Piso de tabuas corridas (como quadra de madeira): fileiras horizontais que alargam para a
    frente, tom por tabua, emendas desencontradas, veios e pontinhos de no."""
    seam = seam or rp[3]
    ys = floor_rows(y0, y1, rows)
    tones = (rp[1], lerp(rp[1], rp[0], 0.28), lerp(rp[1], rp[2], 0.35), lerp(rp[1], rp[0], 0.12),
             lerp(rp[1], rp[2], 0.15))
    for r in range(rows):
        ya, yb = ys[r], ys[r + 1]
        hh = max(1, yb - ya)
        x = -rng.randint(0, plank[1])
        scale_ = 0.45 + 0.55 * (r / float(max(1, rows - 1)))
        while x < LW:
            pl = int(rng.randint(*plank) * scale_ * 1.6)
            tone = rng.choice(tones)
            c.fill(tone, (x, ya, pl, hh))
            if hh >= 3:
                c.fill(lerp(tone, rp[0], 0.35), (x, ya + 1, pl, 1))          # brilho da borda da tabua
            for _ in range(max(1, pl // 9)):                                   # veios
                gx = x + rng.randrange(max(1, pl))
                gy = ya + 1 + rng.randrange(max(1, hh - 1))
                c.fill(lerp(tone, rp[2], 0.55), (gx, gy, rng.randint(3, 8), 1))
            if rng.random() < 0.25 and hh >= 3:                                 # no da madeira
                c.fill(rp[2], (x + rng.randrange(max(1, pl)), ya + hh // 2, 1, 1))
            c.fill(seam, (x, ya, 1, hh))                                       # emenda
            x += pl
        c.fill(seam, (0, ya, LW, 1))


def persp_lines(c, y0, y1, col, n, spread, depth=0.42, vx=LW / 2.0):
    for i in range(-n, n + 1):
        xb = vx + i * spread
        line(c, col, (persp_x(xb, y0, y0, y1, vx, depth), y0), (xb, y1))


def checker_floor(c, y0, y1, ca, cb, cols=14, rows=7, depth=0.45, vx=LW / 2.0, gamma=1.4):
    """Piso xadrez em perspectiva; `cols` = ladrilhos visiveis na linha de baixo."""
    ys = floor_rows(y0, y1, rows, gamma)
    tw = LW / float(cols)
    n = int(LW / depth / tw / 2) + 2
    for r in range(rows):
        ya, yb = ys[r], ys[r + 1]
        for k in range(-n, n):
            xa_b = vx + (k - 0.5) * tw
            xb_b = vx + (k + 0.5) * tw
            pts = [(persp_x(xa_b, ya, y0, y1, vx, depth), ya), (persp_x(xb_b, ya, y0, y1, vx, depth), ya),
                   (persp_x(xb_b, yb, y0, y1, vx, depth), yb), (persp_x(xa_b, yb, y0, y1, vx, depth), yb)]
            pygame.draw.polygon(c, ca if (r + k) % 2 else cb, pts)


# ================================================================================ TORCIDA (atlas)
SKINS = ((246, 208, 170), (226, 178, 136), (196, 140, 98), (150, 98, 66), (108, 70, 50))
HAIRS = ((40, 28, 24), (86, 52, 30), (22, 20, 26), (214, 176, 96), (160, 70, 40), (176, 176, 184), (60, 40, 30))
SHIRTS = ((226, 64, 64), (64, 126, 232), (246, 204, 74), (80, 196, 120), (176, 96, 222), (236, 236, 242),
          (255, 140, 56), (30, 190, 220), (238, 110, 160), (60, 70, 96))
EYE = (36, 24, 30)
CELL_W, CELL_H = 7, 11
SMALL_W, SMALL_H = 4, 6
ATLAS_N = 72

# rosto/corpo (sentado, visto de frente). Letras: h cabelo, H luz do cabelo, s pele, S sombra da pele,
# e olho, m boca, t camisa, L luz da camisa, T sombra da camisa, c 2a cor (gola/listra/bone), k mao
_BODY = (
    ".......",
    ".......",
    "..hHh..",
    ".hhhhh.",
    ".seseS.",
    ".ssmS..",
    "..sS...",
    ".LtctT.",
    "TLtttTT",
    "TLtttTT",
    "kLtttTk",
)


def _person(sp, ox, oy, rng, shirts=SHIRTS, mood=None):
    skin = rng.choice(SKINS)
    hair = rng.choice(HAIRS)
    shirt = rng.choice(shirts)
    sec = rng.choice(((236, 236, 242), (30, 30, 40), rng.choice(SHIRTS), lerp(shirt, (255, 255, 255), 0.5)))
    style = rng.choices(("curto", "longo", "careca", "bone", "coque", "black", "franja"), (5, 4, 1, 2, 1, 2, 2))[0]
    stripes = rng.random() < 0.18
    arms = rng.choices(("baixo", "cima", "um", "faixa"), (14, 4, 2, 1))[0] if mood is None else mood
    rows = [list(r) for r in _BODY]
    if style == "longo":
        for y in (4, 5, 6):
            rows[y][1] = "h"
        rows[4][5] = "h"
        rows[5][5] = "h"
        rows[6][5] = "h"
    elif style == "careca":
        rows[2] = list(".......")
        rows[3] = list(".sHhHS.") if rng.random() < 0.5 else list(".sssSS.")
    elif style == "bone":
        rows[2] = list("..ccc..")
        rows[3] = list(".ccccc" + ("c" if rng.random() < 0.5 else "."))
    elif style == "coque":
        rows[1][3] = "h"
    elif style == "black":
        rows[1] = list("..hhh..")
        rows[2] = list(".hHhhh.")
        rows[3] = list("hhhhhhh")
        rows[4][0] = "h"
        rows[4][6] = "h"
    elif style == "franja":
        rows[3] = list("hhhhhh.")
        rows[4][1] = "h"
    if rng.random() < 0.35:
        rows[5][3] = "s"                               # boca fechada (nem todo mundo sorri)
    if stripes:
        rows[8] = [("c" if ch in "tLT" else ch) for ch in rows[8]]
        rows[10] = [("c" if ch in "tLT" else ch) for ch in rows[10]]
    if arms in ("cima", "faixa", "um"):
        sides = (0, 6) if arms != "um" else (rng.choice((0, 6)),)
        for sx in sides:
            for y in (8, 9, 10):
                rows[y][sx] = "."
            rows[1][sx] = "k"
            for y in (2, 3, 4, 5):
                rows[y][sx] = "T" if y > 2 else "t"
            rows[6][sx] = "T"
            rows[7][sx] = "T"
        if arms == "faixa":
            rows[0] = list("ccccccc")
    pal = {"h": hair, "H": lerp(hair, (255, 240, 210), 0.35), "s": skin, "S": lerp(skin, (110, 50, 70), 0.3),
           "e": EYE, "m": lerp(skin, (150, 40, 60), 0.5), "t": shirt, "L": lerp(shirt, (255, 245, 220), 0.3),
           "T": lerp(shirt, (30, 20, 60), 0.3), "c": sec, "k": skin}
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                sp.set_at((ox + x, oy + y), pal[ch])


def _person_small(sp, ox, oy, rng, shirts=SHIRTS):
    skin = rng.choice(SKINS)
    hair = rng.choice(HAIRS)
    shirt = rng.choice(shirts)
    up = rng.random() < 0.18
    rows = [".hh.", ".ss.", "tttt", "tttT", "tTTT", "tttt"]
    if rng.random() < 0.3:
        rows[1] = "hssh" if not up else ".ss."
    if up:
        rows[0] = "khhk"
        rows[1] = "t" + rows[1][1:3] + "t"
    pal = {"h": hair, "s": skin, "t": shirt, "T": lerp(shirt, (30, 20, 60), 0.35), "k": skin}
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                sp.set_at((ox + x, oy + y), pal[ch])


def crowd_atlas(kind="big", shirts=SHIRTS, tag="std"):
    """Atlas (Surface com colorkey KEY) de ATLAS_N torcedores; criado uma vez por (tipo, paleta)."""
    key = ("atlas", kind, tag)
    sp = _SP.get(key)
    if sp is None:
        cw, ch = (CELL_W, CELL_H) if kind == "big" else (SMALL_W, SMALL_H)
        sp = pygame.Surface((cw * ATLAS_N, ch))
        sp.fill(KEY)
        rng = random.Random(4242 if kind == "big" else 2424)
        for i in range(ATLAS_N):
            if kind == "big":
                _person(sp, i * cw, 0, rng, shirts)
            else:
                _person_small(sp, i * cw, 0, rng, shirts)
        sp.set_colorkey(KEY)
        _SP[key] = sp
    return sp


def _faded(atlas, f, tint_col, key):
    """Copia do atlas escurecida (profundidade): MULT pela cor `tint_col*f`; o colorkey e relido."""
    k = ("afade",) + key + (f, tint_col)
    sp = _SP.get(k)
    if sp is None:
        sp = atlas.copy()
        sp.set_colorkey(None)
        sp.fill(mul(tint_col, f), special_flags=pygame.BLEND_RGB_MULT)
        probe = pygame.Surface((1, 1))
        probe.fill(KEY)
        probe.fill(mul(tint_col, f), special_flags=pygame.BLEND_RGB_MULT)
        sp.set_colorkey(probe.get_at((0, 0)))
        _SP[k] = sp
    return sp


def bleachers(c, x0, x1, y0, rows, row_h, seat, rng, shirts=SHIRTS, tag="std", empty=0.07,
              fade=(0.55, 0.95), tint_col=(200, 214, 255), kind="big", rail=None, step=6):
    """Arquibancada em degraus com torcida do atlas (fundo para a frente; fileira de tras mais escura)."""
    atlas = crowd_atlas(kind, shirts, tag)
    cw, ch = (CELL_W, CELL_H) if kind == "big" else (SMALL_W, SMALL_H)
    srp = ramp(seat)
    for i in range(rows):
        y = y0 + i * row_h
        f = fade[0] + (fade[1] - fade[0]) * (i / float(max(1, rows - 1)))
        F(c, mul(srp[2], f), x0, y, x1 - x0, row_h)                        # espelho do degrau
        F(c, mul(srp[1], f), x0, y + row_h - 4, x1 - x0, 3)                # assento
        F(c, mul(srp[0], f), x0, y + row_h - 4, x1 - x0, 1)
        F(c, mul(srp[3], f), x0, y + row_h - 1, x1 - x0, 1)
        fa = _faded(atlas, round(f * 20) / 20.0, tint_col, (kind, tag))          # niveis de 0,05: poucas copias
        x = x0 - rng.randint(0, step)
        while x < x1 - 1:
            if rng.random() > empty:
                idx = rng.randrange(ATLAS_N)
                c.blit(fa, (x + rng.randint(-1, 0), y + row_h - ch - (1 if kind == "big" else 0)),
                       (idx * cw, 0, cw, ch))
            x += step + (1 if rng.random() < 0.15 else 0)
        if rail is not None:
            F(c, mul(rail, f), x0, y + row_h - 1, x1 - x0, 1)


# ================================================================================ montagem
def build(surf, painter):
    """Pinta `painter(low)` na tela logica e amplia x3 (vizinho) em surf."""
    low = pygame.Surface((LW, LH))
    low.fill((0, 0, 0))
    painter(low)
    big = pygame.transform.scale(low, (LW * S, LH * S))
    surf.blit(big, (0, 0))


def build_front(painter):
    """(Surface com colorkey, (x, y)) da camada de frente logica ampliada, recortada ao conteudo."""
    low = pygame.Surface((LW, LH))
    low.fill(KEY)
    painter(low)
    low.set_colorkey(KEY)
    r = low.get_bounding_rect()
    if not (r.w and r.h):
        return None
    piece = pygame.Surface((r.w * S, r.h * S))
    pygame.transform.scale(low.subsurface(r), (r.w * S, r.h * S), piece)
    rx, ry = r.x * S, r.y * S
    cut = max(0, ry + piece.get_height() - P.STAGE_H)
    if cut or rx + piece.get_width() > P.STAGE_W:
        w = min(piece.get_width(), P.STAGE_W - rx)
        sub = pygame.Surface((w, piece.get_height() - cut))
        sub.blit(piece, (0, 0))
        piece = sub
    piece.set_colorkey(KEY, pygame.RLEACCEL)
    return piece, (rx, ry)


# ---------------------------------------------------------------------------- animacao (tela final)
def Q(scr, col, x, y, w=1, h=1):
    """Bloco logico (3x3 px por unidade) na tela final, sem Surface."""
    scr.fill(col, (int(x) * S, int(y) * S, int(w) * S, int(h) * S))


def pglow_sprite(r, col, steps=4):
    """Brilho em aneis de pixel grosso para a animacao (logico r, ampliado x3; aquecido no _warm)."""
    key = ("pglow3", r, col, steps)
    sp = _SP.get(key)
    if sp is None:
        lo = _glow_sp(r, col, steps)
        sp = pygame.transform.scale(lo, (lo.get_width() * S, lo.get_height() * S))
        _SP[key] = sp
    return sp


def AG(scr, center, r, col, steps=4):
    """Brilho aditivo de pixel grosso centrado no ponto logico."""
    sp = pglow_sprite(r, col, steps)
    scr.blit(sp, (int(center[0]) * S - r * S, int(center[1]) * S - r * S), special_flags=pygame.BLEND_RGB_ADD)


def flashes(scr, t, pts, rate=0.9, duty=0.07, col=(255, 255, 255)):
    """Flashes de camera (cruz de pixel grosso) em pontos logicos."""
    for i, (x, y) in enumerate(pts):
        ph = (t * rate * (1.0 + (i % 3) * 0.17) + i * 0.618) % 1.0
        if ph < duty:
            Q(scr, col, x - 1, y, 3, 1)
            Q(scr, col, x, y - 1, 1, 3)
            if ph < duty * 0.5:
                Q(scr, mul(col, 0.6), x - 2, y, 1, 1)
                Q(scr, mul(col, 0.6), x + 2, y, 1, 1)
                Q(scr, mul(col, 0.6), x, y - 2, 1, 1)
                Q(scr, mul(col, 0.6), x, y + 2, 1, 1)


def pts(seed, n, rect):
    rng = random.Random(seed)
    x, y, w, h = rect
    return [(x + rng.randint(0, w), y + rng.randint(0, h)) for _ in range(n)]


def motes(scr, t, rect, n, col, seed=0, speed=3.0):
    x, y, w, h = rect
    dim = mul(col, 0.6)
    for i in range(n):
        a = ((i * 7919 + seed * 104729) % 1000) / 1000.0
        b = ((i * 3571 + seed * 7717) % 1000) / 1000.0
        px = x + int(a * w + 3 * math.sin(t * 0.7 + i * 1.7))
        py = y + h - int((b * h + t * speed * (0.6 + 0.1 * (i % 5))) % h)
        Q(scr, col if i % 3 else dim, px, py)


def blink(t, period, duty, phase=0.0):
    return ((t + phase) % period) < duty * period


# ================================================================================ pecas comuns
WOOD = ramp((178, 114, 64))
GOLD = (255, 214, 90)
NEON = (0, 230, 255)
LINE = (238, 226, 204)


def night_sky(c, y1, rng, cols=((6, 10, 26), (12, 20, 44), (22, 34, 66)), stars=40, x0=0, x1=LW):
    grad(c, (x0, 0, x1 - x0, y1), list(cols))
    for _ in range(stars):
        x, y = rng.randrange(x0, x1), rng.randrange(0, max(1, int(y1 * 0.8)))
        b = rng.random()
        F(c, lerp((60, 70, 110), (220, 228, 255), b), x, y)
        if b > 0.93:
            F(c, (120, 130, 170), x - 1, y)
            F(c, (120, 130, 170), x + 1, y)
            F(c, (120, 130, 170), x, y - 1)
            F(c, (120, 130, 170), x, y + 1)


def skyline(c, rng, x0, x1, base, hmin, hmax, rp, win=(250, 206, 110), p=0.25):
    x = x0
    while x < x1:
        w = rng.randint(9, 22)
        h = rng.randint(hmin, hmax)
        F(c, rp[1], x, base - h, w, h)
        F(c, rp[0], x, base - h, 1, h)
        F(c, rp[2], x + w - 1, base - h, 1, h)
        if rng.random() < 0.3:
            F(c, rp[1], x + w // 2, base - h - rng.randint(2, 6), 1, 6)
        for wy in range(base - h + 2, base - 2, 3):
            for wx in range(x + 2, x + w - 2, 3):
                if rng.random() < p:
                    F(c, win if rng.random() < 0.8 else lerp(win, (120, 200, 255), 0.6), wx, wy)
        x += w + rng.randint(0, 2)


def court(c, y0, y1, col=LINE, cx=LW / 2.0):
    """Linhas de quadra em perspectiva: lateral do fundo, meio, circulo e arcos de 3 pontos."""
    F(c, col, 0, y0 + 3, LW, 1)
    line(c, col, (cx, y0 + 3), (cx, y1))
    pygame.draw.ellipse(c, col, (int(cx - 34), y0 + 13, 68, 26), 1)
    pygame.draw.ellipse(c, col, (int(cx - 9), y0 + 22, 18, 8), 1)
    for side in (-1, 1):
        ex = cx + side * 236
        pygame.draw.ellipse(c, col, (int(ex - 120), y0 + 3, 240, 74), 1)
        line(c, col, (cx + side * 180, y0 + 3), (cx + side * 205, y1))


def lamp_head(c, x, y, w=7, warm=(255, 244, 214)):
    box(c, (x - w // 2, y - 2, w, 3), ramp((60, 66, 86)))
    F(c, warm, x - w // 2 + 1, y + 1, w - 2, 1)
    F(c, lerp(warm, (255, 255, 255), 0.6), x - 1, y + 1, 2, 1)


# ================================================================================ GINASIO
def bg_ginasio(c):
    rng = random.Random(5)
    grad(c, (0, 0, LW, 34), [(6, 10, 24), (12, 18, 38), (20, 30, 56)])
    tr = (30, 42, 70)
    for x in range(-37, LW + 37, 37):                                              # trelicas do teto
        line(c, tr, (x, 0), (x + 18, 10))
        line(c, tr, (x + 37, 0), (x + 18, 10))
    F(c, (40, 54, 86), 0, 10, LW, 1)
    F(c, (24, 34, 58), 0, 11, LW, 1)
    bleachers(c, 0, LW, 30, 6, 11, (38, 64, 120), rng, fade=(0.5, 0.92))
    for x in range(0, LW, 46):                                                     # escadas entre setores
        F(c, (22, 30, 50), x + 23, 30, 3, 66)
        F(c, (60, 80, 120), x + 23, 30, 1, 66)
    F(c, (14, 20, 36), 0, 96, LW, 9)                                              # muro com placas
    ads = (("COPA", (0, 210, 240)), ("ASPIRADOR", (255, 214, 90)), ("ZE", (120, 240, 140)), ("SUCATA", (255, 120, 160)))
    x = 2
    i = 0
    while x < LW:
        word, col = ads[i % len(ads)]
        w = text_w(word) + 10
        box(c, (x, 97, w - 2, 7), ramp(lerp((20, 30, 56), col, 0.18)), outline=None)
        text(c, word, x + 4, 98, col, shadow=mul(col, 0.35))
        x += w
        i += 1
    F(c, (0, 200, 230), 0, 104, LW, 1)
    F(c, (8, 12, 22), 0, 105, LW, 1)
    wood_floor(c, 106, LH, WOOD, rng)
    court(c, 106, LH)
    for x, col in ((24, (200, 40, 50)), (70, (30, 90, 200)), (297, (230, 180, 40)), (343, (30, 150, 90))):
        rp = ramp(col)                                                             # flamulas de campeao
        F(c, (60, 70, 90), x - 5, 11, 11, 1)
        F(c, INK, x - 6, 12, 13, 20)
        F(c, rp[1], x - 5, 12, 11, 19)
        F(c, rp[0], x - 5, 12, 2, 19)
        F(c, rp[2], x + 4, 12, 1, 19)
        for k in range(6):
            F(c, rp[1], x - 5 + k, 31 + k, 11 - 2 * k, 1)
            F(c, INK, x - 6 + k, 31 + k, 1, 1)
            F(c, INK, x + 5 - k, 31 + k, 1, 1)
        F(c, GOLD, x - 5, 14, 11, 1)
        F(c, (250, 250, 250), x - 2, 18, 5, 5)
        F(c, rp[1], x - 1, 19, 3, 3)
        F(c, GOLD, x - 3, 26, 7, 1)
    for x in (46, 138, 230, 322):                                                  # refletores
        F(c, (40, 50, 70), x, 0, 1, 3)
        lamp_head(c, x, 4)
        glow(c, (x, 5), 16, (70, 66, 50), 4)
        streak(c, x, 107, 150, 12, (70, 56, 36))
    for x in (92, 184, 276):
        beam(c, (x, 6), (x, 104), 3, 20, (16, 16, 12), 3, 0.15)
    # placar suspenso
    for x in (140, 226):
        F(c, (50, 60, 80), x, 0, 1, 7)
    box(c, (132, 7, 103, 26), ramp((22, 26, 40)), outline=(4, 6, 12))
    F(c, (8, 10, 18), 135, 10, 97, 20)
    outline_rect(c, (0, 160, 190), 134, 9, 99, 22)
    text(c, "CASA", 143, 11, (180, 200, 220))
    text(c, "VIS", 203, 11, (180, 200, 220))
    P._pixtext(c, "03", 140, 18, 2, (255, 96, 70))
    P._pixtext(c, "02", 202, 18, 2, (255, 96, 70))
    text(c, "4", 181, 11, (255, 214, 90))
    glow_ellipse(c, (110, 118, 150, 30), (40, 30, 18))
    vignette(c, 0.45)


_PTS_GIN = pts(51, 16, (6, 34, 354, 56))


def anim_ginasio(scr, t):
    on = blink(t, 1.0, 0.5)
    for y in (21, 25):
        Q(scr, (255, 214, 90) if on else (70, 50, 20), 183, y)
    if (t % 5.3) < 0.07:
        Q(scr, (90, 90, 80), 135, 5, 7, 1)
    flashes(scr, t, _PTS_GIN, 0.6)


# ================================================================================ QUADRA
def fence(c, rect, col, step=4):
    x, y, w, h = rect
    old = c.get_clip()
    c.set_clip(pygame.Rect(rect))
    for k in range(-h, w + h, step):
        line(c, col, (x + k, y), (x + k + h, y + h))
        line(c, col, (x + k + h, y), (x + k, y + h))
    c.set_clip(old)


def bg_quadra(c):
    rng = random.Random(3)
    night_sky(c, 40, rng, stars=36)
    # fundo: setor central atras do alambrado (torcida distante, menor e mais escura)
    bleachers(c, 96, 272, 40, 6, 9, (30, 50, 94), rng, kind="small", fade=(0.35, 0.6), step=4)
    F(c, (16, 24, 44), 96, 94, 176, 4)
    fence(c, (98, 34, 172, 62), (58, 74, 104))
    for x in (98, 140, 183, 226, 269):
        box(c, (x - 1, 32, 2, 66), ramp((70, 84, 110)), outline=None)
    F(c, (80, 96, 124), 96, 33, 176, 1)
    bleachers(c, 0, 100, 38, 5, 12, (40, 70, 130), rng, fade=(0.6, 0.98))
    bleachers(c, 267, LW, 38, 5, 12, (40, 70, 130), rng, fade=(0.6, 0.98))
    for x0 in (0, 267):                                                            # guarda-corpo das laterais
        F(c, (110, 130, 160), x0, 36, 100, 1)
        for xx in range(x0 + 4, x0 + 100, 16):
            F(c, (90, 104, 130), xx, 36, 1, 60)
    F(c, (14, 22, 40), 0, 98, LW, 6)
    F(c, (0, 200, 230), 0, 98, LW, 1)
    F(c, (8, 12, 22), 0, 104, LW, 1)
    wood_floor(c, 105, LH, WOOD, rng)
    court(c, 105, LH)
    # tabela de basquete
    box(c, (129, 59, 3, 41), ramp((120, 130, 150)))
    box(c, (110, 42, 41, 27), ramp((236, 238, 244)))
    outline_rect(c, (210, 60, 50), 123, 52, 15, 11)
    F(c, (180, 186, 200), 110, 67, 41, 1)
    pygame.draw.ellipse(c, (255, 120, 40), (119, 67, 22, 4), 1)
    for i in range(5):
        line(c, (226, 226, 236), (120 + i * 5, 70), (122 + i * 4, 77))
    line(c, (200, 200, 214), (121, 74), (139, 74))
    # tambor da torcida
    box(c, (246, 78, 14, 20), ramp((60, 70, 110)))
    F(c, (230, 230, 236), 246, 77, 14, 2)
    for yy in (82, 88, 94):
        F(c, (200, 170, 70), 246, yy, 14, 1)
    for x in (12, 354):                                                            # postes de luz
        box(c, (x - 1, 8, 3, 30), ramp((50, 62, 90)))
        box(c, (x - 8, 2, 17, 6), ramp((40, 50, 70)))
        for k in range(4):
            F(c, (255, 248, 220), x - 6 + k * 4, 4, 3, 2)
        glow(c, (x, 5), 26, (70, 76, 84), 4)
        streak(c, x * 0.7 + 55, 106, 150, 16, (50, 42, 30))
    glow_ellipse(c, (90, 112, 190, 34), (36, 28, 16))
    vignette(c, 0.42)


_QUADRA_FLAGS = ((110, (220, 70, 70)), (160, (0, 220, 245)), (210, (255, 214, 90)), (260, (100, 214, 110)))
_PTS_QUADRA = pts(31, 8, (4, 40, 90, 56)) + pts(32, 8, (272, 40, 90, 56))


def pennant(scr, x, y, w, h, col, t, ph):
    """Bandeirola com ponta em V balancando (blocos de 3 px)."""
    rp = ramp(col)
    sway = math.sin(t * 2.2 + ph)
    mid = (w - 1) / 2.0
    for k in range(w):
        f = k / float(max(1, w - 1))
        ln = h - max(0, int(5 - abs(k - mid)))                        # recorte em V no meio
        dy = int(round(sway * 1.2 * f))
        colk = rp[0] if k < 2 else (rp[2] if k >= w - 3 else rp[1])
        Q(scr, colk, x + k, y + dy, 1, ln - 1)
        Q(scr, rp[3], x + k, y + dy + ln - 1, 1, 1)
    Q(scr, rp[0], x, y, w, 1)
    Q(scr, rp[3], x + 3, y + 4 + int(round(sway * 0.6)), w - 6, 1)


def anim_quadra(scr, t):
    Q(scr, (120, 130, 150), 100, 6, 196, 1)
    for i, (x, col) in enumerate(_QUADRA_FLAGS):                                       # bandeirolas
        pennant(scr, x, 7, 28, 19, col, t, i * 1.3)
    flashes(scr, t, _PTS_QUADRA, 0.5)


def fg_quadra(c):
    box(c, (334, 140, 31, 15), ramp((70, 80, 104)))                                    # carrinho de bolas
    for k in range(0, 31, 4):
        F(c, (40, 46, 64), 334 + k, 141, 1, 13)
    for i, x in enumerate(range(338, 366, 7)):
        col = ((255, 128, 50), (236, 236, 242))[i % 2]
        rp = ramp(col)
        pygame.draw.circle(c, rp[3], (x, 137), 4)
        pygame.draw.circle(c, rp[1], (x, 137), 3)
        F(c, rp[0], x - 2, 135, 2, 1)
        F(c, rp[2], x + 1, 138, 2, 1)
    for x in (337, 361):
        pygame.draw.circle(c, (18, 20, 28), (x, 156), 2)


# ================================================================================ GARAGEM
def pegboard(c, rect):
    x, y, w, h = rect
    box(c, rect, ramp((92, 74, 54)))
    for yy in range(y + 2, y + h - 1, 3):
        for xx in range(x + 2 + (yy // 3) % 2, x + w - 1, 3):
            F(c, (54, 40, 30), xx, yy)


def bg_garagem(c):
    rng = random.Random(1)
    brick = ramp((86, 60, 66), warm=(255, 210, 170), cool=(20, 16, 40))
    bricks(c, (0, 0, LW, 118), brick, 10, 4, rng)
    tint(c, (0, 0, LW, 118), (150, 160, 200))                                        # parede no escuro
    # portao de enrolar
    gx, gy, gw, gh = 108, 22, 151, 96
    box(c, (gx - 4, gy - 4, gw + 8, gh + 4), ramp((58, 70, 92)))
    slat = ramp((84, 100, 128))
    for yy in range(gy, gy + gh, 5):
        F(c, slat[1], gx, yy, gw, 5)
        F(c, slat[0], gx, yy, gw, 1)
        F(c, slat[2], gx, yy + 3, gw, 1)
        F(c, slat[3], gx, yy + 4, gw, 1)
    for i in range(4):                                                                # janelinhas: rua a noite
        wx = gx + 8 + i * 36
        box(c, (wx - 1, 33, 30, 14), ramp((70, 86, 116)))
        old = c.get_clip()
        c.set_clip(pygame.Rect(wx, 34, 28, 12))
        grad(c, (wx, 34, 28, 12), [(10, 16, 40), (30, 40, 84), (60, 60, 110)])
        for _ in range(5):
            F(c, (200, 210, 240), wx + rng.randrange(28), 34 + rng.randrange(5))
        if i == 2:
            pygame.draw.circle(c, (240, 238, 214), (wx + 21, 37), 2)
            F(c, (30, 40, 84), wx + 22, 36, 1, 1)
        skyline(c, rng, wx - 4, wx + 30, 46, 3, 9, ramp((26, 30, 58)), p=0.35)
        c.set_clip(old)
        F(c, (60, 74, 104), wx + 13, 34, 2, 12)
        F(c, (170, 190, 220), wx + 2, 35, 1, 3)
    box(c, (gx + gw // 2 - 6, gy + gh - 6, 12, 2), ramp((255, 214, 90)))
    F(c, (40, 48, 64), gx, gy + gh - 1, gw, 1)
    # painel de ferramentas
    pegboard(c, (10, 30, 84, 54))
    steel = ramp((176, 184, 198))
    for k in range(6):                                                                # chave inglesa
        F(c, steel[1], 22 + k, 46 + k, 2, 2)
    pygame.draw.circle(c, steel[1], (20, 44), 4, 2)
    F(c, steel[0], 18, 41, 2, 1)
    box(c, (40, 40, 3, 22), ramp((150, 100, 60)))                                     # martelo
    box(c, (35, 37, 13, 5), steel)
    pygame.draw.polygon(c, steel[1], [(54, 38), (68, 38), (68, 41), (58, 64), (54, 64)])   # serrote
    F(c, steel[0], 54, 38, 14, 1)
    box(c, (52, 34, 18, 5), ramp((200, 70, 50)))
    for i, col in enumerate(((220, 70, 60), (70, 130, 230), (250, 200, 70))):           # chaves de fenda
        x = 76 + i * 5
        box(c, (x, 40, 3, 8), ramp(col), outline=None)
        F(c, steel[1], x + 1, 48, 1, 10)
    pygame.draw.circle(c, (200, 120, 40), (30, 72), 6, 2)                               # rolo de fio
    pygame.draw.circle(c, (150, 80, 30), (30, 72), 3, 1)
    # bancada com maleta e carcaca de aspirador
    box(c, (12, 99, 80, 4), ramp((120, 88, 58)))
    for x in (16, 84):
        box(c, (x, 103, 4, 15), ramp((70, 56, 46)))
    box(c, (22, 91, 20, 8), ramp((200, 56, 46)))
    F(c, (240, 200, 90), 31, 91, 3, 1)
    box(c, (52, 93, 24, 6), ramp((110, 120, 140)))
    F(c, (0, 200, 230), 62, 95, 3, 1)
    # estantes com caixas
    for i, y in enumerate((50, 77, 104)):
        box(c, (268, y, 88, 3), ramp((96, 110, 140)))
        x = 271
        while x < 350:
            w = rng.randint(14, 24)
            h = rng.randint(10, 17)
            if x + w > 354:
                break
            if rng.random() < 0.28:                                                  # lata de tinta
                col = rng.choice(((200, 60, 60), (60, 120, 210), (230, 190, 60)))
                box(c, (x, y - 10, 9, 10), ramp(col))
                F(c, (200, 204, 214), x, y - 10, 9, 2)
                x += 12
                continue
            cb = ramp(lerp((150, 108, 70), (130, 100, 80), rng.random()))
            box(c, (x, y - h, w, h), cb)
            F(c, lerp(cb[1], (230, 210, 170), 0.5), x + w // 2 - 1, y - h, 3, h)
            if rng.random() < 0.5:
                F(c, cb[3], x + 3, y - h + 4, w // 3, 1)
            x += w + 2
    for x in (270, 353):
        F(c, (70, 80, 104), x, 40, 2, 78)
    box(c, (258, 108, 9, 10), ramp((40, 50, 70)))                                    # doca do Ze
    line(c, (36, 40, 52), (262, 118), (272, 140))
    # chao de cimento
    grad(c, (0, 118, LW, LH - 118), [(64, 66, 78), (48, 50, 62), (34, 36, 48), (24, 26, 36)])
    speckle(c, (0, 118, LW, 42), ((70, 72, 86), (40, 42, 54), (30, 32, 44)), 420, rng)
    for y in floor_rows(118, LH, 3, 1.4)[1:-1]:
        F(c, (30, 32, 42), 0, y, LW, 1)
    persp_lines(c, 118, LH, (36, 38, 50), 3, 92)
    F(c, (90, 100, 120), 0, 118, LW, 1)
    pygame.draw.ellipse(c, (16, 16, 24), (124, 136, 66, 13))                        # mancha de oleo
    pygame.draw.ellipse(c, (26, 26, 38), (134, 139, 40, 7))
    F(c, (70, 80, 110), 140, 140, 14, 1)
    F(c, (90, 70, 110), 156, 141, 6, 1)
    # lampada pendurada
    line(c, (30, 30, 40), (0, 10), (60, 18))
    line(c, (30, 30, 40), (60, 18), (183, 4))
    F(c, (70, 80, 100), 183, 0, 1, 10)
    pygame.draw.polygon(c, (80, 96, 120), [(174, 18), (192, 18), (188, 11), (178, 11)])
    F(c, (110, 130, 160), 178, 11, 10, 1)
    F(c, (40, 46, 60), 174, 18, 18, 1)
    beam(c, (183, 19), (183, 160), 9, 100, (46, 42, 30), 3, 0.18)
    glow_ellipse(c, (100, 126, 166, 34), (40, 34, 22))
    vignette(c, 0.55)


def fg_garagem(c):
    tire = ramp((40, 42, 52))
    for i, (y, w) in enumerate(((147, 34), (137, 33), (127, 32))):                     # pneus empilhados
        x = 2 + (34 - w) // 2
        pygame.draw.ellipse(c, INK, (x - 1, y - 1, w + 2, 13))
        pygame.draw.ellipse(c, tire[1], (x, y, w, 11))
        pygame.draw.ellipse(c, tire[0], (x + 2, y + 1, w - 4, 4), 1)
        pygame.draw.ellipse(c, (10, 10, 16), (x + 10, y + 3, w - 20, 5))
        for k in range(x + 3, x + w - 3, 3):
            F(c, tire[2], k, y + 8, 1, 2)
    cb = ramp((150, 104, 64))
    box(c, (327, 133, 40, 27), cb)                                                    # caixa FRAGIL
    F(c, (214, 200, 160), 343, 133, 7, 27)
    F(c, cb[2], 327, 141, 40, 1)
    for k in range(0, 40, 5):
        F(c, cb[2], 327 + k, 152, 3, 1)
    text(c, "FRAGIL", 330, 145, (170, 40, 36))


def anim_garagem(scr, t):
    flick = (t % 6.3) < 0.08 or 0.16 < (t % 6.3) < 0.22
    if not flick:
        AG(scr, (183, 19), 10, (60, 56, 40))
    Q(scr, (150, 150, 140) if flick else (255, 248, 222), 180, 18, 7, 1)
    motes(scr, t, (140, 30, 86, 120), 14, (120, 140, 175), 1)
    Q(scr, (80, 240, 130) if blink(t, 1.6, 0.5) else (20, 70, 40), 261, 111)


def foliage(c, base, stems, leaf=(60, 176, 110), stem=(30, 104, 74), size=(9, 4), rng=None):
    """Planta de vaso: hastes (angulo, comprimento) com folhas ao longo e na ponta, luz em cima."""
    rp = ramp(leaf)
    bx, by = base
    rng = rng or random.Random(int(bx * 7 + by))
    leaves = []
    for a, ln in stems:
        ex, ey = bx + ln * math.cos(a), by + ln * math.sin(a)
        line(c, stem, (bx, by), (ex, ey))
        for f in (0.45, 0.7, 1.0):
            px_, py_ = bx + ln * f * math.cos(a), by + ln * f * math.sin(a)
            side = 1 if (f * 10) % 2 < 1 else -1
            w, h = (size if f == 1.0 else (size[0] - 3, size[1] - 1))
            leaves.append((py_, px_ + (0 if f == 1.0 else side * w // 2), w, h))
    for py_, px_, w, h in sorted(leaves):
        pygame.draw.ellipse(c, INK, (px_ - w // 2 - 1, py_ - h // 2 - 1, w + 2, h + 2))
        pygame.draw.ellipse(c, rp[1], (px_ - w // 2, py_ - h // 2, w, h))
        F(c, rp[0], px_ - w // 2 + 1, py_ - h // 2, max(1, w // 2), 1)
        F(c, rp[2], px_, py_ + h // 2 - 1, max(1, w // 2 - 1), 1)
        F(c, rp[3], px_ - 1, py_, 3, 1) if w > 6 else None


def pot(c, x, y, w, h, col):
    rp = ramp(col)
    pygame.draw.polygon(c, INK, [(x - 1, y), (x + w, y), (x + w - 4, y + h), (x + 3, y + h)])
    pygame.draw.polygon(c, rp[1], [(x, y + 1), (x + w - 1, y + 1), (x + w - 4, y + h), (x + 4, y + h)])
    F(c, rp[0], x + 2, y + 1, 2, h - 2)
    F(c, rp[2], x + w - 6, y + 2, 2, h - 3)
    box(c, (x - 2, y - 3, w + 3, 4), ramp(lerp(col, (255, 255, 255), 0.1)))


# ================================================================================ OFICINA
def cloud(c, x, y, w, rp):
    """Nuvem de pixel: tres bolhas + base reta, luz em cima e sombra embaixo."""
    for dx, r in ((0, w // 4), (w // 3, w // 3), (2 * w // 3, w // 4)):
        pygame.draw.circle(c, rp[1], (x + dx + w // 6, y), max(2, r // 2 + 1))
    F(c, rp[1], x, y, w, 3)
    F(c, rp[2], x + 1, y + 2, w - 2, 1)
    F(c, rp[0], x + w // 3, y - w // 6, w // 4, 1)


def window_day(c, rect, rng, frame=(70, 104, 140), mull=True):
    x, y, w, h = rect
    box(c, (x - 2, y - 2, w + 4, h + 4), ramp(frame))
    old = c.get_clip()
    c.set_clip(pygame.Rect(x, y, w, h))
    grad(c, (x, y, w, h), [(84, 150, 214), (128, 186, 234), (184, 222, 246)])
    for k in range(2 if w > 40 else 0):
        cloud(c, x + rng.randint(2, w - 26), y + rng.randint(5, h // 2 - 2), rng.randint(16, 24),
              ramp((232, 242, 252)))
    skyline(c, rng, x - 4, x + w + 4, y + h, h // 6, int(h * 0.4), ramp((96, 136, 176)),
            win=(150, 190, 226), p=0.12)
    F(c, (220, 240, 255), x + 3, y + 3, 1, h // 2)
    c.set_clip(old)
    if mull:
        F(c, ramp(frame)[2], x + w // 2 - 1, y, 2, h)
        F(c, ramp(frame)[2], x, y + h // 2 - 1, w, 2)
        F(c, ramp(frame)[0], x + w // 2 - 1, y, 1, h)


def bg_oficina(c):
    rng = random.Random(2)
    wall = ramp((56, 84, 118))
    for i, x in enumerate(range(0, LW, 15)):                                       # paineis metalicos
        box(c, (x, 0, 15, 84), wall, outline=None)
        F(c, wall[3], x + 14, 0, 1, 84)
        rivets(c, (x + 2, x + 12), (4, 40, 78), wall)
    low = ramp((40, 62, 92))
    for x in range(0, LW, 23):                                                     # rodape de chapas
        box(c, (x, 84, 23, 26), low, outline=None)
        F(c, low[3], x + 22, 84, 1, 26)
        F(c, low[2], x + 3, 96, 16, 1)
    F(c, (24, 36, 56), 0, 83, LW, 1)
    for x in (37, 143, 249):                                                       # janelas com ceu e cidade
        window_day(c, (x, 14, 80, 42), rng)
        F(c, (34, 50, 76), x - 3, 58, 86, 3)
        beam(c, (x + 40, 58), (x + 16, 112), 38, 50, (26, 30, 26), 3, 0.25)
    for x in (122, 233):                                                           # prateleiras de pecas
        box(c, (x, 70, 12, 2), ramp((110, 120, 140)))
    for x, y, col in ((123, 64, (200, 100, 60)), (128, 66, (90, 140, 200)), (234, 63, (230, 190, 70)),
                      (239, 66, (120, 200, 130))):
        box(c, (x, y, 4, 70 - y), ramp(col), outline=INK)
    # chao: placas de concreto encerado (antes da bancada, que fica apoiada nele)
    grad(c, (0, 110, LW, 50), [(58, 66, 84), (44, 50, 66), (30, 34, 48)])
    speckle(c, (0, 110, LW, 50), ((66, 74, 92), (36, 40, 54)), 260, rng)
    for y in floor_rows(110, LH, 3, 1.4)[1:-1]:
        F(c, (34, 38, 52), 0, y, LW, 1)
    persp_lines(c, 110, LH, (38, 42, 56), 4, 70)
    F(c, (20, 28, 40), 0, 110, LW, 1)
    # bancada comprida com gavetas
    top = ramp((150, 104, 66))
    front = ramp((70, 86, 116))
    box(c, (12, 112, 343, 12), front)
    for x in range(16, 350, 28):
        box(c, (x, 114, 24, 8), ramp((84, 100, 132)), outline=(36, 44, 62))
        F(c, (200, 206, 220), x + 10, 117, 4, 1)
    box(c, (12, 108, 343, 4), top)
    for x in range(14, 352, 2):
        if rng.random() < 0.3:
            F(c, top[2], x, 109 + rng.randrange(2), rng.randint(2, 5), 1)
    for x in (14, 349):
        box(c, (x, 124, 4, 6), ramp((60, 70, 90)))
    F(c, (14, 18, 28), 12, 130, 343, 1)
    # monitor com grafico
    box(c, (36, 88, 42, 20), ramp((40, 54, 80)))
    F(c, (2, 30, 40), 39, 91, 36, 14)
    for yy in range(92, 104, 3):
        F(c, (8, 60, 70), 39, yy, 36, 1)
    gp = ((42, 100), (50, 95), (58, 102), (70, 93))
    for a, b in zip(gp, gp[1:]):
        line(c, (0, 230, 255), a, b)
    box(c, (54, 108, 6, 1), ramp((60, 70, 90)), outline=None)
    # pecas (engrenagens) na bancada
    steel = ramp((170, 178, 194))
    for i, x in enumerate((100, 112, 122)):
        r = 5 - i
        pygame.draw.circle(c, INK, (x, 104), r + 2)
        pygame.draw.circle(c, steel[1], (x, 104), r + 1)
        pygame.draw.circle(c, steel[0], (x - 1, 103), max(1, r - 1), 1)
        pygame.draw.circle(c, (40, 50, 70), (x, 104), max(1, r // 2))
    # bolo de aniversario
    box(c, (254, 99, 30, 9), ramp((236, 206, 164)))
    box(c, (254, 95, 30, 4), ramp((244, 124, 154)))
    for k in range(256, 283, 4):
        F(c, (255, 236, 240), k, 99, 2, 1)
    F(c, (255, 214, 90), 268, 89, 1, 6)
    # caixa de ferramentas
    box(c, (300, 96, 36, 12), ramp((206, 62, 50)))
    F(c, (150, 36, 30), 300, 101, 36, 1)
    pygame.draw.rect(c, (200, 204, 214), (311, 92, 14, 5), 1)
    for x in (77, 183, 289):
        glow_ellipse(c, (x - 40, 132, 80, 18), (30, 30, 24))
    vignette(c, 0.5)


def fg_oficina(c):
    foliage(c, (350, 134), ((-1.2, 30), (-1.6, 36), (-2.0, 28), (-0.8, 22), (-2.5, 22), (-1.4, 18)))
    pot(c, 334, 136, 32, 24, (150, 84, 58))


def gear(scr, cx, cy, r, rp, ang, teeth=8):
    """Engrenagem de pixel grosso (por quadro, so fills)."""
    for i in range(teeth):
        a = ang + i * 2 * math.pi / teeth
        Q(scr, rp[2], cx + round((r + 1) * math.cos(a)) - 1, cy + round((r + 1) * math.sin(a)) - 1, 2, 2)
    for yy in range(-r, r + 1):
        half = int(math.sqrt(max(0, r * r - yy * yy)))
        Q(scr, rp[1] if yy < 0 else rp[2], cx - half, cy + yy, 2 * half + 1, 1)
    Q(scr, rp[0], cx - r + 1, cy - 1, 2, 1)
    Q(scr, rp[3], cx - 1, cy - 1, 3, 3)
    Q(scr, rp[0], cx + round(r * 0.6 * math.cos(ang)), cy + round(r * 0.6 * math.sin(ang)), 1, 1)


_GEAR = ramp((60, 88, 124))


def anim_oficina(scr, t):
    gear(scr, 8, 70, 7, _GEAR, t * 0.6)
    gear(scr, 357, 66, 9, _GEAR, -t * 0.45, 10)
    ph = (t * 0.5) % 1.0                                                              # ponto do grafico
    gp = ((42, 100), (50, 95), (58, 102), (70, 93))
    seg = min(2, int(ph * 3))
    f = ph * 3 - seg
    a, b = gp[seg], gp[seg + 1]
    Q(scr, (220, 255, 255), round(a[0] + (b[0] - a[0]) * f), round(a[1] + (b[1] - a[1]) * f))
    on = blink(t, 0.9, 0.6)
    Q(scr, (255, 150, 60) if on else (255, 226, 120), 268, 87, 1, 2)
    if on:
        AG(scr, (268, 88), 4, (70, 46, 14))
    motes(scr, t, (40, 50, 280, 60), 14, (190, 200, 210), 2, 2.0)


# ================================================================================ ESCOLA
def locker(c, x, y, w, h, col, rng, num=None):
    rp = ramp(col)
    box(c, (x, y, w, h), rp)
    F(c, rp[3], x + w - 1, y, 1, h)
    for vy in (y + 4, y + 6, y + 8):
        F(c, rp[3], x + 3, vy, w - 6, 1)
        F(c, rp[0], x + 3, vy + 1, w - 6, 1)
    F(c, (210, 214, 226), x + w - 5, y + h // 2, 2, 4)
    F(c, rp[3], x + w - 4, y + h // 2 + 3, 1, 1)
    F(c, rp[2], x + 2, y + h - 10, w - 4, 1)
    if num is not None:
        F(c, (220, 224, 230), x + 3, y + 12, 6, 4)
        F(c, (60, 60, 80), x + 5, y + 13, 2, 2)
    if rng.random() < 0.3:
        sc = rng.choice(((255, 120, 150), (255, 214, 90), (110, 220, 140), (120, 200, 255)))
        F(c, sc, x + rng.randint(3, w - 8), y + rng.randint(20, h - 20), 4, 3)


def bg_escola(c):
    rng = random.Random(4)
    grad(c, (0, 0, LW, 80), [(54, 76, 116), (64, 88, 128), (70, 96, 136)])
    F(c, (30, 40, 64), 0, 0, LW, 6)                                                # teto
    tiles(c, (0, 80, LW, 33), ramp((44, 110, 120)), 4, 4, rng, grout=(24, 60, 70), gloss=False, var=0.4)
    F(c, (110, 170, 180), 0, 79, LW, 1)
    F(c, (20, 40, 50), 0, 80, LW, 1)
    for x in (40, 153, 266):                                                        # luminarias
        box(c, (x, 3, 62, 3), ramp((90, 104, 130)))
        F(c, (236, 246, 255), x + 2, 6, 58, 1)
        glow(c, (x + 31, 7), 18, (34, 40, 44), 3)
        beam(c, (x + 31, 7), (x + 31, 113), 26, 52, (16, 20, 24), 3, 0.1)
    # armarios dos dois lados
    for i in range(7):
        col = ((44, 96, 160), (40, 86, 148))[i % 2] if i != 4 else (190, 70, 64)
        locker(c, 6 + i * 18, 23, 17, 90, col, rng, num=i)
        locker(c, 238 + i * 18, 23, 17, 90, ((44, 96, 160), (40, 86, 148))[(i + 1) % 2] if i != 2 else (220, 170, 60),
               rng, num=i + 7)
    # mural de avisos entre armarios e porta
    box(c, (133, 40, 10, 30), ramp((150, 110, 70)))
    for k, col in enumerate(((240, 240, 230), (255, 214, 90), (140, 220, 160))):
        F(c, col, 134 + (k % 2) * 4, 42 + k * 9, 5, 6)
        F(c, (200, 60, 60), 136 + (k % 2) * 4, 42 + k * 9, 1, 1)
    box(c, (224, 40, 10, 30), ramp((150, 110, 70)))
    F(c, (240, 240, 230), 225, 43, 7, 9)
    F(c, (120, 180, 240), 226, 56, 6, 8)
    # porta aberta para o corredor
    box(c, (147, 33, 73, 80), ramp((70, 110, 160)))
    old = c.get_clip()
    c.set_clip(pygame.Rect(151, 37, 65, 76))
    grad(c, (151, 37, 65, 76), [(150, 200, 236), (120, 170, 214), (90, 136, 186)])
    vx, vy = 183, 66
    F(c, (100, 150, 196), 151, 37, 65, 4)                                           # teto do corredor
    for k in range(6):                                                              # armarios ao longe
        x0 = 151 + k * 4
        F(c, lerp((50, 100, 160), (120, 170, 214), k / 6.0), x0, 44 + k, 4, 48 - 2 * k)
        F(c, lerp((50, 100, 160), (120, 170, 214), k / 6.0), 212 - k * 4, 44 + k, 4, 48 - 2 * k)
    pygame.draw.polygon(c, (170, 196, 214), [(151, 113), (216, 113), (194, 80), (172, 80)])
    for k in range(4):
        F(c, (200, 220, 236), 176 + k * 0, 82 + k * 8, 14 + k * 6 - k * 4, 1)
    F(c, (240, 250, 255), 175, 46, 16, 2)
    F(c, (60, 110, 160), 183, 50, 1, 30)
    c.set_clip(old)
    F(c, (40, 70, 110), 151, 37, 2, 76)
    # relogio
    pygame.draw.circle(c, INK, (183, 21), 10)
    pygame.draw.circle(c, (236, 238, 244), (183, 21), 9)
    pygame.draw.circle(c, (180, 186, 200), (183, 21), 9, 1)
    for a in range(12):
        an = a * math.pi / 6
        F(c, (60, 70, 90), 183 + round(7 * math.cos(an)), 21 + round(7 * math.sin(an)))
    line(c, (30, 40, 60), (183, 21), (183, 15))
    line(c, (30, 40, 60), (183, 21), (187, 22))
    # piso de lajotas brilhantes
    checker_floor(c, 113, LH, (170, 176, 188), (140, 146, 162), cols=10, rows=6, depth=0.5)
    tint(c, (0, 113, LW, 47), (190, 196, 220))
    for x in (71, 184, 297):
        streak(c, x, 114, 156, 14, (60, 66, 74))
    F(c, (40, 50, 70), 0, 113, LW, 1)
    vignette(c, 0.5)


def fg_escola(c):
    bag = ramp((60, 90, 170))
    pygame.draw.rect(c, INK, (3, 132, 29, 28), border_radius=5)
    pygame.draw.rect(c, bag[1], (4, 133, 27, 27), border_radius=4)
    F(c, bag[0], 6, 134, 2, 24)
    box(c, (8, 143, 19, 11), ramp((80, 120, 200)))
    F(c, (255, 214, 90), 16, 146, 3, 2)
    pygame.draw.arc(c, (40, 50, 90), (9, 125, 17, 15), 0.2, math.pi - 0.2, 2)
    bin_ = ramp((80, 96, 124))
    pygame.draw.polygon(c, INK, [(334, 136), (364, 136), (360, 160), (338, 160)])
    pygame.draw.polygon(c, bin_[1], [(335, 137), (363, 137), (359, 160), (339, 160)])
    for x in (342, 349, 356):
        F(c, bin_[2], x, 140, 1, 18)
        F(c, bin_[0], x - 1, 140, 1, 18)
    box(c, (332, 133, 34, 3), ramp((100, 116, 144)))
    F(c, (240, 240, 230), 344, 130, 6, 3)


def anim_escola(scr, t):
    a = -math.pi / 2 + (t % 60.0) / 60.0 * 2 * math.pi
    for k in range(1, 8):
        Q(scr, (220, 60, 60), 183 + round(k * math.cos(a)), 21 + round(k * math.sin(a)))
    Q(scr, (220, 60, 60), 183, 21)
    if (t % 4.7) < 0.1 or 0.18 < (t % 4.7) < 0.24:                                   # lampada falhando
        Q(scr, (100, 116, 136), 268, 6, 58, 1)
    motes(scr, t, (60, 10, 240, 90), 12, (170, 190, 220), 3, 1.7)


# ================================================================================ CANTINA
def snack(c, x, y, kind):
    if kind == 0:                                                                    # coxinha
        rp = ramp((220, 150, 70))
        pygame.draw.polygon(c, INK, [(x, y - 5), (x + 4, y + 2), (x - 4, y + 2)])
        pygame.draw.polygon(c, rp[1], [(x, y - 4), (x + 3, y + 1), (x - 3, y + 1)])
        F(c, rp[0], x - 1, y - 2, 1, 2)
    elif kind == 1:                                                                  # pastel
        rp = ramp((236, 196, 110))
        pygame.draw.ellipse(c, INK, (x - 5, y - 2, 10, 5))
        pygame.draw.ellipse(c, rp[1], (x - 4, y - 1, 8, 3))
        for k in range(-3, 4, 2):
            F(c, rp[2], x + k, y + 1)
    else:                                                                            # brigadeiros
        for k in (-3, 0, 3):
            F(c, (70, 40, 30), x + k - 1, y - 1, 2, 2)
            F(c, (230, 200, 120), x + k - 1, y - 1, 1, 1)


def bg_cantina(c):
    rng = random.Random(6)
    grad(c, (0, 0, LW, 52), [(58, 86, 110), (68, 98, 122)])
    for x in range(0, LW, 4):
        if (x // 4) % 3 == 0:
            F(c, (64, 92, 116), x, 0, 1, 52)
    tiles(c, (0, 52, LW, 22), ramp((200, 214, 220)), 6, 5, rng, grout=(130, 150, 160), var=0.1)
    tint(c, (0, 52, LW, 22), (170, 190, 210))
    for x in range(0, LW, 6):
        if (x // 6) % 2 == 0:
            F(c, (60, 140, 150), x, 57, 5, 4)
    window_day(c, (12, 9, 30, 38), rng, mull=False)
    F(c, (70, 104, 140), 26, 9, 2, 38)
    # lousa do cardapio
    box(c, (52, 10, 140, 40), ramp((132, 96, 66)))
    F(c, (22, 54, 50), 55, 13, 134, 34)
    dith(c, (55, 13, 134, 34), (30, 64, 60), 1)
    text(c, "CARDAPIO", 59, 15, (236, 240, 226))
    for i, (w, p) in enumerate(((50, "350"), (38, "500"), (62, "425"))):
        y = 24 + i * 7
        for k in range(0, w, 3):
            F(c, (190, 214, 200), 59 + k, y + 2, 2, 1)
        text(c, p, 186 - text_w(p), y, (255, 214, 90))
    pygame.draw.circle(c, (230, 150, 70), (160, 20), 3)
    F(c, (200, 220, 210), 154, 16, 2, 1)
    # piso de ladrilho
    checker_floor(c, 104, LH, (150, 84, 70), (198, 176, 150), cols=11, rows=7)
    tint(c, (0, 104, LW, 56), (160, 156, 180))
    F(c, (30, 40, 56), 0, 104, LW, 1)
    # balcao com vitrine
    F(c, (40, 60, 80), 16, 70, 335, 1)
    glass = (150, 200, 220)
    box(c, (18, 71, 331, 11), ramp((40, 70, 100)), outline=INK)
    F(c, (24, 44, 64), 19, 72, 329, 9)
    for i, x in enumerate(range(26, 345, 12)):
        snack(c, x, 78, i % 3)
    F(c, glass, 18, 71, 331, 1)
    dith(c, (19, 72, 329, 9), (80, 120, 150), 1)
    for k in range(30, 340, 45):
        line(c, (180, 220, 240), (k, 80), (k + 5, 72))
    front = ramp((90, 130, 170))
    box(c, (16, 82, 335, 22), front)
    for x in range(20, 348, 20):
        box(c, (x, 86, 17, 14), ramp((70, 110, 150)), outline=None)
        F(c, (50, 80, 120), x + 17, 86, 1, 14)
    F(c, (220, 230, 240), 16, 82, 335, 1)
    # luminarias pendentes
    for x in (217, 267, 317):
        F(c, (90, 100, 120), x, 0, 1, 14)
        pygame.draw.polygon(c, INK, [(x - 7, 20), (x + 7, 20), (x + 4, 13), (x - 4, 13)])
        pygame.draw.polygon(c, (90, 120, 150), [(x - 6, 19), (x + 6, 19), (x + 3, 14), (x - 3, 14)])
        F(c, (255, 246, 210), x - 3, 20, 7, 1)
        glow(c, (x, 21), 15, (60, 54, 34), 4)
        beam(c, (x, 21), (x, 104), 5, 28, (30, 28, 16), 3, 0.15)
    # banquinhos
    for x in (52, 120, 247, 315):
        seat = ramp((210, 70, 84))
        F(c, (150, 160, 176), x, 108, 2, 12)
        pygame.draw.ellipse(c, INK, (x - 8, 103, 18, 7))
        pygame.draw.ellipse(c, seat[1], (x - 7, 104, 16, 5))
        F(c, seat[0], x - 4, 104, 8, 1)
        pygame.draw.ellipse(c, (60, 70, 92), (x - 6, 119, 14, 3))
    glow_ellipse(c, (120, 112, 130, 26), (40, 34, 20))
    vignette(c, 0.48)


def fg_cantina(c):
    foliage(c, (19, 138), ((-1.3, 34), (-1.7, 40), (-2.1, 30), (-0.9, 26), (-1.5, 22), (-2.5, 20)),
            leaf=(70, 190, 120))
    pot(c, 3, 138, 33, 22, (70, 100, 150))


def anim_cantina(scr, t):
    for j, x in enumerate((62, 153, 243)):                                             # vapor dos salgados
        for i in range(5):
            yy = 70 - i * 3 - int((t * 5) % 3)
            Q(scr, (150, 176, 200) if i < 3 else (110, 130, 160), x + round(1.5 * math.sin(t * 3 + i * 0.9 + j)), yy)
    k = 0.9 + 0.1 * math.sin(t * 2.0)
    Q(scr, mul((255, 246, 210), k), 264, 20, 7, 1)


# ================================================================================ CAMARIM
def bulbs_row(c, x, y, n, step, col=(200, 180, 130)):
    for i in range(n):
        F(c, INK, x + i * step - 1, y - 1, 4, 4)
        F(c, col, x + i * step, y, 2, 2)
        F(c, lerp(col, (255, 255, 255), 0.5), x + i * step, y, 1, 1)


def bg_camarim(c):
    rng = random.Random(8)
    paper = ramp((70, 52, 104))
    F(c, paper[1], 0, 0, LW, 118)
    for y in range(2, 118, 8):                                                       # papel de parede (losangos)
        for x in range((y // 8) % 2 * 6, LW, 12):
            F(c, paper[2], x + 2, y, 1, 1)
            F(c, paper[2], x + 1, y + 1, 3, 1)
            F(c, paper[2], x + 2, y + 2, 1, 1)
            F(c, lerp(paper[1], paper[0], 0.4), x + 2, y + 1, 1, 1)
    for x in range(0, LW, 24):
        F(c, lerp(paper[1], paper[2], 0.5), x, 0, 1, 118)
    planks_v(c, (0, 106, LW, 12), ramp((96, 62, 70)), 5, rng)                     # lambri
    F(c, (130, 96, 150), 0, 106, LW, 1)
    # espelhos com lampadas
    for x in (30, 106, 182):
        box(c, (x, 22, 66, 66), ramp((110, 80, 140)))
        old = c.get_clip()
        c.set_clip(pygame.Rect(x + 3, 25, 60, 60))
        grad(c, (x + 3, 25, 60, 60), [(150, 186, 222), (112, 140, 190), (84, 92, 150), (76, 62, 112)])
        for dx, wd, col in ((6, 7, (196, 222, 246)), (17, 3, (176, 206, 240)), (36, 5, (170, 200, 236))):
            pygame.draw.polygon(c, col, [(x + dx, 85), (x + dx + wd, 85), (x + dx + wd + 34, 25), (x + dx + 34, 25)])
        F(c, (230, 244, 255), x + 5, 27, 1, 6)
        c.set_clip(old)
        bulbs_row(c, x + 3, 19, 8, 8)
        bulbs_row(c, x + 3, 89, 8, 8)
    # bancada com maquiagem
    box(c, (24, 96, 238, 5), ramp((120, 92, 150)))
    for x, col, h in ((44, (255, 120, 170), 5), (52, (120, 200, 255), 7), (78, (255, 214, 90), 4),
                      (124, (200, 160, 255), 6), (140, (240, 240, 240), 4), (204, (255, 140, 100), 6),
                      (220, (120, 230, 170), 5)):
        box(c, (x, 96 - h, 4, h), ramp(col))
    for x in (34, 252):
        box(c, (x, 101, 4, 16), ramp((60, 46, 86)))
    # armarios e camisas penduradas
    for i in range(5):
        x = 276 + i * 17
        rp = ramp((66, 90, 140))
        box(c, (x, 26, 16, 90), rp)
        for vy in (32, 35, 38):
            F(c, rp[3], x + 3, vy, 10, 1)
        F(c, (255, 214, 90), x + 12, 70, 2, 3)
    F(c, (190, 190, 206), 280, 28, 80, 1)
    for i, col in enumerate(((220, 50, 50), (60, 120, 230), (240, 200, 80))):
        x = 292 + i * 24
        rp = ramp(col)
        F(c, (190, 190, 206), x, 29, 1, 3)
        pygame.draw.polygon(c, INK, [(x - 9, 31), (x + 9, 31), (x + 13, 37), (x + 9, 39), (x + 8, 52), (x - 8, 52),
                                     (x - 9, 39), (x - 13, 37)])
        pygame.draw.polygon(c, rp[1], [(x - 8, 32), (x + 8, 32), (x + 11, 37), (x + 8, 38), (x + 7, 51), (x - 7, 51),
                                       (x - 8, 38), (x - 11, 37)])
        F(c, rp[0], x - 7, 33, 2, 17)
        F(c, rp[2], x + 5, 38, 2, 13)
        text(c, str(i + 7)[-1], x - 2, 40, (250, 250, 255))
    # banco encostado
    box(c, (40, 112, 150, 4), ramp((110, 64, 170)))
    # piso emborrachado
    grad(c, (0, 118, LW, 42), [(56, 44, 78), (40, 32, 58), (26, 20, 40)])
    for y in floor_rows(118, LH, 4, 1.4)[1:-1]:
        F(c, (30, 24, 44), 0, y, LW, 1)
    persp_lines(c, 118, LH, (34, 26, 48), 5, 60)
    F(c, (255, 120, 200), 0, 118, LW, 1)
    glow_ellipse(c, (30, 98, 230, 20), (50, 40, 30))
    vignette(c, 0.5)


_CAM_BULBS = [(x + 3 + i * 8, y) for x in (30, 106, 182) for y in (19, 89) for i in range(8)]


def anim_camarim(scr, t):
    step = int(t * 6)
    for i, (x, y) in enumerate(_CAM_BULBS):
        if (i + step) % 4 == 0:
            Q(scr, (255, 248, 210), x, y, 2, 2)
            AG(scr, (x + 1, y + 1), 4, (80, 70, 40), 3)


# ================================================================================ ARENA / MUNDIAL
_SHIRTS_GOLD = ((236, 196, 70), (240, 240, 245), (220, 70, 70), (70, 130, 230), (255, 214, 90), (40, 44, 60))


def skyboxes(c, y, rng, x0=0, x1=LW, step=24, warm=(255, 210, 140)):
    F(c, (10, 14, 30), x0, y, x1 - x0, 11)
    F(c, (40, 50, 80), x0, y, x1 - x0, 1)
    atlas = crowd_atlas("small")
    for x in range(x0 + 3, x1 - 16, step):
        lit = lerp((30, 40, 70), warm, 0.35 + 0.4 * rng.random())
        box(c, (x, y + 2, 17, 7), ramp(lit), outline=(4, 6, 14))
        for k in range(rng.randint(1, 3)):
            idx = rng.randrange(ATLAS_N)
            c.blit(atlas, (x + 2 + k * 5, y + 4), (idx * SMALL_W, 0, SMALL_W, 5))
        F(c, lerp(lit, (255, 255, 255), 0.4), x + 1, y + 2, 15, 1)


def glossy_floor(c, y0, base, line_col, rng, acc=None):
    grad(c, (0, y0, LW, LH - y0), [base, mul(base, 0.75), mul(base, 0.5)])
    for y in floor_rows(y0, LH, 5, 1.6)[1:-1]:
        F(c, line_col, 0, y, LW, 1)
    persp_lines(c, y0, LH, line_col, 8, 34, depth=0.3)
    if acc is not None:
        F(c, acc, 0, y0, LW, 1)


def bg_arena(c, gold=False):
    rng = random.Random(11)
    acc = GOLD if gold else NEON
    grad(c, (0, 0, LW, 96), [(4, 6, 18), (8, 12, 32), (16, 18, 48)] if not gold else
         [(8, 6, 14), (18, 14, 26), (30, 24, 34)])
    for _ in range(50):                                                                # luzinhas da cupula
        F(c, lerp((40, 50, 90), (200, 210, 255), rng.random()), rng.randrange(LW), rng.randrange(60))
    for x in range(0, LW, 30):                                                        # anel do teto
        line(c, (24, 30, 56), (x, 0), (x + 15, 8))
        line(c, (24, 30, 56), (x + 30, 0), (x + 15, 8))
    F(c, (30, 36, 66), 0, 8, LW, 1)
    bcol = (22, 40, 86) if not gold else (60, 48, 22)
    for x0, x1 in ((20, 70), (347, 297), (100, 140), (267, 227)):                     # feixes dos refletores
        beam(c, (x0, 0), (x1, 132), 3, 26, bcol, 3, 0.2)
    for x in (20, 347, 100, 267):
        lamp_head(c, x, 2, 7, (255, 250, 230))
        glow(c, (x, 3), 9, (70, 80, 110) if not gold else (110, 90, 40), 3)
    skyboxes(c, 85, rng)
    # telao
    for x in (114, 253):
        F(c, (40, 46, 66), x, 0, 1, 11)
    box(c, (99, 11, 169, 76), ramp((30, 34, 52)), outline=(2, 4, 10))
    F(c, (6, 8, 16), 102, 14, 163, 70)
    grad(c, (103, 15, 161, 68), [(26, 14, 76), (16, 30, 100), (0, 60, 120)] if not gold else
         [(40, 20, 50), (60, 40, 30), (90, 70, 30)])
    for yy in range(15, 83, 2):
        dith(c, (103, yy, 161, 1), (0, 0, 0), 1)
    for xx in range(105, 264, 3):
        F(c, mul((0, 60, 120) if not gold else (90, 70, 30), 0.6), xx, 15, 1, 68)
    outline_rect(c, acc, 100, 12, 167, 74)
    F(c, lerp(acc, (255, 255, 255), 0.5), 100, 12, 167, 1)
    if gold:                                                                         # globo
        pygame.draw.circle(c, (16, 60, 120), (183, 46), 23)
        pygame.draw.circle(c, (30, 100, 170), (177, 40), 13)
        pygame.draw.circle(c, (60, 150, 210), (174, 37), 5)
        rngg = random.Random(12)
        for _ in range(26):                                                          # continentes
            a, r = rngg.random() * 6.28, rngg.random() * 19
            F(c, (60, 160, 90), 183 + int(r * math.cos(a)), 46 + int(r * math.sin(a)), 3, 2)
        pygame.draw.circle(c, GOLD, (183, 46), 24, 1)
        F(c, GOLD, 160, 46, 47, 1)
        F(c, (200, 160, 60), 163, 36, 41, 1)
        F(c, (200, 160, 60), 163, 56, 41, 1)
    else:
        for i in range(6):
            F(c, (0, 110, 160), 103, 24 + i * 10, 161, 1)
    # arquibancada (mais escura atras dos personagens)
    bleachers(c, 0, LW, 96, 4, 10, (24, 40, 86) if not gold else (60, 50, 34), rng,
              shirts=_SHIRTS_GOLD if gold else SHIRTS, tag="gold" if gold else "std", fade=(0.42, 0.7))
    F(c, (8, 12, 24), 0, 134, LW, 4)                                                    # faixa de LED
    F(c, acc, 0, 137, LW, 1)
    glossy_floor(c, 138, (20, 30, 66) if not gold else (40, 32, 26), (30, 46, 94) if not gold else (70, 56, 34), rng)
    glow_ellipse(c, (100, 139, 167, 18), (26, 40, 80) if not gold else (70, 56, 20))
    for x in (60, 183, 306):
        glow_ellipse(c, (x - 30, 146, 60, 12), (20, 30, 50) if not gold else (40, 30, 14))
    vignette(c, 0.5)


def bg_mundial(c):
    bg_arena(c, True)


_PTS_ARENA = pts(111, 18, (4, 98, 358, 32))


def eq_bars(scr, t, acc):
    y = 15 + int((t * 20) % 68)                                                       # linha de varredura
    Q(scr, (60, 120, 200), 103, y, 161, 1)
    for i in range(14):                                                                # equalizador
        h = int(4 + 9 * abs(math.sin(t * 3.1 + i * 0.7)))
        col = lerp(acc, (255, 255, 255), 0.25) if i % 2 else acc
        Q(scr, col, 110 + i * 11, 82 - h, 7, h)
        Q(scr, lerp(col, (255, 255, 255), 0.5), 110 + i * 11, 82 - h, 7, 1)


def led_band(scr, t, acc):
    for i in range(12):
        x = int((i * 32 + t * 46) % 390) - 12
        Q(scr, lerp(acc, (255, 255, 255), 0.5), x, 135, 10, 2)


def anim_arena(scr, t):
    eq_bars(scr, t, NEON)
    full = blink(t, 1.2, 0.5)
    for k in range(0, 31):                                                            # botao de play
        hw = 15 - abs(k - 15)
        Q(scr, NEON, 172, 32 + k, 1, 1)
        if full and hw > 0:
            Q(scr, (0, 150, 200), 173, 32 + k, hw, 1)
        Q(scr, NEON, 172 + hw, 32 + k, 1, 1)
    led_band(scr, t, NEON)
    flashes(scr, t, _PTS_ARENA, 0.8)


_BUNT = [(x, ((220, 70, 70), (70, 130, 230), (240, 220, 90), (240, 240, 240))[(x // 18) % 4]) for x in range(6, LW, 18)]
_CONF = [((i * 47) % LW, (i * 23) % 134, ((220, 70, 70), (70, 130, 230), (240, 220, 90), (240, 240, 240))[i % 4])
         for i in range(26)]


def drone(scr, x, y, t, i):
    Q(scr, (170, 190, 220), x - 6, y - 2, 13, 1)
    Q(scr, (90, 110, 150), x - 3, y - 1, 7, 3)
    Q(scr, (60, 70, 100), x - 3, y + 1, 7, 1)
    Q(scr, GOLD if blink(t, 0.8, 0.5, i * 0.3) else (220, 60, 60), x, y + 2, 1, 1)


def anim_mundial(scr, t):
    eq_bars(scr, t, GOLD)
    for j in range(2):                                                                 # globo girando
        w = int(46 * abs(math.cos(t * 0.8 + j * math.pi / 2)))
        if w > 2:
            for yy in range(-23, 24):
                half = w / 2.0 * math.sqrt(max(0.0, 1 - (yy / 23.5) ** 2))
                Q(scr, GOLD, 183 - round(half), 46 + yy)
                Q(scr, GOLD, 183 + round(half), 46 + yy)
    Q(scr, (120, 130, 150), 0, 0, LW, 1)
    for x, col in _BUNT:                                                                 # bandeirinhas
        d = int(round(1.2 * math.sin(t * 2.5 + x * 0.15)))
        rp = ramp(col)
        for k in range(8):
            Q(scr, rp[1] if k < 6 else rp[2], x + k // 2 + (d if k > 4 else 0), 1 + k, 10 - k, 1)
    for i, (x, y) in enumerate(((40, 40), (320, 50), (70, 24))):
        drone(scr, x + int(3 * math.sin(t * 0.7 + i)), y + int(2 * math.sin(t * 1.9 + i * 2)), t, i)
    for i, (x, y, col) in enumerate(_CONF):                                              # confete
        yy = int((y + t * (13 + i % 5 * 3)) % 134)
        xx = x + int(3 * math.sin(t * 2 + i))
        Q(scr, col, xx, yy, 1 + (i % 2), 1)
    led_band(scr, t, GOLD)
    flashes(scr, t, _PTS_ARENA, 1.1)


# ================================================================================ ESTADIO
def light_tower(c, x, top, base, glow_col=(60, 80, 110)):
    rp = ramp((60, 74, 104))
    F(c, rp[2], x - 2, top + 8, 1, base - top - 8)
    F(c, rp[1], x + 2, top + 8, 1, base - top - 8)
    for y in range(top + 10, base, 6):                                                   # trelica
        line(c, rp[0], (x - 2, y), (x + 2, y + 6))
        line(c, rp[2], (x + 2, y), (x - 2, y + 6))
    box(c, (x - 14, top - 6, 29, 14), ramp((30, 38, 60)), outline=(6, 8, 16))
    for i in range(4):
        for j in range(2):
            F(c, (255, 252, 236), x - 12 + i * 7, top - 4 + j * 6, 5, 4)
            F(c, (255, 255, 255), x - 11 + i * 7, top - 3 + j * 6, 2, 1)
    glow(c, (x, top), 44, glow_col, 5)


def grass(c, y0, rng, base=(46, 128, 74), stripes=6):
    rp = ramp(base)
    ys = floor_rows(y0, LH, stripes, 1.3)
    for i in range(stripes):
        F(c, rp[1] if i % 2 else lerp(rp[1], rp[0], 0.35), 0, ys[i], LW, ys[i + 1] - ys[i])
    for _ in range(500):
        x, y = rng.randrange(LW), rng.randrange(y0, LH)
        F(c, rp[2] if rng.random() < 0.6 else lerp(rp[1], rp[0], 0.6), x, y, 1, 1 + (y > y0 + 20))


def bg_estadio(c):
    rng = random.Random(13)
    night_sky(c, 62, rng, cols=((2, 4, 16), (8, 14, 36), (18, 28, 62)), stars=60)
    F(c, (14, 18, 34), 0, 40, LW, 6)                                                  # cobertura
    for x in range(0, LW, 6):
        F(c, (34, 40, 64), x, 45, 3, 1)
    bleachers(c, 0, LW, 46, 6, 6, (30, 44, 84), rng, kind="small", fade=(0.32, 0.55), step=4)
    F(c, (18, 22, 40), 0, 82, LW, 4)                                                  # mureta do anel
    x = 0
    for i in range(0, LW, 30):
        F(c, ((200, 60, 60), (40, 120, 220), (240, 200, 70))[(i // 30) % 3], i + 4, 83, 22, 2)
    bleachers(c, 0, LW, 86, 4, 10, (34, 56, 108), rng, fade=(0.45, 0.72))
    F(c, (8, 12, 26), 0, 124, LW, 5)                                                  # placas de LED
    F(c, (220, 240, 245), 0, 129, LW, 1)
    grass(c, 130, rng)
    F(c, (220, 236, 230), 0, 132, LW, 1)                                              # linhas do campo
    line(c, (220, 236, 230), (183, 132), (183, LH))
    pygame.draw.ellipse(c, (220, 236, 230), (148, 138, 70, 22), 1)
    for x in (37, 330):
        light_tower(c, x, 14, 46)
        beam(c, (x, 18), (183 + (x - 183) // 3, 150), 6, 60, (20, 26, 30), 3, 0.15)
    glow_ellipse(c, (60, 132, 250, 28), (30, 40, 30))
    vignette(c, 0.45)


_STARS_EST = pts(131, 10, (0, 0, LW, 36))
_PTS_EST = pts(132, 22, (4, 48, 358, 72))


def anim_estadio(scr, t):
    for i, (x, y) in enumerate(_STARS_EST):
        if blink(t, 2.0 + (i % 4) * 0.4, 0.3, i * 0.37):
            Q(scr, (220, 230, 255), x, y - 1, 1, 3)
            Q(scr, (220, 230, 255), x - 1, y, 3, 1)
    big = blink(t, 2.4, 0.5)
    for x in (37, 330):
        AG(scr, (x, 14), 16 if big else 12, (40, 50, 60), 3)
    for i in range(12):
        x = int((i * 34 + t * 30) % 400) - 20
        Q(scr, (0, 160, 200) if i % 2 else GOLD, x, 125, 18, 2)
        Q(scr, (255, 255, 255), x + 2, 127, 6, 1)
    flashes(scr, t, _PTS_EST, 1.0)


# ================================================================================ COLISEU
_SHIRTS_DARK = ((30, 30, 36), (236, 196, 70), (200, 170, 70), (44, 40, 50), (232, 232, 236), (150, 30, 40))


def bg_coliseu(c):
    rng = random.Random(27)
    grad(c, (0, 0, LW, 60), [(2, 2, 8), (8, 6, 16), (16, 12, 24)])
    for _ in range(40):
        F(c, lerp((60, 50, 40), (230, 210, 160), rng.random()), rng.randrange(LW), rng.randrange(30))
    cx, cy = 183, 158
    stone = ramp((60, 50, 62), warm=(255, 220, 160))
    rings = 5
    for i in range(rings):                                                            # aneis da arquibancada
        rx, ry = 274 - i * 22, 128 - i * 17
        col = stone[1] if i % 2 == 0 else stone[2]
        pygame.draw.ellipse(c, col, (cx - rx, cy - ry, 2 * rx, 2 * ry))
        pygame.draw.ellipse(c, (150, 116, 50), (cx - rx, cy - ry, 2 * rx, 2 * ry), 1)
    for k in range(-14, 15):                                                          # arcos no topo
        a = math.pi / 2 - k * 0.11
        x = cx + 274 * math.cos(a)
        y = cy - 128 * math.sin(a)
        if -6 <= x < LW + 6:
            pygame.draw.rect(c, (12, 10, 18), (int(x) - 4, int(y) - 9, 8, 10), border_top_left_radius=4,
                             border_top_right_radius=4)
            F(c, (110, 86, 40), int(x) - 5, int(y), 10, 1)
    for i in range(rings):                                                            # publico nos aneis
        big = i >= 3                                                                  # aneis de baixo: mais perto
        kind = "big" if big else "small"
        cw, chh = (CELL_W, CELL_H) if big else (SMALL_W, SMALL_H)
        atlas = crowd_atlas(kind, _SHIRTS_DARK, "dark")
        f = 0.42 + i * 0.1
        fa = _faded(atlas, round(f * 20) / 20.0, (230, 210, 200), (kind, "dark"))
        for row in range(1 if big else 2):
            rx, ry = 268 - i * 22 - row * 7, 122 - i * 17 - row * 6
            n = int(rx * 3.1 / (6.2 if big else 4.4))
            for j in range(n):
                a = math.pi * (j + rng.random() * 0.3) / n
                x = int(cx + rx * math.cos(a))
                y = int(cy - ry * math.sin(a))
                if -6 <= x < LW and y < 108 and rng.random() > 0.05:
                    idx = rng.randrange(ATLAS_N)
                    c.blit(fa, (x - cw // 2, y - chh + 2), (idx * cw, 0, cw, chh))
    # muro da arena com a placa OMEGA
    F(c, (14, 12, 20), 0, 106, LW, 17)
    stone_blocks = ramp((40, 34, 46))
    for x in range(0, LW, 12):
        box(c, (x, 109, 11, 12), stone_blocks, outline=None)
    F(c, GOLD, 0, 106, LW, 2)
    F(c, (110, 84, 30), 0, 121, LW, 2)
    w = P.pixtext_w("OMEGA", 2)
    box(c, (183 - w // 2 - 6, 108, w + 12, 14), ramp((14, 12, 18)), outline=(110, 84, 30))
    P._pixtext(c, "OMEGA", 183 - w // 2 + 1, 111, 2, (110, 20, 20))
    P._pixtext(c, "OMEGA", 183 - w // 2, 110, 2, (255, 70, 60))
    # areia
    sand = ramp((96, 80, 62))
    grad(c, (0, 123, LW, 37), [sand[1], sand[2], mul(sand[2], 0.8)])
    speckle(c, (0, 123, LW, 37), (sand[0], sand[2], sand[3]), 600, rng)
    for i in range(-6, 7):
        line(c, mul(sand[2], 0.9), (183 + i * 20, 123), (183 + i * 66, LH))
    for x in (27, 340):                                                               # torres de refletor
        box(c, (x - 1, 12, 3, 96), ramp((40, 40, 52)))
        box(c, (x - 12, 6, 25, 9), ramp((30, 28, 40)), outline=(4, 4, 8))
        for i in range(3):
            F(c, (255, 244, 210), x - 10 + i * 8, 8, 5, 4)
        glow(c, (x, 10), 22, (70, 60, 36), 4)
        beam(c, (x, 12), (183 + (x - 183) // 3, 156), 8, 60, (36, 30, 16), 3, 0.15)
    glow_ellipse(c, (100, 126, 166, 30), (50, 40, 20))
    vignette(c, 0.55)


_PTS_COL = pts(271, 22, (14, 30, 340, 74))
_GCONF = [((i * 58) % LW, (i * 21) % 156, GOLD if i % 2 else (40, 36, 44)) for i in range(22)]


def anim_coliseu(scr, t):
    for i, x in enumerate((27, 340)):
        big = blink(t, 2.0, 0.5, i * 0.7)
        AG(scr, (x, 10), 16 if big else 12, (60, 50, 30), 3)
    flashes(scr, t, _PTS_COL, 1.2)
    for i, (x, y, col) in enumerate(_GCONF):
        yy = int((y + t * (10 + i % 4 * 3)) % 156)
        Q(scr, col, x + int(2 * math.sin(t * 2 + i)), yy, 1, 1 + (i % 3 == 0))
    if blink(t, 1.0, 0.85):
        w = P.pixtext_w("OMEGA", 2)
        x0 = 183 - w // 2 - 7
        Q(scr, (255, 70, 60), x0, 107, w + 14, 1)
        Q(scr, (255, 70, 60), x0, 122, w + 14, 1)
        Q(scr, (255, 70, 60), x0, 107, 1, 16)
        Q(scr, (255, 70, 60), x0 + w + 13, 107, 1, 16)


# ================================================================================ CABINE
def foam(c, rect):
    """Espuma acustica (piramides): quadrados com luz em cima/esquerda e sombra embaixo/direita."""
    x, y, w, h = rect
    rp = ramp((30, 40, 70))
    c.fill(rp[2], (x, y, w, h))
    for yy in range(y, y + h, 6):
        for xx in range(x, x + w, 6):
            for k in range(3):
                F(c, rp[0] if (xx // 6 + yy // 6) % 2 else rp[1], xx + k, yy + k, 5 - 2 * k, 1)
                F(c, rp[3], xx + k, yy + 5 - k, 5 - 2 * k + 1, 1)


def bg_cabine(c):
    rng = random.Random(29)
    foam(c, (0, 0, LW, 100))
    wx, wy, ww, wh = 30, 14, 307, 82                                                  # janelao: estadio
    box(c, (wx - 3, wy - 3, ww + 6, wh + 6), ramp((50, 64, 100)), outline=(6, 8, 16))
    old = c.get_clip()
    c.set_clip(pygame.Rect(wx, wy, ww, wh))
    night_sky(c, wy + 30, rng, cols=((4, 8, 24), (12, 18, 46), (22, 30, 70)), stars=40, x0=wx, x1=wx + ww)
    bleachers(c, wx, wx + ww, wy + 28, 6, 6, (26, 36, 70), rng, kind="small", fade=(0.35, 0.6), step=4)
    F(c, (12, 16, 30), wx, wy + 64, ww, 2)
    grass(c, wy + 66, rng, stripes=4)
    F(c, (210, 236, 230), wx, wy + 69, ww, 1)
    pygame.draw.ellipse(c, (210, 236, 230), (183 - 26, wy + 72, 52, 10), 1)
    line(c, (210, 236, 230), (183, wy + 69), (183, wy + wh))
    for x in (wx + 20, wx + ww - 20):
        light_tower(c, x, wy + 6, wy + 40, (50, 60, 80))
    for k in range(4):                                                                 # reflexos no vidro
        x = wx + 30 + k * 80
        pygame.draw.polygon(c, (60, 80, 120), [(x, wy + wh), (x + 6, wy + wh), (x + 36, wy), (x + 30, wy)])
    tint(c, (wx, wy, ww, wh), (220, 230, 255))
    c.set_clip(old)
    F(c, (8, 10, 20), wx, wy, ww, 1)
    for x in range(wx + 76, wx + ww, 77):
        F(c, (50, 64, 100), x, wy, 2, wh)
    # bancada
    box(c, (0, 99, LW, 4), ramp((70, 90, 130)), outline=None)
    F(c, NEON, 0, 99, LW, 1)
    front = ramp((26, 34, 58))
    F(c, front[1], 0, 103, LW, 57)
    for x in range(0, LW, 37):
        box(c, (x + 2, 106, 33, 32), ramp((32, 42, 70)), outline=(14, 18, 32))
        for yy in range(109, 136, 3):
            F(c, (24, 32, 54), x + 5, yy, 27, 1)
    F(c, (0, 120, 150), 0, 103, LW, 1)
    grad(c, (0, 140, LW, 20), [(20, 26, 44), (12, 16, 28)])
    for x in (143, 223):                                                               # monitores
        box(c, (x - 17, 79, 34, 20), ramp((40, 52, 80)), outline=(4, 6, 12))
        F(c, (0, 40, 60), x - 15, 81, 30, 16)
        F(c, (60, 76, 110), x - 2, 99, 4, 1)
    for x in (100, 267):                                                               # microfones de mesa
        F(c, (110, 120, 140), x, 84, 1, 15)
        pygame.draw.ellipse(c, INK, (x - 4, 74, 9, 12))
        pygame.draw.ellipse(c, (70, 76, 96), (x - 3, 75, 7, 10))
        for yy in range(76, 85, 2):
            F(c, (120, 130, 150), x - 2, yy, 5, 1)
        F(c, (40, 44, 60), x - 7, 98, 15, 1)
    box(c, (40, 95, 30, 3), ramp((220, 220, 230)))                                     # papeis e notebook
    box(c, (300, 90, 26, 8), ramp((60, 66, 84)))
    F(c, (100, 180, 230), 302, 91, 22, 5)
    glow_ellipse(c, (60, 96, 250, 12), (30, 40, 60))
    vignette(c, 0.5)


_PTS_CAB = pts(291, 18, (40, 44, 280, 30))


def _noar(sp, on):
    sp.fill((200, 30, 40) if on else (60, 16, 20))
    pygame.draw.rect(sp, (255, 120, 120) if on else (90, 30, 30), sp.get_rect(), 1)
    P._pixtext(sp, "NO AR", 4, 3, 1, (255, 240, 240) if on else (120, 80, 80))


def noar_sprite(on):
    key = ("noar", on)
    sp = _SP.get(key)
    if sp is None:
        lo = pygame.Surface((37, 11))
        _noar(lo, on)
        sp = pygame.transform.scale(lo, (37 * S, 11 * S))
        _SP[key] = sp
    return sp


def anim_cabine(scr, t):
    on = blink(t, 1.6, 0.7)
    scr.blit(noar_sprite(on), (165 * S, 1 * S))
    for i, x in enumerate((143, 223)):                                                  # monitores
        for j in range(6):
            h = int(2 + 11 * abs(math.sin(t * (2.5 + i) + j)))
            Q(scr, NEON if j % 2 else GOLD, x - 13 + j * 5, 97 - h, 3, h)
    for i, x in enumerate((100, 267)):                                                  # VU dos microfones
        lv = int(4 * abs(math.sin(t * 6 + i * 1.7)))
        for j in range(4):
            Q(scr, (90, 240, 120) if j < lv else (30, 50, 40), x + 6, 96 - j * 3, 3, 2)
    flashes(scr, t, _PTS_CAB, 1.3)


def fg_cabine(c):
    box(c, (3, 138, 34, 2), ramp((220, 220, 230)))                                      # papeis e caneca
    box(c, (14, 126, 12, 11), ramp((220, 70, 70)))
    pygame.draw.arc(c, (220, 70, 70), (22, 128, 8, 7), -math.pi / 2, math.pi / 2, 2)
    F(c, (240, 240, 245), 15, 127, 10, 1)
    box(c, (0, 141, 37, 19), ramp((30, 34, 46)))
    box(c, (330, 141, 37, 19), ramp((30, 34, 46)))                                     # fones
    pygame.draw.arc(c, INK, (334, 116, 26, 24), 0, math.pi, 3)
    pygame.draw.arc(c, (80, 86, 104), (335, 117, 24, 22), 0, math.pi, 1)
    for x in (334, 354):
        box(c, (x, 126, 6, 11), ramp((50, 54, 70)))


# ================================================================================ FEDERACAO
def column(c, x, y0, y1, w=14, col=(206, 214, 232)):
    rp = ramp(col)
    box(c, (x - w // 2 - 3, y0 - 6, w + 6, 6), rp)                                    # capitel
    F(c, rp[2], x - w // 2 - 2, y0 - 2, w + 4, 1)
    F(c, rp[1], x - w // 2, y0, w, y1 - y0)                                            # fuste canelado
    for k in range(0, w, 3):
        F(c, rp[0], x - w // 2 + k, y0, 1, y1 - y0)
        F(c, rp[2], x - w // 2 + k + 2, y0, 1, y1 - y0)
    F(c, rp[3], x + w // 2 - 1, y0, 1, y1 - y0)
    pygame.draw.rect(c, INK, (x - w // 2 - 1, y0, w + 2, y1 - y0), 1)
    box(c, (x - w // 2 - 3, y1, w + 6, 4), rp)                                         # base


def curtain(c, x, y, w, h, col):
    rp = ramp(col)
    for k in range(w):
        c.fill((rp[0], rp[1], rp[1], rp[2], rp[3])[k % 5], (x + k, y, 1, h))
    F(c, rp[3], x, y + h - 2, w, 2)
    box(c, (x - 1, y + h // 2, w + 2, 2), ramp(GOLD))


def bg_federacao(c):
    rng = random.Random(17)
    grad(c, (0, 0, LW, 80), [(22, 30, 62), (30, 40, 78), (36, 48, 88)])
    for x in range(0, LW, 9):
        F(c, (26, 34, 68), x, 0, 1, 80)
    wood = ramp((96, 62, 46))
    F(c, wood[2], 0, 78, LW, 32)                                                       # lambri com almofadas
    for x in range(2, LW, 22):
        box(c, (x, 82, 18, 24), wood, outline=wood[3])
        F(c, wood[0], x + 3, 85, 12, 1)
    F(c, GOLD, 0, 78, LW, 1)
    # janelao com a cidade a noite
    wx, wy, ww, wh = 106, 34, 155, 72
    box(c, (wx - 3, wy - 3, ww + 6, wh + 6), ramp((60, 70, 110)), outline=INK)
    old = c.get_clip()
    c.set_clip(pygame.Rect(wx, wy, ww, wh))
    night_sky(c, wy + wh, rng, cols=((8, 12, 34), (20, 28, 66), (50, 50, 100)), stars=24, x0=wx, x1=wx + ww)
    skyline(c, rng, wx - 6, wx + ww + 6, wy + wh, 18, 52, ramp((26, 30, 64)), p=0.22)
    skyline(c, rng, wx - 6, wx + ww + 6, wy + wh, 6, 24, ramp((36, 40, 80)), win=(255, 220, 140), p=0.3)
    c.set_clip(old)
    for x in range(wx + 38, wx + ww, 39):
        F(c, (40, 50, 84), x, wy, 2, wh)
    F(c, (40, 50, 84), wx, wy + 18, ww, 2)
    curtain(c, wx - 12, wy - 6, 12, wh + 8, (150, 30, 50))
    curtain(c, wx + ww, wy - 6, 12, wh + 8, (150, 30, 50))
    F(c, GOLD, wx - 14, wy - 8, ww + 28, 2)
    # selo da federacao
    pygame.draw.circle(c, INK, (183, 17), 14)
    pygame.draw.circle(c, (196, 160, 60), (183, 17), 13)
    pygame.draw.circle(c, (24, 40, 84), (183, 17), 10)
    pygame.draw.circle(c, (255, 230, 140), (183, 17), 13, 1)
    star = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = 7 if i % 2 == 0 else 3
        star.append((183 + rr * math.cos(a), 17 + rr * math.sin(a)))
    pygame.draw.polygon(c, GOLD, star)
    F(c, (255, 244, 200), 182, 12, 1, 3)
    for x in (20, 70, 297, 347):                                                        # colunas
        column(c, x, 22, 106)
    for x in (45, 322):                                                                  # arandelas
        box(c, (x - 2, 46, 5, 6), ramp(GOLD))
        F(c, (255, 244, 210), x - 1, 43, 3, 3)
        glow(c, (x, 44), 16, (80, 66, 36), 4)
    for x in (127, 240):                                                                 # mastros
        box(c, (x - 1, 30, 2, 80), ramp((200, 170, 90)), outline=None)
        F(c, GOLD, x - 2, 27, 4, 3)
    # piso de marmore com tapete
    checker_floor(c, 110, LH, (52, 66, 106), (34, 44, 76), cols=12, rows=6)
    for _ in range(140):
        x, y = rng.randrange(LW), rng.randrange(112, LH)
        F(c, (70, 86, 130), x, y, rng.randint(2, 4), 1)
    pts_ = [(160, 110), (207, 110), (236, LH), (130, LH)]
    pygame.draw.polygon(c, (130, 28, 46), pts_)
    for k in range(112, LH, 3):
        xa, xb = persp_x(130, k, 110, LH, depth=1.0), 0
        xa = 160 + (130 - 160) * (k - 110) / 50.0
        xb = 207 + (236 - 207) * (k - 110) / 50.0
        F(c, (110, 22, 40), xa + 3, k, xb - xa - 6, 1)
    line(c, GOLD, (160, 110), (130, LH))
    line(c, GOLD, (207, 110), (236, LH))
    F(c, GOLD, 0, 110, LW, 1)
    # mesa do conselho
    box(c, (112, 98, 143, 4), ramp((120, 80, 56)))
    box(c, (116, 102, 135, 8), ramp((80, 52, 38)))
    F(c, GOLD, 116, 106, 135, 1)
    box(c, (140, 95, 18, 3), ramp((236, 236, 244)))
    box(c, (200, 94, 14, 4), ramp((214, 224, 238)))
    F(c, (60, 60, 80), 226, 92, 1, 6)
    vignette(c, 0.5)


def fg_federacao(c):
    for x in (13, 353):                                                                  # pedestais com corda
        box(c, (x - 1, 126, 3, 30), ramp(GOLD))
        pygame.draw.circle(c, INK, (x, 125), 4)
        pygame.draw.circle(c, GOLD, (x, 125), 3)
        F(c, (255, 244, 200), x - 1, 124, 1, 1)
        pygame.draw.ellipse(c, (150, 110, 40), (x - 8, 155, 17, 5))
    rope = ramp((170, 30, 50))
    for x0, x1 in ((15, 44), (322, 351)):
        for k in range(x1 - x0):
            f = k / float(x1 - x0)
            y = 127 + int(9 * math.sin(f * math.pi))
            F(c, rope[1], x0 + k, y, 1, 2)
            F(c, rope[2], x0 + k, y + 2, 1, 1)


def flag(scr, x, y, cols, t, ph, w=24, rows=8):
    for j, col in enumerate(cols):
        rp = ramp(col)
        for k in range(w):
            dy = round(1.6 * math.sin(t * 3 + ph + k * 0.3) * (k / float(w)))
            Q(scr, rp[1] if (k + j) % 7 else rp[0], x + k, y + j * rows + dy, 1, rows)
        Q(scr, rp[2], x, y + j * rows + rows - 1, 3, 1)


def anim_federacao(scr, t):
    flag(scr, 128, 31, ((220, 70, 70), (240, 240, 240)), t, 0.0)
    flag(scr, 241, 31, ((70, 130, 230), (240, 220, 90)), t, 1.3)
    if (t % 4.0) < 1.2:
        a = t * 1.6
        x, y = 183 + round(15 * math.cos(a)), 17 + round(15 * math.sin(a))
        Q(scr, (255, 250, 220), x - 1, y, 3, 1)
        Q(scr, (255, 250, 220), x, y - 1, 1, 3)


# ================================================================================ PRACA
def tree(c, x, y, r, col, rng, trunk_h=30):
    rp = ramp(col)
    box(c, (x - 2, y, 5, trunk_h), ramp((86, 60, 46)))
    F(c, (60, 40, 32), x + 1, y + 4, 1, trunk_h - 6)
    blobs = []
    for _ in range(14):
        dx, dy = rng.randint(-r, r), rng.randint(-r // 2, r // 3)
        blobs.append((dy, dx, rng.randint(r // 3, r // 2 + 2)))
    for dy, dx, rr in sorted(blobs):
        pygame.draw.circle(c, INK, (x + dx, y + dy), rr + 1)
    for dy, dx, rr in sorted(blobs):
        pygame.draw.circle(c, rp[2], (x + dx, y + dy), rr)
        pygame.draw.circle(c, rp[1], (x + dx - 1, y + dy - 1), max(1, rr - 1))
        pygame.draw.circle(c, rp[0], (x + dx - rr // 2, y + dy - rr // 2), max(1, rr // 3))
    for _ in range(r * 2):
        F(c, rp[3], x + rng.randint(-r, r), y + rng.randint(-r // 2, r // 3), 1, 1)


def bg_praca(c):
    rng = random.Random(21)
    grad(c, (0, 0, LW, 100), [(8, 12, 40), (24, 26, 74), (60, 48, 110), (110, 76, 136)])
    for _ in range(60):
        x, y = rng.randrange(LW), rng.randrange(60)
        F(c, lerp((90, 90, 140), (240, 240, 255), rng.random()), x, y)
    glow(c, (300, 24), 30, (40, 40, 56), 4)
    pygame.draw.circle(c, (240, 240, 220), (300, 24), 9)
    pygame.draw.circle(c, (210, 212, 196), (297, 22), 2)
    pygame.draw.circle(c, (214, 214, 200), (303, 28), 1)
    F(c, (255, 255, 240), 296, 17, 3, 1)
    skyline(c, rng, -10, LW + 10, 98, 16, 54, ramp((28, 28, 66)), p=0.16)
    skyline(c, rng, -10, LW + 10, 100, 6, 28, ramp((38, 36, 80)), win=(255, 220, 150), p=0.12)
    gr = ramp((40, 84, 70))
    grad(c, (0, 98, LW, 62), [(36, 74, 64), (28, 60, 54), (18, 42, 40)])
    for _ in range(420):
        x, y = rng.randrange(LW), rng.randrange(100, LH)
        F(c, gr[0] if rng.random() < 0.4 else gr[2], x, y, 1, 2 if y > 120 else 1)
    stone = ramp((96, 98, 126))
    pygame.draw.polygon(c, stone[2], [(150, 98), (217, 98), (300, LH), (66, LH)])      # caminho de pedras
    ys = floor_rows(98, LH, 9, 1.5)
    for r in range(9):
        ya, yb = ys[r], ys[r + 1]
        xa = 150 + (66 - 150) * (ya - 98) / 62.0
        xb = 217 + (300 - 217) * (ya - 98) / 62.0
        sw = max(4, int((yb - ya) * 2.2))
        x = xa + (r % 2) * sw // 2
        while x < xb - 2:
            w = min(sw - 1, int(xb - x - 1))
            if w >= 2:
                tone = stone[1] if rng.random() < 0.6 else lerp(stone[1], stone[0], 0.4)
                F(c, tone, x, ya + 1, w, max(1, yb - ya - 1))
                F(c, lerp(tone, stone[0], 0.5), x, ya + 1, w, 1)
            x += sw
    tree(c, 30, 56, 26, (40, 120, 90), rng, 46)
    tree(c, 340, 50, 30, (40, 120, 90), rng, 52)
    tree(c, 82, 76, 15, (46, 104, 92), rng, 26)
    # chafariz
    st = ramp((110, 116, 146))
    pygame.draw.ellipse(c, INK, (153, 85, 61, 16))
    pygame.draw.ellipse(c, st[1], (154, 86, 59, 14))
    pygame.draw.ellipse(c, (70, 130, 190), (158, 88, 51, 8))
    F(c, (150, 200, 240), 166, 90, 14, 1)
    box(c, (180, 72, 6, 16), st)
    pygame.draw.ellipse(c, INK, (171, 68, 25, 7))
    pygame.draw.ellipse(c, st[0], (172, 69, 23, 5))
    F(c, (90, 150, 210), 176, 70, 15, 2)
    # banco
    wood = ramp((120, 80, 52))
    for y in (106, 110):
        box(c, (86, y, 64, 2), wood, outline=None)
    for y in (114, 117):
        box(c, (84, y, 68, 2), wood, outline=None)
    for x in (88, 145):
        F(c, (34, 36, 50), x, 105, 2, 20)
    # postes
    for x in (53, 283):
        box(c, (x - 1, 54, 3, 58), ramp((40, 46, 70)))
        box(c, (x - 5, 46, 11, 3), ramp((50, 56, 84)))
        F(c, (255, 236, 180), x - 3, 49, 7, 5)
        F(c, (255, 252, 230), x - 1, 50, 3, 2)
        box(c, (x - 4, 54, 9, 2), ramp((50, 56, 84)))
        glow(c, (x, 51), 24, (70, 60, 34), 4)
        glow_ellipse(c, (x - 30, 110, 60, 14), (60, 50, 26))
    vignette(c, 0.5)


def fg_praca(c):
    rng = random.Random(22)
    for cx in (12, 355):                                                                 # arbustos com flores
        leaf = ramp((40, 120, 80))
        blobs = [(rng.randint(-18, 18), rng.randint(-10, 12), rng.randint(6, 10)) for _ in range(12)]
        for dx, dy, r in blobs:
            pygame.draw.circle(c, INK, (cx + dx, 148 + dy), r + 1)
        for dx, dy, r in sorted(blobs, key=lambda b: b[1]):
            pygame.draw.circle(c, leaf[2], (cx + dx, 148 + dy), r)
            pygame.draw.circle(c, leaf[1], (cx + dx - 1, 147 + dy), r - 2)
            F(c, leaf[0], cx + dx - r // 2, 146 + dy - r // 2, 3, 1)
        for _ in range(7):
            fx, fy = cx + rng.randint(-16, 16), 144 + rng.randint(-8, 10)
            F(c, (255, 140, 180), fx - 1, fy, 3, 1)
            F(c, (255, 140, 180), fx, fy - 1, 1, 3)
            F(c, (255, 230, 120), fx, fy, 1, 1)


def anim_praca(scr, t):
    hop = int(abs(math.sin(t * 1.3)) * 1.5) if (t % 5.0) < 2.0 else 0                      # pombo-robo
    px, py = 233, 147 - hop
    peck = 1 if blink(t, 1.6, 0.25) else 0
    Q(scr, INK, px - 6, py - 3, 12, 6)
    Q(scr, (130, 140, 160), px - 5, py - 3, 10, 5)
    Q(scr, (170, 180, 200), px - 4, py - 3, 6, 1)
    Q(scr, (100, 110, 130), px - 7, py - 2, 4, 3)
    Q(scr, INK, px + 3, py - 7 + peck, 5, 5)
    Q(scr, (150, 160, 180), px + 4, py - 6 + peck, 3, 3)
    Q(scr, GOLD, px + 7, py - 5 + peck, 2, 1)
    Q(scr, (255, 60, 60) if blink(t, 1.1, 0.5) else (90, 20, 20), px + 5, py - 5 + peck, 1, 1)
    Q(scr, (80, 90, 110), px - 2, py + 2, 1, 2)
    Q(scr, (80, 90, 110), px + 2, py + 2, 1, 2)
    for i in range(5):                                                                     # agua do chafariz
        ph = (t * 1.4 + i * 0.2) % 1.0
        x = 183 + round((i - 2) * 5 * ph)
        y = 70 - round(9 * math.sin(ph * math.pi))
        Q(scr, (150, 210, 255), x, y)
    motes(scr, t, (20, 60, 327, 70), 12, (220, 240, 140), 4, 1.4)                          # vagalumes


# ================================================================================ LABORATORIO
def hexgrid(c, rect, col, lit, rng):
    x, y, w, h = rect
    for r, yy in enumerate(range(y, y + h, 10)):
        for xx in range(x - 12 + (r % 2) * 12, x + w, 24):
            pts_ = [(xx + 4, yy), (xx + 12, yy), (xx + 16, yy + 5), (xx + 12, yy + 10), (xx + 4, yy + 10), (xx, yy + 5)]
            if rng.random() < 0.08:
                pygame.draw.polygon(c, lit, pts_)
            pygame.draw.polygon(c, col, pts_, 1)


def tank(c, x, y0, y1, liq):
    glass = ramp((70, 110, 130))
    lq = ramp(liq)
    pygame.draw.rect(c, INK, (x - 11, y0 - 1, 22, y1 - y0 + 2), border_radius=8)
    pygame.draw.rect(c, (20, 40, 54), (x - 10, y0, 20, y1 - y0), border_radius=8)
    grad(c, (x - 8, y0 + 14, 16, y1 - y0 - 18), [mul(lq[1], 0.55), mul(lq[1], 0.8), mul(lq[2], 0.9)])
    F(c, lq[0], x - 8, y0 + 14, 16, 1)
    F(c, (220, 250, 255), x - 6, y0 + 4, 1, y1 - y0 - 8)
    F(c, glass[0], x + 6, y0 + 6, 1, y1 - y0 - 12)
    for yy in (y0, y1 - 6):
        box(c, (x - 12, yy, 24, 6), ramp((110, 126, 146)))
        F(c, (60, 70, 90), x - 12, yy + 3, 24, 1)
    glow(c, (x, (y0 + y1) // 2), 16, mul(liq, 0.18), 3)


def bg_laboratorio(c):
    rng = random.Random(23)
    grad(c, (0, 0, LW, 113), [(4, 12, 22), (8, 22, 34), (12, 32, 46)])
    hexgrid(c, (0, 0, LW, 113), (18, 44, 60), (14, 60, 66), rng)
    for x in (33, 300):                                                                   # fitas de luz
        F(c, (180, 255, 240), x, 2, 40, 1)
        F(c, (90, 140, 140), x, 1, 40, 1)
        beam(c, (x + 20, 3), (x + 20, 113), 20, 40, (8, 30, 28), 3, 0.15)
    # piso de chapas com juntas luminosas
    plate = ramp((34, 52, 66))
    grad(c, (0, 113, LW, 47), [(30, 48, 62), (20, 34, 46), (12, 20, 30)])
    for y in floor_rows(113, LH, 4, 1.4)[1:-1]:
        F(c, (10, 16, 24), 0, y, LW, 1)
        F(c, plate[0], 0, y + 1, LW, 1)
    persp_lines(c, 113, LH, (10, 16, 24), 6, 46, depth=0.4)
    F(c, (0, 255, 190), 0, 113, LW, 1)
    for i, x in enumerate((20, 50, 80, 287, 317)):                                        # tubos
        liq = ((0, 210, 170), (80, 220, 255), (150, 120, 255), (0, 210, 170), (255, 130, 200))[i]
        tank(c, x, 28, 114, liq)
    # consoles
    for x, w in ((117, 32), (218, 42)):
        pygame.draw.polygon(c, INK, [(x - 1, 96), (x + w + 1, 96), (x + w + 4, 114), (x - 4, 114)])
        pygame.draw.polygon(c, (34, 50, 70), [(x, 97), (x + w, 97), (x + w + 3, 113), (x - 3, 113)])
        F(c, (60, 80, 104), x, 97, w, 1)
        box(c, (x + 2, 82, w - 4, 14), ramp((30, 44, 60)), outline=INK)
        F(c, (4, 20, 26), x + 4, 84, w - 8, 10)
        for k in range(0, w - 6, 5):
            F(c, (255, 90, 90) if k % 10 else (90, 240, 120), x + 3 + k, 104, 2, 2)
    for i in range(3):                                                                    # cabos no chao
        P._catenary(c, (100 + i * 12, 114), (166 + i * 9, 114), 5 + i * 2, (14, 22, 30), 1, 10)
    # pedestal do holograma
    pygame.draw.ellipse(c, INK, (155, 101, 57, 15))
    pygame.draw.ellipse(c, (44, 64, 84), (156, 102, 55, 13))
    pygame.draw.ellipse(c, (0, 210, 210), (163, 104, 41, 7), 1)
    beam(c, (183, 107), (183, 46), 16, 34, (0, 60, 70), 3, 0.3)
    vignette(c, 0.55)


_LAB_TUBES = ((20, (160, 255, 220)), (50, (180, 240, 255)), (80, (210, 200, 255)), (287, (160, 255, 220)),
              (317, (255, 200, 230)))


def anim_laboratorio(scr, t):
    for j, (x, col) in enumerate(_LAB_TUBES):                                              # bolhas
        for i in range(4):
            ph = (t * (0.35 + 0.05 * i) + i * 0.27 + j * 0.13) % 1.0
            Q(scr, col, x - 4 + (i * 3) % 8 + round(math.sin(t * 3 + i)), round(104 - ph * 62), 1, 1)
    hy = 70 + round(2 * math.sin(t * 1.5))                                                  # holograma
    for yy in range(-15, 16):
        half = round(math.sqrt(max(0, 225 - yy * yy)))
        Q(scr, (0, 230, 230), 183 - half, hy + yy)
        Q(scr, (0, 230, 230), 183 + half, hy + yy)
        for j in range(2):
            w = 15 * abs(math.cos(t * 0.9 + j * math.pi / 2))
            hw = round(w * math.sqrt(max(0.0, 1 - (yy / 15.5) ** 2)))
            if hw > 1:
                Q(scr, (0, 180, 200), 183 - hw, hy + yy)
                Q(scr, (0, 180, 200), 183 + hw, hy + yy)
    Q(scr, (0, 200, 220), 168, hy, 31, 1)
    sy = hy - 15 + int((t * 16) % 31)
    Q(scr, (150, 255, 255), 172, sy, 23, 1)
    for x, w in ((117, 32), (218, 42)):                                                   # telas dos consoles
        for i in range(w - 8):
            Q(scr, (0, 255, 190), x + 4 + i, 89 + round(3 * math.sin(t * 4 + i * 0.6 + x)), 1, 1)
        for i in range(0, w - 6, 5):
            on = blink(t, 0.7 + (i // 5) * 0.2, 0.5, i * 0.3 + x)
            Q(scr, (255, 90, 90) if on else (60, 30, 30), x + 3 + i, 104, 2, 2) if i % 10 else None


def fg_laboratorio(c):
    pipe = ramp((70, 90, 110))
    F(c, (20, 30, 42), 0, 92, 17, 68)
    for x in (2, 9):
        box(c, (x, 92, 5, 68), pipe, outline=None)
        for y in (98, 124, 148):
            box(c, (x - 1, y, 7, 3), ramp((100, 120, 140)))
    box(c, (334, 132, 33, 3), ramp((60, 76, 100)))                                       # suporte com frascos
    for i, col in enumerate(((0, 230, 180), (255, 130, 200), (120, 200, 255))):
        x = 340 + i * 10
        pygame.draw.polygon(c, INK, [(x - 2, 118), (x + 2, 118), (x + 2, 123), (x + 5, 132), (x - 5, 132),
                                     (x - 2, 123)])
        pygame.draw.polygon(c, (170, 210, 226), [(x - 1, 119), (x + 1, 119), (x + 1, 124), (x + 4, 131),
                                                 (x - 4, 131), (x - 1, 124)])
        F(c, col, x - 3, 127, 7, 4)
        F(c, lerp(col, (255, 255, 255), 0.5), x - 3, 127, 7, 1)
    for x in (336, 362):
        box(c, (x, 135, 3, 25), ramp((40, 54, 74)))


# ================================================================================ AEROPORTO
def plane(c, x, y, col):
    rp = ramp(col)
    pygame.draw.polygon(c, rp[1], [(x - 30, y + 7), (x + 22, y - 6), (x + 30, y - 7), (x + 27, y - 3), (x - 26, y + 10)])
    pygame.draw.polygon(c, rp[2], [(x - 3, y + 1), (x + 7, y - 1), (x - 10, y + 13), (x - 15, y + 13)])
    pygame.draw.polygon(c, rp[2], [(x - 25, y + 7), (x - 20, y + 5), (x - 28, y - 2), (x - 31, y - 2)])
    for i in range(6):
        F(c, (255, 230, 160), x - 16 + i * 6, y + 4 - i * 2, 1, 1)
    F(c, (255, 70, 70), x + 29, y - 7, 1, 1)


def bg_aeroporto(c):
    rng = random.Random(24)
    grad(c, (0, 0, LW, 80), [(12, 18, 54), (40, 38, 100), (110, 70, 130), (220, 130, 110)])
    for _ in range(26):
        F(c, (200, 200, 240), rng.randrange(LW), rng.randrange(30))
    skyline(c, rng, -10, LW + 10, 80, 3, 12, ramp((34, 30, 70)), p=0.12)
    F(c, (22, 22, 44), 0, 80, LW, 20)                                                     # pista
    for x in range(0, LW, 10):
        F(c, (255, 200, 120), x + 3, 86, 1, 1)
        F(c, (120, 200, 255), x + 7, 94, 1, 1)
    F(c, (60, 60, 90), 0, 90, LW, 1)
    box(c, (44, 46, 6, 34), ramp((50, 50, 80)))                                            # torre de controle
    pygame.draw.polygon(c, (60, 66, 110), [(38, 40), (56, 40), (54, 47), (40, 47)])
    F(c, (130, 210, 240), 40, 42, 14, 2)
    plane(c, 150, 30, (60, 62, 110))
    for x in range(0, LW + 1, 37):                                                         # caixilhos
        box(c, (x - 1, 0, 3, 100), ramp((36, 46, 76)), outline=None)
    F(c, (30, 40, 66), 0, 0, LW, 4)
    F(c, (70, 100, 150), 0, 99, LW, 1)
    for i in range(5):                                                                     # reflexos
        x = 20 + i * 77
        pygame.draw.polygon(c, (64, 70, 120), [(x, 95), (x + 3, 95), (x + 23, 6), (x + 20, 6)])
    # piso brilhante
    grad(c, (0, 100, LW, 60), [(70, 80, 112), (54, 62, 92), (34, 40, 62)])
    for y in floor_rows(100, LH, 5, 1.5)[1:-1]:
        F(c, (60, 70, 100), 0, y, LW, 1)
    persp_lines(c, 100, LH, (60, 70, 100), 9, 36, depth=0.35)
    for x in (60, 180, 300):
        streak(c, x, 101, 150, 20, (50, 40, 50))
    # painel de voos
    for x in (230, 330):
        F(c, (60, 70, 90), x, 0, 1, 8)
    box(c, (207, 8, 146, 48), ramp((20, 20, 32)), outline=(4, 4, 8))
    F(c, (10, 10, 16), 210, 11, 140, 42)
    text(c, "PARTIDAS", 213, 13, (255, 200, 80))
    for i, (code, hh) in enumerate((("SF101", "08:15"), ("LX220", "09:40"), ("SL007", "11:05"), ("CC900", "13:30"))):
        y = 21 + i * 8
        F(c, (24, 24, 36), 212, y - 1, 136, 7)
        text(c, code, 214, y, (255, 200, 80))
        text(c, hh, 260, y, (230, 230, 240))
        F(c, (90, 220, 120) if i % 2 == 0 else (255, 200, 80), 334, y + 1, 11, 3)
    # esteira de bagagem
    box(c, (0, 117, 172, 4), ramp((110, 130, 160)), outline=None)
    F(c, (20, 24, 34), 0, 121, 172, 6)
    box(c, (0, 127, 172, 6), ramp((44, 54, 74)), outline=None)
    F(c, (8, 10, 16), 0, 133, 172, 1)
    # cadeiras
    seat = ramp((50, 100, 180))
    for x in range(213, 320, 22):
        box(c, (x, 104, 19, 10), seat)
        box(c, (x + 1, 114, 18, 4), ramp((40, 84, 156)))
        F(c, (110, 120, 140), x + 9, 118, 2, 10)
    F(c, (90, 100, 120), 211, 127, 112, 2)
    vignette(c, 0.45)


_BAGS = [((200, 60, 60), 15, 7), ((60, 120, 220), 12, 9), ((240, 200, 80), 17, 7), ((90, 200, 140), 13, 8),
         ((180, 120, 220), 15, 7)]


def anim_aeroporto(scr, t):
    off = int(t * 15) % 4
    for x in range(-4 + off, 172, 4):                                                      # esteira andando
        Q(scr, (34, 40, 54), x, 121, 1, 6)
    for i, (col, w, h) in enumerate(_BAGS):                                                # malas
        x = int((i * 37 + t * 15) % 200) - 23
        x0, x1 = max(0, x), min(172, x + w)
        if x1 > x0:
            rp = ramp(col)
            Q(scr, INK, x0, 126 - h, x1 - x0, h + 1)
            Q(scr, rp[1], x0, 127 - h, x1 - x0, h - 1)
            Q(scr, rp[0], x0, 127 - h, x1 - x0, 1)
            Q(scr, rp[2], x0, 125, x1 - x0, 1)
    for x in range(0, LW, 10):                                                             # luzes da pista
        if (x // 10 - int(t * 8)) % 12 == 0:
            Q(scr, (255, 255, 230), x + 3, 86)
            AG(scr, (x + 3, 86), 3, (90, 80, 40), 2)
    row = int(t / 1.6) % 4                                                                 # painel trocando
    if (t % 1.6) < 0.25:
        y = 21 + row * 8
        Q(scr, (24, 24, 36), 213, y - 1, 116, 7)
        for i in range(14):
            Q(scr, (255, 200, 80) if (i + int(t * 20)) % 2 else (120, 90, 40), 214 + i * 8, y + 1, 5, 4)
    if blink(t, 1.4, 0.5):
        Q(scr, (255, 60, 60), 47, 44)


def fg_aeroporto(c):
    foliage(c, (350, 136), ((-0.5, 26), (-1.0, 30), (-1.6, 32), (-2.2, 30), (-2.7, 26), (-1.3, 18)),
            leaf=(70, 170, 110), size=(12, 4))
    pot(c, 336, 136, 28, 24, (96, 104, 128))
    box(c, (2, 130, 31, 3), ramp((110, 120, 140)))                                         # carrinho de malas
    box(c, (5, 115, 17, 15), ramp((200, 60, 60)))
    F(c, (240, 220, 200), 12, 113, 4, 2)
    box(c, (10, 105, 13, 10), ramp((60, 120, 220)))
    line(c, (120, 130, 150), (32, 131), (37, 106))
    for x in (6, 28):
        pygame.draw.circle(c, (16, 18, 26), (x, 136), 3)
        F(c, (80, 84, 100), x, 135, 1, 1)


# ================================================================================ DOJO
def shoji(c, x, y, w, h, lit=True):
    box(c, (x - 2, y - 2, w + 4, h + 4), ramp((70, 48, 40)))
    grad(c, (x, y, w, h), [(236, 226, 196), (214, 204, 180), (180, 172, 160)] if lit else
         [(150, 146, 136), (120, 116, 110)])
    for gx in range(x + w // 3, x + w - 1, w // 3):
        F(c, (80, 56, 44), gx, y, 1, h)
    for gy in range(y + h // 6, y + h - 1, h // 6):
        F(c, (80, 56, 44), x, gy, w, 1)
        F(c, (250, 244, 224), x, gy + 1, w, 1) if lit else None


def bg_dojo(c):
    rng = random.Random(25)
    planks_v(c, (0, 0, LW, 110), ramp((84, 60, 52)), 6, rng)
    tint(c, (0, 0, LW, 110), (170, 160, 170))
    box(c, (0, 8, LW, 5), ramp((60, 40, 34)), outline=INK)                               # viga
    for x in (10, 46, 82):                                                               # shoji
        shoji(c, x, 20, 32, 84)
    for x in (231, 267):
        shoji(c, x, 20, 32, 84)
    # painel aberto: jardim a noite
    x0 = 303
    box(c, (x0 - 2, 18, 36, 88), ramp((70, 48, 40)))
    old = c.get_clip()
    c.set_clip(pygame.Rect(x0, 20, 32, 84))
    grad(c, (x0, 20, 32, 84), [(10, 16, 40), (20, 30, 66), (34, 48, 90)])
    pygame.draw.circle(c, (240, 240, 220), (x0 + 22, 32), 5)
    F(c, (210, 210, 196), x0 + 20, 31, 2, 1)
    for bx in (x0 + 4, x0 + 13, x0 + 27):
        box(c, (bx, 30, 2, 74), ramp((40, 100, 80)), outline=None)
        for yy in range(38, 100, 11):
            F(c, (20, 60, 50), bx, yy, 2, 1)
            line(c, (50, 130, 90), (bx + 2, yy), (bx + 7, yy - 3))
    F(c, (30, 40, 40), x0, 100, 32, 4)
    c.set_clip(old)
    # tokonoma com pergaminho
    F(c, (40, 28, 26), 140, 16, 87, 94)
    F(c, (60, 42, 36), 140, 16, 87, 2)
    box(c, (142, 100, 83, 6), ramp((110, 76, 56)))
    box(c, (174, 21, 19, 74), ramp((236, 226, 196)))
    F(c, (70, 46, 34), 172, 19, 23, 3)
    F(c, (70, 46, 34), 172, 94, 23, 3)
    for i, ch in enumerate("GANBARE"):
        P._pixtext(c, ch, 181, 25 + i * 9, 1, (36, 26, 30))
    F(c, (200, 50, 40), 179, 88, 7, 4)
    box(c, (204, 92, 8, 8), ramp((60, 90, 140)))                                         # ikebana
    for a in (-1.2, -1.6, -2.0):
        line(c, (40, 110, 60), (208, 92), (208 + 10 * math.cos(a), 92 + 12 * math.sin(a)))
    F(c, (255, 140, 170), 210, 81, 2, 2)
    F(c, (255, 200, 210), 204, 80, 2, 2)
    # suporte de bokken
    box(c, (118, 50, 18, 3), ramp((70, 46, 34)))
    box(c, (118, 90, 18, 3), ramp((70, 46, 34)))
    for i in range(3):
        box(c, (120 + i * 6, 30, 2, 70), ramp((190, 150, 96)), outline=None)
    F(c, (40, 26, 22), 118, 50, 1, 50)
    # tatame
    straw = ramp((160, 164, 104))
    F(c, (150, 30, 30), 0, 108, LW, 2)
    ys = floor_rows(110, LH, 4, 1.35)
    for r in range(4):
        ya, yb = ys[r], ys[r + 1]
        for y in range(ya, yb):
            F(c, straw[1] if (y // 1) % 2 else lerp(straw[1], straw[0], 0.3), 0, y, LW, 1)
        F(c, (40, 46, 30), 0, ya, LW, 1)
    for i in range(-5, 6):
        xb = 183 + i * 74 + (37 if 0 else 0)
        line(c, (40, 46, 30), (persp_x(xb, 110, 110, LH, depth=0.45), 110), (xb, LH))
    dith(c, (0, 110, LW, 50), straw[2], 1)
    glow(c, (183, 60), 70, (24, 20, 12), 4)
    glow_ellipse(c, (70, 118, 226, 26), (40, 34, 20))
    vignette(c, 0.55)


_PETALS = [((i * 50) % LW, (i * 18) % 110) for i in range(16)]


def lantern(scr, x, y, t, i):
    d = round(1.3 * math.sin(t * 1.2 + i))
    AG(scr, (x + d, y + 9), 15, (70, 36, 18), 3)
    rp = ramp((220, 70, 50))
    Q(scr, (40, 30, 30), x - 3 + d, y - 1, 7, 2)
    Q(scr, INK, x - 7 + d, y + 1, 15, 17)
    Q(scr, rp[1], x - 6 + d, y + 1, 13, 17)
    Q(scr, (255, 150, 96), x - 3 + d, y + 3, 6, 12)
    Q(scr, (255, 214, 150), x - 1 + d, y + 5, 2, 7)
    for yy in (y + 4, y + 9, y + 14):
        Q(scr, rp[3], x - 6 + d, yy, 13, 1)
    Q(scr, (40, 30, 30), x - 3 + d, y + 18, 7, 2)
    Q(scr, (40, 30, 30), x + d, y - 6, 1, 5)


def anim_dojo(scr, t):
    for i, x in enumerate((77, 290)):                                                    # lanternas
        lantern(scr, x, 20, t, i)
    for i, (x, y) in enumerate(_PETALS):                                                 # petalas
        yy = int((y + t * (7 + i % 4 * 2)) % 156)
        xx = int((x + t * 4 + 6 * math.sin(t * 1.5 + i)) % LW)
        Q(scr, (255, 170, 200) if i % 2 else (255, 210, 225), xx, yy, 2, 1)


def fg_dojo(c):
    drum = ramp((120, 50, 36))                                                           # taiko
    box(c, (3, 134, 34, 22), drum)
    for x in range(5, 36, 4):
        F(c, GOLD, x, 137, 1, 1)
        F(c, GOLD, x, 152, 1, 1)
    pygame.draw.ellipse(c, INK, (2, 128, 36, 11))
    pygame.draw.ellipse(c, (232, 214, 176), (3, 129, 34, 9))
    pygame.draw.ellipse(c, (190, 170, 140), (8, 131, 24, 5), 1)
    box(c, (5, 156, 30, 4), ramp((70, 46, 34)))
    box(c, (334, 146, 30, 12), ramp((70, 46, 34)))                                     # bonsai
    box(c, (337, 140, 24, 6), ramp((50, 80, 130)))
    line(c, (80, 56, 44), (348, 140), (344, 126))
    line(c, (80, 56, 44), (346, 130), (356, 122))
    leaf = ramp((50, 130, 84))
    for cx, cy, r in ((342, 122, 7), (356, 119, 6), (349, 115, 6)):
        pygame.draw.circle(c, INK, (cx, cy), r + 1)
        pygame.draw.circle(c, leaf[1], (cx, cy), r)
        pygame.draw.circle(c, leaf[0], (cx - 2, cy - 2), r // 2)
        F(c, leaf[2], cx, cy + r - 2, r, 1)


# ================================================================================ FABRICA
def bg_fabrica(c):
    rng = random.Random(26)
    wall = ramp((60, 70, 96))
    corrugated(c, (0, 16, LW, 92), wall)
    tint(c, (0, 16, LW, 92), (190, 196, 220))
    for x in range(0, LW, 46):
        F(c, wall[3], x, 16, 1, 92)
    for x in range(20, LW, 73):                                                           # janelas altas
        box(c, (x, 24, 40, 24), ramp((70, 90, 120)), outline=INK)
        grad(c, (x + 1, 25, 38, 22), [(120, 160, 200), (80, 120, 170)])
        for gx in range(x + 10, x + 40, 10):
            F(c, (50, 64, 90), gx, 25, 1, 22)
        F(c, (50, 64, 90), x + 1, 35, 38, 1)
        F(c, (200, 230, 250), x + 2, 26, 1, 8)
        beam(c, (x + 20, 48), (x + 8, 110), 18, 30, (22, 28, 36), 3, 0.2)
    F(c, (36, 40, 58), 0, 0, LW, 16)                                                      # trelica
    steel = ramp((110, 116, 136))
    for x in range(0, LW + 16, 16):
        line(c, steel[2], (x, 1), (x + 16, 15))
        line(c, steel[2], (x + 16, 1), (x, 15))
    F(c, steel[1], 0, 0, LW, 2)
    F(c, steel[1], 0, 14, LW, 2)
    F(c, steel[0], 0, 14, LW, 1)
    for x in (40, 173):                                                                   # canos
        box(c, (x, 16, 5, 84), ramp((90, 104, 126)), outline=INK)
        for y in (40, 70):
            box(c, (x - 1, y, 7, 3), ramp((120, 134, 156)))
    box(c, (0, 58, 173, 3), ramp((80, 94, 116)), outline=INK)
    for x in (100, 233):                                                                  # sirenes (base)
        box(c, (x - 5, 19, 10, 4), ramp((50, 56, 72)))
    # maquina do braco robotico
    box(c, (293, 40, 27, 52), ramp((60, 70, 94)))
    F(c, (240, 190, 40), 293, 40, 27, 4)
    for k in range(0, 27, 6):
        F(c, (30, 30, 36), 293 + k, 40, 3, 4)
    for i in range(4):
        F(c, (20, 26, 36), 298 + i * 5, 64, 3, 3)
        F(c, (90, 240, 120) if i % 2 else (255, 90, 80), 299 + i * 5, 65, 1, 1)
    # chao de concreto
    grad(c, (0, 108, LW, 52), [(56, 60, 72), (42, 46, 58), (26, 28, 38)])
    speckle(c, (0, 108, LW, 52), ((66, 70, 84), (34, 36, 46)), 300, rng)
    persp_lines(c, 108, LH, (36, 40, 50), 4, 70)
    for k in range(-4, LW, 8):                                                             # faixa de perigo
        pygame.draw.polygon(c, (230, 180, 40), [(k, 141), (k + 4, 141), (k + 7, 137), (k + 3, 137)])
    F(c, (20, 20, 26), 0, 136, LW, 1)
    F(c, (20, 20, 26), 0, 141, LW, 1)
    # esteira
    box(c, (0, 92, LW, 4), ramp((60, 66, 84)), outline=None)
    F(c, (24, 26, 34), 0, 96, LW, 7)
    for x in range(4, LW, 9):
        pygame.draw.circle(c, (70, 76, 96), (x, 99), 2)
        F(c, (110, 116, 136), x - 1, 98, 1, 1)
    F(c, (130, 140, 160), 0, 92, LW, 1)
    for x in range(10, LW, 40):
        box(c, (x, 103, 3, 10), ramp((50, 56, 72)))
    F(c, (14, 16, 22), 0, 113, LW, 1)
    vignette(c, 0.55)


def anim_fabrica(scr, t):
    off = int(t * 20) % 10
    for x in range(-10 + off, LW, 10):                                                   # esteira andando
        Q(scr, (44, 48, 60), x, 93, 1, 2)
    for i in range(7):                                                                   # Zes na esteira
        x = int((i * 57 + t * 20) % 400) - 20
        Q(scr, INK, x - 9, 86, 18, 7)
        Q(scr, (100, 110, 126), x - 8, 89, 16, 3)
        Q(scr, (160, 170, 186), x - 8, 87, 16, 2)
        Q(scr, (200, 210, 224), x - 6, 87, 6, 1)
        Q(scr, (0, 230, 255) if (i + int(t * 2)) % 3 else (110, 240, 130), x, 88, 1, 1)
    a = 0.6 * math.sin(t * 1.3)                                                           # braco robotico
    j1 = (306, 44)
    j2 = (round(j1[0] - 30 * math.cos(a + 0.6)), round(j1[1] + 23 + 13 * math.sin(a)))
    j3 = (j2[0] - 7, 84)
    for (ax, ay), (bx, by), w, col in ((j1, j2, 4, (240, 190, 40)), (j2, j3, 3, (200, 160, 40))):
        n = max(abs(bx - ax), abs(by - ay), 1)
        for k in range(n + 1):
            Q(scr, col, round(ax + (bx - ax) * k / n) - w // 2, round(ay + (by - ay) * k / n) - w // 2, w, w)
    Q(scr, (60, 66, 84), j1[0] - 2, j1[1] - 2, 4, 4)
    Q(scr, (60, 66, 84), j2[0] - 1, j2[1] - 1, 3, 3)
    Q(scr, (120, 130, 150), j3[0] - 3, j3[1], 7, 2)
    Q(scr, (120, 130, 150), j3[0] - 3, j3[1] + 2, 1, 2)
    Q(scr, (120, 130, 150), j3[0] + 3, j3[1] + 2, 1, 2)
    if blink(t, 0.5, 0.4):                                                                # faiscas
        for i in range(5):
            ang = t * 7 + i * 1.3
            Q(scr, (255, 220, 120), j3[0] + round(4 * math.cos(ang)), j3[1] + 3 + round(3 * abs(math.sin(ang))))
    for i, x in enumerate((100, 233)):                                                   # sirenes
        on = blink(t, 1.0, 0.5, i * 0.5)
        Q(scr, INK, x - 4, 14, 9, 6)
        Q(scr, (255, 140, 30) if on else (110, 60, 20), x - 3, 15, 7, 4)
        Q(scr, (255, 220, 160) if on else (140, 80, 30), x - 2, 15, 2, 1)
        if on:
            AG(scr, (x, 17), 13, (90, 46, 10), 3)


def fg_fabrica(c):
    for i, x in enumerate((3, 21)):                                                       # barris
        rp = ramp((40, 90, 160) if i else (200, 70, 50))
        box(c, (x, 128, 16, 30), rp)
        F(c, rp[0], x + 2, 129, 2, 28)
        for y in (134, 150):
            F(c, (20, 26, 36), x, y, 16, 2)
        pygame.draw.ellipse(c, rp[2], (x, 126, 16, 4))
    cb = ramp((140, 100, 60))
    box(c, (332, 130, 35, 30), cb)                                                         # caixote
    for k in (0, 1):
        line(c, cb[3], (332, 130 + k), (366, 159 + k))
        line(c, cb[3], (366, 130 + k), (332, 159 + k))
    pygame.draw.rect(c, cb[3], (334, 132, 31, 26), 1)


# ================================================================================ LANCHONETE
def neon_text_sprite(word, col, on, px=2):
    key = ("neon", word, col, on, px)
    sp = _SP.get(key)
    if sp is None:
        w = P.pixtext_w(word, px) + 10
        h = 5 * px + 10
        lo = pygame.Surface((w, h))
        lo.fill((0, 0, 0))
        c_on = col if on else mul(col, 0.3)
        if on:
            P._pixtext(lo, word, 4, 5, px, mul(col, 0.35))
            P._pixtext(lo, word, 6, 5, px, mul(col, 0.35))
            P._pixtext(lo, word, 5, 4, px, mul(col, 0.35))
            P._pixtext(lo, word, 5, 6, px, mul(col, 0.35))
        P._pixtext(lo, word, 5, 5, px, c_on)
        pygame.draw.rect(lo, (0, 200, 230) if on else (20, 60, 70), (1, 1, w - 2, h - 2), 1)
        sp = pygame.transform.scale(lo, (w * S, h * S))
        _SP[key] = sp
    return sp


def bg_lanchonete(c):
    rng = random.Random(28)
    grad(c, (0, 0, LW, 66), [(18, 28, 56), (26, 40, 74)])
    for x in range(0, LW, 3):
        if x % 9 == 0:
            F(c, (22, 34, 64), x, 0, 1, 66)
    for y in range(66, 96, 5):                                                            # azulejos xadrez
        for x in range(0, LW, 5):
            col = (226, 230, 236) if ((x // 5) + (y // 5)) % 2 else (40, 150, 160)
            F(c, col, x, y, 5, 5)
    tint(c, (0, 66, LW, 30), (150, 160, 190))
    F(c, (200, 210, 230), 0, 65, LW, 1)
    # janela: rua a noite
    wx, wy, ww, wh = 13, 17, 104, 70
    box(c, (wx - 3, wy - 3, ww + 6, wh + 6), ramp((60, 90, 130)), outline=INK)
    old = c.get_clip()
    c.set_clip(pygame.Rect(wx, wy, ww, wh))
    night_sky(c, wy + wh, rng, cols=((8, 12, 34), (20, 28, 62), (40, 44, 90)), stars=14, x0=wx, x1=wx + ww)
    skyline(c, rng, wx - 4, wx + ww + 4, wy + 58, 12, 40, ramp((24, 28, 60)), p=0.28)
    F(c, (30, 30, 46), wx, wy + 58, ww, 12)
    F(c, (240, 200, 90), wx, wy + 64, ww, 1)
    for k in range(wx, wx + ww, 8):
        F(c, (30, 30, 46), k + 4, wy + 64, 3, 1)
    c.set_clip(old)
    F(c, (60, 90, 130), wx + ww // 2 - 1, wy, 2, wh)
    F(c, (160, 200, 230), wx + 2, wy + 2, 1, 12)
    # cardapio luminoso
    box(c, (226, 12, 128, 46), ramp((14, 16, 28)), outline=(4, 4, 10))
    pygame.draw.rect(c, (255, 120, 180), (227, 13, 126, 44), 1)
    for i, (w, p) in enumerate(((60, "890"), (50, "1250"), (70, "690"), (40, "450"))):
        y = 18 + i * 9
        F(c, (220, 230, 245), 233, y + 2, w - 4, 2)
        F(c, (120, 130, 150), 233, y + 4, w - 14, 1)
        text(c, p, 346 - text_w(p), y, (255, 214, 90))
    # balcao
    F(c, (14, 18, 30), 127, 8, 80, 18)                                                    # placa do neon (apagada)
    front = ramp((200, 50, 70))
    box(c, (10, 96, 347, 22), front)
    for x in range(14, 354, 17):
        box(c, (x, 100, 14, 14), ramp((180, 40, 62)), outline=None)
        F(c, (130, 24, 44), x + 14, 100, 1, 14)
    F(c, (220, 226, 236), 10, 106, 347, 1)
    box(c, (8, 92, 351, 4), ramp((214, 222, 236)))
    # cafeteira
    box(c, (326, 70, 33, 22), ramp((170, 180, 200)))
    F(c, (40, 50, 70), 330, 75, 25, 10)
    F(c, (90, 100, 120), 331, 76, 8, 1)
    F(c, (255, 80, 80), 354, 87, 2, 2)
    box(c, (336, 86, 6, 5), ramp((240, 240, 240)))
    for x, col in ((160, (255, 150, 190)), (180, (150, 220, 255))):                       # milkshakes
        pygame.draw.polygon(c, INK, [(x - 5, 79), (x + 5, 79), (x + 3, 92), (x - 3, 92)])
        pygame.draw.polygon(c, (226, 234, 244), [(x - 4, 80), (x + 4, 80), (x + 2, 91), (x - 2, 91)])
        pygame.draw.polygon(c, col, [(x - 3, 83), (x + 3, 83), (x + 2, 90), (x - 2, 90)])
        pygame.draw.circle(c, (250, 250, 255), (x, 79), 3)
        F(c, (255, 60, 60), x + 1, 74, 1, 4)
        F(c, (255, 60, 60), x + 2, 72, 1, 2)
    # luminarias pendentes
    for x in (150, 250):
        F(c, (90, 100, 120), x, 0, 1, 56)
        pygame.draw.polygon(c, INK, [(x - 9, 64), (x + 9, 64), (x + 4, 56), (x - 4, 56)])
        pygame.draw.polygon(c, (255, 120, 180), [(x - 8, 63), (x + 8, 63), (x + 3, 57), (x - 3, 57)])
        F(c, (255, 240, 220), x - 5, 64, 11, 1)
        glow(c, (x, 64), 12, (70, 40, 54), 3)
        beam(c, (x, 64), (x, 120), 7, 34, (40, 28, 36), 3, 0.15)
    # piso xadrez
    checker_floor(c, 118, LH, (210, 214, 224), (40, 44, 60), cols=12, rows=6)
    tint(c, (0, 118, LW, 42), (150, 150, 180))
    F(c, (10, 12, 20), 0, 118, LW, 1)
    for x in (110, 257):                                                                  # banquetas
        F(c, (180, 190, 210), x, 112, 2, 16)
        pygame.draw.ellipse(c, INK, (x - 8, 107, 18, 7))
        pygame.draw.ellipse(c, (220, 60, 90), (x - 7, 108, 16, 5))
        F(c, (255, 130, 160), x - 4, 108, 8, 1)
        pygame.draw.ellipse(c, (130, 140, 160), (x - 6, 127, 14, 3))
    vignette(c, 0.5)


def anim_lanchonete(scr, t):
    off = (t % 7.0) < 0.12 or 0.2 < (t % 7.0) < 0.26
    sp = neon_text_sprite("LANCHES", (255, 90, 170), not off)
    scr.blit(sp, (125 * S, 7 * S), special_flags=pygame.BLEND_RGB_ADD)
    for i in range(3):                                                                    # vapor da cafeteira
        for j in range(5):
            Q(scr, (150, 166, 196) if j < 3 else (110, 124, 150),
              335 + i * 4 + round(1.5 * math.sin(t * 3 + j * 0.8 + i)), 68 - j * 3 - int((t * 5) % 3))
    x = int((t * 46) % 175) - 34                                                          # carro passando
    for dx in (0, 9):
        if 13 <= x + dx < 117:
            Q(scr, (255, 240, 180), x + dx, 79, 2, 1)
    if 13 <= x - 14 < 117:
        Q(scr, (255, 60, 60), x - 14, 79)


def fg_lanchonete(c):
    box(c, (330, 140, 37, 20), ramp((200, 60, 80)))                                        # mesa e condimentos
    box(c, (328, 137, 39, 3), ramp((220, 230, 240)))
    box(c, (336, 120, 6, 17), ramp((220, 40, 40)))
    F(c, (255, 255, 255), 337, 118, 3, 2)
    box(c, (346, 122, 6, 15), ramp((240, 200, 40)))
    F(c, (255, 255, 255), 347, 120, 3, 2)
    box(c, (356, 128, 9, 9), ramp((200, 210, 230)))


DRAW = {"ginasio": bg_ginasio, "quadra": bg_quadra, "garagem": bg_garagem, "oficina": bg_oficina,
        "escola": bg_escola, "cantina": bg_cantina, "camarim": bg_camarim, "arena": bg_arena,
        "mundial": bg_mundial, "estadio": bg_estadio, "coliseu": bg_coliseu, "cabine": bg_cabine,
        "federacao": bg_federacao, "praca": bg_praca, "laboratorio": bg_laboratorio,
        "aeroporto": bg_aeroporto, "dojo": bg_dojo, "fabrica": bg_fabrica, "lanchonete": bg_lanchonete}
ANIM = {"ginasio": anim_ginasio, "quadra": anim_quadra, "garagem": anim_garagem, "oficina": anim_oficina,
        "escola": anim_escola, "cantina": anim_cantina, "camarim": anim_camarim, "arena": anim_arena,
        "mundial": anim_mundial, "estadio": anim_estadio, "coliseu": anim_coliseu, "cabine": anim_cabine,
        "federacao": anim_federacao, "praca": anim_praca, "laboratorio": anim_laboratorio,
        "aeroporto": anim_aeroporto, "dojo": anim_dojo, "fabrica": anim_fabrica, "lanchonete": anim_lanchonete}
FRONT = {"quadra": fg_quadra, "garagem": fg_garagem, "oficina": fg_oficina, "escola": fg_escola,
         "cantina": fg_cantina, "cabine": fg_cabine, "federacao": fg_federacao, "praca": fg_praca,
         "laboratorio": fg_laboratorio, "aeroporto": fg_aeroporto, "dojo": fg_dojo, "fabrica": fg_fabrica,
         "lanchonete": fg_lanchonete}
