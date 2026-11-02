# -*- coding: utf-8 -*-
"""Calibragem da FORCA das skills (skills.SKILL_FORCE) contra o MOTOR REAL (Fase 4 / B9; spec 9.1).

Uso (da raiz; lento: ~0,25 s por partida por processo; nao grava nada fora do repo):
  .venv/bin/python tests/calib_skills.py [--n 200] [--F 55,65,75] [--ranks 1,3] [--skills arrancada,curva]
                                         [--procs 4] [--json out.json] [--write]
Para cada skill e rank: N partidas por F (Modo Robos: Game.start_robot_match, TUNING_ROBOTS, bateria
ligada, 90 s, time A mandante nas seeds pares) do time A (5 robos from_overall(F), chassis de papel, como
robot_league.opponent_team) COM a skill nos titulares elegiveis (papeis de skills.ALL[id]["roles"]; o
Lider so em 1 robo: aura) contra o MESMO adversario (ovr F - GAP, ~50% de V+E/2), e o mesmo A SEM skills
(mesmas seeds: numeros aleatorios comuns). delta = (V+E/2 com) - (V+E/2 sem), media dos F.
  forca por robo (pontos de F) = delta / SLOPE * 5 / n_robos_com_a_skill     (SLOPE = 1,8 pts/F: o motor e
  ~linear, V+E/2 ~ 34 + 1,8*(F - O); ver tests/calib_campaign.py)
Ranks nao medidos sao interpolados (r2 = media de r1 e r3); forca >= 0 e monotona no rank. Meta da spec:
|delta| 1,5-4,0 pontos de V+E/2 por robo (reliquias/Lendarias ate 6). --write grava SKILL_FORCE em
game/skills.py (bloco entre os marcadores SKILL_FORCE-BEGIN/END).

Ruido: V+E/2 por partida tem desvio ~0,45; com n partidas por F e k valores de F o erro padrao de delta
e ~ 45*sqrt(2/(n*k)) pontos (n=200, k=3: ~2,6 pts = ~1,4 F para uma skill dos 5 robos). Os valores sao
uma ESTIMATIVA ruidosa: a tabela imprime o erro padrao de cada celula.

RESULTADO (02/11/2026; n=200 por F, F = 55/65/75, adversario F-9; base sem skills V+E/2 65,5/67,8/67,5;
"ep" = erro padrao de delta; F/robo = delta/1,8*5/robos; curva medida de novo depois da correcao da
pre-rotacao do arco). Gravado em skills.SKILL_FORCE (r2 interpolado; < 0 vira 0; monotono no rank):
  skill          r | delta(r1) ep  | delta(r3) ep  | robos | SKILL_FORCE r1/r2/r3
  arrancada        |  +2,7   2,4   |  +5,1   2,3   |  4    | 1,85 / 2,69 / 3,53
  succao           |  +6,0   2,4   | +11,8   2,2   |  4    | 4,17 / 6,19 / 8,22
  curva            |  -0,8   2,2   |  -0,1   2,2   |  4    | 0 / 0 / 0
  muralha          |  -2,0   2,0   |  +0,9   1,9   |  2    | 0 / 0 / 1,27
  leitura      (P) |  +2,1   2,4   |  +7,9   2,2   |  4    | 1,45 / 3,47 / 5,50
  poupanca     (P) |  +0,3   0,6   |  +1,4   0,5   |  5    | 0,19 / 0,49 / 0,79
  recarga          |  +0,2   0,3   |  -0,3   0,2   |  5    | 0,09 / 0,09 / 0,09
  overclock        |  +3,1   2,3   |  +7,6   2,3   |  5    | 1,71 / 2,96 / 4,21
  blindagem        |  +3,8   2,2   |  +5,8   2,2   |  3    | 3,55 / 4,44 / 5,32
  drible           |  -2,2   2,0   |  -1,3   2,1   |  3    | 0 / 0 / 0
  elastica         |  +5,3   2,0   |  +7,9   2,0   |  1 GK | 14,81 / 18,40 / 20,00
  pressao          |  +0,5   2,3   |  +1,9   2,3   |  3    | 0,46 / 1,12 / 1,77
  choque           |  -0,3   0,3   |  -0,2   0,4   |  1    | 0 / 0 / 0
  matador      (C) |  -1,2   1,3   |  -0,3   1,4   |  1    | 0 / 0 / 0
  lancador     (P) |   0,0   0,0   |   0,0   0,0   |  1 GK | 0 / 0 / 0   (nao muda NADA no motor)
  lider     (aura) |  +1,1   2,3   |  +3,8   2,2   |  1    | 3,01 / 6,83 / 10,65
  especiais (r1): rolando +3,3 (1,85) | instinto_vo +0,4 (0,23) | remendo +1,1 (0,60) | calor_forno 0,0 (0)
  | chinelada -2,8 (0) | faro_meia +0,2 (0,09) | faxina_total +7,7 (4,26) | sobrecarga -2,6 (0)
  | muralha_aco +4,9 (2,73) | mente_zen 0,0 (0) | impecavel +3,4 (1,90).
Fora da meta da spec (|delta| 1,5-4,0 por robo): quase todas abaixo (curva, muralha, drible, choque,
matador, recarga, poupanca, pressao, lancador ~0 = dentro do ruido) e elastica acima (5,3 num robo so).
ROBOT_SK_CAP subiu para 20 (= 5 x SK_CAP) para nao cortar skills de 1 robo (elastica, lider); o teto
que vale e o do time (SK_CAP 4,0).
"""
import argparse
import math
import os
import random
import re
import sys
from multiprocessing import Pool

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
os.chdir(os.path.join(ROOT, "game"))

