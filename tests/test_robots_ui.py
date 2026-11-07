"""Testes da UI do Modo Robôs (passos 10-11). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_robots_ui.py

NUNCA toca ~/.soccerpy_*.json: stores de garage e career vão para dicts em memória,
trocados ANTES de criar o Game.
"""
import os
import random
import shutil
import sys
import tempfile
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
os.chdir(os.path.join(ROOT, "game"))

import pygame  # noqa: E402

import career  # noqa: E402
import store  # noqa: E402
import garage as gm  # noqa: E402

MEM = {}          # garage: {"save": str, "bad": str}
CAREER = {}       # career: {"save": str}
gm._store_get = lambda: MEM.get("save")
gm._store_set = lambda t: MEM.__setitem__("save", t) or True
gm._store_set_bad = lambda t: MEM.__setitem__("bad", t) or True
career._store_get = lambda: CAREER.get("save")
career._store_set = lambda t: CAREER.__setitem__("save", t) or True

import robots_ui  # noqa: E402
import soccer  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)
ui = g.robots_ui
SCRATCH = tempfile.mkdtemp(prefix="soccerpy_ui_test_")
SHOTS_DIR = os.environ.get("SOCCERPY_SHOTS_DIR")          # screenshots só se definido


def reset(save=None, career_save=None):
    MEM.clear()
    CAREER.clear()
    if save is not None:
        MEM["save"] = save
    if career_save is not None:
        CAREER["save"] = career_save
    g.has_save = career.Career.has_save()
    g.refresh_robots_status()
    g.state = "menu"


def click(pos):
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def key(k):
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, unicode=""))


def click_btn(label_rect_fn):
    """Clica no primeiro botão de ui.buttons cujo rect satisfaz o predicado.
    Cada clique consome os botões (handle_event os invalida): redesenha se faltarem."""
    if not ui.buttons:
        frame()
    for r, fn, enabled in ui.buttons:
        if enabled and label_rect_fn(r):
            click(r.center)
            return True
    return False


def frame():
    g.update(1 / 60)
    g.draw()


def new_game_open():
    reset()
    key(pygame.K_5)
    frame()
    assert g.state == "robots" and ui.screen_id == "menu"
    click_btn(lambda r: r.size == (300, 64) and r.y == 400)       # NOVO JOGO
    frame()
    assert ui.screen_id == "hub" and ui.garage is not None


def saved_text():
    return MEM.get("save")


