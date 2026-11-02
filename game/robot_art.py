# -*- coding: utf-8 -*-
"""Arte dos robos em campo (Fase 4, passos 0.4 e A9-A11): aspirador visto de cima, tudo pre-renderizado.

Camadas de um robo na partida (ordem de desenho; nenhuma Surface e criada por quadro):

1. **Halo** (A9): 4 niveis de pulso + 1 nivel "bateria baixa", por cor de LED, Surfaces RGB pretas
   blitadas com BLEND_RGB_ADD (o LED "respira" sem recriar nada). Chave ("halo", led).
2. **Baixo** (por direcao): detalhes que ficam SOB o corpo e apontam para onde o robo olha
   (esteiras do Tanque, aleta da Velocista, turbina). 8 direcoes, recortadas no bounding rect.
3. **Escovas** laterais (A9): 6 quadros de 14x14 (3 bracos; 120 graus de simetria), giram por tempo
   real no desenho. 1 escova; 2 com peca de succao. Somem com bateria < 0,10 (spec 3).
4. **Corpo** 64x64 sem rotacao, por (chassis, led, gk, low) - a mesma chave antiga, sem halo. O quadro
   `low` (A11) tem meio anel de LED apagado, rachaduras, chamuscado e uma faisca.
5. **Cima** (por direcao): pecas visiveis (canhao, para-choque blindado, entrada de vacuo, radar,
   antena, modulo/chip) e detalhes do chassi (aba do Disco, faixas da Velocista, luvas e antena do
   Goleiro, viseira do Tita). Tingidas pela cor do LED; a raridade da peca da a cor de destaque.
6. **Por quadro, so pygame.draw** (custo ~0): satelites do Orbital, varredura do radar, luz do
   modulo, chama da turbina; olho e barra de bateria (soccer.draw_player).

Atlas: o pacote de direcoes de um robo (baixo + cima, 8 + 8 recortes) tem chave
("ov", chassis, led, gk, pecas) onde `pecas` = tupla ordenada de (overlay, raridade) - so as que
desenham algo. Cache (`SpriteCache`) com LRU por BYTES (CACHE_BYTES = 6 MB): o warm de uma partida
toca tudo o que ela usa por ultimo, entao uma partida nunca perde o que precisa (ela usa < 1,5 MB).
Memoria tipica (medida em test_robot_art): corpo 16 KB (x2 com low), halo 5 x 16 KB = 80 KB por cor,
atlas 15-40 KB, escovas 5 KB, fumaca/poeira ~60 KB. Partida com 10 robos distintos ~1 MB.

Tudo usa convert()/convert_alpha(): so construa depois de pygame.display.set_mode().
"""
import math
from collections import OrderedDict

import pygame

import parts as _parts                                  # so o catalogo de cosmeticos (parts nao importa nada)

SPRITE_SIZE = 64        # sprite quadrado; o centro fica em (32, 32)
PR = 14                 # raio do corpo no sprite = raio fisico do jogador (soccer.PR)
C = SPRITE_SIZE // 2
DIRS = 8
DIR_HYST = 0.14         # rad alem de pi/8 para trocar de direcao (histerese, evita tremer)
HALO_R = 30
HALO_AMPS = (0.62, 0.8, 0.96, 1.12)   # 4 niveis de pulso; o 5o (indice 4) e o "bateria baixa"
HALO_LOW = 4
HALO_LOW_AMP = 0.3
BRUSH_FRAMES = 6
BRUSH_SIZE = 14
CACHE_BYTES = 6 * 1024 * 1024
BRUSH_OFF_DEG = 52      # escovas a +-52 graus da frente
TITA_R = 17             # Tita: octogono cabe no raio de 18 px (a fisica continua PR=14)
ORBIT_R = PR + 4
RADAR_AB = (-5, 5)      # radar: 5 px atras e 5 px a direita do centro

# overlays de pecas (nomes de garage.VIS_OVERLAY, que mapeia modelo de peca -> overlay)
UNDER = ("turbina",)                                  # overlays desenhados sob o corpo
OVER = ("canhao", "blindado", "vacuo", "radar", "antena", "modulo")
ATLAS_PARTS = UNDER + OVER                            # "escova" so muda a contagem de escovas
RAR_COLORS = ((190, 200, 210), (0, 170, 255), (190, 110, 255), (255, 200, 60))   # = parts.RAR_COLORS
METAL = (78, 86, 102)
METAL_HI = (150, 160, 178)
DARK = (14, 18, 26)

# fumaca/poeira (A11): cor por estilo de particula (soccer.FX_STYLE)
PUFF_COLORS = ((170, 146, 108), (206, 208, 218), (112, 110, 118))   # poeira, fumaca, fumaca escura
PUFF_RADII = (2, 3, 4, 5, 6, 7, 8, 9, 10)
PUFF_FADES = 4

# cosmeticos (B13; so visuais). Adesivo e antena entram no atlas (chave ganha `look`): custo por quadro 0.
DECAL_AB = (1, 7)        # adesivo ~9x9 a 1 px a frente e 7 px a direita do centro (sob as pecas)
TRAIL_N = 6              # rastro do robo: pool fixo de 6 pontos por jogador (amostra a cada TRAIL_DT s reais)
TRAIL_DT = 0.045
TRAIL_SIZE = 16
TRAIL_SPEED2 = 90 * 90   # so deixa rastro acima de 90 px/s
ICON_SIZE = 40           # icone da galeria/loja
RAINBOW = ((255, 70, 70), (255, 160, 40), (255, 235, 60), (80, 220, 100), (60, 150, 255), (190, 100, 255))
CELEBRATION_COLORS = {"confete": ((255, 80, 120), (255, 220, 60), (80, 220, 120), (70, 170, 255)),
                      "bolo": ((255, 150, 190), (255, 245, 225), (150, 90, 50), (255, 220, 80)),
                      "chinelo_voando": ((60, 140, 255), (255, 220, 60), (60, 200, 110)),
                      "fogos": ((255, 210, 70), (255, 80, 60), (120, 230, 255))}

