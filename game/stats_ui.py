# -*- coding: utf-8 -*-
"""Desenho das estatisticas da partida: cartao MELHOR DO JOGO, faixa compacta do MVP e o painel
ESTATISTICAS (tabela dos dois times + robo a robo). Usado na tela de fim da partida (soccer.Game), no card
do resumo do Modo Robos / campanha (RobotsUI.draw_round_body) e no resultado da carreira (CareerUI).

`ui` e qualquer objeto com text(s, size, color, **ancora), fit(s, size, maxw), panel(rect) e `g` (o Game:
g.screen, g.sprites). Regras: zero pygame.Surface por quadro (so pygame.draw, textos do cache do Game e o
sprite do robo cacheado em robot_art), Font(None) e texto Latin-1.
"""
import pygame

import match_stats as MS
import robot_art
from career_ui import DIM, GOLD, GREEN, LINE, PANEL, TEXT, vis

MVP_FILL = (30, 26, 8)              # fundo do cartao do MVP (dourado escuro)
MVP_EDGE = (255, 214, 90)
ROW_HI = (40, 34, 10)
TEAM_ROWS = (("POSSE", "poss"), ("CHUTES", "sh"), ("NO GOL", "sot"), ("PASSES", "pass"),
             ("DESARMES", "tk"), ("DRIBLES", "dr"), ("DEFESAS", "sv"))
PCOLS = (("G", "g", 30), ("A", "a", 30), ("CH", "sh", 34), ("PAS", "pc", 36), ("DES", "tk", 38),
         ("DEF", "sv", 36), ("NOTA", "nota", 44))


class Painter:
    """Adaptador do soccer.Game para as funcoes daqui (o Game nao tem fit/panel)."""

    def __init__(self, game):
        self.g = game

    def text(self, *a, **k):
        k.setdefault("shadow", False)
        self.g.text(*a, **k)

    def fit(self, s, size, maxw):
        f = self.g.font(size)
        if f.size(s)[0] <= maxw:
            return s
        while s and f.size(s + "..")[0] > maxw:
            s = s[:-1]
        return s + ".."

    def panel(self, rect, fill=PANEL):
        pygame.draw.rect(self.g.screen, fill, rect, border_radius=12)
        pygame.draw.rect(self.g.screen, LINE, rect, 2, border_radius=12)

    def sprite_for(self, row):
        """Retrato do robo da partida que acabou: o corpo ja pre-renderizado (Player.art, warm_sprites). Nunca
        constroi nada no desenho: sem arte pronta (teste/demo), sem retrato."""
        try:
            p = self.g.teams[row.get("team", 0)].players[row.get("idx", 0)]
        except (AttributeError, IndexError, TypeError):
            return False
        art = getattr(p, "art", None)
        return art.body if art is not None else False


def fnota(v):
    return ("%.1f" % float(v)).replace(".", ",")


def player_name(row):
    return row.get("name") or ("%s %d" % (MS.ROLE_PT.get(row.get("role"), "ROBO"), int(row.get("idx", 0)) + 1))


def _team_color(summary, t):
    try:
        return vis(summary["teams"][t].get("color") or (255, 255, 255))
    except (KeyError, IndexError, TypeError):
        return TEXT


def _sprite(ui, row, summary):
    """Sprite 64x64 do robo (cacheado em robot_art; construido so na 1a vez). Na tela de fim da partida
    (Painter) usa o corpo ja pronto do robo em campo."""
    own = getattr(ui, "sprite_for", None)
    if own is not None:
        s = own(row)
        return s or None
    ch = row.get("chassis")
    cache = getattr(ui.g, "sprites", None)
    if not ch or cache is None:
        return None
    paint = row.get("paint") or summary["teams"][row.get("team", 0)].get("color") or (0, 200, 255)
    rb = {"chassis": ch, "paint": list(paint)[:3], "role": row.get("role", "MID"), "look": None}
    try:
        return robot_art.robot_sprite(cache, rb)
    except Exception:  # noqa: BLE001  (chassi desconhecido: sem retrato)
        return None


