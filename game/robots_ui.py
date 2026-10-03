# -*- coding: utf-8 -*-
"""Telas do Modo Robôs (imediate-mode, mouse), no padrão de career_ui.py.

Telas (screen_id): menu, hub (aba LIGA), garage (aba GARAGEM), shop (aba LOJA),
bench (bancada, com cabeçalho; aba GARAGEM destacada), round, league_end.
round (resultado da rodada) e league_end (fim da liga) fecham o fluxo de partida.
Regras de performance: nunca criar pygame.Surface no draw; só Font(None) e glifos Latin-1.
"""
import random

import pygame

import garage as G
import parts as P
import robot_league as RL
import robots
from career_ui import (BG, BTN, DIM, GOLD, GREEN, LINE, PANEL, RED, TEXT, W,
                       CareerUI, ovr_color)

TABS = [("hub", "LIGA"), ("garage", "GARAGEM"), ("shop", "LOJA")]
FRAME_SCREENS = tuple(t for t, _ in TABS)          # telas com cabeçalho + abas
END_SCREENS = ("round", "league_end")
SCREENS = ("menu",) + FRAME_SCREENS + ("bench",) + END_SCREENS
SLOT_LABELS = {"motor": "MOTOR", "bateria": "BATERIA", "parachoque": "PARA-CHOQUE",
               "chutador": "CHUTADOR", "succao": "SUCÇÃO", "sensor": "SENSOR", "chip": "CHIP"}
FUN_NAMES = ("Zé Parafuso", "Chuta-Bolt", "Mini Hulk", "Robozilla", "Fio Solto", "Sir Pixel",
             "Dona Bateria", "Bip Bop", "Lata Veia", "Cabo Zero", "Faísca Jr", "Mecha Fofo",
             "Turbinado", "Zunido", "Ferrugento", "Pé de Ferro")
PIECE_ROWS = 6
SHOP_ROWS = 10
ROLE_PT = {"GK": "goleiro", "DEF": "defensor", "MID": "meia", "ATT": "atacante"}
TEAM_NAMES = ("Meu Time", "Os Cabos Soltos", "Pó de Ferro", "Aspira Mais", "Sucata FC",
              "Turbo Rodinhas", "Faísca Elétrica", "Zumbidos", "Engrenagem", "Rolo Compressor")
ATT_LABELS = ("VEL", "ACE", "CHU", "CTR", "DEF", "VIS", "BAT", "QI")
ROW_H, ROW_PITCH = 40, 44
SEL_COLOR = (0, 230, 255)
NAME_FIELD = pygame.Rect(748, 482, 185, 34)
NAME_MAX = G.NAME_MAX_ROBOT


def attr_color(v):
    """Cor da barra de atributo por faixa."""
    if v >= 75:
        return GREEN
    if v >= 60:
        return (190, 235, 120)
    if v >= 45:
        return (240, 220, 100)
    return (240, 150, 90)


