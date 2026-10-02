# -*- coding: utf-8 -*-
"""Balanco do Modo Robos: equipe do garage (5 robos x 7 pecas) vs time base (tier 0, ovr 44).

Rodar da raiz: .venv/bin/python tests/test_robot_balance.py [-n 70] [--procs 4]
Motor real (Game.start_robot_match, TUNING_ROBOTS, bateria ligada, 90 s), seeds fixas, A
mandante nas seeds pares. "% de vitoria" = (V + E/2) / n (empate vale meio).
Alvos numericos sao SOFT ([ALVO OK] / [ALVO NAO ATINGIDO]); asserts duros so onde a direcao
e segura (ordem entre raridades, faixa larga do nivel 1, overclock gasta bateria).
Nunca grava no disco (nada de Garage.save).

Referencia medida com n=300 (final): nivel1 49.3 | kit 54.0 | 7 Comuns 63.3 | Raras 66.0 | Epicas 79.5 |
Lendarias 97.3 | nivel 10 70.7 (ruido de n=70 ~ +-5 pts: os alvos soft podem oscilar com n pequeno).
Constantes ajustadas: garage.BASE_OVR 44->46 (Disco sem bonus de papel perde ~10 pts contra os
chassis de papel do oponente), garage.LEVEL_STEP 1.0->1.1, parts POWER[Epica] 13->12.
Alvo (b) (kit 55-60) fica ~1 pt abaixo: 5 Comuns somam so +0.7 de rating; subir mais exigiria
Comum ~ Rara (quebraria a ordem) ou mais pecas no kit (mudanca de design).
"""
import argparse
import copy
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

import garage as gm  # noqa: E402
import parts  # noqa: E402
import robot_league as rl  # noqa: E402
import robots  # noqa: E402
import soccer  # noqa: E402

DT = 1 / 60
N = 70
PROCS = 4
OPP_OVR = 44                 # time base do tier 0 (fixo, independe de gm.BASE_OVR)
BAL = {"motor": "Motor Escovado", "bateria": "Célula Longa", "parachoque": "Borracha",
       "chutador": "Solenoide", "succao": "Escova de Sucção", "sensor": "Infravermelho",
       "chip": "Chip de CPU"}
_g = None


# ---------------------------------------------------------------- montagem
def build_garage(rar=None, level=1, oc=0, lvl=0):
    """Garage com 5 robos titulares; rar=None = sem pecas; rar=0..3 = 7 pecas balanceadas."""
    g = gm.new_game(random.Random(7))
    for r in g.robots:
        r["slots"] = {s: None for s in parts.SLOTS}
        r["level"], r["oc"] = level, oc
    g.inventory = []
    if rar is not None:
        for r in g.robots:
            for slot in parts.SLOTS:
                pc = g.new_piece(BAL[slot], rar, lvl)
                g.inventory.append(pc)
                assert g.equip(r["id"], pc["id"])[0]
    return g


def kit_garage():
    """Starter kit como entregue por new_game (5 pecas Comuns ja equipadas)."""
    return gm.new_game(random.Random(7))


# ---------------------------------------------------------------- partidas
def _game():
    global _g
    if _g is None:
        pygame.init()
        _g = soccer.Game(pygame.display.set_mode((soccer.W, soccer.H)))
    return _g


def one(args):
    cfg_a, seed, want_bat = args
    g = _game()
    opp = rl.match_cfg(rl.opponent_team("Base", (235, 65, 65), OPP_OVR, 500 + seed))
    random.seed(seed)
    old = soccer.BATTERY_ON
    soccer.BATTERY_ON = True
    try:
        home_a = seed % 2 == 0
        h, a = (cfg_a, opp) if home_a else (opp, cfg_a)
        g.start_robot_match(h, a, lambda s, e: None, tuning=robots.TUNING_ROBOTS)
        while g.state != "over":
            g.step(DT)
        ga, gb = g.score if home_a else g.score[::-1]
        mine = g.teams[0 if home_a else 1].players
        bat = sum(p.bat for p in mine) / len(mine)
    finally:
        soccer.BATTERY_ON = old
    return ga, gb, bat


