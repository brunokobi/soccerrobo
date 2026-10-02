# -*- coding: utf-8 -*-
"""Garagem do modo robos: elenco, pecas, XP, loja e recompensas.

Modulo puro: sem pygame e sem random global (todo RNG entra como random.Random
injetado). Robos e pecas sao dicts simples, prontos para JSON. A persistencia
(save/load/sanitize) e do passo 5 e estende esta classe.
"""
import copy
import json
import math
import os
import random

import parts
import robots
import store

# --- constantes de balanceamento -------------------------------------------------
LEVEL_STEP = 1.1
OC_BAT = (0, 6, 14)
OC_MUL = (1.0, 1.15, 1.30)
OC_NAMES = ("NORMAL", "TURBO", "OVERDRIVE")
MAX_LEVEL = 10
BASE_OVR = 46   # starter (Disco, sem bonus de papel de chassis): compensa ~-10 pts vs chassis de papel do oponente
MIN_SQUAD, MAX_SQUAD = 5, 8
MAX_INVENTORY = 200
TIER_MUL = (1.0, 1.5, 2.2, 3.2)
TIER_OVR = (42, 50, 58, 66)
ROBOT_PRICES = (150, 250, 400, 650)
START_SCRAP = 150
LINEUP_SLOTS = ("GK", "DEF", "MID", "MID", "ATT")
SLOT_PT = ("GOL", "DEF", "MEI", "MEI", "ATA")
ROLES = ("GK", "DEF", "MID", "ATT")
ROLE_CHASSIS = robots.ROLE_CHASSIS
CHASSIS_ROLE = {"Goleiro": "GK", "Tanque": "DEF", "Disco": "MID", "Velocista": "ATT",
                "Orbital": "MID", "Titã": "DEF"}
# desbloqueio ao concluir o tier (qualquer posicao)
CHASSIS_UNLOCK = {0: ("Tanque",), 1: ("Velocista",), 2: ("Goleiro",), 3: ("Orbital", "Titã")}
START_CHASSIS = ("Disco",)

# recompensas de partida
SCRAP_WIN, SCRAP_DRAW, SCRAP_LOSS = 50, 30, 15
SCRAP_PER_GOAL, SCRAP_GOAL_CAP = 5, 5
XP_BASE, XP_WIN, XP_DRAW, XP_GOAL = 20, 15, 7, 10
XP_RESERVE_PCT = 0.30
DROP_CHANCE = 0.20

# loja
SHOP_COMMONS = 6
EPIC_CHANCE, EPIC_MIN_TIER = 0.25, 1
LEGEND_CHANCE, LEGEND_MIN_TIER = 0.10, 3

ROBOT_NAMES = ("Zumbi", "Faísca", "Bolt", "Turbo", "Mecha", "Pixel", "Sucata", "Raio",
               "Ferrugem", "Cometa", "Chispa", "Rolo", "Gatilho", "Trovão", "Magnus",
               "Tico", "Bibi", "Neon", "Cacto", "Bits")
PAINT_PALETTE = ((230, 60, 60), (255, 140, 40), (255, 215, 60), (110, 220, 90),
                 (30, 190, 150), (0, 200, 255), (60, 120, 255), (140, 90, 255),
                 (230, 90, 220), (240, 240, 240), (150, 160, 175), (60, 70, 90))
TEAM_COLOR = (0, 170, 255)
NAME_MAX_ROBOT, NAME_MAX_TEAM = 12, 16
NAME_MAX_LEAGUE_TEAM = 24     # nomes gerados da liga (ex.: "Engrenagem Atlética")

FIELDS = ("scrap", "next_id", "team", "robots", "lineup", "inventory", "unlocked",
          "tier_done", "league", "shop", "stats", "flags")