class RobotsUI(CareerUI):
    """Herda só os helpers de desenho de CareerUI (text/fit/wrap/panel/hit/btn);
    construtor, eventos e desenho são próprios."""
    # textos da loja (subclasses, como a Campanha, trocam por atributo)
    SHOP_EMPTY_TEXT = "Sem peças nesse slot. A loja é reposta a cada rodada da liga."
    SHOP_STOCK_FMT = "Estoque: %d peça(s). Reposto a cada rodada da liga."

    def __init__(self, game):  # noqa: super().__init__ intencionalmente não chamado
        self.g = game
        self.garage = None
        self.rng = random.Random()
        self.screen_id = "menu"
        self.buttons = []
        self.status = "none"
        self.team_name = TEAM_NAMES[0]
        self.confirm_new = False
        self.menu_msg = ""
        # Ganchos para subclasses (ex.: CampaignUI troca a aba LIGA por HISTÓRIA); defaults = constantes
        self.tabs = list(TABS)
        self.frame_screens = tuple(FRAME_SCREENS)
        self.screens = tuple(SCREENS)
        self.reset_ui()

    # ------------------------------------------------------------ navegação
    def reset_ui(self):
        self.sel = None            # id do robô selecionado (garagem)
        self.place_mode = False    # ESCALAR: aguardando o clique num slot de titular
        self.msg = ""
        self.cache = None          # {rid: (attrs, ovr)} + rating; invalidado em toda ação
        self.bench_rid = None
        self.sel_slot = None       # bancada: slot selecionado
        self.sel_piece = None      # bancada: id da peça livre selecionada
        self.confirm_sell = None   # bancada: id da peça aguardando 2º clique de VENDER
        self.page = 0              # bancada: página da lista de peças livres
        self.editing = False       # bancada: edição do nome do robô
        self.edit_text = ""
        self.blink = 0.0
        self.shop_tab = "parts"    # loja: "parts" | "models"
        self.shop_mode = "buy"     # loja/peças: "buy" | "sell"
        self.shop_slot = None      # loja/peças: filtro de slot (None = TODOS)
        self.shop_sel = None       # loja/peças: id da peça selecionada
        self.shop_page = 0
        self.model_sel = None      # loja/modelos: chassis selecionado
        self.round_info = None     # tela "round": resumo da rodada
        self.end_info = None       # tela "league_end": resumo da liga
        self.pending = None        # jogo do usuário em andamento (rodada, casa, fora)

    def open(self):
        """Entra no Modo Robôs (tela de menu do modo)."""
        self.status = G.Garage.load_status()
        if self.status == "bad":
            G.Garage.load()        # tenta gravar o texto cru em <chave>.bad; nunca sobrescreve o save
        self.garage = None
        self.confirm_new = False
        self.menu_msg = ""
        self.screen_id = "menu"
        self.reset_ui()
        self.g.state = "robots"

    def to_menu(self):
        """Sai para o menu principal do jogo (salva antes se há garagem aberta)."""
        if self.garage is not None and self.screen_id != "menu":
            self.persist()
        self.g.refresh_robots_status()
        self.g.state = "menu"
        self.screen_id = "menu"
        self.garage = None

    def go(self, screen):
        self.screen_id = screen
        self.place_mode = False
        self.editing = False
        self.msg = ""
        if screen == "garage" and self.garage is not None and self.garage.robot(self.sel) is None:
            self.sel = self.garage.lineup[0] if self.garage.lineup else None

    def persist(self):
        """Único ponto de gravação do modo (subclasses podem sobrescrever)."""
        if self.garage is not None and self.garage.save():
            self.g.refresh_robots_status()
            return True
        if self.garage is not None:
            self.msg = "Falha ao salvar."
        return False

    def act(self, result):
        """Aplica um (ok, msg) do garage: mostra a mensagem, invalida o cache e salva."""
        ok, self.msg = result
        self.cache = None
        if ok:
            self.persist()
        return ok

    def info(self):
        """Atributos/overall efetivos de todos os robôs, calculados uma vez por mudança."""
        if self.cache is None:
            gg = self.garage
            pb = gg.pieces_by_id()
            per = {}
            for r in gg.robots:
                a = G.effective_attrs(r, pb)
                per[r["id"]] = (a, int(round(robots.mean_attr(a) * 100)))
            self.cache = {"per": per, "rating": gg.rating()}
        return self.cache

    # --------------------------------------------------------------- menu
    def do_continue(self):
        gg = G.Garage.load()
        if gg is None:
            self.status = G.Garage.load_status()
            self.menu_msg = "Não foi possível carregar o save."
            return
        self.garage = gg
        self.sel = None
        self.cache = None
        self.go("hub")

    def do_new(self):
        self.status = G.Garage.load_status()      # reavalia: outra aba pode ter criado save
        if self.status != "none" and not self.confirm_new:
            self.confirm_new = True
            return
        if self.status == "bad":
            G.Garage.load()                       # garante a cópia em .bad antes de sobrescrever
        gg = G.new_game(self.rng, self.team_name)
        self.garage = gg
        self.cache = None
        self.go("hub")
        self.persist()
        self.status = "ok"
        self.confirm_new = False

    def do_shuffle_name(self):
        self.team_name = self.rng.choice([n for n in TEAM_NAMES if n != self.team_name])
        self.confirm_new = False

    def do_cancel_confirm(self):
        self.confirm_new = False

    # -------------------------------------------------------------- eventos
    def handle_event(self, e):
        if self.screen_id == "bench" and self.editing:
            if e.type == pygame.KEYDOWN:
                return self.edit_key(e)
            if e.type == pygame.MOUSEBUTTONDOWN and not NAME_FIELD.collidepoint(e.pos):
                self.editing = False                  # clique fora do campo cancela a edição
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, fn, enabled in reversed(self.buttons):
                if enabled and r.collidepoint(e.pos):
                    self.buttons = []             # descarta cliques do mesmo frame até o próximo draw
                    fn()
                    break
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            sid = self.screen_id
            if sid == "menu":
                self.to_menu()
            elif self.place_mode:
                self.place_mode = False
                self.msg = ""
            elif sid in self.frame_screens:
                self.to_menu()
            elif sid == "bench":
                self.bench_back()
            else:
                self.go("hub")

    def update(self, dt):
        if self.editing:
            self.blink = (self.blink + dt) % 1.0

    # --------------------------------------------------------------- desenho
    def draw(self):
        self.g.screen.fill(BG)
        self.buttons = []
        if self.screen_id in self.frame_screens or self.screen_id == "bench":
            self.draw_frame()
        getattr(self, "draw_" + self.screen_id)()

    # ---- menu do modo
    def draw_menu(self):
        cx = W // 2
        self.text("MODO ROBÔS", 64, TEXT, center=(cx, 60), shadow=True)
        self.text("monte sua equipe, melhore peças e dispute a liga", 28, DIM, center=(cx, 106))
        self.panel((250, 150, 600, 400))
        st = self.status
        if st == "bad":
            self.text("Save incompatível", 40, RED, center=(cx, 190))
            for k, line in enumerate(self.wrap(
                    "O save de robôs não pôde ser lido (versão nova ou arquivo danificado). "
                    "Ele não foi alterado e uma cópia foi guardada. NOVO JOGO apaga esse save.",
                    24, 540)):
                self.text(line, 24, TEXT, center=(cx, 226 + k * 26))
        elif st == "ok":
            self.text("Save encontrado", 36, GREEN, center=(cx, 190))
            self.btn((cx - 150, 220, 300, 64), "CONTINUAR", self.do_continue, size=38,
                     color=(0, 140, 110))
        else:
            self.text("Nenhum save de robôs", 32, DIM, center=(cx, 190))
        y = 330
        self.text("Nome da equipe", 22, DIM, center=(cx, y - 16))
        pygame.draw.rect(self.g.screen, BG, (cx - 190, y, 270, 44), border_radius=8)
        pygame.draw.rect(self.g.screen, LINE, (cx - 190, y, 270, 44), 2, border_radius=8)
        self.text(self.team_name, 28, GOLD, center=(cx - 55, y + 22))
        self.btn((cx + 94, y, 96, 44), "SORTEAR", self.do_shuffle_name, color=(60, 80, 130), size=22)
        if self.confirm_new:
            self.btn((cx - 200, 400, 400, 56), "CONFIRMAR: APAGAR O SAVE", self.do_new, size=28,
                     color=(170, 60, 50))
            self.btn((cx - 100, 466, 200, 40), "CANCELAR", self.do_cancel_confirm, size=24,
                     color=(60, 60, 70))
            self.text("O save atual será substituído.", 22, GOLD, center=(cx, 524))
        else:
            self.btn((cx - 150, 400, 300, 64), "NOVO JOGO", self.do_new, size=36)
        if self.menu_msg:
            self.text(self.menu_msg, 22, GOLD, center=(cx, 524))
        self.btn((25, 652, 160, 40), "VOLTAR", self.to_menu, color=(60, 60, 70), size=26)

    # ---- cabeçalho + abas (hub, garage, shop)
    def draw_frame(self):
        gg = self.garage
        scr = self.g.screen
        pygame.draw.rect(scr, PANEL, (0, 0, W, 74))
        pygame.draw.rect(scr, tuple(gg.team["color"]), (0, 0, 12, 74))
        self.text(gg.team["name"], 46, TEXT, midleft=(28, 26), shadow=True)
        st = gg.stats
        self.text("Jogos %d   |   V %d  E %d  D %d   |   Títulos %d" % (
            st["played"], st["w"], st["d"], st["l"], st["titles"]), 24, DIM, midleft=(30, 55))
        self.text("Sucata: %d" % gg.scrap, 34, GOLD, midright=(W - 20, 26), shadow=True)
        self.text("Força do time: %d" % int(round(self.info()["rating"])), 24, DIM,
                  midright=(W - 20, 55))
        for i, (tid, label) in enumerate(self.tabs):
            self.btn((20 + i * 160, 82, 150, 40), label, lambda t=tid: self.go(t),
                     color=(50, 160, 220) if self.tab_active(tid) else (16, 44, 70), size=26)
        self.btn((W - 210, 82, 190, 40), "SALVAR E SAIR", self.to_menu, color=(70, 60, 60), size=24)

    def tab_active(self, tid):
        """A aba tid está ativa na tela atual? (a bancada destaca GARAGEM)"""
        return self.screen_id == tid or (tid == "garage" and self.screen_id == "bench")

    # ================================================================ LOJA
    def set_shop_tab(self, t):
        self.shop_tab = t
        self.shop_sel = None
        self.confirm_sell = None
        self.model_sel = None
        self.shop_page = 0
        self.msg = ""

    def set_shop_mode(self, m):
        self.shop_mode = m
        self.shop_sel = None
        self.confirm_sell = None
        self.shop_page = 0
        self.msg = ""

    def set_shop_slot(self, sl):
        self.shop_slot = sl
        self.shop_sel = None
        self.confirm_sell = None
        self.shop_page = 0
        self.msg = ""

    def set_shop_page(self, p):
        self.shop_page = max(0, p)

    def pick_shop(self, pid):
        self.shop_sel = pid
        self.confirm_sell = None
        self.msg = ""

    def pick_model(self, ch):
        self.model_sel = ch
        self.msg = ""

    def shop_list(self):
        """Peças listadas: estoque da loja (COMPRAR) ou peças livres do inventário (VENDER)."""
        gg = self.garage
        if self.shop_mode == "sell":
            lst = gg.free_pieces(self.shop_slot)
        else:
            lst = [p for p in gg.shop["stock"] if self.shop_slot is None or P.part_slot(p) == self.shop_slot]
        return sorted(lst, key=lambda p: (-p["rar"], P.SLOTS.index(P.part_slot(p)), p["id"]))

    def do_buy_part(self):
        if self.shop_sel is None:
            return
        if self.act(self.garage.buy_part(self.shop_sel)):
            self.shop_sel = None

    def do_sell_part(self):
        gg = self.garage
        pc = gg.piece(self.shop_sel) if self.shop_sel is not None else None
        if pc is None:
            return
        if self.confirm_sell != pc["id"]:
            self.confirm_sell = pc["id"]
            return
        self.confirm_sell = None
        if self.act(gg.sell_part(pc["id"])):
            self.shop_sel = None

    def do_buy_robot(self):
        if self.model_sel is not None:
            self.act(self.garage.buy_robot(self.model_sel, rng=self.rng))

    @staticmethod
    def chassis_unlock_tier(ch):
        for t, lst in G.CHASSIS_UNLOCK.items():
            if ch in lst:
                return t
        return None

    def draw_shop(self):
        gg = self.garage
        scr = self.g.screen
        for i, (tid, lab) in enumerate((("parts", "PEÇAS"), ("models", "MODELOS"))):
            self.btn((20 + i * 120, 132, 110, 36), lab, lambda t=tid: self.set_shop_tab(t),
                     color=(50, 160, 220) if self.shop_tab == tid else (16, 44, 70), size=24)
        self.text("Sucata: %d" % gg.scrap, 28, GOLD, midright=(W - 24, 150))
        if self.shop_tab == "models":
            return self.draw_shop_models()
        for i, (m, lab) in enumerate((("buy", "COMPRAR"), ("sell", "VENDER"))):
            self.btn((280 + i * 120, 132, 110, 36), lab, lambda m=m: self.set_shop_mode(m),
                     color=(0, 140, 110) if (self.shop_mode == m and m == "buy") else (
                         (170, 90, 60) if self.shop_mode == m else (16, 44, 70)), size=24)
        for i, sl in enumerate((None,) + P.SLOTS):
            self.btn((20 + i * 132, 176, 126, 32), "TODOS" if sl is None else SLOT_LABELS[sl],
                     lambda s=sl: self.set_shop_slot(s),
                     color=(50, 160, 220) if self.shop_slot == sl else (16, 44, 70), size=20)
        lst = self.shop_list()
        pages = max(1, (len(lst) + SHOP_ROWS - 1) // SHOP_ROWS)
        self.shop_page = min(self.shop_page, pages - 1)
        if pages > 1:
            self.btn((540, 132, 40, 36), "<", lambda: self.set_shop_page(self.shop_page - 1),
                     enabled=self.shop_page > 0, size=24)
            self.btn((590, 132, 40, 36), ">", lambda: self.set_shop_page(self.shop_page + 1),
                     enabled=self.shop_page < pages - 1, size=24)
            self.text("%d/%d" % (self.shop_page + 1, pages), 22, DIM, midleft=(640, 150))
        sell = self.shop_mode == "sell"
        if self.shop_sel is not None and not any(p["id"] == self.shop_sel for p in lst):
            self.shop_sel = None
            self.confirm_sell = None
        for lab, x, right in (("SLOT", 40, False), ("PEÇA", 150, False), ("BÔNUS", 520, False),
                              ("VENDA" if sell else "PREÇO", 1055, True)):
            self.text(lab, 20, DIM, **({"midright": (x, 224)} if right else {"midleft": (x, 224)}))
        for k, pc in enumerate(lst[self.shop_page * SHOP_ROWS:(self.shop_page + 1) * SHOP_ROWS]):
            y = 238 + k * 38
            r = pygame.Rect(20, y, 1060, 34)
            on = pc["id"] == self.shop_sel
            pygame.draw.rect(scr, (20, 60, 90) if on else PANEL, r, border_radius=5)
            pygame.draw.rect(scr, GOLD if on else LINE, r, 2 if on else 1, border_radius=5)
            self.text(SLOT_LABELS[P.part_slot(pc)], 20, DIM, midleft=(40, y + 17))
            self.text(self.fit(P.part_name(pc), 26, 360), 26, P.RAR_COLORS[pc["rar"]], midleft=(150, y + 17))
            self.text(self.fit(P.bonus_text(pc), 22, 380), 22, TEXT, midleft=(520, y + 17))
            if sell:
                self.text("+%d" % P.sell_price(pc), 24, GREEN, midright=(1055, y + 17))
            else:
                price = P.buy_price(pc)
                self.text(str(price), 24, TEXT if gg.scrap >= price else RED, midright=(1055, y + 17))
            self.hit(r, lambda i=pc["id"]: self.pick_shop(i))
        if not lst:
            self.text("Nenhuma peça livre para vender." if sell else
                      self.SHOP_EMPTY_TEXT, 24, DIM, topleft=(30, 262))
        pc = gg.piece(self.shop_sel) if (sell and self.shop_sel is not None) else next(
            (p for p in gg.shop["stock"] if p["id"] == self.shop_sel), None)
        if sell:
            conf = pc is not None and self.confirm_sell == pc["id"]
            self.btn((860, 650, 220, 44), ("CONFIRMAR +%d" % P.sell_price(pc)) if conf else (
                "VENDER" if pc is None else "VENDER +%d" % P.sell_price(pc)), self.do_sell_part,
                enabled=pc is not None, color=(170, 60, 50) if conf else (110, 60, 60), size=26)
            if conf:
                self.text("Clique de novo para vender.", 20, GOLD, topleft=(24, 626))
            else:
                self.text("Só peças livres (não equipadas). Venda = 50% do preço; upgrades não voltam.", 20, DIM,
                          topleft=(24, 626))
        else:
            ok = pc is not None and gg.scrap >= P.buy_price(pc)
            self.btn((860, 650, 220, 44), "COMPRAR" if pc is None else "COMPRAR %d" % P.buy_price(pc),
                     self.do_buy_part, enabled=ok, size=26)
            self.text(self.SHOP_STOCK_FMT % len(gg.shop["stock"]), 20, DIM,
                      topleft=(24, 626))
        for k, line in enumerate(self.wrap(self.msg, 22, 820)[:1]):
            self.text(line, 22, GOLD, topleft=(24, 656 + k * 24))

    def draw_shop_models(self):
        gg = self.garage
        scr = self.g.screen
        price = gg.robot_price()
        for lab, x, right in (("CHASSIS", 40, False), ("PAPEL PADRÃO", 260, False), ("SITUAÇÃO", 480, False),
                              ("PREÇO", 1055, True)):
            self.text(lab, 20, DIM, **({"midright": (x, 190)} if right else {"midleft": (x, 190)}))
        names = list(robots.CHASSIS)
        for k, ch in enumerate(names):
            y = 206 + k * 44
            r = pygame.Rect(20, y, 1060, 40)
            unlocked = ch in gg.unlocked
            on = ch == self.model_sel
            pygame.draw.rect(scr, (20, 60, 90) if on else PANEL, r, border_radius=5)
            pygame.draw.rect(scr, GOLD if on else LINE, r, 2 if on else 1, border_radius=5)
            col = TEXT if unlocked else (95, 110, 105)
            self.text(ch, 28, col, midleft=(40, y + 20))
            self.text(ROLE_PT.get(G.CHASSIS_ROLE.get(ch, "MID"), "meia"), 24, DIM if unlocked else (95, 110, 105),
                      midleft=(260, y + 20))
            if unlocked:
                self.text("desbloqueado", 22, GREEN, midleft=(480, y + 20))
                self.text(str(price), 26, TEXT if gg.scrap >= price else RED, midright=(1055, y + 20))
            else:
                t = self.chassis_unlock_tier(ch)
                self.text("bloqueado: conclua o tier %d" % ((t or 0) + 1), 22, (130, 140, 135),
                          midleft=(480, y + 20))
                self.text(str(price), 26, (95, 110, 105), midright=(1055, y + 20))
            self.hit(r, lambda c=ch: self.pick_model(c))
        sel = self.model_sel
        full = len(gg.robots) >= G.MAX_SQUAD
        can = sel is not None and sel in gg.unlocked and not full and gg.scrap >= price
        self.btn((830, 650, 250, 44), "COMPRAR ROBÔ", self.do_buy_robot, enabled=can, size=26)
        self.text("Elenco: %d/%d   |   Preço atual: %d (sobe a cada tier concluído)" % (
            len(gg.robots), G.MAX_SQUAD, price), 22, TEXT, topleft=(24, 484))
        if sel is None:
            self.text("Selecione um chassis para ver o papel padrão.", 22, DIM, topleft=(24, 514))
        else:
            self.text("%s entra como %s; depois use ESCALAR na garagem." % (
                sel, ROLE_PT.get(G.CHASSIS_ROLE.get(sel, "MID"), "meia")), 22, DIM, topleft=(24, 514))
            if sel not in gg.unlocked:
                self.text("Chassis ainda bloqueado.", 22, RED, topleft=(24, 544))
            elif full:
                self.text("Elenco cheio (máx %d)." % G.MAX_SQUAD, 22, RED, topleft=(24, 544))
        for k, line in enumerate(self.wrap(self.msg, 22, 780)[:2]):
            self.text(line, 22, GOLD, topleft=(24, 650 + k * 24))

    # ================================================================ LIGA
    def new_league(self):
        gg = self.garage
        RL.new_league(gg, gg.tier(), self.rng)
        self.pending = None
        self.msg = ""
        self.persist()

    def user_strength(self):
        return self.info()["rating"]

    def side_cfgs(self, fx):
        """(home_cfg, away_cfg) do jogo do usuário: garage.match_cfg() e robot_league.match_cfg()."""
        gg = self.garage
        _opp_idx, opp = RL.opponent_of(gg.league, fx)
        mine, other = gg.match_cfg(), RL.match_cfg(opp)
        return (mine, other) if fx[1] == RL.USER else (other, mine)

    def do_watch(self):
        gg = self.garage
        lg = gg.league
        fx = RL.next_fixture(lg) if lg else None
        if fx is None:
            return
        self.pending = fx
        home, away = self.side_cfgs(fx)
        self.g.start_robot_match(home, away, on_done=self.match_done)

    def do_sim(self):
        gg = self.garage
        lg = gg.league
        fx = RL.next_fixture(lg) if lg else None
        if fx is None:
            return
        self.pending = fx
        _r, h, a = fx
        hg, ag = RL.quick_sim(RL.team_strength(lg, h, gg), RL.team_strength(lg, a, gg), self.rng)
        self.finish_round([hg, ag], [], True)

    def match_done(self, score, events):
        """Callback de Game.start_robot_match (o Game já voltou ao estado "robots")."""
        self.finish_round(score, events, False)

    def finish_round(self, score, events, simulated):
        gg = self.garage
        lg = gg.league
        fx, self.pending = self.pending, None
        if lg is None or fx is None or fx[0] != lg["round"]:
            self.go("hub")
            return
        rnd, h, a = fx
        hg, ag = int(score[0]), int(score[1])
        RL.record(lg, h, a, hg, ag)
        uh = h == RL.USER
        my, opp = (hg, ag) if uh else (ag, hg)
        side = 0 if uh else 1
        pids = [e["pid"] for e in events if e.get("team") == side and not e.get("own")
                and e.get("pid") is not None]
        tier = lg["tier"]
        eq = sum(1 for r in gg.lineup_robots() for v in r["slots"].values() if v is not None)
        order = [r for r in gg.robots if r["id"] in gg.lineup] + [r for r in gg.robots if r["id"] not in gg.lineup]
        starters = set(gg.lineup)
        rew = G.match_rewards(gg, my, opp, pids, tier, self.rng)
        rows = []
        for r in order:
            gained = rew["levels"].get(r["id"], 0)
            rows.append((r["name"], r["id"] in starters, rew["xp"].get(r["id"], 0),
                         r["level"] - gained, r["level"], gained > 0))
        RL.advance_round(lg, gg, self.rng)
        fin = RL.is_finished(lg)
        if not fin:
            gg.refresh_shop(tier, self.rng)
        self.cache = None
        base = G.team_rating(gg.lineup_robots(), {})
        self.round_info = {
            "round": rnd + 1, "teams": (lg["teams"][h], lg["teams"][a]), "score": (hg, ag),
            "user_home": uh, "sim": simulated, "fin": fin, "rew": rew, "rows": rows,
            "goals": [(e.get("min", 0), e.get("name", ""), e.get("team", 0), bool(e.get("own")))
                      for e in events],
            "equipped": eq, "rating": self.info()["rating"], "base": base,
        }
        self.persist()
        self.screen_id = "round"
        self.place_mode = False
        self.editing = False
        self.msg = ""

    def round_continue(self):
        gg = self.garage
        if gg.league is not None and RL.is_finished(gg.league):
            return self.to_league_end()
        self.go("hub")

    def to_league_end(self):
        """Encerra a liga (prêmio/desbloqueios/tier) uma única vez e mostra o resumo."""
        gg = self.garage
        if gg.league is not None and RL.is_finished(gg.league):
            lg = gg.league
            rows = RL.table(lg)
            res = RL.finish_league(gg, self.rng)
            res["rows"] = [(r["idx"] == RL.USER, r["name"], r["color"], r["pts"], r["p"], r["gd"]) for r in rows]
            self.end_info = res
            self.cache = None
            self.persist()
        if self.end_info is None:
            return self.go("hub")
        self.screen_id = "league_end"
        self.msg = ""

    def end_next(self):
        self.new_league()
        self.end_info = None
        self.go("hub")

    def draw_hub(self):
        gg = self.garage
        lg = gg.league
        if lg is None:
            return self.draw_no_league()
        scr = self.g.screen
        fx = RL.next_fixture(lg)
        # ---- tabela
        self.panel((520, 135, 560, 300))
        self.text("TABELA  -  TIER %d" % (lg["tier"] + 1), 24, GOLD, topleft=(540, 143))
        for lab, x in (("PTS", 820), ("J", 866), ("V", 910), ("E", 954), ("D", 998), ("SG", 1060)):
            self.text(lab, 20, DIM, midright=(x, 186))
        for k, row in enumerate(RL.table(lg)):
            y = 200 + k * 38
            me = row["idx"] == RL.USER
            if me:
                pygame.draw.rect(scr, (22, 70, 100), (528, y, 544, 34), border_radius=6)
                pygame.draw.rect(scr, GOLD, (528, y, 544, 34), 2, border_radius=6)
            self.text(str(k + 1), 24, GOLD if me else DIM, midright=(556, y + 17))
            pygame.draw.rect(scr, tuple(row["color"]), (566, y + 8, 14, 18), border_radius=3)
            self.text(self.fit(row["name"], 24, 200), 24, TEXT if me else (200, 215, 205), midleft=(590, y + 17))
            for v, x in ((row["pts"], 820), (row["p"], 866), (row["w"], 910), (row["d"], 954),
                         (row["l"], 998), (row["gd"], 1060)):
                self.text(("%+d" % v) if x == 1060 and v else str(v), 24, GOLD if (me and x == 820) else TEXT,
                          midright=(x, y + 17))
        # ---- próximo jogo
        self.panel((20, 135, 480, 300))
        if fx is None:
            self.text("LIGA ENCERRADA", 36, GOLD, center=(260, 230), shadow=True)
            self.text("Posição final: %dº" % RL.user_position(lg), 28, TEXT, center=(260, 278))
            self.btn((60, 330, 400, 60), "VER RESULTADO FINAL", self.to_league_end, size=30)
        else:
            rnd, h, a = fx
            self.text("RODADA %d/%d" % (rnd + 1, RL.ROUNDS), 28, GOLD, topleft=(40, 145))
            self.text("PRÓXIMO JOGO", 20, DIM, topleft=(300, 152))
            for yy, idx, lab in ((190, h, "CASA"), (250, a, "FORA")):
                t = lg["teams"][idx]
                me = idx == RL.USER
                pygame.draw.rect(scr, tuple(t["color"]), (40, yy, 22, 44), border_radius=4)
                self.text(self.fit(t["name"], 30, 250), 30, TEXT, midleft=(74, yy + 14))
                strength = int(round(self.user_strength())) if me else t["ovr"]
                self.text("Força %d%s" % (strength, "  (você)" if me else ""), 22,
                          GOLD if me else DIM, midleft=(74, yy + 36))
                self.text(lab, 22, DIM, midright=(480, yy + 22))
            self.text("x", 26, DIM, center=(300, 241))
            self.btn((40, 320, 440, 54), "ASSISTIR", self.do_watch, size=32)
            self.btn((40, 380, 440, 44), "SIMULAR", self.do_sim, color=(60, 80, 130), size=26)
        # ---- resultados da rodada anterior
        self.panel((20, 450, 480, 230))
        prev = lg["round"] - 1
        self.text("RODADA ANTERIOR" if prev >= 0 else "RODADA ANTERIOR (nenhuma)", 22, GOLD, topleft=(40, 460))
        if prev >= 0:
            for k, (rr, h2, a2, hg, ag) in enumerate([x for x in lg["results"] if x[0] == prev][:3]):
                y = 496 + k * 36
                th, ta = lg["teams"][h2], lg["teams"][a2]
                mine = RL.USER in (h2, a2)
                self.text(self.fit(th["name"], 22, 170), 22, GOLD if mine else TEXT, midright=(222, y + 14))
                self.text("%d x %d" % (hg, ag), 24, TEXT, center=(260, y + 14))
                self.text(self.fit(ta["name"], 22, 170), 22, GOLD if mine else TEXT, midleft=(298, y + 14))
        self.panel((520, 450, 560, 230))
        self.text("PREMIAÇÃO DA LIGA", 22, GOLD, topleft=(540, 460))
        mul = G.TIER_MUL[lg["tier"]]
        for k, (lab, v) in enumerate((("1º lugar", RL.PRIZE_BASE[0]), ("2º lugar", RL.PRIZE_BASE[1]),
                                      ("3º lugar", RL.PRIZE_BASE[2]), ("4º ao 6º", RL.PRIZE_BASE[3]))):
            self.text("%s: +%d sucata" % (lab, int(round(v * mul))), 22, TEXT, topleft=(540, 494 + k * 28))
        self.text("Termine em 3º ou melhor para avançar de tier.", 20, DIM, topleft=(540, 612))
        self.text("Chassis novos liberam ao concluir o tier.", 20, DIM, topleft=(540, 638))

    def draw_no_league(self):
        gg = self.garage
        tier = gg.tier()
        self.panel((250, 160, 600, 420))
        self.text("NENHUMA LIGA ATIVA", 40, GOLD, center=(W // 2, 205), shadow=True)
        self.text("Próxima liga: TIER %d" % (tier + 1), 34, TEXT, center=(W // 2, 262))
        self.text("Rivais com Força em torno de %d" % G.TIER_OVR[tier], 26, DIM, center=(W // 2, 306))
        self.text("Sua Força: %d" % int(round(self.info()["rating"])), 26, GOLD, center=(W // 2, 340))
        self.text("6 times, ida e volta: %d rodadas." % RL.ROUNDS, 24, DIM, center=(W // 2, 384))
        self.text("Sucata e prêmios x%.1f neste tier." % G.TIER_MUL[tier], 24, DIM, center=(W // 2, 414))
        self.btn((W // 2 - 160, 470, 320, 64), "INICIAR LIGA", self.new_league, size=38)

    # ================================================================ RESULTADO
    def draw_round(self):
        info = self.round_info
        scr = self.g.screen
        if info is None:
            self.text("RESULTADO DA RODADA", 48, TEXT, center=(W // 2, 80), shadow=True)
            self.text("Sem resultado para mostrar.", 28, DIM, center=(W // 2, 300))
            self.btn((W // 2 - 130, 650, 260, 42), "CONTINUAR", lambda: self.go("hub"), size=30)
            return
        self.draw_round_header(info)
        self.draw_round_body(info)

    def draw_round_header(self, info):
        """Título, placar e resultado (trecho específico da liga)."""
        scr = self.g.screen
        th, ta = info["teams"]
        self.text("RODADA %d/%d%s" % (info["round"], RL.ROUNDS, "  (simulada)" if info["sim"] else ""),
                  40, TEXT, center=(W // 2, 34), shadow=True)
        self.panel((20, 62, 1060, 100))
        hg, ag = info["score"]
        for team, cx, left in ((th, 280, True), (ta, 820, False)):
            pygame.draw.rect(scr, tuple(team["color"]), (cx - 230 if left else cx + 218, 82, 12, 60), border_radius=3)
            self.text(self.fit(team["name"], 34, 400), 34, TEXT, center=(cx, 112), shadow=True)
        self.text("%d  x  %d" % (hg, ag), 64, GOLD, center=(W // 2, 112), shadow=True)
        rew = info["rew"]
        res = {"w": ("VITÓRIA", GREEN), "d": ("EMPATE", GOLD), "l": ("DERROTA", RED)}[rew["result"]]
        self.text(res[0], 22, res[1], center=(W // 2, 148))

    def draw_round_body(self, info):
        """Gols, recompensas, XP e botão CONTINUAR."""
        scr = self.g.screen
        th, ta = info["teams"]
        rew = info["rew"]
        # gols
        self.panel((20, 172, 520, 222))
        self.text("GOLS", 22, GOLD, topleft=(38, 180))
        goals = info["goals"]
        if not goals:
            self.text("Jogo simulado: sem lances." if info["sim"] else "Sem gols.", 22, DIM, topleft=(38, 212))
        for k, (mn, name, tm, own) in enumerate(goals[:7]):
            y = 210 + k * 25
            team = th if tm == 0 else ta
            pygame.draw.rect(scr, tuple(team["color"]), (38, y + 4, 8, 16), border_radius=2)
            self.text("%d'  %s%s" % (mn, self.fit(name or "?", 22, 300), "  (contra)" if own else ""),
                      22, TEXT, midleft=(56, y + 12))
        if len(goals) > 7:
            self.text("+%d gol(s)" % (len(goals) - 7), 20, DIM, topleft=(38, 386 - 4))
        # recompensas
        self.panel((560, 172, 520, 222))
        self.text("RECOMPENSAS", 22, GOLD, topleft=(578, 180))
        gg = self.garage
        self.text("Sucata ganha: +%d" % rew["scrap"], 28, GOLD, topleft=(578, 212))
        self.text("Total: %d" % gg.scrap, 22, DIM, topleft=(578, 246))
        if rew["drop"] is not None:
            self.text("Peça encontrada:", 22, TEXT, topleft=(578, 274))
            self.text(self.fit(P.part_name(rew["drop"]), 26, 480), 26, P.RAR_COLORS[rew["drop"]["rar"]],
                      topleft=(578, 298))
        else:
            self.text("Nenhuma peça encontrada.", 22, DIM, topleft=(578, 274))
        diff = int(round(info["rating"] - info["base"]))
        eff = "Efeito das peças: %d equipada(s) nos titulares = %+d de Força (%d sem peças, %d com)." % (
            info["equipped"], diff, int(round(info["base"])), int(round(info["rating"])))
        for k, line in enumerate(self.wrap(eff, 20, 480)[:2]):
            self.text(line, 20, DIM, topleft=(578, 326 + k * 22))
        if not info["fin"]:
            self.text("A loja foi reposta.", 20, DIM, topleft=(578, 372))
        # XP
        self.panel((20, 404, 1060, 238))
        self.text("EXPERIÊNCIA", 22, GOLD, topleft=(38, 412))
        rows = info["rows"]
        half = (len(rows) + 1) // 2
        for k, (name, starter, xp, lo, hi, up) in enumerate(rows):
            col = 0 if k < half else 1
            ri = k if k < half else k - half
            x0 = 38 + col * 520
            y = 446 + ri * 46
            self.text("TIT" if starter else "RES", 20, GREEN if starter else DIM, midleft=(x0, y + 18))
            self.text(self.fit(name, 26, 170), 26, TEXT, midleft=(x0 + 46, y + 18))
            self.text("+%d XP" % xp, 24, (0, 210, 240), midright=(x0 + 290, y + 18))
            if up:
                self.text("NIVEL UP! Nv %d > %d" % (lo, hi), 24, GOLD, midleft=(x0 + 306, y + 18), shadow=True)
            else:
                self.text("Nv %d" % hi, 22, DIM, midleft=(x0 + 306, y + 18))
        self.btn((W // 2 - 130, 650, 260, 42), "CONTINUAR", self.round_continue, size=30)

    def draw_league_end(self):
        info = self.end_info
        scr = self.g.screen
        if info is None:
            self.text("FIM DA LIGA", 56, TEXT, center=(W // 2, 80), shadow=True)
            self.text("Sem resumo para mostrar.", 28, DIM, center=(W // 2, 300))
            self.btn((W // 2 - 130, 600, 260, 50), "VOLTAR", lambda: self.go("hub"), size=30)
            return
        pos = info["pos"]
        self.text("FIM DA LIGA - TIER %d" % (info["tier"] + 1), 44, TEXT, center=(W // 2, 40), shadow=True)
        medal = {1: "CAMPEÃO!", 2: "VICE-CAMPEÃO", 3: "TERCEIRO LUGAR"}.get(pos, "%dº LUGAR" % pos)
        self.text("%dº lugar - %s" % (pos, medal) if pos <= 3 else medal, 36, GOLD if pos <= 3 else TEXT,
                  center=(W // 2, 90), shadow=True)
        self.panel((20, 120, 560, 330))
        self.text("CLASSIFICAÇÃO FINAL", 22, GOLD, topleft=(38, 128))
        for lab, x in (("PTS", 470), ("J", 515), ("SG", 560)):
            self.text(lab, 20, DIM, midright=(x, 162))
        for k, (me, name, color, pts, p, gd) in enumerate(info["rows"]):
            y = 176 + k * 44
            if me:
                pygame.draw.rect(scr, (22, 70, 100), (28, y, 544, 40), border_radius=6)
                pygame.draw.rect(scr, GOLD, (28, y, 544, 40), 2, border_radius=6)
            self.text(str(k + 1), 26, GOLD if me else DIM, midright=(60, y + 20))
            pygame.draw.rect(scr, tuple(color), (72, y + 10, 14, 20), border_radius=3)
            self.text(self.fit(name, 26, 250), 26, TEXT, midleft=(96, y + 20))
            self.text(str(pts), 26, GOLD if me else TEXT, midright=(470, y + 20))
            self.text(str(p), 24, TEXT, midright=(515, y + 20))
            self.text("%+d" % gd if gd else "0", 24, TEXT, midright=(560, y + 20))
        self.panel((600, 120, 480, 330))
        self.text("RESULTADO", 22, GOLD, topleft=(618, 128))
        self.text("Prêmio: +%d sucata" % info["prize"], 32, GOLD, topleft=(618, 164), shadow=True)
        if pos == 1:
            self.text("Título conquistado!", 24, GREEN, topleft=(618, 208))
        if info["advanced"]:
            self.text("Avançou de tier! Próxima liga: TIER %d" % (info["next_tier"] + 1), 26, GREEN,
                      topleft=(618, 246))
        else:
            self.text("Não avançou: precisa de 3º ou melhor.", 26, RED, topleft=(618, 246))
        self.text("Chassis desbloqueados:", 24, TEXT, topleft=(618, 290))
        if info["unlocked"]:
            for k, ch in enumerate(info["unlocked"]):
                self.text("+ %s" % ch, 28, GOLD, topleft=(638, 322 + k * 34), shadow=True)
        else:
            self.text("nenhum novo", 24, DIM, topleft=(638, 324))
        self.text("Loja reposta para o próximo tier.", 20, DIM, topleft=(618, 420))
        again = info["advanced"] and info["next_tier"] > info["tier"]
        self.btn((W // 2 - 230, 480, 460, 64), "PRÓXIMA LIGA" if again else "REPETIR LIGA", self.end_next, size=36)
        self.btn((W // 2 - 110, 560, 220, 44), "VOLTAR AO HUB", lambda: self.go("hub"), color=(60, 60, 70),
                 size=24)

    # ---- garagem
    def pick_robot(self, rid):
        self.sel = rid
        self.place_mode = False
        self.msg = ""

    def click_row(self, rid, slot):
        """Clique numa linha: no modo ESCALAR, linha de titular = trocar; senão seleciona."""
        if self.place_mode and slot is not None:
            self.place_mode = False
            self.act(self.garage.swap_lineup(slot, self.sel))
            return
        self.pick_robot(rid)

    def toggle_place(self):
        self.place_mode = not self.place_mode
        self.msg = "Escolha o slot: clique numa linha de titular." if self.place_mode else ""

    def do_auto(self):
        self.place_mode = False
        self.act(self.garage.auto_lineup())

    def open_bench(self):
        self.bench_rid = self.sel
        self.bench_reset()
        self.go("bench")

    def draw_garage(self):
        gg = self.garage
        info = self.info()["per"]
        scr = self.g.screen
        if self.sel is None or gg.robot(self.sel) is None:
            self.sel = gg.lineup[0] if gg.lineup else None
        for lab, x, right in (("ROBÔ", 100, False), ("CHASSIS", 290, False), ("NV", 470, True),
                              ("OVR", 535, True), ("XP", 560, False)):
            self.text(lab, 22, DIM, **({"midright": (x, 148)} if right else {"midleft": (x, 148)}))
        by_id = {r["id"]: r for r in gg.robots}
        starters = [by_id[i] for i in gg.lineup if i in by_id]
        bench = sorted((r for r in gg.robots if r["id"] not in gg.lineup), key=lambda r: -info[r["id"]][1])
        for k, rb in enumerate(starters):
            self.garage_row(160 + k * ROW_PITCH, rb, info, k)
        self.text("RESERVAS", 22, DIM, topleft=(24, 390))
        pygame.draw.line(scr, LINE, (20, 410), (720, 410), 1)
        for k, rb in enumerate(bench):
            self.garage_row(416 + k * ROW_PITCH, rb, info, None)
        if not bench:
            self.text("Sem reservas. Compre robôs na LOJA.", 22, DIM, topleft=(24, 430))
        if self.place_mode:
            self.text("ESCALAR: clique na linha do titular que vai ceder o lugar (Esc cancela).", 22, SEL_COLOR,
                      topleft=(24, 566))
        for k, line in enumerate(self.wrap(self.msg, 24, 690)[:3]):
            self.text(line, 24, GOLD, topleft=(24, 600 + k * 28))
        self.garage_panel(by_id.get(self.sel), info)

    def garage_row(self, y, rb, info, slot):
        gg = self.garage
        scr = self.g.screen
        r = pygame.Rect(20, y, 700, ROW_H)
        starter = slot is not None
        if starter:
            pygame.draw.rect(scr, (16, 50, 75), r, border_radius=5)
            pygame.draw.rect(scr, GREEN, (24, y + 8, 8, ROW_H - 16), border_radius=3)
        if rb["id"] == self.sel:
            pygame.draw.rect(scr, GOLD, r, 2, border_radius=5)
        elif self.place_mode and starter:
            pygame.draw.rect(scr, SEL_COLOR, r, 2, border_radius=5)
        cy = y + ROW_H // 2
        self.text(G.SLOT_PT[slot] if starter else "RES", 22, GREEN if starter else DIM, midleft=(44, cy))
        self.text(self.fit(rb["name"], 26, 175), 26, TEXT, midleft=(100, cy))
        self.text(rb["chassis"], 22, DIM, midleft=(290, cy))
        self.text("Nv %d" % rb["level"], 24, TEXT, midright=(470, cy))
        ovr = info[rb["id"]][1]
        self.text(str(ovr), 28, ovr_color(ovr), midright=(535, cy))
        bar = pygame.Rect(560, cy - 6, 140, 12)
        pygame.draw.rect(scr, BG, bar, border_radius=4)
        if rb["level"] >= G.MAX_LEVEL:
            frac = 1.0
        else:
            frac = max(0.0, min(1.0, rb["xp"] / float(G.xp_need(rb["level"]))))
        if frac > 0:
            pygame.draw.rect(scr, GOLD if rb["level"] >= G.MAX_LEVEL else (0, 190, 230),
                             (bar.x, bar.y, max(4, int(bar.w * frac)), bar.h), border_radius=4)
        pygame.draw.rect(scr, LINE, bar, 1, border_radius=4)
        self.hit(r, lambda rid=rb["id"], s=slot: self.click_row(rid, s))

    def garage_panel(self, rb, info):
        scr = self.g.screen
        self.panel((745, 135, 335, 540))
        if rb is None:
            self.text("Nenhum robô", 24, DIM, topleft=(765, 240))
            return
        attrs, ovr = info[rb["id"]]
        scr.blit(self.g.robot_sprite(rb), (765, 148))
        self.text(self.fit(rb["name"], 32, 235), 32, TEXT, midleft=(840, 166))
        self.text("%s   Nv %d   OVR %d" % (rb["chassis"], rb["level"], ovr), 22, DIM, midleft=(840, 194))
        self.text("Overclock: " + G.OC_NAMES[rb.get("oc", 0)], 22, DIM, midleft=(840, 216))
        for k, a in enumerate(robots.ATTRS):
            y = 246 + k * 26
            v = attrs[a]
            self.text(ATT_LABELS[k], 22, DIM, midleft=(765, y + 8))
            bar = pygame.Rect(815, y + 1, 190, 14)
            pygame.draw.rect(scr, BG, bar, border_radius=4)
            pygame.draw.rect(scr, attr_color(v), (bar.x, bar.y, max(3, int(bar.w * v / 99.0)), bar.h),
                             border_radius=4)
            pygame.draw.rect(scr, LINE, bar, 1, border_radius=4)
            self.text(str(v), 24, attr_color(v), midright=(1062, y + 8))
        self.btn((765, 462, 295, 44), "CANCELAR ESCALAR" if self.place_mode else "ESCALAR", self.toggle_place,
                 enabled=rb is not None, size=26, color=(0, 150, 190) if self.place_mode else BTN)
        self.btn((765, 512, 295, 44), "AUTO ESCALAÇÃO", self.do_auto, color=(60, 80, 130), size=26)
        self.btn((765, 562, 295, 44), "ABRIR BANCADA", self.open_bench, enabled=rb is not None,
                 color=(60, 110, 90), size=26)
        self.text("Papel: " + {"GK": "goleiro", "DEF": "defensor", "MID": "meia", "ATT": "atacante"}[rb["role"]],
                  22, DIM, midleft=(765, 640))

    # ================================================================ BANCADA
    def bench_reset(self):
        self.sel_slot = self.sel_piece = self.confirm_sell = None
        self.page = 0
        self.editing = False

    def bench_back(self):
        self.sel = self.bench_rid
        self.go("garage")

    def bench_robot(self):
        gg = self.garage
        rb = gg.robot(self.bench_rid)
        if rb is None:
            rb = gg.robot(self.sel) or (gg.robots[0] if gg.robots else None)
            self.bench_rid = rb["id"] if rb else None
        return rb

    def bench_nav(self, d):
        gg = self.garage
        ids = [r["id"] for r in gg.robots]
        if not ids:
            return
        i = ids.index(self.bench_rid) if self.bench_rid in ids else 0
        self.bench_rid = ids[(i + d) % len(ids)]
        self.sel = self.bench_rid
        self.bench_reset()
        self.msg = ""

    def pick_slot(self, slot):
        self.sel_slot = slot
        self.sel_piece = None
        self.confirm_sell = None
        self.page = 0
        self.editing = False
        self.msg = ""

    def pick_piece(self, pid):
        self.sel_piece = pid
        self.confirm_sell = None
        self.msg = ""

    def set_page(self, p):
        self.page = max(0, p)

    def target_piece(self, rb, pb):
        """Peça-alvo de UPGRADE/VENDER: a livre selecionada ou a equipada no slot selecionado."""
        if self.sel_piece is not None:
            return pb.get(self.sel_piece)
        if self.sel_slot is not None:
            return pb.get(rb["slots"].get(self.sel_slot))
        return None

    def do_equip(self):
        if self.sel_piece is None or self.sel_slot is None:
            return
        self.confirm_sell = None
        if self.act(self.garage.equip(self.bench_rid, self.sel_piece, self.sel_slot)):
            self.sel_piece = None

    def do_unequip(self):
        self.confirm_sell = None
        self.act(self.garage.unequip(self.bench_rid, self.sel_slot))

    def do_upgrade(self):
        rb = self.garage.robot(self.bench_rid)
        pc = self.target_piece(rb, self.garage.pieces_by_id()) if rb else None
        self.confirm_sell = None
        if pc is not None:
            self.act(self.garage.upgrade(pc["id"]))

    def do_sell(self):
        gg = self.garage
        rb = gg.robot(self.bench_rid)
        pc = self.target_piece(rb, gg.pieces_by_id()) if rb else None
        if pc is None:
            return
        if self.confirm_sell != pc["id"]:
            self.confirm_sell = pc["id"]
            return
        self.confirm_sell = None
        if self.sel_piece is None:                    # peça equipada: desequipa e vende
            ok, msg = gg.unequip(rb["id"], self.sel_slot)
            if not ok:
                self.msg = msg
                return
        if self.act(gg.sell_part(pc["id"])):
            self.sel_piece = None

    def start_edit(self):
        rb = self.garage.robot(self.bench_rid)
        self.editing = True
        self.edit_text = rb["name"] if rb else ""
        self.blink = 0.0
        self.msg = "Digite o nome (Enter confirma, Esc cancela)."

    def edit_key(self, e):
        k = e.key
        if k == pygame.K_ESCAPE:
            self.editing = False
            self.msg = ""
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            ok = self.act(self.garage.rename(self.bench_rid, self.edit_text))
            if ok:
                self.editing = False
        elif k == pygame.K_BACKSPACE:
            self.edit_text = self.edit_text[:-1]
        else:
            for ch in getattr(e, "unicode", "") or "":
                if len(self.edit_text) < NAME_MAX and 32 <= ord(ch) <= 255 and ch.isprintable():
                    self.edit_text += ch
        self.blink = 0.0

    def do_shuffle_robot_name(self):
        rb = self.garage.robot(self.bench_rid)
        if rb is None:
            return
        self.editing = False
        self.act(self.garage.rename(rb["id"], self.rng.choice([n for n in FUN_NAMES if n != rb["name"]])))

    def do_paint(self, rgb):
        self.act(self.garage.set_paint(self.bench_rid, rgb))

    def do_oc(self):
        rb = self.garage.robot(self.bench_rid)
        if rb is not None:
            self.act(self.garage.set_oc(rb["id"], (rb.get("oc", 0) + 1) % 3))

    def draw_bench(self):
        gg = self.garage
        scr = self.g.screen
        rb = self.bench_robot()
        if rb is None:
            self.text("Nenhum robô", 30, DIM, center=(W // 2, 300))
            return
        pb = gg.pieces_by_id()
        attrs, ovr = self.info()["per"][rb["id"]]
        slot = self.sel_slot
        free = gg.free_pieces(slot) if slot else []
        if self.sel_piece is not None and not any(p["id"] == self.sel_piece for p in free):
            self.sel_piece = None
        # ---- título: nome, chassis, nível, barra de XP, navegação
        self.text(self.fit(rb["name"], 36, 235), 36, TEXT, midleft=(24, 152))
        self.text("%s  Nv %d" % (rb["chassis"], rb["level"]), 24, DIM, midleft=(268, 152))
        bar = pygame.Rect(420, 146, 200, 12)
        pygame.draw.rect(scr, BG, bar, border_radius=4)
        maxed = rb["level"] >= G.MAX_LEVEL
        frac = 1.0 if maxed else max(0.0, min(1.0, rb["xp"] / float(G.xp_need(rb["level"]))))
        if frac > 0:
            pygame.draw.rect(scr, GOLD if maxed else (0, 190, 230),
                             (bar.x, bar.y, max(4, int(bar.w * frac)), bar.h), border_radius=4)
        pygame.draw.rect(scr, LINE, bar, 1, border_radius=4)
        self.text("XP MAX" if maxed else "XP %d/%d" % (rb["xp"], G.xp_need(rb["level"])), 20, DIM,
                  midleft=(628, 152))
        self.btn((735, 132, 70, 36), "ANT", lambda: self.bench_nav(-1), color=(60, 80, 130), size=24)
        self.btn((815, 132, 70, 36), "PROX", lambda: self.bench_nav(1), color=(60, 80, 130), size=24)
        self.btn((895, 132, 185, 36), "VOLTAR", self.bench_back, color=(60, 60, 70), size=26)
        # ---- coluna esquerda: 7 slots
        for i, sl in enumerate(P.SLOTS):
            y = 182 + i * 50
            r = pygame.Rect(20, y, 280, 46)
            pygame.draw.rect(scr, (16, 50, 75) if sl == slot else PANEL, r, border_radius=6)
            pygame.draw.rect(scr, SEL_COLOR if sl == slot else LINE, r, 2, border_radius=6)
            self.text(SLOT_LABELS[sl], 18, DIM, topleft=(30, y + 5))
            pc = pb.get(rb["slots"].get(sl))
            if pc is None:
                self.text("vazio", 24, DIM, midleft=(30, y + 33))
            else:
                self.text(self.fit(P.part_name(pc), 24, 262), 24, P.RAR_COLORS[pc["rar"]], midleft=(30, y + 33))
            self.hit(r, lambda s=sl: self.pick_slot(s))
        # ---- coluna central: peças livres + ANTES/DEPOIS
        cx, cw = 312, 410
        self.panel((cx - 6, 178, cw + 12, 470))
        if slot is None:
            self.text("Selecione um slot à esquerda.", 24, DIM, topleft=(cx + 8, 200))
        else:
            pages = max(1, (len(free) + PIECE_ROWS - 1) // PIECE_ROWS)
            self.page = min(self.page, pages - 1)
            self.text("PEÇAS LIVRES: %s (%d)" % (SLOT_LABELS[slot], len(free)), 22, GOLD, topleft=(cx + 8, 188))
            if pages > 1:
                self.btn((cx + cw - 118, 184, 36, 24), "<", lambda: self.set_page(self.page - 1),
                         enabled=self.page > 0, size=22)
                self.btn((cx + cw - 76, 184, 36, 24), ">", lambda: self.set_page(self.page + 1),
                         enabled=self.page < pages - 1, size=22)
                self.text("%d/%d" % (self.page + 1, pages), 18, DIM, midright=(cx + cw - 124, 197))
            if not free:
                self.text("Sem peças livres para este slot (veja a LOJA).", 20, DIM, topleft=(cx + 8, 222))
            for k, pc in enumerate(free[self.page * PIECE_ROWS:(self.page + 1) * PIECE_ROWS]):
                y = 214 + k * 33
                r = pygame.Rect(cx, y, cw, 30)
                pygame.draw.rect(scr, (16, 50, 75) if pc["id"] == self.sel_piece else BG, r, border_radius=5)
                pygame.draw.rect(scr, SEL_COLOR if pc["id"] == self.sel_piece else LINE, r, 1, border_radius=5)
                self.text(self.fit(P.part_name(pc), 22, 215), 22, P.RAR_COLORS[pc["rar"]], midleft=(cx + 8, y + 15))
                self.text(self.fit(P.bonus_text(pc), 18, 175), 18, DIM, midright=(cx + cw - 6, y + 15))
                self.hit(r, lambda i=pc["id"]: self.pick_piece(i))
            self.draw_compare(rb, attrs, pb, cx, cw)
        # ---- coluna direita: robô, nome, pintura, overclock
        self.draw_bench_right(rb, attrs, ovr)
        # ---- ações
        pc = self.target_piece(rb, pb)
        cost = P.upgrade_cost(pc["rar"], pc["lvl"]) if pc else None
        up_ok = pc is not None and cost is not None and gg.scrap >= cost
        eq_ok = self.sel_piece is not None and slot is not None
        un_ok = slot is not None and rb["slots"].get(slot) is not None
        self.btn((20, 548, 135, 44), "EQUIPAR", self.do_equip, enabled=eq_ok, color=(0, 140, 110), size=24)
        self.btn((165, 548, 135, 44), "DESEQUIPAR", self.do_unequip, enabled=un_ok, color=(120, 90, 40), size=22)
        self.btn((20, 598, 135, 44), "MAX" if (pc is not None and cost is None) else (
            "UPGRADE %d" % cost if cost else "UPGRADE"), self.do_upgrade, enabled=up_ok, size=22)
        sell = P.sell_price(pc) if pc else 0
        conf = pc is not None and self.confirm_sell == pc["id"]
        self.btn((165, 598, 135, 44), ("CONFIRMAR +%d" if conf else "VENDER +%d") % sell if pc else "VENDER",
                 self.do_sell, enabled=pc is not None, color=(170, 60, 50) if conf else (110, 60, 60), size=22)
        if conf:
            self.text("Clique de novo para vender.", 20, GOLD, topleft=(cx + 8, 652))
        for k, line in enumerate(self.wrap(self.msg, 22, 700)[:1]):
            self.text(line, 22, GOLD, topleft=(24, 664 + k * 24))

    def draw_compare(self, rb, attrs, pb, cx, cw):
        scr = self.g.screen
        if self.sel_piece is None or self.sel_slot is None:
            self.text("Selecione uma peça livre para comparar ANTES/DEPOIS.", 20, DIM,
                      topleft=(cx + 8, 428))
            return
        sim = dict(rb)                                   # simula sem equipar nem mutar o garage
        sim["slots"] = dict(rb["slots"])
        sim["slots"][self.sel_slot] = self.sel_piece
        after = G.effective_attrs(sim, pb)
        self.text("ATRIBUTO", 20, DIM, midleft=(cx + 8, 438))
        self.text("ANTES", 20, DIM, midright=(cx + 235, 438))
        self.text("DEPOIS", 20, DIM, midright=(cx + 315, 438))
        for k, a in enumerate(robots.ATTRS):
            y = 450 + k * 24
            b, d = attrs[a], after[a]
            col = GREEN if d > b else (RED if d < b else DIM)
            self.text(ATT_LABELS[k], 22, TEXT, midleft=(cx + 8, y + 10))
            self.text(str(b), 22, TEXT, midright=(cx + 235, y + 10))
            self.text(str(d), 22, col, midright=(cx + 315, y + 10))
            self.text("%+d" % (d - b) if d != b else "=", 20, col, midright=(cx + cw - 6, y + 10))

    def draw_bench_right(self, rb, attrs, ovr):
        scr = self.g.screen
        self.panel((735, 178, 345, 474))
        scr.blit(self.g.robot_sprite(rb), (748, 188))
        self.text("OVR %d" % ovr, 30, ovr_color(ovr), midleft=(830, 206))
        self.text("Papel: " + {"GK": "goleiro", "DEF": "defensor", "MID": "meia", "ATT": "atacante"}[rb["role"]],
                  22, DIM, midleft=(830, 234))
        for k, a in enumerate(robots.ATTRS):
            y = 262 + k * 24
            v = attrs[a]
            self.text(ATT_LABELS[k], 20, DIM, midleft=(748, y + 8))
            b = pygame.Rect(795, y + 1, 195, 14)
            pygame.draw.rect(scr, BG, b, border_radius=4)
            pygame.draw.rect(scr, attr_color(v), (b.x, b.y, max(3, int(b.w * v / 99.0)), b.h), border_radius=4)
            pygame.draw.rect(scr, LINE, b, 1, border_radius=4)
            self.text(str(v), 22, attr_color(v), midright=(1066, y + 8))
        self.text("NOME", 18, DIM, topleft=(748, 462))
        pygame.draw.rect(scr, BG, NAME_FIELD, border_radius=6)
        pygame.draw.rect(scr, SEL_COLOR if self.editing else LINE, NAME_FIELD, 2, border_radius=6)
        if self.editing:
            shown = self.edit_text
            if shown:
                self.text(shown, 26, GOLD, midleft=(NAME_FIELD.x + 8, NAME_FIELD.centery))
            if self.blink < 0.5:
                cxp = NAME_FIELD.x + 8 + (self.g.font(26).size(shown)[0] if shown else 0) + 2
                pygame.draw.line(scr, GOLD, (cxp, NAME_FIELD.y + 7), (cxp, NAME_FIELD.bottom - 7), 2)
        else:
            self.text(rb["name"], 26, TEXT, midleft=(NAME_FIELD.x + 8, NAME_FIELD.centery))
        self.hit(NAME_FIELD, self.start_edit)
        self.btn((941, 482, 125, 34), "SORTEAR NOME", self.do_shuffle_robot_name, color=(60, 80, 130), size=20)
        self.text("PINTURA", 18, DIM, topleft=(748, 520))
        cur = tuple(rb["paint"])
        for i, rgb in enumerate(G.PAINT_PALETTE):
            r = pygame.Rect(748 + (i % 6) * 53, 538 + (i // 6) * 28, 48, 24)
            pygame.draw.rect(scr, rgb, r, border_radius=5)
            pygame.draw.rect(scr, SEL_COLOR if tuple(rgb) == cur else LINE, r, 3 if tuple(rgb) == cur else 1,
                             border_radius=5)
            self.hit(r, lambda c=rgb: self.do_paint(c))
        oc = rb.get("oc", 0)
        self.text("OVERCLOCK", 18, DIM, topleft=(748, 596))
        if oc:
            self.text("bateria gasta mais", 20, RED, midright=(1066, 604))
        self.btn((748, 614, 318, 34), "OVERCLOCK: " + G.OC_NAMES[oc], self.do_oc,
                 color=(0, 120, 170) if not oc else ((190, 120, 30) if oc == 1 else (190, 50, 50)), size=24)
