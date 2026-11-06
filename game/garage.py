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
import skills
import store

# --- constantes de balanceamento -------------------------------------------------
LEVEL_STEP = 1.1
OC_BAT = (0, 6, 14)
OC_MUL = (1.0, 1.15, 1.30)
OC_NAMES = ("NORMAL", "TURBO", "OVERDRIVE")
MAX_LEVEL = 10                 # teto do Modo Robos (Garage.cap padrao)
CAMPAIGN_CAP = 15              # teto da campanha (Garage.cap = 15 a partir do Ato 2)
MOD_ON_TIER = 0                # Modo Robos: modulos/skills ligam ao concluir o tier 1 (indice 0)
BASE_OVR = 46   # starter (Disco, sem bonus de papel de chassis): compensa ~-10 pts vs chassis de papel do oponente
MIN_SQUAD, MAX_SQUAD = 5, 8
MAX_INVENTORY = 200
# tiers 0-3: Modo Robos e Ato 1; 4-6: so a campanha (Ato 2/3, C9; spec secao 10). As 4 primeiras nao mudam.
TIER_MUL = (1.0, 1.5, 2.2, 3.2, 4.2, 5.2, 6.4)
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
# C9: chances (Epica, Lendaria) da loja nos tiers da campanha 4-6; ate o tier 3 vale o par acima (o stream
# do RNG da loja nao muda)
SHOP_CHANCE_BY_TIER = {4: (0.35, 0.18), 5: (0.45, 0.25), 6: (0.55, 0.32)}
# B16 (spec 7.3: modulos vem da loja e de drops): com mod_on a loja ganha 1 Modulo e 1 drop em
# MODULE_DROP_SHARE vira Modulo. Sorteios num RNG DERIVADO (seed ^ sal), nunca no stream da loja/drops:
# sem mod_on (Ato 1, Modo Robos antes do tier 1) tudo fica identico ao da v1.
MODULE_SHOP_SALT = 0x6D6F64            # "mod"
MODULE_SHOP_RAR = ((0, 0.55), (1, 0.30), (2, 0.15))   # raridade do Modulo da loja (Lendaria: tier >= 3)
MODULE_LEGEND_CHANCE = 0.05
MODULE_DROP_SHARE = 0.25

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
          "tier_done", "league", "shop", "stats", "flags", "items", "cosmetics", "cap", "tactic")
# v2 (Fase 4/B3): slot "modulo", robo.skills/look, items, cosmetics, cap, tactic, MAX_FLAGS 128.
VERSION = 2
SAVE_KEY = "soccerpy_robots_v1"
SAVE_PATH = os.path.join(os.path.expanduser("~"), ".soccerpy_robots.json")
MAX_SAVE_CHARS = 2_000_000
SCRAP_MAX = 10_000_000
ID_MAX = 10 ** 9
MAX_FLAGS, FLAG_KEY_MAX = 128, 32
MOD_FLAG = "mod_on"           # flag de sistema: slot Modulo/skills liberados
SHOP_MAX = 16
LEAGUE_TEAMS, LEAGUE_ROUNDS = 6, 10          # espelha robot_league (evita import circular)
# status de load_status()
SAVE_NONE, SAVE_OK, SAVE_BAD = "none", "ok", "bad"
# migracoes: {versao_de_origem: fn(dict) -> dict da versao seguinte}, aplicadas antes do sanitize
MIGRATIONS = {}


def _migrate_v1(d):
    """v1 -> v2: so ACRESCENTA (nada e removido nem renomeado). Robos ganham slots.modulo=None,
    skills (PH retroativos = nivel-1), look={}; o garage ganha items={}, cosmetics=[], cap=10,
    tactic padrao; flag mod_on se o tier 1 ja foi concluido (a campanha re-deriva o flag dela).
    Entradas estranhas passam como estao (o sanitize limpa depois)."""
    d = copy.deepcopy(d)
    for r in d.get("robots") if isinstance(d.get("robots"), list) else ():
        if not isinstance(r, dict):
            continue
        if isinstance(r.get("slots"), dict):
            r["slots"].setdefault("modulo", None)
        lv = _int(r.get("level"), 1, MAX_LEVEL, 1)
        r.setdefault("skills", {"learned": {}, "equipped": [], "pts": skills.ph_for_level(lv)})
        r.setdefault("look", {})
    d.setdefault("items", {})
    d.setdefault("cosmetics", [])
    d.setdefault("cap", MAX_LEVEL)
    d.setdefault("tactic", skills.DEFAULT_TACTIC)
    td = d.get("tier_done")
    fl = d.get("flags")
    if _is_int(td) and td >= MOD_ON_TIER and isinstance(fl, dict):
        fl.setdefault(MOD_FLAG, 1)
    d["v"] = 2
    return d


