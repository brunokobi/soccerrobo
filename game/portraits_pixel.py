# -*- coding: utf-8 -*-
"""Personagens da Campanha em PIXEL ART (estilo padrao; portraits.STYLE = "pixel").

Tecnica
- Cada personagem e pintado em resolucao LOGICA baixa (CW x CH px, ~1/3 do palco) num "mapa de
  materiais": cada pixel guarda (material, tom) com 4 tons por material (luz, base, sombra, sombra
  profunda; rampa com desvio de matiz: luz puxa para o quente, sombra para o roxo). Um passe de
  "bevel" automatico acende as bordas de cima/esquerda e sombreia as de baixo/direita; detalhes
  (mechas, dobras, costuras, ziper, botoes, trico) sao pintados a mao por cima.
- Duas camadas: PERNAS (estatica) e CORPO (tronco, bracos, cabeca, rosto). O corpo e montado por
  quadro de animacao (piscar x boca) e humor; o contorno escuro de 1 px logico sai de uma mascara.
- Ordem de pintura do corpo: cabelo de tras -> roupa -> cabeca/pescoco -> gola/cachecol -> cabelo
  da frente -> acessorios de cabeca. Rosto (sobrancelhas, olhos, boca, lagrimas) e oculos sao
  pintados por quadro em cima da base.
- Cache: bases k=1 por (personagem, camada) (o mapa de materiais e descartado depois de pintado) e
  quadros prontos por (personagem, humor, k) com os 4 quadros (LRU de PX_CACHE_MAX grupos; ~23 KB
  por quadro). O esmaecido (k < 1) sai da versao k=1 com 2 fills (MULT + ADD), igual a P.shade.
  Nada de Surface por quadro: a ampliacao (vizinho mais proximo) e feita com
  pygame.transform.scale(..., dest) numa Surface de rascunho por tamanho, criada no aquecimento.
- Robos (Ze Poeira, Ze Perfeito, X-Omega) tem versao pixel propria (disco com LED), no mesmo cache.
- So pygame.draw/fill/set_at; nenhuma imagem externa; nenhum RNG (texturas por hash da posicao).
"""
import math
import time
from collections import OrderedDict

import pygame

import portraits as P
import story

CW, CH = 56, 102                       # tela logica
OY = 4                                 # linha 0 do corpo = linha OY da tela logica
ORIGIN_X = 28.0                        # x logico que cai em cx
LEG_CUT = (70, 4)                      # pernas: corta 4 linhas na coxa (proporcao ~3,5 cabecas)
FEET_Y = 100.0 - LEG_CUT[1]            # y logico (tela) que cai em feet_y
HEAD_C = (28.0, 24.0)                  # centro da cabeca (tela logica) - ancora do busto
BUST_LIFT = -0.12                      # desloca a cabeca no busto (negativo = desce; mostra cabelo)
BUST_MARGIN = 5                        # px livres entre o topo do cabelo e a borda do busto
PX_CACHE_MAX = 48                      # grupos (personagem, humor, k) com 4 quadros cada
LEGS_CACHE_MAX = 24                    # pernas esmaecidas (personagem, k)
SCRATCH_MAX = 6                        # Surfaces de rascunho (uma por tamanho ampliado; no jogo sao 3)

OUT = (26, 18, 30)                     # contorno
EYE = (34, 24, 30)
SCLERA = (244, 242, 236)
LIP = (150, 70, 72)
LIP_F = (184, 72, 96)                  # labio feminino (batom leve)
LIP_F2 = (226, 128, 140)               # labio inferior feminino (luz)
MOUTH_IN = (84, 26, 40)
TEETH = (246, 244, 240)
TONGUE = (222, 104, 116)
BLUSH = (238, 120, 120)
TEAR = (120, 200, 255)
SWEAT = (110, 190, 255)

HI, BASE, SH, DP = 0, 1, 2, 3


def _sat(c, f):
    m = (c[0] + c[1] + c[2]) / 3.0
    return tuple(max(0, min(255, int(m + (v - m) * f))) for v in c)


def _ramp(c, kind="std"):
    c = tuple(c)
    if kind == "std" and max(c) - min(c) < 90:            # tons apagados ganham um pouco de cor
        c = _sat(c, 1.35)
    if kind == "skin":
        return (P.lerp(c, (255, 236, 205), 0.38), c, P.lerp(c, (160, 72, 74), 0.30), P.lerp(c, (104, 46, 60), 0.52))
    if kind == "white":
        return (P.lerp(c, (255, 255, 255), 0.6), c, P.lerp(c, (120, 128, 176), 0.32), P.lerp(c, (70, 74, 120), 0.55))
    return (P.lerp(c, (255, 238, 200), 0.32), c, P.lerp(c, (44, 26, 70), 0.34), P.lerp(c, (24, 14, 40), 0.6))


def _mk(v):
    """Rampa a partir de: 4 tons explicitos | (rgb, tipo) | rgb (tipo automatico)."""
    if len(v) == 4 and isinstance(v[0], tuple):
        return tuple(v)
    if len(v) == 2 and isinstance(v[0], tuple):
        return _ramp(v[0], v[1])
    return _ramp(v, "white" if min(v) > 200 else "std")


