"""Testes de game/story.py (dados da campanha). Mede texto com pygame.font real (SDL dummy).

Rodar da raiz: SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_story.py [teste ...]
Nao grava em nenhum ~/.soccerpy_*.json (so le dados puros).
"""
import os
import re
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import parts  # noqa: E402
import robots  # noqa: E402
import skills  # noqa: E402
import campaign as cm  # noqa: E402
import story as st  # noqa: E402

PASS, FAIL = [], []

BOX_W, MAX_LINES, MAX_TEXT, MAX_OPT, MAX_NAME = 780, 4, 260, 46, 14
FX_KEYS = {"flag", "scrap", "xp_hero", "xp_team", "piece", "skill", "pts"}     # skill/pts: B11
BAD_CHARS = "‘’“”–—…→←"
FLAG_RE = re.compile(r"^[A-Za-z0-9_]{1,32}$")
ID_RE = re.compile(r"^[A-Za-z0-9_]+$")
_font = None


def font():
    global _font
    if _font is None:
        import pygame
        pygame.font.init()
        _font = pygame.font.Font(None, 28)
    return _font


def wrap(text, width=BOX_W):
    """Quebra gulosa por palavras (como a UI fara)."""
    f = font()
    lines, cur = [], ""
    for w in text.split(" "):
        t = w if not cur else cur + " " + w
        if cur and f.size(t)[0] > width:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    return lines


# ----------------------------------------------------------------- helpers de varredura
def items(scene):
    """(tipo, item) de cada item de lines: 'line' ou 'choice'."""
    return [("choice" if isinstance(it, dict) else "line", it) for it in scene["lines"]]


def all_lines(scene):
    """Todas as linhas (principais, replies), na forma tupla."""
    out = []
    for kind, it in items(scene):
        if kind == "line":
            out.append(it)
        else:
            for o in it["opts"]:
                out.extend(o.get("reply", []))
    return out


def all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from all_strings(k)
            yield from all_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from all_strings(v)


def chapters(draft=False):
    return [c for c in st.CHAPTERS if draft or not c.get("draft")]


def stages_of(t):
    return cm.stages_of(t)


def hook_scenes(t):
    h = t["hooks"]
    out = list(h["before"].values()) + list(h["after"].values())
    out += [x for x in (h["win"], h["lose"], h["elim"]) if x]
    return out


def check_cond_format(cond, where):
    """Formato de cond (o mesmo de Campaign.check_cond): None | ("flag"|"noflag", f) | ("done", id) |
    ("count", prefixo, n) | ("all"|"any", [conds])."""
    if cond is None:
        return
    assert isinstance(cond, tuple) and cond, (where, cond)
    k = cond[0]
    if k in ("flag", "noflag"):
        assert len(cond) == 2 and FLAG_RE.match(cond[1]), (where, cond)
    elif k == "done":
        d = cond[1]
        assert len(cond) == 2 and (d in st.SCENES or (d.startswith("reward:") and d[7:] in st.REWARDS)
                                   or (d.startswith("side:") and d[5:] in st.SIDES)), (where, cond)
    elif k == "count":
        assert len(cond) == 3 and isinstance(cond[1], str) and cond[1], (where, cond)
        assert isinstance(cond[2], int) and 1 <= cond[2] <= 50, (where, cond)
    elif k in ("all", "any"):
        assert len(cond) == 2 and len(cond[1]) >= 1, (where, cond)
        for c in cond[1]:
            check_cond_format(c, where)
    else:
        raise AssertionError("cond desconhecida em %s: %r" % (where, cond))


def ending_scenes():
    return [x for _c, sc in st.ENDINGS for x in ([sc] if isinstance(sc, str) else sc)]


def side_scenes():
    return [x for sp in st.SIDES.values() for x in sp["scenes"].values() if x]


