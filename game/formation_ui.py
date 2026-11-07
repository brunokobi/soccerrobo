# -*- coding: utf-8 -*-
"""Desenho compartilhado das FORMACOES (game/formations.py): mini-campo com os 5 pontos e o seletor compacto
"FORMACAO: < EQUILIBRADA 1-2-1 >" usado na Campanha, no Modo Robos e na Carreira (o Amistoso usa o mesmo
mini-campo, maior).

Sem pygame.Surface por quadro: so pygame.draw direto na tela e textos pelo cache do Game (ui.text / ui.fit,
Font(None), Latin-1). Os cliques sao registrados por `register(rect, fn)` (cada tela tem o seu formato de
botao). Teclado (nas telas que usam o seletor): setas esquerda/direita ou F (Shift+F volta) -> key_step().
"""
import pygame

import formations
from robot_art import led_color

PITCH_FILL = (16, 70, 46)
PITCH_LINE = (150, 220, 180)
GOLD = (255, 214, 90)
NEON = (0, 230, 255)
LINE = (0, 150, 190)
CARD = (10, 24, 44)
CARD_HI = (14, 40, 66)
TEXT = (235, 245, 250)
DIM = (150, 185, 205)
GK_COLORS = ((250, 200, 40), (70, 205, 130))


def draw_pitch(scr, r, form, side, col, dot=11, arrow=True, gk_color=None):
    """Mini-campo em `r` com os 5 pontos da formacao (com o push do bloco). side 0 ataca para a direita, 1 para
    a esquerda (como na partida). dot = raio dos pontos; arrow = seta do gol atacado."""
    small = dot < 8
    w = 1 if small else 2
    pygame.draw.rect(scr, PITCH_FILL, r, border_radius=3 if small else 6)
    pygame.draw.rect(scr, PITCH_LINE, r, w, border_radius=3 if small else 6)
    pygame.draw.line(scr, PITCH_LINE, (r.centerx, r.y), (r.centerx, r.bottom - 1), w)
    pygame.draw.circle(scr, PITCH_LINE, r.center, max(3, r.h // 6), w)
    gh = r.h // 4
    for gx, d in ((r.x, 1), (r.right - 1, -1)):
        box = pygame.Rect(0, r.centery - gh, max(3, r.w // 9), 2 * gh)
        if d == 1:
            box.left = gx
        else:
            box.right = gx + 1
        pygame.draw.rect(scr, PITCH_LINE, box, w)
    d = 1 if side == 0 else -1
    if arrow:
        ax = r.right - 18 if side == 0 else r.x + 18
        pygame.draw.polygon(scr, GOLD, [(ax + 8 * d, r.y + 14), (ax - 6 * d, r.y + 6), (ax - 6 * d, r.y + 22)])
    lc = led_color(col)
    push = form.get("push", 0.0)
    gk = gk_color or GK_COLORS[side]
    for i, (fx, fy) in enumerate(form["pts"]):
        if i:
            fx = min(0.92, max(0.10, fx + push))
        px = r.x + int(fx * r.w) if side == 0 else r.right - int(fx * r.w)
        py = r.y + int(fy * r.h)
        c = gk if i == 0 else lc
        if not small:
            pygame.draw.circle(scr, (6, 12, 20), (px + 2, py + 2), dot)
        pygame.draw.circle(scr, c, (px, py), dot)
        pygame.draw.circle(scr, (255, 255, 255), (px, py), dot, 1 if small else 2)


def _arrow(scr, rect, left, on):
    hover = rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(scr, (0, 90, 125) if hover else (6, 30, 52), rect, border_radius=6)
    pygame.draw.rect(scr, NEON if (hover or on) else LINE, rect, 2, border_radius=6)
    cx, cy = rect.center
    d = -1 if left else 1
    pygame.draw.polygon(scr, NEON if on else TEXT, [(cx - 5 * d, cy - 8), (cx + 6 * d, cy), (cx - 5 * d, cy + 8)])


def draw_selector(ui, rect, fid, change, register, col=(0, 170, 255), label="FORMAÇÃO", hint="(F)"):
    """Seletor compacto (cartao neon): seta <, mini-campo, rotulo + "NOME 1-2-1", seta >. Clique nas setas muda
    a formacao (change(-1/+1)); clique no corpo avanca (+1). ui: tela com .g.screen, .text(s, size, color, **pos)
    e .fit(s, size, maxw). register(rect, fn): registra o clique no formato da tela. Devolve o Rect."""
    scr = ui.g.screen
    r = pygame.Rect(rect)
    hover = r.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(scr, CARD_HI if hover else CARD, r, border_radius=10)
    pygame.draw.rect(scr, NEON if hover else LINE, r, 2, border_radius=10)
    form = formations.get(fid)
    aw = 26
    ah = min(36, r.h - 12)
    left = pygame.Rect(r.x + 6, r.centery - ah // 2, aw, ah)
    right = pygame.Rect(r.right - 6 - aw, r.centery - ah // 2, aw, ah)
    register(r, lambda: change(1))                     # corpo: proxima (registrado antes: as setas ganham)
    register(left, lambda: change(-1))
    register(right, lambda: change(1))
    _arrow(scr, left, True, hover)
    _arrow(scr, right, False, hover)
    ph = r.h - 14
    pw = int(ph * 1.55)
    pr = pygame.Rect(left.right + 8, r.centery - ph // 2, pw, ph)
    draw_pitch(scr, pr, form, 0, col, dot=max(3, ph // 9), arrow=False)
    tx = pr.right + 10
    maxw = right.x - 8 - tx
    big = 26 if r.h >= 50 else 22
    if r.h >= 44:
        ui.text(label + ("  " + hint if hint else ""), 18, DIM, midleft=(tx, r.y + r.h * 30 // 100))
        ui.text(ui.fit("%s  %s" % (form["name"], form["code"]), big, maxw), big, TEXT,
                midleft=(tx, r.y + r.h * 70 // 100))
    else:
        ui.text(ui.fit("%s: %s  %s" % (label, form["name"], form["code"]), big, maxw), big, TEXT,
                midleft=(tx, r.centery))
    return r


def key_step(e):
    """Passo do seletor para um KEYDOWN (setas esquerda/direita, F = proxima, Shift+F = anterior) ou 0."""
    if e.type != pygame.KEYDOWN:
        return 0
    if e.key == pygame.K_LEFT:
        return -1
    if e.key == pygame.K_RIGHT:
        return 1
    if e.key == pygame.K_f:
        return -1 if getattr(e, "mod", 0) & pygame.KMOD_SHIFT else 1
    return 0
