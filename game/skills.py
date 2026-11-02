# -*- coding: utf-8 -*-
"""Skills (habilidades) dos robos - dados e regras PURAS (sem pygame, sem random global).

Spec: docs/specs/itens-e-habilidades.md secao 7 (Onda B, passos B5-B9). O motor (soccer.py, B6) usa
compile_factors/aura_mods/item_mods, TRIGGERS/TRIGGER_KEYS/check_trigger, pick_active, cooldown e
scaled_extra; a garagem usa effective_skills, skill_force/team_skill_force (team_rating, B9) e as regras
de PH/arvore/equipar.

Efeitos = os da spec (rank 1). SKILL_FORCE: calibrada no motor real por tests/calib_skills.py (B9).

Convencoes
----------
* `mods`: {fator: ("mul"|"add", valor)}; fator = nome de robots.Factors, ou "spd" (alias de `speed`:
  o motor copia p.spd = f.speed ao ativar). Rank 1/2/3 escala a MAGNITUDE (RANK_MUL: mul m vira
  1 + (m-1)*k; add a vira a*k) e a recarga (RANK_CD). Mods listados em `cost` (o lado ruim: dreno,
  lentidao) nao escalam. Modulos com upgrade (+lvl) somam UP_MUL*lvl a k.
* Tipos: "P" passiva (sempre), "A" ativa (gatilho + dur + cd + bat), "C" condicional (vale enquanto o
  gatilho vale). `aura`: efeito no time inteiro (so 1 por time; nao entra em compile_factors).
* `extra`: efeitos fora de Factors (motor B6/B14): pull (px/s2; numa bola lenta o ima a arrasta a
  >= SK_PULL_MIN x pull px/s), tk_ext (px de raio de desarme), curve (graus/s) + curve_t (s), stun (s
  paralisado: nao anda nem domina), evade (s sem desarmar impostos a quem erra o desarme no Drible), aim
  (fracao da meia-boca do gol a mais na mira: mais no canto), launch (chance de o goleiro lancar por
  cima em cada reposicao), bat_add (bateria imediata), fatigue (s, mul de spd), uses (vezes por partida).
  Todos escalam com o rank, menos uses e fatigue.
* Gatilhos: TRIGGERS[nome](ctx) -> bool, sobre um contexto `ctx` (dict) montado pelo motor a ~10 Hz.
  Campos de ctx (ausente = valor neutro): has_ball, opp_ahead (px do adversario mais perto a frente),
  opp_near (px do adversario mais perto), bat (0..1), vel_frac (|v|/max), ball_free, ball_dist,
  ball_speed, is_chaser, kicking (vai chutar agora), dist_opp_goal, shoot_range, gk_off_line,
  ball_goal_dist (bola -> gol proprio), ball_toward_goal, shot_speed, opp_ball_zone (adversario com a
  bola na zona do robo), opp_has_ball, ball_third ("att"|"mid"|"def", do ponto de vista do robo),
  score_diff (meus - deles), minute, won_ball, lost_ball (eventos do passo).
"""
import math

import parts
import robots

LOAD_MAX = 6                  # carga maxima das skills equipadas (P/C 1, A 2, rank 3 = 3)
MAX_EQUIPPED = 3
RANKS = (1, 2, 3)
RANK_MUL = (1.0, 1.25, 1.5)
RANK_CD = (1.0, 0.9, 0.8)
UP_MUL = 0.04                 # +4% de magnitude por nivel de upgrade do modulo (provisorio)
SK_CAP = 9.0                  # teto da forca de skills (pontos de F) por time; 4,0 subestimava o motor
#                               em ~5 F apos o rebalanceamento B14 (calib_campaign --skills, calib_robots --skills)
FORCE_R1_MAX, FORCE_R3_MAX = 5.5, 8.5   # B14/B15: teto da SKILL_FORCE (pontos de F por robo) no rank 1 e no 3
ROBOT_SK_CAP = 20.0           # teto por robo (B9), um robo sozinho (ex.: goleiro com Defesa
#                               Elastica) pode carregar no maximo o teto do time inteiro
PH_PER_LEVEL = 1              # 1 PH por nivel a partir do 2
PTS_MAX = 99
TRAIN_PH_EVERY, TRAIN_PH_MAX = 5, 5    # treino: +1 PH a cada 5 jogadas, max 5 por robo (B11)
GCD = 1.5                     # recarga global entre skills do mesmo robo (motor)
BAT_MARGIN = 0.05             # ativa exige bat >= custo + margem (motor)
NEAR_GOAL = 220.0             # px do gol adversario: Instinto Matador (B14: era 180, so chutes que ja entravam;
#                               a 260 a mira no canto valia ~8 F)
RECHARGE_BELOW = 0.6          # Recarga Rapida: bateria abaixo disso (B14: era 0,25, a bateria quase nunca chega la)