# ------------------------------------------------------------------ menu principal
def test_main_menu_button_5_layout():
    reset()
    assert g.robots_btn() == pygame.Rect(soccer.W // 2 - 160, 450, 320, 70)       # centralizado
    reset(career_save='{"user": 1}')
    assert g.has_save
    assert g.continue_btn == pygame.Rect(soccer.W // 2 - 330, 450, 320, 70)
    assert g.robots_btn() == pygame.Rect(soccer.W // 2 + 10, 450, 320, 70)
    for _ in range(3):
        frame()


def test_menu_opens_by_key_and_click():
    reset()
    key(pygame.K_5)
    assert g.state == "robots"
    ui.to_menu()
    assert g.state == "menu"
    click(g.robots_btn().center)
    assert g.state == "robots" and ui.screen_id == "menu"
    key(pygame.K_ESCAPE)
    assert g.state == "menu"


def test_career_speed_keys_unchanged():
    g.start_career_match({"name": "A", "color": (200, 0, 0), "squad": [("a%d" % i, 60) for i in range(5)]},
                         {"name": "B", "color": (0, 0, 200), "squad": [("b%d" % i, 60) for i in range(5)]})
    key(pygame.K_3)
    assert g.speed_idx == 2
    key(pygame.K_5)
    assert g.state != "robots"
    g.new_match(1)
    g.state = "menu"


def test_menu_subtitle_follows_status():
    reset()
    assert g.robots_status == "none"
    ui.open()
    ui.do_new()
    assert saved_text() and g.robots_status == "ok"
    ui.to_menu()
    assert g.robots_status == "ok" and g.state == "menu"
    g.draw()
    assert ("continuar", 22, (190, 245, 232)) in g.text_cache


def test_menu_status_cached_not_read_per_frame():
    reset()
    calls = []
    orig = gm._store_get
    gm._store_get = lambda: calls.append(1) or orig()
    try:
        g.state = "menu"
        for _ in range(30):
            frame()
        assert not calls, "menu leu o store durante o draw"
        ui.open()
        n = len(calls)
        for _ in range(30):
            frame()
        assert len(calls) == n, "tela do modo robôs leu o store durante o draw"
    finally:
        gm._store_get = orig


# ------------------------------------------------------------- novo jogo / continuar
def test_new_game_then_continue():
    new_game_open()
    assert saved_text() is not None
    name = ui.garage.team["name"]
    ui.to_menu()
    ui.open()
    assert ui.status == "ok"
    frame()
    assert click_btn(lambda r: r.size == (300, 64) and r.y == 220)   # CONTINUAR
    assert ui.screen_id == "hub" and ui.garage.team["name"] == name


def test_new_game_over_valid_save_needs_confirmation():
    new_game_open()
    before = saved_text()
    ui.to_menu()
    ui.open()
    ui.rng = random.Random(5)
    ui.do_shuffle_name()
    frame()
    click_btn(lambda r: r.size == (300, 64) and r.y == 400)         # NOVO JOGO (1o clique so pede confirmar)
    assert ui.screen_id == "menu" and ui.confirm_new and saved_text() == before
    frame()
    assert click_btn(lambda r: r.size == (200, 40))                  # CANCELAR
    assert not ui.confirm_new and saved_text() == before
    frame()
    click_btn(lambda r: r.size == (300, 64) and r.y == 400)
    frame()
    assert click_btn(lambda r: r.size == (400, 56))                  # CONFIRMAR
    assert ui.screen_id == "hub"


def test_incompatible_save_never_overwritten_without_confirmation():
    raw = '{"v": 99, "robots": "lixo"}'
    reset(save=raw)
    assert g.robots_status == "bad"
    key(pygame.K_5)
    frame()
    assert ui.status == "bad" and MEM.get("bad") == raw
    assert ("Save incompatível", 40, (240, 100, 90)) in g.text_cache
    # clicar em NOVO JOGO so pede confirmacao
    click_btn(lambda r: r.size == (300, 64) and r.y == 400)
    assert ui.confirm_new and MEM["save"] == raw and ui.screen_id == "menu"
    # sair e voltar sem confirmar: save intacto
    key(pygame.K_ESCAPE)
    assert MEM["save"] == raw and g.state == "menu" and g.robots_status == "bad"
    # confirmando, ai sim substitui
    key(pygame.K_5)
    frame()
    click_btn(lambda r: r.size == (300, 64) and r.y == 400)
    frame()
    click_btn(lambda r: r.size == (400, 56))
    assert ui.screen_id == "hub" and MEM["save"] != raw
    assert gm.Garage.load_status() == "ok"


def test_menu_has_no_continue_without_save():
    reset()
    key(pygame.K_5)
    frame()
    assert not click_btn(lambda r: r.size == (300, 64) and r.y == 220)


# --------------------------------------------------------------------- todas as telas
def screens():
    return [s for s in robots_ui.SCREENS if s != "menu"]


def test_all_screens_draw_and_back_to_menu():
    new_game_open()
    for sid in screens():
        ui.go(sid)
        for _ in range(60):
            frame()
        assert ui.screen_id == sid
    # abas por clique
    ui.go("hub")
    frame()
    for _, label in robots_ui.TABS:
        pass
    for k, (tid, _) in enumerate(robots_ui.TABS):
        frame()
        click((20 + k * 160 + 5, 82 + 5))
        frame()
        assert ui.screen_id == tid
    # stubs: Esc volta ao hub; hub: Esc salva e volta ao menu
    ui.go("round")
    key(pygame.K_ESCAPE)
    assert ui.screen_id == "hub" and g.state == "robots"
    del MEM["save"]
    key(pygame.K_ESCAPE)
    assert g.state == "menu" and MEM.get("save"), "Esc no hub deve salvar e voltar ao menu"
    # botao SALVAR E SAIR
    ui.open()
    ui.do_continue()
    frame()
    del MEM["save"]
    assert click_btn(lambda r: r.size == (190, 40) and r.x == soccer.W - 210)
    assert g.state == "menu" and MEM.get("save")
    # menu do modo (com e sem save) desenha
    for st in ("ok", "bad", "none"):
        reset(save={"ok": MEM.get("save"), "bad": "{", "none": None}[st])
        ui.open()
        for _ in range(5):
            frame()
        ui.to_menu()


def test_zero_surface_per_frame_after_warmup():
    new_game_open()
    real = pygame.Surface
    count = [0]

    class Counting(real):
        def __init__(self, *a, **k):
            count[0] += 1
            super().__init__(*a, **k)

    # menu (sem e com aviso), todas as telas e abas
    cases = [("menu_main", None), ("menu_robots_ok", None), ("menu_robots_bad", None)] + \
            [(s, s) for s in screens()]
    for name, sid in cases:
        if name == "menu_main":
            g.state = "menu"
        elif name.startswith("menu_robots"):
            reset(save={"menu_robots_ok": MEM.get("save"), "menu_robots_bad": "{"}[name]
                  if name != "menu_robots_ok" else gm.new_game(random.Random(1)).to_json())
            ui.open()
        else:
            if g.state != "robots" or ui.garage is None:
                reset(save=gm.new_game(random.Random(1)).to_json())
                ui.open()
                ui.do_continue()
            ui.go(sid)
        for _ in range(5):
            frame()                       # aquecimento (sprites/fontes/texto)
        pygame.Surface = Counting
        try:
            count[0] = 0
            for _ in range(60):
                frame()
        finally:
            pygame.Surface = real
        assert count[0] == 0, "%s criou %d Surface em 60 quadros" % (name, count[0])
        if name.startswith("menu_robots"):
            ui.to_menu()


def test_text_cache_keys_below_max():
    new_game_open()
    cases = [None] + screens()
    for sid in cases:
        if sid is None:
            g.state = "menu"
        else:
            if g.state != "robots" or ui.garage is None:
                ui.open()
                ui.do_continue()
            ui.go(sid)
        g.text_cache.clear()
        keys = set()
        for _ in range(60):
            frame()
            keys.update(g.text_cache.keys())
        assert len(keys) < soccer.TEXT_CACHE_MAX, (sid, len(keys))
        assert len(keys) < 150, (sid, len(keys))     # folga confortavel
        assert len(g.text_cache) <= soccer.TEXT_CACHE_MAX


# ----------------------------------------------------------------------- aba GARAGEM
def garage_open():
    new_game_open()
    click((20 + 160 + 5, 87))
    frame()
    assert ui.screen_id == "garage"


def row_rect(k, reserve=False):
    y = (416 if reserve else 160) + k * 44
    return pygame.Rect(20, y, 700, 40)


def test_garage_select_and_attr_panel():
    garage_open()
    gg = ui.garage
    assert ui.sel == gg.lineup[0]
    # extra robo reserva
    gg.scrap = 10_000
    assert gg.buy_robot("Disco", rng=random.Random(2))[0]
    ui.cache = None
    frame()
    click(row_rect(2).center)
    assert ui.sel == gg.lineup[2]
    frame()
    click(row_rect(0, reserve=True).center)
    rid = [r["id"] for r in gg.robots if r["id"] not in gg.lineup][0]
    assert ui.sel == rid
    frame()
    attrs, ovr = ui.info()["per"][rid]
    assert list(attrs) == list(__import__("robots").ATTRS) and 20 <= ovr <= 99


def test_garage_place_mode_swaps_lineup():
    garage_open()
    gg = ui.garage
    gg.scrap = 10_000
    gg.buy_robot("Disco", rng=random.Random(2))
    ui.cache = None
    frame()
    reserve = [r["id"] for r in gg.robots if r["id"] not in gg.lineup][0]
    click(row_rect(0, reserve=True).center)
    frame()
    assert click_btn(lambda r: r.size == (295, 44) and r.y == 462)           # ESCALAR
    assert ui.place_mode
    frame()
    old = gg.lineup[3]
    click(row_rect(3).center)
    assert gg.lineup[3] == reserve and old not in gg.lineup and not ui.place_mode
    assert ui.msg == "Escalação alterada." and MEM.get("save")
    frame()
    # trocar entre titulares
    click(row_rect(1).center)
    sel = ui.sel
    ui.toggle_place()
    frame()
    a, b = gg.lineup[1], gg.lineup[4]
    click(row_rect(4).center)
    assert gg.lineup[4] == a and gg.lineup[1] == b
    # Esc cancela o modo sem sair da tela
    ui.toggle_place()
    key(pygame.K_ESCAPE)
    assert not ui.place_mode and ui.screen_id == "garage" and g.state == "robots"
    # mensagem de erro do garage (mesmo slot) aparece
    ui.sel = gg.lineup[0]
    ui.toggle_place()
    frame()
    click(row_rect(0).center)
    assert ui.msg == "Já está nesse slot."
    assert sel is not None


def test_garage_auto_and_bench_buttons():
    garage_open()
    gg = ui.garage
    gg.lineup = list(reversed(gg.lineup))
    frame()
    assert click_btn(lambda r: r.size == (295, 44) and r.y == 512)           # AUTO
    assert ui.msg == "Escalação automática aplicada."
    frame()
    click(row_rect(1).center)
    sel = ui.sel
    assert click_btn(lambda r: r.size == (295, 44) and r.y == 562)           # BANCADA
    assert ui.screen_id == "bench" and ui.bench_rid == sel
    frame()
    assert click_btn(lambda r: r.size == (185, 36) and r.y == 132)           # VOLTAR (bancada)
    assert ui.screen_id == "garage" and ui.sel == sel


def test_garage_uses_cached_sprite():
    garage_open()
    frame()
    n = len(g.sprites)
    for _ in range(30):
        frame()
    assert len(g.sprites) == n and n >= 1


# ------------------------------------------------------------------------- BANCADA
def shot(name):
    frame()
    if SHOTS_DIR:
        os.makedirs(SHOTS_DIR, exist_ok=True)
        pygame.image.save(g.screen, "%s/%s.png" % (SHOTS_DIR, name))


def bench_open(scrap=1000):
    garage_open()
    gg = ui.garage
    gg.scrap = scrap
    ui.cache = None
    frame()
    assert click_btn(lambda r: r.size == (295, 44) and r.y == 562)           # ABRIR BANCADA
    frame()
    assert ui.screen_id == "bench"
    return gg


def slot_rect(i):
    return pygame.Rect(20, 182 + i * 50, 280, 46)


def piece_rect(k):
    return pygame.Rect(312, 214 + k * 33, 410, 30)


def btn_at(x, y):
    return click_btn(lambda r: r.x == x and r.y == y)


def free_part(gg, model, rar=1, lvl=0):
    p = gg.new_piece(model, rar, lvl)
    gg.inventory.append(p)
    return p


def test_bench_draw_states_zero_surface_and_cache():
    gg = bench_open()
    rb = gg.robot(ui.bench_rid)
    free_part(gg, "Motor Escovado", 2)
    rb["slots"]["sensor"] = None
    real = pygame.Surface
    count = [0]

    class Counting(real):
        def __init__(self, *a, **k):
            count[0] += 1
            super().__init__(*a, **k)

    steps = [None, "sensor", "motor", "piece", "edit"]
    g.text_cache.clear()
    keys = set()
    for st in steps:
        if st in ("sensor", "motor"):
            frame()
            click(slot_rect(__import__("parts").SLOTS.index(st)).center)
        elif st == "piece":
            frame()
            click(piece_rect(0).center)
        elif st == "edit":
            frame()
            click(robots_ui.NAME_FIELD.center)
            assert ui.editing
        for _ in range(5):
            frame()
        pygame.Surface = Counting
        try:
            count[0] = 0
            for _ in range(60):
                frame()
                keys.update(g.text_cache.keys())
        finally:
            pygame.Surface = real
        assert count[0] == 0, (st, count[0])
    assert len(keys) < soccer.TEXT_CACHE_MAX and len(keys) < 300, len(keys)
    ui.editing = False


def test_bench_modulo_slot_layout_and_equip():
    """B4: sem mod_on a bancada tem os 7 slots de sempre; com mod_on, 8 slots a 42 px (altura 38),
    acima das acoes (y 548), e o Modulo equipa pela bancada."""
    gg = bench_open()
    assert not gg.mod_on()
    rects = robots_ui.bench_slot_rects(False)
    assert [s for s, _ in rects] == list(robots_ui.P.GEAR_SLOTS)
    assert all(r == slot_rect(i) for i, (_s, r) in enumerate(rects))
    rects8 = robots_ui.bench_slot_rects(True)
    assert [s for s, _ in rects8] == list(robots_ui.P.SLOTS) and len(rects8) == 8
    assert rects8[-1][1].bottom == 512 < 548 and all(r.h == 38 for _s, r in rects8)
    for (_a, r1), (_b, r2) in zip(rects8, rects8[1:]):
        assert r2.y - r1.y == 42 and not r1.colliderect(r2)
    mod = free_part(gg, "Módulo Arrancada", 2)
    ok, _ = gg.equip(ui.bench_rid, mod["id"])
    assert not ok                                          # bloqueado sem mod_on
    gg.flags["mod_on"] = 1
    frame()
    click(rects8[-1][1].center)
    frame()
    assert ui.sel_slot == "modulo"
    click(piece_rect(0).center)
    frame()
    assert ui.sel_piece == mod["id"]
    assert btn_at(20, 548)                                 # EQUIPAR
    frame()
    assert gg.robot(ui.bench_rid)["slots"]["modulo"] == mod["id"]
    zero_surface_frames(30)
    gg.flags.pop("mod_on", None)
    gg.robot(ui.bench_rid)["slots"]["modulo"] = None


def test_bench_full_flow():
    gg = bench_open(scrap=1000)
    rid = ui.bench_rid
    rb = gg.robot(rid)
    saves0 = MEM.get("save")
    assert ui.garage.robot(rid)["name"] in [r["name"] for r in gg.robots]
    # 1) selecionar slot (motor) e peça livre mais forte
    new = free_part(gg, "Motor Escovado", 2, 0)
    frame()
    click(slot_rect(0).center)
    assert ui.sel_slot == "motor"
    frame()
    free = gg.free_pieces("motor")
    assert new in free
    k = free.index(new)
    click(piece_rect(k).center)
    assert ui.sel_piece == new["id"]
    # 2) ANTES/DEPOIS nao muta o garage
    snap = gg.to_json()
    before = dict(gg.attrs_of(rb))
    frame()
    assert gg.to_json() == snap and rb["slots"]["motor"] != new["id"]
    shot("bench_compare")
    # 3) EQUIPAR
    old_pid = rb["slots"]["motor"]
    assert btn_at(20, 548)
    assert rb["slots"]["motor"] == new["id"] and ui.sel_piece is None
    assert old_pid is None or old_pid in [p["id"] for p in gg.free_pieces("motor")], (old_pid, [r["slots"]["motor"] for r in gg.robots])
    after = gg.attrs_of(rb)
    assert after != before and MEM.get("save") != saves0
    # 4) UPGRADE (sucata desce, nivel sobe)
    frame()
    sc, lv = gg.scrap, new["lvl"]
    assert btn_at(20, 598)
    assert gg.scrap < sc and new["lvl"] == lv + 1
    # sem sucata: desabilitado
    gg.scrap = 0
    frame()
    assert not any(r.x == 20 and r.y == 598 and en for r, fn, en in ui.buttons)
    gg.scrap = 1000
    # 5) renomear via KEYDOWN com unicode
    frame()
    click(robots_ui.NAME_FIELD.center)
    assert ui.editing
    for _ in range(20):
        key(pygame.K_BACKSPACE)
    assert ui.edit_text == ""
    for ch in "Robo\u4e2d\u00e7\u00e3o 1234567890":
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=ch))
    assert ui.edit_text == "Robo\u00e7\u00e3o 1234", ui.edit_text      # CJK ignorado, max 12
    assert len(ui.edit_text) == 12
    for _ in range(3):
        frame()
    shot("bench_rename")
    key(pygame.K_BACKSPACE)
    key(pygame.K_ESCAPE)                                        # Esc cancela so a edicao
    assert not ui.editing and ui.screen_id == "bench" and rb["name"] != "Robo\u00e7\u00e3o 123"
    frame()
    click(robots_ui.NAME_FIELD.center)
    for ch in "":
        pass
    ui.edit_text = ""
    for ch in "Fulano":
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=ch))
    key(pygame.K_RETURN)
    assert rb["name"] == "Fulano" and not ui.editing
    assert __import__("json").loads(MEM["save"])["robots"][[r["id"] for r in gg.robots].index(rid)]["name"] == "Fulano"
    # sortear nome (rede de seguranca)
    frame()
    assert btn_at(941, 482)
    assert rb["name"] in robots_ui.FUN_NAMES
    # 6) pintar
    frame()
    sw = pygame.Rect(748 + 3 * 53, 538, 48, 24)
    n0 = len(g.sprites)
    click(sw.center)
    assert tuple(rb["paint"]) == gm.PAINT_PALETTE[3]
    frame()
    assert g.robot_sprite(rb) is g.robot_sprite(rb)
    # 7) overclock cicla
    for want in (1, 2, 0):
        frame()
        assert click_btn(lambda r: r.size == (318, 34) and r.x == 748)
        assert rb["oc"] == want
        if want:
            assert "bateria gasta mais" in ui.msg
    # 8) VENDER com confirmacao (peca livre)
    spare = free_part(gg, "Motor Escovado", 1, 0)
    frame()
    ui.pick_slot("motor")
    frame()
    k = gg.free_pieces("motor").index(spare)
    click(piece_rect(k).center)
    frame()
    sc = gg.scrap
    assert btn_at(165, 598)
    assert spare in gg.inventory and gg.scrap == sc and ui.confirm_sell == spare["id"]
    frame()
    assert btn_at(165, 598)
    assert spare not in gg.inventory and gg.scrap == sc + __import__("parts").sell_price(spare)
    # vender peca equipada: desequipa e vende
    frame()
    ui.pick_slot("chip")
    cur = rb["slots"]["chip"]
    if cur is not None:
        frame()
        btn_at(165, 598)
        frame()
        btn_at(165, 598)
        assert rb["slots"]["chip"] is None and gg.piece(cur) is None
    # desequipar
    ui.pick_slot("motor")
    frame()
    assert btn_at(165, 548)
    assert rb["slots"]["motor"] is None
    frame()
    shot("bench_empty_slot")
    # nav entre robos e VOLTAR
    frame()
    first = ui.bench_rid
    assert click_btn(lambda r: r.size == (70, 36) and r.x == 815)
    assert ui.bench_rid != first
    assert click_btn(lambda r: r.size == (70, 36) and r.x == 735)
    assert ui.bench_rid == first
    frame()
    assert click_btn(lambda r: r.size == (185, 36) and r.y == 132)
    assert ui.screen_id == "garage" and ui.sel == rid
    # cabecalho/abas na bancada
    ui.open_bench()
    frame()
    assert any(r.size == (150, 40) and r.y == 82 for r, fn, en in ui.buttons)