VERSION = 1
SAVE_KEY = "soccerpy_robots_v1"
SAVE_PATH = os.path.join(os.path.expanduser("~"), ".soccerpy_robots.json")
MAX_SAVE_CHARS = 2_000_000
SCRAP_MAX = 10_000_000
ID_MAX = 10 ** 9
MAX_FLAGS, FLAG_KEY_MAX = 64, 32
SHOP_MAX = 16
LEAGUE_TEAMS, LEAGUE_ROUNDS = 6, 10          # espelha robot_league (evita import circular)
# status de load_status()
SAVE_NONE, SAVE_OK, SAVE_BAD = "none", "ok", "bad"
# migracoes: {versao_de_origem: fn(dict) -> dict da versao seguinte}, aplicadas antes do sanitize
MIGRATIONS = {}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# --- atributos efetivos -----------------------------------------------------------
def effective_attrs(robot, pieces_by_id):
    """Atributos efetivos (ints 20..99, na ordem de robots.ATTRS). Nao muta o robo."""
    oc = clamp(int(robot.get("oc", 0)), 0, 2)
    ocm = OC_MUL[oc]
    raw = {a: float(robot["base"][a]) + LEVEL_STEP * (robot.get("level", 1) - 1)
           for a in robots.ATTRS}
    bat_extra = 0.0
    for slot in parts.SLOTS:
        pid = robot.get("slots", {}).get(slot)
        pc = pieces_by_id.get(pid) if pid is not None else None
        if pc is None or parts.part_slot(pc) != slot:
            continue
        for a, v in parts.part_bonus(pc["model"], pc["rar"], pc["lvl"]).items():
            if a == "bat":
                bat_extra += v
            else:
                raw[a] += ocm * v
        bat_extra -= parts.part_heat(pc["model"], pc["rar"], pc["lvl"])
    raw["bat"] += bat_extra - OC_BAT[oc]
    return {a: int(clamp(round(raw[a]), robots.ATTR_MIN, robots.ATTR_MAX))
            for a in robots.ATTRS}


def team_rating(robot_list, pieces_by_id):
    """Forca da equipe: media da media dos atributos efetivos dos robos, x100."""
    if not robot_list:
        return 0.0
    tot = sum(robots.mean_attr(effective_attrs(r, pieces_by_id)) for r in robot_list)
    return tot / len(robot_list) * 100.0


def match_entry(robot, pieces_by_id):
    """Entrada de elenco aceita por soccer.Team (modo robos)."""
    return {"name": robot["name"], "attrs": effective_attrs(robot, pieces_by_id),
            "chassis": robot["chassis"], "pid": robot["id"], "paint": tuple(robot["paint"])}


# --- XP -----------------------------------------------------------------------------
def xp_need(level):
    """XP para ir do nivel `level` ao seguinte."""
    return 40 + 25 * (level - 1) + 5 * (level - 1) ** 2


def xp_to_next(robot):
    """XP que falta para o proximo nivel (0 no nivel maximo)."""
    if robot["level"] >= MAX_LEVEL:
        return 0
    return xp_need(robot["level"]) - robot["xp"]


def add_xp(robot, amount):
    """Soma XP (xp guarda o resto dentro do nivel); devolve niveis ganhos."""
    gained = 0
    amount = max(0, int(amount))
    if robot["level"] >= MAX_LEVEL:
        robot["xp"] = 0
        return 0
    robot["xp"] += amount
    while robot["level"] < MAX_LEVEL and robot["xp"] >= xp_need(robot["level"]):
        robot["xp"] -= xp_need(robot["level"])
        robot["level"] += 1
        gained += 1
    if robot["level"] >= MAX_LEVEL:
        robot["xp"] = 0
    return gained