# --- catalogo: 16 skills (spec 7.2) ------------------------------------------------------
# cat: "atk" | "def" | "neutro" (usada pela TATICA de time). src: como se ganha.
SKILLS = {
    "arrancada": {"name": "Arrancada", "kind": "A", "roles": ("ATT", "MID", "DEF"), "load": 2,
                  "trigger": "carry_free_lane", "dur": 1.2, "cd": 9.0, "bat": 0.10,
                  "mods": {"spd": ("mul", 1.35), "accel": ("mul", 1.6)}, "fx": "dash", "cat": "atk",
                  "text": "Acelera com a bola quando há espaço livre.",
                  "src": ("modulo", "arvore", "historia")},
    "succao": {"name": "Sucção Magnética", "kind": "A", "roles": ("MID", "DEF", "ATT"), "load": 2,
               "trigger": "loose_ball_near", "dur": 1.5, "cd": 12.0, "bat": 0.08,
               "mods": {"reach": ("add", 8.0), "catch_speed": ("mul", 1.3), "fumble": ("mul", 0.4)},
               "extra": {"pull": 100.0}, "fx": "magnet", "cat": "neutro",
               "text": "Puxa a bola solta para perto com um ímã.",
               "src": ("modulo", "historia")},
    "curva": {"name": "Chute em Curva", "kind": "A", "roles": ("ATT", "MID"), "load": 2,
              "trigger": "curve_shot", "dur": 0.8, "cd": 10.0, "bat": 0.06,
              "mods": {"shot_err": ("mul", 0.5), "kick_pow": ("mul", 1.2)},
              "extra": {"curve": 70.0, "curve_t": 0.8, "aim": 0.15}, "fx": "curve", "cat": "atk",
              "text": "Chute com efeito quando o goleiro sai da linha.",
              "src": ("modulo", "arvore", "historia")},
    "muralha": {"name": "Muralha", "kind": "A", "roles": ("DEF", "GK"), "load": 2,
                "trigger": "goal_threat", "dur": 2.0, "cd": 11.0, "bat": 0.08,
                "mods": {"tackle": ("mul", 1.5), "gk_save": ("add", 0.08), "spd": ("mul", 0.92)},
                "cost": ("spd",), "extra": {"tk_ext": 8.0}, "fx": "shield", "cat": "def",
                "text": "Fecha a área: desarme forte, anda mais devagar.",
                "src": ("modulo", "arvore", "historia")},
    "leitura": {"name": "Leitura de Jogo", "kind": "P", "roles": ("MID", "ATT", "GK"), "load": 1,
                "trigger": "always", "dur": 0.0, "cd": 0.0, "bat": 0.0,
                "mods": {"pass_range": ("mul", 1.15), "lane_margin": ("mul", 0.85),
                         "gk_lead": ("add", 0.1), "think_mul": ("mul", 0.9), "dec_err": ("mul", 0.7)},
                "fx": "icon", "cat": "neutro",
                "text": "Lê o jogo: passes mais longos e decisões melhores.",
                "src": ("arvore", "historia")},
    "poupanca": {"name": "Poupança", "kind": "P", "roles": ("GK", "DEF", "MID", "ATT"), "load": 1,
                 "trigger": "always", "dur": 0.0, "cd": 0.0, "bat": 0.0,
                 "mods": {"bat_regen_mul": ("mul", 1.6), "bat_drain_mul": ("mul", 0.75)},
                 "fx": None, "cat": "neutro",
                 "text": "Gasta menos bateria e recarrega mais rápido.",
                 "src": ("modulo", "arvore", "historia")},
    "recarga": {"name": "Recarga Rápida", "kind": "A", "roles": ("GK", "DEF", "MID", "ATT"), "load": 2,
                "trigger": "low_bat_still", "dur": 2.5, "cd": 15.0, "bat": 0.0,
                "mods": {"bat_regen_mul": ("mul", 4.0), "spd": ("mul", 1.2), "accel": ("mul", 1.4)},
                "extra": {"bat_add": 0.10}, "fx": "heal", "cat": "neutro",
                "text": "Parado, recarrega na hora e sai embalado.",
                "src": ("modulo", "historia")},
    "overclock": {"name": "Overclock Contido", "kind": "A", "roles": ("GK", "DEF", "MID", "ATT"),
                  "load": 2, "trigger": "late_or_charged", "dur": 6.0, "cd": 25.0, "bat": 0.0,
                  "mods": {"spd": ("mul", 1.15), "accel": ("mul", 1.15), "kick_pow": ("mul", 1.10),
                           "bat_drain_mul": ("mul", 1.5)}, "cost": ("bat_drain_mul",),
                  "extra": {"fatigue": (3.0, 0.9)}, "fx": "overclock", "cat": "atk",
                  "text": "Tudo no máximo por 6 s; depois cansa um pouco.",
                  "src": ("modulo", "historia")},
    "blindagem": {"name": "Blindagem Inercial", "kind": "A", "roles": ("DEF", "MID"), "load": 2,
                  "trigger": "shielded_carry", "dur": 1.5, "cd": 10.0, "bat": 0.05,
                  "mods": {"shield": ("mul", 0.6), "spd": ("mul", 0.9)}, "cost": ("spd",),
                  "fx": "gold_ring", "cat": "def",
                  "text": "Protege a bola quando o adversário chega.",
                  "src": ("modulo", "arvore")},
    "drible": {"name": "Drible Giratório", "kind": "A", "roles": ("ATT", "MID"), "load": 2,
               "trigger": "pressed", "dur": 0.8, "cd": 8.0, "bat": 0.04,
               "mods": {"shield": ("mul", 0.0)}, "extra": {"evade": 0.5},
               "fx": "spin", "cat": "atk",
               "text": "Gira, não perde a bola e deixa o marcador.",
               "src": ("modulo",)},
    "elastica": {"name": "Defesa Elástica", "kind": "A", "roles": ("GK",), "load": 2,
                 "trigger": "shot_incoming", "dur": 1.0, "cd": 6.0, "bat": 0.0,
                 "mods": {"gk_save": ("add", 0.07), "gk_speed": ("mul", 1.08)}, "fx": "gloves",
                 "cat": "def", "text": "Goleiro estica e defende chutes fortes.",
                 "src": ("modulo", "historia")},
    "pressao": {"name": "Pressão Alta", "kind": "A", "roles": ("MID", "ATT"), "load": 2,
                "trigger": "high_press", "dur": 3.0, "cd": 15.0, "bat": 0.05,
                "mods": {"spd": ("mul", 1.2), "tackle": ("mul", 1.3)}, "extra": {"tk_ext": 4.0},
                "fx": "sparks", "cat": "atk",
                "text": "Aperta a saída de bola do adversário.",
                "src": ("arvore",)},
    "choque": {"name": "Choque Elétrico", "kind": "A", "roles": ("DEF",), "load": 2,
               "trigger": "won_ball", "dur": 0.0, "cd": 20.0, "bat": 0.05,
               "mods": {}, "extra": {"stun": 0.15}, "fx": "zap", "cat": "def",
               "text": "Desarma e deixa o adversário paralisado.",
               "src": ("arvore",)},
    "matador": {"name": "Instinto Matador", "kind": "C", "roles": ("ATT",), "load": 1,
                "trigger": "near_goal", "dur": 0.0, "cd": 0.0, "bat": 0.0,
                "mods": {"shot_err": ("mul", 0.7), "kick_pow": ("mul", 1.06)}, "extra": {"aim": 0.02},
                "fx": "glow",
                "cat": "atk", "text": "Perto do gol, chuta com mais precisão.",
                "src": ("modulo", "historia")},
    "lancador": {"name": "Lançador", "kind": "P", "roles": ("GK",), "load": 1,
                 "trigger": "always", "dur": 0.0, "cd": 0.0, "bat": 0.0,
                 "mods": {"pass_range": ("mul", 1.2)}, "extra": {"launch": 0.12}, "fx": None,
                 "cat": "neutro", "text": "Goleiro lança por cima no mais adiantado.",
                 "src": ("modulo",)},
    "lider": {"name": "Líder", "kind": "P", "roles": ("GK", "DEF", "MID", "ATT"), "load": 1,
              "trigger": "always", "dur": 0.0, "cd": 0.0, "bat": 0.0, "aura": True,
              "mods": {"speed": ("mul", 1.014), "think_mul": ("mul", 0.98)}, "fx": "captain",
              "cat": "neutro", "text": "Capitão: o time todo joga um pouco melhor.",
              "src": ("arvore", "historia")},
}
SKILL_IDS = tuple(SKILLS)