def test_bench_esc_without_edit_returns_to_garage():
    bench_open()
    key(pygame.K_ESCAPE)
    assert ui.screen_id == "garage" and g.state == "robots"


def test_bench_upgrade_disabled_at_max_and_sell_blocked_msgs():
    gg = bench_open()
    rb = gg.robot(ui.bench_rid)
    pc = free_part(gg, "Motor Escovado", 1, 0)
    gg.equip(rb["id"], pc["id"])
    pid = pc["id"]
    gg.piece(pid)["lvl"] = __import__("parts").MAX_UP
    frame()
    ui.pick_slot("motor")
    frame()
    assert not any(r.x == 20 and r.y == 598 and en for r, fn, en in ui.buttons)


# ----------------------------------------------------------------- LOJA e LIGA (passos 13-14)
import robot_league as RL  # noqa: E402


def fresh(seed=11, scrap=None):
    """Garagem nova (RNG do UI fixo) aberta no hub, stores em memória."""
    reset()
    ui.rng = random.Random(seed)
    key(pygame.K_5)
    frame()
    click_btn(lambda r: r.size == (300, 64) and r.y == 400)
    frame()
    assert ui.screen_id == "hub"
    if scrap is not None:
        ui.garage.scrap = scrap
        ui.cache = None
    return ui.garage


def saved():
    """Garage lido do store em memória (reflete o save mais recente)."""
    return gm.Garage.load()


def tab(tid):
    k = [t for t, _ in robots_ui.TABS].index(tid)
    frame()
    click((20 + k * 160 + 5, 82 + 5))
    frame()
    assert ui.screen_id == tid


def zero_surface_frames(n=60):
    real = pygame.Surface
    count = [0]

    class Counting(real):
        def __init__(self, *a, **k):
            count[0] += 1
            super().__init__(*a, **k)

    for _ in range(5):
        frame()
    g.text_cache.clear()
    keys = set()
    pygame.Surface = Counting
    try:
        for _ in range(n):
            frame()
            keys.update(g.text_cache.keys())
    finally:
        pygame.Surface = real
    assert count[0] == 0, "criou %d Surface em %d quadros" % (count[0], n)
    assert len(keys) < soccer.TEXT_CACHE_MAX and len(keys) < 200, len(keys)


def shop_stock_row(k):
    return pygame.Rect(20, 238 + k * 38, 1060, 34)


def test_shop_draw_states_zero_surface_and_cache():
    gg = fresh(scrap=3000)
    tab("shop")
    zero_surface_frames()                                            # PEÇAS / COMPRAR / TODOS
    for sl in robots_ui.P.GEAR_SLOTS:        # filtros da loja = 7 slots de equipamento (modulo: B12)
        ui.set_shop_slot(sl)
        zero_surface_frames(10)
    ui.set_shop_slot(None)
    click(shop_stock_row(0).center)
    frame()
    assert ui.shop_sel is not None
    shot("t13_loja_pecas")
    ui.set_shop_mode("sell")                                         # VENDER
    zero_surface_frames()
    ui.set_shop_mode("buy")
    ui.set_shop_tab("models")                                        # MODELOS
    ui.model_sel = "Tanque"
    zero_surface_frames()
    ui.model_sel = "Disco"
    shot("t13_loja_modelos")
    gg.scrap = 0                                                     # tudo vermelho / desabilitado
    ui.cache = None
    zero_surface_frames(10)
    ui.set_shop_tab("parts")
    zero_surface_frames(10)


def test_shop_buy_sell_flow():
    gg = fresh(scrap=1000)
    tab("shop")
    stock0 = len(gg.shop["stock"])
    inv0 = len(gg.inventory)
    ui.set_shop_slot(None)
    frame()
    lst = ui.shop_list()
    target = lst[0]
    price = robots_ui.P.buy_price(target)
    assert click_btn(lambda r: r == shop_stock_row(0))
    frame()
    assert ui.shop_sel == target["id"]
    assert click_btn(lambda r: r.x == 860 and r.y == 650)            # COMPRAR
    frame()
    assert gg.scrap == 1000 - price and len(gg.inventory) == inv0 + 1 and len(gg.shop["stock"]) == stock0 - 1
    s = saved()
    assert s.scrap == gg.scrap and any(p["id"] == target["id"] for p in s.inventory), "save não reflete a compra"
    # sem sucata: COMPRAR desabilitado
    gg.scrap = 0
    frame()
    click(shop_stock_row(0).center)
    frame()
    assert not any(en for r, fn, en in ui.buttons if r.x == 860 and r.y == 650)
    # VENDER com confirmação em dois cliques
    gg.scrap = 100
    ui.cache = None
    click_btn(lambda r: r.x == 640 and r.y == 132)                   # VENDER (modo)
    frame()
    assert ui.shop_mode == "sell"
    free = ui.shop_list()
    assert free and all(gg.equipped_by(p["id"]) is None for p in free)
    tp = free[0]
    click(shop_stock_row(0).center)
    frame()
    assert ui.shop_sel == tp["id"]
    n = len(gg.inventory)
    assert click_btn(lambda r: r.x == 860 and r.y == 650)            # 1º clique: só confirma
    frame()
    assert len(gg.inventory) == n and gg.scrap == 100 and ui.confirm_sell == tp["id"]
    assert click_btn(lambda r: r.x == 860 and r.y == 650)            # 2º clique: vende
    frame()
    assert len(gg.inventory) == n - 1 and gg.scrap == 100 + robots_ui.P.sell_price(tp)
    assert saved().scrap == gg.scrap
    # trocar de peça cancela a confirmação
    if ui.shop_list():
        click(shop_stock_row(0).center)
        frame()
        click_btn(lambda r: r.x == 860 and r.y == 650)
        frame()
        assert ui.confirm_sell is not None
        ui.set_shop_slot("chip")
        assert ui.confirm_sell is None
    # peça equipada nunca aparece
    eq = next(iter(gg.equipped_ids()))
    assert all(p["id"] != eq for p in ui.shop_list())


