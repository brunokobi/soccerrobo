# -*- coding: utf-8 -*-
"""Fase 4 / Onda B, passos B6-B9: skills no MOTOR (soccer.py), FX das skills, garagem/campanha (B8) e
forca das skills em team_rating (B9).

Rodar da raiz:  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_skills_engine.py [teste ...]

NUNCA toca ~/.soccerpy_*.json: stores de prefs/campanha/garagem/carreira vao para dicts em memoria
(trocados ANTES de criar o Game); as gravacoes da garagem e da carreira sao sentinelas que falham.
"""
import copy
import os
import random
import subprocess
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "game"))
sys.path.insert(0, HERE)
os.chdir(os.path.join(ROOT, "game"))

import pygame  # noqa: E402

import campaign as cm  # noqa: E402
import career  # noqa: E402
import garage as gm  # noqa: E402
import prefs  # noqa: E402

MEM = {}


def _forbid(name):
    def f(*a, **k):
        raise AssertionError("%s chamada no teste" % name)
    return f


cm._store_get = lambda: MEM.get("camp")
cm._store_set = lambda t: MEM.__setitem__("camp", t) or True
cm._store_set_bad = lambda t: MEM.__setitem__("camp_bad", t) or True
gm._store_get = lambda: None
gm._store_set = _forbid("garage._store_set")
gm._store_set_bad = _forbid("garage._store_set_bad")
career._store_get = lambda: None
career._store_set = _forbid("career._store_set")
PREFS = {"raw": '{"v": 1, "crowd": "OFF"}'}
prefs._store_get = lambda: PREFS["raw"]
prefs._store_set = lambda text: PREFS.__setitem__("raw", text) or True
prefs.reset_cache()

import parts  # noqa: E402
import robot_league as RL  # noqa: E402
import robots  # noqa: E402
import skills as S  # noqa: E402
import soccer  # noqa: E402
from soccer import V  # noqa: E402

import sim_harness as H  # noqa: E402  (usa os stores ja trocados; cria o proprio Game)

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)
PASS, FAIL = [], []
GK, DEF, MID1, MID2, ATT = range(5)


def set_crowd(level):
    PREFS["raw"] = '{"v": 1, "crowd": "%s"}' % level
    prefs.reset_cache()


def cfg(name, ovr, seed, sk=None, items=None, tactic=None):
    """Time do Modo Robos; sk = {indice do titular: [(id, rank)]}."""
    c = RL.match_cfg(RL.opponent_team(name, (50, 120, 255) if name == "A" else (235, 65, 65), ovr, seed))
    for i, lst in (sk or {}).items():
        c["squad"][i]["skills"] = tuple(lst)
    if items:
        c["items"] = tuple(items)
    if tactic:
        c["tactic"] = tactic
    return c


def start(sk=None, away_sk=None, seed=1, items=None, tactic=None, ovr=60):
    random.seed(seed)
    g.start_robot_match(cfg("A", ovr, 11, sk, items, tactic), cfg("B", ovr, 22, away_sk), lambda s, e: None,
                        tuning=robots.TUNING_ROBOTS)
    g.state = "play"
    return g.teams[0], g.teams[1]


def play_out(max_steps=60 * 100):
    n = 0
    while g.state != "over" and n < max_steps:
        g.step(1 / 60)
        n += 1
    g.match_sink = None
    return list(g.score)


def park(team, x0=None):
    """Tira todos os robos do lance: espalhados no proprio campo, parados."""
    for k, p in enumerate(team.players):
        x = team.goal_x + team.dir * (40 + 30 * k) if x0 is None else x0
        p.pos = V(x, soccer.PITCH.top + 40 + 60 * k)
        p.vel = V()


def tick_all(n=soccer.SK_EVAL_EVERY):
    """n passos de tick_skills (todos os grupos sao avaliados em SK_EVAL_EVERY passos)."""
    for _ in range(n):
        g.tick_skills(1 / 60)