import pygame  # noqa: E402

import career  # noqa: E402
import campaign as cm  # noqa: E402
import garage as gm  # noqa: E402
import prefs  # noqa: E402

# nunca le/grava os saves reais: stores em memoria; torcida OFF (warm de torcida e caro e nao muda nada)
gm._store_get = cm._store_get = career._store_get = lambda: None
gm._store_set = cm._store_set = career._store_set = lambda t: True
prefs._store_get = lambda: '{"v": 1, "crowd": "OFF"}'
prefs._store_set = lambda t: True
prefs.reset_cache()

import robot_league as rl  # noqa: E402
import robots  # noqa: E402
import skills  # noqa: E402
import soccer  # noqa: E402

DT = 1 / 60
GAP = 9                    # adversario = F - GAP (V+E/2 ~ 50% sem skills)
SLOPE = 1.8                # pontos de V+E/2 por ponto de F (regressao do motor, calib_campaign)
VARIANTS = 10
_g = None


def _game():
    global _g
    if _g is None:
        pygame.init()
        _g = soccer.Game(pygame.display.set_mode((soccer.W, soccer.H)))
    return _g


def holders(sid):
    """Indices dos titulares (GK, DEF, MID, MID, ATT) que recebem a skill na medicao."""
    s = skills.ALL[sid]
    if s.get("aura"):
        return (2,)
    return tuple(i for i, r in enumerate(rl.ROLES) if r in s["roles"])


def team(F, k, sid=None, rank=1):
    t = rl.match_cfg(rl.opponent_team("A", (50, 120, 255), F, 101 + k))
    if sid is not None:
        for i in holders(sid):
            t["squad"][i]["skills"] = ((sid, rank, 0),)
    return t


def one(args):
    F, sid, rank, seed = args
    g = _game()
    k = seed % VARIANTS
    home = team(F, k, sid, rank)
    away = rl.match_cfg(rl.opponent_team("B", (235, 65, 65), F - GAP, 501 + k))
    if seed % 2:
        home, away = away, home
    random.seed(seed)
    old = soccer.BATTERY_ON
    soccer.BATTERY_ON = True
    try:
        g.start_robot_match(home, away, lambda s, e: None, tuning=robots.TUNING_ROBOTS)
        while g.state != "over":
            g.step(DT)
        a, b = g.score if seed % 2 == 0 else g.score[::-1]
        g.match_sink = None
        return 1.0 if a > b else (0.5 if a == b else 0.0)
    finally:
        soccer.BATTERY_ON = old


def measure(pool, F, sid, rank, n):
    """Lista de pontos (1/0,5/0) por seed 0..n-1."""
    return pool.map(one, [(F, sid, rank, s) for s in range(n)], chunksize=5)


