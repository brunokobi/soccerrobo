"""Testes do AMISTOSO com escolha de times e formacoes (game/friendly.py + game/friendly_ui.py). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_friendly.py [teste ...]

NUNCA toca ~/.soccerpy_*.json: prefs usa um dict em memoria e store.write/career/garage/campanha sao sentinelas.
"""
import json
import os
import random
import sys

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
import store  # noqa: E402

FORBIDDEN = []


def _forbid(name):
    def f(*a, **k):
        FORBIDDEN.append(name)
        raise AssertionError("%s chamada pelos testes do amistoso" % name)
    return f


PREFS = {}
WRITES = []
prefs._store_get = lambda: PREFS.get("raw")
prefs._store_set = lambda t: WRITES.append(t) or PREFS.__setitem__("raw", t) or True
cm._store_get = lambda: None
cm._store_set = _forbid("campaign._store_set")
gm._store_get = lambda: None
gm._store_set = _forbid("garage._store_set")
career._store_get = lambda: None
career._store_set = _forbid("career._store_set")
store.write = _forbid("store.write")

import crowd  # noqa: E402
import friendly  # noqa: E402
import soccer  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)
ui = g.friendly_ui


def reset(raw=None):
    PREFS.clear()
    WRITES.clear()
    if raw is not None:
        PREFS["raw"] = raw
    prefs.reset_cache()
    g.friendly_last = None
    g.state = "menu"
    g.paused = False


def key(k):
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0))


def click(pos):
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def snapshot(game):
    """Estado do motor que importa para o resultado (posicoes, atributos, placar)."""
    out = [tuple(game.score), (round(game.ball.pos.x, 6), round(game.ball.pos.y, 6))]
    for t in game.teams:
        out.append((t.name, tuple(t.color), tuple(t.gk_color), t.push))
        for p in t.players:
            out.append((p.role, p.chassis, p.fx, p.fy, tuple(sorted(p.robot.items())),
                        round(p.pos.x, 6), round(p.pos.y, 6)))
    return out


def run(game, steps, seed):
    random.seed(seed)
    for t in game.teams:
        t.human = None                       # CPU x CPU (deterministico com a semente)
    for _ in range(steps):
        if game.state == "over":
            break
        game.step(1 / 60)
    return snapshot(game)


# ------------------------------------------------------------------ dados
def test_teams_and_formations_data():
    ids = friendly.TEAM_IDS
    assert len(ids) >= 20 and len(set(ids)) == len(ids)
    assert ids[:2] == friendly.DEFAULT_TEAMS
    srcs = {t["src"] for t in friendly.TEAMS}
    assert srcs == {"AMISTOSO", "CARREIRA", "CAMPANHA", "MODO ROBÔS"}, srcs
    for t in friendly.TEAMS:
        assert 0 < len(t["name"]) <= 20, t["name"]
        t["name"].encode("latin-1")                                   # Font(None) / Latin-1
        assert len(t["color"]) == 3 and all(0 <= c <= 255 for c in t["color"])
        assert friendly.FORCE_MIN <= t["ovr"] <= friendly.FORCE_MAX
        if t["id"] in friendly.CLASSIC:
            assert t["names"] is None and t["ovr"] == 65 and friendly.squad(t["id"]) is None
        else:
            sq = friendly.squad(t["id"])
            assert len(sq) == 5 and len({n for n, _ in sq}) == 5 and all(o == t["ovr"] for _, o in sq)
    assert set(friendly.FORMATION_ORDER) == set(friendly.FORMATIONS)
    for fid, f in friendly.FORMATIONS.items():
        assert len(f["pts"]) == 5 and f["pts"][0] == (0.05, 0.50), fid
        assert all(0.0 < x < 1.0 and 0.0 < y < 1.0 for x, y in f["pts"]), fid
        assert -0.1 <= f["push"] <= 0.1
        (f["name"] + f["code"] + f["desc"]).encode("latin-1")
    eq = friendly.FORMATIONS[friendly.DEFAULT_FORMATION]
    assert [(fx, fy) for _, fx, fy in soccer.FORMATION] == list(eq["pts"]) and eq["push"] == 0.0
    assert len({f["pts"] for f in friendly.FORMATIONS.values()}) == len(friendly.FORMATIONS)


