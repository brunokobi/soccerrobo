# -*- coding: utf-8 -*-
"""Tela do AMISTOSO: escolha dos times e das formacoes dos dois lados antes da partida.

Estado do jogo "friendly" (menu 1 = voce x CPU: o J1 escolhe os dois lados; menu 2 = J1 x J2: WASD mexe no
lado esquerdo e as setas no direito, ao mesmo tempo). Teclado: cima/baixo escolhe a linha (TIME/FORMACAO),
esquerda/direita troca; TAB (modo 1) passa para o outro lado; R = ALEATORIO; ENTER/ESPACO = JOGAR; ESC =
menu. Mouse: setas < >, clique na linha, roda do mouse sobre a linha, botoes VOLTAR/ALEATORIO/JOGAR.

A escolha fica na sessao (Game.friendly_last) e nas prefs (fr_t0/fr_t1/fr_f0/fr_f1, gravadas quando a partida
comeca). Desenho sem Surface por quadro: textos pelo cache do Game (text_img), formas com pygame.draw direto
na tela. Sorteio do ALEATORIO com RNG proprio (nunca o random global nem o do motor).
"""
import random

import pygame

import crowd
import formation_ui
import friendly
import prefs
import sfx
from robot_art import led_color

W, H = 1100, 700
PANEL = (10, 24, 44)
PANEL_HI = (14, 40, 66)
LINE = (0, 150, 190)
NEON = (0, 230, 255)
TEXT = (235, 245, 250)
DIM = (150, 185, 205)
GOLD = (255, 214, 90)
SRC_COLORS = {"AMISTOSO": (120, 200, 255), "CARREIRA": (255, 214, 90), "CAMPANHA": (210, 170, 255),
              "MODO ROBÔS": (90, 255, 210)}
ROWS = ("team", "form")
PANEL_W, PANEL_H, PANEL_Y = 480, 470, 118
PANEL_X = (34, W - 34 - 480)


