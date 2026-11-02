# -*- coding: utf-8 -*-
"""Torcida da partida (Fase 4, Onda A, passos A1-A7).

Tudo desenhado por codigo (pygame.draw), pre-renderizado no inicio da partida:

- **Atomo**: espectador de 14x18 (cabeca, tronco, bracos), 4 tons de pele x 5 cabelos x
  camisetas (casa / fora / neutras), em 5 poses: sentado, de pe com bracos para cima,
  decepcao (maos na cabeca) e 2 quadros de "bandeira" (aceno; alguns seguram bandeirinha).
  Na arquibancada frontal (lado da camera) a torcida aparece de costas; nas laterais, de
  frente, girada para olhar o campo. Locais de robos (`laboratorio`, `fabrica`) usam
  robos-fa com olhos de LED.
- **Segmentos**: cada fileira/coluna da arquibancada e dividida em faixas de ate 8 lugares.
  Cada faixa tem uma "fidelidade" (`home`, `away`, `neutral`) e uma Surface pronta por pose
  (colorkey). Por quadro so ha blits dessas faixas (com deslocamento de pulo): nenhuma
  Surface e criada depois de `warm_crowd`.
- **Arena composta** (`stands_static`): `pitch_surf` + degraus, cadeiras, corrimaos,
  refletores, placa de LED (parte fixa) e a torcida distante (estatica, sob o HUD), numa
  unica Surface 1100x700. Mais a tarja translucida do rodape (UI legivel sobre a torcida).
- **Cache**: um "pacote" (atlas + arena composta + tarja) por (local, cor casa, cor fora,
  nivel), LRU de 3 chaves.
- **Reacoes** (`Crowd.event`): humores por fidelidade (gol, chance, defesa, trave,
  pontape inicial, fim de jogo), ola, calmaria. RNG proprio (`random.Random`) e relogio
  injetavel: nunca toca o random global nem o estado da simulacao. Estado atualizado a
  cada N quadros (3 em ALTA, 6 em MEDIA).
- **Extras** (A4, tabela EXTRAS por local): confete (pygame.draw.rect), flashes de camera e
  sinalizadores (sprites aditivos prontos), fumaca colorida (3 sprites alfa prontos), bandeiras
  de 2 quadros nas laterais, mosaico (pose MOSAIC: cartoes formando listras na cor do time, no
  pontape inicial e na vitoria) e faixas de pano na grade da frente. Particulas com teto fixo
  (CONFETTI_MAX/FLASH_MAX/SMOKE_MAX por nivel) e vida por tempo real (RNG proprio `fxr`).
- **LED e "som visual"** (A5): placa de LED do topo = tira longa pre-renderizada, scroll com
  `blit(area=...)`; onomatopeias com 4 degraus de cor pre-buscados via Game.text_img.
- **Telao** (A6): legendas de 2 locutores (CAPTIONS) no rodape, so em partidas assistidas.
- **LOD** (A7): ver LOD_* (media do quadro de partida em janelas de 60 quadros; > 4 ms desce,
  < 2,5 ms por 3 janelas sobe). Em MAX nada disso e desenhado nem atualizado.

Geometria (tela logica 1100x700, PITCH = Rect(60, 90, 980, 560)): fundo/frente
y 654..700 (3 fileiras), laterais x 0..56 / 1044..1100 (3 colunas; no bolsao do gol so
a coluna de fora, x 2..20), distante y 0..78 (sob o HUD), placa de LED y 79..87. A tarja
do rodape (y 670..700) fica por cima da torcida, mais opaca atras dos textos/botoes.
"""
import math
import random
import time
import zlib
from collections import OrderedDict

import pygame

W, H = 1100, 700
PITCH = pygame.Rect(60, 90, 980, 560)
CX, CY = PITCH.center

AW, AH = 14, 18                 # atomo (espectador) em pe/sentado, vista "de frente para a camera"
KEY = (255, 0, 255)             # colorkey das faixas
CACHE_MAX = 3
DEFAULT_VENUE = "arena"         # partidas assistidas sem local definido (o mapeamento por modo e o A8)

SIT, UP, SAD, FLAG_A, FLAG_B, MOSAIC = range(6)
POSES = (SIT, UP, SAD, FLAG_A, FLAG_B)
POSE_NAMES = ("sentado", "bracos_para_cima", "decepcao", "bandeira_a", "bandeira_b", "mosaico")

# nivel (prefs "crowd") -> densidade, atualizacao a cada N quadros, ondas (ola/calmaria)
LEVELS = {
    "ALTA": {"density": 1.0, "every": 3, "waves": True},
    "MEDIA": {"density": 0.6, "every": 6, "waves": False},
}

# --- geometria -------------------------------------------------------------------------------
FRONT_ROW_Y = (655, 667, 679)   # topo da caixa 14x18 de cada fileira frontal (0 = mais perto do campo)
FRONT_SEATS = 72                # lugares por fileira em 0..1100
SEG_SEATS = 8                   # lugares por faixa (frente)
SIDE_COL_X = (38, 20, 2)        # esquerda: x da caixa 18x14 de cada coluna (0 = mais perto do campo)
SIDE_Y0, SIDE_Y1 = 92, 648
SIDE_PITCH = 14
SIDE_SEG = 7                    # lugares por faixa (laterais)
POCKET = (276, 464)             # bolsao do gol: colunas 0 e 1 param aqui
FAR_ROWS = (66, 55, 44, 33, 22, 11)   # torcida distante (estatica): topo de pessoas de 10 px
TARJA_Y = 670
HOME_X, AWAY_X = 440, 660       # frente: x < 440 casa, > 660 visitante, meio neutro

# --- locais (spec 2.5) -------------------------------------------------------------------------
# front: fileiras frontais; span: faixa x da arquibancada frontal; sides: laterais ("L"/"R");
# far: pessoas na arquibancada distante (estatica); people: total da spec; ola: arena+;
# robots: robos-fa no lugar de pessoas; style: paleta da estrutura.
VENUES = {
    "bairro":      dict(front=2, span=(300, 800), sides="", far=0, people=30, ola=False, robots=False, style="bairro"),
    "quadra":      dict(front=3, span=(200, 900), sides="", far=0, people=30, ola=False, robots=False, style="madeira"),
    "ginasio":     dict(front=3, span=(0, W), sides="L", far=0, people=90, ola=False, robots=False, style="ginasio"),
    "arena":       dict(front=3, span=(0, W), sides="LR", far=0, people=220, ola=True, robots=False, style="arena"),
    "estadio":     dict(front=3, span=(0, W), sides="LR", far=110, people=360, ola=True, robots=False, style="estadio"),
    "superliga":   dict(front=3, span=(0, W), sides="LR", far=110, people=360, ola=True, robots=False, style="superliga"),
    "mundial":     dict(front=3, span=(0, W), sides="LR", far=150, people=520, ola=True, robots=False, style="mundial"),
    "coliseu":     dict(front=3, span=(0, W), sides="LR", far=150, people=520, ola=True, robots=False, style="coliseu"),
    "laboratorio": dict(front=3, span=(150, 950), sides="LR", far=0, people=100, ola=False, robots=True, style="laboratorio"),
    "fabrica":     dict(front=3, span=(150, 950), sides="LR", far=0, people=100, ola=False, robots=True, style="fabrica"),
    "dojo":        dict(front=2, span=(250, 850), sides="", far=0, people=40, ola=False, robots=False, style="dojo"),
    "aeroporto":   dict(front=2, span=(250, 850), sides="", far=0, people=40, ola=False, robots=False, style="aeroporto"),
}

# estrutura: degrau, borda (neon/corrimao), cadeira, refletores, placa de LED no topo
STYLES = {
    "bairro":      dict(step=(44, 48, 58), edge=(96, 104, 120), seat=(30, 34, 42), lights=False, board=False),
    "madeira":     dict(step=(84, 56, 34), edge=(150, 104, 62), seat=(62, 40, 24), lights=False, board=False),
    "ginasio":     dict(step=(34, 42, 60), edge=(70, 150, 200), seat=(24, 52, 92), lights=False, board=True),
    "arena":       dict(step=(26, 34, 56), edge=(0, 170, 230), seat=(18, 40, 78), lights=True, board=True),
    "estadio":     dict(step=(28, 32, 48), edge=(0, 200, 255), seat=(20, 36, 70), lights=True, board=True),
    "superliga":   dict(step=(30, 28, 50), edge=(170, 110, 255), seat=(40, 26, 74), lights=True, board=True),
    "mundial":     dict(step=(32, 30, 44), edge=(255, 205, 70), seat=(52, 40, 24), lights=True, board=True),
    "coliseu":     dict(step=(36, 30, 22), edge=(220, 170, 60), seat=(40, 30, 16), lights=True, board=True),
    "laboratorio": dict(step=(20, 36, 42), edge=(60, 255, 180), seat=(16, 50, 46), lights=False, board=True),
    "fabrica":     dict(step=(40, 38, 34), edge=(255, 150, 40), seat=(54, 44, 30), lights=False, board=True),
    "dojo":        dict(step=(112, 118, 66), edge=(70, 46, 30), seat=(86, 92, 50), lights=False, board=False),
    "aeroporto":   dict(step=(58, 62, 72), edge=(190, 196, 210), seat=(40, 70, 120), lights=False, board=False),
}

