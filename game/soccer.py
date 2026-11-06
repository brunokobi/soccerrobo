"""SoccerPy - futebol arcade 100% Python (pygame).

Roda no desktop (`python main.py`) e no navegador via pygbag (WebAssembly).
"""
import asyncio
import math
import random
import time
from collections import OrderedDict, deque

import pygame
from pygame import Vector2 as V

import crowd
import prefs
import robot_art
import robots
import sfx
import skills
from campaign import Campaign
from campaign_ui import CampaignUI
from career import Career
from career_ui import CareerUI
from garage import Garage
from robot_art import led_color, scale_color  # noqa: F401  (reexportados: soccer.led_color)
from robots_ui import RobotsUI

W, H = 1100, 700
PITCH = pygame.Rect(60, 90, 980, 560)
CX, CY = PITCH.center
GOAL_HALF = 80          # metade da largura do gol
GOAL_DEPTH = 36
PR = 14                 # raio do jogador
BR = 8                  # raio da bola
MATCH_TIME = 120.0
PLAYER_SPEED = 205.0
AI_SPEED = 0.93
CATCH_SPEED = 520.0     # acima disso a bola nao e dominada, so rebatida
CAREER_TIME = 90.0      # segundos reais (1x) = 90 minutos de jogo
SPEEDS = [1, 2, 4, "max"]
GK_COLORS = [(250, 200, 40), (70, 205, 130)]
ACTIVE_TUNING = robots.TUNING          # padrao do jogo; o modo legado (robots.LEGACY_TUNING + BATTERY_ON=False) so vale p/ o golden
BATTERY_ON = True                      # bateria ligada (False so no modo legado)
FX_MAX = 120                           # teto de particulas
TEXT_CACHE_MAX = 600
CROWD_CYCLE = ("ALTA", "MEDIA", "OFF")    # opcao TORCIDA (prefs "crowd"), tecla T no menu e na pausa
EVENT_SFX = {"kickoff": "whistle", "chance": "ooh", "save": "save", "goal": "goal", "post": "post",
             "end": "whistle_end"}
CROWD_LABELS = {"ALTA": "ALTA", "MEDIA": "MÉDIA", "OFF": "DESLIGADA"}
# Camera (prefs "camera", tecla C no menu e na pausa). Regra: sem escolha do jogador (AUTO) as partidas
# ASSISTIDAS (campanha, Modo Robos, carreira) usam ESTADIO e o Amistoso com humano (modos 1/2) usa PERTO;
# escolhida, vale para todas. No menu C gira AUTO -> ESTADIO -> PERTO -> AUTO; na pausa alterna a camera
# da partida (grava a escolha). ESTADIO so existe com torcida (OFF = campo cheio) e fora do MAX.
CAMERA_MODES = ("ESTADIO", "PERTO")
CAMERA_MENU_CYCLE = (None, "ESTADIO", "PERTO")
CAMERA_LABELS = {None: "AUTO", "ESTADIO": "ESTÁDIO", "PERTO": "PERTO"}
# LOD da camera: media do tempo de desenho (ms) em janelas de CAM_LOD_WINDOW quadros em ESTADIO; acima de
# CAM_LOD_MS a partida cai para PERTO ate o fim (re-warm unico da torcida; a pausa/C pode voltar).
CAM_LOD_WINDOW, CAM_LOD_MS = 60, 8.0
# Escala do mundo por quadro, sempre com destino pre-alocado: f(src, size, dest) existe com essa assinatura
# no pygame 2.6.1 (desktop) e no pygame-ce 2.5.7 (navegador). Medido (desktop, 1068x596 -> 854x477):
# smoothscale 1,1-1,7 ms (pygame) / 0,8-0,9 ms (ce, SSE2) contra scale 0,25-0,3 / 0,12-0,2 ms. O WASM nao
# tem o caminho SIMD: "scale" (vizinho mais proximo; casa com o visual pixelado) e o padrao.
CAM_SCALERS = {"scale": pygame.transform.scale, "smooth": pygame.transform.smoothscale}
CAM_SCALER = "scale"
# Onda D (Torre do Po): modificadores de arena OPT-IN por partida (start_robot_match(arena=...)). None (o
# padrao de TODOS os modos: amistoso, carreira, Modo Robos, campanha) = caminho legado intocado (goldens).
# bola_pesada: a bola freia mais (ARENA_BALL_DRAG ** dt em vez de 0.35 ** dt; os dois times. Medido: chute
# mais fraco junto quebrava o motor - o time forte fazia 5-6 gols); bateria_curta: o dreno ao correr x ARENA_BAT_DRAIN (os dois
# times); goleiro_gigante: o goleiro do RIVAL (lado 1) alcanca a bola ARENA_GK_REACH px mais longe.
ARENA_MODS = ("bola_pesada", "bateria_curta", "goleiro_gigante")
ARENA_LABELS = {"bola_pesada": "BOLA PESADA", "bateria_curta": "BATERIA CURTA",
                "goleiro_gigante": "GOLEIRO GIGANTE"}
ARENA_BALL_DRAG = 0.25
ARENA_BAT_DRAIN = 1.8
ARENA_GK_REACH = 10
HUMAN_AIM_ERR = 30                     # graus de erro de mira humano por 1.0 de (0.65 - chu/100); so chu < 65

# (papel, fracao x a partir do proprio gol, fracao y)
FORMATION = [
    ("GK", 0.05, 0.50),
    ("DEF", 0.25, 0.50),
    ("MID", 0.45, 0.22),
    ("MID", 0.45, 0.78),
    ("ATT", 0.66, 0.50),
]

K = pygame
P1_KEYS = dict(up=[K.K_w], down=[K.K_s], left=[K.K_a], right=[K.K_d],
               shoot=[K.K_SPACE], pas=[K.K_LSHIFT])
P2_KEYS = dict(up=[K.K_UP], down=[K.K_DOWN], left=[K.K_LEFT], right=[K.K_RIGHT],
               shoot=[K.K_RETURN, K.K_KP_ENTER], pas=[K.K_RSHIFT])
SOLO_KEYS = dict(up=[K.K_w, K.K_UP], down=[K.K_s, K.K_DOWN],
                 left=[K.K_a, K.K_LEFT], right=[K.K_d, K.K_RIGHT],
                 shoot=[K.K_SPACE, K.K_RETURN],
                 pas=[K.K_LSHIFT, K.K_RSHIFT, K.K_x, K.K_z])


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def angle_between(a, b):
    return abs((a.angle_to(b) + 180) % 360 - 180)


def seg_dist(pt, a, b):
    ab = b - a
    l2 = ab.length_squared()
    if l2 == 0:
        return pt.distance_to(a)
    t = clamp((pt - a).dot(ab) / l2, 0, 1)
    return pt.distance_to(a + ab * t)


# (quantidade, velocidade min/max, vida min/max, cor, tamanho)
FX_KINDS = {
    "tackle": (6, 90, 230, 0.25, 0.5, (255, 235, 150), 3),
    "kick":   (8, 120, 320, 0.2, 0.45, (170, 245, 255), 3),
    "bump":   (4, 60, 160, 0.2, 0.4, (255, 170, 80), 2),
    "goal":   (40, 100, 420, 0.6, 1.2, None, 4),
    "wall":   (4, 50, 150, 0.2, 0.35, (150, 200, 255), 2),
    # A11 (robos): so pelo desenho (Game.robot_fx), no RNG proprio e com teto ROBOT_FX_MAX
    "dust":   (2, 20, 60, 0.35, 0.6, (150, 128, 96), 2),       # poeira ao correr/arrancar
    "smoke":  (1, 10, 30, 0.6, 1.0, (176, 178, 188), 4),       # superaquecendo (pecas de calor)
    "smoke_dark": (2, 10, 26, 0.7, 1.2, (58, 58, 64), 4),      # bateria critica (< 0,10)
    "spark":  (3, 70, 170, 0.12, 0.25, (255, 236, 110), 1),    # curto-circuito (bateria baixa)
    # B7 (skills): so pelo desenho (Game.draw_skill_fx), no fx_rng
    "sk_spark": (3, 80, 190, 0.15, 0.3, (255, 150, 40), 2),     # Pressao Alta / Arrancada
    "sk_zap": (5, 120, 260, 0.1, 0.22, (255, 250, 140), 1),     # Choque Eletrico
    # B13 (comemoracao cosmetica do autor do gol): fx_rng, cor por chamada (robot_art.CELEBRATION_COLORS)
    "cel_confete": (9, 90, 320, 0.9, 1.6, None, 2),
    "cel_bolo": (8, 60, 220, 0.8, 1.4, None, 3),
    "cel_chinelo_voando": (5, 160, 360, 0.7, 1.2, None, 4),
    "cel_fogos": (10, 160, 380, 0.5, 1.0, None, 2),
    "cel_trofeu": (8, 80, 260, 0.8, 1.4, None, 3),         # Onda D (cosmeticos de recompensa)
    "cel_relampagos": (8, 200, 420, 0.4, 0.8, None, 2),
}
# estilo da particula: indice em robot_art.PUFF_COLORS (fumaca/poeira desenhadas com sprites prontos);
# ausente = faisca (linha + circulo). FX_RISE: deriva para cima (fumaca).
FX_STYLE = {"dust": 0, "smoke": 1, "smoke_dark": 2}
FX_RISE = {"smoke": 26.0, "smoke_dark": 34.0}
ROBOT_FX = ("dust", "smoke", "smoke_dark", "spark")
ROBOT_FX_MAX = 36                      # particulas de robo ao mesmo tempo (dentro do FX_MAX)
# --- skills (B6/B7) ---
SK_EVAL_EVERY = 6                      # gatilhos periodicos: cada robo e avaliado a cada 6 passos (~10 Hz)
SK_RNG_SEED = 20261                    # RNG proprio das skills (direcao da curva); nunca o random global
SK_ZONE = 160.0                        # px: "adversario com a bola na zona do robo" (Muralha)
SK_AHEAD_COS = 0.5                     # cone de 60 graus a frente (Arrancada: campo livre)
SK_GK_OFF = (40.0, 20.0)               # goleiro "fora da linha": > 40 px da linha do gol ou > 20 px do centro
SK_ZAP_T = 0.35                        # s de jogo: raio do Choque visivel
SK_PULL_MIN = 0.4                      # Succao: velocidade minima do ima (x pull) numa bola lenta
SK_DRAG_K = 1.0498                     # -ln(0.35): arrasto da bola (v perde K px/s por px andado)
SK_LAUNCH_AIR = 0.5                    # s maximos de bola no ar no lancamento
SK_LAUNCH_VMAX = 900.0                 # px/s: teto da velocidade do lancamento do goleiro
SK_FX_COLORS = {"dash": (120, 230, 255), "magnet": (90, 160, 255), "curve": (255, 70, 220),
                "shield": (110, 220, 255), "overclock": (255, 70, 50), "heal": (80, 240, 120),
                "zap": (255, 250, 140), "gold_ring": (255, 205, 60), "spin": (200, 255, 255),
                "gloves": (255, 235, 90), "sparks": (255, 150, 40), "glow": (255, 255, 200),
                "wheel": (255, 200, 120), "tape": (230, 210, 150), "slipper": (255, 120, 120),
                "captain": (255, 215, 60), "icon": (170, 230, 255)}
DUST_SPEED = 165.0                     # px/s: acima disso o robo levanta poeira
LOW_BAT, CRIT_BAT = 0.25, 0.10


class Human:
    """Estado de entrada de um jogador humano."""

    def __init__(self, keys):
        self.keys = keys
        self.charge = 0.0
        self.shoot_prev = False
        self.pass_prev = False

    def down(self, pressed, action):
        return any(pressed[k] for k in self.keys[action])


class Ball:
    def __init__(self):
        self.pos = V(CX, CY)
        self.vel = V()
        self.owner = None
        self.roll = 0.0
        self.curve = 0.0                         # graus/s (skill Chute em Curva); 0.0 = bola reta (legado)
        self.curve_t = 0.0
        self.air = 0.0                           # s de bola "por cima" (Lancador); 0.0 = rasteira (legado)
        self.air_to = None                       # quem pode dominar a bola no ar (o alvo do lancamento)


class Player:
    def __init__(self, team, idx, role, fx, fy, name="", ovr=65.0, chassis=None, seed=None,
                 attrs=None, tuning=None, pid=None, paint=None, vis=None, skills=None):
        self.team = team
        self.idx = idx
        self.role = role
        self.name = name
        self.chassis = chassis or robots.ROLE_CHASSIS[role]
        self.pid = pid                           # id do robo no modo robos (vai no evento de gol)
        self.paint = tuple(paint[:3]) if paint else None   # pintura = cor do LED
        self.vis = vis if isinstance(vis, dict) else None    # so desenho (pecas visiveis); nao entra na simulacao
        self.art = None                          # robot_art.Art (warm_sprites); referencias prontas do desenho
        self.vdir = None                         # direcao visual 0..7 (histerese no desenho)
        self.fx_next = 0.0                       # proxima particula de robo (relogio real do desenho)
        if attrs is not None:                    # modo robos: atributos diretos, tuning do proprio robo
            self.tuning = tuning or ACTIVE_TUNING
            self.robot = dict(attrs)
        else:
            self.tuning = tuning or ACTIVE_TUNING
            self.robot = robots.from_overall(ovr, role, self.chassis, seed,
                                             flat=self.tuning["flat"])
        self.f = robots.factors(self.robot, self.tuning)
        self.s = robots.mean_attr(self.robot)   # alias legado: media dos atributos / 100
        self.spd = self.f.speed                  # fator de velocidade
        self.bat = 1.0                           # bateria 0..1 (usada a partir do passo 4)
        self.fx, self.fy = fx, fy
        self.pos = V()
        self.vel = V()
        self.face = V(team.dir, 0)
        self.cd = 0.0          # tempo sem poder dominar a bola
        self.tackle_cd = 0.0
        self.think = random.random() * 0.3
        self.hold = 0.0        # goleiro segurando a bola
        # skills (B6): [(id, rank, up)] vindos da entrada de elenco; o estado so e montado por
        # Game.sk_setup quando a partida tem skills (sk_on). Valores neutros: tk_ext 0.0 (x + 0.0 e exato).
        self.skills = tuple(tuple(e) for e in skills if e) if skills else ()
        self.tk_ext = 0.0
        self.sk_cur = None     # skill ativa agora (id) ou None
        self.sk_fx = None      # FX desenhado agora (skills.ALL[id]["fx"]) ou None
        self.sk_kick = self.sk_won = self.sk_lost = ()
        self.sk_curve = 0.0
        self.sk_zap = None
        self.sk_stun = 0.0     # Choque: paralisado ate sk_t (so com sk_on)
        self.sk_evade = 0.0    # Drible: s de recarga impostos a quem erra o desarme (0.0 = nada)
        self.sk_aim = 0.0      # mira mais no canto (Matador/Curva/Chinelada); 0.0 = mira legado
        self.sk_launch = 0.0   # Lancador: chance de lancar por cima em cada reposicao do goleiro
        self.sk_ev = None      # FX de evento (kind, ate sk_t): drible, lancamento, paralisado
        self.sk_badge = False  # Lider: faixa de capitao (so desenho)
        self.sk_fx_next = 0.0