# --- passivas especiais (reliquias e sets: mesmo motor, nao se aprendem nem se equipam) -------------
SPECIAL = {
    "rolando": {"name": "Rolando Sozinha", "kind": "A", "trigger": "carry_any", "dur": 4.0, "cd": 0.0,
                "bat": 0.0, "mods": {"spd": ("mul", 1.25)}, "extra": {"uses": 1}, "fx": "wheel",
                "cat": "atk", "text": "1 vez por jogo a rodinha cai: corre muito.", "src": ("reliquia",)},
    "instinto_vo": {"name": "Instinto do Vô", "kind": "P", "trigger": "always", "dur": 0.0, "cd": 0.0,
                    "bat": 0.0, "mods": {"dec_err": ("mul", 0.4), "think_mul": ("mul", 0.85),
                                                       "lane_margin": ("mul", 0.85)},
                    "fx": None, "cat": "neutro", "text": "Decide como o vô: rápido e certo.",
                    "src": ("reliquia",)},
    "remendo": {"name": "Remendo", "kind": "A", "trigger": "lost_ball", "dur": 2.0, "cd": 5.0,
                "bat": 0.0, "mods": {"shield": ("mul", 0.7)}, "fx": "tape", "cat": "def",
                "text": "Depois de perder a bola, protege melhor.", "src": ("reliquia",)},
    "calor_forno": {"name": "Calor de Forno", "kind": "P", "trigger": "always", "dur": 0.0, "cd": 0.0,
                    "bat": 0.0, "mods": {"bat_regen_mul": ("mul", 1.5), "accel": ("mul", 1.1)}, "fx": None,
                    "cat": "neutro", "text": "Sai do forno: recarrega e arranca mais rápido.", "src": ("reliquia",)},
    "chinelada": {"name": "Chinelada de Honra", "kind": "A", "trigger": "curve_shot_any", "dur": 0.8,
                  "cd": 0.0, "bat": 0.0, "mods": {"kick_pow": ("mul", 1.35), "shot_err": ("mul", 0.3)},
                  "extra": {"uses": 1, "aim": 0.2}, "fx": "slipper", "cat": "atk",
                  "text": "1 chute por jogo com força de chinelada.", "src": ("reliquia",)},
    "faro_meia": {"name": "Faro de Meia", "kind": "P", "trigger": "always", "dur": 0.0, "cd": 0.0,
                  "bat": 0.0, "mods": {"lane_margin": ("mul", 0.8), "think_mul": ("mul", 0.92),
                                       "gk_lead": ("add", 0.15)},
                  "fx": None, "cat": "neutro", "text": "Fareja o lance antes de todo mundo.",
                  "src": ("reliquia",)},
    "faxina_total": {"name": "Faxina Total", "kind": "P", "trigger": "always", "dur": 0.0, "cd": 0.0,
                     "bat": 0.0, "mods": {"tackle": ("mul", 1.1), "reach": ("add", 3.0)}, "fx": None,
                     "cat": "def", "text": "Set Faxineiro: desarma e domina melhor.", "src": ("set",)},
    "sobrecarga": {"name": "Sobrecarga", "kind": "P", "trigger": "always", "dur": 0.0, "cd": 0.0,
                   "bat": 0.0, "mods": {"speed": ("mul", 1.03), "accel": ("mul", 1.08),
                                        "bat_drain_mul": ("mul", 1.1)}, "cost": ("bat_drain_mul",),
                   "fx": None, "cat": "atk", "text": "Set Plasma: mais rápido, gasta mais bateria.",
                   "src": ("set",)},
    "muralha_aco": {"name": "Muralha de Aço", "kind": "P", "trigger": "always", "dur": 0.0, "cd": 0.0,
                    "bat": 0.0, "mods": {"shield": ("mul", 0.92)}, "fx": None, "cat": "def",
                    "text": "Set Titã: quase não perde a bola.", "src": ("set",)},
    "mente_zen": {"name": "Mente Zen", "kind": "P", "trigger": "always", "dur": 0.0, "cd": 0.0,
                  "bat": 0.0, "mods": {"dec_err": ("mul", 0.4), "think_mul": ("mul", 0.92),
                                       "lane_margin": ("mul", 0.85)}, "fx": None,
                  "cat": "neutro",
                  "text": "Set Dojo: decisões calmas e certeiras.", "src": ("set",)},
    "impecavel": {"name": "Impecável", "kind": "P", "trigger": "always", "dur": 0.0, "cd": 0.0,
                  "bat": 0.0, "mods": {"speed": ("mul", 1.02), "gk_save": ("add", 0.03)}, "fx": None,
                  "cat": "neutro", "text": "Set Limpex: tudo um pouco melhor.", "src": ("set",)},
}
for _sid, _s in SPECIAL.items():
    _s.setdefault("roles", ("GK", "DEF", "MID", "ATT"))
    _s.setdefault("load", 0)