# ------------------------------------------------------------------------- goldens / flags
def test_golden_unchanged_flags_off():
    py = sys.executable
    for mode in ("golden", "golden-new"):
        out = subprocess.run([py, os.path.join(HERE, "sim_harness.py"), mode, "--check"], cwd=ROOT,
                             capture_output=True, text=True, timeout=900)
        line = out.stdout.strip().splitlines()[-1]
        assert out.returncode == 0 and "80/80" in line, (mode, line, out.stderr[-500:])


def test_empty_skills_tuple_equals_absent_key():
    """20 partidas: `skills=()` explicito == elenco sem a chave (sk_on desligado, mesmos placares)."""
    for seed in range(20):
        res = []
        for empty in (False, True):
            h, a = cfg("A", 58, 3 + seed), cfg("B", 56, 9 + seed)
            if empty:
                for e in h["squad"] + a["squad"]:
                    e["skills"] = ()
            random.seed(seed)
            g.start_robot_match(h, a, lambda s, e: None, tuning=robots.TUNING_ROBOTS)
            assert not g.sk_on
            res.append(play_out())
        assert res[0] == res[1], (seed, res)


def test_sk_on_only_with_skills():
    g.new_match(1)
    assert not g.sk_on                                      # amistoso
    for legacy in (True, False):
        with H.mode(legacy):
            g.start_career_match(H.cfg("A", 65), H.cfg("B", 60))  # carreira/golden: tuplas (nome, ovr)
            assert not g.sk_on and all(not p.skills for t in g.teams for p in t.players)
            assert g.ball.curve == 0.0 and all(p.tk_ext == 0.0 for t in g.teams for p in t.players)
    start()                                                 # Modo Robos sem skills
    assert not g.sk_on
    start({ATT: [("arrancada", 1)]})
    assert g.sk_on
    start(items=["cafe"])                                   # so consumivel tambem liga (aura de time)
    assert g.sk_on
    g.match_sink = None


def test_global_rng_untouched_by_skills():
    """O maquinario das skills nao consome o random global: uma skill que nao muda nada na simulacao
    (Defesa Elastica num MEIA: gk_save/gk_speed nao valem fora do gol, custo 0) liga sk_on, dispara
    varias vezes e o placar/eventos/estado do RNG ficam IDENTICOS ao jogo sem skills."""
    outs = []
    for sk in (None, {MID1: [("elastica", 1)], MID2: [("elastica", 3)]}):
        random.seed(77)
        g.start_robot_match(cfg("A", 60, 5, sk), cfg("B", 60, 6), lambda s, e: None, tuning=robots.TUNING_ROBOTS)
        on = g.sk_on
        sc = play_out()
        outs.append((sc, [dict(e) for e in g.events], random.getstate(), on, dict(g.sk_count)))
    assert outs[0][:3] == outs[1][:3]
    assert outs[1][3] and outs[1][4].get("elastica", 0) > 0, outs[1][4]
    # sk_setup / tick / curva usam so o sk_rng
    start({ATT: [("curva", 3)], DEF: [("choque", 1), ("muralha", 1)], MID1: [("succao", 1)]})
    st = random.getstate()
    tick_all(30)
    p = g.teams[0].players[ATT]
    p.sk_curve, p.sk_curve_t = 70.0, 0.8
    g.sk_on_kick(p, V(1, 0), 600.0)
    g.ball_curve(g.ball, 1 / 60)
    assert random.getstate() == st
    g.match_sink = None


