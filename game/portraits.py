# -*- coding: utf-8 -*-
"""Desenho por codigo dos CENARIOS e RETRATOS da Campanha (passo 9). Modulo de desenho PURO
(so pygame.draw; nenhuma imagem externa; nenhuma Surface por quadro).

- Cenarios: draw_background() pinta um cenario inteiro numa Surface; get_background(bg) cria UMA
  Surface por cenario na primeira vez (convert() depois do set_mode) e a reaproveita (estatica).
- Personagens: draw_character() (corpo inteiro, no palco) e draw_bust() (retrato da caixa de
  dialogo, recortado com set_clip). Os humores mudam sobrancelhas/olhos/boca. `k` (0..1) escurece
  todas as cores (personagens "esmaecidos") misturando com o fundo, sem alpha nem Surface.
- "ze" (Ze Poeira) vira um robo-aspirador (disco com LED); "narrador" vira moldura/icone de narracao.
Dados vem de story.CHARACTERS / HAIR_STYLES / ACCESSORIES / OUTFITS / MOODS / BGS.
"""
import math
import random

import pygame

import story

STAGE_W, STAGE_H = 1100, 478          # area do palco (acima da caixa de dialogo)
NEON = (0, 230, 255)
GOLD = (255, 214, 90)
INK = (30, 24, 40)
SHADE_BASE = (10, 16, 30)
PANTS = (28, 36, 64)


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


# ================================================================================ CENARIOS
def _vgrad(s, rect, c1, c2):
    x, y, w, h = rect
    for i in range(h):
        pygame.draw.line(s, lerp(c1, c2, i / max(1, h - 1)), (x, y + i), (x + w - 1, y + i))


def _glow(s, center, r, col, base, steps=7):
    """Brilho redondo por circulos concentricos opacos (sem alpha)."""
    for i in range(steps):
        t = i / (steps - 1.0)
        pygame.draw.circle(s, lerp(base, col, t * t), center, int(r * (1 - t * 0.85)))


def _bleachers(s, x0, x1, y0, rows, row_h, c1, c2, crowd=0, rng=None):
    for i in range(rows):
        y = y0 + i * row_h
        pygame.draw.rect(s, lerp(c1, c2, i / max(1, rows - 1)), (x0, y, x1 - x0, row_h))
        pygame.draw.line(s, lighter(c1, 0.1), (x0, y), (x1, y))
        if crowd and rng is not None:
            for x in range(x0 + 8, x1 - 6, 17):
                col = rng.choice(((200, 90, 90), (90, 150, 230), (230, 200, 120), (120, 220, 160), (180, 120, 220)))
                pygame.draw.circle(s, darker(col, 0.55), (x + rng.randint(-3, 3), y + 5), 5)