def walk(policy):
    """Percorre o grafo de nos das campanhas nao-draft; devolve (ordem de cenas, terminou_em_end).

    policy 'win' = sempre vence; 'lose' = elimina uma vez no grupo, perde uma vez a SF e perde a final
    PITY_MAX vezes (ate o pity dar a vitoria), visitando os hooks de cada derrota.
    """
    order = []

    def visit(sid):
        if sid:
            assert sid in st.SCENES, "cena inexistente: %s" % sid
            if sid not in order:
                order.append(sid)

    ended = False
    for ch in chapters():
        nodes = ch["nodes"]
        assert nodes, "capitulo %s sem nos" % ch["id"]
        for n in nodes:                     # nos condicionais: visita os dois ramos (todas as cenas)
            kind, ref = n[0], n[1]
            if kind == "end" and ref == cm.AUTO_END:
                for sid in ending_scenes():
                    visit(sid)
                ended = True
            elif kind in ("scene", "end"):
                visit(ref)
                if kind == "end":
                    ended = True
            elif kind == "tournament":
                t = st.TOURNAMENTS[ref]
                h = t["hooks"]
                stages = stages_of(t)
                attempts = 0
                losses_f = 0
                while True:
                    attempts += 1
                    assert attempts < 20, "laco de retry sem saida em %s" % ref
                    failed = False
                    for s in stages:
                        visit(h["before"].get(s))
                        if policy == "lose":
                            if attempts == 1 and cm.round_stages(t) and s == cm.round_stages(t)[-1]:
                                assert h["elim"], "torneio %s sem hook de eliminacao" % ref
                                visit(h["elim"])
                                failed = True
                                break
                            if s == "SF" and attempts == 2:
                                assert h["lose"], "torneio %s sem hook de derrota" % ref
                                visit(h["lose"])
                                failed = True
                                break
                            if cm.is_boss_stage(t, s) and losses_f < st.PITY_MAX:
                                assert h["lose"], "torneio %s sem hook de derrota" % ref
                                visit(h["lose"])
                                losses_f += 1
                                failed = True
                                break
                        visit(h["after"].get(s))
                    if not failed:
                        break
                visit(h["win"])
            elif kind == "chapter_end":
                assert ref == ch["id"]
    for sid in side_scenes():               # missoes secundarias: pre/win/lose
        visit(sid)
    return order, ended


# ================================================================= testes
def test_encoding_and_chars():
    n = 0
    for s in all_strings([st.CHARACTERS, st.TEAMS, st.TOURNAMENTS, st.SCENES, st.CHAPTERS, st.REWARDS]):
        s.encode("latin-1")
        assert s.isprintable(), repr(s)
        assert not any(c in s for c in BAD_CHARS), repr(s)
        assert "…" not in s and "\xa0" not in s, repr(s)
        assert "‘" not in s and "“" not in s
        n += 1
    assert n > 200


def test_characters_and_vocab():
    need = {"teo", "ambrosio", "vivi", "bia", "dudu", "augusto", "gervasio", "rodolfo", "helena",
            "kenji", "narrador", "ze"}
    assert set(st.CHARACTERS) == need
    names = set()
    for cid, c in st.CHARACTERS.items():
        assert ID_RE.match(cid)
        assert c["name"] == c["name"].upper() and len(c["name"]) <= MAX_NAME, c["name"]
        assert c["name"] not in names
        names.add(c["name"])
        for k in ("color", "skin"):
            assert len(c[k]) == 3 and all(0 <= v <= 255 for v in c[k])
        style, hc = c["hair"]
        assert style in st.HAIR_STYLES and len(hc) == 3
        assert all(a in st.ACCESSORIES for a in c["acc"]), cid
        kind, oc = c["outfit"]
        assert kind in st.OUTFITS and len(oc) == 3
    assert len(set(st.MOODS)) == len(st.MOODS)
    for m in ("neutro", "feliz", "susto", "triste", "bravo", "pensando", "convencida", "convencido",
              "corada", "suor", "espirro", "calmo", "cansado", "robo"):
        assert m in st.MOODS
    assert len(set(st.BGS)) == len(st.BGS)
    for b in ("garagem", "oficina", "quadra", "ginasio", "arena", "camarim", "mundial", "federacao"):
        assert b in st.BGS