MIGRATIONS[1] = _migrate_v1


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
    models = []
    for slot in parts.SLOTS:
        pid = robot.get("slots", {}).get(slot)
        pc = pieces_by_id.get(pid) if pid is not None else None
        if pc is None or parts.part_slot(pc) != slot:
            continue
        models.append(pc["model"])
        for a, v in parts.part_bonus(pc["model"], pc["rar"], pc["lvl"]).items():
            if a == "bat":
                bat_extra += v
            else:
                raw[a] += ocm * v
        bat_extra -= parts.part_heat(pc["model"], pc["rar"], pc["lvl"])
    # sets (B2): bonus fixo por faixa (2/3/4 pecas), fora do multiplicador de overclock
    set_attrs, _passives = parts.set_bonus(parts.set_counts(models))
    for a, v in set_attrs.items():
        if a == "bat":
            bat_extra += v
        else:
            raw[a] += v
    raw["bat"] += bat_extra - OC_BAT[oc]
    return {a: int(clamp(round(raw[a]), robots.ATTR_MIN, robots.ATTR_MAX))
            for a in robots.ATTRS}


def team_rating(robot_list, pieces_by_id, mod_on=False):
    """Forca da equipe: media da media dos atributos efetivos dos robos, x100; com mod_on (skills
    ligadas) soma skills.team_skill_force (pontos de F calibrados no motor por tests/calib_skills.py,
    teto SK_CAP 9,0 no time). Sem mod_on (Ato 1, Modo Robos antes do tier 1) e o valor antigo exato."""
    if not robot_list:
        return 0.0
    tot = sum(robots.mean_attr(effective_attrs(r, pieces_by_id)) for r in robot_list)
    base = tot / len(robot_list) * 100.0
    if not mod_on:
        return base
    return base + skills.team_skill_force(skills.effective_skills(r, pieces_by_id, True) for r in robot_list)


def robot_set_counts(robot, pieces_by_id):
    """{set: n} das pecas equipadas no robo (para a UI: 'Faxineiro 3/4')."""
    models = []
    for slot in parts.SLOTS:
        pid = robot.get("slots", {}).get(slot)
        pc = pieces_by_id.get(pid) if pid is not None else None
        if pc is not None and parts.part_slot(pc) == slot:
            models.append(pc["model"])
    return parts.set_counts(models)


# peca -> overlay desenhado em campo (A9; a arte de cada overlay fica em robot_art.py). Modelos fora da
# tabela (motor escovado, baterias, borracha, solenoide) nao aparecem.
VIS_OVERLAY = {"Turbina": "turbina", "Canhão de Plasma": "canhao", "Blindado": "blindado",
               "Escova de Sucção": "escova", "Vácuo Turbo": "vacuo", "Radar LiDAR": "radar",
               "Infravermelho": "antena", "Chip de CPU": "modulo", "Chip Neural": "modulo"}


def robot_vis(robot, pieces_by_id):
    """Dados SO visuais do robo para a partida: {"chassis","paint","parts":((overlay, raridade),..),
    "hot"}. hot = alguma peca de calor equipada ou overclock (fumaca ao superaquecer). Nao entra na
    simulacao; Team/Player aceitam a ausencia (squads antigos e os goldens nao tem `vis`)."""
    vis_parts = []
    hot = int(robot.get("oc", 0) or 0) > 0
    for slot in parts.SLOTS:
        pid = robot.get("slots", {}).get(slot)
        pc = pieces_by_id.get(pid) if pid is not None else None
        if pc is None or parts.part_slot(pc) != slot:
            continue
        if parts.part_heat(pc["model"], pc["rar"], pc["lvl"]) > 0:
            hot = True
        nm = VIS_OVERLAY.get(pc["model"])
        if nm:
            vis_parts.append((nm, int(pc["rar"])))
    vis = {"chassis": robot["chassis"], "paint": tuple(robot["paint"]), "parts": tuple(sorted(vis_parts)),
           "hot": hot}
    look = robot.get("look")
    if look:                                  # B13: cosmeticos (so desenho); ausente = sem cosmetico
        vis["look"] = dict(look)
    return vis


