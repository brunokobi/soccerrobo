"""Modelo de robos (chassis, atributos, fatores de jogo e bateria).

Modulo puro: sem pygame e sem random global. O jitter usa random.Random(seed)
local (seed None = sem jitter), entao nunca altera a sequencia do RNG global.
"""
import math
import random

# ordem fixa dos atributos
ATTRS = ("vel", "ace", "chu", "ctr", "def", "vis", "bat", "qi")

# bias por chassis (na ordem de ATTRS)
CHASSIS = {
    "Disco":     (0, 0, 0, 0, 0, 0, 0, 0),
    "Tanque":    (-15, -10, 10, 10, 15, 0, 10, 0),
    "Velocista": (20, 15, 5, -5, -15, 0, -10, 0),
    "Goleiro":   (-10, 0, -10, 0, 20, 15, 0, 5),
}

# bias por papel de escalacao
ROLE_BIAS = {
    "GK":  {"def": 15, "vis": 10, "vel": -10},
    "DEF": {"def": 10, "ctr": 5},
    "MID": {"ctr": 5, "qi": 5},
    "ATT": {"chu": 15, "vel": 5},
}

# chassis padrao por papel / por posicao real do jogador
ROLE_CHASSIS = {"GK": "Goleiro", "DEF": "Tanque", "MID": "Disco", "ATT": "Velocista"}
POS_CHASSIS = ROLE_CHASSIS

ATTR_MIN, ATTR_MAX = 20, 99
JITTER = 3

# --- bateria ---------------------------------------------------------------
BAT_RUN = 0.75          # dreno/s (a velocidade maxima) / match_time
BAT_REGEN = 2.0         # recarga/s parado / match_time
BAT_LOW = 0.30          # abaixo disso a velocidade cai
BAT_REGEN_BELOW = 0.25  # recarrega quando |vel| < 25% do maximo
BAT_KICK_BASE = 0.02
BAT_KICK_POW = 0.03     # custo = BASE + POW * potencia / 850
BAT_GOAL_BONUS = 0.12


def bat_mul(bat):
    """Multiplicador de velocidade pela bateria (1.0 ate 30%, depois cai)."""
    if bat >= BAT_LOW:
        return 1.0
    return 0.62 + 1.26 * max(0.0, bat)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def from_overall(ovr, role, chassis=None, seed=None, flat=False):
    """Converte um overall em dict de atributos (ordem ATTRS), valores 20..99.

    atributo = ovr + bias(papel) + bias(chassis), com o bias combinado centrado
    (soma zero) para a media ficar em ~ovr; jitter +-3 com Random(seed) local.
    flat=True (modo legado): todos os atributos = clamp(ovr, 20, 98), float.
    """
    if flat:
        v = _clamp(ovr, ATTR_MIN, 98)
        return {a: v for a in ATTRS}
    cname = chassis or ROLE_CHASSIS[role]
    cb = CHASSIS[cname]
    rb = ROLE_BIAS[role]
    bias = [rb.get(a, 0) + cb[i] for i, a in enumerate(ATTRS)]
    mean = sum(bias) / len(bias)
    rng = random.Random(seed) if seed is not None else None
    out = {}
    for i, a in enumerate(ATTRS):
        v = ovr + bias[i] - mean
        if rng is not None:
            v += rng.randint(-JITTER, JITTER)
        out[a] = int(_clamp(round(v), ATTR_MIN, ATTR_MAX))
    return out


