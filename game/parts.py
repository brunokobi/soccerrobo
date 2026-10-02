# -*- coding: utf-8 -*-
"""Catalogo de pecas do modo robos (puro: sem pygame e sem random global)."""

SLOTS = ("motor", "bateria", "parachoque", "chutador", "succao", "sensor", "chip")
SLOT_NAMES = {"motor": "Motor", "bateria": "Bateria", "parachoque": "Parachoque",
              "chutador": "Chutador", "succao": "Sucção", "sensor": "Sensor", "chip": "Chip"}

MAX_UP = 5

# raridade -> nome / cor / POWER / UP_STEP / PRICE
RARITIES = (
    {"name": "Comum", "color": (190, 200, 210), "power": 4, "up_step": 0.8, "price": 60},
    {"name": "Rara", "color": (0, 170, 255), "power": 8, "up_step": 1.2, "price": 220},
    {"name": "Épica", "color": (190, 110, 255), "power": 12, "up_step": 1.6, "price": 700},
    {"name": "Lendária", "color": (255, 200, 60), "power": 19, "up_step": 2.0, "price": 2200},
)
POWER = tuple(r["power"] for r in RARITIES)
UP_STEP = tuple(r["up_step"] for r in RARITIES)
PRICE = tuple(r["price"] for r in RARITIES)
RAR_NAMES = tuple(r["name"] for r in RARITIES)
RAR_COLORS = tuple(r["color"] for r in RARITIES)

# modelo -> slot, pesos por atributo (o primeiro = primario), heat (dreno de bat; 0 = nenhum)
PARTS = {
    "Motor Escovado":    {"slot": "motor", "w": {"vel": 1.0, "ace": 0.4}, "heat": 0.0},
    "Turbina":           {"slot": "motor", "w": {"vel": 1.3, "ace": 0.6}, "heat": 0.35},
    "Célula Longa":      {"slot": "bateria", "w": {"bat": 1.0, "def": 0.2}, "heat": 0.0},
    "Célula Rápida":     {"slot": "bateria", "w": {"bat": 0.7, "ace": 0.5}, "heat": 0.0},
    "Borracha":          {"slot": "parachoque", "w": {"def": 1.0, "ctr": 0.3}, "heat": 0.0},
    "Blindado":          {"slot": "parachoque", "w": {"def": 1.3, "ctr": 0.3}, "heat": 0.3},
    "Solenoide":         {"slot": "chutador", "w": {"chu": 1.0, "ctr": 0.3}, "heat": 0.0},
    "Canhão de Plasma":  {"slot": "chutador", "w": {"chu": 1.3, "ctr": 0.3}, "heat": 0.35},
    "Escova de Sucção":  {"slot": "succao", "w": {"ctr": 1.0, "def": 0.3}, "heat": 0.0},
    "Vácuo Turbo":       {"slot": "succao", "w": {"ctr": 1.3, "def": 0.3}, "heat": 0.3},
    "Infravermelho":     {"slot": "sensor", "w": {"vis": 1.0, "ctr": 0.3}, "heat": 0.0},
    "Radar LiDAR":       {"slot": "sensor", "w": {"vis": 1.3, "ctr": 0.3}, "heat": 0.25},
    "Chip de CPU":       {"slot": "chip", "w": {"qi": 1.0, "vis": 0.3}, "heat": 0.0},
    "Chip Neural":       {"slot": "chip", "w": {"qi": 1.3, "vis": 0.3}, "heat": 0.3},
}
MODELS = tuple(PARTS)
BALANCED_MODELS = tuple(m for m in PARTS if PARTS[m]["heat"] == 0.0)


def models_for_slot(slot):
    return [m for m in PARTS if PARTS[m]["slot"] == slot]


def part_power(rar, lvl):
    return POWER[rar] + UP_STEP[rar] * lvl


def part_bonus(model, rar, lvl):
    """Bonus por atributo (ints) da peca: round(peso * (POWER + UP_STEP * lvl))."""
    p = part_power(rar, lvl)
    return {a: int(round(w * p)) for a, w in PARTS[model]["w"].items()}


def part_heat(model, rar, lvl):
    """Calor (float) subtraido de bat; 0 para modelos nao agressivos."""
    return PARTS[model]["heat"] * part_power(rar, lvl)


def upgrade_cost(rar, lvl):
    """Custo de lvl -> lvl+1 (PRICE*0.3*(lvl+1)); None se ja esta no MAX_UP."""
    if lvl >= MAX_UP:
        return None
    return int(round(PRICE[rar] * 0.3 * (lvl + 1)))


def part_name(piece):
    return "%s %s +%d" % (piece["model"], RAR_NAMES[piece["rar"]], piece["lvl"])


def part_slot(piece):
    return PARTS[piece["model"]]["slot"]


def buy_price(piece):
    return PRICE[piece["rar"]]


def sell_price(piece):
    """Venda = 50% do preco da raridade (upgrades nao voltam)."""
    return PRICE[piece["rar"]] // 2


def bonus_text(piece):
    """Texto compacto 'VEL+8 ACE+3 BAT-3' (bonus liquido, calor em BAT)."""
    b = part_bonus(piece["model"], piece["rar"], piece["lvl"])
    h = part_heat(piece["model"], piece["rar"], piece["lvl"])
    bits = ["%s+%d" % (a.upper(), v) for a, v in b.items() if v]
    if h > 0:
        bits.append("BAT-%d" % int(round(h)))
    return " ".join(bits)
