# -*- coding: utf-8 -*-
"""Estatisticas da partida e MELHOR DO JOGO (modulo puro: sem pygame e sem random global).

O motor (soccer.Game) so OBSERVA o jogo: cada robo tem um PStat (contadores) e os ganchos somam nos
lances que ja acontecem (chute, passe, dominio, desarme, defesa, gol). Nenhuma chamada a RNG, nenhuma
decisao muda (goldens identicos). No fim, summary() monta um dict JSON-simples usado pelas telas e pelos
acumulados (artilharia/assistencias dos saves).

Definicoes (as mesmas na tela e na spec docs/specs/estatisticas.md):
- gol (g): o ultimo robo que dominou a bola antes dela entrar (o mesmo "name/pid" do evento de gol).
  Gol contra (og) nao conta como gol do robo nem gera assistencia.
- assistencia (a): o ultimo PASSE certo do mesmo time para o autor do gol, recebido ate ASSIST_WINDOW s
  (tempo de jogo) antes do gol, sem o rival ter dominado a bola no meio.
- chute (sh): chute da IA (ai_shoot), chute humano na direcao do gol ou gol sem chute registrado.
  No gol (sot): virou gol ou foi defendido pelo goleiro rival.
- passe (pa/pc): passe tentado / certo (o proximo robo a dominar a bola e do mesmo time).
- desarme (tk): tomou a bola do rival no corpo a corpo. Drible (dr): o rival tentou o desarme e falhou.
- defesa (sv, goleiro): o goleiro tocou (segurou ou espalmou) um chute do rival.
- posse (%): tempo de jogo com a bola sob controle (ou solta depois do toque) de cada time.

Nota (0-10) = 5 + pontos/30, pontos (inteiros) = 30 g + 20 a + 8 sv + 4 sot + 3 tk + 1 dr + 1 pc - 20 og
(desarmes e dribles sao muitos por partida no motor: pesam pouco; gol e assistencia decidem).
MELHOR DO JOGO: maior pontuacao; empate -> time vencedor, mais gols, mais assistencias, mais defesas,
mais desarmes, lado da casa, ordem no time (deterministico).
"""
import math

ASSIST_WINDOW = 10.0                 # s de jogo entre receber o passe e marcar
PKEYS = ("g", "a", "sh", "sot", "pa", "pc", "tk", "dr", "sv", "og")
TKEYS = ("g", "sh", "sot", "pa", "pc", "tk", "dr", "sv")
POINTS = {"g": 30, "a": 20, "sv": 8, "tk": 3, "sot": 4, "dr": 1, "pc": 1, "og": -20}
ROLE_ORDER = {"GK": 0, "DEF": 1, "MID": 2, "ATT": 3}
ROLE_PT = {"GK": "GOL", "DEF": "DEF", "MID": "MEI", "ATT": "ATA"}
VAL_MAX = 999


class PStat:
    """Contadores de um robo na partida (zerados a cada Player novo)."""
    __slots__ = PKEYS

    def __init__(self):
        for k in PKEYS:
            setattr(self, k, 0)

    def as_dict(self):
        return {k: getattr(self, k) for k in PKEYS}


def points(row):
    return sum(POINTS[k] * int(row.get(k, 0)) for k in POINTS)


def nota(row):
    return round(max(0.0, min(10.0, 5.0 + points(row) / 30.0)), 1)


def pick_mvp(players, score):
    """Indice do MELHOR DO JOGO em `players` (ou None se vazio). Deterministico."""
    if not players:
        return None
    a, b = int(score[0]), int(score[1])
    win = 0 if a > b else 1 if b > a else None

    def key(i):
        r = players[i]
        return (points(r), 1 if r.get("team") == win else 0, r.get("g", 0), r.get("a", 0), r.get("sv", 0),
                r.get("tk", 0), -int(r.get("team", 0)), -int(r.get("idx", i)))
    return max(range(len(players)), key=key)


def _team_rows(players, poss):
    rows = []
    for t in (0, 1):
        row = {k: 0 for k in TKEYS}
        for p in players:
            if p["team"] == t:
                for k in TKEYS:
                    row[k] += p.get(k, 0)
        row["poss"] = poss[t]
        rows.append(row)
    for t in (0, 1):                     # gols contra contam no placar do time que se beneficiou
        rows[t]["g"] += sum(p.get("og", 0) for p in players if p["team"] == 1 - t)
    return rows