# --- extras (A4) por local (spec 2.4/2.5) --------------------------------------------------------
# confetti/flashes/flares (sinalizadores + fumaca)/mosaic: liga o efeito; flags: bandeiras nas
# laterais (2 quadros); banners: faixas de pano na grade da frente; led: placa de LED do topo
# (os locais com moldura de placa, STYLES[...]["board"]); conf: paleta do confete.
_B = {
    "zé": "VAI, ZÉ POEIRA!", "gol": "ASPIRA QUE É GOL!", "sf": "SANTA FAÍSCA 4 EVER",
    "limpex": "LIMPEX: LIMPA, MAS NÃO GANHA", "po": "SEM POEIRA, SEM PIEDADE",
}
EXTRAS = {
    "bairro":      dict(confetti=False, flashes=False, flares=False, flags=0, mosaic=False,
                        banners=(_B["zé"], _B["gol"])),
    "quadra":      dict(confetti=False, flashes=False, flares=False, flags=0, mosaic=False,
                        banners=(_B["zé"], _B["po"])),
    "ginasio":     dict(confetti=False, flashes=False, flares=False, flags=3, mosaic=False,
                        banners=(_B["sf"], _B["gol"])),
    "arena":       dict(confetti=True, flashes=True, flares=False, flags=2, mosaic=False,
                        banners=(_B["zé"], _B["limpex"])),
    "estadio":     dict(confetti=True, flashes=True, flares=True, flags=4, mosaic=True,
                        banners=(_B["zé"], _B["sf"], _B["limpex"])),
    "superliga":   dict(confetti=True, flashes=True, flares=True, flags=4, mosaic=True,
                        banners=(_B["zé"], "SUPERLIGA OU NADA", _B["limpex"])),
    "mundial":     dict(confetti=True, flashes=True, flares=True, flags=8, mosaic=True, nations=True,
                        banners=(_B["zé"], "O MUNDO É NOSSO TAPETE", _B["sf"])),
    "coliseu":     dict(confetti=True, flashes=True, flares=True, flags=6, mosaic=True, conf="coliseu",
                        banners=(_B["zé"], "OMEGA? SÓ SE FOR OMELETE", "NENHUM GRÃO DE PÓ")),
    "laboratorio": dict(confetti=False, flashes=True, flares=False, flags=0, mosaic=False, alert=True,
                        banners=("CIÊNCIA COM CHINELO", "GOL = 1, DERROTA = 0")),
    "fabrica":     dict(confetti=False, flashes=True, flares=False, flags=0, mosaic=False, alert=True,
                        banners=("TURNO DA NOITE APOIA", "MONTADO COM AMOR")),
    "dojo":        dict(confetti=False, flashes=False, flares=False, flags=0, mosaic=False,
                        banners=("GANBARE!", "GANBARE, ZÉ-SAN!")),
    "aeroporto":   dict(confetti=False, flashes=False, flares=False, flags=0, mosaic=False,
                        banners=("BEM-VINDOS AO PORTÃO 7", "BAGAGEM DE MÃO: 1 BOLA")),
}
NATIONS = (((0, 150, 70), (250, 210, 0)), ((30, 60, 170), (240, 240, 240), (30, 60, 170)),
           ((200, 30, 40), (240, 240, 240)), ((20, 20, 20), (220, 40, 40), (250, 200, 0)))
GOLD = (255, 210, 60)

# tetos fixos de particulas por nivel (MEDIA = reduzido; MAX/OFF = nada)
CONFETTI_MAX = {"ALTA": 90, "MEDIA": 40}
FLASH_MAX = {"ALTA": 8, "MEDIA": 4}
SMOKE_MAX = {"ALTA": 14, "MEDIA": 0}
ONO_MAX = 2                     # onomatopeias ao mesmo tempo

# placa de LED do topo (moldura fixa em y 79..87 desenhada em _draw_static)
LED_X, LED_Y, LED_W, LED_H = PITCH.left + 1, 79, PITCH.w - 2, 8
LED_ADS = ("LIMPEX - PERFEICAO EM CADA CANTO", "CERA TURBO: BRILHO ATE NO GOL", "ASPIRE COM MODERACAO",
           "SANTA FAISCA BATERIAS - CARGA QUE NAO ACABA", "RODINHAS DO VO - DESDE 1987",
           "PROIBIDO ASPIRAR O JUIZ")
LED_HEAD = {"ginasio": "GINASIO DO BAIRRO", "arena": "ARENA LIMPEX", "estadio": "ESTADIO MUNICIPAL",
            "superliga": "SUPERLIGA ASPIRADORA", "mundial": "COPA DOS CAMPEOES",
            "coliseu": "COLISEU DO PO - CASA DO X-OMEGA", "laboratorio": "LABORATORIO 7 - ROBOS TRABALHANDO",
            "fabrica": "FABRICA DE ZES - SEGURANCA EM 1O LUGAR"}
LED_AMBER = (255, 176, 48)
LED_SPEED, LED_GOAL_SPEED, LED_GOAL_S = 45, 150, 3.5

# "som visual": onomatopeias (spec 2.6), via Game.text_img, 4 degraus de cor pre-cacheados
WORDS = {"goal": "GOOOL!", "no": "NÃOOO!", "go": "VAAAI!", "ole": "OLÉ!", "uh": "UHHH!", "oh": "OOOH!",
         "clang": "CLANG!", "clap": "CLAP CLAP", "win": "OLÉ, OLÉ!"}
ROBOT_WORDS = dict(WORDS, go="BIP BIP!", uh="BZZZT!", ole="OLÉ.EXE", no="ERRO 404!", clap="CLIC CLIC")
WORD_SIZE = {"goal": 52}        # demais: 36
ONO_FADE = (1.0, 0.78, 0.55, 0.32)
ONO_S, ONO_RISE, ONO_Y = 1.0, 30, 632

# telao (spec 2.7): legendas de 2 locutores, so em partidas assistidas
TELAO = pygame.Rect(236, 665, 356, 26)
TELAO_SIZE = 20
SPEAKERS = (("TONHO:", (255, 214, 90)), ("CLEIDE:", (255, 140, 200)))
CAPTIONS = {
    "goal": (("Que lance, Cleide!", "O chinelo ainda está no lugar, Tonho."),
             ("É GOL! Pode varrer a rede!", "Nenhum grão de pó resistiu, Tonho."),
             ("Entrou! A sala inteira vibra!", "Até o tapete levantou, Tonho!")),
    "chance": (("Lá vem ele, lá vem ele...", "Bateria no talo, Tonho!"),
               ("Chute perigoso!", "Quase aspirou a trave, Tonho."),
               ("Olha o chute, Cleide!", "Esse foi com vontade!")),
    "save": (("Que defesa, Cleide!", "Goleiro com sucção máxima, Tonho."),
             ("Pegou! Pegou!", "Parece que tem ímã nas luvas."),
             ("Defesaça!", "Não deixa passar nem migalha.")),
    "post": (("Na trave! Na trave!", "Fez barulho de panela, Tonho."),
             ("Trave! Por um fio de cabelo!", "Fio de cabelo ele aspira, Tonho.")),
    "kickoff": (("Rola a bola, Cleide!", "Filtros limpos e motores ligados."),
                ("Começa o jogo!", "Torcida em festa, Tonho!")),
    "win": (("Acabou! Que vitória!", "A torcida vai limpar a casa hoje."),
            ("Fim de papo, Cleide!", "Missão cumprida, sala impecável.")),
    "draw": (("Fim de jogo: empate!", "Cada um varreu metade, Tonho."),),
    "idle": (("Clima de decisão aqui, Cleide.", "Cheiro de cera nova no ar, Tonho."),
             ("A bola corre limpinha.", "Gramado sem um farelo sequer."),
             ("Recado do patrocinador...", "Aspire com moderação!"),
             ("Que torcida, Cleide!", "Até os robôs do vô estão de pé.")),
}
CAP_PRIO = {"goal": 3, "win": 4, "draw": 4, "save": 2, "post": 2, "chance": 1, "kickoff": 1, "idle": 0}
CAP_LINE_S = (2.2, 2.6)         # Tonho, depois Cleide
CAP_IDLE_GAP = 7.0

# LOD automatico (A7): media de Game.draw em janelas de LOD_WINDOW quadros de partida (1x-4x).
# Acima de LOD_DOWN_MS desce um nivel (2 completo -> 1 sem ondas/confete/fumaca, poses a cada 2N
# quadros -> 0 torcida congelada sentada, sem flashes/bandeiras animadas). Volta um nivel depois de
# LOD_UP_WINDOWS janelas seguidas abaixo de LOD_UP_MS (histerese: nao oscila).
LOD_WINDOW, LOD_DOWN_MS, LOD_UP_MS, LOD_UP_WINDOWS = 60, 4.0, 2.5, 3

SKINS = ((242, 204, 168), (210, 156, 114), (156, 104, 68), (100, 64, 42))
HAIRS = (("curto", (30, 24, 22)), ("longo", (104, 62, 32)), ("afro", (36, 26, 20)),
         ("curto", (226, 190, 96)), ("bone", None))
NEUTRAL_SHIRTS = ((214, 216, 222), (236, 196, 64))
ROBOT_METAL = ((120, 130, 146), (150, 140, 120), (96, 110, 120))

_CACHE = OrderedDict()          # (venue, home, away, level) -> _Bundle
STATS = {"builds": 0}           # quantas vezes um pacote foi construido (testes de cache)


def scale(c, f):
    return (min(255, int(c[0] * f)), min(255, int(c[1] * f)), min(255, int(c[2] * f)))


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _shirt(c):
    """Cor de camiseta legivel no fundo escuro, um pouco abaixo do LED dos robos."""
    c = tuple(int(x) for x in c[:3])
    lum = _lum(c)
    if lum < 110:
        c = mix(c, (255, 255, 255), (110 - lum) / 255.0)
    return scale(c, 0.86)


def resolve_venue(venue):
    return venue if venue in VENUES else DEFAULT_VENUE