class Garage:
    FIELDS = FIELDS

    def __init__(self):
        self.scrap = 0
        self.next_id = 1
        self.team = {"name": "Meu Time", "color": list(TEAM_COLOR)}
        self.robots = []
        self.lineup = []
        self.inventory = []
        self.unlocked = list(START_CHASSIS)
        self.tier_done = -1
        self.league = None
        self.shop = {"stock": [], "seed": 0}
        self.stats = {"played": 0, "w": 0, "d": 0, "l": 0, "titles": 0}
        self.flags = {}

    # ---------------------------------------------------------------- serializacao
    def to_dict(self):
        d = {"v": VERSION}
        for f in FIELDS:
            d[f] = copy.deepcopy(getattr(self, f))
        return d

    # ---------------------------------------------------------------- persistencia
    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=True, separators=(",", ":"))

    @staticmethod
    def sanitize(data):
        """Dict (qualquer coisa vinda do JSON) -> dict limpo com exatamente VERSION+FIELDS,
        ou None se irrecuperavel. Nunca levanta."""
        try:
            return _sanitize(data)
        except Exception as ex:  # noqa: BLE001
            print("sanitize error:", ex)
            return None

    @classmethod
    def from_dict(cls, data):
        """Garage a partir de um dict (migra, sanitiza). None se invalido. So usa FIELDS."""
        data = _migrate(data)
        clean = cls.sanitize(data)
        if clean is None:
            return None
        g = cls()
        for f in FIELDS:
            setattr(g, f, clean[f])
        return g

    def save(self):
        """Grava em SAVE_KEY; so grava um Garage valido. True se gravou."""
        try:
            if Garage.sanitize(self.to_dict()) is None:
                return False
            return bool(_store_set(self.to_json()))
        except Exception as ex:  # noqa: BLE001
            print("save error:", ex)
            return False

    @classmethod
    def load(cls):
        """Garage salvo ou None (ausente ou incompativel). Save invalido NUNCA e
        sobrescrito: o texto cru vai para `<SAVE_KEY>.bad`. Veja load_status()."""
        g, status, raw = _load_core()
        if status == SAVE_BAD and raw is not None:
            _store_set_bad(raw)
        return g

    @staticmethod
    def load_status():
        """"none" (sem save), "ok" (carregavel) ou "bad" (existe mas incompativel). Sem efeitos."""
        return _load_core()[1]

    @staticmethod
    def has_save():
        return _store_get() is not None

    # ---------------------------------------------------------------- consultas
    def robot(self, rid):
        for r in self.robots:
            if r["id"] == rid:
                return r
        return None

    def piece(self, pid):
        for p in self.inventory:
            if p["id"] == pid:
                return p
        return None

    def pieces_by_id(self):
        return {p["id"]: p for p in self.inventory}

    def equipped_by(self, pid):
        """Robo que usa a peca (ou None)."""
        for r in self.robots:
            if pid in r["slots"].values():
                return r
        return None

    def equipped_ids(self):
        return {pid for r in self.robots for pid in r["slots"].values() if pid is not None}

    def free_pieces(self, slot=None):
        used = self.equipped_ids()
        return [p for p in self.inventory if p["id"] not in used
                and (slot is None or parts.part_slot(p) == slot)]

    def attrs_of(self, robot):
        return effective_attrs(robot, self.pieces_by_id())

    def lineup_robots(self):
        return [self.robot(i) for i in self.lineup]

    def rating(self):
        return team_rating(self.lineup_robots(), self.pieces_by_id())

    def entry(self, robot):
        return match_entry(robot, self.pieces_by_id())

    def match_cfg(self):
        """Config de time para Game.start_robot_match (lado do usuario)."""
        pb = self.pieces_by_id()
        return {"name": self.team["name"], "color": tuple(self.team["color"]),
                "squad": [match_entry(self.robot(i), pb) for i in self.lineup]}

    def new_id(self):
        i = self.next_id
        self.next_id += 1
        return i

    def new_piece(self, model, rar, lvl=0):
        return {"id": self.new_id(), "model": model, "rar": rar, "lvl": lvl}

    def make_robot(self, name, role, chassis, base_ovr=BASE_OVR, paint=None):
        rid = self.new_id()
        return {"id": rid, "name": name, "chassis": chassis, "role": role, "level": 1,
                "xp": 0,
                "paint": list(paint if paint is not None else self.team["color"]),
                "base": robots.from_overall(base_ovr, role, chassis, seed=rid),
                "slots": {s: None for s in parts.SLOTS}, "oc": 0}

    def tier(self):
        """Tier da proxima liga: o seguinte ao ultimo concluido (3 e o teto)."""
        return clamp(self.tier_done + 1, 0, len(TIER_OVR) - 1)

    # ---------------------------------------------------------------- equipar
    def equip(self, rid, pid, slot=None):
        r, p = self.robot(rid), self.piece(pid)
        if r is None:
            return False, "Robô não encontrado."
        if p is None:
            return False, "Peça não encontrada."
        ps = parts.part_slot(p)
        if slot is not None and slot != ps:
            return False, "Essa peça não encaixa no slot %s." % parts.SLOT_NAMES.get(slot, slot)
        other = self.equipped_by(pid)
        if other is not None:
            return False, "Peça já equipada em %s." % other["name"]
        r["slots"][ps] = pid
        return True, "%s equipado em %s." % (parts.part_name(p), r["name"])

    def unequip(self, rid, slot):
        r = self.robot(rid)
        if r is None:
            return False, "Robô não encontrado."
        if slot not in parts.SLOTS:
            return False, "Slot inválido."
        if r["slots"].get(slot) is None:
            return False, "Slot vazio."
        r["slots"][slot] = None
        return True, "Peça removida."

    def upgrade(self, pid):
        p = self.piece(pid)
        if p is None:
            return False, "Peça não encontrada."
        cost = parts.upgrade_cost(p["rar"], p["lvl"])
        if cost is None:
            return False, "Peça já está no nível máximo (+%d)." % parts.MAX_UP
        if self.scrap < cost:
            return False, "Sucata insuficiente (precisa de %d)." % cost
        self.scrap -= cost
        p["lvl"] += 1
        return True, "%s melhorada por %d sucata." % (parts.part_name(p), cost)

    def buy_part(self, pid):
        stock = self.shop["stock"]
        p = next((x for x in stock if x["id"] == pid), None)
        if p is None:
            return False, "Peça não está à venda."
        if len(self.inventory) >= MAX_INVENTORY:
            return False, "Inventário cheio."
        price = parts.buy_price(p)
        if self.scrap < price:
            return False, "Sucata insuficiente (precisa de %d)." % price
        self.scrap -= price
        stock.remove(p)
        self.inventory.append(p)
        return True, "Comprou %s por %d." % (parts.part_name(p), price)

    def sell_part(self, pid):
        p = self.piece(pid)
        if p is None:
            return False, "Peça não encontrada."
        other = self.equipped_by(pid)
        if other is not None:
            return False, "Desequipe a peça de %s antes de vender." % other["name"]
        v = parts.sell_price(p)
        self.inventory.remove(p)
        self.scrap += v
        return True, "Vendeu %s por %d." % (parts.part_name(p), v)

    # ---------------------------------------------------------------- robo
    def rename(self, rid, name):
        r = self.robot(rid)
        if r is None:
            return False, "Robô não encontrado."
        name = str(name).strip()
        if not name:
            return False, "Nome vazio."
        if len(name) > NAME_MAX_ROBOT:
            return False, "Nome longo demais (máx %d)." % NAME_MAX_ROBOT
        try:
            name.encode("latin-1")
        except UnicodeEncodeError:
            return False, "Nome tem caracteres inválidos."
        if not name.isprintable():
            return False, "Nome tem caracteres inválidos."
        r["name"] = name
        return True, "Robô renomeado para %s." % name

    def set_paint(self, rid, rgb):
        r = self.robot(rid)
        if r is None:
            return False, "Robô não encontrado."
        try:
            c = [int(v) for v in rgb]
        except (TypeError, ValueError):
            return False, "Cor inválida."
        if len(c) != 3 or any(v < 0 or v > 255 for v in c):
            return False, "Cor inválida."
        r["paint"] = c
        return True, "Pintura aplicada."

    def set_oc(self, rid, level):
        r = self.robot(rid)
        if r is None:
            return False, "Robô não encontrado."
        if level not in (0, 1, 2):
            return False, "Overclock inválido."
        r["oc"] = level
        if level:
            return True, "Overclock %s: bateria gasta mais." % OC_NAMES[level]
        return True, "Overclock desligado."

    # ---------------------------------------------------------------- escalacao
    def swap_lineup(self, slot, rid):
        """Poe o robo `rid` no slot da escalacao. Se ele ja e titular, troca de lugar
        com o ocupante; se e reserva, o ocupante vai para o banco."""
        if not (0 <= slot < len(self.lineup)):
            return False, "Slot inválido."
        if self.robot(rid) is None:
            return False, "Robô não encontrado."
        if self.lineup[slot] == rid:
            return False, "Já está nesse slot."
        if rid in self.lineup:
            j = self.lineup.index(rid)
            self.lineup[slot], self.lineup[j] = self.lineup[j], self.lineup[slot]
        else:
            self.lineup[slot] = rid
        return True, "Escalação alterada."

    def auto_lineup(self):
        """Melhor robo por slot (forca efetiva, com preferencia pelo papel do robo)."""
        pb = self.pieces_by_id()
        score = {r["id"]: robots.mean_attr(effective_attrs(r, pb)) * 100.0 for r in self.robots}
        used, out = set(), []
        for role in LINEUP_SLOTS:
            cand = [r for r in self.robots if r["id"] not in used]
            if not cand:
                break
            best = max(cand, key=lambda r: (score[r["id"]] + (5.0 if r["role"] == role else 0.0),
                                            -r["id"]))
            used.add(best["id"])
            out.append(best["id"])
        self.lineup = out
        return True, "Escalação automática aplicada."

    def robot_price(self):
        return ROBOT_PRICES[clamp(self.tier_done + 1, 0, len(ROBOT_PRICES) - 1)]

    def buy_robot(self, chassis, role=None, rng=None):
        if chassis not in self.unlocked or chassis not in robots.CHASSIS:
            return False, "Chassis bloqueado."
        if len(self.robots) >= MAX_SQUAD:
            return False, "Elenco cheio (máx %d)." % MAX_SQUAD
        price = self.robot_price()
        if self.scrap < price:
            return False, "Sucata insuficiente (precisa de %d)." % price
        role = role or CHASSIS_ROLE.get(chassis, "MID")
        if role not in ROLES:
            return False, "Papel inválido."
        taken = {r["name"] for r in self.robots}
        free = [n for n in ROBOT_NAMES if n not in taken]
        if free and rng is not None:
            name = rng.choice(free)
        elif free:
            name = free[0]
        else:
            name = ("Robô %d" % self.next_id)[:NAME_MAX_ROBOT]
        self.scrap -= price
        rb = self.make_robot(name, role, chassis)
        self.robots.append(rb)
        return True, "%s (%s) entrou para o time por %d." % (name, chassis, price)

    # ---------------------------------------------------------------- loja
    def refresh_shop(self, tier, rng):
        """Novo estoque: 6 Comuns, 1 Rara garantida, Epica 25% (tier>=1), Lendaria 10% (tier>=3)."""
        seed = rng.getrandbits(31)
        r = random.Random(seed)
        stock = [self.new_piece(r.choice(parts.MODELS), 0) for _ in range(SHOP_COMMONS)]
        stock.append(self.new_piece(r.choice(parts.MODELS), 1))
        if tier >= EPIC_MIN_TIER and r.random() < EPIC_CHANCE:
            stock.append(self.new_piece(r.choice(parts.MODELS), 2))
        if tier >= LEGEND_MIN_TIER and r.random() < LEGEND_CHANCE:
            stock.append(self.new_piece(r.choice(parts.MODELS), 3))
        self.shop = {"stock": stock, "seed": seed}
        return stock