def match_entry(robot, pieces_by_id, mod_on=False):
    """Entrada de elenco aceita por soccer.Team (modo robos). `vis` (A9) e aditivo e so visual.
    Com mod_on (B8) e alguma skill efetiva, ganha `skills` = ((id, rank, up), ...) para o motor (B6);
    sem mod_on a entrada e a antiga (o motor nao liga skills: Ato 1 e Modo Robos antes do tier 1)."""
    e = {"name": robot["name"], "attrs": effective_attrs(robot, pieces_by_id),
         "chassis": robot["chassis"], "pid": robot["id"], "paint": tuple(robot["paint"]),
         "vis": robot_vis(robot, pieces_by_id)}
    if mod_on:
        sk = skills.effective_skills(robot, pieces_by_id, True)
        if sk:
            e["skills"] = tuple(sk)
    return e


# --- XP -----------------------------------------------------------------------------
def xp_need(level):
    """XP para ir do nivel `level` ao seguinte. Do 10 em diante (so a campanha passa do 10, cap 15):
    560 + 40*(level-10) (C9; spec secao 10: 560, 600, 640, 680, 720)."""
    if level >= 10:
        return 560 + 40 * (level - 10)
    return 40 + 25 * (level - 1) + 5 * (level - 1) ** 2


def xp_to_next(robot, cap=MAX_LEVEL):
    """XP que falta para o proximo nivel (0 no nivel maximo `cap`)."""
    if robot["level"] >= cap:
        return 0
    return xp_need(robot["level"]) - robot["xp"]