# ------------------------------------------------------------------------- efeitos por skill
def test_passives_aura_and_items_compile():
    start({GK: [("lancador", 1)], MID1: [("leitura", 2), ("lider", 1)]}, items=["cera_turbo", "fita_isolante"])
    t = g.teams[0]
    ref = [robots.factors(e["attrs"], robots.TUNING_ROBOTS) for e in cfg("A", 60, 11)["squad"]]
    lid = S.scaled_mods("lider", 1)
    for k, p in enumerate(t.players):
        sp = ref[k].speed * lid["speed"][1] * 1.05
        assert abs(p.f.speed - sp) < 1e-9 and abs(p.spd - p.f.speed) < 1e-12, k   # aura + Cera Turbo
    gk = t.players[GK]
    assert abs(gk.f.pass_range - min(1600.0, ref[GK].pass_range * 1.4)) < 1e-6
    assert abs(gk.f.gk_save - min(0.95, ref[GK].gk_save + 0.10)) < 1e-9          # Fita Isolante: so o GK
    assert abs(t.players[DEF].f.gk_save - ref[DEF].gk_save) < 1e-12
    m = t.players[MID1]
    assert abs(m.f.dec_err - ref[MID1].dec_err * (1 + (0.7 - 1) * 1.25)) < 1e-9     # leitura rank 2
    o = g.teams[1].players[MID1]                                                    # adversario intacto
    assert abs(o.f.speed - robots.factors(cfg("B", 60, 22)["squad"][MID1]["attrs"], robots.TUNING_ROBOTS).speed) < 1e-12
    g.match_sink = None


def test_arrancada_speeds_up_with_ball_and_free_lane():
    a, b = start({ATT: [("arrancada", 1)]})
    p = a.players[ATT]
    for q in b.players:                                     # adversarios ATRAS do atacante (campo livre)
        q.pos = V(p.pos.x - a.dir * 150, q.pos.y)
    g.ball.owner = p
    p.bat = 1.0
    tick_all()
    assert p.sk_cur == "arrancada" and abs(p.spd - p.spd_base * 1.35) < 1e-9
    assert abs(p.bat - 0.9) < 1e-9                          # custo 0,10
    # mesma conducao (steer do motor, 0,5 s) com e sem a variante: mais rapido com a skill
    v = {}
    for k, f in (("on", p.f_var["arrancada"]), ("off", p.f_base)):
        q = copy.copy(p)
        q.f, q.spd, q.vel, q.bat = f, f.speed, V(), 1.0
        for _ in range(30):
            g.steer(q, V(a.dir, 0), soccer.PLAYER_SPEED * soccer.AI_SPEED * 0.92, 1 / 60)
        v[k] = q.vel.length()
    assert v["on"] > v["off"] * 1.3, v
    # com adversario a frente (< 80 px) nao dispara
    start({ATT: [("arrancada", 1)]})
    p = g.teams[0].players[ATT]
    g.ball.owner = p
    g.teams[1].players[DEF].pos = p.pos + V(g.teams[0].dir * 50, 0)
    tick_all()
    assert p.sk_cur is None
    g.match_sink = None


def test_muralha_raises_tackles_near_goal():
    """Muralha: adversario com a bola perto do gol -> desarme x1,5 e raio +6 px; em 400 tentativas
    (motor: ball_interactions) desarma bem mais que sem a skill."""
    wins = {}
    for sk in ({DEF: [("muralha", 1)]}, None):
        a, b = start(sk)
        d = a.players[DEF]
        att = b.players[ATT]
        park(b)
        att.pos = V(a.goal_x + a.dir * 150, soccer.CY)
        d.pos = att.pos + V(a.dir * -35, 0)                    # 35 px: fora do raio base (32), dentro com +6
        g.ball.owner = att
        g.ball.pos = V(att.pos)
        tick_all()
        if sk:
            assert d.sk_cur == "muralha" and d.tk_ext == 6.0
            assert abs(d.f.tackle - min(1.0, d.f_base.tackle * 1.5)) < 1e-9
            assert abs(d.spd - d.spd_base * 0.85) < 1e-9
        rng_state = random.getstate()
        random.seed(5)
        n = 0
        for _ in range(400):
            g.ball.owner = att
            d.tackle_cd = 0.0
            for q in a.players:
                if q is not d:
                    q.tackle_cd = 9.0
            g.ball_interactions()
            n += g.ball.owner is d
        random.setstate(rng_state)
        wins["on" if sk else "off"] = n
    assert wins["off"] == 0 and wins["on"] > 150, wins
    g.match_sink = None


