# -*- coding: utf-8 -*-
"""Escudos dos times em PIXEL ART desenhados por codigo (nenhuma imagem externa, nada copiado de clube real).

Uso: crests.get(nome, cor, altura) -> Surface (SRCALPHA) em cache. O MESMO time (nome + cor) gera sempre o
MESMO escudo: tudo sai de um hash estavel do nome (zlib.crc32, nunca hash() nem o random global).

Tecnica (mesmo estilo de portraits_pixel/scenes_pixel)
- Tela logica pequena (LW x LH = 32 x 40) pintada pixel a pixel num buffer RGBA e ampliada por vizinho
  mais proximo (multiplos inteiros: 40, 80, 120, 160 px de altura). Alturas que nao sao multiplo de 40
  ampliam para o multiplo de cima e reduzem com smoothscale (fica nitido). Abaixo de 40 px o layout
  "compacto" tira a faixa com as iniciais (ilegivel nesse tamanho) e centraliza o medalhao.
- Formato (7: classico, redondo, losango, hexagono, pontudo, frances, oval) + padrao (8: liso, faixa,
  listras, metade, diagonal, quartos, chevron, aro) com a cor do time e uma cor secundaria escolhida com
  contraste minimo; luz em cima/esquerda e sombra embaixo/direita (rampa de 4 tons), borda dourada e
  contorno escuro de 1 px logico.
- Medalhao escuro com SIMBOLO 15x15 colorido (contorno automatico), escolhido por palavra-chave do nome
  (tubarao, leao, dragao, raio, chama, coroa, ... ver SYMBOL_RULES) com fallback deterministico.
- Faixa (fita com pontas dobradas) com ate 3 iniciais numa fonte pixel 5x7.
- Escudos ESPECIAIS (chefes/rivais da campanha, SPECIALS): borda dupla, coroa ou estrelas em cima,
  louros ou asas dos lados.
- Time do jogador: get(..., custom={"sym": id, "shape": id}) troca simbolo/formato (campo opcional
  "crest" do time na garagem; sanitize()).

Cache: LRU por (nome, cor, altura, custom) com limite em bytes (CACHE_MAX_BYTES) + cache da arte logica
(LRU por contagem). warm() gera fora do desenho; draw/blit so faz get() (acerto de cache, zero Surface).
STATS conta geracoes, acertos e bytes (testes e medicao).
"""
import math
import re
import time
import unicodedata
import zlib
from collections import OrderedDict

import pygame

LW, LH = 32, 40                        # tela logica
CACHE_MAX_BYTES = 4 * 1024 * 1024      # limite do cache de Surfaces prontas
BASE_CACHE_MAX = 160                   # artes logicas (32x40, ~5 KB cada)
STATS = {"gen": 0, "base_gen": 0, "hit": 0, "miss": 0, "bytes": 0, "gen_ms": 0.0}

INK = (22, 14, 32)                     # contorno
GOLD = ((255, 236, 150), (250, 196, 64), (196, 132, 34), (120, 70, 24))   # luz, base, sombra, funda
CREAM = (244, 236, 216)
NAVY = (30, 28, 58)