ALL = dict(SKILLS)
ALL.update(SPECIAL)

# --- forca provisoria (pontos de F por robo, por rank) - recalibrada em B9 (calib_skills.py) -------
# SKILL_FORCE-BEGIN (gerado por tests/calib_skills.py --write; nao editar a mao)
SKILL_FORCE = {
    "arrancada": (1.39, 2.47, 3.55),
    "succao": (3.67, 4.19, 4.71),
    "curva": (3.24, 3.24, 3.24),
    "muralha": (3.09, 3.09, 3.09),
    "leitura": (1.50, 3.34, 5.17),
    "poupanca": (0.29, 0.29, 0.29),
    "recarga": (0.93, 1.17, 1.42),
    "overclock": (1.14, 2.82, 4.51),
    "blindagem": (4.01, 4.42, 4.84),
    "drible": (4.78, 5.97, 7.15),
    "elastica": (4.28, 6.04, 7.80),
    "pressao": (3.70, 5.09, 6.48),
    "choque": (1.77, 1.77, 1.77),
    "matador": (5.27, 5.27, 5.27),
    "lancador": (3.12, 3.12, 3.12),
    "lider": (4.46, 5.58, 6.71),
    "rolando": (1.67, 1.67, 1.67),
    "instinto_vo": (1.08, 1.08, 1.08),
    "remendo": (0.59, 0.59, 0.59),
    "calor_forno": (1.67, 1.67, 1.67),
    "chinelada": (0.83, 0.83, 0.83),
    "faro_meia": (2.22, 2.22, 2.22),
    "faxina_total": (3.86, 3.86, 3.86),
    "sobrecarga": (3.89, 3.89, 3.89),
    "muralha_aco": (2.84, 2.84, 2.84),
    "mente_zen": (1.67, 1.67, 1.67),
    "impecavel": (1.64, 1.64, 1.64),
}
# SKILL_FORCE-END