def test_elastica_more_saves():
    saves = {}
    for sk in ({GK: [("elastica", 1)]}, None):
        a, b = start(sk)
        park(b)
        gk = a.players[GK]
        gk.pos = V(a.goal_x + a.dir * 30, soccer.CY)
        g.ball.owner = None
        g.ball.pos = V(a.goal_x + a.dir * 200, soccer.CY)
        g.ball.vel = V(-a.dir * 700, 0)
        tick_all()
        if sk:
            assert gk.sk_cur == "elastica"
            assert abs(gk.f.gk_save - min(0.95, gk.f_base.gk_save + 0.25)) < 1e-9
            assert abs(gk.f.gk_speed - gk.f_base.gk_speed * 1.3) < 1e-9
        st = random.getstate()
        random.seed(9)
        n = 0
        for _ in range(400):
            g.ball.owner = None
            g.ball.pos = gk.pos + V(a.dir * 12, 0)
            g.ball.vel = V(-a.dir * 700, 0)
            gk.cd = 0.0
            g.ball_interactions()
            n += g.ball.owner is gk
        random.setstate(st)
        saves["on" if sk else "off"] = n
    assert saves["on"] > saves["off"] + 60, saves
    g.match_sink = None


def test_recarga_recharges_standing_still():
    a, b = start({MID1: [("recarga", 1)]})
    p = a.players[MID1]
    p.bat, p.vel = 0.2, V()
    tick_all()
    assert p.sk_cur == "recarga"
    gain = {}
    for k, f in (("on", p.f_var["recarga"]), ("off", p.f_base)):
        q = copy.copy(p)
        q.f, q.bat, q.vel = f, 0.2, V()
        for _ in range(60):
            g.tick_battery(q, 1 / 60)
        gain[k] = q.bat - 0.2
    assert gain["on"] > gain["off"] * 2.9 > 0, gain
    g.match_sink = None
    a, b = start({MID2: [("recarga", 1)]})
    p2 = a.players[MID2]
    p2.bat, p2.vel = 0.2, V(soccer.PLAYER_SPEED * p2.spd, 0)
    tick_all()
    assert p2.sk_cur is None
    g.match_sink = None


def test_choque_stuns_and_zaps():
    a, b = start({DEF: [("choque", 1)]})
    d, o = a.players[DEF], b.players[ATT]
    park(b)
    o.pos = V(soccer.CX, soccer.CY)
    d.pos = o.pos + V(20, 0)
    g.ball.owner = o
    d.f = S.apply_mods(d.f, {"tackle": ("add", 1.0)})       # desarme certo (so neste teste)
    o.f = S.apply_mods(o.f, {"shield": ("add", 5.0)})
    for q in a.players:
        q.tackle_cd = 0.0 if q is d else 9.0
    bat0 = d.bat
    g.ball_interactions()
    assert g.ball.owner is d
    assert abs(o.cd - (0.7 + 0.5)) < 1e-9, o.cd            # 0,5 s a mais sem dominar
    assert d.sk_zap is not None and d.sk_zap[0] is o and abs(d.bat - (bat0 - 0.05)) < 1e-9
    assert d.sk_ready["choque"] > g.sk_t                   # recarga: o proximo desarme nao atordoa
    g.ball.owner = o
    o.cd = 0.0
    d.tackle_cd = 0.0
    g.ball_interactions()
    assert g.ball.owner is d and abs(o.cd - 0.7) < 1e-9
    g.match_sink = None


