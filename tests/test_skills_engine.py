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
    assert abs(gk.f.pass_range - min(1600.0, ref[GK].pass_range * S.scaled_mods("lancador", 1)["pass_range"][1])) < 1e-6
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
        d.pos = att.pos + V(a.dir * -35, 0)                    # 35 px: fora do raio base (32), dentro com +tk_ext
        g.ball.owner = att
        g.ball.pos = V(att.pos)
        tick_all()
        if sk:
            m = S.scaled_mods("muralha", 1)
            assert d.sk_cur == "muralha" and d.tk_ext == S.scaled_extra("muralha", 1)["tk_ext"] > 3.0
            assert abs(d.f.tackle - min(1.0, d.f_base.tackle * m["tackle"][1])) < 1e-9
            assert abs(d.spd - d.spd_base * m["speed"][1]) < 1e-9
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
            m = S.scaled_mods("elastica", 1)
            assert gk.sk_cur == "elastica"
            assert abs(gk.f.gk_save - min(0.95, gk.f_base.gk_save + m["gk_save"][1])) < 1e-9
            assert abs(gk.f.gk_speed - gk.f_base.gk_speed * m["gk_speed"][1]) < 1e-9
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
    assert saves["on"] > saves["off"] + 15, saves
    g.match_sink = None


def test_recarga_recharges_standing_still():
    a, b = start({MID1: [("recarga", 1)]})
    p = a.players[MID1]
    p.bat, p.vel = 0.2, V()
    tick_all()
    assert p.sk_cur == "recarga" and abs(p.bat - (0.2 + S.scaled_extra("recarga", 1)["bat_add"])) < 1e-9
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
    p2.bat, p2.vel = 0.2, V(soccer.PLAYER_SPEED * p2.spd, 0)       # correndo: nao dispara
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
    stun = S.scaled_extra("choque", 1)["stun"]
    assert abs(o.cd - (0.7 + stun)) < 1e-9, o.cd           # `stun` s a mais sem dominar...
    assert o.sk_stun > g.sk_t and o.vel.length() == 0.0     # ...nem andar (paralisado)
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
    assert abs(abs(b0.curve) - 70.0) < 1e-9
    assert abs(p.f.shot_err - p.f_base.shot_err * S.scaled_mods("curva", 1)["shot_err"][1]) < 1e-9
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
    assert p.sk_cur == "succao" and p.f.reach == p.f_base.reach + S.scaled_mods("succao", 1)["reach"][1]
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


# ------------------------------------------------------------------------- B14: cada skill MUDA o lance
# Um cenario deterministico por skill do catalogo (16 + 11 especiais): o mesmo lance COM e SEM a skill; a
# metrica e a do proprio motor (posse, desarmes, velocidade, mira, bateria...) e precisa mudar a favor de
# quem tem a skill. Se uma skill voltar a ser no-op (gatilho que nao dispara, fator que a IA nao usa,
# efeito curto demais) o cenario dela falha. Desarmes/defesas usam random.seed fixo e restauram o estado.
def _seeded(seed, fn):
    st = random.getstate()
    random.seed(seed)
    try:
        return fn()
    finally:
        random.setstate(st)


def _tackles(att, d, n=400, seed=5):
    """n tentativas de desarme de d em att (motor: ball_interactions); quantas d ganhou."""
    others = [q for q in d.team.players if q is not d]

    def go():
        k = 0
        for _ in range(n):
            g.ball.owner = att
            d.tackle_cd = 0.0
            for q in others:
                q.tackle_cd = 9.0
            g.ball_interactions()
            k += g.ball.owner is d
        return k
    return _seeded(seed, go)


def _steer_speed(p, steps=30, d=None):
    q = copy.copy(p)
    q.vel, q.bat = V(), 1.0
    for _ in range(steps):
        g.steer(q, d or V(p.team.dir, 0), soccer.PLAYER_SPEED * soccer.AI_SPEED, 1 / 60)
    return q.vel.length()


