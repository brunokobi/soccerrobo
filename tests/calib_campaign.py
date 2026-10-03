# -*- coding: utf-8 -*-
"""Calibragem da campanha contra o MOTOR REAL (lento, opcional): mede o aproveitamento V+E/2 do jogador
e confere o SIMULAR (campaign.sim_bias(O)) e as metas de dificuldade (passo 16).

Uso (da raiz; ~12 min com n=300, 4 processos; nao grava nada em disco):
  .venv/bin/python tests/calib_campaign.py [--n 300] [--procs 4] [--chapters 1,3] [--json out.json]
  .venv/bin/python tests/calib_campaign.py --grid --n 200 --json grade.json     (grade F x O, regressao)
Para cada checkpoint (treino e cada estagio do torneio de cada capitulo: G1..G3, [QF], SF, final) monta um
Garage de Forca F = F_rec do estagio (F_start + (F_end - F_start) * i/(n-1), como Campaign._match_action;
F_start/F_end sao a Forca da politica gulosa) pela API do garage (nivel + pecas, ver build_garage_for) e
joga o MOTOR (Game.start_robot_match, TUNING_ROBOTS, bateria ligada, 90 s, usuario sempre mandante como na
campanha, seeds 0..n-1, 10 variantes de adversario) contra o time gerado como em Campaign._opp_team
(story.TEAMS: names/chassis/jitter=not perfect/paint, ovr efetivo com pity 0). Imprime V/E/D, V+E/2 do
motor, o Poisson com o vies atual (SIM) e o Poisson(F-2) antigo.

REGRESSAO do vies (campaign.sim_bias): grade F 44..65 x O 36..64 (n=200, com e sem jitter) + os checkpoints;
o motor e aproximadamente linear, V+E/2 ~ 34 + 1.8*F - 1.8*O (rmse ~4 pts, ~ ruido do motor), mais plano
em F do que o Poisson; ajuste L1 de F - bias(O): bias = clamp(5 + 1.5*(O-40), -2, 8). A "perfeicao" (sem
jitter) nao muda o aproveitamento de forma mensuravel (|dif| < ruido).

METAS do passo 16 (motor): treino 60-75; regulares 58-66; SF 52-58; chefes 45-52; chefe final do Mundial
42-50. O motor e MUITO mais duro que o Poisson contra adversarios fortes: para dar V+E/2 ~60% o adversario
regular precisa estar ~11-13 pontos de ovr abaixo da Forca (F-O ~ 7 so da 46%).

TABELA FINAL (n=300, seeds 0..299, 03/10/2026). ANTES = story do passo 15 (ovr e F do plano);
DEPOIS = story calibrada. F = Forca real do garage de teste; motor = V+E/2 %; Pois(F-2) = Poisson antigo
(SIM_BIAS=2); SIM(O) = simulador novo; dif = SIM - motor.
  checkpoint                 | ANTES: F    O  motor Pois(F-2) | DEPOIS: F    O  motor  SIM(O)  dif
  P treino Clube do Xadrez   |        43.7  36   73.2   62.8   |         43.7  36   73.2   69.2  -4.0
  1 treino                   |        44.7  38   66.7   60.6   |         44.7  36   66.8   71.2  +4.4
  1 G1 Turma 3ºB             |        44.7  38   58.2   60.6   |         44.7  38   58.2   60.6  +2.4
  1 G2 Fundão FC             |        45.7  39   56.3   60.6   |         45.7  39   56.3   57.2  +0.9
  1 G3 Grêmio                |        45.7  40   54.5   58.4   |         46.7  39   63.2   59.5  -3.7
  1 SF Clube de Teatro       |        46.7  42   43.7   56.1   |         47.7  40   56.0   56.1  +0.1
  1 F Os Impecáveis          |        47.7  46   34.8   49.3   |         47.7  41   53.8   50.4  -3.4
  2 treino                   |        49.5  43   50.3   60.1   |         51.4  39   71.2   69.7  -1.4
  2 G1 Padaria Pão Quen      |        49.5  43   46.5   60.1   |         51.4  40   70.5   64.5  -6.0
  2 G2 Tios do Churrasc      |        49.9  43   55.7   61.1   |         51.4  40   64.7   64.5  -0.2
  2 G3 Academia Sem Esf      |        51.4  45   48.3   60.1   |         51.7  41   60.3   59.5  -0.8
  2 SF Impecáveis Mk II      |        51.4  46   43.7   57.9   |         52.7  43   54.5   53.8  -0.7
  2 F Esquadrão Faxina       |        51.4  50   43.7   48.7   |         53.7  47   48.2   47.0  -1.2
  3 treino                   |        53.7  47   44.5   60.6   |         55.7  43   65.0   60.6  -4.4
  3 G1 Bombeiros Volunt      |        53.7  46   48.2   62.8   |         55.7  43   64.2   60.6  -3.6
  3 G2 Coral Desafinado      |        53.7  48   45.8   58.4   |         56.2  43   65.7   61.7  -4.0
  3 G3 Detetives do Qua      |        54.7  48   45.2   60.6   |         56.2  44   58.3   59.5  +1.2
  3 SF Sindicato dos Ze      |        54.7  51   47.2   53.8   |         57.2  46   55.0   57.2  +2.2
  3 F Imaculados L-9         |        55.7  54   41.8   49.3   |         58.2  51   46.2   48.1  +1.9
  4 treino                   |        56.2  49   44.5   61.7   |         58.2  47   58.3   57.2  -1.1
  4 G1 Escoteiros Eletr      |        56.2  50   45.2   59.5   |         58.2  44   67.7   63.9  -3.8
  4 G2 Cartório Veloz        |        56.2  50   47.0   59.5   |         59.2  45   67.2   63.9  -3.3
  4 G3 Cooperativa dos       |        56.2  51   45.7   57.2   |         60.2  46   62.2   63.9  +1.7
  4 SF Platinum Reserva      |        56.2  53   36.7   52.7   |         60.7  50   57.8   56.1  -1.7
  4 F Divisão Platinum       |        57.2  56   36.5   48.1   |         60.7  54   46.2   47.0  +0.8
  5 treino                   |        60.7  54   52.3   60.6   |         63.6  52   59.5   58.1  -1.4
  5 G1 Sakura Vacuum Cl      |        60.7  55   46.8   58.4   |         63.6  47   66.8   68.9  +2.1
  5 G2 Staubsauger Spor      |        61.7  57   41.8   56.1   |         64.5  48   63.0   68.9  +5.9
  5 G3 Les Aspirateurs       |        61.7  57   41.8   56.1   |         64.5  49   62.7   66.8  +4.2
  5 QF Dust Bunnies USA      |        62.7  58   45.0   56.1   |         64.9  50   64.5   65.5  +1.0
  5 SF Dojo do Kenji         |        62.7  59   44.2   53.8   |         64.9  53   56.2   58.9  +2.8
  5 F Hiperlimpos X-9        |        62.7  63   29.7   44.7   |         65.9  58   45.0   49.8  +4.8
  motor (DEPOIS): treino media 64.2 (58-71) | regulares 63.5 (56-71) | SF 55.9 (54-58) | chefes 47.9 (45-54;
  chefe final do Mundial 45.0). |SIM - motor|: media 2.5, max 6.0 (duas celulas >5: 6.0 e 5.9, dentro do
  ruido de +-4.6 do motor com n=300).
  motor (ANTES): treino 51.7 | regulares 48.2 | SF 43.1 | chefes 37.3 (final do Mundial 29.7).
Valores medidos antes (n=400, passo 6): treino F43.7 O36 72.8% | Cap1 grupo F44.7 O38 65.0% | Cap1 chefe
F47.7 O46 36.1% (o motor nao e funcao so de F-O).
Opcao antiga --roles (chassis de papel) removida: o motor usa os atributos, nao o chassis.
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


def story_team(tid, ovr, seed=777):
    return boss_team(tid, ovr, seed)


def boss_team(tid, ovr, seed=777):
    spec = story.TEAMS[tid]
    t = rl.opponent_team(spec["name"], spec["color"], ovr, seed, names=spec["names"],
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


def opp_team(tid, ovr, seed):
    """Adversario exatamente como Campaign._opp_team (names/chassis/jitter=not perfect/paint)."""
    return boss_team(tid, ovr, seed)


def table_cells(chapters=None):
    """Celulas da tabela final: por capitulo jogavel, o treino (F_start, ovr de campaign.training_ovr
    com adversario generico) e cada estagio do torneio (G1..G3, [QF], SF, F) com F = F_rec do estagio
    (F_start + (F_end - F_start) * i / (n-1), como Campaign._match_action) e o ovr efetivo (pity 0).
    Devolve [(rotulo, tipo, tid, ovr, F)], tipo em train/reg/qf/sf/boss/ptrain."""
    out = []
    for ch in story.CHAPTERS:
        if ch.get("draft") or not ch["nodes"] or (chapters and ch["id"] not in chapters):
            continue
        tid = next((a for k, a in ch["nodes"] if k == "tournament"), None)
        tr = story.TOURNAMENTS.get(tid)
        if tr is None:
            continue
        if tr["format"] == "single":
            sp = story.TEAMS[tr["final"]]
            out.append(("P treino %s" % sp["name"], "ptrain", tr["final"], sp["ovr"], ch["F_start"]))
            continue
        tov = max(cm.TRAIN_MIN_OVR, int(round(ch["F_start"])) - cm.TRAIN_DELTA)
        out.append(("%s treino" % ch["id"], "train", None, tov, ch["F_start"]))
        stages = cm.stages_of(tr)
        for i, st in enumerate(stages):
            t = {"QF": tr.get("qf"), "SF": tr.get("sf"), "F": tr["final"]}.get(st)
            if st[0] == "G":
                t = tr["group"][int(st[1]) - 1]
            frac = i / max(1, len(stages) - 1)
            F = ch["F_start"] + (ch["F_end"] - ch["F_start"]) * frac
            kind = {"G": "reg", "QF": "reg", "SF": "sf", "F": "boss"}[st[0] if st[0] == "G" else st]
            out.append(("%s %s %s" % (ch["id"], st, story.TEAMS[t]["name"][:16]), kind, t,
                        story.TEAMS[t]["ovr"], F))
    return out


def measure(pool, F, kind, tid, ovr, n):
    """(F real do garage, V, E, D) do motor: usuario mandante, 10 variantes de adversario."""
    g = build_garage_for(F)
    home = g.match_cfg()
    if kind == "train":
        spec = lambda k: rl.opponent_team(rl.TEAM_NAMES[k % len(rl.TEAM_NAMES)],  # noqa: E731
                                          rl.TEAM_COLORS[k % len(rl.TEAM_COLORS)], ovr, 31 + k)
    else:
        spec = lambda k: opp_team(tid, ovr, 777 + k)  # noqa: E731
    aways = [rl.match_cfg(spec(k)) for k in range(10)]
    res = pool.map(one, [(home, aways[s % 10], s) for s in range(n)], chunksize=4)
    w = sum(x > y for x, y in res)
    l = sum(x < y for x, y in res)
    return g.rating(), w, n - w - l, l


def main_table(a):
    cells = table_cells(a.chapters.split(",") if a.chapters else None)
    print("sim_bias(O) = clamp(%.2f + %.2f*(O-%d), %.2f, %.2f)  n=%d" % (
        cm.SIM_BIAS0, cm.SIM_BIAS_SLOPE, cm.SIM_O_REF, cm.SIM_BIAS_MIN, cm.SIM_BIAS_MAX, a.n))
    print("\n%-30s %-5s %5s %4s | %-13s %6s | %-7s %5s | %s" % (
        "checkpoint", "tipo", "F", "O", "motor V/E/D", "V+E/2", "SIM(O)", "viés", "Pois(F-2) antigo"))
    rows = []
    with Pool(a.procs) as pool:
        for name, kind, tid, ovr, F in cells:
            Fr, w, d, l = measure(pool, F, kind, tid, ovr, a.n)
            eng = 100.0 * (w + d / 2.0) / a.n
            pw, pd, _ = poisson_wdl(Fr - cm.sim_bias(ovr), ovr)
            ow, od, _ = poisson_wdl(Fr - 2.0, ovr)
            sim = points(pw, pd)
            rows.append({"name": name, "kind": kind, "F": Fr, "O": ovr, "eng": eng, "sim": sim,
                         "old": points(ow, od)})
            print("%-30s %-5s %5.1f %4s | %3d/%3d/%3d   %6.1f | %6.1f  %+5.1f | %6.1f" % (
                name, kind, Fr, ovr, w, d, l, eng, sim, sim - eng, points(ow, od)), flush=True)
    err = [abs(r["sim"] - r["eng"]) for r in rows]
    print("\n|SIM - motor|: media %.1f, max %.1f (alvo <= 5 por celula, ruido do motor +-%.1f)" % (
        sum(err) / len(err), max(err), 100 * 0.5 / math.sqrt(a.n) * 1.6))
    tg = {"train": (60, 75), "reg": (58, 66), "sf": (52, 58), "boss": (45, 52)}
    for k, (lo, hi) in tg.items():
        v = [r["eng"] for r in rows if r["kind"] == k]
        if v:
            print("%-6s motor: media %.1f  min %.1f  max %.1f   (alvo %d-%d)" % (
                k, sum(v) / len(v), min(v), max(v), lo, hi))
    if a.json:
        import json
        json.dump(rows, open(a.json, "w"), indent=1)


def main_grid(a):
    """Grade F x O (O em 36..64 passo 4, F em 44..65 passo 3), com e sem 'perfect': base da regressao
    de campaign.sim_bias (--json grava as celulas)."""
    import json
    Fs = [44, 47, 50, 53, 56, 59, 62, 65]
    Os = [36, 40, 44, 48, 52, 56, 60, 64]
    rows = []
    with Pool(a.procs) as pool:
        for perfect, tid in ((False, "gremio"), (True, "impecaveis")):
            for F in Fs:
                for O in Os:
                    if not (-4 <= F - O <= 14):
                        continue
                    Fr, w, d, l = measure(pool, F, "boss", tid, O, a.n)
                    p = 100.0 * (w + d / 2.0) / a.n
                    rows.append({"F": Fr, "O": O, "perfect": perfect, "pts": p, "n": a.n})
                    print(perfect, round(Fr, 1), O, round(p, 1), flush=True)
    if a.json:
        json.dump(rows, open(a.json, "w"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--chapters", default="", help="ex.: 1,3 (padrao: todos os jogaveis)")
    ap.add_argument("--json", default="", help="grava as linhas em JSON")
    ap.add_argument("--grid", action="store_true", help="grade F x O (regressao do vies)")
    a = ap.parse_args()
    if a.grid:
        main_grid(a)
    else:
        main_table(a)


if __name__ == "__main__":
    main()
