"""Testes de game/campaign.py (logica pura da campanha). Sem pygame, sem disco.

Rodar da raiz: .venv/bin/python tests/test_campaign.py [teste ...]
Todo store.write/_store_set da garagem e da carreira falha se chamado (a campanha nunca grava).
"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import campaign as cm  # noqa: E402
import career  # noqa: E402
import garage as gm  # noqa: E402
import robots  # noqa: E402
import store  # noqa: E402
import story  # noqa: E402

PASS, FAIL = [], []
CALLS = []


def _boom(*a, **k):
    CALLS.append(a)
    raise AssertionError("gravacao proibida na campanha")


for _m, _n in ((gm, "_store_set"), (gm, "_store_set_bad"), (career, "_store_set"), (store, "write")):
    if hasattr(_m, _n):
        setattr(_m, _n, _boom)


class drafted:
    """Context manager: marca capitulos REAIS como draft (copia profunda de story.CHAPTERS, restaurada ao
    sair). Os testes de comportamento de capitulo draft nao dependem do conteudo real em draft."""

    def __init__(self, *ids):
        self.ids = ids

    def __enter__(self):
        import copy as _copy
        self.orig = story.CHAPTERS
        chs = _copy.deepcopy(story.CHAPTERS)
        for c in chs:
            if c["id"] in self.ids:
                c["draft"], c["nodes"], c["reward"] = True, [], None
        story.CHAPTERS = chs
        return self

    def __exit__(self, *a):
        story.CHAPTERS = self.orig
        return False


def new(seed=1):
    return cm.new_campaign(random.Random(seed))


def play_scenes(c, pick=0):
    """Consome cenas ate a proxima acao que nao seja cena; devolve (acao, ids de cenas vistos)."""
    seen = []
    for _ in range(80):
        a = c.next_action()
        if a["kind"] != "scene":
            return a, seen
        seen.append(a["id"])
        has_choice = any(isinstance(i, dict) for i in c.scene_lines(a["id"]))
        c.finish_scene(a["id"], pick if has_choice else None)
    raise AssertionError("cenas sem fim")


def win(c, my=2, opp=0):
    return c.record_match(my, opp)


def to_cap1_tour(c):
    """Prologo completo ate o torneio do Cap.1 (primeira partida pendente)."""
    a, _ = play_scenes(c)
    assert a["kind"] == "match" and a["tournament"] == "t_p_treino", a["kind"]
    c.record_match(3, 0)
    a, _ = play_scenes(c)
    assert a["kind"] == "chapter_end" and a["chapter"] == "P"
    assert c.advance_chapter() == "1"
    a, _ = play_scenes(c)
    assert a["kind"] == "match" and a["tournament"] == "t_c1" and a["stage"] == "G1", a
    return a


def to_final(c):
    """Cap.1 ate a final (vencendo grupo e SF)."""
    a = to_cap1_tour(c)
    for st in ("G1", "G2", "G3", "SF"):
        a, _ = play_scenes(c)
        assert a["stage"] == st, (a["stage"], st)
        win(c, 3, 0)
    a, _ = play_scenes(c)
    assert a["stage"] == "F" and a["boss"]
    return a


# --- testes ---------------------------------------------------------------------------
def test_new_campaign_invariants():
    c = new(7)
    g = c.garage
    assert len(g.robots) == 5 and len(g.lineup) == 5 and len(set(g.lineup)) == 5
    assert all(g.robot(i) is not None for i in g.lineup)
    assert g.scrap == 100 and g.scrap >= 0
    assert c.hero == g.robot(c.hero)["id"] and g.robot(c.hero)["name"] == "Zé Poeira"
    assert g.robot(c.hero)["name"].encode("latin-1")
    bases = sorted(sum(r["base"].values()) / 8 for r in g.robots)
    assert len(g.inventory) == 5 and len({p["id"] for p in g.inventory}) == 5
    assert all(p["rar"] == 0 for p in g.inventory)
    assert len(g.equipped_ids()) == 5
    assert 43.0 <= g.rating() <= 45.6, g.rating()
    assert c.ch == "P" and c.node == 0 and c.done == [] and c.tour is None and c.pity == 0
    assert 0 < len(g.team["name"]) <= gm.NAME_MAX_TEAM
    # round-trip minimo
    d = c.to_dict()
    c2 = cm.Campaign.from_dict(d)
    assert c2 is not None and c2.hero == c.hero and c2.seed == c.seed and c2.ch == "P"
    assert bases[0] < bases[1]


def test_new_campaign_deterministic():
    a, b = new(5), new(5)
    assert a.to_dict() == b.to_dict()
    assert new(6).to_dict() != a.to_dict()


def test_prologue_walk():
    c = new(1)
    a = c.next_action()
    assert a["kind"] == "scene" and a["id"] == "p1_garagem"
    assert c.next_action()["id"] == "p1_garagem"          # idempotente sem finish
    assert c.finish_scene("p1_garagem", 1) is True        # escolha 2 = +25 sucata
    assert c.garage.scrap == 125
    assert c.finish_scene("p1_garagem", 0) is False       # nao reaplica
    assert c.garage.scrap == 125
    a = c.next_action()
    assert a["id"] == "p2_oficina"
    c.finish_scene("p2_oficina", 0)
    assert c.garage.flags.get("chinelo_fica") == 1
    a = c.next_action()
    assert a["id"] == "p3_peneira_pre"
    c.finish_scene("p3_peneira_pre")
    a = c.next_action()
    assert a["kind"] == "match" and a["tournament"] == "t_p_treino" and a["stage"] == "F"
    assert a["O"] == 36 and a["opp"]["name"] == "Clube do Xadrez" and len(a["away"]["squad"]) == 5
    assert len(a["home"]["squad"]) == 5
    r = c.record_match(0, 2)                               # perder o treino nao bloqueia
    assert r["outcome"] == "done" and c.pity == 0
    a = c.next_action()
    assert a["kind"] == "scene" and a["id"] == "p4_peneira_pos"
    c.finish_scene("p4_peneira_pos")
    a = c.next_action()
    assert a["kind"] == "chapter_end" and a["chapter"] == "P"
    assert a["report"]["scrap"] == 30 and a["report"]["applied"] is True
    assert c.garage.tier_done == -1
    assert c.advance_chapter() == "1" and c.tour is None and c.node == 0


def test_chapter1_walk_and_conditions():
    c = new(2)
    play_scenes(c)
    c.record_match(1, 1)
    play_scenes(c)
    c.advance_chapter()
    a, seen = play_scenes(c)
    assert seen == ["c1_intro"]
    assert a["stage"] == "G1" and a["opp"]["name"] == "Turma 3ºB"
    win(c, 2, 0)
    a, seen = play_scenes(c)
    assert seen == ["c1_g2_fundao_pre"] and a["stage"] == "G2" and a["opp"]["name"] == "Fundão FC"
    # a fala condicional de Bia so aparece com a flag
    assert c.garage.flags.get("bia_convidada") == 1
    tot = len(story.SCENES["c1_g2_fundao_pre"]["lines"])
    assert len(c.scene_lines("c1_g2_fundao_pre")) == tot
    del c.garage.flags["bia_convidada"]
    assert len(c.scene_lines("c1_g2_fundao_pre")) == tot - 1
    c.garage.flags["bia_convidada"] = 1
    win(c, 2, 0)
    a, _ = play_scenes(c)
    assert a["stage"] == "G3"
    win(c, 2, 0)
    a, _ = play_scenes(c)
    assert a["stage"] == "SF" and a["opp"]["name"] == "Clube de Teatro" and not a["boss"]
    r = win(c, 1, 0)
    assert r["outcome"] == "next"
    a, seen = play_scenes(c)
    assert seen == ["c1_sf_pos", "c1_final_pre"] and a["stage"] == "F" and a["boss"]
    assert a["opp"]["name"] == "Os Impecáveis" and a["O"] == story.TEAMS["impecaveis"]["ovr"]
    # chefe perfeito: sem jitter => os 5 robos com o mesmo "ovr" medio por papel/chassis
    assert all(e["paint"] == (235, 248, 255) for e in a["away"]["squad"])
    r = win(c, 2, 1)
    assert r["outcome"] == "champion"
    a, seen = play_scenes(c)
    assert seen == ["c1_final_win", "c1_end"], seen
    assert a["kind"] == "chapter_end" and a["chapter"] == "1"
    rep = a["report"]
    assert rep["scrap"] == 120 and rep["recruits"] == ["Gambiarra"] and "Tanque" in rep["unlocked"]
    assert "Tanque" in c.garage.unlocked and c.garage.tier_done == 0
    assert c.advance_chapter() == "2"
    with drafted("2"):                                      # cap. draft sintetico: fim "draft"
        assert c.next_action() == {"kind": "end", "draft": True}
        assert c.advance_chapter() is None                  # nao esta no chapter_end


def test_shootout():
    def run(rh, ra, seed):
        return cm.shootout(rh, ra, random.Random(seed))
    assert run(50, 50, 3) == run(50, 50, 3)
    wh = wa = 0
    for s in range(3000):
        h, a = run(60, 40, s)
        assert h != a
        wh += h > a
        wa += a > h
    assert wh > wa * 1.3, (wh, wa)
    ties = sum(1 for s in range(2000) if len(set(run(50, 50, s))) == 1)
    assert ties == 0
    eq = sum(1 for s in range(4000) if run(50, 50, s)[0] > run(50, 50, s)[1])
    assert 1700 < eq < 2300
    # sem empate nem com ratings extremos
    assert run(0, 99, 1)[0] != run(0, 99, 1)[1]


def test_sim_match_bias():
    rng1, rng2 = random.Random(9), random.Random(9)
    assert cm.sim_match(50, 46, rng1) == cm.RL.quick_sim(50 - cm.sim_bias(46), 46, rng2)
    # bias(O): linear em O, com limites; contra ovr alto satura, contra ovr baixo cai
    assert cm.sim_bias(cm.SIM_O_REF) == cm.SIM_BIAS0 or cm.sim_bias(cm.SIM_O_REF) == cm.SIM_BIAS_MAX
    assert cm.sim_bias(10) == cm.SIM_BIAS_MIN and cm.sim_bias(90) == cm.SIM_BIAS_MAX
    bs = [cm.sim_bias(o) for o in range(30, 70)]
    assert all(b2 >= b1 for b1, b2 in zip(bs, bs[1:])) and bs[0] < bs[-1]
    assert cm.sim_bias(36) < cm.sim_bias(44)
    # o simulador usa bias(O): mesmo (F, O) com ovr diferente muda a taxa de vitoria
    def winrate(F, O):
        r = random.Random(3)
        return sum(m > o for m, o in (cm.sim_match(F, O, r) for _ in range(2000)))
    assert winrate(50, 38) > winrate(50, 46)
    n, w, l = 3000, 0, 0
    rng = random.Random(1)
    for _ in range(n):
        m, o = cm.sim_match(46, 46, rng)
        w += m > o
        l += m < o
    assert w < l                                           # vies: o jogador perde um pouco mais


def test_pity():
    c = new(3)
    to_final(c)
    base = c._opp_ovr(story.TOURNAMENTS["t_c1"], "F")
    boss = story.TEAMS["impecaveis"]["ovr"]
    assert base == boss and c.pity == 0
    seen = []
    for i in range(5):
        r = c.record_match(0, 1)
        assert r["outcome"] == "retry"
        seen.append(c.pity)
        a, _ = play_scenes(c)
        assert a["stage"] == "F"
        assert a["O"] == boss - min(i + 1, 3), (a["O"], i)
    assert seen == [1, 2, 3, 3, 3]
    assert c.pity_delta() == -3
    assert a["opp"]["ovr"] == boss - 3
    r = win(c, 1, 0)
    assert r["outcome"] == "champion" and c.pity == 0


def test_pity_not_applied_to_regular_or_sf():
    c = new(4)
    to_cap1_tour(c)
    for st in ("G1", "G2", "G3"):
        win(c, 2, 0)
        play_scenes(c)
    c.record_match(0, 1)                                    # derrota na SF: nao mexe no pity
    assert c.pity == 0
    a, _ = play_scenes(c)
    assert a["stage"] == "SF" and a["O"] == story.TEAMS["teatro"]["ovr"]


def test_rewards_once():
    c = new(5)
    to_final(c)
    g = c.garage
    n_before = len(g.robots)
    win(c, 1, 0)
    a, _ = play_scenes(c)
    assert a["kind"] == "chapter_end"
    snap = (g.scrap, len(g.robots), len(g.inventory), list(g.unlocked), g.tier_done,
            g.robot(c.hero)["level"], g.robot(c.hero)["xp"])
    assert any(r["name"] == "Gambiarra" for r in g.robots)
    assert len(g.robots) == n_before + 1
    for _ in range(3):
        rep = c.apply_chapter_rewards()
        assert rep["applied"] is False
        c.next_action()
        assert (g.scrap, len(g.robots), len(g.inventory), list(g.unlocked), g.tier_done,
                g.robot(c.hero)["level"], g.robot(c.hero)["xp"]) == snap
    assert sum(1 for r in g.robots if r["name"] == "Gambiarra") == 1
    assert "reward:rw_1" in c.done
    # a peca Rara foi entregue e a do recruta equipada
    assert any(p["model"] == "Escova de Sucção" and p["rar"] == 1 for p in g.inventory)
    gam = next(r for r in g.robots if r["name"] == "Gambiarra")
    assert gam["level"] == 3 and gam["chassis"] == "Tanque" and gam["role"] == "DEF"
    assert any(v is not None for v in gam["slots"].values())
    assert len(g.equipped_ids()) == len({i for i in g.equipped_ids()})


def test_recruit_full_squad_replaces_weakest_reserve():
    c = new(6)
    g = c.garage
    while len(g.robots) < gm.MAX_SQUAD:
        g.robots.append(g.make_robot("R%d" % g.next_id, "MID", "Disco"))
    assert len(g.robots) == 8
    reserves = [r for r in g.robots if r["id"] not in g.lineup]
    for i, r in enumerate(reserves):
        r["level"] = 4 + i
    weakest = reserves[0]
    weakest["level"] = 2
    wid, wname = weakest["id"], weakest["name"]
    # leva o capitulo ao chapter_end do 1 para aplicar rw_1
    c.ch, c.node = "1", len(story.CHAPTERS[1]["nodes"]) - 1
    lineup = list(g.lineup)
    rep = c.apply_chapter_rewards()
    assert len(g.robots) == 8
    assert g.robot(wid) is None
    assert any(r["name"] == "Gambiarra" for r in g.robots)
    assert g.lineup == lineup and g.robot(c.hero) is not None
    assert len(rep["warnings"]) == 1 and wname in rep["warnings"][0]
    # idempotente
    again = c.apply_chapter_rewards()
    assert again["applied"] is False and len(g.robots) == 8


def test_recruit_full_squad_never_removes_hero_or_starters():
    c = new(8)
    g = c.garage
    while len(g.robots) < gm.MAX_SQUAD:
        g.robots.append(g.make_robot("R%d" % g.next_id, "MID", "Disco"))
    for r in g.robots:
        r["level"] = 5
    for r in g.robots:
        if r["id"] not in g.lineup:
            r["level"] = 9
    lineup = list(g.lineup)
    c._recruit(story.REWARDS["rw_1"]["recruits"][0])
    assert all(g.robot(i) is not None for i in lineup) and g.robot(c.hero) is not None


def test_group_elimination_restarts_with_new_seed():
    c = new(9)
    to_cap1_tour(c)
    seed0 = c.tour["seed"]
    outs = []
    for st in ("G1", "G2", "G3"):
        a, _ = play_scenes(c)
        assert a["stage"] == st
        outs.append(c.record_match(0, 3))
    assert outs[-1]["outcome"] == "elim" and outs[-1]["group_pos"] > 2
    assert c.tour["attempt"] == 1 and c.tour["seed"] != seed0 and c.tour["stage"] == "G1"
    assert c.tour["results"] == []
    a = c.next_action()
    assert a["kind"] == "scene" and a["id"] == "c1_repescagem" and a["key"] == "c1_repescagem#0"
    c.finish_scene("c1_repescagem", 0)
    assert c.garage.flags.get("coxinha_frango") == 1
    a, _ = play_scenes(c)
    assert a["kind"] == "match" and a["stage"] == "G1" and a["attempt"] == 1
    # segunda eliminacao: cena aparece de novo, mas sem reaplicar fx
    for st in ("G1", "G2", "G3"):
        play_scenes(c)
        c.record_match(0, 3)
    a = c.next_action()
    assert a["kind"] == "scene" and a["id"] == "c1_repescagem" and a["key"] == "c1_repescagem#1"
    xp_before = [(r["level"], r["xp"]) for r in c.garage.robots]
    c.finish_scene("c1_repescagem", 1)
    assert [(r["level"], r["xp"]) for r in c.garage.robots] == xp_before
    assert not c.garage.flags.get("coxinha_queijo")
    assert c.finish_scene("c1_repescagem", 1) is False
    assert c.next_action()["kind"] == "match"
    # before G2 so toca uma vez por capitulo
    assert c.is_done("c1_repescagem") and c.is_done("c1_intro")


def test_group_table_and_top2():
    c = new(10)
    to_cap1_tour(c)
    for _ in range(3):
        play_scenes(c)
        win(c, 4, 0)
    tour = c.tour
    assert tour["stage"] == "SF"
    tb = c.group_table()
    assert len(tb) == 4 and tb[0]["idx"] == 0 and tb[0]["pts"] == 9
    assert sum(r["p"] for r in tb) == 12
    # recomputar e deterministico
    assert c.group_table() == tb


def test_final_loss_repeats_only_final():
    c = new(11)
    to_final(c)
    g = c.garage
    scrap0, played0 = g.scrap, g.stats["played"]
    r = c.record_match(0, 2)
    assert r["outcome"] == "retry" and r["result"] == "l"
    assert g.scrap > scrap0 and g.stats["l"] == 1                  # consolacao de derrota
    assert r["rewards"]["scrap"] == int(round(gm.SCRAP_LOSS * gm.TIER_MUL[0]))
    assert all(x == gm.XP_BASE for k, x in r["rewards"]["xp"].items() if k in g.lineup)
    a = c.next_action()
    assert a["kind"] == "scene" and a["id"] == "c1_final_lose" and a["key"] == "c1_final_lose#1"
    c.finish_scene("c1_final_lose")
    a = c.next_action()
    assert a["kind"] == "match" and a["stage"] == "F" and len(c.tour["results"]) == 4
    c.record_match(0, 1)                                            # 2a derrota: cena de novo
    a = c.next_action()
    assert a["kind"] == "scene" and a["key"] == "c1_final_lose#2"
    c.finish_scene("c1_final_lose")
    r = win(c, 1, 0)
    assert r["outcome"] == "champion"
    a, seen = play_scenes(c)
    assert seen == ["c1_final_win", "c1_end"]
    assert a["kind"] == "chapter_end"
    assert g.stats["played"] > played0


def test_knockout_draw_goes_to_penalties():
    c = new(12)
    to_final(c)
    r = c.record_match(1, 1)
    assert r["pen"] is not None and r["pen"][0] != r["pen"][1] and r["result"] == "d"
    assert r["outcome"] in ("champion", "retry")
    c2 = new(12)
    to_final(c2)
    r = c2.record_match(2, 2, pen=(4, 5))
    assert r["outcome"] == "retry" and r["pen"] == (4, 5) and c2.pity == 1
    try:
        c2.record_match(1, 1, pen=(3, 3))
        raise AssertionError("empate de penaltis deveria falhar")
    except ValueError:
        pass


def test_final_win_closes_chapter():
    c = new(13)
    to_final(c)
    r = win(c, 3, 2)
    assert r["outcome"] == "champion" and c.tour["stage"] == "DONE"
    a, seen = play_scenes(c)
    assert a["kind"] == "chapter_end" and seen == ["c1_final_win", "c1_end"]
    assert c.tour is None


def test_training_does_not_advance():
    c = new(14)
    a, _ = play_scenes(c)
    snap = (c.ch, c.node, dict(c.tour) if c.tour else None, c.pity)
    t = c.training_cfg()
    assert t["training"] and len(t["away"]["squad"]) == 5 and t["O"] == c.training_ovr()
    assert t["O"] == max(cm.TRAIN_MIN_OVR, round(story.CHAPTERS[0]["F_start"]) - cm.TRAIN_DELTA)
    assert t["econ_tier"] == 0
    g = c.garage
    s0 = g.scrap
    r = c.record_training(3, 0)
    assert r["result"] == "w" and g.scrap > s0 and c.stats["trained"] == 1
    assert (c.ch, c.node, c.pity) == snap[:2] + (snap[3],)
    assert c.tour is not None and c.tour["results"] == []
    assert c.next_action()["kind"] == "match"
    # capitulo 2+: tier do treino = tier do capitulo - 1
    c.ch = "3"
    assert c.training_econ_tier() == 1 and c.training_ovr() == max(
        cm.TRAIN_MIN_OVR, int(round(story.CHAPTERS[3]["F_start"])) - cm.TRAIN_DELTA)


def test_events_pids_give_goal_xp():
    c = new(15)
    play_scenes(c)
    g = c.garage
    pid = g.lineup[4]
    other = g.lineup[3]
    ev = [{"team": 0, "pid": pid, "own": False}, {"team": 0, "pid": pid},
          {"team": 1, "pid": other}, {"team": 0, "pid": other, "own": True}]
    r = c.record_match(2, 0, events=ev)
    xp = r["rewards"]["xp"]
    assert xp[pid] == gm.XP_BASE + gm.XP_WIN + 2 * gm.XP_GOAL
    assert xp[other] == gm.XP_BASE + gm.XP_WIN


def test_no_store_writes_and_global_rng_intact():
    random.seed(4242)
    st = random.getstate()
    del CALLS[:]
    for s in (1, 2):
        c = new(s)
        autoplay(c, forced=None, seed=s)
        c.to_dict()
    assert random.getstate() == st
    assert CALLS == []


def autoplay(c, forced=None, seed=0, max_matches=40, until="2"):
    """Joga ate o capitulo `until` (rascunho). forced: fn(act)->(my,opp). Devolve n de partidas."""
    n = 0
    for _ in range(2000):
        a = c.next_action()
        if a["kind"] == "scene":
            has = any(isinstance(i, dict) for i in c.scene_lines(a["id"]))
            c.finish_scene(a["id"], 0 if has else None)
        elif a["kind"] == "match":
            n += 1
            assert n <= max_matches, "partidas demais (%d)" % n
            if forced is None:
                c.simulate_current()
            else:
                my, opp = forced(a, n)
                c.record_match(my, opp)
        elif a["kind"] == "chapter_end":
            if c.advance_chapter() is None or c.ch == until:
                return n
        else:
            return n
    raise AssertionError("laco infinito")


def test_autoplay_forced_results():
    # sempre vence
    c = new(21)
    n = autoplay(c, forced=lambda a, i: (2, 0))
    assert c.ch == "2" and n == 1 + 5, n
    # sempre perde ate o pity (final): perde ate pity>=3 e ai vence; grupo vence sempre
    c = new(22)

    def pol(a, i):
        if a["tournament"] == "t_c1" and a["stage"] == "F" and c.pity < 3:
            return (0, 1)
        if a["tournament"] == "t_c1" and a["stage"] == "SF":
            return (1, 0)
        return (2, 0)
    n = autoplay(c, forced=pol)
    assert c.ch == "2" and c.pity == 0 and n == 1 + 5 + 3, n
    # perde o grupo duas vezes e depois joga limpo (com empates e penaltis)
    c = new(23)
    state = {"elims": 0}

    def pol2(a, i):
        if a["tournament"] == "t_c1" and a["stage"][0] == "G" and state["elims"] < 2:
            if a["stage"] == "G3":
                state["elims"] += 1
            return (0, 3)
        return (1, 1) if a["knockout"] else (1, 0)
    n = autoplay(c, forced=pol2)
    assert c.ch == "2" and state["elims"] == 2


def test_autoplay_sim_many_seeds_terminates():
    counts = []
    for seed in range(40):
        c = new(100 + seed)
        n = autoplay(c, forced=None, seed=seed, max_matches=40)
        assert c.ch == "2"
        counts.append(n)
    assert max(counts) <= 40
    print("     partidas por campanha (sim): media %.1f, max %d" % (sum(counts) / len(counts), max(counts)))


def full_run(seed, policy, save_each_chapter=False):
    """Joga a campanha INTEIRA (P->1->2->3->4->5->epilogo) pela API pura. policy: "sim" (simulate_current),
    "win" (sempre vence 2x0) ou "pity" (perde a final ate o pity zerar o chefe, vence o resto).
    Devolve (campanha, n_partidas, [saves round-trip por capitulo])."""
    rng = random.Random(seed)
    c = new(500 + seed)
    n, ends, rounds = 0, 0, []
    for _ in range(4000):
        a = c.next_action()
        k = a["kind"]
        if k == "scene":
            has_choice = any(isinstance(i, dict) for i in c.scene_lines(a["id"]))
            c.finish_scene(a["id"], rng.randrange(2) if has_choice else None)
        elif k == "match":
            n += 1
            if policy == "sim":
                c.simulate_current()
            elif policy == "win" or a["stage"] != "F":
                c.record_match(2, 0)
            else:                                           # final: perde ate o pity chegar ao maximo
                if c.pity < story.PITY_MAX:
                    c.record_match(0, 1)
                else:
                    c.record_match(1, 0)
        elif k == "chapter_end":
            rep = c.next_action()["report"]
            assert rep["applied"] is False                  # idempotente: a segunda leitura nao reaplica
            if save_each_chapter:
                rounds.append(check_roundtrip(c))
            nxt = c.advance_chapter()
            assert nxt is not None
            if nxt == cm.END_ID:
                assert c.chapter()["nodes"][c.node][0] == "end"
        elif k == "end":
            ends += 1
            assert a == {"kind": "end", "draft": False}
            break
        else:
            raise AssertionError(k)
        if save_each_chapter and k == "match" and c.tour and c.tour["stage"] == "SF":
            rounds.append(check_roundtrip(c))              # meio de cada capitulo (antes da semifinal)
    else:
        raise AssertionError("laco infinito")
    assert ends == 1
    return c, n, rounds


def check_roundtrip(c):
    d = c.to_dict()
    c2 = cm.Campaign.from_dict(copy_json(d))
    assert c2 is not None and c2.to_dict() == d, "save/load nao preservou o estado"
    assert c2.next_action()["kind"] == c.next_action()["kind"]
    return c.ch


def copy_json(d):
    import json
    return json.loads(json.dumps(d))


def check_final_state(c):
    g = c.garage
    assert c.next_action() == {"kind": "end", "draft": False}
    assert all(not ch.get("draft") for ch in story.CHAPTERS)
    assert g.stats["titles"] == 1, g.stats
    names = {r["name"] for r in g.robots}
    assert {"Gambiarra", "Pixelado", "Majestade"} <= names and len(g.robots) == gm.MAX_SQUAD
    assert sum(len(story.REWARDS[x].get("recruits", ())) for x in story.REWARDS) == 3
    for ch in story.CHAPTERS:                               # todas as recompensas aplicadas, uma vez
        assert ("reward:%s" % ch["reward"]) in c.done and c.done.count("reward:%s" % ch["reward"]) == 1
    # rewards idempotentes: reaplicar nao muda nada
    before = c.to_dict()
    for ch in story.CHAPTERS:
        assert c.apply_chapter_rewards(ch["id"])["applied"] is False
    assert c.to_dict() == before and g.stats["titles"] == 1
    assert {"Tanque", "Velocista", "Goleiro", "Titã"} <= set(g.unlocked)
    hero = g.robot(c.hero)                                   # "Chip do Vovo" (Lendaria) equipado no heroi
    pb = g.pieces_by_id()
    assert any(pb[pid]["model"] == "Chip de CPU" and pb[pid]["rar"] == 3
               for pid in hero["slots"].values() if pid is not None)


def test_full_campaign_autoplay_all_policies():
    """Autoplay COMPLETO P->1->2->3->4->5 (varias seeds; sim aleatorio, sempre vence, perde a final
    ate o pity): termina em kind=="end" (draft False) sem erro."""
    tot = {}
    for policy, seeds in (("sim", range(12)), ("win", range(3)), ("pity", range(3))):
        for seed in seeds:
            c, n, _ = full_run(seed, policy)
            check_final_state(c)
            assert c.ch == "5" and c.chapter()["nodes"][c.node] == ("end", "e1_epilogo")
            tot.setdefault(policy, []).append(n)
    for p, v in tot.items():
        print("     autoplay %s: partidas media %.1f max %d" % (p, sum(v) / len(v), max(v)))
    # sempre vence: 1 treino + 5+5+5+5 + 6 = 1 + 20 + 6 = 27 partidas
    assert set(tot["win"]) == {27}, tot["win"]


def test_full_campaign_save_load_every_chapter():
    for seed in range(3):
        c, n, rounds = full_run(seed, "sim", save_each_chapter=True)
        check_final_state(c)
        assert {"1", "2", "3", "4", "5"} <= set(rounds), rounds


def test_advance_chapter_last_chapter_enters_end_node():
    c, _, _ = full_run(1, "win")
    # fim: node no ("end"), cena ja jogada -> {"kind":"end","draft":False}; advance_chapter nao esta no chapter_end
    assert c.advance_chapter() is None
    # reconstroi o estado "chapter_end" do ultimo capitulo e confere o valor documentado
    c2 = new(7)
    c2.ch = "5"
    c2.node = [k for k, _ in story.CHAPTERS[-1]["nodes"]].index("chapter_end")
    assert c2.advance_chapter() == cm.END_ID == "END"
    assert story.CHAPTERS[-1]["nodes"][c2.node] == ("end", "e1_epilogo")
    a = c2.next_action()
    assert a["kind"] == "scene" and a["id"] == "e1_epilogo"
    c2.finish_scene("e1_epilogo")
    assert c2.next_action() == {"kind": "end", "draft": False}
    assert c2.advance_chapter() is None                      # ja no "end": nao avanca mais
    # ultimo capitulo SEM no "end" (sintetico): nao avanca, devolve None como antes
    import copy
    orig = story.CHAPTERS
    chs = copy.deepcopy(orig)
    chs[-1]["nodes"] = chs[-1]["nodes"][:-1]
    story.CHAPTERS = chs
    try:
        c3 = new(8)
        c3.ch, c3.node = "5", len(chs[-1]["nodes"]) - 1
        assert c3.advance_chapter() is None and c3.node == len(chs[-1]["nodes"]) - 1
    finally:
        story.CHAPTERS = orig


def test_deterministic_given_seed():
    def run():
        c = new(31)
        autoplay(c, forced=None)
        return c.to_dict()
    assert run() == run()


def test_finish_scene_validation():
    c = new(33)
    try:
        c.finish_scene("p1_garagem", 5)
        raise AssertionError("indice invalido deveria falhar")
    except ValueError:
        pass
    assert "p1_garagem" not in c.done
    try:
        c.finish_scene("nao_existe")
        raise AssertionError("cena inexistente")
    except KeyError:
        pass


def test_hero_never_in_reserve_swap_when_no_reserves():
    c = new(34)
    g = c.garage
    while len(g.robots) < gm.MAX_SQUAD:
        g.robots.append(g.make_robot("R%d" % g.next_id, "MID", "Disco"))
    g.lineup = [r["id"] for r in g.robots[3:8]]            # heroi (idx 2) vira reserva
    w = c._recruit(story.REWARDS["rw_1"]["recruits"][0])
    assert g.robot(c.hero) is not None and w


def main():
    names = sys.argv[1:] or [n for n in globals() if n.startswith("test_")]
    for n in names:
        try:
            globals()[n]()
            PASS.append(n)
            print("OK   %s" % n)
        except Exception as e:  # noqa: BLE001
            import traceback
            FAIL.append(n)
            print("FAIL %s: %r" % (n, e))
            traceback.print_exc()
    print("\n%d testes passaram, %d falhas" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
