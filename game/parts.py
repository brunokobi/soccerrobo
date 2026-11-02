# -*- coding: utf-8 -*-
"""Catalogo de pecas do modo robos (puro: sem pygame e sem random global).

Fase 4 / Onda B (docs/specs/itens-e-habilidades.md):
* CORE_MODELS = os 14 modelos originais, NA MESMA ORDEM (o stream do RNG da loja e dos drops depende
  disso: `r.choice(CORE_MODELS)` sorteia exatamente o que `r.choice(MODELS)` sorteava). MODELS e alias.
* ALL_MODELS = CORE + os 16 novos (30 modelos de equipamento em 7 slots). A loja so usa ALL_MODELS a
  partir do tier SHOP_ALL_TIER (4); o "Chip Zero" (`legend_only`) so sai como Lendaria.
* RELIC_MODELS = 6 reliquias (`unique`: no maximo 1 de cada no save, sempre Lendaria, potencia fixa 22,
  nao compraveis nem vendaveis).
* MODULE_MODELS = 12 modulos (slot "modulo", `w` vazio, `skill` = id em skills.SKILLS).
* `set` opcional: bonus de conjunto (SETS, set_bonus, set_bonus_text).
"""

GEAR_SLOTS = ("motor", "bateria", "parachoque", "chutador", "succao", "sensor", "chip")
SLOTS = GEAR_SLOTS + ("modulo",)
SLOT_NAMES = {"motor": "Motor", "bateria": "Bateria", "parachoque": "Parachoque",
              "chutador": "Chutador", "succao": "Sucção", "sensor": "Sensor", "chip": "Chip",
              "modulo": "Módulo"}

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
LEGEND = len(RARITIES) - 1
RELIC_POWER = 22                       # reliquias: potencia fixa (Lendaria comum = 19)
MODULE_RANK = (1, 1, 2, 3)             # raridade do modulo -> rank da skill
SHOP_ALL_TIER = 4                      # tier a partir do qual a loja sorteia ALL_MODELS

