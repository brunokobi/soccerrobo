"""Testes da Fase 4, passos A8-A11: locais da torcida por modo/cenario e robos detalhados em campo.

Rodar da raiz:  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_robot_art.py

NUNCA toca ~/.soccerpy_*.json: stores de prefs/campanha/garagem/carreira vao para dicts em memoria
(trocados ANTES de criar o Game); as gravacoes da garagem e da carreira sao sentinelas que falham.
"""
import math
import os
import random
import sys
import time
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
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
PREFS = {"raw": '{"v": 1, "crowd": "ALTA"}'}
prefs._store_get = lambda: PREFS["raw"]
prefs._store_set = lambda text: PREFS.__setitem__("raw", text) or True
prefs.reset_cache()

import crowd  # noqa: E402
import robot_art  # noqa: E402
import robot_league as RL  # noqa: E402
import robots  # noqa: E402
import soccer  # noqa: E402
import story  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)

LOADOUT = (
    ("Goleiro", [("Radar LiDAR", 2), ("Chip Neural", 3)]),
    ("Titã", [("Blindado", 3), ("Vácuo Turbo", 2)]),
    ("Orbital", [("Canhão de Plasma", 3), ("Infravermelho", 1)]),
    ("Tanque", [("Blindado", 1), ("Escova de Sucção", 0)]),
    ("Velocista", [("Turbina", 3), ("Canhão de Plasma", 1), ("Chip de CPU", 1)]),
)
ALL_PARTS = tuple((nm, k % 4) for k, nm in enumerate(robot_art.ATLAS_PARTS))   # todas as pecas visiveis


def set_level(level):
    PREFS["raw"] = '{"v": 1, "crowd": "%s"}' % level
    prefs.reset_cache()


def loaded_garage(seed=1):
    gg = gm.new_game(random.Random(seed), "Faisca FC")
    for rb, (ch, models) in zip(gg.robots, LOADOUT):
        rb["chassis"] = ch
        for model, rar in models:
            pc = gg.new_piece(model, rar, 2)
            gg.inventory.append(pc)
            ok, msg = gg.equip(rb["id"], pc["id"])
            assert ok, msg
    return gg


def opp_cfg(ovr=55, seed=7):
    return RL.match_cfg(RL.opponent_team("Platinum", (230, 230, 245), ovr, seed))


class FakeTime:
    """Substitui soccer.time: relogio que avanca 1/60 s por quadro (animacoes e FX deterministicos)."""

    def __init__(self, t=100.0):
        self.t = t

    def perf_counter(self):
        return self.t


class SurfaceCounter:
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


def fake_player(ch, d, bat=1.0, vis=None, gk=False, idx=0):
    a = d * math.pi / 4
    return SimpleNamespace(pos=soccer.V(300, 300), face=soccer.V(math.cos(a), math.sin(a)),
                           vel=soccer.V(math.cos(a), math.sin(a)) * 200, bat=bat, idx=idx, vis=vis, art=None,
                           vdir=None, fx_next=0.0, chassis=ch, paint=None, role="GK" if gk else "MID")


# ------------------------------------------------------------------------------- A8: locais
def test_bg_venue_covers_every_bg_and_tournament():
    for bg in story.BGS:
        assert bg in crowd.BG_VENUE, bg
        assert crowd.venue_for_bg(bg) in crowd.VENUES, bg
    assert set(crowd.BG_VENUE) == set(story.BGS)                      # nada sobrando
    for tid, tr in story.TOURNAMENTS.items():
        assert crowd.venue_for_bg(tr["bg"]) in crowd.VENUES, tid
    # a spec 2.5: o cenario de estadio e o proprio local; os 8 cenarios novos tambem
    for bg in ("quadra", "ginasio", "arena", "estadio", "mundial", "laboratorio", "fabrica", "dojo",
               "aeroporto", "coliseu"):
        assert crowd.venue_for_bg(bg) == bg
    assert crowd.venue_for_bg("escola") == "quadra" and crowd.venue_for_bg("praca") == "bairro"
    assert crowd.venue_for_bg(None) == crowd.DEFAULT_VENUE
    assert crowd.ROBOTS_VENUE == "bairro" and crowd.FRIENDLY_VENUE == "bairro"
    assert [crowd.venue_for_tier(t) for t in range(4)] == ["bairro", "ginasio", "arena", "estadio"]
    assert crowd.venue_for_tier(9) == "estadio" and crowd.venue_for_tier(None) == crowd.ROBOTS_VENUE
    assert len(crowd.ROBOTS_TIER_VENUE) == len(gm.TIER_OVR)
    assert len(crowd.CAREER_DIV_VENUE) == len(career.DIV_NAMES)
    assert [crowd.venue_for_div(d) for d in range(3)] == ["estadio", "arena", "ginasio"]
    assert crowd.venue_for_div(9) == "ginasio" and crowd.venue_for_div("x") == crowd.DEFAULT_VENUE


