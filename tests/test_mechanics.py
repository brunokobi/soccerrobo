"""Testes de mecanica (passos 4-8) com o TUNING novo e a bateria ligados por monkeypatch local.

Uso (da raiz): SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_mechanics.py [p4 p5 ...]
Alvos numericos sao SOFT: imprime o numero medido e "ALVO OK/NAO ATINGIDO" (calibragem = passo 9).
Verificacoes estruturais (direcao do efeito) sao asserts duros.
"""
import contextlib
import math
import os
import random
import statistics
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(os.path.dirname(HERE), "game")
sys.path.insert(0, GAME)
os.chdir(GAME)

import pygame  # noqa: E402
from pygame import Vector2 as V  # noqa: E402
import robots  # noqa: E402
import soccer  # noqa: E402

pygame.init()
_scr = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(_scr)
DT = 1 / 60
REPORT = []


@contextlib.contextmanager
def new_mechanics(tuning=None, battery=True):
    """Liga o TUNING novo (ou o dado) e a bateria; restaura ao final."""
    old = (soccer.ACTIVE_TUNING, soccer.BATTERY_ON)
    soccer.ACTIVE_TUNING = tuning or robots.TUNING
    soccer.BATTERY_ON = battery
    try:
        yield
    finally:
        soccer.ACTIVE_TUNING, soccer.BATTERY_ON = old


def set_attrs(p, **over):
    """Sobrescreve atributos de um Player e recalcula f/spd/s sob o tuning ativo."""
    p.robot = dict(p.robot)
    p.robot.update(over)
    p.f = robots.factors(p.robot, soccer.ACTIVE_TUNING)
    p.s = robots.mean_attr(p.robot)
    p.spd = p.f.speed


def report(name, value, target=None, ok=None):
    flag = "" if ok is None else ("  [ALVO OK]" if ok else "  [ALVO NAO ATINGIDO]")
    line = "%-46s %s%s%s" % (name, value, ("   (alvo: %s)" % target) if target else "", flag)
    REPORT.append(line)
    print(line)


def fresh_match(ovr_a=65, ovr_b=65, seed=0):
    random.seed(seed)
    cfg = lambda n, o: {"name": n, "color": (50, 120, 255) if n == "A" else (235, 65, 65),
                        "squad": [("x%d" % i, o) for i in range(5)]}
    g.start_career_match(cfg("A", ovr_a), cfg("B", ovr_b))
    g.state = "play"


# ---------------------------------------------------------------- passo 4
def test_p4_battery():
    with new_mechanics():
        fresh_match()
        p = g.teams[0].players[2]
        # parado recarrega
        p.bat, p.vel = 0.5, V()
        for _ in range(600):
            g.tick_battery(p, DT)
        assert p.bat > 0.5, p.bat
        regen = p.bat
        # correndo drena
        p.bat = 1.0
        p.vel = V(soccer.PLAYER_SPEED * p.spd * 0.93, 0)
        for _ in range(600):
            g.tick_battery(p, DT)
        assert p.bat < 1.0, p.bat
        drain = p.bat
        report("p4 recarga parado 10s (0.5 ->)", "%.3f" % regen)
        report("p4 dreno correndo 10s (1.0 ->)", "%.3f" % drain)

        # velocidade cai com bat<0.3 (steer ate saturar)
        def top(bat):
            q = g.teams[0].players[2]
            q.bat, q.vel = bat, V()
            for _ in range(120):
                g.steer(q, V(1, 0), soccer.PLAYER_SPEED, DT)
            return q.vel.length()
        v_full, v_low = top(1.0), top(0.1)
        assert v_low < v_full * 0.9, (v_low, v_full)
        report("p4 vel bat=1.0 / bat=0.1", "%.1f / %.1f (x%.2f)" % (v_full, v_low, v_low / v_full))

        # log de bateria por partida (min/medio por jogador ao fim)
        mins, means = [], []
        for seed in range(6):
            fresh_match(70, 70, seed)
            while g.state != "over":
                g.step(DT)
            bats = [q.bat for t in g.teams for q in t.players]
            mins.append(min(bats))
            means.append(sum(bats) / len(bats))
        report("p4 bat fim de jogo: min / medio (6 jogos)", "%.2f / %.2f" % (statistics.mean(mins), statistics.mean(means)),
               "quem mais corre 0.35-0.45", 0.30 <= statistics.mean(mins) <= 0.50)