def add_xp(robot, amount, cap=MAX_LEVEL):
    """Soma XP (xp guarda o resto dentro do nivel); devolve niveis ganhos. `cap` = nivel maximo
    (MAX_LEVEL=10 no Modo Robos; Garage.cap, ate CAMPAIGN_CAP=15, na campanha). Cada nivel ganho da
    skills.PH_PER_LEVEL ponto de habilidade (robo.skills.pts)."""
    gained = 0
    amount = max(0, int(amount))
    cap = clamp(int(cap), 1, CAMPAIGN_CAP)
    if robot["level"] >= cap:
        robot["xp"] = 0
        return 0
    robot["xp"] += amount
    while robot["level"] < cap and robot["xp"] >= xp_need(robot["level"]):
        robot["xp"] -= xp_need(robot["level"])
        robot["level"] += 1
        gained += 1
    if robot["level"] >= cap:
        robot["xp"] = 0
    if gained and isinstance(robot.get("skills"), dict):
        skills.grant_pts(robot, gained * skills.PH_PER_LEVEL)
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
        self.items = {}
        self.cosmetics = []
        self.cap = MAX_LEVEL
        self.tactic = skills.DEFAULT_TACTIC
        self.backpack = []            # Mochila da PROXIMA partida (transitoria: nao vai ao save; UI no B12)

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
        ou None se irrecuperavel. Versao antiga e migrada antes (MIGRATIONS). Nunca levanta."""
        try:
            return _sanitize(_migrate(data))
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
        """Grava em SAVE_KEY; so grava um Garage valido (e sem perder a liga). True se gravou."""
        try:
            clean = Garage.sanitize(self.to_dict())
            if clean is None:
                return False
            if self.league is not None and clean.get("league") is None:
                # a liga em andamento nao sobreviveria ao sanitize: nao grava (preserva o save
                # anterior em vez de apagar a liga em silencio); a UI mostra "Falha ao salvar."
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

    def mod_on(self):
        return bool(self.flags.get(MOD_FLAG))

    def xp_to_next(self, robot):
        return xp_to_next(robot, self.cap)

    def skills_of(self, robot):
        """[(id, rank, up)] efetivas do robo (o motor so as usa a partir do passo B6)."""
        return skills.effective_skills(robot, self.pieces_by_id(), self.mod_on())

    def attrs_of(self, robot):
        return effective_attrs(robot, self.pieces_by_id())

    def lineup_robots(self):
        return [self.robot(i) for i in self.lineup]

    def rating(self):
        """Forca do time (B9: com mod_on inclui a forca das skills, teto SK_CAP). Os consumiveis da
        Mochila NAO entram aqui (so na partida: match_F)."""
        return team_rating(self.lineup_robots(), self.pieces_by_id(), self.mod_on())

    def match_F(self):
        """Forca para o SIMULAR da proxima partida: rating() + item_force da Mochila (spec 5/9.2)."""
        return self.rating() + skills.item_force(self.backpack_items())

    def entry(self, robot):
        return match_entry(robot, self.pieces_by_id(), self.mod_on())

    def match_cfg(self):
        """Config de time para Game.start_robot_match (lado do usuario). Com mod_on: skills por robo e a
        tatica do time; com Mochila: `items` (consumiveis aplicados como aura pelo motor)."""
        pb = self.pieces_by_id()
        on = self.mod_on()
        cfg = {"name": self.team["name"], "color": tuple(self.team["color"]),
               "squad": [match_entry(self.robot(i), pb, on) for i in self.lineup]}
        if on:
            cfg["tactic"] = self.tactic
        items = self.backpack_items()
        if items:
            cfg["items"] = tuple(items)
        return cfg

    # ---------------------------------------------------------------- mochila (consumiveis, B8)
    def set_backpack(self, ids):
        """Escolhe ate skills.BACKPACK consumiveis distintos que o jogador TEM (items[id] > 0).
        Devolve a Mochila valida (ids desconhecidos/sem estoque/repetidos sao ignorados)."""
        out = []
        for i in ids or ():
            if i in skills.ITEMS and self.items.get(i, 0) > 0 and i not in out:
                out.append(i)
            if len(out) >= skills.BACKPACK:
                break
        self.backpack = out
        return list(out)

    def backpack_items(self):
        """Mochila valida agora (estoque pode ter mudado)."""
        out = []
        for i in self.backpack:
            if i in skills.ITEMS and self.items.get(i, 0) > 0 and i not in out:
                out.append(i)
        return out[:skills.BACKPACK]

    def consume_backpack(self):
        """Consome 1 de cada item da Mochila (partida assistida ou simulada) e a esvazia."""
        used = self.backpack_items()
        for i in used:
            self.items[i] -= 1
            if self.items[i] <= 0:
                del self.items[i]
        self.backpack = []
        return used

    # ---------------------------------------------------------------- loja de itens (B12)
    def buy_item(self, item_id):
        """Compra 1 consumivel (skills.ITEMS) com sucata; estoque max skills.ITEM_MAX por item. So com
        mod_on (itens e skills ligam juntos: decisao 6 do plano). (ok, msg)."""
        it = skills.ITEMS.get(item_id)
        if it is None:
            return False, "Item inválido."
        if not self.mod_on():
            return False, "Itens ainda bloqueados."
        have = int(self.items.get(item_id, 0))
        if have >= skills.ITEM_MAX:
            return False, "Estoque cheio (máx %d)." % skills.ITEM_MAX
        if self.scrap < it["price"]:
            return False, "Sucata insuficiente (precisa de %d)." % it["price"]
        self.scrap -= it["price"]
        self.items[item_id] = have + 1
        return True, "Comprou %s por %d (agora %d)." % (it["name"], it["price"], have + 1)

    # ---------------------------------------------------------------- cosmeticos (B13; so visuais)
    def owns_cosmetic(self, cid):
        return cid in self.cosmetics

    def grant_cosmetic(self, cid):
        """Desbloqueia um cosmetico (recompensa/conquista). True se era novo."""
        if cid not in parts.COSMETICS or cid in self.cosmetics:
            return False
        self.cosmetics.append(cid)
        return True

    def buy_cosmetic(self, cid):
        """Compra um cosmetico na LOJA (aba COSMETICOS) com sucata; cada um so uma vez. (ok, msg)."""
        if cid not in parts.COSMETICS:
            return False, "Cosmético inválido."
        name = parts.COSMETIC_NAMES[cid]
        if cid in self.cosmetics:
            return False, "Você já tem %s." % name
        if not parts.cosmetic_for_sale(cid):             # Onda D: cosmetico de recompensa
            return False, "%s não está à venda (prêmio: %s)." % (name, parts.REWARD_COSMETICS[cid])
        price = parts.cosmetic_price(cid)
        if self.scrap < price:
            return False, "Sucata insuficiente (precisa de %d)." % price
        self.scrap -= price
        self.cosmetics.append(cid)
        return True, "Comprou %s por %d. Equipe na bancada (botão VISUAL)." % (name, price)

    def equip_look(self, rid, cid):
        """Equipa um cosmetico desbloqueado no slot do tipo dele (robot["look"]). (ok, msg)."""
        r = self.robot(rid)
        if r is None:
            return False, "Robô não encontrado."
        kind = parts.COSMETIC_KIND.get(cid)
        if kind is None:
            return False, "Cosmético inválido."
        if cid not in self.cosmetics:
            return False, "Cosmético bloqueado: compre na LOJA."
        r.setdefault("look", {})[kind] = cid
        return True, "%s: %s." % (parts.LOOK_TITLES[kind], parts.COSMETIC_NAMES[cid])

    def unequip_look(self, rid, kind):
        r = self.robot(rid)
        if r is None:
            return False, "Robô não encontrado."
        if kind not in parts.LOOK_KINDS:
            return False, "Tipo inválido."
        if r.get("look", {}).pop(kind, None) is None:
            return False, "Nada equipado."
        return True, "%s: nenhum." % parts.LOOK_TITLES[kind]

    # ---------------------------------------------------------------- habilidades (B10, UI)
    def learn_skill_node(self, rid, node_id):
        """Compra um no da arvore (skills.learn_node) com os PH do robo. So com mod_on. (ok, msg)."""
        r = self.robot(rid)
        if r is None:
            return False, "Robô não encontrado."
        if not self.mod_on():
            return False, "Habilidades ainda bloqueadas."
        return skills.learn_node(r, node_id)

    def equip_skill(self, rid, sid):
        """Equipa uma skill aprendida (regras de skills.equip_skill: max MAX_EQUIPPED, carga LOAD_MAX).
        Com Modulo equipado (que ocupa 1 vaga e carga), so equipa se a skill entra de fato na partida
        (skills.effective_skills); senao desfaz e explica. (ok, msg)."""
        r = self.robot(rid)
        if r is None:
            return False, "Robô não encontrado."
        if not self.mod_on():
            return False, "Habilidades ainda bloqueadas."
        ok, msg = skills.equip_skill(r, sid)
        if not ok:
            return ok, msg
        eff = {e[0] for e in skills.effective_skills(r, self.pieces_by_id(), True)}
        if sid not in eff:
            r["skills"]["equipped"].remove(sid)
            return False, "Sem vaga: o módulo ocupa 1 vaga e conta na carga."
        return ok, msg

    def unequip_skill(self, rid, sid):
        r = self.robot(rid)
        if r is None:
            return False, "Robô não encontrado."
        return skills.unequip_skill(r, sid)

    def set_tactic(self, tactic):
        """Tatica do time (skills.TACTICS): so muda a prioridade dos gatilhos no motor. (ok, msg)."""
        if tactic not in skills.TACTICS:
            return False, "Tática inválida."
        self.tactic = tactic
        return True, "Tática: %s." % skills.TACTIC_NAMES.get(tactic, tactic)

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
                "slots": {s: None for s in parts.SLOTS}, "oc": 0,
                "skills": skills.new_robot_skills(), "look": {}}

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
        if ps == "modulo" and not self.mod_on():
            return False, "Módulos ainda bloqueados."
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
        if parts.is_unique(p["model"]):
            return False, "Relíquias não podem ser vendidas."
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
        """Novo estoque: 6 Comuns, 1 Rara garantida, Epica 25% (tier>=1), Lendaria 10% (tier>=3); nos
        tiers 4-6 da campanha as chances sobem (SHOP_CHANCE_BY_TIER, C9). Modelos: parts.shop_models(tier,
        rar) = CORE_MODELS ate o tier 3 (stream do RNG identico ao da v1), ALL_MODELS a partir do tier 4."""
        seed = rng.getrandbits(31)
        r = random.Random(seed)
        stock = [self.new_piece(r.choice(parts.shop_models(tier, 0)), 0) for _ in range(SHOP_COMMONS)]
        stock.append(self.new_piece(r.choice(parts.shop_models(tier, 1)), 1))
        epic, legend = SHOP_CHANCE_BY_TIER.get(tier, (EPIC_CHANCE, LEGEND_CHANCE))
        if tier >= EPIC_MIN_TIER and r.random() < epic:
            stock.append(self.new_piece(r.choice(parts.shop_models(tier, 2)), 2))
        if tier >= LEGEND_MIN_TIER and r.random() < legend:
            stock.append(self.new_piece(r.choice(parts.shop_models(tier, 3)), 3))
        if self.mod_on():                               # B16: 1 Modulo (RNG derivado: o resto nao muda)
            mr = random.Random(seed ^ MODULE_SHOP_SALT)
            model = mr.choice(parts.MODULE_MODELS)
            x, rar = mr.random(), 0
            if tier >= LEGEND_MIN_TIER and x < MODULE_LEGEND_CHANCE:
                rar = 3
            else:
                acc = 0.0
                for rr, pr in MODULE_SHOP_RAR:
                    acc += pr
                    rar = rr
                    if x < acc:
                        break
            stock.append(self.new_piece(model, rar))
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
def match_rewards(garage, my_goals, opp_goals, scorer_pids, tier, rng, scrap_mul=1.0, xp_mul=1.0):
    """Calcula E APLICA as recompensas de uma partida do usuario. scrap_mul/xp_mul (C9): bonus da
    campanha (escolha B2 do Ato 2); 1,0 = sem bonus (Modo Robos, Ato 1).

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
    scrap = int(round((base + SCRAP_PER_GOAL * min(my_goals, SCRAP_GOAL_CAP)) * TIER_MUL[tier] * scrap_mul))
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
        if xp_mul != 1.0:
            amt = int(round(amt * xp_mul))
        xp[r["id"]] = amt
        levels[r["id"]] = add_xp(r, amt, garage.cap)
    garage.scrap += scrap
    drop = None
    if res == "w" and rng.random() < DROP_CHANCE and len(garage.inventory) < MAX_INVENTORY:
        drop = garage.new_piece(rng.choice(parts.CORE_MODELS), 0)
        if garage.mod_on():                          # B16: parte dos drops vira Modulo (RNG derivado)
            dr = random.Random((drop["id"] * 7919) ^ MODULE_SHOP_SALT)
            if dr.random() < MODULE_DROP_SHARE:
                drop["model"] = dr.choice(parts.MODULE_MODELS)
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
    if raw is store.ERROR:                      # existe/talvez exista, mas ilegivel
        return None, SAVE_BAD, None
    if isinstance(raw, store.InvalidText):      # bytes invalidos: nunca "consertar" em silencio
        return None, SAVE_BAD, str(raw)
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
    rar = _int(p.get("rar"), 0, 10 ** 6, 0)
    if rar > parts.MYTHIC:                       # lixo acima da faixa: Lendaria, como antes da Onda D
        rar = parts.LEGEND
    if parts.is_unique(model):
        rar = parts.LEGEND                       # reliquia: sempre Lendaria
    rar = min(rar, parts.max_rarity(model))      # Onda D: Mitica so em equipamento (modulo ate Lendaria)
    return {"id": pid, "model": model, "rar": rar,
            "lvl": _int(p.get("lvl"), 0, parts.MAX_UP, 0)}