def test_fase4_visual_vocab():
    """A12/A13: humores, estilos e cenarios novos registrados (sem repetir) e so ids ASCII."""
    for m in ("determinado", "maravilhado", "malicioso", "sonolento", "chorando", "gritando", "piscando",
              "euforico"):
        assert m in st.MOODS, m
    for h in ("trancas", "coque", "moicano"):
        assert h in st.HAIR_STYLES, h
    for a in ("bone", "bengala", "avental", "tiara", "cachecol"):
        assert a in st.ACCESSORIES, a
    for o in ("avental", "colete"):
        assert o in st.OUTFITS, o
    for b in ("praca", "laboratorio", "aeroporto", "dojo", "fabrica", "coliseu", "lanchonete", "cabine"):
        assert b in st.BGS, b
    for vocab in (st.MOODS, st.HAIR_STYLES, st.ACCESSORIES, st.OUTFITS, st.BGS):
        assert len(set(vocab)) == len(vocab)
        assert all(ID_RE.match(v) for v in vocab), vocab


def test_text_fits_box():
    f = font()
    worst = 0
    for sid, sc in st.SCENES.items():
        for kind, it in items(sc):
            if kind == "choice":
                assert len(it["q"]) <= MAX_TEXT and len(wrap(it["q"])) <= MAX_LINES, (sid, it["q"])
                assert 2 <= len(it["opts"]) <= 3, sid
                for o in it["opts"]:
                    assert len(o["t"]) <= MAX_OPT, (sid, o["t"])
                    assert f.size(o["t"])[0] <= BOX_W, (sid, o["t"])
        for ln in all_lines(sc):
            who, mood, text = ln[0], ln[1], ln[2]
            assert len(st.CHARACTERS[who]["name"]) <= MAX_NAME
            assert len(text) <= MAX_TEXT, (sid, len(text), text)
            n = len(wrap(text))
            worst = max(worst, n)
            assert n <= MAX_LINES, (sid, n, text)
    print("  (maior fala: %d linhas)" % worst)


def test_scene_structure_and_refs():
    for sid, sc in st.SCENES.items():
        assert ID_RE.match(sid)
        assert sc["bg"] in st.BGS, sid
        cast = sc["cast"]
        assert len(set(cast)) == len(cast) and all(c in st.CHARACTERS for c in cast), sid
        main = [it for k, it in items(sc) if k == "line"]
        assert 8 <= len(main) <= 14, (sid, len(main))
        assert sum(1 for k, _ in items(sc) if k == "choice") <= 1, sid
        # escolha so no fim da cena
        for i, (k, _) in enumerate(items(sc)):
            if k == "choice":
                assert i == len(sc["lines"]) - 1, sid
        for ln in all_lines(sc):
            assert len(ln) in (3, 4), (sid, ln)
            who, mood = ln[0], ln[1]
            assert who in st.CHARACTERS, (sid, who)
            assert who == "narrador" or who in cast, (sid, who)
            assert mood in st.MOODS, (sid, mood)
            if len(ln) == 4:
                cond = ln[3]
                check_cond_format(cond, sid)
                assert cond != ("done", sid), sid


def test_effects_valid():
    for sid, sc in st.SCENES.items():
        for kind, it in items(sc):
            if kind != "choice":
                continue
            for o in it["opts"]:
                assert set(o) <= {"t", "fx", "reply"}, (sid, o.keys())
                fx = o.get("fx", {})
                assert set(fx) <= FX_KEYS, (sid, fx)
                if "flag" in fx:
                    assert FLAG_RE.match(fx["flag"]), fx["flag"]
                for k in ("scrap", "xp_hero", "xp_team"):
                    if k in fx:
                        assert isinstance(fx[k], int) and 0 <= fx[k] <= 100, (sid, k, fx[k])
                if "piece" in fx:
                    check_piece(fx["piece"])
                if "skill" in fx:
                    check_skill(fx["skill"])
                if "pts" in fx:
                    check_pts(fx["pts"], 5)
                assert o.get("reply", []), "opcao sem reply em %s" % sid