# ================================================================================ MAPA DE MATERIAIS
class _Map:
    """Grade CW x CH de (material, tom); coordenadas em espaco do CORPO (y + OY na tela logica)."""

    def __init__(self):
        self.m = [[None] * CW for _ in range(CH)]
        self.t = [[BASE] * CW for _ in range(CH)]
        self.abs = {}                                   # (x, y) -> cor absoluta (antes do k)

    def ok(self, x, y):
        return 0 <= x < CW and 0 <= y + OY < CH

    def put(self, x, y, mat, tone=BASE):
        if self.ok(x, y):
            self.m[y + OY][x] = mat
            self.t[y + OY][x] = tone
            self.abs.pop((x, y + OY), None)

    def tone(self, x, y, tone, only=None):
        if self.ok(x, y) and self.m[y + OY][x] is not None and (only is None or self.m[y + OY][x] in only):
            self.t[y + OY][x] = tone

    def mat(self, x, y):
        return self.m[y + OY][x] if self.ok(x, y) else None

    def color(self, x, y, col):
        if self.ok(x, y):
            if self.m[y + OY][x] is None:
                self.m[y + OY][x] = "_abs"
            self.abs[(x, y + OY)] = col

    def hline(self, x0, x1, y, mat, tone=BASE):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.put(x, y, mat, tone)

    def vline(self, x, y0, y1, mat, tone=BASE):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.put(x, y, mat, tone)

    def rect(self, x, y, w, h, mat, tone=BASE):
        for yy in range(y, y + h):
            self.hline(x, x + w - 1, yy, mat, tone)

    def rows(self, spans, mat, tone=BASE):
        for y, (x0, x1) in spans.items():
            self.hline(x0, x1, y, mat, tone)

    def mirror(self, spans, mat, tone=BASE):
        """Spans do lado esquerdo e o espelho (x -> 55 - x)."""
        for y, (x0, x1) in spans.items():
            self.hline(x0, x1, y, mat, tone)
            self.hline(55 - x1, 55 - x0, y, mat, tone)

    def poly(self, pts, mat, tone=BASE):
        """Poligono preenchido (scanline, regra par-impar, amostra no centro do pixel)."""
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(int(math.floor(min(ys))), int(math.ceil(max(ys))) + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                for x in range(int(math.ceil(a - 0.5)), int(math.floor(b - 0.5)) + 1):
                    self.put(x, y, mat, tone)

    def disc(self, cx, cy, r, mat, tone=BASE, ry=None):
        ry = ry or r
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if ((x + 0.5 - cx) / r) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0:
                    self.put(x, y, mat, tone)

    def line(self, a, b, mat, tone=BASE):
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 1
        for i in range(n + 1):
            t = i / float(n)
            self.put(int(round(a[0] + (b[0] - a[0]) * t)), int(round(a[1] + (b[1] - a[1]) * t)), mat, tone)

    def cut_rows(self, y0, n):
        """Remove n linhas a partir de y0 (espaco do corpo) e sobe o que esta abaixo."""
        a = y0 + OY
        del self.m[a:a + n]
        del self.t[a:a + n]
        self.m.extend([[None] * CW for _ in range(n)])
        self.t.extend([[BASE] * CW for _ in range(n)])
        self.abs = {(x, y - n if y >= a + n else y): c for (x, y), c in self.abs.items() if not a <= y < a + n}

    def bevel(self, mats, lit=True, shade=True, deep=False):
        """Acende bordas de cima/esquerda e sombreia as de baixo/direita (so pixels em tom BASE)."""
        mats = set(mats)
        ch = []
        for y in range(CH):
            row = self.m[y]
            for x in range(CW):
                mm = row[x]
                if mm not in mats or self.t[y][x] != BASE:
                    continue

                def same(dx, dy):
                    xx, yy = x + dx, y + dy
                    return 0 <= xx < CW and 0 <= yy < CH and self.m[yy][xx] == mm
                if shade and (not same(1, 0)):
                    ch.append((x, y, DP if deep else SH))
                elif shade and not same(0, 1):
                    ch.append((x, y, SH))
                elif lit and (not same(-1, 0) or not same(0, -1)):
                    ch.append((x, y, HI))
        for x, y, tn in ch:
            self.t[y][x] = tn

    def render(self, pal, k, surf):
        """Pinta a grade em `surf` (SRCALPHA, ja limpa) com a paleta escurecida por k."""
        cache = {}
        for y in range(CH):
            row, trow = self.m[y], self.t[y]
            for x in range(CW):
                mm = row[x]
                if mm is None:
                    continue
                if mm == "_abs":
                    surf.set_at((x, y), P.shade(self.abs[(x, y)], k))
                    continue
                key = (mm, trow[x])
                c = cache.get(key)
                if c is None:
                    c = cache[key] = P.shade(pal[mm][trow[x]], k)
                surf.set_at((x, y), c)


# ================================================================================ CORPO (comum)
HEAD = {8: (21, 34), 9: (19, 36), 10: (18, 37)}
HEAD.update({y: (18, 37) for y in range(11, 26)})
HEAD.update({26: (19, 36), 27: (19, 36), 28: (20, 35), 29: (21, 34), 30: (22, 33), 31: (24, 31)})
HEAD_F = dict(HEAD)                                                # queixo mais fino
HEAD_F.update({27: (19, 36), 28: (20, 35), 29: (22, 33), 30: (23, 32), 31: (25, 30)})


def _head(mp, fem=False):
    mp.rows(HEAD_F if fem else HEAD, "skin")
    for sx, (x0, x1) in ((-1, (16, 17)), (1, (38, 39))):           # orelhas
        for y in range(17, 23):
            if y in (17, 22):
                mp.put(x1 if sx < 0 else x0, y, "skin")
            else:
                mp.hline(x0, x1, y, "skin")
        ix = 17 if sx < 0 else 38
        mp.put(ix, 19, "skin", SH)
        mp.put(ix, 20, "skin", DP if sx > 0 else SH)
    mp.bevel(("skin",), lit=False)
    # luz/sombra do rosto (luz de cima-esquerda)
    for y in range(11, 28):
        mp.tone(36, y, SH, ("skin",))
        if 13 <= y <= 26:
            mp.tone(35, y, SH, ("skin",))
    for y in range(12, 24):
        mp.tone(19, y, HI, ("skin",))
    mp.hline(20, 26, 10, "skin", HI)
    mp.hline(21, 24, 11, "skin", HI)
    for x in range(21, 35):                                        # mandibula
        mp.tone(x, 29, SH, ("skin",))
    for x in range(23, 33):
        mp.tone(x, 30, SH, ("skin",))
    for x in range(24, 32):
        mp.tone(x, 31, DP, ("skin",))
    mp.tone(34, 28, DP, ("skin",))
    mp.tone(35, 27, DP, ("skin",))
    mp.tone(36, 26, DP, ("skin",))
    mp.put(22, 24, "skin", HI)                                     # bochecha
    mp.put(23, 24, "skin", HI)
    # nariz
    mp.put(28, 20, "skin", SH)
    mp.put(28, 21, "skin", SH)
    mp.put(29, 22, "skin", SH)
    mp.put(27, 22, "skin", HI)
    mp.hline(27, 29, 23, "skin", DP)
    mp.put(26, 23, "skin", SH)
    # pescoco
    if fem:
        mp.rect(25, 30, 6, 5, "skin")
        mp.hline(25, 30, 31, "skin", DP)
        mp.hline(25, 30, 32, "skin", SH)
        for y in range(30, 35):
            mp.put(30, y, "skin", DP)
            mp.put(29, y, "skin", SH)
    else:
        mp.rect(24, 30, 8, 5, "skin")
        mp.hline(24, 31, 31, "skin", DP)
        mp.hline(24, 31, 32, "skin", SH)
        for y in range(30, 35):
            mp.put(31, y, "skin", DP)
            mp.put(30, y, "skin", SH)


def _wrinkles(mp, forehead=True):
    """Rugas de idade: pes de galinha, bigode chines (sulco nasolabial) e testa."""
    for x, y in ((19, 19), (19, 21), (36, 19), (36, 21), (25, 24), (24, 25), (30, 24), (31, 25)):
        mp.tone(x, y, SH, ("skin",))
    if forehead:
        for x in range(23, 33):
            if x not in (27, 28):
                mp.tone(x, 12, SH, ("skin",))
        for x in range(24, 32):
            mp.tone(x, 14, SH, ("skin",))


def _arms(mp, mat="top", cuff_mat=None, cuff_rows=(55, 58), hands=True, hand="skin"):
    spans_l = {34: (11, 13), 35: (10, 13)}
    spans_l.update({y: (9, 13) for y in range(36, cuff_rows[1] + 1)})
    for y, (x0, x1) in spans_l.items():
        mp.hline(x0, x1, y, mat)
        mp.hline(55 - x1, 55 - x0, y, mat)
    for y in range(36, cuff_rows[1] + 1):                          # volume das mangas
        mp.put(10, y, mat, HI)
        mp.put(13, y, mat, SH)
        mp.put(42, y, mat, SH)
        mp.put(45, y, mat, SH)
        mp.put(46, y, mat, DP)
    mp.put(11, 34, mat, HI)
    mp.put(10, 35, mat, HI)
    for x, y in ((11, 45), (12, 46), (10, 47), (43, 45), (44, 46), (45, 47), (11, 48)):   # dobras do cotovelo
        mp.put(x, y, mat, SH)
    if cuff_mat:
        for y in range(cuff_rows[0], cuff_rows[1] + 1):
            mp.hline(9, 13, y, cuff_mat)
            mp.hline(42, 46, y, cuff_mat)
        mp.hline(9, 13, cuff_rows[1], cuff_mat, SH)
        mp.hline(42, 46, cuff_rows[1], cuff_mat, SH)
        mp.put(46, cuff_rows[0], cuff_mat, SH)
        mp.put(13, cuff_rows[0], cuff_mat, SH)
    if hands:
        _hands(mp, cuff_rows[1] + 1, hand)


def _arms_short(mp, mat="top", end=43, hand="skin", roll=False):
    """Mangas curtas (ou arregacadas, roll=True) + antebraco de pele + maos."""
    spans_l = {34: (11, 14), 35: (10, 14)}
    spans_l.update({y: (9, 14) for y in range(36, end + 1)})
    for y, (x0, x1) in spans_l.items():
        mp.hline(x0, x1, y, mat)
        mp.hline(55 - x1, 55 - x0, y, mat)
    for y in range(36, end - 1):
        mp.put(10, y, mat, HI)
        mp.put(14, y, mat, SH)
        mp.put(41, y, mat, DP)
        mp.put(45, y, mat, SH)
        mp.put(46, y, mat, DP)
    mp.put(11, 34, mat, HI)
    mp.put(10, 35, mat, HI)
    if roll:                                                       # barra dobrada (manga arregacada)
        mp.hline(9, 14, end - 2, mat, HI)
        mp.hline(41, 46, end - 2, mat, BASE)
        mp.hline(9, 14, end - 1, mat, BASE)
        mp.hline(41, 46, end - 1, mat, SH)
    else:
        mp.hline(9, 14, end - 1, mat, SH)
        mp.hline(41, 46, end - 1, mat, SH)
    mp.hline(9, 14, end, mat, DP)
    mp.hline(41, 46, end, mat, DP)
    for y in range(end + 1, 59):                                   # antebracos
        mp.hline(10, 13, y, "skin")
        mp.hline(42, 45, y, "skin")
        mp.put(10, y, "skin", HI)
        mp.put(13, y, "skin", SH)
        mp.put(45, y, "skin", SH)
        mp.put(42, y, "skin", BASE)
    mp.hline(10, 13, end + 1, "skin", SH)                          # sombra da manga no braco
    mp.hline(42, 45, end + 1, "skin", DP)
    mp.put(11, end + 5, "skin", SH)                                # cotovelo
    mp.put(43, end + 5, "skin", SH)
    _hands(mp, 59, hand)


def _hands(mp, y0, mat="skin"):
    for sx in (-1, 1):
        xs = range(9, 14) if sx < 0 else range(42, 47)
        x0, x1 = xs[0], xs[-1]
        mp.hline(x0, x1, y0, mat, SH)
        for y in range(y0 + 1, y0 + 5):
            mp.hline(x0, x1, y, mat)
        mp.hline(x0 + 1, x1 - 1, y0 + 5, mat)
        # polegar para dentro, dedos marcados
        tx = x1 + 1 if sx < 0 else x0 - 1
        mp.put(tx, y0 + 1, mat, BASE)
        mp.put(tx, y0 + 2, mat, SH)
        for y in range(y0 + 1, y0 + 5):
            mp.put(x0, y, mat, HI if sx < 0 else SH)
            mp.put(x1, y, mat, SH if sx < 0 else DP)
        mp.put(x0 + 2, y0 + 4, mat, SH)
        mp.put(x0 + 2, y0 + 5, mat, SH)
        mp.put(x0 + 1, y0 + 2, mat, HI)
        if mat == "glove":                                         # costuras da luva
            mp.put(x0 + 1, y0 + 3, mat, SH)
            mp.put(x0 + 3, y0 + 3, mat, SH)
            mp.hline(x0, x1, y0, mat, DP)


def _legs(mp, pants="pants", shoe="shoe", sole="sole", style="jeans", stripe=None):
    """Pernas: style jeans | suit (vinco) | gi (calca larga, pe descalco) | slipper (chinelo) | boots."""
    hem = 88 if style in ("gi", "slipper") else 90
    gap = (27, 28)
    xl, xr = (15, 27) if style == "gi" else (16, 26), (28, 40) if style == "gi" else (29, 39)
    mp.rect(xl[0], 60, xr[1] - xl[0] + 1, 4, pants)
    for y in range(64, hem + 1):
        mp.hline(xl[0], xl[1], y, pants)
        mp.hline(xr[0], xr[1], y, pants)
    if style != "gi":
        mp.hline(27, 28, 64, pants, SH)
    for y in range(60, hem + 1):                                   # volume
        mp.put(xl[0], y, pants, HI)
        mp.put(xl[0] + 1, y, pants, HI if y % 7 else BASE)
        mp.put(xl[1], y, pants, SH)
        mp.put(xr[0], y, pants, SH)
        mp.put(xr[1] - 1, y, pants, SH)
        mp.put(xr[1], y, pants, DP)
    for y in range(60, 64):
        mp.put(gap[0], y, pants, SH)
        mp.put(gap[1], y, pants, SH)
    if style == "suit":                                            # vinco da calca social
        for y in range(66, 89):
            mp.put(21, y, pants, HI)
            mp.put(34, y, pants, HI)
    elif style == "gi":                                            # calca de kimono: pregas largas
        for x, y in ((20, 66), (21, 67), (21, 68), (34, 66), (34, 67), (35, 68), (19, 80), (20, 81),
                     (33, 80), (34, 81), (22, 75), (36, 75), (27, 66), (28, 66)):
            mp.put(x, y, pants, SH)
        mp.hline(xl[0], xl[1], hem - 1, pants, SH)
        mp.hline(xr[0], xr[1], hem - 1, pants, SH)
        for y in range(65, hem + 1):
            mp.put(27, y, pants, DP)
            mp.put(26, y, pants, SH)
    else:                                                          # costura + dobras (jeans)
        for x, y in ((19, 74), (20, 75), (22, 74), (33, 76), (34, 77), (36, 76), (20, 86), (21, 87), (35, 86), (34, 87)):
            mp.put(x, y, pants, SH)
        mp.hline(xl[0], xl[1], hem - 1, pants, SH)
        mp.hline(xr[0], xr[1], hem - 1, pants, SH)
    mp.hline(xl[0], xl[1], hem, pants, DP)
    mp.hline(xr[0], xr[1], hem, pants, DP)
    if stripe:                                                     # listra lateral (farda / agasalho)
        for y in range(62, hem):
            mp.put(xl[0] + 1, y, stripe, BASE if y % 9 else HI)
            mp.put(xr[1] - 1, y, stripe, SH)
    if style == "gi":
        _bare_feet(mp, hem)
        return
    if style == "slipper":
        _slippers(mp, hem, sole)
        return
    if style == "boots":                                           # cano da bota sobre a calca
        for sx in (-1, 1):
            a, b = (16, 26) if sx < 0 else (29, 39)
            for y in range(84, 91):
                mp.hline(a, b, y, shoe)
                mp.put(a, y, shoe, HI)
                mp.put(b, y, shoe, SH if sx < 0 else DP)
            mp.hline(a, b, 84, shoe, HI)
            mp.hline(a, b, 85, shoe, SH)
            for y in (87, 89):                                     # cadarcos
                mp.put((a + b) // 2, y, shoe, HI)
                mp.put((a + b) // 2 + 1, y, shoe, SH)
    # sapatos (biqueira para fora)
    for sx in (-1, 1):
        if sx < 0:
            spans = {91: (17, 26), 92: (15, 26), 93: (14, 26), 94: (14, 26)}
        else:
            spans = {91: (29, 38), 92: (29, 40), 93: (29, 41), 94: (29, 41)}
        mp.rows(spans, shoe)
        x0, x1 = spans[94]
        mp.hline(x0, x1, 95, sole)
        mp.hline(x0 + 1, x1 - 1, 95, sole, SH)
        if sx < 0:
            mp.hline(15, 18, 92, shoe, HI)
            mp.put(14, 93, shoe, HI)
            mp.hline(23, 26, 93, shoe, SH)
            mp.hline(20, 26, 94, shoe, SH)
            mp.put(16, 92, shoe, HI)
        else:
            mp.hline(37, 40, 92, shoe, HI)
            mp.put(29, 93, shoe, SH)
            mp.hline(29, 35, 94, shoe, SH)
            mp.put(41, 94, shoe, SH)
        mp.put(x1, 93, shoe, DP)
        if style == "sneaker":                                     # tenis: faixa lateral na cor do sole
            for x in range(x0 + 2, x1 - 1):
                if (x + 93) % 3 == 0:
                    mp.put(x, 93, sole, BASE)


def _bare_feet(mp, hem):
    for sx in (-1, 1):
        if sx < 0:
            sp = {hem + 1: (19, 24), hem + 2: (19, 24), hem + 3: (18, 24), hem + 4: (16, 24), hem + 5: (15, 24),
                  hem + 6: (15, 24)}
        else:
            sp = {hem + 1: (31, 36), hem + 2: (31, 36), hem + 3: (31, 37), hem + 4: (31, 39), hem + 5: (31, 40),
                  hem + 6: (31, 40)}
        mp.rows(sp, "skin")
        x0, x1 = sp[hem + 6]
        mp.hline(x0, x1, hem + 7, "skin", DP)
        mp.hline(sp[hem + 1][0], sp[hem + 1][1], hem + 1, "skin", DP)       # sombra da barra da calca
        for x in range(x0 + 1, x1, 2) if sx < 0 else range(x1 - 1, x0, -2):  # dedos
            mp.put(x, hem + 6, "skin", SH)
        mp.put(x0 if sx < 0 else x1, hem + 5, "skin", HI if sx < 0 else SH)
        for y in range(hem + 2, hem + 7):
            mp.put(sp[y][1] if sx < 0 else sp[y][1], y, "skin", SH)


def _slippers(mp, hem, sole):
    for sx in (-1, 1):
        if sx < 0:
            ank, foot, sl = (19, 24), (16, 25), (14, 26)
        else:
            ank, foot, sl = (31, 36), (30, 39), (29, 41)
        for y in range(hem + 1, hem + 4):
            mp.hline(ank[0], ank[1], y, "skin")
            mp.put(ank[1], y, "skin", SH)
            mp.put(ank[0], y, "skin", HI)
        mp.hline(ank[0], ank[1], hem + 1, "skin", DP)
        for y in range(hem + 4, hem + 6):
            mp.hline(foot[0], foot[1], y, "skin")
        mp.hline(foot[0], foot[1], hem + 5, "skin", SH)
        mp.hline(sl[0], sl[1], hem + 6, sole, HI)
        mp.hline(sl[0], sl[1], hem + 7, sole, SH)
        mp.put(sl[1] if sx > 0 else sl[0], hem + 7, sole, DP)
        cxs = (foot[0] + foot[1]) // 2 + (-2 if sx < 0 else 2)      # tira em Y
        mp.put(cxs, hem + 5, "strap", BASE)
        mp.put(cxs, hem + 4, "strap", BASE)
        mp.put(cxs - 1, hem + 3, "strap", SH)
        mp.put(cxs + 1, hem + 3, "strap", SH)
        mp.put(cxs - 2, hem + 3, "strap", SH)
        mp.put(cxs + 2, hem + 3, "strap", SH)


# ================================================================================ CABELOS
def _spike(mp, b0, b1, tip, mat="hair"):
    """Mecha pontuda: metade de cima/esquerda em tom base, a outra em sombra; ponta acesa."""
    mp.poly([b0, tip, b1], mat)
    mx, my = (b0[0] + b1[0]) / 2.0, (b0[1] + b1[1]) / 2.0
    xs = [b0[0], b1[0], tip[0]]
    ys = [b0[1], b1[1], tip[1]]
    for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
        for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
            if mp.mat(x, y) != mat:
                continue
            # lado da linha ponta -> meio da base
            cr = (mx - tip[0]) * (y + 0.5 - tip[1]) - (my - tip[1]) * (x + 0.5 - tip[0])
            if cr > 0.6 and _in_tri(x + 0.5, y + 0.5, b0, b1, tip):
                mp.tone(x, y, SH)


def _in_tri(x, y, a, b, c):
    def s(p, q, r):
        return (p[0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[1] - r[1])
    d1, d2, d3 = s((x, y), a, b), s((x, y), b, c), s((x, y), c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def _fringe_shadow(mp, y0=12, y1=18, mats=("hair",)):
    """Sombra que a franja/aba projeta na testa."""
    for x in range(18, 38):
        for y in range(y0, y1):
            if mp.mat(x, y) == "skin" and mp.mat(x, y - 1) in mats:
                mp.tone(x, y, SH, ("skin",))


TEO_SPIKES = (((15.5, 15), (19, 9), (9.5, 8.5)), ((17.5, 10), (23, 6.5), (14, -0.5)),
              ((21.5, 7), (28.5, 5.5), (23.5, -4.5)), ((27, 5.5), (34, 7), (33.5, -3.5)),
              ((32, 6.5), (38.5, 10), (42, -0.5)), ((37, 9), (40.5, 15.5), (46, 7.5)))


def _hair_espetado(mp, spikes=TEO_SPIKES):
    dome = [(17, 21), (16, 12), (19, 7), (24, 5), (32, 5), (37, 7), (40, 12), (39, 21), (37.4, 21),
            (37.2, 15), (35, 14), (33.5, 16.5), (31, 13), (29, 16), (26.5, 13), (24.5, 16.5), (22.5, 13.5),
            (20.5, 16.5), (18.8, 15), (18.6, 21)]
    mp.poly(dome, "hair")
    for b0, b1, tip in spikes:
        _spike(mp, b0, b1, tip)
    mp.bevel(("hair",), deep=True)
    # sombra profunda na raiz das mechas e na franja; brilho em faixa na copa
    for x, y in ((19, 10), (20, 9), (24, 7), (25, 7), (30, 7), (31, 7), (35, 9), (36, 10), (18, 12), (38, 13)):
        mp.tone(x, y, SH, ("hair",))
    for x, y in ((21, 9), (22, 8), (23, 8), (26, 6), (27, 6), (28, 7), (32, 8), (33, 8), (29, 9), (34, 9)):
        mp.tone(x, y, HI, ("hair",))
    _fringe_shadow(mp, 13, 18)
    for y in range(16, 22):                                        # costeletas
        mp.tone(18, y, DP, ("hair",))
        mp.tone(37, y, DP, ("hair",))


KENJI_SPIKES = (((16, 14), (20, 8), (10.5, 5)), ((18.5, 9), (24, 6), (16.5, -1.5)),
                ((22.5, 6.5), (29, 5.5), (25.5, -3.5)), ((27.5, 5.5), (33.5, 6.5), (33, -3)),
                ((32, 6), (38, 9.5), (40.5, -1)), ((36.5, 8.5), (40, 14), (45.5, 5)))


def _hair_kenji(mp):
    """Espetado preto em labaredas + mechas caindo sobre a faixa."""
    _hair_espetado(mp, KENJI_SPIKES)
    for b0, b1, tip in (((22, 12), (25.5, 12), (23, 17.5)), ((30, 12), (33.5, 12), (33, 16.5))):
        _spike(mp, b0, b1, tip)                                    # mechas sobre a testa
    mp.bevel(("hair",), lit=False, deep=True)
    _fringe_shadow(mp, 14, 19)


def _hair_calvo(mp, bushy=False):
    # tampo careca com brilho e laterais grisalhas fofas sobre as orelhas
    mp.hline(22, 25, 9, "skin", HI)
    mp.hline(21, 23, 10, "skin", HI)
    mp.color(23, 9, (255, 250, 236))
    mp.color(24, 9, (255, 250, 236))
    for sx in (-1, 1):
        spans = {12: (17, 18), 13: (16, 19), 14: (15, 19), 15: (15, 19), 16: (15, 18), 17: (15, 17),
                 18: (15, 16), 19: (15, 16), 20: (15, 16), 21: (16, 16)}
        if bushy:                                                  # tufos mais cheios e espetados
            spans.update({11: (17, 18), 12: (15, 19), 13: (14, 19), 14: (14, 19), 15: (14, 19), 16: (14, 18),
                          17: (14, 17), 18: (15, 16), 19: (15, 16), 20: (15, 16), 21: (15, 16), 22: (16, 16)})
        for y, (a, b) in spans.items():
            if sx > 0:
                a, b = 55 - b, 55 - a
            mp.hline(a, b, y, "hair")
    if bushy:
        for x, y in ((13, 13), (13, 15), (42, 13), (42, 15), (16, 10), (39, 10)):
            mp.put(x, y, "hair")
    mp.bevel(("hair",))
    for x, y in ((16, 14), (17, 16), (16, 18), (38, 14), (39, 16), (39, 18), (18, 13), (37, 13)):
        mp.tone(x, y, SH, ("hair",))
    for x, y in ((17, 13), (16, 15), (38, 13), (37, 14)):
        mp.tone(x, y, HI, ("hair",))
    # rugas na testa
    for x in range(24, 32):
        if x not in (27, 28):
            mp.tone(x, 12, SH, ("skin",))
    for x in range(25, 31):
        mp.tone(x, 14, SH, ("skin",))


def _hair_raspado(mp):
    """Corte social curto (risca do lado, topete baixo) - o "raspado" do estilo classico."""
    spans = {5: (22, 32), 6: (19, 35), 7: (18, 37), 8: (17, 38), 9: (17, 38), 10: (17, 38), 11: (17, 38),
             12: (17, 23), 13: (17, 20), 14: (17, 19), 15: (17, 18), 16: (17, 18), 17: (17, 18)}
    mp.rows(spans, "hair")
    mp.rows({12: (31, 38), 13: (34, 38), 14: (35, 38), 15: (36, 38), 16: (37, 38), 17: (37, 38)}, "hair")
    mp.hline(24, 30, 12, "hair")                                    # franja varrida para o lado
    mp.hline(25, 28, 13, "hair")
    mp.bevel(("hair",), deep=True)
    mp.vline(22, 6, 9, "hair", DP)                                 # risca
    mp.put(23, 9, "hair", DP)
    for x, y in ((24, 6), (25, 6), (26, 6), (27, 7), (28, 7), (30, 7), (31, 8), (19, 8), (20, 7), (25, 8), (26, 9)):
        mp.tone(x, y, HI, ("hair",))                                # brilho / mechas penteadas
    for x, y in ((29, 9), (30, 10), (32, 10), (33, 9), (34, 10), (27, 10), (28, 11), (35, 9), (20, 11), (19, 10)):
        mp.tone(x, y, SH, ("hair",))
    _fringe_shadow(mp, 12, 15)


def _hair_militar(mp):
    """Corte militar (raspado alto): topo curto e chato, laterais quase na pele (barba por fazer)."""
    mp.rows({5: (22, 33), 6: (19, 36), 7: (18, 37), 8: (17, 38), 9: (17, 38), 10: (17, 38)}, "hair")
    mp.bevel(("hair",), deep=True)
    for y in range(6, 10):                                         # textura de cabelo raspado
        for x in range(18, 38):
            if mp.mat(x, y) == "hair" and mp.t[y + OY][x] == BASE and (x * 3 + y * 5) % 7 == 0:
                mp.tone(x, y, HI)
            elif mp.mat(x, y) == "hair" and mp.t[y + OY][x] == BASE and (x * 5 + y * 3) % 9 == 0:
                mp.tone(x, y, SH)
    mp.hline(22, 30, 6, "hair", HI)
    for y in range(11, 20):                                        # laterais (pele com fios)
        for x in (17, 18, 37, 38):
            if mp.mat(x, y) == "skin":
                if (x + y) % 2 == 0:
                    mp.put(x, y, "hair", SH)
                else:
                    mp.tone(x, y, SH, ("skin",))
    mp.hline(19, 36, 11, "skin", SH)                               # linha do cabelo (sombra)


def _hair_ogawa(mp):
    """Mestre: cabelo curto grisalho com entradas, laterais mais claras (tempora branca)."""
    mp.rows({5: (23, 32), 6: (21, 34), 7: (20, 35), 8: (22, 33), 9: (24, 31)}, "hair")
    sides = {8: (17, 20), 9: (17, 20), 10: (16, 19), 11: (16, 19), 12: (16, 18), 13: (16, 18), 14: (16, 18),
             15: (16, 18), 16: (16, 18), 17: (16, 17), 18: (16, 17), 19: (16, 17), 20: (16, 17)}
    mp.mirror(sides, "hair")
    mp.bevel(("hair",), deep=True)
    for y in range(10, 21):                                        # temporas brancas
        for x in (16, 17, 38, 39):
            mp.tone(x, y, HI, ("hair",))
    for x, y in ((24, 6), (25, 6), (26, 7), (29, 6), (30, 6), (31, 7), (22, 7)):
        mp.tone(x, y, HI, ("hair",))
    for x in range(25, 31, 2):                                     # pente para tras
        mp.tone(x, 8, SH, ("hair",))
    _wrinkles(mp)
    mp.tone(22, 10, SH, ("skin",))                                 # entradas
    mp.tone(33, 10, SH, ("skin",))


def _hair_curto_m(mp):
    """Curto penteado para tras (Dr. Augusto): sem franja, bico de viuva, laterais rentes."""
    sp = {3: (23, 32), 4: (20, 35), 5: (18, 37), 6: (17, 38), 7: (17, 38), 8: (17, 38), 9: (17, 38),
          10: (17, 25), 11: (17, 20), 12: (17, 19), 13: (17, 18), 14: (17, 18), 15: (17, 18), 16: (17, 18)}
    mp.rows(sp, "hair")
    mp.rows({10: (30, 38), 11: (35, 38), 12: (36, 38), 13: (37, 38), 14: (37, 38), 15: (37, 38), 16: (37, 38)}, "hair")
    mp.hline(26, 29, 10, "hair")                                    # bico de viuva
    mp.hline(27, 28, 11, "hair")
    mp.bevel(("hair",), deep=True)
    for i, (x0, y0) in enumerate(((20, 9), (23, 8), (27, 9), (31, 8), (34, 9))):   # fios penteados para tras
        for j in range(4):
            mp.tone(x0 + (j if x0 > 28 else -j) // 2, y0 - j, SH if i % 2 == 0 else HI, ("hair",))
    for x, y in ((22, 4), (23, 4), (24, 5), (25, 5), (26, 5), (30, 5), (31, 4), (21, 6)):
        mp.tone(x, y, HI, ("hair",))
    _fringe_shadow(mp, 10, 13)
    _wrinkles(mp, forehead=False)


def _hair_longo_back(mp):
    mp.poly([(15, 9), (40, 9), (42, 22), (42, 36), (13, 36), (13, 22)], "hair", SH)
    for x in range(14, 42, 3):
        for y in range(20, 36):
            mp.tone(x, y, DP, ("hair",))


def _hair_longo(mp):
    """Liso longo (Vivi): coroa com "anel" de brilho, franja varrida e mechas sobre os ombros."""
    crown = {3: (23, 32), 4: (20, 35), 5: (18, 37), 6: (17, 38), 7: (16, 39)}
    crown.update({y: (16, 39) for y in range(8, 13)})
    mp.rows(crown, "hair")
    fb = {18: 16, 19: 15, 20: 14, 21: 13, 22: 12, 23: 12, 24: 11, 25: 12, 26: 12, 27: 13, 28: 13, 29: 14, 30: 14,
          31: 14, 32: 15, 33: 15, 34: 16, 35: 16, 36: 17, 37: 18}
    for x, yb in fb.items():
        for y in range(12, yb + 1):
            mp.put(x, y, "hair")
    lock_l = {y: (14, 18) for y in range(12, 30)}
    lock_l.update({y: (14, 19) for y in range(30, 42)})
    lock_l.update({42: (14, 19), 43: (15, 19), 44: (15, 18), 45: (16, 18), 46: (16, 17), 47: (17, 17)})
    lock_r = {y: (37, 41) for y in range(12, 30)}
    lock_r.update({y: (36, 41) for y in range(30, 42)})
    lock_r.update({42: (36, 41), 43: (36, 40), 44: (37, 40), 45: (37, 39), 46: (38, 39), 47: (38, 38)})
    mp.rows(lock_l, "hair")
    mp.rows(lock_r, "hair")
    mp.bevel(("hair",), deep=True)
    for y in range(13, 45):                                        # fios
        if mp.mat(16, y) == "hair":
            mp.tone(16, y, SH)
        if mp.mat(39, y) == "hair":
            mp.tone(39, y, SH)
        if mp.mat(15, y) == "hair" and y < 40:
            mp.tone(15, y, HI)
        if mp.mat(38, y) == "hair" and 14 < y < 40:
            mp.tone(38, y, BASE)
    for y in range(13, 30):                                        # mecha junto do rosto (sombra)
        mp.tone(18, y, DP, ("hair",))
        mp.tone(37, y, DP, ("hair",))
    for x in range(18, 38):                                        # anel de brilho
        y = 7 if 21 <= x <= 34 else 8
        if (x % 4) != 1:
            mp.tone(x, y, HI, ("hair",))
    mp.vline(24, 4, 10, "hair", DP)                                # risca
    for x, y in ((25, 11), (26, 11), (21, 12), (30, 13), (33, 14), (34, 15)):
        mp.tone(x, y, SH, ("hair",))
    _fringe_shadow(mp, 12, 19)


def _hair_bob_back(mp):
    mp.poly([(16, 12), (39, 12), (40, 26), (38, 31), (17, 31), (15, 26)], "hair", DP)


def _hair_bob(mp):
    """Chanel (Dra. Helena): franja de lado e pontas viradas para dentro na altura do queixo."""
    crown = {3: (23, 32), 4: (20, 35), 5: (18, 37), 6: (17, 38), 7: (16, 39)}
    crown.update({y: (16, 39) for y in range(8, 12)})
    mp.rows(crown, "hair")
    fb = {18: 13, 19: 14, 20: 15, 21: 15, 22: 15, 23: 14, 24: 14, 25: 13, 26: 13, 27: 12, 28: 12, 29: 12,
          30: 11, 31: 11, 32: 11, 33: 12, 34: 12, 35: 13, 36: 13, 37: 14}
    for x, yb in fb.items():
        for y in range(11, yb + 1):
            mp.put(x, y, "hair")
    side = {y: (15, 18) for y in range(12, 26)}
    side.update({26: (15, 19), 27: (15, 20), 28: (16, 20), 29: (17, 19)})
    mp.mirror(side, "hair")
    mp.bevel(("hair",), deep=True)
    for y in range(13, 27):
        mp.tone(16, y, HI if y < 22 else BASE, ("hair",))
        mp.tone(18, y, SH, ("hair",))
        mp.tone(37, y, DP, ("hair",))
        mp.tone(39, y, SH, ("hair",))
    for x in range(19, 37):                                        # brilho
        if x % 3 != 0:
            mp.tone(x, 6 if 22 <= x <= 33 else 7, HI, ("hair",))
    mp.vline(31, 4, 10, "hair", DP)                                # risca do lado direito
    for x, y in ((21, 13), (22, 13), (24, 12), (26, 11), (28, 10)):
        mp.tone(x, y, SH, ("hair",))
    _fringe_shadow(mp, 11, 17)


def _hair_bia(mp):
    """Curto baguncado (Bia): tufos por cima e laterais curtas (bandana e oculos vao por cima)."""
    mp.rows({4: (22, 33), 5: (19, 36), 6: (18, 37), 7: (17, 38)}, "hair")
    mp.rows({y: (17, 38) for y in range(8, 12)}, "hair")
    mp.mirror({y: (16, 18) for y in range(12, 20)}, "hair")
    mp.mirror({20: (17, 18)}, "hair")
    for b0, b1, tip in (((18, 6), (22, 5), (16, 1.5)), ((22, 5), (27, 4), (23.5, 0)), ((27, 4), (32, 4.5), (31, 0.5)),
                        ((32, 5), (37, 6), (38.5, 2)), ((15.5, 12), (17, 8), (13.5, 9.5)), ((38.5, 12), (38, 8), (41.5, 10))):
        _spike(mp, b0, b1, tip)
    for x, yb in ((19, 14), (20, 15), (21, 14), (33, 14), (34, 15), (35, 14), (36, 13)):   # mechas sob a bandana
        for y in range(12, yb + 1):
            mp.put(x, y, "hair")
    mp.bevel(("hair",), deep=True)
    for x, y in ((21, 4), (22, 4), (26, 3), (27, 3), (30, 3), (20, 6), (33, 5)):
        mp.tone(x, y, HI, ("hair",))
    _fringe_shadow(mp, 14, 17)


def _hair_ondulado(mp):
    """Cacheado (Dudu): cachos sobrepostos de tras para frente, cada um com luz e sombra proprias."""
    curls = [(18, 9, 3.2), (22, 5.5, 3.2), (27.5, 4.2, 3.4), (33, 5.5, 3.2), (37.5, 9, 3.2),
             (15.5, 13.5, 2.8), (40, 13.5, 2.8), (15.6, 18, 2.4), (40, 18, 2.4),
             (21, 9.5, 3), (27.5, 8.5, 3), (34, 9.5, 3),
             (19.5, 13, 2.4), (23.8, 13.4, 2.4), (28.2, 13, 2.4), (32.4, 13.4, 2.4), (36.3, 12.8, 2.3)]
    for cx, cy, r in curls:
        mp.disc(cx, cy, r, "hair")
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                dx, dy = x + 0.5 - cx, y + 0.5 - cy
                dd = math.sqrt(dx * dx + dy * dy)
                if dd <= r and mp.mat(x, y) == "hair":
                    if dd > 0.62 * r and dx + dy > 0.35 * r:
                        mp.tone(x, y, SH if dd < 0.9 * r else DP)
                    elif dd < 0.7 * r and dx + dy < -0.45 * r:
                        mp.tone(x, y, HI)
                    else:
                        mp.tone(x, y, BASE)
    _fringe_shadow(mp, 13, 18)


def _hair_coque(mp, odete=False):
    """Coque no alto: cabelo puxado para tras (fios convergindo), coque redondo e elastico rosa."""
    cap = {4: (22, 33), 5: (19, 36), 6: (18, 37), 7: (17, 38), 8: (17, 38), 9: (17, 38), 10: (17, 38)}
    cap.update({11: (17, 20), 12: (17, 19), 13: (17, 18), 14: (17, 18), 15: (17, 18), 16: (17, 18)})
    mp.rows(cap, "hair")
    mp.rows({11: (35, 38), 12: (36, 38), 13: (37, 38), 14: (37, 38), 15: (37, 38), 16: (37, 38)}, "hair")
    mp.hline(21, 34, 11, "hair")
    mp.bevel(("hair",), deep=True)
    for x0 in (20, 23, 26, 29, 32, 35):                            # fios puxados para o coque
        for j in range(5):
            x = int(round(x0 + (27.5 - x0) * j / 6.0))
            mp.tone(x, 10 - j, SH, ("hair",))
    for x, y in ((21, 6), (22, 5), (24, 5), (25, 4), (30, 5), (19, 8)):
        mp.tone(x, y, HI, ("hair",))
    by = 1.0 if not odete else 1.5
    mp.disc(27.5, by, 4.3, "hair", ry=3.8)
    for y in range(int(by) - 4, int(by) + 5):
        for x in range(23, 33):
            if mp.mat(x, y) == "hair" and y < 4:
                dx, dy = x + 0.5 - 27.5, y + 0.5 - by
                if dx + dy > 3.2:
                    mp.tone(x, y, DP)
                elif dx + dy > 1.2:
                    mp.tone(x, y, SH)
                elif dx + dy < -3.5:
                    mp.tone(x, y, HI)
    for x, y in ((25, -1), (26, -2), (27, -2), (29, 0), (30, 1), (28, 2)):   # espiral do coque
        mp.tone(x, y, SH if y >= 0 else HI, ("hair",))
    mp.hline(24, 31, 4, "band")                                    # elastico
    mp.put(24, 4, "band", HI)
    mp.put(31, 4, "band", SH)
    mp.hline(25, 30, 5, "hair", DP)
    if odete:                                                      # fios soltos nas temporas
        for x, y in ((16, 13), (16, 14), (15, 15), (39, 13), (39, 14), (40, 15)):
            mp.put(x, y, "hair", SH)
    _fringe_shadow(mp, 11, 14)


def _cap_spikes(mp):
    """Cabelo espetado saindo por baixo do bone (Gabi): pontas nas laterais e na nuca."""
    mp.rows({y: (16, 39) for y in range(4, 12)}, "hair")
    for b0, b1, tip in (((17, 12), (18, 17), (10.5, 13)), ((17, 16), (18, 21), (11.5, 20.5)),
                        ((38, 8), (39, 13), (46, 8.5)), ((38, 12), (39, 17), (46.5, 15)),
                        ((38, 16), (38.5, 21), (44, 21.5)), ((17, 8), (18, 12), (12, 8))):
        _spike(mp, b0, b1, tip)
    mp.mirror({y: (17, 18) for y in range(12, 21)}, "hair")
    mp.bevel(("hair",), deep=True)


def _cap(mp):
    """Bone (Gabi): copa com gomos, logo branco com raio, botao e aba virada de lado."""
    crown = {1: (24, 31), 2: (21, 34), 3: (19, 36), 4: (18, 37), 5: (17, 38)}
    crown.update({y: (17, 38) for y in range(6, 12)})
    mp.rows(crown, "acc")
    mp.bevel(("acc",))
    mp.vline(22, 3, 10, "acc", SH)                                 # gomos
    mp.vline(33, 3, 10, "acc", SH)
    for y in range(2, 11):
        mp.tone(18, y, HI, ("acc",))
    mp.hline(26, 29, 0, "acc", HI)                                 # botao
    mp.disc(27.5, 6.2, 2.4, "acc2")                                # logo branco com raio
    mp.put(28, 5, "acc", BASE)
    mp.put(27, 6, "acc", BASE)
    mp.put(28, 6, "acc", BASE)
    mp.put(27, 7, "acc", BASE)
    mp.put(26, 5, "acc2", HI)
    mp.hline(17, 38, 11, "acc", DP)                                # barra da copa
    mp.hline(18, 37, 10, "acc", SH)
    mp.poly([(23, 8.5), (10, 8.5), (6.5, 10.5), (8, 12.6), (23, 12.6)], "acc")   # aba para a esquerda
    mp.hline(9, 20, 9, "acc", HI)
    mp.hline(7, 20, 10, "acc", BASE)
    mp.hline(7, 21, 11, "acc", SH)
    mp.hline(8, 22, 12, "acc", DP)
    mp.put(7, 10, "acc", HI)
    _spike(mp, (17.5, 11.5), (22, 11.5), (19, 16))                 # mechas por baixo da copa
    _spike(mp, (33.5, 11.5), (38, 11.5), (36.5, 15.5))
    _spike(mp, (25, 11.5), (28.5, 11.5), (25.5, 14))
    for x in range(19, 37):                                        # sombra da copa/aba na testa
        for y in (12, 13):
            if mp.mat(x, y) == "skin":
                mp.tone(x, y, SH if (y == 12 or x < 25) else BASE, ("skin",))


# ================================================================================ ACESSORIOS (base)
def _bandana(mp, y0=10, dots=True, tails=True):
    band = {y0: (17, 38), y0 + 1: (16, 39), y0 + 2: (16, 39), y0 + 3: (17, 38)}
    mp.rows(band, "acc")
    mp.hline(17, 38, y0, "acc", HI)
    mp.hline(17, 38, y0 + 3, "acc", SH)
    mp.put(39, y0 + 1, "acc", SH)
    mp.put(39, y0 + 2, "acc", DP)
    mp.put(16, y0 + 1, "acc", HI)
    for x in range(18, 38):                                        # dobras do pano
        if x % 5 == 2:
            mp.put(x, y0 + 2, "acc", SH)
    if dots:
        for x in range(20, 37, 5):
            mp.put(x, y0 + 1, "acc2")
            mp.put(x + 2, y0 + 2, "acc2", SH)
    if tails:                                                      # no e pontas soltas (lado direito)
        mp.rect(39, y0, 3, 4, "acc")
        mp.put(40, y0 + 1, "acc", HI)
        mp.put(41, y0 + 3, "acc", DP)
        mp.poly([(41, y0 + 0.5), (47.5, y0 - 2.5), (46.5, y0 + 2.2)], "acc", SH)
        mp.poly([(41, y0 + 2.5), (46.5, y0 + 6.5), (43.5, y0 + 7)], "acc", BASE)
        mp.put(46, y0 - 2, "acc", HI)
        mp.put(45, y0 + 6, "acc", SH)
    for x in range(18, 38):
        if mp.mat(x, y0 + 4) == "skin":
            mp.tone(x, y0 + 4, SH, ("skin",))


def _goggles(mp, y0=4):
    """Oculos de protecao na testa (Bia): tira de couro, aros de latao e lentes ambar."""
    mp.hline(16, 39, y0 + 3, "belt")
    mp.hline(16, 39, y0 + 4, "belt", SH)
    mp.put(16, y0 + 3, "belt", HI)
    for cx in (22.5, 32.5):
        mp.disc(cx, y0 + 3.5, 3.3, "gold")
        mp.disc(cx, y0 + 3.5, 2.1, "lens")
        x = int(cx)
        mp.put(x - 1, y0 + 2, "lens", HI)
        mp.put(x, y0 + 2, "lens", HI)
        mp.put(x - 1, y0 + 3, "lens", HI)
        mp.put(x + 1, y0 + 4, "lens", SH)
        mp.put(x, y0 + 5, "lens", DP)
        mp.put(x + 1, y0 + 5, "lens", DP)
    mp.bevel(("gold",), deep=True)
    mp.hline(26, 29, y0 + 3, "gold", SH)
    mp.hline(26, 29, y0 + 4, "gold", DP)


def _tiara(mp, star_x=33):
    for x in range(17, 39):
        y = int(round(3.6 + 7.0 * ((x - 27.5) / 10.5) ** 2))
        mp.put(x, y, "acc", HI if x < 27 else BASE)
        mp.put(x, y + 1, "acc", SH)
    sy = int(round(3.6 + 7.0 * ((star_x - 27.5) / 10.5) ** 2))
    for dx, dy in ((0, -2), (0, -1), (-1, 0), (1, 0), (0, 0), (-2, 0), (2, 0), (0, 1), (0, 2)):
        mp.put(star_x + dx, sy + dy, "gold", HI if (dx, dy) == (0, 0) else BASE)
    mp.put(star_x + 1, sy + 1, "gold", SH)


def _headset(mp):
    """Headset (Dudu): arco sobre o cabelo, conchas com LED verde e microfone ate a boca."""
    for x in range(15, 41):
        y = int(round(1.0 + 12.0 * ((x - 27.5) / 12.5) ** 2))
        mp.put(x, y, "acc2", HI)
        mp.put(x, y + 1, "acc2", SH)
    for sx in (-1, 1):
        x0 = 13 if sx < 0 else 38
        cup = {14: (x0 + 1, x0 + 3), 15: (x0, x0 + 4)}
        cup.update({y: (x0, x0 + 4) for y in range(16, 23)})
        cup.update({23: (x0 + 1, x0 + 3)})
        mp.rows(cup, "acc2")
        for y in range(15, 23):
            mp.put(x0, y, "acc2", HI if sx < 0 else SH)
            mp.put(x0 + 4, y, "acc2", SH if sx < 0 else DP)
        mp.hline(x0 + 1, x0 + 3, 22, "acc2", SH)
        mp.put(x0 + 2, 18, "led", HI)
        mp.put(x0 + 2, 19, "led")
        mp.put(x0 + 1 if sx < 0 else x0 + 3, 18, "led", SH)
    for x, y in ((16, 23), (17, 24), (18, 24), (19, 25), (20, 25)):  # haste do microfone
        mp.put(x, y, "acc2", BASE)
        mp.put(x, y + 1, "acc2", DP)
    mp.rect(21, 24, 3, 3, "acc2")                                  # capsula
    mp.put(21, 24, "acc2", HI)
    mp.put(23, 26, "acc2", DP)
    mp.put(22, 25, "led", HI)


def _scarf(mp):
    """Cachecol listrado (Dra. Helena): volta no pescoco e ponta caindo no peito com franja."""
    roll = {29: (22, 33), 30: (21, 34), 31: (20, 35), 32: (20, 35), 33: (21, 34), 34: (22, 33)}
    mp.rows(roll, "acc")
    mp.bevel(("acc",))
    for x in range(21, 35):
        if x % 3 == 0:
            mp.put(x, 31, "acc2")
            mp.put(x + 1, 32, "acc2", SH)
    mp.hline(22, 33, 29, "acc", HI)
    tail = {}
    for i, y in enumerate(range(33, 50)):
        x0 = 30 + i // 6
        tail[y] = (x0, x0 + 4)
    mp.rows(tail, "acc")
    for y, (a, b) in tail.items():
        mp.put(a, y, "acc", HI)
        mp.put(b, y, "acc", SH)
        if y % 4 == 1:
            mp.hline(a + 1, b - 1, y, "acc2")
    for x in range(32, 38):                                        # franja
        if x % 2 == 0:
            mp.put(x, 50, "acc", SH)
            mp.put(x, 51, "acc", DP)
        else:
            mp.put(x, 50, "acc", DP)
    mp.put(30, 34, "acc", DP)


def _mustache(mp):
    spans = {23: (24, 31), 24: (23, 32), 25: (23, 25)}
    mp.rows(spans, "mus")
    mp.hline(30, 32, 25, "mus")
    mp.hline(25, 30, 23, "mus", HI)
    mp.hline(29, 32, 24, "mus", SH)
    mp.put(23, 25, "mus", SH)
    mp.put(32, 25, "mus", DP)
    mp.put(27, 24, "mus", SH)
    mp.put(28, 24, "mus", SH)


def _mustache_walrus(mp):
    """Bigodao branco (Vo Nestor): cobre o labio de cima, pontas caidas."""
    mp.rows({22: (25, 30), 23: (23, 32), 24: (22, 33), 25: (22, 25)}, "mus")
    mp.hline(30, 33, 25, "mus")
    mp.put(22, 26, "mus", SH)
    mp.put(33, 26, "mus", DP)
    mp.hline(24, 30, 23, "mus", HI)
    mp.hline(26, 27, 22, "mus", HI)
    mp.hline(30, 33, 24, "mus", SH)
    for x in (24, 26, 29, 31):
        mp.put(x, 24, "mus", SH)
    mp.put(27, 24, "mus", DP)
    mp.put(28, 24, "mus", DP)


def _mustache_long(mp):
    """Bigode fino e comprido caindo pelos cantos da boca (Mestre Ogawa)."""
    mp.rows({23: (25, 30), 24: (24, 31)}, "mus")
    mp.hline(25, 27, 23, "mus", HI)
    mp.put(27, 24, "mus", SH)
    mp.put(28, 24, "mus", SH)
    for i, y in enumerate(range(25, 32)):
        mp.put(23 - (1 if i > 3 else 0), y, "mus", BASE if i < 4 else SH)
        mp.put(32 + (1 if i > 3 else 0), y, "mus", SH if i < 4 else DP)
    mp.put(22, 32, "mus", HI)
    mp.put(33, 32, "mus", SH)


def _grease(mp):
    """Graxa (Bia): manchas na bochecha, no nariz e na testa."""
    for x, y in ((33, 23), (34, 23), (34, 24), (35, 24), (21, 25), (22, 26)):
        mp.color(x, y, (70, 56, 54))
    mp.color(29, 21, (110, 82, 70))
    mp.color(33, 24, (96, 74, 66))


def _earrings(mp):
    mp.put(16, 23, "gold", HI)
    mp.put(16, 24, "gold", SH)
    mp.put(39, 23, "gold")
    mp.put(39, 24, "gold", SH)


def _cane(mp):
    """Bengala na mao direita (lado direito da tela): cabo curvo e ponteira de borracha."""
    for y in range(56, 92):                                        # haste (sai da mao e vai ao chao)
        x = 47 if y < 74 else 48
        mp.put(x, y, "wood", BASE)
        mp.put(x + 1, y, "wood", SH)
    for x, y in ((47, 55), (47, 54), (46, 53), (45, 53), (44, 53), (43, 54), (43, 55), (48, 55), (48, 54), (47, 53)):
        mp.put(x, y, "wood", HI if y == 53 else BASE)
    mp.put(43, 56, "wood", SH)
    mp.rect(47, 89, 3, 3, "belt")


# ================================================================================ ROUPAS
def _torso_spans(bottom=61, waist=50, fem=False):
    s = {33: (19, 36), 34: (15, 40)}
    for y in range(35, bottom + 1):
        if fem and 44 <= y < 54:
            s[y] = (15, 40) if y < 47 or y > 51 else (16, 39)
        else:
            s[y] = (14, 41) if y < waist else (15, 40)
    return s


def _moletom(mp, acc=()):
    mp.rows(_torso_spans(61), "top")
    _arms(mp, "top", "top", (55, 58))
    # volume do tronco
    for y in range(35, 58):
        mp.tone(15, y, HI)
        mp.tone(16, y, HI if y < 44 else BASE)
        mp.tone(39 if y >= 50 else 40, y, SH)
        mp.tone(40 if y >= 50 else 41, y, DP)
        mp.tone(38 if y >= 50 else 39, y, SH if y % 3 == 0 else BASE)
    # sombra dos bracos sobre o tronco
    for y in range(36, 50):
        mp.tone(14, y, SH)
    # capuz embolado atras do pescoco + gola
    mp.rows({30: (21, 23), 31: (20, 23), 32: (19, 23), 33: (19, 24), 34: (20, 35)}, "top")
    mp.rows({30: (32, 34), 31: (32, 35), 32: (32, 36), 33: (31, 36)}, "top")
    for x, y in ((21, 30), (20, 31), (19, 32), (34, 30), (35, 31), (36, 32)):
        mp.put(x, y, "top", HI if x < 28 else SH)
    mp.hline(23, 32, 34, "top", DP)                                 # gola (sombra do pescoco)
    mp.hline(22, 33, 35, "top", SH)
    mp.put(23, 33, "top", SH)
    mp.put(32, 33, "top", DP)
    # cordoes
    for x in (25, 30):
        for y in range(35, 43):
            mp.put(x, y, "cord", BASE if y < 41 else SH)
        mp.put(x, 43, "cord", DP)
        mp.put(x + (1 if x > 28 else -1), 36, "top", DP)
    # bolso canguru
    mp.hline(20, 35, 47, "top", DP)
    for y in range(48, 56):
        d = max(0, 50 - y)
        mp.put(19 + d, y, "top", DP)
        mp.put(36 - d, y, "top", DP)
    mp.hline(21, 34, 48, "top", HI)
    mp.hline(22, 33, 55, "top", SH)
    for y in range(49, 55):
        mp.put(35 - max(0, 50 - y), y, "top", SH)
    # textura de malha (pontinhos em V) nas areas em tom base
    for y in range(36, 57):
        for x in range(15, 41):
            if mp.mat(x, y) == "top" and mp.t[y + OY][x] == BASE and x % 3 == 0 and (y + x // 3) % 3 == 0:
                mp.tone(x, y, SH)
    # dobras na cintura e no peito
    for x, y in ((18, 44), (19, 45), (36, 43), (35, 44), (37, 45), (17, 52), (38, 52), (37, 53)):
        mp.tone(x, y, SH)
    # barra canelada
    for y in range(58, 62):
        for x in range(15, 41):
            mp.put(x, y, "top", SH if x % 2 else BASE)
    mp.hline(15, 40, 58, "top", DP)
    mp.hline(16, 39, 61, "top", DP)
    for y in range(55, 59):                                         # punhos canelados
        for x in list(range(9, 14)) + list(range(42, 47)):
            mp.put(x, y, "top", SH if x % 2 else BASE)
    mp.hline(9, 13, 55, "top", DP)
    mp.hline(42, 46, 55, "top", DP)
    for y in range(36, 55):                                         # costura do braco
        mp.tone(13, y, DP)
        mp.tone(42, y, DP)


def _jaleco(mp, acc):
    sp = _torso_spans(73, 60)
    for y in range(62, 74):
        sp[y] = (14, 41) if y < 70 else (13, 42)
    mp.rows(sp, "top")
    _arms(mp, "top", "top", (56, 58))
    # camisa + gravata no decote
    v = {33: (22, 33), 34: (23, 32), 35: (24, 31), 36: (24, 31), 37: (25, 30), 38: (25, 30), 39: (26, 29),
         40: (26, 29), 41: (27, 28), 42: (27, 28)}
    mp.rows(v, "shirt")
    mp.rows({33: (25, 30), 34: (25, 30)}, "shirt", HI)              # gola da camisa
    mp.put(27, 34, "shirt", SH)
    mp.put(28, 34, "shirt", SH)
    for y in range(35, 43):
        mp.put(27, y, "tie", BASE if y < 41 else SH)
        mp.put(28, y, "tie", SH)
    mp.put(27, 35, "tie", HI)
    mp.hline(27, 28, 34, "tie", SH)
    # lapelas
    for y in range(33, 48):
        d = (y - 33) // 2
        lx = 21 + d
        rx = 34 - d
        if y < 47:
            mp.put(lx, y, "top", DP)
            mp.put(lx - 1, y, "top", HI)
            mp.put(rx, y, "top", DP)
            mp.put(rx + 1, y, "top", SH)
    mp.vline(28, 48, 73, "top", DP)                                 # abertura central
    mp.vline(27, 48, 73, "top", HI)
    for y in (50, 56, 62):                                         # botoes
        mp.put(29, y, "button", BASE)
        mp.put(29, y + 1, "button", SH)
    for y in range(35, 72):                                        # volume
        mp.tone(15, y, HI)
        mp.tone(40, y, SH)
        mp.tone(41, y, DP)
    for y in range(66, 74):
        mp.tone(14, y, HI)
        mp.tone(13, y, BASE)
        mp.tone(42, y, DP)
    mp.hline(14, 41, 73, "top", SH)
    mp.hline(29, 41, 72, "top", SH)
    # bolso do peito (lado do coracao = esquerda da tela) com canetas
    mp.hline(16, 21, 43, "top", DP)
    mp.vline(16, 43, 48, "top", SH)
    mp.vline(21, 43, 48, "top", SH)
    mp.hline(16, 21, 48, "top", SH)
    if "canetas" in acc:
        for i, c in enumerate(("pen1", "pen2", "pen3")):
            mp.vline(17 + i * 2 - (1 if i == 2 else 0), 40, 43, c)
            mp.put(17 + i * 2 - (1 if i == 2 else 0), 40, c, HI)
    # bolsos laterais
    mp.hline(16, 22, 60, "top", DP)
    mp.hline(33, 39, 60, "top", DP)
    mp.hline(16, 22, 61, "top", SH)
    mp.hline(33, 39, 61, "top", SH)
    # dobras
    for x, y in ((24, 52), (25, 53), (33, 54), (32, 55), (19, 66), (20, 67), (36, 66), (35, 67), (31, 69)):
        mp.tone(x, y, SH)
    mp.tone(13, 55, SH)


def _terno(mp, acc):
    sp = _torso_spans(65, 52)
    for y in range(62, 66):
        sp[y] = (15, 40)
    mp.rows(sp, "top")
    _arms(mp, "top", "shirt", (57, 58), hand="glove" if "luvas" in acc else "skin")
    # lapelas (V fundo ate a linha 47) com entalhe; camisa e gravata so dentro do V
    def vx(y):
        d = (y - 32) / 3.0
        return int(round(22 + d)), int(round(33 - d))
    for y in range(32, 48):
        lx, rx = vx(y)
        for x in range(lx + 1, rx):
            mp.put(x, y, "shirt", BASE)
        mp.put(lx, y, "top", DP)
        mp.put(lx - 1, y, "top", HI)
        mp.put(lx - 2, y, "top", HI if y < 42 else BASE)
        mp.put(rx, y, "top", DP)
        mp.put(rx + 1, y, "top", SH)
        mp.put(rx + 2, y, "top", SH if y < 42 else BASE)
    mp.put(23, 32, "shirt", HI)
    mp.hline(23, 25, 33, "shirt", HI)                              # gola da camisa
    mp.hline(30, 32, 33, "shirt", SH)
    mp.put(24, 34, "shirt", SH)
    mp.put(31, 34, "shirt", SH)
    tie = {33: (27, 28), 34: (27, 28), 35: (27, 28), 36: (27, 28), 37: (27, 28), 38: (26, 29), 39: (26, 29),
           40: (26, 29), 41: (26, 29), 42: (26, 29), 43: (26, 29), 44: (26, 29), 45: (26, 29), 46: (26, 29)}
    for y, (a, b) in tie.items():
        lx, rx = vx(y)
        for x in range(max(a, lx + 1), min(b, rx - 1) + 1):
            tn = HI if x == a and y < 44 else (SH if x == b else BASE)
            mp.put(x, y, "tie", tn)
    mp.hline(27, 28, 33, "tie", HI)                                 # no
    mp.hline(27, 28, 35, "tie", SH)
    for y in (39, 42, 45):                                         # listras
        lx, rx = vx(y)
        for x in range(max(26, lx + 1), min(29, rx - 1) + 1):
            if (x + y) % 2 == 0:
                mp.put(x, y, "tie", DP)
    for x, y in ((19, 36), (20, 37), (35, 36), (36, 37)):             # entalhe da lapela
        mp.tone(x, y, DP)
    mp.vline(28, 48, 65, "top", DP)                                 # fechamento
    mp.put(29, 64, "top", DP)
    mp.put(30, 65, "top", DP)
    mp.put(27, 64, "top", HI)
    for y in (53, 59):                                             # botoes
        mp.put(27, y, "button", BASE)
        mp.put(27, y + 1, "button", SH)
    # lenco no bolso do peito (cor da gravata)
    mp.hline(32, 37, 42, "top", DP)
    mp.hline(33, 35, 41, "tie", HI)
    mp.put(34, 40, "tie", BASE)
    mp.put(36, 41, "tie", SH)
    # bolsos com aba
    for x0 in (17, 31):
        mp.hline(x0, x0 + 7, 58, "top", DP)
        mp.hline(x0, x0 + 7, 59, "top", SH)
    # volume
    for y in range(34, 66):
        mp.tone(15 if y >= 52 else 14, y, HI)
        mp.tone(16 if y >= 52 else 15, y, HI if y < 45 else BASE)
        mp.tone(39 if y >= 52 else 40, y, SH)
        mp.tone(40 if y >= 52 else 41, y, DP)
    for y in range(36, 52):
        mp.tone(14, y, SH)
    mp.hline(15, 40, 65, "top", DP)
    for x, y in ((20, 50), (21, 51), (35, 50), (34, 51), (23, 62), (24, 61), (33, 62)):
        mp.tone(x, y, SH)                                          # dobras
    for y in range(57, 59):                                        # punho da camisa
        mp.hline(9, 13, y, "shirt", HI if y == 57 else SH)
        mp.hline(42, 46, y, "shirt", BASE if y == 57 else SH)
    mp.hline(9, 13, 56, "top", DP)
    mp.hline(42, 46, 56, "top", DP)
    for y in range(36, 56):
        mp.tone(13, y, DP)
        mp.tone(42, y, DP)


def _blazer(mp, acc, pin=False):
    """Blazer feminino acinturado (Vivi, Helena, Valquiria): camisa no V, um botao, recortes."""
    sp = _torso_spans(61, 99, fem=True)
    for y in range(54, 62):
        sp[y] = (14, 41)
    mp.rows(sp, "top")
    _arms(mp, "top", "shirt", (57, 58))

    def vx(y):
        d = (y - 32) / 2.6
        return int(round(22 + d)), int(round(33 - d))
    for y in range(32, 46):
        lx, rx = vx(y)
        for x in range(lx + 1, rx):
            mp.put(x, y, "shirt", BASE if y > 34 else HI)
        mp.put(lx, y, "top", DP)
        mp.put(lx - 1, y, "top", HI)
        mp.put(lx - 2, y, "top", HI if y < 41 else BASE)
        mp.put(rx, y, "top", DP)
        mp.put(rx + 1, y, "top", SH)
        mp.put(rx + 2, y, "top", SH if y < 41 else BASE)
    for x, y in ((24, 34), (25, 35), (31, 34), (30, 35)):             # gola da camisa (pontas)
        mp.put(x, y, "shirt", SH)
    for y in range(36, 45):                                        # vista da camisa
        if mp.mat(28, y) == "shirt":
            mp.put(28, y, "shirt", SH)
    for y in (38, 42):
        if mp.mat(27, y) == "shirt":
            mp.put(27, y, "shirt", HI)
    for x, y in ((19, 37), (20, 38), (36, 37), (35, 38)):             # entalhe da lapela
        mp.tone(x, y, DP)
    mp.vline(28, 46, 57, "top", DP)                                 # fechamento + abertura em curva
    for x, y in ((29, 58), (30, 59), (31, 60), (32, 61), (27, 58), (26, 59), (25, 60), (24, 61)):
        mp.put(x, y, "top", DP)
    for y, (a, b) in ((59, (27, 29)), (60, (26, 30)), (61, (25, 31))):
        mp.hline(a, b, y, "pants", SH)
    mp.put(27, 50, "button", HI)
    mp.put(27, 51, "button", SH)
    for y in range(44, 54):                                        # recortes (pences)
        mp.tone(20, y, SH)
        mp.tone(35, y, SH)
    for x0 in (16, 33):                                            # bolsos com aba
        mp.hline(x0, x0 + 6, 55, "top", DP)
        mp.hline(x0, x0 + 6, 56, "top", SH)
    for y in range(34, 62):
        a, b = sp[y]
        mp.tone(a, y, HI)
        mp.tone(a + 1, y, HI if y < 44 else BASE)
        mp.tone(b - 1, y, SH)
        mp.tone(b, y, DP)
    for y in range(36, 52):
        mp.tone(14, y, SH)
    mp.hline(14, 41, 61, "top", DP)
    for y in range(36, 56):
        mp.tone(13, y, DP)
        mp.tone(42, y, DP)
    mp.hline(9, 13, 56, "top", DP)
    mp.hline(42, 46, 56, "top", DP)
    if pin:                                                        # broche na lapela
        mp.put(35, 41, "pin", HI)
        mp.put(36, 41, "pin")
        mp.put(35, 42, "pin")
        mp.put(36, 42, "pin", SH)


def _camiseta(mp, fem=False, print_=None, grease=False, rag=False):
    sp = _torso_spans(60, 99, fem=fem)
    sp[34] = (16, 39)
    mp.rows(sp, "top")
    _arms_short(mp, "top", 43)
    # gola careca canelada
    mp.hline(22, 33, 33, "top", HI)
    mp.hline(23, 32, 34, "top", SH)
    mp.hline(24, 31, 35, "top", DP)
    for y in range(35, 59):                                        # volume
        a, b = sp[y]
        mp.tone(a, y, HI)
        mp.tone(a + 1, y, HI if y < 42 else BASE)
        mp.tone(b - 1, y, SH)
        mp.tone(b, y, DP)
    for y in range(36, 44):
        mp.tone(15, y, SH)
        mp.tone(40, y, DP)
    for x, y in ((20, 46), (21, 47), (34, 45), (35, 46), (19, 54), (20, 55), (36, 55), (35, 56), (27, 52), (28, 53)):
        mp.tone(x, y, SH)                                          # dobras
    mp.hline(14, 41, 59, "top", SH)
    mp.hline(15, 40, 60, "top", DP)
    if print_ == "raio":                                           # raio estampado (Gabi Trovao)
        bolt = [(29.5, 37), (24.5, 45.5), (28, 45.5), (25.5, 53.5), (32, 43.5), (28.5, 43.5), (31.5, 37)]
        mp.poly(bolt, "acc")
        mp.bevel(("acc",))
        for x, y in ((29, 38), (28, 40), (27, 42), (26, 44)):
            mp.tone(x, y, HI, ("acc",))
    if grease:
        for x, y in ((33, 50), (34, 50), (34, 51), (19, 40), (20, 41), (24, 56), (25, 56), (37, 39)):
            mp.color(x, y, (56, 50, 56))
    if rag:                                                        # estopa vermelha presa na cintura
        mp.rows({57: (33, 36), 58: (33, 37), 59: (34, 37), 60: (34, 37), 61: (34, 36), 62: (35, 37), 63: (35, 36),
                 64: (36, 36)}, "rag", BASE)
        mp.bevel(("rag",), deep=True)
        mp.put(35, 59, "rag", SH)
        mp.put(36, 61, "rag", HI)
    if print_ == "engrenagem":                                     # engrenagem laranja no peito
        gx, gy = 21.5, 41.5
        for y in range(36, 47):
            for x in range(16, 27):
                dx, dy = x + 0.5 - gx, y + 0.5 - gy
                d = math.sqrt(dx * dx + dy * dy)
                a = math.atan2(dy, dx)
                if 1.6 < d <= 3.4 or (3.4 < d <= 4.6 and math.cos(8 * a) > 0.25):
                    mp.put(x, y, "acc", HI if dx + dy < -2 else (SH if dx + dy > 2.5 else BASE))


def _uniforme(mp):
    """Farda (Cap. Rodolfo): gola alta, dragonas, faixa dourada, estrela, barretas e cinto."""
    sp = _torso_spans(63, 52)
    mp.rows(sp, "top")
    _arms(mp, "top", "top", (55, 58))
    mp.hline(9, 13, 55, "gold", SH)                                # galao no punho
    mp.hline(42, 46, 55, "gold", SH)
    for y in range(34, 64):                                        # volume
        a, b = sp[y]
        mp.tone(a, y, HI)
        mp.tone(a + 1, y, HI if y < 44 else BASE)
        mp.tone(b - 1, y, SH)
        mp.tone(b, y, DP)
    for y in range(36, 52):
        mp.tone(14, y, SH)
    for y in range(36, 55):
        mp.tone(13, y, DP)
        mp.tone(42, y, DP)
    mp.vline(28, 35, 63, "top", DP)                                # fechamento + botoes dourados
    mp.vline(27, 35, 63, "top", HI)
    for y in (37, 41, 48, 52, 60):
        mp.put(29, y, "gold", HI)
        mp.put(29, y + 1, "gold", SH)
    mp.hline(14, 41, 45, "gold")                                   # faixa dourada (como no classico)
    mp.hline(14, 41, 46, "gold", SH)
    mp.put(14, 45, "gold", HI)
    for x0 in (16, 31):                                            # bolsos com aba
        mp.hline(x0, x0 + 7, 37, "top", DP)
        mp.hline(x0, x0 + 7, 38, "top", SH)
        mp.put(x0 + 3, 39, "top", DP)
        mp.put(x0 + 4, 39, "top", DP)
    for dx, dy in ((0, -2), (0, -1), (-1, 0), (1, 0), (0, 0), (-2, 0), (2, 0), (0, 1), (-1, 2), (1, 2)):   # estrela
        mp.put(19 + dx, 42 + dy, "gold", HI if (dx, dy) == (0, 0) else BASE)
    for i, c in enumerate(("medal1", "medal2", "medal3")):        # barretas
        mp.hline(32 + i * 2, 33 + i * 2, 41, c)
        mp.hline(32 + i * 2, 33 + i * 2, 42, c, SH)
    mp.hline(15, 40, 56, "belt")                                   # cinto + fivela
    mp.hline(15, 40, 57, "belt", SH)
    mp.rect(26, 55, 4, 4, "gold")
    mp.rect(27, 56, 2, 2, "belt", SH)
    mp.put(26, 55, "gold", HI)
    for sx in (-1, 1):                                             # dragonas com franja
        x0 = 10 if sx < 0 else 38
        mp.hline(x0 + 1, x0 + 6, 33, "gold", HI)
        mp.hline(x0, x0 + 7, 34, "gold")
        mp.hline(x0, x0 + 7, 35, "gold", SH)
        for x in range(x0, x0 + 8, 2):
            mp.put(x, 36, "gold", SH)
    mp.hline(15, 40, 63, "top", DP)
    for x, y in ((20, 50), (21, 51), (35, 50), (34, 51), (22, 60), (34, 61)):
        mp.tone(x, y, SH)


def _uniform_collar(mp):
    mp.rows({30: (23, 32), 31: (22, 33), 32: (22, 33), 33: (22, 33)}, "top")
    mp.hline(23, 32, 30, "top", HI)
    mp.hline(22, 33, 33, "top", SH)
    mp.put(22, 31, "top", HI)
    mp.put(33, 31, "top", DP)
    mp.put(33, 32, "top", DP)
    mp.hline(27, 28, 31, "top", DP)
    mp.hline(27, 28, 32, "top", DP)
    for x in (24, 31):                                             # insignias da gola
        mp.put(x, 32, "gold", HI)


def _kimono(mp, fem=False):
    """Kimono de artes marciais (Kenji, Ogawa): golas cruzadas, mangas largas e faixa com no."""
    sp = {33: (19, 36), 34: (15, 40)}
    sp.update({y: (14, 41) for y in range(35, 63)})
    mp.rows(sp, "top")
    arm = {34: (11, 13), 35: (10, 13)}
    for y in range(36, 57):
        arm[y] = (max(7, 9 - max(0, y - 44) // 4), 13)
    mp.mirror(arm, "top")
    for y in range(36, 55):
        a, _ = arm[y]
        mp.put(a, y, "top", HI)
        mp.put(55 - a, y, "top", DP)
        mp.put(13, y, "top", SH)
        mp.put(42, y, "top", SH)
    mp.hline(arm[56][0], 13, 56, "top", DP)                        # boca da manga
    mp.hline(42, 55 - arm[56][0], 56, "top", DP)
    mp.hline(arm[55][0] + 1, 13, 55, "top", SH)
    mp.hline(42, 54 - arm[55][0], 55, "top", SH)
    for x, y in ((10, 46), (11, 47), (9, 50), (44, 46), (45, 47), (46, 50)):   # dobras das mangas
        mp.put(x, y, "top", SH)
    _hands(mp, 57)
    # peito (V de pele) + golas cruzadas (a de cima vai da direita para a esquerda da tela)
    for y in range(33, 41):
        d = (y - 33) * 0.62
        for x in range(int(23 + d), int(33 - d) + 1):
            mp.put(x, y, "skin", BASE)
        mp.put(int(33 - d), y, "skin", SH)
    mp.hline(25, 30, 33, "skin", DP)
    mp.put(27, 36, "skin", SH)
    mp.put(28, 37, "skin", SH)
    for i in range(0, 17):                                         # gola de cima (larga): (33,33) -> (22,49)
        t = i / 16.0
        x = int(round(33 - 11 * t))
        y = int(round(33 + 16 * t))
        mp.put(x, y, "top", HI)
        mp.put(x + 1, y, "top", BASE)
        mp.put(x + 2, y, "top", SH)
        mp.put(x - 1, y, "top", DP)
    for i in range(0, 8):                                          # gola de baixo: (22,33) -> (27,40)
        t = i / 7.0
        x = int(round(22 + 5 * t))
        y = int(round(33 + 7 * t))
        mp.put(x, y, "top", SH)
        mp.put(x - 1, y, "top", HI)
        mp.put(x + 1, y, "top", DP)
    for y in range(35, 62):                                        # volume
        mp.tone(15, y, HI)
        mp.tone(40, y, SH)
        mp.tone(41, y, DP)
    for y in range(36, 52):
        mp.tone(14, y, SH)
    # faixa com no e pontas
    mp.hline(14, 41, 49, "belt", HI)
    mp.hline(14, 41, 50, "belt")
    mp.hline(14, 41, 51, "belt", SH)
    mp.rows({48: (25, 30), 49: (24, 31), 50: (24, 31), 51: (24, 31), 52: (25, 30)}, "belt")
    mp.hline(25, 30, 48, "belt", HI)
    mp.vline(27, 49, 51, "belt", DP)
    mp.put(28, 50, "belt", SH)
    for i, y in enumerate(range(53, 60)):
        mp.put(25 - i // 3, y, "belt", BASE)
        mp.put(26 - i // 3, y, "belt", SH)
        mp.put(30 + i // 3, y, "belt", SH)
        mp.put(31 + i // 3, y, "belt", DP)
    for i in range(0, 10):                                         # aba de baixo continua a gola
        mp.put(22 - i // 3, 52 + i, "top", DP)
    for x, y in ((19, 56), (20, 57), (35, 54), (36, 55), (33, 59), (17, 60)):
        mp.tone(x, y, SH)
    mp.hline(14, 41, 62, "top", DP)


def _colete(mp, acc):
    """Camisa branca de manga comprida + colete marrom (Vo Nestor), botoes dourados e corrente."""
    sp = _torso_spans(62, 52)
    mp.rows(sp, "shirt")
    _arms(mp, "shirt", "shirt", (56, 58))
    mp.hline(9, 13, 56, "shirt", DP)
    mp.hline(42, 46, 56, "shirt", DP)
    for y in range(36, 56):
        mp.tone(13, y, SH)
        mp.tone(42, y, DP)
    vest = {33: (18, 21), 34: (16, 22), 35: (15, 22)}
    for y in range(36, 62):
        lx = min(28, 22 + max(0, (y - 35)) // 2)
        vest[y] = (14 if y < 52 else 15, lx)
    vest_r = {y: (55 - b, 55 - a) for y, (a, b) in vest.items()}
    mp.rows(vest, "top")
    mp.rows(vest_r, "top")
    mp.rows({62: (15, 27), 63: (22, 28), 64: (26, 28)}, "top")      # pontas da barra
    mp.rows({62: (28, 40), 63: (28, 33), 64: (28, 29)}, "top")
    for y in range(33, 63):                                        # beiradas do colete
        if y in vest:
            mp.put(vest[y][1], y, "top", DP)
            mp.put(vest[y][1] - 1, y, "top", HI)
            mp.put(vest_r[y][0], y, "top", HI)
            mp.put(vest_r[y][0] + 1, y, "top", BASE)
            mp.put(vest[y][0], y, "top", HI)
            mp.put(vest_r[y][1], y, "top", DP)
            mp.put(vest_r[y][1] - 1, y, "top", SH)
    for y in range(36, 44):                                        # vista da camisa no V
        if mp.mat(28, y) == "shirt":
            mp.put(28, y, "shirt", SH)
    for y in (48, 52, 56, 60):                                     # botoes
        mp.put(29, y, "gold", HI)
        mp.put(29, y + 1, "gold", SH)
    for x0 in (17, 33):                                            # bolsos
        mp.hline(x0, x0 + 5, 52, "top", DP)
        mp.hline(x0, x0 + 5, 53, "top", HI)
    for x, y in ((30, 53), (31, 54), (32, 54), (33, 54), (34, 53)):  # corrente do relogio
        mp.put(x, y, "gold", BASE if x % 2 else HI)
    for y in range(37, 62):                                        # trama (tweed)
        for x in range(15, 41):
            if mp.mat(x, y) == "top" and mp.t[y + OY][x] == BASE and (x + 2 * y) % 5 == 0:
                mp.tone(x, y, SH)
    for x, y in ((20, 47), (21, 48), (35, 47), (34, 48)):
        mp.tone(x, y, SH)


def _shirt_collar(mp):
    for x, y in ((23, 33), (24, 33), (24, 34), (25, 34), (32, 33), (31, 33), (31, 34), (30, 34), (23, 32), (32, 32)):
        mp.put(x, y, "shirt", HI if x < 28 else BASE)
    mp.put(25, 35, "shirt", SH)
    mp.put(30, 35, "shirt", SH)
    mp.put(32, 32, "shirt", SH)


def _avental(mp, acc):
    """Blusa clara de manga arregacada + avental marrom (Dona Odete): bolso, colher e farinha."""
    sp = _torso_spans(61, 99, fem=True)
    mp.rows(sp, "top")
    _arms_short(mp, "top", 46, roll=True)
    mp.hline(22, 33, 33, "top", HI)                                 # gola
    mp.hline(23, 32, 34, "top", SH)
    for y in range(35, 61):
        a, b = sp[y]
        mp.tone(a, y, HI)
        mp.tone(b - 1, y, SH)
        mp.tone(b, y, DP)
    bib = {y: (21, 34) for y in range(38, 46)}
    skirt = {}
    for y in range(46, 77):
        w = min(3, (y - 46) // 6)
        skirt[y] = (18 - w, 37 + w)
    mp.rows(bib, "apron")
    mp.rows(skirt, "apron")
    mp.bevel(("apron",), deep=True)
    for i in range(6):                                             # alcas do pescoco
        mp.put(21 + i // 3, 37 - i, "apron", SH)
        mp.put(34 - i // 3, 37 - i, "apron", DP)
    mp.hline(15, 40, 46, "apron", DP)                              # amarracao na cintura
    mp.hline(15, 40, 47, "apron", SH)
    mp.put(15, 46, "apron", SH)
    mp.put(40, 47, "apron", DP)
    for y in range(52, 60):                                        # bolso com pesponto
        mp.put(22, y, "apron", SH)
        mp.put(33, y, "apron", DP)
    mp.hline(22, 33, 52, "apron", HI)
    mp.hline(22, 33, 59, "apron", DP)
    for x in range(23, 33, 2):
        mp.put(x, 53, "apron", BASE)
    mp.vline(30, 47, 53, "wood")                                    # colher de pau no bolso
    mp.rect(29, 45, 3, 3, "wood")
    mp.put(29, 45, "wood", HI)
    mp.put(31, 47, "wood", SH)
    for y in range(48, 76):                                        # pregas
        if y % 2 == 0:
            mp.tone(21, y, SH, ("apron",))
            mp.tone(34, y, SH, ("apron",))
    for x, y in ((24, 41), (25, 41), (31, 64), (32, 65), (20, 68), (36, 70), (27, 72)):   # farinha
        mp.color(x, y, (236, 226, 206))
    mp.hline(15 + 0, 40, 76, "apron", DP)


# ================================================================================ PERSONAGENS
# hair: cabelo da frente | back: cabelo de tras (antes da roupa) | neck: depois da cabeca (golas)
# head: acessorios de cabeca (depois do cabelo) | legs: estilo das pernas | fem/old: rosto
SPECS = {
    "teo": {"hair": _hair_espetado, "outfit": "moletom", "pants": (52, 66, 104), "shoe": (60, 56, 70),
            "sole": (236, 232, 226), "cord": (238, 230, 220), "eye": (70, 46, 34),
            "hair_pal": ((168, 112, 70), (104, 66, 42), (64, 40, 30), (40, 24, 22))},
    "ambrosio": {"hair": _hair_calvo, "outfit": "jaleco", "pants": (52, 54, 66), "shoe": (40, 34, 38),
                 "sole": (24, 20, 24), "shirt": (176, 206, 236), "tie": (150, 50, 60),
                 "button": (200, 200, 210), "eye": (70, 60, 50), "mus": ((176, 176, 182), "white")},
    "gervasio": {"hair": _hair_raspado, "outfit": "terno", "shoe": (92, 52, 34), "sole": (40, 26, 22),
                 "legs": "suit", "shirt": (244, 244, 248), "tie": (0, 176, 210), "button": (40, 30, 26),
                 "eye": (64, 42, 30)},
    "vivi": {"hair": _hair_longo, "back": _hair_longo_back, "outfit": "blazer", "fem": True,
             "pants": (40, 44, 78), "shoe": (40, 36, 52), "sole": (20, 18, 26), "legs": "suit",
             "shirt": (70, 100, 190), "eye": (46, 80, 170), "pin": (0, 220, 255), "head": ("tiara",),
             "hair_pal": ((92, 120, 214), (44, 60, 140), (28, 36, 96), (16, 18, 56)),
             "acc": ((236, 244, 255), (184, 210, 255), (120, 150, 230), (70, 90, 170))},
    "bia": {"hair": _hair_bia, "outfit": "camiseta", "fem": True, "pants": (54, 62, 92), "shoe": (110, 70, 44),
            "sole": (50, 36, 30), "legs": "boots", "eye": (70, 44, 30), "head": ("bandana", "goggles", "graxa"),
            "hair_pal": ((96, 66, 52), (60, 38, 30), (40, 25, 20), (24, 14, 14)),
            "acc": (255, 150, 40), "acc2": ((255, 235, 190), "white"), "belt": (92, 60, 40),
            "gold": ((150, 140, 136), (96, 88, 90), (64, 58, 64), (40, 34, 42)),
            "lens": ((210, 246, 255), (90, 190, 220), (50, 120, 170), (30, 70, 110)),
            "shirt_extra": {"grease": True}, "print": "engrenagem"},
    "dudu": {"hair": _hair_ondulado, "outfit": "moletom", "pants": (60, 66, 84), "shoe": (230, 230, 236),
             "sole": (80, 230, 120), "legs": "sneaker", "cord": (230, 240, 230), "eye": (60, 40, 30),
             "head": ("headset",), "hair_pal": ((96, 92, 104), (52, 50, 60), (34, 32, 42), (18, 16, 24)),
             "acc2": ((150, 160, 184), (92, 100, 124), (60, 64, 84), (36, 38, 54)), "led": (80, 230, 120)},
    "augusto": {"hair": _hair_curto_m, "outfit": "terno", "legs": "suit", "shoe": (36, 34, 44), "sole": (16, 14, 20),
                "shirt": (214, 226, 242), "tie": (0, 190, 220), "button": (190, 196, 210), "eye": (90, 110, 140),
                "glove": ((246, 248, 255), "white"), "brow": "light"},
    "rodolfo": {"hair": _hair_militar, "outfit": "uniforme", "neck": _uniform_collar, "legs": "boots",
                "pants": (60, 70, 80), "stripe": "gold", "shoe": (34, 32, 38), "sole": (18, 16, 20),
                "eye": (60, 46, 36), "hair_pal": ((100, 100, 112), (66, 66, 74), (46, 46, 54), (30, 30, 36)),
                "gold": (240, 200, 70), "belt": (36, 34, 40), "brow": "thick",
                "medal1": (220, 60, 60), "medal2": (60, 120, 230), "medal3": (70, 190, 100)},
    "helena": {"hair": _hair_bob, "back": _hair_bob_back, "outfit": "blazer", "fem": True, "neck": _scarf,
               "pants": (44, 38, 66), "shoe": (60, 40, 70), "sole": (24, 18, 30), "legs": "suit",
               "shirt": (70, 100, 190), "eye": (80, 60, 110),
               "hair_pal": ((134, 104, 166), (88, 64, 114), (62, 42, 84), (38, 26, 56)),
               "acc": (190, 130, 255), "acc2": ((236, 214, 255), "white")},
    "kenji": {"hair": _hair_kenji, "outfit": "kimono", "legs": "gi", "eye": (50, 34, 30), "head": ("bandana",),
              "pants": None, "hair_pal": ((80, 82, 104), (40, 40, 52), (26, 26, 34), (14, 14, 20)),
              "acc": (255, 150, 40), "acc2": ((255, 235, 190), "white"), "belt": (40, 40, 60), "brow": "thick"},
    "nestor": {"hair": lambda mp: _hair_calvo(mp, True), "outfit": "colete", "neck": _shirt_collar, "old": True,
               "legs": "slipper", "pants": (70, 66, 80), "sole": (40, 150, 200), "strap": (30, 60, 110),
               "shirt": ((236, 238, 244), "white"), "eye": (80, 70, 60), "brow": "bushy",
               "mus": ((236, 236, 240), "white"), "gold": (230, 190, 80), "wood": (130, 90, 55),
               "head": ("cane",), "beard": "walrus"},
    "valquiria": {"hair": _hair_coque, "outfit": "blazer", "fem": True, "old": True, "legs": "suit",
                  "pants": (60, 30, 56), "shoe": (40, 20, 34), "sole": (20, 10, 18), "shirt": (70, 100, 190),
                  "eye": (110, 60, 120), "head": ("tiara", "earrings"), "pin": (255, 214, 90),
                  "hair_pal": ((255, 255, 255), (234, 234, 242), (182, 186, 210), (128, 132, 166)),
                  "acc": ((255, 168, 205), "std"), "band": (255, 110, 160), "lip": ((176, 36, 84), (220, 90, 130)),
                  "brow": "light"},
    "gabi": {"hair": _cap_spikes, "outfit": "camiseta", "fem": True, "pants": (40, 50, 96), "stripe": "acc2",
             "shoe": (240, 240, 246), "sole": (60, 140, 255), "legs": "sneaker", "eye": (60, 40, 30),
             "head": ("cap",), "hair_pal": ((130, 210, 255), (54, 136, 250), (32, 86, 206), (20, 48, 136)),
             "acc": ((96, 140, 236), (40, 82, 196), (28, 54, 140), (18, 32, 90)), "acc2": ((248, 248, 252), "white"),
             "print": "raio"},
    "odete": {"hair": lambda mp: _hair_coque(mp, True), "outfit": "avental", "fem": True, "old": True,
              "pants": (54, 52, 70), "shoe": (60, 50, 50), "sole": (30, 24, 24), "eye": (60, 40, 30),
              "hair_pal": ((222, 222, 226), (172, 172, 178), (128, 128, 140), (86, 86, 100)),
              "band": (255, 110, 160), "apron": (120, 82, 52), "wood": (190, 140, 80), "brow": "light"},
    "ogawa": {"hair": _hair_ogawa, "outfit": "kimono", "legs": "gi", "old": True, "eye": (50, 40, 34),
              "pants": None, "hair_pal": ((200, 200, 206), (88, 88, 96), (60, 60, 68), (38, 38, 46)),
              "belt": (24, 22, 28), "mus": ((160, 160, 168), "white"), "beard": "long", "brow": "thick_grey"},
}


def supports(cid):
    return cid in SPECS and cid in story.CHARACTERS


def is_robot(cid):
    ch = story.CHARACTERS.get(cid)
    return ch is not None and (cid == "ze" or ch["outfit"][0] == "robo")


def _palette(cid):
    ch = story.CHARACTERS[cid]
    sp = SPECS[cid]
    top = tuple(ch["outfit"][1])
    kind = ch["outfit"][0]
    if kind == "avental":
        top = P.lerp(top, (250, 250, 250), 0.75)
    hair = tuple(ch["hair"][1])
    pal = {"skin": _ramp(ch["skin"], "skin"), "hair": _ramp(hair, "white" if hair[0] > 150 else "std"),
           "top": _ramp(top, "white" if min(top) > 200 else "std"),
           "pants": _mk(sp.get("pants") or top), "shoe": _mk(sp.get("shoe", (40, 36, 44))),
           "sole": _mk(sp.get("sole", (24, 20, 24))),
           "cord": _ramp(sp.get("cord", (230, 230, 230)), "white"),
           "shirt": _mk(sp.get("shirt", (240, 240, 245))), "tie": _ramp(sp.get("tie", (0, 176, 210))),
           "button": _ramp(sp.get("button", (40, 40, 40))),
           "pen1": _ramp((60, 120, 240)), "pen2": _ramp((230, 70, 70)), "pen3": _ramp((60, 200, 110)),
           "mus": _mk(sp["mus"]) if "mus" in sp else _ramp(P.darker(hair, 0.8)),
           "glass": _ramp((70, 66, 80)), "acc": _mk(sp.get("acc", tuple(ch["color"]))),
           "acc2": _mk(sp.get("acc2", (240, 240, 245))), "gold": _mk(sp.get("gold", (240, 196, 70))),
           "glove": _mk(sp.get("glove", (246, 248, 255))), "wood": _mk(sp.get("wood", (130, 90, 55))),
           "belt": _mk(sp.get("belt", (40, 34, 36))), "lens": _mk(sp.get("lens", (120, 200, 240))),
           "apron": _mk(sp.get("apron", (120, 82, 52))), "band": _mk(sp.get("band", (255, 110, 160))),
           "led": _mk(sp.get("led", (80, 230, 120))), "strap": _mk(sp.get("strap", (40, 40, 40))),
           "pin": _mk(sp.get("pin", (255, 214, 90))), "rag": _mk(sp.get("rag", (200, 50, 50)))}
    for m in ("medal1", "medal2", "medal3"):
        if m in sp:
            pal[m] = _mk(sp[m])
    if sp.get("hair_pal"):
        pal["hair"] = tuple(sp["hair_pal"])
    if kind == "kimono" and min(top) > 200:                        # kimono branco: sombra mais fria
        pal["top"] = ((255, 255, 255), (236, 238, 244), (184, 190, 214), (128, 132, 168))
    return pal


def _build_maps(cid):
    sp = SPECS[cid]
    ch = story.CHARACTERS[cid]
    acc = ch.get("acc", ())
    kind = sp["outfit"]
    fem = sp.get("fem", False)
    legs = _Map()
    lstyle = sp.get("legs", "jeans")
    pants = "top" if kind == "terno" or sp.get("pants", 1) is None else "pants"
    _legs(legs, pants=pants, style=lstyle, stripe=sp.get("stripe"))
    legs.cut_rows(*LEG_CUT)
    up = _Map()
    if sp.get("back"):
        sp["back"](up)
    if kind == "moletom":
        _moletom(up, acc)
    elif kind == "jaleco":
        _jaleco(up, acc)
    elif kind == "terno":
        _terno(up, acc)
    elif kind == "blazer":
        _blazer(up, acc, pin="pin" in sp)
    elif kind == "camiseta":
        extra = sp.get("shirt_extra", {})
        _camiseta(up, fem, sp.get("print"), extra.get("grease"), extra.get("rag"))
    elif kind == "uniforme":
        _uniforme(up)
    elif kind == "kimono":
        _kimono(up, fem)
    elif kind == "colete":
        _colete(up, acc)
    elif kind == "avental":
        _avental(up, acc)
    _head(up, fem)
    if sp.get("old") and ch["hair"][0] != "calvo":
        _wrinkles(up, forehead=False)
    if sp.get("neck"):
        sp["neck"](up)
    sp["hair"](up)
    for a in sp.get("head", ()):
        if a == "tiara":
            _tiara(up)
        elif a == "bandana":
            _bandana(up, 10 if cid == "bia" else 10)
        elif a == "goggles":
            _goggles(up, 3)
        elif a == "graxa":
            _grease(up)
        elif a == "headset":
            _headset(up)
        elif a == "cap":
            _cap(up)
        elif a == "earrings":
            _earrings(up)
        elif a == "cane":
            _cane(up)
    beard = sp.get("beard")
    if beard == "walrus":
        _mustache_walrus(up)
    elif beard == "long":
        _mustache_long(up)
    elif "bigode" in acc:
        _mustache(up)
    return legs, up


# ================================================================================ ROSTO POR HUMOR
# sobrancelhas: (y externo, y interno) em px (negativo = sobe), por lado (esq, dir)
_BROWS = {"neutro": (0, 0, 0, 0), "feliz": (-1, -1, -1, -1), "euforico": (-2, -2, -2, -2), "susto": (-2, -3, -2, -3),
          "maravilhado": (-2, -3, -2, -3), "triste": (1, -1, 1, -1), "chorando": (1, -2, 1, -2), "bravo": (-1, 2, -1, 2),
          "convencida": (-1, -1, -2, -3), "convencido": (-1, -1, -2, -3), "corada": (0, -1, 0, -1),
          "suor": (1, -1, 1, -1), "espirro": (1, 0, 1, 0), "calmo": (0, 0, 0, 0), "sonolento": (1, 1, 1, 1),
          "cansado": (1, 1, 1, 1), "piscando": (1, 1, -1, -1), "malicioso": (-2, 1, -2, 1),
          "pensando": (0, 0, -2, -1), "determinado": (-1, 2, -1, 2), "gritando": (-1, 2, -1, 2), "robo": (0, 0, 0, 0)}
_SHUT = P._CLOSED_EYES


class _Painter:
    def __init__(self, surf, pal, k):
        self.s, self.pal, self.k = surf, pal, k

    def c(self, col):
        return P.shade(col, self.k)

    def px(self, x, y, col):
        if 0 <= x < CW and 0 <= y + OY < CH:
            self.s.set_at((x, y + OY), self.c(col))

    def h(self, x0, x1, y, col):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.px(x, y, col)

    def skin(self, t):
        return self.pal["skin"][t]


def _eye_open(pn, x, y, eye, look=(0, 0), big=False):
    """Olho aberto: palpebra escura, esclera e iris 2x2 com brilho (x = coluna da esquerda)."""
    lx, ly = look
    pn.h(x, x + 2, y, EYE)
    pn.h(x, x + 2, y + 1, SCLERA)
    pn.h(x, x + 2, y + 2, SCLERA)
    ix = x + 1 + lx if x < 28 else x + lx
    ix = max(x, min(x + 1, ix))
    pn.px(ix, y + 1 + ly, EYE)
    pn.px(ix + 1, y + 1 + ly, EYE)
    pn.px(ix, y + 2 + ly, eye)
    pn.px(ix + 1, y + 2 + ly, eye)
    pn.px(ix, y + 1 + ly, (255, 255, 255))                  # brilho
    if big:
        pn.h(x, x + 2, y + 3, SCLERA)
        pn.px(x - 1, y + 1, EYE) if x < 28 else pn.px(x + 3, y + 1, EYE)


def _eye_half(pn, x, y, eye, look=0):
    """Olho semicerrado (palpebra pesada): so a linha de baixo da esclera aparece, iris de lado."""
    pn.h(x - (1 if x < 28 else 0), x + 2 + (1 if x > 28 else 0), y + 1, EYE)
    pn.h(x, x + 2, y + 2, SCLERA)
    ix = (x + 1 if x < 28 else x) + look
    ix = max(x, min(x + 1, ix))
    pn.px(ix, y + 2, EYE)
    pn.px(ix + 1, y + 2, eye)
    pn.h(x, x + 2, y, pn.skin(SH))                          # palpebra (pele em sombra)


def _brows(pn, mood, col, style=None, fem=False):
    lo, li, ro, ri = _BROWS.get(mood, (0, 0, 0, 0))
    thick = mood in ("bravo", "determinado", "gritando", "malicioso") or style in ("thick", "bushy", "thick_grey")
    if fem and style not in ("thick", "bushy"):
        thick = mood in ("bravo", "determinado", "gritando")
    for side, xs, o, i_ in ((0, range(20, 25), lo, li), (1, range(35, 30, -1), ro, ri)):
        for j, x in enumerate(xs):                         # j: 0 = ponta externa .. 4 = ponta interna
            y = 16 + int(round(o + (i_ - o) * j / 4.0))
            if fem and j == 0 and o >= i_:
                y += 1                                     # arco feminino (cauda desce)
            pn.px(x, y, col)
            if thick and j >= (0 if style == "bushy" else 2):
                pn.px(x, y - 1, col)
        if style == "bushy":                               # sobrancelha farta caindo para fora
            xo = 19 if side == 0 else 36
            pn.px(xo, 16 + o, col)
            pn.px(xo, 17 + o, col)


def _paint_face(pn, cid, mood, blink, mouth):
    sp = SPECS[cid]
    eye = sp["eye"]
    pal = pn.pal
    fem = sp.get("fem", False)
    bstyle = sp.get("brow")
    if bstyle == "bushy":
        brow = pal["mus"][BASE]
    elif bstyle in ("light", "thick_grey") or story.CHARACTERS[cid]["hair"][0] == "calvo":
        brow = pal["hair"][SH] if bstyle != "thick_grey" else pal["hair"][BASE]
    else:
        brow = pal["hair"][DP]
    lip = LIP_F if fem else LIP
    lip2 = LIP_F2 if fem else None
    if sp.get("lip"):
        lip, lip2 = sp["lip"]
    skin_sh, skin_dp = pn.skin(SH), pn.skin(DP)
    L, Rr, EY = 21, 32, 18                                   # colunas dos olhos e linha da palpebra
    _brows(pn, mood, brow, bstyle, fem)
    closed = blink and mood not in _SHUT

    def happy(x):                                         # ^  (olho fechado sorrindo)
        pn.h(x, x + 2, EY + 1, EYE)
        pn.px(x - 1 if x < 28 else x + 3, EY + 2, EYE)
        pn.px(x + 3 if x < 28 else x - 1, EY + 2, skin_sh)
        if fem:
            pn.px(x - 1 if x < 28 else x + 3, EY + 1, EYE)

    def shut(x, down=True):                               # -  (olho fechado/sonolento)
        pn.h(x, x + 2, EY + 2, EYE)
        pn.px(x - 1 if x < 28 else x + 3, EY + (1 if down else 3), EYE)
        pn.h(x, x + 2, EY + 3, skin_sh)
        if fem:
            pn.px(x - 1 if x < 28 else x + 3, EY + 3, EYE)

    def lash(x):                                          # cilio na ponta de fora
        pn.px(x - 1 if x < 28 else x + 3, EY, EYE)
        pn.px(x - 1 if x < 28 else x + 3, EY - 1, EYE)

    # ---- olhos
    opened = False
    if closed:
        shut(L)
        shut(Rr)
    elif mood in ("feliz", "euforico"):
        happy(L)
        happy(Rr)
    elif mood in ("calmo", "sonolento", "chorando"):
        shut(L)
        shut(Rr)
        if mood == "sonolento":
            pn.h(L, L + 2, EY + 1, EYE)
            pn.h(Rr, Rr + 2, EY + 1, EYE)
    elif mood in ("espirro", "gritando"):
        for x, d in ((L, 1), (Rr, -1)):
            a, b = (x, x + 2) if d > 0 else (x + 2, x)
            pn.px(a, EY, EYE)
            pn.px(a + d, EY + 1, EYE)
            pn.px(b, EY + 2, EYE)
            pn.px(a + d, EY + 3, EYE)
            pn.px(a, EY + 4, EYE)
    elif mood in ("susto", "maravilhado"):
        for x in (L, Rr):
            pn.h(x - 1, x + 3, EY, EYE)
            pn.h(x - 1, x + 3, EY + 1, SCLERA)
            pn.h(x - 1, x + 3, EY + 2, SCLERA)
            pn.h(x - 1, x + 3, EY + 3, SCLERA)
            pn.h(x, x + 2, EY + 4, skin_sh)
            if mood == "susto":
                pn.px(x + 1, EY + 2, EYE)
            else:
                pn.px(x + 1, EY + 1, P.GOLD)
                pn.h(x, x + 2, EY + 2, P.GOLD)
                pn.px(x + 1, EY + 3, P.GOLD)
                pn.px(x + 1, EY + 2, (255, 255, 255))
        if fem:
            pn.px(L - 2, EY - 1, EYE)
            pn.px(Rr + 4, EY - 1, EYE)
    elif mood == "piscando":
        happy(L)
        _eye_open(pn, Rr, EY, eye)
        if fem:
            lash(Rr)
    elif mood in ("convencida", "convencido"):              # palpebras pesadas, olhar de cima, de lado
        _eye_half(pn, L, EY, eye, 1)
        _eye_half(pn, Rr, EY, eye, 1)
        if fem:
            pn.px(L - 2, EY + 1, EYE)
            pn.px(Rr + 4, EY + 1, EYE)
    elif mood == "malicioso":                                # olhos apertados olhando de lado + olheira
        for x in (L, Rr):
            pn.h(x, x + 2, EY + 1, EYE)
            pn.h(x, x + 2, EY + 2, SCLERA)
            pn.px(x, EY + 2, EYE)
            pn.px(x + 1, EY + 2, eye)
            pn.h(x, x + 2, EY + 3, EYE)
            pn.px(x + 2 if x < 28 else x, EY + 3, skin_sh)
            pn.h(x, x + 2, EY, skin_sh)
            pn.px(x + 2 if x < 28 else x, EY + 1, EYE)
            pn.px(x + 3 if x < 28 else x - 1, EY, EYE)     # canto interno puxado para baixo
        if fem:
            pn.px(L - 1, EY + 1, EYE)
            pn.px(Rr + 3, EY + 1, EYE)
    elif mood == "determinado":                              # olhar firme: palpebra reta e baixa, brilho forte
        for x in (L, Rr):
            pn.h(x - (1 if x < 28 else 0), x + 2 + (1 if x > 28 else 0), EY, EYE)
            pn.h(x, x + 2, EY + 1, EYE)
            pn.h(x, x + 2, EY + 2, SCLERA)
            pn.h(x, x + 2, EY + 3, SCLERA)
            ix = x + 1 if x < 28 else x
            pn.px(ix, EY + 2, eye)
            pn.px(ix + 1, EY + 2, eye)
            pn.px(ix, EY + 3, EYE)
            pn.px(ix + 1, EY + 3, EYE)
            pn.px(ix + 1, EY + 2, (255, 255, 255))
            pn.px(x + 2 if x < 28 else x, EY + 1, EYE)
            pn.h(x, x + 2, EY + 4, skin_sh)
        if fem:
            pn.px(L - 2, EY, EYE)
            pn.px(Rr + 4, EY, EYE)
    elif mood in ("bravo", "cansado"):
        for x in (L, Rr):
            _eye_open(pn, x, EY, eye)
            pn.h(x, x + 2, EY + 1, EYE)
            if mood == "bravo":                             # palpebra inclinada para dentro
                pn.px(x + 2 if x < 28 else x, EY + 2, EYE)
            if mood == "cansado":
                pn.h(x, x + 2, EY + 3, skin_dp)
        opened = fem
    elif mood == "pensando":
        _eye_open(pn, L, EY, eye, (1, 0))
        _eye_open(pn, Rr, EY, eye, (1, 0))
        pn.px(L + 2, EY + 1, EYE)
        pn.px(Rr + 2, EY + 1, EYE)
        opened = fem
    elif mood == "triste":
        _eye_open(pn, L, EY, eye, (0, 0))
        _eye_open(pn, Rr, EY, eye, (0, 0))
        pn.px(L + 2, EY, skin_sh)
        pn.px(Rr, EY, skin_sh)
        opened = fem
    else:                                                  # neutro, suor, corada, robo
        _eye_open(pn, L, EY, eye)
        _eye_open(pn, Rr, EY, eye)
        opened = fem
    if opened:
        lash(L)
        lash(Rr)

    # ---- boca (linha 26; o bigode cobre 23-25)
    my = 26
    if mouth:
        sc = P._TALK_SCALE.get(mood, 0.9)
        w = 2 if sc < 0.8 else (3 if sc < 1.2 else 4)
        hgt = 2 if sc < 0.8 else (3 if sc < 1.2 else 4)
        x0, x1 = 28 - w, 27 + w
        for y in range(my - 1, my - 1 + hgt):
            inset = 1 if (y == my - 1 or y == my - 2 + hgt) and w > 2 else 0
            pn.h(x0 + inset, x1 - inset, y, MOUTH_IN)
        if mood in ("feliz", "euforico", "determinado", "gritando", "bravo", "malicioso") or w >= 3:
            pn.h(x0 + 1, x1 - 1, my - 1, TEETH)
        if hgt >= 3:
            pn.h(x0 + 2, x1 - 2, my - 2 + hgt, TONGUE)
        pn.h(x0 + 1, x1 - 1, my - 1 + hgt, lip2 or skin_sh)
        if mood == "malicioso":                             # canto puxado para cima mesmo falando
            pn.px(x1 + 1, my - 2, lip)
    elif mood == "feliz":
        pn.h(25, 30, my - 1, MOUTH_IN)
        pn.h(26, 29, my - 1, TEETH)
        pn.h(26, 29, my, MOUTH_IN)
        pn.px(24, my - 2, lip)
        pn.px(31, my - 2, lip)
        pn.h(26, 29, my + 1, lip2 or skin_sh)
    elif mood == "euforico":
        pn.h(24, 31, my - 1, MOUTH_IN)
        pn.h(25, 30, my - 1, TEETH)
        pn.h(24, 31, my, MOUTH_IN)
        pn.h(25, 30, my + 1, MOUTH_IN)
        pn.h(26, 29, my + 1, TONGUE)
        pn.h(26, 29, my + 2, MOUTH_IN)
        pn.px(23, my - 2, lip)
        pn.px(32, my - 2, lip)
    elif mood in ("susto", "maravilhado", "espirro", "sonolento"):
        r = 1 if mood == "sonolento" else 2
        pn.h(28 - r, 27 + r, my - 1, MOUTH_IN)
        pn.h(28 - r, 27 + r, my, MOUTH_IN)
        pn.h(28 - r, 27 + r, my + 1, MOUTH_IN if r > 1 else skin_sh)
        if r > 1:
            pn.h(27, 28, my + 1, TONGUE)
            pn.h(27, 28, my + 2, skin_sh)
    elif mood in ("triste", "bravo"):
        line = P.lerp(lip, MOUTH_IN, 0.6) if mood == "bravo" else lip
        pn.h(26, 29, my - 1, line)
        pn.px(25, my, line)
        pn.px(30, my, line)
        pn.h(26, 29, my, skin_sh)
        if mood == "bravo":
            pn.px(24, my + 1, line)
            pn.px(31, my + 1, line)
    elif mood == "chorando":
        pn.h(25, 30, my - 1, lip)
        pn.h(25, 30, my, MOUTH_IN)
        pn.h(26, 29, my + 1, MOUTH_IN)
        pn.h(27, 28, my + 1, TONGUE)
        pn.px(24, my, lip)
        pn.px(31, my, lip)
    elif mood == "determinado":                              # boca firme, cantos travados, queixo tenso
        dark = P.lerp(lip, MOUTH_IN, 0.55)
        pn.h(25, 30, my, dark)
        pn.px(24, my - 1, dark)
        pn.px(31, my - 1, dark)
        pn.h(26, 29, my + 1, lip2 or skin_sh)
        pn.h(26, 29, my + 3, skin_sh)                          # queixo contraido
        pn.px(23, my + 1, skin_sh)
        pn.px(32, my + 1, skin_sh)
    elif mood == "gritando":
        for y in range(my - 2, my + 3):
            pn.h(24 if my - 1 <= y <= my + 1 else 25, 31 if my - 1 <= y <= my + 1 else 30, y, MOUTH_IN)
        pn.h(25, 30, my - 2, TEETH)
        pn.h(26, 29, my + 2, TONGUE)
    elif mood == "pensando":
        pn.h(27, 30, my, lip)
        pn.px(31, my - 1, lip)
    elif mood in ("convencida", "convencido"):              # sorrisinho de lado bem marcado + covinha
        pn.h(24, 29, my, lip)
        pn.px(30, my - 1, lip)
        pn.px(31, my - 2, lip)
        pn.px(32, my - 2, skin_sh)
        pn.px(31, my - 1, skin_sh)
        if lip2:
            pn.h(25, 28, my + 1, lip2)
    elif mood == "malicioso":                                # sorriso torto mostrando os dentes de um lado
        pn.h(24, 29, my, MOUTH_IN)
        pn.h(25, 29, my - 1, MOUTH_IN)
        pn.h(26, 29, my - 1, TEETH)
        pn.px(30, my - 1, MOUTH_IN)
        pn.px(30, my - 2, lip)
        pn.px(31, my - 2, lip)
        pn.px(32, my - 3, lip)
        pn.px(23, my, lip)
        pn.h(25, 28, my + 1, lip2 or skin_sh)
        pn.px(32, my - 2, skin_sh)
    elif mood == "corada":
        pn.h(26, 29, my, lip)
        pn.px(25, my - 1, lip)
        pn.px(30, my - 1, lip)
    elif mood == "suor":
        for i, x in enumerate(range(24, 32)):
            pn.px(x, my - (i % 2), lip)
    elif mood == "calmo":
        pn.h(26, 29, my, lip)
        pn.px(25, my - 1, lip)
        pn.px(30, my - 1, lip)
    elif mood == "piscando":
        pn.h(25, 30, my, lip)
        pn.px(24, my - 1, lip)
        pn.px(31, my - 1, lip)
        pn.h(28, 29, my + 1, TONGUE)
    elif mood == "cansado":
        pn.h(26, 29, my, lip)
    else:                                                  # neutro, robo
        pn.h(26, 29, my, lip)
        pn.h(27, 28, my + 1, skin_sh)
    if not mouth and mood not in ("gritando", "euforico", "susto", "maravilhado", "determinado", "malicioso",
                                  "convencida", "convencido"):
        pn.h(27, 28, my + 1, lip2 or skin_sh)               # labio inferior

    # ---- extras
    if mood in ("corada", "euforico", "piscando") or (fem and mood in ("feliz", "convencida")):
        for x in (21, 22, 33, 34):
            pn.px(x, 23, BLUSH)
        if mood == "corada":
            pn.px(20, 23, BLUSH)
            pn.px(35, 23, BLUSH)
            pn.h(21, 22, 22, BLUSH)
            pn.h(33, 34, 22, BLUSH)
    if mood == "triste":
        pn.px(21, 22, TEAR)
        pn.px(21, 23, TEAR)
        pn.px(20, 24, TEAR)
    elif mood == "chorando":
        for x in (21, 22, 33, 34):
            for y in range(EY + 4, 29):
                pn.px(x, y, TEAR if (x + y) % 3 else (200, 236, 255))
    elif mood == "suor":
        pts = {9: (40, 40), 10: (40, 40), 11: (39, 41), 12: (39, 41), 13: (38, 42), 14: (38, 42), 15: (39, 41)}
        for y, (a, b) in pts.items():
            pn.h(a, b, y, SWEAT)
        pn.px(39, 12, (230, 245, 255))
        pn.px(39, 13, (230, 245, 255))
        pn.h(40, 41, 14, (70, 140, 220))
        pn.px(41, 13, (70, 140, 220))
    elif mood == "bravo":                                     # veia saltada
        red = (220, 60, 60)
        for x, y in ((40, 8), (41, 9), (43, 9), (44, 8), (40, 12), (41, 11), (43, 11), (44, 12)):
            pn.px(x, y, red)
    elif mood == "espirro":
        for x, y in ((32, 28), (34, 30), (33, 32)):
            pn.px(x, y, P.WHITE)
    elif mood == "malicioso":                                 # sombra no alto do rosto
        for x in (20, 24, 31, 35):
            pn.px(x, EY + 4, skin_sh)
    if mood in ("bravo", "determinado", "gritando", "malicioso"):   # sombra entre as sobrancelhas
        pn.px(27, 17, skin_sh)
        pn.px(28, 17, skin_sh)
    if mood in ("cansado", "sonolento"):
        pn.h(21, 23, EY + 4, skin_sh)
        pn.h(32, 34, EY + 4, skin_sh)


def _glasses(pn, cid):
    acc = story.CHARACTERS[cid].get("acc", ())
    if "oculos_redondos" in acc:
        fr = (54, 50, 64)
        for x0 in (19, 30):
            pn.h(x0 + 1, x0 + 5, 17, fr)
            pn.h(x0 + 1, x0 + 5, 23, fr)
            for y in range(18, 23):
                pn.px(x0, y, fr)
                pn.px(x0 + 6, y, fr)
            pn.px(x0 + 1, 18, (210, 236, 255))                   # reflexo da lente
            pn.px(x0 + 5, 22, (150, 180, 210))
        pn.h(26, 29, 18, fr)
        pn.px(18, 18, fr)
        pn.px(17, 18, fr)
        pn.px(37, 18, fr)
        pn.px(38, 18, fr)
    elif "oculos_grandes" in acc:                                 # armacao grossa retangular (Dudu)
        fr, hi = (28, 26, 36), (70, 70, 86)
        for x0 in (18, 30):
            pn.h(x0, x0 + 7, 16, fr)
            pn.h(x0, x0 + 7, 17, fr)
            pn.h(x0 + 1, x0 + 6, 23, fr)
            for y in range(17, 23):
                pn.px(x0, y, fr)
                pn.px(x0 + 7, y, fr)
            pn.h(x0 + 1, x0 + 3, 16, hi)
            pn.px(x0 + 1, 18, (210, 236, 255))
            pn.px(x0 + 2, 18, (210, 236, 255))
            pn.px(x0 + 1, 19, (210, 236, 255))
            pn.px(x0 + 6, 22, (150, 180, 210))
        pn.h(26, 29, 18, fr)
        pn.h(26, 29, 17, fr)


# ================================================================================ ROBOS (pixel)
RW, RH = 46, 30                        # tela logica do robo
R_FLOOR = 27                           # linha logica do chao
R_CX = 23.0


def _robot_map(ch):
    mp = _Map()
    acc = ch.get("acc", ())
    slipper = "chinelo" in acc
    cy0 = R_FLOOR - 4                                              # coordenadas do mapa: y + OY
    # base (saia) e grade
    mp.disc(R_CX, R_FLOOR - 7.2 - OY, 18.0, "rbase", ry=6.0)
    for i in range(5):
        x = int(R_CX - 10.7 + i * 5.3)
        for y in range(R_FLOOR - 7 - OY, R_FLOOR - 4 - OY):
            mp.put(x, y, "rbase", DP)
    mp.bevel(("rbase",), deep=True)
    # tampa
    mp.disc(R_CX, R_FLOOR - 12.0 - OY, 18.0, "lid", ry=6.0)
    mp.bevel(("lid",))
    mp.disc(R_CX, R_FLOOR - 14.6 - OY, 15.0, "lidtop", ry=2.6)
    mp.bevel(("lidtop",), shade=False)
    mp.disc(R_CX, R_FLOOR - 12.7 - OY, 8.0, "visor", ry=4.0)
    mp.bevel(("visor",), lit=False)
    for x in range(int(R_CX) - 5, int(R_CX) - 1):                  # reflexo do visor
        mp.put(x, R_FLOOR - 15 - OY, "visor", HI)
    # rodinhas
    for sx in (-1, 1):
        mp.disc(R_CX + sx * 12.7, R_FLOOR - 1.6 - OY, 2.8, "wheel")
        mp.put(int(R_CX + sx * 12.7), R_FLOOR - 2 - OY, "wheel", HI)
    # antena
    mp.line((R_CX - 5.3, R_FLOOR - 17.5 - OY), (R_CX - 10.5, R_FLOOR - 22.2 - OY), "rbase", HI)
    if slipper:                                                    # chinelo preso por fita
        sx0, sy0 = R_CX + 7.3, R_FLOOR - 18.6 - OY
        mp.disc(sx0, sy0, 6.6, "slip", ry=3.2)
        mp.bevel(("slip",), deep=True)
        mp.disc(sx0, sy0 - 0.6, 3.2, "strap", ry=1.8)
        mp.disc(sx0, sy0 - 0.6, 2.0, "slip", ry=0.9)
        mp.line((sx0 - 8, sy0 - 3.5), (sx0 + 7.5, sy0 + 2.5), "tape")
        mp.line((sx0 - 8, sy0 - 2.5), (sx0 + 7.5, sy0 + 3.5), "tape", SH)
        mp.line((R_CX - 12, R_FLOOR - 11 - OY), (R_CX - 4, R_FLOOR - 17.5 - OY), "tape")
        mp.line((R_CX - 12, R_FLOOR - 10 - OY), (R_CX - 4, R_FLOOR - 16.5 - OY), "tape", SH)
    return mp


def _robot_palette(ch):
    slipper = "chinelo" in ch.get("acc", ())
    body = (150, 160, 175) if slipper else tuple(ch["outfit"][1])
    top = (205, 212, 224) if slipper else P.lighter(tuple(ch["outfit"][1]), 0.25)
    return {"rbase": _ramp((90, 100, 116)), "lid": _mk(body), "lidtop": _mk(top),
            "visor": ((70, 84, 120), (34, 42, 62), (26, 30, 46), (16, 18, 30)),
            "wheel": _ramp((40, 44, 58)), "slip": _ramp((230, 190, 90)), "strap": _ramp((190, 70, 60)),
            "tape": _ramp((200, 200, 205), "white")}


def _robot_face(surf, ch, mood, blink, mouth):
    """LED (olho), aro brilhante da tampa, ponta da antena e ondas de fala no quadro do robo."""
    led = tuple(ch["led"]) if ch.get("led") else P._LED.get(mood, (0, 230, 255))
    lite = P.lighter(led, 0.45)
    cx, cy = int(R_CX), R_FLOOR - 13
    w, h = surf.get_size()

    def px(x, y, c):
        if 0 <= x < w and 0 <= y < h:
            surf.set_at((x, y), c)
    # aro da tampa na cor do LED (pixels da borda de cima/lados da tampa)
    for x in range(int(R_CX - 18), int(R_CX + 18) + 1):
        dx = (x + 0.5 - R_CX) / 18.0
        if abs(dx) <= 1:
            y = int(round(R_FLOOR - 12.0 - 6.0 * math.sqrt(max(0.0, 1 - dx * dx)) - 0.5))
            px(x, y, led)
    for y in range(R_FLOOR - 13, R_FLOOR - 10):
        px(int(R_CX - 18), y, led)
        px(int(R_CX + 17), y, led)
    if blink:
        for x in range(cx - 3, cx + 3):
            px(x, cy, led)
    else:
        r = 3.4 if mouth else 2.8
        for y in range(cy - 4, cy + 5):
            for x in range(cx - 4, cx + 5):
                if (x + 0.5 - (cx + 0.0)) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                    px(x, y, lite if mouth else led)
        px(cx - 1, cy - 1, P.lighter(led, 0.75))
        px(cx, cy - 1, P.lighter(led, 0.6))
    if mouth:                                                      # ondas de som
        for i in range(2):
            x0 = cx + 10 + i * 3
            for dy in range(-2 - i, 3 + i):
                px(x0 + (1 if abs(dy) < 2 + i - 1 else 0), cy - 1 + dy, led)
    px(int(R_CX - 10.5), R_FLOOR - 22, led)                        # ponta da antena
    px(int(R_CX - 11.5), R_FLOOR - 22, led)
    px(int(R_CX - 10.5), R_FLOOR - 23, P.lighter(led, 0.6))
    px(int(R_CX - 11.5), R_FLOOR - 23, led)


# ================================================================================ CACHE / DESENHO
_BASES = {}                         # (cid, camada) -> Surface logica k=1 sem rosto (camada "legs" com contorno)
_TOP = {}                           # cid -> primeira linha logica com pixel (para o enquadramento do busto)
_GROUPS = OrderedDict()             # (cid, mood, kq) -> [4 quadros]  (indice = blink*2 + mouth)
_LEGS = OrderedDict()               # (cid, kq) -> Surface
_SCRATCH = OrderedDict()            # (w, h) -> Surface de rascunho para a ampliacao
STATS = {"built_frames": 0, "build_ms": 0.0, "bases": 0}


def _outline(surf, k=1.0):
    m = pygame.mask.from_surface(surf, 1)
    o = pygame.mask.Mask(m.get_size())
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o.draw(m, d)
    o.erase(m, (0, 0))
    o.to_surface(surf, setcolor=P.shade(OUT, k) + (255,), unsetcolor=None)


def _dim(src, kq):
    """Copia esmaecida (k < 1): c*k + SHADE_BASE*(1-k), igual a P.shade, so com 2 fills."""
    s = src.copy()
    if kq < 0.999:
        f = int(round(kq * 255))
        s.fill((f, f, f), special_flags=pygame.BLEND_RGB_MULT)
        b = P.SHADE_BASE
        s.fill(tuple(int(round(v * (1.0 - kq))) for v in b), special_flags=pygame.BLEND_RGB_ADD)
    return s


def _base(cid, layer):
    key = (cid, layer)
    s = _BASES.get(key)
    if s is None:
        t0 = time.perf_counter()
        if is_robot(cid):
            ch = story.CHARACTERS[cid]
            s = pygame.Surface((RW, RH), pygame.SRCALPHA)
            _robot_map(ch).render(_robot_palette(ch), 1.0, s)
            _BASES[key] = s
            _TOP[cid] = 0
        else:
            legs, up = _build_maps(cid)
            pal = _palette(cid)
            for lay, mp in (("legs", legs), ("up", up)):
                sf = pygame.Surface((CW, CH), pygame.SRCALPHA)
                mp.render(pal, 1.0, sf)
                if lay == "legs":
                    _outline(sf)
                _BASES[(cid, lay)] = sf
            _TOP[cid] = _BASES[(cid, "up")].get_bounding_rect().top
            s = _BASES[key]
        STATS["bases"] += 1
        STATS["build_ms"] += (time.perf_counter() - t0) * 1000
    return s


def _group(cid, mood, kq):
    key = (cid, mood, kq)
    g = _GROUPS.get(key)
    if g is not None:
        _GROUPS.move_to_end(key)
        return g
    t0 = time.perf_counter()
    if kq < 0.999:
        g = [_dim(s, kq) for s in _group(cid, mood, 1.0)]
    else:
        robot = is_robot(cid)
        base = _base(cid, "up")
        ch = story.CHARACTERS[cid]
        pal = None if robot else _palette(cid)
        g = []
        for blink in (0, 1):
            for mouth in (0, 1):
                s = base.copy()
                if robot:
                    _robot_face(s, ch, mood, bool(blink), mouth)
                else:
                    pn = _Painter(s, pal, 1.0)
                    _paint_face(pn, cid, mood, bool(blink), mouth)
                    _glasses(pn, cid)
                _outline(s)
                g.append(s)
    _GROUPS[key] = g
    while len(_GROUPS) > PX_CACHE_MAX:
        _GROUPS.popitem(last=False)
    STATS["built_frames"] += 4
    STATS["build_ms"] += (time.perf_counter() - t0) * 1000
    return g


def _legs_surf(cid, kq):
    key = (cid, kq)
    s = _LEGS.get(key)
    if s is None:
        s = _LEGS[key] = _dim(_base(cid, "legs"), kq)
        while len(_LEGS) > LEGS_CACHE_MAX:
            _LEGS.popitem(last=False)
    else:
        _LEGS.move_to_end(key)
    return s


def _scale_factor(R, bust):
    s = R / 10.0 if bust else R * 3.0 / 40.0
    r = round(s)
    return float(r) if r >= 1 and abs(s - r) < 0.35 else s


def _blit_scaled(scr, src, x, y, sc):
    sw, sh = src.get_size()
    w, h = int(round(sw * sc)), int(round(sh * sc))
    dst = _SCRATCH.get((w, h))
    if dst is None:
        dst = _SCRATCH[(w, h)] = pygame.Surface((w, h), pygame.SRCALPHA)
        while len(_SCRATCH) > SCRATCH_MAX:
            _SCRATCH.popitem(last=False)
    pygame.transform.scale(src, (w, h), dst)
    scr.blit(dst, (int(round(x)), int(round(y))))


def warm(cid, moods=("neutro",), ks=(1.0,)):
    """Pre-monta os quadros (fora do draw) - opcional; o draw monta sob demanda."""
    if not (supports(cid) or is_robot(cid)):
        return
    for kq in ks:
        kq = round(max(0.0, min(1.0, kq)), 2)
        if not is_robot(cid):
            _legs_surf(cid, kq)
        for m in moods:
            _group(cid, m if m in story.MOODS else "neutro", kq)


def draw(scr, cid, mood, cx, feet_y, R, k, bob, bust, blink, mouth, t, breath):
    kq = round(max(0.0, min(1.0, k)), 2)
    if mood not in story.MOODS:
        mood = "neutro"
    frames = _group(cid, mood, kq)
    sc = _scale_factor(R, bust)
    img = frames[(1 if blink else 0) * 2 + (1 if mouth else 0)]
    if bust:
        x0 = cx - HEAD_C[0] * sc
        y0 = feet_y + bob - HEAD_C[1] * sc - BUST_LIFT * R
        top = feet_y - int(R * 1.9) + 3 + BUST_MARGIN               # topo util do busto (draw_bust)
        y0 = max(y0, top - _TOP.get(cid, 0) * sc)                  # cabelo alto: desce ate caber
        _blit_scaled(scr, img, x0, y0, sc)
    else:
        legs = _legs_surf(cid, kq)
        x0 = cx - ORIGIN_X * sc
        y0 = feet_y + bob - FEET_Y * sc
        _blit_scaled(scr, legs, x0, y0, sc)
        _blit_scaled(scr, img, x0, y0 + breath * sc, sc)
        y0 += breath * sc
    hx = x0 + HEAD_C[0] * sc
    hy = y0 + HEAD_C[1] * sc
    rr = 11 * sc
    if mood == "chorando":
        for i, x in enumerate((21.5, 33.5)):
            dy = ((t * 1.6 + i * 0.5) % 1.0) * 4
            pygame.draw.rect(scr, P.shade(TEAR, k), (int(x0 + x * sc), int(y0 + (OY + 29 + dy) * sc), int(sc), int(sc)))
    if mood == "pensando":                                  # baloes de pensamento (pixelados)
        for dx, dy, r in ((1.05, -0.35, 1), (1.3, -0.75, 1.5), (1.45, -1.3, 2.5)):
            x, y, w = int(hx + dx * rr), int(hy + dy * rr), int(r * 2 * sc)
            pygame.draw.rect(scr, P.shade(OUT, k), (x - int(sc), y - int(sc), w + 2 * int(sc), w + 2 * int(sc)))
            pygame.draw.rect(scr, P.shade(P.WHITE, k), (x, y, w, w))
    P._mood_decor(scr, mood, hx, hy, rr, k, t)


def draw_robot(scr, cid, mood, cx, base_y, R, k, bob, blink, mouth, t):
    """Robo-aspirador em pixel art (mesma ancora do classico: base_y = chao)."""
    kq = round(max(0.0, min(1.0, k)), 2)
    if mood not in story.MOODS:
        mood = "robo"
    frames = _group(cid, mood, kq)
    sc = _scale_factor(R, False)
    img = frames[(1 if blink else 0) * 2 + (1 if mouth else 0)]
    y = base_y + bob
    pygame.draw.ellipse(scr, P.shade((10, 14, 26), k), (int(cx - 1.62 * R), int(y - 0.18 * R), int(3.24 * R), int(0.3 * R)))
    x0 = cx - R_CX * sc
    y0 = y - R_FLOOR * sc
    _blit_scaled(scr, img, x0, y0, sc)
    if mood == "chorando":
        for i, sx in enumerate((-1, 1)):
            dy = ((t * 1.6 + i * 0.5) % 1.0) * 0.5 * R
            pygame.draw.rect(scr, P.shade(TEAR, k), (int(cx + sx * 0.5 * R), int(y - 0.7 * R + dy), int(sc), int(sc * 2)))
    elif mood == "bravo":
        red = P.shade((220, 60, 60), k)
        for i in range(4):
            pygame.draw.rect(scr, red, (int(cx + 0.9 * R + i * sc), int(y - 2.0 * R + i * sc), int(sc), int(sc)))
            pygame.draw.rect(scr, red, (int(cx + 0.9 * R + (3 - i) * sc), int(y - 2.0 * R + i * sc), int(sc), int(sc)))
    P._mood_decor(scr, mood, cx, y - 1.5 * R, R * 0.85, k, t)


def cache_bytes():
    n = sum(s.get_width() * s.get_height() * 4 for g in _GROUPS.values() for s in g)
    n += sum(s.get_width() * s.get_height() * 4 for s in _BASES.values())
    n += sum(s.get_width() * s.get_height() * 4 for s in _LEGS.values())
    n += sum(s.get_width() * s.get_height() * 4 for s in _SCRATCH.values())
    return n


def clear_cache():
    _BASES.clear()
    _TOP.clear()
    _GROUPS.clear()
    _LEGS.clear()
    _SCRATCH.clear()