def poss_pct(t0, t1):
    tot = t0 + t1
    if tot <= 0:
        return [50, 50]
    p0 = int(round(100.0 * t0 / tot))
    return [p0, 100 - p0]


def finish(players, score, poss, team_names=("", ""), team_colors=((255, 255, 255), (255, 255, 255)),
           sim=False):
    """Dict final: {"sim","score","teams":[2],"players":[...],"mvp":idx}. players ja com g/a/... por robo."""
    for p in players:
        p["nota"] = nota(p)
    teams = _team_rows(players, poss)
    for t in (0, 1):
        teams[t]["name"] = team_names[t]
        teams[t]["color"] = list(team_colors[t])[:3]
    return {"sim": bool(sim), "score": [int(score[0]), int(score[1])], "teams": teams, "players": players,
            "mvp": pick_mvp(players, score)}


def from_engine(teams, score, poss_time, fallback=None):
    """Resumo de uma partida jogada no motor (soccer.Team com Player.st). fallback = 2 listas de 5 nomes para
    robos sem nome (amistoso classico: os mesmos apelidos da narracao)."""
    players = []
    for t in teams:
        for p in t.players:
            st = getattr(p, "st", None)
            row = st.as_dict() if st is not None else {k: 0 for k in PKEYS}
            name = p.name or (fallback[t.idx % 2][p.idx] if fallback else "")
            row.update(team=t.idx, idx=p.idx, name=name, role=p.role, pid=p.pid, chassis=p.chassis,
                       paint=list(p.paint) if p.paint else None)
            players.append(row)
    out = finish(players, score, poss_pct(*poss_time), (teams[0].name, teams[1].name),
                 (tuple(teams[0].color), tuple(teams[1].color)))
    for t, row in zip(teams, out["teams"]):             # escudo (nome/cor do time; amistoso: "VOCE" = Azul)
        cr = getattr(t, "crest", None)
        if cr:
            row["crest"] = [cr[0], list(cr[1])[:3], cr[2]]
    return out


def mvp_row(summary):
    """Linha do MELHOR DO JOGO (ou None)."""
    if not isinstance(summary, dict):
        return None
    i = summary.get("mvp")
    pl = summary.get("players") or ()
    return pl[i] if isinstance(i, int) and 0 <= i < len(pl) else None


def mvp_line(row):
    """Texto curto das estatisticas do MVP: "2 gols, 1 assist., 4 chutes (3 no gol)"."""
    if row is None:
        return ""
    bits = []
    for k, one, many in (("g", "gol", "gols"), ("a", "assist.", "assist."), ("sv", "defesa", "defesas"),
                         ("tk", "desarme", "desarmes"), ("dr", "drible", "dribles")):
        v = int(row.get(k, 0))
        if v:
            bits.append("%d %s" % (v, one if v == 1 else many))
    if row.get("sh"):
        bits.append("%d chute%s (%d no gol)" % (row["sh"], "" if row["sh"] == 1 else "s", row.get("sot", 0)))
    if row.get("pa"):
        bits.append("passes %d/%d" % (row.get("pc", 0), row["pa"]))
    return ", ".join(bits[:4]) if bits else "partida segura"


def plural(n, one, many):
    """"1 gol" / "2 gols"."""
    return "%d %s" % (n, one if n == 1 else many)


def goal_rows(summary, team=None):
    """[(pid, name, team, g, a, mvp)] por robo com algo a acumular (artilharia/assistencias/MVP)."""
    out = []
    if not isinstance(summary, dict):
        return out
    mvp = summary.get("mvp")
    for i, p in enumerate(summary.get("players") or ()):
        if team is not None and p.get("team") != team:
            continue
        out.append((p.get("pid"), p.get("name", ""), p.get("team", 0), int(p.get("g", 0)), int(p.get("a", 0)),
                    1 if i == mvp else 0))
    return out