def test_shop_buy_robot_flow():
    gg = fresh(scrap=2000)
    tab("shop")
    click_btn(lambda r: r.x == 140 and r.y == 132)                   # MODELOS
    frame()
    assert ui.shop_tab == "models"
    # bloqueado: botão desabilitado
    click((300, 206 + 1 * 44 + 10))                                  # Tanque (bloqueado)
    frame()
    assert ui.model_sel == "Tanque"
    assert not any(en for r, fn, en in ui.buttons if r.x == 830 and r.y == 650)
    # Disco desbloqueado: compra até o elenco máximo (8)
    n0 = len(gg.robots)
    click((300, 206 + 10))
    frame()
    assert ui.model_sel == "Disco"
    price = gg.robot_price()
    assert click_btn(lambda r: r.x == 830 and r.y == 650)
    frame()
    assert len(gg.robots) == n0 + 1 and gg.scrap == 2000 - price
    assert len(saved().robots) == n0 + 1
    while len(gg.robots) < G_MAX:
        gg.scrap = 2000
        assert click_btn(lambda r: r.x == 830 and r.y == 650)
        frame()
    assert len(gg.robots) == G_MAX
    frame()
    assert not any(en for r, fn, en in ui.buttons if r.x == 830 and r.y == 650)    # elenco cheio
    gg.scrap = 2000
    assert ui.garage.buy_robot("Disco")[0] is False
    zero_surface_frames(10)


G_MAX = gm.MAX_SQUAD


def start_league():
    gg = ui.garage
    tab("hub")
    assert gg.league is None
    zero_surface_frames(10)                                          # LIGA sem liga
    shot("t14_liga_sem_liga")
    assert click_btn(lambda r: r.size == (320, 64))                  # INICIAR LIGA
    frame()
    assert gg.league is not None and gg.league["tier"] == gg.tier() and gg.league["round"] == 0
    assert saved().league is not None
    return gg.league


def test_league_draw_states():
    gg = fresh()
    lg = start_league()
    zero_surface_frames()                                            # LIGA com liga
    shot("t14_liga_tabela")
    for _ in range(3):
        assert click_btn(lambda r: r.size == (440, 44))              # SIMULAR
        frame()
        assert ui.screen_id == "round"
        zero_surface_frames(10)
        assert click_btn(lambda r: r.size == (260, 42))              # CONTINUAR
        frame()
        assert ui.screen_id == "hub"
    shot("t14_liga_rodada4")
    assert lg["round"] == 3 and len([x for x in lg["results"]]) == 9


def test_league_full_sim_to_end_and_rewards():
    gg = fresh(seed=5)
    lg = start_league()
    tier0 = lg["tier"]
    scrap_start = gg.scrap
    gained = 0
    xp_before = {r["id"]: (r["level"], r["xp"]) for r in gg.robots}
    for rnd in range(RL.ROUNDS):
        sc = gg.scrap
        assert gg.league["round"] == rnd
        assert click_btn(lambda r: r.size == (440, 44))              # SIMULAR
        frame()
        assert ui.screen_id == "round"
        info = ui.round_info
        assert gg.scrap == sc + info["rew"]["scrap"] and info["rew"]["scrap"] > 0
        gained += info["rew"]["scrap"]
        assert gg.stats["played"] == rnd + 1
        assert saved().stats["played"] == rnd + 1, "save atrasado"
        if rnd == 4:
            shot("t14_round_sim")
        for _ in range(60):
            frame()
        assert click_btn(lambda r: r.size == (260, 42))              # CONTINUAR
        frame()
        if rnd < RL.ROUNDS - 1:
            assert ui.screen_id == "hub"
            # cada rodada: loja reposta e todos os 3 jogos registrados
            assert len([x for x in gg.league["results"] if x[0] == rnd]) == 3
    assert ui.screen_id == "league_end"
    info = ui.end_info
    assert gg.league is None, "finish_league deve limpar a liga"
    assert gg.scrap == scrap_start + gained + info["prize"]
    assert 1 <= info["pos"] <= 6 and info["tier"] == tier0
    assert "Tanque" in gg.unlocked and info["unlocked"] == ["Tanque"]
    assert info["advanced"] == (info["pos"] <= 3)
    assert gg.tier_done == (tier0 if info["advanced"] else -1)
    assert gg.stats["played"] == 10 and gg.stats["w"] + gg.stats["d"] + gg.stats["l"] == 10
    assert any(r["level"] > 1 or r["xp"] > 0 for r in gg.robots)
    s = saved()
    assert s.league is None and s.scrap == gg.scrap and s.tier_done == gg.tier_done and "Tanque" in s.unlocked
    zero_surface_frames()
    shot("t14_league_end")
    assert click_btn(lambda r: r.size == (460, 64))                  # PRÓXIMA LIGA / REPETIR
    frame()
    assert ui.screen_id == "hub" and gg.league is not None and gg.league["tier"] == gg.tier()
    assert saved().league is not None
    # Esc em league_end/round volta ao hub sem perder a liga
    ui.go("round")
    key(pygame.K_ESCAPE)
    assert ui.screen_id == "hub"


def test_league_end_without_advancing_repeats_tier():
    gg = fresh(seed=3)
    start_league()
    gg.league["teams"][1]["ovr"] = 99
    # força o fim: registra 10 rodadas simuladas e coloca o usuário em último
    lg = gg.league
    for _ in range(RL.ROUNDS):
        RL.advance_round(lg, gg, random.Random(1))
    for x in lg["results"]:
        if RL.USER in (x[1], x[2]):
            x[3], x[4] = (0, 3) if x[1] == RL.USER else (3, 0)       # usuário perde tudo
    ui.to_league_end()
    frame()
    info = ui.end_info
    assert info["pos"] == 6 and info["advanced"] is False and gg.tier_done == -1
    assert gg.stats["titles"] == 0 and "Tanque" in gg.unlocked
    zero_surface_frames(10)
    assert click_btn(lambda r: r.size == (460, 64))
    frame()
    assert gg.league["tier"] == 0


def play_watched_match(speed_idx=3):
    gg = ui.garage
    sc, nres = gg.scrap, len(gg.league["results"])
    assert click_btn(lambda r: r.size == (440, 54))                  # ASSISTIR
    assert g.state in ("kickoff", "play") and g.career_match and g.match_sink is not None
    g.speed_idx = speed_idx
    for _ in range(20000):
        g.update(1 / 60)
        g.draw()
        if g.state == "over":
            break
    assert g.state == "over", "partida não terminou"
    assert g.state != "robots"
    return gg, sc, nres


def test_watch_match_max_reaches_round_with_rewards():
    gg = fresh(seed=9)
    start_league()
    gg, sc, nres = play_watched_match()
    fx_h = gg.league["fixtures"][0]
    score = list(g.score)
    events = list(g.events)
    xp_before = {r["id"]: (r["level"], r["xp"]) for r in gg.robots}
    key(pygame.K_RETURN)                                             # finaliza -> match_sink
    assert g.state == "robots" and ui.screen_id == "round", (g.state, ui.screen_id)
    assert g.match_sink is None and not g.career_match
    info = ui.round_info
    assert list(info["score"]) == score and info["sim"] is False
    assert len(gg.league["results"]) == nres + 3 and gg.league["round"] == 1
    uh = info["user_home"]
    my, opp = (score[0], score[1]) if uh else (score[1], score[0])
    side = 0 if uh else 1
    mine = [e for e in events if e["team"] == side and not e["own"]]
    # gols com pid creditam XP do autor (10 por gol)
    per_robot = {}
    for e in mine:
        if e["pid"] is not None:
            per_robot[e["pid"]] = per_robot.get(e["pid"], 0) + 1
    base = 20 + (15 if my > opp else 7 if my == opp else 0)
    for pid, n in per_robot.items():
        assert info["rew"]["xp"][pid] == base + 10 * n
    assert gg.scrap == sc + info["rew"]["scrap"] > sc
    assert saved().scrap == gg.scrap and saved().stats["played"] == 1
    assert len(info["goals"]) == len(events)
    for _ in range(60):
        frame()
    shot("t14_round_assistida")
    zero_surface_frames(10)
    # partida clássica e carreira não afetadas
    g.state = "robots"
    click_btn(lambda r: r.size == (260, 42))
    frame()
    ui.to_menu()
    g.new_match(1)
    assert g.mode == 1 and not g.career_match and g.match_sink is None and g.state == "kickoff"
    for _ in range(300):
        g.update(1 / 60)
        g.draw()
    assert g.score is not None and g.state in ("kickoff", "play", "goal")
    reset(career_save=None)
    g.state = "menu"