# modelo -> slot, pesos por atributo (o primeiro = primario), heat (dreno de bat; 0 = nenhum)
# campos opcionais: set, kind (tipo de design), legend_only, unique (+ power, passive), skill (modulos)
PARTS = {
    # --- 14 originais (CORE_MODELS: nao mudar a ordem) ---
    "Motor Escovado":    {"slot": "motor", "w": {"vel": 1.0, "ace": 0.4}, "heat": 0.0},
    "Turbina":           {"slot": "motor", "w": {"vel": 1.3, "ace": 0.6}, "heat": 0.35, "set": "Plasma"},
    "Célula Longa":      {"slot": "bateria", "w": {"bat": 1.0, "def": 0.2}, "heat": 0.0},
    "Célula Rápida":     {"slot": "bateria", "w": {"bat": 0.7, "ace": 0.5}, "heat": 0.0, "set": "Limpex"},
    "Borracha":          {"slot": "parachoque", "w": {"def": 1.0, "ctr": 0.3}, "heat": 0.0, "set": "Faxineiro"},
    "Blindado":          {"slot": "parachoque", "w": {"def": 1.3, "ctr": 0.3}, "heat": 0.3, "set": "Titã"},
    "Solenoide":         {"slot": "chutador", "w": {"chu": 1.0, "ctr": 0.3}, "heat": 0.0},
    "Canhão de Plasma":  {"slot": "chutador", "w": {"chu": 1.3, "ctr": 0.3}, "heat": 0.35, "set": "Plasma"},
    "Escova de Sucção":  {"slot": "succao", "w": {"ctr": 1.0, "def": 0.3}, "heat": 0.0, "set": "Faxineiro"},
    "Vácuo Turbo":       {"slot": "succao", "w": {"ctr": 1.3, "def": 0.3}, "heat": 0.3, "set": "Titã"},
    "Infravermelho":     {"slot": "sensor", "w": {"vis": 1.0, "ctr": 0.3}, "heat": 0.0, "set": "Dojo"},
    "Radar LiDAR":       {"slot": "sensor", "w": {"vis": 1.3, "ctr": 0.3}, "heat": 0.25, "set": "Limpex"},
    "Chip de CPU":       {"slot": "chip", "w": {"qi": 1.0, "vis": 0.3}, "heat": 0.0, "set": "Dojo"},
    "Chip Neural":       {"slot": "chip", "w": {"qi": 1.3, "vis": 0.3}, "heat": 0.3},
    # --- 16 novos (spec secao 1) ---
    "Servo Ágil":        {"slot": "motor", "w": {"ace": 1.0, "vel": 0.4}, "heat": 0.0,
                          "kind": "equilibrado", "set": "Faxineiro"},
    "Ímã Linear":        {"slot": "motor", "w": {"vel": 1.5, "ace": 0.5}, "heat": 0.45,
                          "kind": "agressivo", "set": "Plasma"},
    "Célula Solar":      {"slot": "bateria", "w": {"bat": 1.2, "vel": 0.1}, "heat": 0.0,
                          "kind": "equilibrado", "set": "Faxineiro"},
    # Celula Fusao (decisao do dev, B6-B9): sidegrade de pico - muita ACE (arranque) com calor alto, o
    # que deixa a BAT LIQUIDA abaixo de todas as baterias (drena mais). Antes (bat 1,5 ace 0,4 def 0,2)
    # empatava em BAT liquido e dominava a Celula Longa/Rapida.
    "Célula Fusão":      {"slot": "bateria", "w": {"bat": 1.1, "ace": 0.8}, "heat": 0.5,
                          "kind": "agressivo", "set": "Plasma"},
    "Espuma Viscoelástica": {"slot": "parachoque", "w": {"def": 0.7, "ctr": 0.7}, "heat": 0.0,
                             "kind": "especialista", "set": "Faxineiro"},
    "Placa Reativa":     {"slot": "parachoque", "w": {"def": 1.5, "ctr": 0.3}, "heat": 0.4,
                          "kind": "agressivo", "set": "Titã"},
    "Mola Dupla":        {"slot": "chutador", "w": {"chu": 0.8, "vis": 0.4, "ctr": 0.2}, "heat": 0.0,
                          "kind": "especialista", "set": "Dojo"},
    "Railgun de Bolso":  {"slot": "chutador", "w": {"chu": 1.6, "ctr": 0.3}, "heat": 0.45,
                          "kind": "agressivo", "set": "Plasma"},
    "Escova Dupla":      {"slot": "succao", "w": {"ctr": 0.8, "vel": 0.3, "def": 0.3}, "heat": 0.0,
                          "kind": "especialista", "set": "Faxineiro"},
    "Vórtice":           {"slot": "succao", "w": {"ctr": 1.5, "def": 0.3}, "heat": 0.35,
                          "kind": "agressivo", "set": "Titã"},
    "Câmera Dupla":      {"slot": "sensor", "w": {"vis": 0.7, "qi": 0.5, "ctr": 0.2}, "heat": 0.0,
                          "kind": "especialista", "set": "Dojo"},
    "Sonar Quântico":    {"slot": "sensor", "w": {"vis": 1.5, "qi": 0.3}, "heat": 0.35,
                          "kind": "agressivo", "set": "Plasma"},
    "Chip Tático":       {"slot": "chip", "w": {"qi": 0.8, "ctr": 0.5}, "heat": 0.0,
                          "kind": "equilibrado", "set": "Dojo"},
    "Chip Zero":         {"slot": "chip", "w": {"qi": 1.6, "vis": 0.4}, "heat": 0.4,
                          "kind": "agressivo", "set": "Limpex", "legend_only": True},
    "Motor Torque":      {"slot": "motor", "w": {"vel": 0.6, "ace": 0.6, "def": 0.3}, "heat": 0.0,
                          "kind": "especialista", "set": "Titã"},
    "Solenoide Duplo":   {"slot": "chutador", "w": {"chu": 1.1, "ctr": 0.3}, "heat": 0.15,
                          "kind": "meio-termo", "set": "Limpex"},
    # --- reliquias (spec secao 4): unicas, Lendaria de potencia fixa, passiva propria ---
    "Rodinha Esquerda do Zé": {"slot": "motor", "w": {"vel": 1.2, "ace": 0.6}, "heat": 0.0,
                               "unique": True, "power": RELIC_POWER, "passive": "rolando"},
    "Chip do Vovô":      {"slot": "chip", "w": {"qi": 1.3, "vis": 0.4}, "heat": 0.0,
                          "unique": True, "power": RELIC_POWER, "passive": "instinto_vo"},
    "Fita Crepe Reforçada": {"slot": "parachoque", "w": {"def": 1.3, "ctr": 0.5}, "heat": 0.0,
                             "unique": True, "power": RELIC_POWER, "passive": "remendo"},
    "Pão de Queijo Térmico": {"slot": "bateria", "w": {"bat": 1.6}, "heat": 0.0,
                              "unique": True, "power": RELIC_POWER, "passive": "calor_forno"},
    "Chinelo Estrutural": {"slot": "succao", "w": {"ctr": 1.2, "def": 0.5}, "heat": 0.0,
                           "unique": True, "power": RELIC_POWER, "passive": "chinelada"},
    "Meia do Prof. Ambrósio": {"slot": "sensor", "w": {"vis": 1.3, "qi": 0.5}, "heat": 0.0,
                               "unique": True, "power": RELIC_POWER, "passive": "faro_meia"},
}
# --- modulos (slot 8, spec secao 2): 1 por skill, exceto as 4 que so vem da arvore/historia
# (leitura, pressao, choque, lider). Nome = "Módulo <skill>" (o nome da skill vem de skills.py, mas
# parts nao importa skills: a tabela fica aqui e test_skills confere que os ids existem).
MODULE_SKILLS = ("arrancada", "succao", "curva", "muralha", "poupanca", "recarga", "overclock",
                 "blindagem", "drible", "elastica", "matador", "lancador")