STATS = {"atlas": 0, "body": 0, "halo": 0}           # construcoes (testes de cache)


# ---------------------------------------------------------------------------------- cores
def led_color(c, min_lum=125):
    """Cor do LED/halo do time com luminancia minima (cores escuras somem na arena escura)."""
    c = tuple(int(x) for x in c[:3])
    lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    if lum >= min_lum:
        return c
    k = (min_lum - lum) / (255.0 - lum)
    return tuple(int(x + (255 - x) * k) for x in c)


def scale_color(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------------------------------------------------------------------------------- cache
class SpriteCache(OrderedDict):
    """dict de sprites com LRU por bytes. `put` registra o tamanho e despeja os mais antigos acima
    de `max_bytes`; `get`/`[]` de leitura nao reordena (o warm reordena com `touch`)."""

    def __init__(self, max_bytes=CACHE_BYTES):
        super().__init__()
        self.max_bytes = max_bytes
        self.sizes = {}
        self.nbytes = 0
        self.evicted = 0

    def put(self, key, val, nbytes):
        if key in self:
            self.nbytes -= self.sizes.get(key, 0)
        OrderedDict.__setitem__(self, key, val)
        self.move_to_end(key)
        self.sizes[key] = nbytes
        self.nbytes += nbytes
        while self.nbytes > self.max_bytes and len(self) > 1:
            k, _ = self.popitem(last=False)
            self.nbytes -= self.sizes.pop(k, 0)
            self.evicted += 1

    def __setitem__(self, key, val):              # compatibilidade: cache[key] = Surface
        self.put(key, val, _nbytes(val))

    def touch(self, key):
        if key in self:
            self.move_to_end(key)

    def clear(self):
        OrderedDict.clear(self)
        self.sizes.clear()
        self.nbytes = 0


def _nbytes(v):
    if isinstance(v, pygame.Surface):
        w, h = v.get_size()
        return w * h * v.get_bytesize()
    if isinstance(v, (list, tuple)):
        return sum(_nbytes(x) for x in v)
    if isinstance(v, dict):
        return sum(_nbytes(x) for x in v.values())
    if isinstance(v, Atlas):
        return v.nbytes
    return 0


def _get(cache, key, build):
    v = cache.get(key)
    if v is None:
        v = build()
        if isinstance(cache, SpriteCache):
            cache.put(key, v, _nbytes(v))
        else:
            cache[key] = v
    elif isinstance(cache, SpriteCache):
        cache.touch(key)
    return v


# ---------------------------------------------------------------------------------- geometria
DIR_VEC = tuple((math.cos(d * math.pi / 4), math.sin(d * math.pi / 4)) for d in range(DIRS))


def face_dir(face, prev=None):
    """Direcao 0..7 (0 = leste, sentido horario na tela) do vetor `face`, com histerese sobre `prev`."""
    fx, fy = face[0], face[1]
    if fx == 0 and fy == 0:
        return prev if prev is not None else 0
    a = math.atan2(fy, fx)
    near = int(round(a / (math.pi / 4))) % DIRS
    if prev is None or near == prev:
        return near
    pa = prev * math.pi / 4
    diff = abs((a - pa + math.pi) % (2 * math.pi) - math.pi)
    return near if diff > math.pi / 8 + DIR_HYST else prev


def _pt(d, a, b, cx=C, cy=C):
    """Ponto a `a` px para a frente e `b` px para a direita do robo virado para `d`."""
    fx, fy = DIR_VEC[d] if isinstance(d, int) else d
    return (cx + fx * a - fy * b, cy + fy * a + fx * b)


def _poly(d, pts):
    return [_pt(d, a, b) for a, b in pts]


def dir_offset(d, a, b):
    """Deslocamento (dx, dy) inteiro de um ponto do robo (usado por quadro, sem Surface)."""
    fx, fy = DIR_VEC[d]
    return (int(round(fx * a - fy * b)), int(round(fy * a + fx * b)))


def _arc_poly(d, r0, r1, deg0, deg1, steps=10):
    """Faixa de arco (anel parcial) entre os raios r0..r1, de deg0 a deg1 relativos a frente."""
    base = d * 45
    out, inn = [], []
    for i in range(steps + 1):
        g = math.radians(base + deg0 + (deg1 - deg0) * i / steps)
        out.append((C + math.cos(g) * r1, C + math.sin(g) * r1))
        inn.append((C + math.cos(g) * r0, C + math.sin(g) * r0))
    return out + inn[::-1]


def _octagon(r, cx=C, cy=C):
    return [(cx + math.cos(math.pi / 8 + k * math.pi / 4) * r, cy + math.sin(math.pi / 8 + k * math.pi / 4) * r)
            for k in range(8)]


def _right_half(r):
    """Vertices do octogono com x > centro, de cima para baixo (meio anel do Tita)."""
    angs = sorted((math.pi / 8 + k * math.pi / 4 + math.pi) % (2 * math.pi) - math.pi for k in range(8))
    return [(C + math.cos(a) * r, C + math.sin(a) * r) for a in angs if -math.pi / 2 < a < math.pi / 2]


# ---------------------------------------------------------------------------------- corpo
def _dome(s, cx, cy, body, tint=(0, 4, 14)):
    for i in range(body, 0, -1):                       # domo metalico com brilho
        t = 1 - i / body
        v = int(46 + 92 * t)
        pygame.draw.circle(s, (v + tint[0], v + tint[1], v + tint[2]), (cx - int(t * 3), cy - int(t * 3)), i)
    pygame.draw.circle(s, (20, 24, 34), (cx, cy), body, 1)
    pygame.draw.circle(s, (190, 200, 215), (cx - 4, cy - 4), 2)   # reflexo


def build_robot_sprite(chassis, led, gk, low):
    """Corpo do aspirador visto de cima (64x64, sem halo e sem rotacao). Detalhes por chassi (A10) e
    quadro `low` expressivo (A11). O halo e as pecas sao camadas separadas (build_halo/build_atlas)."""
    s = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)
    c = C
    ledc = scale_color(led, 0.4) if low else led
    tita = chassis == "Titã"
    rad = TITA_R if tita else PR
    pygame.draw.ellipse(s, (0, 0, 0, 110), (c - rad + 1, c + rad - 9, rad * 2, 18))   # sombra
    if chassis == "Orbital":                           # anel externo fino (trilho dos satelites)
        pygame.draw.circle(s, scale_color(ledc, 0.55), (c, c), ORBIT_R, 1)
        for k in range(4):
            a = k * math.pi / 2 + math.pi / 4
            pygame.draw.line(s, scale_color(ledc, 0.4), (c + math.cos(a) * (PR - 1), c + math.sin(a) * (PR - 1)),
                             (c + math.cos(a) * ORBIT_R, c + math.sin(a) * ORBIT_R), 1)
    if tita:
        pygame.draw.polygon(s, ledc, _octagon(TITA_R))
        pygame.draw.polygon(s, DARK, _octagon(TITA_R), 1)
        for i in range(13, 0, -1):                     # placa octogonal blindada
            t = 1 - i / 13
            v = int(52 + 80 * t)
            pygame.draw.polygon(s, (v, v + 3, v + 10), _octagon(i, c - int(t * 2), c - int(t * 2)))
        pygame.draw.polygon(s, (20, 24, 34), _octagon(13), 1)
        pygame.draw.polygon(s, (36, 40, 52), _octagon(8), 1)
        for k in range(6):                             # 6 rebites
            a = math.pi / 6 + k * math.pi / 3
            p = (int(c + math.cos(a) * 10.5), int(c + math.sin(a) * 10.5))
            pygame.draw.circle(s, (34, 38, 48), p, 2)
            pygame.draw.circle(s, (176, 184, 198), (p[0] - 1, p[1] - 1), 1)
        for sx in (-1, 1):                             # aberturas de ventilacao laterais
            for dy in (-4, 0, 4):
                pygame.draw.line(s, (16, 18, 24), (c + sx * 15, c + dy), (c + sx * 12, c + dy), 2)
        pygame.draw.circle(s, (190, 200, 215), (c - 5, c - 6), 2)
    else:
        ring = 5 if chassis == "Tanque" else 3
        pygame.draw.circle(s, ledc, (c, c), PR)
        pygame.draw.circle(s, (12, 16, 24), (c, c), PR, 1)
        body = PR - ring
        if chassis == "Disco":                         # aba metalica em volta do domo
            pygame.draw.circle(s, (104, 112, 128), (c, c), body)
            pygame.draw.circle(s, (40, 44, 56), (c, c), body, 1)
            for k in range(6):
                a = k * math.pi / 3
                pygame.draw.circle(s, (54, 58, 70), (int(c + math.cos(a) * (body - 1.5)),
                                                     int(c + math.sin(a) * (body - 1.5))), 1)
            _dome(s, c, c, body - 2)
        elif chassis == "Velocista":                   # domo alongado e mais claro
            _dome(s, c, c, body, (8, 10, 18))
        else:
            _dome(s, c, c, body)
        if chassis == "Tanque":                        # placas de blindagem + rebites
            for sx in (-1, 1):
                pygame.draw.line(s, (25, 28, 38), (c + sx * 3, c - body + 1), (c + sx * 3, c + body - 1), 2)
            for k in range(4):
                a = math.pi / 4 + k * math.pi / 2
                pygame.draw.circle(s, (30, 34, 44), (int(c + math.cos(a) * (PR - 2.5)),
                                                     int(c + math.sin(a) * (PR - 2.5))), 1)
        if chassis == "Orbital":                       # nucleo com anel concentrico
            pygame.draw.circle(s, (54, 64, 84), (c, c), body - 3, 1)
            pygame.draw.circle(s, ledc, (c, c), 3)
            pygame.draw.circle(s, (240, 250, 255), (c, c), 1)
    if gk or chassis == "Goleiro":                     # LEDs extras
        r = TITA_R - 5 if tita else PR - 6
        for k in range(8):
            a = k * math.pi / 4
            pygame.draw.circle(s, ledc, (int(c + math.cos(a) * r), int(c + math.sin(a) * r)), 1)
    if low:                                            # A11: meio LED apagado, rachaduras, faisca
        dead = (24, 26, 32)
        if tita:
            pygame.draw.polygon(s, dead, _right_half(TITA_R) + _right_half(13)[::-1])
            pygame.draw.polygon(s, (60, 62, 70), _octagon(13), 1)
        else:
            pygame.draw.arc(s, dead, (c - PR, c - PR, PR * 2, PR * 2), -math.pi / 2, math.pi / 2, 3)
        crack = (16, 18, 22)
        pygame.draw.lines(s, crack, False, [(c - 6, c - 2), (c - 2, c + 1), (c - 4, c + 4), (c + 1, c + 7)], 1)
        pygame.draw.lines(s, crack, False, [(c + 2, c - 7), (c + 4, c - 3), (c + 2, c - 1)], 1)
        pygame.draw.circle(s, (46, 38, 32), (c + 5, c + 4), 3)          # chamuscado
        sx, sy = c + 9, c - 10                                          # faisca eletrica
        for (ax, ay) in ((-3, 0), (3, 0), (0, -3), (0, 3)):
            pygame.draw.line(s, (255, 236, 110), (sx, sy), (sx + ax, sy + ay), 1)
        pygame.draw.lines(s, (150, 230, 255), False, [(sx - 5, sy + 5), (sx - 2, sy + 2), (sx - 3, sy), (sx, sy - 1)], 1)
        pygame.draw.circle(s, (255, 255, 230), (sx, sy), 1)
    STATS["body"] += 1
    return s.convert_alpha()