def test_round_shows_level_up_and_drop():
    gg = fresh(seed=2)
    start_league()
    rb = gg.robots[0]
    rb["xp"] = gm.xp_need(rb["level"]) - 1                           # sobe de nível com qualquer XP
    ui.cache = None
    frame()
    assert click_btn(lambda r: r.size == (440, 44))
    frame()
    info = ui.round_info
    row = next(r for r in info["rows"] if r[0] == rb["name"])
    assert row[5] and row[4] == row[3] + 1 and rb["level"] == 2
    # força drop: vitória garantida com RNG viciado
    class Always:
        def random(self):
            return 0.0

        def choice(self, seq):
            return seq[0]

        def getrandbits(self, n):
            return 1

        def randint(self, a, b):
            return a

        def sample(self, seq, k):
            return list(seq)[:k]

        def randrange(self, *a):
            return a[0]

        def shuffle(self, x):
            pass
    rew = gm.match_rewards(gg, 3, 0, [rb["id"]], 0, Always())
    assert rew["drop"] is not None
    ui.round_info["rew"] = rew
    shot("t14_round_nivel_up")
    for _ in range(60):
        frame()


# ------------------------------------------------- save ilegível / cliques no mesmo frame
def test_new_game_over_unreadable_bytes_needs_confirmation():
    """Save com bytes \\xff\\xfe injetados (via store real, em arquivo temporário): 'bad',
    .bad com o texto, NOVO JOGO exige confirmação e o original só some após confirmar."""
    p = os.path.join(SCRATCH, "robots_ff.json")
    old = (gm._store_get, gm._store_set, gm._store_set_bad, gm.SAVE_PATH)
    try:
        gm.SAVE_PATH = p
        gm._store_get = lambda: store.read(gm.SAVE_KEY, p)
        gm._store_set = lambda t: store.write(gm.SAVE_KEY, p, t)
        gm._store_set_bad = lambda t: store.write(gm.SAVE_KEY + ".bad", p + ".bad", t)
        good = gm.new_game(random.Random(1))
        assert good.save()
        raw = open(p, "rb").read()
        bad = raw[:100] + b"\xff\xfe" + raw[100:]
        open(p, "wb").write(bad)
        assert gm.Garage.load_status() == "bad"
        g.refresh_robots_status()
        g.state = "menu"
        key(pygame.K_5)
        frame()
        assert ui.status == "bad" and os.path.exists(p + ".bad")
        assert "\ufffd" in open(p + ".bad", encoding="utf-8").read()
        click_btn(lambda r: r.size == (300, 64) and r.y == 400)       # NOVO JOGO
        assert ui.confirm_new and ui.screen_id == "menu"
        assert open(p, "rb").read() == bad                             # original intacto
        frame()
        assert click_btn(lambda r: r.size == (400, 56))                # CONFIRMAR
        assert ui.screen_id == "hub" and open(p, "rb").read() != bad
        assert gm.Garage.load_status() == "ok"
    finally:
        gm._store_get, gm._store_set, gm._store_set_bad, gm.SAVE_PATH = old
        for f in (p, p + ".bad", p + ".tmp"):
            if os.path.exists(f):
                os.remove(f)
        ui.to_menu()


def test_new_game_read_error_is_bad_and_needs_confirmation():
    reset()
    MEM["save"] = store.ERROR                      # leitura lança -> sentinela
    assert gm.Garage.load_status() == "bad"
    ui.open()
    assert ui.status == "bad"
    ui.do_new()
    assert ui.confirm_new and ui.garage is None
    ui.do_new()
    assert ui.garage is not None and ui.screen_id == "hub"
    reset()
    assert gm.Garage.load_status() == "none"       # ausência continua "none"


def test_new_game_rechecks_status_before_writing():
    """Outra aba criou o save depois do menu aberto: NOVO JOGO não sobrescreve sozinho."""
    reset()
    ui.open()
    assert ui.status == "none"
    other = gm.new_game(random.Random(3))
    other.save()
    before = saved_text()
    ui.do_new()
    assert ui.confirm_new and ui.garage is None and saved_text() == before
    ui.do_new()
    assert ui.garage is not None
    ui.to_menu()


def test_double_click_same_frame_simulates_one_round():
    gg = fresh(seed=21)
    start_league()
    frame()
    sim = [r for r, fn, en in ui.buttons if en and r.size == (440, 44)][0]
    watch = [r for r, fn, en in ui.buttons if en and r.size == (440, 54)][0]
    assert gg.league["round"] == 0
    click(sim.center)
    click(sim.center)                              # sem draw entre os cliques
    assert gg.league["round"] == 1 and gg.stats["played"] == 1
    ui.go("hub")
    frame()
    sim = [r for r, fn, en in ui.buttons if en and r.size == (440, 44)][0]
    watch = [r for r, fn, en in ui.buttons if en and r.size == (440, 54)][0]
    click(sim.center)
    click(watch.center)                            # SIMULAR + ASSISTIR no mesmo frame
    assert gg.league["round"] == 2 and gg.stats["played"] == 2 and g.state == "robots"
    ui.to_menu()


def test_career_double_click_same_frame_no_duplicate():
    c = career.Career.new()
    cu = g.career_ui
    cu.career = c
    cu.screen_id = "pick"
    cu.reset_ui()
    cu.choose(0)
    g.state = "career"
    frame()
    sim = [r for r, fn, en in cu.buttons if en and r.size == (240, 70) and r.x == 300][0]
    r0 = c.round
    click(sim.center)
    click(sim.center)
    assert c.round == r0 + 1
    cu.screen_id = "hub"
    g.state = "menu"


# -------------------------------------------------------------------------- medição
def test_subclass_hooks_persist_tabs_and_round_split():
    gg = fresh(seed=5)

    class Sub(robots_ui.RobotsUI):
        def __init__(self, game):
            super().__init__(game)
            self.calls = 0
            self.tabs = [("hub", "HISTORIA"), ("garage", "GARAGEM"), ("shop", "LOJA")]
            self.hdr = self.body = 0

        def persist(self):
            self.calls += 1
            return True

        def draw_round_header(self, info):
            self.hdr += 1
            super().draw_round_header(info)

        def draw_round_body(self, info):
            self.body += 1
            super().draw_round_body(info)

    sub = Sub(g)
    assert sub.screens == robots_ui.SCREENS and sub.frame_screens == robots_ui.FRAME_SCREENS
    assert robots_ui.RobotsUI.__dict__.get("save") is None, "save() antigo não deve existir"
    sub.garage = gg
    real_set = gm._store_set

    def boom(t):
        raise AssertionError("garage.save() chamado direto fora de persist()")
    gm._store_set = boom
    try:
        sub.go("hub")
        sub.new_league()                                    # (a) liga
        assert sub.calls == 1
        sub.do_sim()                                        # rodada simulada
        assert sub.calls >= 2 and sub.screen_id == "round"
        n = sub.calls
        assert sub.act((True, "ok")) and sub.calls == n + 1  # bancada/loja/garagem passam por act()
        assert not sub.act((False, "no")) and sub.calls == n + 1
        sub.do_new()                                        # há save: 1º clique só pede confirmação
        assert sub.confirm_new and sub.calls == n + 1
        sub.do_new()
        assert sub.calls == n + 2
        sub.to_menu()
        assert sub.calls == n + 3
        # (b) abas customizadas no cabeçalho
        sub.garage = gg
        sub.go("hub")
        g.screen.fill((0, 0, 0))
        sub.draw_frame()
        labels = []
        real_btn = sub.btn
        sub.btn = lambda rect, label, *a, **k: (labels.append(label), real_btn(rect, label, *a, **k))[1]
        sub.draw_frame()
        sub.btn = real_btn
        assert labels[:3] == ["HISTORIA", "GARAGEM", "LOJA"], labels
        assert sub.tab_active("hub") and not sub.tab_active("shop")
        sub.frame_screens = ("shop",)
        sub.screen_id = "hub"
        sub.draw()                                          # hub fora de frame_screens: sem cabeçalho
        sub.frame_screens = robots_ui.FRAME_SCREENS
        # (c) draw_round chama header e body
        sub.go("hub")
        sub.new_league()
        sub.do_sim()
        sub.hdr = sub.body = 0
        sub.draw_round()
        assert sub.hdr == 1 and sub.body == 1
        sub.round_info = None
        sub.draw_round()
        assert sub.hdr == 1 and sub.body == 1, "sem info: nenhum dos dois"
    finally:
        gm._store_set = real_set
    ui.garage = None
    reset()


def test_draw_ms_budget():
    new_game_open()
    out = {}
    g.state = "menu"
    for _ in range(5):
        g.draw()
    t = time.perf_counter()
    for _ in range(200):
        g.draw()
    out["menu"] = (time.perf_counter() - t) / 200 * 1000
    for sid in ("hub", "garage", "bench", "shop", "shop_models", "shop_sell", "hub_league", "round", "league_end"):
        ui.open()
        ui.do_continue()
        if sid == "hub_league":
            RL.new_league(ui.garage, 0, random.Random(1))
            ui.go("hub")
        elif sid.startswith("shop"):
            ui.go("shop")
            ui.shop_tab = "models" if sid == "shop_models" else "parts"
            ui.shop_mode = "sell" if sid == "shop_sell" else "buy"
        elif sid == "round":
            RL.new_league(ui.garage, 0, random.Random(1))
            ui.pending = RL.next_fixture(ui.garage.league)
            ui.do_sim()
        elif sid == "league_end":
            lg = RL.new_league(ui.garage, 0, random.Random(1))
            for _ in range(RL.ROUNDS):
                RL.advance_round(lg, ui.garage, random.Random(2))
            ui.to_league_end()
        else:
            ui.go(sid)
        for _ in range(5):
            g.draw()
        t = time.perf_counter()
        for _ in range(200):
            g.draw()
        out[sid] = (time.perf_counter() - t) / 200 * 1000
    print("draw_ms:", {k: round(v, 2) for k, v in out.items()})
    for k, v in out.items():
        if v >= 3.0:
            print("AVISO: frame lento (informativo):", k, round(v, 2), "ms")
        assert v < 25.0, (k, v)
    ui.to_menu()