# ---------------------------------------------------------------- partidas SIMULADAS
# Pesos por papel (gol, assistencia, chute, passe, desarme, drible) - calibrados a olho contra partidas do motor
# (tests/test_match_stats.py mede as medias).
W_GOAL = {"GK": 0.02, "DEF": 0.9, "MID": 2.2, "ATT": 4.5}
W_AST = {"GK": 0.4, "DEF": 1.2, "MID": 3.0, "ATT": 2.0}
W_SHOT = {"GK": 0.0, "DEF": 0.8, "MID": 2.2, "ATT": 3.5}
W_PASS = {"GK": 1.2, "DEF": 2.4, "MID": 3.0, "ATT": 1.6}
W_TACK = {"GK": 0.0, "DEF": 3.0, "MID": 2.4, "ATT": 1.2}
W_DRIB = {"GK": 0.0, "DEF": 0.6, "MID": 2.0, "ATT": 3.0}
ATTR_W = {"g": ("chu", "ctr"), "a": ("vis", "ctr"), "sh": ("chu", "vel"), "pa": ("vis", "ctr"),
          "tk": ("def", "ace"), "dr": ("ctr", "vel")}
# Medido no motor (30 partidas 65x65, por time): 16,5 chutes, 6,8 no gol, 11,5 passes (5,9 certos), 20 desarmes,
# 21 dribles, 5,7 defesas, ~8% dos gols com assistencia (a IA conduz e chuta mais do que passa).
SIM_AST_P = 0.12                    # chance de um gol simulado ter assistencia


def _skill(p, kind):
    """Fator 0.6..1.4 pelo atributo do papel (robos) ou pelo overall (carreira)."""
    a = p.get("attrs")
    if isinstance(a, dict):
        v = sum(float(a.get(k, 50)) for k in ATTR_W[kind]) / len(ATTR_W[kind])
    else:
        v = float(p.get("ovr", 60))
    return 0.6 + 0.8 * max(0.0, min(1.0, (v - 20.0) / 79.0))


def _pick(rng, weights):
    tot = sum(weights)
    if tot <= 0:
        return None
    x = rng.random() * tot
    for i, w in enumerate(weights):
        x -= w
        if x < 0:
            return i
    return len(weights) - 1


def _spread(rng, n, weights):
    out = [0] * len(weights)
    for _ in range(max(0, int(n))):
        i = _pick(rng, weights)
        if i is not None:
            out[i] += 1
    return out


def _strength(players):
    vals = []
    for p in players:
        a = p.get("attrs")
        vals.append(sum(float(v) for v in a.values()) / max(1, len(a)) if isinstance(a, dict)
                    else float(p.get("ovr", 60)))
    return sum(vals) / max(1, len(vals))


def simulate(rng, score, sides, names=("", ""), colors=((255, 255, 255), (255, 255, 255))):
    """Estatisticas plausiveis de uma partida SIMULADA (o placar ja decidido nao muda).

    rng: random.Random PRIVADO (semente derivada da partida); sides: 2 listas de 5 dicts
    {"name","role","pid"(opcional),"attrs"(robos) ou "ovr"(carreira),"chassis","paint"} na ordem do motor
    (GK, DEF, MID, MID, ATT). Gols, assistencias e o resto saem proporcionais aos papeis/atributos."""
    score = [max(0, int(score[0])), max(0, int(score[1]))]
    stren = [_strength(sides[0]), _strength(sides[1])]
    players = []
    for t in (0, 1):
        for i, p in enumerate(sides[t]):
            row = {k: 0 for k in PKEYS}
            row.update(team=t, idx=i, name=p.get("name", ""), role=p.get("role", "MID"), pid=p.get("pid"),
                       chassis=p.get("chassis"), paint=list(p["paint"])[:3] if p.get("paint") else None)
            players.append(row)
    poss0 = 50.0 + (stren[0] - stren[1]) * 0.6 + rng.uniform(-6.0, 6.0)
    poss0 = int(round(max(30.0, min(70.0, poss0))))
    poss = [poss0, 100 - poss0]
    for t in (0, 1):
        mine = [p for p in players if p["team"] == t]
        src = sides[t]
        roles = [p["role"] for p in mine]

        def w(table, kind, excl=None):
            return [0.0 if (excl is not None and i == excl) else table.get(r, 1.0) * _skill(src[i], kind)
                    for i, r in enumerate(roles)]
        g = score[t]
        for _ in range(g):                                  # gols e assistencias
            s = _pick(rng, w(W_GOAL, "g"))
            mine[s]["g"] += 1
            mine[s]["sh"] += 1
            mine[s]["sot"] += 1
            if rng.random() < SIM_AST_P:
                a = _pick(rng, w(W_AST, "a", excl=s))
                if a is not None:
                    mine[a]["a"] += 1
        opp_gk_sv = rng.randint(3, 8) + (1 if stren[t] > stren[1 - t] + 6 else 0)
        miss = rng.randint(6, 13) + (2 if poss[t] > 55 else 0)
        for i, n in enumerate(_spread(rng, opp_gk_sv, w(W_SHOT, "sh"))):
            mine[i]["sh"] += n
            mine[i]["sot"] += n
        for i, n in enumerate(_spread(rng, miss, w(W_SHOT, "sh"))):
            mine[i]["sh"] += n
        gk_opp = next((p for p in players if p["team"] == 1 - t and p["role"] == "GK"), None)
        if gk_opp is not None:
            gk_opp["sv"] += opp_gk_sv
        pa = int(round((8 + rng.randint(0, 8)) * poss[t] / 50.0))
        acc = max(0.3, min(0.85, 0.5 + (stren[t] - 60.0) * 0.006 + rng.uniform(-0.06, 0.06)))
        pw = w(W_PASS, "pa")
        tries = _spread(rng, pa, pw)
        for i, n in enumerate(tries):
            mine[i]["pa"] += n
            mine[i]["pc"] += int(round(n * acc))
        for i, n in enumerate(_spread(rng, rng.randint(14, 26), w(W_TACK, "tk"))):
            mine[i]["tk"] += n
        for i, n in enumerate(_spread(rng, rng.randint(14, 27), w(W_DRIB, "dr"))):
            mine[i]["dr"] += n
    return finish(players, score, poss, names, colors, sim=True)