def mean(v):
    return sum(v) / len(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--F", default="55,65,75")
    ap.add_argument("--ranks", default="1,3")
    ap.add_argument("--skills", default="", help="ids (padrao: as 16 + as 11 especiais)")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--json", default="")
    ap.add_argument("--write", action="store_true", help="grava SKILL_FORCE em game/skills.py")
    a = ap.parse_args()
    Fs = [int(x) for x in a.F.split(",")]
    ranks = [int(x) for x in a.ranks.split(",")]
    ids = [x for x in a.skills.split(",") if x] or list(skills.ALL)
    base = {}
    rows = []
    with Pool(a.procs) as pool:
        for F in Fs:
            base[F] = measure(pool, F, None, 1, a.n)
            print("base F=%d O=%d: V+E/2 %.1f" % (F, F - GAP, 100 * mean(base[F])), flush=True)
        print("\n%-14s %-4s %2s | %s | %7s %5s | %6s" % ("skill", "tipo", "r", " ".join("F%d" % F for F in Fs),
                                                      "delta", "ep", "F/robo"))
        for sid in ids:
            rks = ranks if sid in skills.SKILLS else [1]
            for rank in rks:
                ds, diffs = [], []
                for F in Fs:
                    pts = measure(pool, F, sid, rank, a.n)
                    ds.append(100 * (mean(pts) - mean(base[F])))
                    diffs.extend(x - y for x, y in zip(pts, base[F]))
                d = mean(ds)
                sd = math.sqrt(sum((x - mean(diffs)) ** 2 for x in diffs) / (len(diffs) - 1))
                ep = 100 * sd / math.sqrt(len(diffs))
                nh = len(holders(sid))
                force = d / SLOPE * 5.0 / nh
                rows.append({"id": sid, "rank": rank, "deltas": ds, "delta": d, "ep": ep, "holders": nh,
                             "force": force, "delta_robot": d / nh})
                print("%-14s %-4s %2d | %s | %+7.2f %5.2f | %+6.2f" % (
                    sid, skills.ALL[sid]["kind"], rank, " ".join("%+5.1f" % x for x in ds), d, ep, force), flush=True)
    table = build_table(rows)
    print("\nSKILL_FORCE (pontos de F por robo, r1/r2/r3; >= 0, monotono, teto %.1f):" % skills.ROBOT_SK_CAP)
    for sid, v in table.items():
        print("  %-14s %s" % (sid, v))
    if a.json:
        import json
        json.dump({"rows": rows, "table": table, "n": a.n, "F": Fs, "gap": GAP}, open(a.json, "w"), indent=1)
    if a.write:
        write_table(table)


def build_table(rows):
    """{id: (r1, r2, r3)} a partir das linhas medidas (interpola r2; >= 0; monotono; teto por robo)."""
    by = {}
    for r in rows:
        by.setdefault(r["id"], {})[r["rank"]] = r["force"]
    out = {}
    for sid, m in by.items():
        f1 = m.get(1, m.get(2, m.get(3, 0.0)))
        f3 = m.get(3, f1)
        f2 = m.get(2, (f1 + f3) / 2.0)
        v = [max(0.0, x) for x in (f1, f2, f3)]
        v[1] = max(v[0], v[1])
        v[2] = max(v[1], v[2])
        out[sid] = tuple(round(min(skills.ROBOT_SK_CAP, x), 2) for x in v)
    return out


def write_table(table):
    path = os.path.join(ROOT, "game", "skills.py")
    src = open(path, encoding="utf-8").read()
    cur = dict(skills.SKILL_FORCE)
    cur.update(table)
    lines = ["# SKILL_FORCE-BEGIN (gerado por tests/calib_skills.py --write; nao editar a mao)",
             "SKILL_FORCE = {"]
    for sid in skills.ALL:
        if sid in cur:
            lines.append('    "%s": (%s),' % (sid, ", ".join("%.2f" % x for x in cur[sid])))
    lines += ["}", "# SKILL_FORCE-END"]
    new, k = re.subn(r"# SKILL_FORCE-BEGIN.*?# SKILL_FORCE-END", "\n".join(lines), src, flags=re.S)
    if k != 1:
        raise SystemExit("marcadores SKILL_FORCE-BEGIN/END nao encontrados em game/skills.py")
    open(path, "w", encoding="utf-8").write(new)
    print("gravado:", path)


if __name__ == "__main__":
    main()