def check_skill(sk):
    """fx/REWARDS `skill` (B11): {"robot": "hero"|"team", "id": skills.SKILLS, "rank": 1..3} ou lista."""
    lst = sk if isinstance(sk, list) else [sk]
    assert lst, sk
    for x in lst:
        assert isinstance(x, dict) and set(x) <= {"robot", "id", "rank"} and "id" in x, x
        assert x.get("robot", "hero") in ("hero", "team"), x
        assert x["id"] in skills.SKILLS, x
        assert isinstance(x.get("rank", 1), int) and 1 <= x.get("rank", 1) <= 3, x


def check_pts(n, hi):
    """fx/REWARDS `pts` (B11): int 1..hi (heroi) ou {"robot": "hero"|"team", "n": 1..hi}."""
    if isinstance(n, dict):
        assert set(n) <= {"robot", "n"} and n.get("robot", "hero") in ("hero", "team"), n
        n = n.get("n")
    assert isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= hi, n


def test_skill_pts_validators():
    """As regras novas (B11) aceitam o formato da spec e recusam lixo (o roteiro atual nao usa as chaves)."""
    check_skill({"robot": "hero", "id": "arrancada", "rank": 1})
    check_skill([{"id": "leitura"}, {"robot": "team", "id": "poupanca", "rank": 2}])
    check_pts(2, 5)
    check_pts({"robot": "team", "n": 3}, 10)
    bad = [lambda: check_skill({"robot": "vilao", "id": "arrancada"}),
           lambda: check_skill({"id": "nao_existe"}),
           lambda: check_skill({"id": "rolando"}),                 # passiva de reliquia: nao se aprende
           lambda: check_skill({"id": "curva", "rank": 4}),
           lambda: check_skill([]),
           lambda: check_pts(0, 5), lambda: check_pts(6, 5), lambda: check_pts(True, 5),
           lambda: check_pts({"robot": "hero", "n": 99}, 10)]
    for fn in bad:
        try:
            fn()
        except AssertionError:
            continue
        raise AssertionError("validador aceitou lixo")


def check_piece(p):
    assert set(p) == {"model", "rar"}, p
    assert p["model"] in parts.PARTS, p
    assert isinstance(p["rar"], int) and 0 <= p["rar"] <= 3, p


def test_flags_budget_and_order():
    written, read = set(), set()
    for sc in st.SCENES.values():
        for kind, it in items(sc):
            if kind == "choice":
                for o in it["opts"]:
                    if "flag" in o.get("fx", {}):
                        written.add(o["fx"]["flag"])
        for ln in all_lines(sc):
            if len(ln) == 4 and ln[3][0] in ("flag", "noflag"):
                read.add(ln[3][1])
    assert len(written | read) <= 48, len(written | read)
    assert read <= written, "flag lida e nunca escrita: %s" % (read - written)
    # ordem: a flag lida precisa ser escrita por cena visitada ANTES (em alguma das politicas)
    for pol in ("win", "lose"):
        order, _ = walk(pol)
        seen_flags, seen_scenes = set(), set()
        for sid in order:
            sc = st.SCENES[sid]
            for ln in all_lines(sc):
                if len(ln) == 4:
                    k, v = ln[3]
                    if k in ("flag", "noflag") and pol == "lose":
                        assert v in seen_flags, "flag %s lida em %s antes de ser escrita" % (v, sid)
                    if k == "done" and pol == "lose":
                        assert v in seen_scenes, "done %s lido em %s antes de existir" % (v, sid)
            for kind, it in items(sc):
                if kind == "choice":
                    for o in it["opts"]:
                        if "flag" in o.get("fx", {}):
                            seen_flags.add(o["fx"]["flag"])
            seen_scenes.add(sid)