# ---------------------------------------------------------------------------------- halo
def build_halo(led):
    """5 Surfaces RGB (pretas = transparentes no BLEND_RGB_ADD): 4 niveis de pulso + bateria baixa."""
    out = []
    for amp in HALO_AMPS + (HALO_LOW_AMP,):
        s = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE))
        s.fill((0, 0, 0))
        for r in range(HALO_R, PR - 3, -1):
            k = (1 - (r - PR + 3) / (HALO_R - PR + 3)) ** 2 * 0.42 * amp
            pygame.draw.circle(s, tuple(min(255, int(x * k)) for x in led), (C, C), r)
        out.append(s.convert())
    STATS["halo"] += 1
    return tuple(out)


def _halo_alpha(s, led):
    """Halo antigo (alfa) para o sprite da UI (garagem/bancada)."""
    for r in range(C - 2, PR, -1):
        k = (1 - (r - PR) / (C - 2 - PR)) ** 2
        pygame.draw.circle(s, led + (int(70 * k),), (C, C), r)


# ---------------------------------------------------------------------------------- overlays
def _draw_chassis_under(s, ch, d, led):
    if ch == "Tanque":                                 # esteiras laterais
        for side in (-1, 1):
            b0, b1 = side * (PR - 3), side * (PR + 3)
            pygame.draw.polygon(s, (30, 32, 40), _poly(d, [(13, b0), (13, b1), (-13, b1), (-13, b0)]))
            pygame.draw.polygon(s, (8, 10, 14), _poly(d, [(13, b0), (13, b1), (-13, b1), (-13, b0)]), 1)
            for a in range(-11, 13, 4):
                pygame.draw.line(s, (84, 88, 100), _pt(d, a, b0 + side * 1), _pt(d, a, b1 - side * 1), 1)
    elif ch == "Velocista":                            # aleta traseira
        fin = _poly(d, [(-PR + 3, -7), (-PR + 3, 7), (-PR - 8, 0)])
        pygame.draw.polygon(s, led, fin)
        pygame.draw.polygon(s, (20, 24, 32), fin, 1)
        pygame.draw.line(s, scale_color(led, 0.55), _pt(d, -PR + 2, 0), _pt(d, -PR - 6, 0), 1)


