# -*- coding: utf-8 -*-
"""Fogos de artificio da comemoracao (gol e vitoria): foguetes que sobem da arquibancada e estouram
em coroas de faiscas sobre o campo.

So pygame.draw (nenhuma Surface criada por quadro), RNG proprio (`random.Random`) e relogio real
passado por quem chama: nunca toca o random global nem a simulacao. Teto fixo de faiscas.

Uso (soccer.Game):
    fw = Fireworks()
    fw.show(now, n, cores, area)     agenda n foguetes nos proximos segundos dentro de `area` (Rect)
    fw.draw(scr, now, paused)        atualiza (tempo real; pausado = congelado) e desenha
    fw.clear()                       nova partida
"""
import math
import random

import pygame

SPARK_MAX = 260                 # faiscas vivas ao mesmo tempo
# protecao de desempenho (soccer.Game copia o LOD da torcida em `lod` a cada quadro): menos faiscas por
# estouro e teto menor. E isso que cai quando o quadro pesa; a camera da partida nunca muda.
LOD_SPARKS = {2: 1.0, 1: 0.55, 0: 0.3}
ROCKET_MAX = 10
QUEUE_MAX = 24                  # agendados (partidas sem desenho, ex.: simuladas, nao acumulam)
BURST = (26, 34)                # faiscas por estouro
GRAVITY = 110.0                 # px/s^2 nas faiscas
ROCKET_G = 900.0                # px/s^2 no foguete (sobe rapido e estoura em ~1 s)
SPARK_LIFE = (0.9, 1.5)
SPARK_SPEED = (120.0, 280.0)
GAP = (0.16, 0.34)              # intervalo entre lancamentos de um show
FLASH_S = 0.12                  # clarao do estouro
WHITE = (255, 255, 255)
GOLD = (255, 210, 60)


def _scale(c, f):
    f = max(0.0, min(1.0, f))
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))


def _bright(c):
    """Cor de faisca legivel: clareia cores escuras (times de cor escura)."""
    m = max(c)
    if m < 160:
        k = 200.0 / max(m, 1)
        c = (min(255, int(c[0] * k + 30)), min(255, int(c[1] * k + 30)), min(255, int(c[2] * k + 30)))
    return c


class Fireworks:
    def __init__(self, seed=20262):
        self.rng = random.Random(seed)
        self.queue = []         # [(instante, cores, area)]
        self.rockets = []       # [x, y, vx, vy, alvo_y, cor, cores]
        self.sparks = []        # [x, y, vx, vy, vida, vida_max, cor, cor2]
        self.flashes = []       # [x, y, fim, cor]
        self.last = None
        self.lod = 2

    def clear(self):
        self.queue.clear()
        self.rockets.clear()
        self.sparks.clear()
        self.flashes.clear()
        self.last = None
        self.lod = 2

    @property
    def active(self):
        return bool(self.queue or self.rockets or self.sparks or self.flashes)

    def show(self, now, n, colors, area):
        """Agenda `n` foguetes a partir de `now` (cores: lista RGB; area: Rect do campo na tela)."""
        cols = [_bright(tuple(c)) for c in colors] or [GOLD]
        t = now
        r = self.rng
        for _ in range(max(0, n)):
            self.queue.append((t, cols, pygame.Rect(area)))
            t += r.uniform(*GAP)
        if len(self.queue) > QUEUE_MAX:
            del self.queue[:-QUEUE_MAX]

    def _launch(self, cols, area):
        r = self.rng
        x = r.uniform(area.left + 40, area.right - 40)
        y = area.bottom + 30
        ty = r.uniform(area.top + 20, area.top + area.h * 0.45)
        # velocidade para chegar ao alvo: v^2 = 2 g h (com folga para estourar no alto da subida)
        vy = -math.sqrt(2 * ROCKET_G * max(60.0, y - ty)) * 1.04
        vx = r.uniform(-40, 40)
        self.rockets.append([x, y, vx, vy, ty, r.choice(cols), cols])

    def _burst(self, x, y, cols, now):
        r = self.rng
        k = LOD_SPARKS.get(self.lod, 1.0)
        room = int(SPARK_MAX * k) - len(self.sparks)
        n = max(0, min(int(r.randint(*BURST) * k), room))
        c1 = r.choice(cols)
        c2 = r.choice((WHITE, GOLD) + tuple(cols))
        ring = r.random() < 0.5                   # coroa redonda ou estouro "salgueiro" (velocidades soltas)
        base = r.uniform(*SPARK_SPEED)
        for k in range(n):
            a = (k / max(1, n)) * 2 * math.pi + r.uniform(-0.08, 0.08)
            sp = base * r.uniform(0.92, 1.05) if ring else r.uniform(*SPARK_SPEED)
            life = r.uniform(*SPARK_LIFE)
            self.sparks.append([x, y, math.cos(a) * sp, math.sin(a) * sp, life, life, c1, c2])
        self.flashes.append([x, y, now + FLASH_S, c1])

    def update(self, now, dt):
        if self.queue:
            due = [q for q in self.queue if q[0] <= now]
            if due:
                self.queue = [q for q in self.queue if q[0] > now]
                for _, cols, area in due:
                    if len(self.rockets) < ROCKET_MAX:
                        self._launch(cols, area)
        if dt <= 0:
            return
        if self.rockets:
            keep = []
            for rk in self.rockets:
                rk[3] += ROCKET_G * dt
                rk[0] += rk[2] * dt
                rk[1] += rk[3] * dt
                if rk[1] <= rk[4] or rk[3] >= -40:
                    self._burst(rk[0], rk[1], rk[6], now)
                else:
                    keep.append(rk)
            self.rockets = keep
        if self.sparks:
            keep = []
            drag = max(0.0, 1.0 - 1.6 * dt)
            for p in self.sparks:
                p[4] -= dt
                if p[4] <= 0:
                    continue
                p[2] *= drag
                p[3] = p[3] * drag + GRAVITY * dt
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                keep.append(p)
            self.sparks = keep
        if self.flashes:
            self.flashes = [f for f in self.flashes if f[2] > now]

    def draw(self, scr, now, paused=False):
        dt = 0.0 if paused or self.last is None else max(0.0, min(now - self.last, 0.05))
        self.last = now
        if not paused:
            self.update(now, dt)
        line, circ = pygame.draw.line, pygame.draw.circle
        for x, y, vx, vy, _ty, col, _cols in self.rockets:
            ix, iy = int(x), int(y)
            line(scr, _scale(col, 0.55), (ix, iy), (int(x - vx * 0.05), int(y - vy * 0.05)), 2)
            circ(scr, WHITE, (ix, iy), 2)
        for x, y, end, col in self.flashes:
            f = max(0.0, (end - now) / FLASH_S)
            circ(scr, _scale(WHITE, 0.6 + 0.4 * f), (int(x), int(y)), int(4 + 10 * f))
            circ(scr, col, (int(x), int(y)), int(2 + 6 * f), 2)
        for p in self.sparks:
            f = p[4] / p[5]
            twinkle = f < 0.35 and int((now + p[0]) * 20) % 2 == 0      # faisca piscando no fim
            col = _scale(p[7] if twinkle else p[6], 0.35 + 0.65 * f)
            x, y = int(p[0]), int(p[1])
            line(scr, col, (x, y), (int(p[0] - p[2] * 0.045), int(p[1] - p[3] * 0.045)), 2 if f > 0.5 else 1)
            if f > 0.3:
                circ(scr, col, (x, y), 2 if f > 0.6 else 1)
