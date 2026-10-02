"""Modo Carreira (estilo Elifoot): liga com 3 divisões, elenco, mercado e finanças.

Lógica pura (sem pygame). Tudo é dict/list simples para salvar em JSON.
"""
import json
import math
import os
import random
import sys

SLOTS = ["GK", "DEF", "MID", "MID", "ATT"]       # os 5 titulares em campo
TEMPLATE = [("GK", 2), ("DEF", 4), ("MID", 5), ("ATT", 4)]
MIN_SQUAD, MAX_SQUAD = 12, 20
ROUNDS = 14                                      # 8 clubes, ida e volta
DIV_NAMES = ["Divisão 1", "Divisão 2", "Divisão 3"]
DIV_BASE = [68, 58, 48]                          # força média inicial por divisão
START_MONEY = [4_000_000, 1_500_000, 600_000]
TICKET = [400_000, 250_000, 150_000]             # bilheteria por jogo em casa
PRIZES = [
    [1_500_000, 1_000_000, 700_000, 500_000, 300_000, 200_000, 100_000, 0],
    [700_000, 500_000, 350_000, 250_000, 150_000, 100_000, 50_000, 0],
    [300_000, 200_000, 150_000, 100_000, 75_000, 50_000, 25_000, 0],
]
PROMOTED = 2                                     # sobem / descem 2 por divisão
POS_PT = {"GK": "GOL", "DEF": "DEF", "MID": "MEI", "ATT": "ATA"}

FIRST = ["Rafael", "Lucas", "Pedro", "Gabriel", "Mateus", "Bruno", "Diego", "Thiago",
         "Caio", "André", "Felipe", "Rodrigo", "João", "Vitor", "Marcos", "Leandro",
         "Danilo", "Igor", "Renan", "Paulo", "Henrique", "Samuel", "Otávio", "Murilo"]
LAST = ["Silva", "Souza", "Costa", "Santos", "Oliveira", "Pereira", "Lima", "Alves",
        "Rocha", "Ribeiro", "Carvalho", "Gomes", "Martins", "Araújo", "Barbosa",
        "Nunes", "Moreira", "Cardoso", "Teixeira", "Dias", "Freitas", "Mendes"]

