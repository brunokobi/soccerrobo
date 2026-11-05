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
    """Joga a campanha INTEIRA (P->1->...->6, ate o primeiro capitulo em rascunho) pela API pura. policy: "sim" (simulate_current),
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
            assert a == {"kind": "end", "draft": True} and c.chapter().get("draft")      # o proximo capitulo ainda e rascunho
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
    assert c.next_action() == {"kind": "end", "draft": True} and c.chapter().get("draft")
    assert all(not ch.get("draft") for ch in story.CHAPTERS if ch["reward"])
    assert g.stats["titles"] == 1, g.stats
    names = {r["name"] for r in g.robots}
    # recrutas: Gambiarra, Pixelado, Majestade; Ato 2: Relampago (gabi_amigo), Ze Perfeito (poupou_ze);
    # Ato 3: Samurai (gabi_amigo) ou Ronin. Com o elenco cheio (MAX_SQUAD) sai o reserva mais fraco
    # (Campaign._recruit, com aviso); o recruta mais recente sempre fica.
    assert len(g.robots) == gm.MAX_SQUAD, names
    assert ("Samurai" if g.flags.get("gabi_amigo") else "Ronin") in names, names
    assert sum(len(story.REWARDS[x].get("recruits", ())) for x in story.REWARDS) == 3
    for ch in story.CHAPTERS:                               # todas as recompensas aplicadas, uma vez
        if ch["reward"] is None:                            # ponte provisoria do cap. 6
            continue
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
    """Autoplay COMPLETO P->1->...->6 (varias seeds; sim aleatorio, sempre vence, perde a final
    ate o pity): termina em kind=="end" (draft False) sem erro."""
    tot = {}
    for policy, seeds in (("sim", range(12)), ("win", range(3)), ("pity", range(3))):
        for seed in seeds:
            c, n, _ = full_run(seed, policy)
            check_final_state(c)
            assert c.ch == next(x["id"] for x in story.CHAPTERS if x.get("draft")) and "c6_end" in c.done
            tot.setdefault(policy, []).append(n)
    for p, v in tot.items():
        print("     autoplay %s: partidas media %.1f max %d" % (p, sum(v) / len(v), max(v)))
    # sempre vence: 1 treino + uma partida por estagio de cada torneio jogavel (Ato 1: 26; cap. 6: 5;
    # cap. 7, liga: 7; cap. 8, copa com quartas: 6; ...)
    def ch_matches(ch):                                     # versoes condicionais (cap. 11): so uma e jogada
        tours = [n for n in ch["nodes"] if n[0] == "tournament" and n[1] != "t_p_treino"]
        plain = [n for n in tours if len(n) < 3]
        cond = [n for n in tours if len(n) > 2]
        return sum(len(cm.stages_of(story.TOURNAMENTS[n[1]])) for n in plain + cond[:1])
    want = 1 + sum(ch_matches(ch) for ch in story.CHAPTERS if not ch.get("draft"))
    assert want >= 45 and set(tot["win"]) == {want}, (want, tot["win"])


def test_full_campaign_save_load_every_chapter():
    for seed in range(3):
        c, n, rounds = full_run(seed, "sim", save_each_chapter=True)
        check_final_state(c)
        assert {"1", "2", "3", "4", "5"} <= set(rounds), rounds


def test_advance_chapter_last_chapter_enters_end_node():
    c, _, _ = full_run(1, "win")
    # fim: capitulo em rascunho -> {"kind":"end","draft":True}; advance_chapter nao esta no chapter_end
    assert c.advance_chapter() is None
    # cap. 5 no chapter_end -> cap. 6, cujo no 0 e o epilogo (C2)
    c2 = new(7)
    c2.ch = "5"
    c2.node = [k for k, _ in story.CHAPTERS[5]["nodes"]].index("chapter_end")
    assert c2.advance_chapter() == "6" and c2.node == 0 and c2.tour is None
    assert c2.chapter()["nodes"][0] == ("scene", "e1_epilogo")
    a = c2.next_action()
    assert a["kind"] == "scene" and a["id"] == "e1_epilogo"
    c2.finish_scene("e1_epilogo")
    a = c2.next_action()                                     # C6: o Ato 2 segue (volta do Vo Nestor)
    assert a["kind"] == "scene" and a["id"] == "c6_nestor"
    assert c2.advance_chapter() is None                      # nao esta no chapter_end
    # ultimo capitulo com chapter_end seguido de "end" (sintetico, formato do cap. 13): END_ID
    import copy
    orig = story.CHAPTERS
    chs = copy.deepcopy(orig)[:6]
    chs[-1]["nodes"].append(("end", "e1_epilogo"))
    story.CHAPTERS = chs
    try:
        c4 = new(9)
        c4.ch, c4.node = "5", 3
        assert c4.advance_chapter() == cm.END_ID == "END" and c4.chapter()["nodes"][c4.node][0] == "end"
    finally:
        story.CHAPTERS = orig
    # ultimo capitulo SEM no "end" (sintetico): nao avanca, devolve None como antes
    chs = copy.deepcopy(orig)[:6]
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


# --- C3: formatos league e series (torneios sinteticos; o Ato 1 so usa cup/single) --------------
LEAGUE = {"chapter": "1", "local": "Liga de teste", "bg": "arena", "format": "league",
          "group": ["turma3b", "fundao", "gremio", "teatro", "padaria"], "qf": None, "sf": "academia",
          "final": "faxina", "boss": "faxina", "boss_delta": 0, "regular_delta": (0, 0),
          "hooks": {"before": {"R1": "c1_intro"}, "after": {}, "win": None, "lose": "c1_final_lose",
                    "elim": "c2_repescagem"}}
SERIES = {"chapter": "1", "local": "Serie de teste", "bg": "arena", "format": "series",
          "series": ["coral", "detetives", "imaculados"], "group": [], "qf": None, "sf": None,
          "final": "imaculados", "boss": "imaculados", "boss_delta": 0, "regular_delta": (0, 0),
          "hooks": {"before": {}, "after": {}, "win": None, "lose": "c1_final_lose", "elim": None}}


class synthetic:
    """Troca o no de torneio do cap. 1 por um torneio sintetico `tr` (restaura ao sair)."""

    def __init__(self, tr, tid="t_test"):
        self.tr, self.tid = tr, tid

    def __enter__(self):
        import copy as _copy
        self.orig_ch = story.CHAPTERS
        chs = _copy.deepcopy(story.CHAPTERS)
        cap1 = next(c for c in chs if c["id"] == "1")
        cap1["nodes"] = [("tournament", self.tid), ("chapter_end", "1")]
        story.CHAPTERS = chs
        story.TOURNAMENTS[self.tid] = _copy.deepcopy(self.tr)
        return self

    def __exit__(self, *exc):
        story.CHAPTERS = self.orig_ch
        story.TOURNAMENTS.pop(self.tid, None)
        return False


def at_cap1(seed=3):
    c = new(seed)
    c.ch, c.node = "1", 0
    return c


def next_match(c):
    a, seen = play_scenes(c)
    assert a["kind"] == "match", a["kind"]
    return a, seen


def test_round_pairs_each_pair_once():
    for m in (1, 3, 5, 7):
        seen = []
        for r in range(m):
            pr = cm.round_pairs(m, r)
            flat = [x for p in pr for x in p]
            assert r not in flat and len(flat) == len(set(flat)) == m - 1, (m, r, pr)
            assert all(a < b for a, b in pr)
            seen += pr
        assert len(seen) == len(set(seen)) == m * (m - 1) // 2, m
    # copa (3 adversarios): o mesmo emparelhamento de antes do C3 (resultados do Ato 1 identicos)
    assert [cm.round_pairs(3, r) for r in range(3)] == [[(1, 2)], [(0, 2)], [(0, 1)]]


def test_stage_helpers_by_format():
    cup = story.TOURNAMENTS["t_c1"]
    assert cm.stages_of(cup)[-2:] == ["SF", "F"] and cm.boss_stages(cup) == ["F"]
    assert cm.round_stages(cup) == ["G1", "G2", "G3"] and cm.advance_pos(cup) == 2
    assert cm.stages_of(LEAGUE) == ["R1", "R2", "R3", "R4", "R5", "SF", "F"]
    assert cm.round_stages(LEAGUE) == ["R1", "R2", "R3", "R4", "R5"] and cm.advance_pos(LEAGUE) == 4
    assert [cm.stage_team(LEAGUE, s) for s in cm.stages_of(LEAGUE)] == LEAGUE["group"] + ["academia", "faxina"]
    assert cm.stages_of(SERIES) == ["S1", "S2", "S3"] and cm.round_stages(SERIES) == []
    assert [cm.stage_team(SERIES, s) for s in cm.stages_of(SERIES)] == SERIES["series"]
    assert cm.boss_stages(SERIES) == ["S3"] and cm.boss_stages(dict(SERIES, boss_stages=["S2", "S3"])) == ["S2", "S3"]
    assert cm.boss_stages(story.TOURNAMENTS["t_p_treino"]) == []
    assert cm.STAGE_NAMES["R3"] == "Rodada 3" and cm.STAGE_NAMES["S2"] == "Duelo 2"


def test_league_win_path_table_and_champion():
    with synthetic(LEAGUE):
        c = at_cap1()
        a, seen = next_match(c)
        assert seen == ["c1_intro"] and a["stage"] == "R1" and not a["knockout"] and not a["boss"]
        assert a["stage_name"] == "Rodada 1" and a["opp"]["name"] == story.TEAMS["turma3b"]["name"]
        for i in range(5):
            a, _ = next_match(c)
            assert a["stage"] == "R%d" % (i + 1)
            out = c.record_match(1, 1)                       # empate na liga: sem penaltis
            assert out["pen"] is None and out["result"] == "d"
            if i < 4:
                assert out["advanced"] and "group_pos" not in out
                assert len(c.group_league()["results"]) == 3 * (i + 1)
        # 5 empates: o desfecho depende dos outros jogos simulados (eliminado reinicia do zero)
        if out["outcome"] == "elim":
            assert out["group_pos"] > 4 and c.tour["results"] == [] and c.tour["attempt"] == 1
        else:
            assert out["group_pos"] <= 4 and c.tour["stage"] == "SF"
            _league_finish(c)


def _league_finish(c):
    a, _ = next_match(c)
    assert a["stage"] == "SF" and a["knockout"] and not a["boss"]
    out = c.record_match(0, 0, pen=(4, 2))                   # mata-mata: penaltis
    assert out["pen"] == (4, 2) and out["advanced"]
    a, _ = next_match(c)
    assert a["stage"] == "F" and a["boss"]
    c.pity = 0
    assert c.record_match(0, 1)["outcome"] == "retry" and c.pity == 1
    a, seen = next_match(c)
    assert "c1_final_lose" in seen and a["stage"] == "F" and a["O"] == story.TEAMS["faxina"]["ovr"] - 1
    out = c.record_match(3, 0)
    assert out["outcome"] == "champion" and c.pity == 0 and c.tour["stage"] == cm.DONE
    assert c.next_action()["kind"] == "chapter_end"


def test_league_win_path_table_and_champion_forced():
    with synthetic(LEAGUE):
        c = at_cap1(4)
        for _ in range(5):
            next_match(c)
            out = c.record_match(5, 0)                       # 5 vitorias: 15 pts, 1o lugar
        assert out["group_pos"] == 1 and out["advanced"] and c.tour["stage"] == "SF"
        lg = c.group_league()
        assert len(lg["teams"]) == 6 and len(lg["results"]) == 15
        assert all(r["p"] == 5 for r in c.group_table())     # turno unico: todos jogam 5
        assert len({tuple(sorted((r[1], r[2]))) for r in lg["results"]}) == 15     # cada par uma vez
        _league_finish(c)


def test_league_cut_at_fourth_and_elim_restarts():
    with synthetic(LEAGUE):
        for pos, elim in ((4, False), (5, True), (6, True)):
            c = at_cap1(5)
            for i in range(5):
                next_match(c)
                if i == 4:
                    c.user_group_pos = lambda p=pos: p
                out = c.record_match(1, 0)
            assert out["group_pos"] == pos
            if elim:
                assert out["outcome"] == "elim" and c.tour["attempt"] == 1 and c.tour["stage"] == "R1"
                assert c.tour["results"] == []
                a, seen = next_match(c)
                assert "c2_repescagem" in seen and a["stage"] == "R1"
            else:
                assert out["advanced"] and c.tour["stage"] == "SF"
        c = at_cap1(6)
        for _ in range(5):                                   # perde tudo: lanterna, elimina de verdade
            next_match(c)
            out = c.record_match(0, 3)
        assert out["outcome"] == "elim" and out["group_pos"] == 6


def test_series_duels_retry_pity_only_on_boss():
    with synthetic(SERIES):
        c = at_cap1()
        a, _ = next_match(c)
        assert a["stage"] == "S1" and a["knockout"] and not a["boss"] and a["stage_name"] == "Duelo 1"
        out = c.record_match(0, 2)                           # perder um duelo comum: repete, sem pity
        assert out["outcome"] == "retry" and c.pity == 0 and c.tour["stage"] == "S1"
        a, seen = next_match(c)
        assert seen == [] and a["stage"] == "S1"             # cena "lose" so contra o chefe
        assert c.record_match(1, 1, pen=(3, 5))["outcome"] == "retry"      # empate: penaltis decidem
        assert c.record_match(2, 1)["advanced"] and c.tour["stage"] == "S2"
        next_match(c)
        c.record_match(1, 0)
        a, _ = next_match(c)
        assert a["stage"] == "S3" and a["boss"] and a["O"] == story.TEAMS["imaculados"]["ovr"]
        c.record_match(0, 1)
        assert c.pity == 1
        a, seen = next_match(c)
        assert seen == ["c1_final_lose"] and a["O"] == story.TEAMS["imaculados"]["ovr"] - 1
        out = c.record_match(1, 0)
        assert out["outcome"] == "champion" and c.pity == 0 and c.tour["stage"] == cm.DONE
        assert c.next_action()["kind"] == "chapter_end"
    with synthetic(dict(SERIES, boss_stages=["S2", "S3"])):
        c = at_cap1()
        next_match(c)
        c.record_match(1, 0)
        a, _ = next_match(c)
        assert a["stage"] == "S2" and a["boss"]
        c.record_match(0, 1)
        assert c.pity == 1


def test_league_and_series_save_roundtrip_and_sanitize():
    for tr, mid in ((LEAGUE, 3), (SERIES, 2)):
        with synthetic(tr):
            c = at_cap1(8)
            for _ in range(mid):
                next_match(c)
                c.record_match(2, 0)
            d = copy_json(c.to_dict())
            c2 = cm.Campaign.from_dict(d)
            assert c2 is not None and not c2.repaired and c2.to_dict() == c.to_dict()
            assert c2.next_action()["stage"] == c.next_action()["stage"]
            if tr is LEAGUE:
                assert c2.group_table() == c.group_table()
            bad = copy_json(c.to_dict())
            bad["c"]["tour"]["stage"] = "R6" if tr is LEAGUE else "S4"
            r = cm.Campaign.from_dict(bad)
            assert r is not None and r.repaired and r.node == 0 and r.tour is None


# --- C4: nos condicionais, variantes de adversario, finais e missoes secundarias ----------------
class patched:
    """Troca nos de capitulos (dict id -> nodes) e preenche SIDES/ENDINGS/TOURNAMENTS sinteticos."""

    def __init__(self, nodes=None, sides=None, endings=None, tours=None):
        self.nodes, self.sides = nodes or {}, sides or {}
        self.endings, self.tours = endings, tours or {}

    def __enter__(self):
        import copy as _copy
        self.orig = (story.CHAPTERS, dict(story.SIDES), list(story.ENDINGS))
        chs = _copy.deepcopy(story.CHAPTERS)
        for c in chs:
            if c["id"] in self.nodes:
                c["nodes"] = list(self.nodes[c["id"]])
        story.CHAPTERS = chs
        story.SIDES.update(self.sides)
        if self.endings is not None:
            story.ENDINGS[:] = self.endings
        for k, v in self.tours.items():
            story.TOURNAMENTS[k] = v
        return self

    def __exit__(self, *exc):
        story.CHAPTERS = self.orig[0]
        story.SIDES.clear()
        story.SIDES.update(self.orig[1])
        story.ENDINGS[:] = self.orig[2]
        for k in self.tours:
            story.TOURNAMENTS.pop(k, None)
        return False


def test_check_cond_count_all_any():
    c = new(2)
    c.done = ["side:a", "side:b", "c1_intro", "reward:rw_P"]
    c.garage.flags["x"] = 1
    assert c.check_cond(("count", "side:", 2)) and not c.check_cond(("count", "side:", 3))
    assert c.check_cond(("all", [("flag", "x"), ("done", "c1_intro"), ("count", "side:", 1)]))
    assert not c.check_cond(("all", [("flag", "x"), ("noflag", "x")]))
    assert c.check_cond(("any", [("flag", "nada"), ("done", "reward:rw_P")]))
    assert not c.check_cond(("any", [("flag", "nada")])) and not c.check_cond(("xyz", 1))
    assert c.check_cond(None)


def test_conditional_scene_and_tournament_nodes():
    ta = dict(story.TOURNAMENTS["t_c1"])
    nodes = {"1": [("scene", "c1_intro", ("flag", "rota_a")), ("scene", "c1_end", ("noflag", "rota_a")),
                   ("tournament", "t_c1", ("flag", "rota_a")), ("tournament", "t_alt", ("noflag", "rota_a")),
                   ("chapter_end", "1")]}
    with patched(nodes=nodes, tours={"t_alt": ta}):
        for flag, scene, tour in ((True, "c1_intro", "t_c1"), (False, "c1_end", "t_alt")):
            c = at_cap1(11)
            if flag:
                c.garage.flags["rota_a"] = 1
            a = c.next_action()
            assert a["kind"] == "scene" and a["id"] == scene, (flag, a.get("id"))
            c.finish_scene(scene)
            a = c.next_action()
            assert a["kind"] == "match" and a["tournament"] == tour, (flag, a.get("tournament"))
            # torneio ja iniciado continua mesmo se a cond mudar no meio
            c.garage.flags["rota_a"] = 0 if flag else 1
            assert c.next_action()["tournament"] == tour
            d = copy_json(c.to_dict())
            c2 = cm.Campaign.from_dict(d)
            assert c2 is not None and not c2.repaired and c2.tour == c.tour   # sanitize aceita no de 3


def test_alt_variant_swaps_teams_not_stages():
    tr = dict(story.TOURNAMENTS["t_c1"], alt=[(("flag", "rival"), {"final": "impec2", "sf": "academia"})])
    with patched(nodes={"1": [("tournament", "t_v"), ("chapter_end", "1")]}, tours={"t_v": tr}):
        base = at_cap1(12)
        assert base.tournament("t_v")["final"] == tr["final"] and base.tournament("t_v")["boss"] == tr["boss"]
        c = at_cap1(12)
        c.garage.flags["rival"] = 1
        eff = c.tournament("t_v")
        assert eff["final"] == eff["boss"] == "impec2" and eff["sf"] == "academia"
        assert cm.stages_of(eff) == cm.stages_of(tr)
        for _ in range(3):
            next_match(c)
            c.record_match(3, 0)
        a, _ = next_match(c)
        assert a["stage"] == "SF" and a["opp"]["name"] == story.TEAMS["academia"]["name"]
        c.record_match(2, 0)
        a, _ = next_match(c)
        assert a["stage"] == "F" and a["boss"] and a["opp"]["name"] == story.TEAMS["impec2"]["name"]
        assert story.TOURNAMENTS["t_v"]["final"] == tr["final"]          # os dados nao sao alterados


def test_auto_end_picks_first_valid_ending_and_records_gallery():
    endings = [(("flag", "fim_b"), ["c1_intro", "c1_end"]), (None, ["c2_intro"])]
    with patched(nodes={"6": [("end", cm.AUTO_END)]}, endings=endings):
        for flag, scenes in ((True, ["c1_intro", "c1_end"]), (False, ["c2_intro"])):
            c = new(13)
            c.ch, c.node = "6", 0
            if flag:
                c.garage.flags["fim_b"] = 1
            seen = []
            for _ in range(10):
                a = c.next_action()
                if a["kind"] != "scene":
                    break
                seen.append(a["id"])
                c.finish_scene(a["id"])
                if len(seen) == 1:
                    c.garage.flags["fim_b"] = 0 if flag else 1      # final ja comecado nao muda
            assert seen == scenes and a == {"kind": "end", "draft": False, "ending": scenes[0]}
            assert c.endings == [scenes[0]]
            c.next_action()
            assert c.endings == [scenes[0]]                         # sem duplicata
            c2 = cm.Campaign.from_dict(copy_json(c.to_dict()))
            assert c2.endings == c.endings and not c2.repaired
    with patched(nodes={"6": [("end", cm.AUTO_END)]}, endings=[(("flag", "nunca"), ["c2_intro"])]):
        c = new(13)
        c.ch, c.node = "6", 0
        try:
            c.next_action()
            raise AssertionError("sem final valido deveria levantar")
        except ValueError:
            pass


SIDE = {"title": "Missao teste", "local": "Quadra", "bg": "quadra", "team": "coral", "delta": 14,
        "unlock": ("done", "reward:rw_P"), "scenes": {"pre": "c2_intro", "win": "c2_end",
                                                      "lose": "c1_final_lose"},
        "reward": {"scrap": 50, "flag": "fita_1"}, "repeat": False}


def test_side_full_flow_lose_retry_win_reward():
    with patched(sides={"s_t": SIDE}):
        c = new(14)
        assert c.available_sides() == []
        try:
            c.start_side("s_t")
            raise AssertionError("missao bloqueada nao deveria abrir")
        except ValueError:
            pass
        c.done.append("reward:rw_P")
        assert c.available_sides() == ["s_t"]
        node_before = (c.ch, c.node)
        c.start_side("s_t")
        try:
            c.start_side("s_t")
            raise AssertionError("duas missoes ao mesmo tempo")
        except ValueError:
            pass
        a = c.next_action()
        assert a["kind"] == "scene" and a["id"] == "c2_intro"
        c.finish_scene("c2_intro")
        a = c.next_action()
        assert a["kind"] == "match" and a["side"] == "s_t" and a["tournament"] is None
        assert c.side_ovr() == max(cm.TRAIN_MIN_OVR, int(round(c.garage.rating())) - 14)
        assert abs(a["O"] - c.side_ovr()) <= 3                       # jitter do time (perfect False)
        assert a["opp"]["name"] == story.TEAMS["coral"]["name"]
        out = c.record_match(1, 1)                                    # empate = nao venceu
        assert out["outcome"] == "side_lose" and c.side["loses"] == 1
        a = c.next_action()
        assert a["kind"] == "scene" and a["id"] == "c1_final_lose" and a["key"] == "c1_final_lose#1"
        c.finish_scene("c1_final_lose")
        assert "c1_final_lose#1" in c.done
        scrap0 = c.garage.scrap
        out = c.record_match(3, 0)
        assert out["outcome"] == "side_win" and out["side_reward"] == {"scrap": 50, "flag": "fita_1"}
        assert c.side_done("s_t") and c.garage.flags.get("fita_1") == 1 and c.stats["sides"] == 1
        assert c.garage.scrap >= scrap0 + 50
        a = c.next_action()
        assert a["kind"] == "scene" and a["id"] == "c2_end"
        c.finish_scene("c2_end")
        a = c.next_action()                                           # volta aos nos do capitulo
        assert c.side is None and (c.ch, c.node) == node_before and a.get("side") is None
        assert c.available_sides() == [] and c.check_cond(("count", "side:", 1))


def test_side_cancel_keeps_tournament_and_save_roundtrip():
    with patched(sides={"s_t": SIDE}):
        c = new(15)
        to_cap1_tour(c)
        c.record_match(1, 0)                                          # treino do Prologo
        play_scenes(c)
        if "reward:rw_P" not in c.done:
            c.done.append("reward:rw_P")
        tour_before = copy_json(c.tour) if c.tour else None
        c.start_side("s_t")
        c.finish_scene("c2_intro")
        c.record_match(0, 2)                                          # perde uma
        d = copy_json(c.to_dict())
        c2 = cm.Campaign.from_dict(d)
        assert c2 is not None and not c2.repaired and c2.to_dict() == c.to_dict()
        assert c2.side == {"id": "s_t", "seed": c.side["seed"], "loses": 1}
        assert c2.next_action()["id"] == "c1_final_lose"
        c2.cancel_side()
        assert c2.side is None and c2.tour == tour_before and c2.available_sides() == ["s_t"]
        a = c2.next_action()
        assert a.get("side") is None and a["kind"] in ("scene", "match")


def test_conditional_reward_rw7_by_gabi_choice():
    """rw_7 (C7): com gabi_amigo entra o recruta Relampago; sem, a peca Mola Dupla. A skill vale nos dois."""
    for amigo in (True, False):
        c = new(51)
        if amigo:
            c.garage.flags["gabi_amigo"] = 1
        spec = c.reward_spec("rw_7")
        assert ("alt" in spec) and (bool(spec["recruits"]) == amigo) and ((spec["piece"] is None) == amigo)
        n_rob, n_inv = len(c.garage.robots), len(c.garage.inventory)
        rep = c.apply_chapter_rewards("7")
        assert rep["applied"] and rep["scrap"] == 900 and rep["skills"]
        if amigo:
            assert rep["recruits"] == ["Relâmpago"] and rep["piece"] is None
            r = next(x for x in c.garage.robots if x["name"] == "Relâmpago")
            assert r["chassis"] == "Velocista" and r["level"] == 7 and len(c.garage.robots) == n_rob + 1
        else:
            assert rep["recruits"] == [] and rep["piece"] and len(c.garage.inventory) == n_inv + 1
            assert all(x["name"] != "Relâmpago" for x in c.garage.robots)
        assert c.apply_chapter_rewards("7")["applied"] is False        # uma vez so


def test_cap9_series_variant_and_rw9_by_choice():
    """t_c9 (C8): o 2o duelo e o Reserva da Valquiria, ou os Trovoes Limpex com gabi_rival. rw_9: poupou_ze
    traz o Ze Perfeito; desligou_ze da o Modulo Overclock e 1.700 de sucata."""
    c = new(52)
    assert c.tournament("t_c9")["series"][1] == "reserva_valq"
    c.garage.flags["gabi_rival"] = 1
    eff = c.tournament("t_c9")
    assert eff["series"] == ["droides", "trovoes_lx", "zeperfeito_gz"] and eff["boss"] == "zeperfeito_gz"
    assert cm.boss_stages(eff) == ["S3"]
    for poupou in (True, False):
        c = new(53)
        c.garage.flags["poupou_ze" if poupou else "desligou_ze"] = 1
        rep = c.apply_chapter_rewards("9")
        names = {r["name"] for r in c.garage.robots}
        if poupou:
            assert rep["recruits"] == ["Zé Perfeito"] and rep["scrap"] == 1300 and "Zé Perfeito" in names
            r = next(x for x in c.garage.robots if x["name"] == "Zé Perfeito")
            assert r["chassis"] == "Orbital" and r["level"] == 9
        else:
            assert rep["recruits"] == [] and rep["scrap"] == 1700 and rep["piece"]
            assert "Zé Perfeito" not in names


def test_act2_economy_tiers_xp_and_b2_bonus():
    """C9: tiers 4-6 so na campanha, XP dos niveis 10-14 da spec e o bonus da escolha B2 no Ato 2."""
    assert gm.TIER_MUL[:4] == (1.0, 1.5, 2.2, 3.2) and len(gm.TIER_MUL) == 7
    assert [gm.xp_need(l) for l in range(10, 15)] == [560, 600, 640, 680, 720]
    assert {c["id"]: c["econ_tier"] for c in story.CHAPTERS if c["id"] in ("6", "7", "8", "9")} == \
        {"6": 4, "7": 4, "8": 5, "9": 5}
    rewards = {}
    for flag in (None, "renova_limpex", "independente"):
        c = new(61)
        c.ch, c.node = "7", 0
        if flag:
            c.garage.flags[flag] = 1
        sm, xm = c.econ_mults()
        assert (sm, xm) == {None: (1.0, 1.0), "renova_limpex": (cm.B2_SCRAP_MUL, 1.0),
                            "independente": (1.0, cm.B2_XP_MUL)}[flag]
        c.start_tournament("t_c7")
        r = c.record_match(2, 0)["rewards"]
        rewards[flag] = (r["scrap"], sum(r["xp"].values()))
    base_s, base_x = rewards[None]
    assert rewards["renova_limpex"][0] == int(round(base_s * 1.2)) and rewards["renova_limpex"][1] == base_x
    assert rewards["independente"][0] == base_s and rewards["independente"][1] > base_x
    c = new(62)                                              # Ato 1: a flag nao tem efeito
    c.garage.flags["renova_limpex"] = 1
    assert c.econ_mults() == (1.0, 1.0)


def test_shop_tiers_4_to_6_use_better_chances():
    import random as _r
    hits = {}
    for tier in (3, 4, 6):
        epic = legend = 0
        for seed in range(400):
            g = gm.Garage()
            stock = g.refresh_shop(tier, _r.Random(seed)) or g.shop["stock"]
            rars = [p["rar"] for p in stock]
            epic += 2 in rars
            legend += 3 in rars
        hits[tier] = (epic / 400, legend / 400)
    assert hits[3][0] < hits[4][0] < hits[6][0] and hits[3][1] < hits[4][1] < hits[6][1], hits


def test_cap11_version_by_b2_and_rw11():
    """C10: o cap. 11 joga a versao corp (renova_limpex) ou rebel (independente) e a Lendaria de rw_11 segue."""
    for renova in (True, False):
        c = new(71)
        c.ch, c.node = "11", 0
        c.garage.flags["renova_limpex" if renova else "independente"] = 1
        for sid in ("c11_intro", "c11_dudu_hack", "c11_bia"):
            c.done.append(sid)
        a = c.next_action()
        assert a["kind"] == "match" and a["tournament"] == ("t_c11_corp" if renova else "t_c11_rebel"), a
        assert a["stage"] == "S1"
        d = copy_json(c.to_dict())
        assert cm.Campaign.from_dict(d).tour == c.tour                # save no meio da versao escolhida
        spec = c.reward_spec("rw_11")
        assert spec["piece"]["model"] == ("Railgun de Bolso" if renova else "Sonar Quântico")


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
