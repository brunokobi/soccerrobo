"""Telas do Modo Carreira (desenhadas com pygame, controladas por mouse)."""
import pygame

import career as C

W, H = 1100, 700
BG = (8, 14, 24)
PANEL = (12, 28, 44)
LINE = (40, 100, 140)
TEXT = (235, 242, 236)
DIM = (150, 175, 158)
GOLD = (255, 214, 90)
GREEN = (110, 230, 120)
RED = (240, 100, 90)
BTN = (0, 120, 170)
POS_ORDER = {"GK": 0, "DEF": 1, "MID": 2, "ATT": 3}
TABS = [("home", "INÍCIO"), ("table", "TABELA"), ("squad", "ELENCO"), ("market", "MERCADO")]


def ovr_color(o):
    if o >= 75:
        return GREEN
    if o >= 62:
        return (190, 235, 120)
    if o >= 50:
        return (240, 220, 100)
    return (240, 150, 90)


def vis(color):
    """Garante que a cor do clube seja legível em fundo escuro."""
    c = tuple(color)
    if sum(c) < 300:
        c = tuple((v + 255) // 2 for v in c)
    return c


class CareerUI:
    def __init__(self, game):
        self.g = game
        self.career = None
        self.screen_id = "pick"
        self.tab = "home"
        self.buttons = []
        self.reset_ui()
        self.round_info = None
        self.season_info = None

    # ------------------------------------------------------------ navegação
    def reset_ui(self):
        self.sel = None
        self.msel = None
        self.msg = ""
        self.confirm = None
        self.pos_filter = None
        self.table_div = 0

    def open_new(self):
        self.career = C.Career.new()
        self.screen_id = "pick"
        self.reset_ui()
        self.g.state = "career"

    def open_saved(self):
        c = C.Career.load()
        if c is None or c.user is None:
            self.g.has_save = False
            return
        self.career = c
        self.screen_id = "hub"
        self.tab = "home"
        self.reset_ui()
        self.table_div = c.clubs[c.user]["div"]
        self.g.state = "career"

    def save(self):
        if self.career and self.career.user is not None:
            if self.career.save():
                self.g.has_save = True

    def to_menu(self):
        if self.screen_id != "pick":
            self.save()
        self.g.state = "menu"

    def choose(self, idx):
        c = self.career
        c.user = idx
        c.market_refresh()
        c.add_log("Bem-vindo ao %s! Boa sorte na Divisão %d." % (c.clubs[idx]["name"], c.clubs[idx]["div"] + 1))
        self.table_div = c.clubs[idx]["div"]
        self.screen_id = "hub"
        self.tab = "home"
        self.save()

    def set_tab(self, t):
        self.tab = t
        self.sel = self.msel = self.confirm = None
        self.msg = ""

    # ----------------------------------------------------------- partidas
    def play_match(self):
        c = self.career
        h, a = c.user_fixture()
        self.g.start_career_match(c.match_cfg(h), c.match_cfg(a))

    def quick_sim(self):
        self.career.play_round(None)
        self.make_round_info([])

    def match_done(self, score, events):
        self.career.play_round(user_score=(score[0], score[1]))
        self.make_round_info(events)

    def make_round_info(self, events):
        c = self.career
        res = next(r for r in c.last_results if c.user in (r["h"], r["a"]))
        self.round_info = {"round": c.round, "res": res, "events": events, "fin": dict(c.last_fin)}
        self.screen_id = "round"
        self.save()

    def after_round(self):
        c = self.career
        if c.round >= C.ROUNDS:
            self.season_info = c.end_season()
            self.screen_id = "season"
        else:
            self.screen_id = "hub"
            self.tab = "home"
        self.reset_ui()
        self.table_div = c.clubs[c.user]["div"]
        self.save()

    def after_season(self):
        self.screen_id = "hub"
        self.tab = "home"

    # -------------------------------------------------------------- eventos
    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, fn, enabled in reversed(self.buttons):
                if enabled and r.collidepoint(e.pos):
                    self.buttons = []             # descarta cliques do mesmo frame até o próximo draw
                    fn()
                    break
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and self.screen_id in ("pick", "hub"):
            self.to_menu()

    def update(self, dt):
        pass

    # ------------------------------------------------------------- helpers
    def text(self, *a, **k):
        k.setdefault("shadow", False)
        self.g.text(*a, **k)

    def fit(self, s, size, maxw):
        f = self.g.font(size)
        if f.size(s)[0] <= maxw:
            return s
        while s and f.size(s + "..")[0] > maxw:
            s = s[:-1]
        return s + ".."

    def wrap(self, s, size, maxw):
        f, lines, cur = self.g.font(size), [], ""
        for w in s.split():
            t = (cur + " " + w).strip()
            if f.size(t)[0] <= maxw:
                cur = t
            else:
                lines.append(cur)
                cur = w
        return lines + [cur] if cur else lines

    def panel(self, rect, fill=PANEL):
        pygame.draw.rect(self.g.screen, fill, rect, border_radius=12)
        pygame.draw.rect(self.g.screen, LINE, rect, 2, border_radius=12)

    def hit(self, rect, fn, enabled=True):
        self.buttons.append((pygame.Rect(rect), fn, enabled))

    def btn(self, rect, label, fn, enabled=True, color=BTN, size=28):
        r = pygame.Rect(rect)
        col = color if enabled else (48, 58, 52)
        if enabled and r.collidepoint(pygame.mouse.get_pos()):
            col = tuple(min(255, v + 28) for v in col)
        pygame.draw.rect(self.g.screen, col, r, border_radius=10)
        pygame.draw.rect(self.g.screen, (200, 225, 208) if enabled else LINE, r, 2, border_radius=10)
        self.text(label, size, TEXT if enabled else DIM, center=r.center)
        self.hit(r, fn, enabled)

    # --------------------------------------------------------------- desenho
    def draw(self):
        self.g.screen.fill(BG)
        self.buttons = []
        getattr(self, "draw_" + self.screen_id)()

    # ---- escolha do clube
    def draw_pick(self):
        c = self.career
        self.text("ESCOLHA SEU CLUBE", 56, TEXT, center=(W // 2, 44), shadow=True)
        self.text("Divisões mais baixas têm menos dinheiro e elenco mais fraco. Suba de divisão!",
                  24, DIM, center=(W // 2, 86))
        for d in range(3):
            x = 25 + d * 360
            self.text(C.DIV_NAMES[d], 34, GOLD, topleft=(x + 6, 118))
            for k, idx in enumerate(c.divs[d]):
                club = c.clubs[idx]
                r = pygame.Rect(x, 158 + k * 60, 340, 54)
                hover = r.collidepoint(pygame.mouse.get_pos())
                self.panel(r, (20, 60, 90) if hover else PANEL)
                pygame.draw.rect(self.g.screen, tuple(club["color"]), (r.x + 8, r.y + 8, 12, 38), border_radius=4)
                self.text(club["name"], 28, TEXT, midleft=(r.x + 34, r.centery - 8))
                self.text("Força %d   Caixa %s" % (c.rating(club), C.fmt_money(club["money"])),
                          21, DIM, midleft=(r.x + 34, r.centery + 14))
                self.hit(r, lambda i=idx: self.choose(i))
        self.btn((25, 652, 160, 40), "VOLTAR", self.to_menu, color=(60, 60, 70), size=26)

    # ---- hub
    def draw_hub(self):
        c = self.career
        club = c.clubs[c.user]
        scr = self.g.screen
        pygame.draw.rect(scr, PANEL, (0, 0, W, 74))
        pygame.draw.rect(scr, tuple(club["color"]), (0, 0, 12, 74))
        self.text(club["name"], 46, TEXT, midleft=(28, 26), shadow=True)
        self.text("%s   |   Temporada %d   |   Rodada %d/%d" % (
            C.DIV_NAMES[club["div"]], c.season, min(c.round + 1, C.ROUNDS), C.ROUNDS),
            24, DIM, midleft=(30, 55))
        self.text("Caixa: " + C.fmt_money(club["money"]), 34, GOLD if club["money"] >= 0 else RED,
                  midright=(W - 20, 26), shadow=True)
        self.text("Força do time: %d" % c.rating(club), 24, DIM, midright=(W - 20, 55))
        for i, (tid, label) in enumerate(TABS):
            self.btn((20 + i * 160, 82, 150, 40), label, lambda t=tid: self.set_tab(t),
                     color=(50, 160, 220) if self.tab == tid else (16, 44, 70), size=26)
        self.btn((W - 210, 82, 190, 40), "SALVAR E SAIR", self.to_menu, color=(70, 60, 60), size=24)
        getattr(self, "tab_" + self.tab)()

    def tab_home(self):
        c = self.career
        club = c.clubs[c.user]
        h, a = c.user_fixture()
        ch, ca = c.clubs[h], c.clubs[a]
        self.panel((20, 135, 540, 400))
        self.text("PRÓXIMA PARTIDA  -  Rodada %d" % (c.round + 1), 30, GOLD, topleft=(42, 150))
        self.text(ch["name"], 46, vis(ch["color"]), center=(290, 225), shadow=True)
        self.text("x", 34, DIM, center=(290, 272))
        self.text(ca["name"], 46, vis(ca["color"]), center=(290, 319), shadow=True)
        self.text("Você joga %s" % ("em CASA (bilheteria!)" if h == c.user else "FORA de casa"), 26, TEXT,
                  center=(290, 370))
        self.text("Força:  %d  x  %d" % (c.rating(ch), c.rating(ca)), 26, DIM, center=(290, 400))
        self.btn((40, 440, 240, 70), "ASSISTIR", self.play_match, size=34)
        self.btn((300, 440, 240, 70), "SIMULAR", self.quick_sim, color=(60, 80, 130), size=34)

        self.panel((580, 135, 500, 400))
        self.text("SUA CAMPANHA", 30, GOLD, topleft=(602, 150))
        order = c.table(club["div"])
        s = club["stats"]
        self.text("%dº lugar  -  %d pts em %d jogos" % (order.index(c.user) + 1, s["pts"], s["j"]),
                  28, TEXT, topleft=(602, 190))
        self.text("Gols: %d pró  %d contra" % (s["gp"], s["gc"]), 24, DIM, topleft=(602, 224))
        x = 602
        self.text("Últimos:", 24, DIM, topleft=(x, 256))
        for k, r in enumerate(c.form[-6:]):
            col = {"V": GREEN, "E": GOLD, "D": RED}[r]
            pygame.draw.rect(self.g.screen, col, (692 + k * 34, 254, 28, 26), border_radius=6)
            self.text(r, 24, (10, 20, 12), center=(706 + k * 34, 267))
        self.text("NOTÍCIAS", 26, GOLD, topleft=(602, 300))
        for k, line in enumerate(c.log[:6]):
            self.text(self.fit(line, 22, 460), 22, TEXT, topleft=(602, 332 + k * 31))

        fin = c.last_fin
        if fin:
            self.text("Última rodada:  bilheteria %s   |   salários -%s" % (
                C.fmt_money(fin.get("ticket", 0)), C.fmt_money(fin.get("wages", 0))), 24, DIM,
                topleft=(24, 556))
        self.text("Dica: compre jogadores no MERCADO e ajuste a escalação em ELENCO.", 24, DIM, topleft=(24, 590))

    def tab_table(self):
        c = self.career
        d = self.table_div
        for i in range(3):
            self.btn((20 + i * 170, 135, 160, 38), C.DIV_NAMES[i], lambda i=i: setattr(self, "table_div", i),
                     color=(50, 160, 220) if d == i else (16, 44, 70), size=26)
        cols = [("J", 560), ("V", 640), ("E", 720), ("D", 800), ("SG", 890), ("PTS", 1000)]
        self.text("#", 24, DIM, center=(50, 196))
        self.text("CLUBE", 24, DIM, topleft=(105, 186))
        for lab, x in cols:
            self.text(lab, 24, DIM, midright=(x, 196))
        order = c.table(d)
        for k, idx in enumerate(order):
            club = c.clubs[idx]
            s = club["stats"]
            r = pygame.Rect(20, 214 + k * 46, 1060, 42)
            fill = PANEL
            if d > 0 and k < C.PROMOTED:
                fill = (28, 72, 44)
            elif d < 2 and k >= len(order) - C.PROMOTED:
                fill = (80, 38, 38)
            pygame.draw.rect(self.g.screen, fill, r, border_radius=8)
            if idx == c.user:
                pygame.draw.rect(self.g.screen, GOLD, r, 3, border_radius=8)
            self.text(str(k + 1), 28, TEXT, center=(50, r.centery))
            pygame.draw.rect(self.g.screen, tuple(club["color"]), (80, r.y + 8, 12, 26), border_radius=3)
            self.text(club["name"], 28, TEXT, midleft=(105, r.centery))
            vals = [s["j"], s["v"], s["e"], s["d"], "%+d" % (s["gp"] - s["gc"]), s["pts"]]
            for (lab, x), v in zip(cols, vals):
                self.text(str(v), 28 if lab != "PTS" else 32, GOLD if lab == "PTS" else TEXT,
                          midright=(x, r.centery))
        self.text("Verde: sobem 2   |   Vermelho: caem 2   (D1 não sobe, D3 não cai)", 22, DIM,
                  topleft=(24, 590))

    # ---- elenco
    def squad_rows(self, club):
        by_id = {p["id"]: p for p in club["squad"]}
        starters = [by_id[i] for i in club["lineup"]]
        bench = sorted((p for p in club["squad"] if p["id"] not in club["lineup"]),
                       key=lambda p: (POS_ORDER[p["pos"]], -p["ovr"]))
        return starters, bench

    def tab_squad(self):
        c = self.career
        club = c.clubs[c.user]
        starters, bench = self.squad_rows(club)
        self.text("JOGADOR", 22, DIM, topleft=(60, 138))
        for lab, x in (("POS", 360), ("OVR", 440), ("IDADE", 520), ("VALOR", 700)):
            self.text(lab, 22, DIM, midright=(x, 148))
        for k, p in enumerate(starters + bench):
            y = 166 + k * 25
            r = pygame.Rect(20, y, 700, 24)
            starter = k < 5
            if starter:
                pygame.draw.rect(self.g.screen, (16, 50, 75), r, border_radius=5)
                pygame.draw.rect(self.g.screen, GREEN, (24, y + 4, 8, 16), border_radius=3)
            if p["id"] == self.sel:
                pygame.draw.rect(self.g.screen, GOLD, r, 2, border_radius=5)
            self.text(p["name"], 22, TEXT, midleft=(44, y + 12))
            self.text(C.POS_PT[p["pos"]], 22, DIM, midright=(360, y + 12))
            self.text(str(p["ovr"]), 24, ovr_color(p["ovr"]), midright=(440, y + 12))
            self.text(str(p["age"]), 22, TEXT, midright=(520, y + 12))
            self.text(C.fmt_money(C.value(p)), 22, TEXT, midright=(700, y + 12))
            self.hit(r, lambda pid=p["id"]: self.pick_player(pid))
            if k == 4:
                pygame.draw.line(self.g.screen, LINE, (20, y + 25), (720, y + 25), 1)

        self.panel((745, 135, 335, 540))
        self.text("Elenco: %d/%d" % (len(club["squad"]), C.MAX_SQUAD), 26, GOLD, topleft=(765, 150))
        self.text("Verde = titular", 22, GREEN, topleft=(765, 182))
        p = next((q for q in club["squad"] if q["id"] == self.sel), None)
        if p:
            self.text(p["name"], 28, TEXT, topleft=(765, 225))
            self.text("%s   Overall %d   %d anos" % (C.POS_PT[p["pos"]], p["ovr"], p["age"]), 22, DIM,
                      topleft=(765, 258))
            self.text("Valor: " + C.fmt_money(C.value(p)), 24, TEXT, topleft=(765, 286))
        else:
            self.text("Clique num jogador", 24, DIM, topleft=(765, 240))
        is_st = bool(p) and p["id"] in club["lineup"]
        self.btn((765, 330, 295, 46), "ESCALAR TITULAR", self.do_lineup, enabled=bool(p) and not is_st, size=26)
        self.btn((765, 386, 295, 46), "AUTO ESCALAÇÃO", self.do_auto, color=(60, 80, 130), size=26)
        sell_lab = "CONFIRMAR VENDA" if p and self.confirm == p["id"] else (
            "VENDER (%s)" % C.fmt_money(int(C.value(p) * 0.8)) if p else "VENDER")
        self.btn((765, 442, 295, 46), sell_lab, self.do_sell, enabled=bool(p),
                 color=(150, 60, 50) if p and self.confirm == p["id"] else (110, 55, 50), size=24)
        for k, line in enumerate(self.wrap(self.msg, 22, 295)[:5]):
            self.text(line, 22, GOLD, topleft=(765, 510 + k * 26))

    def pick_player(self, pid):
        self.sel = pid
        self.confirm = None
        self.msg = ""

    def do_lineup(self):
        self.msg = self.career.put_in_lineup(self.sel)
        self.save()

    def do_auto(self):
        club = self.career.clubs[self.career.user]
        self.career.auto_lineup(club)
        self.msg = "Escalação automática aplicada."
        self.save()

    def do_sell(self):
        if self.confirm != self.sel:
            self.confirm = self.sel
            return
        ok, self.msg = self.career.sell(self.sel)
        self.confirm = None
        if ok:
            self.sel = None
            self.save()

    # ---- mercado
    def tab_market(self):
        c = self.career
        club = c.clubs[c.user]
        starters, _ = self.squad_rows(club)
        for i, (pos, lab) in enumerate([(None, "TODOS"), ("GK", "GOL"), ("DEF", "DEF"),
                                         ("MID", "MEI"), ("ATT", "ATA")]):
            self.btn((20 + i * 110, 135, 100, 36), lab, lambda p=pos: setattr(self, "pos_filter", p),
                     color=(50, 160, 220) if self.pos_filter == pos else (16, 44, 70), size=24)
        self.text("Caixa: " + C.fmt_money(club["money"]), 28, GOLD, midright=(W - 24, 153))
        for lab, x, right in (("CLUBE", 40, False), ("JOGADOR", 290, False), ("POS", 590, True),
                              ("OVR", 660, True), ("IDADE", 745, True), ("VS TITULAR", 850, True),
                              ("PREÇO", 1055, True)):
            self.text(lab, 22, DIM, **({"midright": (x, 194)} if right else {"midleft": (x, 194)}))
        entries = sorted(c.market, key=lambda e: -e["p"]["ovr"])
        entries = [e for e in entries if self.pos_filter is None or e["p"]["pos"] == self.pos_filter]
        for k, e in enumerate(entries[:15]):
            p = e["p"]
            y = 210 + k * 27
            r = pygame.Rect(20, y, 1060, 26)
            if e is self.msel:
                pygame.draw.rect(self.g.screen, (20, 60, 90), r, border_radius=5)
                pygame.draw.rect(self.g.screen, GOLD, r, 2, border_radius=5)
            price = c.buy_price(e)
            same = [q["ovr"] for q in starters if q["pos"] == p["pos"]]
            delta = p["ovr"] - min(same) if same else 0
            self.text("Sem clube" if e["club"] < 0 else c.clubs[e["club"]]["name"], 22,
                      DIM if e["club"] < 0 else TEXT, midleft=(40, y + 13))
            self.text(p["name"], 22, TEXT, midleft=(290, y + 13))
            self.text(C.POS_PT[p["pos"]], 22, DIM, midright=(590, y + 13))
            self.text(str(p["ovr"]), 24, ovr_color(p["ovr"]), midright=(660, y + 13))
            self.text(str(p["age"]), 22, TEXT, midright=(745, y + 13))
            self.text(("%+d" % delta) if delta else "0", 22, GREEN if delta > 0 else (RED if delta < 0 else DIM),
                      midright=(850, y + 13))
            self.text(C.fmt_money(price), 22, TEXT if price <= club["money"] else RED, midright=(1055, y + 13))
            self.hit(r, lambda e=e: self.pick_market(e))
        if not entries:
            self.text("Nenhum jogador nessa posição agora. O mercado muda a cada rodada.", 24, DIM,
                      topleft=(30, 230))
        e = self.msel if self.msel in c.market else None
        self.btn((880, 648, 200, 44), "COMPRAR", self.do_buy, enabled=bool(e), size=28)
        for k, line in enumerate(self.wrap(self.msg, 22, 820)[:2]):
            self.text(line, 22, GOLD, topleft=(24, 650 + k * 24))
        self.text("VS TITULAR: diferença de overall para o seu pior titular da posição.", 20, DIM,
                  topleft=(24, 628))

    def pick_market(self, e):
        self.msel = e
        self.msg = ""

    def do_buy(self):
        c = self.career
        ok, self.msg = c.buy(c.market.index(self.msel))
        self.msel = None
        if ok:
            self.save()

    # ---- resultados da rodada
    def draw_round(self):
        c = self.career
        info = self.round_info
        res = info["res"]
        self.text("RODADA %d  -  RESULTADOS" % info["round"], 46, TEXT, center=(W // 2, 40), shadow=True)
        ch, ca = c.clubs[res["h"]], c.clubs[res["a"]]
        self.panel((20, 75, 1060, 170))
        self.text(ch["name"], 40, vis(ch["color"]), midright=(430, 130), shadow=True)
        self.text("%d x %d" % (res["hg"], res["ag"]), 68, TEXT, center=(W // 2, 130), shadow=True)
        self.text(ca["name"], 40, vis(ca["color"]), midleft=(670, 130), shadow=True)
        for team, x, anchor in ((0, 430, "midright"), (1, 670, "midleft")):
            evs = [e for e in info["events"] if e["team"] == team][:4]
            for k, e in enumerate(evs):
                self.text("%s %d'%s" % (e["name"] or "?", e["min"], " (c)" if e["own"] else ""), 22, DIM,
                          **{anchor: (x, 170 + k * 20)})
        mine = "VITÓRIA!" if (res["hg"] > res["ag"]) == (res["h"] == c.user) and res["hg"] != res["ag"] else (
            "EMPATE" if res["hg"] == res["ag"] else "DERROTA")
        col = {"VITÓRIA!": GREEN, "EMPATE": GOLD, "DERROTA": RED}[mine]
        self.text(mine, 34, col, center=(W // 2, 215), shadow=True)

        d = c.clubs[c.user]["div"]
        self.text(C.DIV_NAMES[d].upper(), 26, GOLD, topleft=(30, 262))
        for k, r in enumerate([r for r in c.last_results if r["div"] == d]):
            y = 298 + k * 40
            me = c.user in (r["h"], r["a"])
            if me:
                pygame.draw.rect(self.g.screen, (20, 60, 90), (20, y - 4, 560, 36), border_radius=6)
            self.text(c.clubs[r["h"]]["name"], 26, TEXT, midright=(270, y + 14))
            self.text("%d x %d" % (r["hg"], r["ag"]), 28, GOLD, center=(310, y + 14))
            self.text(c.clubs[r["a"]]["name"], 26, TEXT, midleft=(355, y + 14))
        y0 = 262
        for d2 in range(3):
            if d2 == d:
                continue
            self.text(C.DIV_NAMES[d2].upper(), 22, GOLD, topleft=(610, y0))
            for k, r in enumerate([r for r in c.last_results if r["div"] == d2]):
                self.text("%s %d x %d %s" % (self.fit(c.clubs[r["h"]]["name"], 20, 150), r["hg"], r["ag"],
                                              self.fit(c.clubs[r["a"]]["name"], 20, 150)),
                          20, DIM, topleft=(610, y0 + 26 + k * 22))
            y0 += 130
        fin = info["fin"]
        self.text("Bilheteria: %s    Salários: -%s" % (C.fmt_money(fin.get("ticket", 0)),
                                                       C.fmt_money(fin.get("wages", 0))), 24, DIM,
                  topleft=(30, 480))
        self.btn((W // 2 - 130, 620, 260, 56), "CONTINUAR", self.after_round, size=34)

    # ---- fim de temporada
    def draw_season(self):
        c = self.career
        i = self.season_info
        self.text("FIM DA TEMPORADA %d" % i["season"], 56, TEXT, center=(W // 2, 50), shadow=True)
        for d in range(3):
            self.text("Campeão %s:  %s" % (C.DIV_NAMES[d], i["champions"][d]), 30, GOLD,
                      center=(W // 2, 120 + d * 38))
        self.panel((120, 250, 860, 250))
        self.text("Seu clube terminou em %dº na %s" % (i["u_pos"] + 1, C.DIV_NAMES[i["u_div"]]), 34, TEXT,
                  center=(W // 2, 290))
        if i["status"]:
            self.text(i["status"], 64, GREEN if i["status"].startswith("PRO") else RED,
                      center=(W // 2, 350), shadow=True)
        else:
            self.text("Manteve a divisão", 40, GOLD, center=(W // 2, 350))
        self.text("Premiação: " + C.fmt_money(i["prize"]), 30, GOLD, center=(W // 2, 410))
        self.text("Sobem: " + ", ".join(i["up"]), 22, GREEN, center=(W // 2, 450))
        self.text("Descem: " + ", ".join(i["down"]), 22, RED, center=(W // 2, 478))
        club = c.clubs[c.user]
        self.text("Caixa atual: " + C.fmt_money(club["money"]), 28, TEXT, center=(W // 2, 535))
        if i["retired"]:
            self.text("Aposentados: " + ", ".join(i["retired"]) + " (veja o novo elenco)", 22, DIM,
                      center=(W // 2, 570))
        self.btn((W // 2 - 180, 620, 360, 56), "INICIAR TEMPORADA %d" % c.season, self.after_season, size=32)