# --- novo jogo ---------------------------------------------------------------------
_STARTER_MODELS = ("Borracha", "Célula Longa", "Chip de CPU", "Motor Escovado", "Solenoide")


def new_game(rng, team_name="Meu Time"):
    """Starter kit: 150 sucata, 5 robos base_ovr BASE_OVR (GK,DEF,MID,MID,ATT, todos Disco),
    cada um ja com uma peca Comum equilibrada equipada, loja do tier 0."""
    g = Garage()
    g.scrap = START_SCRAP
    g.team["name"] = team_name[:NAME_MAX_TEAM]
    names = rng.sample(ROBOT_NAMES, len(LINEUP_SLOTS))
    for name, role in zip(names, LINEUP_SLOTS):
        g.robots.append(g.make_robot(name, role, START_CHASSIS[0]))
    for rb, model in zip(g.robots, _STARTER_MODELS):
        pc = g.new_piece(model, 0)
        g.inventory.append(pc)
        rb["slots"][parts.part_slot(pc)] = pc["id"]
    g.lineup = [r["id"] for r in g.robots]
    g.refresh_shop(0, rng)
    return g


# --- recompensas -------------------------------------------------------------------
def match_rewards(garage, my_goals, opp_goals, scorer_pids, tier, rng):
    """Calcula E APLICA as recompensas de uma partida do usuario.

    Devolve {"result","scrap","xp":{rid:int},"levels":{rid:int},"drop":piece|None}.
    Determinístico dado (estado, entradas, rng).
    """
    tier = clamp(int(tier), 0, len(TIER_MUL) - 1)
    if my_goals > opp_goals:
        res, base, bonus = "w", SCRAP_WIN, XP_WIN
    elif my_goals == opp_goals:
        res, base, bonus = "d", SCRAP_DRAW, XP_DRAW
    else:
        res, base, bonus = "l", SCRAP_LOSS, 0
    scrap = int(round((base + SCRAP_PER_GOAL * min(my_goals, SCRAP_GOAL_CAP)) * TIER_MUL[tier]))
    goals = {}
    for pid in scorer_pids or ():
        goals[pid] = goals.get(pid, 0) + 1
    xp, levels = {}, {}
    starters = set(garage.lineup)
    for r in garage.robots:
        if r["id"] in starters:
            amt = XP_BASE + bonus + XP_GOAL * goals.get(r["id"], 0)
        else:
            amt = int((XP_BASE + bonus) * XP_RESERVE_PCT)
        xp[r["id"]] = amt
        levels[r["id"]] = add_xp(r, amt)
    garage.scrap += scrap
    drop = None
    if res == "w" and rng.random() < DROP_CHANCE and len(garage.inventory) < MAX_INVENTORY:
        drop = garage.new_piece(rng.choice(parts.MODELS), 0)
        garage.inventory.append(drop)
    st = garage.stats
    st["played"] += 1
    st[res] += 1
    return {"result": res, "scrap": scrap, "xp": xp, "levels": levels, "drop": drop}