def _both(holder, sid, fn, rank=1, ovr=60):
    """fn(a, b, on) no mesmo lance com a skill (holder) e sem nenhuma skill."""
    out = {}
    for on in (True, False):
        a, b = start({holder: [(sid, rank)]} if on else None, ovr=ovr)
        out[on] = fn(a, b, on)
        g.match_sink = None
    return out[True], out[False]


def _carry_vs(a, b, holder, opp_idx, gap):
    """holder com a bola, o adversario opp_idx a `gap` px a frente; o resto longe."""
    p = a.players[holder]
    park(b)
    p.pos = V(soccer.CX, soccer.CY)
    o = b.players[opp_idx]
    o.pos = p.pos + V(a.dir * gap, 0)
    g.ball.owner = p
    g.ball.pos = V(p.pos)
    p.bat = 1.0
    return p, o


def _carry_free(a, b, sid, on):
    p = a.players[ATT]
    for q in b.players:
        q.pos = V(p.pos.x - a.dir * 150, q.pos.y)
    g.ball.owner = p
    p.bat = 1.0
    tick_all()
    assert (p.sk_cur == sid) == on
    return _steer_speed(p)


def sc_arrancada(a, b, on):
    return _carry_free(a, b, "arrancada", on)


def sc_succao(a, b, on):
    p = a.players[MID1]
    park(b)
    p.pos, p.vel = V(soccer.CX, soccer.CY), V()
    g.ball.owner, g.ball.pos, g.ball.vel = None, p.pos + V(60, 0), V()
    a.chaser = p
    tick_all()
    for _ in range(60):                       # 1 s: so o ima/alcance mexem (robos parados)
        g.tick_skills(1 / 60)
        g.update_ball(1 / 60)
        if g.ball.owner is p:
            return 1
    return 0


def _shot_cross(p, a):
    """Simula a bola (robos parados) ate a linha do gol: (y real, y previsto pela reta inicial, |v0|)."""
    b = g.ball
    v0, p0 = V(b.vel), V(b.pos)
    tx = a.target_x
    pred = p0.y + v0.y * (tx - p0.x) / v0.x
    y = None
    for _ in range(240):
        if g.state != "play":
            break
        prev = V(b.pos)
        g.update_ball(1 / 60)
        if (b.pos.x - tx) * a.dir >= 0 or g.state != "play":
            y = prev.y
            break
    return y, pred, v0.length()


def sc_curva(a, b, on):
    p = a.players[ATT]
    park(b, a.goal_x + a.dir * 60)
    gk = b.players[GK]
    gk.pos = V(a.target_x - a.dir * 90, soccer.CY + 40)       # goleiro fora da linha
    p.pos = V(a.target_x - a.dir * 300, soccer.CY)
    g.ball.owner = p
    _seeded(3, lambda: g.ai_shoot(p))
    gk.pos = V(a.goal_x, soccer.PITCH.top + 20)                # sai do caminho: so a trajetoria importa
    y, pred, v = _shot_cross(p, a)
    return abs(y - pred) if y is not None else 0.0            # o goleiro le a reta: erro da leitura


def sc_muralha(a, b, on):
    d, att = a.players[DEF], b.players[ATT]
    park(b)
    att.pos = V(a.goal_x + a.dir * 150, soccer.CY)
    d.pos = att.pos + V(a.dir * -35, 0)
    g.ball.owner, g.ball.pos = att, V(att.pos)
    tick_all()
    return _tackles(att, d)


