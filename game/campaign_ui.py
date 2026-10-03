# -*- coding: utf-8 -*-
"""Telas da Campanha "A Garagem do Vô" (passos 8 a 10: menu, mapa, DIALOGO, torneio, resultado, fim de capitulo, fim).

CampaignUI herda de RobotsUI a garagem, a bancada, a loja e os helpers de desenho. Tudo opera sobre
`self.campaign.garage` e grava SOMENTE na chave da campanha (persist() -> Campaign.save()); nunca
chama garage.save() e nunca toca a chave do modo livre.

Telas (screen_id): menu, map (aba HISTÓRIA), garage (aba GARAGEM), shop (aba LOJA), bench, dialog
(cena com retratos/cenarios por codigo, digitacao e escolhas; ver game/portraits.py),
tourney (grupo + chaveamento + ASSISTIR/SIMULAR/TREINO), training (partida de treino), round (resultado,
reaproveita draw_round_body de RobotsUI), chapter_end (relatorio de recompensas), ending (fim/em producao).

Partidas (passo 10): ASSISTIR chama Game.start_robot_match(..., return_state="campaign") e o Game devolve
(score, events) a match_done(); SIMULAR chama Campaign.simulate_current(). Ambos terminam em finish_result(),
que persiste (autosave) e abre a tela "round". A campanha so avanca em record_match/advance_chapter.
Estado derivado do torneio (tabela do grupo, chaveamento) e calculado UMA vez ao entrar na tela, nunca por quadro.

Dialogo (passo 9): ao entrar, pega a cena de next_action() (kind scene) e filtra as falas por cond com
Campaign.scene_lines(). A fala e quebrada UMA vez (greedy, Font(None,28), 780 px, max 4 linhas); cada
LINHA inteira e renderizada uma vez por Game.text_img (cache) e a digitacao (~45 chars/s) so recorta
com blit(area=Rect): nunca se renderiza prefixo. Clique/Enter/Espaco completa a linha digitando e,
depois, avanca. Escolha (ultimo item da cena): pergunta + 2-3 botoes (teclas 1-3); depois as falas de
`reply`. Ao terminar a cena (e a escolha) finish_scene() e chamada UMA vez, depois persist() (autosave)
e a proxima acao de next_action() e despachada. Esc = mini-menu (CONTINUAR / SALVAR E VOLTAR AO MAPA;
voltar nao conclui a cena: ela recomeca do inicio, sem duplicar fx). PULAR CENA pede confirmacao e,
se a cena tem escolha, ESCOLHE A OPCAO 1 (o aviso diz isso e mostra o efeito); sem escolha, so conclui.
Regras de performance: nada de pygame.Surface no draw; so Font(None) e glifos Latin-1; a proxima acao
da campanha (next_action) e calculada ao entrar no mapa, nunca por quadro.
"""
import math

import pygame

import campaign as C
import garage as G
import parts as P
import portraits
import story
from career_ui import BG, DIM, GOLD, GREEN, LINE, PANEL, RED, TEXT, W
from robots_ui import RobotsUI

TABS = [("map", "HISTÓRIA"), ("garage", "GARAGEM"), ("shop", "LOJA")]
FRAME_SCREENS = tuple(t for t, _ in TABS)
STUB_SCREENS = ("tourney", "training", "round", "chapter_end", "ending")   # Esc = volta ao mapa
SCREENS = ("menu", "map", "garage", "shop", "bench", "dialog") + STUB_SCREENS
FRAME_EXTRA = ("tourney", "training")          # telas com cabecalho + abas (HISTORIA fica ativa)
NODE_X0, NODE_DX = 110, 176
NODE_Y = (200, 262)
NODE_R = 26
PULSE_PERIOD = 1.6
NEON = (0, 230, 255)
# ---- dialogo
DLG_BOX = pygame.Rect(30, 478, 1040, 190)
PORTRAIT_RECT = pygame.Rect(46, 490, 150, 166)
TXT_X, TXT_Y, TXT_W, LINE_H, TXT_SIZE, MAX_LINES = 215, 512, 780, 34, 28, 4
TYPE_CPS = 45.0                       # caracteres por segundo da digitacao
NARRATOR_TEXT = (190, 205, 230)
DARK = (10, 16, 30)
TOAST_SECONDS = 4.0
KIND_SCREEN = {"scene": "dialog", "match": "tourney", "chapter_end": "chapter_end", "end": "ending"}
STAGE_TITLES = {"QF": "QUARTAS DE FINAL", "SF": "SEMIFINAL", "F": "FINAL"}
BOX_BG = (14, 30, 52)
HILITE = (22, 70, 100)


def wrap_dialog(font, text, maxw=TXT_W):
    """Quebra gulosa por largura real da fonte (UMA vez por fala). Devolve a lista de linhas."""
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if font.size(t)[0] <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fx_text(fx):
    """Feedback discreto dos efeitos de uma escolha (flags nao aparecem)."""
    out = []
    fx = fx or {}
    if fx.get("scrap"):
        out.append("%+d sucata" % fx["scrap"])
    if fx.get("xp_hero"):
        out.append("XP do herói %+d" % fx["xp_hero"])
    if fx.get("xp_team"):
        out.append("XP da equipe %+d" % fx["xp_team"])
    if fx.get("piece"):
        out.append("peça nova")
    return "   ".join(out)


def stage_label(stage, single=False):
    """Titulo do estagio: "GRUPO - JOGO 2/3", "SEMIFINAL", "FINAL"..."""
    if single:
        return "PARTIDA ÚNICA"
    if stage[0] == "G":
        return "GRUPO - JOGO %s/3" % stage[1]
    return STAGE_TITLES.get(stage, stage)


def stage_team(tr, stage):
    """Id do time (story.TEAMS) que o usuario enfrenta no estagio."""
    if stage[0] == "G":
        return tr["group"][int(stage[1]) - 1]
    return {"QF": tr.get("qf"), "SF": tr.get("sf"), "F": tr["final"]}[stage]


def force_text(lo, hi):
    """Faixa de Força recomendada ("45" ou "45 a 47")."""
    a, b = int(round(lo)), int(round(hi))
    return str(a) if a == b else "%d a %d" % (a, b)