# --- persistencia: armazenamento (monkeypatchavel nos testes) -----------------------
def _store_get():
    return store.read(SAVE_KEY, SAVE_PATH)


def _store_set(text):
    return store.write(SAVE_KEY, SAVE_PATH, text)


def _store_set_bad(text):
    return store.write(SAVE_KEY + ".bad", SAVE_PATH + ".bad", text)


def _load_core():
    """(Garage|None, status, texto_cru|None)."""
    raw = _store_get()
    if raw is None:
        return None, SAVE_NONE, None
    try:
        if not isinstance(raw, str) or len(raw) > MAX_SAVE_CHARS:
            return None, SAVE_BAD, raw if isinstance(raw, str) else None
        g = Garage.from_dict(json.loads(raw))
    except Exception:  # noqa: BLE001  (JSON invalido, recursao, etc.)
        g = None
    if g is None:
        return None, SAVE_BAD, raw
    return g, SAVE_OK, raw


def _migrate(data):
    """Aplica MIGRATIONS ate VERSION. Devolve o dict migrado ou None."""
    if not isinstance(data, dict):
        return None
    v = data.get("v")
    if not _is_int(v) or v < 1 or v > VERSION:
        return None
    while v < VERSION:
        fn = MIGRATIONS.get(v)
        if fn is None:
            return None
        try:
            data = fn(data)
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(data, dict):
            return None
        v += 1
    return data