def _lane_case(a, b, holder):
    """holder com a bola, ATT a frente e um adversario a meio caminho, a margem (m_sem + m_com)/2 da
    linha: so a margem menor (lane_margin da skill) enxerga o passe."""
    p, t = a.players[holder], a.players[ATT]
    park(b)
    for q in a.players:
        if q not in (p, t):
            q.pos = V(a.goal_x + a.dir * 20, soccer.PITCH.top + 20)
    p.pos = V(soccer.CX - a.dir * 100, soccer.CY)
    t.pos = p.pos + V(a.dir * 220, 0)
    ref = robots.factors(cfg("A", 60, 11)["squad"][holder]["attrs"], robots.TUNING_ROBOTS).lane_margin
    m = (ref + p.f.lane_margin) / 2 if p.f.lane_margin < ref else ref * 0.9
    b.players[MID1].pos = (p.pos + t.pos) / 2 + V(0, m)
    g.ball.owner = p
    return 1 if g.best_pass_target(p) is t else 0


def sc_leitura(a, b, on):
    return _lane_case(a, b, MID1)


def sc_poupanca(a, b, on):
    p = a.players[MID1]
    q = copy.copy(p)
    q.bat, q.vel = 1.0, V(soccer.PLAYER_SPEED * q.spd, 0)
    for _ in range(600):
        g.tick_battery(q, 1 / 60)
    return q.bat


def sc_recarga(a, b, on):
    p = a.players[MID1]
    p.bat, p.vel = 0.3, V()
    tick_all()
    for _ in range(60):
        g.tick_skills(1 / 60)
        g.tick_battery(p, 1 / 60)
    return p.bat


def sc_overclock(a, b, on):
    p = a.players[ATT]
    p.bat = 0.9
    g.ball.pos = V(a.target_x - a.dir * 100, soccer.CY)       # bola no terco de ataque
    tick_all()
    assert (p.sk_cur == "overclock") == on
    return _steer_speed(p)


def _shielded(a, b, sid, on):
    p, o = _carry_vs(a, b, MID1, MID1, 30)
    tick_all()
    if sid == "blindagem":
        assert (p.sk_cur == "blindagem") == on
    return -_tackles(p, o)


def sc_blindagem(a, b, on):
    return _shielded(a, b, "blindagem", on)


def sc_drible(a, b, on):
    """Marcacao colada por 3 s (so o marcador o alcanca): passos ate perder a bola."""
    p, o = _carry_vs(a, b, ATT, DEF, 30)
    tick_all()
    assert (p.sk_cur == "drible") == on
    for q in b.players:
        q.tackle_cd = 0.0 if q is o else 99.0

    def go():
        for k in range(180):
            o.pos = p.pos + V(a.dir * 20, 0)
            g.ball_interactions()
            if g.ball.owner is not p:
                return k
            if on and k == 0:
                assert o.tackle_cd >= S.scaled_extra("drible", 1)["evade"] - 1e-9 and p.sk_ev[0] == "evade"
            g.tick_timers(1 / 60)
            g.tick_skills(1 / 60)
        return 180
    return _seeded(13, go)


def sc_elastica(a, b, on):
    gk = a.players[GK]
    park(b)
    gk.pos = V(a.goal_x + a.dir * 30, soccer.CY)
    g.ball.owner, g.ball.pos, g.ball.vel = None, V(a.goal_x + a.dir * 200, soccer.CY), V(-a.dir * 700, 0)
    tick_all()

    def go():
        n = 0
        for _ in range(400):
            g.ball.owner = None
            g.ball.pos = gk.pos + V(a.dir * 12, 0)
            g.ball.vel = V(-a.dir * 700, 0)
            gk.cd = 0.0
            g.ball_interactions()
            n += g.ball.owner is gk
        return n
    return _seeded(9, go)


def sc_pressao(a, b, on):
    p, o = a.players[MID1], b.players[DEF]
    park(b)
    o.pos = V(a.target_x - a.dir * 200, soccer.CY)            # adversario com a bola no terco dele
    p.pos = o.pos + V(-a.dir * 34, 0)                          # 34 px: fora do raio base (32)
    g.ball.owner, g.ball.pos = o, V(o.pos)
    p.bat = 1.0
    tick_all()
    assert (p.sk_cur == "pressao") == on
    return _tackles(o, p)