def test_campaign_matches_and_training_use_tournament_venue():
    calls = []
    real = g.start_robot_match
    g.start_robot_match = lambda home, away, on_done, **kw: calls.append(kw)
    ui = g.campaign_ui
    try:
        camp = cm.new_campaign(random.Random(3))
        ui.campaign = camp
        seen = set()
        for _ in range(600):
            a = camp.next_action()
            if a["kind"] == "scene":
                camp.finish_scene(a["id"])
            elif a["kind"] == "match":
                tr = story.TOURNAMENTS[a["tournament"]]
                want = crowd.venue_for_bg(tr["bg"])
                ui.do_watch_match()
                assert calls[-1]["venue"] == want and calls[-1]["return_state"] == "campaign", (a["tournament"], calls[-1])
                if a["tournament"] not in seen:          # treino do capitulo: mesmo local do torneio
                    seen.add(a["tournament"])
                    ui.train = camp.training_cfg()
                    ui.do_watch_train()
                    assert calls[-1]["venue"] == want, ("treino", a["tournament"], calls[-1])
                camp.record_match(4, 0)
            elif a["kind"] == "chapter_end":
                camp.advance_chapter()
            else:
                break
        # todos os torneios sem condicao; dos condicionais (ex.: cap. 11 corp/rebel) so uma versao por partida
        plain = {n[1] for c in story.CHAPTERS for n in c["nodes"] if n[0] == "tournament" and len(n) < 3}
        conds = [{n[1] for n in c["nodes"] if n[0] == "tournament" and len(n) > 2} for c in story.CHAPTERS]
        assert plain <= seen <= set(story.TOURNAMENTS), seen
        assert all(len(grp & seen) == 1 for grp in conds if grp), seen
    finally:
        g.start_robot_match = real
        ui.campaign = None
        ui.pending = None
        g.state = "menu"


def test_robots_mode_and_career_use_their_venues():
    calls = []
    real_r, real_c = g.start_robot_match, g.start_career_match
    g.start_robot_match = lambda home, away, on_done, **kw: calls.append(("robots", kw.get("venue")))
    g.start_career_match = lambda home, away, venue=None: calls.append(("career", venue))
    try:
        rui = g.robots_ui
        gg = gm.new_game(random.Random(5))
        RL.new_league(gg, 0, random.Random(6))
        rui.garage = gg
        rui.do_watch()
        assert calls[-1] == ("robots", "bairro")
        rui.pending = None
        for tier, want in enumerate(("bairro", "ginasio", "arena", "estadio")):   # local pelo tier da liga
            RL.new_league(gg, tier, random.Random(6 + tier))
            assert gg.league["tier"] == tier
            rui.do_watch()
            assert calls[-1] == ("robots", want), (tier, calls[-1])
            rui.pending = None
        cui = g.career_ui
        c = career.Career.new()
        for div in range(3):
            c.user = c.divs[div][0]
            cui.career = c
            cui.play_match()
            assert calls[-1] == ("career", crowd.CAREER_DIV_VENUE[div]), calls[-1]
    finally:
        g.start_robot_match, g.start_career_match = real_r, real_c
        g.state = "menu"


def test_friendly_light_crowd_respects_prefs():
    set_level("ALTA")
    g.state = "menu"
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1, unicode="1"))
    assert g.crowd is not None and g.crowd.b.venue == "bairro" and not g.crowd.telao_on
    g.state = "play"
    for _ in range(5):
        g.draw()
    g.state = "over"                                      # ENTER = jogar de novo: mantem o local
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode=""))
    assert g.crowd is not None and g.crowd.b.venue == "bairro" and g.mode == 1
    set_level("OFF")
    g.state = "menu"
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2, unicode="2"))
    assert g.crowd is None and g.mode == 2
    g.paused = True                                       # T na pausa do amistoso liga de novo
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t, unicode="t"))
    assert prefs.get("crowd") == "ALTA" and g.crowd is not None and g.crowd.b.venue == "bairro"
    g.paused = False
    g.new_match(1)                                        # chamada direta (testes/goldens): sem torcida
    assert g.crowd is None
    set_level("ALTA")
    g.state = "menu"