def test_curva_bends_ball():
    a, b = start({ATT: [("curva", 1)]})
    p = a.players[ATT]
    park(b, a.goal_x + a.dir * 60)                         # fora do caminho do chute
    gk = b.players[GK]
    gk.pos = V(a.target_x - a.dir * 90, soccer.CY + 40)     # goleiro fora da linha
    p.pos = V(a.target_x - a.dir * 300, soccer.CY)
    g.ball.owner = p
    bat0 = p.bat
    g.ai_shoot(p)
    b0 = g.ball
    assert b0.curve != 0.0 and p.sk_cur == "curva" and p.bat <= bat0 - 0.06   # custo 0,06 + o do chute
    assert abs(abs(b0.curve) - 70.0) < 1e-9 and abs(p.f.shot_err - p.f_base.shot_err * 0.6) < 1e-9
    v0 = V(b0.vel)
    for _ in range(12):
        g.update_ball(1 / 60)
    ang = abs(v0.angle_to(b0.vel))
    ang = min(ang, 360 - ang)
    assert 8 < ang < 20, ang                               # ~70 graus/s por 0,2 s
    # sem goleiro fora da linha: nao dispara (a recarga nao foi gasta)
    start({ATT: [("curva", 1)]})
    a, b = g.teams
    p = a.players[ATT]
    b.players[GK].pos = V(a.target_x - a.dir * 30, soccer.CY)
    p.pos = V(a.target_x - a.dir * 300, soccer.CY)
    g.ball.owner = p
    g.ai_shoot(p)
    assert g.ball.curve == 0.0 and p.sk_cur is None
    g.match_sink = None


def test_succao_pulls_loose_ball():
    a, b = start({MID1: [("succao", 1)]})
    p = a.players[MID1]
    park(b)
    p.pos = V(soccer.CX, soccer.CY)
    p.vel = V()
    g.ball.owner = None
    g.ball.pos = p.pos + V(70, 0)
    g.ball.vel = V()
    a.chaser = p
    tick_all()
    assert p.sk_cur == "succao" and p.f.reach == p.f_base.reach + 10
    g.tick_skills(1 / 60)
    assert g.ball.vel.x < 0                               # puxada para o robo
    g.match_sink = None


def test_other_actives_switch_factors():
    """Toda ativa/condicional troca os fatores pela variante ao ligar e volta a f_base ao terminar."""
    allsk = [sid for sid, s in S.ALL.items() if s["kind"] in ("A", "C") and s["dur"] > 0]
    for sid in allsk:
        start({MID1: [(sid, 1)]})
        p = g.teams[0].players[MID1]
        g.sk_start(p, sid, g.sk_t)
        assert p.f is p.f_var[sid] and p.sk_cur == sid and p.sk_fx == S.ALL[sid]["fx"], sid
        for name, (op, v) in S.scaled_mods(sid, 1).items():
            base = getattr(p.f_base, name)
            exp = base * v if op == "mul" else base + v
            lo, hi = S._LIMITS.get(name, (None, None))
            exp = S._clamp(exp, lo, hi)
            assert abs(getattr(p.f, name) - exp) < 1e-9, (sid, name)
        for _ in range(int(S.ALL[sid]["dur"] * 60) + 2):
            g.tick_skills(1 / 60)
        assert p.sk_cur is None and p.f is p.f_base and p.tk_ext == 0.0, sid
        if sid == "overclock":                             # cansaco de 3 s depois
            assert abs(p.spd - p.spd_base * 0.9) < 1e-9
            for _ in range(3 * 60 + 2):
                g.tick_skills(1 / 60)
        assert abs(p.spd - p.spd_base) < 1e-12, sid
    g.match_sink = None


def test_matador_conditional_near_goal():
    a, b = start({ATT: [("matador", 1)]})
    p = a.players[ATT]
    p.pos = V(a.target_x - a.dir * 100, soccer.CY)
    tick_all()
    assert p.sk_condon == "matador" and p.f is p.f_var["matador"]
    p.pos = V(soccer.CX, soccer.CY)
    tick_all()
    assert p.sk_condon is None and p.f is p.f_base
    g.match_sink = None