def sc_choque(a, b, on):
    d, o = a.players[DEF], b.players[ATT]
    park(b)
    o.pos = V(soccer.CX, soccer.CY)
    d.pos = o.pos + V(20, 0)
    g.ball.owner = o
    d.f = S.apply_mods(d.f, {"tackle": ("add", 1.0)})
    o.f = S.apply_mods(o.f, {"shield": ("add", 5.0)})
    for q in a.players:
        q.tackle_cd = 0.0 if q is d else 9.0
    g.ball_interactions()
    assert g.ball.owner is d
    p0 = V(o.pos)
    for _ in range(40):                       # 2/3 s: o desarmado persegue a bola (IA) e tenta de novo
        g.tick_timers(1 / 60)
        g.tick_skills(1 / 60)
        o.team.chaser = o
        g.ai_player(o, 1 / 60)
        o.pos += o.vel / 60
    return -(o.pos - p0).length()             # paralisado: nao sai do lugar


def _shot(a, b, holder, dist, seed=3):
    p = a.players[holder]
    park(b, a.goal_x + a.dir * 60)
    gk = b.players[GK]
    gk.pos = V(a.target_x - a.dir * 30, soccer.CY)
    p.pos = V(a.target_x - a.dir * dist, soccer.CY + 5)
    tick_all()
    g.ball.owner = p
    _seeded(seed, lambda: g.ai_shoot(p))
    v = g.ball.vel
    y = g.ball.pos.y + v.y * (a.target_x - g.ball.pos.x) / v.x  # onde a reta cruza a linha do gol
    return p, abs(y - gk.pos.y), v.length()


def sc_matador(a, b, on):
    p, off_gk, v = _shot(a, b, ATT, 200)
    assert (getattr(p, "sk_condon", None) == "matador") == on
    return off_gk + v * 0.05


def sc_lancador(a, b, on):
    """12 reposicoes com todas as linhas de passe fechadas (pressao): quantas chegam ao atacante."""
    gk, t = a.players[GK], a.players[ATT]
    hits = launched = 0
    for k in range(12):
        park(b)
        gk.pos, gk.cd = V(a.goal_x + a.dir * 30, soccer.CY), 0.0
        xs = {DEF: 200, MID1: 330, MID2: 330, ATT: 520}
        ys = {DEF: soccer.CY, MID1: soccer.CY - 120, MID2: soccer.CY + 120, ATT: soccer.CY}
        for i, x in xs.items():
            a.players[i].pos, a.players[i].vel, a.players[i].cd = V(a.goal_x + a.dir * x, ys[i]), V(), 0.0
        for kk, i in enumerate((DEF, MID1, MID2, ATT)):       # um adversario fechando cada linha
            b.players[kk + 1].pos = gk.pos + (a.players[i].pos - gk.pos) * 0.3
            b.players[kk + 1].cd = 0.0
        b.players[0].pos = V(a.target_x, soccer.CY)
        g.ball.owner, g.ball.air, gk.hold = gk, 0.0, 0.0
        _seeded(4 + k, lambda: g.ai_gk(gk, 1 / 60))
        if g.ball.air > 0:
            launched += 1
            assert g.ball.air_to is t and gk.sk_ev[0] == "launch"
        for _ in range(150):                  # robos parados: a bola chega ao alvo?
            g.update_ball(1 / 60)
            if g.ball.owner is not None:
                break
        hits += g.ball.owner is t
    assert (launched > 0) == on, launched
    return hits


def sc_lider(a, b, on):
    if on:
        assert a.players[MID1].sk_badge
    return _steer_speed(a.players[DEF]) + 1000 * (1.0 - a.players[ATT].f.think_mul)


def _bad_decisions(p, n=400, seed=21):
    """n decisoes da IA com a bola (ai_with_ball com think zerado): quantas foram decisoes ruins."""
    cnt = [0]
    real = g.ai_bad_decision
    g.ai_bad_decision = lambda q: cnt.__setitem__(0, cnt[0] + 1)

    def go():
        for _ in range(n):
            g.ball.owner = p
            p.think = 0.0
            p.pos = V(soccer.CX, soccer.CY)
            g.ai_with_ball(p, 1 / 60)
    try:
        _seeded(seed, go)
    finally:
        del g.ai_bad_decision
    return cnt[0]