# =========================================================== Fase 4 / Onda B: B10 (HABILIDADES/bancada), B12
import skills as SK  # noqa: E402
import parts as PT  # noqa: E402

SK_TAB = [t for t, _ in robots_ui.TABS].index("skills")


def has_text(sub):
    return any(isinstance(k[0], str) and sub in k[0] for k in g.text_cache)


def mod_game(seed=21, scrap=5000, pts=0):
    """Garagem nova no hub com mod_on (tier 1 concluído), sucata e PH no 1º titular."""
    gg = fresh(seed, scrap)
    gg.flags[gm.MOD_FLAG] = 1
    rb = gg.robot(gg.lineup[0])
    rb["skills"]["pts"] = pts
    ui.cache = None
    return gg, rb


def counting_frames(n=60):
    """Conta Surfaces e chaves de texto em n quadros (depois de 5 de aquecimento)."""
    real = pygame.Surface
    count = [0]

    class Counting(real):
        def __init__(self, *a, **k):
            count[0] += 1
            super().__init__(*a, **k)

    for _ in range(5):
        frame()
    g.text_cache.clear()
    keys = set()
    pygame.Surface = Counting
    try:
        for _ in range(n):
            frame()
            keys.update(g.text_cache.keys())
    finally:
        pygame.Surface = real
    return count[0], keys


def info_btn():
    """Botão de ação do painel de detalhes (APRENDER/EQUIPAR/DESEQUIPAR)."""
    r = robots_ui.SK_INFO
    return pygame.Rect(r.x + 18, r.bottom - 48, r.w - 36, 38)


def test_skills_tab_locked_shows_how_to_unlock():
    gg = fresh(31)
    assert not gg.mod_on()
    gg.robots[0]["skills"]["pts"] = 2
    tab("skills")
    n, keys = counting_frames(60)
    assert n == 0 and len(keys) < 150, (n, len(keys))
    assert has_text("HABILIDADES BLOQUEADAS") and has_text("tier 1 da liga")
    assert not ui.sk_node_rects()["atq1"].collidelist([r for r, _f, _e in ui.buttons]) >= 0
    ok, msg = gg.learn_skill_node(gg.robots[0]["id"], "atq1")
    assert not ok and "bloqueadas" in msg
    assert not gg.buy_item("cafe")[0] and not gg.equip_skill(gg.robots[0]["id"], "arrancada")[0]
    shot("b10_habilidades_bloqueada")


def test_skills_tab_tree_learn_equip_tactic_and_save():
    gg, rb = mod_game(pts=20)
    rid = rb["id"]
    tab("skills")
    assert ui.screen_id == "skills" and ui.sk_robot()["id"] == rid
    n, keys = counting_frames(60)
    assert n == 0, "HABILIDADES criou %d Surface em 60 quadros" % n
    assert len(keys) < 150 and len(g.text_cache) <= soccer.TEXT_CACHE_MAX, len(keys)
    rects = ui.sk_node_rects()
    assert len(rects) == sum(len(b) for b in SK.TREE.values()) == 12
    assert all(robots_ui.SK_PANEL.contains(r) for r in rects.values())
    assert not any(a.colliderect(b) for i, a in enumerate(rects.values()) for b in list(rects.values())[i + 1:])
    # aprender o nó 1 do ramo de ataque: gasta PH e libera o seguinte
    first, second = SK.TREE["ATQ"][0], SK.TREE["ATQ"][1]
    assert SK.node_state(rb, second["id"]) == "locked"
    frame()
    click(rects[first["id"]].center)
    assert ui.sk_sel == ("node", first["id"])
    frame()
    btn = info_btn()
    click(btn.center)
    click(btn.center)                                   # 2º clique no mesmo quadro: ignorado
    assert rb["skills"]["pts"] == 20 - first["cost"], rb["skills"]["pts"]
    assert SK.node_state(rb, first["id"]) == "learned" and SK.node_state(rb, second["id"]) == "open"
    assert saved().robot(rid)["skills"]["learned"].get(first["skill"]) == first["rank"]
    g.text_cache.clear()
    frame()
    assert has_text("EQUIPAR") and has_text("APRENDIDA")         # nó aprendido: o botão vira EQUIPAR
    # aprende mais (sem clique) e equipa pelos chips/botão
    for nid in ("atq2", "ctr1", "ctr2", "def1"):
        assert gg.learn_skill_node(rid, nid)[0], nid
    ui.cache = None
    want = ["arrancada", "curva", "leitura"]               # carga 2+2+1 = 5 <= 6, 3 vagas
    for sid in want:
        ui.sk_pick("skill", sid)
        frame()
        click(info_btn().center)
        frame()
        assert sid in rb["skills"]["equipped"], (sid, ui.msg)
    assert SK.equipped_load(rb) <= SK.LOAD_MAX and len(rb["skills"]["equipped"]) == SK.MAX_EQUIPPED
    ui.sk_pick("skill", "poupanca")
    frame()
    click(info_btn().center)
    assert "poupanca" not in rb["skills"]["equipped"] and "Máximo" in ui.msg, ui.msg
    assert saved().robot(rid)["skills"]["equipped"] == want
    # módulo ocupa 1 vaga: com 3 equipadas, a 3ª fica fora da partida e equipar outra é recusado
    mod = gg.new_piece("Módulo Recarga", 0)
    gg.inventory.append(mod)
    assert gg.equip(rid, mod["id"])[0]
    ui.cache = None
    eff = [e[0] for e in SK.effective_skills(rb, gg.pieces_by_id(), True)]
    assert "recarga" in eff and len([e for e in eff if e in SK.SKILLS]) == SK.MAX_EQUIPPED
    frame()
    assert has_text("Fora da partida")
    gg.unequip_skill(rid, "leitura")
    ok, msg = gg.equip_skill(rid, "leitura")
    assert not ok and "módulo" in msg and "leitura" not in rb["skills"]["equipped"]
    # desequipar pelo botão
    ui.sk_pick("skill", "curva")
    frame()
    click(info_btn().center)
    assert "curva" not in rb["skills"]["equipped"]
    # tática: DEFENSIVO grava e vai para o match_cfg
    frame()
    tac = [r for r, _f, en in ui.buttons if en and robots_ui.SK_TAC.contains(r)]
    assert len(tac) == len(SK.TACTICS)
    click(tac[SK.TACTICS.index("defensivo")].center)
    assert gg.tactic == "defensivo" and saved().tactic == "defensivo"
    assert gg.match_cfg()["tactic"] == "defensivo"
    # outro robô pelos chips
    other = ui.sk_robots()[1]
    frame()
    click(pygame.Rect(20 + 1 * 106, 130, 100, 34).center)
    assert ui.sk_rid == other["id"] and ui.sk_sel is None
    ui.sk_rid = rid
    ui.sk_pick("node", "atq3")
    n, keys = counting_frames(30)
    assert n == 0 and len(keys) < 150
    shot("b10_habilidades")
    # Esc volta ao menu salvando (como as outras abas)
    key(pygame.K_ESCAPE)
    assert g.state == "menu"


def test_bench_8_slots_set_relic_details_tooltip_and_force_line():
    gg, rb = mod_game(seed=23, scrap=3000)
    rid = rb["id"]
    for m, r in (("Borracha", 1), ("Escova de Sucção", 1), ("Servo Ágil", 2)):
        p = free_part(gg, m, r)
        rb["slots"][PT.part_slot(p)] = None
        assert gg.equip(rid, p["id"])[0]
    relic = free_part(gg, "Rodinha Esquerda do Zé", 3)
    mod = free_part(gg, "Módulo Arrancada", 2)
    assert gg.equip(rid, mod["id"])[0]
    ui.cache = None
    ui.sel = rid
    ui.go("garage")
    ui.open_bench()
    rects = robots_ui.bench_slot_rects(True)
    assert len(rects) == 8 and rects[-1][1].bottom < 548
    frame()
    assert has_text("Faxineiro 3/4") and has_text("Arrancada")      # resumo de sets + tag do módulo
    # slot MOTOR (Servo Ágil, set Faxineiro) sem peça livre selecionada: painel de detalhes
    click(dict(rects)["motor"].center)
    frame()
    assert ui.sel_slot == "motor" and ui.sel_piece is None
    assert has_text("Set Faxineiro 3/4 neste robô") and has_text("com 4:")
    n, keys = counting_frames(30)
    assert n == 0 and len(keys) < 200, (n, len(keys))
    # relíquia livre: ANTES/DEPOIS com FORÇA e TIME (o set quebra: Força das skills cai)
    click(piece_rect(0).center)
    frame()
    assert ui.sel_piece == relic["id"]
    d = ui.compare_data(rb, gg.pieces_by_id())
    f0, f1, dsk = d["force"]
    assert d["starter"] and abs(f0 - ui.robot_force(rb, gg.pieces_by_id())[0]) < 1e-9
    assert has_text("FORÇA") and has_text("TIME") and has_text("DEPOIS")
    assert ui.compare_data(rb, gg.pieces_by_id()) is d                     # cache por seleção
    # tooltip: mouse sobre a relíquia (lista de peças livres) mostra RELÍQUIA e a passiva
    real_pos = pygame.mouse.get_pos
    pygame.mouse.get_pos = lambda: piece_rect(0).center
    try:
        frame()
        assert has_text("RELÍQUIA: peça única") and has_text("Rolando Sozinha")
        n, keys = counting_frames(30)
        assert n == 0, n
        shot("b10_bancada_8slots_reliquia")
        pygame.mouse.get_pos = lambda: dict(rects)["modulo"].center
        frame()
        assert has_text("Habilidade: Arrancada r2")
        shot("b10_bancada_tooltip_modulo")
    finally:
        pygame.mouse.get_pos = real_pos
    # relíquia não se vende: VENDER desabilitado com ela selecionada
    frame()
    assert not any(en for r, _f, en in ui.buttons if r.x == 165 and r.y == 598)
    gg.flags.pop(gm.MOD_FLAG)
    ui.cache = None
    frame()
    assert len(robots_ui.bench_slot_rects(False)) == 7


