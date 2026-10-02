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
    for sl in robots_ui.P.SLOTS:
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
    click_btn(lambda r: r.x == 400 and r.y == 132)                   # VENDER (modo)
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