def draw_mvp_card(ui, rect, summary):
    """Cartao MELHOR DO JOGO (retrato, nome, time, nota e numeros)."""
    r = pygame.Rect(rect)
    scr = ui.g.screen
    row = MS.mvp_row(summary)
    pygame.draw.rect(scr, MVP_FILL, r, border_radius=14)
    pygame.draw.rect(scr, MVP_EDGE, r, 3, border_radius=14)
    ui.text("MELHOR DO JOGO", 30, GOLD, center=(r.centerx, r.y + 26), shadow=True)
    if row is None:
        ui.text("Sem dados da partida.", 22, DIM, center=r.center)
        return
    t = row.get("team", 0)
    cy = r.y + 92
    pygame.draw.circle(scr, (60, 50, 14), (r.centerx, cy), 42)
    pygame.draw.circle(scr, MVP_EDGE, (r.centerx, cy), 42, 2)
    spr = _sprite(ui, row, summary)
    if spr is not None:
        scr.blit(spr, spr.get_rect(center=(r.centerx, cy)))
    ui.text(ui.fit(player_name(row), 34, r.w - 24), 34, TEXT, center=(r.centerx, r.y + 156), shadow=True)
    team = summary["teams"][t].get("name") or ""
    ui.text(ui.fit("%s - %s" % (MS.ROLE_PT.get(row.get("role"), ""), team.upper()), 22, r.w - 24), 22,
            _team_color(summary, t), center=(r.centerx, r.y + 184))
    ui.text(fnota(row.get("nota", 0)), 64, GOLD, center=(r.centerx - 40, r.y + 232), shadow=True)
    ui.text("NOTA", 20, DIM, midleft=(r.centerx + 6, r.y + 222))
    ui.text("de 10", 20, DIM, midleft=(r.centerx + 6, r.y + 242))
    lines = (("Gols", row.get("g", 0)), ("Assistências", row.get("a", 0)),
             ("Chutes (no gol)", "%d (%d)" % (row.get("sh", 0), row.get("sot", 0))),
             ("Passes certos", "%d/%d" % (row.get("pc", 0), row.get("pa", 0))),
             ("Desarmes", row.get("tk", 0)), ("Dribles", row.get("dr", 0)), ("Defesas", row.get("sv", 0)))
    y0 = r.y + 276
    step = min(26, max(18, (r.bottom - 12 - y0) // len(lines)))
    for k, (lab, v) in enumerate(lines):
        y = y0 + k * step
        if y + 10 > r.bottom:
            break
        ui.text(lab, 22, DIM, midleft=(r.x + 22, y + 10))
        ui.text(str(v), 24, TEXT, midright=(r.right - 22, y + 10))


def draw_mvp_strip(ui, rect, summary):
    """Faixa compacta do MVP (tela de fim da partida, por cima do campo)."""
    r = pygame.Rect(rect)
    row = MS.mvp_row(summary)
    if row is None:
        return
    scr = ui.g.screen
    pygame.draw.rect(scr, MVP_FILL, r, border_radius=12)
    pygame.draw.rect(scr, MVP_EDGE, r, 2, border_radius=12)
    spr = _sprite(ui, row, summary)
    if spr is not None:
        scr.blit(spr, spr.get_rect(center=(r.x + 44, r.centery)))
    t = row.get("team", 0)
    ui.text("MELHOR DO JOGO", 20, GOLD, topleft=(r.x + 86, r.y + 8))
    ui.text(ui.fit(player_name(row), 32, r.w - 230), 32, TEXT, topleft=(r.x + 86, r.y + 26), shadow=True)
    team = summary["teams"][t].get("name") or ""
    ui.text(ui.fit(team.upper() + "  -  " + MS.mvp_line(row), 20, r.w - 200), 20, _team_color(summary, t),
            topleft=(r.x + 86, r.y + 56))
    ui.text(fnota(row.get("nota", 0)), 48, GOLD, midright=(r.right - 16, r.centery - 6), shadow=True)
    ui.text("NOTA", 18, DIM, midright=(r.right - 18, r.bottom - 12))


def _team_val(row, key):
    if key == "poss":
        return "%d%%" % row.get("poss", 0)
    if key == "pass":
        return "%d/%d" % (row.get("pc", 0), row.get("pa", 0))
    return str(row.get(key, 0))


def draw_stats_panel(ui, rect, summary, title=True):
    """Painel ESTATISTICAS: os dois times lado a lado e a tabela robo a robo (G, A, chutes, passes certos,
    desarmes, defesas, nota). O MVP fica destacado."""
    r = pygame.Rect(rect)
    scr = ui.g.screen
    ui.panel(r)
    teams = summary.get("teams") or ({}, {})
    x0 = r.x + 18
    y = r.y + 10
    if title:
        ui.text("ESTATÍSTICAS", 22, GOLD, topleft=(x0, y))
        if summary.get("sim"):
            ui.text("estimadas: jogo simulado", 20, DIM, midright=(r.right - 18, y + 8))
        y += 28
    # ---- times
    cx = r.centerx
    lw = r.w // 2 - 120
    ui.text(ui.fit((teams[0].get("name") or "").upper(), 24, lw), 24, _team_color(summary, 0),
            midright=(cx - 110, y + 10))
    ui.text(ui.fit((teams[1].get("name") or "").upper(), 24, lw), 24, _team_color(summary, 1),
            midleft=(cx + 110, y + 10))
    y += 26
    for k, (lab, key) in enumerate(TEAM_ROWS):
        yy = y + k * 22
        if k % 2 == 0:
            pygame.draw.rect(scr, (16, 38, 58), (r.x + 12, yy, r.w - 24, 21), border_radius=4)
        a, b = _team_val(teams[0], key), _team_val(teams[1], key)
        ui.text(lab, 20, DIM, center=(cx, yy + 11))
        ui.text(a, 22, TEXT, midright=(cx - 110, yy + 11))
        ui.text(b, 22, TEXT, midleft=(cx + 110, yy + 11))
        if key == "poss":                                   # barra de posse
            p0 = max(0, min(100, int(teams[0].get("poss", 50))))
            bx, bw = r.x + 22, cx - 170 - (r.x + 22)
            if bw > 40:
                pygame.draw.rect(scr, (8, 14, 24), (bx, yy + 6, bw, 9), border_radius=3)
                pygame.draw.rect(scr, _team_color(summary, 0), (bx + bw - bw * p0 // 100, yy + 6, bw * p0 // 100, 9),
                                 border_radius=3)
                bx2 = cx + 170
                bw2 = r.right - 22 - bx2
                pygame.draw.rect(scr, (8, 14, 24), (bx2, yy + 6, bw2, 9), border_radius=3)
                pygame.draw.rect(scr, _team_color(summary, 1), (bx2, yy + 6, bw2 * (100 - p0) // 100, 9),
                                 border_radius=3)
    y += len(TEAM_ROWS) * 22 + 8
    pygame.draw.line(scr, LINE, (r.x + 12, y), (r.right - 12, y), 1)
    y += 6
    # ---- robo a robo (2 tabelas lado a lado)
    players = summary.get("players") or ()
    mvp = summary.get("mvp")
    colw = (r.w - 36) // 2
    rows_h = max(18, min(26, (r.bottom - 10 - (y + 22)) // 5))
    for t in (0, 1):
        tx = r.x + 12 + t * (colw + 12)
        right = tx + colw
        x = right
        heads = []
        for lab, key, w in reversed(PCOLS):
            heads.append((lab, key, x))
            x -= w
        name_w = x - tx - 8
        for lab, key, xx in heads:
            ui.text(lab, 18, DIM, midright=(xx, y + 9))
        ui.text("ROBÔ", 18, DIM, midleft=(tx + 6, y + 9))
        mine = [(i, p) for i, p in enumerate(players) if p.get("team") == t]
        for k, (i, p) in enumerate(mine[:5]):
            yy = y + 20 + k * rows_h
            if i == mvp:
                pygame.draw.rect(scr, ROW_HI, (tx, yy, colw, rows_h - 2), border_radius=4)
                pygame.draw.rect(scr, MVP_EDGE, (tx, yy, colw, rows_h - 2), 1, border_radius=4)
            nm = MS.ROLE_PT.get(p.get("role"), "") + " " + player_name(p)
            ui.text(ui.fit(nm, 20, name_w), 20, GOLD if i == mvp else TEXT, midleft=(tx + 6, yy + rows_h // 2 - 1))
            for lab, key, xx in heads:
                v = p.get(key, 0)
                s = fnota(v) if key == "nota" else str(v)
                col = GOLD if key == "nota" and i == mvp else (GREEN if key in ("g", "a") and v else TEXT)
                ui.text(s, 20, col, midright=(xx, yy + rows_h // 2 - 1))


def draw_stats_view(ui, rect, summary):
    """Cartao do MVP a esquerda + painel ESTATISTICAS a direita, dentro de `rect`."""
    r = pygame.Rect(rect)
    if not isinstance(summary, dict) or not summary.get("players"):
        ui.panel(r)
        ui.text("Sem estatísticas desta partida.", 26, DIM, center=r.center)
        return
    cw = 300
    draw_mvp_card(ui, (r.x, r.y, cw, r.h), summary)
    draw_stats_panel(ui, (r.x + cw + 12, r.y, r.w - cw - 12, r.h), summary)


def all_strings():
    """Textos fixos desta tela (teste de Latin-1)."""
    out = {"MELHOR DO JOGO", "ESTATÍSTICAS", "estimadas: jogo simulado", "NOTA", "de 10", "ROBÔ",
           "Sem estatísticas desta partida.", "Sem dados da partida.", "Gols", "Assistências", "Chutes (no gol)",
           "Passes certos", "Desarmes", "Dribles", "Defesas"}
    out |= {lab for lab, _ in TEAM_ROWS} | {lab for lab, _, _ in PCOLS}
    return out