def test_teams():
    for tid, t in st.TEAMS.items():
        assert ID_RE.match(tid)
        assert len(t["name"]) <= 24, t["name"]
        assert len(t["color"]) == 3 and len(t["paint"]) == 3
        assert 20 <= t["ovr"] <= 99
        assert len(t["names"]) == 5 and len(set(t["names"])) == 5, tid
        assert all(1 <= len(n) <= 12 for n in t["names"]), tid
        assert len(t["chassis"]) == 5 and all(c in robots.CHASSIS for c in t["chassis"]), tid
        assert isinstance(t["perfect"], bool)
    assert len({t["name"] for t in st.TEAMS.values()}) == len(st.TEAMS)
    expect = {"xadrez": 36, "turma3b": 38, "fundao": 39, "gremio": 39, "teatro": 40, "impecaveis": 41}
    for k, v in expect.items():
        assert st.TEAMS[k]["ovr"] == v
    assert st.TEAMS["impecaveis"]["perfect"] and not st.TEAMS["gremio"]["perfect"]


def test_tournaments():
    chap = {c["id"]: c for c in st.CHAPTERS}
    for tid, t in st.TOURNAMENTS.items():
        assert t["chapter"] in chap and t["bg"] in st.BGS and len(t["local"]) <= 40
        assert t["format"] in cm.FORMATS
        assert t["boss"] in st.TEAMS and t["final"] == t["boss"]
        assert set(t.get("boss_stages") or ()) <= set(stages_of(t)), tid
        for cond, over in t.get("alt", ()):             # variantes: trocam o time, nao o ovr (+-1)
            check_cond_format(cond, tid)
            assert over and set(over) <= {"qf", "sf", "final", "series", "group"}, (tid, over)
            for key, val in over.items():
                old = t.get(key)
                vals, olds = (val, old) if isinstance(val, list) else ([val], [old])
                assert len(vals) == len(olds), (tid, key)
                for a, b in zip(vals, olds):
                    assert a in st.TEAMS and abs(st.TEAMS[a]["ovr"] - st.TEAMS[b]["ovr"]) <= 1, (tid, key, a)
        assert isinstance(t["boss_delta"], (int, float))
        lo, hi = t["regular_delta"]
        assert lo <= hi
        h = t["hooks"]
        assert set(h) == {"before", "after", "win", "lose", "elim"}
        stages = stages_of(t)
        for s, sid in list(h["before"].items()) + list(h["after"].items()):
            assert s in stages and sid in st.SCENES, (tid, s, sid)
        for sid in hook_scenes(t):
            assert sid in st.SCENES
        ovrs = lambda ids: [st.TEAMS[i]["ovr"] for i in ids]  # noqa: E731
        if t["format"] == "cup":
            assert len(t["group"]) == 3 and len(set(t["group"])) == 3
            assert all(g in st.TEAMS for g in t["group"]) and t["sf"] in st.TEAMS
            assert t.get("qf") is None or t["qf"] in st.TEAMS
            regs = ovrs(t["group"])
            assert st.TEAMS[t["boss"]]["ovr"] >= max(regs + ovrs([t["sf"]])), tid
            c = chap[t["chapter"]]
            assert abs(c["F_end"] - t["boss_delta"] - st.TEAMS[t["boss"]]["ovr"]) <= 0.6, tid
            for o in regs:
                # passo 16: o motor exige regulares bem abaixo da Forca (F-O ~ 6..13 para 58-66%)
                assert 4 <= c["F_start"] - o <= 18, (tid, o)
            assert 1 <= c["F_start"] - st.TEAMS[t["sf"]]["ovr"] <= 11
            ids = t["group"] + [t["sf"], t["boss"]] + ([t["qf"]] if t.get("qf") else [])
            assert len(set(ids)) == len(ids), tid
        elif t["format"] == "league":
            assert len(t["group"]) == 5 and len(set(t["group"])) == 5, tid
            assert all(g in st.TEAMS for g in t["group"]) and t["sf"] in st.TEAMS and not t.get("qf")
            ids = t["group"] + [t["sf"], t["boss"]]
            assert len(set(ids)) == len(ids), tid
        elif t["format"] == "series":
            assert 2 <= len(t["series"]) <= 3 and all(x in st.TEAMS for x in t["series"]), tid
            assert t["final"] == t["series"][-1] and not t["group"] and t["sf"] is None, tid
        else:
            assert not t["group"] and t["sf"] is None
    # ovr nao decrescente entre capitulos (min e max por capitulo)
    last_min = last_max = 0
    for c in chapters():
        os_ = []
        for n in c["nodes"]:
            kind, ref = n[0], n[1]
            if kind == "tournament":
                t = st.TOURNAMENTS[ref]
                os_ += [st.TEAMS[i]["ovr"] for i in t["group"] + t.get("series", []) +
                        [t["sf"], t["boss"], t.get("qf")] if i]
        if os_:
            assert min(os_) >= last_min and max(os_) >= last_max, c["id"]
            last_min, last_max = min(os_), max(os_)


