# -*- coding: utf-8 -*-
"""Balanceamento das FORMACOES (game/formations.py) no MOTOR REAL (lento, opcional; nao grava nada em disco).

Uso (da raiz):
  .venv/bin/python tests/calib_formations.py [--n 300] [--procs 4] [--ovr 50,65] [--mode robots|friendly]
                                             [--all] [--json out.json]
Para cada formacao X (e, com --all, cada par X x Y) joga n partidas CPU x CPU com as MESMAS forcas:
  --mode robots   (padrao; Campanha/Modo Robos): times robot_league.opponent_team(ovr, seed) com jitter,
                  TUNING_ROBOTS, bateria ligada, 90 s (Game.start_robot_match);
  --mode friendly (Amistoso/Carreira): squad legado [(nome, ovr)] x 5 (Game.start_career_match, TUNING padrao).
Desenho pareado: a partida k usa os elencos A_k/B_k e a semente k; X fica com A_k e mandante nas k pares,
e o jogo espelhado (X com B_k, visitante) usa a mesma semente -> o elenco, o mando e o sorteio se cancelam.
Imprime, do ponto de vista de X: V/E/D %, aproveitamento V+E/2 (%), gols pro/contra por jogo e saldo.
Ruido (1 desvio) do aproveitamento com n partidas ~ 40/sqrt(n) pts (n=600 -> ~1,6).

Ajuste fino: --cand cand.json {id: {"pts": [[fx, fy] x 5], "push": p}} + --only id1,id2 (formacoes candidatas
so neste processo; nada muda no jogo).

TABELA (07/11/2026; --mode robots, aproveitamento V+E/2 % de X contra a EQUILIBRADA, mesmas forcas; n=400 em
45/60/75 e n=300 em 90; ruido ~+-2,0 / +-2,3 pts). ANTES = formacoes do amistoso original (so ovr 45, n=800):
  formacao     | ANTES 45 | DEPOIS 45    60    75    90 | gols pro x contra (60)
  RETRANCA     |   44.8   |       51.7  42.2  30.4  11.2 | 1.27 x 1.58
  OFENSIVA     |   43.9   |       54.2  44.6  29.9  27.8 | 1.08 x 1.32
  QUADRADO     |    9.1   |       54.8  46.0  40.4  38.7 | 1.76 x 1.93
  PRESSAO      |   36.4   |       50.2  50.6  54.6  67.0 | 1.14 x 1.14
O efeito depende muito da forca: com robos fracos as quatro ficam a +-5 da EQUILIBRADA; com robos fortes as
alternativas que tiram gente do corredor central (RETRANCA/OFENSIVA/QUADRADO) sao punidas e a PRESSAO (bloco
mais alto) ganha. Ate 75 (campanha) nenhuma passa de +5; no pos-campanha (90) a PRESSAO fica +17. Por isso o
efeito entra no SIMULAR (formations.SIM_DF, dF = (aprov - 50) / 1,8 pontos de Forca, por Forca do time).
Confrontos diretos (ovr 60, n=300, aproveitamento da linha): RETRANCA x OFENSIVA 56.2 | RETRANCA x QUADRADO 61.8 |
RETRANCA x PRESSAO 37.3 | OFENSIVA x QUADRADO 32.0 | OFENSIVA x PRESSAO 24.2 | QUADRADO x PRESSAO 52.7
(ciclo RETRANCA > QUADRADO > PRESSAO > RETRANCA; OFENSIVA perde de todas). QUADRADO e o jogo aberto (mais gols
pro e contra). --mode friendly (Amistoso/Carreira, ovr 65, n=300): RETRANCA 36.2 | OFENSIVA 34.3 | QUADRADO
42.8 | PRESSAO 59.0. Buscas (8 rodadas, ~60 candidatas, n=200-300 em 45/55/60/65/75/90): formas "estreitas"
(meias em y .30/.70) ganham de +10 a +14 em toda forca (descartadas: dominantes); recuar o bloco (push < 0) e
punido com forca alta.
"""
import argparse
import json
import os
import random
import sys
from multiprocessing import Pool

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
os.chdir(os.path.join(ROOT, "game"))

import pygame  # noqa: E402

import formations  # noqa: E402
import robot_league as rl  # noqa: E402
import robots  # noqa: E402
import soccer  # noqa: E402

DT = 1 / 60
MODE = "robots"
_g = None


