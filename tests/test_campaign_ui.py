"""Testes da UI da Campanha (passos 8 a 10: botao 6, menu, mapa, dialogo, torneio, partida, fim de capitulo, fim). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_campaign_ui.py

NUNCA toca ~/.soccerpy_*.json: stores de campaign/garage/career vao para dicts em memoria, trocados
ANTES de criar o Game. garage._store_set e career._store_set sao sentinelas que FALHAM se chamadas.
"""
import json
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

import campaign as cm  # noqa: E402
import career  # noqa: E402
import garage as gm  # noqa: E402
import parts  # noqa: E402

CAMP = {}         # campanha: {"save": str, "bad": str}
CAREER = {}       # career: {"save": str}
FORBIDDEN = []


def _forbid(name):
    def f(*a, **k):
        FORBIDDEN.append(name)
        raise AssertionError("%s chamada pela campanha" % name)
    return f


cm._store_get = lambda: CAMP.get("save")
cm._store_set = lambda t: CAMP.__setitem__("save", t) or True
cm._store_set_bad = lambda t: CAMP.__setitem__("bad", t) or True
gm._store_get = lambda: None                       # o modo robos nunca tem save aqui
gm._store_set = _forbid("garage._store_set")
gm._store_set_bad = _forbid("garage._store_set_bad")
career._store_get = lambda: CAREER.get("save")
career._store_set = _forbid("career._store_set")

import soccer  # noqa: E402
import story  # noqa: E402
import campaign_ui as cui  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
g = soccer.Game(screen)
ui = g.campaign_ui
SCRATCH = tempfile.mkdtemp(prefix="soccerpy_campui_test_")
SHOTS_DIR = os.environ.get("SOCCERPY_SHOTS_DIR")          # screenshots so se definido


def reset(save=None, career_save=None):
    CAMP.clear()
    CAREER.clear()
    del FORBIDDEN[:]
    if save is not None:
        CAMP["save"] = save
    if career_save is not None:
        CAREER["save"] = career_save
    g.has_save = career.Career.has_save()
    g.refresh_campaign_status()
    g.state = "menu"
    ui.campaign = None


def click(pos):
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def key(k):
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, unicode=""))


def frame():
    g.update(1 / 60)
    g.draw()


def click_label_rect(pred):
    """Clica no primeiro botao habilitado cujo rect satisfaz pred (redesenha antes)."""
    frame()
    for r, fn, enabled in ui.buttons:
        if enabled and pred(r):
            click(r.center)
            return True
    return False


def click_tab(i):
    click((20 + i * 160 + 5, 87))


def shot(name):
    if SHOTS_DIR:
        os.makedirs(SHOTS_DIR, exist_ok=True)
        frame()
        pygame.image.save(g.screen, "%s/%s.png" % (SHOTS_DIR, name))


def new_campaign_open():
    reset()
    key(pygame.K_6)
    frame()
    assert g.state == "campaign" and ui.screen_id == "menu"
    assert click_label_rect(lambda r: r.size == (300, 64) and r.y == 400)       # NOVA CAMPANHA
    frame()
    assert ui.screen_id == "map" and ui.campaign is not None


def force_to(camp, target_ch):
    """Joga a campanha (API pura) ate o capitulo target_ch (vitorias forcadas)."""
    for _ in range(400):
        if camp.ch == target_ch:
            return
        a = camp.next_action()
        if a["kind"] == "scene":
            camp.finish_scene(a["id"])
        elif a["kind"] == "match":
            camp.record_match(4, 0)
        elif a["kind"] == "chapter_end":
            camp.advance_chapter()
        else:
            return
    raise AssertionError("force_to nao convergiu")