def _draw_chassis_over(s, ch, d, led):
    if ch == "Disco":                                  # aba frontal (labio do para-choque)
        pygame.draw.polygon(s, (112, 120, 138), _arc_poly(d, PR - 2, PR + 1, -48, 48))
        pygame.draw.polygon(s, DARK, _arc_poly(d, PR - 2, PR + 1, -48, 48), 1)
    elif ch == "Velocista":                            # 2 faixas de aceleracao
        for b in (-3, 3):
            pygame.draw.line(s, led, _pt(d, 6, b), _pt(d, -9, b), 2)
        pygame.draw.line(s, (240, 248, 255), _pt(d, 7, 0), _pt(d, 3, 0), 1)
    elif ch == "Goleiro":                              # luvas + antena traseira
        for b in (-1, 1):
            p = _pt(d, PR - 3, b * (PR - 4))
            pygame.draw.circle(s, (236, 240, 246), p, 4)
            pygame.draw.circle(s, led, p, 4, 1)
            pygame.draw.circle(s, (170, 178, 190), p, 2)
        pygame.draw.line(s, (40, 44, 56), _pt(d, -6, 5), _pt(d, -PR - 5, 8), 2)
        pygame.draw.circle(s, led, _pt(d, -PR - 5, 8), 2)
    elif ch == "Titã":                                 # viseira frontal
        pygame.draw.line(s, DARK, _pt(d, TITA_R - 5, -7), _pt(d, TITA_R - 5, 7), 4)
        pygame.draw.line(s, led, _pt(d, TITA_R - 5, -6), _pt(d, TITA_R - 5, 6), 2)