def test_shop_items_buy_and_limits():
    gg, _rb = mod_game(seed=25, scrap=1000)
    tab("shop")
    assert click_btn(lambda r: r.x == 260 and r.y == 132)            # ITENS
    frame()
    assert ui.shop_tab == "items"
    n, keys = counting_frames(60)
    assert n == 0 and len(keys) < 150, (n, len(keys))
    iid = "cera_turbo"
    k = list(SK.ITEMS).index(iid)
    frame()
    click(pygame.Rect(20, 206 + k * 46, 1060, 42).center)
    assert ui.item_sel == iid
    sc = gg.scrap
    frame()
    btn = pygame.Rect(860, 650, 220, 44)
    click(btn.center)
    click(btn.center)                                                # mesmo quadro: 1 compra só
    assert gg.items.get(iid) == 1 and gg.scrap == sc - SK.ITEMS[iid]["price"]
    assert saved().items.get(iid) == 1 and saved().scrap == gg.scrap
    gg.items[iid] = SK.ITEM_MAX
    ok, msg = gg.buy_item(iid)
    assert not ok and "cheio" in msg
    gg.scrap = 0
    assert not gg.buy_item("cafe")[0]
    assert not gg.buy_item("nao_existe")[0]
    gg.scrap = 1000
    gg.items[iid] = 2
    frame()
    shot("b12_loja_itens")
    # sem mod_on: aviso e COMPRAR desabilitado
    gg.flags.pop(gm.MOD_FLAG)
    ui.cache = None
    frame()
    assert has_text("Itens bloqueados")
    assert not any(en for r, _f, en in ui.buttons if r == btn)


def test_backpack_league_pick_consume_and_result():
    gg, _rb = mod_game(seed=27, scrap=1000)
    gg.items = {"cera_turbo": 2, "cafe": 1}
    start_league()
    zero_surface_frames(30)                                          # hub com o painel da Mochila
    assert has_text("MOCHILA")
    assert click_btn(lambda r: r.size == (218, 40) and r.x == 846)  # ESCOLHER ITENS
    frame()
    assert ui.bp_open
    m = robots_ui.BP_MODAL
    rows = {iid: pygame.Rect(m.x + 20, m.y + 134 + k * 44, m.w - 40, 40) for k, iid in enumerate(SK.ITEMS)}
    click(rows["cera_turbo"].center)
    frame()
    click(rows["cafe"].center)
    frame()
    click(rows["spray"].center)                                      # sem estoque: botão desabilitado
    frame()
    assert gg.backpack_items() == ["cera_turbo", "cafe"]
    assert abs(gg.match_F() - gg.rating() - SK.item_force(["cera_turbo", "cafe"])) < 1e-9
    n, keys = counting_frames(60)
    assert n == 0 and len(keys) < 150, (n, len(keys))
    shot("b12_mochila")
    # modal: os botões da tela de trás não respondem; Esc só fecha a Mochila
    assert not any(r.size == (440, 44) for r, _f, _e in ui.buttons)  # SIMULAR escondido
    key(pygame.K_ESCAPE)
    assert not ui.bp_open and ui.screen_id == "hub" and g.state == "robots"
    frame()
    assert ui.user_strength() > ui.info()["rating"]
    # SIMULAR: gasta a Mochila e mostra no resultado
    assert click_btn(lambda r: r.size == (440, 44))
    frame()
    assert ui.screen_id == "round"
    assert ui.round_info["items"] == [SK.ITEMS["cera_turbo"]["name"], SK.ITEMS["cafe"]["name"]]
    assert gg.items == {"cera_turbo": 1} and gg.backpack_items() == []
    assert saved().items == {"cera_turbo": 1}
    frame()
    assert has_text("Mochila usada")
    shot("b12_resultado_mochila")
    assert click_btn(lambda r: r.size == (260, 42))
    frame()
    # ASSISTIR: a config da partida leva os itens e eles são gastos no fim (callback do Game)
    gg.set_backpack(["cera_turbo"])
    ui.cache = None
    assert click_btn(lambda r: r.size == (440, 54))                  # ASSISTIR
    assert g.state in ("kickoff", "play")
    ui.match_done([1, 0], [])
    g.state = "robots"
    assert ui.screen_id == "round" and ui.round_info["items"] == [SK.ITEMS["cera_turbo"]["name"]]
    assert "cera_turbo" not in gg.items
    ui.match_done([1, 0], [])                                        # callback repetido: nada
    assert ui.screen_id == "hub"
    ui.to_menu()


# ------------------------------------------------------------------ B13: cosméticos
class FakeClock:
    """Relógio de soccer.time que avança 1/60 s por quadro (rastro determinístico no screenshot)."""

    def __init__(self, t=900.0):
        self.t = t

    def perf_counter(self):
        return self.t


def cos_card(row, k):
    cw, ch = robots_ui.COS_CARD
    return pygame.Rect(20 + k * (cw + 8), robots_ui.COS_ROW0 + row * robots_ui.COS_ROW_PITCH + 20, cw, ch)


def vis_card(row, k):
    """Cartão da galeria VISUAL: k = 0 é "nenhum", k >= 1 é o (k-1)-ésimo do catálogo do tipo."""
    m = robots_ui.VIS_MODAL
    cw, ch = robots_ui.VIS_CARD
    return pygame.Rect(m.x + 230 + k * (cw + 6), m.y + 72 + row * 106 + 20, cw, ch)


def test_cosmetics_shop_gallery_and_match():
    import parts as PP
    gg = fresh(31, scrap=1000)
    tab("shop")
    assert click_btn(lambda r: r.x == 380 and r.y == 132)            # COSMÉTICOS
    frame()
    assert ui.shop_tab == "cosmetics"
    n, keys = counting_frames(60)
    assert n == 0 and len(keys) < 150, (n, len(keys))
    order = robots_ui.LOOK_ORDER
    assert order == ("decal", "antenna", "trail", "celebration")
    # cartões não se sobrepõem e cabem acima do botão COMPRAR
    rects = [cos_card(r, k) for r, kd in enumerate(order) for k in range(len(PP.LOOK_KINDS[kd]))]
    assert all(r.right <= 1080 and r.bottom <= 636 for r in rects)
    assert not any(a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1:])
    frame()
    click(cos_card(0, PP.DECALS.index("raio")).center)
    assert ui.cos_sel == "raio"
    frame()
    btn = pygame.Rect(860, 650, 220, 44)
    click(btn.center)
    click(btn.center)                                                # mesmo quadro: 1 compra só
    price = PP.COSMETIC_PRICE["decal"]
    assert gg.cosmetics == ["raio"] and gg.scrap == 1000 - price
    assert saved().cosmetics == ["raio"] and saved().scrap == gg.scrap
    frame()
    click(cos_card(0, PP.DECALS.index("raio")).center)
    frame()
    assert not any(en for r, _f, en in ui.buttons if r == btn)       # já tem: COMPRAR desabilitado
    for row, cid in ((2, "fogo"), (1, "mola"), (3, "fogos")):
        frame()
        click(cos_card(row, PP.LOOK_KINDS[order[row]].index(cid)).center)
        frame()
        click(btn.center)
    assert gg.cosmetics == ["raio", "fogo", "mola", "fogos"]
    frame()
    assert has_text("TENHO")
    shot("b13_loja_cosmeticos")
    # bancada -> galeria VISUAL (modal)
    tab("garage")
    assert click_btn(lambda r: r.size == (295, 44) and r.y == 562)  # ABRIR BANCADA
    frame()
    assert ui.screen_id == "bench"
    rb = gg.robot(ui.bench_rid)
    assert click_btn(lambda r: r == robots_ui.VIS_BTN)
    frame()
    assert ui.vis_open
    assert not any(r.size == (185, 36) for r, _f, _e in ui.buttons)  # VOLTAR escondido pelo modal
    m = robots_ui.VIS_MODAL
    cards = [vis_card(r, k) for r, kd in enumerate(order) for k in range(len(PP.LOOK_KINDS[kd]) + 1)]
    assert all(m.contains(r) for r in cards)
    assert not any(a.colliderect(b) for i, a in enumerate(cards) for b in cards[i + 1:])
    ok_btn = pygame.Rect(m.right - 176, m.bottom - 56, 150, 40)
    assert not any(c.colliderect(ok_btn) for c in cards)
    for row, cid in ((0, "raio"), (1, "mola"), (2, "fogo"), (3, "fogos")):
        frame()
        click(vis_card(row, PP.LOOK_KINDS[order[row]].index(cid) + 1).center)
    assert rb["look"] == {"decal": "raio", "antenna": "mola", "trail": "fogo", "celebration": "fogos"}
    assert saved().robot(rb["id"])["look"] == rb["look"]
    frame()
    click(vis_card(0, PP.DECALS.index("estrela") + 1).center)        # bloqueado: nada
    frame()
    assert rb["look"]["decal"] == "raio"
    n, keys = counting_frames(60)
    assert n == 0 and len(keys) < 150, (n, len(keys))
    shot("b13_galeria_visual")
    click(vis_card(2, 0).center)                                     # "nenhum" no rastro
    frame()
    assert "trail" not in rb["look"] and saved().robot(rb["id"])["look"].get("trail") is None
    click(vis_card(2, PP.TRAILS.index("fogo") + 1).center)
    frame()
    assert rb["look"]["trail"] == "fogo"
    click(pygame.Rect(m.x + 26 + 90, m.y + 82 + 170 + 62, 80, 34).center)   # PROX: troca o robô no modal
    frame()
    assert ui.vis_open and ui.bench_rid != rb["id"]
    rb2 = gg.robot(ui.bench_rid)
    click(vis_card(0, PP.DECALS.index("raio") + 1).center)
    frame()
    assert rb2["look"] == {"decal": "raio"}
    key(pygame.K_ESCAPE)                                             # Esc só fecha o modal
    assert not ui.vis_open and ui.screen_id == "bench" and g.state == "robots"
    frame()
    shot("b13_bancada_visual")
    # partida com os cosméticos (todos os titulares) - screenshot com rastro
    for cid in sorted(PP.COSMETICS):
        gg.grant_cosmetic(cid)
    for i, rid in enumerate(gg.lineup):
        for kd in order:
            ids = PP.LOOK_KINDS[kd]
            gg.equip_look(rid, ids[i % len(ids)])
    opp = gm.new_game(random.Random(77))
    old = soccer.time
    clock = soccer.time = FakeClock()
    try:
        random.seed(5)
        g.start_robot_match(gg.match_cfg(), opp.match_cfg(), lambda s, e: None, venue="bairro")
        g.state = "play"
        assert len(g.trail_players) == 5
        for _ in range(150):
            clock.t += 1 / 60
            g.step(1 / 60)
            g.draw()
        assert any(p.trail_n for p in g.trail_players)
        if SHOTS_DIR:
            os.makedirs(SHOTS_DIR, exist_ok=True)
            pygame.image.save(g.screen, "%s/%s.png" % (SHOTS_DIR, "b13_partida"))
            g.crowd = None                                           # sem torcida/câmera: campo 1:1
            for _ in range(20):
                clock.t += 1 / 60
                g.step(1 / 60)
                g.draw()
            pygame.image.save(g.screen, "%s/%s.png" % (SHOTS_DIR, "b13_partida_perto"))
    finally:
        soccer.time = old
        g.match_sink = None
        g.crowd = None
    g.state = "robots"
    ui.to_menu()