_MODULE_NAMES = {"arrancada": "Arrancada", "succao": "Sucção", "curva": "Curva", "muralha": "Muralha",
                 "poupanca": "Poupança", "recarga": "Recarga", "overclock": "Overclock",
                 "blindagem": "Blindagem", "drible": "Drible", "elastica": "Elástica",
                 "matador": "Matador", "lancador": "Lançador"}
for _sk in MODULE_SKILLS:
    PARTS["Módulo " + _MODULE_NAMES[_sk]] = {"slot": "modulo", "w": {}, "heat": 0.0, "skill": _sk}

CORE_MODELS = ("Motor Escovado", "Turbina", "Célula Longa", "Célula Rápida", "Borracha", "Blindado",
               "Solenoide", "Canhão de Plasma", "Escova de Sucção", "Vácuo Turbo", "Infravermelho",
               "Radar LiDAR", "Chip de CPU", "Chip Neural")
MODELS = CORE_MODELS                   # compat: quem sorteava parts.MODELS continua com o mesmo stream
NEW_MODELS = tuple(m for m in PARTS if m not in CORE_MODELS and "kind" in PARTS[m])
ALL_MODELS = CORE_MODELS + NEW_MODELS
RELIC_MODELS = tuple(m for m in PARTS if PARTS[m].get("unique"))
MODULE_MODELS = tuple(m for m in PARTS if PARTS[m]["slot"] == "modulo")
UNIQUE_MODELS = frozenset(RELIC_MODELS)
BALANCED_MODELS = tuple(m for m in CORE_MODELS if PARTS[m]["heat"] == 0.0)