def _draw_part(s, name, rar, d, led):
    acc = RAR_COLORS[max(0, min(3, int(rar)))]
    if name == "turbina":                              # cone traseiro + bocal
        cone = _poly(d, [(-PR + 4, -5), (-PR + 4, 5), (-PR - 7, 7), (-PR - 7, -7)])
        pygame.draw.polygon(s, METAL, cone)
        pygame.draw.polygon(s, DARK, cone, 1)
        for b in (-3, 0, 3):                           # aletas do cone
            pygame.draw.line(s, METAL_HI, _pt(d, -PR, b), _pt(d, -PR - 5, b * 1.6), 1)
        pygame.draw.line(s, led, _pt(d, -PR - 2, -6), _pt(d, -PR - 2, 6), 2)
        pygame.draw.line(s, acc, _pt(d, -PR - 7, -7), _pt(d, -PR - 7, 7), 2)
    elif name == "canhao":                             # cano que cresce com a raridade
        L = PR + 4 + 2 * int(rar)
        pygame.draw.circle(s, METAL, _pt(d, PR - 6, 0), 5)
        pygame.draw.circle(s, DARK, _pt(d, PR - 6, 0), 5, 1)
        barrel = _poly(d, [(PR - 6, -3), (L, -3), (L, 3), (PR - 6, 3)])
        pygame.draw.polygon(s, (58, 64, 78), barrel)
        pygame.draw.polygon(s, DARK, barrel, 1)
        pygame.draw.line(s, METAL_HI, _pt(d, PR - 4, -1), _pt(d, L - 1, -1), 1)
        pygame.draw.line(s, led, _pt(d, L - 6, -3), _pt(d, L - 6, 3), 2)
        tip = _pt(d, L, 0)
        pygame.draw.circle(s, mix(acc, (140, 245, 255), 0.5), tip, 3)
        pygame.draw.circle(s, (245, 255, 255), tip, 1)
    elif name == "blindado":                           # arco frontal grosso com rebites
        arc = _arc_poly(d, PR - 1, PR + 4, -70, 70, 12)
        pygame.draw.polygon(s, (118, 124, 140), arc)
        pygame.draw.polygon(s, DARK, arc, 1)
        pygame.draw.lines(s, acc, False, _arc_poly(d, PR + 3, PR + 3, -64, 64, 10)[:11], 1)
        for g in (-45, 0, 45):
            a = math.radians(d * 45 + g)
            pygame.draw.circle(s, (40, 44, 54), (int(C + math.cos(a) * (PR + 1.5)), int(C + math.sin(a) * (PR + 1.5))), 1)
    elif name == "vacuo":                              # entrada de ar frontal
        pygame.draw.polygon(s, (16, 18, 24), _arc_poly(d, PR - 5, PR - 1, -38, 38))
        for g in (-24, -8, 8, 24):
            a = math.radians(d * 45 + g)
            pygame.draw.line(s, scale_color(led, 0.8), (C + math.cos(a) * (PR - 5), C + math.sin(a) * (PR - 5)),
                             (C + math.cos(a) * (PR - 1), C + math.sin(a) * (PR - 1)), 1)
    elif name == "radar":                              # base do radar (a varredura e por quadro)
        p = _pt(d, *RADAR_AB)
        pygame.draw.circle(s, (24, 28, 38), p, 4)
        pygame.draw.circle(s, acc, p, 4, 1)
    elif name == "antena":                             # antena com ponta de LED infravermelho
        pygame.draw.line(s, (36, 40, 50), _pt(d, -5, -5), _pt(d, -PR - 4, -9), 2)
        pygame.draw.circle(s, (255, 70, 70), _pt(d, -PR - 4, -9), 2)
        pygame.draw.circle(s, acc, _pt(d, -PR - 4, -9), 3, 1)
    elif name == "modulo":                             # modulo/chip (a luzinha pisca por quadro)
        q = _poly(d, [(5, -9), (5, -3), (-1, -3), (-1, -9)])
        pygame.draw.polygon(s, (36, 42, 56), q)
        pygame.draw.polygon(s, acc, q, 1)


def _crop(s):
    r = s.get_bounding_rect()
    if r.w == 0 or r.h == 0:
        return None
    return (s.subsurface(r).copy().convert_alpha(), r.x - C, r.y - C)


# ---------------------------------------------------------------------------------- cosmeticos (B13)
def _draw_sticker(s, did, cx, cy):
    """Adesivo no robo (~11 px): selo redondo claro (escuro na caveira) com o simbolo por cima, para ler
    bem sobre o domo cinza em qualquer cor de time."""
    back = (40, 44, 60) if did == "caveira" else (244, 244, 236)
    pygame.draw.circle(s, back, (cx, cy), 5.5)
    pygame.draw.circle(s, (16, 20, 30), (cx, cy), 5.5, 1)
    _draw_decal(s, did, cx, cy, 0.95)


def _draw_decal(s, did, cx, cy, k=1.0):
    """Adesivo `did` centrado em (cx, cy); k = escala (1 = ~9 px no robo; a galeria usa ~3,6). Abaixo de
    k 2 sem contorno (o selo de _draw_sticker faz o contraste)."""
    def q(x, y):
        return (cx + x * k, cy + y * k)
    w = max(1, int(round(k * 0.6)))
    edge = (30, 22, 18)
    if k < 2:
        w = 0
    if did == "estrela":
        pts = [q(math.cos(-math.pi / 2 + i * math.pi / 5) * (4.6 if i % 2 == 0 else 1.9),
                 math.sin(-math.pi / 2 + i * math.pi / 5) * (4.6 if i % 2 == 0 else 1.9)) for i in range(10)]
        pygame.draw.polygon(s, (255, 215, 60), pts)
        if w:
            pygame.draw.polygon(s, edge, pts, w)
    elif did == "raio":
        pts = [q(1.2, -4.6), q(-2.8, 0.6), q(-0.2, 0.6), q(-1.2, 4.6), q(2.8, -0.8), q(0.2, -0.8)]
        pygame.draw.polygon(s, (255, 180, 20) if k < 2 else (255, 196, 40), pts)
        if w:
            pygame.draw.polygon(s, edge, pts, w)
    elif did == "pao_queijo":
        pygame.draw.circle(s, (232, 186, 104), q(0, 0), 4.2 * k)
        pygame.draw.circle(s, (150, 98, 44), q(0, 0), 4.2 * k, max(1, w))
        for x, y in ((-1.6, -1.2), (1.4, -0.6), (-0.2, 1.6)):
            pygame.draw.circle(s, (196, 134, 62), q(x, y), max(1.0, 0.8 * k))
        pygame.draw.circle(s, (252, 226, 160), q(-1.4, -2.2), max(1.0, 0.7 * k))
    elif did == "chinelo":
        r = pygame.Rect(0, 0, int(4.6 * k), int(9.4 * k))
        r.center = (int(cx), int(cy))
        pygame.draw.ellipse(s, (60, 140, 255), r)
        if w:
            pygame.draw.ellipse(s, (16, 40, 90), r, w)
        pygame.draw.lines(s, (255, 230, 60) if k < 2 else (250, 250, 250), False,
                          [q(-2, -0.6), q(0, -2.8), q(2, -0.6)], max(1, w))
    elif did == "caveira":
        pygame.draw.circle(s, (240, 240, 232), q(0, -0.9), 3.6 * k)
        pygame.draw.rect(s, (240, 240, 232), pygame.Rect(q(-2.0, 1.2), (4.0 * k + 1, 3.0 * k)))
        if w:
            pygame.draw.circle(s, edge, q(0, -0.9), 3.6 * k, w)
        for x in (-1.4, 1.4):
            pygame.draw.circle(s, (20, 20, 24), q(x, -0.9), max(1.0, 1.0 * k))
        pygame.draw.line(s, (20, 20, 24), q(0, 2.0), q(0, 4.0), max(1, w))
    elif did == "coracao":
        red = (235, 50, 80)
        for x in (-1.7, 1.7):
            pygame.draw.circle(s, red, q(x, -1.2), 2.3 * k)
        pygame.draw.polygon(s, red, [q(-3.9, -0.7), q(3.9, -0.7), q(0, 4.2)])
        pygame.draw.circle(s, (255, 190, 200), q(-1.9, -1.8), max(1.0, 0.7 * k))


