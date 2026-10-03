# -*- coding: utf-8 -*-
"""Calibragem da campanha contra o MOTOR REAL (lento, opcional): confirma SIM_BIAS (campaign.SIM_BIAS = 2).

Uso (da raiz): .venv/bin/python tests/calib_campaign.py [--n 200] [--procs 4]
Para cada checkpoint (chefe do Cap.1 e, quando os capitulos existirem/deixarem de ser draft, o chefe do
Cap.3 e a final do Mundial = chefe do Cap.5) monta um Garage de Forca conhecida (F = F_end do capitulo,
valor "normal" da tabela do plano) pela API do garage (nivel + pecas Comuns/Raras/Epicas equipadas nos 5
titulares, ver build_garage_for) e joga o MOTOR (Game.start_robot_match, TUNING_ROBOTS, bateria ligada,
partidas de 90 s, usuario sempre mandante como na campanha, seeds 0..n-1, multiprocessing) contra o time
do chefe gerado como em campaign.Campaign._opp_team (story.TEAMS: nomes, chassis, jitter, ovr).
Imprime V/E/D e aproveitamento V+E/2 do motor vs Poisson(F - SIM_BIAS) (exato, como na campanha) e o vies
implicito (b em 0..5 que melhor casa o Poisson(F - b) com o motor) e confirma SIM_BIAS ~ 2 (soft, +-1).
Nao grava nada em disco.

Referencia (n alto; as celulas do calib_robots.py, dif de rating 0..+5 -> V+E/2 ~ 50-65% no motor, e a
tabela do plano: motor 2 pontos mais duro que o Poisson): SIM_BIAS=2. Ruido do motor com n=200: +-3.5 pts
de aproveitamento (~ +-0.7 ponto de vies); com n=60 so serve como smoke test.

VALORES MEDIDOS (n=400, seeds 0..399, usuario mandante, garage so Disco da campanha nova, 02/10/2026):
  cap P treino vs Xadrez ovr 36, F 43.7 : motor V252/E78/D70  = 72.8% | Poisson(F-2) 62.8% | vies implicito -1.0
  cap 1 grupo vs Turma 3B ovr 38, F 44.7: motor V215/E90/D95  = 65.0% | Poisson(F-2) 60.6% | vies implicito  0.0
  cap 1 CHEFE Impecaveis ovr 46, F 47.7 : motor V82/E125/D193 = 36.1% | Poisson(F-2) 49.3% | vies implicito +7.8
O motor NAO e funcao so de (F - O): contra adversarios fortes (ovr ~46) ele e MUITO mais duro que o Poisson
(F 51.4 vs ovr 46 ainda da so ~46%; vs ovr 38 da 70-80% para F 44-51), enquanto contra ovr 36-38 ate e mais
facil. O vies medio (+2.3) bate com SIM_BIAS=2 so por coincidencia das duas pontas (diga-se: nao e
constante). Sem jitter (perfect) vs com jitter: ~+3 pts de aproveitamento a favor do jitter (ruido) ->
o "perfect" nao explica sozinho. Ver o relatorio da Fase 3 (passo 6): decisao de design pendente.
Opcoes: --extra inclui treino/grupo de cada capitulo; --roles testa chassis de papel (sem efeito: o motor
usa os atributos, nao o chassis).
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

import campaign as cm  # noqa: E402
import garage as gm  # noqa: E402
import parts  # noqa: E402
import robot_league as rl  # noqa: E402
import robots  # noqa: E402
import soccer  # noqa: E402
import story  # noqa: E402

DT = 1 / 60
CHECK_CHAPTERS = ("1", "3", "5")        # chefe do Cap.1, do Cap.3 e final do Mundial (quando existirem)
_g = None
BAL = {"motor": "Motor Escovado", "bateria": "Célula Longa", "parachoque": "Borracha",
       "chutador": "Solenoide", "succao": "Escova de Sucção", "sensor": "Infravermelho",
       "chip": "Chip de CPU"}


# ---------------------------------------------------------------- Garage de Forca conhecida
def _equip_all(g, rar, lvl):
    for r in g.robots:
        r["slots"] = {s: None for s in parts.SLOTS}
    g.inventory = []
    for r in g.robots:
        for slot in parts.SLOTS:
            pc = g.new_piece(BAL[slot], rar, lvl)
            g.inventory.append(pc)
            assert g.equip(r["id"], pc["id"])[0]


def build_garage_for(F):
    """Garage (campanha nova) com Forca ~F: escada nivel/pecas pela API do garage (a primeira
    configuracao com rating >= F-2) e ajuste fino por um deslocamento uniforme dos atributos base."""
    g = cm.new_campaign(random.Random(7)).garage
    ladder = [(None, 0, lv) for lv in range(1, 11)]                      # so nivel
    ladder += [(rar, lvl, 10) for rar in (0, 1, 2, 3) for lvl in (0, 3, 5)]
    for rar, lvl, level in ladder:
        for r in g.robots:
            r["level"], r["xp"] = level, 0
        if rar is None:
            for r in g.robots:
                r["slots"] = {s: None for s in parts.SLOTS}
            g.inventory = []
        else:
            _equip_all(g, rar, lvl)
        if g.rating() >= F - 2.0:
            break
    g.auto_lineup()
    for _ in range(40):                                                   # ajuste fino
        d = F - g.rating()
        if abs(d) < 0.3:
            break
        step = 1 if d > 0 else -1
        for r in g.robots:
            for a in robots.ATTRS:
                r["base"][a] = int(max(robots.ATTR_MIN, min(robots.ATTR_MAX, r["base"][a] + step)))
    return g


def boss_team(tid, ovr):
    spec = story.TEAMS[tid]
    t = rl.opponent_team(spec["name"], spec["color"], ovr, 777, names=spec["names"],
                         chassis=spec["chassis"], jitter=not spec["perfect"])
    for e in t["squad"]:
        e["paint"] = tuple(spec["paint"])
    return t


# ---------------------------------------------------------------- motor
def _game():
    global _g
    if _g is None:
        pygame.init()
        _g = soccer.Game(pygame.display.set_mode((soccer.W, soccer.H)))
    return _g


def one(args):
    home, away, seed = args
    g = _game()
    random.seed(seed)
    old = soccer.BATTERY_ON
    soccer.BATTERY_ON = True
    try:
        g.start_robot_match(home, away, lambda s, e: None, tuning=robots.TUNING_ROBOTS)
        while g.state != "over":
            g.step(DT)
        return g.score[0], g.score[1]
    finally:
        soccer.BATTERY_ON = old


def pois_pmf(lam, kmax=25):
    p, out = math.exp(-lam), []
    for k in range(kmax):
        out.append(p)
        p *= lam / (k + 1)
    return out


def poisson_wdl(F, O):
    """(V, E, D) exatos de quick_sim(F, O)."""
    d = (F - O) * rl.SIM_SLOPE * rl.SIM_K / 2.0
    ph, pa = pois_pmf(rl.GOALS_AVG * math.exp(d)), pois_pmf(rl.GOALS_AVG * math.exp(-d))
    w = sum(ph[i] * pa[j] for i in range(len(ph)) for j in range(i))
    dr = sum(ph[i] * pa[i] for i in range(len(ph)))
    return w, dr, 1 - w - dr


def points(w, d):
    return 100.0 * (w + d / 2.0)


def implied_bias(F, O, eng_pts):
    best = None
    for bi in range(-10, 81):
        b = bi / 10.0
        w, d, _ = poisson_wdl(F - b, O)
        err = abs(points(w, d) - eng_pts)
        if best is None or err < best[0]:
            best = (err, b)
    return best[1]


def checkpoints(extra=False):
    """Chefes dos capitulos CHECK_CHAPTERS (F = F_end). extra=True: tambem o 1o adversario do grupo
    (F = F_start) de todo capitulo jogavel e o treino do Prologo."""
    out = []
    for ch in story.CHAPTERS:
        if ch.get("draft") or not ch["nodes"]:
            continue
        tid = next((a for k, a in ch["nodes"] if k == "tournament"), None)
        tr = story.TOURNAMENTS.get(tid)
        if tr is None:
            continue
        if tr["format"] == "single":
            if extra:
                out.append(("cap %s: treino %s" % (ch["id"], story.TEAMS[tr["final"]]["name"]),
                            tr["final"], story.TEAMS[tr["final"]]["ovr"], ch["F_start"]))
            continue
        if extra:
            t0 = tr["group"][0]
            out.append(("cap %s: grupo %s" % (ch["id"], story.TEAMS[t0]["name"]), t0,
                        story.TEAMS[t0]["ovr"], ch["F_start"]))
        if ch["id"] in CHECK_CHAPTERS or extra:
            out.append(("cap %s: chefe %s" % (ch["id"], story.TEAMS[tr["final"]]["name"]),
                        tr["final"], story.TEAMS[tr["final"]]["ovr"], ch["F_end"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--extra", action="store_true", help="inclui tambem o treino/grupo de cada capitulo")
    ap.add_argument("--roles", action="store_true",
                    help="titulares com o chassis do papel (Goleiro/Tanque/Disco/Disco/Velocista), como os adversarios")
    a = ap.parse_args()
    cps = checkpoints(a.extra)
    print("SIM_BIAS atual = %s  (SIM_K=%s GOALS_AVG=%s SIM_SLOPE=%s)  n=%d" % (
        cm.SIM_BIAS, rl.SIM_K, rl.GOALS_AVG, rl.SIM_SLOPE, a.n))
    if not cps:
        print("nenhum checkpoint (Caps. 1/3/5 nao jogaveis)")
        return
    biases = []
    print("\n%-34s %5s %5s | %-14s %-6s | %-6s %-6s | %s" % (
        "checkpoint", "F", "O", "motor V/E/D", "V+E/2", "Pois(F-B)", "Pois(F)", "vies implicito"))
    with Pool(a.procs) as pool:
        for name, tid, O, F in cps:
            g = build_garage_for(F)
            if a.roles:
                for r in g.lineup_robots():
                    r["chassis"] = robots.ROLE_CHASSIS[r["role"]]
            Fr = g.rating()
            home = g.match_cfg()
            away = rl.match_cfg(boss_team(tid, O))
            res = pool.map(one, [(home, away, s) for s in range(a.n)], chunksize=2)
            w = sum(x > y for x, y in res)
            l = sum(x < y for x, y in res)
            d = a.n - w - l
            eng = 100.0 * (w + d / 2.0) / a.n
            pw, pd, _pl = poisson_wdl(Fr - cm.SIM_BIAS, O)
            p0w, p0d, _ = poisson_wdl(Fr, O)
            b = implied_bias(Fr, O, eng)
            biases.append(b)
            print("%-34s %5.1f %5d | %3d/%3d/%3d    %5.1f  | %5.1f  %5.1f  | %+.1f" % (
                name, Fr, O, w, d, l, eng, points(pw, pd), points(p0w, p0d), b))
    mean_b = sum(biases) / len(biases)
    ok = abs(mean_b - cm.SIM_BIAS) <= 1.0
    print("\nvies implicito medio = %.1f (SIM_BIAS=%s, tolerancia +-1)  %s" % (
        mean_b, cm.SIM_BIAS, "[ALVO OK]" if ok else "[ALVO NAO ATINGIDO]"))


if __name__ == "__main__":
    main()