class CampaignUI(RobotsUI):
    SHOP_EMPTY_TEXT = "Sem peças nesse slot. A loja é reposta a cada partida."
    SHOP_STOCK_FMT = "Estoque: %d peça(s). Reposta a cada partida."

    def __init__(self, game):
        self.campaign = None            # antes do super: a propriedade `garage` o consulta
        super().__init__(game)
        self.tabs = list(TABS)
        self.frame_screens = FRAME_SCREENS + FRAME_EXTRA
        self.screens = SCREENS
        self.map_act = None             # proxima acao (cache; recalculada ao entrar no mapa)
        self.notices = []               # avisos persistentes no mapa (reparo, recruta, save) ate o OK
        self.warned = set()             # chaves de avisos de save ja mostrados nesta campanha
        self.pulse = 0.0
        self.dlg = None                 # estado da cena em andamento (tela "dialog")
        self.toast = ""                 # aviso curto (ex.: cena pulada com escolha 1)
        self.toast_t = 0.0
        self.tview = None               # modelo da tela "tourney" (calculado ao entrar)
        self.train = None               # adversario do treino em andamento (tela "training")
        self.train_back = "map"
        self.ce_view = None             # modelo da tela "chapter_end"
        self.end_view = None            # modelo da tela "ending"

    # `self.garage` aponta SEMPRE para a garagem da campanha (os metodos herdados usam self.garage)
    @property
    def garage(self):
        return self.campaign.garage if self.campaign is not None else None

    @garage.setter
    def garage(self, value):
        pass                            # ignorado de proposito: a fonte da verdade e a campanha

    # ------------------------------------------------------------ navegacao
    def open(self):
        """Entra na Campanha (tela de menu)."""
        self.status = C.Campaign.load_status()
        if self.status == "bad":
            C.Campaign.load()           # grava o texto cru em <chave>.bad; nunca sobrescreve o save
        self.campaign = None
        self.map_act = None
        self.notices = []
        self.warned = set()
        self.dlg = None
        self.toast = ""
        self.tview = self.train = self.ce_view = self.end_view = None
        self.confirm_new = False
        self.menu_msg = ""
        self.screen_id = "menu"
        self.reset_ui()
        self.g.state = "campaign"

    def to_menu(self):
        """Sai para o menu principal do jogo (salva antes se ha campanha aberta)."""
        if self.campaign is not None and self.screen_id != "menu":
            self.persist()
        self.g.refresh_campaign_status()
        self.g.state = "menu"
        self.screen_id = "menu"
        self.campaign = None
        self.map_act = None
        self.dlg = None
        self.toast = ""
        self.tview = self.train = self.ce_view = self.end_view = None

    def go(self, screen):
        if screen == "hub":             # seguranca: codigo herdado do modo liga
            screen = "map"
        super().go(screen)
        if screen != "dialog":
            self.dlg = None
        if screen == "map":
            self.refresh_map()
        elif screen == "dialog":
            self.start_dialog(self.map_act)
        elif screen == "tourney":
            self.enter_tourney()
        elif screen == "chapter_end":
            self.enter_chapter_end()
        elif screen == "ending":
            self.enter_ending()

    def refresh_map(self):
        self.map_act = self.campaign.next_action() if self.campaign is not None else None

    def persist(self):
        """Unico ponto de gravacao: a CAMPANHA (nunca garage.save())."""
        if self.campaign is None:
            return False
        if self.campaign.save():
            self.g.refresh_campaign_status()
            return True
        draft = bool(self.campaign.chapter().get("draft"))
        if draft:
            self.msg = "Progresso salvo no início do capítulo."
            self.add_notice("Progresso salvo no início do capítulo (este capítulo ainda está em produção).",
                            "draft")
        else:
            self.msg = "Falha ao salvar."
            self.add_notice("Não foi possível salvar agora: vale o último ponto salvo.", "fail")
        return False

    def add_notice(self, text, key=None):
        """Aviso persistente no mapa (ate o OK). `key` evita repetir o mesmo aviso de save."""
        if key is not None:
            if key in self.warned:
                return
            self.warned.add(key)
        if text and text not in self.notices:
            self.notices.append(text)

    # ------------------------------------------------------------ menu da campanha
    def do_continue(self):
        c = C.Campaign.load()
        if c is None:
            self.status = C.Campaign.load_status()
            self.menu_msg = "Não foi possível carregar o save."
            return
        self.campaign = c
        self.sel = None
        self.cache = None
        self.notices = list(c.warnings) if c.repaired else []
        self.warned = set()
        self.go("map")

    def do_new(self):
        self.status = C.Campaign.load_status()        # reavalia: outra aba pode ter criado save
        if self.status != "none" and not self.confirm_new:
            self.confirm_new = True
            return
        if self.status == "bad":
            C.Campaign.load()                         # garante a copia em .bad antes de sobrescrever
        self.campaign = C.new_campaign(self.rng)
        self.cache = None
        self.notices = []
        self.warned = set()
        self.go("map")
        ok = self.persist()
        self.status = "ok" if ok else C.Campaign.load_status()
        self.confirm_new = False

    # ------------------------------------------------------------ garagem da campanha
    def draw_garage(self):
        super().draw_garage()
        ch = self.campaign.chapter()
        mine = int(round(self.info()["rating"]))
        low = int(round(ch["F_start"]))
        line = "Capítulo %s: Força recomendada %s | Sua Força %d" % (ch["id"], force_text(
            ch["F_start"], ch["F_end"]), mine)
        self.text(self.fit(line, 20, 700), 20, GREEN if mine >= low else GOLD, midleft=(24, 131))
        self.btn((510, 82, 150, 40), "TREINO", lambda: self.open_training("garage"), size=26,
                 color=(60, 80, 130))

    # ------------------------------------------------------------ mapa
    def do_story(self):
        """CONTINUAR HISTORIA: despacha pela proxima acao da campanha."""
        act = self.campaign.next_action()
        self.map_act = act
        self.go(KIND_SCREEN.get(act["kind"], "ending"))

    def back_to_map(self):
        self.go("map")

    def clear_notices(self):
        self.notices = []

    # ------------------------------------------------------------ eventos
    def handle_event(self, e):
        if self.screen_id == "dialog":
            return self.dialog_event(e)
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and not self.editing:
            sid = self.screen_id
            if sid == "menu" or sid == "map":
                return self.to_menu()
            if sid == "shop" and self.confirm_sell is not None:
                self.confirm_sell = None            # 1o Esc cancela a confirmacao de venda
                return
            if sid in STUB_SCREENS or (sid in ("garage", "shop") and not self.place_mode):
                return self.go("map")
        return super().handle_event(e)

    def update(self, dt):
        super().update(dt)
        self.pulse = (self.pulse + dt) % PULSE_PERIOD
        d = self.dlg
        if self.screen_id == "dialog" and d is not None and not d["paused"] and not d["confirm"]:
            d["t"] += dt
        if self.toast_t > 0:
            self.toast_t = max(0.0, self.toast_t - dt)

    # ------------------------------------------------------------ desenho
    def draw(self):
        if self.screen_id != "menu" and self.campaign is None:    # estado inconsistente: volta ao menu
            self.screen_id = "menu"
        super().draw()
        if self.toast_t > 0 and self.toast:
            f = self.g.font(22)
            w = f.size(self.toast)[0] + 28
            r = pygame.Rect(0, 0, w, 34)
            r.midtop = (W // 2, 44 if self.screen_id == "dialog" else 8)
            pygame.draw.rect(self.g.screen, (10, 28, 50), r, border_radius=8)
            pygame.draw.rect(self.g.screen, GOLD, r, 2, border_radius=8)
            self.text(self.toast, 22, GOLD, center=r.center)

    def draw_menu(self):
        cx = W // 2
        self.text("CAMPANHA", 64, TEXT, center=(cx, 60), shadow=True)
        self.text("A Garagem do Vô", 32, GOLD, center=(cx, 106))
        self.panel((250, 150, 600, 400))
        st = self.status
        if st == "bad":
            self.text("Save incompatível", 40, RED, center=(cx, 190))
            for k, line in enumerate(self.wrap(
                    "O save da campanha não pôde ser lido (versão nova ou arquivo danificado). "
                    "Ele não foi alterado e uma cópia foi guardada. NOVA CAMPANHA apaga esse save.",
                    24, 540)):
                self.text(line, 24, TEXT, center=(cx, 226 + k * 26))
        elif st == "ok":
            self.text("Save encontrado", 36, GREEN, center=(cx, 190))
            self.btn((cx - 150, 220, 300, 64), "CONTINUAR", self.do_continue, size=38,
                     color=(0, 140, 110))
        else:
            self.text("Nenhuma campanha salva", 32, DIM, center=(cx, 190))
        for k, line in enumerate(self.wrap(
                "Téo herdou do avô um aspirador quebrado e precisa vencer a Copa Interclasses "
                "para salvar o clube de robótica.", 24, 520)):
            self.text(line, 24, DIM, center=(cx, 316 + k * 26))
        if self.confirm_new:
            self.btn((cx - 200, 400, 400, 56), "CONFIRMAR: APAGAR O SAVE", self.do_new, size=28,
                     color=(170, 60, 50))
            self.btn((cx - 100, 466, 200, 40), "CANCELAR", self.do_cancel_confirm, size=24,
                     color=(60, 60, 70))
            self.text("O save atual será substituído.", 22, GOLD, center=(cx, 524))
        else:
            self.btn((cx - 150, 400, 300, 64), "NOVA CAMPANHA", self.do_new, size=34)
        if self.menu_msg:
            self.text(self.menu_msg, 22, GOLD, center=(cx, 524))
        self.btn((25, 652, 160, 40), "VOLTAR", self.to_menu, color=(60, 60, 70), size=26)

    def chapter_state(self, ch):
        """"done" (recompensa aplicada), "current" ou "future"."""
        rid = ch.get("reward")
        if rid and ("reward:%s" % rid) in self.campaign.done:
            return "done"
        return "current" if ch["id"] == self.campaign.ch else "future"

    def draw_map(self):
        cp = self.campaign
        scr = self.g.screen
        chs = story.CHAPTERS
        self.panel((20, 134, 1060, 270))
        pts = [(NODE_X0 + i * NODE_DX, NODE_Y[i % 2]) for i in range(len(chs))]
        states = [self.chapter_state(c) for c in chs]
        pygame.draw.lines(scr, LINE, False, pts, 5)
        for i in range(len(pts) - 1):                               # trecho concluido em verde
            if states[i] == "done":
                pygame.draw.line(scr, GREEN, pts[i], pts[i + 1], 5)
        pulse = abs(math.sin(self.pulse / PULSE_PERIOD * math.pi))
        for i, (ch, (x, y)) in enumerate(zip(chs, pts)):
            st = states[i]
            draft = bool(ch.get("draft"))
            fill = (20, 120, 70) if st == "done" else ((20, 70, 110) if st == "current" else (18, 36, 54))
            pygame.draw.circle(scr, fill, (x, y), NODE_R)
            pygame.draw.circle(scr, GREEN if st == "done" else (NEON if st == "current" else LINE),
                               (x, y), NODE_R, 3)
            if st == "done":
                pygame.draw.lines(scr, TEXT, False, [(x - 11, y), (x - 3, y + 9), (x + 12, y - 10)], 5)
            else:
                self.text(ch["id"], 34, TEXT if st == "current" else DIM, center=(x, y))
            if ch["id"] == cp.ch:                                   # anel pulsante (sem Surface)
                pygame.draw.circle(scr, GOLD, (x, y), NODE_R + 6 + int(5 * pulse), 3)
            col = TEXT if not draft else DIM
            yy = y + 44
            for line in self.wrap(ch["subtitle"], 22, NODE_DX - 8)[:2]:
                self.text(line, 22, col, center=(x, yy))
                yy += 20
            yy += 4
            for line in self.wrap(ch["local"], 18, NODE_DX - 8)[:2]:
                self.text(line, 18, DIM, center=(x, yy))
                yy += 17
            if draft:
                self.text("em breve", 18, GOLD, center=(x, yy + 4))
        # ---- painel do capitulo atual
        ch = cp.chapter()
        self.panel((20, 414, 1060, 268))
        self.text("%s - %s" % (ch["title"], ch["subtitle"]), 36, GOLD, topleft=(40, 428), shadow=True)
        self.text(self.fit(ch["local"], 26, 620), 26, TEXT, topleft=(40, 470))
        if ch.get("draft"):
            self.text("Este capítulo ainda está em produção: em breve.", 24, DIM, topleft=(40, 506))
        self.text("Força recomendada: %s" % force_text(ch["F_start"], ch["F_end"]), 28, TEXT,
                  topleft=(40, 546))
        mine = int(round(self.info()["rating"]))
        low = int(round(ch["F_start"]))
        self.text("Sua Força: %d" % mine, 28, GREEN if mine >= low else GOLD, topleft=(40, 580))
        act = self.map_act
        nxt = ""
        if act is not None:
            nxt = {"scene": "Próximo: cena", "match": "Próximo: partida (%s)" % act.get("stage_name", ""),
                   "chapter_end": "Próximo: fim do capítulo",
                   "end": "Próximo: em breve" if act.get("draft") else "Próximo: fim da campanha"}.get(
                       act["kind"], "")
        self.text(nxt, 24, DIM, topleft=(40, 616))
        self.btn((700, 446, 360, 76), "CONTINUAR HISTÓRIA", self.do_story, size=34, color=(0, 140, 110))
        self.text("Sucata: %d" % self.garage.scrap, 26, GOLD, midleft=(704, 552))
        self.btn((880, 532, 180, 40), "TREINO", lambda: self.open_training("map"), size=26,
                 color=(60, 80, 130))
        if self.notices:
            more = len(self.notices) - 1
            shown = self.notices[0] + (" (+%d aviso%s)" % (more, "s" if more > 1 else "") if more else "")
            for k, line in enumerate(self.wrap(shown, 20, 330)[:2]):
                self.text(line, 20, GOLD, topleft=(704, 586 + k * 20))
            self.btn((704, 634, 120, 34), "OK", self.clear_notices, size=22, color=(60, 60, 70))
        elif self.msg:
            for k, line in enumerate(self.wrap(self.msg, 22, 340)[:2]):
                self.text(line, 22, GOLD, topleft=(704, 590 + k * 24))

    # ------------------------------------------------------------ dialogo (passo 9)
    def start_dialog(self, act):
        """Prepara a cena de `act` (next_action kind scene). Cena invalida volta ao mapa; cena vazia
        (todas as falas filtradas por cond) e concluida e a campanha segue."""
        cp = self.campaign
        sid = act.get("id") if isinstance(act, dict) else None
        if cp is None or sid not in story.SCENES:
            self.dlg = None
            self.screen_id = "map"
            self.refresh_map()
            return
        main, choice = [], None
        for it in cp.scene_lines(sid):
            if isinstance(it, dict):
                choice = it if it.get("opts") else None
                break
            main.append(it)
        sc = story.SCENES[sid]
        d = {"sid": sid, "bg": sc.get("bg"), "cast": [c for c in sc.get("cast", ()) if c in story.CHARACTERS],
             "main": main, "choice": choice, "list": main, "i": 0, "mode": "say", "reply": False,
             "choice_idx": None, "fx": "", "final": False, "paused": False, "confirm": False,
             "t": 0.0, "moods": {}, "who": "narrador", "mood": "neutro", "lines": [], "imgs": [],
             "widths": [], "total": 0, "q": "", "col": TEXT}
        self.dlg = d
        portraits.get_background(d["bg"])           # pre-render fora do draw (uma Surface por cenario)
        if not main and choice is None:
            return self.dlg_finish(None)
        if main:
            self.dlg_load_line()
        else:
            self.dlg_to_choice()

    def dlg_load_line(self):
        d = self.dlg
        who, mood, text = d["list"][d["i"]][:3]
        f = self.g.font(TXT_SIZE)
        d["who"], d["mood"] = who, mood
        d["moods"][who] = mood
        d["lines"] = wrap_dialog(f, text)[:MAX_LINES]
        d["col"] = NARRATOR_TEXT if who == "narrador" else TEXT
        d["imgs"] = [self.g.text_img(ln, TXT_SIZE, d["col"]) for ln in d["lines"]]
        d["widths"] = [[f.size(ln[:n])[0] for n in range(len(ln) + 1)] for ln in d["lines"]]
        d["total"] = sum(len(ln) for ln in d["lines"])
        d["t"] = 0.0

    def dlg_to_choice(self):
        d = self.dlg
        d["mode"] = "choice"
        d["q"] = d["choice"]["q"]
        d["t"] = 0.0

    def dlg_chars(self):
        d = self.dlg
        return int(d["t"] * TYPE_CPS)

    def dlg_typing(self):
        d = self.dlg
        return d["mode"] == "say" and d["total"] > 0 and self.dlg_chars() < d["total"]

    def dlg_advance(self):
        """Clique/Enter/Espaco: completa a linha em digitacao; senao vai para a proxima fala."""
        d = self.dlg
        if d is None or d["mode"] != "say" or d["final"]:
            return
        if self.dlg_typing():
            d["t"] = d["total"] / TYPE_CPS + 0.001
            return
        d["i"] += 1
        if d["i"] < len(d["list"]):
            return self.dlg_load_line()
        if not d["reply"] and d["choice"] is not None:
            return self.dlg_to_choice()
        self.dlg_finish(d["choice_idx"])

    def dlg_pick(self, idx):
        d = self.dlg
        if d is None or d["mode"] != "choice" or d["final"]:
            return
        opts = d["choice"]["opts"]
        if not (0 <= idx < len(opts)):
            return
        d["choice_idx"] = idx
        d["fx"] = fx_text(opts[idx].get("fx"))
        reply = [r for r in (opts[idx].get("reply") or [])]
        if not reply:
            return self.dlg_finish(idx)
        d["mode"], d["reply"], d["list"], d["i"] = "say", True, reply, 0
        self.dlg_load_line()

    def dlg_finish(self, choice_idx):
        """Conclui a cena UMA vez: finish_scene -> persist (autosave) -> proxima acao."""
        d = self.dlg
        if d is None or d["final"]:
            return
        d["final"] = True
        sid = d["sid"]
        try:
            self.campaign.finish_scene(sid, choice_idx)
        except (KeyError, ValueError):
            try:
                self.campaign.finish_scene(sid)
            except (KeyError, ValueError):
                pass
        self.persist()
        self.dlg = None
        self.dlg_next()

    def dlg_next(self):
        """Despacha pela proxima acao da campanha (cena -> outra cena; partida -> torneio; etc.)."""
        try:
            act = self.campaign.next_action()
        except Exception:  # noqa: BLE001  (nunca quebra a UI)
            return self.go("map")
        self.map_act = act
        self.go(KIND_SCREEN.get(act["kind"], "map"))

    def dlg_skip(self):
        """PULAR CENA (apos confirmar): conclui a cena; com escolha, aplica a opcao 1 por padrao."""
        d = self.dlg
        if d is None:
            return
        ch = d["choice"]
        if ch is None or d["choice_idx"] is not None:
            idx = d["choice_idx"]
            self.toast = "Cena pulada."
        else:
            idx = 0
            fx = fx_text(ch["opts"][0].get("fx"))
            self.toast = "Cena pulada: escolha 1 aplicada" + (" (%s)" % fx if fx else "")
        self.toast_t = TOAST_SECONDS
        self.dlg_finish(idx)

    def dlg_set(self, key, value):
        if self.dlg is not None:
            self.dlg[key] = value

    def dlg_pause_save(self):
        """Mini-menu: salva e volta ao mapa (a cena nao e concluida: recomeca depois, sem duplicar fx)."""
        self.persist()
        self.go("map")

    def dialog_event(self, e):
        d = self.dlg
        if d is None:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return self.go("map")
            return RobotsUI.handle_event(self, e)
        modal = d["paused"] or d["confirm"]
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if d["confirm"]:
                    d["confirm"] = False
                else:
                    d["paused"] = not d["paused"]
                return
            if modal:
                return
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self.dlg_advance()
            if pygame.K_1 <= e.key <= pygame.K_3:
                return self.dlg_pick(e.key - pygame.K_1)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if any(en and r.collidepoint(e.pos) for r, _fn, en in self.buttons):
                return RobotsUI.handle_event(self, e)
            if not modal:
                self.dlg_advance()

    # ---- desenho do dialogo
    def draw_dialog(self):
        d = self.dlg
        scr = self.g.screen
        if d is None:
            self.text("Cena indisponível", 40, DIM, center=(W // 2, 300))
            self.btn((W // 2 - 150, 360, 300, 60), "VOLTAR AO MAPA", self.back_to_map, size=32,
                     color=(60, 80, 130))
            return
        scr.blit(portraits.get_background(d["bg"]), (0, 0))
        self.draw_stage(d)
        self.draw_dlg_box(d)
        modal = d["paused"] or d["confirm"]
        if not modal:
            self.btn((938, 10, 132, 30), "PULAR CENA", lambda: self.dlg_set("confirm", True), size=20,
                     color=(30, 44, 74))
        if d["paused"]:
            self.draw_pause(d)
        elif d["confirm"]:
            self.draw_confirm_skip(d)

    def stage_cast(self, d):
        cast = list(d["cast"])
        who = d["who"]
        if who != "narrador" and who in story.CHARACTERS and who not in cast:
            cast.append(who)
        return cast

    def draw_stage(self, d):
        scr = self.g.screen
        cast = self.stage_cast(d)
        n = len(cast)
        if n == 0:
            return
        xs = [550] if n == 1 else [190 + i * (720 // (n - 1)) for i in range(n)]
        speaker = d["who"] if d["mode"] == "say" else None
        narr = speaker == "narrador" or speaker is None
        talking = self.dlg_typing()
        order = sorted(range(n), key=lambda i: cast[i] == speaker)       # o falante por ultimo (na frente)
        for i in order:
            cid = cast[i]
            on = cid == speaker
            k = 1.0 if on else (0.72 if narr else 0.5)
            mood = d["mood"] if on else d["moods"].get(cid, "robo" if cid == "ze" else "neutro")
            if on:
                col = tuple(story.CHARACTERS[cid]["color"])
                pygame.draw.ellipse(scr, portraits.lerp((14, 26, 52), col, 0.55), (xs[i] - 86, 452, 172, 26))
                pygame.draw.ellipse(scr, col, (xs[i] - 86, 452, 172, 26), 2)
            bob = -abs(int(4 * math.sin(d["t"] * 13))) if (on and talking) else 0
            portraits.draw_character(scr, cid, mood, xs[i], 466, 40, k, bob)

    def draw_dlg_box(self, d):
        scr = self.g.screen
        who = d["who"] if d["mode"] == "say" else None
        ch = story.CHARACTERS.get(who) if who else None
        col = tuple(ch["color"]) if ch else NEON
        pygame.draw.rect(scr, (8, 18, 36), DLG_BOX, border_radius=14)
        pygame.draw.rect(scr, col, DLG_BOX, 2, border_radius=14)
        name = ch["name"] if ch else ("ESCOLHA" if who is None else str(who).upper())
        f = self.g.font(26)
        tw = f.size(name)[0] + 30
        tag = pygame.Rect(TXT_X if who else 60, 462, tw, 32)
        pygame.draw.rect(scr, col, tag, border_radius=8)
        pygame.draw.rect(scr, DARK, tag, 2, border_radius=8)
        self.text(name, 26, DARK, center=tag.center)
        if d["mode"] == "choice":
            return self.draw_choice(d)
        portraits.draw_bust(scr, PORTRAIT_RECT, d["who"], d["mood"])
        rem = self.dlg_chars()
        for i, img in enumerate(d["imgs"]):
            ln = d["lines"][i]
            n = min(len(ln), rem)
            if n <= 0:
                break
            rem -= n
            wpx = img.get_width() if n >= len(ln) else min(img.get_width(), d["widths"][i][n] + 1)
            scr.blit(img, (TXT_X, TXT_Y + i * LINE_H), pygame.Rect(0, 0, wpx, img.get_height()))
        if d["fx"] and d["reply"]:
            self.text(d["fx"], 22, GOLD, midright=(1054, 494))
        if not self.dlg_typing() and int(d["t"] * 2.5) % 2 == 0:
            pygame.draw.polygon(scr, NEON, [(1024, 632), (1048, 632), (1036, 648)])

    def draw_choice(self, d):
        self.text(self.fit(d["q"], 28, 960), 28, TEXT, midleft=(60, 510))
        for i, o in enumerate(d["choice"]["opts"][:3]):
            self.btn((60, 530 + i * 46, 980, 40), "%d   %s" % (i + 1, o["t"]), lambda i=i: self.dlg_pick(i),
                     size=28, color=(0, 100, 150))

    def draw_pause(self, d):
        self.panel((300, 190, 500, 250), fill=(8, 18, 36))
        self.text("PAUSA", 44, TEXT, center=(W // 2, 236))
        self.btn((350, 280, 400, 56), "CONTINUAR", lambda: self.dlg_set("paused", False), size=30,
                 color=(0, 140, 110))
        self.btn((350, 352, 400, 56), "SALVAR E VOLTAR AO MAPA", self.dlg_pause_save, size=28,
                 color=(60, 80, 130))

    def draw_confirm_skip(self, d):
        self.panel((250, 170, 600, 290), fill=(8, 18, 36))
        self.text("Pular esta cena?", 40, TEXT, center=(W // 2, 214))
        ch = d["choice"]
        if ch is not None and d["choice_idx"] is None:
            msg = "A cena tem uma escolha: a opção 1 será escolhida automaticamente."
            for k, ln in enumerate(self.wrap(msg, 24, 540)):
                self.text(ln, 24, GOLD, center=(W // 2, 258 + k * 26))
            self.text(self.fit("1: " + ch["opts"][0]["t"], 24, 540), 24, DIM, center=(W // 2, 322))
        else:
            self.text("A cena será concluída agora.", 24, DIM, center=(W // 2, 270))
        self.btn((290, 360, 250, 56), "PULAR", self.dlg_skip, size=30, color=(170, 90, 50))
        self.btn((560, 360, 250, 56), "CANCELAR", lambda: self.dlg_set("confirm", False), size=30,
                 color=(60, 60, 70))

    # ================================================================ TORNEIO (passo 10)
    def sync_act(self, kind):
        """Recalcula a proxima acao; se nao for `kind`, despacha para a tela certa e devolve None."""
        try:
            act = self.campaign.next_action()
        except Exception:  # noqa: BLE001  (nunca quebra a UI)
            self.screen_id = "map"
            self.map_act = None
            return None
        self.map_act = act
        if act["kind"] != kind:
            self.go(KIND_SCREEN.get(act["kind"], "map"))
            return None
        return act

    def enter_tourney(self):
        self.tview = None
        act = self.sync_act("match")
        if act is not None:
            self.tview = self.build_tview(act)

    def build_tview(self, act):
        cp = self.campaign
        tour = cp.tour
        tr = story.TOURNAMENTS[act["tournament"]]
        single = tr["format"] == "single"
        v = {"single": single, "title": cp.chapter()["subtitle"], "local": tr["local"],
             "label": stage_label(act["stage"], single), "rows": [], "ko": [],
             "names": [e["name"] for e in act["opp"]["squad"]]}
        if not single:
            v["rows"] = cp.group_table()
            res = {r[0]: r for r in tour["results"]}
            for st in C.stages_of(tr):
                if st[0] == "G":
                    continue
                v["ko"].append({"stage": st, "name": story.TEAMS[stage_team(tr, st)]["name"],
                                "res": res.get(st), "cur": st == act["stage"]})
        return v

    def fresh_match(self):
        """Partida pendente recalculada na hora do clique (a garagem pode ter mudado)."""
        if self.campaign is None:
            return None
        return self.sync_act("match")

    def do_watch_match(self):
        act = self.fresh_match()
        if act is None:
            return
        self.pending = {"act": act, "training": False}
        self.g.start_robot_match(act["home"], act["away"], on_done=self.match_done, return_state="campaign")

    def do_sim_match(self):
        act = self.fresh_match()
        if act is None:
            return
        self.pending = None
        try:
            out = self.campaign.simulate_current()
        except (RuntimeError, ValueError, KeyError):
            self.go("map")
            return
        self.finish_result(out, act, [], True)

    def match_done(self, score, events):
        """Callback de Game.start_robot_match (o Game ja voltou ao estado "campaign")."""
        pend, self.pending = self.pending, None
        cp = self.campaign
        if cp is None or not isinstance(pend, dict) or pend.get("training"):
            if cp is not None:
                self.go("map")
            return
        try:
            out = cp.record_match(int(score[0]), int(score[1]), events=events, simulated=False)
        except (RuntimeError, ValueError, KeyError):
            self.go("map")
            return
        self.finish_result(out, pend["act"], events, False)

    # ---- treino
    def open_training(self, back):
        if self.campaign is None:
            return
        self.train_back = back
        self.train = self.campaign.training_cfg()
        self.go("training")

    def do_watch_train(self):
        if self.train is None:
            return
        self.pending = {"act": self.train, "training": True}
        self.g.start_robot_match(self.train["home"], self.train["away"], on_done=self.train_done,
                                 return_state="campaign")

    def do_sim_train(self):
        cp = self.campaign
        tr = self.train
        if cp is None or tr is None:
            return
        my, opp = C.sim_match(cp.garage.rating(), tr["O"], cp._rng("trainsim"))
        out = cp.record_training(my, opp, simulated=True)
        self.finish_result(out, tr, [], True, training=True)

    def train_done(self, score, events):
        pend, self.pending = self.pending, None
        cp = self.campaign
        if cp is None:
            return
        if not isinstance(pend, dict) or not pend.get("training"):
            self.go("map")
            return
        out = cp.record_training(int(score[0]), int(score[1]), events=events, simulated=False)
        self.finish_result(out, pend["act"], events, False, training=True)

    # ---- resultado (tela "round" herdada: draw_round_body + cabecalho proprio)
    def finish_result(self, out, act, events, simulated, training=False):
        cp = self.campaign
        gg = self.garage
        rew = out["rewards"]
        by_id = {r["id"]: r["name"] for r in gg.robots}
        starters = set(gg.lineup)
        order = [r for r in gg.robots if r["id"] in starters] + [r for r in gg.robots if r["id"] not in starters]
        rows = []
        for r in order:
            gained = rew["levels"].get(r["id"], 0)
            rows.append((r["name"], r["id"] in starters, rew["xp"].get(r["id"], 0),
                         r["level"] - gained, r["level"], gained > 0))
        goals = []
        for e in events or ():
            nm = e.get("name") or by_id.get(e.get("pid"), "")
            goals.append((e.get("min", 0), nm, e.get("team", 0), bool(e.get("own"))))
        eq = sum(1 for r in gg.lineup_robots() for v in r["slots"].values() if v is not None)
        self.cache = None
        base = G.team_rating(gg.lineup_robots(), {})
        opp = act["opp"]
        self.round_info = {
            "camp": True, "training": training, "teams": ({"name": gg.team["name"], "color": tuple(gg.team["color"])},
                                                          {"name": opp["name"], "color": tuple(opp["color"])}),
            "score": (out["my"], out["opp"]), "sim": simulated, "fin": False, "rew": rew, "rows": rows,
            "goals": goals, "equipped": eq, "rating": self.info()["rating"], "base": base,
            "stage": out.get("stage"), "tname": cp.chapter()["subtitle"], "pen": out.get("pen"),
            "outcome": out.get("outcome"), "boss": bool(out.get("boss")), "group_pos": out.get("group_pos"),
            "pity": cp.pity, "single": out.get("outcome") == "done"}
        self.persist()
        self.go("round")

    def round_continue(self):
        info = self.round_info
        if info is not None and info.get("training"):
            return self.back_from_training()
        self.dlg_next()

    def outcome_text(self, info):
        """(mensagem, cor) do resultado conforme o desfecho do estagio."""
        if info.get("training"):
            return "Treino concluído - o torneio não avançou", DIM
        oc, st = info.get("outcome"), info.get("stage")
        if oc == "champion":
            return "CAMPEÃO!", GOLD
        if oc == "elim":
            return "Eliminado no grupo - o torneio recomeça", RED
        if oc == "retry":
            if info.get("boss") and info.get("pity"):
                return "Derrota - tente de novo (o chefe perde %d de Força)" % (info["pity"] * C.PITY_STEP), RED
            return "Derrota - tente de novo", RED
        if oc == "done":
            return "Peneira concluída!", GREEN
        if st in ("G1", "G2"):
            return "Rodada do grupo concluída", TEXT
        if st == "G3":
            return "Você avançou! (%dº no grupo)" % (info.get("group_pos") or 0), GREEN
        return "Você avançou!", GREEN

    def draw_round_header(self, info):
        if not info.get("camp"):
            return super().draw_round_header(info)
        scr = self.g.screen
        th, ta = info["teams"]
        if info.get("training"):
            title = "TREINO"
        else:
            title = "%s - %s" % (stage_label(info["stage"], info.get("single")), info["tname"])
        if info["sim"]:
            title += "  (simulada)"
        self.text(self.fit(title, 30, 1040), 30, TEXT, center=(W // 2, 20), shadow=True)
        msg, col = self.outcome_text(info)
        self.text(msg, 26, col, center=(W // 2, 46), shadow=True)
        self.panel((20, 62, 1060, 100))
        hg, ag = info["score"]
        for team, cx, left in ((th, 280, True), (ta, 820, False)):
            pygame.draw.rect(scr, tuple(team["color"]), (cx - 230 if left else cx + 218, 82, 12, 60), border_radius=3)
            self.text(self.fit(team["name"], 32, 400), 32, TEXT, center=(cx, 108), shadow=True)
        self.text("%d  x  %d" % (hg, ag), 60, GOLD, center=(W // 2, 100), shadow=True)
        res = {"w": ("VITÓRIA", GREEN), "d": ("EMPATE", GOLD), "l": ("DERROTA", RED)}[info["rew"]["result"]]
        line = res[0]
        if info.get("pen"):
            line += "  (%d-%d nos pênaltis)" % tuple(info["pen"])
        self.text(line, 22, res[1], center=(W // 2, 146))

    # ---- desenho do torneio
    def draw_tourney(self):
        v = self.tview
        act = self.map_act or {}
        if v is None or act.get("kind") != "match":
            self.text("Partida indisponível", 40, DIM, center=(W // 2, 300))
            self.btn((W // 2 - 150, 360, 300, 60), "VOLTAR AO MAPA", self.back_to_map, size=32,
                     color=(60, 80, 130))
            return
        self.text(self.fit(v["title"], 34, 640), 34, GOLD, topleft=(24, 130), shadow=True)
        self.text(self.fit(v["local"], 22, 400), 22, DIM, midright=(W - 24, 148))
        if v["single"]:
            self.panel((20, 172, 1060, 190))
            self.text("PENEIRA", 32, TEXT, topleft=(44, 188), shadow=True)
            for k, line in enumerate(self.wrap(
                    "Partida única de treino contra o Clube do Xadrez. Qualquer resultado conclui a "
                    "peneira e a história segue; vencer ou perder rende sucata e experiência.", 26, 980)):
                self.text(line, 26, DIM, topleft=(44, 236 + k * 30))
        else:
            self.draw_group_panel(v)
            self.draw_bracket_panel(v, act)
        self.draw_match_panel(v, act)

    def draw_group_panel(self, v):
        scr = self.g.screen
        self.panel((20, 172, 520, 190))
        self.text("GRUPO", 22, GOLD, topleft=(38, 180))
        for lab, x in (("PTS", 300), ("J", 340), ("V", 380), ("E", 420), ("D", 460), ("SG", 515)):
            self.text(lab, 20, DIM, midright=(x, 206))
        for k, row in enumerate(v["rows"]):
            y = 218 + k * 34
            me = row["idx"] == 0
            if me:
                pygame.draw.rect(scr, HILITE, (28, y, 504, 30), border_radius=6)
                pygame.draw.rect(scr, GOLD, (28, y, 504, 30), 2, border_radius=6)
            self.text(str(k + 1), 22, GOLD if me else DIM, midright=(52, y + 15))
            pygame.draw.rect(scr, tuple(row["color"]), (62, y + 6, 12, 18), border_radius=3)
            self.text(self.fit(row["name"], 22, 190), 22, TEXT if me else (200, 215, 205), midleft=(82, y + 15))
            for val, x in ((row["pts"], 300), (row["p"], 340), (row["w"], 380), (row["d"], 420),
                           (row["l"], 460), (row["gd"], 515)):
                self.text(("%+d" % val) if x == 515 and val else str(val), 22,
                          GOLD if (me and x == 300) else TEXT, midright=(x, y + 15))

    def draw_bracket_panel(self, v, act):
        scr = self.g.screen
        px, py, pw = 556, 172, 524
        self.panel((px, py, pw, 190))
        self.text("CHAVEAMENTO", 22, GOLD, topleft=(px + 18, py + 8))
        ko = v["ko"]
        n = len(ko)
        gap = 28
        cw = min(190, (pw - 28 - (n - 1) * gap) // n)
        x0 = px + (pw - (n * cw + (n - 1) * gap)) // 2
        bh = 52
        yu, yo = py + 50, py + 112
        ymid = (yu + yo) // 2
        me_name = self.garage.team["name"]
        for i, b in enumerate(ko):
            x = x0 + i * (cw + gap)
            last = i == n - 1
            label = STAGE_TITLES[b["stage"]] + (" (CHEFE)" if last else "")
            self.text(label, 18, RED if last else DIM, center=(x + cw // 2, py + 40))
            ys = [ymid - bh // 2] if last else [yu, yo]
            for j, y in enumerate(ys):
                user_box = last or j == 0
                r = pygame.Rect(x, y, cw, bh)
                res = b["res"] if user_box else None
                if user_box and b["cur"]:
                    edge, wd = (0, 230, 255), 3
                elif res is not None:
                    edge, wd = GREEN, 2
                else:
                    edge, wd = LINE, 2
                pygame.draw.rect(scr, BOX_BG, r, border_radius=6)
                pygame.draw.rect(scr, edge, r, wd, border_radius=6)
                if user_box:
                    names = (me_name, b["name"])
                    cols = (GOLD, TEXT if res is None or res[1] >= res[2] else DIM)
                    sc = ("", "")
                    if res is not None:
                        pen = res[3] or res[4]
                        sc = ("%d%s" % (res[1], " (%d)" % res[3] if pen else ""),
                              "%d%s" % (res[2], " (%d)" % res[4] if pen else ""))
                else:
                    names, cols, sc = ("?", "?"), (DIM, DIM), ("", "")
                for k in range(2):
                    yy = y + 14 + k * 24
                    self.text(self.fit(names[k], 20, cw - 52), 20, cols[k], midleft=(x + 8, yy))
                    if sc[k]:
                        self.text(sc[k], 20, TEXT, midright=(x + cw - 8, yy))
            if not last:                                    # liga ao proximo estagio
                nx = x + cw + gap
                nlast = i + 1 == n - 1
                for ya in (yu, yo):
                    yc = ya + bh // 2
                    if nlast:
                        mx = x + cw + gap // 2
                        pygame.draw.lines(scr, LINE, False, [(x + cw, yc), (mx, yc), (mx, ymid), (nx, ymid)], 2)
                    else:
                        pygame.draw.line(scr, LINE, (x + cw, yc), (nx, yc), 2)

    def draw_match_panel(self, v, act):
        scr = self.g.screen
        self.panel((20, 372, 1060, 308))
        self.text(v["label"], 44, GOLD, topleft=(40, 384), shadow=True)
        if act.get("boss"):
            r = pygame.Rect(0, 0, 90, 28)
            r.midleft = (60 + self.g.font(44).size(v["label"])[0], 404)
            pygame.draw.rect(scr, (150, 40, 40), r, border_radius=6)
            self.text("CHEFE", 22, TEXT, center=r.center)
        if not v["single"]:
            self.text("Tentativa %d" % (act["attempt"] + 1), 24, DIM, topleft=(40, 432))
        mine = int(round(act["user_F"]))
        opp = act["opp"]
        enough = mine >= int(round(act["F_rec"]))
        # --- cartoes dos dois times
        gg = self.garage
        for x, name, col, sub, subc in (
                (40, gg.team["name"], gg.team["color"], "Sua Força: %d" % mine, GREEN if enough else GOLD),
                (400, opp["name"], opp["color"], "Força do rival: %d" % act["O"], TEXT)):
            pygame.draw.rect(scr, tuple(col), (x, 476, 14, 50), border_radius=3)
            self.text(self.fit(name, 32, 270), 32, TEXT, topleft=(x + 26, 474), shadow=True)
            self.text(sub, 24, subc, topleft=(x + 26, 506))
        self.text("x", 32, DIM, center=(366, 502))
        self.text("Força recomendada: %d" % int(round(act["F_rec"])), 26, TEXT, topleft=(40, 546))
        if act.get("boss") and act.get("pity", 0) > 0:
            self.text("Ajuda do chefe: -%d de Força" % (act["pity"] * C.PITY_STEP), 24, GREEN, topleft=(40, 580))
        self.text(self.fit("Robôs: " + ", ".join(v["names"]), 20, 640), 20, DIM, topleft=(40, 614))
        if v["single"]:
            self.text("Peneira: qualquer resultado conclui.", 20, DIM, topleft=(40, 640))
        else:
            self.text("Grupo: os 2 primeiros avançam. Mata-mata: empate vai para os pênaltis.", 20, DIM,
                      topleft=(40, 640))
        self.btn((700, 390, 360, 76), "ASSISTIR", self.do_watch_match, size=36)
        self.btn((700, 478, 360, 56), "SIMULAR", self.do_sim_match, size=30, color=(60, 80, 130))
        self.btn((700, 546, 360, 50), "TREINO", lambda: self.open_training("tourney"), size=26,
                 color=(60, 80, 130))
        self.btn((700, 608, 360, 44), "VOLTAR AO MAPA", self.back_to_map, size=24, color=(60, 60, 70))

    # ---- treino
    def tab_active(self, tid):
        return super().tab_active(tid) or (tid == "map" and self.screen_id in FRAME_EXTRA)

    def back_from_training(self):
        if self.train_back == "tourney":
            return self.dlg_next()
        self.go("garage" if self.train_back == "garage" else "map")

    def draw_training(self):
        tr = self.train
        if tr is None:
            self.back_to_map()
            return
        cx = W // 2
        scr = self.g.screen
        self.text("TREINO", 52, TEXT, center=(cx, 160), shadow=True)
        self.panel((250, 196, 600, 250))
        opp = tr["opp"]
        pygame.draw.rect(scr, tuple(opp["color"]), (290, 222, 14, 50), border_radius=3)
        self.text(self.fit(opp["name"], 36, 500), 36, TEXT, topleft=(316, 218), shadow=True)
        self.text("Força do rival: %d" % tr["O"], 26, DIM, topleft=(316, 256))
        mine = int(round(self.info()["rating"]))
        self.text("Sua Força: %d" % mine, 28, GREEN if mine >= tr["O"] else GOLD, topleft=(290, 306))
        for k, line in enumerate(self.wrap(
                "Partida livre: não avança o torneio nem a história. A recompensa é menor que a de "
                "uma partida valendo.", 22, 540)):
            self.text(line, 22, DIM, topleft=(290, 350 + k * 26))
        self.btn((250, 470, 600, 64), "ASSISTIR TREINO", self.do_watch_train, size=34)
        self.btn((250, 546, 600, 50), "SIMULAR TREINO", self.do_sim_train, size=28, color=(60, 80, 130))
        self.btn((250, 610, 600, 42), "VOLTAR", self.back_from_training, size=24, color=(60, 60, 70))

    # ================================================================ FIM DE CAPITULO
    def enter_chapter_end(self):
        self.ce_view = None
        act = self.sync_act("chapter_end")
        if act is None:
            return
        cp = self.campaign
        ch = cp.chapter()
        rw = story.REWARDS.get(ch.get("reward")) or {}
        rep = act.get("report") or {}
        v = {"title": "%s - %s" % (ch["title"], ch["subtitle"]), "scrap": int(rw.get("scrap", 0)),
             "piece": None, "recruits": [], "unlocked": list(rw.get("unlock", ())),
             "xp_hero": int(rw.get("xp_hero", 0)), "xp_team": int(rw.get("xp_team", 0)),
             "equip": None, "warnings": list(act.get("warnings") or rep.get("warnings") or [])}
        pc = rw.get("piece")
        if pc:
            v["piece"] = ("%s %s" % (pc["model"], P.RAR_NAMES[pc["rar"]]), P.RAR_COLORS[pc["rar"]])
            if rep.get("applied") and rep.get("piece") is None:
                v["warnings"].append("Inventário cheio: a peça não foi entregue.")
        eq = rw.get("equip_hero_piece")
        if eq:
            v["equip"] = (rep.get("equip") or "%s %s" % (eq["model"], P.RAR_NAMES[eq["rar"]]),
                          P.RAR_COLORS[eq["rar"]])
        for sp in rw.get("recruits", ()):
            v["recruits"].append((sp["name"], sp["chassis"], int(sp.get("level", 1)),
                                  tuple(sp.get("paint") or (200, 200, 200))))
        self.ce_view = v

    def do_chapter_continue(self):
        warns = list(self.ce_view["warnings"]) if self.ce_view else []
        self.campaign.advance_chapter()
        self.go("map")
        for w in warns:                          # ex.: recruta substituiu um reserva: fica no mapa ate o OK
            self.add_notice(w)
        self.persist()

    def draw_chapter_end(self):
        v = self.ce_view
        cx = W // 2
        scr = self.g.screen
        if v is None:
            self.text("Capítulo indisponível", 40, DIM, center=(cx, 300))
            self.btn((cx - 150, 360, 300, 60), "VOLTAR AO MAPA", self.back_to_map, size=32,
                     color=(60, 80, 130))
            return
        self.text("CAPÍTULO CONCLUÍDO", 52, TEXT, center=(cx, 44), shadow=True)
        self.text(self.fit(v["title"], 30, 900), 30, GOLD, center=(cx, 90))
        self.panel((120, 118, 860, 456))
        y = 132
        x = 150
        self.text("RECOMPENSAS DO CAPÍTULO", 22, GOLD, topleft=(x, y))
        y += 32
        if v["scrap"]:
            self.text("Sucata: +%d" % v["scrap"], 30, GOLD, topleft=(x, y), shadow=True)
            y += 40
        if v["piece"]:
            self.text("Peça:", 24, DIM, topleft=(x, y + 4))
            self.text(self.fit(v["piece"][0], 30, 640), 30, v["piece"][1], topleft=(x + 70, y), shadow=True)
            y += 40
        if v["equip"]:
            self.text("Equipada no herói:", 24, DIM, topleft=(x, y + 4))
            self.text(self.fit(v["equip"][0], 30, 520), 30, v["equip"][1], topleft=(x + 220, y), shadow=True)
            y += 40
        if v["xp_hero"] or v["xp_team"]:
            parts = []
            if v["xp_hero"]:
                parts.append("herói +%d XP" % v["xp_hero"])
            if v["xp_team"]:
                parts.append("equipe +%d XP" % v["xp_team"])
            self.text("Experiência: " + "   ".join(parts), 26, (0, 210, 240), topleft=(x, y + 2))
            y += 38
        if v["unlocked"]:
            self.text("Chassis desbloqueados:", 24, DIM, topleft=(x, y + 4))
            self.text(self.fit(", ".join(v["unlocked"]), 30, 500), 30, GREEN, topleft=(x + 250, y), shadow=True)
            y += 40
        if v["recruits"]:
            self.text("NOVOS RECRUTAS", 22, GOLD, topleft=(x, y + 4))
            y += 32
            for name, chassis, lvl, paint in v["recruits"]:
                pygame.draw.rect(scr, paint, (x, y + 2, 14, 28), border_radius=3)
                self.text(self.fit(name, 30, 300), 30, TEXT, topleft=(x + 26, y), shadow=True)
                self.text("%s  -  Nv %d" % (chassis, lvl), 26, DIM, topleft=(x + 340, y + 3))
                y += 36
        if v["warnings"]:
            y += 10
            self.text("AVISOS", 22, GOLD, topleft=(x, y))
            y += 28
        for line in v["warnings"][:3]:
            for t in self.wrap(line, 22, 800)[:2]:
                self.text(t, 22, GOLD, topleft=(x, y))
                y += 24
            y += 4
        self.btn((cx - 150, 596, 300, 64), "CONTINUAR", self.do_chapter_continue, size=36, color=(0, 140, 110))

    # ================================================================ FIM DA CAMPANHA
    def count_keys(self, hook):
        n = 0
        done = self.campaign.done
        for tr in story.TOURNAMENTS.values():
            sid = tr["hooks"].get(hook)
            if sid:
                pre = sid + "#"
                n += sum(1 for k in done if k.startswith(pre))
        return n

    def enter_ending(self):
        self.end_view = None
        act = self.sync_act("end")
        if act is None:
            return
        cp = self.campaign
        st = cp.stats
        self.end_view = {"draft": bool(act.get("draft")), "matches": st["matches"], "sims": st["sims"],
                         "trained": st["trained"], "titles": cp.garage.stats["titles"],
                         "boss_losses": self.count_keys("lose"), "elims": self.count_keys("elim"),
                         "rating": int(round(cp.garage.rating()))}

    def draw_ending(self):
        v = self.end_view
        cx = W // 2
        if v is None:
            self.text("Fim indisponível", 40, DIM, center=(cx, 300))
            self.btn((cx - 150, 360, 300, 60), "VOLTAR AO MAPA", self.back_to_map, size=32,
                     color=(60, 80, 130))
            return
        if v["draft"]:
            self.text("EM BREVE", 60, TEXT, center=(cx, 90), shadow=True)
            self.text("A Garagem do Vô", 30, GOLD, center=(cx, 140))
            self.panel((200, 180, 700, 300))
            for k, line in enumerate(self.wrap("Os próximos capítulos ainda estão em produção.", 34, 640)):
                self.text(line, 34, GOLD, center=(cx, 232 + k * 38), shadow=True)
            self.text("Você concluiu tudo o que existe até agora.", 24, TEXT, center=(cx, 330))
            self.text("Partidas jogadas: %d    Títulos: %d" % (v["matches"], v["titles"]), 24, DIM,
                      center=(cx, 380))
            self.text("O TREINO continua livre no mapa.", 22, DIM, center=(cx, 430))
        else:
            self.text("CAMPANHA CONCLUÍDA", 56, GOLD, center=(cx, 80), shadow=True)
            self.text("A Garagem do Vô", 30, TEXT, center=(cx, 130))
            self.panel((200, 170, 700, 350))
            self.text("ESTATÍSTICAS", 22, GOLD, topleft=(230, 184))
            rows = (("Partidas jogadas", "%d (%d simuladas)" % (v["matches"], v["sims"])),
                    ("Títulos conquistados", str(v["titles"])),
                    ("Derrotas contra chefes", str(v["boss_losses"])),
                    ("Eliminações no grupo", str(v["elims"])),
                    ("Treinos", str(v["trained"])),
                    ("Força final do time", str(v["rating"])))
            for k, (a, b) in enumerate(rows):
                y = 226 + k * 44
                self.text(a, 28, DIM, midleft=(230, y))
                self.text(b, 30, TEXT, midright=(870, y), shadow=True)
            self.text("O TREINO continua livre no mapa.", 22, DIM, center=(cx, 500))
        self.btn((cx - 150, 560, 300, 60), "VOLTAR AO MAPA", self.back_to_map, size=32, color=(60, 80, 130))