# ------------------------------------------------------------------------------- A9-A11: arte
def test_every_chassis_dir_low_gk_overlay_draws():
    team = SimpleNamespace(idx=0, human=None, color=(0, 200, 255), gk_color=(250, 200, 40), players=[])
    bg = (6, 12, 26)
    old = soccer.time
    soccer.time = FakeTime(0.0)                           # int(0*5)%2 == 0: quadro low visivel
    g.state, g.paused, g.speed_idx = "play", True, 0
    try:
        for ch in robots.CHASSIS:
            for vis in (None, {"parts": ALL_PARTS, "hot": True}, {"parts": (("canhao", 0),), "hot": False}):
                for gk in (False, True):
                    for bat in (1.0, 0.2, 0.05):
                        for d in range(8):
                            screen.fill(bg)
                            p = fake_player(ch, d, bat, vis, gk)
                            g.draw_player(team, p)
                            assert p.vdir == d and p.art is not None
                            assert screen.get_at((300, 300))[:3] != bg
                            spr = robot_art.get_sprite(g.sprites, ch, p.art.led, gk, bat < 0.25)
                            assert spr.get_size() == (64, 64)
            a = robot_art.build_atlas(ch, (0, 200, 255), False, ALL_PARTS)
            assert len(a.under) == len(a.over) == robot_art.DIRS
            assert all(o is not None for o in a.over)       # com pecas: sempre ha camada de cima
    finally:
        soccer.time = old
        g.paused = False
        g.state = "menu"


def test_low_frame_differs_and_parts_change_sprite():
    for ch in robots.CHASSIS:
        a = robot_art.build_robot_sprite(ch, (0, 200, 255), False, False)
        b = robot_art.build_robot_sprite(ch, (0, 200, 255), False, True)
        diff = sum(1 for x in range(64) for y in range(64) if a.get_at((x, y)) != b.get_at((x, y)))
        assert diff > 80, (ch, diff)                       # low expressivo (meio LED, rachaduras, faisca)
    plain = robot_art.build_atlas("Disco", (0, 200, 255), False, ())
    full = robot_art.build_atlas("Disco", (0, 200, 255), False, ALL_PARTS)
    assert plain.nbytes < full.nbytes
    assert plain.under[0] is None                          # Disco sem pecas: nada sob o corpo
    small = robot_art.build_atlas("Disco", (0, 200, 255), False, (("canhao", 0),))
    big = robot_art.build_atlas("Disco", (0, 200, 255), False, (("canhao", 3),))
    assert big.over[0][0].get_width() > small.over[0][0].get_width()   # o canhao cresce com a raridade


def test_face_dir_quantized_with_hysteresis():
    assert robot_art.face_dir((1, 0)) == 0 and robot_art.face_dir((0, 1)) == 2
    assert robot_art.face_dir((-1, 0)) == 4 and robot_art.face_dir((0, -1)) == 6
    a = math.radians(25)                                   # perto da fronteira 0/1: fica no anterior
    assert robot_art.face_dir((math.cos(a), math.sin(a)), 0) == 0
    assert robot_art.face_dir((math.cos(a), math.sin(a)), None) == 1
    a = math.radians(40)
    assert robot_art.face_dir((math.cos(a), math.sin(a)), 0) == 1
    assert robot_art.face_dir((0, 0), 5) == 5