class Team:
    def __init__(self, idx, name, color, gk_color, human=None, squad=None, tuning=None):
        self.idx = idx
        self.dir = 1 if idx == 0 else -1
        self.name = name
        self.color = color
        self.gk_color = gk_color
        self.human = human
        self.players = []
        for i, (r, fx, fy) in enumerate(FORMATION):
            extra = {}
            if not squad:                          # modos 1P/2P: chassis padrao do papel, sem jitter
                nm, ovr, chassis, seed = "", 65, None, None
            elif isinstance(squad[i], dict):       # modo robos: {name, attrs, chassis, pid, paint}
                e = squad[i]
                nm, ovr, chassis, seed = e.get("name", ""), 65, e.get("chassis"), None
                extra = dict(attrs=e["attrs"], pid=e.get("pid"), paint=e.get("paint"), vis=e.get("vis"),
                             skills=e.get("skills"))
            elif len(squad[i]) >= 4:               # carreira: (nome, ovr, pid, pos)
                nm, ovr, pid, pos = squad[i][:4]
                chassis, seed = robots.POS_CHASSIS.get(pos), pid
            else:                                  # legado: (nome, ovr), chassis pelo papel
                nm, ovr = squad[i]
                chassis, seed = None, None
            self.players.append(Player(self, i, r, fx, fy, nm, ovr, chassis, seed,
                                       tuning=tuning, **extra))
        self.ctrl = None
        self.switch_cd = 0.0
        self.chaser = None
        self.tactic = skills.DEFAULT_TACTIC      # prioridade das skills (Ofensivo/Equilibrado/Defensivo)
        self.items = ()                          # consumiveis da partida (aura de time)
        self.sk_pilha = 0                        # Pilha Reserva: usos restantes

    @property
    def goal_x(self):      # gol que eu defendo
        return PITCH.left if self.dir == 1 else PITCH.right

    @property
    def target_x(self):    # gol que eu ataco
        return PITCH.right if self.dir == 1 else PITCH.left


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.fonts = {}
        self.text_cache = OrderedDict()
        self.fx = []                              # particulas: [x, y, vx, vy, vida, vida_max, cor, tam]
        self.fx_rng = random.Random(20260)        # RNG proprio: nunca toca o random global
        self.fx_pairs = {}
        self.fx_last = time.perf_counter()
        self.trail = deque(maxlen=10)
        self.trail_players = []                   # B13: jogadores com rastro cosmetico (warm_sprites)
        self.sprites = robot_art.SpriteCache()   # sprites dos robos (LRU por bytes; ver robot_art)
        self.puffs = None
        self.fx_amb = 0                           # particulas de robo vivas (teto ROBOT_FX_MAX)
        self.speed_idx = 0
        self.sk_on = False                        # skills ligadas nesta partida (so Modo Robos/campanha com skills)
        self.arena = None                         # modificador de arena (Torre do Po) ou None (legado)
        self.sk_rng = random.Random(SK_RNG_SEED)
        self.sk_t = 0.0
        self.sk_n = 0
        self.sk_groups = ()
        self.sk_live = []
        self.sk_count = {}
        self.sk_imgs = {}
        self.sk_pilha_on = False
        self.crowd = None                         # torcida da partida assistida (crowd.Crowd) ou None
        self.crowd_clock = None                   # relogio injetavel da torcida (testes); None = perf_counter
        self.crowd_venue = None                   # local da partida assistida atual (re-warm na pausa)
        self.crowd_story = False                  # partida da campanha: faixas da torcida citam o Ze Poeira
        self.pitch_surf = self.build_arena()
        # camera ESTADIO: o mundo (campo/robos/bola/FX) e desenhado aqui e reduzido para crowd.CAM_RECT.
        # Tudo pre-alocado: a escala por quadro usa a API com destino (nenhuma Surface nova).
        self.world = pygame.Surface((W, H)).convert()
        self.world_src = self.world.subsurface(crowd.CAM_CROP)
        self.world_dst = pygame.Surface(crowd.CAM_SIZE).convert()
        self.cam_scale = CAM_SCALERS[CAM_SCALER]
        self.cam_fallback = False                 # LOD da camera: caiu para PERTO nesta partida
        self.cam_acc, self.cam_n = 0.0, 0
        self.last_draw_ms = 0.0                   # ultimo quadro de partida medido (informativo)
        self.world_dirty = []                     # retangulos desenhados no mundo no quadro anterior
        self.world_full = True                    # proximo quadro ESTADIO repinta o campo inteiro
        self.glows = self.build_glows()
        self.hud_panel = self.build_hud_panel()
        self.banner_veil = self.build_banner_veil()
        self.menu_bg = self.build_menu_bg()
        self.state = "menu"
        self.mode = 1
        self.paused = False
        self.timer = 0.0
        self.msg = ""
        self.scorer = None
        self.menu_btns = [pygame.Rect(50 + i * 340, 330, 320, 90) for i in range(3)]
        self.continue_btn = pygame.Rect(W // 2 - 330, 450, 320, 70)
        self.career_match = False
        self.match_time = MATCH_TIME
        self.speed_idx = 0
        self.events = []
        self.last_owner = None
        self.has_save = Career.has_save()
        self.match_sink = None                    # (return_state, fn) quando a partida vem de outro modo (robos)
        self.career_ui = CareerUI(self)
        self.robots_status = "none"               # cache de Garage.load_status() (nao ler o store a cada frame)
        self.refresh_robots_status()
        self.robots_ui = RobotsUI(self)
        self.campaign_status = "none"             # cache de Campaign.load_status() (nunca lido por frame)
        self.refresh_campaign_status()
        self.campaign_ui = CampaignUI(self)
        self.new_match(1)
        self.state = "menu"

    # ------------------------------------------------------------------ setup
    def refresh_robots_status(self):
        self.robots_status = Garage.load_status()

    def refresh_campaign_status(self):
        self.campaign_status = Campaign.load_status()

    def campaign_btn(self):
        """Botao 6 do menu: terceira linha, larga (nao altera os botoes 1-5)."""
        return pygame.Rect(W // 2 - 330, 535, 660, 70)

    def robots_btn(self):
        """Botao 5 do menu: ao lado do 4 se ha save de carreira, senao centralizado."""
        x = W // 2 + 10 if self.has_save else W // 2 - 160
        return pygame.Rect(x, 450, 320, 70)

    def new_match(self, mode, venue=None):
        """Amistoso (modos 1/2). venue: local da torcida leve (A8: o menu passa crowd.FRIENDLY_VENUE);
        None = sem torcida (padrao: testes, goldens e o Game() inicial nao pre-renderizam nada)."""
        self.mode = mode
        if mode == 1:
            h0, h1 = Human(SOLO_KEYS), None
            n0, n1 = "VOCÊ", "CPU"
        else:
            h0, h1 = Human(P1_KEYS), Human(P2_KEYS)
            n0, n1 = "JOGADOR 1", "JOGADOR 2"
        self.teams = [
            Team(0, n0, (50, 120, 255), (250, 200, 40), h0),
            Team(1, n1, (235, 65, 65), (70, 205, 130), h1),
        ]
        self.score = [0, 0]
        self.career_match = False
        self.match_sink = None
        self.crowd = None
        self.sk_on = False                        # amistoso: nunca ha skills
        self.arena = None                         # amistoso: nunca ha modificador de arena
        self.speed_idx = 0
        self.match_time = self.time_left = MATCH_TIME
        self.events = []
        self.last_owner = None
        self.ball = Ball()
        self.paused = False
        self.reset_fx()
        self.crowd_venue = None
        self.crowd_story = False
        self.cam_reset()
        if venue is not None:
            self.warm_crowd(venue)
        self.kickoff(0)

    def start_career_match(self, home, away, venue=None):
        """Partida automática (CPU x CPU) do modo carreira. home/away = match_cfg()."""
        self.match_sink = None
        self._begin_match(home, away, venue=venue, story=False)

    def start_robot_match(self, home, away, on_done, tuning=robots.TUNING_ROBOTS, return_state="robots",
                          venue=None, arena=None):
        """Partida automática do modo robôs. home/away = {"name","color","squad":[5 dicts]}.

        Ao terminar chama on_done(score, events) e volta ao estado return_state ("robots" por padrao).
        venue: local da torcida (crowd.VENUES); None = crowd.DEFAULT_VENUE. arena: modificador da Torre do
        Po (ARENA_MODS) ou None (padrao; id desconhecido tambem vira None).
        """
        self._begin_match(home, away, tuning, venue=venue, story=return_state == "campaign", arena=arena)
        self.match_sink = (return_state, on_done)

    def _begin_match(self, home, away, tuning=None, venue=None, story=False, arena=None):
        self.mode = 0
        self.arena = arena if arena in ARENA_MODS else None
        self.crowd_story = bool(story)
        c1 = tuple(away["color"])
        if sum(abs(a - b) for a, b in zip(led_color(home["color"]), led_color(c1))) < 130:
            c1 = (235, 235, 235) if sum(home["color"]) < 600 else (0, 230, 255)
        self.teams = [
            Team(0, home["name"], tuple(home["color"]), GK_COLORS[0], None, home["squad"], tuning),
            Team(1, away["name"], c1, GK_COLORS[1], None, away["squad"], tuning),
        ]
        self.score = [0, 0]
        self.career_match = True
        self.match_time = self.time_left = CAREER_TIME
        self.events = []
        self.last_owner = None
        self.speed_idx = 0
        self.ball = Ball()
        self.paused = False
        self.sk_setup(home, away)
        self.reset_fx()
        self.cam_reset()
        self.warm_crowd(venue)
        self.state = "kickoff"
        self.kickoff(0)

    def finish_career_match(self):
        self.career_match = False
        self.arena = None
        self.crowd = None
        self.fx.clear()
        sink, self.match_sink = self.match_sink, None
        if sink:
            return_state, fn = sink
            self.state = return_state
            fn(list(self.score), list(self.events))
            return
        self.state = "career"
        self.career_ui.match_done(list(self.score), list(self.events))

    def minute(self):
        return int(clamp(90 * (1 - self.time_left / self.match_time) + 1, 1, 90))

    def kickoff(self, team_idx):
        b = self.ball
        for t in self.teams:
            t.ctrl = None
            for p in t.players:
                p.pos = self.formation_pos(p, kickoff=True)
                p.vel = V()
                p.face = V(t.dir, 0)
                p.cd = p.tackle_cd = p.hold = 0.0
        if self.sk_on:
            self.sk_kickoff()
        b.pos = V(CX, CY)
        b.vel = V()
        kicker = self.teams[team_idx].players[4]
        kicker.pos = V(CX - self.teams[team_idx].dir * PR, CY)
        b.owner = kicker
        self.state = "kickoff"
        self.timer = 1.6
        self.crowd_event("kickoff")

    def formation_pos(self, p, attack=0.0, kickoff=False):
        t, b = p.team, self.ball
        fx, fy = p.fx, p.fy
        if p.role != "GK":
            if kickoff:
                fx = min(fx, 0.40)
            else:
                bf = (b.pos.x - PITCH.left) / PITCH.w
                if t.dir == -1:
                    bf = 1 - bf
                fx = clamp(fx + (bf - 0.5) * 0.55 + attack, 0.10, 0.92)
                fy = clamp(fy + ((b.pos.y - PITCH.top) / PITCH.h - 0.5) * 0.3, 0.10, 0.90)
        x = PITCH.left + fx * PITCH.w if t.dir == 1 else PITCH.right - fx * PITCH.w
        return V(x, PITCH.top + fy * PITCH.h)

    # ------------------------------------------------------------------ input
    def speed_rects(self):
        return [pygame.Rect(W - 330 + i * 80, H - 36, 72, 28) for i in range(4)]

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and not self.text_editing() and self.audio_key(e.key):
            return
        if self.state in ("career", "robots", "campaign") and e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            sfx.play("back")
        if self.state == "career":
            return self.career_ui.handle_event(e)
        if self.state == "robots":
            ui = getattr(self, "robots_ui", None)
            if ui is not None:
                return ui.handle_event(e)
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):   # sem UI ainda: volta ao menu
                self.state = "menu"
            return
        if self.state == "campaign":
            ui = getattr(self, "campaign_ui", None)
            if ui is not None:
                return ui.handle_event(e)
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):   # sem UI: volta ao menu
                self.state = "menu"
            return
        if e.type == pygame.KEYDOWN:
            if self.state == "menu":
                if e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6):
                    sfx.play("click")
                elif e.key in (pygame.K_t, pygame.K_c):
                    sfx.play("toggle")
                if e.key == pygame.K_1:
                    self.new_match(1, crowd.FRIENDLY_VENUE)
                elif e.key == pygame.K_2:
                    self.new_match(2, crowd.FRIENDLY_VENUE)
                elif e.key == pygame.K_3:
                    self.career_ui.open_new()
                elif e.key == pygame.K_4:
                    self.career_ui.open_saved()
                elif e.key == pygame.K_5:
                    self.robots_ui.open()
                elif e.key == pygame.K_6:
                    self.campaign_ui.open()
                elif e.key == pygame.K_t:
                    self.toggle_crowd()
                elif e.key == pygame.K_c:
                    self.toggle_camera()
            elif self.career_match:
                if e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    self.speed_idx = e.key - pygame.K_1
                elif e.key == pygame.K_p:
                    self.paused = not self.paused
                elif e.key == pygame.K_t and self.paused:
                    sfx.play("toggle")
                    self.toggle_crowd()
                elif e.key == pygame.K_c and self.paused:
                    sfx.play("toggle")
                    self.toggle_camera()
                elif e.key in (pygame.K_RETURN, pygame.K_SPACE) and self.state == "over":
                    self.finish_career_match()
            elif self.state == "over":
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.new_match(self.mode, self.crowd_venue)
                elif e.key == pygame.K_ESCAPE:
                    self.state = "menu"
            else:
                if e.key == pygame.K_ESCAPE:
                    self.state = "menu"
                elif e.key == pygame.K_p:
                    self.paused = not self.paused
                elif e.key == pygame.K_t and self.paused and self.crowd_venue is not None:
                    self.toggle_crowd()
                elif e.key == pygame.K_c and self.paused and self.crowd_venue is not None:
                    self.toggle_camera()
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if self.state == "menu":
                if (any(r.collidepoint(e.pos) for r in self.menu_btns) or self.robots_btn().collidepoint(e.pos)
                        or self.campaign_btn().collidepoint(e.pos)
                        or (self.has_save and self.continue_btn.collidepoint(e.pos))):
                    sfx.play("click")
                for i, r in enumerate(self.menu_btns):
                    if r.collidepoint(e.pos):
                        [lambda: self.new_match(1, crowd.FRIENDLY_VENUE), lambda: self.new_match(2, crowd.FRIENDLY_VENUE),
                         self.career_ui.open_new][i]()
                        return
                if self.has_save and self.continue_btn.collidepoint(e.pos):
                    self.career_ui.open_saved()
                elif self.robots_btn().collidepoint(e.pos):
                    self.robots_ui.open()
                elif self.campaign_btn().collidepoint(e.pos):
                    self.campaign_ui.open()
            elif self.career_match:
                if self.state == "over":
                    self.finish_career_match()
                else:
                    for i, r in enumerate(self.speed_rects()):
                        if r.collidepoint(e.pos):
                            self.speed_idx = i

    def text_editing(self):
        """Campo de texto ativo (nome do time no Modo Robos/campanha): teclas de som nao valem."""
        ui = {"robots": "robots_ui", "campaign": "campaign_ui"}.get(self.state)
        return bool(ui and getattr(getattr(self, ui, None), "editing", False))

    # ----------------------------------------------------------------- update
    def update(self, dt):
        if self.state == "menu" or self.paused:
            return
        if self.state == "career":
            return self.career_ui.update(dt)
        if self.state == "robots":
            ui = getattr(self, "robots_ui", None)
            if ui is None:
                self.state = "menu"
                return
            return ui.update(dt)
        if self.state == "campaign":
            ui = getattr(self, "campaign_ui", None)
            if ui is None:
                self.state = "menu"
                return
            return ui.update(dt)
        if self.career_match and self.state != "over":
            # velocidade: n passos por frame (ou o máximo possível em ~12 ms)
            n = SPEEDS[self.speed_idx]
            t0, i = time.perf_counter(), 0
            while self.state != "over" and (n == "max" or i < n):
                self.step(1 / 60)
                i += 1
                if i > 1 and time.perf_counter() - t0 > 0.012:
                    break
            return
        self.step(dt)

    def step(self, dt):
        if self.state == "kickoff":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
        elif self.state == "play":
            self.update_play(dt)
        elif self.state == "goal":
            self.update_goal(dt)

    def tick_timers(self, dt):
        for t in self.teams:
            t.switch_cd = max(0.0, t.switch_cd - dt)
            for p in t.players:
                p.cd = max(0.0, p.cd - dt)
                p.tackle_cd = max(0.0, p.tackle_cd - dt)

    def update_play(self, dt):
        self.time_left -= dt
        self.tick_timers(dt)
        if self.sk_on:
            self.tick_skills(dt)
        for t in self.teams:
            cand = [p for p in t.players if p.role != "GK"]
            t.chaser = min(cand, key=lambda p: p.pos.distance_squared_to(self.ball.pos))
            if t.human:
                self.pick_ctrl(t)

        for t in self.teams:
            for p in t.players:
                if t.human and p is t.ctrl:
                    self.human_control(t, dt)
                else:
                    self.ai_player(p, dt)

        self.integrate(dt)
        if BATTERY_ON:
            for t in self.teams:
                for p in t.players:
                    self.tick_battery(p, dt)
        self.update_ball(dt)
        if self.state == "play" and self.time_left <= 0:
            self.time_left = 0
            self.state = "over"
            self.crowd_end()

    def update_goal(self, dt):
        self.timer -= dt
        b = self.ball
        b.pos += b.vel * dt
        b.vel *= 0.05 ** dt
        net_x0 = PITCH.left - GOAL_DEPTH + BR if self.scorer == 1 else PITCH.right - BR
        net_x1 = PITCH.left + BR if self.scorer == 1 else PITCH.right + GOAL_DEPTH - BR
        b.pos.x = clamp(b.pos.x, net_x0, net_x1)
        b.pos.y = clamp(b.pos.y, CY - GOAL_HALF + BR, CY + GOAL_HALF - BR)
        if self.timer <= 0:
            if self.time_left <= 0:
                self.time_left = 0
                self.state = "over"
                self.crowd_end()
            else:
                self.kickoff(1 - self.scorer)

    # --------------------------------------------------------- human control
    def pick_ctrl(self, t):
        b = self.ball
        cand = [p for p in t.players if p.role != "GK"]
        if b.owner and b.owner.team is t and b.owner.role != "GK":
            t.ctrl = b.owner
            return
        best = min(cand, key=lambda p: p.pos.distance_squared_to(b.pos))
        if t.ctrl not in cand:
            t.ctrl = best
        elif best is not t.ctrl and t.switch_cd <= 0:
            if t.ctrl.pos.distance_to(b.pos) - best.pos.distance_to(b.pos) > 30:
                t.ctrl = best
                t.switch_cd = 0.25

    def can_kick(self, p):
        b = self.ball
        return b.owner is p or (b.owner is None and p.pos.distance_to(b.pos) < PR + BR + 12)

    def human_control(self, t, dt):
        h, p, b = t.human, t.ctrl, self.ball
        pressed = pygame.key.get_pressed()
        d = V(h.down(pressed, "right") - h.down(pressed, "left"),
              h.down(pressed, "down") - h.down(pressed, "up"))
        speed = PLAYER_SPEED * (0.93 if b.owner is p else 1.0)
        self.steer(p, d, speed, dt)

        has_ball = self.can_kick(p)
        shoot = h.down(pressed, "shoot")
        pas = h.down(pressed, "pas")
        aim = d if d.length_squared() > 0 else p.face

        if shoot:
            h.charge = min(1.0, h.charge + dt / 0.75) if has_ball else 0.0
        elif h.shoot_prev:
            if h.charge > 0 and has_ball:
                d = self.aim_assist(p, aim)
                aim_err = HUMAN_AIM_ERR * max(0.0, 0.65 - p.f.g_chu)   # so abaixo de 65 (zero no legado)
                if aim_err > 0:
                    d = d.rotate(random.uniform(-aim_err, aim_err))
                self.kick(p, d, 330 + 520 * h.charge)
            h.charge = 0.0
        if pas and not h.pass_prev and has_ball:
            self.pass_ball(p, aim)
        h.shoot_prev, h.pass_prev = shoot, pas

    def aim_assist(self, p, d):
        t = p.team
        goal = V(t.target_x, CY)
        to = goal - p.pos
        if to.length() < 620 and angle_between(d, to) < 35:
            ty = CY + clamp(d.y * 2, -1, 1) * GOAL_HALF * 0.55
            return V(t.target_x, ty) - p.pos
        return d

    # ------------------------------------------------------------- ball ops
    def kick(self, p, d, power):
        b = self.ball
        if d.length_squared() == 0:
            d = V(p.face)
        d = d.normalize()
        power *= p.f.kick_pow
        if BATTERY_ON:
            power *= 0.85 + 0.15 * robots.bat_mul(p.bat)
            p.bat = max(0.0, p.bat - (robots.BAT_KICK_BASE + robots.BAT_KICK_POW * power / 850.0))
        b.owner = None
        b.pos = p.pos + d * (PR + BR + 3)
        b.vel = d * power
        p.cd = 0.35
        if self.sk_on:
            self.sk_on_kick(p, d, power)
        if power >= 600:
            self.fx_emit("kick", b.pos, d=d)
        self.snd("kick" if power >= 600 else "touch")
        if power > 450:                                 # chance: chute forte perto do gol, na direcao dele
            t = p.team
            if d.x * t.dir > 0.5 and abs(b.pos.x - t.target_x) < 300:
                self.crowd_event("chance", t.idx)

    def pass_ball(self, p, aim):
        best, best_score = None, 1e9
        for q in p.team.players:
            if q is p:
                continue
            rel = q.pos - p.pos
            dist = rel.length()
            if dist < 40:
                continue
            ang = angle_between(aim, rel)
            if ang > 55:
                continue
            score = ang + dist * 0.04 + (25 if q.role == "GK" else 0)
            if score < best_score:
                best, best_score = q, score
        if best is None:
            self.kick(p, aim, 380)
        else:
            self.send_pass(p, best)

    def send_pass(self, p, q):
        dist = p.pos.distance_to(q.pos)
        speed = min(CATCH_SPEED - 20, 230 + dist * 1.1)
        lead = q.pos + q.vel * (dist / speed) * 0.6
        d = lead - p.pos
        if p.f.pass_err > 0:                 # erro angular por controle (zero no legado)
            d = d.rotate(random.uniform(-p.f.pass_err, p.f.pass_err))
        self.kick(p, d, speed)
        t = p.team
        if t.human and q.role != "GK":
            t.ctrl = q
            t.switch_cd = 0.6

    def update_ball(self, dt):
        b = self.ball
        o = b.owner
        if o:
            self.last_owner = o
            b.pos = o.pos + o.face * (PR + BR - 2)
            b.vel = V(o.vel)
        else:
            if b.curve:
                self.ball_curve(b, dt)
            if b.air:
                b.air = max(0.0, b.air - dt)
            b.pos += b.vel * dt
            if self.arena == "bola_pesada":
                b.vel *= ARENA_BALL_DRAG ** dt
            else:
                b.vel *= 0.35 ** dt
            if b.vel.length() < 8:
                b.vel = V()
        b.roll += b.vel.length() * dt * 0.12

        self.ball_interactions()
        self.ball_bounds()

    def ball_interactions(self):
        b = self.ball
        o = b.owner
        if o and o.role != "GK":                      # desarme
            for q in self.teams[1 - o.team.idx].players:
                if q.role == "GK" or q.tackle_cd > 0:
                    continue
                if q.pos.distance_to(o.pos) < PR * 2 + 4 + q.tk_ext:
                    q.tackle_cd = 0.55
                    chance = 0.5 if q.team.human else q.f.tackle
                    if random.random() < chance * o.f.shield:
                        b.owner = q
                        q.cd = 0.0
                        o.cd = 0.7
                        self.fx_emit("tackle", b.pos)
                        self.snd("steal")
                        if self.sk_on:
                            self.on_steal(q, o)
                        break
                    if self.sk_on and o.sk_evade:          # Drible: o desarme falhou, o marcador fica
                        self.on_evade(q, o)
            return
        if o:
            return

        speed = b.vel.length()
        best, best_d = None, 1e9
        air = b.air
        for t in self.teams:
            for p in t.players:
                if air and p is not b.air_to and p.role != "GK":   # Lancador: bola por cima
                    continue
                d = p.pos.distance_to(b.pos)
                reach = PR + BR + (12 if p.role == "GK" else p.f.reach)
                if self.arena == "goleiro_gigante" and t.idx == 1 and p.role == "GK":
                    reach += ARENA_GK_REACH
                if d > reach or p.cd > 0:
                    continue
                if p.role == "GK":
                    if speed < CATCH_SPEED or random.random() < p.f.gk_save:
                        b.owner = p
                        b.vel = V()
                        p.hold = 0.8
                    else:
                        self.deflect(p, 0.6, spread=25)
                        p.cd = 0.35
                    if speed >= CATCH_SPEED:                       # defesa de chute forte
                        self.crowd_event("save", t.idx)
                    return
                cs = p.f.catch_speed
                if speed < cs:
                    fm = p.f.fumble
                    if fm > 0 and speed > 250 and random.random() < fm * (speed - 250) / (cs - 250):
                        self.deflect(p, 0.5)      # bola escapa do dominio
                        p.cd = 0.2
                    elif d < best_d:
                        best, best_d = p, d
                else:
                    self.deflect(p, 0.5)
                    p.cd = 0.15
        if best:
            b.owner = best
            b.vel = V()
            if air:
                b.air = 0.0

    def deflect(self, p, keep, spread=0):
        b = self.ball
        n = b.pos - p.pos
        n = n.normalize() if n.length_squared() else V(1, 0)
        if b.vel.dot(n) < 0:
            b.vel = b.vel.reflect(n) * keep
        if spread:
            b.vel = b.vel.rotate(random.uniform(-spread, spread))
        b.pos = p.pos + n * (PR + BR + 1)

    def ball_bounds(self):
        b, r = self.ball, PITCH
        in_mouth = abs(b.pos.y - CY) < GOAL_HALF - BR * 0.5
        if in_mouth:
            if b.pos.x < r.left - BR:
                return self.goal(1)
            if b.pos.x > r.right + BR:
                return self.goal(0)
        else:
            if b.pos.x < r.left + BR:
                self.fx_wall(abs(b.vel.x))
                b.pos.x = r.left + BR
                b.vel.x = abs(b.vel.x) * 0.6
            elif b.pos.x > r.right - BR:
                self.fx_wall(abs(b.vel.x))
                b.pos.x = r.right - BR
                b.vel.x = -abs(b.vel.x) * 0.6
        if b.pos.y < r.top + BR:
            self.fx_wall(abs(b.vel.y))
            b.pos.y = r.top + BR
            b.vel.y = abs(b.vel.y) * 0.6
        elif b.pos.y > r.bottom - BR:
            self.fx_wall(abs(b.vel.y))
            b.pos.y = r.bottom - BR
            b.vel.y = -abs(b.vel.y) * 0.6

    def goal(self, team_idx):
        self.score[team_idx] += 1
        self.scorer = team_idx
        lo = self.last_owner
        self.events.append({"min": self.minute(), "team": team_idx,
                            "name": lo.name if lo else "", "own": bool(lo and lo.team.idx != team_idx),
                            "pid": getattr(lo, "pid", None)})
        self.ball.owner = None
        if BATTERY_ON:                      # gol recarrega todos os robos
            for t in self.teams:
                for p in t.players:
                    p.bat = min(1.0, p.bat + robots.BAT_GOAL_BONUS)
        self.fx_emit("goal", self.ball.pos, led_color(self.teams[team_idx].color))
        if lo is not None and lo.team.idx == team_idx and lo.vis:
            self.fx_celebrate((lo.vis.get("look") or {}).get("celebration"), self.ball.pos)
        self.state = "goal"
        self.timer = 2.4
        self.crowd_event("goal", team_idx)

    # ---------------------------------------------------------- movement
    def tick_battery(self, p, dt):
        """Dreno proporcional a velocidade; recarga quando quase parado (so com BATTERY_ON)."""
        ratio = p.vel.length() / (PLAYER_SPEED * p.spd)
        if ratio < robots.BAT_REGEN_BELOW:
            p.bat += robots.BAT_REGEN / self.match_time * p.f.bat_regen_mul * dt
        elif self.arena == "bateria_curta":
            p.bat -= robots.BAT_RUN / self.match_time * min(1.0, ratio) * p.f.bat_drain_mul * dt * ARENA_BAT_DRAIN
        else:
            p.bat -= robots.BAT_RUN / self.match_time * min(1.0, ratio) * p.f.bat_drain_mul * dt
        p.bat = clamp(p.bat, 0.0, 1.0)

    def steer(self, p, d, speed, dt):
        speed *= p.spd
        if BATTERY_ON:
            speed *= robots.bat_mul(p.bat)
        if d.length_squared() > 1e-6:
            d = d.normalize()
            p.vel = p.vel.lerp(d * speed, min(1.0, p.f.accel * dt))
            f = p.face.lerp(d, min(1.0, 14 * dt))
            p.face = f.normalize() if f.length_squared() > 1e-4 else d
        else:
            p.vel = p.vel.lerp(V(), min(1.0, p.f.stop * dt))

    def integrate(self, dt):
        players = [p for t in self.teams for p in t.players]
        for p in players:
            p.pos += p.vel * dt
            p.pos.x = clamp(p.pos.x, PITCH.left + PR, PITCH.right - PR)
            p.pos.y = clamp(p.pos.y, PITCH.top + PR, PITCH.bottom - PR)
        for i, a in enumerate(players):
            for c in players[i + 1:]:
                diff = a.pos - c.pos
                l = diff.length()
                if 0 < l < PR * 2 - 2:
                    push = diff / l * (PR * 2 - 2 - l) * 0.5
                    a.pos += push
                    c.pos -= push
                    if self.fx_ok():
                        self.fx_bump(a, c)

    # --------------------------------------------------------------- AI
    def ai_player(self, p, dt):
        if self.sk_on and p.sk_stun > self.sk_t:      # Choque: paralisado (so com skills)
            return self.steer(p, V(), 0, dt)
        if p.role == "GK":
            return self.ai_gk(p, dt)
        t, b = p.team, self.ball
        if b.owner is p:
            return self.ai_with_ball(p, dt)
        if b.owner and b.owner.team is t:
            target = self.formation_pos(p, attack=0.15)
        elif t.chaser is p:
            if b.owner:
                target = b.owner.pos + b.owner.vel * 0.2
            else:
                target = b.pos + b.vel * 0.3
        else:
            target = self.formation_pos(p)
        to = target - p.pos
        speed = PLAYER_SPEED * AI_SPEED * min(1.0, to.length() / 40)
        self.steer(p, to, speed, dt)

    def lane_open(self, a, b, opps, margin=35):
        return all(seg_dist(o.pos, a, b) > margin for o in opps)

    def best_pass_target(self, p):
        t = p.team
        opps = self.teams[1 - t.idx].players
        best, best_score = None, -1e9
        for q in t.players:
            if q is p or q.role == "GK":
                continue
            adv = (q.pos.x - p.pos.x) * t.dir
            dist = p.pos.distance_to(q.pos)
            if adv < -20 or dist < 60 or dist > p.f.pass_range:
                continue
            if not self.lane_open(p.pos, q.pos, opps, p.f.lane_margin):
                continue
            score = adv - dist * 0.2
            if score > best_score:
                best, best_score = q, score
        return best

    def ai_shoot(self, p, bad_aim=False):
        t = p.team
        gk = self.teams[1 - t.idx].players[0]
        side = -1 if gk.pos.y > CY else 1
        if bad_aim:                          # decisao ruim: mira no lado do goleiro
            side = -side
        u = random.uniform(0.35, 0.7)
        if self.sk_on:
            if p.sk_kick:
                self.sk_pre_shot(p)
            if p.sk_aim:                     # Matador/Curva/Chinelada: mais no canto, longe do goleiro
                u = min(0.9, u + p.sk_aim)
        ty = CY + side * GOAL_HALF * u
        err = p.f.shot_err
        d = (V(t.target_x, ty) - p.pos).rotate(random.uniform(-err, err))
        self.kick(p, d, random.uniform(560, 680) + 140 * p.f.g_chu)

    def ai_bad_decision(self, p):
        """Decisao ruim (dec_err > 0): passe aleatorio, mira no goleiro ou chute de longe."""
        kind = random.randrange(3)
        if kind == 0:
            mates = [q for q in p.team.players if q is not p and q.role != "GK"]
            self.send_pass(p, random.choice(mates))
        elif kind == 1:
            self.ai_shoot(p, bad_aim=True)
        else:
            self.ai_shoot(p)

    def ai_with_ball(self, p, dt):
        t = p.team
        goal = V(t.target_x, CY)
        to_goal = goal - p.pos
        d = to_goal.normalize()
        pressed = False
        for q in self.teams[1 - t.idx].players:
            rel = p.pos - q.pos
            l = rel.length()
            if 1 < l < 100:
                d += rel.normalize() * (1 - l / 100) * 1.4
                pressed = pressed or l < 55
        self.steer(p, d, PLAYER_SPEED * AI_SPEED * 0.92, dt)

        p.think -= dt
        if p.think > 0:
            return
        p.think = random.uniform(0.2, 0.4) * p.f.think_mul
        if p.f.dec_err > 0 and random.random() < p.f.dec_err:
            return self.ai_bad_decision(p)
        if to_goal.length() < p.f.shoot_range and random.random() < 0.8:
            self.ai_shoot(p)
        elif pressed and random.random() < 0.65:
            tm = self.best_pass_target(p)
            if tm:
                self.send_pass(p, tm)
            elif abs(p.pos.x - t.goal_x) < 260:
                self.kick(p, V(CX, p.pos.y + random.uniform(-150, 150)) - p.pos, 560)
        elif random.random() < 0.08:
            tm = self.best_pass_target(p)
            if tm:
                self.send_pass(p, tm)

    def ai_gk(self, p, dt):
        t, b = p.team, self.ball
        if b.owner is p:
            self.steer(p, V(), 0, dt)
            p.hold -= dt
            if p.hold <= 0:
                tm = self.best_pass_target(p)
                if tm:
                    self.send_pass(p, tm)
                elif self.sk_on and p.sk_launch:          # Lancador: bola por cima no mais adiantado
                    self.sk_gk_launch(p)
                else:
                    self.kick(p, V(CX, random.uniform(PITCH.top + 80, PITCH.bottom - 80)) - p.pos, 600)
            return
        line_x = t.goal_x + t.dir * 30
        shot = False
        if (b.owner is None and abs(b.pos.x - t.goal_x) < 200
                and b.pos.distance_to(p.pos) < 190 and b.vel.length() < 260):
            target = V(b.pos)
        else:
            ty = b.pos.y
            if b.vel.x * t.dir < -30:
                tt = (line_x - b.pos.x) / b.vel.x
                if 0 < tt < 1.5:
                    ty = b.pos.y + b.vel.y * tt * p.f.gk_lead
                    shot = b.vel.length() > 200
            ty = clamp(ty, CY - GOAL_HALF * 0.9, CY + GOAL_HALF * 0.9)
            target = V(line_x, ty)
        to = target - p.pos
        speed = p.f.gk_speed * min(1.0, to.length() / 30) * (1.25 if shot else 1.0)
        self.steer(p, to, speed, dt)
        p.face = V(t.dir, 0)

    # ---------------------------------------------------------------- skills (B6)
    def sk_setup(self, home, away):
        """Monta as skills da partida (Fase 4, B6). So liga (sk_on) se algum time traz skills, aura ou
        consumiveis; senao o motor fica EXATAMENTE como o legado (goldens, carreira, amistoso).

        Por time: aura (Lider) + consumiveis (ITEMS: "team" no time, "gk" so no goleiro, "one" = Pilha
        Reserva) entram nos fatores base de cada robo; por robo: passivas compiladas em f_base, uma
        variante pre-calculada (f_var) por ativa/condicional. Nao toca o random global (RNG: sk_rng)."""
        self.sk_on = False
        self.sk_rng = random.Random(SK_RNG_SEED)
        self.sk_t = 0.0
        self.sk_n = 0
        self.sk_live = []
        self.sk_count = {}
        groups = [[] for _ in range(SK_EVAL_EVERY)]
        k = 0
        self.sk_pilha_on = False
        for t, cfg in zip(self.teams, (home, away)):
            tac = cfg.get("tactic") if isinstance(cfg, dict) else None
            t.tactic = tac if tac in skills.TACTICS else skills.DEFAULT_TACTIC
            raw = cfg.get("items") if isinstance(cfg, dict) else None
            items = tuple(i for i in (raw or ()) if i in skills.ITEMS)[:skills.BACKPACK]
            t.items = items
            lists = [p.skills for p in t.players]
            aura = skills.aura_mods(lists)
            if not (aura or items or any(lists)):
                continue
            self.sk_on = True
            t.sk_pilha = sum(skills.ITEMS[i].get("extra", {}).get("uses", 0) for i in items
                             if skills.ITEMS[i]["scope"] == "one")
            self.sk_pilha_on = self.sk_pilha_on or t.sk_pilha > 0
            for p in t.players:
                if self.sk_init_player(p, aura, items):
                    groups[k % SK_EVAL_EVERY].append(p)
                    k += 1
            if aura:                                   # faixa de capitao no dono da aura (so desenho)
                for p in t.players:
                    if any(skills.ALL.get(e[0], {}).get("aura") for e in p.skills):
                        p.sk_badge = True
                        break
        self.sk_groups = tuple(tuple(g) for g in groups)
        if self.sk_on:
            self.warm_skill_fx()

    def sk_init_player(self, p, aura, items):
        """Estado de skills de um robo. Devolve True se ele tem gatilho periodico (vai num grupo)."""
        f0 = p.f
        if aura:
            f0 = skills.apply_mods(f0, aura)
        for it in items:
            sc = skills.ITEMS[it]["scope"]
            if sc == "team" or (sc == "gk" and p.role == "GK"):
                f0 = skills.apply_mods(f0, skills.item_mods(it))
        comp = skills.compile_factors(f0, p.skills)
        p.f = p.f_base = comp["_base"]
        p.spd = p.spd_base = p.f.speed
        p.f_var = {sid: v for sid, v in comp.items() if sid != "_base"}
        p.sk_rank, p.sk_cdv, p.sk_extra, p.sk_ready, p.sk_uses = {}, {}, {}, {}, {}
        per, kick, won, lost, cond, need = [], [], [], [], [], set()
        ev_kick, ev_won, ev_lost = (skills.EVENT_TRIGGERS[k] for k in ("kick", "won", "lost"))
        p.sk_launch = 0.0
        for e in p.skills:
            sid, rank, up = skills._norm(e)
            s = skills.ALL.get(sid)
            if s is not None and s["kind"] == "P" and "launch" in s.get("extra", {}):
                p.sk_launch = max(p.sk_launch, skills.scaled_extra(sid, rank, up)["launch"])
            if s is None or s["kind"] == "P" or sid in p.sk_rank:
                continue
            p.sk_rank[sid] = (rank, up)
            p.sk_cdv[sid] = skills.cooldown(sid, rank)
            p.sk_extra[sid] = skills.scaled_extra(sid, rank, up)
            p.sk_ready[sid] = 0.0
            if "uses" in p.sk_extra[sid]:
                p.sk_uses[sid] = int(p.sk_extra[sid]["uses"])
            trg = s["trigger"]
            fn = skills.TRIGGERS[trg]
            if s["kind"] == "C":
                cond.append((sid, fn))
                need.update(skills.TRIGGER_KEYS.get(trg, ()))
            elif trg in ev_kick:
                kick.append(sid)
            elif trg in ev_won:
                won.append(sid)
            elif trg in ev_lost:
                lost.append(sid)
            else:
                per.append((sid, fn, s["bat"] + skills.BAT_MARGIN if s["bat"] else 0.0))
                need.update(skills.TRIGGER_KEYS.get(trg, ()))
        p.sk_per, p.sk_kick, p.sk_won, p.sk_lost, p.sk_cond = (tuple(x) for x in (per, kick, won, lost, cond))
        p.sk_need = frozenset(need)
        p.sk_cur = p.sk_condon = p.sk_fx = None
        p.sk_end = p.sk_gcd = p.sk_fat_end = p.sk_fx_t = 0.0
        p.sk_pull = 0.0
        p.sk_curve = 0.0
        p.sk_curve_t = 0.0
        p.sk_zap = None
        p.sk_fx_next = 0.0
        p.sk_stun = p.sk_evade = p.sk_aim = 0.0
        p.sk_ev = None
        return bool(per or cond)

    def sk_kickoff(self):
        """Saida de bola: encerra as ativas (o cansaco do Overclock tambem) e a curva da bola."""
        t = self.sk_t
        for p in list(self.sk_live):
            if p.sk_cur is not None:
                self.sk_stop(p, t, fatigue=False)
            p.sk_fat_end = 0.0
            p.spd = p.f.speed
        self.sk_live = []
        for tm in self.teams:
            for p in tm.players:
                if p.sk_cur is None and getattr(p, "sk_condon", None) is not None:
                    p.f = p.f_base
                    p.spd = p.spd_base
                    p.sk_condon = None
                    p.sk_fx = None
                p.sk_stun = p.sk_aim = 0.0
        self.ball.curve = self.ball.curve_t = self.ball.air = 0.0
        self.ball.air_to = None

    def tick_skills(self, dt):
        """Relogio das skills (so com sk_on): fim de ativas/cansaco e o ima da Succao a cada passo; os
        gatilhos periodicos de 1/6 dos robos por passo (cada robo a ~10 Hz); Pilha Reserva."""
        t = self.sk_t = self.sk_t + dt
        if self.sk_live:
            b = self.ball
            for p in tuple(self.sk_live):
                if p.sk_cur is not None:
                    if t >= p.sk_end:
                        self.sk_stop(p, t)
                    elif p.sk_pull and b.owner is None:
                        to = p.pos - b.pos
                        d2 = to.length_squared()
                        if 1.0 < d2 < 14400.0:            # ima ate 120 px
                            dd = math.sqrt(d2)
                            b.vel += to * (p.sk_pull * dt / dd)
                            if b.vel.length_squared() < (p.sk_pull * SK_PULL_MIN) ** 2:
                                # bola parada/lenta: o arrasto zera < 8 px/s a cada passo; o ima a
                                # arrasta a uma velocidade minima (B14: antes nao mexia a bola parada)
                                b.vel = to * (p.sk_pull * SK_PULL_MIN / dd)
                elif t >= p.sk_fat_end:
                    p.sk_fat_end = 0.0
                    p.spd = p.f.speed
                    self.sk_live.remove(p)
        n = self.sk_n = (self.sk_n + 1) % SK_EVAL_EVERY
        for p in self.sk_groups[n]:
            if p.sk_cur is None:
                self.sk_eval(p, t)
        if not self.sk_pilha_on:
            return
        self.sk_pilha_on = any(tm.sk_pilha for tm in self.teams)
        for tm in self.teams:
            if tm.sk_pilha:
                for p in tm.players:
                    if p.bat < skills.ITEMS["pilha_reserva"]["extra"]["restore_below"]:
                        p.bat = 1.0
                        tm.sk_pilha -= 1
                        self.sk_count["pilha_reserva"] = self.sk_count.get("pilha_reserva", 0) + 1
                        break

    def sk_ctx(self, p, need):
        """Contexto dos gatilhos (skills.TRIGGERS) so com os campos que o robo precisa."""
        b = self.ball
        o = b.owner
        t = p.team
        hb = o is p
        c = {"has_ball": hb, "bat": p.bat}
        if hb and ("opp_ahead" in need or "opp_near" in need):
            ahead = near = math.inf
            dx = t.dir
            px, py = p.pos.x, p.pos.y
            for q in self.teams[1 - t.idx].players:
                rx, ry = q.pos.x - px, q.pos.y - py
                dd = math.hypot(rx, ry)
                if dd < near:
                    near = dd
                if rx * dx > SK_AHEAD_COS * dd and dd < ahead:
                    ahead = dd
            c["opp_ahead"] = ahead
            c["opp_near"] = near
        opp_has = o is not None and o.team is not t
        if "opp_has_ball" in need:
            c["opp_has_ball"] = opp_has
        if "opp_ball_zone" in need:
            c["opp_ball_zone"] = opp_has and o.pos.distance_squared_to(p.pos) < SK_ZONE * SK_ZONE
        if "ball_free" in need:
            c["ball_free"] = o is None
            c["is_chaser"] = t.chaser is p
            c["ball_dist"] = p.pos.distance_to(b.pos)
            c["ball_speed"] = b.vel.length()
        if "ball_goal_dist" in need:
            c["ball_goal_dist"] = math.hypot(b.pos.x - t.goal_x, b.pos.y - CY)
        if "shot_speed" in need:
            c["shot_speed"] = b.vel.length() if o is None else 0.0
            c["ball_toward_goal"] = o is None and b.vel.x * t.dir < 0
        if "dist_opp_goal" in need:
            c["dist_opp_goal"] = math.hypot(p.pos.x - t.target_x, p.pos.y - CY)
        if "ball_third" in need:
            bf = (b.pos.x - PITCH.left) / PITCH.w
            if t.dir == -1:
                bf = 1.0 - bf
            c["ball_third"] = "att" if bf > 2 / 3 else ("def" if bf < 1 / 3 else "mid")
        if "vel_frac" in need:
            c["vel_frac"] = p.vel.length() / (PLAYER_SPEED * p.spd_base)
        if "score_diff" in need:
            c["score_diff"] = self.score[t.idx] - self.score[1 - t.idx]
            c["minute"] = self.minute()
        return c

    def sk_ready_ok(self, p, sid, t):
        """Pronta: recarga zerada, usos restantes e bateria >= custo + margem."""
        if p.sk_ready[sid] > t:
            return False
        if sid in p.sk_uses and p.sk_uses[sid] <= 0:
            return False
        cost = skills.ALL[sid]["bat"]
        return not cost or p.bat >= cost + skills.BAT_MARGIN

    def sk_eval(self, p, t):
        """Avaliacao periodica de um robo sem ativa: condicional (Instinto Matador) e ativas prontas.
        Caminho quente (~1,7 robos por passo): gatilhos pre-resolvidos (skills.TRIGGERS) e ctx so com os
        campos que o robo usa, montado so se alguma skill esta pronta."""
        ctx = None
        if p.sk_cond:
            ctx = self.sk_ctx(p, p.sk_need)
            on = None
            for sid, fn in p.sk_cond:
                if fn(ctx):
                    on = sid
                    break
            if on != p.sk_condon:
                p.sk_condon = on
                p.f = p.f_var[on] if on is not None else p.f_base
                p.sk_aim = p.sk_extra[on].get("aim", 0.0) if on is not None else 0.0
                if not p.sk_fat_end:
                    p.spd = p.f.speed
                p.sk_fx = skills.ALL[on]["fx"] if on is not None else None
                if on is not None:
                    p.sk_fx_t = t
                    self.sk_count[on] = self.sk_count.get(on, 0) + 1
        if t < p.sk_gcd:
            return
        bat = p.bat
        ready, uses = p.sk_ready, p.sk_uses
        cand = None
        for sid, fn, need_bat in p.sk_per:
            if ready[sid] > t or bat < need_bat or (uses and uses.get(sid, 1) <= 0):
                continue
            if ctx is None:
                ctx = self.sk_ctx(p, p.sk_need)
            if fn(ctx):
                cand = [sid] if cand is None else cand + [sid]
        if cand:
            self.sk_start(p, cand[0] if len(cand) == 1 else skills.pick_active(cand, p.team.tactic), t)

    def sk_start(self, p, sid, t):
        """Liga a ativa: custo de bateria, recarga, GCD, variante de fatores (dur > 0)."""
        s = skills.ALL[sid]
        p.bat = max(0.0, p.bat - s["bat"])
        p.sk_ready[sid] = t + p.sk_cdv[sid]
        if sid in p.sk_uses:
            p.sk_uses[sid] -= 1
        p.sk_gcd = t + skills.GCD
        self.sk_count[sid] = self.sk_count.get(sid, 0) + 1
        ex = p.sk_extra[sid]
        if "bat_add" in ex:                            # Recarga: carga imediata
            p.bat = min(1.0, p.bat + ex["bat_add"])
        self.snd("dash" if s["fx"] in ("dash", "wheel") else "skill")
        if s["dur"] <= 0:                              # efeito imediato (Choque): sem variante
            return
        p.sk_cur = sid
        p.sk_end = t + s["dur"]
        p.sk_condon = None
        p.f = p.f_var[sid]
        p.spd = p.f.speed
        p.sk_fat_end = 0.0
        p.tk_ext = ex.get("tk_ext", 0.0)
        p.sk_pull = ex.get("pull", 0.0)
        p.sk_evade = ex.get("evade", 0.0)
        p.sk_aim = ex.get("aim", 0.0)
        p.sk_fx = s["fx"]
        p.sk_fx_t = t
        if p not in self.sk_live:
            self.sk_live.append(p)

    def sk_stop(self, p, t, fatigue=True):
        """Desliga a ativa: volta a f_base (passivas), tk_ext 0.0; Overclock deixa cansaco (spd)."""
        sid = p.sk_cur
        p.sk_cur = None
        p.f = p.f_base
        p.tk_ext = 0.0
        p.sk_pull = 0.0
        p.sk_evade = p.sk_aim = 0.0
        p.sk_fx = None
        fat = p.sk_extra[sid].get("fatigue") if sid is not None else None
        if fatigue and fat:
            p.sk_fat_end = t + fat[0]
            p.spd = p.f.speed * fat[1]
        else:
            p.spd = p.spd_base
            if p in self.sk_live:
                self.sk_live.remove(p)

    def sk_pre_shot(self, p):
        """Gatilho de chute (Chute em Curva, Chinelada): chamado em ai_shoot ANTES do erro de mira, para
        shot_err/kick_pow da variante valerem neste chute. Interrompe a ativa atual (o chute encerra a
        conducao); ignora o GCD (gatilho de evento)."""
        t = self.sk_t
        cand = [sid for sid in p.sk_kick if self.sk_ready_ok(p, sid, t)]
        if not cand:
            return
        tm = p.team
        gk = self.teams[1 - tm.idx].players[0]
        ctx = {"kicking": True, "dist_opp_goal": math.hypot(p.pos.x - tm.target_x, p.pos.y - CY),
               "shoot_range": p.f.shoot_range,
               "gk_off_line": abs(gk.pos.x - tm.target_x) > SK_GK_OFF[0] or abs(gk.pos.y - CY) > SK_GK_OFF[1]}
        cand = [sid for sid in cand if skills.check_trigger(sid, ctx)]
        if not cand:
            return
        sid = cand[0] if len(cand) == 1 else skills.pick_active(cand, tm.tactic)
        if p.sk_cur is not None:
            self.sk_stop(p, t, fatigue=False)
        self.sk_start(p, sid, t)
        p.sk_curve = p.sk_extra[sid].get("curve", 0.0)
        p.sk_curve_t = p.sk_extra[sid].get("curve_t", 0.0)

    def sk_on_kick(self, p, d, power):
        """Depois de kick() (sk_on): a bola sai reta (curve 0) salvo um Chute em Curva pendente; a curva
        gira a velocidade a `curve` graus/s por `curve_t` s e a saida e pre-girada para o arco terminar
        no alvo (o goleiro le a linha reta). Direcao (horario/anti) pelo sk_rng."""
        b = self.ball
        b.air = 0.0
        b.air_to = None
        cv = p.sk_curve
        if not cv:
            b.curve = b.curve_t = 0.0
            return
        p.sk_curve = 0.0
        sign = 1.0 if self.sk_rng.random() < 0.5 else -1.0
        pre = -self.sk_curve_chord(sign * cv, p.sk_curve_t, power, abs(p.team.target_x - p.pos.x))
        b.vel = b.vel.rotate(pre)
        b.pos = p.pos + d.rotate(pre) * (PR + BR + 3)
        b.curve = sign * cv
        b.curve_t = p.sk_curve_t

    @staticmethod
    def sk_curve_chord(curve, curve_t, power, dist):
        """Angulo (graus) da corda do arco de um chute com curva ate percorrer `dist` px na direcao do
        chute: integra a mesma fisica de update_ball (arrasto 0,35**dt, giro curve*dt por curve_t s) num
        laco curto (so no chute em curva). Pre-girar a saida por -angulo faz a bola chegar ao alvo."""
        dt = 1 / 60
        vx, vy = power, 0.0
        x = y = 0.0
        t = 0.0
        drag = 0.35 ** dt
        c, s = math.cos(math.radians(curve * dt)), math.sin(math.radians(curve * dt))
        while x < dist and t < 2.0 and vx * vx + vy * vy > 64.0:
            if t < curve_t:
                vx, vy = vx * c - vy * s, vx * s + vy * c
            x += vx * dt
            y += vy * dt
            vx *= drag
            vy *= drag
            t += dt
        return math.degrees(math.atan2(y, x)) if x > 1.0 else 0.0

    def ball_curve(self, b, dt):
        """Bola com efeito (so existe com sk_on): gira a velocidade; acaba em curve_t."""
        b.vel = b.vel.rotate(b.curve * dt)
        b.curve_t -= dt
        if b.curve_t <= 0:
            b.curve = b.curve_t = 0.0

    def on_steal(self, q, o):
        """Desarme com sucesso (sk_on): q ganhou, o perdeu. Choque (o fica `stun` s a mais sem dominar)
        e Remendo (o protege a bola por 2 s)."""
        t = self.sk_t
        for sid in q.sk_won:
            if self.sk_ready_ok(q, sid, t) and skills.check_trigger(sid, {"won_ball": True}):
                self.sk_start(q, sid, t)
                stun = q.sk_extra[sid].get("stun", 0.0)
                if stun:                               # paralisado: nao anda nem domina (B14; o desarme
                    o.cd += stun                       # de volta continua valendo: bloquea-lo valia demais)
                    o.sk_stun = t + stun
                    o.vel = V()
                    o.sk_ev = ("stun", t + stun)
                    q.sk_zap = (o, t + SK_ZAP_T)
                break
        if o.sk_lost and o.sk_cur is None:
            for sid in o.sk_lost:
                if self.sk_ready_ok(o, sid, t) and skills.check_trigger(sid, {"lost_ball": True}):
                    self.sk_start(o, sid, t)
                    break

    def on_evade(self, q, o):
        """Desarme que falhou contra o Drible (sk_on): o marcador q fica `evade` s sem tentar de novo e
        perde o embalo (fica para tras); o FX "DRIBLE!" so aparece aqui, quando a skill muda o lance."""
        t = self.sk_t
        q.tackle_cd = max(q.tackle_cd, o.sk_evade)
        q.vel = q.vel * 0.2
        o.sk_ev = ("evade", t + 0.6)
        self.snd("dribble")
        self.sk_count["drible_evade"] = self.sk_count.get("drible_evade", 0) + 1

    def sk_gk_launch(self, p):
        """Lancador (sk_on): sem linha de passe, o goleiro (com chance `launch` por reposicao, no sk_rng)
        lanca POR CIMA para o companheiro mais adiantado ao alcance (pass_range); a bola fica ate
        SK_LAUNCH_AIR s sem poder ser dominada por ninguem alem do alvo (os goleiros ainda defendem) e
        chega dominavel (~200 px/s). Sem lancamento: o chutao legado."""
        if self.sk_rng.random() >= p.sk_launch:
            return self.kick(p, V(CX, random.uniform(PITCH.top + 80, PITCH.bottom - 80)) - p.pos, 600)
        t = p.team
        best, best_adv = None, -1e9
        for q in t.players:
            if q is p or q.role == "GK":
                continue
            dist = p.pos.distance_to(q.pos)
            adv = (q.pos.x - p.pos.x) * t.dir
            if dist < 120 or dist > p.f.pass_range or adv <= best_adv:
                continue
            best, best_adv = q, adv
        if best is None:
            return self.kick(p, V(CX, random.uniform(PITCH.top + 80, PITCH.bottom - 80)) - p.pos, 600)
        dist = p.pos.distance_to(best.pos)
        lead = best.pos + best.vel * 0.5
        v0 = min(SK_LAUNCH_VMAX, SK_DRAG_K * dist + 200.0)
        self.kick(p, lead - p.pos, v0 / max(0.3, p.f.kick_pow))
        b = self.ball
        frac = min(0.95, SK_DRAG_K * dist / v0)
        b.air = min(SK_LAUNCH_AIR, -math.log(1.0 - frac) / SK_DRAG_K * 0.85)
        b.air_to = best
        p.sk_ev = ("launch", self.sk_t + 0.8)
        self.sk_count["lancador"] = self.sk_count.get("lancador", 0) + 1

    # ------------------------------------------------------------------ fx
    def reset_fx(self):
        self.fx.clear()
        self.fx_amb = 0
        self.fx_pairs.clear()
        self.trail.clear()
        self.warm_sprites()

    def fx_ok(self):
        return self.speed_idx != 3 and self.state != "over"

    def fx_emit(self, kind, pos, color=None, d=None):
        """Dispara faiscas. Usa so o RNG proprio; no-op em MAX e em 'over'. Nao altera a simulacao.

        Particula: [x, y, vx, vy, vida, vida_max, cor, tam, estilo, de_robo]; estilo None = faisca,
        int = sprite de fumaca/poeira (FX_STYLE). As de robo (ROBOT_FX) tem teto ROBOT_FX_MAX."""
        if self.speed_idx == 3 or self.state == "over":
            return
        n, v0, v1, l0, l1, base, size = FX_KINDS[kind]
        col = color or base or (255, 255, 255)
        room = FX_MAX - len(self.fx)
        amb = kind in ROBOT_FX
        if amb:
            room = min(room, ROBOT_FX_MAX - self.fx_amb)
        if room <= 0:
            return
        rng = self.fx_rng
        px, py = pos.x, pos.y
        style = FX_STYLE.get(kind)
        rise = FX_RISE.get(kind, 0.0)
        for _ in range(min(n, room)):
            if d is not None:                       # leque para tras da direcao do chute
                a = math.atan2(d.y, d.x) + math.pi + rng.uniform(-0.9, 0.9)
            else:
                a = rng.uniform(0, 2 * math.pi)
            sp = rng.uniform(v0, v1)
            life = rng.uniform(l0, l1)
            self.fx.append([px, py, math.cos(a) * sp, math.sin(a) * sp - rise, life, life, col, size, style, amb])
        if amb:
            self.fx_amb += min(n, room)

    def robot_fx(self, p, art, now):
        """A11: poeira ao correr, fumaca ao superaquecer/bateria critica, faiscas com bateria baixa.

        Chamado pelo desenho (relogio real, RNG proprio fx_rng): nunca toca a simulacao nem o random
        global; desligado em MAX, em 'over' e na pausa (fx_emit/guarda abaixo)."""
        if now < p.fx_next or self.paused or self.speed_idx == 3 or self.state == "over":
            return
        sp2 = p.vel.length_squared()
        bat = p.bat
        rng = self.fx_rng
        if bat < CRIT_BAT:
            kind, gap = "smoke_dark", 0.2
        elif art.hot and bat < 0.5 and sp2 > 140 * 140:
            kind, gap = "smoke", 0.28
        elif bat < LOW_BAT:
            kind, gap = "spark", 0.3 + rng.random() * 0.5
        elif sp2 > DUST_SPEED * DUST_SPEED:
            kind, gap = "dust", 0.14
        else:
            p.fx_next = now + 0.1
            return
        p.fx_next = now + gap
        if kind == "spark":
            self.fx_emit(kind, p.pos + V(rng.uniform(-8, 8), rng.uniform(-8, 8)))
            return
        back = p.vel.normalize() * -art.rad if sp2 > 1 else V(0, 0)
        self.fx_emit(kind, p.pos + back, d=(p.vel if sp2 > 1 else None))

    def fx_celebrate(self, cid, pos):
        """B13: comemoracao cosmetica (so particulas no fx_rng; no-op em MAX/'over' via fx_emit)."""
        cols = robot_art.CELEBRATION_COLORS.get(cid)
        if not cols:
            return
        kind = "cel_" + cid
        if cid == "fogos":                          # 3 estouros em volta da bola
            for (dx, dy), c in zip(((-40, -30), (35, -20), (0, 35)), cols):
                self.fx_emit(kind, pos + V(dx, dy), c)
            return
        for c in cols:
            self.fx_emit(kind, pos, c)

    def fx_bump(self, a, c):
        """Colisao robo x robo: 4 faiscas, no maximo 1 por par a cada 0.3 s de jogo."""
        key = (a.team.idx, a.idx, c.team.idx, c.idx)
        last = self.fx_pairs.get(key)
        if last is not None and last - self.time_left < 0.3:
            return
        self.fx_pairs[key] = self.time_left
        self.fx_emit("bump", (a.pos + c.pos) * 0.5)

    def fx_wall(self, impact):
        if impact > 200 and self.ball.owner is None:
            self.fx_emit("wall", self.ball.pos)
            b = self.ball                            # trave: batida no fundo, rente a boca do gol
            if (abs(b.pos.x - CX) > PITCH.w / 2 - BR - 2
                    and GOAL_HALF - BR <= abs(b.pos.y - CY) < GOAL_HALF + 18):
                self.crowd_event("post")

    # --------------------------------------------------------------- torcida
    def warm_crowd(self, venue=None):
        """Torcida da partida assistida (inicio da partida, nunca no meio). prefs "crowd" OFF = sem torcida.

        Pre-renderiza o atlas e a arena composta (cache LRU de 3 em crowd.py). Nao toca o random global.
        Tambem busca (text_img) as imagens de onomatopeias, placas de LED e legendas do telao: nenhum
        texto novo e renderizado durante a partida.
        """
        self.crowd = None
        self.crowd_venue = venue
        level = self.crowd_level()
        if level not in crowd.LEVELS:                 # "OFF" (ou valor estranho): sem torcida
            return None
        self.world_full = True
        c0, c1 = (led_color(t.color) for t in self.teams)
        bundle = crowd.warm_crowd(venue, c0, c1, level, base=self.pitch_surf, txt=self.text_img,
                                  camera=self.camera_mode())
        self.crowd = crowd.Crowd(bundle, clock=self.crowd_clock, txt=self.text_img, telao=self.career_match,
                                 story=self.crowd_story)
        return self.crowd

    def crowd_level(self):
        try:
            level = prefs.get("crowd")
        except Exception:  # noqa: BLE001  (prefs nunca devem derrubar a partida)
            level = "ALTA"
        return level if level in CROWD_CYCLE else "ALTA"

    def toggle_crowd(self):
        """Tecla T (menu ou pausa da partida): ALTA -> MEDIA -> OFF -> ALTA, gravado em prefs.

        Na pausa de uma partida assistida aplica na hora (re-warm aqui, no evento; nunca no desenho)."""
        cur = self.crowd_level()
        nxt = CROWD_CYCLE[(CROWD_CYCLE.index(cur) + 1) % len(CROWD_CYCLE)]
        try:
            prefs.set("crowd", nxt)
        except Exception:  # noqa: BLE001
            pass
        if self.state != "menu" and (self.career_match or self.crowd_venue is not None):
            self.warm_crowd(self.crowd_venue)   # amistoso: so se comecou com torcida (crowd_venue)
        return nxt

    def crowd_label(self):
        return "T: torcida " + CROWD_LABELS[self.crowd_level()]

    # ------------------------------------------------------------- camera
    def camera_pref(self):
        """Escolha gravada (prefs "camera"): "ESTADIO", "PERTO" ou None (AUTO, nunca escolhida)."""
        try:
            c = prefs.get("camera")
        except Exception:  # noqa: BLE001
            c = None
        return c if c in CAMERA_MODES else None

    def camera_mode(self):
        """Camera da partida atual. AUTO: assistida ESTADIO, amistoso com humano (modos 1/2) PERTO.
        O LOD da camera (cam_fallback) forca PERTO ate a proxima partida."""
        if self.cam_fallback:
            return "PERTO"
        c = self.camera_pref()
        if c is None:
            c = "PERTO" if (not self.career_match and self.mode in (1, 2)) else "ESTADIO"
        return c

    def camera_on(self):
        """Camera ESTADIO desenhando agora: torcida larga existe e nao esta em MAX."""
        cr = self.crowd
        return cr is not None and cr.b.camera == "ESTADIO" and self.speed_idx != 3

    def cam_reset(self):
        self.cam_fallback = False
        self.cam_acc, self.cam_n = 0.0, 0

    def toggle_camera(self):
        """Tecla C. Menu: AUTO -> ESTADIO -> PERTO -> AUTO (gravado). Pausa da partida (com torcida):
        alterna a camera atual, grava a escolha e aplica na hora (re-warm aqui, no evento)."""
        if self.state == "menu":
            cur = self.camera_pref()
            nxt = CAMERA_MENU_CYCLE[(CAMERA_MENU_CYCLE.index(cur) + 1) % len(CAMERA_MENU_CYCLE)]
            try:
                prefs.set("camera", nxt) if nxt is not None else prefs.unset("camera")
            except Exception:  # noqa: BLE001
                pass
            return nxt
        nxt = "PERTO" if self.camera_mode() == "ESTADIO" else "ESTADIO"
        try:
            prefs.set("camera", nxt)
        except Exception:  # noqa: BLE001
            pass
        self.cam_reset()
        if self.career_match or self.crowd_venue is not None:
            self.warm_crowd(self.crowd_venue)
        return nxt

    def camera_label(self, menu=False):
        return "C: câmera " + CAMERA_LABELS[self.camera_pref() if menu else self.camera_mode()]

    def world_restore(self):
        """Fundo do mundo (ESTADIO): o campo inteiro so quando preciso (world_full); senao repinta do
        pitch_surf apenas os retangulos desenhados no quadro anterior (world_dirty)."""
        bg = self.pitch_surf
        if self.world_full:
            self.world.blit(bg, crowd.CAM_CROP.topleft, crowd.CAM_CROP)
            self.world_full = False
        elif self.world_dirty:
            self.world.blits([(bg, r, r) for r in self.world_dirty], False)
        self.world_dirty.clear()

    def world_mark(self):
        """Caixas (folgadas) de tudo que foi desenhado no mundo neste quadro: robos (halo 64x64, barra,
        seta/forca do humano, satelites), bola (glow, sombra, rastro) e particulas (linha/fumaca)."""
        d = self.world_dirty
        R = pygame.Rect
        for t in self.teams:
            for p in t.players:
                d.append(R(int(p.pos.x) - 40, int(p.pos.y) - 50, 80, 100))
        b = self.ball
        d.append(R(int(b.pos.x) - 30, int(b.pos.y) - 30, 60, 60))
        for q in self.trail:
            d.append(R(q[0] - 10, q[1] - 10, 20, 20))
        th = robot_art.TRAIL_SIZE // 2 + 1
        for p in self.trail_players:                    # B13: rastro dos robos (pontos vivos)
            pts, h = p.trail_pts, p.trail_h
            for i in range(p.trail_n):
                q = pts[(h - i) % robot_art.TRAIL_N]
                d.append(R(q[0] - th, q[1] - th, th * 2, th * 2))
        for p in self.fx:
            d.append(R(int(p[0]) - 24, int(p[1]) - 24, 48, 48))

    def cam_feed(self, ms):
        """LOD da camera: amostra do quadro em ESTADIO; media da janela > CAM_LOD_MS -> PERTO (uma vez)."""
        self.cam_acc += ms
        self.cam_n += 1
        if self.cam_n < CAM_LOD_WINDOW:
            return
        avg = self.cam_acc / self.cam_n
        self.cam_acc, self.cam_n = 0.0, 0
        if avg > CAM_LOD_MS and not self.cam_fallback:
            self.cam_fallback = True
            self.warm_crowd(self.crowd_venue)     # torcida PERTO (custo unico; nada por quadro depois)

    def crowd_on(self):
        """Torcida desenhada/reagindo agora: partida assistida, existe e nao esta em MAX."""
        return self.crowd is not None and self.speed_idx != 3

    def crowd_event(self, kind, team=None):
        """Hook do motor: so escreve no estado da torcida e toca o som do lance (nunca na simulacao nem
        no RNG global). Em MAX nada acontece."""
        if self.speed_idx == 3:
            return
        sfx.play(EVENT_SFX.get(kind))
        if self.crowd is not None:
            self.crowd.event(kind, team)

    def crowd_end(self):
        a, c = self.score
        self.crowd_event("end", None if a == c else (0 if a > c else 1))
        if not self.career_match and self.speed_idx != 3:   # amistoso: jingle (modo 1 = visao do humano)
            if self.mode == 1:
                sfx.result(a, c)
            elif a != c:
                sfx.result(1, 0)
            else:
                sfx.play("draw")

    def snd(self, sid):
        """Efeito sonoro de lance do motor (no-op em MAX e antes de sfx.init)."""
        if self.speed_idx != 3:
            sfx.play(sid)

    def music_track(self):
        """Trilha do quadro: menus/telas = "menu"; partida (inclusive pausa e fim) = "match"."""
        return "menu" if self.state in ("menu", "career", "robots", "campaign") else "match"

    def audio_key(self, key):
        """M (em qualquer tela), S/N (menu e pausa): som. True se a tecla foi usada."""
        if key == pygame.K_m:
            sfx.toggle_mute()
            return True
        if self.state == "menu" or (self.paused and self.state in ("kickoff", "play", "goal")):
            if key == pygame.K_s:
                sfx.cycle("sfx_vol")
                return True
            if key == pygame.K_n:
                sfx.cycle("music_vol")
                return True
        return False

    def audio_label(self):
        return "  |  ".join(sfx.labels())

    def draw_fx(self, scr):
        now = time.perf_counter()
        dt = 0.0 if self.paused else max(0.0, min(now - self.fx_last, 0.05))   # relogio voltando nao "rejuvenesce" particulas
        self.fx_last = now
        if not self.fx:
            self.fx_amb = 0
            return
        keep = []
        amb = 0
        puffs = self.puffs
        for p in self.fx:
            p[4] -= dt
            if p[4] <= 0:
                continue
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.94
            p[3] *= 0.94
            keep.append(p)
            if len(p) > 9 and p[9]:
                amb += 1
            f = p[4] / p[5]
            x, y = int(p[0]), int(p[1])
            st = p[8] if len(p) > 8 else None
            if st is not None and puffs is not None:     # fumaca/poeira: sprite pronto (cresce e some)
                img = robot_art.puff_img(puffs, st, p[7], f)
                hw = img.get_width() >> 1
                scr.blit(img, (x - hw, y - hw))
                continue
            col = scale_color(p[6], f)
            pygame.draw.line(scr, col, (x, y), (int(x - p[2] * 0.03), int(y - p[3] * 0.03)), 2)
            pygame.draw.circle(scr, col, (x, y), max(1, int(p[7] * f)))
        self.fx = keep
        self.fx_amb = amb

    # ------------------------------------------------------------- drawing
    def font(self, size):
        f = self.fonts.get(size)
        if f is None:
            f = self.fonts[size] = pygame.font.Font(None, size)
        return f

    def text_img(self, s, size, color):
        key = (s, size, color)
        cache = self.text_cache
        img = cache.get(key)
        if img is None:
            img = self.font(size).render(s, True, color)
            cache[key] = img
            if len(cache) > TEXT_CACHE_MAX:
                cache.popitem(last=False)
        else:
            cache.move_to_end(key)
        return img

    def text(self, s, size, color, center=None, topleft=None, shadow=True,
             midleft=None, midright=None):
        color = tuple(color)
        img = self.text_img(s, size, color)
        r = img.get_rect()
        if center:
            r.center = center
        elif midleft:
            r.midleft = midleft
        elif midright:
            r.midright = midright
        else:
            r.topleft = topleft
        if shadow:
            self.screen.blit(self.text_img(s, size, (0, 0, 0)), r.move(2, 2))
        self.screen.blit(img, r)

    def build_arena(self):
        """Arena tecnologica pre-renderizada: piso escuro em gradiente, grade neon, linhas holograficas."""
        s = pygame.Surface((W, H)).convert()
        for y in range(H):
            t = y / H
            pygame.draw.line(s, (int(5 + 6 * t), int(8 + 9 * t), int(20 + 14 * t)), (0, y), (W, y))
        for y in range(PITCH.top, PITCH.bottom):
            t = (y - PITCH.top) / PITCH.h
            pygame.draw.line(s, (int(16 - 6 * t), int(30 - 11 * t), int(58 - 18 * t)),
                             (PITCH.left, y), (PITCH.right, y))
        layer = pygame.Surface((W, H), pygame.SRCALPHA)
        n = 14
        sw = PITCH.w / n
        for i in range(1, n, 2):
            pygame.draw.rect(layer, (255, 255, 255, 7), (PITCH.left + i * sw, PITCH.top, math.ceil(sw), PITCH.h))
        for x in range(PITCH.left, PITCH.right + 1, 40):
            pygame.draw.line(layer, (0, 200, 255, 30), (x, PITCH.top), (x, PITCH.bottom))
        for y in range(PITCH.top, PITCH.bottom + 1, 40):
            pygame.draw.line(layer, (0, 200, 255, 30), (PITCH.left, y), (PITCH.right, y))
        s.blit(layer, (0, 0))
        # redes dos gols
        for side in (0, 1):
            gx = PITCH.left - GOAL_DEPTH if side == 0 else PITCH.right
            net = pygame.Rect(gx, CY - GOAL_HALF, GOAL_DEPTH, GOAL_HALF * 2)
            pygame.draw.rect(s, (6, 14, 28), net)
            for yy in range(net.top, net.bottom, 10):
                pygame.draw.line(s, (50, 120, 160), (net.left, yy), (net.right, yy), 1)
            for xx in range(net.left, net.right, 10):
                pygame.draw.line(s, (50, 120, 160), (xx, net.top), (xx, net.bottom), 1)
        # linhas holograficas: 3 passes (larga/fraca, media, nucleo)
        for width, col in ((9, (0, 170, 255, 36)), (5, (0, 215, 255, 100)), (2, (215, 255, 255, 255))):
            layer.fill((0, 0, 0, 0))
            pygame.draw.rect(layer, col, PITCH, width)
            pygame.draw.line(layer, col, (CX, PITCH.top), (CX, PITCH.bottom), width)
            pygame.draw.circle(layer, col, (CX, CY), 70, width)
            pygame.draw.circle(layer, col, (CX, CY), 2 + width // 2)
            for side in (0, 1):
                big_x = PITCH.left if side == 0 else PITCH.right - 150
                small_x = PITCH.left if side == 0 else PITCH.right - 55
                pygame.draw.rect(layer, col, (big_x, CY - 150, 150, 300), width)
                pygame.draw.rect(layer, col, (small_x, CY - 85, 55, 170), width)
                spot_x = PITCH.left + 105 if side == 0 else PITCH.right - 105
                pygame.draw.circle(layer, col, (spot_x, CY), 2 + width // 2)
                gx = PITCH.left - GOAL_DEPTH if side == 0 else PITCH.right
                pygame.draw.rect(layer, col, (gx, CY - GOAL_HALF, GOAL_DEPTH, GOAL_HALF * 2), width)
            s.blit(layer, (0, 0))
        for side in (0, 1):                         # traves com glow
            line_x = PITCH.left if side == 0 else PITCH.right
            for yy in (CY - GOAL_HALF, CY + GOAL_HALF):
                pygame.draw.circle(s, (0, 90, 150), (line_x, yy), 10)
                pygame.draw.circle(s, (90, 210, 255), (line_x, yy), 7)
                pygame.draw.circle(s, (255, 255, 255), (line_x, yy), 4)
        return s

    def build_glows(self):
        """Sprites de glow (aditivos, fundo preto) para a bola."""
        size = 56
        c = size // 2
        s = pygame.Surface((size, size))
        for r in range(c, 0, -1):
            k = (1 - r / c) ** 2
            pygame.draw.circle(s, (int(70 * k), int(150 * k), int(190 * k)), (c, c), r)
        return {"ball": s.convert()}

    def build_hud_panel(self):
        s = pygame.Surface((W, 78), pygame.SRCALPHA)
        for y in range(76):
            pygame.draw.line(s, (6, 14, 30, int(215 - 50 * y / 76)), (0, y), (W, y))
        pygame.draw.line(s, (0, 120, 160, 120), (0, 76), (W, 76), 4)
        pygame.draw.line(s, (0, 230, 255, 255), (0, 76), (W, 76), 2)
        return s.convert_alpha()

    def build_banner_veil(self):
        s = pygame.Surface((W, 150), pygame.SRCALPHA)
        s.fill((2, 8, 20, 165))
        pygame.draw.line(s, (0, 230, 255, 255), (0, 0), (W, 0), 2)
        pygame.draw.line(s, (0, 230, 255, 255), (0, 149), (W, 149), 2)
        return s.convert_alpha()

    def build_menu_bg(self):
        """Arena + veu escuro ja compostos (o menu so faz um blit)."""
        s = self.pitch_surf.copy()
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((2, 6, 16, 165))
        s.blit(veil, (0, 0))
        return s.convert()

    # robos ------------------------------------------------------------
    def build_robot_sprite(self, chassis, led, gk, low):
        """Aspirador visto de cima (sem cache). A arte fica em robot_art.py."""
        return robot_art.build_robot_sprite(chassis, led, gk, low)

    def sprite_key(self, t, p):
        return robot_art.sprite_key(t, p)

    def robot_sprite(self, rb):
        """Sprite (cacheado) de um robo da garagem, com a cor de pintura dele."""
        return robot_art.robot_sprite(self.sprites, rb)

    def get_sprite(self, ch, led, gk, low=False):
        return robot_art.get_sprite(self.sprites, ch, led, gk, low)

    def warm_sprites(self):
        robot_art.warm_sprites(self.sprites, self.teams)
        self.puffs = robot_art.get_puffs(self.sprites)
        self.trail_players = [p for t in self.teams for p in t.players if p.art.trail is not None]

    def draw_robot_trails(self, scr):
        """B13: rastro cosmetico atras dos robos em movimento. Pool fixo de TRAIL_N pontos por robo
        (amostrado no relogio real do desenho), imagens prontas (build_trail); congela na pausa."""
        now = time.perf_counter()
        n_max = robot_art.TRAIL_N
        half = robot_art.TRAIL_SIZE // 2
        paused = self.paused
        for p in self.trail_players:
            pts = p.trail_pts
            if not paused and now >= p.trail_next:
                p.trail_next = now + robot_art.TRAIL_DT
                if p.vel.length_squared() > robot_art.TRAIL_SPEED2:
                    h = p.trail_h = (p.trail_h + 1) % n_max
                    q = pts[h]
                    q[0] = int(p.pos.x)
                    q[1] = int(p.pos.y)
                    if p.trail_n < n_max:
                        p.trail_n += 1
                elif p.trail_n:
                    p.trail_n -= 1
            n = p.trail_n
            if n:
                imgs, h = p.art.trail, p.trail_h
                for i in range(n - 1, -1, -1):            # do mais velho (menor) para o mais novo
                    q = pts[(h - i) % n_max]
                    scr.blit(imgs[i], (q[0] - half, q[1] - half))

    def draw(self):
        scr = self.screen
        if self.state == "career":
            return self.career_ui.draw()
        if self.state == "robots":
            ui = getattr(self, "robots_ui", None)
            if ui is not None:
                return ui.draw()
            self.state = "menu"
        if self.state == "campaign":
            ui = getattr(self, "campaign_ui", None)
            if ui is not None:
                return ui.draw()
            self.state = "menu"
        if self.state == "menu":
            scr.blit(self.menu_bg, (0, 0))
            return self.draw_menu()
        cr = self.crowd                                 # amistoso: so existe se o menu pediu (A8)
        cam = False
        if cr is not None and self.speed_idx == 3:
            if cr.b.camera == "ESTADIO":                # MAX na camera ESTADIO: o minimo (campo cheio)
                scr.blit(self.pitch_surf, (0, 0))
            else:
                scr.blit(cr.b.static, (0, 0))           # MAX: so a arena composta (1 blit), sem extras
            cr = None
        elif cr is None:
            scr.blit(self.pitch_surf, (0, 0))
        else:
            t_draw = time.perf_counter()
            cam = cr.b.camera == "ESTADIO"
            if cam:                                     # ESTADIO: so as arquibancadas (o mundo cobre o meio)
                st = cr.b.static
                for r in crowd.CAM_STRIPS:
                    scr.blit(st, r, r)
            else:
                scr.blit(cr.b.static, (0, 0))
            cr.draw(scr, self.paused)

        if cam:                                         # ESTADIO: o mundo vai para a Surface pre-alocada
            self.world_restore()
            self.screen = self.world
        try:
            ws = self.screen
            b = self.ball
            pygame.draw.ellipse(ws, (3, 8, 18), (b.pos.x - BR + 2, b.pos.y - BR + 5, BR * 2, BR * 1.4))
            if self.trail_players and self.speed_idx != 3:   # B13: rastros sob todos os robos (nada em MAX)
                self.draw_robot_trails(ws)
            for t in self.teams:
                for p in t.players:
                    self.draw_player(t, p)
            self.draw_ball()
            self.draw_fx(ws)
        finally:
            self.screen = scr
        if cam:                                         # escala com destino pronto (zero Surface por quadro)
            self.world_mark()
            self.cam_scale(self.world_src, crowd.CAM_SIZE, self.world_dst)
            scr.blit(self.world_dst, crowd.CAM_POS)
        if cr is not None:
            cr.draw_over(scr, self.paused)
        self.draw_hud()

        if self.paused:
            self.banner("PAUSADO", "P para continuar" + ("" if self.career_match else "  |  ESC para o menu"))
            if self.career_match or self.crowd_venue is not None:
                self.draw_crowd_option()
            else:
                self.draw_audio_option()
        elif self.state == "kickoff":
            self.banner("PREPARAR!" if not self.career_match else "BOLA ROLANDO!", None)
        elif self.state == "goal":
            col = self.teams[self.scorer].color
            ev = self.events[-1]
            who = ev["name"] + (" (contra)" if ev["own"] else "") if ev["name"] else self.teams[self.scorer].name
            self.banner("GOOOOL!", who + "  " + str(ev["min"]) + "'", col)
        elif self.state == "over":
            a, c = self.score
            if a == c:
                title, col = "EMPATE!", (255, 255, 255)
            else:
                w = self.teams[0 if a > c else 1]
                title, col = "VITÓRIA: " + w.name, w.color
            if self.career_match:
                self.banner(title, "ENTER ou clique = continuar", col)
                self.draw_scorers()
            else:
                self.banner(title, "ENTER = jogar de novo   |   ESC = menu", col)
        if cr is not None and not self.paused:          # LOD automatico: tempo do quadro de partida
            ms = (time.perf_counter() - t_draw) * 1000
            self.last_draw_ms = ms
            cr.lod_feed(ms)
            if cam:
                self.cam_feed(ms)

    def draw_crowd_option(self):
        """Pausa da partida assistida: opcao TORCIDA (tecla T), logo abaixo da faixa do PAUSADO."""
        for lab, y in ((self.crowd_label(), CY + 100), (self.camera_label(), CY + 146), (self.audio_label(), CY + 192)):
            img = self.text_img(lab, 28, (255, 230, 120))
            r = img.get_rect(center=(W // 2, y))
            pygame.draw.rect(self.screen, (2, 8, 20), r.inflate(28, 14), border_radius=10)
            pygame.draw.rect(self.screen, (0, 200, 240), r.inflate(28, 14), 2, border_radius=10)
            self.screen.blit(img, r)

    def draw_audio_option(self):
        """Pausa sem torcida: so a linha do som (M / S / N)."""
        img = self.text_img(self.audio_label(), 28, (255, 230, 120))
        r = img.get_rect(center=(W // 2, CY + 100))
        pygame.draw.rect(self.screen, (2, 8, 20), r.inflate(28, 14), border_radius=10)
        pygame.draw.rect(self.screen, (0, 200, 240), r.inflate(28, 14), 2, border_radius=10)
        self.screen.blit(img, r)

    def draw_scorers(self):
        for team in (0, 1):
            x = W // 2 - 250 if team == 0 else W // 2 + 250
            evs = [e for e in self.events if e["team"] == team]
            for k, e in enumerate(evs[:6]):
                txt = "%s %d'%s" % (e["name"] or "?", e["min"], " (contra)" if e["own"] else "")
                self.text(txt, 28, (240, 240, 240), center=(x, CY + 105 + k * 26))

    def draw_player(self, t, p):
        """Robo em camadas (A9-A11): halo aditivo pulsando, baixo/cima por direcao, escovas girando,
        corpo (quadro low piscando), extras por pygame.draw. So blits de Surfaces prontas (p.art)."""
        scr = self.screen
        pos = (int(p.pos.x), int(p.pos.y))
        art = p.art
        if art is None:                                      # fora do warm (nao deveria): aquece 1 vez
            art = p.art = robot_art.warm_player(self.sprites, self.sprite_key(t, p), p.vis)
        led = art.led
        now = time.perf_counter()
        bat = p.bat
        low = bat < LOW_BAT and int(now * 5) % 2 == 0
        d = p.vdir = robot_art.face_dir(p.face, p.vdir)
        x0, y0 = pos[0] - 32, pos[1] - 32
        if bat < LOW_BAT:
            lvl = robot_art.HALO_LOW if low else 0
        else:
            lvl = int((math.sin(now * 3.1 + p.idx * 1.7 + t.idx) + 1.0) * 1.999)
        scr.blit(art.halo[lvl], (x0, y0), special_flags=pygame.BLEND_RGB_ADD)
        if self.arena == "goleiro_gigante" and t.idx == 1 and p.role == "GK":   # alcance do goleiro gigante
            pygame.draw.circle(scr, (255, 150, 90), pos, PR + BR + 12 + ARENA_GK_REACH, 2)
        u = art.atlas.under[d]
        if u is not None:
            scr.blit(u[0], (pos[0] + u[1], pos[1] + u[2]))
        moving = p.vel.length_squared() > 400
        if art.turbina and moving and not low:               # chama/ar da turbina (2 circulos)
            jx, jy = art.jet_off[d]
            k = int(now * 22) % 2
            pygame.draw.circle(scr, (255, 150, 60) if k else (255, 236, 150), (pos[0] + jx, pos[1] + jy), 4 - k)
            pygame.draw.circle(scr, (255, 252, 230), (pos[0] + jx, pos[1] + jy), 1)
        if bat >= CRIT_BAT:                                  # escovas (somem com bateria critica)
            fr = art.brushes[int(now * (22 if moving else 9) + p.idx) % robot_art.BRUSH_FRAMES]
            for bx, by in art.brush_off[d]:
                scr.blit(fr, (pos[0] + bx, pos[1] + by))
        scr.blit(art.low if low else art.body, (x0, y0))
        o = art.atlas.over[d]
        if o is not None:
            scr.blit(o[0], (pos[0] + o[1], pos[1] + o[2]))
        if art.orbital:                                      # satelites orbitando (2 circulos)
            a = now * 2.6 + p.idx
            ca, sa = math.cos(a) * robot_art.ORBIT_R, math.sin(a) * robot_art.ORBIT_R
            sc = scale_color(led, 0.45) if low else led
            for sx in (1, -1):
                q = (int(pos[0] + ca * sx), int(pos[1] + sa * sx))
                pygame.draw.circle(scr, (12, 16, 24), q, 4)
                pygame.draw.circle(scr, sc, q, 3)
                pygame.draw.circle(scr, (245, 252, 255), q, 1)
        if art.radar is not None:                            # varredura do radar
            rx, ry = art.radar_off[d]
            a = now * 6.5
            c0 = (pos[0] + rx, pos[1] + ry)
            pygame.draw.line(scr, art.radar, c0, (int(c0[0] + math.cos(a) * 4), int(c0[1] + math.sin(a) * 4)), 1)
            pygame.draw.circle(scr, (240, 250, 255), c0, 1)
        if art.modulo is not None:                           # luzinha do modulo
            mx, my = art.mod_off[d]
            on = int(now * 2.5 + p.idx) % 2 == 0
            pygame.draw.circle(scr, art.modulo if on else scale_color(art.modulo, 0.35), (pos[0] + mx, pos[1] + my), 1)
        eye = p.pos + p.face * (PR - 6)                      # olho/sensor na direcao do rosto
        ex, ey = int(eye.x), int(eye.y)
        pygame.draw.circle(scr, (10, 14, 20), (ex, ey), 5)
        pygame.draw.circle(scr, (235, 250, 255), (ex, ey), 3)
        pygame.draw.circle(scr, led, (ex, ey), 1)
        self.robot_fx(p, art, now)
        if self.sk_on and self.speed_idx != 3 and (p.sk_fx is not None or p.sk_zap is not None
                                                   or p.sk_ev is not None or p.sk_badge):
            self.draw_skill_fx(scr, p, pos, now)
        bat = p.bat
        if bat < 0.98 or p.vel.length_squared() > 625:       # barra de bateria 22x4
            x, y = pos[0] - 12, pos[1] - art.rad - 11
            pygame.draw.rect(scr, (6, 10, 18), (x, y, 24, 6))
            if bat >= 0.5:
                bc = (70, 230, 110)
            elif bat >= 0.25:
                bc = (255, 215, 60)
            else:
                bc = (255, 70, 60)
            if bat >= 0.25 or int(now * 5) % 2 == 0:
                pygame.draw.rect(scr, bc, (x + 1, y + 1, int(22 * bat), 4))
        if t.human and p is t.ctrl and self.state != "over":
            pygame.draw.circle(scr, (255, 255, 255), pos, PR + 4, 2)
            tip = (pos[0], pos[1] - PR - 14)
            pygame.draw.polygon(scr, (255, 230, 60),
                                [tip, (tip[0] - 7, tip[1] - 11), (tip[0] + 7, tip[1] - 11)])
            if t.human.charge > 0:
                x, y = pos[0] - 20, pos[1] + PR + 8
                pygame.draw.rect(scr, (0, 0, 0), (x - 1, y - 1, 42, 8))
                c = t.human.charge
                pygame.draw.rect(scr, (int(80 + 175 * c), int(230 - 150 * c), 60), (x, y, int(40 * c), 6))

    # ------------------------------------------------------------- FX das skills (B7)
    def warm_skill_fx(self):
        """Pre-render (inicio da partida, nunca por quadro) dos letreiros das skills; o resto e pygame.draw."""
        self.sk_imgs = {"dash": self.text_img("ZOOM!", 22, (150, 240, 255)),
                        "gloves": self.text_img("!!", 26, (255, 235, 90)),
                        "captain": self.text_img("C", 16, (20, 20, 30)),
                        "slipper": self.text_img("PLAFT!", 22, (255, 150, 150)),
                        "evade": self.text_img("DRIBLE!", 20, (200, 255, 255)),
                        "launch": self.text_img("LANÇOU!", 20, (255, 225, 140)),
                        "stun": self.text_img("ZZT!", 20, (255, 250, 140))}

    def draw_skill_fx(self, scr, p, pos, now):
        """FX da skill ativa do robo (so com sk_on, fora do MAX): so pygame.draw e blits de imagens
        prontas (sk_imgs); faiscas no fx_rng (fx_emit). Nunca toca a simulacao nem o random global."""
        x, y = pos
        kind = p.sk_fx
        if kind is not None:
            col = SK_FX_COLORS.get(kind, (255, 255, 255))
            ph = now * 8.0 + p.idx
            if kind == "dash" or kind == "wheel":            # imagens residuais + letreiro ZOOM
                v = p.vel
                if v.length_squared() > 100:
                    back = v * -0.035
                    for k in (3, 2, 1):
                        q = (int(x + back.x * k), int(y + back.y * k))
                        pygame.draw.circle(scr, scale_color(col, 0.25 + 0.15 * (3 - k)), q, PR - 2 * k, 2)
                if kind == "dash" and self.sk_t - p.sk_fx_t < 0.6:
                    img = self.sk_imgs["dash"]
                    scr.blit(img, (x - (img.get_width() >> 1), y - 44))
            elif kind == "magnet":                          # arcos concentricos azuis
                for k in range(3):
                    r = 18 + int((ph * 3 + k * 8) % 24)
                    pygame.draw.circle(scr, scale_color(col, 1.0 - (r - 18) / 26), pos, r, 1)
            elif kind in ("shield", "gold_ring", "tape"):   # anel de escudo
                r = PR + 7 + int(math.sin(ph) * 2)
                pygame.draw.circle(scr, scale_color(col, 0.45), pos, r + 2, 1)
                pygame.draw.circle(scr, col, pos, r, 2)
            elif kind == "overclock":                       # halo vermelho pulsando
                r = PR + 6 + int((math.sin(ph * 1.5) + 1) * 3)
                pygame.draw.circle(scr, col, pos, r, 2)
                pygame.draw.circle(scr, scale_color(col, 0.4), pos, r + 4, 1)
            elif kind == "heal":                            # cruz verde
                cy = y - PR - 16
                pygame.draw.rect(scr, (10, 40, 18), (x - 6, cy - 2, 12, 5))
                pygame.draw.rect(scr, (10, 40, 18), (x - 2, cy - 6, 5, 13))
                pygame.draw.rect(scr, col, (x - 5, cy - 1, 10, 3))
                pygame.draw.rect(scr, col, (x - 1, cy - 5, 3, 10))
            elif kind == "spin":                            # anel girando
                a = ph * 1.4
                r = PR + 6
                rect = (x - r, y - r, 2 * r, 2 * r)
                pygame.draw.arc(scr, col, rect, a, a + 2.2, 2)
                pygame.draw.arc(scr, col, rect, a + math.pi, a + math.pi + 2.2, 2)
            elif kind == "gloves":                          # luvas piscando "!!"
                if int(now * 8) % 2 == 0:
                    img = self.sk_imgs["gloves"]
                    scr.blit(img, (x - (img.get_width() >> 1), y - 44))
                pygame.draw.circle(scr, col, pos, PR + 5, 2)
            elif kind == "sparks":                          # faiscas laranja (fx_rng)
                pygame.draw.circle(scr, scale_color(col, 0.6), pos, PR + 5, 1)
                if now >= p.sk_fx_next:
                    p.sk_fx_next = now + 0.12
                    self.fx_emit("sk_spark", p.pos)
            elif kind == "glow" or kind == "curve":         # brilho no sensor
                e = p.pos + p.face * (PR - 6)
                pygame.draw.circle(scr, col, (int(e.x), int(e.y)), 4 + int(now * 10) % 2, 1)
            elif kind == "slipper":
                img = self.sk_imgs["slipper"]
                scr.blit(img, (x - (img.get_width() >> 1), y - 44))
        zp = p.sk_zap
        if zp is not None:                                  # Choque: raio curto ate o desarmado
            o, until = zp
            if self.sk_t >= until or self.state != "play":
                p.sk_zap = None
            else:
                ox, oy = int(o.pos.x), int(o.pos.y)
                mx, my = (x + ox) >> 1, (y + oy) >> 1
                j = 6 if int(now * 20) % 2 else -6
                pts = [(x, y), (mx + j, my - j), (mx - j, my + j), (ox, oy)]
                pygame.draw.lines(scr, (120, 90, 20), False, pts, 4)
                pygame.draw.lines(scr, SK_FX_COLORS["zap"], False, pts, 2)
                pygame.draw.circle(scr, SK_FX_COLORS["zap"], (ox, oy), PR + 3, 1)
                if now >= p.sk_fx_next:
                    p.sk_fx_next = now + 0.1
                    self.fx_emit("sk_zap", o.pos)
        ev = p.sk_ev
        if ev is not None:                                  # FX de evento: a skill mudou o lance agora
            kind, until = ev
            if self.sk_t >= until or self.state != "play":
                p.sk_ev = None
            else:
                img = self.sk_imgs.get(kind)
                if img is not None:
                    scr.blit(img, (x - (img.get_width() >> 1), y - 46))
                if kind == "stun":                          # estrelinhas girando na cabeca
                    a = now * 9.0
                    for k in range(3):
                        ang = a + k * 2.094
                        pygame.draw.circle(scr, SK_FX_COLORS["zap"],
                                           (int(x + math.cos(ang) * 11), int(y - 4 + math.sin(ang) * 5)), 2)
                elif kind == "evade":
                    r = PR + 8
                    pygame.draw.arc(scr, SK_FX_COLORS["spin"], (x - r, y - r, 2 * r, 2 * r), now * 12, now * 12 + 4.0, 2)
        if p.sk_badge:                                      # Lider: faixa de capitao
            bx, by = x + PR - 2, y - PR + 2
            pygame.draw.circle(scr, SK_FX_COLORS["captain"], (bx, by), 6)
            img = self.sk_imgs["captain"]
            scr.blit(img, (bx - (img.get_width() >> 1), by - (img.get_height() >> 1)))

    def draw_ball(self):
        b, scr = self.ball, self.screen
        pos = (int(b.pos.x), int(b.pos.y))
        tr = self.trail
        if self.paused:
            pass
        elif b.vel.length_squared() > 350 * 350 or (b.curve and b.owner is None):
            tr.append(pos)
        elif tr:
            tr.popleft()
        n = len(tr)
        if b.air and self.sk_on:                         # Lancador: bola por cima (sombra + bola alta)
            pygame.draw.ellipse(scr, (18, 36, 22), (pos[0] - 7, pos[1] - 3, 14, 6))
            pos = (pos[0], pos[1] - 6 - int(10 * min(1.0, b.air)))
        tc = SK_FX_COLORS["curve"] if b.curve and self.sk_on else (120, 230, 255)   # rastro curvo magenta
        for i, q in enumerate(tr):
            f = (i + 1) / (n + 1)
            pygame.draw.circle(scr, scale_color(tc, f * 0.8), q, max(1, int(BR * f * 0.8)))
        scr.blit(self.glows["ball"], (pos[0] - 28, pos[1] - 28), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(scr, (250, 250, 250), pos, BR)
        a = b.roll
        for k in range(3):
            ang = a + k * 2.094
            px, py = pos[0] + math.cos(ang) * 4, pos[1] + math.sin(ang) * 4
            pygame.draw.circle(scr, (30, 30, 30), (int(px), int(py)), 2)
        pygame.draw.circle(scr, (20, 30, 40), pos, BR, 2)

    def draw_hud(self):
        scr = self.screen
        scr.blit(self.hud_panel, (0, 0))
        t0, t1 = self.teams
        self.text(t0.name, 44, led_color(t0.color), center=(W // 2 - 270, 36))
        self.text(t1.name, 44, led_color(t1.color), center=(W // 2 + 270, 36))
        self.text("%d  x  %d" % tuple(self.score), 64, (255, 255, 255), center=(W // 2, 30))
        if self.career_match:
            self.text("%d'" % self.minute(), 30, (255, 230, 120), center=(W // 2, 62))
            if self.arena is not None:                     # Torre do Po: modificador da arena (texto em cache)
                self.text(ARENA_LABELS[self.arena], 22, (255, 150, 90), center=(W // 2 + 120, 62))
            self.draw_speed_buttons()
            return
        secs = int(math.ceil(max(0, self.time_left)))
        self.text("%d:%02d" % (secs // 60, secs % 60), 30, (255, 230, 120), center=(W // 2, 62))
        if self.mode == 1:
            hint = "WASD / Setas: mover   |   ESPAÇO (segure): chutar   |   SHIFT / X: passar   |   P: pausa"
        else:
            hint = "J1: WASD + ESPAÇO chuta + SHIFT passa   |   J2: Setas + ENTER chuta + SHIFT DIR passa"
        self.text(hint, 24, (190, 225, 235), center=(W // 2, H - 22), shadow=False)

    def draw_speed_buttons(self):
        self.text("Velocidade (1-4):", 24, (190, 225, 235), midright=(W - 342, H - 22), shadow=False)
        for i, (r, lab) in enumerate(zip(self.speed_rects(), ["1x", "2x", "4x", "MAX"])):
            on = i == self.speed_idx
            pygame.draw.rect(self.screen, (0, 120, 165) if on else (12, 30, 54), r, border_radius=6)
            pygame.draw.rect(self.screen, (0, 230, 255) if on else (70, 130, 160), r, 2, border_radius=6)
            self.text(lab, 24, (255, 255, 255), center=r.center, shadow=False)
        self.text("P: pausa", 24, (190, 225, 235), midleft=(24, H - 22), shadow=False)

    def banner(self, title, sub, color=(255, 255, 255)):
        self.screen.blit(self.banner_veil, (0, CY - 75))
        self.text(title, 84, led_color(color), center=(W // 2, CY - (15 if sub else 0)))
        if sub:
            self.text(sub, 32, (230, 240, 245), center=(W // 2, CY + 42))

    def draw_menu(self):
        scr = self.screen
        cx = W // 2
        self.text("COPA ASPIRADOR", 130, (0, 120, 170), center=(cx + 3, 193), shadow=False)
        self.text("COPA ASPIRADOR", 130, (225, 252, 255), center=(cx, 190), shadow=False)
        self.text("robôs aspiradores jogam bola e ninguém varre a sala", 36, (120, 225, 245), center=(cx, 275))
        labels = [("1 - AMISTOSO", "você contra a CPU"), ("2 - AMISTOSO", "J1 contra J2, mesmo teclado"),
                  ("3 - NOVA CARREIRA", "gerente: elenco, mercado, ligas")]
        mx, my = pygame.mouse.get_pos()
        for r, (a, c) in zip(self.menu_btns, labels):
            hover = r.collidepoint(mx, my)
            pygame.draw.rect(scr, (0, 100, 140) if hover else (10, 40, 72), r, border_radius=14)
            pygame.draw.rect(scr, (0, 230, 255) if hover else (0, 150, 190), r, 3, border_radius=14)
            self.text(a, 34, (255, 255, 255), center=(r.centerx, r.centery - 14))
            self.text(c, 24, (190, 235, 245), center=(r.centerx, r.centery + 22), shadow=False)
        if self.has_save:
            r = self.continue_btn
            hover = r.collidepoint(mx, my)
            pygame.draw.rect(scr, (200, 150, 30) if hover else (160, 115, 20), r, border_radius=14)
            pygame.draw.rect(scr, (255, 240, 200), r, 3, border_radius=14)
            self.text("4 - CONTINUAR CARREIRA", 31, (255, 255, 255), center=r.center)
        r = self.robots_btn()
        hover = r.collidepoint(mx, my)
        pygame.draw.rect(scr, (0, 130, 110) if hover else (6, 80, 76), r, border_radius=14)
        pygame.draw.rect(scr, (90, 255, 210) if hover else (40, 200, 170), r, 3, border_radius=14)
        self.text("5 - MODO ROBÔS", 32, (255, 255, 255), center=(r.centerx, r.centery - 12))
        self.text("continuar" if self.robots_status == "ok" else "equipe de robôs, peças e liga", 22,
                  (190, 245, 232), center=(r.centerx, r.centery + 18), shadow=False)
        r = self.campaign_btn()
        hover = r.collidepoint(mx, my)
        pygame.draw.rect(scr, (110, 70, 160) if hover else (56, 36, 100), r, border_radius=14)
        pygame.draw.rect(scr, (210, 170, 255) if hover else (150, 110, 220), r, 3, border_radius=14)
        self.text("6 - CAMPANHA", 32, (255, 255, 255), center=(r.centerx, r.centery - 12))
        self.text("continuar" if self.campaign_status == "ok" else "a história de Téo e do Zé Poeira", 22,
                  (225, 210, 250), center=(r.centerx, r.centery + 18), shadow=False)
        self.text("clique ou aperte 1 / 2 / 3 / 4 / 5 / 6" if self.has_save else "clique ou aperte 1 / 2 / 3 / 5 / 6",
                  28, (200, 225, 235), center=(cx, 640))
        a, c = "F11: tela cheia  |  " + self.crowd_label(), "  |  " + self.camera_label(menu=True)
        col = (120, 160, 185)
        wa, wc = self.text_img(a, 22, col).get_width(), self.text_img(c, 22, col).get_width()
        x0 = cx - (wa + wc) // 2
        self.text(a, 22, col, midleft=(x0, 664), shadow=False)
        self.text(c, 22, col, midleft=(x0 + wa, 664), shadow=False)
        self.text(self.audio_label(), 22, col, center=(cx, 688), shadow=False)


async def main():
    sfx.pre_init()
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Copa Aspirador")
    clock = pygame.time.Clock()
    game = Game(screen)
    sfx.init()                                  # depois do Game: o new_match do construtor nao apita
    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 20)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            game.handle_event(e)
        game.update(dt)
        sfx.tick(game.music_track())
        game.draw()
        pygame.display.flip()
        await asyncio.sleep(0)