# --- sets (spec secao 3; faixas 2/3/4 por decisao do dev: com 1 peca por slot as faixas 4/6 da spec
# eram inalcancaveis). Magnitudes: faixa 2 = a 2 da spec; faixa 3 = a 4 da spec; faixa 4 = a 6 da spec
# (= faixa 3 + a passiva). Faixas SUBSTITUEM a anterior (3 pecas vale o 3, nao 2+3). Bonus em pontos de
# atributo, fora do multiplicador de overclock. Titã e Dojo so tem pecas em 3 slots: a faixa 4 (passiva)
# deles e inalcancavel num robo (ver test_parts_v2.test_set_max_equippable_and_text).
SET_TIERS = (2, 3, 4)
SETS = {
    "Faxineiro": {2: {"ctr": 2}, 3: {"ctr": 3, "bat": 3}, 4: {"ctr": 3, "bat": 3}, "passive": "faxina_total"},
    "Plasma":    {2: {"chu": 2}, 3: {"chu": 3, "vel": 3}, 4: {"chu": 3, "vel": 3}, "passive": "sobrecarga"},
    "Titã":      {2: {"def": 3}, 3: {"def": 4, "ctr": 3}, 4: {"def": 4, "ctr": 3}, "passive": "muralha_aco"},
    "Dojo":      {2: {"qi": 2}, 3: {"qi": 3, "vis": 3}, 4: {"qi": 3, "vis": 3}, "passive": "mente_zen"},
    "Limpex":    {2: {"vel": 2}, 3: {"vel": 3, "ace": 3}, 4: {"vel": 3, "ace": 3}, "passive": "impecavel"},
}
SET_NAMES = tuple(SETS)

# --- cosmeticos (spec secao 6; so visuais) ---
DECALS = ("estrela", "raio", "pao_queijo", "chinelo", "caveira", "coracao")
TRAILS = ("neon", "fogo", "arco_iris", "estrelas")
ANTENNAS = ("curta", "mola", "dupla")              # provisorio: a spec cita `antenna` sem catalogo
CELEBRATIONS = ("confete", "bolo", "chinelo_voando", "fogos")
# B13: slots de `robot["look"]` (a comemoracao e por robo: toca quando ESSE robo marca; a spec fala em
# "por time", mas um campo de time exigiria subir a versao do save)
LOOK_KINDS = {"decal": DECALS, "antenna": ANTENNAS, "trail": TRAILS, "celebration": CELEBRATIONS}
COSMETICS = frozenset(DECALS + TRAILS + ANTENNAS + CELEBRATIONS)
COSMETIC_KIND = {c: k for k, ids in LOOK_KINDS.items() for c in ids}
COSMETIC_PRICE = {"decal": 80, "antenna": 100, "trail": 150, "celebration": 120}   # sucata (LOJA > COSMETICOS)
COSMETIC_NAMES = {"estrela": "Estrela", "raio": "Raio", "pao_queijo": "Pão de Queijo", "chinelo": "Chinelo",
                  "caveira": "Caveira", "coracao": "Coração",
                  "neon": "Neon", "fogo": "Fogo", "arco_iris": "Arco-Íris", "estrelas": "Estrelas",
                  "curta": "Curta", "mola": "Mola", "dupla": "Dupla",
                  "confete": "Confete", "bolo": "Bolo", "chinelo_voando": "Chinelo Voando", "fogos": "Fogos"}
LOOK_LABELS = {"decal": "ADESIVO", "antenna": "ANTENA", "trail": "RASTRO", "celebration": "COMEMORAÇÃO"}
LOOK_TITLES = {"decal": "Adesivo", "antenna": "Antena", "trail": "Rastro", "celebration": "Comemoração"}


def cosmetic_price(cid):
    return COSMETIC_PRICE[COSMETIC_KIND[cid]]


def models_for_slot(slot, pool=None):
    return [m for m in (PARTS if pool is None else pool) if PARTS[m]["slot"] == slot]


def is_unique(model):
    return bool(PARTS.get(model, {}).get("unique"))