# --- consumiveis (spec secao 5): scope "team" | "gk" | "one" ----------------------------------------
ITEM_MAX = 9
BACKPACK = 2
ITEMS = {
    "bateria_extra": {"name": "Bateria Extra", "price": 90, "scope": "team",
                      "mods": {"bat_drain_mul": ("mul", 0.85)}, "force": 0.6},
    "cera_turbo": {"name": "Cera Turbo", "price": 120, "scope": "team",
                   "mods": {"speed": ("mul", 1.05), "accel": ("mul", 1.08)}, "force": 0.9},
    "cafe": {"name": "Café do Prof.", "price": 100, "scope": "team",
             "mods": {"think_mul": ("mul", 0.9)}, "force": 0.5},
    "fita_isolante": {"name": "Fita Isolante", "price": 110, "scope": "gk",
                      "mods": {"gk_save": ("add", 0.10)}, "force": 0.6},
    "pilha_reserva": {"name": "Pilha Reserva", "price": 140, "scope": "one",
                      "mods": {}, "extra": {"restore_below": 0.2, "uses": 1}, "force": 0.5},
    "spray": {"name": "Spray Anti-Poeira", "price": 150, "scope": "team",
              "mods": {"shield": ("mul", 0.92)}, "force": 0.7},
}

# --- arvore (spec 7.3.2): 3 ramos x 4 camadas; no = {"id","skill","rank","cost","needs":[ids]} -------
TREE = {
    "ATQ": [{"id": "atq1", "skill": "arrancada", "rank": 1, "cost": 1, "needs": []},
            {"id": "atq2", "skill": "curva", "rank": 1, "cost": 2, "needs": ["atq1"]},
            {"id": "atq3", "skill": "arrancada", "rank": 2, "cost": 2, "needs": ["atq2"]},
            {"id": "atq4", "skill": "pressao", "rank": 1, "cost": 3, "needs": ["atq3"]}],
    "CTR": [{"id": "ctr1", "skill": "leitura", "rank": 1, "cost": 1, "needs": []},
            {"id": "ctr2", "skill": "poupanca", "rank": 1, "cost": 2, "needs": ["ctr1"]},
            {"id": "ctr3", "skill": "leitura", "rank": 2, "cost": 2, "needs": ["ctr2"]},
            {"id": "ctr4", "skill": "lider", "rank": 1, "cost": 3, "needs": ["ctr3"]}],
    "DEF": [{"id": "def1", "skill": "muralha", "rank": 1, "cost": 1, "needs": []},
            {"id": "def2", "skill": "blindagem", "rank": 1, "cost": 2, "needs": ["def1"]},
            {"id": "def3", "skill": "muralha", "rank": 2, "cost": 2, "needs": ["def2"]},
            {"id": "def4", "skill": "choque", "rank": 1, "cost": 3, "needs": ["def3"]}],
}
TREE_NAMES = {"ATQ": "Ataque", "CTR": "Controle", "DEF": "Defesa"}
NODES = {n["id"]: n for br in TREE.values() for n in br}

# --- tatica de time (decisao 2 do plano): so muda a PRIORIDADE entre gatilhos validos -------------
TACTICS = ("ofensivo", "equilibrado", "defensivo")
TACTIC_NAMES = {"ofensivo": "Ofensivo", "equilibrado": "Equilibrado", "defensivo": "Defensivo"}
DEFAULT_TACTIC = "equilibrado"
_TACTIC_PRIO = {"ofensivo": {"atk": 2, "neutro": 1, "def": 0},
                "equilibrado": {"atk": 1, "neutro": 1, "def": 1},
                "defensivo": {"atk": 0, "neutro": 1, "def": 2}}

# --- limites dos fatores depois dos mods (alem dos lo/hi de robots.TUNING) -----------------------
_LIMITS = {n: (lo, hi) for n, (_a, _s, lo, hi) in robots.TUNING["f"].items()}
_LIMITS.update({"speed": (0.2, 2.0), "accel": (1.0, 40.0), "stop": (1.0, 40.0), "kick_pow": (0.3, 2.0),
                "gk_save": (0.0, 0.95), "reach": (0.0, 40.0), "catch_speed": (200.0, 2000.0),
                "shield": (0.0, 2.0), "pass_range": (100.0, 1600.0), "gk_lead": (0.4, 1.0)})
FACTOR_NAMES = tuple(n for n in robots.Factors.__slots__ if n != "g_chu")
MOD_NAMES = frozenset(FACTOR_NAMES) | {"spd"}


# --- gatilhos -------------------------------------------------------------------------------
def _g(ctx, k, default=0.0):
    v = ctx.get(k, default)
    return default if v is None else v


