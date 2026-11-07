# -*- coding: utf-8 -*-
"""Amistoso: times e formacoes que o jogador escolhe antes da partida (modulo puro: sem pygame, sem random).

TEAMS: lista de times que ja existem no jogo -- os 2 classicos do amistoso (azul e vermelho, o padrao de
sempre), clubes da carreira (career.CLUBS), times da campanha (story.TEAMS) e da liga do Modo Robos
(robot_league.TEAM_NAMES/COLORS). Cada um: {"id", "name", "color", "ovr" (forca no amistoso), "src" (de onde
vem), "names" (5 robos, ordem GK DEF MID MID ATT)}. Os classicos tem squad None: o Team do motor nasce
exatamente como antes (atributos base 65, nomes "VOCE"/"CPU" ou "JOGADOR 1"/"JOGADOR 2").

FORMATIONS: posicoes base dos 5 robos (fracao x a partir do proprio gol, fracao y), na ordem do motor
(indice 0 = goleiro, 4 = quem da a saida). Os papeis (GK/DEF/MID/MID/ATT -> chassi e atributos) NAO mudam:
a formacao so muda onde cada robo fica e para onde volta (soccer.Game.formation_pos), mais um "push"
(avanco/recuo do bloco inteiro, fracao do campo) quando diferente de 0.0. "equilibrada" = soccer.FORMATION
de sempre com push 0.0 (o padrao reproduz exatamente o motor antigo; goldens 80/80).
"""
import career
import robot_league
import story

CLASSIC = ("azul", "vermelho")
DEFAULT_TEAMS = ("azul", "vermelho")
DEFAULT_FORMATION = "equilibrada"
FORCE_MIN, FORCE_MAX = 45, 85

# id -> {"name", "code" (notacao: linhas de linha sem o goleiro), "desc", "pts": 5 x (fx, fy), "push"}
FORMATIONS = {
    "equilibrada": {"name": "EQUILIBRADA", "code": "1-2-1", "desc": "a de sempre: um atrás, dois no meio",
                    "pts": ((0.05, 0.50), (0.25, 0.50), (0.45, 0.22), (0.45, 0.78), (0.66, 0.50)),
                    "push": 0.0},
    "retranca": {"name": "RETRANCA", "code": "2-1-1", "desc": "dois zagueiros e o time recuado",
                 "pts": ((0.05, 0.50), (0.20, 0.30), (0.20, 0.70), (0.38, 0.50), (0.56, 0.50)),
                 "push": -0.06},
    "ofensiva": {"name": "OFENSIVA", "code": "1-1-2", "desc": "dois atacantes abertos lá na frente",
                 "pts": ((0.05, 0.50), (0.28, 0.50), (0.48, 0.50), (0.68, 0.26), (0.68, 0.74)),
                 "push": 0.05},
    "quadrado": {"name": "QUADRADO", "code": "2-2", "desc": "duas linhas de dois, bem fechado",
                 "pts": ((0.05, 0.50), (0.25, 0.28), (0.55, 0.28), (0.25, 0.72), (0.55, 0.72)),
                 "push": 0.0},
    "pressao": {"name": "PRESSÃO", "code": "1-2-1", "desc": "linha alta: aperta a saída do rival",
                "pts": ((0.05, 0.50), (0.40, 0.50), (0.58, 0.22), (0.58, 0.78), (0.76, 0.50)),
                "push": 0.08},
}
FORMATION_ORDER = ("equilibrada", "retranca", "ofensiva", "quadrado", "pressao")


def _force_story(ovr):
    """Forca da campanha (escala do Modo Robos, ~36-78) para a do amistoso (atributos base 65)."""
    return max(FORCE_MIN, min(FORCE_MAX, int(round(50 + (ovr - 36) * 0.7))))


def _robot_names(name):
    tag = name.split()[0][:8]
    return ["%s %d" % (tag, i + 1) for i in range(5)]


