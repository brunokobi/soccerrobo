# -*- coding: utf-8 -*-
"""Arte dos robos em campo: desenho e cache dos sprites (aspirador visto de cima).

Extraido de soccer.py (Fase 4, passo 0.4) sem mudanca visual. O cache e um dict
`{(chassis, led, gk, low): Surface}` que pertence ao chamador (Game.sprites);
as funcoes daqui so leem/escrevem nele. Os sprites sao criados sob demanda
(nunca por frame depois de aquecidos) e usam convert_alpha(), entao so podem
ser construidos depois de pygame.display.set_mode().
"""
import math

import pygame

SPRITE_SIZE = 64        # sprite quadrado; o centro fica em (32, 32)
PR = 14                 # raio do corpo no sprite = raio fisico do jogador (soccer.PR)


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


def build_robot_sprite(chassis, led, gk, low):
    """Aspirador visto de cima: sombra, halo, anel de LED, corpo metalico. Sem rotacao em runtime."""
    size = SPRITE_SIZE
    c = size // 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    led = scale_color(led, 0.4) if low else led
    pygame.draw.ellipse(s, (0, 0, 0, 110), (c - PR + 1, c + PR - 9, PR * 2, 18))
    for r in range(c - 2, PR, -1):                       # halo
        k = (1 - (r - PR) / (c - 2 - PR)) ** 2
        pygame.draw.circle(s, led + (int((22 if low else 70) * k),), (c, c), r)
    ring = 5 if chassis == "Tanque" else 3
    if chassis == "Velocista":                           # aleta traseira
        pygame.draw.polygon(s, led, [(c - 7, c - PR + 2), (c + 7, c - PR + 2), (c, c - PR - 7)])
        pygame.draw.polygon(s, (20, 24, 32), [(c - 7, c - PR + 2), (c + 7, c - PR + 2), (c, c - PR - 7)], 1)
    pygame.draw.circle(s, led, (c, c), PR)
    pygame.draw.circle(s, (12, 16, 24), (c, c), PR, 1)
    body = PR - ring
    for i in range(body, 0, -1):                         # domo metalico com brilho
        t = 1 - i / body
        v = int(46 + 92 * t)
        pygame.draw.circle(s, (v, v + 4, v + 14), (c - int(t * 3), c - int(t * 3)), i)
    pygame.draw.circle(s, (20, 24, 34), (c, c), body, 1)
    pygame.draw.circle(s, (190, 200, 215), (c - 4, c - 4), 2)   # reflexo
    if chassis == "Tanque":                              # placas de blindagem
        for sx in (-1, 1):
            pygame.draw.line(s, (25, 28, 38), (c + sx * 3, c - body + 1), (c + sx * 3, c + body - 1), 2)
    if gk or chassis == "Goleiro":                       # LEDs extras
        for k in range(8):
            a = k * math.pi / 4
            pygame.draw.circle(s, led, (int(c + math.cos(a) * (PR - 6)), int(c + math.sin(a) * (PR - 6))), 1)
    return s.convert_alpha()


def sprite_key(t, p):
    """(chassis, led, gk) do jogador `p` do time `t` (pintura propria ou cor do time/goleiro)."""
    col = p.paint or (t.gk_color if p.role == "GK" else t.color)
    return (p.chassis, led_color(col), p.role == "GK")


def get_sprite(cache, ch, led, gk, low=False):
    """Sprite cacheado em `cache`; constroi so na primeira vez."""
    key = (ch, led, gk, low)
    spr = cache.get(key)
    if spr is None:
        spr = cache[key] = build_robot_sprite(ch, led, gk, low)
    return spr


def robot_sprite(cache, rb):
    """Sprite (cacheado) de um robo da garagem, com a cor de pintura dele."""
    return get_sprite(cache, rb["chassis"], led_color(rb["paint"]), rb["role"] == "GK")


def warm_sprites(cache, teams):
    """Pre-constroi os sprites (normal e `low`) de todos os jogadores dos times."""
    for t in teams:
        for p in t.players:
            ch, led, gk = sprite_key(t, p)
            for low in (False, True):
                if (ch, led, gk, low) not in cache:
                    cache[(ch, led, gk, low)] = build_robot_sprite(ch, led, gk, low)
