# -*- coding: utf-8 -*-
"""Personagens da Campanha em PIXEL ART (prototipo; ligado por portraits.STYLE = "pixel").

Tecnica
- Cada personagem e pintado em resolucao LOGICA baixa (CW x CH px, ~1/3 do palco) num "mapa de
  materiais": cada pixel guarda (material, tom) com 4 tons por material (luz, base, sombra, sombra
  profunda; rampa com desvio de matiz: luz puxa para o quente, sombra para o roxo). Um passe de
  "bevel" automatico acende as bordas de cima/esquerda e sombreia as de baixo/direita; detalhes
  (mechas, dobras, costuras, ziper, botoes, trico) sao pintados a mao por cima.
- Duas camadas: PERNAS (estatica) e CORPO (tronco, bracos, cabeca, rosto). O corpo e montado por
  quadro de animacao (piscar x boca) e humor; o contorno escuro de 1 px logico sai de uma mascara.
- Cache em 2 niveis: base sem rosto por (personagem, k) e quadros prontos por (personagem, humor,
  k) com os 4 quadros (LRU de PX_CACHE_MAX grupos; ~16 KB por quadro). Nada de Surface por quadro:
  a ampliacao (vizinho mais proximo) e feita com pygame.transform.scale(..., dest) numa Surface de
  rascunho por tamanho, criada no aquecimento.
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
BUST_LIFT = -0.12                      # sobe a cabeca no busto (mostra ombros)
PX_CACHE_MAX = 48                      # grupos (personagem, humor, k) com 4 quadros cada

OUT = (26, 18, 30)                     # contorno
EYE = (34, 24, 30)
SCLERA = (244, 242, 236)
LIP = (150, 70, 72)
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


def _head(mp):
    mp.rows(HEAD, "skin")
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
    mp.hline(23, 32, 30, "skin", SH)
    mp.hline(24, 31, 31, "skin", DP)
    mp.put(34, 28, "skin", DP)
    mp.put(35, 27, "skin", DP)
    mp.put(36, 26, "skin", DP)
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
    mp.rect(24, 30, 8, 5, "skin")
    mp.hline(24, 31, 31, "skin", DP)
    mp.hline(24, 31, 32, "skin", SH)
    for y in range(30, 35):
        mp.put(31, y, "skin", DP)
        mp.put(30, y, "skin", SH)


def _arms(mp, mat="top", cuff_mat=None, cuff_rows=(55, 58), hands=True):
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
        _hands(mp, cuff_rows[1] + 1)


def _hands(mp, y0):
    for sx in (-1, 1):
        xs = range(9, 14) if sx < 0 else range(42, 47)
        x0, x1 = xs[0], xs[-1]
        mp.hline(x0, x1, y0, "skin", SH)
        for y in range(y0 + 1, y0 + 5):
            mp.hline(x0, x1, y, "skin")
        mp.hline(x0 + 1, x1 - 1, y0 + 5, "skin")
        # polegar para dentro, dedos marcados
        tx = x1 + 1 if sx < 0 else x0 - 1
        mp.put(tx, y0 + 1, "skin", BASE)
        mp.put(tx, y0 + 2, "skin", SH)
        for y in range(y0 + 1, y0 + 5):
            mp.put(x0, y, "skin", HI if sx < 0 else SH)
            mp.put(x1, y, "skin", SH if sx < 0 else DP)
        mp.put(x0 + 2, y0 + 4, "skin", SH)
        mp.put(x0 + 2, y0 + 5, "skin", SH)
        mp.put(x0 + 1, y0 + 2, "skin", HI)


def _legs(mp, pants="pants", shoe="shoe", sole="sole", suit=False):
    mp.rect(16, 60, 24, 4, pants)
    for y in range(64, 91):
        mp.hline(16, 26, y, pants)
        mp.hline(29, 39, y, pants)
    mp.hline(27, 28, 64, pants, SH)
    for y in range(60, 91):                                        # volume
        mp.put(16, y, pants, HI)
        mp.put(17, y, pants, HI if y % 7 else BASE)
        mp.put(26, y, pants, SH)
        mp.put(29, y, pants, SH)
        mp.put(38, y, pants, SH)
        mp.put(39, y, pants, DP)
    for y in range(60, 64):
        mp.put(27, y, pants, SH)
        mp.put(28, y, pants, SH)
    if suit:                                                       # vinco da calca social
        for y in range(66, 89):
            mp.put(21, y, pants, HI)
            mp.put(34, y, pants, HI)
    else:                                                          # costura + dobras (jeans)
        for y in range(66, 90, 1):
            mp.put(18 if y < 80 else 18, y, pants, BASE)
        for x, y in ((19, 74), (20, 75), (22, 74), (33, 76), (34, 77), (36, 76), (20, 86), (21, 87), (35, 86), (34, 87)):
            mp.put(x, y, pants, SH)
        mp.hline(16, 26, 89, pants, SH)
        mp.hline(29, 39, 89, pants, SH)
    mp.hline(16, 26, 90, pants, DP)
    mp.hline(29, 39, 90, pants, DP)
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


def _hair_espetado(mp):
    dome = [(17, 21), (16, 12), (19, 7), (24, 5), (32, 5), (37, 7), (40, 12), (39, 21), (37.4, 21),
            (37.2, 15), (35, 14), (33.5, 16.5), (31, 13), (29, 16), (26.5, 13), (24.5, 16.5), (22.5, 13.5),
            (20.5, 16.5), (18.8, 15), (18.6, 21)]
    mp.poly(dome, "hair")
    spikes = (((15.5, 15), (19, 9), (9.5, 8.5)), ((17.5, 10), (23, 6.5), (14, -0.5)),
              ((21.5, 7), (28.5, 5.5), (23.5, -4.5)), ((27, 5.5), (34, 7), (33.5, -3.5)),
              ((32, 6.5), (38.5, 10), (42, -0.5)), ((37, 9), (40.5, 15.5), (46, 7.5)))
    for b0, b1, tip in spikes:
        _spike(mp, b0, b1, tip)
    mp.bevel(("hair",), deep=True)
    # sombra profunda na raiz das mechas e na franja; brilho em faixa na copa
    for x, y in ((19, 10), (20, 9), (24, 7), (25, 7), (30, 7), (31, 7), (35, 9), (36, 10), (18, 12), (38, 13)):
        mp.tone(x, y, SH, ("hair",))
    for x, y in ((21, 9), (22, 8), (23, 8), (26, 6), (27, 6), (28, 7), (32, 8), (33, 8), (29, 9), (34, 9)):
        mp.tone(x, y, HI, ("hair",))
    for x in range(19, 38):                                        # sombra da franja na testa
        for y in range(13, 18):
            if mp.mat(x, y) == "skin" and mp.mat(x, y - 1) == "hair":
                mp.tone(x, y, SH, ("skin",))
    for y in range(16, 22):                                        # costeletas
        mp.tone(18, y, DP, ("hair",))
        mp.tone(37, y, DP, ("hair",))


def _hair_calvo(mp):
    # tampo careca com brilho e laterais grisalhas fofas sobre as orelhas
    mp.hline(22, 25, 9, "skin", HI)
    mp.hline(21, 23, 10, "skin", HI)
    mp.put(23, 10, "skin", (HI))
    mp.color(23, 9, (255, 250, 236))
    mp.color(24, 9, (255, 250, 236))
    for sx in (-1, 1):
        spans = {12: (17, 18), 13: (16, 19), 14: (15, 19), 15: (15, 19), 16: (15, 18), 17: (15, 17),
                 18: (15, 16), 19: (15, 16), 20: (15, 16), 21: (16, 16)}
        for y, (a, b) in spans.items():
            if sx > 0:
                a, b = 55 - b, 55 - a
            mp.hline(a, b, y, "hair")
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
    for x in range(19, 38):
        for y in range(12, 15):
            if mp.mat(x, y) == "skin" and mp.mat(x, y - 1) == "hair":
                mp.tone(x, y, SH, ("skin",))


# ================================================================================ ROUPAS
def _torso_spans(bottom=61, waist=50):
    s = {33: (19, 36), 34: (15, 40)}
    for y in range(35, bottom + 1):
        s[y] = (14, 41) if y < waist else (15, 40)
    return s


def _moletom(mp):
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
    _arms(mp, "top", "shirt", (57, 58))
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


# ================================================================================ PERSONAGENS
SPECS = {
    "teo": {"hair": _hair_espetado, "outfit": "moletom", "pants": (52, 66, 104), "shoe": (60, 56, 70),
            "sole": (236, 232, 226), "suit": False, "cord": (238, 230, 220), "eye": (70, 46, 34)},
    "ambrosio": {"hair": _hair_calvo, "outfit": "jaleco", "pants": (52, 54, 66), "shoe": (40, 34, 38),
                 "sole": (24, 20, 24), "suit": False, "shirt": (176, 206, 236), "tie": (150, 50, 60),
                 "button": (200, 200, 210), "eye": (70, 60, 50)},
    "gervasio": {"hair": _hair_raspado, "outfit": "terno", "shoe": (92, 52, 34), "sole": (40, 26, 22),
                 "suit": True, "shirt": (244, 244, 248), "tie": (0, 176, 210), "button": (40, 30, 26),
                 "eye": (64, 42, 30)},
}


def supports(cid):
    return cid in SPECS and cid in story.CHARACTERS


def _palette(cid):
    ch = story.CHARACTERS[cid]
    sp = SPECS[cid]
    top = tuple(ch["outfit"][1])
    hair = tuple(ch["hair"][1])
    if cid == "teo":
        hair = (96, 62, 40)                         # base mais clara: as pontas ganham luz (cor original vira sombra)
    pal = {"skin": _ramp(ch["skin"], "skin"), "hair": _ramp(hair, "white" if hair[0] > 150 else "std"),
           "top": _ramp(top, "white" if min(top) > 200 else "std"),
           "pants": _ramp(sp.get("pants", top)), "shoe": _ramp(sp["shoe"]), "sole": _ramp(sp["sole"]),
           "cord": _ramp(sp.get("cord", (230, 230, 230)), "white"),
           "shirt": _ramp(sp.get("shirt", (240, 240, 245)), "white"), "tie": _ramp(sp.get("tie", (0, 176, 210))),
           "button": _ramp(sp.get("button", (40, 40, 40))),
           "pen1": _ramp((60, 120, 240)), "pen2": _ramp((230, 70, 70)), "pen3": _ramp((60, 200, 110)),
           "mus": (_ramp((176, 176, 182), "white") if ch["hair"][0] == "calvo" else _ramp(P.darker(hair, 0.8))),
           "glass": _ramp((70, 66, 80))}
    if cid == "teo":
        pal["hair"] = ((168, 112, 70), (104, 66, 42), (64, 40, 30), (40, 24, 22))
    return pal


_MAPS = {}


def _maps(cid):
    got = _MAPS.get(cid)
    if got:
        return got
    sp = SPECS[cid]
    acc = story.CHARACTERS[cid].get("acc", ())
    legs = _Map()
    _legs(legs, suit=sp["suit"], pants="top" if sp["suit"] else "pants")
    legs.cut_rows(*LEG_CUT)
    up = _Map()
    kind = sp["outfit"]
    if kind == "moletom":
        _moletom(up)
    elif kind == "jaleco":
        _jaleco(up, acc)
    else:
        _terno(up, acc)
    _head(up)
    sp["hair"](up)
    if "bigode" in acc:
        _mustache(up)
    _MAPS[cid] = (legs, up)
    return _MAPS[cid]


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


# ================================================================================ ROSTO POR HUMOR
# sobrancelhas: (y externo, y interno) em px (negativo = sobe), por lado (esq, dir)
_BROWS = {"neutro": (0, 0, 0, 0), "feliz": (-1, -1, -1, -1), "euforico": (-2, -2, -2, -2), "susto": (-2, -3, -2, -3),
          "maravilhado": (-2, -3, -2, -3), "triste": (1, -1, 1, -1), "chorando": (1, -2, 1, -2), "bravo": (-1, 2, -1, 2),
          "convencida": (0, 0, -1, -1), "convencido": (0, 0, -1, -1), "corada": (0, -1, 0, -1), "suor": (1, -1, 1, -1),
          "espirro": (1, 0, 1, 0), "calmo": (0, 0, 0, 0), "sonolento": (1, 1, 1, 1), "cansado": (1, 1, 1, 1),
          "piscando": (1, 1, -1, -1), "malicioso": (-1, 1, -2, -1), "pensando": (0, 0, -2, -1),
          "determinado": (0, 1, 0, 1), "gritando": (-1, 2, -1, 2), "robo": (0, 0, 0, 0)}
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
    pn.px(ix, y + 1 + ly, EYE)
    pn.px(ix + 1, y + 1 + ly, EYE)
    pn.px(ix, y + 2 + ly, eye)
    pn.px(ix + 1, y + 2 + ly, eye)
    pn.px(ix, y + 1 + ly, (255, 255, 255))                  # brilho
    if big:
        pn.h(x, x + 2, y + 3, SCLERA)
        pn.px(x - 1, y + 1, EYE) if x < 28 else pn.px(x + 3, y + 1, EYE)


def _brows(pn, mood, hair):
    lo, li, ro, ri = _BROWS.get(mood, (0, 0, 0, 0))
    thick = mood in ("bravo", "determinado", "gritando")
    for side, xs, o, i_ in ((0, range(20, 25), lo, li), (1, range(35, 30, -1), ro, ri)):
        for j, x in enumerate(xs):                         # j: 0 = ponta externa .. 4 = ponta interna
            y = 16 + int(round(o + (i_ - o) * j / 4.0))
            pn.px(x, y, hair)
            if thick and j >= 2:
                pn.px(x, y - 1, hair)


def _paint_face(pn, cid, mood, blink, mouth):
    sp = SPECS[cid]
    eye = sp["eye"]
    pal = pn.pal
    hair_dark = pal["hair"][DP] if story.CHARACTERS[cid]["hair"][0] != "calvo" else pal["hair"][SH]
    skin_sh, skin_dp, skin_hi = pn.skin(SH), pn.skin(DP), pn.skin(HI)
    L, Rr, EY = 21, 32, 18                                   # colunas dos olhos e linha da palpebra
    _brows(pn, mood, hair_dark)
    closed = blink and mood not in _SHUT

    def happy(x):                                         # ^  (olho fechado sorrindo)
        pn.h(x, x + 2, EY + 1, EYE)
        pn.px(x - 1 if x < 28 else x + 3, EY + 2, EYE)
        pn.px(x + 3 if x < 28 else x - 1, EY + 2, skin_sh)

    def shut(x, down=True):                               # -  (olho fechado/sonolento)
        pn.h(x, x + 2, EY + 2, EYE)
        pn.px(x - 1 if x < 28 else x + 3, EY + (1 if down else 3), EYE)
        pn.h(x, x + 2, EY + 3, skin_sh)

    # ---- olhos
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
    elif mood == "piscando":
        happy(L)
        _eye_open(pn, Rr, EY, eye)
    elif mood in ("bravo", "determinado", "convencida", "convencido", "malicioso", "cansado"):
        for x in (L, Rr):
            _eye_open(pn, x, EY, eye)
            pn.h(x, x + 2, EY + 1, EYE if mood != "determinado" else EYE)
            if mood == "bravo":                             # palpebra inclinada para dentro
                pn.px(x + 2 if x < 28 else x, EY + 2, EYE)
            if mood == "cansado":
                pn.h(x, x + 2, EY + 3, skin_dp)
        if mood == "malicioso":
            pn.h(Rr, Rr + 2, EY + 2, EYE)
    elif mood == "pensando":
        _eye_open(pn, L, EY, eye, (1, 0))
        _eye_open(pn, Rr, EY, eye, (1, 0))
        pn.px(L + 2, EY + 1, EYE)
        pn.px(Rr + 2, EY + 1, EYE)
    elif mood == "triste":
        _eye_open(pn, L, EY, eye, (0, 0))
        _eye_open(pn, Rr, EY, eye, (0, 0))
        pn.px(L + 2, EY, skin_sh)
        pn.px(Rr, EY, skin_sh)
    else:                                                  # neutro, suor, corada, robo
        _eye_open(pn, L, EY, eye)
        _eye_open(pn, Rr, EY, eye)

    # ---- boca (linha 26; o bigode cobre 23-25)
    my = 26
    lip = LIP
    if mouth:
        sc = P._TALK_SCALE.get(mood, 0.9)
        w = 2 if sc < 0.8 else (3 if sc < 1.2 else 4)
        hgt = 2 if sc < 0.8 else (3 if sc < 1.2 else 4)
        x0, x1 = 28 - w, 27 + w
        for y in range(my - 1, my - 1 + hgt):
            inset = 1 if (y == my - 1 or y == my - 2 + hgt) and w > 2 else 0
            pn.h(x0 + inset, x1 - inset, y, MOUTH_IN)
        if mood in ("feliz", "euforico", "determinado", "gritando", "bravo") or w >= 3:
            pn.h(x0 + 1, x1 - 1, my - 1, TEETH)
        if hgt >= 3:
            pn.h(x0 + 2, x1 - 2, my - 2 + hgt, TONGUE)
        pn.h(x0 + 1, x1 - 1, my - 1 + hgt, skin_sh)
    elif mood == "feliz":
        pn.h(25, 30, my - 1, MOUTH_IN)
        pn.h(26, 29, my - 1, TEETH)
        pn.h(26, 29, my, MOUTH_IN)
        pn.px(24, my - 2, lip)
        pn.px(31, my - 2, lip)
        pn.h(26, 29, my + 1, skin_sh)
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
    elif mood == "determinado":
        pn.h(25, 30, my - 1, EYE)
        pn.h(25, 30, my, TEETH)
        pn.h(25, 30, my + 1, EYE)
        pn.px(27, my, (200, 196, 200))
    elif mood == "gritando":
        for y in range(my - 2, my + 3):
            pn.h(24 if my - 1 <= y <= my + 1 else 25, 31 if my - 1 <= y <= my + 1 else 30, y, MOUTH_IN)
        pn.h(25, 30, my - 2, TEETH)
        pn.h(26, 29, my + 2, TONGUE)
    elif mood == "pensando":
        pn.h(27, 30, my, lip)
        pn.px(31, my - 1, lip)
    elif mood in ("convencida", "convencido", "malicioso"):
        pn.h(25, 29, my, lip)
        pn.px(30, my - 1, lip)
        pn.px(31, my - 2, lip)
        if mood == "malicioso":
            pn.px(29, my + 1, TEETH)
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
    if not mouth and mood not in ("gritando", "euforico", "susto", "maravilhado"):
        pn.h(27, 28, my + 1, skin_sh)                       # labio inferior

    # ---- extras
    if mood in ("corada", "euforico", "piscando"):
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
    if mood in ("bravo", "determinado", "gritando"):         # sombra entre as sobrancelhas
        pn.px(27, 17, skin_sh)
        pn.px(28, 17, skin_sh)
    if mood in ("cansado", "sonolento"):
        pn.h(21, 23, EY + 4, skin_sh)
        pn.h(32, 34, EY + 4, skin_sh)


def _glasses(pn, cid):
    if "oculos_redondos" not in story.CHARACTERS[cid].get("acc", ()):
        return
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


# ================================================================================ CACHE / DESENHO
_BASES = {}                         # (cid, kq, camada) -> Surface logica sem rosto/sem contorno
_GROUPS = OrderedDict()             # (cid, mood, kq) -> [4 quadros]  (indice = blink*2 + mouth)
_LEGS = {}                          # (cid, kq) -> Surface
_SCRATCH = {}                       # (w, h) -> Surface de rascunho para a ampliacao
STATS = {"built_frames": 0, "build_ms": 0.0}


def _outline(surf, k):
    m = pygame.mask.from_surface(surf, 1)
    o = pygame.mask.Mask(m.get_size())
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o.draw(m, d)
    o.erase(m, (0, 0))
    o.to_surface(surf, setcolor=P.shade(OUT, k) + (255,), unsetcolor=None)


def _base(cid, kq, layer):
    key = (cid, kq, layer)
    s = _BASES.get(key)
    if s is None:
        legs, up = _maps(cid)
        s = pygame.Surface((CW, CH), pygame.SRCALPHA)
        (legs if layer == "legs" else up).render(_palette(cid), kq, s)
        if layer == "legs":
            _outline(s, kq)
        _BASES[key] = s
    return s


def _group(cid, mood, kq):
    key = (cid, mood, kq)
    g = _GROUPS.get(key)
    if g is not None:
        _GROUPS.move_to_end(key)
        return g
    t0 = time.perf_counter()
    base = _base(cid, kq, "up")
    pal = {m: tuple(P.shade(c, 1.0) for c in tones) for m, tones in _palette(cid).items()}
    g = []
    for blink in (0, 1):
        for mouth in (0, 1):
            s = base.copy()
            pn = _Painter(s, pal, kq)
            _paint_face(pn, cid, mood, bool(blink), mouth)
            _glasses(pn, cid)
            _outline(s, kq)
            g.append(s)
    _GROUPS[key] = g
    while len(_GROUPS) > PX_CACHE_MAX:
        _GROUPS.popitem(last=False)
    STATS["built_frames"] += 4
    STATS["build_ms"] += (time.perf_counter() - t0) * 1000
    return g


def _scale_factor(R, bust):
    s = R / 10.0 if bust else R * 3.0 / 40.0
    r = round(s)
    return float(r) if r >= 1 and abs(s - r) < 0.35 else s


def _blit_scaled(scr, src, x, y, sc):
    w, h = int(round(CW * sc)), int(round(CH * sc))
    dst = _SCRATCH.get((w, h))
    if dst is None:
        dst = _SCRATCH[(w, h)] = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.transform.scale(src, (w, h), dst)
    scr.blit(dst, (int(round(x)), int(round(y))))


def warm(cid, moods=("neutro",), ks=(1.0,)):
    """Pre-monta os quadros (fora do draw) - opcional; o draw monta sob demanda."""
    if not supports(cid):
        return
    for kq in ks:
        _LEGS.setdefault((cid, round(kq, 2)), _base(cid, round(kq, 2), "legs"))
        for m in moods:
            _group(cid, m, round(kq, 2))


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
        _blit_scaled(scr, img, x0, y0, sc)
    else:
        legs = _LEGS.get((cid, kq))
        if legs is None:
            legs = _LEGS[(cid, kq)] = _base(cid, kq, "legs")
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


def cache_bytes():
    n = sum(s.get_width() * s.get_height() * 4 for g in _GROUPS.values() for s in g)
    n += sum(s.get_width() * s.get_height() * 4 for s in _BASES.values())
    n += sum(s.get_width() * s.get_height() * 4 for s in _SCRATCH.values())
    return n


def clear_cache():
    _BASES.clear()
    _GROUPS.clear()
    _LEGS.clear()
    _SCRATCH.clear()