def _build():
    out = [
        {"id": "azul", "name": "Azul Clássico", "color": (50, 120, 255), "ovr": 65, "src": "AMISTOSO",
         "names": None},
        {"id": "vermelho", "name": "Vermelho Clássico", "color": (235, 65, 65), "ovr": 65, "src": "AMISTOSO",
         "names": None},
    ]
    # carreira: 4 clubes da divisao 1, 2 da 2 e 2 da 3 (forca = base da divisao)
    for i in (0, 1, 3, 4, 10, 14, 16, 18):
        name, color = career.CLUBS[i]
        out.append({"id": "car_%d" % i, "name": name, "color": tuple(color), "ovr": career.DIV_BASE[i // 8],
                    "src": "CARREIRA", "names": _robot_names(name)})
    # campanha: do Clube do Xadrez ao X-Omega Prime (nomes dos robos da historia)
    for tid in ("xadrez", "padaria", "impecaveis", "sakura", "aspirateurs", "dustbunnies", "kenji_team",
                "trovoes", "x9", "esfregao", "higiene", "guarda_zero", "xomega_prime"):
        t = story.TEAMS[tid]
        out.append({"id": "st_" + tid, "name": t["name"], "color": tuple(t["color"]),
                    "ovr": _force_story(t["ovr"]), "src": "CAMPANHA", "names": list(t["names"])})
    # liga do Modo Robos
    for i, ovr in ((0, 58), (1, 60), (5, 62), (6, 64), (9, 66), (15, 70)):
        name = robot_league.TEAM_NAMES[i]
        out.append({"id": "rl_%d" % i, "name": name, "color": tuple(robot_league.TEAM_COLORS[i]), "ovr": ovr,
                    "src": "MODO ROBÔS", "names": _robot_names(name)})
    return tuple(out)


TEAMS = _build()
TEAM_IDS = tuple(t["id"] for t in TEAMS)
BY_ID = {t["id"]: t for t in TEAMS}


def team(tid):
    """Time pelo id (desconhecido -> None)."""
    return BY_ID.get(tid)


def formation(fid):
    """Formacao pelo id (desconhecido -> a padrao)."""
    return FORMATIONS.get(fid) or FORMATIONS[DEFAULT_FORMATION]


def squad(tid):
    """Elenco no formato legado do soccer.Team: [(nome, forca)] x 5, ou None (classico = motor de sempre)."""
    t = BY_ID.get(tid)
    if t is None or t["names"] is None:
        return None
    return [(nm, t["ovr"]) for nm in t["names"]]


def sanitize(sel):
    """Escolha valida {"teams": (id0, id1), "forms": (f0, f1)}: id desconhecido -> padrao; mesmo time dos dois
    lados -> o lado 1 vai para o proximo da lista."""
    if not isinstance(sel, dict):
        sel = {}
    teams = list(sel.get("teams") or DEFAULT_TEAMS)[:2]
    forms = list(sel.get("forms") or (DEFAULT_FORMATION, DEFAULT_FORMATION))[:2]
    while len(teams) < 2:
        teams.append(DEFAULT_TEAMS[len(teams)])
    while len(forms) < 2:
        forms.append(DEFAULT_FORMATION)
    teams = [t if t in BY_ID else DEFAULT_TEAMS[i] for i, t in enumerate(teams)]
    forms = [f if f in FORMATIONS else DEFAULT_FORMATION for f in forms]
    if teams[0] == teams[1]:
        teams[1] = TEAM_IDS[(TEAM_IDS.index(teams[1]) + 1) % len(TEAM_IDS)]
    return {"teams": tuple(teams), "forms": tuple(forms)}


def is_default(sel):
    s = sanitize(sel)
    return s["teams"] == DEFAULT_TEAMS and s["forms"] == (DEFAULT_FORMATION, DEFAULT_FORMATION)


def cycle_team(cur, other, step):
    """Proximo time da lista (step +1/-1), pulando o do outro lado."""
    i = TEAM_IDS.index(cur) if cur in BY_ID else 0
    n = len(TEAM_IDS)
    for _ in range(n):
        i = (i + step) % n
        if TEAM_IDS[i] != other:
            return TEAM_IDS[i]
    return cur


def cycle_formation(cur, step):
    i = FORMATION_ORDER.index(cur) if cur in FORMATIONS else 0
    return FORMATION_ORDER[(i + step) % len(FORMATION_ORDER)]


def random_pick(rng):
    """Escolha sorteada com o RNG recebido (nunca o random global): dois times diferentes e duas formacoes."""
    a = rng.randrange(len(TEAM_IDS))
    b = rng.randrange(len(TEAM_IDS) - 1)
    if b >= a:
        b += 1
    return {"teams": (TEAM_IDS[a], TEAM_IDS[b]),
            "forms": (FORMATION_ORDER[rng.randrange(len(FORMATION_ORDER))],
                      FORMATION_ORDER[rng.randrange(len(FORMATION_ORDER))])}