def test_rewards():
    recruits = 0
    for rid, r in st.REWARDS.items():
        assert set(r) <= {"scrap", "piece", "recruits", "unlock", "xp_hero", "xp_team", "equip_hero_piece", "title",
                          "skill", "pts"}
        if r.get("skill"):
            check_skill(r["skill"])
        if r.get("pts"):
            check_pts(r["pts"], 10)
        for k in ("scrap", "xp_hero", "xp_team"):
            assert isinstance(r.get(k, 0), int) and 0 <= r.get(k, 0) <= 1000
        for k in ("piece", "equip_hero_piece"):
            if r.get(k):
                check_piece(r[k])
        for u in r.get("unlock", []):
            assert u in robots.CHASSIS, u
        for rc in r.get("recruits", []):
            recruits += 1
            assert 1 <= len(rc["name"]) <= 12
            assert rc["role"] in ("GK", "DEF", "MID", "ATT")
            assert rc["chassis"] in robots.CHASSIS
            assert 20 <= rc["base_ovr"] <= 99
            assert 0 <= rc["level"] <= 10
            assert len(rc["paint"]) == 3
            if rc.get("piece"):
                check_piece(rc["piece"])
    assert recruits <= 3
    names = [rc["name"] for r in st.REWARDS.values() for rc in r.get("recruits", [])]
    assert len(set(names)) == len(names)