def shop_models(tier, rar):
    """Modelos sorteaveis pela loja num tier/raridade. Ate o tier 3: CORE_MODELS (stream identico ao
    antigo). Do tier SHOP_ALL_TIER em diante: ALL_MODELS (o Chip Zero so na Lendaria)."""
    if tier < SHOP_ALL_TIER:
        return CORE_MODELS
    if rar >= LEGEND:
        return ALL_MODELS
    return tuple(m for m in ALL_MODELS if not PARTS[m].get("legend_only"))


def part_power(rar, lvl, model=None):
    base = PARTS[model].get("power", POWER[rar]) if model is not None else POWER[rar]
    return base + UP_STEP[rar] * lvl


def part_bonus(model, rar, lvl):
    """Bonus por atributo (ints) da peca: round(peso * (POWER + UP_STEP * lvl))."""
    p = part_power(rar, lvl, model)
    return {a: int(round(w * p)) for a, w in PARTS[model]["w"].items()}


def part_heat(model, rar, lvl):
    """Calor (float) subtraido de bat; 0 para modelos nao agressivos."""
    return PARTS[model]["heat"] * part_power(rar, lvl, model)


def upgrade_cost(rar, lvl):
    """Custo de lvl -> lvl+1 (PRICE*0.3*(lvl+1)); None se ja esta no MAX_UP."""
    if lvl >= MAX_UP:
        return None
    return int(round(PRICE[rar] * 0.3 * (lvl + 1)))


def part_name(piece):
    return "%s %s +%d" % (piece["model"], RAR_NAMES[piece["rar"]], piece["lvl"])


def part_slot(piece):
    return PARTS[piece["model"]]["slot"]


def part_skill(piece):
    """(skill_id, rank) do modulo, ou None. Rank pela raridade (Comum/Rara 1, Epica 2, Lendaria 3)."""
    sk = PARTS[piece["model"]].get("skill")
    if sk is None:
        return None
    return sk, MODULE_RANK[piece["rar"]]


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
    sk = PARTS[piece["model"]].get("skill")
    if sk is not None:
        bits.append("SKILL r%d" % MODULE_RANK[piece["rar"]])
    return " ".join(bits)


# --- sets ---------------------------------------------------------------------------
def set_counts(models):
    """{set: n} das pecas (modelos) equipadas; qualquer raridade."""
    out = {}
    for m in models:
        s = PARTS.get(m, {}).get("set")
        if s is not None:
            out[s] = out.get(s, 0) + 1
    return out


def set_tier(n):
    """Maior faixa (2/3/4) atingida com n pecas, ou 0."""
    t = 0
    for k in SET_TIERS:
        if n >= k:
            t = k
    return t


def set_bonus(counts):
    """(bonus de atributo {attr: int}, passivas [ids]) dos sets ativos. Faixas substituem a anterior;
    sets diferentes somam."""
    attrs, passives = {}, []
    for s in SET_NAMES:
        t = set_tier(counts.get(s, 0))
        if not t:
            continue
        for a, v in SETS[s][t].items():
            attrs[a] = attrs.get(a, 0) + v
        if t >= SET_TIERS[-1]:
            passives.append(SETS[s]["passive"])
    return attrs, passives


def set_bonus_text(counts):
    """Linhas curtas (Latin-1) por set com peca equipada: 'Faxineiro 3/4: CTR+3 BAT+3'."""
    lines = []
    for s in SET_NAMES:
        n = counts.get(s, 0)
        if not n:
            continue
        t = set_tier(n)
        if not t:
            lines.append("%s %d/%d" % (s, n, SET_TIERS[-1]))
            continue
        bits = " ".join("%s+%d" % (a.upper(), v) for a, v in SETS[s][t].items())
        if t >= SET_TIERS[-1]:
            bits += " +passiva"
        lines.append("%s %d/%d: %s" % (s, n, SET_TIERS[-1], bits))
    return lines