def shield_points(cx, top, w, h):
    """Escudo simples (pentagono com bico embaixo), em pontos inteiros."""
    hw = w // 2
    return [(cx - hw, top), (cx + hw, top), (cx + hw, top + h * 55 // 100), (cx, top + h),
            (cx - hw, top + h * 55 // 100)]


class FriendlyUI:
    def __init__(self, game):
        self.g = game
        self.mode = 1
        self.sel = friendly.sanitize(None)
        self.focus = [0, 0]                 # linha focada de cada lado (0 = TIME, 1 = FORMACAO)
        self.side = 0                       # lado ativo no modo 1
        self.buttons = []                   # (rect, fn) do ultimo desenho
        self.rows = {}                      # (lado, linha) -> rect (clique/roda do mouse)
        self.rng = random.Random()          # ALEATORIO: RNG proprio (semente do sistema)

    # ------------------------------------------------------------------ estado
    def saved(self):
        """Ultima escolha: a da sessao; senao a das prefs; senao o padrao."""
        last = getattr(self.g, "friendly_last", None)
        if last:
            return friendly.sanitize(last)
        try:
            t = (prefs.get("fr_t0"), prefs.get("fr_t1"))
            f = (prefs.get("fr_f0"), prefs.get("fr_f1"))
        except Exception:  # noqa: BLE001
            t = f = (None, None)
        if None in t:
            t = None
        if None in f:
            f = None
        return friendly.sanitize({"teams": t, "forms": f})

    def open(self, mode):
        self.mode = 1 if mode == 1 else 2
        self.sel = self.saved()
        self.focus = [0, 0]
        self.side = 0
        self.buttons = []
        self.g.state = "friendly"

    def labels(self):
        if self.mode == 1:
            return ("VOCÊ", "CPU")
        return ("JOGADOR 1  (WASD)", "JOGADOR 2  (SETAS)")

    def set_team(self, side, tid):
        teams = list(self.sel["teams"])
        if tid == teams[1 - side] or tid not in friendly.BY_ID:
            return False
        teams[side] = tid
        self.sel = {"teams": tuple(teams), "forms": self.sel["forms"]}
        return True

    def change(self, side, row, step):
        if row == 0:
            cur = self.sel["teams"]
            self.set_team(side, friendly.cycle_team(cur[side], cur[1 - side], step))
        else:
            forms = list(self.sel["forms"])
            forms[side] = friendly.cycle_formation(forms[side], step)
            self.sel = {"teams": self.sel["teams"], "forms": tuple(forms)}
        sfx.play("click")

    def randomize(self):
        self.sel = friendly.sanitize(friendly.random_pick(self.rng))
        sfx.play("toggle")

    def back(self):
        sfx.play("back")
        self.g.state = "menu"

    def start(self):
        sel = friendly.sanitize(self.sel)
        self.g.friendly_last = sel
        try:
            prefs.update({"fr_t0": sel["teams"][0], "fr_t1": sel["teams"][1],
                          "fr_f0": sel["forms"][0], "fr_f1": sel["forms"][1]})
        except Exception:  # noqa: BLE001
            pass
        sfx.play("click")
        self.g.new_match(self.mode, crowd.FRIENDLY_VENUE, sel)

    # ------------------------------------------------------------------ eventos
    def move_focus(self, side, step):
        """Modo 2: cada jogador anda nas linhas do seu lado. Modo 1: TIME/FORMACAO dos dois lados em sequencia."""
        if self.mode == 2:
            self.focus[side] = (self.focus[side] + step) % 2
            return
        k = (self.side * 2 + self.focus[self.side] + step) % 4
        self.side, self.focus[k // 2] = k // 2, k % 2

    def handle_event(self, e):
        K = pygame
        if e.type == K.KEYDOWN:
            k = e.key
            if k == K.K_ESCAPE:
                return self.back()
            if k in (K.K_RETURN, K.K_KP_ENTER, K.K_SPACE):
                return self.start()
            if k == K.K_r:
                return self.randomize()
            if self.mode == 1:
                if k in (K.K_UP, K.K_w):
                    self.move_focus(0, -1)
                elif k in (K.K_DOWN, K.K_s):
                    self.move_focus(0, 1)
                elif k in (K.K_LEFT, K.K_a):
                    self.change(self.side, self.focus[self.side], -1)
                elif k in (K.K_RIGHT, K.K_d):
                    self.change(self.side, self.focus[self.side], 1)
                elif k == K.K_TAB:
                    self.side = 1 - self.side
                return
            for side, (up, down, left, right) in ((0, (K.K_w, K.K_s, K.K_a, K.K_d)),
                                                  (1, (K.K_UP, K.K_DOWN, K.K_LEFT, K.K_RIGHT))):
                if k in (up, down):
                    self.move_focus(side, -1 if k == up else 1)
                elif k in (left, right):
                    self.change(side, self.focus[side], -1 if k == left else 1)
            return
        if e.type == K.MOUSEBUTTONDOWN and e.button == 1:
            for r, fn in reversed(self.buttons):
                if r.collidepoint(e.pos):
                    self.buttons = []           # um clique por desenho
                    fn()
                    return
            for (side, row), r in self.rows.items():
                if r.collidepoint(e.pos):
                    self.side, self.focus[side] = side, row
                    return
        elif e.type == K.MOUSEWHEEL:
            pos = pygame.mouse.get_pos()
            for (side, row), r in self.rows.items():
                if r.collidepoint(pos) and e.y:
                    self.side, self.focus[side] = side, row
                    self.change(side, row, -1 if e.y > 0 else 1)
                    return

    # ------------------------------------------------------------------ desenho
    def text(self, s, size, color, **k):
        k.setdefault("shadow", False)
        self.g.text(s, size, color, **k)

    def fit(self, s, size, maxw):
        f = self.g.font(size)
        if f.size(s)[0] <= maxw:
            return s
        while s and f.size(s + "..")[0] > maxw:
            s = s[:-1]
        return s + ".."

    def btn(self, rect, label, fn, fill, border, size=30):
        scr = self.g.screen
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(scr, tuple(min(255, v + 30) for v in fill) if hover else fill, rect, border_radius=12)
        pygame.draw.rect(scr, NEON if hover else border, rect, 3, border_radius=12)
        self.text(label, size, TEXT, center=rect.center)
        self.buttons.append((rect, fn))

    def arrow(self, rect, left, fn, on):
        scr = self.g.screen
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(scr, (0, 90, 125) if hover else (6, 30, 52), rect, border_radius=8)
        pygame.draw.rect(scr, NEON if (hover or on) else LINE, rect, 2, border_radius=8)
        cx, cy = rect.center
        d = -1 if left else 1
        pygame.draw.polygon(scr, NEON if on else TEXT, [(cx - 7 * d, cy - 11), (cx + 8 * d, cy), (cx - 7 * d, cy + 11)])
        self.buttons.append((rect, fn))

    def focused(self, side, row):
        if self.focus[side] != row:
            return False
        return self.mode == 2 or self.side == side

    def draw(self):
        g, scr = self.g, self.g.screen
        scr.blit(g.menu_bg, (0, 0))
        self.buttons = []
        self.rows = {}
        self.text("AMISTOSO", 76, (0, 120, 170), center=(W // 2 + 3, 49))
        self.text("AMISTOSO", 76, (225, 252, 255), center=(W // 2, 46))
        sub = "escolha o seu time e o da CPU" if self.mode == 1 else "J1 e J2 escolhem ao mesmo tempo"
        self.text(sub, 28, (120, 225, 245), center=(W // 2, 92))
        for side in (0, 1):
            self.draw_side(side)
        self.text("VS", 64, (0, 120, 170), center=(W // 2 + 2, PANEL_Y + 132))
        self.text("VS", 64, GOLD, center=(W // 2, PANEL_Y + 130))
        y = PANEL_Y + PANEL_H + 18
        self.btn(pygame.Rect(34, y, 220, 58), "VOLTAR", self.back, (40, 44, 58), (120, 130, 150), 30)
        self.btn(pygame.Rect(W // 2 - 140, y, 280, 58), "ALEATÓRIO (R)", self.randomize, (56, 36, 100),
                 (150, 110, 220), 30)
        self.btn(pygame.Rect(W - 34 - 260, y, 260, 58), "JOGAR (ENTER)", self.start, (0, 110, 70),
                 (60, 230, 150), 32)
        if self.mode == 1:
            hint = "setas / WASD: escolher   |   TAB: outro lado   |   ENTER: jogar   |   ESC: menu"
        else:
            hint = "J1: WASD (lado esquerdo)   |   J2: setas (lado direito)   |   ENTER: jogar   |   ESC: menu"
        self.text(hint, 22, (170, 205, 220), center=(W // 2, H - 18))

    def draw_side(self, side):
        g, scr = self.g, self.g.screen
        tid, fid = self.sel["teams"][side], self.sel["forms"][side]
        t, form = friendly.team(tid), friendly.formation(fid)
        x = PANEL_X[side]
        pr = pygame.Rect(x, PANEL_Y, PANEL_W, PANEL_H)
        active = self.mode == 2 or self.side == side
        pygame.draw.rect(scr, PANEL, pr, border_radius=14)
        pygame.draw.rect(scr, NEON if active else LINE, pr, 3 if active else 2, border_radius=14)
        col = self.colors()[side]
        lc = led_color(col)
        self.text(self.labels()[side], 30, lc, center=(pr.centerx, pr.y + 24))
        # ---- TIME
        r = pygame.Rect(x + 14, pr.y + 46, PANEL_W - 28, 128)
        self.rows[(side, 0)] = r
        on = self.focused(side, 0)
        pygame.draw.rect(scr, PANEL_HI if on else PANEL, r, border_radius=10)
        pygame.draw.rect(scr, NEON if on else (30, 80, 110), r, 3 if on else 1, border_radius=10)
        self.arrow(pygame.Rect(r.x + 8, r.centery - 22, 34, 44), True, lambda: self.change(side, 0, -1), on)
        self.arrow(pygame.Rect(r.right - 42, r.centery - 22, 34, 44), False, lambda: self.change(side, 0, 1), on)
        sx = r.x + 82
        pts = shield_points(sx, r.y + 22, 62, 78)
        pygame.draw.polygon(scr, col, pts)
        pygame.draw.polygon(scr, lc if sum(col) < 200 else (240, 250, 255), pts, 3)
        pygame.draw.line(scr, (255, 255, 255), (sx - 18, r.y + 46), (sx + 18, r.y + 46), 3)
        self.text(t["name"][:1].upper(), 34, (10, 14, 24) if sum(col) > 520 else (255, 255, 255),
                  center=(sx, r.y + 66))
        tx = r.x + 128
        maxw = r.right - 50 - tx
        self.text(self.fit(t["name"].upper(), 34, maxw), 34, TEXT, midleft=(tx, r.y + 30))
        self.text(t["src"], 22, SRC_COLORS.get(t["src"], DIM), midleft=(tx, r.y + 58))
        idx = "%d / %d" % (friendly.TEAM_IDS.index(tid) + 1, len(friendly.TEAM_IDS))
        self.text(idx, 22, DIM, midright=(r.right - 50, r.y + 58))
        ovr = t["ovr"]
        self.text("FORÇA %d" % ovr, 24, GOLD, midleft=(tx, r.y + 92))
        bar = pygame.Rect(tx + 92, r.y + 86, maxw - 92, 12)
        pygame.draw.rect(scr, (24, 40, 60), bar, border_radius=6)
        frac = (ovr - 40) / 45.0
        fill = bar.copy()
        fill.w = max(6, int(bar.w * min(1.0, max(0.0, frac))))
        pygame.draw.rect(scr, GOLD if ovr < 70 else (110, 230, 120), fill, border_radius=6)
        # ---- FORMACAO
        r = pygame.Rect(x + 14, pr.y + 184, PANEL_W - 28, 74)
        self.rows[(side, 1)] = r
        on = self.focused(side, 1)
        pygame.draw.rect(scr, PANEL_HI if on else PANEL, r, border_radius=10)
        pygame.draw.rect(scr, NEON if on else (30, 80, 110), r, 3 if on else 1, border_radius=10)
        self.arrow(pygame.Rect(r.x + 8, r.centery - 22, 34, 44), True, lambda: self.change(side, 1, -1), on)
        self.arrow(pygame.Rect(r.right - 42, r.centery - 22, 34, 44), False, lambda: self.change(side, 1, 1), on)
        self.text("%s  %s" % (form["name"], form["code"]), 32, TEXT, center=(r.centerx, r.y + 24))
        self.text(form["desc"], 22, DIM, center=(r.centerx, r.y + 52))
        # ---- mini-campo (lado 0 ataca para a direita, lado 1 para a esquerda, como na partida)
        self.draw_pitch(pygame.Rect(x + 60, pr.y + 272, PANEL_W - 120, 182), form, side, col)

    def draw_pitch(self, r, form, side, col):
        """Mini-campo da formacao (desenho compartilhado com Campanha/Modo Robos/Carreira: formation_ui)."""
        formation_ui.draw_pitch(self.g.screen, r, form, side, col)

    def colors(self):
        """Cores dos dois lados como ficarao na partida (cores parecidas: o lado 1 muda, igual ao motor)."""
        a = tuple(friendly.team(self.sel["teams"][0])["color"])
        b = tuple(friendly.team(self.sel["teams"][1])["color"])
        if sum(abs(x - y) for x, y in zip(led_color(a), led_color(b))) < 130:
            b = (235, 235, 235) if sum(a) < 600 else (0, 230, 255)
        return a, b
