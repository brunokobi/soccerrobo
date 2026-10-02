# -*- coding: utf-8 -*-
"""Calibragem do Poisson (robot_league.quick_sim) contra o motor (Modo Robos).

Uso (da raiz): .venv/bin/python tests/calib_robots.py [--n 100] [--diffs -20,-15,...,20] [--fit]
Imprime, por diferenca de rating (A - B), a % de vitoria/empate/derrota e os gols/jogo do
MOTOR (Game.start_robot_match, TUNING_ROBOTS, bateria ligada, 90 s, A mandante nas seeds
pares) e do POISSON (probabilidades exatas de robot_league.quick_sim com as constantes
atuais). --fit procura SIM_K / GOALS_AVG que minimizam o erro de %vitoria (V + D/2) e de
gols/jogo contra a tabela medida. Nao grava nada em disco.

Times: cada lado = 5 robos from_overall(ovr, papel, ROLE_CHASSIS) (como opponent_team);
B fica em ovr 50 e A em 50 + diff (rating ~ ovr).

RESULTADO DA CALIBRAGEM (n=100 por celula, seeds 0..n-1, diffs -20..+20 passo 5):
SIM_K = 1.85, SIM_SLOPE = 0.04 (inalterada), GOALS_AVG = 1.34 (robot_league.py).
Antes (K=1.0, GOALS=1.4): pior erro de (V+E/2) = 14.3 pts; Depois: 6.7 pts (V puro <= 7.6 pts).
Motor n=200/celula (V/E/D %, gols/jogo): -20: 9/11/80 3.73 | -15: 12/12/77 3.69 | -10: 22/21/56 2.90
 | -5: 26/24/49 2.66 | 0: 36/31/34 2.49 | +5: 54/21/25 2.69 | +10: 63/20/17 2.68 | +15: 65/18/16 2.79
 | +20: 74/18/8 3.35. Poisson final: gols/jogo 2.68-3.45 (2.68 em dif 0).
Faixa de validade: |dif de rating| <= 20 (A-B, ratings = media dos atributos x100, ~ovr). Fora disso o
Poisson satura mais devagar/rapido que o motor: nao extrapolar; o ruido de n=200 e ~+-3.5 pts.
Reexecutar apos mudar TUNING_ROBOTS, formulas do motor ou constantes de atributos.
"""
import argparse
import math
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

import robot_league as rl  # noqa: E402
import robots  # noqa: E402
import soccer  # noqa: E402

DT = 1 / 60
BASE = 50
_g = None


def _game():
    global _g
    if _g is None:
        pygame.init()
        _g = soccer.Game(pygame.display.set_mode((soccer.W, soccer.H)))
    return _g


def one(args):
    ovr_a, ovr_b, seed = args
    g = _game()
    a = rl.match_cfg(rl.opponent_team("A", (50, 120, 255), ovr_a, 1000 + seed))
    b = rl.match_cfg(rl.opponent_team("B", (235, 65, 65), ovr_b, 2000 + seed))
    random.seed(seed)
    old = soccer.BATTERY_ON
    soccer.BATTERY_ON = True
    try:
        home_a = seed % 2 == 0
        if home_a:
            g.start_robot_match(a, b, lambda s, e: None, tuning=robots.TUNING_ROBOTS)
        else:
            g.start_robot_match(b, a, lambda s, e: None, tuning=robots.TUNING_ROBOTS)
        while g.state != "over":
            g.step(DT)
        ga, gb = g.score if home_a else g.score[::-1]
    finally:
        soccer.BATTERY_ON = old
    return ga, gb


def engine_cell(pool, diff, n):
    res = pool.map(one, [(BASE + diff, BASE, s) for s in range(n)], chunksize=4)
    w = sum(x > y for x, y in res)
    l = sum(x < y for x, y in res)
    return w / n, (n - w - l) / n, l / n, sum(x + y for x, y in res) / n


def pois_pmf(lam, kmax=25):
    p, out = math.exp(-lam), []
    for k in range(kmax):
        out.append(p)
        p *= lam / (k + 1)
    return out


def poisson_cell(diff, k=None, goals=None, slope=None):
    """(w, d, l, gols/jogo) exatos do quick_sim para rating_h - rating_a = diff."""
    k = rl.SIM_K if k is None else k
    goals = rl.GOALS_AVG if goals is None else goals
    slope = rl.SIM_SLOPE if slope is None else slope
    d = diff * slope * k / 2.0
    lh, la = goals * math.exp(d), goals * math.exp(-d)
    ph, pa = pois_pmf(lh), pois_pmf(la)
    w = sum(ph[i] * pa[j] for i in range(len(ph)) for j in range(i))
    dr = sum(ph[i] * pa[i] for i in range(len(ph)))
    return w, dr, 1 - w - dr, lh + la


def table(diffs, eng, **kw):
    print("%6s | %-26s | %-26s | %s" % ("dif", "MOTOR V/E/D%  gols", "POISSON V/E/D%  gols", "dV(V+E/2)"))
    worst = 0.0
    for d in diffs:
        ew, ed, el, eg = eng[d]
        pw, pd, pl, pg = poisson_cell(d, **kw)
        dv = 100 * ((pw + pd / 2) - (ew + ed / 2))
        worst = max(worst, abs(dv))
        print("%+6d | %5.1f %5.1f %5.1f  %5.2f   | %5.1f %5.1f %5.1f  %5.2f   | %+6.1f" % (
            d, 100 * ew, 100 * ed, 100 * el, eg, 100 * pw, 100 * pd, 100 * pl, pg, dv))
    print("pior |dV| = %.1f pontos (alvo <= 10)  SIM_K=%s SIM_SLOPE=%s GOALS_AVG=%s" % (
        worst, kw.get("k", rl.SIM_K), kw.get("slope", rl.SIM_SLOPE), kw.get("goals", rl.GOALS_AVG)))
    return worst


def fit(diffs, eng):
    best = None
    mean_eg = sum(eng[d][3] for d in diffs) / len(diffs)
    for ki in range(20, 301, 5):
        k = ki / 100
        for gi in range(80, 181, 2):
            goals = gi / 100
            err = 0.0
            for d in diffs:
                ew, ed, el, eg = eng[d]
                pw, pd, pl, pg = poisson_cell(d, k=k, goals=goals)
                err += (100 * ((pw + pd / 2) - (ew + ed / 2))) ** 2 + (30 * (pg - eg)) ** 2
            if best is None or err < best[0]:
                best = (err, k, goals)
    print("melhor ajuste: SIM_K=%.2f GOALS_AVG=%.2f (media de gols do motor %.2f)" % (best[1], best[2], mean_eg))
    return best[1], best[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--diffs", default="-20,-15,-10,-5,0,5,10,15,20")
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    diffs = [int(x) for x in a.diffs.split(",")]
    eng = {}
    with Pool(a.procs) as pool:
        for d in diffs:
            eng[d] = engine_cell(pool, d, a.n)
            print("motor dif %+d: V%.0f E%.0f D%.0f gols %.2f" % (d, 100 * eng[d][0], 100 * eng[d][1],
                                                                  100 * eng[d][2], eng[d][3]), flush=True)
    print("\n== constantes atuais ==")
    table(diffs, eng)
    if a.fit:
        k, goals = fit(diffs, eng)
        print("\n== com o ajuste ==")
        table(diffs, eng, k=k, goals=goals)


if __name__ == "__main__":
    main()