# --- fatores -----------------------------------------------------------------
# nome -> (atributo, ancora em g=0.65, inclinacao por unidade de d=g-0.65, lo, hi)
# "gk_speed" usa a media de vel e ace.
_SPEC = (
    ("speed",       "vel", 0.9925, 0.70, None, None),
    ("accel",       "ace", 9.0, 12.0, 1.0, None),
    ("stop",        "ace", 10.0, 8.0, 1.0, None),
    ("kick_pow",    "chu", 1.0, 0.45, 0.3, None),
    ("shot_err",    "chu", 4.2, -12.0, 0.0, None),
    ("pass_err",    "ctr", 2.0, -10.0, 0.0, None),
    ("reach",       "ctr", 3.0, 6.0, 0.0, None),
    ("catch_speed", "ctr", 520.0, 182.0, 200.0, None),
    ("fumble",      "ctr", 0.18, -0.35, 0.0, 0.35),
    ("tackle",      "def", 0.4775, 0.55, 0.0, 1.0),
    ("shield",      "ctr", 0.81, -0.6, 0.0, None),
    ("gk_save",     "def", 0.575, 0.70, 0.0, 1.0),
    ("gk_speed",    "mean", 240.0, 120.0, 60.0, None),
    ("gk_lead",     "vis", 0.8, 0.6, 0.4, 1.0),
    ("pass_range",  "vis", 450.0, 350.0, 100.0, None),
    ("lane_margin", "vis", 35.0, 25.0, 5.0, None),
    ("shoot_range", "vis", 420.0, 200.0, 100.0, None),
    ("think_mul",   "qi", 1.0, -0.8, 0.3, None),
    ("dec_err",     "qi", 0.12, -0.5, 0.0, None),
    ("bat_drain_mul", "bat", 1.0, -1.2, 0.6, 1.5),
    ("bat_regen_mul", "bat", 1.0, 0.8, 0.2, None),
)

# inclinacoes/ancoras do motor ORIGINAL (s = media/100; s=0.65 => ancora)
_LEGACY = {
    "speed":       (0.9925, 0.45),
    "accel":       (9.0, 0.0),
    "stop":        (10.0, 0.0),
    "kick_pow":    (1.0, 0.0),
    "shot_err":    (4.2, -12.0),
    "pass_err":    (0.0, 0.0),
    "reach":       (3.0, 0.0),
    "catch_speed": (520.0, 0.0),
    "fumble":      (0.0, 0.0),
    "tackle":      (0.38, 0.40),
    "shield":      (0.94, -0.40),
    "gk_save":     (0.432, 0.48),
    "gk_speed":    (240.0, 0.0),
    "gk_lead":     (0.8, 0.0),
    "pass_range":  (450.0, 0.0),
    "lane_margin": (35.0, 0.0),
    "shoot_range": (420.0, 0.0),
    "think_mul":   (1.0, 0.0),
    "dec_err":     (0.0, 0.0),
    "bat_drain_mul": (1.0, -1.2),
    "bat_regen_mul": (1.0, 0.8),
}

# TUNING["f"][nome] = (ancora, inclinacao, lo, hi); "flat" = atributos planos (= ovr)
TUNING = {
    "flat": False,
    "f": {n: (a, s, lo, hi) for n, _at, a, s, lo, hi in _SPEC},
}
LEGACY_TUNING = {
    "flat": True,
    "f": {n: (_LEGACY[n][0], _LEGACY[n][1], lo, hi) for n, _at, _a, _s, lo, hi in _SPEC},
}


class Factors:
    __slots__ = tuple(n for n, *_ in _SPEC) + ("g_chu",)

    def __repr__(self):
        return "Factors(%s)" % ", ".join("%s=%.4g" % (k, getattr(self, k)) for k in self.__slots__)


def factors(robot, tuning=None):
    """Calcula os fatores de jogo de um robo (dict de atributos) sob um tuning."""
    tuning = tuning or TUNING
    f = Factors()
    for name, attr, _a, _s, _lo, _hi in _SPEC:
        anchor, slope, lo, hi = tuning["f"][name]
        if attr == "mean":
            g = (robot["vel"] + robot["ace"]) / 200.0
        else:
            g = robot[attr] / 100.0
        v = anchor + slope * (g - 0.65)
        if lo is not None and v < lo:
            v = lo
        if hi is not None and v > hi:
            v = hi
        setattr(f, name, v)
    f.g_chu = robot["chu"] / 100.0
    return f


def mean_attr(robot):
    """Media dos atributos / 100 (exata para atributos planos)."""
    return math.fsum(robot[a] for a in ATTRS) / len(ATTRS) / 100.0
