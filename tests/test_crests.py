"""Testes dos ESCUDOS dos times (game/crests.py e as telas que os mostram). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_crests.py [teste ...]

Determinismo (mesmo time = mesmo escudo, inclusive entre processos com PYTHONHASHSEED diferente), todos os
times de todos os modos com escudo, cache LRU com limite de memoria, zero Surface por quadro nas telas,
contraste minimo, campo opcional "crest" da garagem. NUNCA toca ~/.soccerpy_*.json (stores em memoria).
"""
import hashlib
import json
import os
import random
import subprocess
import sys
import time

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
        raise AssertionError("%s chamada pelos testes dos escudos" % name)
    return f


MEM = {}
prefs._store_get = lambda: None
prefs._store_set = lambda t: True
cm._store_get = lambda: None
cm._store_set = _forbid("campaign._store_set")
gm._store_get = lambda: MEM.get("g")
gm._store_set = lambda t: MEM.__setitem__("g", t) or True
gm._store_set_bad = lambda t: True
career._store_get = lambda: MEM.get("c")
career._store_set = lambda t: MEM.__setitem__("c", t) or True
store.write = _forbid("store.write")

import crests  # noqa: E402
import crowd  # noqa: E402
import friendly  # noqa: E402
import robot_league  # noqa: E402
import robots_ui  # noqa: E402
import soccer  # noqa: E402
import story  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)


def digest(surf):
    return hashlib.sha1(pygame.image.tobytes(surf, "RGBA") if hasattr(pygame.image, "tobytes")
                        else pygame.image.tostring(surf, "RGBA")).hexdigest()


def every_team():
    """(nome, cor) de todos os times do jogo: catalogo + amistoso + adversarios da Torre/treino + nomes do time
    do jogador."""
    out = [(t["name"], t["color"]) for t in crests.all_teams()]
    out += [(t["name"], t["color"]) for t in friendly.TEAMS]
    out += [("%s %d" % (n, k), c) for k, (n, c) in enumerate(zip(robot_league.TEAM_NAMES,
                                                                robot_league.TEAM_COLORS), 1)]
    out += [(n, gm.TEAM_COLOR) for n in robots_ui.TEAM_NAMES]
    return out


# ------------------------------------------------------------------------------------------ dados
def test_art_grids_valid():
    for sym, rows in crests.ART.items():
        assert len(rows) == 15, sym
        for r in rows:
            assert len(r) == 15, (sym, r)
            assert all(ch == "." or ch in crests.PAL for ch in r), (sym, r)
    for sym in crests.GEN:
        grid = crests._symbol_grid(sym)
        assert len(grid) == 15 and all(len(r) == 15 for r in grid), sym
        assert sum(ch != "." for r in grid for ch in r) >= 20, sym          # simbolo tem corpo
    for ch, glyph in crests.FONT.items():
        assert len(glyph) == 7 and all(len(r) == 5 for r in glyph), ch
    assert len(crests.SYMBOLS) >= 40 and len(crests.SHAPES) >= 6 and len(crests.PATTERNS) >= 6
    for _keys, sym in crests.SYMBOL_RULES:
        assert sym in crests.SYMBOLS, sym
    assert set(crests.FALLBACK) <= set(crests.SYMBOLS)


def test_initials_and_symbols_by_keyword():
    assert crests.initials("Tubarões FC") == "TF"
    assert crests.initials("Hiperlimpos X-9") == "HX9"
    assert crests.initials("Os Impecáveis") == "IMP"
    assert crests.initials("Impecáveis Mk II") == "I2"
    assert crests.initials("X-Ômega Prime") == "XOP"
    assert crests.initials("Parafusos FC 12") == crests.initials("Parafusos FC")
    for name in [t[0] for t in every_team()]:
        ini = crests.initials(name)
        assert 1 <= len(ini) <= 3 and all(ch in crests.FONT for ch in ini), (name, ini)
    want = {"Tubarões FC": "tubarao", "Leões do Norte": "leao", "Dragões SC": "dragao", "Raio Vermelho": "raio",
            "Clube do Xadrez": "torre", "Padaria Pão Quente": "pao", "Sakura Vacuum Club": "flor",
            "Os Impecáveis": "aspirador", "Esquadrão Faxina": "vassoura", "Parafusos FC": "parafuso",
            "Engrenagem Atlética": "engrenagem", "Sol Nascente": "sol", "Cometas FC": "cometa",
            "X-Ômega Prime": "omega", "Grêmio": "trevo", "Furacão Verde": "furacao", "Guarda Zero": "cavaleiro",
            "Dust Bunnies USA": "coelho", "Academia Sem Esforço": "haltere", "Os Sem-Poeira": "bolha"}
    for name, sym in want.items():
        assert crests.spec(name, (100, 100, 100))["sym"] == sym, (name, crests.spec(name, (1, 1, 1))["sym"])