SCEN = {
    "arrancada": (ATT, sc_arrancada), "succao": (MID1, sc_succao), "curva": (ATT, sc_curva),
    "muralha": (DEF, sc_muralha), "leitura": (MID1, sc_leitura), "poupanca": (MID1, sc_poupanca),
    "recarga": (MID1, sc_recarga), "overclock": (ATT, sc_overclock), "blindagem": (MID1, sc_blindagem),
    "drible": (ATT, sc_drible), "elastica": (GK, sc_elastica), "pressao": (MID1, sc_pressao),
    "choque": (DEF, sc_choque), "matador": (ATT, sc_matador), "lancador": (GK, sc_lancador),
    "lider": (MID1, sc_lider),
    # especiais (reliquias e sets)
    "rolando": (ATT, lambda a, b, on: _carry_free(a, b, "rolando", on)), "faro_meia": (MID1, sc_leitura),
    "calor_forno": (MID1, lambda a, b, on: _steer_speed(a.players[MID1], 8) + sc_recarga(a, b, on)),
    "chinelada": (ATT, lambda a, b, on: _shot(a, b, ATT, 300)[2]),
    "sobrecarga": (ATT, lambda a, b, on: _steer_speed(a.players[ATT], 10)),
    "instinto_vo": (MID1, lambda a, b, on: -_bad_decisions(a.players[MID1])),
    "mente_zen": (MID1, lambda a, b, on: -_bad_decisions(a.players[MID1])),
    "faxina_total": (MID1, lambda a, b, on: _tackles(*_carry_vs(b, a, MID1, MID1, 30))),
    "muralha_aco": (MID1, lambda a, b, on: _shielded(a, b, "muralha_aco", on)), "impecavel": (DEF, lambda a, b, on: _steer_speed(a.players[DEF])),
    "remendo": (MID1, None),
}


def _remendo(a, b, on):
    p, o = a.players[MID1], b.players[MID1]
    park(b)
    p.pos, o.pos = V(soccer.CX, soccer.CY), V(soccer.CX + 20, soccer.CY)
    g.on_steal(o, p)                          # p acabou de perder a bola (gatilho lost_ball)
    assert (p.sk_cur == "remendo") == on
    return -_tackles(p, o)


SCEN["remendo"] = (MID1, _remendo)


def test_every_skill_changes_the_play():
    """B14: para CADA skill do catalogo (e as especiais) o mesmo lance com/sem a skill da resultado
    diferente, a favor de quem tem a skill (a metrica e a do motor: falha se a skill virar no-op)."""
    assert set(SCEN) == set(S.ALL), set(S.ALL) ^ set(SCEN)
    bad = []
    for sid, (holder, fn) in SCEN.items():
        try:
            on, off = _both(holder, sid, fn)
        except AssertionError as e:
            g.match_sink = None
            bad.append((sid, "assert", str(e)))
            continue
        if not on > off:
            bad.append((sid, on, off))
    assert not bad, bad


# Lancador: o lancamento e uma CHANCE (launch, no sk_rng) em cada reposicao sem linha de passe (~3 por
# partida); com a chance calibrada (0,12 no rank 1, forca ~3 F) ele acontece ~0,1-0,4 vez por partida.
MIN_FIRES = {"lancador": 0.1}