TRIGGERS = {
    "always": lambda c: True,
    "carry_free_lane": lambda c: bool(_g(c, "has_ball", False)) and _g(c, "opp_ahead", math.inf) >= 80
    and _g(c, "bat") > 0.35,
    "loose_ball_near": lambda c: bool(_g(c, "ball_free", False)) and _g(c, "ball_dist", math.inf) < 90
    and _g(c, "ball_speed", math.inf) < 280 and bool(_g(c, "is_chaser", False)),
    "curve_shot": lambda c: bool(_g(c, "kicking", False))
    and _g(c, "dist_opp_goal", math.inf) < _g(c, "shoot_range", 0.0) and bool(_g(c, "gk_off_line", False)),
    "curve_shot_any": lambda c: bool(_g(c, "kicking", False))
    and _g(c, "dist_opp_goal", math.inf) < _g(c, "shoot_range", 0.0),
    "goal_threat": lambda c: _g(c, "ball_goal_dist", math.inf) < 220 and bool(_g(c, "opp_ball_zone", False)),
    "low_bat_still": lambda c: _g(c, "bat", 1.0) < RECHARGE_BELOW and _g(c, "vel_frac", 1.0) < 0.3,
    "late_or_charged": lambda c: (_g(c, "score_diff") <= 0 and _g(c, "minute") >= 60)
    or (_g(c, "bat") > 0.7 and _g(c, "ball_third", "mid") == "att"),
    "shielded_carry": lambda c: bool(_g(c, "has_ball", False)) and _g(c, "opp_near", math.inf) < 55,
    "pressed": lambda c: bool(_g(c, "has_ball", False)) and _g(c, "opp_near", math.inf) < 45,
    "shot_incoming": lambda c: _g(c, "shot_speed") > 450 and _g(c, "ball_goal_dist", math.inf) < 260
    and bool(_g(c, "ball_toward_goal", False)),
    "high_press": lambda c: bool(_g(c, "opp_has_ball", False)) and _g(c, "ball_third", "mid") == "att",
    "won_ball": lambda c: bool(_g(c, "won_ball", False)),
    "lost_ball": lambda c: bool(_g(c, "lost_ball", False)),
    "near_goal": lambda c: _g(c, "dist_opp_goal", math.inf) < NEAR_GOAL,
    "carry_any": lambda c: bool(_g(c, "has_ball", False)),
}


# Campos de ctx que cada gatilho le (o motor monta so estes: ctx barato a ~10 Hz). Os gatilhos de
# EVENTO nao sao avaliados no ciclo periodico: o motor os chama no proprio evento (chute, desarme).
TRIGGER_KEYS = {
    "always": (),
    "carry_free_lane": ("has_ball", "opp_ahead", "bat"),
    "loose_ball_near": ("ball_free", "ball_dist", "ball_speed", "is_chaser"),
    "curve_shot": ("kicking", "dist_opp_goal", "shoot_range", "gk_off_line"),
    "curve_shot_any": ("kicking", "dist_opp_goal", "shoot_range"),
    "goal_threat": ("ball_goal_dist", "opp_ball_zone"),
    "low_bat_still": ("bat", "vel_frac"),
    "late_or_charged": ("score_diff", "minute", "bat", "ball_third"),
    "shielded_carry": ("has_ball", "opp_near"),
    "pressed": ("has_ball", "opp_near"),
    "shot_incoming": ("shot_speed", "ball_goal_dist", "ball_toward_goal"),
    "high_press": ("opp_has_ball", "ball_third"),
    "won_ball": ("won_ball",),
    "lost_ball": ("lost_ball",),
    "near_goal": ("dist_opp_goal",),
    "carry_any": ("has_ball",),
}
EVENT_TRIGGERS = {"kick": ("curve_shot", "curve_shot_any"), "won": ("won_ball",), "lost": ("lost_ball",)}


def check_trigger(sid, ctx):
    """O gatilho da skill vale neste contexto? (False se a skill/gatilho nao existe)."""
    s = ALL.get(sid)
    fn = TRIGGERS.get(s["trigger"]) if s else None
    try:
        return bool(fn(ctx)) if fn else False
    except Exception:  # noqa: BLE001  (ctx incompleto/tipos estranhos: nunca derruba a partida)
        return False


# --- escala por rank ------------------------------------------------------------------------
def _clamp(v, lo, hi):
    if lo is not None and v < lo:
        v = lo
    if hi is not None and v > hi:
        v = hi
    return v


def _rank(rank):
    try:
        r = int(rank)
    except (TypeError, ValueError):
        return 1
    return max(1, min(3, r))


def magnitude(rank, up=0):
    """Fator de magnitude do rank (1, 1,25, 1,5) + UP_MUL por nivel de upgrade (modulos)."""
    return RANK_MUL[_rank(rank) - 1] + UP_MUL * max(0, min(parts.MAX_UP, int(up or 0)))


def cooldown(sid, rank):
    return ALL[sid]["cd"] * RANK_CD[_rank(rank) - 1]


def scaled_mods(sid, rank=1, up=0):
    """{fator: (op, valor escalado)} da skill no rank/upgrade. 'spd' vira 'speed'."""
    s = ALL[sid]
    k = magnitude(rank, up)
    cost = s.get("cost", ())
    out = {}
    for name, (op, v) in s["mods"].items():
        kk = 1.0 if name in cost else k
        fac = "speed" if name == "spd" else name
        nv = v * kk if op == "add" else 1.0 + (v - 1.0) * kk
        if op == "mul":
            nv = max(0.0, nv)
        if fac in out:                                   # spd e speed na mesma skill: compoe
            pop, pv = out[fac]
            nv = pv + nv if op == "add" else pv * nv
            op = pop if pop == op else "mul"
        out[fac] = (op, nv)
    return out


def scaled_extra(sid, rank=1, up=0):
    """Efeitos fora de Factors, escalados (uses e fatigue nao escalam)."""
    k = magnitude(rank, up)
    out = {}
    for name, v in ALL[sid].get("extra", {}).items():
        out[name] = v if name in ("uses", "fatigue") else v * k
    return out