def test_every_team_of_every_mode_has_a_crest():
    teams = every_team()
    cat = {t["name"] for t in crests.all_teams()}
    assert {n for n, _c in crests.CLASSIC_TEAMS} <= cat
    assert {n for n, _c in career.CLUBS} <= cat
    assert {t["name"] for t in story.TEAMS.values()} <= cat
    assert set(robot_league.TEAM_NAMES) <= cat
    assert {t["name"] for t in friendly.TEAMS} <= cat
    assert len(cat) >= 120
    syms, shapes = set(), set()
    for name, color in teams:
        sp = crests.spec(name, color)
        assert sp["sym"] in crests.SYMBOLS and sp["shape"] in crests.SHAPES and sp["pattern"] in crests.PATTERNS
        syms.add(sp["sym"])
        shapes.add(sp["shape"])
        s = crests.get(name, color, 40)
        assert s.get_size() == (crests.width_for(40), 40)
        assert s.get_bounding_rect().h >= 30                                   # desenhado (nao vazio)
    assert len(syms) >= 40, len(syms)                                          # variedade de simbolos
    assert shapes == set(crests.SHAPES)
    # chefes de cada capitulo: escudo especial
    for tr in story.TOURNAMENTS.values():
        boss = story.TEAMS[tr["boss"]]["name"]
        assert crests.spec(boss, (1, 2, 3))["special"], boss
    # Torre: "Parafusos FC 12" = escudo do "Parafusos FC"
    a = crests.get("Parafusos FC 12", (230, 60, 60), 40)
    b = crests.get("Parafusos FC", (230, 60, 60), 40)
    assert a is b


def test_deterministic_and_no_global_random():
    crests.clear()
    st = random.getstate()
    first = {n: digest(crests.get(n, c, 80)) for n, c in every_team()[:40]}
    assert random.getstate() == st                                             # nada de random global
    crests.clear()
    random.seed(12345)
    again = {n: digest(crests.get(n, c, 80)) for n, c in every_team()[:40]}
    assert first == again
    # em outro processo (hash() de str muda com PYTHONHASHSEED): mesmos pixels
    code = ("import os,sys,hashlib;os.environ['SDL_VIDEODRIVER']='dummy';sys.path.insert(0,'.');"
            "import pygame;pygame.init();pygame.display.set_mode((8,8));import crests;"
            "f=getattr(pygame.image,'tobytes',None) or pygame.image.tostring;"
            "print(hashlib.sha1(b''.join(f(crests.get(t['name'],t['color'],40),'RGBA') "
            "for t in crests.all_teams())).hexdigest())")
    outs = set()
    for seed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=seed, SDL_VIDEODRIVER="dummy")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env,
                           cwd=os.path.join(ROOT, "game"), timeout=120)
        assert r.returncode == 0, r.stderr
        outs.add(r.stdout.strip().splitlines()[-1])
    assert len(outs) == 1


def test_contrast_minimums():
    for name, color in every_team():
        sp = crests.spec(name, color)
        # padrao: cor secundaria distinguivel da cor do time
        assert crests.contrast(sp["sec"], sp["color"]) >= 1.5 or sp["pattern"] == "liso", name
        # faixa: iniciais legiveis
        if sp["light_banner"]:
            fill, txt = (236, 226, 204), crests.INK
        else:
            fill, txt = crests.NAVY, (255, 246, 220)
        assert crests.contrast(fill, txt) >= 7.0, name
        # simbolo x fundo do medalhao
        bg, _hi = crests.medallion_colors(sp)
        lum = crests.symbol_lum(sp["sym"])
        ratio = (max(lum, crests.rel_lum(bg)) + 0.05) / (min(lum, crests.rel_lum(bg)) + 0.05)
        assert ratio >= 2.4, (name, sp["sym"], ratio)
    # borda dourada x contorno escuro
    assert crests.contrast(crests.GOLD[1], crests.INK) >= 7.0


