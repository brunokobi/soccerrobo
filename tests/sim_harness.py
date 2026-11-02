"""Harness de simulacao headless do soccerpy.

Uso (da raiz do repo):
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/sim_harness.py golden --write
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/sim_harness.py golden --check
  ... tests/sim_harness.py golden-new --write|--check   (padrao novo: TUNING + bateria; regressao do balanco)
  ... tests/sim_harness.py run 80 50 40 [seed0] [legacy]
  ... tests/sim_harness.py run-skills 65 65 20 [seed0] [off]   (Modo Robos, 10 robos x 3 skills; off = sem)
  ... tests/sim_harness.py skill-shots                 (B7: partida com Arrancada, Muralha e Choque ativando)

O golden confere o MODO LEGADO: ele aplica LEGACY_TUNING + BATTERY_ON=False explicitamente
(o padrao do jogo agora e TUNING + BATTERY_ON=True) e tem de ficar 80/80.
  ... tests/sim_harness.py draw
  ... tests/sim_harness.py draw --crowd [ALTA|MEDIA] [ESTADIO|PERTO]
        (draw_ms por local da torcida, partida assistida; camera padrao = AUTO = ESTADIO nas assistidas)
  ... tests/sim_harness.py shot out.png
  ... tests/sim_harness.py crowd-shots [local ...]     (PNGs em $SOCCERPY_SHOTS_DIR ou num tempdir)
  ... tests/sim_harness.py camera-shots [local ...]    (camera ESTADIO x PERTO por local, com gol e confete)
  ... tests/sim_harness.py ui-shots                    (gol/confete, telao, LED, pausa e menu: A4-A7)
  ... tests/sim_harness.py robot-shots                 (robos A9-A11: grade de chassis, zoom, estadio, bairro)
"""
import json
import math
import os
import random
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(os.path.dirname(HERE), "game")
sys.path.insert(0, GAME)
os.chdir(GAME)

import pygame  # noqa: E402
import soccer  # noqa: E402

GOLDEN_PATH = os.path.join(HERE, "baseline_golden.json")
GOLDEN_NEW_PATH = os.path.join(HERE, "baseline_golden_new.json")
MATCHUPS = [(65, 65), (80, 50), (50, 80), (70, 60)]
SEEDS = range(20)

pygame.init()
_scr = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(_scr)


class mode:
    """Contexto que fixa o modo do motor: legacy=True -> LEGACY_TUNING + BATTERY_ON=False."""

    def __init__(self, legacy):
        self.legacy = legacy

    def __enter__(self):
        self.old = (soccer.ACTIVE_TUNING, soccer.BATTERY_ON)
        if self.legacy:
            soccer.ACTIVE_TUNING, soccer.BATTERY_ON = soccer.robots.LEGACY_TUNING, False
        else:
            soccer.ACTIVE_TUNING, soccer.BATTERY_ON = soccer.robots.TUNING, True

    def __exit__(self, *a):
        soccer.ACTIVE_TUNING, soccer.BATTERY_ON = self.old


def cfg(name, ovr):
    color = (50, 120, 255) if name == "A" else (235, 65, 65)
    return {"name": name, "color": color, "squad": [("x%d" % i, ovr) for i in range(5)]}


def play(home_ovr, away_ovr, seed):
    """Uma partida completa; devolve (gols_casa, gols_fora, steps)."""
    random.seed(seed)
    g.start_career_match(cfg("A", home_ovr), cfg("B", away_ovr))
    steps = 0
    while g.state != "over":
        g.step(1 / 60)
        steps += 1
    return g.score[0], g.score[1], steps


def run(ovr_a, ovr_b, n, seed0=0, legacy=False):
    """n partidas, A mandante nas pares e visitante nas impares.
    Retorna dict: goals_per_game, wld (V/D/E de A), ms_step."""
    goals = 0
    wld = [0, 0, 0]
    steps = 0
    t0 = time.perf_counter()
    for i in range(n):
        with mode(legacy):
            if i % 2 == 0:
                ga, gb, s = play(ovr_a, ovr_b, seed0 + i)
            else:
                gb, ga, s = play(ovr_b, ovr_a, seed0 + i)
        steps += s
        goals += ga + gb
        wld[0 if ga > gb else 1 if gb > ga else 2] += 1
    dt = time.perf_counter() - t0
    return {"goals_per_game": goals / n, "wld": wld, "ms_step": dt / steps * 1000}