def copy_factors(f):
    g = robots.Factors()
    for n in robots.Factors.__slots__:
        setattr(g, n, getattr(f, n))
    return g


def apply_mods(f, mods):
    """Aplica {fator: (op, v)} numa COPIA de Factors, com os limites de _LIMITS."""
    g = copy_factors(f)
    for name, (op, v) in mods.items():
        cur = getattr(g, name)
        nv = cur * v if op == "mul" else cur + v
        lo, hi = _LIMITS.get(name, (None, None))
        setattr(g, name, _clamp(nv, lo, hi))
    return g


def _norm(entry):
    """(id, rank, up) a partir de (id, rank) ou (id, rank, up)."""
    sid, rank = entry[0], entry[1]
    up = entry[2] if len(entry) > 2 else 0
    return sid, _rank(rank), up


def compile_factors(base_factors, skill_list):
    """Fatores pre-calculados de um robo (motor B6). skill_list = [(id, rank[, up])].

    Devolve {"_base": Factors com todas as passivas (P, sem aura), id: Factors da variante} para cada
    ativa (A) e condicional (C): variante = _base + mods da skill. Ids desconhecidos sao ignorados.
    Nao muta base_factors."""
    ents = [_norm(e) for e in skill_list if e and e[0] in ALL]
    base = copy_factors(base_factors)
    for sid, rank, up in ents:
        s = ALL[sid]
        if s["kind"] == "P" and not s.get("aura"):
            base = apply_mods(base, scaled_mods(sid, rank, up))
    out = {"_base": base}
    for sid, rank, up in ents:
        if ALL[sid]["kind"] in ("A", "C"):
            out[sid] = apply_mods(base, scaled_mods(sid, rank, up))
    return out


def aura_mods(team_skill_lists):
    """Mods de aura do time (Lider): so a de maior rank conta (1 por time)."""
    best = None
    for lst in team_skill_lists:
        for e in lst:
            sid, rank, up = _norm(e)
            if sid in ALL and ALL[sid].get("aura") and (best is None or (rank, up) > best[1:]):
                best = (sid, rank, up)
    return scaled_mods(*best) if best else {}


def item_mods(item_id):
    return dict(ITEMS[item_id]["mods"]) if item_id in ITEMS else {}


# --- tatica -------------------------------------------------------------------------------
def tactic_priority(sid, tactic):
    t = tactic if tactic in _TACTIC_PRIO else DEFAULT_TACTIC
    return _TACTIC_PRIO[t].get(ALL[sid]["cat"], 1) if sid in ALL else -1


def pick_active(candidates, tactic=DEFAULT_TACTIC):
    """Entre as ativas prontas cujo gatilho vale, a de maior prioridade pela tatica; empate: ordem do
    catalogo (deterministico, sem RNG). None se nao ha candidatas."""
    order = {sid: i for i, sid in enumerate(ALL)}
    cand = [c for c in candidates if c in ALL]
    if not cand:
        return None
    return max(cand, key=lambda c: (tactic_priority(c, tactic), -order[c]))


# --- carga / PH / arvore / equipar ----------------------------------------------------------
def load_of(sid, rank=1):
    """Carga: passiva/condicional 1, ativa 2, rank 3 (lendaria) 3."""
    if sid not in SKILLS:
        return 0
    return 3 if _rank(rank) >= 3 else SKILLS[sid]["load"]


def ph_for_level(level):
    """PH acumulados por nivel (1 por nivel a partir do 2)."""
    try:
        lv = int(level)
    except (TypeError, ValueError):
        return 0
    return max(0, lv - 1) * PH_PER_LEVEL


def new_robot_skills():
    return {"learned": {}, "equipped": [], "pts": 0}


def _sk(robot):
    s = robot.get("skills")
    if not isinstance(s, dict):
        s = new_robot_skills()
        robot["skills"] = s
    s.setdefault("learned", {})
    s.setdefault("equipped", [])
    s.setdefault("pts", 0)
    return s


def grant_pts(robot, n):
    s = _sk(robot)
    s["pts"] = max(0, min(PTS_MAX, int(s["pts"]) + int(n)))
    return s["pts"]


def node_state(robot, node_id):
    """"learned" | "open" (pode comprar) | "locked" (falta pre-requisito ou PH) | None."""
    n = NODES.get(node_id)
    if n is None:
        return None
    s = _sk(robot)
    if s["learned"].get(n["skill"], 0) >= n["rank"]:
        return "learned"
    for req in n["needs"]:
        r = NODES[req]
        if s["learned"].get(r["skill"], 0) < r["rank"]:
            return "locked"
    return "open" if s["pts"] >= n["cost"] else "locked"