def winrate(pool, garage, n=None):
    """% de vitoria (V + E/2), V, E, D, gols/jogo, bateria media no fim, (placares por seed)."""
    n = n or N
    cfg = garage.match_cfg()
    res = pool.map(one, [(cfg, s, True) for s in range(n)], chunksize=2)
    w = sum(a > b for a, b, _ in res)
    l = sum(a < b for a, b, _ in res)
    d = n - w - l
    return {"pct": 100.0 * (w + d / 2) / n, "w": w, "d": d, "l": l,
            "goals": sum(a + b for a, b, _ in res) / n,
            "bat": sum(x for _, _, x in res) / n, "res": [(a, b) for a, b, _ in res]}


def soft(name, value, lo, hi, ok=None):
    ok = (lo <= value <= hi) if ok is None else ok
    print("%-34s %6.1f%%  (alvo %s)  %s" % (name, value, "%g-%g" % (lo, hi) if hi < 1000 else ">=%g" % lo,
                                            "[ALVO OK]" if ok else "[ALVO NAO ATINGIDO]"), flush=True)
    return ok


def main():
    global N, PROCS
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=N)
    ap.add_argument("--procs", type=int, default=PROCS)
    a = ap.parse_args()
    N, PROCS = a.n, a.procs
    fails = []

    def check(cond, msg):
        print("%s  %s" % ("OK  " if cond else "FAIL", msg), flush=True)
        if not cond:
            fails.append(msg)

    with Pool(PROCS) as pool:
        cases = [("(a) nivel 1 sem pecas", build_garage(None, 1)),
                 ("(b) starter kit (5 Comuns)", kit_garage()),
                 ("    7 Comuns/robo", build_garage(0)),
                 ("(c) todas Raras", build_garage(1)),
                 ("(d) todas Epicas", build_garage(2)),
                 ("(e) todas Lendarias", build_garage(3)),
                 ("(f) nivel 10 sem pecas", build_garage(None, 10))]
        R = {}
        for name, gg in cases:
            R[name] = winrate(pool, gg)
            r = R[name]
            print("   %-28s rating %.1f  V%d E%d D%d  gols/jogo %.2f  bat fim %.2f" % (
                name, gg.rating(), r["w"], r["d"], r["l"], r["goals"], r["bat"]), flush=True)
        base, kit, commons7, rare, epic, leg, lv10 = (R[c[0]] for c in cases)

        print("\n== alvos (soft) ==")
        soft("(a) nivel 1 sem pecas", base["pct"], 45, 55)
        soft("(b) starter kit", kit["pct"], 55, 60)
        soft("(c) todas Raras", rare["pct"], 65, 1000)
        soft("(d) todas Epicas", epic["pct"], 78, 82)
        soft("(e) todas Lendarias", leg["pct"], 88, 1000)
        soft("(f) nivel 10 sem pecas", lv10["pct"], 66, 74)

        print("\n== asserts duros ==")
        check(40 <= base["pct"] <= 60, "(a) nivel 1 sem pecas entre 40 e 60%% (%.1f)" % base["pct"])
        check(rare["pct"] > commons7["pct"], "(c) Raras > Comuns (%.1f > %.1f)" % (rare["pct"], commons7["pct"]))
        check(leg["pct"] > epic["pct"] > rare["pct"] > commons7["pct"] > base["pct"],
              "(g) ordem lendaria > epica > rara > comum > base (%.1f > %.1f > %.1f > %.1f > %.1f)" % (
                  leg["pct"], epic["pct"], rare["pct"], commons7["pct"], base["pct"]))
        check(lv10["pct"] > base["pct"], "(f) nivel 10 > nivel 1 (%.1f > %.1f)" % (lv10["pct"], base["pct"]))

        # (h) overclock
        g0, g2 = build_garage(1, 1, 0), build_garage(1, 1, 2)
        bat0 = [g0.attrs_of(r)["bat"] for r in g0.robots]
        bat2 = [g2.attrs_of(r)["bat"] for r in g2.robots]
        check(all(b2 < b0 for b0, b2 in zip(bat0, bat2)), "(h) oc=2 reduz bat efetivo (%s -> %s)" % (bat0, bat2))
        oc0, oc2 = winrate(pool, g0), winrate(pool, g2)
        print("   Raras oc=0: %.1f%%, bat fim %.3f | oc=2: %.1f%%, bat fim %.3f" % (
            oc0["pct"], oc0["bat"], oc2["pct"], oc2["bat"]))
        soft("(h) bateria restante oc=2 < oc=0", 100 * oc2["bat"], 0, 0, ok=oc2["bat"] < oc0["bat"])

    print("\n%s" % ("TUDO OK" if not fails else "FALHAS: %s" % fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