def resolve_level(level):
    return level if level in LEVELS else "ALTA"


def _seed(*parts):
    return zlib.crc32(":".join(str(p) for p in parts).encode("latin-1"))


# --- atomo ------------------------------------------------------------------------------------
def _arm(s, a, b, c, w=2):
    pygame.draw.line(s, c, a, b, w)


def draw_person(s, ox, oy, look, pose, back):
    """Espectador 14x18 em (ox, oy). look = (pele, cabelo, camiseta, bandeira)."""
    skin, hair, shirt, flag = look
    style, hcol = hair
    sh_d = scale(shirt, 0.66)
    sk_d = scale(skin, 0.8)
    seated = pose == SIT
    hy = oy + (7 if seated else 5)
    ty = oy + (11 if seated else 9)
    x = ox
    # tronco (ombros arredondados) + sombra lateral
    pygame.draw.rect(s, shirt, (x + 3, ty + 1, 8, oy + AH - ty - 1))
    pygame.draw.rect(s, shirt, (x + 4, ty, 6, 1))
    pygame.draw.line(s, sh_d, (x + 10, ty + 1), (x + 10, oy + AH - 1))
    if back:                                             # costas: faixa clara (numero/listra)
        pygame.draw.line(s, scale(shirt, 1.25), (x + 6, ty + 3), (x + 7, ty + 3))
        pygame.draw.line(s, scale(shirt, 1.25), (x + 6, ty + 5), (x + 7, ty + 5))
    # bracos
    left_up = pose in (UP, FLAG_A)
    right_up = pose in (UP, FLAG_B)
    if pose == SAD:                                      # maos na cabeca
        _arm(s, (x + 3, ty + 1), (x + 1, ty - 2), shirt)
        _arm(s, (x + 1, ty - 2), (x + 4, hy - 3), skin)
        _arm(s, (x + 10, ty + 1), (x + 12, ty - 2), shirt)
        _arm(s, (x + 12, ty - 2), (x + 9, hy - 3), skin)
    else:
        for side, up in ((0, left_up), (1, right_up)):
            sx = x + (2 if side == 0 else 11)
            if up:
                hx = x + (1 if side == 0 else 12)
                _arm(s, (x + (3 if side == 0 else 10), ty + 1), (sx, ty - 3), shirt)
                _arm(s, (sx, ty - 3), (hx, oy + 1), skin)
                pygame.draw.rect(s, skin, (hx - 1 if side == 0 else hx, oy, 2, 2))
                if flag and (pose == FLAG_A and side == 0 or pose == FLAG_B and side == 1):
                    fx = hx - 1 if side == 0 else hx - 3
                    pygame.draw.rect(s, flag, (fx, oy, 5, 3))
                    pygame.draw.line(s, (240, 240, 240), (fx, oy + 1), (fx + 4, oy + 1))
            else:
                pygame.draw.line(s, sh_d, (sx, ty + 1), (sx, ty + 5))
                s.set_at((sx, ty + 6), sk_d)
    # cabeca
    if back:
        if style == "bone":
            pygame.draw.circle(s, shirt, (x + 7, hy), 3)
            pygame.draw.line(s, sh_d, (x + 4, hy + 1), (x + 10, hy + 1))
        else:
            pygame.draw.circle(s, hcol, (x + 7, hy), 4 if style == "afro" else 3)
            if style == "longo":
                pygame.draw.rect(s, hcol, (x + 4, hy, 7, 4))
        pygame.draw.line(s, scale(mix(hcol or shirt, (200, 220, 255), 0.45), 1.0), (x + 6, hy - 3), (x + 8, hy - 3))
        s.set_at((x + 7, hy + 3), sk_d)                  # nuca
    else:
        if style == "afro":
            pygame.draw.circle(s, hcol, (x + 7, hy - 1), 4)
        elif style == "longo":
            pygame.draw.rect(s, hcol, (x + 3, hy - 2, 9, 6))
        pygame.draw.circle(s, skin, (x + 7, hy), 3)
        if style == "bone":
            pygame.draw.rect(s, shirt, (x + 4, hy - 3, 7, 2))
            pygame.draw.line(s, sh_d, (x + 3, hy - 1), (x + 11, hy - 1))
        elif style in ("curto", "longo"):
            pygame.draw.rect(s, hcol, (x + 4, hy - 3, 7, 2))
        if pose == SAD:
            pygame.draw.line(s, (40, 20, 20), (x + 6, hy + 2), (x + 8, hy + 2))
        else:
            s.set_at((x + 6, hy), (30, 24, 24))
            s.set_at((x + 8, hy), (30, 24, 24))
            if pose != SIT:                              # boca aberta (grito)
                s.set_at((x + 7, hy + 2), (90, 20, 20))


def draw_robot_fan(s, ox, oy, look, pose, back):
    """Robo-fa 14x18: cabeca quadrada com olhos de LED, antena, bracos finos."""
    metal, led, flag = look
    seated = pose == SIT
    hy = oy + (6 if seated else 4)
    ty = oy + (11 if seated else 9)
    x = ox
    dark = scale(metal, 0.55)
    pygame.draw.rect(s, metal, (x + 3, ty, 8, oy + AH - ty))
    pygame.draw.line(s, dark, (x + 10, ty), (x + 10, oy + AH - 1))
    pygame.draw.line(s, led, (x + 5, ty + 3), (x + 8, ty + 3))          # faixa de LED do peito
    left_up = pose in (UP, FLAG_A)
    right_up = pose in (UP, FLAG_B)
    for side, up in ((0, left_up), (1, right_up)):
        sx = x + (2 if side == 0 else 11)
        if pose == SAD:
            _arm(s, (sx, ty + 1), (x + (4 if side == 0 else 9), hy - 2), dark, 1)
        elif up:
            hx = x + (1 if side == 0 else 12)
            _arm(s, (sx, ty + 1), (hx, oy + 1), dark, 1)
            pygame.draw.rect(s, led, (hx - 1 if side == 0 else hx, oy, 2, 2))
            if flag and (pose == FLAG_A and side == 0 or pose == FLAG_B and side == 1):
                fx = hx - 1 if side == 0 else hx - 3
                pygame.draw.rect(s, flag, (fx, oy, 5, 3))
        else:
            _arm(s, (sx, ty + 1), (sx, ty + 6), dark, 1)
    pygame.draw.rect(s, scale(metal, 0.8), (x + 3, hy - 3, 8, 6))
    pygame.draw.line(s, (200, 210, 225), (x + 4, hy - 3), (x + 9, hy - 3))
    pygame.draw.line(s, dark, (x + 7, hy - 3), (x + 7, hy - 5))
    s.set_at((x + 7, hy - 6), led)
    if not back:
        eye = led if pose != SAD else scale(led, 0.45)
        pygame.draw.rect(s, eye, (x + 4, hy - 1, 2, 2))
        pygame.draw.rect(s, eye, (x + 8, hy - 1, 2, 2))


def _tiny(s, x, y, skin, hcol, shirt):
    """Pessoa de 10 px da torcida distante (estatica)."""
    pygame.draw.rect(s, shirt, (x + 1, y + 5, 6, 5))
    pygame.draw.circle(s, skin, (x + 4, y + 3), 2)
    if hcol:
        pygame.draw.line(s, hcol, (x + 2, y + 1), (x + 5, y + 1))


# --- layout -----------------------------------------------------------------------------------
def _seats(v):
    """Lugares possiveis do local: lista de (zona, linha/coluna, indice, caixa_x, caixa_y, cx, cy)."""
    out = []
    x0, x1 = v["span"]
    for row in range(v["front"]):
        for i in range(FRONT_SEATS):
            cx = int((i + 0.5) * W / FRONT_SEATS) + (7 if row % 2 else 0)
            if cx - 7 < x0 or cx + 7 > x1 + 7:
                continue
            y = FRONT_ROW_Y[row]
            out.append(("F", row, i, cx - 7, y, cx, y + 9))
    for zone in v["sides"]:
        for col, lx in enumerate(SIDE_COL_X):
            bx = lx if zone == "L" else W - lx - AH
            for k, y in enumerate(range(SIDE_Y0, SIDE_Y1 - SIDE_PITCH + 1, SIDE_PITCH)):
                if col < 2 and y + SIDE_PITCH > POCKET[0] and y < POCKET[1]:
                    continue
                out.append((zone, col, k, bx, y, bx + 9, y + 7))
    return out