def _draw_antenna(s, aid, d, led, cx=C, cy=C):
    """Antena cosmetica na traseira do robo virado para `d` (desenhada por cima de tudo)."""
    def p(a, b):
        return _pt(d, a, b, cx, cy)
    dark = (36, 40, 52)
    if aid == "curta":
        pygame.draw.line(s, dark, p(-6, 0), p(-PR - 3, 0), 2)
        pygame.draw.circle(s, led, p(-PR - 3, 0), 3)
        pygame.draw.circle(s, (250, 252, 255), p(-PR - 3, 0), 1)
    elif aid == "mola":
        pts = [p(-6 - i * 2.2, 0 if i in (0, 6) else (2 if i % 2 else -2)) for i in range(7)]
        pygame.draw.lines(s, (186, 192, 206), False, pts, 1)
        pygame.draw.circle(s, (255, 90, 150), pts[-1], 3)
        pygame.draw.circle(s, (255, 230, 240), pts[-1], 1)
    elif aid == "dupla":
        for b in (-1, 1):
            pygame.draw.line(s, dark, p(-5, b * 3), p(-PR - 3, b * 8), 2)
            pygame.draw.circle(s, led, p(-PR - 3, b * 8), 2)
            pygame.draw.circle(s, (250, 252, 255), p(-PR - 3, b * 8), 1)


def look_key(look):
    """(adesivo, antena) que entram no sprite/atlas (None = nenhum), a partir de um dict `look`."""
    look = look or {}
    return (look.get("decal"), look.get("antenna"))