# ------------------------------------------------------------------ menu principal
def test_main_menu_button_6_and_keys():
    reset()
    r = g.campaign_btn()
    assert r == pygame.Rect(soccer.W // 2 - 330, 535, 660, 70)
    assert r.top >= g.robots_btn().bottom + 10 and r.bottom <= 640 - 14
    key(pygame.K_6)
    assert g.state == "campaign" and ui.screen_id == "menu"
    ui.to_menu()
    assert g.state == "menu"
    click(r.center)
    assert g.state == "campaign"
    key(pygame.K_ESCAPE)                                  # menu da campanha -> principal
    assert g.state == "menu"
    key(pygame.K_5)
    assert g.state == "robots"
    g.robots_ui.to_menu()
    assert g.state == "menu"
    key(pygame.K_1)
    assert g.state == "playing" or g.state != "menu"
    g.new_match(1)
    g.state = "menu"


def test_main_menu_button_5_layout_unchanged():
    reset()
    assert g.robots_btn() == pygame.Rect(soccer.W // 2 - 160, 450, 320, 70)
    reset(career_save='{"user": 1}')
    assert g.has_save
    assert g.continue_btn == pygame.Rect(soccer.W // 2 - 330, 450, 320, 70)
    assert g.robots_btn() == pygame.Rect(soccer.W // 2 + 10, 450, 320, 70)
    assert g.menu_btns[0] == pygame.Rect(50, 330, 320, 90)
    for _ in range(3):
        frame()
    assert ("clique ou aperte 1 / 2 / 3 / 4 / 5 / 6", 28, (200, 225, 235)) in g.text_cache
    reset()
    frame()
    assert ("clique ou aperte 1 / 2 / 3 / 5 / 6", 28, (200, 225, 235)) in g.text_cache


def test_menu_subtitle_follows_status():
    reset()
    frame()
    assert ("a história de Téo e do Zé Poeira", 22, (225, 210, 250)) in g.text_cache
    new_campaign_open()
    ui.to_menu()
    assert g.campaign_status == "ok" and g.state == "menu"
    g.text_cache.clear()
    frame()
    assert ("continuar", 22, (225, 210, 250)) in g.text_cache


def test_campaign_status_not_read_per_frame():
    reset()
    calls = [0]
    real = cm.Campaign.load_status

    def counting():
        calls[0] += 1
        return real()
    cm.Campaign.load_status = staticmethod(counting)
    try:
        for _ in range(30):
            frame()
    finally:
        cm.Campaign.load_status = staticmethod(real)
    assert calls[0] == 0


# ------------------------------------------------------------------ menu da campanha
def test_campaign_menu_states():
    reset()
    ui.open()
    assert ui.status == "none"
    frame()
    shot("campaign_menu_none")
    ui.to_menu()
    reset(save="{")
    ui.open()
    assert ui.status == "bad" and CAMP.get("bad") == "{"          # .bad guardado ao abrir
    frame()
    assert ("Save incompatível", 40, (240, 100, 90)) in g.text_cache
    shot("campaign_menu_bad")
    ui.to_menu()
    reset(save=cm.new_campaign(__import__("random").Random(1)).to_json())
    ui.open()
    assert ui.status == "ok"
    frame()
    assert ("Save encontrado", 36, (110, 230, 120)) in g.text_cache
    shot("campaign_menu_ok")
    ui.to_menu()
    reset(save='{"v": 99, "garage": {}}')                          # versao incompativel
    ui.open()
    assert ui.status == "bad"
    ui.to_menu()


def test_new_campaign_creates_and_writes_only_campaign_key():
    new_campaign_open()
    assert isinstance(ui.campaign, cm.Campaign)
    assert CAMP.get("save"), "nao gravou a campanha"
    assert ui.garage is ui.campaign.garage
    assert cm.Campaign.load_status() == "ok" and g.campaign_status == "ok"
    assert not FORBIDDEN
    assert ui.screen_id == "map"
    ui.to_menu()


def test_new_over_existing_requires_confirmation_and_reevaluates():
    reset()
    ui.open()
    assert ui.status == "none"
    CAMP["save"] = cm.new_campaign(__import__("random").Random(7)).to_json()   # "outra aba" criou
    old = CAMP["save"]
    ui.do_new()                                   # status reavaliado: exige confirmacao
    assert ui.confirm_new and ui.screen_id == "menu" and CAMP["save"] == old
    frame()
    assert ui.confirm_new
    ui.do_cancel_confirm()
    assert not ui.confirm_new and CAMP["save"] == old
    ui.do_new()
    assert ui.confirm_new and CAMP["save"] == old
    assert click_label_rect(lambda r: r.size == (400, 56))         # CONFIRMAR: APAGAR O SAVE
    assert ui.screen_id == "map" and CAMP["save"] != old
    assert cm.Campaign.load_status() == "ok"
    assert not FORBIDDEN
    ui.to_menu()


def test_bad_save_needs_confirmation_and_keeps_bad_copy():
    reset(save="\x00lixo{[")
    ui.open()
    assert ui.status == "bad"
    CAMP.pop("bad", None)                         # forca: garantir a copia no momento de sobrescrever
    ui.do_new()
    assert ui.confirm_new and CAMP["save"] == "\x00lixo{["
    ui.do_new()                                   # confirmado
    assert CAMP.get("bad") == "\x00lixo{["
    assert CAMP["save"] != "\x00lixo{[" and cm.Campaign.load_status() == "ok"
    assert ui.screen_id == "map"
    ui.to_menu()


def test_unreadable_store_is_bad_with_confirmation():
    reset()
    real = cm._store_get
    import store
    cm._store_get = lambda: store.ERROR
    try:
        ui.open()
        assert ui.status == "bad"
        ui.do_new()
        assert ui.confirm_new
    finally:
        cm._store_get = real
    ui.to_menu()


def test_continue_loads_and_shows_repair_warning():
    reset()
    c = cm.new_campaign(__import__("random").Random(3))
    force_to(c, "1")
    c.finish_scene("c1_intro")
    c.next_action()
    c.tour["stage"] = "G2"                        # tour coerente
    text = c.to_json()
    import json
    data = json.loads(text)
    data["c"]["done"].append("cena_que_nao_existe")   # inconsistencia -> sanitize
    reset(save=json.dumps(data))
    ui.open()
    frame()
    if ui.status == "ok":
        ui.do_continue()
        assert ui.screen_id == "map"
        frame()
        if ui.campaign.repaired:
            assert ui.notices
            shot("map_repaired")
    ui.to_menu()
    # reparo por rewind garantido: tour com estagio invalido
    reset()
    c = cm.new_campaign(__import__("random").Random(4))
    force_to(c, "1")
    c.next_action()
    data = json.loads(c.to_json())
    data["c"]["tour"] = {"id": "t_c1", "attempt": 0, "seed": 5, "stage": "XX", "results": [], "loses": 0}
    reset(save=json.dumps(data))
    ui.open()
    assert ui.status == "ok"
    ui.do_continue()
    assert ui.campaign is not None and ui.campaign.repaired and ui.notices
    frame()
    assert click_label_rect(lambda r: r.size == (120, 34))         # OK limpa o aviso
    assert not ui.notices
    ui.to_menu()


# ------------------------------------------------------------------ mapa
def test_map_start_mid_and_draft():
    new_campaign_open()
    frame()
    shot("map_start")
    assert ui.chapter_state(story.CHAPTERS[0]) == "current"
    assert ui.chapter_state(story.CHAPTERS[1]) == "future"
    force_to(ui.campaign, "1")
    ui.go("map")
    frame()
    assert ui.chapter_state(story.CHAPTERS[0]) == "done"
    assert ui.chapter_state(story.CHAPTERS[1]) == "current"
    shot("map_cap1")
    force_to(ui.campaign, "2")
    ui.go("map")
    frame()
    assert ui.chapter_state(story.CHAPTERS[1]) == "done"
    assert ui.chapter_state(story.CHAPTERS[2]) == "current" and story.CHAPTERS[2].get("draft")
    assert ui.map_act["kind"] == "end" and ui.map_act["draft"]
    assert ("em breve", 18, (255, 214, 90)) in g.text_cache
    shot("map_cap1_done")
    ui.to_menu()


def test_map_pulse_uses_counter_and_is_deterministic():
    new_campaign_open()
    p0 = ui.pulse
    for _ in range(10):
        frame()
    assert ui.pulse != p0 and 0 <= ui.pulse < 2.0
    ui.to_menu()


def test_escape_flow():
    new_campaign_open()
    key(pygame.K_ESCAPE)                          # mapa -> salva e vai ao menu principal
    assert g.state == "menu" and ui.campaign is None
    assert cm.Campaign.load_status() == "ok"
    key(pygame.K_6)
    ui.do_continue()
    ui.go("garage")
    key(pygame.K_ESCAPE)                          # garagem -> mapa
    assert ui.screen_id == "map"
    ui.do_story()
    assert ui.screen_id == "dialog"
    key(pygame.K_ESCAPE)                          # dialogo: Esc abre o mini-menu (nao sai)
    assert ui.screen_id == "dialog" and ui.dlg["paused"]
    key(pygame.K_ESCAPE)                          # Esc de novo fecha
    assert not ui.dlg["paused"]
    ui.go("map")
    ui.do_story()
    ui.go("map")
    ui.to_menu()


# ------------------------------------------------------------------ fluxo por cliques
def test_flow_by_clicks_story_stub_garage_bench_shop_save():
    reset()
    key(pygame.K_6)
    frame()
    assert click_label_rect(lambda r: r.size == (300, 64) and r.y == 400)
    frame()
    assert ui.screen_id == "map"
    # CONTINUAR HISTORIA -> stub de cena
    assert click_label_rect(lambda r: r.size == (360, 76))
    frame()
    assert ui.screen_id == "dialog" and ui.map_act["kind"] == "scene" and ui.dlg["sid"] == "p1_garagem"
    shot("dialog_first_line")
    # Esc abre o mini-menu; SALVAR E VOLTAR AO MAPA
    key(pygame.K_ESCAPE)
    assert ui.dlg["paused"]
    assert click_label_rect(lambda r: r.size == (400, 56) and r.y == 352)
    frame()
    assert ui.screen_id == "map" and ui.dlg is None
    # aba GARAGEM -> bancada
    click_tab(1)
    frame()
    assert ui.screen_id == "garage" and ui.garage is ui.campaign.garage
    assert ui.sel is not None
    assert click_label_rect(lambda r: r.size == (295, 44) and r.y == 562)    # ABRIR BANCADA
    frame()
    assert ui.screen_id == "bench"
    assert click_label_rect(lambda r: r.size == (185, 36))                   # VOLTAR
    frame()
    assert ui.screen_id == "garage"
    # aba LOJA: comprar peca
    click_tab(2)
    frame()
    assert ui.screen_id == "shop"
    gg = ui.garage
    before = gg.scrap
    npieces = len(gg.inventory)
    ui.shop_slot = None
    lst = ui.shop_list()
    pc = next(p for p in lst if parts.buy_price(p) <= gg.scrap)
    ui.pick_shop(pc["id"])
    CAMP.pop("save")
    assert click_label_rect(lambda r: r.size == (220, 44) and r.y == 650)    # COMPRAR
    assert gg.scrap < before and len(gg.inventory) == npieces + 1
    assert CAMP.get("save"), "persist nao gravou a chave da campanha"
    assert not FORBIDDEN
    assert cm.Campaign.load().garage.scrap == gg.scrap
    # SALVAR E SAIR -> menu principal com "continuar"
    assert click_label_rect(lambda r: r.size == (190, 40) and r.y == 82)
    assert g.state == "menu" and g.campaign_status == "ok"
    g.text_cache.clear()
    frame()
    assert ("continuar", 22, (225, 210, 250)) in g.text_cache
    shot("main_with_campaign")
    assert not FORBIDDEN


def test_stub_screens_and_back():
    new_campaign_open()
    camp = ui.campaign
    ui.do_story()
    assert ui.screen_id == "dialog"
    ui.back_to_map()
    force_to(camp, "1")
    camp.finish_scene("c1_intro")
    ui.go("map")
    ui.do_story()
    assert ui.screen_id == "tourney" and ui.map_act["kind"] == "match"
    frame()
    shot("stub_tourney")
    ui.back_to_map()
    # chapter_end: avanca ate o fim do capitulo 1 sem aplicar a recompensa antes
    for _ in range(100):
        a = camp.next_action()
        if a["kind"] == "chapter_end":
            break
        if a["kind"] == "scene":
            camp.finish_scene(a["id"])
        else:
            camp.record_match(4, 0)
    ui.go("map")
    ui.do_story()
    assert ui.screen_id == "chapter_end"
    frame()
    ui.back_to_map()
    camp.advance_chapter()
    ui.go("map")
    ui.do_story()
    assert ui.screen_id == "ending"
    frame()
    shot("stub_ending")
    ui.back_to_map()
    ui.to_menu()


# ------------------------------------------------------------------ dialogo
def advance_to_choice(limit=400):
    """Avanca por cliques (completa + proxima) ate a tela de escolha."""
    for _ in range(limit):
        frame()
        if ui.dlg["mode"] == "choice":
            return
        click((500, 200))
    raise AssertionError("nao chegou na escolha")


def play_scene(sid, policy="first", camp=None):
    """Autoplay por cliques de UMA cena (a partir de map_act forcado). Devolve (n_falas, n_escolhas)."""
    ui.map_act = {"kind": "scene", "id": sid}
    ui.go("dialog")
    assert ui.screen_id == "dialog" and ui.dlg is not None, sid
    seen, chose = 0, 0
    for _ in range(2000):
        d = ui.dlg
        if d is None or d["sid"] != sid:
            return seen, chose
        frame()
        if d["mode"] == "choice":
            opts = d["choice"]["opts"]
            idx = 0 if policy == "first" else len(opts) - 1
            r = next(r for r, fn, en in ui.buttons if en and r.size == (980, 40) and r.y == 530 + idx * 46)
            click(r.center)
            chose += 1
            continue
        item = d["list"][d["i"]]
        assert 1 <= len(d["lines"]) <= 4, (sid, item[2])
        assert " ".join(d["lines"]) == " ".join(item[2].split()), (sid, item[2])
        for _ in range(3):
            frame()
        click((500, 200))                       # completa a linha
        assert ui.dlg is d and ui.dlg_chars() >= d["total"], (sid, "linha nao completou")
        frame()
        click((500, 200))                       # avanca
        seen += 1
    raise AssertionError("autoplay nao terminou: " + sid)


def test_all_scene_lines_fit_four_lines_and_options_one_line():
    f = g.font(28)
    for sid, sc in story.SCENES.items():
        items = list(sc["lines"])
        for it in sc["lines"]:
            if isinstance(it, dict):
                assert 2 <= len(it["opts"]) <= 3, sid
                for o in it["opts"]:
                    assert len(o["t"]) <= 46 and f.size("1   " + o["t"])[0] <= 940, (sid, o["t"])
                    items += list(o.get("reply") or [])
        for it in items:
            if isinstance(it, dict):
                continue
            ls = ui.wrap_dialog(f, it[2]) if hasattr(ui, "wrap_dialog") else cui.wrap_dialog(f, it[2])
            assert 1 <= len(ls) <= 4, (sid, it[2])
            assert all(f.size(x)[0] <= 780 for x in ls), (sid, it[2])


def test_autoplay_every_scene_first_and_last_option():
    real_persist = ui.persist
    for policy in ("first", "last"):
        for sid in story.SCENES:
            new_campaign_open()
            camp = ui.campaign
            calls = {"fin": 0, "persist": 0, "fin_sid": []}
            real_fin = camp.finish_scene

            def fin(scene_id, choice_index=None, _real=real_fin, _c=calls):
                _c["fin"] += 1
                _c["fin_sid"].append(scene_id)
                return _real(scene_id, choice_index)

            def persist(_c=calls):
                _c["persist"] += 1
                return True

            camp.finish_scene = fin
            ui.persist = persist
            try:
                n, ch = play_scene(sid, policy)
            finally:
                ui.persist = real_persist
                del camp.finish_scene
            assert n >= 1, sid
            assert calls["fin_sid"][:1] == [sid] and calls["fin_sid"].count(sid) == 1, (sid, calls)
            assert calls["persist"] >= 1, sid
            has_choice = any(isinstance(it, dict) for it in camp.scene_lines(sid))
            assert ch == (1 if has_choice else 0), (sid, ch)
            assert not FORBIDDEN
            ui.to_menu()


def test_p1_screenshots_and_effects():
    new_campaign_open()
    camp = ui.campaign
    scrap0 = camp.garage.scrap
    ui.do_story()
    d = ui.dlg
    assert d["sid"] == "p1_garagem" and d["bg"] == "garagem"
    for _ in range(4):                                  # ate a fala do Ambrosio (falante em destaque)
        frame()
        click((500, 200))
        click((500, 200))
    d["t"] = 99.0
    assert d["who"] == "ambrosio", d["who"]
    shot("p1_garagem")
    advance_to_choice()
    shot("choice_p1")
    assert ui.dlg["mode"] == "choice"
    key(pygame.K_2)                                     # opcao 2: +25 sucata
    assert ui.dlg["reply"] and ui.dlg["fx"] == "+25 sucata"
    ui.dlg["t"] = 99.0
    shot("choice_reply")
    assert camp.garage.scrap == scrap0                  # fx so ao concluir a cena
    for _ in range(10):
        if ui.dlg is None or ui.dlg["sid"] != "p1_garagem":
            break
        frame()
        click((500, 200))
        click((500, 200))
    assert camp.garage.scrap == scrap0 + 25
    assert camp.is_done("p1_garagem")
    assert ui.screen_id == "dialog" and ui.dlg["sid"] == "p2_oficina"     # cena -> cena
    saved = cm.Campaign.load()
    assert saved.is_done("p1_garagem") and saved.garage.scrap == scrap0 + 25
    assert not FORBIDDEN
    ui.to_menu()


def test_scene_ends_in_match_goes_to_tourney_stub_and_final_pre_screenshot():
    new_campaign_open()
    camp = ui.campaign
    force_to(camp, "1")
    for _ in range(60):
        a = camp.next_action()
        if a["kind"] == "scene" and a["id"] == "c1_final_pre":
            break
        if a["kind"] == "scene":
            camp.finish_scene(a["id"])
        else:
            camp.record_match(4, 0)
    assert a["id"] == "c1_final_pre"
    ui.go("map")
    ui.do_story()
    assert ui.dlg["bg"] == "quadra" and set(ui.dlg["cast"]) == {"teo", "vivi", "ambrosio"}
    for _ in range(3):
        frame()
        click((500, 200))
        click((500, 200))
    ui.dlg["t"] = 99.0
    assert ui.dlg["who"] == "vivi"
    shot("c1_final_pre")
    for _ in range(40):
        if ui.screen_id != "dialog":
            break
        frame()
        click((500, 200))
        click((500, 200))
    assert ui.screen_id == "tourney" and ui.map_act["kind"] == "match"
    assert not FORBIDDEN
    ui.to_menu()


def test_cond_lines_use_scene_lines():
    sid = "c1_end"
    new_campaign_open()
    camp = ui.campaign
    full = [x for x in story.SCENES[sid]["lines"] if not isinstance(x, dict)]
    assert any(len(x) > 3 for x in full)
    camp.garage.flags.pop("bia_convidada", None)
    ui.map_act = {"kind": "scene", "id": sid}
    ui.go("dialog")
    a = [x for x in ui.dlg["main"]]
    assert a == [x for x in camp.scene_lines(sid) if not isinstance(x, dict)]
    camp.garage.flags["bia_convidada"] = 1
    camp.done.append("c1_final_lose")                   # cond ("done", ...) tambem entra
    ui.go("map")
    ui.map_act = {"kind": "scene", "id": sid}
    ui.go("dialog")
    b = ui.dlg["main"]
    assert b == [x for x in camp.scene_lines(sid) if not isinstance(x, dict)] and len(b) > len(a)
    ui.to_menu()


def test_esc_resume_does_not_duplicate_fx_and_choice_applied_once():
    new_campaign_open()
    camp = ui.campaign
    scrap0 = camp.garage.scrap
    ui.do_story()
    advance_to_choice()
    ui.dlg_pick(1)                                      # +25 sucata (ainda nao aplicado)
    key(pygame.K_ESCAPE)
    assert ui.dlg["paused"]
    key(pygame.K_ESCAPE)                                # fecha o mini-menu
    assert not ui.dlg["paused"]
    key(pygame.K_ESCAPE)
    assert click_label_rect(lambda r: r.size == (400, 56) and r.y == 352)
    frame()
    assert ui.screen_id == "map" and camp.garage.scrap == scrap0 and not camp.is_done("p1_garagem")
    assert cm.Campaign.load().garage.scrap == scrap0
    ui.do_story()                                       # retoma do comeco
    assert ui.dlg["i"] == 0 and ui.dlg["mode"] == "say"
    advance_to_choice()
    ui.dlg_pick(1)
    for _ in range(10):
        if ui.dlg is None or ui.dlg["sid"] != "p1_garagem":
            break
        frame()
        click((500, 200))
        click((500, 200))
    assert camp.garage.scrap == scrap0 + 25             # uma vez so
    ui.to_menu()


def test_skip_scene_with_choice_picks_option_one_and_warns():
    new_campaign_open()
    camp = ui.campaign
    hero = camp.hero_robot()
    xp0 = (hero["level"], hero["xp"])
    ui.do_story()
    frame()
    assert click_label_rect(lambda r: r.size == (132, 30))              # PULAR CENA
    frame()
    assert ui.dlg["confirm"]
    assert click_label_rect(lambda r: r.size == (250, 56) and r.x == 560)   # CANCELAR
    assert not ui.dlg["confirm"] and not camp.is_done("p1_garagem")
    assert click_label_rect(lambda r: r.size == (132, 30))
    frame()
    shot("skip_confirm")
    assert click_label_rect(lambda r: r.size == (250, 56) and r.x == 290)   # PULAR
    assert camp.is_done("p1_garagem")
    assert (hero["level"], hero["xp"]) != xp0                           # opcao 1: xp_hero +20
    assert "escolha 1" in ui.toast and ui.toast_t > 0
    frame()
    assert ui.screen_id == "dialog" and ui.dlg["sid"] == "p2_oficina"
    # sem escolha: so conclui
    ui.go("map")
    ui.map_act = {"kind": "scene", "id": "p3_peneira_pre"}
    ui.go("dialog")
    ui.dlg_set("confirm", True)
    ui.dlg_skip()
    assert camp.is_done("p3_peneira_pre") and ui.toast == "Cena pulada."
    ui.to_menu()


def test_invalid_or_empty_scene_returns_to_map():
    new_campaign_open()
    for act in ({"kind": "scene", "id": "zzz_inexistente"}, {"kind": "scene"}, None, {}):
        ui.map_act = act
        ui.go("dialog")
        assert ui.screen_id == "map" and ui.dlg is None
        frame()
    ui.screen_id = "dialog"                              # tela sem dlg: nao quebra e Esc volta
    ui.dlg = None
    frame()
    key(pygame.K_ESCAPE)
    assert ui.screen_id == "map"
    ui.to_menu()


def test_typing_300_frames_no_char_keys_no_surface():
    new_campaign_open()
    ui.do_story()
    frame()
    real = pygame.Surface
    count = [0]

    class Counting(real):
        def __init__(self, *a, **k):
            count[0] += 1
            super().__init__(*a, **k)

    g.text_cache.clear()
    for _ in range(3):
        frame()
    keys = set()
    pygame.Surface = Counting
    try:
        for n in range(300):
            if n % 60 == 0:
                click((500, 200))
                click((500, 200))
            frame()
            keys.update(g.text_cache.keys())
    finally:
        pygame.Surface = real
    assert count[0] == 0
    assert len(keys) < 150 and len(g.text_cache) < soccer.TEXT_CACHE_MAX
    lines = set()
    for it in story.SCENES["p1_garagem"]["lines"]:
        if not isinstance(it, dict):
            lines.update(wrap for wrap in cui.wrap_dialog(g.font(28), it[2]))
    for (sx, size, _c) in keys:
        if size == 28:
            assert sx in lines or not any(l.startswith(sx) for l in lines if len(sx) > 3), sx
    ui.to_menu()


def test_dialog_never_touches_free_mode_saves():
    new_campaign_open()
    ui.do_story()
    advance_to_choice()
    ui.dlg_pick(0)
    for _ in range(40):
        if ui.dlg is None:
            break
        frame()
        click((500, 200))
        click((500, 200))
    assert not FORBIDDEN
    assert set(CAMP) <= {"save", "bad"} and not CAREER
    ui.to_menu()


# ------------------------------------------------------------------ desenho
def states():
    """Gera (nome, preparar) para cada tela/estado."""
    return ["menu_none", "menu_ok", "menu_bad", "menu_confirm", "map_start", "map_mid", "map_draft",
            "garage", "bench", "shop", "dialog", "dialog_done", "dialog_choice", "dialog_reply",
            "dialog_pause", "dialog_confirm", "tourney", "chapter_end", "ending"] + P10_STATES


def setup_state(name):
    if name in P10_STATES:
        return setup_p10(name)
    if name.startswith("menu"):
        save = {"menu_none": None, "menu_ok": cm.new_campaign(random.Random(1)).to_json(),
                "menu_bad": "{", "menu_confirm": cm.new_campaign(random.Random(1)).to_json()}[name]
        reset(save=save)
        ui.open()
        if name == "menu_confirm":
            ui.do_new()
            assert ui.confirm_new
        return
    reset()
    ui.open()
    ui.do_new()
    camp = ui.campaign
    if name == "map_start":
        return
    if name == "map_mid":
        force_to(camp, "1")
        camp.finish_scene("c1_intro")
        ui.go("map")
    elif name in ("map_draft", "ending"):
        force_to(camp, "2")
        ui.go("map")
        if name == "ending":
            ui.do_story()
    elif name in ("garage", "shop"):
        ui.go(name)
    elif name == "bench":
        ui.go("garage")
        ui.open_bench()
    elif name.startswith("dialog"):
        ui.do_story()
        if name != "dialog":
            dialog_state(name)
    elif name == "tourney":
        force_to(camp, "1")
        camp.finish_scene("c1_intro")
        ui.go("map")
        ui.do_story()
    elif name == "chapter_end":
        force_to(camp, "1")
        for _ in range(100):
            a = camp.next_action()
            if a["kind"] == "chapter_end":
                break
            if a["kind"] == "scene":
                camp.finish_scene(a["id"])
            else:
                camp.record_match(4, 0)
        ui.go("map")
        ui.do_story()
    assert ui.screen_id in ("map", "garage", "shop", "bench", "dialog", "tourney", "chapter_end", "ending")


def dialog_state(name):
    """Leva o dialogo (p1_garagem) ao estado pedido."""
    if name == "dialog_done":
        ui.dlg["t"] = 99.0
    elif name in ("dialog_choice", "dialog_reply"):
        advance_to_choice()
        if name == "dialog_reply":
            ui.dlg_pick(1)
    elif name == "dialog_pause":
        key(pygame.K_ESCAPE)
    elif name == "dialog_confirm":
        ui.dlg["confirm"] = True


def test_60_frames_every_screen_zero_surface_and_cache():
    real = pygame.Surface
    count = [0]

    class Counting(real):
        def __init__(self, *a, **k):
            count[0] += 1
            super().__init__(*a, **k)

    for name in states():
        setup_state(name)
        g.text_cache.clear()
        keys = set()
        for _ in range(5):
            frame()                       # aquecimento
        pygame.Surface = Counting
        try:
            count[0] = 0
            for _ in range(60):
                frame()
                keys.update(g.text_cache.keys())
        finally:
            pygame.Surface = real
        assert count[0] == 0, "%s criou %d Surface em 60 quadros" % (name, count[0])
        assert len(keys) < soccer.TEXT_CACHE_MAX and len(keys) < 150, (name, len(keys))
        assert len(g.text_cache) <= soccer.TEXT_CACHE_MAX
        assert not FORBIDDEN
        ui.to_menu()
    # menu principal (com campanha salva) tambem
    reset(save=cm.new_campaign(__import__("random").Random(1)).to_json())
    pygame.Surface = Counting
    try:
        count[0] = 0
        for _ in range(60):
            frame()
    finally:
        pygame.Surface = real
    assert count[0] == 0


def test_persist_never_writes_garage_or_career():
    new_campaign_open()
    ui.act((True, "ok"))
    ui.persist()
    ui.to_menu()
    assert not FORBIDDEN
    assert cm.Campaign.load().garage is not None


def test_draw_time_budget():
    out = {}
    for name in states():
        setup_state(name)
        for _ in range(5):
            g.draw()
        t = time.perf_counter()
        for _ in range(100):
            g.draw()
        out[name] = (time.perf_counter() - t) / 100 * 1000
        ui.to_menu()
    print("draw_ms:", {k: round(v, 2) for k, v in out.items()})
    for k, v in out.items():
        if v >= 3.0:
            print("AVISO: frame lento (informativo):", k, round(v, 2), "ms")
        assert v < 25.0, (k, v)



# ================================================================== passo 10: torneio / partida / fim
REAL_SIM = cm.sim_match
REAL_SHOOT = cm.shootout
SIMQ = []                                   # placares forcados (my, opp) consumidos por sim_match
cm.sim_match = lambda F, O, rng: SIMQ.pop(0) if SIMQ else REAL_SIM(F, O, rng)
MAP_CONT = (700, 446, 360, 76)
BTN_WATCH, BTN_SIM, BTN_TRAIN, BTN_BACK = (700, 390, 360, 76), (700, 478, 360, 56), (700, 546, 360, 50), (700, 608, 360, 44)
ROUND_CONT = (420, 650, 260, 42)
CE_CONT = (400, 596, 300, 64)
END_BACK = (400, 560, 300, 60)
TR_WATCH, TR_SIM, TR_BACK = (250, 470, 600, 64), (250, 546, 600, 50), (250, 610, 600, 42)
P10_STATES = ["tourney_g0", "tourney_g2", "tourney_sf", "tourney_final_pity", "tourney_single", "training",
              "round_camp", "round_pen", "round_levelup", "round_elim", "round_training", "chapter_end_recruit",
              "ending_draft", "ending_done"]


def click_rect(rect):
    r0 = pygame.Rect(rect)
    frame()
    for r, fn, enabled in ui.buttons:
        if enabled and r == r0:
            click(r.center)
            return
    raise AssertionError("botao %s nao encontrado em %s" % (rect, ui.screen_id))


def dialog_step():
    d = ui.dlg
    frame()
    if d is None:
        return
    if d["mode"] == "choice":
        click_rect((60, 530, 980, 40))
        return
    for _ in range(3):
        frame()
    click((500, 200))
    frame()
    click((500, 200))


def drive_until(pred, score=(2, 0), limit=500, seen=None):
    """Joga a campanha so por cliques (mapa/dialogo/torneio com SIMULAR forcado/resultado/fim de capitulo)."""
    for _ in range(limit):
        frame()
        if seen is not None:
            seen.add(ui.screen_id)
        if pred():
            del SIMQ[:]
            return
        sid = ui.screen_id
        if sid == "map":
            click_rect(MAP_CONT)
        elif sid == "dialog":
            dialog_step()
        elif sid == "tourney":
            SIMQ.append(score)
            click_rect(BTN_SIM)
        elif sid == "round":
            click_rect(ROUND_CONT)
        elif sid == "chapter_end":
            click_rect(CE_CONT)
        else:
            raise AssertionError("tela inesperada " + sid)
    raise AssertionError("drive_until nao convergiu")


def at_match(tid=None, stage=None):
    def pred():
        a = ui.map_act
        return (ui.screen_id == "tourney" and a is not None and a["kind"] == "match"
                and (tid is None or a["tournament"] == tid) and (stage is None or a["stage"] == stage))
    return pred


def fresh_campaign(seed=11):
    reset()
    ui.open()
    ui.rng.seed(seed)
    ui.do_new()
    del SIMQ[:]
    assert ui.screen_id == "map"


def text_cache_has(sub):
    return any(sub in k[0] for k in g.text_cache)


def test_latin1_source():
    src = open(os.path.join(ROOT, "game", "campaign_ui.py"), encoding="utf-8").read()
    assert max(ord(c) for c in src) <= 255
    src.encode("latin-1")


def test_flow_prologue_cap1_all_simulated_by_clicks():
    fresh_campaign()
    seen = set()
    drive_until(lambda: ui.screen_id == "map" and ui.campaign.ch == "2", seen=seen)
    cp = ui.campaign
    assert {"map", "dialog", "tourney", "round", "chapter_end"} <= seen
    for sid in ("c1_g2_fundao_pre", "c1_final_pre", "c1_sf_pos", "c1_final_win", "c1_end", "p4_peneira_pos"):
        assert sid in cp.done, sid
    assert "reward:rw_P" in cp.done and "reward:rw_1" in cp.done
    assert cp.stats["matches"] == 6 and cp.stats["sims"] == 6          # treino + G1 G2 G3 SF F
    assert ui.chapter_state(story.CHAPTERS[1]) == "done" and ui.chapter_state(story.CHAPTERS[0]) == "done"
    assert any(r["name"] == "Gambiarra" for r in cp.garage.robots)
    assert "Tanque" in cp.garage.unlocked and cp.garage.stats["played"] == 6
    ui.map_act = cp.next_action()
    assert ui.map_act == {"kind": "end", "draft": True}
    saved = cm.Campaign.load()
    # capitulo 2 ainda e esqueleto (draft): Campaign.save recusa estado em capitulo draft e preserva o save
    # anterior (chapter_end do Cap.1); quando o Cap.2 existir, o save sera "2".
    assert saved.ch in ("1", "2") and "c1_end" in saved.done
    assert not FORBIDDEN and set(CAMP) == {"save"}
    ui.to_menu()


def test_real_watch_match_at_max_speed_returns_to_campaign():
    fresh_campaign(3)
    drive_until(at_match("t_c1", "G1"))
    cp = ui.campaign
    sc0 = cp.garage.scrap
    click_rect(BTN_WATCH)
    assert g.state == "kickoff" and g.match_sink[0] == "campaign" and g.career_match
    t0 = json.loads(CAMP["save"])["c"]["tour"]
    assert not t0 or not t0["results"]                     # ASSISTIR so grava ao terminar a partida
    g.speed_idx = 3
    key(pygame.K_ESCAPE)                                  # Esc e ignorado em partida assistida
    assert g.state == "kickoff" and g.career_match
    for _ in range(200000):
        g.update(1 / 60)
        if g.state == "over":
            break
    assert g.state == "over"
    key(pygame.K_RETURN)
    assert g.state == "campaign" and ui.screen_id == "round"
    info = ui.round_info
    assert info["camp"] and info["score"] == (g.score[0], g.score[1])
    assert len(info["goals"]) == sum(g.score) and info["stage"] == "G1"
    assert all(nm for (_m, nm, _t, _o) in info["goals"])
    assert cp.garage.scrap == sc0 + info["rew"]["scrap"] and cp.stats["matches"] == 2
    res = json.loads(CAMP["save"])["c"]["tour"]["results"]
    assert len(res) == 1 and res[0][:3] == ["G1", g.score[0], g.score[1]]
    shot("round_watched")
    frame()
    click_rect(ROUND_CONT)
    assert ui.screen_id in ("tourney", "dialog")
    assert not FORBIDDEN
    ui.to_menu()


def test_forced_draw_in_knockout_shows_penalties():
    fresh_campaign()
    drive_until(at_match("t_c1", "SF"))
    cm.shootout = lambda a, b, r: (4, 3)
    try:
        SIMQ.append((1, 1))
        click_rect(BTN_SIM)
    finally:
        cm.shootout = REAL_SHOOT
    assert ui.screen_id == "round"
    info = ui.round_info
    assert info["pen"] == (4, 3) and info["outcome"] == "next" and info["score"] == (1, 1)
    g.text_cache.clear()
    frame()
    assert text_cache_has("(4-3 nos pênaltis)") and text_cache_has("Você avançou!")
    assert text_cache_has("(simulada)") and text_cache_has("Jogo simulado: sem lances.")
    shot("round_penalties")
    assert ui.campaign.tour["results"][-1] == ["SF", 1, 1, 4, 3]
    ui.to_menu()


def test_forced_group_elimination_restarts_tournament_with_elim_scene():
    fresh_campaign()
    drive_until(at_match("t_c1", "G1"))
    for _ in range(3):
        if ui.screen_id == "dialog":
            drive_until(at_match("t_c1"))
        SIMQ.append((0, 3))
        click_rect(BTN_SIM)
        info = ui.round_info
        frame()
        click_rect(ROUND_CONT)
    assert info["outcome"] == "elim"
    assert ui.screen_id == "dialog" and ui.dlg["sid"] == "c1_repescagem"
    drive_until(at_match("t_c1", "G1"))
    assert ui.map_act["attempt"] == 1 and ui.campaign.tour["results"] == []
    g.text_cache.clear()
    frame()
    assert text_cache_has("Tentativa 2") and text_cache_has("GRUPO - JOGO 1/3")
    assert "c1_repescagem#0" in ui.campaign.done
    ui.to_menu()


def test_elimination_message_text():
    fresh_campaign()
    drive_until(at_match("t_c1", "G1"))
    drive_until(at_match("t_c1", "G3"), score=(0, 3))
    SIMQ.append((0, 3))
    click_rect(BTN_SIM)
    assert ui.round_info["outcome"] == "elim"
    g.text_cache.clear()
    frame()
    assert text_cache_has("Eliminado no grupo - o torneio recomeça")
    shot("round_elim")
    ui.to_menu()


def test_forced_loss_in_final_pity_lose_scene_and_win():
    fresh_campaign()
    drive_until(at_match("t_c1", "F"))
    assert not ui.map_act["pity"]
    SIMQ.append((0, 2))
    click_rect(BTN_SIM)
    assert ui.round_info["outcome"] == "retry" and ui.campaign.pity == 1
    g.text_cache.clear()
    frame()
    assert text_cache_has("Derrota - tente de novo")
    click_rect(ROUND_CONT)
    assert ui.screen_id == "dialog" and ui.dlg["sid"] == "c1_final_lose"
    drive_until(at_match("t_c1", "F"))
    assert ui.map_act["pity"] == 1 and "c1_final_lose#1" in ui.campaign.done
    g.text_cache.clear()
    frame()
    assert text_cache_has("Ajuda do chefe: -1 de Força") and text_cache_has("CHEFE")
    shot("tourney_final_pity")
    SIMQ.append((2, 0))
    click_rect(BTN_SIM)
    assert ui.round_info["outcome"] == "champion" and ui.campaign.pity == 0
    g.text_cache.clear()
    frame()
    assert text_cache_has("CAMPEÃO!")
    click_rect(ROUND_CONT)
    assert ui.screen_id == "dialog" and ui.dlg["sid"] == "c1_final_win"
    ui.to_menu()


def test_training_does_not_advance_and_pays_less_in_later_tiers():
    fresh_campaign()
    drive_until(at_match("t_c1", "G1"))
    cp = ui.campaign
    st = json.dumps(cp.tour, sort_keys=True)
    sc0, played0 = cp.garage.scrap, cp.garage.stats["played"]
    click_rect(BTN_TRAIN)
    assert ui.screen_id == "training" and ui.train["training"]
    shot("training")
    SIMQ.append((2, 0))
    click_rect(TR_SIM)
    assert ui.screen_id == "round" and ui.round_info["training"]
    assert json.dumps(cp.tour, sort_keys=True) == st and cp.stats["trained"] == 1
    assert cp.garage.stats["played"] == played0 + 1 and cp.garage.scrap > sc0
    g.text_cache.clear()
    frame()
    assert text_cache_has("TREINO") and text_cache_has("Treino concluído - o torneio não avançou")
    click_rect(ROUND_CONT)
    assert ui.screen_id == "tourney" and ui.map_act["stage"] == "G1"
    # capitulo 2 (tier 1): treino usa tier 0 => sucata menor que a de uma partida valendo
    ui.to_menu()
    reset(save=None)
    ui.open()
    ui.do_new()
    cp = ui.campaign
    force_to(cp, "2")
    ui.go("map")
    sc0 = cp.garage.scrap
    click_rect((880, 532, 180, 40))                           # TREINO no mapa
    assert ui.screen_id == "training" and ui.train_back == "map"
    SIMQ.append((2, 0))
    click_rect(TR_SIM)
    gain = cp.garage.scrap - sc0
    base = gm.SCRAP_WIN + gm.SCRAP_PER_GOAL * 2
    assert gain == int(round(base * gm.TIER_MUL[0])) < int(round(base * gm.TIER_MUL[cp.econ_tier()]))
    click_rect(ROUND_CONT)
    assert ui.screen_id == "map"
    assert not FORBIDDEN
    ui.to_menu()


def test_real_watch_training_match():
    fresh_campaign(5)
    drive_until(at_match("t_c1", "G1"))
    cp = ui.campaign
    ui.open_training("tourney")
    click_rect(TR_WATCH)
    assert g.state == "kickoff" and g.match_sink[0] == "campaign"
    g.speed_idx = 3
    for _ in range(200000):
        g.update(1 / 60)
        if g.state == "over":
            break
    click((10, 10))                                       # clique tambem finaliza
    assert g.state == "campaign" and ui.screen_id == "round" and ui.round_info["training"]
    assert cp.stats["trained"] == 1 and cp.tour["results"] == []
    ui.to_menu()


def test_esc_on_tourney_and_round_returns_to_map_with_save():
    fresh_campaign()
    drive_until(at_match("t_c1", "G1"))
    key(pygame.K_ESCAPE)
    assert ui.screen_id == "map" and CAMP.get("save")
    ui.do_story()
    assert ui.screen_id == "tourney"
    SIMQ.append((2, 0))
    click_rect(BTN_SIM)
    assert ui.screen_id == "round"
    key(pygame.K_ESCAPE)
    assert ui.screen_id == "map"
    frame()
    # o save feito ao fim da partida ja guardou o resultado (Esc nao perde progresso)
    assert len(cm.Campaign.load().tour["results"]) == 1
    ui.to_menu()


def test_close_between_screens_keeps_progress():
    fresh_campaign()
    drive_until(at_match("t_c1", "G1"))
    SIMQ.append((3, 0))
    click_rect(BTN_SIM)
    assert ui.screen_id == "round"
    snap = CAMP["save"]
    # "fecha o navegador" na tela de resultado e reabre
    reset(save=snap)
    ui.open()
    ui.do_continue()
    assert ui.screen_id == "map"
    cp = ui.campaign
    assert [r[:3] for r in cp.tour["results"]] == [["G1", 3, 0]]
    ui.do_story()
    assert ui.screen_id in ("tourney", "dialog")
    ui.to_menu()


def test_round_info_none_returns_to_map_without_exception():
    fresh_campaign()
    ui.round_info = None
    ui.screen_id = "round"
    frame()
    click_rect(ROUND_CONT)
    assert ui.screen_id == "map"
    ui.match_done([1, 0], [])                              # callback sem partida pendente: nao levanta
    assert ui.screen_id == "map"
    ui.train_done([1, 0], [])
    assert ui.screen_id == "map"
    ui.to_menu()


def test_two_clicks_same_frame_do_not_duplicate():
    fresh_campaign()
    drive_until(at_match("t_c1", "G1"))
    cp = ui.campaign
    frame()
    r = next(r for r, fn, en in ui.buttons if r == pygame.Rect(BTN_SIM))
    SIMQ.append((2, 0))
    click(r.center)
    click(r.center)
    assert cp.stats["matches"] == 2 and len(cp.tour["results"]) == 1
    ui.to_menu()


def test_tourney_group_table_bracket_and_labels():
    fresh_campaign()
    drive_until(at_match("t_c1", "G1"))
    g.text_cache.clear()
    frame()
    shot("tourney_group_before")
    for lab in ("GRUPO - JOGO 1/3", "Força recomendada: 45", "Tentativa 1", "CHAVEAMENTO", "SEMIFINAL", "FINAL (CHEFE)"):
        assert text_cache_has(lab), lab
    assert len(ui.tview["rows"]) == 4 and [b["stage"] for b in ui.tview["ko"]] == ["SF", "F"]
    drive_until(at_match("t_c1", "G3"))
    frame()
    shot("tourney_group_after")
    assert sum(r["p"] for r in ui.tview["rows"]) >= 8
    drive_until(at_match("t_c1", "F"))
    frame()
    shot("tourney_knockout")
    assert ui.tview["ko"][0]["res"][:3] == ["SF", 2, 0] and ui.tview["ko"][1]["cur"]
    assert ui.campaign.user_group_pos() <= 2
    ui.to_menu()


def test_chapter_end_report_and_full_squad_warning():
    fresh_campaign()
    drive_until(at_match("t_c1", "F"))
    gg = ui.campaign.garage
    while len(gg.robots) < gm.MAX_SQUAD - 1:
        gg.robots.append(gg.make_robot("Extra%d" % len(gg.robots), "MID", "Disco", 40))
    gg.robots.append(gg.make_robot("Extra9", "MID", "Disco", 40))          # elenco cheio (8)
    drive_until(lambda: ui.screen_id == "chapter_end" and ui.campaign.ch == "1")
    v = ui.ce_view
    assert v["recruits"] == [("Gambiarra", "Tanque", 3, (255, 150, 40))] and v["unlocked"] == ["Tanque"]
    assert v["piece"][1] == parts.RAR_COLORS[1] and v["scrap"] == 120
    assert v["warnings"] and "Elenco cheio" in v["warnings"][0]
    g.text_cache.clear()
    frame()
    assert text_cache_has("Gambiarra") and text_cache_has("CAPÍTULO CONCLUÍDO")
    shot("chapter_end_recruit")
    assert len(gg.robots) == gm.MAX_SQUAD
    click_rect(CE_CONT)
    assert ui.screen_id == "map" and ui.campaign.ch == "2"
    assert json.loads(CAMP["save"])["c"]["ch"] in ("1", "2")      # "2" so quando o Cap.2 deixar de ser draft
    ui.to_menu()


def test_ending_draft_and_completed():
    fresh_campaign()
    force_to(ui.campaign, "2")
    ui.go("map")
    ui.do_story()
    assert ui.screen_id == "ending" and ui.end_view["draft"]
    g.text_cache.clear()
    frame()
    assert text_cache_has("Os próximos capítulos ainda estão em produção.")
    shot("ending_draft")
    click_rect(END_BACK)
    assert ui.screen_id == "map"
    ui.do_story()
    ui.end_view = dict(ui.end_view, draft=False, titles=1, matches=31, boss_losses=4)
    g.text_cache.clear()
    frame()
    assert text_cache_has("CAMPANHA CONCLUÍDA") and text_cache_has("Derrotas contra chefes")
    shot("ending_done")
    click_rect(END_BACK)
    assert ui.screen_id == "map"
    ui.to_menu()


def test_round_levelup_shows_level_up_rows():
    setup_p10("round_levelup")
    info = ui.round_info
    assert any(row[5] for row in info["rows"]) and ui.screen_id == "round"
    g.text_cache.clear()
    frame()
    assert text_cache_has("NIVEL UP!")
    shot("round_levelup")
    ui.to_menu()


def setup_p10(name):
    fresh_campaign(11)
    cp = ui.campaign
    if name == "tourney_g0":
        return drive_until(at_match("t_c1", "G1"))
    if name == "tourney_g2":
        return drive_until(at_match("t_c1", "G3"))
    if name == "tourney_sf":
        return drive_until(at_match("t_c1", "SF"))
    if name == "tourney_final_pity":
        drive_until(at_match("t_c1", "F"))
        cp.pity = 2
        return ui.go("tourney")
    if name == "tourney_single":
        return drive_until(at_match("t_p_treino"))
    if name == "training":
        return ui.open_training("map")
    if name == "round_levelup":
        drive_until(at_match("t_c1", "G1"))
        for r in cp.garage.robots:
            r["xp"] = gm.xp_need(r["level"]) - 1
    elif name == "round_pen":
        drive_until(at_match("t_c1", "SF"))
    elif name == "round_elim":
        drive_until(at_match("t_c1", "G3"), score=(0, 3))
    elif name == "round_camp":
        drive_until(at_match("t_c1", "G2"))
    elif name == "round_training":
        drive_until(at_match("t_c1", "G1"))
        ui.open_training("tourney")
        SIMQ.append((2, 1))
        return click_rect(TR_SIM)
    elif name == "chapter_end_recruit":
        return drive_until(lambda: ui.screen_id == "chapter_end")
    elif name in ("ending_draft", "ending_done"):
        force_to(cp, "2")
        ui.go("map")
        ui.do_story()
        if name == "ending_done":
            ui.end_view = dict(ui.end_view, draft=False)
        return
    if name.startswith("round_"):
        if name == "round_pen":
            cm.shootout = lambda a, b, r: (5, 4)
            SIMQ.append((1, 1))
        elif name == "round_elim":
            SIMQ.append((0, 3))
        else:
            SIMQ.append((3, 1))
        try:
            click_rect(BTN_SIM)
        finally:
            cm.shootout = REAL_SHOOT
        assert ui.screen_id == "round", name


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