# --- persistencia: coercao e limites -------------------------------------------------
def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _int(v, lo, hi, default):
    """Coage int/float finito/str numerica para int limitado; senao `default`."""
    try:
        if isinstance(v, bool):
            return default
        if isinstance(v, str):
            v = v.strip()
            if len(v) > 20:
                return default
            v = float(v) if ("." in v or "e" in v.lower()) else int(v)
        if isinstance(v, float):
            if not math.isfinite(v):
                return default
            v = int(v)
        if not isinstance(v, int):
            return default
    except (ValueError, OverflowError, TypeError):
        return default
    return max(lo, min(hi, v))


def _strict_int(v, lo, hi):
    """int exato (sem coagir) dentro de [lo, hi]; senao None."""
    if _is_int(v) and lo <= v <= hi:
        return v
    return None


def _num(v):
    """float finito (int/float, nao bool) ou None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    try:
        f = float(v)
    except OverflowError:
        return None
    return f if math.isfinite(f) else None


def _str(v, maxlen, default):
    """str truncada, so Latin-1 imprimivel; vazia -> default."""
    if not isinstance(v, str):
        return default
    out = "".join(c for c in v[:maxlen * 4 + 64] if c.isprintable() and ord(c) < 256)
    out = out.strip()[:maxlen].strip()
    return out or default


def _color(v, default):
    if isinstance(v, (list, tuple)) and len(v) == 3:
        c = [_int(x, 0, 255, None) for x in v]
        if None not in c:
            return c
    return list(default)


def _piece(p):
    """Peca limpa ou None."""
    if not isinstance(p, dict):
        return None
    pid = _strict_int(p.get("id"), 1, ID_MAX)
    model = p.get("model")
    if pid is None or not isinstance(model, str) or model not in parts.PARTS:
        return None
    return {"id": pid, "model": model,
            "rar": _int(p.get("rar"), 0, len(parts.RARITIES) - 1, 0),
            "lvl": _int(p.get("lvl"), 0, parts.MAX_UP, 0)}


def _robot(r, team_color):
    """Robo limpo (slots ainda como candidatos) ou None."""
    if not isinstance(r, dict):
        return None
    rid = _strict_int(r.get("id"), 1, ID_MAX)
    chassis, role = r.get("chassis"), r.get("role")
    if rid is None or not isinstance(chassis, str) or chassis not in robots.CHASSIS:
        return None
    if not isinstance(role, str) or role not in ROLES:
        return None
    b = r.get("base")
    if not isinstance(b, dict):
        return None
    base = {}
    for a in robots.ATTRS:
        f = _num(b.get(a))
        if f is None:
            return None
        base[a] = int(clamp(round(f), robots.ATTR_MIN, robots.ATTR_MAX))
    level = _int(r.get("level"), 1, MAX_LEVEL, 1)
    xp = 0 if level >= MAX_LEVEL else _int(r.get("xp"), 0, xp_need(level) - 1, 0)
    slots = r.get("slots")
    slots = slots if isinstance(slots, dict) else {}
    return {"id": rid, "name": _str(r.get("name"), NAME_MAX_ROBOT, "Robô %d" % rid),
            "chassis": chassis, "role": role, "level": level, "xp": xp,
            "paint": _color(r.get("paint"), team_color), "base": base,
            "slots": {s: _strict_int(slots.get(s), 1, ID_MAX) for s in parts.SLOTS},
            "oc": _int(r.get("oc"), 0, len(OC_MUL) - 1, 0)}


def _league(lg):
    """Liga limpa ou None se inconsistente."""
    if lg is None:
        return None
    if not isinstance(lg, dict):
        return None
    tier = _strict_int(lg.get("tier"), 0, len(TIER_OVR) - 1)
    rnd = _strict_int(lg.get("round"), 0, LEAGUE_ROUNDS)
    teams, fx, res = lg.get("teams"), lg.get("fixtures"), lg.get("results")
    if tier is None or rnd is None:
        return None
    if not (isinstance(teams, list) and len(teams) == LEAGUE_TEAMS):
        return None
    if not (isinstance(fx, list) and len(fx) == LEAGUE_ROUNDS):
        return None
    if not isinstance(res, list) or len(res) > LEAGUE_ROUNDS * LEAGUE_TEAMS // 2:
        return None
    out_teams = []
    for t in teams:
        if not isinstance(t, dict):
            return None
        ovr, seed = _strict_int(t.get("ovr"), 0, 99), _strict_int(t.get("seed"), 0, ID_MAX)
        if ovr is None or seed is None:
            return None
        out_teams.append({"name": _str(t.get("name"), NAME_MAX_LEAGUE_TEAM, "Time"),
                          "color": _color(t.get("color"), TEAM_COLOR), "ovr": ovr, "seed": seed})
    out_fx = []
    for rd in fx:
        if not (isinstance(rd, list) and len(rd) == LEAGUE_TEAMS // 2):
            return None
        pairs, seen = [], set()
        for pr in rd:
            if not (isinstance(pr, (list, tuple)) and len(pr) == 2):
                return None
            h, a = _strict_int(pr[0], 0, LEAGUE_TEAMS - 1), _strict_int(pr[1], 0, LEAGUE_TEAMS - 1)
            if h is None or a is None or h == a or h in seen or a in seen:
                return None
            seen.update((h, a))
            pairs.append([h, a])
        out_fx.append(pairs)
    out_res, keys = [], set()
    for x in res:
        if not (isinstance(x, (list, tuple)) and len(x) == 5):
            return None
        r_, h, a = (_strict_int(x[0], 0, LEAGUE_ROUNDS - 1), _strict_int(x[1], 0, LEAGUE_TEAMS - 1),
                    _strict_int(x[2], 0, LEAGUE_TEAMS - 1))
        hg, ag = _strict_int(x[3], 0, 99), _strict_int(x[4], 0, 99)
        if None in (r_, h, a, hg, ag) or h == a or r_ > rnd or [h, a] not in out_fx[r_]:
            return None
        if (r_, h, a) in keys:
            return None
        keys.add((r_, h, a))
        out_res.append([r_, h, a, hg, ag])
    return {"tier": tier, "teams": out_teams, "fixtures": out_fx, "round": rnd,
            "results": out_res}


def _sanitize(data):
    if not isinstance(data, dict) or not _is_int(data.get("v")) or not (1 <= data["v"] <= VERSION):
        return None
    tm = data.get("team")
    tm = tm if isinstance(tm, dict) else {}
    team = {"name": _str(tm.get("name"), NAME_MAX_TEAM, "Meu Time"),
            "color": _color(tm.get("color"), TEAM_COLOR)}
    # pecas (inventario): ids unicos, modelo conhecido, <=200
    inv_raw = data.get("inventory")
    inventory, ids = [], set()
    for p in (inv_raw[:MAX_INVENTORY * 2] if isinstance(inv_raw, list) else []):
        pc = _piece(p)
        if pc is not None and pc["id"] not in ids and len(inventory) < MAX_INVENTORY:
            ids.add(pc["id"])
            inventory.append(pc)
    # robos: ids unicos, <=8
    rb_raw = data.get("robots")
    if not isinstance(rb_raw, list):
        return None
    robot_list, rids = [], set()
    for r in rb_raw[:MAX_SQUAD * 4]:
        rb = _robot(r, team["color"])
        if rb is not None and rb["id"] not in rids and len(robot_list) < MAX_SQUAD:
            rids.add(rb["id"])
            robot_list.append(rb)
    if len(robot_list) < MIN_SQUAD:
        return None
    # slots: peca existente, do slot certo e ainda nao equipada
    by_id = {p["id"]: p for p in inventory}
    used = set()
    for rb in robot_list:
        for s in parts.SLOTS:
            pid = rb["slots"][s]
            pc = by_id.get(pid) if pid is not None else None
            if pc is None or parts.part_slot(pc) != s or pid in used:
                rb["slots"][s] = None
            else:
                used.add(pid)
    # loja: pecas com ids que nao colidem com inventario
    sh = data.get("shop")
    sh = sh if isinstance(sh, dict) else {}
    stock = []
    st_raw = sh.get("stock")
    for p in (st_raw[:SHOP_MAX * 2] if isinstance(st_raw, list) else []):
        pc = _piece(p)
        if pc is not None and pc["id"] not in ids and len(stock) < SHOP_MAX:
            ids.add(pc["id"])
            stock.append(pc)
    shop = {"stock": stock, "seed": _int(sh.get("seed"), 0, 2 ** 31 - 1, 0)}
    # demais campos
    un_raw = data.get("unlocked")
    unlocked = list(START_CHASSIS)
    for c in (un_raw[:32] if isinstance(un_raw, list) else []):
        if isinstance(c, str) and c in robots.CHASSIS and c not in unlocked:
            unlocked.append(c)
    s_raw = data.get("stats")
    s_raw = s_raw if isinstance(s_raw, dict) else {}
    stats = {k: _int(s_raw.get(k), 0, ID_MAX, 0) for k in ("played", "w", "d", "l", "titles")}
    flags = {}
    f_raw = data.get("flags")
    if isinstance(f_raw, dict):
        for k, v in list(f_raw.items())[:MAX_FLAGS * 2]:
            key = _str(k, FLAG_KEY_MAX, "")
            val = _int(v, -ID_MAX, ID_MAX, None)
            if key and val is not None and len(flags) < MAX_FLAGS:
                flags[key] = val
    max_id = max([r["id"] for r in robot_list] + list(ids))
    clean = {"v": VERSION,
             "scrap": _int(data.get("scrap"), 0, SCRAP_MAX, 0),
             "next_id": max(_int(data.get("next_id"), 1, ID_MAX, 1), max_id + 1),
             "team": team, "robots": robot_list, "lineup": [], "inventory": inventory,
             "unlocked": unlocked,
             "tier_done": _int(data.get("tier_done"), -1, len(TIER_OVR) - 1, -1),
             "league": _league(data.get("league")), "shop": shop, "stats": stats,
             "flags": flags}
    # escalacao: 5 ids distintos de robos existentes; senao automatica
    lu = data.get("lineup")
    ok = (isinstance(lu, list) and len(lu) == len(LINEUP_SLOTS)
          and all(_is_int(i) and i in rids for i in lu) and len(set(lu)) == len(lu))
    if ok:
        clean["lineup"] = list(lu)
    else:
        tmp = Garage()
        tmp.robots, tmp.inventory = robot_list, inventory
        tmp.auto_lineup()
        clean["lineup"] = tmp.lineup
    return clean