def build_trail(tid):
    """Rastro do robo: TRAIL_N imagens TRAIL_SIZE (0 = mais nova/maior, depois some). Prontas no warm."""
    out = []
    h = TRAIL_SIZE // 2
    for i in range(TRAIL_N):
        f = 1.0 - i / float(TRAIL_N)
        a = int(40 + 190 * f)
        r = max(1, int(2 + 4.5 * f))
        s = pygame.Surface((TRAIL_SIZE, TRAIL_SIZE), pygame.SRCALPHA)
        if tid == "neon":
            pygame.draw.circle(s, (40, 230, 255, a // 3), (h, h), min(h, r + 2))
            pygame.draw.circle(s, (120, 245, 255, a), (h, h), r)
            pygame.draw.circle(s, (235, 255, 255, a), (h, h), max(1, r - 2))
        elif tid == "fogo":
            c = mix((255, 236, 110), (220, 50, 20), i / float(TRAIL_N - 1))
            pygame.draw.circle(s, c + (a // 2,), (h, h), min(h, r + 1))
            pygame.draw.circle(s, mix(c, (255, 255, 220), 0.4) + (a,), (h, h - 1), max(1, r - 1))
        elif tid == "arco_iris":
            pygame.draw.circle(s, RAINBOW[i % len(RAINBOW)] + (a,), (h, h), r)
        else:                                           # estrelas: estrelinhas de 4 pontas
            c = (255, 230, 90) if i % 2 == 0 else (255, 255, 235)
            e = r + 1
            pygame.draw.polygon(s, c + (a,), [(h, h - e), (h + 1, h - 1), (h + e, h), (h + 1, h + 1),
                                              (h, h + e), (h - 1, h + 1), (h - e, h), (h - 1, h - 1)])
        out.append(s.convert_alpha())
    return tuple(out)


def build_cosmetic_icon(cid):
    """Icone ICON_SIZE da galeria/loja (pronto; cacheado por cosmetic_icon)."""
    kind = _parts.COSMETIC_KIND.get(cid)
    n = ICON_SIZE
    s = pygame.Surface((n, n), pygame.SRCALPHA)
    h = n // 2
    if kind == "decal":
        _draw_decal(s, cid, h, h, 3.6)
    elif kind == "antenna":
        big = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)   # ampliado 1,5x (pixelado)
        pygame.draw.circle(big, (0, 170, 220), (C, C + 16), PR)
        _dome(big, C, C + 16, PR - 3)
        _draw_antenna(big, cid, 2, (0, 230, 255), C, C + 16)
        s.blit(pygame.transform.scale(big.subsurface((C - 13, C - 10, 27, 27)), (n, n)), (0, 0))
    elif kind == "trail":
        imgs = build_trail(cid)
        for i in range(TRAIL_N - 1, -1, -1):
            x = 4 + int((TRAIL_N - 1 - i) * (n - 8 - TRAIL_SIZE) / (TRAIL_N - 1))
            s.blit(imgs[i], (x, h - TRAIL_SIZE // 2 + (2 if i % 2 else -2)))
    elif kind == "celebration":
        cols = CELEBRATION_COLORS[cid]
        if cid == "bolo":
            pygame.draw.rect(s, (150, 90, 50), (9, 20, 22, 12), border_radius=3)
            pygame.draw.rect(s, (255, 150, 190), (9, 18, 22, 5), border_radius=2)
            for x in (14, 20, 26):
                pygame.draw.line(s, (240, 240, 250), (x, 17), (x, 11), 2)
                pygame.draw.circle(s, (255, 210, 70), (x, 9), 2)
        elif cid == "chinelo_voando":
            _draw_decal(s, "chinelo", 14, 22, 2.6)
            _draw_decal(s, "chinelo", 28, 16, 2.0)
        elif cid == "fogos":
            for (fx, fy, r), c in zip(((13, 14, 9), (28, 22, 8)), cols):
                for k in range(8):
                    a = k * math.pi / 4
                    pygame.draw.line(s, c, (fx + math.cos(a) * 3, fy + math.sin(a) * 3),
                                     (fx + math.cos(a) * r, fy + math.sin(a) * r), 2)
        k = 0
        for x, y in ((6, 6), (33, 7), (20, 4), (5, 32), (35, 33), (21, 36), (12, 26), (30, 28)):
            if cid == "confete" or k % 2 == 0:
                pygame.draw.rect(s, cols[k % len(cols)], (x, y, 4, 3))
            k += 1
    return s.convert_alpha()


def cosmetic_icon(cache, cid):
    return _get(cache, ("cos_icon", cid), lambda: build_cosmetic_icon(cid))


class Atlas:
    """Camadas por direcao de um robo: under[d]/over[d] = (Surface, dx, dy) ou None.
    `look` = (adesivo, antena) cosmeticos (B13): adesivo sob as pecas, antena por cima de tudo."""

    def __init__(self, ch, led, gk, parts, look=(None, None)):
        self.key = (ch, led, gk, parts, look)
        self.under, self.over = [], []
        names = dict(parts)
        decal, antenna = look if look else (None, None)
        for d in range(DIRS):
            u = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)
            _draw_chassis_under(u, ch, d, led)
            for nm in UNDER:
                if nm in names:
                    _draw_part(u, nm, names[nm], d, led)
            o = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)
            _draw_chassis_over(o, ch, d, led)
            if decal:
                _draw_sticker(o, decal, *_pt(d, *DECAL_AB))
            for nm in OVER:
                if nm in names:
                    _draw_part(o, nm, names[nm], d, led)
            if antenna:
                _draw_antenna(o, antenna, d, led)
            self.under.append(_crop(u))
            self.over.append(_crop(o))
        self.nbytes = sum(x[0].get_width() * x[0].get_height() * 4
                          for x in self.under + self.over if x is not None)
        STATS["atlas"] += 1


def build_atlas(ch, led, gk, parts=(), look=(None, None)):
    return Atlas(ch, led, gk, tuple(parts), tuple(look) if look else (None, None))


# ---------------------------------------------------------------------------------- escova e fumaca
def build_brushes():
    """6 quadros da escova lateral (3 bracos, 0..100 graus); neutros (servem para todos)."""
    out = []
    h = BRUSH_SIZE // 2
    for f in range(BRUSH_FRAMES):
        s = pygame.Surface((BRUSH_SIZE, BRUSH_SIZE), pygame.SRCALPHA)
        for k in range(3):
            a = math.radians(f * 120 / BRUSH_FRAMES + k * 120)
            e = (h + math.cos(a) * 6.4, h + math.sin(a) * 6.4)
            pygame.draw.line(s, (196, 200, 212), (h, h), e, 2)
            for da in (-0.35, 0.35):
                pygame.draw.line(s, (150, 156, 170), e, (h + math.cos(a + da) * 6.6, h + math.sin(a + da) * 6.6), 1)
        pygame.draw.circle(s, (70, 76, 92), (h, h), 2)
        pygame.draw.circle(s, (220, 226, 236), (h, h), 1)
        out.append(s.convert_alpha())
    return tuple(out)


def build_puffs():
    """Fumaca/poeira (A11): [estilo][raio][fade] Surfaces alfa macias (prontas, nunca por quadro)."""
    out = []
    for col in PUFF_COLORS:
        by_r = []
        for r in PUFF_RADII:
            fades = []
            for k in range(PUFF_FADES):
                a = 230 * (1 - k / PUFF_FADES)
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                for i in range(r, 0, -1):
                    pygame.draw.circle(s, col + (int(a * (1 - (i / r) ** 2) + 6),), (r, r), i)
                fades.append(s.convert_alpha())
            by_r.append(tuple(fades))
        out.append(tuple(by_r))
    return tuple(out)


def puff_img(puffs, style, size, f):
    """Imagem da particula de fumaca: cresce e some conforme a vida `f` (1 -> 0)."""
    r = size * (1.0 + (1.0 - f) * 1.4)
    ri = max(0, min(len(PUFF_RADII) - 1, int(r) - PUFF_RADII[0]))
    fi = max(0, min(PUFF_FADES - 1, int((1.0 - f) * PUFF_FADES)))
    return puffs[style][ri][fi]


# ---------------------------------------------------------------------------------- dados do robo
def atlas_parts(vis):
    """Tupla ordenada de (overlay, raridade) que desenham algo, a partir de p.vis (None = nenhuma)."""
    if not vis:
        return ()
    out = {}
    for nm, rar in vis.get("parts", ()):
        if nm in ATLAS_PARTS:
            out[nm] = max(int(rar), out.get(nm, -1))
    return tuple(sorted(out.items()))


def brush_count(vis):
    names = {nm for nm, _ in (vis or {}).get("parts", ())}
    return 2 if ("escova" in names or "vacuo" in names) else 1


class Art:
    """Tudo o que draw_player precisa de um jogador (referencias prontas; nada e criado por quadro)."""
    __slots__ = ("body", "low", "halo", "atlas", "brushes", "nbrush", "orbital", "radar", "modulo",
                 "turbina", "hot", "led", "key", "brush_off", "radar_off", "mod_off", "jet_off", "rad", "trail")

    def __init__(self, body, low, halo, atlas, brushes, vis, ch, led, key, trail=None):
        self.body, self.low, self.halo, self.atlas, self.brushes = body, low, halo, atlas, brushes
        self.led, self.key = led, key
        self.trail = trail                               # B13: imagens do rastro (build_trail) ou None
        parts = dict(atlas.key[3])
        self.nbrush = brush_count(vis)
        self.orbital = ch == "Orbital"
        self.rad = TITA_R if ch == "Titã" else PR
        self.radar = RAR_COLORS[parts["radar"]] if "radar" in parts else None
        self.modulo = RAR_COLORS[parts["modulo"]] if "modulo" in parts else None
        self.turbina = "turbina" in parts
        self.hot = bool((vis or {}).get("hot"))
        offs = (-BRUSH_OFF_DEG, BRUSH_OFF_DEG) if self.nbrush == 2 else (BRUSH_OFF_DEG,)
        h = BRUSH_SIZE // 2
        self.brush_off = tuple(tuple((int(round(math.cos(math.radians(d * 45 + g)) * (self.rad - 2))) - h,
                                      int(round(math.sin(math.radians(d * 45 + g)) * (self.rad - 2))) - h)
                                     for g in offs) for d in range(DIRS))
        self.radar_off = tuple(dir_offset(d, *RADAR_AB) for d in range(DIRS))
        self.mod_off = tuple(dir_offset(d, 2, -6) for d in range(DIRS))
        self.jet_off = tuple(dir_offset(d, -PR - 10, 0) for d in range(DIRS))


def warm_player(cache, key, vis):
    """Art de um jogador: (chassis, led, gk) + p.vis. Constroi so o que nao esta no cache."""
    ch, led, gk = key
    parts = atlas_parts(vis)
    look = (vis or {}).get("look") or {}
    lk = look_key(look)
    body = get_sprite(cache, ch, led, gk, False)
    low = get_sprite(cache, ch, led, gk, True)
    halo = _get(cache, ("halo", led), lambda: build_halo(led))
    atlas = _get(cache, ("ov", ch, led, gk, parts, lk), lambda: build_atlas(ch, led, gk, parts, lk))
    brushes = _get(cache, ("brush",), build_brushes)
    tid = look.get("trail")
    trail = _get(cache, ("trail", tid), lambda: build_trail(tid)) if tid else None
    return Art(body, low, halo, atlas, brushes, vis, ch, led, key, trail)


def get_puffs(cache):
    return _get(cache, ("puff",), build_puffs)


# ---------------------------------------------------------------------------------- API antiga
def sprite_key(t, p):
    """(chassis, led, gk) do jogador `p` do time `t` (pintura propria ou cor do time/goleiro)."""
    col = p.paint or (t.gk_color if p.role == "GK" else t.color)
    return (p.chassis, led_color(col), p.role == "GK")


def get_sprite(cache, ch, led, gk, low=False):
    """Corpo cacheado em `cache`; constroi so na primeira vez."""
    return _get(cache, (ch, led, gk, low), lambda: build_robot_sprite(ch, led, gk, low))


def build_ui_sprite(ch, led, gk, d=2, look=(None, None)):
    """Sprite 64x64 da UI (garagem/bancada): halo alfa + camadas do chassi viradas para baixo, com o
    adesivo e a antena cosmeticos (B13) quando houver."""
    s = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)
    _halo_alpha(s, led)
    u = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)
    _draw_chassis_under(u, ch, d, led)
    s.blit(u, (0, 0))
    s.blit(build_robot_sprite(ch, led, gk, False), (0, 0))
    o = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)
    _draw_chassis_over(o, ch, d, led)
    decal, antenna = look if look else (None, None)
    if decal:
        _draw_sticker(o, decal, *_pt(d, *DECAL_AB))
    if antenna:
        _draw_antenna(o, antenna, d, led)
    s.blit(o, (0, 0))
    return s.convert_alpha()


