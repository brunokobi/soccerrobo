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

import robots
from career import Career
from career_ui import CareerUI

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
TEXT_CACHE_MAX = 300
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


# (quantidade, velocidade min/max, vida min/max, cor, tamanho)
FX_KINDS = {
    "tackle": (6, 90, 230, 0.25, 0.5, (255, 235, 150), 3),
    "kick":   (8, 120, 320, 0.2, 0.45, (170, 245, 255), 3),
    "bump":   (4, 60, 160, 0.2, 0.4, (255, 170, 80), 2),
    "goal":   (40, 100, 420, 0.6, 1.2, None, 4),
    "wall":   (4, 50, 150, 0.2, 0.35, (150, 200, 255), 2),
}


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


class Player:
    def __init__(self, team, idx, role, fx, fy, name="", ovr=65.0, chassis=None, seed=None,
                 attrs=None, tuning=None, pid=None, paint=None):
        self.team = team
        self.idx = idx
        self.role = role
        self.name = name
        self.chassis = chassis or robots.ROLE_CHASSIS[role]
        self.pid = pid                           # id do robo no modo robos (vai no evento de gol)
        self.paint = tuple(paint[:3]) if paint else None   # pintura = cor do LED
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
                extra = dict(attrs=e["attrs"], pid=e.get("pid"), paint=e.get("paint"))
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
        self.sprites = {}
        self.speed_idx = 0
        self.pitch_surf = self.build_arena()
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
        self.continue_btn = pygame.Rect(W // 2 - 160, 450, 320, 70)
        self.career_match = False
        self.match_time = MATCH_TIME
        self.speed_idx = 0
        self.events = []
        self.last_owner = None
        self.has_save = Career.has_save()
        self.match_sink = None                    # (return_state, fn) quando a partida vem de outro modo (robos)
        self.career_ui = CareerUI(self)
        self.new_match(1)
        self.state = "menu"

    # ------------------------------------------------------------------ setup
    def new_match(self, mode):
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
        self.speed_idx = 0
        self.match_time = self.time_left = MATCH_TIME
        self.events = []
        self.last_owner = None
        self.ball = Ball()
        self.paused = False
        self.reset_fx()
        self.kickoff(0)

    def start_career_match(self, home, away):
        """Partida automática (CPU x CPU) do modo carreira. home/away = match_cfg()."""
        self.match_sink = None
        self._begin_match(home, away)

    def start_robot_match(self, home, away, on_done, tuning=robots.TUNING_ROBOTS):
        """Partida automática do modo robôs. home/away = {"name","color","squad":[5 dicts]}.

        Ao terminar chama on_done(score, events) e volta ao estado "robots".
        """
        self._begin_match(home, away, tuning)
        self.match_sink = ("robots", on_done)

    def _begin_match(self, home, away, tuning=None):
        self.mode = 0
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
        self.reset_fx()
        self.state = "kickoff"
        self.kickoff(0)

    def finish_career_match(self):
        self.career_match = False
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
        b.pos = V(CX, CY)
        b.vel = V()
        kicker = self.teams[team_idx].players[4]
        kicker.pos = V(CX - self.teams[team_idx].dir * PR, CY)
        b.owner = kicker
        self.state = "kickoff"
        self.timer = 1.6

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
        if self.state == "career":
            return self.career_ui.handle_event(e)
        if self.state == "robots":
            ui = getattr(self, "robots_ui", None)
            if ui is not None:
                return ui.handle_event(e)
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):   # sem UI ainda: volta ao menu
                self.state = "menu"
            return
        if e.type == pygame.KEYDOWN:
            if self.state == "menu":
                if e.key == pygame.K_1:
                    self.new_match(1)
                elif e.key == pygame.K_2:
                    self.new_match(2)
                elif e.key == pygame.K_3:
                    self.career_ui.open_new()
                elif e.key == pygame.K_4:
                    self.career_ui.open_saved()
            elif self.career_match:
                if e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    self.speed_idx = e.key - pygame.K_1
                elif e.key == pygame.K_p:
                    self.paused = not self.paused
                elif e.key in (pygame.K_RETURN, pygame.K_SPACE) and self.state == "over":
                    self.finish_career_match()
            elif self.state == "over":
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.new_match(self.mode)
                elif e.key == pygame.K_ESCAPE:
                    self.state = "menu"
            else:
                if e.key == pygame.K_ESCAPE:
                    self.state = "menu"
                elif e.key == pygame.K_p:
                    self.paused = not self.paused
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if self.state == "menu":
                for i, r in enumerate(self.menu_btns):
                    if r.collidepoint(e.pos):
                        [lambda: self.new_match(1), lambda: self.new_match(2),
                         self.career_ui.open_new][i]()
                        return
                if self.has_save and self.continue_btn.collidepoint(e.pos):
                    self.career_ui.open_saved()
            elif self.career_match:
                if self.state == "over":
                    self.finish_career_match()
                else:
                    for i, r in enumerate(self.speed_rects()):
                        if r.collidepoint(e.pos):
                            self.speed_idx = i

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
        if power >= 600:
            self.fx_emit("kick", b.pos, d=d)

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
            b.pos += b.vel * dt
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
                if q.pos.distance_to(o.pos) < PR * 2 + 4:
                    q.tackle_cd = 0.55
                    chance = 0.5 if q.team.human else q.f.tackle
                    if random.random() < chance * o.f.shield:
                        b.owner = q
                        q.cd = 0.0
                        o.cd = 0.7
                        self.fx_emit("tackle", b.pos)
                        break
            return
        if o:
            return

        speed = b.vel.length()
        best, best_d = None, 1e9
        for t in self.teams:
            for p in t.players:
                d = p.pos.distance_to(b.pos)
                reach = PR + BR + (12 if p.role == "GK" else p.f.reach)
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
        self.state = "goal"
        self.timer = 2.4

    # ---------------------------------------------------------- movement
    def tick_battery(self, p, dt):
        """Dreno proporcional a velocidade; recarga quando quase parado (so com BATTERY_ON)."""
        ratio = p.vel.length() / (PLAYER_SPEED * p.spd)
        if ratio < robots.BAT_REGEN_BELOW:
            p.bat += robots.BAT_REGEN / self.match_time * p.f.bat_regen_mul * dt
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
        ty = CY + side * GOAL_HALF * random.uniform(0.35, 0.7)
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

    # ------------------------------------------------------------------ fx
    def reset_fx(self):
        self.fx.clear()
        self.fx_pairs.clear()
        self.trail.clear()
        self.warm_sprites()

    def fx_ok(self):
        return self.speed_idx != 3 and self.state != "over"

    def fx_emit(self, kind, pos, color=None, d=None):
        """Dispara faiscas. Usa so o RNG proprio; no-op em MAX e em 'over'. Nao altera a simulacao."""
        if self.speed_idx == 3 or self.state == "over":
            return
        n, v0, v1, l0, l1, base, size = FX_KINDS[kind]
        col = color or base or (255, 255, 255)
        room = FX_MAX - len(self.fx)
        if room <= 0:
            return
        rng = self.fx_rng
        px, py = pos.x, pos.y
        for _ in range(min(n, room)):
            if d is not None:                       # leque para tras da direcao do chute
                a = math.atan2(d.y, d.x) + math.pi + rng.uniform(-0.9, 0.9)
            else:
                a = rng.uniform(0, 2 * math.pi)
            sp = rng.uniform(v0, v1)
            life = rng.uniform(l0, l1)
            self.fx.append([px, py, math.cos(a) * sp, math.sin(a) * sp, life, life, col, size])

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

    def draw_fx(self, scr):
        now = time.perf_counter()
        dt = 0.0 if self.paused else min(now - self.fx_last, 0.05)
        self.fx_last = now
        if not self.fx:
            return
        keep = []
        for p in self.fx:
            p[4] -= dt
            if p[4] <= 0:
                continue
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.94
            p[3] *= 0.94
            keep.append(p)
            f = p[4] / p[5]
            col = scale_color(p[6], f)
            x, y = int(p[0]), int(p[1])
            pygame.draw.line(scr, col, (x, y), (int(x - p[2] * 0.03), int(y - p[3] * 0.03)), 2)
            pygame.draw.circle(scr, col, (x, y), max(1, int(p[7] * f)))
        self.fx = keep

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
        """Aspirador visto de cima: sombra, halo, anel de LED, corpo metalico. Sem rotacao em runtime."""
        size = 64
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

    def sprite_key(self, t, p):
        col = p.paint or (t.gk_color if p.role == "GK" else t.color)
        return (p.chassis, led_color(col), p.role == "GK")

    def get_sprite(self, ch, led, gk, low=False):
        key = (ch, led, gk, low)
        spr = self.sprites.get(key)
        if spr is None:
            spr = self.sprites[key] = self.build_robot_sprite(ch, led, gk, low)
        return spr

    def warm_sprites(self):
        for t in self.teams:
            for p in t.players:
                ch, led, gk = self.sprite_key(t, p)
                for low in (False, True):
                    if (ch, led, gk, low) not in self.sprites:
                        self.sprites[(ch, led, gk, low)] = self.build_robot_sprite(ch, led, gk, low)

    def draw(self):
        scr = self.screen
        if self.state == "career":
            return self.career_ui.draw()
        if self.state == "robots":
            ui = getattr(self, "robots_ui", None)
            if ui is not None:
                return ui.draw()
            self.state = "menu"
        if self.state == "menu":
            scr.blit(self.menu_bg, (0, 0))
            return self.draw_menu()
        scr.blit(self.pitch_surf, (0, 0))

        b = self.ball
        pygame.draw.ellipse(scr, (3, 8, 18), (b.pos.x - BR + 2, b.pos.y - BR + 5, BR * 2, BR * 1.4))
        for t in self.teams:
            for p in t.players:
                self.draw_player(t, p)
        self.draw_ball()
        self.draw_fx(scr)
        self.draw_hud()

        if self.paused:
            self.banner("PAUSADO", "P para continuar" + ("" if self.career_match else "  |  ESC para o menu"))
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

    def draw_scorers(self):
        for team in (0, 1):
            x = W // 2 - 250 if team == 0 else W // 2 + 250
            evs = [e for e in self.events if e["team"] == team]
            for k, e in enumerate(evs[:6]):
                txt = "%s %d'%s" % (e["name"] or "?", e["min"], " (contra)" if e["own"] else "")
                self.text(txt, 28, (240, 240, 240), center=(x, CY + 105 + k * 26))

    def draw_player(self, t, p):
        scr = self.screen
        pos = (int(p.pos.x), int(p.pos.y))
        ch, led, gk = self.sprite_key(t, p)
        low = p.bat < 0.25 and int(time.perf_counter() * 5) % 2 == 0
        spr = self.get_sprite(ch, led, gk, low)
        scr.blit(spr, (pos[0] - 32, pos[1] - 32))
        eye = p.pos + p.face * (PR - 6)                      # olho/sensor na direcao do rosto
        ex, ey = int(eye.x), int(eye.y)
        pygame.draw.circle(scr, (10, 14, 20), (ex, ey), 5)
        pygame.draw.circle(scr, (235, 250, 255), (ex, ey), 3)
        pygame.draw.circle(scr, led, (ex, ey), 1)
        bat = p.bat
        if bat < 0.98 or p.vel.length_squared() > 625:       # barra de bateria 22x4
            x, y = pos[0] - 12, pos[1] - PR - 11
            pygame.draw.rect(scr, (6, 10, 18), (x, y, 24, 6))
            if bat >= 0.5:
                bc = (70, 230, 110)
            elif bat >= 0.25:
                bc = (255, 215, 60)
            else:
                bc = (255, 70, 60)
            if bat >= 0.25 or int(time.perf_counter() * 5) % 2 == 0:
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

    def draw_ball(self):
        b, scr = self.ball, self.screen
        pos = (int(b.pos.x), int(b.pos.y))
        tr = self.trail
        if self.paused:
            pass
        elif b.vel.length_squared() > 350 * 350:
            tr.append(pos)
        elif tr:
            tr.popleft()
        n = len(tr)
        for i, q in enumerate(tr):
            f = (i + 1) / (n + 1)
            pygame.draw.circle(scr, scale_color((120, 230, 255), f * 0.8), q, max(1, int(BR * f * 0.8)))
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
        self.text("5 contra 5  |  clique ou aperte 1 / 2 / 3" + ("  / 4" if self.has_save else ""), 28,
                  (200, 225, 235), center=(cx, 570))


async def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Copa Aspirador")
    clock = pygame.time.Clock()
    game = Game(screen)
    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 20)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            game.handle_event(e)
        game.update(dt)
        game.draw()
        pygame.display.flip()
        await asyncio.sleep(0)
