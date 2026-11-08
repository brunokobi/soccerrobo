"""Modo Carreira (estilo Elifoot): liga com 3 divisões, elenco, mercado e finanças.

Lógica pura (sem pygame). Tudo é dict/list simples para salvar em JSON.
"""
import json
import math
import os
import random
import sys

import formations
import match_stats as MS
import robot_names as RN

SLOTS = ["GK", "DEF", "MID", "MID", "ATT"]       # os 5 titulares em campo
# Elenco de 5 a 10 robos: 5 titulares (goleiro + 4 de linha) e ate 5 reservas. Cada clube nasce de uma
# "peneira" de 15 robos (SCOUT, a mesma composicao dos elencos antigos de 15) e fica com os 7-10 melhores: os
# 5 titulares (como auto_lineup), o melhor goleiro reserva e 1-4 reservas de linha (os de maior overall). Assim a
# forca dos titulares e a mesma da geracao antiga (medido em tests/test_career.py e no relatorio do equilibrio).
MIN_SQUAD, MAX_SQUAD = 5, 10
SCOUT = [("GK", 2), ("DEF", 4), ("MID", 5), ("ATT", 4)]
CPU_EXTRA_RANGE = (1, 4)                         # reservas de linha alem do goleiro reserva: elenco de 7 a 10
MARKET_POS = SCOUT                               # pesos das posicoes dos robos sem clube no mercado
# Versao do save da carreira (campo "ver"). Sem o campo = save antigo (nomes de pessoa, elencos de 12-20):
# load() migra (migrate_v1 e depois migrate_v2). ver=2: idade em anos ("age") -> migrate_v2 troca por horas de
# uso ("hours"). O proximo save ja sai com ver=3.
VERSION = 3
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
# Estatisticas por jogador (campos OPCIONAIS no dict do jogador; save antigo = zeros): temporada (sg gols, sa
# assistencias, smvp melhor do jogo) e carreira toda (tg, ta, tmvp). Os jogos simulados tambem contam
# (match_stats.simulate, RNG privado com semente do jogo: placares e economia nao mudam).
PSTAT_KEYS = ("sg", "sa", "smvp", "tg", "ta", "tmvp")
PSTAT_MAX = 10 ** 6
# Horas de uso (campo "hours", substitui a idade em anos do save v2). 1 ano antigo = 1000 h, 18 anos = 0 h.
# Sobem HOURS_MATCH por partida para cada titular (todos os jogos, assistidos e simulados) e HOURS_SEASON para
# todo robo na virada da temporada (titular de temporada inteira: 14 x 50 + 300 = ~1000 h, como 1 ano).
HOURS_MATCH, HOURS_SEASON = 50, 300
HOURS_MAX = 10 ** 6
FACTORY_HOURS = (0, 2000)                        # repostos chegam "de fabrica"
RECYCLE_SURE, RECYCLE_MAYBE, RECYCLE_P = 18_000, 16_000, 0.4
# Fases (evolucao do overall na virada da temporada, a mesma curva da idade antiga): (inicio em h, nome, delta)
PHASES = [(0, "Amaciando", (0, 4)), (5_000, "Auge", (-1, 2)), (11_000, "Desgaste", (-3, 0)),
          (16_000, "Fim de vida", (-4, -1))]
# Revisao (oficina, so o clube do jogador): tira REV_HOURS, sem deixar abaixo de REV_FLOOR (nao vira "novo"),
# 1 por robo por temporada (marca "rev_season" no robo). Preco: max(REV_MIN_PRICE, 25% do valor base).
REV_HOURS, REV_FLOOR, REV_MIN_PRICE, REV_SHARE = 3_000, 5_000, 100_000, 0.25

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
    """Nome exibido do robo (os nomes ja sao curtos; corta so lixo comprido de save)."""
    return str(full)[:RN.NAME_MAX]


def base_value(p):
    """Valor base (so pelo overall, sem o multiplicador de uso)."""
    return (p["ovr"] / 100) ** 4 * 4_000_000