CLUBS = [  # (nome, cor) - 8 por divisão, todos fictícios
    ("Tubarões FC", (30, 110, 230)), ("Leões do Norte", (230, 170, 20)),
    ("Estrela Azul", (60, 90, 200)), ("Furacão Verde", (30, 160, 80)),
    ("Dragões SC", (200, 40, 40)), ("Falcões AC", (110, 70, 170)),
    ("Corsários FC", (40, 40, 50)), ("Tigres da Serra", (240, 130, 20)),
    ("Águias de Prata", (150, 160, 175)), ("Lobos FC", (90, 100, 110)),
    ("Raio Vermelho", (220, 60, 90)), ("Vulcão EC", (200, 90, 30)),
    ("Gaviões SC", (60, 60, 60)), ("Panteras AC", (150, 40, 150)),
    ("Cometas FC", (40, 170, 200)), ("Guerreiros EC", (140, 30, 30)),
    ("Boêmios FC", (120, 190, 60)), ("Operário Novo", (70, 70, 140)),
    ("Sol Nascente", (240, 200, 40)), ("Marujos SC", (30, 90, 130)),
    ("Trovão FC", (100, 60, 200)), ("Bravos AC", (180, 120, 60)),
    ("Centauros EC", (60, 140, 120)), ("União Rural", (160, 200, 120)),
]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def fmt_money(n):
    s = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_000_000:
        return "%sR$ %.2fM" % (s, n / 1e6)
    return "%sR$ %dk" % (s, n // 1000)


def short_name(full):
    first, _, last = full.partition(" ")
    return "%s. %s" % (first[0], last) if last else full


def value(p):
    """Valor de mercado de um jogador."""
    base = (p["ovr"] / 100) ** 4 * 4_000_000
    if p["age"] <= 22:
        base *= 1.3
    elif p["age"] >= 32:
        base *= 0.6
    elif p["age"] >= 29:
        base *= 0.85
    return max(20_000, int(round(base, -3)))


def eff(p, slot):
    """Overall efetivo do jogador numa posição (penaliza fora de posição)."""
    if p["pos"] == slot:
        f = 1.0
    elif p["pos"] == "GK" or slot == "GK":
        f = 0.5
    else:
        f = 0.85
    return p["ovr"] * f


def poisson(lam):
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= random.random()
        if p <= limit:
            return k
        k += 1


# ---------------------------------------------------------------- persistência
SAVE_KEY = "soccerpy_career_v1"
_save_path = os.path.join(os.path.expanduser("~"), ".soccerpy_career.json")


def _store_get():
    try:
        if sys.platform == "emscripten":
            import platform
            v = platform.window.localStorage.getItem(SAVE_KEY)
            return None if v is None or str(v) == "null" else str(v)
        if os.path.exists(_save_path):
            with open(_save_path, encoding="utf-8") as f:
                return f.read()
    except Exception as ex:  # noqa: BLE001
        print("save read error:", ex)
    return None


def _store_set(text):
    try:
        if sys.platform == "emscripten":
            import platform
            platform.window.localStorage.setItem(SAVE_KEY, text)
        else:
            with open(_save_path, "w", encoding="utf-8") as f:
                f.write(text)
        return True
    except Exception as ex:  # noqa: BLE001
        print("save write error:", ex)
        return False


class Career:
    FIELDS = ("season", "round", "clubs", "divs", "fixtures", "user", "market",
              "log", "last_results", "last_fin", "form", "next_id", "history")

    def __init__(self):
        self.season = 1
        self.round = 0
        self.clubs = []
        self.divs = [[], [], []]
        self.fixtures = [[], [], []]
        self.user = None
        self.market = []
        self.log = []
        self.last_results = []
        self.last_fin = {}
        self.form = []
        self.next_id = 1
        self.history = []

    # ------------------------------------------------------------- criação
    @classmethod
    def new(cls):
        c = cls()
        for i, (name, color) in enumerate(CLUBS):
            c.clubs.append(c.gen_club(name, color, i // 8))
            c.divs[i // 8].append(i)
        for d in range(3):
            c.fixtures[d] = c.make_fixtures(c.divs[d])
        c.market_refresh()
        return c

    def gen_player(self, pos, ovr, age=None):
        p = {"id": self.next_id,
             "name": "%s %s" % (random.choice(FIRST), random.choice(LAST)),
             "pos": pos, "ovr": int(clamp(ovr, 28, 95)),
             "age": age if age else random.randint(18, 34)}
        self.next_id += 1
        return p

    def gen_club(self, name, color, div):
        base = DIV_BASE[div] + random.randint(-5, 5)
        squad = []
        for pos, n in TEMPLATE:
            for _ in range(n):
                squad.append(self.gen_player(pos, base + random.randint(-9, 9)))
        club = {"name": name, "color": list(color), "div": div,
                "money": START_MONEY[div], "squad": squad, "lineup": [],
                "stats": self.blank_stats()}
        self.auto_lineup(club)
        return club

    @staticmethod
    def blank_stats():
        return {"pts": 0, "j": 0, "v": 0, "e": 0, "d": 0, "gp": 0, "gc": 0}

    @staticmethod
    def make_fixtures(members):
        teams = members[:]
        random.shuffle(teams)
        n = len(teams)
        rounds = []
        for r in range(n - 1):
            pairs = []
            for i in range(n // 2):
                a, b = teams[i], teams[n - 1 - i]
                pairs.append((a, b) if (r + i) % 2 == 0 else (b, a))
            rounds.append(pairs)
            teams = [teams[0]] + [teams[-1]] + teams[1:-1]
        return rounds + [[(b, a) for a, b in rd] for rd in rounds]

    # ----------------------------------------------------------- escalação
    def auto_lineup(self, club):
        used, ids = set(), []
        for slot in SLOTS:
            best = max((p for p in club["squad"] if p["id"] not in used),
                       key=lambda p: eff(p, slot))
            ids.append(best["id"])
            used.add(best["id"])
        club["lineup"] = ids

    def fix_lineup(self, club):
        """Completa só as vagas inválidas, mantendo as escolhas do usuário."""
        have = {p["id"]: p for p in club["squad"]}
        lineup = [i if i in have else None for i in club["lineup"]]
        if len(lineup) != 5:
            return self.auto_lineup(club)
        used = {i for i in lineup if i}
        for k, slot in enumerate(SLOTS):
            if lineup[k] is None:
                best = max((p for p in club["squad"] if p["id"] not in used),
                           key=lambda p: eff(p, slot))
                lineup[k] = best["id"]
                used.add(best["id"])
        club["lineup"] = lineup

    def lineup_players(self, club):
        have = {p["id"]: p for p in club["squad"]}
        return [have[i] for i in club["lineup"]]

    def rating(self, club):
        pl = self.lineup_players(club)
        return sum(eff(p, s) for p, s in zip(pl, SLOTS)) / 5

    def match_cfg(self, idx):
        club = self.clubs[idx]
        squad = [(short_name(p["name"]), eff(p, s), p["id"], p["pos"])
                 for p, s in zip(self.lineup_players(club), SLOTS)]
        return {"name": club["name"], "color": tuple(club["color"]), "squad": squad}

    def put_in_lineup(self, pid):
        """Escala o jogador no lugar do titular mais fraco da mesma posição."""
        club = self.clubs[self.user]
        if pid in club["lineup"]:
            return "Já é titular."
        p = next(p for p in club["squad"] if p["id"] == pid)
        have = {q["id"]: q for q in club["squad"]}
        slots = [k for k, s in enumerate(SLOTS) if s == p["pos"]]
        k = min(slots, key=lambda k: have[club["lineup"][k]]["ovr"])
        out = have[club["lineup"][k]]
        club["lineup"][k] = pid
        return "%s entra no lugar de %s." % (short_name(p["name"]), short_name(out["name"]))

    # ------------------------------------------------------------ simulação
    def strengths(self, idx):
        club = self.clubs[idx]
        e = [eff(p, s) for p, s in zip(self.lineup_players(club), SLOTS)]
        attack = (2 * e[4] + e[2] + e[3]) / 4
        defense = (e[0] + e[1] + (e[2] + e[3]) / 2) / 3
        return attack, defense

    def sim_match(self, h, a):
        ah, dh = self.strengths(h)
        aa, da = self.strengths(a)
        lam_h = clamp(1.0 * math.exp((ah - da) / 22) * 1.1, 0.2, 4.5)
        lam_a = clamp(1.0 * math.exp((aa - dh) / 22), 0.2, 4.5)
        return poisson(lam_h), poisson(lam_a)

    def user_fixture(self):
        d = self.clubs[self.user]["div"]
        for h, a in self.fixtures[d][self.round]:
            if self.user in (h, a):
                return h, a
        return None

    def record(self, d, h, a, hg, ag):
        self.last_results.append({"div": d, "h": h, "a": a, "hg": hg, "ag": ag})
        for idx, gf, gc in ((h, hg, ag), (a, ag, hg)):
            s = self.clubs[idx]["stats"]
            s["j"] += 1
            s["gp"] += gf
            s["gc"] += gc
            if gf > gc:
                s["v"] += 1
                s["pts"] += 3
                res = "V"
            elif gf == gc:
                s["e"] += 1
                s["pts"] += 1
                res = "E"
            else:
                s["d"] += 1
                res = "D"
            if idx == self.user:
                self.form.append(res)
        ticket = int(TICKET[d] * random.uniform(0.85, 1.15))
        self.clubs[h]["money"] += ticket
        if h == self.user:
            self.last_fin["ticket"] = ticket

    def play_round(self, user_score=None):
        """Joga a rodada. user_score=(gols casa, gols fora) se o jogo foi assistido."""
        self.last_results = []
        self.last_fin = {"ticket": 0, "wages": 0}
        for d in range(3):
            for h, a in self.fixtures[d][self.round]:
                if self.user in (h, a) and user_score is not None:
                    hg, ag = user_score
                else:
                    hg, ag = self.sim_match(h, a)
                self.record(d, h, a, hg, ag)
        for i, club in enumerate(self.clubs):
            wage = int(0.004 * sum(value(p) for p in club["squad"]))
            club["money"] -= wage
            if i == self.user:
                self.last_fin["wages"] = wage
        self.round += 1
        if self.round < ROUNDS:
            self.market_refresh()

    # -------------------------------------------------------------- tabela
    def table(self, d):
        def key(i):
            s = self.clubs[i]["stats"]
            return (-s["pts"], -(s["gp"] - s["gc"]), -s["gp"], self.clubs[i]["name"])
        return sorted(self.divs[d], key=key)

    def add_log(self, text):
        self.log.insert(0, text)
        del self.log[30:]

    # ------------------------------------------------------------- mercado
    def market_refresh(self):
        self.market = []
        for _ in range(6):                              # sem clube (mais baratos)
            pos = random.choice([p for p, n in TEMPLATE for _ in range(n)])
            self.market.append({"club": -1, "p": self.gen_player(
                pos, random.randint(38, 70), random.randint(19, 35))})
        others = [i for i in range(len(self.clubs)) if i != self.user]
        random.shuffle(others)
        for i in others[:9]:
            self.market.append({"club": i, "p": random.choice(self.clubs[i]["squad"])})

    def buy_price(self, entry):
        return int(value(entry["p"]) * (0.7 if entry["club"] < 0 else 1.15))

    def buy(self, k):
        e = self.market[k]
        u = self.clubs[self.user]
        price = self.buy_price(e)
        if u["money"] < price:
            return False, "Dinheiro insuficiente."
        if len(u["squad"]) >= MAX_SQUAD:
            return False, "Elenco cheio (máx. %d). Venda alguém." % MAX_SQUAD
        p = e["p"]
        if e["club"] >= 0:
            src = self.clubs[e["club"]]
            src["squad"].remove(p)
            src["money"] += price
            repl = self.gen_player(p["pos"], p["ovr"] - random.randint(6, 14),
                                   random.randint(17, 21))
            src["squad"].append(repl)
            self.auto_lineup(src)
        u["squad"].append(p)
        u["money"] -= price
        self.market.pop(k)
        msg = "%s contratado por %s." % (short_name(p["name"]), fmt_money(price))
        self.add_log(msg)
        return True, msg

    def sell(self, pid):
        u = self.clubs[self.user]
        p = next((q for q in u["squad"] if q["id"] == pid), None)
        if p is None:
            return False, ""
        if len(u["squad"]) <= MIN_SQUAD:
            return False, "Elenco mínimo: %d jogadores." % MIN_SQUAD
        if p["pos"] == "GK" and sum(q["pos"] == "GK" for q in u["squad"]) <= 1:
            return False, "Você precisa de pelo menos 1 goleiro."
        price = int(value(p) * 0.8)
        u["squad"].remove(p)
        u["money"] += price
        self.fix_lineup(u)
        msg = "%s vendido por %s." % (short_name(p["name"]), fmt_money(price))
        self.add_log(msg)
        return True, msg

    # ----------------------------------------------------------- fim de ano
    def end_season(self):
        u_club = self.clubs[self.user]
        u_div = u_club["div"]
        orders = [self.table(d) for d in range(3)]
        u_pos = orders[u_div].index(self.user)
        info = {"season": self.season, "u_div": u_div, "u_pos": u_pos,
                "champions": [self.clubs[o[0]]["name"] for o in orders],
                "prize": PRIZES[u_div][u_pos], "status": "", "retired": [],
                "up": [], "down": []}
        for d in range(3):
            for pos, idx in enumerate(orders[d]):
                self.clubs[idx]["money"] += PRIZES[d][pos]
        up = {1: orders[1][:PROMOTED], 2: orders[2][:PROMOTED]}
        down = {0: orders[0][-PROMOTED:], 1: orders[1][-PROMOTED:]}
        new = [
            [i for i in orders[0] if i not in down[0]] + up[1],
            [i for i in orders[1] if i not in up[1] and i not in down[1]] + down[0] + up[2],
            [i for i in orders[2] if i not in up[2]] + down[1],
        ]
        info["up"] = [self.clubs[i]["name"] for d in (1, 2) for i in up[d]]
        info["down"] = [self.clubs[i]["name"] for d in (0, 1) for i in down[d]]
        if self.user in up.get(u_div, []):
            info["status"] = "PROMOVIDO!"
        elif self.user in down.get(u_div, []):
            info["status"] = "REBAIXADO"
        for d in range(3):
            self.divs[d] = new[d]
            for i in new[d]:
                self.clubs[i]["div"] = d
                self.clubs[i]["stats"] = self.blank_stats()
        self.age_players(info)
        self.season += 1
        self.round = 0
        self.form = []
        for d in range(3):
            self.fixtures[d] = self.make_fixtures(self.divs[d])
        self.market_refresh()
        self.history.append("Temp. %d: %s (%dº na %s)" % (
            info["season"], info["status"] or "manteve a divisão",
            u_pos + 1, DIV_NAMES[u_div]))
        self.add_log("Nova temporada começou! Boa sorte.")
        return info

    def age_players(self, info):
        for i, club in enumerate(self.clubs):
            avg = sum(p["ovr"] for p in club["squad"]) / len(club["squad"])
            for p in club["squad"][:]:
                p["age"] += 1
                a = p["age"]
                if a <= 23:
                    delta = random.randint(0, 4)
                elif a <= 29:
                    delta = random.randint(-1, 2)
                elif a <= 33:
                    delta = random.randint(-3, 0)
                else:
                    delta = random.randint(-4, -1)
                p["ovr"] = int(clamp(p["ovr"] + delta, 28, 95))
                if a >= 36 or (a >= 34 and random.random() < 0.4):
                    club["squad"].remove(p)
                    club["squad"].append(self.gen_player(
                        p["pos"], avg - 8 + random.randint(-5, 5), random.randint(17, 20)))
                    if i == self.user:
                        info["retired"].append(short_name(p["name"]))
            if i == self.user:
                self.fix_lineup(club)
            else:
                self.auto_lineup(club)

    # ----------------------------------------------------------- persistência
    def to_json(self):
        return json.dumps({k: getattr(self, k) for k in self.FIELDS})

    def save(self):
        return _store_set(self.to_json())

    @classmethod
    def load(cls):
        text = _store_get()
        if not text:
            return None
        try:
            c = cls()
            for k, v in json.loads(text).items():
                setattr(c, k, v)
            return c
        except Exception as ex:  # noqa: BLE001
            print("save load error:", ex)
            return None

    @staticmethod
    def has_save():
        return _store_get() is not None