def test_cooldown_and_battery_cost():
    a, b = start({ATT: [("arrancada", 1)]})
    p = a.players[ATT]
    for q in b.players:
        q.pos = V(p.pos.x - a.dir * 150, q.pos.y)
    g.ball.owner = p
    p.bat = 1.0
    tick_all()
    assert p.sk_cur == "arrancada"
    t_ready = p.sk_ready["arrancada"]
    assert abs(t_ready - (p.sk_fx_t + S.cooldown("arrancada", 1))) < 1e-9
    for _ in range(int(1.3 * 60)):                         # termina (1,2 s)...
        g.tick_skills(1 / 60)
    assert p.sk_cur is None
    p.bat = 1.0
    tick_all(60)                                           # ...e nao volta antes da recarga (9 s)
    assert p.sk_cur is None and g.sk_count["arrancada"] == 1
    while g.sk_t < t_ready:
        g.tick_skills(1 / 60)
    tick_all()
    assert p.sk_cur == "arrancada" and g.sk_count["arrancada"] == 2
    # bateria abaixo de custo + margem: nao dispara
    start({ATT: [("arrancada", 3)]})
    a, b = g.teams
    p = a.players[ATT]
    for q in b.players:
        q.pos = V(p.pos.x - a.dir * 150, q.pos.y)
    g.ball.owner = p
    p.bat = 0.10 + S.BAT_MARGIN - 0.01
    tick_all()
    assert p.sk_cur is None
    assert S.cooldown("arrancada", 3) == 9.0 * 0.8
    g.match_sink = None


def test_tactic_changes_priority():
    """Arrancada (ataque) e Blindagem (defesa) valendo ao mesmo tempo: a tatica escolhe."""
    got = {}
    for tac in ("ofensivo", "defensivo", "equilibrado"):
        a, b = start({MID1: [("arrancada", 1), ("blindagem", 1)]}, tactic=tac)
        p = a.players[MID1]
        for q in b.players:
            q.pos = V(p.pos.x - a.dir * 150, q.pos.y)
        b.players[DEF].pos = p.pos + V(-a.dir * 40, 0)      # perto (< 55), mas atras: campo livre a frente
        g.ball.owner = p
        p.bat = 1.0
        tick_all()
        got[tac] = p.sk_cur
    assert got == {"ofensivo": "arrancada", "defensivo": "blindagem", "equilibrado": "arrancada"}, got
    g.match_sink = None


def test_pilha_reserva_restores_once():
    a, b = start(items=["pilha_reserva"])
    p = a.players[MID2]
    p.bat = 0.1
    g.tick_skills(1 / 60)
    assert p.bat == 1.0 and a.sk_pilha == 0
    p.bat = 0.1
    g.tick_skills(1 / 60)
    assert p.bat == 0.1
    g.match_sink = None


# ------------------------------------------------------------------------- MAX, FX, desempenho
def test_max_runs_skills_without_fx():
    calls = [0]
    real = soccer.Game.draw_skill_fx

    def spy(self, *a):
        calls[0] += 1
        return real(self, *a)

    soccer.Game.draw_skill_fx = spy
    try:
        lo = {i: H.SK_LOADOUT[r] for i, r in enumerate(RL.ROLES)}
        start(lo, lo)
        g.speed_idx = 3
        for _ in range(60 * 40):
            g.step(1 / 60)
            if _ % 5 == 0:
                g.draw()
        assert sum(g.sk_count.values()) > 10, g.sk_count     # skills funcionam em MAX
        assert calls[0] == 0 and not g.fx                    # sem FX de skill (nem particulas)
    finally:
        soccer.Game.draw_skill_fx = real
        g.speed_idx = 0
        g.match_sink = None