def test_cache_lru_memory_limit_and_reuse():
    crests.clear()
    a = crests.get("Tubarões FC", (30, 110, 230), 120)
    assert crests.get("Tubarões FC", (30, 110, 230), 120) is a                 # mesmo objeto (cache)
    assert crests.get("Tubarões FC", [30, 110, 230], 120) is a                  # cor como lista: mesma chave
    assert crests.get("Tubarões FC", (30, 110, 230), 120, compact=True) is not a
    old = crests.CACHE_MAX_BYTES
    try:
        crests.CACHE_MAX_BYTES = 300 * 1024
        for t in crests.all_teams()[:60]:
            crests.get(t["name"], t["color"], 120)
            assert crests.STATS["bytes"] <= crests.CACHE_MAX_BYTES
        assert len(crests._CACHE) < 60
    finally:
        crests.CACHE_MAX_BYTES = old
    assert len(crests._BASE) <= crests.BASE_CACHE_MAX
    # request/pump: nada e gerado no desenho; o pump gera fora dele (o mais novo primeiro)
    crests.clear()
    gen = crests.STATS["gen"]
    surf = pygame.Surface((200, 200))
    r = crests.blit(surf, "Lobos FC", (90, 100, 110), 36, center=(100, 100))
    assert crests.STATS["gen"] == gen and crests.pending() == 1                # placeholder + pedido
    assert r.size == (crests.width_for(36), 36) and r.center == (100, 100)
    assert crests.pump() == 1 and crests.pending() == 0
    assert crests.has("Lobos FC", (90, 100, 110), 36)
    crests.blit(surf, "Lobos FC", (90, 100, 110), 36, center=(100, 100))
    assert crests.pending() == 0


def test_generation_cost_and_memory_report():
    crests.clear()
    teams = crests.all_teams()
    t0 = time.perf_counter()
    for t in teams:
        crests.render_logical(crests.spec(t["name"], t["color"]))
    per = (time.perf_counter() - t0) * 1000 / len(teams)
    crests.clear()
    t0 = time.perf_counter()
    for t in teams:
        for size in (24, 36, 80, 120):
            crests.get(t["name"], t["color"], size)
    per_get = (time.perf_counter() - t0) * 1000 / (len(teams) * 4)
    print("  escudos: %d times, arte %.2f ms/escudo, get (com ampliacao) %.2f ms, cache %.0f KB"
          % (len(teams), per, per_get, crests.cache_bytes() / 1024.0))
    assert per < 40.0                                                          # folga larga (maquina lenta)
    assert crests.STATS["bytes"] <= crests.CACHE_MAX_BYTES


def test_garage_crest_field_sanitize_and_old_saves():
    gg = gm.new_game(random.Random(1), "Meu Time")
    d = gg.to_dict()
    assert "crest" not in d["team"]                                            # save antigo: sem o campo
    assert gm.Garage.sanitize(json.loads(json.dumps(d)))["team"].get("crest") is None
    assert gg.set_crest({"sym": "dragao", "shape": "redondo"}) == {"sym": "dragao", "shape": "redondo"}
    d = json.loads(gg.to_json())
    assert d["team"]["crest"] == {"sym": "dragao", "shape": "redondo"}
    assert gm.Garage.sanitize(d)["team"]["crest"] == {"sym": "dragao", "shape": "redondo"}
    for bad in ("x", 5, None, {"sym": 3}, {"sym": "A" * 40}, {"sym": "../x"}, {"shape": ["a"]}):
        d["team"]["crest"] = bad
        assert gm.Garage.sanitize(d)["team"].get("crest") is None, bad
    d["team"]["crest"] = {"sym": "naoexiste", "shape": "redondo"}
    keep = gm.Garage.sanitize(d)["team"]["crest"]
    assert crests.sanitize(keep) == {"shape": "redondo"}                       # id desconhecido: ignorado
    assert crests.spec("Meu Time", (0, 200, 255), keep)["shape"] == "redondo"
    gg.set_crest(None)
    assert "crest" not in gg.team
    assert crests.spec("Meu Time", (0, 200, 255), {"sym": "dragao"})["sym"] == "dragao"


def _count_frames(n, step=None):
    real = pygame.Surface
    count = [0]

    class Counting(real):
        def __init__(self, *a, **k):
            count[0] += 1
            super().__init__(*a, **k)
    gen = crests.STATS["gen"]
    pygame.Surface = Counting
    try:
        for _ in range(n):
            (step or g.update)(1 / 60)
            g.draw()
    finally:
        pygame.Surface = real
    return count[0], crests.STATS["gen"] - gen