def test_sanitize_cycle_and_random_private_rng():
    d = friendly.sanitize(None)
    assert d == {"teams": friendly.DEFAULT_TEAMS, "forms": ("equilibrada", "equilibrada")}
    assert friendly.is_default(d) and friendly.is_default({"teams": ("lixo", 3)})
    s = friendly.sanitize({"teams": ("st_x9", "st_x9"), "forms": ("pressao", "nao_existe")})
    assert s["teams"][0] == "st_x9" and s["teams"][1] != "st_x9" and s["forms"] == ("pressao", "equilibrada")
    assert friendly.cycle_team("azul", "vermelho", 1) == friendly.TEAM_IDS[2]       # pula o do outro lado
    assert friendly.cycle_team("azul", friendly.TEAM_IDS[-1], -1) == friendly.TEAM_IDS[-2]
    assert friendly.cycle_formation("pressao", 1) == "equilibrada"
    st = random.getstate()
    rng = random.Random(3)
    seen = set()
    for _ in range(200):
        r = friendly.random_pick(rng)
        assert r["teams"][0] != r["teams"][1] and friendly.sanitize(r) == r
        seen.add(r["teams"][0])
    assert len(seen) > 15 and random.getstate() == st                 # nunca o random global


# ------------------------------------------------------------------ motor
def test_default_choice_is_bit_identical_to_old_friendly():
    """Escolha padrao (classicos + EQUILIBRADA) = new_match de sempre, inclusive pela tela."""
    for mode in (1, 2):
        random.seed(11)                                               # Player.think usa o random do motor
        g.new_match(mode)
        a0 = snapshot(g)
        a = run(g, 2400, 12)
        random.seed(11)
        g.new_match(mode, None, friendly.sanitize(None))
        assert snapshot(g) == a0
        assert run(g, 2400, 12) == a, mode
        assert all(t.push == 0.0 for t in g.teams)
    reset()
    random.seed(5)
    g.new_match(1, crowd.FRIENDLY_VENUE)
    old = snapshot(g)
    old_names = [t.name for t in g.teams]
    reset()
    key(pygame.K_1)
    assert g.state == "friendly" and friendly.is_default(ui.sel)
    key(pygame.K_RETURN)
    assert g.state == "kickoff" and g.mode == 1 and g.crowd is not None
    assert snapshot(g) == old and [t.name for t in g.teams] == old_names == ["VOCÊ", "CPU"]


def test_formation_changes_positions_and_play():
    sel = {"teams": ("azul", "vermelho"), "forms": ("retranca", "ofensiva")}
    g.new_match(1, None, sel)
    t0, t1 = g.teams
    assert t0.push < 0 < t1.push
    for t, fid in ((t0, "retranca"), (t1, "ofensiva")):
        assert [(p.fx, p.fy) for p in t.players] == list(friendly.FORMATIONS[fid]["pts"])
        assert [p.role for p in t.players] == [r for r, _, _ in soccer.FORMATION]   # papeis nao mudam
    g.ball.pos.update(soccer.CX, soccer.CY)
    p = t0.players[1]
    eq = friendly.FORMATIONS["equilibrada"]["pts"][1]
    # formation_pos: retranca recua (fx menor + push negativo) em relacao a equilibrada
    x_ret = g.formation_pos(p).x
    p.fx, p.fy = eq
    t0.push = 0.0
    assert g.formation_pos(p).x > x_ret
    # CPU x CPU por 40 s: o bloco da RETRANCA fica mais perto do proprio gol que o da OFENSIVA

    def mean_depth(form, seed):
        random.seed(seed)
        g.new_match(1, None, {"teams": ("azul", "vermelho"), "forms": (form, "equilibrada")})
        g.teams[0].human = None
        tot = n = 0
        for i in range(2400):
            g.step(1 / 60)
            if i % 10 == 0:
                for q in g.teams[0].players[1:]:
                    tot += (q.pos.x - soccer.PITCH.left) / soccer.PITCH.w
                    n += 1
        return tot / n
    d = {f: sum(mean_depth(f, s) for s in (1, 2, 3)) / 3 for f in ("retranca", "equilibrada", "ofensiva", "pressao")}
    assert d["retranca"] < d["equilibrada"] < d["ofensiva"], d
    assert d["pressao"] > d["equilibrada"], d