def _game():
    global _g
    if _g is None:
        pygame.init()
        _g = soccer.Game(pygame.display.set_mode((soccer.W, soccer.H)))
    return _g


def _cfg(tag, ovr, seed, fid):
    color = (50, 120, 255) if tag == "A" else (235, 65, 65)
    if MODE == "friendly":
        c = {"name": tag, "color": color, "squad": [("%s%d" % (tag, i), ovr) for i in range(5)]}
    else:
        c = rl.match_cfg(rl.opponent_team(tag, color, ovr, seed))
    c["formation"] = fid
    return c


def one(args):
    """(fx, fy, ovr, k, mirror) -> (gols de X, gols de Y)."""
    fx, fy, ovr, k, mirror = args
    g = _game()
    x_home = (k % 2 == 0) != bool(mirror)
    sx, sy = (1000 + k, 2000 + k) if not mirror else (2000 + k, 1000 + k)
    x, y = _cfg("A", ovr, sx, fx), _cfg("B", ovr, sy, fy)
    home, away = (x, y) if x_home else (y, x)
    random.seed(k)
    old = soccer.BATTERY_ON
    soccer.BATTERY_ON = True
    try:
        if MODE == "friendly":
            g.start_career_match(home, away)
        else:
            g.start_robot_match(home, away, lambda s, e: None, tuning=robots.TUNING_ROBOTS)
        while g.state != "over":
            g.step(DT)
        sc = list(g.score)
    finally:
        soccer.BATTERY_ON = old
        g.match_sink = None
    return (sc[0], sc[1]) if x_home else (sc[1], sc[0])


def cell(pool, fx, fy, ovr, n):
    half = max(1, n // 2)
    jobs = [(fx, fy, ovr, k, m) for k in range(half) for m in (0, 1)]
    res = pool.map(one, jobs, chunksize=4)
    w = sum(1 for a, b in res if a > b)
    d = sum(1 for a, b in res if a == b)
    m = len(res)
    gf = sum(a for a, _ in res) / m
    ga = sum(b for _, b in res) / m
    return {"x": fx, "y": fy, "ovr": ovr, "n": m, "w": w / m * 100, "d": d / m * 100, "l": (m - w - d) / m * 100,
            "pts": (w + d / 2) / m * 100, "gf": gf, "ga": ga}


def fmt(c):
    return "%-11s x %-11s ovr %2d n %4d | V %4.1f E %4.1f D %4.1f | aprov %5.1f | gols %4.2f x %4.2f (saldo %+5.2f)" % (
        c["x"], c["y"], c["ovr"], c["n"], c["w"], c["d"], c["l"], c["pts"], c["gf"], c["ga"], c["gf"] - c["ga"])


def main():
    global MODE
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--ovr", default="50,65")
    ap.add_argument("--mode", default="robots", choices=("robots", "friendly"))
    ap.add_argument("--all", action="store_true", help="todos os pares X x Y (senao so X x EQUILIBRADA)")
    ap.add_argument("--only", default="", help="formacoes X (ids separados por virgula)")
    ap.add_argument("--json", default="")
    ap.add_argument("--cand", default="", help="JSON {id: {pts, push}}: formacoes candidatas (ajuste fino)")
    a = ap.parse_args()
    MODE = a.mode
    cand = {}
    if a.cand:
        with open(a.cand) as f:
            cand = json.load(f)
        _patch(cand)
    ovrs = [int(v) for v in a.ovr.split(",") if v]
    xs = [f for f in a.only.split(",") if f] or list(formations.ORDER)
    pairs = []
    for fx in xs:
        ys = [f for f in formations.ORDER if f != fx] if a.all else [formations.DEFAULT]
        for fy in ys:
            if fx != fy and (not a.all or (fy, fx) not in pairs):
                pairs.append((fx, fy))
    out = []
    with Pool(a.procs, initializer=_set_mode, initargs=(MODE, cand)) as pool:
        for ovr in ovrs:
            for fx, fy in pairs:
                c = cell(pool, fx, fy, ovr, a.n)
                out.append(c)
                print(fmt(c), flush=True)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1)


def _patch(cand):
    for fid, c in cand.items():
        formations.FORMATIONS[fid] = {"name": fid, "code": "", "desc": "", "push": float(c.get("push", 0.0)),
                                      "pts": tuple(tuple(p) for p in c["pts"])}


def _set_mode(m, cand=None):
    global MODE
    MODE = m
    _patch(cand or {})


if __name__ == "__main__":
    main()