def _settle():
    for _ in range(400):
        g.update(1 / 60)
        g.draw()
        if not crests.pending():
            g.update(1 / 60)
            g.draw()
            if not crests.pending():
                return
    raise AssertionError("escudos pendentes nao acabaram")


def test_zero_surface_per_frame_on_screens():
    # amistoso
    g.friendly_ui.open(1)
    g.friendly_ui.sel = {"teams": ("st_xomega_prime", "car_0"), "forms": ("equilibrada", "equilibrada")}
    g.friendly_ui.warm()
    _settle()
    assert _count_frames(30) == (0, 0)
    # partida (HUD) e fim (escudos grandes + ESTATISTICAS)
    random.seed(7)
    g.new_match(1, crowd.FRIENDLY_VENUE, {"teams": ("st_sakura", "car_4"), "forms": ("equilibrada",) * 2})
    assert g.hud_crests and all(img.get_height() == soccer.HUD_CREST for img, _r in g.hud_crests)
    _settle()
    assert _count_frames(30)[1] == 0
    g.time_left = 0.05
    for _ in range(600):
        g.update(1 / 60)
        if g.state == "over":
            break
    assert g.state == "over"
    _settle()
    assert _count_frames(20) == (0, 0)
    g.stats_tab = True
    _settle()
    assert _count_frames(20) == (0, 0)
    g.stats_tab = False
    g.state = "menu"
    # carreira: escolha, inicio, tabela, resultado
    ui = g.career_ui
    ui.open_new()
    _settle()
    assert _count_frames(10) == (0, 0)
    ui.choose(4)
    for tab in ("home", "table"):
        ui.set_tab(tab)
        _settle()
        assert _count_frames(20) == (0, 0)
    ui.quick_sim()
    _settle()
    assert _count_frames(20) == (0, 0)
    # Modo Robos: hub com liga (tabela, proximo jogo) e o card do resultado
    MEM.clear()
    rui = g.robots_ui
    rui.open()
    rui.rng = random.Random(3)
    rui.do_new()
    assert rui.garage is not None
    rui.go("hub")
    rui.new_league()
    _settle()
    assert _count_frames(20) == (0, 0)
    rui.do_sim()
    assert rui.screen_id == "round"
    _settle()
    assert _count_frames(20) == (0, 0)
    g.state = "menu"


def test_player_crest_click_cycles_symbol_and_shape():
    MEM.clear()
    rui = g.robots_ui
    rui.open()
    rui.rng = random.Random(5)
    rui.do_new()
    rui.go("hub")
    gg = rui.garage
    before = crests.spec(gg.team["name"], gg.team["color"], gg.team.get("crest"))
    g.draw()
    hit = [r for r, fn, en in rui.buttons if getattr(fn, "__name__", "") == "cycle_crest"]
    assert hit and hit[0].collidepoint((52, 37))
    rui.cycle_crest()
    after = crests.spec(gg.team["name"], gg.team["color"], gg.team.get("crest"))
    assert after["sym"] != before["sym"] and after["shape"] == before["shape"]
    assert json.loads(MEM["g"])["team"]["crest"]["sym"] == after["sym"]       # gravado (store em memoria)
    cfg = gg.match_cfg()
    assert cfg["crest"]["sym"] == after["sym"]
    real = pygame.key.get_mods
    pygame.key.get_mods = lambda: pygame.KMOD_LSHIFT
    try:
        rui.cycle_crest()
    finally:
        pygame.key.get_mods = real
    again = crests.spec(gg.team["name"], gg.team["color"], gg.team.get("crest"))
    assert again["shape"] != after["shape"] and again["sym"] == after["sym"]
    # a partida usa o escudo escolhido (Team.crest com o custom)
    g.start_robot_match(cfg, robot_league.match_cfg(robot_league.opponent_team("Lobos FC", (90, 100, 110), 50, 3)),
                        lambda s, e: None)
    assert g.teams[0].crest[2] == cfg["crest"]
    g.match_sink = None
    g.career_match = False
    g.state = "menu"


def test_latin1_source_and_strings():
    with open(os.path.join(ROOT, "game", "crests.py"), encoding="utf-8") as f:
        f.read().encode("latin-1")
    for name, _c in every_team():
        name.encode("latin-1")


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