def test_team_choice_names_colors_and_strength():
    g.new_match(1, None, {"teams": ("st_xomega_prime", "car_16"), "forms": ("equilibrada", "quadrado")})
    t0, t1 = g.teams
    assert t0.name == "X-Ômega Prime" and t1.name == "Boêmios FC"
    assert [p.name for p in t0.players] == friendly.team("st_xomega_prime")["names"]
    strong = sum(robots_mean(p) for p in t0.players)
    weak = sum(robots_mean(p) for p in t1.players)
    assert strong > weak
    # cores parecidas: o lado 1 troca de cor (como nas partidas da carreira/robos)
    g.new_match(2, None, {"teams": ("st_impecaveis", "st_x9"), "forms": ("equilibrada", "equilibrada")})
    assert g.teams[0].color == (0, 220, 255) and g.teams[1].color != (0, 240, 255)
    assert g.teams[0].name == "Os Impecáveis" and g.teams[0].human is not None and g.teams[1].human is not None
    # classico do outro lado: nome do modo
    g.new_match(1, None, {"teams": ("vermelho", "azul"), "forms": ("equilibrada", "equilibrada")})
    assert [t.name for t in g.teams] == ["VOCÊ", "CPU"] and g.teams[0].color == (235, 65, 65)


def robots_mean(p):
    return sum(p.robot.values()) / len(p.robot)


# ------------------------------------------------------------------ tela
def test_keyboard_mode1_and_rematch():
    reset()
    key(pygame.K_1)
    assert g.state == "friendly" and g.music_track() == "menu" and not g.ambience_on()
    key(pygame.K_RIGHT)                                               # VOCE: proximo time (pula o da CPU)
    assert ui.sel["teams"][0] == friendly.TEAM_IDS[2]
    key(pygame.K_s)                                                   # linha da formacao
    key(pygame.K_d)
    assert ui.sel["forms"][0] == "retranca"
    key(pygame.K_DOWN)                                                # CPU: time
    assert ui.side == 1 and ui.focus[1] == 0
    for _ in range(3):
        key(pygame.K_LEFT)
    assert ui.sel["teams"][1] == friendly.TEAM_IDS[-2]               # vermelho -> azul -> ultimo -> penultimo
    key(pygame.K_TAB)
    assert ui.side == 0
    key(pygame.K_TAB)
    key(pygame.K_w)                                                   # sobe para a formacao do lado 0... (sequencia)
    assert (ui.side, ui.focus[ui.side]) == (0, 1)
    for _ in range(10):                                               # nunca o mesmo time dos dois lados
        key(pygame.K_UP)
        key(pygame.K_RIGHT)
        assert ui.sel["teams"][0] != ui.sel["teams"][1]
        key(pygame.K_DOWN)
    chosen = dict(ui.sel)
    key(pygame.K_RETURN)
    assert g.state == "kickoff" and g.mode == 1 and g.friendly_sel == friendly.sanitize(chosen)
    assert len(WRITES) == 1                                           # uma gravacao so (prefs.update)
    saved = json.loads(PREFS["raw"])
    assert (saved["fr_t0"], saved["fr_t1"]) == chosen["teams"] and (saved["fr_f0"], saved["fr_f1"]) == chosen["forms"]
    names = [t.name for t in g.teams]
    g.state = "over"
    key(pygame.K_RETURN)                                              # revanche: mesma escolha
    assert [t.name for t in g.teams] == names and g.friendly_sel == friendly.sanitize(chosen)
    g.state = "over"
    key(pygame.K_ESCAPE)
    assert g.state == "menu"
    key(pygame.K_1)                                                   # lembra a escolha na sessao
    assert ui.sel == friendly.sanitize(chosen)
    key(pygame.K_ESCAPE)
    assert g.state == "menu" and len(WRITES) == 1                     # ESC nao grava nada
    g.friendly_last = None                                            # nova sessao: vem das prefs
    prefs.reset_cache()
    key(pygame.K_2)
    assert ui.mode == 2 and ui.sel == friendly.sanitize(chosen)
    key(pygame.K_ESCAPE)


def test_keyboard_mode2_each_player_own_side():
    reset()
    key(pygame.K_2)
    assert g.state == "friendly" and ui.mode == 2
    t0, t1 = ui.sel["teams"]
    key(pygame.K_d)                                                   # J1 mexe so no lado esquerdo
    assert ui.sel["teams"][1] == t1 and ui.sel["teams"][0] != t0
    key(pygame.K_DOWN)                                                # J2 vai para a formacao dele
    key(pygame.K_RIGHT)
    assert ui.sel["forms"] == ("equilibrada", "retranca")
    key(pygame.K_s)
    key(pygame.K_a)
    assert ui.sel["forms"] == ("pressao", "retranca")
    assert ui.focus == [1, 1]
    key(pygame.K_r)                                                   # ALEATORIO
    assert ui.sel["teams"][0] != ui.sel["teams"][1]
    key(pygame.K_KP_ENTER)
    assert g.mode == 2 and all(t.human is not None for t in g.teams)
    reset()