def test_zero_surface_per_frame_with_skill_fx():
    set_crowd("ALTA")
    calls = {}
    real = soccer.Game.draw_skill_fx

    def spy(self, scr, p, pos, now):
        k = "zap" if p.sk_fx is None else p.sk_fx
        calls[k] = calls.get(k, 0) + 1
        return real(self, scr, p, pos, now)

    soccer.Game.draw_skill_fx = spy
    try:
        lo = {i: H.SK_LOADOUT[r] for i, r in enumerate(RL.ROLES)}
        for venue in ("estadio", "bairro"):
            random.seed(4)
            g.start_robot_match(cfg("A", 62, 11, lo), cfg("B", 60, 22, lo), lambda s, e: None,
                                tuning=robots.TUNING_ROBOTS, venue=venue)
            g.state = "play"
            for _ in range(40):
                g.step(1 / 60)
                g.draw()
            with H_SurfaceCounter() as sc:
                for _ in range(600):
                    g.step(1 / 60)
                    g.draw()
            assert sc.n == 0, (venue, sc.n)
            g.match_sink = None
        assert sum(calls.values()) > 50 and len(calls) >= 4, calls
    finally:
        soccer.Game.draw_skill_fx = real
        set_crowd("OFF")
        g.state = "menu"


class H_SurfaceCounter:
    def __enter__(self):
        self.real = pygame.Surface
        count = self.count = [0]

        class Counting(self.real):
            def __init__(self, *a, **k):
                count[0] += 1
                super().__init__(*a, **k)

        pygame.Surface = Counting
        return self

    def __exit__(self, *a):
        pygame.Surface = self.real

    @property
    def n(self):
        return self.count[0]


def test_ms_step_within_budget():
    """Custo das skills por passo (10 robos x 3 skills): tick_skills + ganchos <= 0,006 ms/step. Tambem
    imprime o ms_step total do harness (run-skills) com e sem skills (ruido de ~+-0,002 ms)."""
    acc = {"t": 0.0, "n": 0}
    names = ("tick_skills", "sk_on_kick", "on_steal", "sk_pre_shot", "ball_curve")
    real = {k: getattr(soccer.Game, k) for k in names}

    def wrap(k):
        f = real[k]

        def w(self, *a):
            t0 = time.perf_counter()
            r = f(self, *a)
            acc["t"] += time.perf_counter() - t0
            if k == "tick_skills":
                acc["n"] += 1
            return r
        return w

    # custo do proprio cronometro (descontado)
    t0 = time.perf_counter()
    for _ in range(20000):
        a = time.perf_counter()
        acc["t"] += time.perf_counter() - a
    acc["t"] = 0.0
    overhead = (time.perf_counter() - t0) / 20000
    for k in names:
        setattr(soccer.Game, k, wrap(k))
    try:
        H.run_skills(65, 65, 6)
    finally:
        for k in names:
            setattr(soccer.Game, k, real[k])
    per = (acc["t"] / acc["n"] - overhead) * 1000
    off = min(H.run_skills(65, 65, 6, with_skills=False)["ms_step"] for _ in range(2))
    on = min(H.run_skills(65, 65, 6)["ms_step"] for _ in range(2))
    print("  skills: %.4f ms/step (tick+ganchos) | ms_step sem %.4f com %.4f (+%.4f)" % (per, off, on, on - off))
    assert per <= 0.006, per


# ------------------------------------------------------------------------- garagem / campanha (B8/B9)
def _equip_module(gg, rb, model, rar=0):
    pc = gg.new_piece(model, rar)
    gg.inventory.append(pc)
    ok, msg = gg.equip(rb["id"], pc["id"])
    assert ok, msg