def _bg_garagem(s):
    _vgrad(s, (0, 0, 1100, 360), (14, 22, 40), (22, 34, 58))
    _vgrad(s, (0, 360, 1100, 118), (34, 40, 58), (18, 22, 34))
    pygame.draw.line(s, NEON, (0, 360), (1100, 360), 2)
    pygame.draw.rect(s, (28, 42, 68), (330, 70, 430, 290))                         # portao
    for y in range(70, 360, 36):
        pygame.draw.line(s, (16, 26, 44), (330, y), (760, y), 3)
        pygame.draw.line(s, (50, 72, 104), (330, y + 3), (760, y + 3), 1)
    pygame.draw.rect(s, (60, 110, 150), (330, 70, 430, 290), 4)
    pygame.draw.rect(s, GOLD, (530, 330, 30, 8), border_radius=3)
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
    for i, y in enumerate((150, 232, 314)):                                          # estantes e caixas
        pygame.draw.rect(s, (70, 90, 120), (800, y + 28, 270, 8))
        for j in range(3):
            w = 56 + (i * 13 + j * 17) % 30
            h = 34 + (i * 7 + j * 11) % 18
            x = 812 + j * 82
            col = lerp((90, 70, 50), (60, 90, 110), ((i + j) % 3) / 2.0)
            pygame.draw.rect(s, col, (x, y + 28 - h, w, h))
            pygame.draw.line(s, lighter(col, 0.3), (x + w // 2, y + 28 - h), (x + w // 2, y + 28), 3)
    pygame.draw.line(s, (80, 90, 110), (550, 0), (550, 36), 3)                      # lampada
    pygame.draw.polygon(s, (70, 90, 120), [(520, 56), (580, 56), (566, 36), (534, 36)])
    _glow(s, (550, 66), 70, (180, 220, 255), (22, 34, 58))
    pygame.draw.ellipse(s, (14, 18, 28), (380, 410, 190, 40))                      # mancha de oleo
    pygame.draw.ellipse(s, (22, 28, 44), (400, 418, 120, 22))


def _bg_oficina(s):
    _vgrad(s, (0, 0, 1100, 330, ), (12, 26, 44), (20, 40, 64))
    _vgrad(s, (0, 330, 1100, 148), (28, 38, 56), (14, 20, 32))
    pygame.draw.line(s, NEON, (0, 330), (1100, 330), 2)
    for x in (110, 420, 730):                                                       # janelas
        pygame.draw.rect(s, (60, 120, 170), (x, 50, 240, 120))
        _vgrad(s, (x + 6, 56, 228, 108), (110, 180, 230), (160, 220, 245))
        pygame.draw.line(s, (20, 40, 64), (x + 120, 56), (x + 120, 164), 5)
        pygame.draw.line(s, (20, 40, 64), (x + 6, 110), (x + 234, 110), 5)
        pygame.draw.rect(s, (70, 110, 150), (x, 50, 240, 120), 4)
    for cx, cy, r in ((70, 250, 34), (1030, 230, 44)):                              # engrenagens
        pygame.draw.circle(s, (40, 66, 98), (cx, cy), r)
        for a in range(0, 360, 30):
            x = cx + int((r + 6) * math.cos(math.radians(a)))
            y = cy + int((r + 6) * math.sin(math.radians(a)))
            pygame.draw.circle(s, (40, 66, 98), (x, y), 7)
        pygame.draw.circle(s, (14, 26, 44), (cx, cy), r // 2)
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
    pygame.draw.circle(s, (255, 150, 60), (805, 266), 5)
    pygame.draw.rect(s, (200, 60, 50), (900, 292, 110, 38), border_radius=5)         # caixa de ferramentas
    pygame.draw.rect(s, (150, 40, 36), (900, 292, 110, 38), 2, border_radius=5)
    pygame.draw.rect(s, (200, 200, 205), (940, 282, 30, 10), 3, border_radius=4)


def _bg_escola(s):
    _vgrad(s, (0, 0, 1100, 340), (22, 36, 66), (30, 50, 84))
    _vgrad(s, (0, 340, 1100, 138), (44, 58, 86), (20, 28, 44))
    pygame.draw.line(s, NEON, (0, 340), (1100, 340), 2)
    for side in (0, 1):                                                              # armarios
        for i in range(7):
            x = 20 + i * 56 if side == 0 else 1100 - 20 - (i + 1) * 56
            col = lerp((40, 90, 140), (30, 60, 100), i / 6.0)
            pygame.draw.rect(s, col, (x, 70, 52, 270))
            pygame.draw.rect(s, (14, 24, 44), (x, 70, 52, 270), 2)
            for vy in (96, 104, 112):
                pygame.draw.line(s, (14, 24, 44), (x + 10, vy), (x + 42, vy), 2)
            pygame.draw.circle(s, (200, 210, 225), (x + 40, 200), 3)
    pygame.draw.rect(s, (60, 100, 150), (440, 100, 220, 240))                         # porta ao fundo
    pygame.draw.rect(s, (26, 44, 76), (452, 112, 196, 228))
    pygame.draw.rect(s, (110, 190, 235), (500, 130, 100, 70))
    pygame.draw.line(s, (26, 44, 76), (550, 130), (550, 200), 4)
    pygame.draw.circle(s, (235, 240, 245), (550, 66), 24)                             # relogio
    pygame.draw.circle(s, (30, 50, 80), (550, 66), 24, 3)
    pygame.draw.line(s, (30, 50, 80), (550, 66), (550, 50), 3)
    pygame.draw.line(s, (30, 50, 80), (550, 66), (562, 70), 3)
    for i in range(-6, 7):                                                            # piso em perspectiva
        pygame.draw.line(s, (60, 80, 112), (550 + i * 30, 340), (550 + i * 120, 478), 1)
    for y in (360, 390, 430):
        pygame.draw.line(s, (60, 80, 112), (0, y), (1100, y), 1)


def _bg_cantina(s):
    _vgrad(s, (0, 0, 1100, 330), (24, 40, 62), (34, 54, 82))
    _vgrad(s, (0, 330, 1100, 148), (50, 62, 88), (22, 30, 46))
    pygame.draw.line(s, NEON, (0, 330), (1100, 330), 2)
    pygame.draw.rect(s, (18, 52, 56), (150, 50, 420, 120), border_radius=6)           # lousa do cardapio
    pygame.draw.rect(s, (110, 90, 70), (150, 50, 420, 120), 5, border_radius=6)
    for i, w in enumerate((240, 180, 300, 210)):
        pygame.draw.line(s, (200, 230, 215), (176, 78 + i * 24), (176 + w, 78 + i * 24), 3)
    pygame.draw.rect(s, (70, 92, 130), (60, 238, 980, 70))                            # balcao
    pygame.draw.rect(s, (110, 170, 215), (60, 214, 980, 28), 3)
    _vgrad(s, (64, 216, 972, 24), (50, 90, 130), (30, 60, 96))
    for i, x in enumerate(range(100, 1000, 90)):                                       # salgados
        col = ((230, 170, 80), (210, 90, 70), (240, 220, 140))[i % 3]
        pygame.draw.circle(s, col, (x, 232), 11)
        pygame.draw.circle(s, darker(col), (x, 232), 11, 2)
    for x in (650, 800, 950):                                                          # luminarias
        pygame.draw.line(s, (90, 100, 120), (x, 0), (x, 48), 2)
        _glow(s, (x, 62), 46, (240, 230, 170), (30, 48, 76), 5)
        pygame.draw.circle(s, (250, 245, 210), (x, 58), 12)
    for x in (140, 360, 580, 800, 980):                                                # banquinhos
        pygame.draw.ellipse(s, (200, 70, 80), (x - 28, 380, 56, 20))
        pygame.draw.line(s, (130, 140, 160), (x, 396), (x, 450), 5)
        pygame.draw.ellipse(s, (60, 70, 92), (x - 26, 446, 52, 12))


def _court_lines(s, y0, y1, col=(210, 235, 250)):
    cx = 550
    pygame.draw.line(s, col, (0, y0 + 14), (1100, y0 + 14), 3)
    pygame.draw.ellipse(s, col, (cx - 130, y0 + 20, 260, y1 - y0 - 30), 3)
    pygame.draw.line(s, col, (cx, y0 + 14), (cx, y1), 3)


def _bg_quadra(s):
    rng = random.Random(3)
    _vgrad(s, (0, 0, 1100, 300), (16, 28, 52), (26, 44, 76))
    _bleachers(s, 0, 300, 120, 5, 36, (36, 64, 104), (24, 44, 76), 1, rng)
    _bleachers(s, 800, 1100, 120, 5, 36, (36, 64, 104), (24, 44, 76), 1, rng)
    for x, col in ((330, (220, 80, 80)), (480, NEON), (630, GOLD), (780, (110, 220, 120))):   # faixas
        pygame.draw.polygon(s, col, [(x, 20), (x + 90, 20), (x + 90, 80), (x + 45, 66), (x, 80)])
        pygame.draw.line(s, darker(col), (x + 10, 36), (x + 80, 36), 3)
    _vgrad(s, (0, 300, 1100, 178), (30, 78, 122), (18, 46, 80))                       # piso
    for y in range(306, 478, 14):
        pygame.draw.line(s, (22, 58, 96), (0, y), (1100, y), 1)
    pygame.draw.line(s, NEON, (0, 300), (1100, 300), 2)
    _court_lines(s, 300, 470)
    pygame.draw.rect(s, (230, 235, 245), (330, 130, 120, 80))                          # tabela
    pygame.draw.rect(s, (200, 60, 50), (370, 160, 40, 30), 3)
    pygame.draw.ellipse(s, (255, 130, 60), (362, 200, 56, 12), 3)
    pygame.draw.line(s, (120, 130, 150), (390, 210), (390, 300), 4)


def _bg_ginasio(s):
    rng = random.Random(5)
    _vgrad(s, (0, 0, 1100, 320), (10, 18, 36), (20, 34, 62))
    for x in range(40, 1100, 90):                                                     # refletores no teto
        pygame.draw.line(s, (50, 70, 100), (x, 0), (x, 14), 2)
        pygame.draw.circle(s, (230, 235, 200), (x, 22), 8)
        _glow(s, (x, 24), 22, (190, 200, 160), (14, 24, 44), 4)
    _bleachers(s, 0, 1100, 150, 5, 34, (34, 58, 96), (22, 38, 66), 1, rng)
    pygame.draw.rect(s, (14, 20, 34), (400, 40, 300, 90), border_radius=6)             # placar
    pygame.draw.rect(s, NEON, (400, 40, 300, 90), 3, border_radius=6)
    for i, x in enumerate((430, 480, 590, 640)):
        for dy in (52, 82, 112):
            pygame.draw.rect(s, (240, 90, 80), (x, dy - 8, 30, 5))
        pygame.draw.line(s, (240, 90, 80), (x, 52), (x, 108), 4)
        pygame.draw.line(s, (240, 90, 80), (x + 30, 52), (x + 30, 108), 4)
    pygame.draw.circle(s, GOLD, (545, 70), 4)
    pygame.draw.circle(s, GOLD, (545, 100), 4)
    _vgrad(s, (0, 320, 1100, 158), (34, 84, 128), (16, 42, 74))
    for y in range(326, 478, 12):
        pygame.draw.line(s, (20, 56, 94), (0, y), (1100, y), 1)
    pygame.draw.line(s, NEON, (0, 320), (1100, 320), 2)
    _court_lines(s, 320, 472)


def _spots(s, srcs, y1, col):
    for x0, x1, y_end in srcs:
        pygame.draw.polygon(s, col, [(x0, 0), (x0 + 24, 0), (x1 + 80, y_end), (x1 - 80, y_end)])


def _bg_arena(s, gold=False):
    rng = random.Random(11)
    top = (6, 10, 26)
    _vgrad(s, (0, 0, 1100, 478), top, (14, 22, 52))
    _spots(s, ((120, 220, 360), (940, 880, 360), (360, 400, 340), (700, 700, 340)), 360, (14, 28, 62))
    acc = GOLD if gold else NEON
    pygame.draw.rect(s, (8, 12, 28), (300, 36, 500, 220), border_radius=10)             # telao
    _vgrad(s, (310, 46, 480, 200), (30, 20, 90), (0, 70, 130))
    pygame.draw.rect(s, acc, (300, 36, 500, 220), 4, border_radius=10)
    if gold:                                                                           # globo
        pygame.draw.circle(s, (20, 80, 150), (550, 146), 70)
        pygame.draw.circle(s, GOLD, (550, 146), 70, 3)
        pygame.draw.ellipse(s, GOLD, (500, 76, 100, 140), 2)
        pygame.draw.ellipse(s, GOLD, (530, 76, 40, 140), 2)
        pygame.draw.line(s, GOLD, (480, 146), (620, 146), 2)
        pygame.draw.line(s, GOLD, (490, 116), (610, 116), 1)
        pygame.draw.line(s, GOLD, (490, 176), (610, 176), 1)
        for x in range(30, 1100, 54):                                                  # bandeirinhas
            pygame.draw.polygon(s, ((220, 70, 70), (70, 130, 230), (240, 220, 90), (240, 240, 240))[(x // 54) % 4],
                                [(x, 0), (x + 30, 0), (x + 15, 26)])
        for x, y in ((120, 120), (960, 150), (210, 70)):                               # drones
            pygame.draw.line(s, (170, 190, 220), (x - 18, y - 6), (x + 18, y - 6), 3)
            pygame.draw.ellipse(s, (90, 110, 150), (x - 10, y - 4, 20, 10))
            pygame.draw.circle(s, GOLD, (x, y + 4), 3)
    else:
        for i in range(6):
            pygame.draw.line(s, (0, 150, 200), (310, 70 + i * 32), (790, 70 + i * 32), 1)
        pygame.draw.polygon(s, NEON, [(520, 100), (600, 146), (520, 192)], 3)
    _bleachers(s, 0, 1100, 292, 4, 28, (16, 28, 60), (10, 18, 40), 1, rng)
    for x in range(8, 1100, 22):                                                        # luzinhas da plateia
        if rng.random() < 0.18:
            pygame.draw.circle(s, rng.choice(((255, 90, 120), (90, 255, 160), acc)), (x, 296 + rng.randint(0, 80)), 2)
    _vgrad(s, (0, 404, 1100, 74), (20, 34, 74), (10, 18, 40))
    pygame.draw.line(s, acc, (0, 404), (1100, 404), 3)
    for x in range(-200, 1400, 90):
        pygame.draw.line(s, (24, 50, 100), (550 + (x - 550) * 0.4, 404), (x, 478), 1)


def _bg_estadio(s):
    rng = random.Random(13)
    _vgrad(s, (0, 0, 1100, 300), (4, 8, 24), (20, 30, 66))
    for _ in range(70):
        pygame.draw.circle(s, (170, 190, 230), (rng.randint(0, 1099), rng.randint(0, 140)), 1)
    for x in (110, 990):                                                                 # torres de luz
        pygame.draw.rect(s, (40, 52, 80), (x - 6, 90, 12, 260))
        _glow(s, (x, 74), 120, (160, 210, 255), (14, 24, 54), 8)
        pygame.draw.rect(s, (20, 28, 50), (x - 46, 50, 92, 50))
        for i in range(3):
            for j in range(2):
                pygame.draw.circle(s, (250, 250, 235), (x - 30 + i * 30, 63 + j * 24), 8)
    for tier in range(4):                                                                # arquibancadas em degraus
        y = 190 + tier * 40
        pygame.draw.polygon(s, lerp((28, 48, 92), (16, 30, 62), tier / 3.0),
                            [(0, y + 30), (550, y - 10), (1100, y + 30), (1100, y + 70), (0, y + 70)])
        for _ in range(60):
            x = rng.randint(4, 1096)
            yy = y + 28 + int(-40 * (1 - abs(x - 550) / 550.0)) + 26 - 26 * 0 + rng.randint(-4, 14)
            pygame.draw.circle(s, darker(rng.choice(((220, 90, 90), (90, 160, 240), (230, 210, 120),
                                                    (130, 230, 170))), 0.6), (x, yy), 3)
    pygame.draw.rect(s, (14, 80, 80), (0, 392, 1100, 86))                                # gramado
    for i in range(0, 1100, 110):
        pygame.draw.rect(s, (10, 100, 96), (i, 392, 55, 86))
    pygame.draw.line(s, (210, 240, 245), (0, 404), (1100, 404), 3)
    pygame.draw.line(s, NEON, (0, 392), (1100, 392), 2)
    pygame.draw.ellipse(s, (210, 240, 245), (470, 420, 160, 40), 2)


def _bg_camarim(s):
    _vgrad(s, (0, 0, 1100, 360), (30, 22, 52), (40, 30, 70))
    _vgrad(s, (0, 360, 1100, 118), (50, 40, 76), (22, 18, 40))
    pygame.draw.line(s, (255, 120, 200), (0, 360), (1100, 360), 2)
    for x in (100, 330, 560):                                                            # espelhos com lampadas
        pygame.draw.rect(s, (120, 150, 190), (x, 70, 190, 190))
        _vgrad(s, (x + 6, 76, 178, 178), (150, 190, 230), (90, 120, 170))
        pygame.draw.line(s, (220, 240, 255), (x + 20, 90), (x + 70, 240), 3)
        pygame.draw.rect(s, (60, 40, 90), (x, 70, 190, 190), 5)
        for i in range(8):
            pygame.draw.circle(s, (255, 235, 170), (x + 12 + i * 24, 62), 6)
            pygame.draw.circle(s, (255, 235, 170), (x + 12 + i * 24, 268), 6)
    pygame.draw.rect(s, (70, 56, 100), (80, 290, 700, 18), border_radius=4)             # bancada
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


def _bg_federacao(s):
    _vgrad(s, (0, 0, 1100, 330), (18, 26, 56), (30, 42, 80))
    for r in range(8):                                                                     # piso quadriculado
        for c in range(24):
            col = (46, 62, 100) if (r + c) % 2 else (34, 46, 78)
            pygame.draw.rect(s, col, (c * 46, 330 + r * 19, 46, 19))
    pygame.draw.line(s, GOLD, (0, 330), (1100, 330), 2)
    for x in (60, 270, 830, 1040):                                                         # colunas
        pygame.draw.rect(s, (200, 210, 230), (x - 22, 90, 44, 240))
        pygame.draw.rect(s, (160, 172, 198), (x - 22, 90, 14, 240))
        pygame.draw.rect(s, (225, 232, 245), (x - 32, 72, 64, 20))
        pygame.draw.rect(s, (225, 232, 245), (x - 32, 326, 64, 12))
    pygame.draw.circle(s, (20, 36, 72), (550, 120), 62)                                     # selo
    pygame.draw.circle(s, GOLD, (550, 120), 62, 4)
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = 40 if i % 2 == 0 else 17
        pts.append((550 + int(rr * math.cos(a)), 120 + int(rr * math.sin(a))))
    pygame.draw.polygon(s, GOLD, pts)
    for x, flag in ((380, ((220, 70, 70), (240, 240, 240))), (720, ((70, 130, 230), (240, 220, 90)))):
        pygame.draw.line(s, (170, 150, 110), (x, 90), (x, 330), 5)
        pygame.draw.rect(s, flag[0], (x, 94, 70, 24))
        pygame.draw.rect(s, flag[1], (x, 118, 70, 24))
        pygame.draw.circle(s, GOLD, (x, 88), 6)
    pygame.draw.polygon(s, (60, 44, 34), [(190, 400), (910, 400), (990, 462), (110, 462)])  # mesa
    pygame.draw.polygon(s, (96, 70, 52), [(190, 400), (910, 400), (900, 410), (200, 410)])
    pygame.draw.line(s, GOLD, (110, 462), (990, 462), 2)


_DRAWERS = {"garagem": _bg_garagem, "oficina": _bg_oficina, "escola": _bg_escola, "cantina": _bg_cantina,
            "quadra": _bg_quadra, "ginasio": _bg_ginasio, "arena": _bg_arena, "camarim": _bg_camarim,
            "federacao": _bg_federacao, "estadio": _bg_estadio, "mundial": lambda s: _bg_arena(s, True)}
_BG_CACHE = {}


def draw_background(surf, bg):
    """Pinta o cenario `bg` em surf (STAGE_W x STAGE_H). Id desconhecido = fundo liso azul."""
    fn = _DRAWERS.get(bg)
    if fn is None:
        _vgrad(surf, (0, 0, STAGE_W, STAGE_H), (10, 18, 36), (20, 34, 62))
    else:
        fn(surf)
    pygame.draw.rect(surf, (6, 10, 20), (0, STAGE_H - 4, STAGE_W, 4))


def get_background(bg):
    """Surface estatica do cenario (criada UMA vez por cenario, convert() so apos set_mode)."""
    s = _BG_CACHE.get(bg)
    if s is None:
        s = pygame.Surface((STAGE_W, STAGE_H))
        try:
            s = s.convert()
        except pygame.error:
            pass
        draw_background(s, bg)
        _BG_CACHE[bg] = s
    return s


# ================================================================================ PERSONAGENS
def _line(scr, col, a, b, w):
    pygame.draw.line(scr, col, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), max(1, int(w)))


def _arc(scr, col, rect, a0, a1, w):
    pygame.draw.arc(scr, col, pygame.Rect(int(rect[0]), int(rect[1]), max(2, int(rect[2])), max(2, int(rect[3]))),
                    a0, a1, max(1, int(w)))


def draw_face(scr, cx, cy, R, mood, k=1.0):
    """Sobrancelhas, olhos e boca (cx,cy = centro da cabeca; R = raio)."""
    ink = shade(INK, k)
    white = shade((250, 250, 255), k)
    ex = 0.42 * R
    ey = cy - 0.02 * R
    er = max(2, int(0.12 * R))
    by = ey - 0.34 * R
    my = cy + 0.55 * R
    w = max(2, int(R * 0.07))
    lx, rx = cx - ex, cx + ex

    def dots(dx=0, dy=0):
        pygame.draw.circle(scr, ink, (int(lx + dx), int(ey + dy)), er)
        pygame.draw.circle(scr, ink, (int(rx + dx), int(ey + dy)), er)

    def brows(l0, l1, r0, r1):          # (dy externo, dy interno) por lado
        _line(scr, ink, (lx - 0.24 * R, by + l0 * R), (lx + 0.24 * R, by + l1 * R), w)
        _line(scr, ink, (rx - 0.24 * R, by + r1 * R), (rx + 0.24 * R, by + r0 * R), w)

    if mood in ("feliz",):
        for x in (lx, rx):
            _arc(scr, ink, (x - 0.2 * R, ey - 0.12 * R, 0.4 * R, 0.4 * R), 0.2, math.pi - 0.2, w)
        brows(0.0, -0.05, 0.0, -0.05)
        pygame.draw.ellipse(scr, shade((120, 40, 50), k), (cx - 0.34 * R, my - 0.2 * R, 0.68 * R, 0.5 * R))
        pygame.draw.rect(scr, white, (cx - 0.28 * R, my - 0.2 * R, 0.56 * R, 0.14 * R))
    elif mood == "susto":
        for x in (lx, rx):
            pygame.draw.circle(scr, white, (int(x), int(ey)), int(0.2 * R))
            pygame.draw.circle(scr, ink, (int(x), int(ey)), int(0.2 * R), 2)
            pygame.draw.circle(scr, ink, (int(x), int(ey)), max(2, int(0.07 * R)))
        brows(-0.16, -0.26, -0.16, -0.26)
        pygame.draw.ellipse(scr, shade((90, 30, 40), k), (cx - 0.16 * R, my - 0.12 * R, 0.32 * R, 0.5 * R))
        pygame.draw.ellipse(scr, ink, (cx - 0.16 * R, my - 0.12 * R, 0.32 * R, 0.5 * R), 2)
    elif mood == "triste":
        dots(0, 0.05 * R)
        brows(0.14, -0.1, 0.14, -0.1)
        _arc(scr, ink, (cx - 0.3 * R, my + 0.02 * R, 0.6 * R, 0.4 * R), 0.4, math.pi - 0.4, w)
        pygame.draw.circle(scr, shade((120, 190, 255), k), (int(lx - 0.1 * R), int(ey + 0.4 * R)), max(2, int(0.07 * R)))
    elif mood == "bravo":
        for x in (lx, rx):
            pygame.draw.ellipse(scr, ink, (int(x - 0.14 * R), int(ey - 0.04 * R), int(0.28 * R), int(0.16 * R)))
        brows(-0.06, 0.16, -0.06, 0.16)
        _arc(scr, ink, (cx - 0.28 * R, my + 0.0 * R, 0.56 * R, 0.36 * R), 0.4, math.pi - 0.4, w)
        _line(scr, shade((220, 60, 60), k), (cx + 0.9 * R, cy - 0.9 * R), (cx + 1.1 * R, cy - 0.7 * R), w)
        _line(scr, shade((220, 60, 60), k), (cx + 1.1 * R, cy - 0.9 * R), (cx + 0.9 * R, cy - 0.7 * R), w)
    elif mood == "pensando":
        dots(0.1 * R, -0.08 * R)
        _line(scr, ink, (lx - 0.24 * R, by + 0.02 * R), (lx + 0.24 * R, by + 0.02 * R), w)
        _line(scr, ink, (rx - 0.24 * R, by - 0.16 * R), (rx + 0.24 * R, by - 0.3 * R), w)
        _line(scr, ink, (cx - 0.1 * R, my + 0.05 * R), (cx + 0.3 * R, my - 0.04 * R), w)
        for i, (dx, dy, rr) in enumerate(((1.15, -0.5, 0.07), (1.35, -0.85, 0.1), (1.6, -1.3, 0.16))):
            pygame.draw.circle(scr, white, (int(cx + dx * R), int(cy + dy * R)), max(2, int(rr * R)))
    elif mood in ("convencida", "convencido"):
        for x in (lx, rx):
            pygame.draw.ellipse(scr, ink, (int(x - 0.14 * R), int(ey), int(0.28 * R), int(0.14 * R)))
            _line(scr, ink, (x - 0.2 * R, ey - 0.02 * R), (x + 0.2 * R, ey - 0.02 * R), w)
        brows(0.0, -0.06, 0.0, -0.06)
        _line(scr, ink, (cx - 0.22 * R, my + 0.03 * R), (cx + 0.3 * R, my - 0.12 * R), w)
        pygame.draw.circle(scr, ink, (int(cx + 0.3 * R), int(my - 0.12 * R)), max(1, w // 2 + 1))
    elif mood == "corada":
        dots(0, 0.02 * R)
        brows(0.04, -0.02, 0.04, -0.02)
        for x in (cx - 0.72 * R, cx + 0.72 * R):
            pygame.draw.ellipse(scr, shade((255, 120, 150), k), (int(x - 0.22 * R), int(cy + 0.2 * R),
                                                                 int(0.44 * R), int(0.28 * R)))
        _arc(scr, ink, (cx - 0.2 * R, my - 0.12 * R, 0.4 * R, 0.3 * R), math.pi + 0.3, 2 * math.pi - 0.3, w)
    elif mood == "suor":
        dots(0, 0)
        brows(0.12, -0.08, 0.12, -0.08)
        pts = [(cx - 0.3 * R + i * 0.15 * R, my + (0.05 if i % 2 else -0.05) * R) for i in range(5)]
        pygame.draw.lines(scr, ink, False, [(int(a), int(b)) for a, b in pts], w)
        dx, dy = cx + 1.0 * R, cy - 0.55 * R
        pygame.draw.polygon(scr, shade((100, 190, 255), k), [(int(dx), int(dy - 0.3 * R)), (int(dx - 0.18 * R), int(dy + 0.05 * R)),
                                                           (int(dx + 0.18 * R), int(dy + 0.05 * R))])
        pygame.draw.circle(scr, shade((100, 190, 255), k), (int(dx), int(dy + 0.06 * R)), max(2, int(0.18 * R)))
    elif mood == "espirro":
        for x, s_ in ((lx, 1), (rx, -1)):
            _line(scr, ink, (x - s_ * 0.2 * R, ey - 0.1 * R), (x + s_ * 0.16 * R, ey), w)
            _line(scr, ink, (x - s_ * 0.2 * R, ey + 0.1 * R), (x + s_ * 0.16 * R, ey), w)
        brows(0.12, -0.04, 0.12, -0.04)
        pygame.draw.ellipse(scr, shade((90, 30, 40), k), (cx - 0.2 * R, my - 0.12 * R, 0.4 * R, 0.5 * R))
        for i, (dx, dy) in enumerate(((0.5, 0.35), (0.7, 0.55), (0.55, 0.75))):
            pygame.draw.circle(scr, white, (int(cx + dx * R), int(cy + dy * R)), max(2, int(0.07 * R)))
    elif mood == "calmo":
        for x in (lx, rx):
            _arc(scr, ink, (x - 0.2 * R, ey - 0.16 * R, 0.4 * R, 0.36 * R), math.pi + 0.2, 2 * math.pi - 0.2, w)
        brows(0.0, 0.0, 0.0, 0.0)
        _arc(scr, ink, (cx - 0.28 * R, my - 0.16 * R, 0.56 * R, 0.36 * R), math.pi + 0.35, 2 * math.pi - 0.35, w)
    elif mood == "cansado":
        for x in (lx, rx):
            pygame.draw.ellipse(scr, ink, (int(x - 0.13 * R), int(ey + 0.02 * R), int(0.26 * R), int(0.14 * R)))
            _line(scr, ink, (x - 0.22 * R, ey), (x + 0.22 * R, ey), w)
            _arc(scr, shade((120, 100, 130), k), (x - 0.2 * R, ey + 0.1 * R, 0.4 * R, 0.24 * R), math.pi, 2 * math.pi, 1)
        brows(0.06, 0.1, 0.06, 0.1)
        _line(scr, ink, (cx - 0.2 * R, my + 0.04 * R), (cx + 0.2 * R, my + 0.04 * R), w)
    else:                                   # neutro (e "robo" em humanos)
        dots()
        brows(0.0, 0.0, 0.0, 0.0)
        _line(scr, ink, (cx - 0.22 * R, my), (cx + 0.22 * R, my), w)


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


def _hair_front(scr, cx, cy, R, style, col):
    if style == "none":
        return
    if style == "calvo":
        for sx in (-1, 1):
            pygame.draw.ellipse(scr, col, (int(cx + sx * 0.9 * R - 0.18 * R), int(cy - 0.45 * R), int(0.36 * R), int(0.6 * R)))
        return
    if style == "raspado":
        pygame.draw.polygon(scr, col, _cap_points(cx, cy, R, 0.78, 1.0))
        return
    fr = {"curto": 0.62, "espetado": 0.55, "longo": 0.6, "ondulado": 0.5}.get(style, 0.6)
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


def _accessories(scr, cx, cy, R, acc, k, front=True):
    w = max(2, int(R * 0.07))
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
            col = shade((255, 150, 40), k)
            pygame.draw.polygon(scr, col, [(int(cx - 1.0 * R), int(cy - 0.45 * R)), (int(cx + 1.0 * R), int(cy - 0.45 * R)),
                                            (int(cx + 0.98 * R), int(cy - 0.15 * R)), (int(cx - 0.98 * R), int(cy - 0.15 * R))])
            pygame.draw.polygon(scr, col, [(int(cx + 0.95 * R), int(cy - 0.3 * R)), (int(cx + 1.4 * R), int(cy - 0.5 * R)),
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


def _outfit_torso(scr, cx, cy, R, kind, col, k, top, bottom):
    """Torso + detalhes da roupa. top = y dos ombros; bottom = y do fim do torso."""
    c = shade(col, k)
    dark = shade(darker(col), k)
    hw = 1.25 * R
    rect = pygame.Rect(int(cx - hw), int(top), int(2 * hw), int(bottom - top))
    w = max(2, int(R * 0.06))
    if kind == "moletom":
        pygame.draw.ellipse(scr, dark, (int(cx - 0.8 * R), int(top - 0.25 * R), int(1.6 * R), int(0.6 * R)))
    pygame.draw.rect(scr, c, rect, border_radius=int(0.5 * R))
    if kind == "moletom":
        pygame.draw.rect(scr, dark, (int(cx - 0.6 * R), int(top + 1.2 * R), int(1.2 * R), int(0.7 * R)), 2, border_radius=int(0.2 * R))
        _line(scr, shade(lighter(col, 0.5), k), (cx - 0.25 * R, top + 0.3 * R), (cx - 0.25 * R, top + 0.9 * R), w)
        _line(scr, shade(lighter(col, 0.5), k), (cx + 0.25 * R, top + 0.3 * R), (cx + 0.25 * R, top + 0.9 * R), w)
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
    elif kind == "jaleco":
        _line(scr, dark, (cx, top + 0.2 * R), (cx, bottom), w)
        _line(scr, dark, (cx - 0.5 * R, top), (cx - 0.1 * R, top + 0.8 * R), w)
        _line(scr, dark, (cx + 0.5 * R, top), (cx + 0.1 * R, top + 0.8 * R), w)
        pygame.draw.rect(scr, dark, (int(cx - 1.0 * R), int(top + 0.9 * R), int(0.6 * R), int(0.7 * R)), 2)
    elif kind == "uniforme":
        pygame.draw.rect(scr, shade((240, 200, 70), k), (int(cx - hw), int(top + 1.0 * R), int(2 * hw), int(0.25 * R)))
        for sx in (-1, 1):
            pygame.draw.rect(scr, shade((240, 200, 70), k), (int(cx + sx * 1.0 * R - 0.2 * R), int(top), int(0.4 * R), int(0.2 * R)))
    elif kind == "camiseta":
        _arc(scr, dark, (cx - 0.45 * R, top - 0.3 * R, 0.9 * R, 0.8 * R), math.pi, 2 * math.pi, w)
    elif kind == "kimono":
        _line(scr, dark, (cx - 0.55 * R, top), (cx + 0.2 * R, top + 1.6 * R), w + 1)
        _line(scr, dark, (cx + 0.55 * R, top), (cx - 0.2 * R, top + 1.6 * R), w + 1)
        pygame.draw.rect(scr, shade((40, 40, 60), k), (int(cx - hw), int(top + 1.7 * R), int(2 * hw), int(0.3 * R)))


def draw_character(scr, cid, mood="neutro", cx=550, feet_y=470, R=40, k=1.0, bob=0, bust=False):
    """Desenha o personagem `cid` em pe (feet_y = chao). bust=True: so cabeca e ombros
    (feet_y passa a ser o y do CENTRO da cabeca). Humores: story.MOODS."""
    ch = story.CHARACTERS.get(cid)
    if ch is None or cid == "narrador":
        return
    if cid == "ze" or ch["outfit"][0] == "robo":
        return draw_robot(scr, cx, feet_y if not bust else feet_y + int(2.2 * R), R, mood, k, ch, bob)
    cy = (feet_y if bust else feet_y - int(5.9 * R)) + bob
    skin = shade(ch["skin"], k)
    hstyle, hcol = ch["hair"]
    hc = shade(hcol, k)
    kind, ocol = ch["outfit"]
    top = cy + 1.1 * R
    bottom = cy + 3.7 * R
    if not bust:
        pc = shade(PANTS if kind != "kimono" else (50, 50, 74), k)
        for sx in (-1, 1):                                                       # pernas e sapatos
            pygame.draw.rect(scr, pc, (int(cx + sx * 0.55 * R - 0.42 * R), int(bottom - 0.2 * R), int(0.84 * R), int(2.2 * R)),
                             border_radius=int(0.2 * R))
            pygame.draw.ellipse(scr, shade((30, 30, 40), k), (int(cx + sx * 0.6 * R - 0.55 * R), int(cy + 5.6 * R), int(1.1 * R), int(0.4 * R)))
    _hair_back(scr, cx, cy, R, hstyle, hc)
    arm = shade(darker(ocol, 0.86), k)
    for sx in (-1, 1):                                                           # bracos
        pygame.draw.rect(scr, arm, (int(cx + sx * 1.5 * R - 0.28 * R), int(top + 0.05 * R), int(0.56 * R), int(2.4 * R)),
                         border_radius=int(0.28 * R))
        hand = shade((250, 250, 255), k) if "luvas" in ch["acc"] else skin
        pygame.draw.circle(scr, hand, (int(cx + sx * 1.5 * R), int(top + 2.5 * R)), int(0.3 * R))
    pygame.draw.rect(scr, skin, (int(cx - 0.3 * R), int(cy + 0.7 * R), int(0.6 * R), int(0.6 * R)))     # pescoco
    _outfit_torso(scr, cx, cy, R, kind, ocol, k, top, bottom)
    pygame.draw.circle(scr, skin, (int(cx - 1.0 * R), int(cy + 0.1 * R)), int(0.2 * R))                # orelhas
    pygame.draw.circle(scr, skin, (int(cx + 1.0 * R), int(cy + 0.1 * R)), int(0.2 * R))
    pygame.draw.circle(scr, skin, (int(cx), int(cy)), int(R))                                            # cabeca
    _hair_front(scr, cx, cy, R, hstyle, hc)
    draw_face(scr, cx, cy, R, mood, k)
    _accessories(scr, cx, cy, R, ch["acc"], k)


_LED = {"robo": (0, 230, 255), "neutro": (0, 230, 255), "feliz": (110, 240, 130), "susto": (255, 90, 80),
        "triste": (80, 120, 255), "bravo": (255, 90, 80), "pensando": (255, 214, 90), "suor": (255, 214, 90),
        "cansado": (255, 160, 60), "espirro": (255, 214, 90), "calmo": (110, 240, 130), "corada": (255, 120, 170)}


def draw_robot(scr, cx, base_y, R, mood="robo", k=1.0, ch=None, bob=0):
    """Robo-aspirador (disco com LED, chinelo preso por fita). base_y = chao."""
    led = shade(_LED.get(mood, (0, 230, 255)), k)
    y = base_y + bob
    w = int(2.7 * R)
    pygame.draw.ellipse(scr, shade((10, 14, 26), k), (int(cx - w * 0.6), int(y - 0.18 * R), int(w * 1.2), int(0.3 * R)))   # sombra
    body = shade((150, 160, 175), k)
    pygame.draw.ellipse(scr, shade((90, 100, 116), k), (int(cx - w / 2), int(y - 0.95 * R), w, int(0.9 * R)))            # base
    pygame.draw.ellipse(scr, body, (int(cx - w / 2), int(y - 1.35 * R), w, int(0.9 * R)))                                 # tampa
    pygame.draw.ellipse(scr, shade((205, 212, 224), k), (int(cx - w / 2 + 0.2 * R), int(y - 1.3 * R), int(w - 0.4 * R), int(0.4 * R)))
    pygame.draw.ellipse(scr, shade((34, 42, 62), k), (int(cx - 0.6 * R), int(y - 1.25 * R), int(1.2 * R), int(0.6 * R)))   # visor
    pygame.draw.circle(scr, led, (int(cx), int(y - 0.95 * R)), max(3, int(0.2 * R)))
    pygame.draw.circle(scr, lighter(led, 0.6), (int(cx), int(y - 0.98 * R)), max(1, int(0.08 * R)))
    pygame.draw.ellipse(scr, led, (int(cx - w / 2), int(y - 1.35 * R), w, int(0.9 * R)), 2)
    for sx in (-1, 1):                                                                                                    # rodinhas
        pygame.draw.circle(scr, shade((30, 34, 46), k), (int(cx + sx * 0.95 * R), int(y - 0.12 * R)), max(2, int(0.2 * R)))
    # chinelo preso por fita
    cxl, cyl = cx + int(0.55 * R), y - 1.4 * R
    pygame.draw.ellipse(scr, shade((230, 190, 90), k), (int(cxl - 0.5 * R), int(cyl - 0.32 * R), int(1.0 * R), int(0.5 * R)))
    pygame.draw.ellipse(scr, shade((190, 70, 60), k), (int(cxl - 0.25 * R), int(cyl - 0.3 * R), int(0.5 * R), int(0.3 * R)), 2)
    _line(scr, shade((190, 190, 195), k), (cxl - 0.6 * R, cyl - 0.35 * R), (cxl + 0.55 * R, cyl + 0.2 * R), max(2, int(R * 0.1)))
    _line(scr, shade((190, 190, 195), k), (cx - 0.9 * R, y - 0.9 * R), (cx - 0.3 * R, y - 1.35 * R), max(2, int(R * 0.1)))
    pygame.draw.line(scr, shade((90, 100, 116), k), (int(cx - 0.4 * R), int(y - 1.35 * R)), (int(cx - 0.8 * R), int(y - 1.7 * R)), 2)
    pygame.draw.circle(scr, led, (int(cx - 0.8 * R), int(y - 1.72 * R)), max(2, int(0.1 * R)))


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


def draw_bust(scr, rect, cid, mood):
    """Retrato da caixa de dialogo: moldura + cenario liso + busto do personagem (recortado)."""
    r = pygame.Rect(rect)
    ch = story.CHARACTERS.get(cid)
    col = tuple(ch["color"]) if ch else (150, 170, 200)
    pygame.draw.rect(scr, (14, 24, 46), r, border_radius=10)
    pygame.draw.circle(scr, lerp((14, 24, 46), col, 0.28), (r.centerx, r.centery + 10), int(r.w * 0.5))
    old = scr.get_clip()
    scr.set_clip(r.inflate(-6, -6))
    if cid == "narrador" or ch is None:
        draw_narrator_icon(scr, r)
    elif cid == "ze" or ch["outfit"][0] == "robo":
        draw_robot(scr, r.centerx, r.bottom - 22, int(r.w * 0.27), mood, 1.0, ch)
    else:
        R = int(r.w * 0.29)
        draw_character(scr, cid, mood, r.centerx, r.y + int(R * 1.9), R, 1.0, 0, bust=True)
    scr.set_clip(old)
    pygame.draw.rect(scr, col, r, 3, border_radius=10)