def test_chapters_structure():
    ids = [c["id"] for c in st.CHAPTERS]
    assert len(set(ids)) == len(ids) and ids[0] == "P"
    assert [c["id"] for c in st.CHAPTERS][1:7] == ["1", "2", "3", "4", "5", "6"]
    prev_f = 0
    for c in st.CHAPTERS:
        assert c["act"] in ("1", "2", "3"), c["id"]
        assert 0 <= c["econ_tier"] <= 3 and -1 <= c["tier_done_on_close"] <= 3
        assert c["F_start"] <= c["F_end"] and c["F_start"] >= prev_f - 3
        prev_f = c["F_end"]
        assert c["reward"] is None or c["reward"] in st.REWARDS
        assert len(c["title"]) <= 24 and len(c["subtitle"]) <= 32
        if c.get("draft"):
            assert c["nodes"] == []
            continue
        kinds = [n[0] for n in c["nodes"]]
        if kinds == ["end"]:                    # ponte provisoria (cap. 6 enquanto o Ato 2 e produzido)
            assert c is st.CHAPTERS[-1] and c["reward"] is None, c["id"]
            assert c["nodes"][0][1] in st.SCENES
            continue
        assert c["reward"] in st.REWARDS
        for n in c["nodes"]:
            k, ref = n[0], n[1]
            assert k in ("scene", "tournament", "chapter_end", "end")
            assert len(n) == 2 or (len(n) == 3 and k in ("scene", "tournament")), (c["id"], n)
            if len(n) == 3:
                check_cond_format(n[2], c["id"])
            if k == "end" and ref == cm.AUTO_END:
                assert st.ENDINGS, "no AUTO sem story.ENDINGS"
            elif k in ("scene", "end"):
                assert ref in st.SCENES
            if k == "tournament":
                assert ref in st.TOURNAMENTS and st.TOURNAMENTS[ref]["chapter"] == c["id"]
        last = c["nodes"][-1]
        assert last[0] in ("chapter_end", "end"), c["id"]
        # capitulo normal: 1 chapter_end no fim; o ULTIMO da campanha: chapter_end seguido de end
        assert kinds.count("chapter_end") == 1 and kinds.count("end") <= 1, c["id"]
        if last[0] == "end":
            assert c is st.CHAPTERS[-1], "so o ultimo capitulo pode terminar com end"
            assert c["nodes"][-2] == ("chapter_end", c["id"]), "end deve vir logo apos o chapter_end"
        else:
            assert last == ("chapter_end", c["id"])
    # o ultimo capitulo nao-draft so pode terminar com "end" se for o ultimo de todos
    nd = chapters()
    if nd[-1] is st.CHAPTERS[-1]:
        assert nd[-1]["nodes"][-1][0] == "end"


def test_reachability_and_no_dead_ends():
    win, _ = walk("win")
    lose, _ = walk("lose")
    reached = set(win) | set(lose)
    need = set()
    for c in chapters():
        for n in c["nodes"]:
            k, ref = n[0], n[1]
            if k == "end" and ref == cm.AUTO_END:
                need |= set(ending_scenes())
            elif k in ("scene", "end"):
                need.add(ref)
            elif k == "tournament":
                need |= set(hook_scenes(st.TOURNAMENTS[ref]))
    need |= set(side_scenes())
    assert need <= reached, need - reached
    # nenhuma cena orfa entre as nao-draft: toda cena usada por algum capitulo
    assert set(st.SCENES) <= need, "cenas orfas: %s" % (set(st.SCENES) - need)
    # politica 'lose' chega ao mesmo conjunto (derrotas so adicionam cenas)
    assert set(win) <= set(lose)
    assert len(win) == len(set(win)) and len(lose) == len(set(lose))


def test_budget_sanity():
    n = len(st.SCENES)
    lines = sum(len([i for k, i in items(s) if k == "line"]) for s in st.SCENES.values())
    chars = sum(len(ln[2]) for s in st.SCENES.values() for ln in all_lines(s))
    assert 12 <= n <= 80, n
    assert 100 <= lines <= 800, lines
    assert st.STORY_VERSION == 2
    print("  (cenas=%d falas-principais=%d falas-total=%d caracteres=%d)" % (
        n, lines, sum(len(all_lines(s)) for s in st.SCENES.values()), chars))