def value(p):
    """Valor de mercado de um robo (novinho vale mais, gasto vale menos)."""
    base = base_value(p)
    h = p["hours"]
    if h <= 4_000:
        base *= 1.3
    elif h >= 14_000:
        base *= 0.6
    elif h >= 11_000:
        base *= 0.85
    return max(20_000, int(round(base, -3)))


def _value_age(p):
    """value() da carreira v2 (por idade): so a migracao do save antigo usa (vende excedentes como na v2)."""
    base = base_value(p)
    if p["age"] <= 22:
        base *= 1.3
    elif p["age"] >= 32:
        base *= 0.6
    elif p["age"] >= 29:
        base *= 0.85
    return max(20_000, int(round(base, -3)))


def hours_from_age(age, pid):
    """Idade antiga (anos) -> horas de uso: (idade-18) x 1000 + variacao deterministica pelo id (+-300)."""
    v = (pid * 37) % 600 - 300 if _is_int(pid) else 0
    return int(clamp((age - 18) * 1000 + v, 0, HOURS_MAX))


def phase_index(hours):
    k = 0
    for i, (start, _, _) in enumerate(PHASES):
        if hours >= start:
            k = i
    return k


def phase_name(hours):
    return PHASES[phase_index(hours)][1]


def fmt_hours(h):
    """'850 h' abaixo de 1000; senao '7,2 mil h' (1 casa, truncada; virgula decimal)."""
    h = max(0, int(h))
    if h < 1000:
        return "%d h" % h
    return "%d,%d mil h" % (h // 1000, (h % 1000) // 100)


def revision_price(p):
    return max(REV_MIN_PRICE, int(round(base_value(p) * REV_SHARE, -3)))


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


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _valid_clubs(clubs, key="hours"):
    """Estrutura minima dos elencos (o que rating/mercado/migracao usam). O nome nao entra: lixo vira o do id.
    key: "hours" (save v3) ou "age" (saves antigos, antes da migracao)."""
    if not isinstance(clubs, list):
        return False
    for club in clubs:
        if not isinstance(club, dict) or not isinstance(club.get("squad"), list) or not club["squad"]:
            return False
        if not isinstance(club.get("lineup"), list) or not _is_int(club.get("money")):
            return False
        for p in club["squad"]:
            if not (isinstance(p, dict) and _is_int(p.get("id")) and p.get("pos") in POS_PT
                    and _is_int(p.get("ovr")) and _is_int(p.get(key))):
                return False
    return True


class Career:
    FIELDS = ("season", "round", "clubs", "divs", "fixtures", "user", "market",
              "log", "last_results", "last_fin", "form", "next_id", "history", "formation", "ver")
    # "formation": formacao do clube do jogador (id de formations.FORMATIONS). Campo opcional: save antigo sem
    # ele (ou com id invalido) carrega com a padrao ("equilibrada"). "ver": versao do save (VERSION; ausente = save
    # antigo, migrado no load).

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
        self.formation = formations.DEFAULT
        self.ver = VERSION
        self.last_stats = None          # estatisticas do ultimo jogo do jogador (so memoria; nao vai ao save)

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

    def gen_player(self, pos, ovr, age=None, squad=(), hours=None):
        """Robo novo. O nome sai do id (robot_names, sem RNG) e nao repete os do `squad` onde ele entra.
        Uso: `hours` direto ou a `age` sorteada como antes (18-34) convertida por hours_from_age (mesma forca e
        valor dos times de sempre)."""
        pid = self.next_id
        if hours is None:
            hours = hours_from_age(age if age else random.randint(18, 34), pid)
        p = {"id": pid, "name": RN.unique_name(pid, {q["name"] for q in squad}),
             "pos": pos, "ovr": int(clamp(ovr, 28, 95)), "hours": int(hours)}
        self.next_id += 1
        return p

    @staticmethod
    def pick_squad(pool, n_extra):
        """Indices (em ordem) dos robos da peneira que formam o elenco: os 5 titulares (melhor eff por vaga, como
        auto_lineup), o melhor goleiro reserva e os n_extra reservas de linha de maior overall."""
        used = []
        for slot in SLOTS:
            used.append(max((k for k in range(len(pool)) if k not in used), key=lambda k: eff(pool[k], slot)))
        rest = sorted((k for k in range(len(pool)) if k not in used), key=lambda k: (-pool[k]["ovr"], k))
        gk = [k for k in rest if pool[k]["pos"] == "GK"][:1]
        field = [k for k in rest if pool[k]["pos"] != "GK"][:n_extra]
        return sorted(used + gk + field)

    def gen_club(self, name, color, div):
        base = DIV_BASE[div] + random.randint(-5, 5)
        pool = [{"pos": pos, "ovr": int(clamp(base + random.randint(-9, 9), 28, 95)), "age": random.randint(18, 34)}
                for pos, n in SCOUT for _ in range(n)]
        squad = []
        for k in self.pick_squad(pool, random.randint(*CPU_EXTRA_RANGE)):
            squad.append(self.gen_player(pool[k]["pos"], pool[k]["ovr"], pool[k]["age"], squad=squad))
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
        cfg = {"name": club["name"], "color": tuple(club["color"]), "squad": squad}
        if idx == self.user and self.formation != formations.DEFAULT:   # padrao: cfg de sempre (motor legado)
            cfg["formation"] = self.formation
        return cfg

    def set_formation(self, fid):
        """Formacao do clube do jogador (so muda as posicoes no motor). True se mudou."""
        if fid not in formations.FORMATIONS:
            return False
        self.formation = fid
        return True

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
        if self.user in (h, a) and self.formation != formations.DEFAULT:   # efeito medido da formacao
            df = formations.sim_df(self.formation, self.rating(self.clubs[self.user]))
            if h == self.user:
                ah, dh = ah + df, dh + df
            else:
                aa, da = aa + df, da + df
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
                self.wear_lineups(h, a)
        for i, club in enumerate(self.clubs):
            wage = int(0.004 * sum(value(p) for p in club["squad"]))
            club["money"] -= wage
            if i == self.user:
                self.last_fin["wages"] = wage
        self.round += 1
        if self.round < ROUNDS:
            self.market_refresh()

    def wear_lineups(self, *idxs):
        """+HOURS_MATCH para cada titular dos clubes que jogaram."""
        for i in idxs:
            for p in self.lineup_players(self.clubs[i]):
                p["hours"] = min(HOURS_MAX, p["hours"] + HOURS_MATCH)

    # ------------------------------------------------------- estatisticas (match_stats)
    def player_by_id(self, club_idx, pid):
        for p in self.clubs[club_idx]["squad"]:
            if p["id"] == pid:
                return p
        return None

    def credit_stats(self, mstats, h, a):
        """Soma gols/assistencias/MVP de uma partida (resumo de match_stats) nos jogadores dos 2 clubes."""
        mvp = mstats.get("mvp")
        for i, row in enumerate(mstats.get("players") or ()):
            g, ast, mv = int(row.get("g", 0)), int(row.get("a", 0)), 1 if i == mvp else 0
            if not (g or ast or mv):
                continue
            p = self.player_by_id(h if row.get("team") == 0 else a, row.get("pid"))
            if p is None:
                continue
            for ks, kt, v in (("sg", "tg", g), ("sa", "ta", ast), ("smvp", "tmvp", mv)):
                p[ks] = min(PSTAT_MAX, int(p.get(ks, 0)) + v)
                p[kt] = min(PSTAT_MAX, int(p.get(kt, 0)) + v)

    def round_stats(self, user_stats=None):
        """Depois de play_round: estatisticas de todos os jogos da rodada (o do jogador assistido vem do motor;
        os demais sao estimados com RNG privado). Guarda o do jogador em last_stats."""
        self.last_stats = None
        for r in self.last_results:
            h, a, hg, ag = r["h"], r["a"], r["hg"], r["ag"]
            mine = self.user in (h, a)
            st = user_stats if (mine and isinstance(user_stats, dict)) else None
            if st is None:
                seed = MS.seed_of("career", self.season, self.round, h, a, hg, ag)
                st = MS.sim_cfgs(random.Random(seed), (hg, ag), self.match_cfg(h), self.match_cfg(a))
            self.credit_stats(st, h, a)
            if mine:
                self.last_stats = st

    def scorers(self, d, n=10):
        """Artilharia da temporada na divisao d: [(nome, clube, cor, gols, assist., mvp, do_jogador)]."""
        rows = []
        for idx in self.divs[d]:
            club = self.clubs[idx]
            for p in club["squad"]:
                g, a = int(p.get("sg", 0)), int(p.get("sa", 0))
                if g or a:
                    rows.append((short_name(p["name"]), club["name"], tuple(club["color"]), g, a,
                                 int(p.get("smvp", 0)), idx == self.user))
        rows.sort(key=lambda e: (-e[3], -e[4], -e[5], e[0], e[1]))
        return rows[:n]

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
            pos = random.choice([p for p, n in MARKET_POS for _ in range(n)])
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
            return False, "Elenco cheio (máx. %d robôs). Venda algum." % MAX_SQUAD
        p = e["p"]
        if e["club"] >= 0:
            src = self.clubs[e["club"]]
            src["squad"].remove(p)
            src["money"] += price
            repl = self.gen_player(p["pos"], p["ovr"] - random.randint(6, 14),
                                   squad=src["squad"], hours=random.randint(*FACTORY_HOURS))
            src["squad"].append(repl)
            self.auto_lineup(src)
        p["name"] = RN.unique_name(p["id"], {q["name"] for q in u["squad"]}) if any(
            q["name"] == p["name"] for q in u["squad"]) else p["name"]
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
            return False, "Elenco mínimo: %d robôs." % MIN_SQUAD
        if p["pos"] == "GK" and sum(q["pos"] == "GK" for q in u["squad"]) <= 1:
            return False, "Você precisa de pelo menos 1 goleiro."
        price = int(value(p) * 0.8)
        u["squad"].remove(p)
        u["money"] += price
        self.fix_lineup(u)
        msg = "%s vendido por %s." % (short_name(p["name"]), fmt_money(price))
        self.add_log(msg)
        return True, msg

    # ------------------------------------------------------------- revisao
    def revision_check(self, pid):
        """(pode, preco, motivo) da revisao de um robo do clube do jogador."""
        u = self.clubs[self.user]
        p = next((q for q in u["squad"] if q["id"] == pid), None)
        if p is None:
            return False, 0, "Robô não está no seu elenco."
        price = revision_price(p)
        if p["hours"] <= REV_FLOOR:
            return False, price, "Revisão só acima de %s de uso." % fmt_hours(REV_FLOOR)
        if p.get("rev_season") == self.season:
            return False, price, "%s já foi revisado nesta temporada." % short_name(p["name"])
        if u["money"] < price:
            return False, price, "Dinheiro insuficiente para a revisão (%s)." % fmt_money(price)
        return True, price, ""

    def revise(self, pid):
        """Revisao: tira REV_HOURS de uso (nunca abaixo de REV_FLOOR), 1 por temporada. Nao muda o overall."""
        ok, price, why = self.revision_check(pid)
        if not ok:
            return False, why
        u = self.clubs[self.user]
        p = next(q for q in u["squad"] if q["id"] == pid)
        before = p["hours"]
        p["hours"] = max(REV_FLOOR, before - REV_HOURS)
        p["rev_season"] = self.season
        u["money"] -= price
        msg = "%s revisado por %s: %s -> %s de uso." % (short_name(p["name"]), fmt_money(price),
                                                         fmt_hours(before), fmt_hours(p["hours"]))
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
                "up": [], "down": [], "top_scorer": (self.scorers(u_div, 1) or [None])[0]}
        for club in self.clubs:                          # artilharia da temporada zera (a da carreira fica)
            for p in club["squad"]:
                for k in ("sg", "sa", "smvp"):
                    p.pop(k, None)
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
        """Virada da temporada: +HOURS_SEASON de uso para todo robo, evolucao do overall pela fase e reciclagem
        (>= 18 mil h certo, >= 16 mil h com 40%); quem vai para a reciclagem da lugar a um robo de fabrica."""
        for i, club in enumerate(self.clubs):
            avg = sum(p["ovr"] for p in club["squad"]) / len(club["squad"])
            for p in club["squad"][:]:
                p["hours"] = min(HOURS_MAX, p["hours"] + HOURS_SEASON)
                h = p["hours"]
                p["ovr"] = int(clamp(p["ovr"] + random.randint(*PHASES[phase_index(h)][2]), 28, 95))
                if h >= RECYCLE_SURE or (h >= RECYCLE_MAYBE and random.random() < RECYCLE_P):
                    club["squad"].remove(p)
                    club["squad"].append(self.gen_player(
                        p["pos"], avg - 8 + random.randint(-5, 5), squad=club["squad"],
                        hours=random.randint(*FACTORY_HOURS)))
                    if i == self.user:
                        info["retired"].append(short_name(p["name"]))
                        self.add_log("%s foi para a reciclagem." % short_name(p["name"]))
            if i == self.user:
                self.fix_lineup(club)
            else:
                self.auto_lineup(club)

    # ------------------------------------------------------ migração (save antigo)
    @staticmethod
    def trim_squad(club):
        """Reduz o elenco a MAX_SQUAD: ficam os titulares e os melhores reservas (overall, depois valor, depois
        id); se nenhum goleiro sobrar, o melhor goleiro excedente entra no lugar do pior reserva mantido.
        Devolve os excedentes (removidos do clube)."""
        squad = club["squad"]
        if len(squad) <= MAX_SQUAD:
            return []
        starters = [p for p in squad if p["id"] in club["lineup"]]
        bench = sorted((p for p in squad if p["id"] not in club["lineup"]),
                       key=lambda p: (-p["ovr"], -(value(p) if "hours" in p else _value_age(p)), p["id"]))
        keep_bench = bench[:MAX_SQUAD - len(starters)]
        out = bench[MAX_SQUAD - len(starters):]
        if keep_bench and not any(p["pos"] == "GK" for p in starters + keep_bench):
            gk = next((p for p in out if p["pos"] == "GK"), None)
            if gk is not None:
                out.remove(gk)
                out.append(keep_bench.pop())
                keep_bench.append(gk)
        keep = {p["id"] for p in starters + keep_bench}
        club["squad"] = [p for p in squad if p["id"] in keep]
        return out

    def migrate_v1(self):
        """Save antigo (sem "ver"): nomes de pessoa e elencos de 12-20 -> robôs e elencos de até 10.
        - todo robô ganha o nome de robô do seu id (robot_names, determinístico; sem repetir no clube);
        - elencos acima de 10: trim_squad (titulares + melhores reservas). No clube do jogador os excedentes são
          vendidos pelo valor de mercado (value(), cheio) e o dinheiro entra no caixa; nos da CPU saem do elenco;
        - mercado: robôs de clube passam a apontar para o robô do elenco (some quem saiu); os sem clube são
          renomeados; o noticiário antigo (com nomes de pessoa) dá lugar ao aviso da migração.
        Estatísticas (sg/tg...) ficam no dict de cada robô mantido, ligadas ao id. Não grava nada."""
        sold, earned = 0, 0
        for i, club in enumerate(self.clubs):
            if i == self.user:
                self.fix_lineup(club)
            elif len(club["lineup"]) != 5 or any(pid not in {p["id"] for p in club["squad"]}
                                                  for pid in club["lineup"]):
                self.auto_lineup(club)
            out = self.trim_squad(club)
            if i == self.user and out:
                sold, earned = len(out), sum(_value_age(p) for p in out)
                club["money"] += earned
            taken = set()
            for p in sorted(club["squad"], key=lambda q: q["id"]):
                p["name"] = RN.unique_name(p["id"], taken)
                taken.add(p["name"])
        market = []
        for e in self.market:
            if e["club"] >= 0:
                p = self.player_by_id(e["club"], e["p"]["id"])
                if p is None:
                    continue
                e["p"] = p
            else:
                e["p"]["name"] = RN.name_for(e["p"]["id"])
            market.append(e)
        self.market = market
        self.log = []
        if sold:
            self.add_log("%d robôs excedentes vendidos por %s (elenco máx. %d)." % (sold, fmt_money(earned), MAX_SQUAD))
        self.add_log("Seu elenco agora é de robôs aspiradores: de %d a %d por time." % (MIN_SQUAD, MAX_SQUAD))
        self.ver = 2
        return sold, earned

    def migrate_v2(self):
        """Save v2 (idade em anos) -> v3 (horas de uso): hours = (idade-18) x 1000 + variacao pelo id (+-300),
        minimo 0; o campo "age" sai. Elencos e mercado (robos sem clube tambem). Overall nao muda. Nao grava."""
        def conv(p):
            if not isinstance(p, dict):
                return
            if "hours" not in p and _is_int(p.get("age")):
                p["hours"] = hours_from_age(p["age"], p.get("id"))
            p.pop("age", None)
        for club in self.clubs:
            for p in club["squad"]:
                conv(p)
        for e in self.market if isinstance(self.market, list) else ():
            if isinstance(e, dict):
                conv(e.get("p"))
        self.add_log("Idade dos robôs virou HORAS DE USO. Revise os mais gastos no ELENCO.")
        self.ver = VERSION

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
            data = json.loads(text)
            for k in cls.FIELDS:          # só campos conhecidos (save corrompido não sobrescreve métodos)
                if k in data:
                    setattr(c, k, data[k])
            if c.user is not None and not (isinstance(c.user, int) and 0 <= c.user < len(c.clubs)):
                return None               # save inconsistente
            ver = data.get("ver")
            ver = ver if _is_int(ver) else 1
            if not _valid_clubs(c.clubs, "hours" if ver >= 3 else "age"):
                return None               # elenco quebrado: nao migra nem carrega (o save fica como esta)
            c.formation = formations.clean(c.formation)   # campo opcional: ausente/invalido -> padrao
            if ver < 2:
                c.migrate_v1()            # save antigo: so em memoria (grava no proximo save normal)
            if ver < 3:
                c.migrate_v2()            # idade -> horas de uso (idem)
            c.clean_market()
            for club in c.clubs if isinstance(c.clubs, list) else ():   # estatisticas opcionais: lixo -> zero
                sq = club.get("squad") if isinstance(club, dict) else None
                for p in sq if isinstance(sq, list) else ():
                    if not isinstance(p, dict):
                        continue
                    if not isinstance(p.get("name"), str) or not p["name"]:
                        p["name"] = RN.name_for(p.get("id"))
                    p["hours"] = int(clamp(p["hours"], 0, HOURS_MAX))
                    if "rev_season" in p and not _is_int(p["rev_season"]):
                        p.pop("rev_season")
                    for k in PSTAT_KEYS:
                        if k in p:
                            v = p[k]
                            ok = isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= PSTAT_MAX
                            if not ok:
                                p[k] = 0
            return c
        except Exception as ex:  # noqa: BLE001
            print("save load error:", ex)
            return None

    def clean_market(self):
        """Mercado do save: robos de clube apontam para o robo do elenco (sai quem nao esta mais la); sem clube
        precisam de pos/overall/horas validos (lixo sai do mercado)."""
        market = []
        for e in self.market if isinstance(self.market, list) else ():
            if not isinstance(e, dict) or not _is_int(e.get("club")) or not isinstance(e.get("p"), dict):
                continue
            p = e["p"]
            if e["club"] >= 0:
                if e["club"] >= len(self.clubs) or e["club"] == self.user:
                    continue
                p = self.player_by_id(e["club"], p.get("id"))
                if p is None:
                    continue
                e["p"] = p
            elif not (_is_int(p.get("id")) and p.get("pos") in POS_PT and _is_int(p.get("ovr"))
                      and _is_int(p.get("hours")) and p["hours"] >= 0):
                continue
            market.append(e)
        self.market = market

    @staticmethod
    def has_save():
        return _store_get() is not None