def _robot_skills(sk, level):
    """skills do robo: learned {id: rank 1..3} (so ids de skills.SKILLS), equipped (subconjunto de
    learned, sem duplicatas, <= MAX_EQUIPPED, carga <= LOAD_MAX), pts 0..PTS_MAX."""
    sk = sk if isinstance(sk, dict) else {}
    lr = sk.get("learned")
    learned = {}
    if isinstance(lr, dict):
        for k, v in list(lr.items())[:len(skills.SKILLS) * 4]:
            rk = _strict_int(v, 1, 3)
            if isinstance(k, str) and k in skills.SKILLS and rk is not None:
                learned[k] = rk
    eq_raw = sk.get("equipped")
    equipped, load = [], 0
    for k in (eq_raw[:skills.MAX_EQUIPPED * 4] if isinstance(eq_raw, list) else []):
        if not isinstance(k, str) or k not in learned or k in equipped:
            continue
        ld = skills.load_of(k, learned[k])
        if len(equipped) < skills.MAX_EQUIPPED and load + ld <= skills.LOAD_MAX:
            equipped.append(k)
            load += ld
    return {"learned": learned, "equipped": equipped,
            "pts": _int(sk.get("pts"), 0, skills.PTS_MAX, 0)}


def _look(lk):
    out = {}
    if isinstance(lk, dict):
        for kind, ids in parts.LOOK_KINDS.items():
            v = lk.get(kind)
            if isinstance(v, str) and v in ids:
                out[kind] = v
    return out