# ------------------------------------------------------------------------------------------- cores
PAL = {
    "x": INK, "k": (18, 18, 26), "W": (255, 255, 250), "#": (238, 230, 214), "+": (184, 176, 170),
    "-": (120, 116, 130),
    "Y": (255, 244, 150), "y": (255, 208, 56), "g": (238, 168, 40), "G": (176, 108, 26),
    "o": (248, 132, 36), "r": (226, 52, 48), "R": (146, 26, 40),
    "B": (160, 222, 255), "b": (60, 144, 236), "d": (30, 74, 160),
    "l": (160, 232, 120), "v": (64, 178, 78), "V": (28, 108, 62),
    "p": (255, 176, 204), "P": (226, 92, 146),
    "c": (226, 164, 92), "n": (170, 108, 56), "N": (104, 62, 36),
    "w": (226, 234, 244), "s": (164, 176, 194), "S": (100, 110, 134),
    "m": (176, 120, 240), "M": (110, 60, 180),
}


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def rel_lum(c):
    """Luminancia relativa (WCAG) 0..1."""
    out = []
    for v in c[:3]:
        v = v / 255.0
        out.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a, b):
    la, lb = rel_lum(a), rel_lum(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def ramp(c):
    """4 tons (luz, base, sombra, funda) com desvio de matiz (luz quente, sombra roxa)."""
    c = tuple(int(v) for v in c[:3])
    if max(c) - min(c) < 40 and max(c) > 60:                 # cinzas ganham um toque frio
        c = lerp(c, (120, 140, 200), 0.12)
    return (lerp(c, (255, 244, 214), 0.36), c, lerp(c, (40, 22, 64), 0.32), lerp(c, (20, 10, 34), 0.58))


# ------------------------------------------------------------------------------------- simbolos 15x15
def _rows(*rows):
    return tuple(rows)


ART = {
    "raio": _rows(
        "...............", ".........YYy...", "........YYy....", ".......YYy.....", "......YYy......",
        ".....YYy.......", "....YYyyyyyy...", "...yyyyyyyyg...", ".......yyyg....", "......yyyg.....",
        ".....yyyg......", "....yyg........", "...yyg.........", "..yg...........", "..............."),
    "chama": _rows(
        ".......r.......", "......rr.......", "......rro...r..", ".....rroo..rr..", "....rrooo.rro..",
        "....rooooorro..", "...rroooyoooo..", "...rooyyyyoor..", "..rrooyYYyyor..", "..roooyYWYyoor.",
        "..rooyyWWYyoor.", "..rooyYWWYyor..", "...rooyyyyoor..", "....rroooorr...", "......rrrr....."),
    "gota": _rows(
        ".......d.......", "......dbd......", "......bbb......", ".....bBbbd.....", ".....bBbbd.....",
        "....bBBbbbd....", "....bWBbbbd....", "...bBWBbbbbd...", "...bBBbbbbbd...", "..bbBbbbbbbbd..",
        "..bbbbbbbbbbd..", "..bbbbbbbbbdd..", "...dbbbbbbdd...", "....ddbbddd....", "......ddd......"),
    "estrela": _rows(
        "...............", ".......Y.......", "......YYg......", "......Yyg......", ".....YYygg.....",
        ".YYYYYYyyygggG.", "..Yyyyyyyyyyg..", "...yyyyyyyyg...", "....yyyyyyg....", "....yyyyyyg....",
        "...yyyygyyyg...", "...yyyg.gyyg...", "..yyg.....gyG..", "..yg.......gG..", "..............."),
    "coroa": _rows(
        "...............", "..Y....Y....Y..", ".YgG..YgG..YgG.", "..y....y....y..", "..yy..yyy..yy..",
        "..yyy.yyy.yyy..", "..yyyyyyyyyyg..", "..yyyyyyyyyyg..", "..yrryybyyrrg..", "..yrryyyyyrrg..",
        "..yyyyyyyyyyg..", "..GGGGGGGGGGG..", "..ggggggggggG..", "..GGGGGGGGGGG..", "..............."),
    "sol": _rows(
        ".......y.......", ".y.....y.....y.", "..y....o....y..", "...o.ooooo.o...", "....oyyyyyo....",
        "...oyYYyyyyo...", "...oyYyyyyyo...", "yyooyyyyyyyooyy", "...oyyyyyyyo...", "...ooyyyyyoo...",
        "....ooyyyoo....", "...o.ooooo.o...", "..y....o....y..", ".y.....y.....y.", ".......y......."),
    "torre": _rows(
        "...............", "...WW.W#W.#+...", "...W#.###.#+...", "...W#######+...", "....W#####+....",
        "....W#####+....", "....W##x##+....", "....W##x##+....", "....W#####+....", "....W#####+....",
        "...W#######+...", "..W#########+..", "..W#########+..", "..+++++++++++..", "..............."),
    "parafuso": _rows(
        "...............", "...wwwwwwwwwS..", "...wwsssssssS..", "...SSSSSSSSSS..", ".....wwssS.....",
        "....wwwssSS....", ".....wwssS.....", "....wwwssSS....", ".....wwssS.....", "....wwwssSS....",
        ".....wwssS.....", "....wwwssSS....", ".....wwsS......", "......wS.......", "..............."),
    "pao": _rows(
        "...............", "....+...+...+..", ".....+...+...+.", "....+...+...+..", "...............",
        "....ccccccc....", "...ccYccYccn...", "..cccYccYcYnn..", ".cccYccYccYcnn.", ".ccYccYccYccnn.",
        ".cccccccccccnN.", ".nnnnnnnnnnnnN.", "..NNNNNNNNNNN..", "...............", "..............."),
    "vassoura": _rows(
        "......cnN......", "......cnN......", "......cnN......", "......cnN......", "......cnN......",
        ".....rrrrR.....", ".....RRRRR.....", "....YyyyyyG....", "....YyYyYyG....", "...YyyYyYyyG...",
        "...YyYyYyYyG...", "..YyyYyYyYyyG..", "..YyYyYyYyYyG..", ".YyYyYyYyYyYyG.", "..............."),
    "cavaleiro": _rows(
        ".......rrR.....", "......rrR......", ".....wwwww.....", "....wwsssssS...", "...wwssssssS...",
        "...wsssssssS...", "...wxxxxxxxS...", "...wsssssssS...", "...wsxsxsxsS...", "...wssssssSS...",
        "....wsssssS....", "...YgggggggG...", "..YggGGGGGggG..", "...............", "..............."),
    "aguia": _rows(
        "...............", "......###......", ".....#k#k#.....", "......#y#......", "c.....ccc.....c",
        "cc...ccccc...cc", "cnc.ccccccc.cnc", ".ccccccccccccc.", "..cnccccccncc..", "...ncccccccn...",
        ".....ccccc.....", "......ncn......", ".....y.y.y.....", "...............", "..............."),
    "garra": _rows(
        "...............", "....##...##....", "...####.####...", "...####.####...", ".##.##...##.##.",
        "####.......####", "####..###..####", ".##..#####..##.", "....#######....", "...#########...",
        "..###########..", "..#########++..", "...####+###+...", "....###.++#....", "..............."),
    "ancora": _rows(
        "......www......", ".....w...S.....", "......wsS......", "...wwwwssSSS...", "......wsS......",
        "......wsS......", "......wsS......", "......wsS......", "......wsS......", ".w....wsS....S.",
        ".ws...wsS...sS.", "..ws..wsS..sS..", "...wsswsSssS...", ".....wsssS.....", "..............."),
    "bateria": _rows(
        "...............", "......wsS......", "...wwwwwsssS...", "...wkkkWkkkS...", "...wkkWWWkkS...",
        "...wkkkWkkkS...", "...wklllllkS...", "...wkvvvvvkS...", "...wklllllkS...", "...wkvvvvvkS...",
        "...wklllllkS...", "...wkvvvvvkS...", "...wkkkkkkkS...", "...SSSSSSSSS...", "..............."),
    "chip": _rows(
        "...............", "....s.s.s.s....", "....s.s.s.s....", "...kkkkkkkkk...", ".sskSSSSSSSkss.",
        "...kSgggggSk...", ".sskSgYYggSkss.", "...kSgYgggSk...", ".sskSgggGGSkss.", "...kSgGGGGSk...",
        ".sskSSSSSSSkss.", "...kkkkkkkkk...", "....s.s.s.s....", "....s.s.s.s....", "..............."),
    "olho": _rows(
        "...............", "...............", "...............", ".....xxxxx.....", "...xx#####xx...",
        "..x###bbb###x..", ".x###bBkbb###x.", "x####bkkkb####x", ".x###bbkbb###x.", "..x###bbb###x..",
        "...xx#####xx...", ".....xxxxx.....", "...............", "...............", "..............."),
    "nota": _rows(
        "...............", "......YYYYYYY..", "......yyyyyyy..", "......yg....yg.", "......yg....yg.",
        "......yg....yg.", "......yg....yg.", "......yg....yg.", "......yg....yg.", "...yyyyg.yyyyg.",
        "..yYyyyg.Yyyyg.", "..yyyyg.yyyyg..", "...yyg...yyg...", "...............", "..............."),
    "mascara": _rows(
        "...............", "....#######....", "...#W######+...", "..#W########+..", "..#WxxW##xx#+..",
        "..#xxx###xxx+..", "..#W########+..", "..#Wp#####p#+..", "..#x#######x+..", "...#xx###xx+...",
        "...+#xxxxx#+...", "....+#####+....", ".....+++++.....", "...............", "..............."),
    "martelo": _rows(
        "...............", "...wwwwwwwwS...", "..wwssssssssS..", "..wssssssssSS..", "...SSSSSSSSS...",
        "......cnN......", "......cnN......", "......cnN......", "......cnN......", "......cnN......",
        "......cnN......", "......cnN......", "......NNN......", "...............", "..............."),
    "ferradura": _rows(
        "...............", "..YY.......gG..", "..Yg.......gG..", ".YYg.......gGG.", ".YkY.......gkG.",
        ".YYg.......gGG.", ".YkY.......gkG.", ".YYg.......gGG.", ".YYg.......gGG.", "..YkG.....gkG..",
        "..YYgg...ggGG..", "...YYggggggG...", "....YggggGG....", ".....GGGGG.....", "..............."),
    "haltere": _rows(
        "...............", "...............", "...............", ".wwS.......wwS.", ".wsS.......wsS.",
        ".wsSw.....wwsS.", ".wsSwsssssswsS.", ".wsSwwwwwwwwsS.", ".wsSwSSSSSwwsS.", ".wsSw.....wwsS.",
        ".wsS.......wsS.", ".SSS.......SSS.", "...............", "...............", "..............."),
    "taca": _rows(
        "...............", "..YYYYYYYYYYg..", ".gYyyyyyyyyyGg.", "g.YyyyyyyyyyG.g", "g.YyyyyyyyyyG.g",
        ".g.Yyyyyyyyg.g.", "..gYyyyyyyyGg..", "....Yyyyyyg....", ".....Yyyyg.....", "......yyg......",
        "......yyg......", ".....Yyyyg.....", "....GGGGGGG....", "...ggggggggG...", "..............."),
    "diamante": _rows(
        "...............", "...............", "....BBBBBBB....", "...BWWBBWBBb...", "..BWBBBBBBBbb..",
        ".bbbbbbbbbbbbd.", "..bBbbbbbbbbd..", "...bBbbbbbbd...", "....bBbbbbd....", ".....bBbbd.....",
        "......bbd......", ".......d.......", "...............", "...............", "..............."),
    "arvore": _rows(
        ".......l.......", "......lvV......", ".....lvvvV.....", "....lvvvvvV....", "......lvV......",
        ".....lvvvV.....", "....lvvvvvV....", "...lvvvvvvvV...", ".....lvvvV.....", "....lvvvvvV....",
        "...lvvvvvvvV...", "..lvvvvvvvvvV..", "......nnN......", "......nnN......", "..............."),
    "coelho": _rows(
        "...##.....##...", "...#p#...#p#...", "...#p#...#p#...", "...#p#...#p#...", "...#p#...#p#...",
        "....##...##....", "...#########...", "..###########..", "..##k#####k##..", ".#############.",
        ".#p####P####p#.", ".##+###x###+##.", "..##+#####+##..", "...+++++++++...", "..............."),
    "torii": _rows(
        "...............", "rrrrrrrrrrrrrrr", ".RrrrrrrrrrrrR.", "...rR.....rR...", ".rrrrrrrrrrrrr.",
        "...rR..y..rR...", "...rR.....rR...", "...rR.....rR...", "...rR.....rR...", "...rR.....rR...",
        "...rR.....rR...", "...rR.....rR...", "..kkkk...kkkk..", "...............", "..............."),
    "robo": _rows(
        ".......r.......", ".......s.......", "...............", "..wwwwwwwwwwS..", "..wkkkkkkkkkS..",
        ".swkBBkkkBBkSs.", ".swkBBkkkBBkSs.", "..wkkkkkkkkkS..", "..wsssssssssS..", "..wsxsxsxsssS..",
        "..SSSSSSSSSSS..", "....SsssssS....", "...............", "...............", "..............."),
    "gravata": _rows(
        "...............", "....wddddbw....", ".....bbbbd.....", "......bbd......", ".....bbybd.....",
        ".....bybbd.....", "....bbbbybd....", "....bbbybbd....", "....bbybbbd....", "....bybbbyd....",
        "....bbbbybd....", ".....bbybd.....", "......bbd......", ".......d.......", "..............."),
    "fita": _rows(
        "...............", "...............", "...............", ".kkkkkkkkkkkkk.", ".kwwwwwwwwwwwk.",
        ".kwrrrrrrrrrwk.", ".kwkkkkkkkkkwk.", ".kwkWkkkkkWkwk.", ".kwkkkkkkkkkwk.", ".kwwwwwwwwwwwk.",
        ".kwwsssssssswk.", ".kkkkkkkkkkkkk.", "...............", "...............", "..............."),
    "balao": _rows(
        "...............", "...............", "...#########...", "..###########..", ".#############.",
        ".###k##k##k###.", ".##kk#kk#kk###.", ".+###########+.", "..++#######++..", "...##+++++.....",
        "...#+..........", "..#............", "...............", "...............", "..............."),
    "coracao": _rows(
        "...............", "...............", "...rrr...rrr...", "..rWrrr.rrrrr..", ".rWWrrrrrrrrrR.",
        ".rWrrrrrrrrrrR.", ".rrrrrrrrrrrrR.", "..rrrrrrrrrrR..", "...rrrrrrrrR...", "....rrrrrrR....",
        ".....rrrrR.....", "......rrR......", ".......R.......", "...............", "..............."),
    "ima": _rows(
        "...............", "..wwS.....wwS..", "..wwS.....wwS..", "..WrR.....WrR..", "..WrR.....WrR..",
        "..WrR.....WrR..", "..WrR.....WrR..", "..WrR.....WrR..", "..WrrR...WrrR..", "...WrrRRRrrR...",
        "....RrrrrrR....", ".....RRRRR.....", "...............", "...............", "..............."),
    "bola": _rows(
        "...............", ".....##k##.....", "...#W#kkk#+#...", "..#W###k###+#..", "..W#########+..",
        ".kk###kkk###kk.", ".kk##kkkkk##kk.", ".k###kkkkk###+.", ".####kkkkk###+.", ".#####kkk####+.",
        "..##k#####k#+..", "..#kkk###kkk+..", "...#kk###kk+...", ".....+++++.....", "..............."),
    "espada": _rows(
        ".......w.......", "......wsS......", "......wsS......", "......wsS......", "......wsS......",
        "......wsS......", "......wsS......", "......wsS......", "..YgggggggggG..", "...GGGGGGGGG...",
        "......nnN......", "......nnN......", "......gGg......", "...............", "..............."),
    "leao": _rows(
        ".....ooooo.....", "...ooooooooo...", ".oooyyyyyyyooo.", ".ooyyyyyyyyyoo.", "oooykkyyykkyooo",
        "ooyyyyyyyyyyyoo", "ooyyyyNNNyyyyoo", "ooyyyyyNyyyyyoo", ".oyyyNyNyNyyyo.", ".ooyyyyyyyyyoo.",
        "..ooyyyyyyyoo..", "...oooyyyooo...", ".....ooooo.....", "...............", "..............."),
    "dragao": _rows(
        "............V..", "...........Vl..", "..........Vl...", "......vvvvvl...", "....vvvlllvvv..",
        "..vvvvvvyklvvV.", ".vvkvvvvvvvvvV.", "vvvvvvvvvvvvVV.", "WvWvW.....vvVV.", ".WvWvvvvvvvVV..",
        "...vvvvvvvVVV..", ".........vVVV..", "........vvVV...", ".......vvVV....", "..............."),
    "tubarao": _rows(
        "...............", ".......S.......", "......sS.......", ".....ssS.......", "....sssS.....S.",
        "..ssssssssS.SS.", ".swssssssssSSS.", "swksssssssssSS.", "ssssssssssssS..", "#x#x###++sssSS.",
        ".#######++.SSS.", "..++++++...SS..", "............S..", "...............", "..............."),
    "vulcao": _rows(
        ".....+..+......", "......+#.+.....", ".....#.+.......", "......Yy.......", ".....cyoyc.....",
        "....ccroyrn....", "....cccrccn....", "...cccrcccnn...", "...ccccrccnn...", "..cccccrcccnn..",
        "..cccccccccnn..", ".ccccccccccnnN.", ".cnnnnnnnnnnnN.", "...............", "..............."),
    "cometa": _rows(
        "...............", "..........yYy..", ".........yYWYy.", "........oyYYyy.", ".......ooyyyy..",
        "......ooooyy...", ".....roooo.....", "....rroo.o.....", "...rro..o......", "..rr...o.......",
        ".r....r........", "....rr.........", "...............", "...............", "..............."),
}

# simbolos gerados por formula (radiais): grade 15x15 de letras da PAL
def _grid():
    return [["."] * 15 for _ in range(15)]


def _gen_engrenagem():
    g = _grid()
    for y in range(15):
        for x in range(15):
            dx, dy = x - 7, y - 7
            r = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            tooth = (math.cos(a * 8) > 0.35)
            if r <= 2.1:
                continue
            if r <= 5.0 or (tooth and r <= 6.9):
                lit = (-dx - dy) / 10.0
                g[y][x] = "w" if lit > 0.35 else ("s" if lit > -0.35 else "S")
                if 2.1 < r <= 3.1:
                    g[y][x] = "S" if lit > 0 else "w"
    return g


def _gen_aspirador():
    g = _grid()
    for y in range(15):
        for x in range(15):
            dx, dy = x - 7, y - 7.5
            r = math.hypot(dx, dy)
            if r > 6.9:
                continue
            if r > 5.9:
                g[y][x] = "S" if dy > -1 else "s"
            elif r > 4.8:
                a = math.atan2(dy, dx)
                g[y][x] = "B" if -2.6 < a < -0.5 else "s"
            else:
                g[y][x] = "w" if dx + dy < -2 else "#"
            if r <= 1.6:
                g[y][x] = "k"
    g[7][7] = "B"
    for x in range(4, 11):                    # para-choque na frente
        if g[13][x] != ".":
            g[13][x] = "y"
    return g


def _gen_flor():
    g = _grid()
    pet = []
    for k in range(5):
        a = -math.pi / 2 + k * 2 * math.pi / 5
        pet.append((7 + math.cos(a) * 4.1, 7.3 + math.sin(a) * 4.1, a))
    for y in range(15):
        for x in range(15):
            for px, py, a in pet:
                d = math.hypot(x - px, y - py)
                if d <= 2.9:
                    tip = math.hypot(x - (7 + math.cos(a) * 6.6), y - (7.3 + math.sin(a) * 6.6))
                    if tip < 0.9:
                        break
                    g[y][x] = "W" if d < 1.0 and y < 7 else ("p" if (x - px) + (y - py) < 1.2 else "P")
                    break
            r = math.hypot(x - 7, y - 7.3)
            if r <= 1.9:
                g[y][x] = "y" if r > 0.9 else "o"
    for x, y in ((7, 5), (5, 7), (9, 7)):
        g[y][x] = "P"
    return g


def _gen_trevo():
    """Trevo de 4 folhas: cada folha e um coracao (2 circulos) separada das outras por um vao em X."""
    g = _grid()
    cx0, cy0 = 7, 6
    for y in range(15):
        for x in range(15):
            dx, dy = x - cx0, y - cy0
            if abs(dx) == abs(dy):                      # vao entre as folhas
                continue
            for k in range(4):
                a = k * math.pi / 2
                ux, uy = math.cos(a), math.sin(a)
                vx, vy = -uy, ux
                along = dx * ux + dy * uy
                side = dx * vx + dy * vy
                if along <= 0:
                    continue
                if any(math.hypot(along - 3.3, side - s * 1.55) <= 2.05 for s in (-1, 1)):
                    g[y][x] = "l" if dx + dy < -2 else ("v" if dx + dy < 3 else "V")
                    break
    g[cy0][cx0] = "V"
    for y in range(11, 15):
        g[y][cx0 + 1 + (y - 11) // 2] = "V"
    return g


def _gen_planeta():
    g = _grid()
    for y in range(15):
        for x in range(15):
            dx, dy = x - 7, y - 7
            r = math.hypot(dx, dy)
            if r <= 4.9:
                land = math.sin(x * 1.3) + math.cos(y * 1.1 + x * 0.4) > 0.6
                c = ("l" if land else "B") if dx + dy < -3 else (("v" if land else "b") if dx + dy < 3 else
                                                                   ("V" if land else "d"))
                g[y][x] = c
            e = (dx * math.cos(0.4) + dy * math.sin(0.4)) / 7.1, (-dx * math.sin(0.4) + dy * math.cos(0.4)) / 2.0
            er = math.hypot(*e)
            if 0.72 <= er <= 1.06 and not (r <= 4.9 and e[1] < 0):
                g[y][x] = "y" if e[0] < 0 else "g"
    return g


def _gen_relogio():
    g = _grid()
    for y in range(15):
        for x in range(15):
            r = math.hypot(x - 7, y - 7)
            if r <= 6.8:
                g[y][x] = "g" if r > 5.7 else ("W" if x + y < 10 else "#")
    for k in range(12):
        a = k * math.pi / 6
        g[int(round(7 + math.sin(a) * 4.6))][int(round(7 + math.cos(a) * 4.6))] = "+" if k % 3 else "x"
    for y in range(3, 8):
        g[y][7] = "x"
    for x in range(7, 11):
        g[7][x] = "x"
    g[7][7] = "r"
    for y in range(1, 3):
        pass
    return g


def _gen_volante():
    g = _grid()
    for y in range(15):
        for x in range(15):
            dx, dy = x - 7, y - 7
            r = math.hypot(dx, dy)
            if 5.0 <= r <= 6.9:
                g[y][x] = "w" if dx + dy < -2 else ("s" if dx + dy < 3 else "S")
            elif r <= 1.9:
                g[y][x] = "r" if r > 0.9 else "y"
            elif r < 5.0:
                a = math.degrees(math.atan2(dy, dx)) % 360
                for sa in (0, 180, 90):
                    if min(abs(a - sa), 360 - abs(a - sa)) < 16:
                        g[y][x] = "s"
    return g


def _gen_lapis():
    g = _grid()
    for y in range(15):
        for x in range(15):
            a = x + y - 14
            b = x - y
            if abs(a) > 2 or b < -11 or b > 11:
                continue
            if b < -6:
                w = (b + 11) * 0.45
                if abs(a) > w:
                    continue
                g[y][x] = "k" if b < -8 else "c"
            elif b < 6:
                g[y][x] = "Y" if a < 0 else ("y" if a == 0 else "o")
            elif b < 8:
                g[y][x] = "w" if a <= 0 else "s"
            else:
                g[y][x] = "p" if a <= 0 else "P"
    return g


def _gen_lupa():
    g = _grid()
    for y in range(15):
        for x in range(15):
            r = math.hypot(x - 6, y - 6)
            if r <= 5.4:
                g[y][x] = "s" if r > 4.0 else ("W" if (x - 6) + (y - 6) < -3 else "B")
            elif x >= 9 and y >= 9 and abs((x - 9) - (y - 9)) <= 1 and x <= 13:
                g[y][x] = "n" if (x - y) <= 0 else "N"
    return g


def _gen_montanha():
    """Dois picos com neve (luz a esquerda, sombra a direita) sobre um morro verde."""
    g = _grid()
    for y in range(15):
        for x in range(15):
            h1 = 1.5 + abs(x - 6) * 1.2
            h2 = 5.5 + abs(x - 11) * 1.3
            if y > 12:
                continue
            if y >= 11:
                g[y][x] = "v" if x < 9 else "V"
                continue
            main = y >= h1
            if not (main or y >= h2):
                continue
            px = 6 if main and (y < h2 or x <= 8) else 11
            hh = h1 if px == 6 else h2
            left = x <= px
            snow = y < hh + 3.2 - (0.8 if (x * 7 + y * 3) % 5 == 0 else 0)
            if snow:
                g[y][x] = "W" if left else "w"
            else:
                g[y][x] = "s" if left else "S"
    return g


def _gen_espiral():
    g = _grid()
    t = 0.0
    while t < 3.0 * math.pi:
        r = 0.6 + t * 0.66
        for w in (-0.45, 0.0, 0.45):
            x = int(round(7 + math.cos(t + 0.3) * (r + w)))
            y = int(round(7 + math.sin(t + 0.3) * (r + w) * 0.95))
            if 0 <= x < 15 and 0 <= y < 15:
                g[y][x] = "W" if t < 2.0 else ("B" if t < 6.0 else "b")
        t += 0.04
    return g


def _gen_omega():
    g = _grid()
    for y in range(15):
        for x in range(15):
            dx, dy = x - 7, y - 6.4
            r = math.hypot(dx, dy)
            a = math.degrees(math.atan2(dy, dx))
            if 3.7 <= r <= 6.0 and not (52 < a < 128):
                g[y][x] = "y" if dx + dy < -1 else ("o" if dx + dy < 4 else "r")
                if r < 4.4 and dy < 0:
                    g[y][x] = "Y"
    for x in list(range(1, 6)) + list(range(9, 14)):
        g[12][x] = "y"
        g[13][x] = "r"
    for x in (4, 5, 9, 10):
        g[11][x] = "o"
    return g


def _gen_bolha():
    g = _grid()
    for cx, cy, rr in ((5.2, 8.6, 4.2), (10.6, 4.4, 3.0), (11.2, 11.0, 2.0)):
        for y in range(15):
            for x in range(15):
                d = math.hypot(x - cx, y - cy)
                if rr - 1.0 <= d <= rr:
                    g[y][x] = "W" if x - cx + y - cy < -1 else "B"
        hx, hy = int(round(cx - rr * 0.45)), int(round(cy - rr * 0.45))
        g[hy][hx] = "W"
    return g


def _gen_chave():
    g = _grid()
    for y in range(15):
        for x in range(15):
            a = x + y - 14                       # perpendicular
            b = x - y                            # ao longo (cabo de baixo-esq para cima-dir)
            if abs(a) <= 1 and -10 <= b <= 4:
                g[y][x] = "w" if a < 0 else ("s" if a == 0 else "S")
            d = math.hypot(x - 10.6, y - 3.4)
            if d <= 3.7:
                jaw = math.hypot(x - 12.4, y - 1.6) <= 2.0
                if not jaw:
                    g[y][x] = "w" if x + y < 13 else ("s" if x + y < 16 else "S")
    return g


def _gen_trigo():
    g = _grid()
    for y in range(4, 15):
        g[y][7] = "G"
    for k in range(5):
        yy = 1 + k * 2
        for side in (-1, 1):
            if k == 0 and side == 1:
                continue
            cx = 7 + side * 1.6
            for y in range(15):
                for x in range(15):
                    if ((x - cx) / 1.3) ** 2 + ((y - yy - 1) / 1.9) ** 2 <= 1.0:
                        g[y][x] = "Y" if side < 0 else "y"
    g[0][7] = "Y"
    return g


GEN = {
    "engrenagem": _gen_engrenagem, "aspirador": _gen_aspirador, "flor": _gen_flor, "trevo": _gen_trevo,
    "planeta": _gen_planeta, "relogio": _gen_relogio, "volante": _gen_volante, "lapis": _gen_lapis,
    "lupa": _gen_lupa, "montanha": _gen_montanha,
    "furacao": _gen_espiral, "omega": _gen_omega, "bolha": _gen_bolha, "chave": _gen_chave, "trigo": _gen_trigo,
}

SYMBOLS = tuple(sorted(set(ART) | set(GEN)))
# simbolos "genericos" para o fallback (nome sem palavra-chave conhecida)
FALLBACK = ("estrela", "raio", "bola", "coroa", "chama", "engrenagem", "aspirador", "cometa", "sol", "diamante",
            "trevo", "taca", "ancora", "planeta", "aguia", "furacao")

# palavra-chave (prefixo de palavra do nome normalizado: minusculo, sem acento; "x$" = palavra inteira) ->
# simbolo; vale a 1a regra que casa
SYMBOL_RULES = (
    (("omega",), "omega"), (("xadrez",), "torre"), (("tubar",), "tubarao"), (("leoes", "leao"), "leao"),
    (("drag",), "dragao"), (("tigre", "pantera", "lobo"), "garra"), (("aguia", "falco", "gaviao", "gavioe",
                                                                       "valquiria"), "aguia"),
    (("corsar", "marujo", "contrabando"), "ancora"), (("vulcao",), "vulcao"), (("cometa",), "cometa"),
    (("odete",), "coracao"), (("academia",), "haltere"), (("estrela", "dream", "all"), "estrela"),
    (("sol$",), "sol"), (("sakura", "nipo"), "flor"),
    (("dojo", "kenji"), "torii"), (("guarda", "pretoriana", "guerreiro", "bravo"), "cavaleiro"),
    (("bunnies", "coelho"), "coelho"), (("padaria", "pao", "merenda", "cantina"), "pao"),
    (("churrasco", "bombeiro", "fogo", "micro"), "chama"),
    (("faxin", "rodo", "esfregao", "pano", "vassoura"), "vassoura"),
    (("impec", "imacul", "aspir", "staub", "hiperlimp", "aspira"), "aspirador"),
    (("higiene", "lavanderia", "poeira", "arroz"), "bolha"), (("pia", "cera", "gota"), "gota"),
    (("furacao", "ventilador"), "furacao"), (("parafus", "lataria"), "parafuso"),
    (("engrenagem", "dinamo", "rolima", "sucat", "montagem", "bobina"), "engrenagem"),
    (("ferro",), "ima"), (("raio", "trov", "curto", "capacitor", "voltagem", "fusive"), "raio"),
    (("bateria",), "bateria"), (("transistor", "circuito", "chat", "cabo"), "chip"),
    (("droide", "prototipo"), "robo"), (("fiscai", "qualidade"), "olho"), (("detetive",), "lupa"),
    (("coral", "boemio"), "nota"), (("teatro",), "mascara"), (("operario",), "martelo"),
    (("oficina", "garagem", "sindicato", "galpao"), "chave"), (("centauro",), "ferradura"),
    (("rural",), "trigo"), (("taxista", "cooperativa", "parachoque"), "volante"), (("cartorio",), "relogio"),
    (("turma", "fundao"), "lapis"), (("campeo", "copa"), "taca"),
    (("platinum", "diamante"), "diamante"), (("titas", "serra", "vale", "norte"), "montanha"),
    (("escoteiro",), "arvore"), (("gremio", "verde"), "trevo"), (("mundos", "internacional"), "planeta"),
    (("gerente",), "gravata"), (("nestor",), "fita"),
    (("real", "rainha", "imperial", "rei"), "coroa"), (("azul", "vermelho", "classico"), "bola"),
    (("rival",), "chave"), (("linha",), "engrenagem"),
    # nomes sugeridos para o time do jogador (robots_ui.TEAM_NAMES)
    (("rodinha", "turbo"), "volante"), (("faisca", "eletric"), "raio"), (("zumbido",), "nota"),
    (("rolo",), "engrenagem"),
)

SHAPES = ("classico", "redondo", "losango", "hexagono", "pontudo", "frances", "oval")
PATTERNS = ("liso", "faixa", "listras", "metade", "diagonal", "quartos", "chevron", "aro")

# escudos especiais: chefes e rivais principais da campanha (nome exato -> enfeites)
#   top: "coroa" | "estrelas" | None; sides: "louros" | "asas" | None; stars: estrelas na faixa
SPECIALS = {
    "Clube do Xadrez": {"top": "estrelas", "sides": None, "shape": "frances"},
    "Os Impecáveis": {"top": "estrelas", "sides": "louros", "shape": "classico"},
    "Esquadrão Faxina": {"top": "estrelas", "sides": None, "shape": "pontudo"},
    "Imaculados L-9": {"top": "estrelas", "sides": "louros", "shape": "hexagono"},
    "Divisão Platinum": {"top": "coroa", "sides": "louros", "shape": "frances"},
    "Hiperlimpos X-9": {"top": "estrelas", "sides": "asas", "shape": "pontudo"},
    "Brigada Higiene": {"top": "estrelas", "sides": "louros", "shape": "redondo"},
    "Platinum Elite": {"top": "coroa", "sides": None, "shape": "classico"},
    "Guarda Zero": {"top": "coroa", "sides": "asas", "shape": "pontudo"},
    "Zé Perfeito e a Guarda": {"top": "coroa", "sides": "asas", "shape": "classico", "sym": "cavaleiro"},
    "Time dos Mundos": {"top": "estrelas", "sides": "louros", "shape": "redondo"},
    "Gerente Mk II": {"top": "estrelas", "sides": None, "shape": "hexagono"},
    "Dono do Galpão": {"top": "coroa", "sides": None, "shape": "frances"},
    "Os Imaculados Ômega": {"top": "coroa", "sides": "louros", "shape": "hexagono"},
    "X-Ômega Prime": {"top": "coroa", "sides": "asas", "shape": "pontudo"},
}


# ------------------------------------------------------------------------------------------ texto
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "#..#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
}
STOP = {"do", "da", "de", "dos", "das", "os", "as", "o", "a", "e", "les", "the", "of", "sob", "mk"}
ROMAN = {"ii": "2", "iii": "3", "iv": "4"}


def norm(name):
    """minusculas sem acento (ASCII)."""
    s = unicodedata.normalize("NFKD", str(name or ""))
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def base_name(name):
    """Nome do escudo: tira o numero do andar da Torre ("Parafusos FC 12" -> "Parafusos FC")."""
    return re.sub(r"\s+\d+$", "", str(name or "").strip()) or "Time"


def words(name):
    return [w for w in re.split(r"[^a-z0-9]+", norm(name)) if w]


def initials(name):
    ws = [w for w in words(base_name(name)) if w not in STOP]
    out = []
    for w in ws:
        if w in ROMAN:
            out.append(ROMAN[w])
        elif w[0].isdigit():
            out.append(w[0])
        else:
            out.append(w[0].upper())
    s = "".join(ch for ch in "".join(out).upper() if ch in FONT)
    if len(s) == 1 and ws and len(ws[0]) >= 3 and not ws[0][0].isdigit():
        s = "".join(ch for ch in ws[0][:3].upper() if ch in FONT)
    return s[:3] or "FC"


def hash32(s):
    return zlib.crc32(s.encode("utf-8")) & 0xFFFFFFFF


def pick_symbol(name):
    ws = words(base_name(name))
    for prefixes, sym in SYMBOL_RULES:
        for w in ws:
            for p in prefixes:
                if p.endswith("$"):
                    if w == p[:-1]:                     # "sol$": so a palavra inteira (nao "soltos")
                        return sym
                elif w.startswith(p) and (len(p) >= 3 or w == p):
                    return sym
    return FALLBACK[hash32(norm(base_name(name)) + "|s") % len(FALLBACK)]


def sanitize(custom):
    """Campo opcional "crest" do time do jogador: {"sym": id, "shape": id} (ids desconhecidos somem)."""
    if not isinstance(custom, dict):
        return None
    out = {}
    if custom.get("sym") in SYMBOLS:
        out["sym"] = custom["sym"]
    if custom.get("shape") in SHAPES:
        out["shape"] = custom["shape"]
    return out or None


def spec(name, color, custom=None):
    """Receita do escudo (dict puro): formato, padrao, simbolo, iniciais, cores, enfeites."""
    bn = base_name(name)
    h = hash32(norm(bn))
    sp = SPECIALS.get(bn)
    col = tuple(int(max(0, min(255, v))) for v in tuple(color)[:3]) if color else (120, 120, 140)
    shape = SHAPES[h % len(SHAPES)]
    pattern = PATTERNS[(h // 7) % len(PATTERNS)]
    sym = pick_symbol(bn)
    if sp:
        shape = sp.get("shape", shape)
        sym = sp.get("sym", sym)
    cu = sanitize(custom)
    if cu:
        sym = cu.get("sym", sym)
        shape = cu.get("shape", shape)
    # cor secundaria: a primeira candidata (ordem pelo hash) com contraste suficiente
    hi, base, sh, dp = ramp(col)
    cands = [CREAM, NAVY, GOLD[1], lerp(col, (255, 255, 255), 0.62), lerp(col, (0, 0, 0), 0.55)]
    k = (h // 61) % len(cands)
    cands = cands[k:] + cands[:k]
    sec = next((c for c in cands if contrast(c, col) >= 1.9), CREAM if rel_lum(col) < 0.35 else NAVY)
    light_banner = (h // 13) % 2 == 0
    if contrast(CREAM, col) < 1.5:              # time quase branco: faixa escura destaca melhor
        light_banner = False
    return {"name": bn, "color": col, "shape": shape, "pattern": pattern, "sym": sym, "ini": initials(bn),
            "sec": sec, "special": dict(sp) if sp else None, "light_banner": light_banner}


# ------------------------------------------------------------------------------------------ pintura
class _Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [None] * (w * h)

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y * self.w + x]
        return None

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = c

    def to_surface(self):
        buf = bytearray(self.w * self.h * 4)
        for i, c in enumerate(self.px):
            if c is not None:
                buf[i * 4] = c[0]
                buf[i * 4 + 1] = c[1]
                buf[i * 4 + 2] = c[2]
                buf[i * 4 + 3] = 255
        frombytes = getattr(pygame.image, "frombytes", None) or pygame.image.fromstring
        surf = frombytes(bytes(buf), (self.w, self.h), "RGBA")
        try:
            return surf.convert_alpha()
        except pygame.error:                     # sem display (testes puros)
            return surf


def _mask(shape, x0, y0, x1, y1):
    """Conjunto de pixels (x, y) dentro do formato no retangulo [x0, x1) x [y0, y1)."""
    w, h = x1 - x0, y1 - y0
    cx = x0 + w / 2.0
    out = set()
    for y in range(y0, y1):
        for x in range(x0, x1):
            px, py = x + 0.5 - cx, y + 0.5 - y0      # px relativo ao centro, py a partir do topo
            hw = w / 2.0
            t = py / h
            if shape == "classico":
                ok = (t < 0.52 and abs(px) <= hw) or (t >= 0.52 and abs(px) <= hw * math.cos(
                    min(1.0, (t - 0.52) / 0.48) * math.pi / 2) ** 0.75)
                if py < 1.0 and abs(px) > hw - 1:
                    ok = False
            elif shape == "redondo":
                r = min(w, h) / 2.0
                ok = px * px + (py - h / 2.0) ** 2 <= r * r
            elif shape == "oval":
                ok = (px / hw) ** 2 + ((py - h / 2.0) / (h / 2.0)) ** 2 <= 1.0
            elif shape == "losango":
                ok = abs(px) / hw + abs(py - h * 0.46) / (h * 0.54 if py > h * 0.46 else h * 0.46) <= 1.04
            elif shape == "hexagono":
                d = abs(py - h / 2.0)
                ok = abs(px) <= hw - max(0.0, d - h * 0.24) * (hw * 0.55 / (h * 0.26))
            elif shape == "pontudo":
                if t < 0.16:
                    ok = abs(px) <= hw * (0.25 + 0.75 * t / 0.16)
                elif t < 0.68:
                    ok = abs(px) <= hw
                else:
                    ok = abs(px) <= hw * (1.0 - (t - 0.68) / 0.32) ** 0.85
            else:  # frances: topo com orelhas e fundo arredondado com bico
                if t < 0.12:
                    ok = abs(px) <= hw and not (abs(px) < hw - 3 and py < 2.2 - abs(px) * 0.0 and abs(px) > 2.5
                                                and math.hypot(abs(px) - hw * 0.5, py) < hw * 0.42)
                elif t < 0.6:
                    ok = abs(px) <= hw
                else:
                    u = (t - 0.6) / 0.4
                    ok = abs(px) <= hw * (1.0 - u ** 1.6) + (0.6 if u > 0.9 else 0)
            if ok:
                out.add((x, y))
    return out


def _edges(m):
    """(borda interna, contorno externo) da mascara (vizinhanca 4)."""
    inner, outer = set(), set()
    for (x, y) in m:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if q not in m:
                inner.add((x, y))
                outer.add(q)
    return inner, outer


def _pattern_color(pat, x, y, cx, cy, base, sec, tone):
    """Cor do campo no pixel (x, y) para o padrao."""
    dx, dy = x - cx, y - cy
    if pat == "faixa":
        return sec if -3 <= dy <= 2 else base
    if pat == "listras":
        return sec if (x // 3) % 2 == 0 else base
    if pat == "metade":
        return sec if dx >= 0 else base
    if pat == "diagonal":
        return sec if abs(dx + dy * 0.8) <= 3.2 else base
    if pat == "quartos":
        return sec if (dx >= 0) == (dy < 0) else base
    if pat == "chevron":
        return sec if 0 <= (dy - abs(dx) * 0.9) + 2 <= 4 else base
    if pat == "aro":
        return base if tone >= 3 else sec
    return base


def _shade(c, k):
    if k > 0:
        return lerp(c, (255, 246, 220), 0.22 * k)
    return lerp(c, (30, 16, 50), -0.2 * k)


def symbol_lum(sym):
    """Luminancia media (relativa) dos pixels do simbolo."""
    vals = [rel_lum(PAL[ch]) for row in _symbol_grid(sym) for ch in row if ch != "." and ch in PAL]
    return sum(vals) / len(vals) if vals else 0.5


_SYM_LUM = {}
MIN_SYMBOL_CONTRAST = 3.0             # simbolo (luminancia media) x fundo do medalhao


def medallion_colors(sp):
    """(fundo, brilho) do medalhao: escuro (tom fundo do time) e, se o simbolo for escuro, claro (creme)."""
    sym = sp["sym"]
    if sym not in _SYM_LUM:
        _SYM_LUM[sym] = symbol_lum(sym)
    _hi, _b, sh, dp = ramp(sp["color"])
    dark = lerp(dp, INK, 0.45)
    if (_SYM_LUM[sym] + 0.05) / (rel_lum(dark) + 0.05) < MIN_SYMBOL_CONTRAST:
        light = lerp(CREAM, sp["color"], 0.12)
        return light, lerp(light, (255, 255, 255), 0.6)
    return dark, lerp(dp, sh, 0.5)


def _symbol_grid(sym):
    if sym in GEN:
        return ["".join(r) for r in GEN[sym]()]
    return ART.get(sym) or ART["estrela"]


def _draw_symbol(cv, sym, ox, oy, inside):
    grid = _symbol_grid(sym)
    pts = {}
    for yy, row in enumerate(grid[:15]):
        for xx, ch in enumerate(row[:15]):
            if ch != "." and ch in PAL:
                pts[(ox + xx, oy + yy)] = PAL[ch]
    # contorno automatico 1 px (so dentro do medalhao)
    for (x, y) in list(pts):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            q = (x + dx, y + dy)
            if q not in pts and q in inside:
                cv.set(q[0], q[1], INK)
    for (x, y), c in pts.items():
        cv.set(x, y, c)


def _draw_text(cv, text, cx, y, fg, shadow):
    w = len(text) * 6 - 1
    x0 = int(round(cx - w / 2.0))
    for i, ch in enumerate(text):
        glyph = FONT.get(ch)
        if not glyph:
            continue
        for yy, row in enumerate(glyph):
            for xx, p in enumerate(row):
                if p == "#":
                    if shadow is not None and cv.get(x0 + i * 6 + xx + 1, y + yy + 1) not in (None, fg):
                        cv.set(x0 + i * 6 + xx + 1, y + yy + 1, shadow)
        for yy, row in enumerate(glyph):
            for xx, p in enumerate(row):
                if p == "#":
                    cv.set(x0 + i * 6 + xx, y + yy, fg)


def _star(cv, cx, cy, c_hi, c_lo):
    for dx, dy in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
        cv.set(cx + dx, cy + dy, c_hi if dy <= 0 and dx <= 0 else c_lo)
    for dx, dy in ((0, -2), (-1, -1), (1, -1), (-2, 0), (2, 0), (-1, 1), (1, 1), (0, 2)):
        if cv.get(cx + dx, cy + dy) is None:
            cv.set(cx + dx, cy + dy, INK)


def _behind(cv, pts):
    """Pinta `pts` ({(x, y): cor}) so onde a tela esta vazia (atras do escudo) e contorna com INK."""
    done = set()
    for (x, y), c in pts.items():
        if 0 <= x < cv.w and 0 <= y < cv.h and cv.get(x, y) is None:
            cv.set(x, y, c)
            done.add((x, y))
    for (x, y) in done:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if cv.get(x + dx, y + dy) is None and 0 <= x + dx < cv.w and 0 <= y + dy < cv.h:
                cv.set(x + dx, y + dy, INK)


def _laurel_pts(cx, cy, rx, ry):
    """Dois ramos de louro em arco dos lados do escudo (folhas alternadas, luz em cima)."""
    leaf_hi, leaf, leaf_lo, stem = (180, 236, 120), (96, 190, 84), (40, 120, 64), (52, 104, 50)
    pts = {}
    for side in (-1, 1):
        for i in range(0, 46):
            phi = math.radians(100 + i * 2.6)
            x = cx + side * -rx * math.cos(phi)
            y = cy + ry * math.sin(phi)
            pts[(int(round(x)), int(round(y)))] = stem
            if i % 5 == 2:
                for k, (ox, oy) in enumerate(((-1, -1), (-2, -1), (-2, -2), (-1, 0))):
                    c = leaf_hi if k == 2 else (leaf if k < 2 else leaf_lo)
                    pts[(int(round(x)) + side * ox, int(round(y)) + oy)] = c
            if i % 5 == 0:
                for k, (ox, oy) in enumerate(((1, -1), (2, -1), (2, 0))):
                    pts[(int(round(x)) + side * ox, int(round(y)) + oy)] = leaf if k else leaf_lo
    return pts


def _wing_pts(ax, ay, side):
    """Asa com 5 penas em leque saindo do canto de cima do escudo (side -1 esquerda, +1 direita)."""
    pts = {}
    feathers = ((-1.0, 0.15, 7), (-1.0, -0.35, 9), (-0.85, -0.85, 10), (-0.45, -1.1, 9), (-0.1, -1.2, 7))
    for k, (fx, fy, ln) in enumerate(feathers):
        n = math.hypot(fx, fy)
        fx, fy = fx / n * -side * -1, fy / n
        if side < 0:
            fx = -abs(fx) if feathers[k][0] < 0 else abs(fx)
        else:
            fx = abs(fx) if feathers[k][0] < 0 else -abs(fx)
        for t in range(ln):
            x, y = ax + fx * t, ay + fy * t
            w = 1.2 if t < ln - 2 else 0.6
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    if math.hypot(ox, oy) <= w:
                        q = (int(round(x + ox)), int(round(y + oy)))
                        tip = t >= ln - 3
                        c = (255, 252, 240) if oy < 0 or tip else (206, 212, 232)
                        if k == 0:
                            c = (176, 184, 210)
                        pts.setdefault(q, c)
    return pts


def render_logical(sp, compact=False):
    """Escudo na tela logica LW x LH (Surface SRCALPHA)."""
    cv = _Canvas(LW, LH)
    special = sp["special"]
    if special:
        x0, y0, x1, y1 = (5, 6, LW - 5, LH - 1) if special.get("sides") else (3, 6, LW - 3, LH - 1)
    else:
        x0, y0, x1, y1 = 2, 1, LW - 2, LH - 1
    m = _mask(sp["shape"], x0, y0, x1, y1)
    inner, outer = _edges(m)
    inner2 = set()
    if special:
        inner2, _o = _edges(m - inner)
    col = sp["color"]
    hi, base, sh, dp = ramp(col)
    sec = sp["sec"]
    shi, sbase, ssh, sdp = ramp(sec)
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    # profundidade (distancia da borda) para o padrao "aro" e o bevel
    depth = {}
    frontier = set(inner)
    d = 0
    left = set(m)
    while frontier and d < 6:
        for p in frontier:
            depth[p] = d
        left -= frontier
        nxt = set()
        for (x, y) in frontier:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if q in left and q not in depth:
                    nxt.add(q)
        frontier = nxt
        d += 1
    for p in left:
        depth.setdefault(p, 6)
    for (x, y) in m:
        c = _pattern_color(sp["pattern"], x, y, cx, cy - 2, base, sbase, depth.get((x, y), 6))
        # luz: diagonal suave de cima/esquerda para baixo/direita + bevel junto da borda
        g = ((x - x0) / float(x1 - x0) + (y - y0) / float(y1 - y0)) - 1.0
        k = -g * 0.9
        if depth.get((x, y), 6) == 1:
            nb_up = (x, y - 2) not in m or (x - 2, y) not in m
            k += 0.9 if nb_up else -0.7
        c = _shade(c, max(-1.2, min(1.2, k)))
        cv.set(x, y, c)
    # brilho: faixa diagonal clara no canto de cima/esquerda
    for (x, y) in m:
        if depth.get((x, y), 6) >= 2 and 5 <= (x - x0) + (y - y0) <= 6:
            c = cv.get(x, y)
            cv.set(x, y, lerp(c, (255, 255, 255), 0.18))
    # borda dourada (com brilho) e contorno escuro
    for (x, y) in inner:
        lit = (x - cx) + (y - cy) < -4
        cv.set(x, y, GOLD[0] if lit and (x + y) % 5 == 0 else (GOLD[1] if (x - cx) + (y - cy) < 6 else GOLD[2]))
    if special:
        for (x, y) in inner2:
            cv.set(x, y, INK)
    for (x, y) in outer:
        cv.set(x, y, INK)
    # medalhao com o simbolo (compacto: simbolo direto no campo, maior em proporcao, sem medalhao)
    if compact:
        mcx = cx - 0.5
        mcy = cy - 0.5 - (2.5 if sp["shape"] in ("pontudo", "classico", "frances") else 0.0)
        if special:
            mcy += 1.0
        ox, oy = int(round(mcx - 7)), int(round(mcy - 7))
        halo = lerp(dp, INK, 0.3)
        grid = _symbol_grid(sp["sym"])
        sym_px = {(ox + xx, oy + yy) for yy, row in enumerate(grid) for xx, ch in enumerate(row) if ch != "."}
        for (x, y) in sym_px:                       # sombra escura de 2 px em volta (destaca do padrao)
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    q = (x + dx, y + dy)
                    if q in m and q not in inner and abs(dx) + abs(dy) <= 3 and q not in sym_px:
                        cv.set(q[0], q[1], halo)
        _draw_symbol(cv, sp["sym"], ox, oy, m - inner)
    else:
        mcx, mcy, mr = cx - 0.5, y0 + 11.5 if not special else y0 + 10.5, 9.4
        if sp["shape"] == "losango":
            mcy += 2
        if sp["shape"] == "pontudo":
            mcy += 1
        med_bg, med_hi = medallion_colors(sp)
        disc = set()
        for y in range(LH):
            for x in range(LW):
                dd = math.hypot(x - mcx, y - mcy)
                if dd <= mr:
                    disc.add((x, y))
                    if dd > mr - 1.0:
                        cv.set(x, y, GOLD[2] if (x - mcx) + (y - mcy) > 3 else GOLD[1])
                    elif dd > mr - 2.0:
                        cv.set(x, y, INK)
                    else:
                        cv.set(x, y, med_hi if (x - mcx) + (y - mcy) < -6 else med_bg)
                elif dd <= mr + 1.0 and cv.get(x, y) is not None:
                    cv.set(x, y, INK)
        inside = {p for p in disc if math.hypot(p[0] - mcx, p[1] - mcy) <= mr - 1.6}
        ox, oy = int(round(mcx - 7)), int(round(mcy - 7))
        _draw_symbol(cv, sp["sym"], ox, oy, inside)
    # enfeites dos especiais
    if special:
        top = special.get("top")
        sides = special.get("sides")
        if sides == "louros":
            _behind(cv, _laurel_pts(cx - 0.5, y0 + 15, (x1 - x0) / 2.0 + 1.6, 18.5))
        elif sides == "asas":
            _behind(cv, _wing_pts(x0 + 2, y0 + 9, -1))
            _behind(cv, _wing_pts(x1 - 3, y0 + 9, 1))
        if top == "coroa":
            ccx = int(cx)
            for y in range(0, 6):
                for x in range(ccx - 6, ccx + 6):
                    rel = x - (ccx - 6)
                    tipline = 0 if rel in (0, 5, 6, 11) else (2 if rel in (1, 4, 7, 10) else 3)
                    if y >= tipline:
                        cv.set(x, y, GOLD[0] if y < 3 and rel < 6 else (GOLD[1] if y < 5 else GOLD[2]))
            for x in range(ccx - 7, ccx + 7):
                if cv.get(x, 6) is None:
                    cv.set(x, 6, INK)
            for (x, y) in ((ccx - 6, 0), (ccx - 1, 0), (ccx, 0), (ccx + 5, 0)):
                cv.set(x, y, (255, 255, 240))
            cv.set(ccx - 1, 4, (226, 52, 48))
            cv.set(ccx, 4, (226, 52, 48))
            for x in range(ccx - 7, ccx + 7):          # contorno da coroa
                for y in range(0, 7):
                    if cv.get(x, y) is None and any(
                            cv.get(x + a, y + b) in (GOLD[0], GOLD[1], GOLD[2], (255, 255, 240))
                            for a, b in ((1, 0), (-1, 0), (0, 1))):
                        cv.set(x, y, INK)
        elif top == "estrelas":
            for sx, sy in ((int(cx) - 7, 3), (int(cx), 2), (int(cx) + 6, 3)):
                _star(cv, sx, sy, (255, 244, 150), (240, 180, 50))
    # faixa com as iniciais
    if not compact:
        by = int(round(mcy + mr - 0.5))
        fill_hi, fill, fill_lo = ((252, 248, 236), (236, 226, 204), (196, 182, 160)) if sp["light_banner"] else \
            (lerp(NAVY, (90, 90, 140), 0.4), NAVY, (16, 14, 34))
        txt = INK if sp["light_banner"] else (255, 246, 220)
        bw = 2 + len(sp["ini"]) * 6 + 3
        bw = max(bw, 16)
        bx0 = int(round(cx - bw / 2.0))
        bx1 = bx0 + bw
        # pontas dobradas
        for side in (-1, 1):
            ex = bx0 - 1 if side < 0 else bx1
            for k in range(4):
                xx = ex + side * k
                for yy in range(by + 3, by + 11):
                    if k == 3 and yy in (by + 3, by + 10):
                        continue
                    edge = k == 3 or yy in (by + 3, by + 10)
                    cv.set(xx, yy, INK if edge else fill_lo)
            notch_x = ex + side * 3
            cv.set(notch_x, by + 6, None if cv.get(notch_x, by + 6) == INK else INK)
            cv.set(notch_x, by + 7, None if cv.get(notch_x, by + 7) == INK else INK)
            cv.set(notch_x - side, by + 6, INK)
            cv.set(notch_x - side, by + 7, INK)
        for x in range(bx0 - 1, bx1 + 1):
            cv.set(x, by, INK)
            cv.set(x, by + 10, INK)
            for y in range(by + 1, by + 10):
                if x in (bx0 - 1, bx1):
                    cv.set(x, y, INK)
                else:
                    cv.set(x, y, fill_hi if y == by + 1 else (fill_lo if y == by + 9 else fill))
        _draw_text(cv, sp["ini"], (bx0 + bx1) / 2.0, by + 2, txt,
                   fill_lo if sp["light_banner"] else (6, 4, 14))
    return cv.to_surface()


# ------------------------------------------------------------------------------------------ cache
_BASE = OrderedDict()                 # (nome, cor, custom, compacto) -> Surface logica
_CACHE = OrderedDict()                # (nome, cor, altura, custom) -> Surface pronta
_BYTES = [0]


def _ckey(custom):
    cu = sanitize(custom)
    return tuple(sorted(cu.items())) if cu else None


def _norm_color(color):
    try:
        return tuple(int(max(0, min(255, v))) for v in tuple(color)[:3])
    except (TypeError, ValueError):
        return (120, 120, 140)


def _base(name, color, custom, compact):
    k = (base_name(name), color, _ckey(custom), compact)
    s = _BASE.get(k)
    if s is not None:
        _BASE.move_to_end(k)
        return s
    s = render_logical(spec(name, color, custom), compact)
    STATS["base_gen"] += 1
    _BASE[k] = s
    while len(_BASE) > BASE_CACHE_MAX:
        _BASE.popitem(last=False)
    return s


def width_for(size):
    return max(1, int(round(int(size) * LW / float(LH))))


def _build(name, color, size, custom, compact):
    logical = _base(name, color, custom, compact)
    w = width_for(size)
    if size % LH == 0:
        return pygame.transform.scale(logical, (w, size))
    k = max(1, -(-size // LH))
    big = pygame.transform.scale(logical, (LW * k, LH * k)) if k > 1 else logical
    return pygame.transform.smoothscale(big, (w, size))


def _key(name, color, size, custom, compact):
    size = max(8, int(size))
    if compact is None:
        compact = size < LH
    return (base_name(name), _norm_color(color), size, _ckey(custom), bool(compact))


def get(name, color, size, custom=None, compact=None):
    """Escudo do time (Surface em cache) com `size` px de altura e largura size*LW/LH. compact: sem a faixa
    das iniciais e com o simbolo direto no campo (None = automatico: altura < 40)."""
    key = _key(name, color, size, custom, compact)
    s = _CACHE.get(key)
    if s is not None:
        _CACHE.move_to_end(key)
        STATS["hit"] += 1
        return s
    STATS["miss"] += 1
    t0 = time.perf_counter()
    s = _build(name, key[1], key[2], custom, key[4])
    STATS["gen_ms"] += (time.perf_counter() - t0) * 1000.0
    STATS["gen"] += 1
    _CACHE[key] = s
    _BYTES[0] += s.get_width() * s.get_height() * 4
    while _BYTES[0] > CACHE_MAX_BYTES and len(_CACHE) > 1:
        _k, old = _CACHE.popitem(last=False)
        _BYTES[0] -= old.get_width() * old.get_height() * 4
    STATS["bytes"] = _BYTES[0]
    return s


def has(name, color, size, custom=None, compact=None):
    return _key(name, color, size, custom, compact) in _CACHE


def warm(items):
    """Aquece o cache fora do desenho: items = [(nome, cor, altura[, custom[, compact]]), ...]."""
    n = 0
    for it in items:
        try:
            get(*it)
            n += 1
        except Exception:  # noqa: BLE001  (escudo nunca derruba a tela)
            pass
    return n


_PENDING = OrderedDict()              # pedidos de escudo ainda nao gerados (request -> pump)
PENDING_MAX = 256
PUMP_BUDGET_MS = 6.0


def request(name, color, size, custom=None, compact=None):
    """Escudo se ja estiver em cache; senao enfileira para pump() (fora do desenho) e devolve None."""
    key = _key(name, color, size, custom, compact)
    s = _CACHE.get(key)
    if s is not None:
        _CACHE.move_to_end(key)
        STATS["hit"] += 1
        return s
    if key not in _PENDING:
        _PENDING[key] = (name, key[1], key[2], custom, key[4])
        while len(_PENDING) > PENDING_MAX:
            _PENDING.popitem(last=False)
    return None


def pending():
    return len(_PENDING)


def pump(budget_ms=PUMP_BUDGET_MS):
    """Gera os escudos pedidos (no update do jogo, nunca no desenho): pelo menos 1 por chamada e mais
    enquanto couber no orcamento (ms). Devolve quantos gerou."""
    if not _PENDING:
        return 0
    t0 = time.perf_counter()
    n = 0
    while _PENDING:
        _k, args = _PENDING.popitem(last=True)      # o pedido mais novo primeiro (a tela atual)
        try:
            get(*args)
        except Exception:  # noqa: BLE001  (escudo nunca derruba o jogo)
            pass
        n += 1
        if (time.perf_counter() - t0) * 1000.0 >= budget_ms:
            break
    return n


def placeholder(screen, color, rect):
    """Enquanto o escudo nao fica pronto: um escudo simples na cor do time (so pygame.draw, sem Surface)."""
    r = pygame.Rect(rect)
    pts = [(r.x + 1, r.y + 1), (r.right - 2, r.y + 1), (r.right - 2, r.y + r.h * 6 // 10),
           (r.centerx, r.bottom - 2), (r.x + 1, r.y + r.h * 6 // 10)]
    pygame.draw.polygon(screen, _norm_color(color), pts)
    pygame.draw.polygon(screen, GOLD[1], pts, 1)


def blit(screen, name, color, size, center=None, custom=None, compact=None, **anchor):
    """Desenha o escudo ancorado (center=..., midleft=..., etc.): so blit de Surface em cache. Se ainda nao
    existe, pede a geracao (pump no proximo update) e desenha um escudo simples no lugar. Devolve o Rect."""
    s = request(name, color, size, custom, compact)
    if center is not None:
        anchor["center"] = center
    size = max(8, int(size))
    r = pygame.Rect(0, 0, width_for(size), size)
    for k, v in anchor.items():
        setattr(r, k, v)
    if s is None:
        placeholder(screen, color, r)
    else:
        screen.blit(s, r)
    return r


def clear():
    _PENDING.clear()
    _BASE.clear()
    _CACHE.clear()
    _BYTES[0] = 0
    STATS["bytes"] = 0


def cache_bytes():
    return _BYTES[0] + sum(s.get_width() * s.get_height() * 4 for s in _BASE.values())


# ------------------------------------------------------------------------------------------ catalogo
CLASSIC_TEAMS = (("Azul Clássico", (50, 120, 255)), ("Vermelho Clássico", (235, 65, 65)))


def all_teams():
    """Todos os times fixos do jogo (sem o do jogador): [{"name", "color", "src"}] sem nomes repetidos, na
    ordem amistoso, carreira, campanha (story.TEAMS: Atos 1-3, missoes), liga do Modo Robos. Os adversarios
    da Torre e do treino usam nomes da liga ("Parafusos FC 12" -> escudo do "Parafusos FC")."""
    import career
    import robot_league
    import story
    out, seen = [], set()

    def add(name, color, src):
        if name not in seen:
            seen.add(name)
            out.append({"name": name, "color": tuple(color), "src": src})
    for n, c in CLASSIC_TEAMS:
        add(n, c, "AMISTOSO")
    for n, c in career.CLUBS:
        add(n, c, "CARREIRA")
    for t in story.TEAMS.values():
        add(t["name"], t["color"], "CAMPANHA")
    for n, c in zip(robot_league.TEAM_NAMES, robot_league.TEAM_COLORS):
        add(n, c, "MODO ROBOS")
    return out