# --- formacao do time (seletor na LIGA do Modo Robos e no INICIO da carreira; saves) --------------
def _form_btns(cu, rect):
    r0 = pygame.Rect(rect)
    return [b for b in cu.buttons if r0.contains(b[0])]


def test_formation_selector_robots_hub_and_save():
    import formations
    gg = fresh(seed=41)
    start_league()
    frame()
    assert gg.formation == "equilibrada" and "formation" not in gg.match_cfg()
    btns = _form_btns(ui, (40, 270, 440, 40))
    assert len(btns) == 3                                            # corpo + setas < >
    assert any("EQUILIBRADA" in k[0] for k in g.text_cache)
    zero_surface_frames(30)
    click(btns[0][0].center)                                         # corpo: proxima
    assert gg.formation == "retranca" and saved().formation == "retranca"
    key(pygame.K_LEFT)
    assert gg.formation == "equilibrada" and saved().formation == "equilibrada"
    key(pygame.K_f)
    key(pygame.K_f)
    assert gg.formation == "ofensiva" and gg.match_cfg()["formation"] == "ofensiva"
    frame()
    zero_surface_frames(30)
    shot("formacao_robos")
    # SIMULAR/ASSISTIR continuam nos mesmos tamanhos; ASSISTIR leva a formacao ao motor (so o lado do usuario)
    assert click_btn(lambda r: r.size == (440, 54))
    uside = 0 if g.teams[0].name == gg.team["name"] else 1
    t = g.teams[uside]
    assert [(p.fx, p.fy) for p in t.players] == list(formations.FORMATIONS["ofensiva"]["pts"])
    assert t.push == formations.FORMATIONS["ofensiva"]["push"] and g.teams[1 - uside].push == 0.0
    g.match_sink = None
    g.career_match = False
    g.crowd = None
    g.state = "robots"
    ui.go("hub")
    # teclas da formacao nao agem fora da LIGA
    ui.go("garage")
    key(pygame.K_RIGHT)
    assert gg.formation == "ofensiva"
    ui.to_menu()


def test_formation_garage_save_migration_and_sanitize():
    import json
    gg = fresh(seed=42)
    d = json.loads(MEM["save"])
    assert d["v"] == gm.VERSION == 2 and d["formation"] == "equilibrada"
    d.pop("formation")                                               # save v2 antigo, sem o campo
    assert gm.Garage.from_dict(d).formation == "equilibrada"
    d["formation"] = 7
    assert gm.Garage.sanitize(d)["formation"] == "equilibrada"
    d["formation"] = "pressao"
    assert gm.Garage.from_dict(d).formation == "pressao"
    assert gg.set_formation("nada")[0] is False and gg.formation == "equilibrada"
    # SIMULAR fiel ao motor: a padrao nao mexe na Forca; as outras somam formations.sim_df(rating)
    import formations
    r = gg.rating()
    base = gg.match_F()
    assert abs(base - r) < 1e-9                                       # Mochila vazia: match_F = rating
    for fid in formations.ORDER:
        gg.formation = fid
        assert abs(gg.match_F() - base - formations.sim_df(fid, r)) < 1e-9
    gg.formation = "equilibrada"
    assert gg.match_F() == base and formations.sim_df("equilibrada", 90) == 0.0
    assert formations.sim_df("retranca", 90) < formations.sim_df("retranca", 45)
    ui.to_menu()


def test_formation_selector_career_home_and_save():
    import json
    reset()
    c = career.Career.new()
    cu = g.career_ui
    cu.career = c
    cu.screen_id = "pick"
    cu.reset_ui()
    cu.choose(0)
    g.state = "career"
    frame()
    assert c.formation == "equilibrada"
    assert all("formation" not in c.match_cfg(i) for i in range(len(c.clubs)))
    btns = _form_btns(cu, (40, 382, 500, 50))
    assert len(btns) == 3
    zero_surface_frames(30)
    click(btns[2][0].center)                                         # seta >
    assert c.formation == "retranca" and json.loads(CAREER["save"])["formation"] == "retranca"
    key(pygame.K_RIGHT)
    assert c.formation == "ofensiva"
    assert c.match_cfg(c.user)["formation"] == "ofensiva"
    assert all("formation" not in c.match_cfg(i) for i in range(len(c.clubs)) if i != c.user)
    frame()
    assert any("OFENSIVA" in k[0] for k in g.text_cache)
    zero_surface_frames(30)
    shot("formacao_carreira")
    # saves antigos (sem o campo) e invalidos carregam com a padrao
    d = json.loads(CAREER["save"])
    d.pop("formation")
    CAREER["save"] = json.dumps(d)
    assert career.Career.load().formation == "equilibrada"
    d["formation"] = ["x"]
    CAREER["save"] = json.dumps(d)
    assert career.Career.load().formation == "equilibrada"
    # SIMULAR da carreira: a formacao entra nas forcas do clube do usuario (formations.sim_df)
    import formations
    real_p = career.poisson
    career.poisson = lambda lam: lam                                 # lambdas do Poisson, sem sorteio
    try:
        h, a = c.user_fixture()
        c.formation = "equilibrada"
        base = c.sim_match(h, a)
        c.formation = "retranca"
        df = formations.sim_df("retranca", c.rating(c.clubs[c.user]))
        got = c.sim_match(h, a)
        assert df < 0 and got != base
        mine = 0 if h == c.user else 1
        assert got[mine] < base[mine] and got[1 - mine] > base[1 - mine]
    finally:
        career.poisson = real_p
    # ASSISTIR: o motor recebe a formacao do clube do usuario
    c.formation = "quadrado"
    frame()
    assert click_btn_career(cu, lambda r: r.size == (240, 70) and r.x == 40)
    us = [t for t in g.teams if t.name == c.clubs[c.user]["name"]][0]
    assert (us.players[1].fx, us.players[1].fy) == formations_pts("quadrado")[1] and us.push > 0.0
    g.career_match = False
    g.crowd = None
    g.state = "menu"


def click_btn_career(cu, pred):
    frame()
    for r, fn, en in cu.buttons:
        if en and pred(r):
            click(r.center)
            return True
    return False


def formations_pts(fid):
    import formations
    return formations.FORMATIONS[fid]["pts"]


if __name__ == "__main__":
    names = sys.argv[1:]
    tests = [(k, v) for k, v in sorted(globals().items(), key=lambda kv: kv[1].__code__.co_firstlineno
                                       if callable(kv[1]) and hasattr(kv[1], "__code__") else 0)
             if k.startswith("test_") and (not names or k in names)]
    for k, t in tests:
        t()
        print("ok", k)
    print(len(tests), "testes passaram")
    shutil.rmtree(SCRATCH, ignore_errors=True)