def _robot(r, team_color, cap=MAX_LEVEL):
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
    level = _int(r.get("level"), 1, cap, 1)
    xp = 0 if level >= cap else _int(r.get("xp"), 0, xp_need(level) - 1, 0)
    slots = r.get("slots")
    slots = slots if isinstance(slots, dict) else {}
    return {"id": rid, "name": _str(r.get("name"), NAME_MAX_ROBOT, "Robô %d" % rid),
            "chassis": chassis, "role": role, "level": level, "xp": xp,
            "paint": _color(r.get("paint"), team_color), "base": base,
            "slots": {s: _strict_int(slots.get(s), 1, ID_MAX) for s in parts.SLOTS},
            "oc": _int(r.get("oc"), 0, len(OC_MUL) - 1, 0),
            "skills": _robot_skills(r.get("skills"), level), "look": _look(r.get("look"))}


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
    cap = _int(data.get("cap"), MAX_LEVEL, CAMPAIGN_CAP, MAX_LEVEL)
    # pecas (inventario): ids unicos, modelo conhecido, <=200, reliquia (unique) no maximo 1
    inv_raw = data.get("inventory")
    inventory, ids, uniq = [], set(), set()
    for p in (inv_raw[:MAX_INVENTORY * 2] if isinstance(inv_raw, list) else []):
        pc = _piece(p)
        if pc is not None and pc["id"] not in ids and len(inventory) < MAX_INVENTORY \
                and pc["model"] not in uniq:
            ids.add(pc["id"])
            if parts.is_unique(pc["model"]):
                uniq.add(pc["model"])
            inventory.append(pc)
    # robos: ids unicos, <=8
    rb_raw = data.get("robots")
    if not isinstance(rb_raw, list):
        return None
    robot_list, rids = [], set()
    for r in rb_raw[:MAX_SQUAD * 4]:
        rb = _robot(r, team["color"], cap)
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
        if pc is not None and pc["rar"] > parts.LEGEND:          # Onda D: a loja nunca vende Mitica
            pc["rar"] = parts.LEGEND
        if pc is not None and pc["id"] not in ids and len(stock) < SHOP_MAX and pc["model"] not in uniq:
            ids.add(pc["id"])
            if parts.is_unique(pc["model"]):
                uniq.add(pc["model"])
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
        items_f = list(f_raw.items())[:MAX_FLAGS * 2]
        if MOD_FLAG in f_raw:                       # flag de sistema: nunca e cortado pelo limite
            items_f = [(MOD_FLAG, f_raw[MOD_FLAG])] + [kv for kv in items_f if kv[0] != MOD_FLAG]
        for k, v in items_f:
            key = _str(k, FLAG_KEY_MAX, "")
            val = _int(v, -ID_MAX, ID_MAX, None)
            if key and val is not None and len(flags) < MAX_FLAGS:
                flags[key] = val
    it_raw = data.get("items")
    items = {}
    if isinstance(it_raw, dict):
        for k, v in list(it_raw.items())[:len(skills.ITEMS) * 4]:
            q = _int(v, 0, skills.ITEM_MAX, 0)
            if isinstance(k, str) and k in skills.ITEMS and q > 0:
                items[k] = q
    co_raw = data.get("cosmetics")
    cosmetics = []
    for c in (co_raw[:len(parts.COSMETICS) * 4] if isinstance(co_raw, list) else []):
        if isinstance(c, str) and c in parts.COSMETICS and c not in cosmetics:
            cosmetics.append(c)
    owned = set(cosmetics)
    for rb in robot_list:                         # look so com cosmeticos desbloqueados (B13)
        rb["look"] = {k: v for k, v in rb["look"].items() if v in owned}
    tactic = data.get("tactic")
    if not (isinstance(tactic, str) and tactic in skills.TACTICS):
        tactic = skills.DEFAULT_TACTIC
    max_id = max([r["id"] for r in robot_list] + list(ids))
    clean = {"v": VERSION,
             "scrap": _int(data.get("scrap"), 0, SCRAP_MAX, 0),
             "next_id": max(_int(data.get("next_id"), 1, ID_MAX, 1), max_id + 1),
             "team": team, "robots": robot_list, "lineup": [], "inventory": inventory,
             "unlocked": unlocked,
             "tier_done": _int(data.get("tier_done"), -1, len(TIER_OVR) - 1, -1),
             "league": _league(data.get("league")), "shop": shop, "stats": stats,
             "flags": flags, "items": items, "cosmetics": cosmetics, "cap": cap, "tactic": tactic}
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