# ---------------------------------------------------------------- passo 5
def _shot_stats(p, n=400):
    """n chutes da IA a 280 px do gol, gol vazio: (potencia media, desvio do angulo em graus)."""
    t = p.team
    b = g.ball
    pw, errs = [], []
    for _ in range(n):
        p.pos = V(t.target_x - t.dir * 280, soccer.CY)
        b.owner, b.vel, b.pos = None, V(), V(p.pos)
        g.ai_shoot(p)
        pw.append(b.vel.length())
        errs.append(V(t.dir, 0).angle_to(b.vel))
    return statistics.mean(pw), statistics.pstdev(errs)


def test_p5_power_error():
    with new_mechanics():
        random.seed(1)
        g.new_match(1)                       # 1P: DEF=Tanque, ATT=Velocista (atributos base 65)
        tank, fast = g.teams[0].players[1], g.teams[0].players[4]
        pt, _ = _shot_stats(tank)
        pf, _ = _shot_stats(fast)
        report("p5 potencia IA Tanque vs Velocista", "%.1f vs %.1f" % (pt, pf), "Tanque > Velocista", pt > pf)
        # mesmo papel (MID), so o chassis muda: isola o efeito do chassis na potencia
        mid = g.teams[0].players[2]
        pw = {}
        for ch in ("Tanque", "Velocista"):
            set_attrs(mid, **robots.from_overall(65, "MID", ch))
            pw[ch] = _shot_stats(mid)[0]
        report("p5 potencia IA mesmo papel MID Tanque vs Velocista", "%.1f vs %.1f" % (pw["Tanque"], pw["Velocista"]),
               "Tanque > Velocista", pw["Tanque"] > pw["Velocista"])
        # kick() direto: mesmo input, potencia final cresce com chu
        lo, hi = g.teams[0].players[2], g.teams[0].players[3]
        set_attrs(lo, chu=40)
        set_attrs(hi, chu=90)
        res = []
        for q in (lo, hi):
            g.ball.owner = q
            g.kick(q, V(1, 0), 600)
            res.append(g.ball.vel.length())
        assert res[1] > res[0], res
        report("p5 kick(600) chu 40 vs 90", "%.0f vs %.0f" % tuple(res))
        # dispersao de erro (chute)
        set_attrs(lo, chu=40)
        set_attrs(hi, chu=90)
        s_lo, s_hi = _shot_stats(lo)[1], _shot_stats(hi)[1]
        assert s_lo > s_hi, (s_lo, s_hi)
        report("p5 dispersao chute (graus) chu 40 vs 90", "%.2f vs %.2f" % (s_lo, s_hi))
        # dispersao de passe (ctr)
        b = g.ball
        devs = {}
        for ctr in (40, 90):
            p, q = g.teams[0].players[2], g.teams[0].players[4]
            set_attrs(p, ctr=ctr)
            ds = []
            for _ in range(400):
                p.pos, q.pos, q.vel = V(400, 300), V(700, 300), V()
                b.owner = None
                g.send_pass(p, q)
                ds.append(V(1, 0).angle_to(b.vel))
            devs[ctr] = statistics.pstdev(ds)
        assert devs[40] > devs[90], devs
        report("p5 dispersao passe (graus) ctr 40 vs 90", "%.2f vs %.2f" % (devs[40], devs[90]))
        # erro de mira humano: so abaixo de 65
        q = g.teams[0].players[2]
        set_attrs(q, chu=65)
        st = random.getstate()
        assert soccer.HUMAN_AIM_ERR * max(0.0, 0.65 - q.f.g_chu) == 0
        random.setstate(st)
        report("p5 erro humano chu 40 / 65 / 90 (graus)",
               " / ".join("%.1f" % (soccer.HUMAN_AIM_ERR * max(0.0, 0.65 - c / 100)) for c in (40, 65, 90)))
        assert soccer.HUMAN_AIM_ERR * (0.65 - 0.40) >= 6.0       # perceptivel abaixo de 65


# ---------------------------------------------------------------- passo 6
def _duel(o_ctr, q_def=65, reps=200, max_s=10.0, seed=5):
    """1x1: o (dono da bola, ctr dado) vs q (marcador). Devolve (tempo medio com posse, % que perdeu)."""
    random.seed(seed)
    times, lost = [], 0
    for _ in range(reps):
        g.new_match(1)
        o, q = g.teams[0].players[2], g.teams[1].players[2]
        set_attrs(o, ctr=o_ctr)
        set_attrs(q, **{"def": q_def})
        o.pos, q.pos = V(500, 300), V(500 + soccer.PR * 2, 300)
        o.vel = q.vel = V()
        g.ball.owner = o
        t = 0.0
        while t < max_s:
            g.tick_timers(DT)
            g.ball_interactions()
            t += DT
            if g.ball.owner is not o:
                lost += 1
                break
        times.append(t)
    return statistics.mean(times), lost / reps