def side_from_cfg(cfg):
    """Lado para simulate() a partir de um cfg de partida (Game.start_robot_match / career.match_cfg)."""
    roles = ("GK", "DEF", "MID", "MID", "ATT")
    out = []
    for i, e in enumerate((cfg or {}).get("squad") or ()):
        role = roles[i] if i < len(roles) else "MID"
        if isinstance(e, dict):
            out.append({"name": e.get("name", ""), "role": role, "pid": e.get("pid"), "attrs": e.get("attrs"),
                        "chassis": e.get("chassis"), "paint": e.get("paint")})
        else:                                            # carreira: (nome, ovr, pid, pos)
            e = tuple(e)
            out.append({"name": e[0], "role": role, "ovr": float(e[1]) if len(e) > 1 else 60.0,
                        "pid": e[2] if len(e) > 2 else None})
    return out


def sim_cfgs(rng, score, home, away):
    """simulate() direto dos 2 cfgs de partida (nome/cor/squad)."""
    return simulate(rng, score, (side_from_cfg(home), side_from_cfg(away)),
                    (home.get("name", ""), away.get("name", "")),
                    (tuple(home.get("color", (255, 255, 255))), tuple(away.get("color", (255, 255, 255)))))


def seed_of(*parts):
    """Semente estavel (string) para o random.Random privado do SIMULAR."""
    return "stats|" + "|".join(str(p) for p in parts)


# ---------------------------------------------------------------- acumulados (saves)
CS_KEYS = ("g", "a", "mvp", "j")


def clean_cs(v):
    """Totais de um robo/jogador {"g","a","mvp","j"} limpos (ints 0..10^6); ausente -> zeros."""
    v = v if isinstance(v, dict) else {}
    out = {}
    for k in CS_KEYS:
        x = v.get(k)
        if isinstance(x, bool) or not isinstance(x, (int, float)) or (isinstance(x, float) and not math.isfinite(x)):
            x = 0
        out[k] = max(0, min(10 ** 6, int(x)))
    return out


def add_cs(cs, g, a, mvp, played=1):
    cs = clean_cs(cs)
    cs["g"] += int(g)
    cs["a"] += int(a)
    cs["mvp"] += int(mvp)
    cs["j"] += int(played)
    return clean_cs(cs)


def top_scorers(entries, n=5):
    """entries: [(name, team_name, color, g, a, extra...)] -> top n por gols, assistencias e nome."""
    rows = [e for e in entries if e[3] > 0 or e[4] > 0]
    rows.sort(key=lambda e: (-e[3], -e[4], e[0], e[1]))
    return rows[:n]