# B6: 3 skills por robo (10 robos), por papel; mede ms_step do motor com skills ligadas (meta <= +0,006 ms)
SK_LOADOUT = {"GK": (("elastica", 1), ("lancador", 1), ("poupanca", 1)),
              "DEF": (("muralha", 1), ("choque", 1), ("blindagem", 1)),
              "MID": (("succao", 1), ("pressao", 1), ("leitura", 1)),
              "ATT": (("arrancada", 1), ("curva", 1), ("matador", 1))}


def robot_cfg(name, ovr, seed, with_skills=True, loadout=None):
    """Time do Modo Robos (robot_league.opponent_team) com `skills` por papel (SK_LOADOUT)."""
    import robot_league as RL
    cfg = RL.match_cfg(RL.opponent_team(name, (50, 120, 255) if name == "A" else (235, 65, 65), ovr, seed))
    if with_skills:
        lo = loadout or SK_LOADOUT
        for e, role in zip(cfg["squad"], RL.ROLES):
            e["skills"] = tuple(lo[role])
    return cfg


def run_skills(ovr_a, ovr_b, n, seed0=0, with_skills=True):
    """Como run(), mas partidas do Modo Robos (TUNING_ROBOTS, bateria) com/sem skills nos 10 robos."""
    goals, wld, steps, acts = 0, [0, 0, 0], 0, {}
    t0 = time.perf_counter()
    for i in range(n):
        a, b = robot_cfg("A", ovr_a, 11, with_skills), robot_cfg("B", ovr_b, 22, with_skills)
        if i % 2:
            a, b = b, a
        random.seed(seed0 + i)
        g.start_robot_match(a, b, lambda s, e: None, tuning=soccer.robots.TUNING_ROBOTS)
        while g.state != "over":
            g.step(1 / 60)
            steps += 1
        ga, gb = g.score if i % 2 == 0 else g.score[::-1]
        goals += ga + gb
        wld[0 if ga > gb else 1 if gb > ga else 2] += 1
        for k, v in g.sk_count.items():
            acts[k] = acts.get(k, 0) + v
    g.match_sink = None
    dt = time.perf_counter() - t0
    return {"goals_per_game": goals / n, "wld": wld, "ms_step": dt / steps * 1000, "sk_on": g.sk_on,
            "activations_per_game": {k: round(v / n, 1) for k, v in sorted(acts.items())}}


def _prep_play(mode=1, warm=120):
    random.seed(0)
    g.new_match(mode)
    g.state = "play"
    for _ in range(warm):
        g.step(1 / 60)


def shot(path, mode=1, warm=120):
    _prep_play(mode, warm)
    g.draw()
    pygame.image.save(_scr, path)
    return path


def draw_ms(n=300):
    _prep_play()
    t = time.perf_counter()
    for _ in range(n):
        g.draw()
    play_ms = (time.perf_counter() - t) / n * 1000
    g.state = "menu"
    t = time.perf_counter()
    for _ in range(100):
        g.draw()
    menu_ms = (time.perf_counter() - t) / 100 * 1000
    return {"draw_ms": play_ms, "menu_ms": menu_ms}


def _crowd_prefs(level="ALTA", camera=None):
    """Torcida no nivel pedido sem ler nem gravar ~/.soccerpy_prefs.json (store em memoria).
    camera None = AUTO (partida assistida -> ESTADIO)."""
    import prefs
    cam = ', "camera": "%s"' % camera if camera else ""
    prefs._store_get = lambda: '{"v": 1, "crowd": "%s"%s}' % (level, cam)
    prefs._store_set = lambda text: False
    prefs.reset_cache()


def _prep_crowd(venue, warm=120):
    random.seed(0)
    g.start_career_match(cfg("A", 65), cfg("B", 65), venue=venue)
    for _ in range(warm):
        g.step(1 / 60)
    g.state = "play"