def test_vis_from_garage_is_additive_and_visual_only():
    gg = loaded_garage()
    pb = gg.pieces_by_id()
    for rb in gg.robots:
        e = gm.match_entry(rb, pb)
        assert e["attrs"] == gm.effective_attrs(rb, pb)
        assert e["vis"]["chassis"] == rb["chassis"] and e["vis"]["paint"] == tuple(rb["paint"])
    vis = gm.match_entry(gg.robots[4], pb)["vis"]
    assert dict(vis["parts"]) == {"turbina": 3, "canhao": 1, "modulo": 1} and vis["hot"]
    vis = gm.match_entry(gg.robots[3], pb)["vis"]
    assert robot_art.brush_count(vis) == 2 and dict(robot_art.atlas_parts(vis)) == {"blindado": 1}
    starter = gm.new_game(random.Random(2))
    v0 = gm.match_entry(starter.robots[0], starter.pieces_by_id())["vis"]
    assert v0["parts"] == () and not v0["hot"]             # pecas Comuns equilibradas: nada visivel
    # vis nao muda a simulacao: mesmo placar/eventos com e sem `vis` no elenco
    home = gg.match_cfg()
    bare = {"name": home["name"], "color": home["color"],
            "squad": [{k: v for k, v in e.items() if k != "vis"} for e in home["squad"]]}
    out = []
    for cfg in (home, bare):
        random.seed(11)
        g.start_robot_match(cfg, opp_cfg(), lambda s, e: None)
        assert all((p.vis is not None) == (cfg is home) for p in g.teams[0].players)
        while g.state != "over":
            g.step(1 / 60)
        out.append((list(g.score), [(e["team"], e["min"], e["name"]) for e in g.events]))
        g.match_sink = None
    assert out[0] == out[1], out
    g.state = "menu"


def test_squads_without_vis_still_work():
    def cfg(name, color):
        return {"name": name, "color": color, "squad": [("J%d" % i, 65) for i in range(5)]}
    random.seed(0)
    g.start_career_match(cfg("A", (50, 120, 255)), cfg("B", (235, 65, 65)))
    for t in g.teams:
        for p in t.players:
            assert p.vis is None and p.art is not None and p.art.nbrush == 1
    g.state = "play"
    for _ in range(10):
        g.step(1 / 60)
        g.draw()
    g.new_match(1)                                         # amistoso legado (tuplas): tambem
    g.state = "play"
    for _ in range(5):
        g.draw()
    g.state = "menu"


def _play_frames(n, clock, counter=None, low_every=0):
    for k in range(n):
        clock.t += 1 / 60
        g.step(1 / 60)
        if low_every and k % low_every == 0:
            for t in g.teams:
                t.players[1].bat = 0.2 if k % (2 * low_every) else 0.05
        g.draw()


def test_zero_surface_300_frames_campaign_parts_and_robots_mode():
    set_level("ALTA")
    old = soccer.time
    clock = soccer.time = FakeTime(500.0)
    try:
        for venue, home in (("mundial", loaded_garage().match_cfg()),
                            ("estadio", loaded_garage(4).match_cfg()),
                            ("bairro", gm.new_game(random.Random(9)).match_cfg())):
            random.seed(1)
            g.start_robot_match(home, opp_cfg(), lambda s, e: None, venue=venue)
            g.state = "play"
            _play_frames(40, clock, low_every=7)               # aquecimento (fontes/texto do HUD)
            builds = dict(robot_art.STATS)
            amb = 0
            with SurfaceCounter() as sc:
                for k in range(300):
                    clock.t += 1 / 60
                    g.step(1 / 60)
                    if k % 7 == 0:
                        for t in g.teams:
                            t.players[1].bat = 0.2 if k % 14 else 0.05
                    g.draw()
                    amb = max(amb, g.fx_amb)
            assert sc.n == 0, (venue, sc.n)
            assert robot_art.STATS == builds, (venue, builds, robot_art.STATS)
            assert 0 < amb <= soccer.ROBOT_FX_MAX, amb               # FX de robo saiu e respeitou o teto
            assert len(g.fx) <= soccer.FX_MAX
            g.match_sink = None
    finally:
        soccer.time = old
        g.state = "menu"