def _seg_key(seat):
    zone, line, idx = seat[0], seat[1], seat[2]
    if zone == "F":
        return (zone, line, idx // SEG_SEATS)
    # laterais: corridas continuas; quebra no bolsao do gol e a cada SIDE_SEG lugares
    run = 0 if seat[4] < POCKET[0] else (1 if seat[4] < POCKET[1] else 2)
    return (zone, line, run, idx // SIDE_SEG)


def _fidelity(zone, cx):
    if zone == "L":
        return "home"
    if zone == "R":
        return "away"
    if cx < HOME_X:
        return "home"
    if cx > AWAY_X:
        return "away"
    return "neutral"


def _pick(v, seats, n, rng):
    """Escolhe n lugares: o publico se concentra no meio e perto do campo (nada de pontinhos soltos)."""
    if n >= len(seats):
        return set(range(len(seats)))
    scored = []
    for k, s in enumerate(seats):
        zone, line = s[0], s[1]
        if zone == "F":
            w = 1.0 - abs(s[5] - W / 2) / (W / 2) * 0.8 + (0.35, 0.18, 0.0)[line]
        else:
            w = 0.7 - abs(s[6] - CY) / 300.0 * 0.6 + (0.45, 0.2, 0.0)[line]
        # grupinhos: ruido por bloco de 3 lugares + ruido individual
        w += _blockjit(s, v) * 0.6 + rng.random() * 0.25
        scored.append((w, k))
    scored.sort(reverse=True)
    return {k for _, k in scored[:n]}


def _blockjit(s, v):
    return (_seed(v["style"], s[0], s[1] // 2, s[2] // 4) % 1000) / 1000.0


def people_count(venue, level="ALTA"):
    """Pessoas desenhadas (dinamicas + distantes) no local/nivel."""
    v = VENUES[resolve_venue(venue)]
    dens = LEVELS[resolve_level(level)]["density"]
    far = int(round(v["far"] * dens))
    dyn = min(len(_seats(v)), int(round((v["people"] - v["far"]) * dens)))
    return dyn + far


# --- construcao do pacote ---------------------------------------------------------------------
class Seg:
    """Faixa da arquibancada: posicao, fidelidade, Surfaces por pose e vetor de pulo."""
    __slots__ = ("zone", "fid", "x", "y", "imgs", "jump", "cx", "cy", "wave", "ph", "n")

    def __init__(self, zone, fid, x, y, imgs, jump, cx, cy, wave, ph, n):
        self.zone, self.fid, self.x, self.y, self.imgs = zone, fid, x, y, imgs
        self.jump, self.cx, self.cy, self.wave, self.ph, self.n = jump, cx, cy, wave, ph, n


class _Bundle:
    __slots__ = ("key", "venue", "level", "static", "tarja", "segs", "people", "nbytes", "build_ms",
                 "ex", "colors", "ono_cols", "anchors", "flags", "flares", "smoke", "star", "conf_cols", "telao",
                 "txt_id", "banners", "led_ads", "led_goal", "led_period")


def _looks(v, venue, seats, chosen, home, away, rng):
    """Aparencia de cada lugar ocupado (85% de pureza de cor por fidelidade)."""
    shirts = {"home": _shirt(home), "away": _shirt(away)}
    neutrals = [_shirt(c) for c in NEUTRAL_SHIRTS]
    looks = {}
    for k in chosen:
        s = seats[k]
        fid = _fidelity(s[0], s[5])
        r = rng.random()
        if fid == "neutral":
            shirt = shirts["home"] if r < 0.4 else shirts["away"] if r < 0.8 else rng.choice(neutrals)
        elif r < 0.85:
            shirt = shirts[fid]
        elif r < 0.95:
            shirt = rng.choice(neutrals)
        else:
            shirt = shirts["away" if fid == "home" else "home"]
        flag = shirt if rng.random() < 0.3 else None
        if v["robots"]:
            looks[k] = ("robo", (rng.choice(ROBOT_METAL), _shirt(shirt) if shirt in neutrals else
                                 scale(shirt, 1.15), flag))
        else:
            looks[k] = ("pessoa", (rng.choice(SKINS), rng.choice(HAIRS), shirt, flag))
    return looks


def _atom(cache, kind, look, pose, back):
    key = (kind, look, pose, back)
    a = cache.get(key)
    if a is None:
        a = pygame.Surface((AW, AH), pygame.SRCALPHA)
        (draw_robot_fan if kind == "robo" else draw_person)(a, 0, 0, look, pose, back)
        cache[key] = a
    return a


def _card(seat, cols):
    """Cor do cartao do mosaico no lugar: listras diagonais (cor do time / clara) pela posicao na tela."""
    main, light = cols
    if seat[0] == "F":
        k = seat[5] // 20 + seat[1]
    else:
        k = seat[6] // 20 + seat[1]
    return light if k % 3 == 0 else main


def _build_segments(v, venue, seats, looks, atoms, mosaic=None):
    """Faixas prontas por pose. mosaic = {"home": (cor, clara), "away": (...)} acrescenta a pose
    MOSAIC (cartoes levantados formando listras na cor do time); faixas neutras reusam a pose UP."""
    groups = OrderedDict()
    for k, s in enumerate(seats):
        groups.setdefault(_seg_key(s), []).append(k)
    segs = []
    nbytes = 0
    for gkey, ks in groups.items():
        occ = [k for k in ks if k in looks]
        if not occ:
            continue
        zone = gkey[0]
        first = seats[ks[0]]
        if zone == "F":
            x0 = min(seats[k][3] for k in ks)
            x1 = max(seats[k][3] for k in ks) + AW
            w, h = x1 - x0, AH
            pos = [(seats[k][3] - x0, 0) for k in occ]
        else:
            # faixa horizontal "de frente", girada depois: esquerda +90 (cabeca para fora), direita -90
            ys = [seats[k][4] for k in ks]
            y0, y1 = min(ys), max(ys) + SIDE_PITCH
            w, h = y1 - y0, AH
            if zone == "L":   # rotate(+90): a borda esquerda da faixa vai para baixo
                pos = [(y1 - SIDE_PITCH - seats[k][4], 0) for k in occ]
            else:             # rotate(-90): a borda esquerda vai para cima
                pos = [(seats[k][4] - y0, 0) for k in occ]
        back = zone == "F"
        imgs = []
        if zone == "F":
            seg_fid = _fidelity(zone, (x0 + x1) // 2)
        else:
            seg_fid = _fidelity(zone, 0)
        poses = POSES
        if mosaic:
            poses = POSES + (MOSAIC,)
        for pose in poses:
            if pose == MOSAIC and seg_fid not in mosaic:
                imgs.append(imgs[UP])
                continue
            st = pygame.Surface((w, h)).convert()
            st.fill(KEY)
            for k, p in zip(occ, pos):
                kind, look = looks[k]
                if pose == MOSAIC:
                    st.blit(_atom(atoms, kind, look, UP, back), p)
                    c = _card(seats[k], mosaic[seg_fid])
                    pygame.draw.rect(st, c, (p[0] + 1, 0, 12, 7))
                    pygame.draw.line(st, scale(c, 0.7), (p[0] + 1, 6), (p[0] + 12, 6))
                else:
                    st.blit(_atom(atoms, kind, look, pose, back), p)
            if zone == "L":
                st = pygame.transform.rotate(st, 90)
            elif zone == "R":
                st = pygame.transform.rotate(st, -90)
            st.set_colorkey(KEY, pygame.RLEACCEL)
            nbytes += st.get_width() * st.get_height() * 4
            imgs.append(st)
        if zone == "F":
            x, y, jump = x0, first[4], (0, -3)
            cx, cy = (x0 + x1) // 2, y + 9
        else:
            x, y = first[3], min(seats[k][4] for k in ks)
            jump = (-2, 0) if zone == "L" else (2, 0)
            cx, cy = x + 9, y + (len(ks) * SIDE_PITCH) // 2
        # posicao no perimetro (ola): esquerda de cima p/ baixo, frente esq->dir, direita de baixo p/ cima
        if zone == "L":
            wave = cy - PITCH.top
        elif zone == "F":
            wave = PITCH.h + cx
        else:
            wave = PITCH.h + W + (PITCH.bottom - cy)
        ph = (_seed(venue, gkey) % 180) / 1000.0
        segs.append(Seg(zone, _fidelity(zone, cx), x, y, tuple(imgs), jump, cx, cy, wave, ph, len(occ)))
    # ordem de desenho: laterais, depois frente de cima (longe da camera) para baixo
    segs.sort(key=lambda s: (s.zone == "F", s.y))
    return segs, nbytes


def _glow(radius, col):
    s = pygame.Surface((radius * 2, radius * 2))
    for r in range(radius, 0, -2):
        k = (1 - r / radius) ** 2
        pygame.draw.circle(s, scale(col, k), (radius, radius), r)
    return s


def _draw_static(v, venue, base, seats, chosen, home, away, rng):
    """Arena composta: base (pitch_surf) + estrutura da arquibancada + torcida distante."""
    st = STYLES[v["style"]]
    s = base.copy()
    step, edge, seat_c = st["step"], st["edge"], st["seat"]
    # fundo do lado da camera: muro/chao escuro
    pygame.draw.rect(s, scale(step, 0.45), (0, PITCH.bottom + 5, W, H - PITCH.bottom - 5))
    x0, x1 = v["span"]
    if v["front"]:
        for row in range(v["front"]):
            y = FRONT_ROW_Y[row] + 7
            col = scale(step, 1.0 - 0.12 * row)
            pygame.draw.rect(s, col, (x0, y, x1 - x0, 12 if row < v["front"] - 1 else H - y))
            pygame.draw.line(s, scale(edge, 0.55), (x0, y), (x1, y))
        # corrimao na frente da primeira fileira (perto do campo)
        pygame.draw.line(s, scale(edge, 0.85), (x0, FRONT_ROW_Y[0] + 3), (x1, FRONT_ROW_Y[0] + 3))
        if x0 > 0 or x1 < W:                              # arquibancada pequena: pes/estrutura nas pontas
            for xx in (x0, x1 - 3):
                pygame.draw.rect(s, scale(edge, 0.7), (xx, FRONT_ROW_Y[0] + 3, 3, H - FRONT_ROW_Y[0]))
        else:                                             # escadas a cada 3 faixas
            for k in range(1, 3):
                xx = k * W // 3
                pygame.draw.rect(s, scale(step, 0.7), (xx - 3, FRONT_ROW_Y[0] + 5, 6, H))
    for zone in v["sides"]:
        for col, lx in enumerate(SIDE_COL_X):
            bx = lx if zone == "L" else W - lx - AH
            spans = [(SIDE_Y0, SIDE_Y1)] if col == 2 else [(SIDE_Y0, POCKET[0]), (POCKET[1], SIDE_Y1)]
            for ya, yb in spans:
                pygame.draw.rect(s, scale(step, 1.0 - 0.12 * col), (bx, ya, AH, yb - ya))
                ex = bx + AH - 1 if zone == "L" else bx
                pygame.draw.line(s, scale(edge, 0.5), (ex, ya), (ex, yb))
        # corrimao junto ao campo
        rx = SIDE_COL_X[0] + AH + 1 if zone == "L" else W - SIDE_COL_X[0] - AH - 2
        pygame.draw.line(s, scale(edge, 0.8), (rx, SIDE_Y0), (rx, POCKET[0]))
        pygame.draw.line(s, scale(edge, 0.8), (rx, POCKET[1]), (rx, SIDE_Y1))
    # cadeiras (vazias: aparecem onde nao ha ninguem)
    for k, se in enumerate(seats):
        if se[0] == "F":
            pygame.draw.rect(s, seat_c, (se[3] + 2, se[4] + 12, 10, 5), border_radius=2)
        elif se[0] == "L":
            pygame.draw.rect(s, seat_c, (se[3] + 12, se[4] + 2, 5, 10), border_radius=2)
        else:
            pygame.draw.rect(s, seat_c, (se[3] + 1, se[4] + 2, 5, 10), border_radius=2)
    # torcida distante (estatica, sob o HUD)
    if v["far"]:
        far_n = int(round(v["far"] * LEVELS[v["_level"]]["density"]))
        spots = []
        for r, y in enumerate(FAR_ROWS):
            pygame.draw.rect(s, scale(step, 0.75 - 0.08 * r), (0, y + 5, W, 6))
            for i in range(0, W // 9):
                x = i * 9 + (4 if r % 2 else 0)
                w = 1.0 - abs(x - W / 2) / (W / 2) * 0.7 + rng.random() * 0.6 - r * 0.05
                spots.append((w, x, y))
        spots.sort(reverse=True)
        hs, aw = _shirt(home), _shirt(away)
        for w, x, y in sorted(spots[:far_n], key=lambda t: t[2]):
            shirt = hs if x < W * 0.45 else aw if x > W * 0.55 else rng.choice(NEUTRAL_SHIRTS)
            if rng.random() < 0.2:
                shirt = rng.choice(NEUTRAL_SHIRTS)
            _tiny(s, x, y, scale(rng.choice(SKINS), 0.6), rng.choice(HAIRS)[1], scale(shirt, 0.48))
    # placa de LED do topo (parte fixa: moldura e blocos apagados nas cores dos times)
    if st["board"]:
        pygame.draw.rect(s, (8, 10, 18), (PITCH.left, 79, PITCH.w, 8))
        for i in range(PITCH.left + 4, PITCH.right - 30, 60):
            c = home if i < CX else away
            pygame.draw.rect(s, scale(_shirt(c), 0.45), (i, 81, 40, 4))
        pygame.draw.line(s, scale(edge, 0.6), (PITCH.left, 87), (PITCH.right, 87))
    # refletores nos cantos (glow estatico)
    if st["lights"]:
        g = _glow(70, (70, 80, 70))
        for gx, gy in ((0, PITCH.bottom + 20), (W, PITCH.bottom + 20), (0, PITCH.top - 10), (W, PITCH.top - 10)):
            s.blit(g, (gx - 70, gy - 70), special_flags=pygame.BLEND_RGB_ADD)
        for gx, gy in ((10, H - 12), (W - 10, H - 12)):
            pygame.draw.circle(s, (240, 250, 255), (gx, gy), 3)
    return s


def _build_tarja():
    """Tarja translucida do rodape: so atras dos textos/botoes da UI; no meio a torcida aparece."""
    s = pygame.Surface((W, H - TARJA_Y), pygame.SRCALPHA)
    hh = H - TARJA_Y
    zones = ((8, 118), (598, 1098))          # "P: pausa" e "Velocidade (1-4):" + botoes
    for x in range(0, W, 2):
        d = min((0 if a <= x <= b else min(abs(x - a), abs(x - b))) for a, b in zones)
        k = 1.0 - min(1.0, d / 24.0)
        if k <= 0:
            continue
        for y in range(0, hh, 2):
            a = int(185 * k * (0.7 + 0.3 * y / hh))
            pygame.draw.rect(s, (2, 8, 20, a), (x, y, 2, 2))
    return s.convert_alpha()


# --- extras pre-renderizados (A4/A5/A6) -------------------------------------------------------
def _light(c):
    return (236, 236, 236) if _lum(c) < 170 else (24, 28, 40)


def _flag_imgs(stripes, seed):
    """Bandeira 22x22 (mastro + pano de listras) em 2 quadros de ondulacao (colorkey)."""
    cloth = pygame.Surface((18, 12)).convert()
    n = len(stripes)
    for i, c in enumerate(stripes):
        cloth.fill(c, (0, i * 12 // n, 18, 12 // n + 1))
    out = []
    for ph in (0.0, math.pi):
        s = pygame.Surface((22, 22)).convert()
        s.fill(KEY)
        for col in range(18):
            dy = int(round(math.sin(col * 0.45 + ph + seed) * 1.5))
            s.blit(cloth, (3 + col, 2 + dy), (col, 0, 1, 12))
            if math.cos(col * 0.45 + ph + seed) < -0.5:                 # dobra na sombra
                pygame.draw.line(s, scale(cloth.get_at((col, 1))[:3], 0.7), (3 + col, 2 + dy), (3 + col, 13 + dy))
        pygame.draw.line(s, (210, 214, 222), (2, 1), (2, 21), 2)
        s.set_colorkey(KEY, pygame.RLEACCEL)
        out.append(s)
    return tuple(out)


def _star():
    """Flash de camera 9x9 (aditivo, fundo preto)."""
    s = pygame.Surface((9, 9)).convert()
    s.fill((0, 0, 0))
    pygame.draw.circle(s, (70, 70, 80), (4, 4), 4)
    pygame.draw.line(s, (200, 200, 220), (0, 4), (8, 4))
    pygame.draw.line(s, (200, 200, 220), (4, 0), (4, 8))
    pygame.draw.circle(s, (255, 255, 255), (4, 4), 1)
    return s


def _puff(col, r, a):
    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for k in range(r, 0, -1):
        pygame.draw.circle(s, col + (int(a * (1 - (k / r) ** 2) + 4),), (r, r), k)
    return s.convert_alpha()


def _build_extras(b, v, ex, home, away, level):
    """Sprites e posicoes dos extras (sem texto): bandeiras, sinalizadores, fumaca, flash, confete,
    ancoras das onomatopeias e a moldura do telao."""
    hs, aws = _shirt(home), _shirt(away)
    b.colors = {"home": scale(hs, 1.18), "away": scale(aws, 1.18), "neutral": (255, 230, 120)}
    b.ono_cols = {"home": mix(b.colors["home"], (255, 255, 255), 0.35),
                  "away": mix(b.colors["away"], (255, 255, 255), 0.35), "neutral": (255, 230, 120)}
    # ancoras (onomatopeias, faixas, sinalizadores): centro das faixas frontais de cada torcida
    anchors = {}
    for fid in FIDS:
        xs = [s.cx for s in b.segs if s.zone == "F" and s.fid == fid]
        anchors[fid] = int(sum(xs) / len(xs)) if xs else {"home": 200, "away": W - 200, "neutral": CX}[fid]
    b.anchors = anchors
    # bandeiras: so nas laterais (a frente fica com faixas/UI); MEDIA = metade
    flags = []
    n = ex["flags"] if level == "ALTA" else ex["flags"] // 2
    ys = (112, 232, 492, 612, 172, 552)
    for zone in v["sides"]:
        per = (n + (1 if zone == "L" else 0)) // 2 if len(v["sides"]) == 2 else n
        fid = "home" if zone == "L" else "away"
        for k in range(per):
            if ex.get("nations") and k % 2:
                stripes = NATIONS[(k // 2 + (zone == "R") * 2) % len(NATIONS)]
            else:
                c = hs if fid == "home" else aws
                stripes = (c, _light(c), c)
            imgs = _flag_imgs(stripes, k * 1.3 + (zone == "R"))
            x = 20 if zone == "L" else W - 20 - 22
            flags.append((imgs, x, ys[k % len(ys)] - 11, fid, (k * 0.11) % 0.25))
    b.flags = flags
    # sinalizadores: 2 na frente + 2 na lateral por torcida
    flares = {"home": [], "away": []}
    if ex["flares"]:
        for fid, sx in (("home", 30), ("away", W - 30)):
            ax = anchors[fid]
            flares[fid] += [(ax - 80, 657), (ax + 80, 657)]
            if ("L" if fid == "home" else "R") in v["sides"]:
                flares[fid] += [(sx, 180), (sx, 560)]
    glow = {}
    for fid in ("home", "away"):
        c = mix(b.colors[fid], (255, 90, 40), 0.55)
        glow[fid] = (_glow(28, scale(c, 1.1)), _glow(24, scale(c, 1.35)))
    b.smoke = {fid: tuple(_puff(mix(b.colors[fid], (170, 170, 180), 0.35), r, a)
                          for r, a in ((10, 150), (14, 105), (18, 60))) for fid in ("home", "away")}
    b.flares = (flares, glow)
    b.star = _star()
    if ex.get("alert"):                                     # laboratorio/fabrica: luzes de alerta
        b.star = _glow(5, (255, 60, 40))
    if ex.get("conf") == "coliseu":
        b.conf_cols = {f: ((30, 30, 34), (232, 182, 52), (255, 232, 130)) for f in FIDS}
    else:
        b.conf_cols = {f: (b.colors[f], (240, 240, 240), GOLD) for f in FIDS}
    # telao: moldura (tela escura com linhas de varredura, borda metalica)
    t = pygame.Surface(TELAO.size).convert()
    t.fill((4, 8, 16))
    for y in range(2, TELAO.h - 2, 2):
        pygame.draw.line(t, (8, 14, 26), (2, y), (TELAO.w - 3, y))
    pygame.draw.rect(t, (70, 84, 104), t.get_rect(), 2, border_radius=4)
    pygame.draw.rect(t, (0, 150, 190), t.get_rect().inflate(-4, -4), 1, border_radius=3)
    b.telao = t


def _led_strip(txt, msgs, color, sep_col):
    """Tira de LED longa (conteudo + LED_W repetidos) para blit com area= (scroll sem Surface por quadro)."""
    parts = []
    for m in msgs:
        parts.append(txt(m, 14, color))
        parts.append(txt("   +   ", 14, sep_col))
    period = sum(p.get_width() for p in parts)
    reps = 1 + (LED_W + period - 1) // period
    s = pygame.Surface((period * reps + LED_W, LED_H)).convert()
    s.fill((10, 8, 6))
    x = 0
    while x < s.get_width():
        for p in parts:
            s.blit(p, (x, 0))
            x += p.get_width()
    for y in range(1, LED_H, 2):                             # linhas de varredura (pontos de LED)
        s.fill((150, 150, 150), (0, y, s.get_width(), 1), special_flags=pygame.BLEND_RGB_MULT)
    return s, period


def _banner(txt, text, cloth, seed):
    """Faixa de pano 11 px com ondulacao leve e cordinhas (colorkey)."""
    ink = _light(cloth)
    t = txt(text, 14, ink)
    w, h = t.get_width() + 14, 11
    s = pygame.Surface((w, h + 2)).convert()
    s.fill(KEY)
    s.fill(cloth, (0, 1, w, h))
    for col in range(w):                                    # dobras do pano (sombras suaves)
        k = math.sin(col * 0.11 + seed)
        if k < -0.6:
            pygame.draw.line(s, scale(cloth, 0.86), (col, 1), (col, h))
    pygame.draw.rect(s, scale(cloth, 0.68), (0, 1, w, h), 1)
    s.blit(t, (7, 3))
    for xx in (1, w - 2):                                   # cordinhas na grade
        pygame.draw.line(s, (210, 210, 210), (xx, 0), (xx, 1))
    s.set_colorkey(KEY, pygame.RLEACCEL)
    return s


def ensure_text_extras(b, txt):
    """Faixas de pano e tiras de LED (precisam de texto: Game.text_img). Uma vez por pacote."""
    owner = getattr(txt, "__self__", txt)
    if txt is None or b.txt_id == id(owner):
        return
    b.txt_id = id(owner)
    ex, v = b.ex, VENUES[b.venue]
    x0, x1 = v["span"]
    banners = []
    texts = ex["banners"]
    fids = ("home", "away", "neutral")
    for k, text in enumerate(texts):
        fid = fids[k % 3]
        cloth = _shirt(b.key[1]) if fid == "home" else _shirt(b.key[2]) if fid == "away" else (232, 228, 214)
        img = _banner(txt, text, cloth, k * 2.1)
        cx = b.anchors[fid]
        x = max(x0 + 2, min(x1 - img.get_width() - 2, cx - img.get_width() // 2))
        banners.append((img, (x, 652)))
    b.banners = banners
    b.led_ads = b.led_goal = None
    if STYLES[v["style"]]["board"]:
        head = LED_HEAD.get(b.venue)
        msgs = ((head,) if head else ()) + LED_ADS
        b.led_ads = _led_strip(txt, msgs, LED_AMBER, (120, 80, 30))
        b.led_goal = {fid: _led_strip(txt, ("GOOOOOL!", "GOOOOOL!", "QUE GOLACO!"), b.colors[fid], (255, 255, 255))
                      for fid in ("home", "away")}


def _build(venue, home, away, level, base):
    t0 = time.perf_counter()
    v = dict(VENUES[venue])
    v["_level"] = level
    ex = EXTRAS[venue]
    dens = LEVELS[level]["density"]
    rng = random.Random(_seed(venue, home, away, level))
    seats = _seats(v)
    n = min(len(seats), int(round((v["people"] - v["far"]) * dens)))
    chosen = _pick(v, seats, n, rng)
    looks = _looks(v, venue, seats, chosen, home, away, rng)
    atoms = {}
    mosaic = None
    if ex["mosaic"]:
        if ex.get("conf") == "coliseu":
            mosaic = {"home": ((24, 24, 28), (232, 182, 52)), "away": ((24, 24, 28), (232, 182, 52))}
        else:
            mosaic = {f: (c, _light(c)) for f, c in (("home", _shirt(home)), ("away", _shirt(away)))}
    segs, nbytes = _build_segments(v, venue, seats, looks, atoms, mosaic)
    if base is None:
        base = pygame.Surface((W, H)).convert()
        base.fill((8, 12, 26))
    b = _Bundle()
    b.key = (venue, home, away, level)
    b.venue, b.level = venue, level
    b.ex = ex
    b.static = _draw_static(v, venue, base, seats, chosen, home, away, rng)
    b.tarja = _build_tarja()
    b.segs = segs
    b.people = len(chosen) + int(round(v["far"] * dens))
    b.nbytes = nbytes
    _build_extras(b, v, ex, home, away, level)
    b.txt_id = None
    b.banners = []
    b.led_ads = b.led_goal = None
    b.build_ms = (time.perf_counter() - t0) * 1000
    STATS["builds"] += 1
    return b


def warm_crowd(venue=None, home=(50, 120, 255), away=(235, 65, 65), level="ALTA", base=None, txt=None):
    """Pacote pronto (atlas + arena composta + tarja + extras) do local/cores/nivel. LRU de 3 chaves.

    Chamar no inicio da partida (nunca no meio). `base` = pitch_surf do jogo; `txt` = Game.text_img
    (faixas de pano e placas de LED; sem ele o pacote fica sem textos)."""
    venue = resolve_venue(venue)
    level = resolve_level(level)
    key = (venue, tuple(int(c) for c in home[:3]), tuple(int(c) for c in away[:3]), level)
    b = _CACHE.get(key)
    if b is not None:
        _CACHE.move_to_end(key)
    else:
        b = _CACHE[key] = _build(venue, key[1], key[2], level, base)
        while len(_CACHE) > CACHE_MAX:
            _CACHE.popitem(last=False)
    ensure_text_extras(b, txt)
    return b


def stands_static(venue, home_color, away_color, level="ALTA", base=None):
    """Arena composta (1100x700) do local: pitch + arquibancadas + torcida distante."""
    return warm_crowd(venue, home_color, away_color, level, base).static


def clear_cache():
    _CACHE.clear()


# --- estado de reacao -------------------------------------------------------------------------
FIDS = ("home", "away", "neutral")
WAVE_S_PER_PX = 0.001           # defasagem da ola/onda: ~0,12 s por faixa de ~120 px
GOAL_S_PER_PX = 0.00045         # onda do gol: sai do gol e cruza a torcida em <= 0,5 s
OLA_EVERY, OLA_QUIET = 25.0, 10.0


class Crowd:
    """Torcida de uma partida: humores por fidelidade, ola, calmaria, extras; desenho so por blits.

    `clock` (injetavel) devolve segundos; padrao time.perf_counter. Usa so `self.rng` (reacoes) e
    `self.fxr` (extras): nunca o random global. `txt` = Game.text_img: as imagens de onomatopeias e
    legendas do telao sao buscadas UMA vez aqui (nada de texto novo por quadro)."""

    def __init__(self, bundle, clock=None, seed=20261, txt=None, telao=True):
        self.b = bundle
        self.segs = bundle.segs
        cfg = LEVELS[bundle.level]
        self.level = bundle.level
        self.every = cfg["every"]
        self.waves = cfg["waves"]
        self.ola_on = self.waves and VENUES[bundle.venue]["ola"]
        self.ex = bundle.ex
        self.clock = clock or time.perf_counter
        self.rng = random.Random(seed)
        self.fxr = random.Random(seed + 1)
        now = self.clock()
        self.react = {}             # fid -> (tipo, inicio, duracao, prioridade, origem_x)
        self.ola = None             # (inicio, fids ou None)
        self.idle = None            # (indice da faixa, pose, fim)
        self.next_idle = now + 1.5
        self.last_react = now
        self.last_ola = now
        self.frame = 0
        self.next_upd = 0
        self.n_events = 0
        self.n_kick = 0
        self.poses = [SIT] * len(self.segs)
        self.offs = [(0, 0)] * len(self.segs)
        self.blits = []
        self.fid_segs = {f: [s for s in self.segs if s.fid == f] for f in FIDS}
        self.has_mosaic = any(len(s.imgs) > MOSAIC for s in self.segs)
        # extras
        self.last_t = now
        self.dt = 0.0
        self.confetti = []          # [x, y, vx, vy, vida, fase, cor_a, cor_b]
        self.conf_until = {}        # fid -> fim da chuva de confete
        self.flashes = []           # [x, y, fim]
        self.flash_until = 0.0
        self.smoke = []             # [x, y, vx, vy, idade, fid]
        self.flare_until = {"home": 0.0, "away": 0.0}
        self.led_goal = None        # (fid, fim)
        self.onos = []              # [chave_imgs, x, y0, inicio]
        self.cap = None             # (tipo, variante, inicio, prioridade)
        self.cap_n = {}
        self.cap_last = now
        self.idle_n = 0
        # LOD
        self.lod = 2
        self._lod_acc = 0.0
        self._lod_n = 0
        self._lod_good = 0
        # textos (pre-buscados)
        self.ono_imgs = {}
        self.cap_imgs = {}
        self.spk_imgs = ()
        self.telao_on = False
        if txt is not None:
            self.prepare_text(txt, telao)
        self.update(now)

    @property
    def static(self):
        return self.b.static

    def prepare_text(self, txt, telao=True):
        """Busca (Game.text_img, com cache) todas as imagens de texto que a partida pode usar."""
        ensure_text_extras(self.b, txt)
        words = ROBOT_WORDS if VENUES[self.b.venue]["robots"] else WORDS
        for key, word in words.items():
            size = WORD_SIZE.get(key, 36)
            shadow = txt(word, size, (0, 0, 0))
            for fid in FIDS:
                col = self.b.ono_cols[fid]
                self.ono_imgs[(key, fid)] = tuple((txt(word, size, scale(col, f)), shadow if k < 2 else None)
                                                  for k, f in enumerate(ONO_FADE))
        self.telao_on = bool(telao)
        if self.telao_on:
            self.spk_imgs = tuple(txt(name, TELAO_SIZE, col) for name, col in SPEAKERS)
            for kind, variants in CAPTIONS.items():
                for i, pair in enumerate(variants):
                    self.cap_imgs[(kind, i)] = tuple(txt(line, TELAO_SIZE, (236, 242, 248)) for line in pair)

    # eventos ----------------------------------------------------------------------------------
    def _set(self, fid, kind, dur, prio, now, origin=None):
        cur = self.react.get(fid)
        if cur is not None and now < cur[1] + cur[2] and cur[3] > prio:
            return
        self.react[fid] = (kind, now, dur, prio, origin)

    def event(self, kind, team=None, x=None):
        """Reacao a um lance. kind: goal, chance, save, post, kickoff, end.

        team: goal/chance = time que ataca/marcou; save = time que defendeu; end = vencedor
        (None = empate). So escreve no estado da torcida."""
        now = self.clock()
        self.n_events += 1
        mine = FIDS[team] if team in (0, 1) else None
        other = FIDS[1 - team] if team in (0, 1) else None
        ex = self.ex
        if kind == "goal" and mine:
            origin = PITCH.right if team == 0 else PITCH.left
            self._set(mine, "jump", 3.0, 3, now, origin)
            self._set(other, "sad", 2.5, 3, now)
            self._set("neutral", "up", 1.5, 3, now, origin)
            self._ono("goal", mine, now)
            self._ono("no", other, now)
            if ex["confetti"] and self.lod >= 2:
                self._confetti(mine, 45)
                self.conf_until[mine] = now + 2.0
            self.flash_until = now + 2.0
            if ex["flares"] and self.lod >= 1:
                self.flare_until[mine] = now + 3.5
            self.led_goal = (mine, now + LED_GOAL_S)
            self._caption("goal", now)
        elif kind == "chance" and mine:
            self._set(mine, "up", 0.6, 1, now)
            self._set("neutral", "up", 0.4, 1, now)
            self._ono("go", mine, now)
            self._caption("chance", now)
        elif kind == "save" and mine:
            self._set(mine, "up", 0.8, 2, now)
            self._set(other, "sad", 0.8, 2, now)
            self._ono("ole", mine, now)
            self._ono("uh", other, now)
            self._caption("save", now)
        elif kind == "post":
            for f in FIDS:
                self._set(f, "up", 0.4, 1, now)
            self._ono("clang", "neutral", now)
            self._ono("oh", "neutral", now, dx=150)
            self._caption("post", now)
        elif kind == "kickoff":
            self.n_kick += 1
            first = self.n_kick == 1
            for f in FIDS:
                if first and f != "neutral" and self.has_mosaic and self.lod >= 1:
                    self._set(f, "mosaic", 3.2, 1, now)
                else:
                    self._set(f, "flags", 1.6, 1, now)
            if first:
                self._ono("go", "neutral", now)
                self._caption("kickoff", now)
        elif kind == "end":
            if mine:
                self._set(mine, "win" if self.has_mosaic else "jump", 9.0 if self.has_mosaic else 4.0, 4, now, CX)
                self._set(other, "sad", 9.0, 4, now)
                self._set("neutral", "up", 2.0, 4, now)
                fids = (mine, "neutral")
                self._ono("win", mine, now)
                if ex["confetti"] and self.lod >= 2:
                    self._confetti(mine, 30)
                    self.conf_until[mine] = now + 3.0
                if ex["flares"] and self.lod >= 1:
                    self.flare_until[mine] = now + 5.0
                self.flash_until = now + 2.5
                self._caption("win", now)
            else:
                for f in FIDS:
                    self._set(f, "up", 2.0, 4, now)
                fids = None
                self._ono("clap", "neutral", now)
                self._caption("draw", now)
            if self.waves:
                self.ola = (now + 4.0 if mine else now + 2.0, fids)
                self.last_ola = now
        else:
            return
        self.last_react = now

    def _ono(self, key, fid, now, dx=0):
        imgs = self.ono_imgs.get((key, fid))
        if imgs is None:
            return
        onos = self.onos
        limit = ONO_MAX if self.lod >= 1 else 1
        while len(onos) >= limit:
            onos.pop(0)
        x = self.b.anchors[fid] + dx
        y = ONO_Y
        for o in onos:                              # nao empilha no mesmo lugar
            if abs(o[1] - x) < 120:
                y = o[2] - 40
        onos.append([imgs, x, y, now])

    def _caption(self, kind, now):
        if not self.telao_on:
            return
        cur = self.cap
        if cur is not None and now < cur[2] + sum(CAP_LINE_S) and cur[3] > CAP_PRIO[kind]:
            return
        n = self.cap_n.get(kind, 0)
        self.cap_n[kind] = n + 1
        self.cap = (kind, n % len(CAPTIONS[kind]), now, CAP_PRIO[kind])
        self.cap_last = now

    # extras ------------------------------------------------------------------------------------
    def _seg_point(self, s):
        w, h = s.imgs[0].get_size()
        r = self.fxr
        return s.x + r.uniform(1, w - 1), s.y + r.uniform(2, h - 2)

    def _confetti(self, fid, n):
        segs = self.fid_segs.get(fid) or self.segs
        if not segs:
            return
        cap = CONFETTI_MAX[self.level] if self.lod >= 2 else 0
        room = cap - len(self.confetti)
        r = self.fxr
        cols = self.b.conf_cols[fid]
        for _ in range(max(0, min(n, room))):
            s = r.choice(segs)
            x, y = self._seg_point(s)
            if s.zone == "F":
                vx, vy = r.uniform(-45, 45), r.uniform(-150, -70)
            else:
                vx, vy = (1 if s.zone == "L" else -1) * r.uniform(60, 150), r.uniform(-90, 10)
            c = r.choice(cols)
            self.confetti.append([x, y, vx, vy, r.uniform(1.8, 3.2), r.uniform(0, 6.28), c, scale(c, 0.6)])

    def _tick_extras(self, now, dt):
        """Fisica dos extras por tempo real (dt = 0 pausado). Tetos fixos por nivel/LOD."""
        if dt <= 0:
            return
        r = self.fxr
        lod = self.lod
        # chuva de confete continua por alguns segundos depois do gol
        if self.conf_until and lod >= 2:
            for fid, until in self.conf_until.items():
                if now < until and r.random() < dt * 22:
                    self._confetti(fid, 1)
        if self.confetti:
            keep = []
            drag = max(0.0, 1.0 - 1.8 * dt)
            for p in self.confetti:
                p[4] -= dt
                if p[4] <= 0 or p[1] > H + 4:
                    continue
                p[3] = min(p[3] + 120 * dt, 46)
                p[2] *= drag
                p[0] += p[2] * dt + math.sin(p[5] + now * 9) * 16 * dt
                p[1] += p[3] * dt
                keep.append(p)
            self.confetti = keep
        # flashes de camera (rajada depois do gol/fim; raros no resto do jogo)
        if self.ex["flashes"] and lod >= 1:
            cap = FLASH_MAX[self.level] // (1 if lod >= 2 else 2)
            rate = 14 if now < self.flash_until else (0.6 if lod >= 2 else 0.0)
            if len(self.flashes) < cap and r.random() < dt * rate and self.segs:
                x, y = self._seg_point(r.choice(self.segs))
                self.flashes.append([x, y, now + r.uniform(0.07, 0.14)])
        if self.flashes:
            self.flashes = [f for f in self.flashes if f[2] > now]
        # fumaca dos sinalizadores
        smax = SMOKE_MAX[self.level] if lod >= 2 else 0
        if smax:
            flares = self.b.flares[0]
            for fid, until in self.flare_until.items():
                if now < until and len(self.smoke) < smax and r.random() < dt * 9 and flares[fid]:
                    fx, fy = r.choice(flares[fid])
                    self.smoke.append([fx + r.uniform(-3, 3), fy - 4, r.uniform(-10, 10), r.uniform(-30, -14), 0.0, fid])
        if self.smoke:
            keep = []
            for p in self.smoke:
                p[4] += dt
                if p[4] >= 2.2:
                    continue
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                keep.append(p)
            self.smoke = keep

    # LOD --------------------------------------------------------------------------------------
    def lod_feed(self, ms):
        """Amostra do tempo de desenho (ms) de um quadro de partida. Ver LOD_* no topo."""
        self._lod_acc += ms
        self._lod_n += 1
        if self._lod_n < LOD_WINDOW:
            return
        avg = self._lod_acc / self._lod_n
        self._lod_acc, self._lod_n = 0.0, 0
        if avg > LOD_DOWN_MS and self.lod > 0:
            self.set_lod(self.lod - 1)
            self._lod_good = 0
        elif avg < LOD_UP_MS and self.lod < 2:
            self._lod_good += 1
            if self._lod_good >= LOD_UP_WINDOWS:
                self.set_lod(self.lod + 1)
                self._lod_good = 0
        else:
            self._lod_good = 0

    def set_lod(self, lod):
        self.lod = max(0, min(2, lod))
        if self.lod < 2:
            self.confetti.clear()
            self.smoke.clear()
            self.conf_until.clear()
        if self.lod == 0:                          # congelada: todos sentados, uma lista de blits fixa
            self.flashes.clear()
            self.react.clear()
            self.ola = self.idle = None
            bl = self.blits
            bl.clear()
            for i, s in enumerate(self.segs):
                self.poses[i] = SIT
                self.offs[i] = (0, 0)
                bl.append((s.imgs[SIT], (s.x, s.y)))
        self.next_upd = 0

    # estado -----------------------------------------------------------------------------------
    def pose_of(self, i, now):
        """(pose, dx, dy) da faixa i no instante now."""
        s = self.segs[i]
        r = self.react.get(s.fid)
        if r is not None and now < r[1] + r[2]:
            kind, t0, _, _, origin = r
            delay = 0.0 if origin is None else abs(s.cx - origin) * GOAL_S_PER_PX
            el = now - t0 - delay
            if el >= 0:
                if kind == "win":
                    kind = "jump" if el < 3.0 else "mosaic"
                if kind == "jump":
                    if int((el + s.ph) / 0.18) % 2 == 0:
                        return UP, s.jump[0], s.jump[1]
                    return UP, 0, 0
                if kind == "up":
                    return UP, 0, 0
                if kind == "sad":
                    return SAD, 0, 0
                if kind == "flags":
                    return (FLAG_A if int((el + s.ph) / 0.25) % 2 == 0 else FLAG_B), 0, 0
                if kind == "mosaic":
                    return (MOSAIC if len(s.imgs) > MOSAIC else UP), 0, 0
            elif kind == "sad":
                return SAD, 0, 0
        ola = self.ola
        if ola is not None:
            el = now - ola[0] - s.wave * WAVE_S_PER_PX
            if 0 <= el < 0.5 and (ola[1] is None or s.fid in ola[1]):
                if el < 0.25:
                    return UP, s.jump[0], s.jump[1]
                return UP, 0, 0
        idle = self.idle
        if idle is not None and idle[0] == i and now < idle[2]:
            pose = idle[1]
            if pose == FLAG_A and int(now / 0.25) % 2:
                pose = FLAG_B
            return pose, 0, 0
        return SIT, 0, 0

    def update(self, now=None):
        """Recalcula as poses e a lista de blits (chamado a cada `every` quadros)."""
        if now is None:
            now = self.clock()
        n = len(self.segs)
        if self.waves and self.lod >= 2 and n:
            if self.ola is not None and now > self.ola[0] + (PITCH.h * 2 + W) * WAVE_S_PER_PX + 0.6:
                self.ola = None
            if (self.ola_on and self.ola is None and now - self.last_react >= OLA_QUIET
                    and now - self.last_ola >= OLA_EVERY):
                self.ola = (now, None)
                self.last_ola = now
            if now >= self.next_idle:                      # calmaria: uma faixa acena/levanta
                rng = self.rng
                self.idle = (rng.randrange(n), FLAG_A if rng.random() < 0.6 else UP, now + rng.uniform(0.5, 0.9))
                self.next_idle = now + rng.uniform(0.6, 1.8)
        bl = self.blits
        bl.clear()
        poses, offs, segs = self.poses, self.offs, self.segs
        for i in range(n):
            p, dx, dy = self.pose_of(i, now)
            poses[i] = p
            offs[i] = (dx, dy)
            s = segs[i]
            bl.append((s.imgs[p], (s.x + dx, s.y + dy)))

    # desenho ----------------------------------------------------------------------------------
    def draw(self, scr, paused=False):
        """Camada sob os robos: faixas, faixas de pano, bandeiras, sinalizadores, fumaca, flashes,
        tarja do rodape, placa de LED e telao. So blits e pygame.draw: nenhuma Surface nova."""
        self.frame += 1
        now = self.clock()
        self.dt = 0.0 if paused else min(max(now - self.last_t, 0.0), 0.05)
        self.last_t = now
        lod = self.lod
        if not paused and lod >= 1 and self.frame >= self.next_upd:
            self.update(now)
            self.next_upd = self.frame + self.every * (1 if lod >= 2 else 2)
        if self.blits:
            scr.blits(self.blits, False)
        self._tick_extras(now, self.dt)
        b = self.b
        for img, pos in b.banners:
            scr.blit(img, pos)
        if b.flags:
            react = self.react
            for imgs, x, y, fid, ph in b.flags:
                if lod == 0:
                    k = 0
                else:
                    r = react.get(fid)
                    fast = r is not None and now < r[1] + r[2]
                    k = int((now + ph) / (0.12 if fast else 0.25)) % 2
                scr.blit(imgs[k], (x, y))
        if lod >= 1:
            flares, glow = b.flares
            for fid, until in self.flare_until.items():
                if now < until:
                    imgs = glow[fid]
                    for fx, fy in flares[fid]:
                        g = imgs[int(now * 15 + fx) % 2]
                        gw = g.get_width() // 2
                        scr.blit(g, (fx - gw, fy - gw), special_flags=pygame.BLEND_RGB_ADD)
                        pygame.draw.circle(scr, (255, 240, 220), (fx, fy), 2)
        if self.smoke:
            sm = b.smoke
            for p in self.smoke:
                k = 0 if p[4] < 0.6 else 1 if p[4] < 1.4 else 2
                img = sm[p[5]][k]
                hw = img.get_width() // 2
                scr.blit(img, (int(p[0]) - hw, int(p[1]) - hw))
        if self.flashes:
            st = b.star
            hw = st.get_width() // 2
            for x, y, _ in self.flashes:
                scr.blit(st, (int(x) - hw, int(y) - hw), special_flags=pygame.BLEND_RGB_ADD)
        scr.blit(b.tarja, (0, TARJA_Y))
        if b.led_ads is not None:
            g = self.led_goal
            if g is not None and now < g[1]:
                strip, period = b.led_goal[g[0]]
                off = int(now * LED_GOAL_SPEED) % period
            else:
                strip, period = b.led_ads
                off = int(now * LED_SPEED) % period
            scr.blit(strip, (LED_X, LED_Y), (off, 0, LED_W, LED_H))
        if self.telao_on:
            self._draw_telao(scr, now)

    def _draw_telao(self, scr, now):
        scr.blit(self.b.telao, TELAO.topleft)
        on = int(now * 1.5) % 2 == 0
        pygame.draw.circle(scr, (235, 50, 50) if on else (90, 20, 20), (TELAO.left + 11, TELAO.centery), 4)
        cap = self.cap
        if cap is None or now >= cap[2] + sum(CAP_LINE_S):
            if now - self.cap_last < CAP_IDLE_GAP:
                return
            self.cap = cap = ("idle", self.idle_n % len(CAPTIONS["idle"]), now, 0)
            self.idle_n += 1
            self.cap_last = now
        el = now - cap[2]
        k = 0 if el < CAP_LINE_S[0] else 1
        line = self.cap_imgs[(cap[0], cap[1])][k]
        name = self.spk_imgs[k]
        x = TELAO.left + 22
        cy = TELAO.centery + 1
        scr.blit(name, (x, cy - name.get_height() // 2))
        scr.blit(line, (x + name.get_width() + 6, cy - line.get_height() // 2))
        if now >= cap[2] + sum(CAP_LINE_S):
            self.cap_last = now

    def draw_over(self, scr, paused=False):
        """Camada sobre os robos: confete e onomatopeias (so blits/pygame.draw)."""
        now = self.clock()
        if self.confetti:
            dr = pygame.draw.rect
            tl, tr, tt = TELAO.left - 3, TELAO.right, TELAO.top - 2
            for p in self.confetti:
                x, y = int(p[0]), int(p[1])
                if y > tt and tl < x < tr:              # o telao fica legivel
                    continue
                if math.sin(p[5] * 3 + now * 11) > 0:
                    dr(scr, p[6], (x, y, 3, 2))
                else:
                    dr(scr, p[7], (x, y, 2, 3))
        if self.onos:
            keep = []
            for o in self.onos:
                u = (now - o[3]) / ONO_S
                if u >= 1.0 and not paused:
                    continue
                keep.append(o)
                u = min(max(u, 0.0), 0.999)
                k = 0 if u < 0.5 else 1 if u < 0.7 else 2 if u < 0.85 else 3
                img, shadow = o[0][k]
                y = o[2] - ONO_RISE * (1 - (1 - u) ** 2)
                w, h = img.get_size()
                x0, y0 = int(o[1] - w / 2), int(y - h / 2)
                if shadow is not None:
                    scr.blit(shadow, (x0 + 2, y0 + 2))
                scr.blit(img, (x0, y0))
            self.onos = keep

    def fid_pose(self, fid):
        """Pose mais comum entre as faixas de uma fidelidade (testes)."""
        cnt = {}
        for s, p in zip(self.segs, self.poses):
            if s.fid == fid:
                cnt[p] = cnt.get(p, 0) + 1
        return max(cnt, key=cnt.get) if cnt else None


def all_strings():
    """Todas as strings que a torcida pode mostrar (Latin-1, testes)."""
    out = set(WORDS.values()) | set(ROBOT_WORDS.values()) | set(LED_ADS) | set(LED_HEAD.values())
    out |= {n for n, _ in SPEAKERS}
    for ex in EXTRAS.values():
        out |= set(ex["banners"])
    for variants in CAPTIONS.values():
        for pair in variants:
            out |= set(pair)
    return out