def draw_crowd_ms(level="ALTA", n=300, camera=None):
    """draw_ms (partida assistida, 1x) sem torcida e com torcida em cada local, com um gol em curso."""
    import crowd
    _crowd_prefs("OFF")
    _prep_crowd(None)
    t = time.perf_counter()
    for _ in range(n):
        g.draw()
    out = {"sem_torcida": (time.perf_counter() - t) / n * 1000}
    _crowd_prefs(level, camera)
    for v in crowd.VENUES:
        crowd.clear_cache()
        t = time.perf_counter()
        _prep_crowd(v)
        b = g.crowd.b
        g.crowd_event("goal", 0)
        for _ in range(10):
            g.draw()
        t = time.perf_counter()
        for _ in range(n):
            g.draw()
        out[v] = {"draw_ms": round((time.perf_counter() - t) / n * 1000, 3), "warm_ms": round(b.build_ms, 1),
                  "pessoas": b.people, "faixas": len(b.segs), "camera": b.camera, "kb": b.nbytes // 1024}
    out["mundial+robos_com_pecas"] = robots_draw_ms("mundial", n)
    g.state = "menu"
    return out


def robots_draw_ms(venue="mundial", n=300):
    """A9-A11: partida da campanha (garagem carregada: 5 chassis, pecas visiveis) no local `venue`, com um
    gol em curso. draw_ms medio, warm da partida (sprites + torcida, cache frio) e memoria do cache."""
    import crowd
    import robot_art
    import robot_league as RL
    crowd.clear_cache()
    g.sprites.clear()
    gg = loaded_garage()
    away = RL.match_cfg(RL.opponent_team("Platinum", (230, 230, 245), 60, 7))
    random.seed(0)
    t = time.perf_counter()
    g.start_robot_match(gg.match_cfg(), away, lambda s, e: None, venue=venue)
    warm = (time.perf_counter() - t) * 1000
    for _ in range(120):
        g.step(1 / 60)
    g.state = "play"
    for t_ in g.teams:
        t_.players[1].bat = 0.2                     # faiscas/low em um robo por time
    g.crowd_event("goal", 0)
    for _ in range(10):
        g.draw()
    t = time.perf_counter()
    for _ in range(n):
        g.draw()
    ms = (time.perf_counter() - t) / n * 1000
    g.match_sink = None
    return {"draw_ms": round(ms, 3), "warm_ms": round(warm, 1), "sprites": len(g.sprites),
            "cache_kb": g.sprites.nbytes // 1024, "atlas": robot_art.STATS["atlas"]}


def crowd_shots(venues=None):
    """Capturas da torcida (antes e durante um gol) em $SOCCERPY_SHOTS_DIR (ou tempdir novo)."""
    import tempfile
    import crowd
    out = os.environ.get("SOCCERPY_SHOTS_DIR") or tempfile.mkdtemp(prefix="soccerpy_shots_")
    os.makedirs(out, exist_ok=True)
    _crowd_prefs("ALTA")
    paths = []
    for v in venues or ("bairro", "arena", "mundial"):
        _prep_crowd(v, warm=200)
        g.crowd.react.clear()                       # sem o aceno do pontape inicial
        g.crowd.next_upd = 0
        g.draw()
        paths.append(os.path.join(out, "crowd_%s.png" % v))
        pygame.image.save(_scr, paths[-1])
        g.goal(0)
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 0.45:      # a onda do gol chega a toda a torcida da casa
            g.draw()
        paths.append(os.path.join(out, "crowd_%s_gol.png" % v))
        pygame.image.save(_scr, paths[-1])
    g.state = "menu"
    return paths


def camera_shots(venues=None):
    """Camera ESTADIO x PERTO por local (antes e durante um gol, com confete) em $SOCCERPY_SHOTS_DIR."""
    import tempfile
    import crowd
    out = os.environ.get("SOCCERPY_SHOTS_DIR") or tempfile.mkdtemp(prefix="soccerpy_shots_")
    os.makedirs(out, exist_ok=True)
    paths = []
    for cam in ("ESTADIO", "PERTO"):
        _crowd_prefs("ALTA", cam)
        for v in venues or ("bairro", "ginasio", "estadio", "mundial"):
            _prep_crowd(v, warm=200)
            g.crowd.react.clear()
            g.crowd.next_upd = 0
            g.draw()
            paths.append(os.path.join(out, "camera_%s_%s.png" % (cam.lower(), v)))
            pygame.image.save(_scr, paths[-1])
            g.goal(0)
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < 0.6:
                g.draw()
            paths.append(os.path.join(out, "camera_%s_%s_gol.png" % (cam.lower(), v)))
            pygame.image.save(_scr, paths[-1])
    g.state = "menu"
    return paths


def _run_for(secs):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < secs:
        g.draw()


def _play_for(secs, sim_secs=12.0):
    """Simula ate `sim_secs` de jogo (passos de 1/60 s) espalhados por `secs` de tempo real, desenhando
    a cada passo (as particulas e animacoes usam o relogio real)."""
    g.state = "play"
    t0 = time.perf_counter()
    steps = int(sim_secs * 60)
    while True:
        el = time.perf_counter() - t0
        if el >= secs:
            break
        while steps > 0 and steps > int(sim_secs * 60 * (1 - el / secs)):
            g.step(1 / 60)
            steps -= 1
        g.draw()


def _zoom(rect, path, k=3):
    sub = _scr.subsurface(pygame.Rect(rect)).copy()
    pygame.image.save(pygame.transform.scale(sub, (sub.get_width() * k, sub.get_height() * k)), path)


def ui_shots():
    """Capturas da Onda A4-A7: gol com confete/onomatopeia (mundial), mosaico e sinalizadores (estadio),
    telao, placa de LED (zoom), pausa com a opcao TORCIDA e menu com a linha "T: torcida"."""
    import tempfile
    out = os.environ.get("SOCCERPY_SHOTS_DIR") or tempfile.mkdtemp(prefix="soccerpy_shots_")
    os.makedirs(out, exist_ok=True)
    _crowd_prefs("ALTA")
    paths = []

    def save(name):
        paths.append(os.path.join(out, name))
        pygame.image.save(_scr, paths[-1])

    # mosaico do pontape inicial (estadio)
    random.seed(0)
    g.start_career_match(cfg("A", 65), cfg("B", 65), venue="estadio")
    _run_for(0.4)
    save("a4_mosaico_estadio.png")
    # gol: confete, flashes, onomatopeia, LED de gol, telao (mundial)
    _prep_crowd("mundial", warm=200)
    g.crowd.react.clear()
    _run_for(0.2)
    g.goal(0)
    _run_for(0.45)
    save("a4_gol_mundial.png")
    _zoom((40, 600, 520, 100), os.path.join(out, "a4_gol_zoom.png"), 2)
    _zoom((soccer.PITCH.left, 74, 500, 18), os.path.join(out, "a5_led_gol_zoom.png"), 3)
    _run_for(1.2)
    save("a4_gol_mundial_1s.png")
    _zoom((200, 640, 420, 60), os.path.join(out, "a6_telao_zoom.png"), 3)
    _run_for(1.5)
    save("a6_telao_cleide.png")
    # sinalizadores e fumaca (estadio), placa de LED comum
    _prep_crowd("estadio", warm=200)
    _run_for(0.2)
    g.goal(1)
    _run_for(1.2)
    save("a4_sinalizadores_estadio.png")
    _run_for(3.0)
    _zoom((soccer.PITCH.left, 74, 500, 18), os.path.join(out, "a5_led_zoom.png"), 3)
    _zoom((0, 620, 560, 80), os.path.join(out, "a4_faixas_zoom.png"), 2)
    # pausa com a opcao TORCIDA
    g.paused = True
    g.draw()
    save("a7_pausa.png")
    g.toggle_crowd()
    g.draw()
    save("a7_pausa_media.png")
    g.paused = False
    _crowd_prefs("ALTA")
    # menu
    g.state = "menu"
    g.draw()
    save("a7_menu.png")
    _zoom((300, 655, 500, 35), os.path.join(out, "a7_menu_zoom.png"), 2)
    paths.append(out)
    return paths


LOADOUT = (  # (chassis, [(modelo, raridade)]) dos 5 titulares da garagem "carregada" (capturas/testes A9)
    ("Goleiro", [("Radar LiDAR", 2), ("Chip Neural", 3)]),
    ("Titã", [("Blindado", 3), ("Vácuo Turbo", 2)]),
    ("Orbital", [("Canhão de Plasma", 3), ("Infravermelho", 1)]),
    ("Tanque", [("Blindado", 1), ("Escova de Sucção", 0)]),
    ("Velocista", [("Turbina", 3), ("Canhão de Plasma", 1), ("Chip de CPU", 1)]),
)


def loaded_garage(seed=1):
    """Garagem (em memoria, nunca gravada) com os 5 chassis e pecas visiveis equipadas (LOADOUT)."""
    import garage as G
    gg = G.new_game(random.Random(seed), "Faisca FC")
    for rb, (ch, models) in zip(gg.robots, LOADOUT):
        rb["chassis"] = ch
        for model, rar in models:
            pc = gg.new_piece(model, rar, 2)
            gg.inventory.append(pc)
            ok, msg = gg.equip(rb["id"], pc["id"])
            assert ok, msg
    return gg


class _FakeClock:
    """Relogio fixo para capturas (time.perf_counter do soccer): quadro `low` e fases deterministicas."""

    def __init__(self, t):
        self.t = t

    def perf_counter(self):
        return self.t


def robot_shots():
    """Capturas A9-A11: grade de todos os chassis x 8 direcoes (com e sem pecas, normal e low), zoom de
    robo com turbina/canhao, partida da campanha no estadio cheio e Modo Robos (bairro)."""
    import tempfile
    import robot_art
    import robots
    from types import SimpleNamespace
    out = os.environ.get("SOCCERPY_SHOTS_DIR") or tempfile.mkdtemp(prefix="soccerpy_shots_")
    os.makedirs(out, exist_ok=True)
    _crowd_prefs("ALTA")
    paths = []

    def save(name, surf=None):
        paths.append(os.path.join(out, name))
        pygame.image.save(surf or _scr, paths[-1])

    chassis = list(robots.CHASSIS)
    # sem conflito visual: o canhao e o blindado/vacuo ficam na frente; um de cada por robo
    sets = {"pecas": {"parts": (("turbina", 3), ("canhao", 3), ("radar", 2), ("modulo", 3), ("escova", 0)),
                      "hot": True},
            "pecas2": {"parts": (("blindado", 2), ("vacuo", 1), ("antena", 1)), "hot": False}}
    team = SimpleNamespace(idx=0, human=None, color=(0, 200, 255), gk_color=(250, 200, 40), players=[])
    real_time = soccer.time
    for tag, vis, bat in (("normal", None, 1.0), ("pecas", sets["pecas"], 1.0), ("pecas2", sets["pecas2"], 1.0),
                          ("low", sets["pecas"], 0.2)):
        _scr.fill((6, 12, 26))
        _scr.blit(g.pitch_surf, (0, 0), pygame.Rect(0, 0, 1100, 700))
        soccer.time = _FakeClock(0.0 if tag == "low" else 0.33)
        g.state, g.paused, g.speed_idx = "play", True, 0
        for r, ch in enumerate(chassis):
            for dcol in range(8):
                a = dcol * math.pi / 4
                p = SimpleNamespace(pos=soccer.V(140 + dcol * 110, 130 + r * 90), face=soccer.V(math.cos(a), math.sin(a)),
                                    vel=soccer.V(math.cos(a), math.sin(a)) * 100, bat=bat, idx=dcol, vis=vis,
                                    art=None, vdir=None, fx_next=1e9, chassis=ch, paint=None,
                                    role="GK" if ch == "Goleiro" else "MID", team=team)
                g.draw_player(team, p)
            g.text(ch, 22, (230, 240, 250), midleft=(10, 130 + r * 90), shadow=True)
        save("a9_grade_%s.png" % tag)
        if tag == "pecas":
            _zoom((140 - 40, 130 + 2 * 90 - 40, 300, 80), os.path.join(out, "a9_zoom_velocista.png"), 4)
            paths.append(os.path.join(out, "a9_zoom_tita_orbital.png"))
            _zoom((140 - 40, 130 + 4 * 90 - 40, 300, 170), paths[-1], 3)
            paths.append(os.path.join(out, "a9_zoom_velocista.png"))
        if tag == "low":
            _zoom((100, 130 - 40, 340, 6 * 90), os.path.join(out, "a11_zoom_low.png"), 2)
            paths.append(os.path.join(out, "a11_zoom_low.png"))
    soccer.time = real_time
    g.paused = False
    # partida da campanha (estadio cheio) com a garagem carregada
    gg = loaded_garage()
    random.seed(3)
    opp = soccer.robots  # noqa: F841
    import robot_league as RL
    away = RL.match_cfg(RL.opponent_team("Platinum", (230, 230, 245), 60, 7))
    g.start_robot_match(gg.match_cfg(), away, lambda s, e: None, return_state="campaign", venue="estadio")
    _play_for(2.5)
    save("a9_campanha_estadio.png")
    b = g.ball.pos
    r = pygame.Rect(0, 0, 360, 240)
    r.center = (int(b.x), int(b.y))
    _zoom(r.clamp(soccer.PITCH), os.path.join(out, "a9_campanha_zoom.png"), 3)
    paths.append(os.path.join(out, "a9_campanha_zoom.png"))
    random.seed(5)
    g.start_robot_match(gg.match_cfg(), away, lambda s, e: None, return_state="campaign", venue="estadio")
    for t in g.teams:                                     # bateria baixa/critica: faiscas e fumaca
        for k, p in enumerate(t.players):
            p.bat = (0.2, 0.06, 0.3, 0.2, 0.06)[k]
    soccer.BATTERY_ON = False                             # congela a bateria (so para a captura)
    _play_for(1.2, sim_secs=1.5)
    soccer.BATTERY_ON = True
    save("a11_bateria_fumaca.png")
    p = g.teams[0].players[1]
    r.center = (int(p.pos.x), int(p.pos.y))
    _zoom(r.clamp(soccer.PITCH), os.path.join(out, "a11_fumaca_zoom.png"), 3)
    paths.append(os.path.join(out, "a11_fumaca_zoom.png"))
    g.match_sink = None
    # Modo Robos (bairro)
    random.seed(4)
    import garage as G
    g2 = G.new_game(random.Random(2), "Bairro FC")
    g.start_robot_match(g2.match_cfg(), RL.match_cfg(RL.opponent_team("Vila Poeira", (255, 120, 40), 50, 3)),
                        lambda s, e: None, venue="bairro")
    _play_for(2.5)
    save("a9_robos_bairro.png")
    g.match_sink = None
    g.state = "menu"
    paths.append(out)
    return paths


def skill_shots():
    """B7: capturas de uma partida do Modo Robos com skills (estadio): pausa o motor no quadro em que
    Arrancada, Muralha e Choque estao visiveis e salva um PNG (+ zoom) de cada."""
    import tempfile
    out = os.environ.get("SOCCERPY_SHOTS_DIR") or tempfile.mkdtemp(prefix="soccerpy_shots_")
    os.makedirs(out, exist_ok=True)
    _crowd_prefs("ALTA")
    paths = []
    want = {"dash": "b7_arrancada", "shield": "b7_muralha", "zap": "b7_choque", "curve": "b7_curva",
            "gloves": "b7_elastica", "magnet": "b7_succao", "sparks": "b7_pressao"}
    for seed in range(12):
        if not want:
            break
        random.seed(seed)
        g.start_robot_match(robot_cfg("A", 62, 11), robot_cfg("B", 60, 22), lambda s, e: None,
                            tuning=soccer.robots.TUNING_ROBOTS, return_state="campaign", venue="estadio")
        for _ in range(60 * 90):
            if g.state == "over" or not want:
                break
            g.step(1 / 60)
            hit = None
            for t in g.teams:
                for p in t.players:
                    k = "zap" if p.sk_zap is not None else p.sk_fx
                    if g.ball.curve and "curve" in want:
                        k, p = "curve", g.last_owner or p
                    if k in want and g.state == "play":
                        hit = (k, p)
            if hit is None:
                continue
            k, p = hit
            for _ in range(3):
                g.draw()
            name = want.pop(k)
            paths.append(os.path.join(out, name + ".png"))
            pygame.image.save(_scr, paths[-1])
            pos = g.ball.pos if k == "curve" else p.pos
            # estadio: o mundo e reduzido para crowd.CAM_RECT; o zoom recorta da tela no ponto mapeado
            import crowd
            if g.camera_on():
                sx = crowd.CAM_POS[0] + (pos.x - crowd.CAM_CROP.x) * crowd.CAM_SIZE[0] / crowd.CAM_CROP.w
                sy = crowd.CAM_POS[1] + (pos.y - crowd.CAM_CROP.y) * crowd.CAM_SIZE[1] / crowd.CAM_CROP.h
            else:
                sx, sy = pos.x, pos.y
            r = pygame.Rect(0, 0, 220, 150)
            r.center = (int(sx), int(sy))
            paths.append(os.path.join(out, name + "_zoom.png"))
            _zoom(r.clamp(_scr.get_rect()), paths[-1], 3)
    g.match_sink = None
    g.state = "menu"
    paths.append(out)
    return paths


def golden_scores():
    out = {}
    for oa, ob in MATCHUPS:
        out["%dx%d" % (oa, ob)] = [list(play(oa, ob, s)[:2]) for s in SEEDS]
    return out


def golden(flag, legacy=True):
    path = GOLDEN_PATH if legacy else GOLDEN_NEW_PATH
    with mode(legacy):
        cur = golden_scores()
    if flag == "--write":
        with open(path, "w") as f:
            json.dump(cur, f, indent=1)
        print("golden gravado:", path, "(%d placares)" % sum(len(v) for v in cur.values()))
        return 0
    with open(path) as f:
        ref = json.load(f)
    bad = 0
    for k, v in cur.items():
        for s, (a, b) in enumerate(zip(v, ref.get(k, []))):
            if a != b:
                bad += 1
                print("DIFF", k, "seed", s, "atual", a, "golden", b)
    n = sum(len(v) for v in cur.values())
    print("golden%s %s: %d/%d placares identicos" % ("" if legacy else "-new", "OK" if not bad else "FALHOU", n - bad, n))
    return 1 if bad else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["golden"] and len(a) == 2 and a[1] in ("--write", "--check"):
        sys.exit(golden(a[1]))
    elif a[:1] == ["golden-new"] and len(a) == 2 and a[1] in ("--write", "--check"):
        sys.exit(golden(a[1], legacy=False))
    elif a[:1] == ["run"]:
        print(run(int(a[1]), int(a[2]), int(a[3]), int(a[4]) if len(a) > 4 and a[4].isdigit() else 0,
                  legacy="legacy" in a))
    elif a[:1] == ["run-skills"]:
        print(run_skills(int(a[1]), int(a[2]), int(a[3]), int(a[4]) if len(a) > 4 and a[4].isdigit() else 0,
                         with_skills="off" not in a))
    elif a[:1] == ["skill-shots"]:
        for p in skill_shots():
            print(p)
    elif a[:1] == ["draw"] and "--crowd" in a:
        lv = [x for x in a if x in ("ALTA", "MEDIA")]
        cam = [x for x in a if x in ("ESTADIO", "PERTO")]
        for k, v in draw_crowd_ms(lv[0] if lv else "ALTA", camera=cam[0] if cam else None).items():
            print(k, v)
    elif a[:1] == ["draw"]:
        print(draw_ms())
    elif a[:1] == ["ui-shots"]:
        for p in ui_shots():
            print(p)
    elif a[:1] == ["robot-shots"]:
        for p in robot_shots():
            print(p)
    elif a[:1] == ["camera-shots"]:
        for p in camera_shots(a[1:] or None):
            print(p)
    elif a[:1] == ["crowd-shots"]:
        for p in crowd_shots(a[1:] or None):
            print(p)
    elif a[:1] == ["shot"]:
        print(shot(a[1]))
    else:
        print(__doc__)
        sys.exit(2)