def test_mouse_arrows_buttons_and_wheel():
    reset()
    key(pygame.K_1)
    g.draw()
    r = ui.rows[(1, 0)]
    click((r.right - 25, r.centery))                                  # seta > do time da CPU
    assert ui.sel["teams"][1] == friendly.TEAM_IDS[2]
    g.draw()
    r = ui.rows[(0, 1)]
    click((r.x + 25, r.centery))                                      # seta < da formacao do jogador
    assert ui.sel["forms"][0] == "pressao"
    g.draw()
    click(ui.rows[(1, 1)].center)                                     # clique na linha: foco
    assert ui.side == 1 and ui.focus[1] == 1
    real = pygame.mouse.get_pos
    try:
        pygame.mouse.get_pos = lambda: ui.rows[(1, 1)].center
        g.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1, flipped=False))
        assert ui.sel["forms"][1] == "retranca"
    finally:
        pygame.mouse.get_pos = real
    g.draw()
    labels = {}
    for rect, fn in ui.buttons:
        labels[fn.__name__] = rect
    click(labels["randomize"].center)
    g.draw()
    click([rc for rc, fn in ui.buttons if getattr(fn, "__name__", "") == "back"][0].center)
    assert g.state == "menu"
    key(pygame.K_1)
    g.draw()
    click([rc for rc, fn in ui.buttons if getattr(fn, "__name__", "") == "start"][0].center)
    assert g.state == "kickoff"
    reset()
    g.draw()
    click(g.menu_btns[1].center)                                      # menu: botao 2 abre a tela
    assert g.state == "friendly" and ui.mode == 2
    reset()


def test_invalid_prefs_fall_back_to_default():
    reset(raw=json.dumps({"v": 1, "fr_t0": "lixo", "fr_t1": "st_x9", "fr_f0": "pressao", "fr_f1": 7}))
    assert prefs.get("fr_t0") is None and prefs.get("fr_t1") == "st_x9"
    key(pygame.K_1)
    assert ui.sel == friendly.sanitize(None)                          # escolha incompleta: padrao
    key(pygame.K_ESCAPE)
    reset(raw=json.dumps({"v": 1, "fr_t0": "st_x9", "fr_t1": "st_x9", "fr_f0": "pressao", "fr_f1": "quadrado"}))
    key(pygame.K_1)
    assert ui.sel["teams"][0] == "st_x9" and ui.sel["teams"][1] != "st_x9"
    assert ui.sel["forms"] == ("pressao", "quadrado")
    key(pygame.K_ESCAPE)
    assert not prefs.update({"fr_t0": "lixo"}) and not prefs.update({}) and not prefs.update({"x": "1"})
    reset()


def test_zero_surface_per_frame_on_screen():
    for mode in (1, 2):
        reset()
        ui.open(mode)
        ui.sel = {"teams": ("st_sakura", "rl_6"), "forms": ("ofensiva", "quadrado")}
        for _ in range(5):
            g.update(1 / 60)
            g.draw()
        real = pygame.Surface
        count = [0]

        class Counting(real):
            def __init__(self, *a, **k):
                count[0] += 1
                super().__init__(*a, **k)
        n_cache = len(g.text_cache)
        pygame.Surface = Counting
        try:
            for _ in range(60):
                g.update(1 / 60)
                g.draw()
        finally:
            pygame.Surface = real
        assert count[0] == 0, "criou %d Surface em 60 quadros" % count[0]
        assert len(g.text_cache) == n_cache                           # nenhum texto novo renderizado
    reset()


def test_never_touched_real_store():
    assert FORBIDDEN == []


def main():
    names = sys.argv[1:] or [n for n in globals() if n.startswith("test_")]
    names = [n for n in names if n != "test_never_touched_real_store"] + \
        (["test_never_touched_real_store"] if "test_never_touched_real_store" in names else [])
    fails = 0
    for n in names:
        try:
            globals()[n]()
            print("ok %s" % n)
        except Exception:  # noqa: BLE001
            import traceback
            fails += 1
            print("FAIL %s" % n)
            traceback.print_exc()
    print("%d testes passaram" % (len(names) - fails) if not fails else "%d falhas" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