def test_fires_in_typical_matches():
    """Cada ativa/condicional (e o lancamento do Lancador, e o drible que de fato engana o marcador)
    dispara >= 1 vez por partida em media, em 10 partidas com o robo do papel certo (holders da calib)."""
    import calib_skills as CS
    want = [sid for sid, s in S.ALL.items() if s["kind"] in ("A", "C")] + ["lancador", "drible_evade"]
    low = {}
    for sid in want:
        real = "drible" if sid == "drible_evade" else sid
        tot = 0
        for k in range(10):
            h = cfg("A", 62, 30 + k)
            for i in CS.holders(real):
                h["squad"][i]["skills"] = ((real, 1, 0),)
            random.seed(k)
            g.start_robot_match(h, cfg("B", 56, 60 + k), lambda s, e: None, tuning=robots.TUNING_ROBOTS)
            play_out()
            tot += g.sk_count.get(sid, 0)
        if tot / 10 < MIN_FIRES.get(sid, 1.0):
            low[sid] = tot / 10
    assert not low, low


def test_skill_force_within_meta():
    """SKILL_FORCE (B15): nenhuma dominante; Elastica e Lider dentro do teto; tudo monotono no rank."""
    for sid, v in S.SKILL_FORCE.items():
        assert v[0] <= v[1] <= v[2], sid
        assert v[0] <= S.FORCE_R1_MAX and v[2] <= S.FORCE_R3_MAX, (sid, v)
    for sid in ("elastica", "lider"):
        assert S.SKILL_FORCE[sid][2] <= S.FORCE_R3_MAX, S.SKILL_FORCE[sid]


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
    names = ("tick_skills", "sk_on_kick", "on_steal", "sk_pre_shot", "ball_curve", "on_evade", "sk_gk_launch")
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


def test_b16_modules_in_shop_and_drops_only_with_mod_on():
    """B16: com mod_on a loja ganha 1 Modulo e parte dos drops vira Modulo, num RNG derivado: o resto do
    estoque/drops e IDENTICO ao de sem mod_on (Ato 1 e Modo Robos antes do tier 1 nao mudam)."""
    for tier in (0, 1, 3, 5):
        for seed in range(20):
            out = {}
            for on in (False, True):
                gg = gm.new_game(random.Random(seed))
                if on:
                    gg.flags[gm.MOD_FLAG] = 1
                st = gg.refresh_shop(tier, random.Random(100 + seed))
                out[on] = [(p["model"], p["rar"]) for p in st]
            mods = [m for m in out[True] if m[0] in parts.MODULE_MODELS]
            assert not any(m[0] in parts.MODULE_MODELS for m in out[False])
            assert len(mods) == 1 and out[True][:-1] == out[False], (tier, seed)
            assert mods[0][1] <= (3 if tier >= gm.LEGEND_MIN_TIER else 2)
    drops = {False: [], True: []}
    for on in (False, True):
        gg = gm.new_game(random.Random(1))
        if on:
            gg.flags[gm.MOD_FLAG] = 1
        rng = random.Random(8)
        for _ in range(300):
            r = gm.match_rewards(gg, 2, 0, [], 1, rng)
            drops[on].append(r["drop"]["model"] if r["drop"] else None)
            gg.inventory = gg.inventory[:10]
    n_mod = sum(1 for m in drops[True] if m in parts.MODULE_MODELS)
    assert [m is None for m in drops[True]] == [m is None for m in drops[False]]   # mesmo stream
    assert not any(m in parts.MODULE_MODELS for m in drops[False] if m)
    n_drop = sum(1 for m in drops[True] if m)
    assert 0.1 * n_drop < n_mod < 0.45 * n_drop, (n_mod, n_drop)
    # liga do Modo Robos: concluir o tier 1 liga mod_on e a loja do proximo tier ja traz um Modulo
    gg = gm.new_game(random.Random(2))
    lg = RL.new_league(gg, 0, random.Random(3))
    lg["round"] = RL.ROUNDS
    lg["results"] = [[0, 0, k, 5, 0] for k in range(1, 6)]
    res = RL.finish_league(gg, random.Random(4))
    assert res["advanced"] and gg.mod_on()
    assert sum(1 for p in gg.shop["stock"] if p["model"] in parts.MODULE_MODELS) == 1


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