def robot_sprite(cache, rb):
    """Sprite (cacheado) de um robo da garagem, com a cor de pintura e o visual dele (UI)."""
    ch, led, gk = rb["chassis"], led_color(rb["paint"]), rb["role"] == "GK"
    lk = look_key(rb.get("look"))
    return _get(cache, ("ui", ch, led, gk, lk), lambda: build_ui_sprite(ch, led, gk, look=lk))


def robot_sprite_big(cache, rb, size=128):
    """Sprite da UI ampliado (vitrine da galeria de cosmeticos); escala feita uma vez e cacheada."""
    ch, led, gk = rb["chassis"], led_color(rb["paint"]), rb["role"] == "GK"
    lk = look_key(rb.get("look"))
    return _get(cache, ("ui_big", ch, led, gk, lk, size),
                lambda: pygame.transform.scale(robot_sprite(cache, rb), (size, size)))


def warm_sprites(cache, teams):
    """Pre-constroi tudo o que a partida desenha (corpo normal e `low`, halo, atlas de direcoes,
    escovas e fumaca) e guarda em cada jogador `p.art` (referencias prontas para o draw)."""
    get_puffs(cache)
    for t in teams:
        for p in t.players:
            p.art = warm_player(cache, sprite_key(t, p), getattr(p, "vis", None))
            p.vdir = None
            # B13: pool fixo do rastro (pontos reaproveitados; nada e alocado por quadro)
            p.trail_pts = [[0, 0] for _ in range(TRAIL_N)] if p.art.trail is not None else None
            p.trail_n = p.trail_h = 0
            p.trail_next = 0.0