def test_match_entry_skills_tactic_items_and_rating():
    gg = gm.new_game(random.Random(3))
    base = gg.rating()
    cfg0 = gg.match_cfg()
    assert all("skills" not in e for e in cfg0["squad"]) and "tactic" not in cfg0 and "items" not in cfg0
    gg.flags[gm.MOD_FLAG] = 1
    assert gg.rating() == base                                 # mod_on sem skills: mesma forca
    rb = gg.robot(gg.lineup[4])
    _equip_module(gg, rb, "Módulo Arrancada", 2)
    S.learn_skill(rb, "leitura", 1)
    S.equip_skill(rb, "leitura")
    c = gg.match_cfg()
    e = next(x for x in c["squad"] if x["pid"] == rb["id"])
    assert e["skills"] == (("arrancada", 2, 0), ("leitura", 1, 0)) and c["tactic"] == gg.tactic
    exp = base + S.team_skill_force([S.effective_skills(r, gg.pieces_by_id()) for r in gg.lineup_robots()])
    assert abs(gg.rating() - exp) < 1e-9 and gg.rating() > base
    # teto 4,0 por time
    for r in gg.lineup_robots():
        r["skills"] = {"learned": {k: 3 for k in S.SKILL_IDS}, "equipped": ["arrancada", "curva"], "pts": 0}
    assert gg.rating() - base <= S.SK_CAP + 1e-9
    # Mochila: so itens que o jogador tem; match_F soma item_force; consumo
    gg.items = {"cera_turbo": 2, "cafe": 1}
    assert gg.set_backpack(["cera_turbo", "xyz", "spray", "cera_turbo", "cafe"]) == ["cera_turbo", "cafe"]
    assert gg.match_cfg()["items"] == ("cera_turbo", "cafe")
    assert abs(gg.match_F() - gg.rating() - 1.4) < 1e-9
    assert gg.consume_backpack() == ["cera_turbo", "cafe"]
    assert gg.items == {"cera_turbo": 1} and gg.backpack == [] and gg.match_F() == gg.rating()
    # o motor aplica os itens e as skills da garagem
    gg.set_backpack(["cera_turbo"])
    random.seed(1)
    g.start_robot_match(gg.match_cfg(), cfg("B", 50, 3), lambda s, e: None, tuning=robots.TUNING_ROBOTS)
    assert g.sk_on and g.teams[0].items == ("cera_turbo",)
    p = next(p for p in g.teams[0].players if p.pid == rb["id"])
    assert "arrancada" in p.f_var
    g.match_sink = None
    assert "backpack" not in gm.FIELDS and "backpack" not in gg.to_dict()   # transitoria: nao vai ao save


def test_campaign_act1_unchanged_and_user_F():
    """Ato 1 (antes de rw_5): mod_on desligado -> elenco sem skills, rating antigo exato; com rw_5 as skills
    entram no elenco e no user_F (rating com skill_force) e a Mochila soma item_force."""
    c = cm.new_campaign(random.Random(4))
    gg = c.garage
    assert not gg.mod_on()
    rb = gg.robot(gg.lineup[4])
    S.learn_skill(rb, "arrancada", 1)                          # mesmo aprendida, sem efeito no Ato 1
    S.equip_skill(rb, "arrancada")
    base = gm.team_rating(gg.lineup_robots(), gg.pieces_by_id())
    act = c.training_cfg()
    assert act["user_F"] == base == gg.rating()
    assert all("skills" not in e for e in act["home"]["squad"])
    cm.sync_unlocks(gg, {"reward:%s" % cm.UNLOCK_REWARD})
    assert gg.mod_on()
    act = c.training_cfg()
    assert any(e.get("skills") for e in act["home"]["squad"])
    assert abs(act["user_F"] - base - S.team_skill_force([[("arrancada", 1)], [], [], [], []])) < 1e-9
    gg.items = {"spray": 1}
    gg.set_backpack(["spray"])
    act = c.training_cfg()
    assert abs(act["user_F"] - gg.rating() - S.ITEMS["spray"]["force"]) < 1e-9
    c.record_training(1, 0)
    assert gg.items == {} and gg.backpack == []


def main():
    names = [n for n in globals() if n.startswith("test_")]
    want = sys.argv[1:]
    if want:
        names = [n for n in names if n in want or n[5:] in want]
    for n in names:
        t0 = time.perf_counter()
        try:
            globals()[n]()
            PASS.append(n)
            print("OK   %s (%.1fs)" % (n, time.perf_counter() - t0))
        except Exception as e:  # noqa: BLE001
            import traceback
            FAIL.append(n)
            print("FAIL %s: %r" % (n, e))
            traceback.print_exc()
    print("\n%d ok, %d falhas" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