def test_facade_extend():
    """story.py junta os submodulos dos Atos 2/3/side; id repetido e erro, nunca sobrescrita."""
    import types
    import story_a2
    import story_a3
    import story_side
    for m in (story_a2, story_a3, story_side):
        for name in ("CHARACTERS", "TEAMS", "TOURNAMENTS", "SCENES", "REWARDS", "SIDES"):
            assert set(getattr(m, name)) <= set(getattr(st, name)), (m.__name__, name)
        assert all(c in st.CHAPTERS for c in m.CHAPTERS), m.__name__
    acts = [c["act"] for c in st.CHAPTERS]
    assert acts == sorted(acts), "capitulos fora da ordem dos Atos"
    assert [c["act"] for c in st.CHAPTERS if c["id"] in ("P", "1", "2", "3", "4", "5")] == ["1"] * 6
    # C2: o epilogo do Ato 1 e o no 0 do cap. 6 (saves migrados ficam em ch "6", node 0)
    cap5 = next(c for c in st.CHAPTERS if c["id"] == "5")
    cap6 = next(c for c in st.CHAPTERS if c["id"] == "6")
    assert cap5["nodes"][-1] == ("chapter_end", "5") and len(cap5["nodes"]) == 4
    assert cap6["act"] == "2" and cap6["nodes"][0][1] == "e1_epilogo"
    for name in ("CHARACTERS", "TEAMS", "TOURNAMENTS", "SCENES", "REWARDS"):   # SIDES: vazio por ora
        fake = types.SimpleNamespace(__name__="fake", CHAPTERS=[],
                                     **{k: {} for k in ("CHARACTERS", "TEAMS", "TOURNAMENTS",
                                                        "SCENES", "REWARDS", "SIDES")})
        getattr(fake, name)[next(iter(getattr(st, name)))] = {}
        before = {k: dict(getattr(st, k)) for k in ("CHARACTERS", "TEAMS", "TOURNAMENTS", "SCENES",
                                                     "REWARDS", "SIDES")}
        try:
            st._extend(fake)
            raise AssertionError("id repetido em %s nao levantou" % name)
        except ValueError:
            pass
        assert all(getattr(st, k) == v for k, v in before.items()), "dados alterados apos erro"
    fake = types.SimpleNamespace(__name__="fake", CHAPTERS=[{"id": "P"}],
                                 **{k: {} for k in ("CHARACTERS", "TEAMS", "TOURNAMENTS", "SCENES",
                                                    "REWARDS", "SIDES")})
    n = len(st.CHAPTERS)
    try:
        st._extend(fake)
        raise AssertionError("capitulo repetido nao levantou")
    except ValueError:
        pass
    assert len(st.CHAPTERS) == n


def test_sides_and_endings_data():
    """story.SIDES (spec 6) e story.ENDINGS (spec 5): formato e referencias (vazios ate o C11/C13)."""
    for sid, sp in st.SIDES.items():
        assert ID_RE.match(sid) and len(sid) <= 24, sid
        assert {"title", "local", "bg", "team", "delta", "unlock", "scenes", "reward"} <= set(sp), sid
        assert len(sp["title"]) <= 24 and len(sp["local"]) <= 40 and sp["bg"] in st.BGS, sid
        assert sp["team"] in st.TEAMS and isinstance(sp["delta"], int) and 0 <= sp["delta"] <= 30, sid
        check_cond_format(sp["unlock"], sid)
        assert set(sp["scenes"]) <= {"pre", "win", "lose"} and sp["scenes"].get("pre"), sid
        assert all(x in st.SCENES for x in sp["scenes"].values() if x), sid
        assert set(sp["reward"]) <= FX_KEYS and sp["reward"], sid
        assert not sp.get("repeat"), "missoes repetiveis nao sao suportadas (%s)" % sid
    seen = set()
    for i, (cond, scenes) in enumerate(st.ENDINGS):
        scenes = [scenes] if isinstance(scenes, str) else scenes
        check_cond_format(cond, "ENDINGS[%d]" % i)
        assert 1 <= len(scenes) <= 3 and all(x in st.SCENES for x in scenes), i
        assert not (set(scenes) & seen), "cena repetida entre finais"
        seen |= set(scenes)
    if st.ENDINGS:
        assert st.ENDINGS[-1][0] is None, "o ultimo final e o padrao (cond None)"
        assert all(c is not None for c, _ in st.ENDINGS[:-1])


def main():
    names = [n for n in globals() if n.startswith("test_")]
    want = sys.argv[1:]
    if want:
        names = [n for n in names if n in want or n[5:] in want]
    for n in names:
        try:
            globals()[n]()
            PASS.append(n)
            print("OK   %s" % n)
        except Exception as e:
            import traceback
            FAIL.append(n)
            print("FAIL %s: %r" % (n, e))
            traceback.print_exc()
    print("\n%d testes passaram, %d falhas" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