def test_p6_duel():
    with new_mechanics():
        t_hi, l_hi = _duel(90)
        t_lo, l_lo = _duel(40)
        assert t_hi > t_lo, (t_hi, t_lo)
        report("p6 duelo 1x1 posse media (s) ctr 90 vs 40", "%.2f vs %.2f (perdeu %.0f%% vs %.0f%%)" % (t_hi, t_lo, 100 * l_hi, 100 * l_lo),
               "ctr alto mantem mais", t_hi > t_lo)
        # fumble: bola solta a 400 px/s, 1000 tentativas: ctr baixo escapa mais
        res = {}
        for ctr in (40, 90):
            random.seed(7)
            esc = 0
            for _ in range(1000):
                g.new_match(1)
                p = g.teams[0].players[2]
                set_attrs(p, ctr=ctr)
                p.pos, p.cd = V(500, 300), 0.0
                b = g.ball
                b.owner, b.pos, b.vel = None, V(p.pos), V(-400, 0)
                g.ball_interactions()
                esc += b.owner is not p
            res[ctr] = esc / 1000
        assert res[40] > res[90], res
        report("p6 fumble bola a 400px/s ctr 40 vs 90", "%.1f%% vs %.1f%%" % (100 * res[40], 100 * res[90]))


# ---------------------------------------------------------------- passo 7
def test_p7_gk():
    with new_mechanics():
        res = {}
        for d in (40, 90):
            random.seed(99 + d)      # sequencias independentes (a mesma sequencia acopla os dois lados)
            saves = 0
            n = 3000
            for _ in range(n):
                g.new_match(1)
                gk = g.teams[1].players[0]
                set_attrs(gk, **{"def": d})
                gk.cd = 0.0
                b = g.ball
                gk.pos = V(g.teams[1].goal_x - 30, soccer.CY)
                b.owner, b.pos, b.vel = None, V(gk.pos + V(-18, 0)), V(700, 0)
                g.ball_interactions()
                saves += b.owner is gk
            res[d] = saves
        assert res[90] > res[40], res
        ratio = res[90] / max(1, res[40])
        report("p7 defesas em 3000 chutes def 40 vs 90", "%d vs %d (+%.0f%%)" % (res[40], res[90], 100 * (ratio - 1)),
               "+35-50%", 1.3 <= ratio <= 1.55)
        # velocidade / antecipacao: fatores
        fa = robots.factors({"vel": 40, "ace": 40, "def": 50, "chu": 50, "ctr": 50, "vis": 40, "bat": 50, "qi": 50}, soccer.ACTIVE_TUNING)
        fb = robots.factors({"vel": 90, "ace": 90, "def": 50, "chu": 50, "ctr": 50, "vis": 90, "bat": 50, "qi": 50}, soccer.ACTIVE_TUNING)
        report("p7 gk_speed / gk_lead fraco vs forte", "%.0f/%.2f vs %.0f/%.2f" % (fa.gk_speed, fa.gk_lead, fb.gk_speed, fb.gk_lead))
        assert fb.gk_speed > fa.gk_speed and fb.gk_lead > fa.gk_lead


# ---------------------------------------------------------------- passo 8
def _boost_team(team, delta):
    for p in team.players:
        set_attrs(p, qi=min(99, max(20, p.robot["qi"] + delta)), vis=min(99, max(20, p.robot["vis"] + delta)))


def test_p8_vision_qi(n=400):
    with new_mechanics():
        w = d = l = 0
        goals = 0
        for i in range(n):
            home_a = i % 2 == 0
            fresh_match(65, 65, 1000 + i)
            _boost_team(g.teams[0], +20 if home_a else -20)
            _boost_team(g.teams[1], -20 if home_a else +20)
            while g.state != "over":
                g.step(DT)
            ga, gb = (g.score[0], g.score[1]) if home_a else (g.score[1], g.score[0])
            goals += ga + gb
            w += ga > gb
            l += ga < gb
            d += ga == gb
        rate = w / n
        report("p8 qi/vis +20 vs -20 (V/E/D, %d jogos)" % n, "%d/%d/%d  vitorias %.0f%%  (V+E/2 %.0f%%)  gols/jogo %.2f" % (
            w, d, l, 100 * rate, 100 * (w + d / 2) / n, goals / n), ">=55% vitorias", rate >= 0.55)


TESTS = [("p4", test_p4_battery), ("p5", test_p5_power_error), ("p6", test_p6_duel),
         ("p7", test_p7_gk), ("p8", test_p8_vision_qi)]

if __name__ == "__main__":
    sel = sys.argv[1:] or [k for k, _ in TESTS]
    for k, fn in TESTS:
        if k in sel:
            fn()
            print("ok", fn.__name__)
    print("\n== resumo ==")
    print("\n".join(REPORT))
