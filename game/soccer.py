"""SoccerPy - futebol arcade 100% Python (pygame).

Roda no desktop (`python main.py`) e no navegador via pygbag (WebAssembly).
"""
import asyncio
import math
import random
import time

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
    def __init__(self, team, idx, role, fx, fy, name="", ovr=65.0, chassis=None, seed=None):
        self.team = team
        self.idx = idx
        self.role = role
        self.name = name
        self.chassis = chassis or robots.ROLE_CHASSIS[role]
        self.robot = robots.from_overall(ovr, role, self.chassis, seed,
                                         flat=ACTIVE_TUNING["flat"])
        self.f = robots.factors(self.robot, ACTIVE_TUNING)
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
    def __init__(self, idx, name, color, gk_color, human=None, squad=None):
        self.idx = idx
        self.dir = 1 if idx == 0 else -1
        self.name = name
        self.color = color
        self.gk_color = gk_color
        self.human = human
        self.players = []
        for i, (r, fx, fy) in enumerate(FORMATION):
            if not squad:                          # modos 1P/2P: chassis padrao do papel, sem jitter
                nm, ovr, chassis, seed = "", 65, None, None
            elif len(squad[i]) >= 4:               # carreira: (nome, ovr, pid, pos)
                nm, ovr, pid, pos = squad[i][:4]
                chassis, seed = robots.POS_CHASSIS.get(pos), pid
            else:                                  # legado: (nome, ovr), chassis pelo papel
                nm, ovr = squad[i]
                chassis, seed = None, None
            self.players.append(Player(self, i, r, fx, fy, nm, ovr, chassis, seed))
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
        self.pitch_surf = self.build_pitch()
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
        self.match_time = self.time_left = MATCH_TIME
        self.events = []
        self.last_owner = None
        self.ball = Ball()
        self.paused = False
        self.kickoff(0)

    def start_career_match(self, home, away):
        """Partida automática (CPU x CPU) do modo carreira. home/away = match_cfg()."""
        self.mode = 0
        c1 = tuple(away["color"])
        if sum(abs(a - b) for a, b in zip(home["color"], c1)) < 130:
            c1 = (235, 235, 235) if sum(home["color"]) < 600 else (0, 230, 255)
        self.teams = [
            Team(0, home["name"], tuple(home["color"]), GK_COLORS[0], None, home["squad"]),
            Team(1, away["name"], c1, GK_COLORS[1], None, away["squad"]),
        ]
        self.score = [0, 0]
        self.career_match = True
        self.match_time = self.time_left = CAREER_TIME
        self.events = []
        self.last_owner = None
        self.speed_idx = 0
        self.ball = Ball()
        self.paused = False
        self.state = "kickoff"
        self.kickoff(0)

    def finish_career_match(self):
        self.career_match = False
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
                b.pos.x = r.left + BR
                b.vel.x = abs(b.vel.x) * 0.6
            elif b.pos.x > r.right - BR:
                b.pos.x = r.right - BR
                b.vel.x = -abs(b.vel.x) * 0.6
        if b.pos.y < r.top + BR:
            b.pos.y = r.top + BR
            b.vel.y = abs(b.vel.y) * 0.6
        elif b.pos.y > r.bottom - BR:
            b.pos.y = r.bottom - BR
            b.vel.y = -abs(b.vel.y) * 0.6

    def goal(self, team_idx):
        self.score[team_idx] += 1
        self.scorer = team_idx
        lo = self.last_owner
        self.events.append({"min": self.minute(), "team": team_idx,
                            "name": lo.name if lo else "", "own": bool(lo and lo.team.idx != team_idx)})
        self.ball.owner = None
        if BATTERY_ON:                      # gol recarrega todos os robos
            for t in self.teams:
                for p in t.players:
                    p.bat = min(1.0, p.bat + robots.BAT_GOAL_BONUS)
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

    # ------------------------------------------------------------- drawing
    def font(self, size):
        f = self.fonts.get(size)
        if f is None:
            f = self.fonts[size] = pygame.font.Font(None, size)
        return f

    def text(self, s, size, color, center=None, topleft=None, shadow=True,
             midleft=None, midright=None):
        img = self.font(size).render(s, True, color)
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
            sh = self.font(size).render(s, True, (0, 0, 0))
            self.screen.blit(sh, r.move(2, 2))
        self.screen.blit(img, r)

    def build_pitch(self):
        s = pygame.Surface((W, H))
        s.fill((20, 66, 36))
        n = 14
        sw = PITCH.w / n
        for i in range(n):
            col = (34, 130, 58) if i % 2 == 0 else (29, 118, 52)
            pygame.draw.rect(s, col, (PITCH.left + i * sw, PITCH.top, math.ceil(sw), PITCH.h))
        line = (235, 245, 235)
        pygame.draw.rect(s, line, PITCH, 3)
        pygame.draw.line(s, line, (CX, PITCH.top), (CX, PITCH.bottom), 3)
        pygame.draw.circle(s, line, (CX, CY), 70, 3)
        pygame.draw.circle(s, line, (CX, CY), 4)
        for side in (0, 1):
            big_x = PITCH.left if side == 0 else PITCH.right - 150
            small_x = PITCH.left if side == 0 else PITCH.right - 55
            pygame.draw.rect(s, line, (big_x, CY - 150, 150, 300), 3)
            pygame.draw.rect(s, line, (small_x, CY - 85, 55, 170), 3)
            spot_x = PITCH.left + 105 if side == 0 else PITCH.right - 105
            pygame.draw.circle(s, line, (spot_x, CY), 3)
            gx = PITCH.left - GOAL_DEPTH if side == 0 else PITCH.right
            net = pygame.Rect(gx, CY - GOAL_HALF, GOAL_DEPTH, GOAL_HALF * 2)
            pygame.draw.rect(s, (14, 40, 26), net)
            for yy in range(net.top, net.bottom, 12):
                pygame.draw.line(s, (110, 140, 118), (net.left, yy), (net.right, yy), 1)
            for xx in range(net.left, net.right, 12):
                pygame.draw.line(s, (110, 140, 118), (xx, net.top), (xx, net.bottom), 1)
            pygame.draw.rect(s, line, net, 3)
            line_x = PITCH.left if side == 0 else PITCH.right
            for yy in (CY - GOAL_HALF, CY + GOAL_HALF):
                pygame.draw.circle(s, (255, 255, 255), (line_x, yy), 6)
        return s

    def draw(self):
        scr = self.screen
        if self.state == "career":
            return self.career_ui.draw()
        scr.blit(self.pitch_surf, (0, 0))
        if self.state == "menu":
            return self.draw_menu()

        b = self.ball
        pygame.draw.ellipse(scr, (15, 70, 35), (b.pos.x - BR + 2, b.pos.y - BR + 5, BR * 2, BR * 1.4))
        for t in self.teams:
            for p in t.players:
                self.draw_player(t, p)
        self.draw_ball()
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
        pygame.draw.ellipse(scr, (15, 70, 35), (pos[0] - PR, pos[1] + PR - 8, PR * 2, 12))
        col = t.gk_color if p.role == "GK" else t.color
        pygame.draw.circle(scr, col, pos, PR)
        pygame.draw.circle(scr, tuple(int(c * 0.55) for c in col), pos, PR, 3)
        nose = p.pos + p.face * (PR - 3)
        pygame.draw.circle(scr, (255, 224, 190), (int(nose.x), int(nose.y)), 4)
        self.text(str(p.idx + 1), 20, (255, 255, 255), center=pos, shadow=False)
        if t.human and p is t.ctrl and self.state != "over":
            pygame.draw.circle(scr, (255, 255, 255), pos, PR + 4, 2)
            tip = (pos[0], pos[1] - PR - 6)
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
        pygame.draw.circle(scr, (250, 250, 250), pos, BR)
        a = b.roll
        for k in range(3):
            ang = a + k * 2.094
            px, py = pos[0] + math.cos(ang) * 4, pos[1] + math.sin(ang) * 4
            pygame.draw.circle(scr, (30, 30, 30), (int(px), int(py)), 2)
        pygame.draw.circle(scr, (20, 20, 20), pos, BR, 2)

    def draw_hud(self):
        scr = self.screen
        pygame.draw.rect(scr, (12, 22, 18), (0, 0, W, 76))
        pygame.draw.line(scr, (60, 90, 70), (0, 76), (W, 76), 2)
        t0, t1 = self.teams
        self.text(t0.name, 44, t0.color, center=(W // 2 - 270, 36))
        self.text(t1.name, 44, t1.color, center=(W // 2 + 270, 36))
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
        self.text(hint, 24, (210, 230, 215), center=(W // 2, H - 22), shadow=False)

    def draw_speed_buttons(self):
        self.text("Velocidade (1-4):", 24, (210, 230, 215), midright=(W - 342, H - 22), shadow=False)
        for i, (r, lab) in enumerate(zip(self.speed_rects(), ["1x", "2x", "4x", "MAX"])):
            on = i == self.speed_idx
            pygame.draw.rect(self.screen, (40, 150, 80) if on else (24, 60, 40), r, border_radius=6)
            pygame.draw.rect(self.screen, (230, 245, 235), r, 2, border_radius=6)
            self.text(lab, 24, (255, 255, 255), center=r.center, shadow=False)
        self.text("P: pausa", 24, (210, 230, 215), midleft=(24, H - 22), shadow=False)

    def banner(self, title, sub, color=(255, 255, 255)):
        veil = pygame.Surface((W, 150), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        self.screen.blit(veil, (0, CY - 75))
        self.text(title, 84, color, center=(W // 2, CY - (15 if sub else 0)))
        if sub:
            self.text(sub, 32, (230, 230, 230), center=(W // 2, CY + 42))

    def draw_menu(self):
        scr = self.screen
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        scr.blit(veil, (0, 0))
        self.text("SOCCERPY", 150, (255, 255, 255), center=(W // 2, 190))
        self.text("futebol arcade feito 100% em Python", 38, (200, 235, 210), center=(W // 2, 275))
        labels = [("1 - UM JOGADOR", "você contra a CPU"), ("2 - DOIS JOGADORES", "J1 contra J2, mesmo teclado"),
                  ("3 - NOVA CARREIRA", "gerente: elenco, mercado, ligas")]
        mx, my = pygame.mouse.get_pos()
        for r, (a, c) in zip(self.menu_btns, labels):
            hover = r.collidepoint(mx, my)
            pygame.draw.rect(scr, (40, 150, 80) if hover else (28, 110, 60), r, border_radius=14)
            pygame.draw.rect(scr, (230, 245, 235), r, 3, border_radius=14)
            self.text(a, 34, (255, 255, 255), center=(r.centerx, r.centery - 14))
            self.text(c, 24, (210, 235, 215), center=(r.centerx, r.centery + 22), shadow=False)
        if self.has_save:
            r = self.continue_btn
            hover = r.collidepoint(mx, my)
            pygame.draw.rect(scr, (200, 150, 30) if hover else (160, 115, 20), r, border_radius=14)
            pygame.draw.rect(scr, (255, 240, 200), r, 3, border_radius=14)
            self.text("4 - CONTINUAR CARREIRA", 34, (255, 255, 255), center=r.center)
        self.text("5 contra 5  |  clique ou aperte 1 / 2 / 3" + ("  / 4" if self.has_save else ""), 28,
                  (230, 230, 230), center=(W // 2, 570))


async def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("SoccerPy")
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