def test_robot_fx_own_rng_cap_and_off_in_max_and_pause():
    set_level("ALTA")
    old = soccer.time
    clock = soccer.time = FakeTime(800.0)
    try:
        random.seed(2)
        g.start_robot_match(loaded_garage().match_cfg(), opp_cfg(), lambda s, e: None, venue="bairro")
        g.state = "play"
        for t in g.teams:
            for p in t.players:
                p.bat = 0.05                                # todos com bateria critica: fumaca + sem escova
        st = random.getstate()
        rng0 = g.fx_rng.getstate()
        for _ in range(120):
            clock.t += 1 / 60
            g.draw()
        assert random.getstate() == st                      # o random global nao foi tocado
        assert g.fx_rng.getstate() != rng0                  # quem sorteou foi o RNG proprio do FX
        assert g.fx_amb <= soccer.ROBOT_FX_MAX
        assert any(p[8] == soccer.FX_STYLE["smoke_dark"] for p in g.fx)
        for k in soccer.ROBOT_FX:
            assert k in soccer.FX_KINDS
        g.fx.clear()
        g.fx_amb = 0
        g.speed_idx = 3                                     # MAX: nada
        for _ in range(60):
            clock.t += 1 / 60
            g.draw()
        assert g.fx == []
        g.speed_idx = 0
        g.paused = True                                     # pausa: nada novo
        for _ in range(60):
            clock.t += 1 / 60
            g.draw()
        assert g.fx == []
        g.paused = False
        for p in g.teams[0].players:                        # bateria cheia e parado: nada
            p.bat, p.vel = 1.0, soccer.V()
        g.fx.clear()
        g.fx_amb = 0
        for p in g.teams[1].players:
            p.bat, p.vel = 1.0, soccer.V()
        for _ in range(30):
            clock.t += 1 / 60
            g.draw()
        assert not [p for p in g.fx if p[9]]
        g.match_sink = None
    finally:
        soccer.time = old
        g.paused = False
        g.speed_idx = 0
        g.state = "menu"


def test_cache_is_limited_and_match_never_rebuilds():
    c = robot_art.SpriteCache(max_bytes=200 * 1024)
    for k in range(40):
        robot_art.warm_player(c, ("Disco", (k * 6 % 256, 120, 200), False), {"parts": ALL_PARTS})
    assert c.nbytes <= c.max_bytes and c.evicted > 0
    # o cache do jogo: muitos times diferentes nao passam do teto
    gc = g.sprites
    for k in range(30):
        cfg = loaded_garage(k).match_cfg()
        cfg["color"] = (20 + k * 7, 200 - k * 5, 90 + k * 3)
        for e in cfg["squad"]:
            e["paint"] = (k * 8 % 255, 255 - k * 8 % 255, 128)
        g.start_robot_match(cfg, opp_cfg(seed=k), lambda s, e: None)
        assert gc.nbytes <= robot_art.CACHE_BYTES
        for t in g.teams:                                   # o que a partida usa continua no cache
            for p in t.players:
                assert p.art is not None and p.art.key in [(k_[0], k_[1], k_[2]) for k_ in gc
                                                            if isinstance(k_[0], str) and len(k_) == 4]
        g.match_sink = None
    print("   cache: %d entradas, %d KB (teto %d KB), %d despejos" % (len(gc), gc.nbytes // 1024,
                                                                   robot_art.CACHE_BYTES // 1024, gc.evicted))
    g.state = "menu"


def test_warm_and_draw_budget():
    set_level("ALTA")
    crowd.clear_cache()
    g.sprites.clear()
    random.seed(0)
    t0 = time.perf_counter()
    g.start_robot_match(loaded_garage().match_cfg(), opp_cfg(), lambda s, e: None, venue="mundial")
    warm = (time.perf_counter() - t0) * 1000
    g.state = "play"
    for _ in range(60):
        g.step(1 / 60)
    g.crowd_event("goal", 0)
    for _ in range(10):
        g.draw()
    t0 = time.perf_counter()
    for _ in range(200):
        g.draw()
    ms = (time.perf_counter() - t0) / 200 * 1000
    print("   warm da partida (cache frio, mundial): %.1f ms (meta 80); draw: %.3f ms (meta 1,5)" % (warm, ms))
    assert ms <= 6.0, ms                                   # duro folgado
    assert warm <= 400, warm                               # duro folgado (meta informativa 80 ms)
    g.match_sink = None
    g.state = "menu"


def test_ui_sprite_cached_and_has_halo():
    rb = loaded_garage().robots[1]
    s1 = g.robot_sprite(rb)
    assert g.robot_sprite(rb) is s1 and s1.get_size() == (64, 64)
    assert s1.get_at((32, 32 - 18))[3] > 0                  # halo alfa em volta do corpo


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok", t.__name__)
    print(len(tests), "testes passaram")