def learn_node(robot, node_id):
    """Compra o no da arvore com PH. (ok, msg)."""
    n = NODES.get(node_id)
    if n is None:
        return False, "Habilidade inválida."
    st = node_state(robot, node_id)
    if st == "learned":
        return False, "Já aprendida."
    s = _sk(robot)
    for req in n["needs"]:
        r = NODES[req]
        if s["learned"].get(r["skill"], 0) < r["rank"]:
            return False, "Aprenda antes: %s %d." % (SKILLS[r["skill"]]["name"], r["rank"])
    if s["pts"] < n["cost"]:
        return False, "PH insuficientes (precisa de %d)." % n["cost"]
    s["pts"] -= n["cost"]
    s["learned"][n["skill"]] = max(s["learned"].get(n["skill"], 0), n["rank"])
    return True, "Aprendeu %s %d." % (SKILLS[n["skill"]]["name"], n["rank"])


def learn_skill(robot, sid, rank=1):
    """Aprende direto (historia/recompensa); so sobe o rank. (ok, msg)."""
    if sid not in SKILLS:
        return False, "Habilidade inválida."
    s = _sk(robot)
    r = _rank(rank)
    if s["learned"].get(sid, 0) >= r:
        return False, "Já aprendida."
    s["learned"][sid] = r
    return True, "Aprendeu %s %d." % (SKILLS[sid]["name"], r)


def equipped_load(robot):
    s = _sk(robot)
    return sum(load_of(sid, s["learned"].get(sid, 1)) for sid in s["equipped"])


def equip_skill(robot, sid):
    s = _sk(robot)
    if sid not in s["learned"]:
        return False, "Habilidade não aprendida."
    if sid in s["equipped"]:
        return False, "Já equipada."
    if len(s["equipped"]) >= MAX_EQUIPPED:
        return False, "Máximo de %d habilidades." % MAX_EQUIPPED
    if equipped_load(robot) + load_of(sid, s["learned"][sid]) > LOAD_MAX:
        return False, "Carga acima de %d." % LOAD_MAX
    s["equipped"].append(sid)
    return True, "%s equipada." % SKILLS[sid]["name"]


def unequip_skill(robot, sid):
    s = _sk(robot)
    if sid not in s["equipped"]:
        return False, "Não está equipada."
    s["equipped"].remove(sid)
    return True, "%s removida." % SKILLS[sid]["name"]


# --- skills efetivas de um robo ---------------------------------------------------------------
def effective_skills(robot, pieces_by_id, mod_on=True):
    """[(id, rank, up)] que o robo leva para a partida: skill do modulo (se mod_on) + aprendidas
    equipadas (respeitando MAX_EQUIPPED e LOAD_MAX, o modulo conta na carga) + passivas de reliquias
    e de sets completos (sem carga). Sem duplicatas (mesma skill: fica o maior rank/up). Ordem
    deterministica. Nunca levanta com robo incompleto."""
    out = {}
    slots = robot.get("slots") if isinstance(robot.get("slots"), dict) else {}
    pcs = []
    for slot in parts.SLOTS:
        pid = slots.get(slot)
        pc = pieces_by_id.get(pid) if pid is not None else None
        if pc is None or pc.get("model") not in parts.PARTS or parts.part_slot(pc) != slot:
            continue
        pcs.append(pc)
    count, load = 0, 0
    mod = next((pc for pc in pcs if parts.part_slot(pc) == "modulo"), None)
    if mod is not None and mod_on:
        sid, rank = parts.part_skill(mod)
        if sid in SKILLS:
            out[sid] = (rank, int(mod.get("lvl", 0)))
            count, load = 1, load_of(sid, rank)
    s = robot.get("skills") if isinstance(robot.get("skills"), dict) else {}
    learned = s.get("learned") if isinstance(s.get("learned"), dict) else {}
    for sid in s.get("equipped") or ():
        if sid not in SKILLS or sid not in learned:
            continue
        rank = _rank(learned[sid])
        if sid in out:
            if (rank, 0) > out[sid]:
                load += load_of(sid, rank) - load_of(sid, out[sid][0])
                out[sid] = (rank, 0)
            continue
        ld = load_of(sid, rank)
        if count >= MAX_EQUIPPED or load + ld > LOAD_MAX:
            continue
        out[sid] = (rank, 0)
        count += 1
        load += ld
    for pc in pcs:
        p = parts.PARTS[pc["model"]].get("passive")
        if p in SPECIAL:
            out.setdefault(p, (1, 0))
    _attrs, passives = parts.set_bonus(parts.set_counts(pc["model"] for pc in pcs))
    for p in passives:
        if p in SPECIAL:
            out.setdefault(p, (1, 0))
    return [(sid, r, u) for sid, (r, u) in out.items()]


def skill_force(skill_list):
    """Pontos de F de um robo pelas skills (SKILL_FORCE calibrada no motor, B9), com teto ROBOT_SK_CAP."""
    tot = 0.0
    for e in skill_list:
        sid, rank, _up = _norm(e)
        if sid in SKILL_FORCE:
            tot += SKILL_FORCE[sid][rank - 1]
    return min(ROBOT_SK_CAP, tot)


def team_skill_force(robot_skill_lists):
    """min(SK_CAP, media de skill_force dos robos) - entra em team_rating no passo B9."""
    lst = list(robot_skill_lists)
    if not lst:
        return 0.0
    return min(SK_CAP, sum(skill_force(x) for x in lst) / len(lst))


def item_force(item_ids):
    return sum(ITEMS[i]["force"] for i in item_ids if i in ITEMS)
