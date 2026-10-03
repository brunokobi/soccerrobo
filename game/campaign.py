# -*- coding: utf-8 -*-
"""Campanha "A Garagem do Vo" (modo robos): logica PURA (sem pygame, sem random global).

Todo RNG e derivado da semente do save: random.Random("<seed>|<tag>|<contador>"), onde o contador
(`stats["ev"]`) so cresce. A campanha NUNCA grava em disco (nem garage.save()): o save e do passo 5.

Estado (segue a secao SAVE do plano):
    garage  Garage (elenco, pecas, sucata, flags de escolhas em garage.flags)
    ch      id do capitulo atual (story.CHAPTERS[i]["id"])
    node    indice do no atual em CHAPTERS[ch]["nodes"]
    done    lista de chaves jogadas: id de cena, "<cena>#<n>" (cenas repetiveis) e "reward:<id>"
    tour    None ou {"id","attempt","seed","stage","results":[[estagio,my,opp,pen_my,pen_opp],..],
                     "loses":int}  ("loses" = derrotas seguidas no estagio atual; adicional ao plano)
    pity    derrotas seguidas contra o chefe (0..PITY_MAX); -PITY_STEP de Forca do chefe por unidade
    hero    id do robo-heroi ("Ze Poeira")
    stats   {"ev","matches","sims","trained"} (contadores inteiros)
    seed    semente da campanha

Convencoes
----------
* O usuario e sempre o MANDANTE (lado 0) nas partidas da campanha. Pares sem pen: pen (0,0) = sem penaltis.
* Estagios: G1 G2 G3 [QF] SF F; "single" (treino do Prologo) so tem F e qualquer resultado conclui.
* Ordem do grupo FIXA (a do story.py): G1=group[0], G2=group[1], G3=group[2] (as cenas amarram o
  adversario ao estagio). A "semente do torneio" varia o jitter dos adversarios e os jogos simulados
  do resto do grupo. Os outros jogos do grupo sao re-derivados da semente (nada disso e persistido).
* Cenas: chave de `done` = id da cena, exceto as REPETIVEIS: `lose` (so apos perder a FINAL; a SF
  repete a partida sem cena) usa "<cena>#<derrotas seguidas>" e `elim` usa "<cena>#<tentativa>".
  Cada ocorrencia e exibida, mas fx/flags so valem na PRIMEIRA vez (se QUALQUER chave da cena ja esta
  em done). ("done", x) em cond vale se x ou algum "x#..." esta em done. Cenas before/after/win: uma vez.
* Consolacao (derrota na SF/final): as recompensas de derrota de match_rewards (sucata 15+5/gol e XP
  base sem bonus de vitoria), sem extras; repete-se so aquela partida.
"""
import copy
import json
import os
import random

import garage as G
import parts
import robot_league as RL
import robots
import store
import story

SIM_BIAS = 2                 # o Poisson e ~2 pontos mais facil que o motor
PITY_STEP = story.PITY_STEP
PITY_MAX = story.PITY_MAX
DONE = "DONE"
TRAIN_DELTA = 7              # adversario de treino: Forca de inicio do capitulo - 7
HERO_NAME, HERO_BASE, OTHER_BASE = "Zé Poeira", 38, 45
HERO_PAINT = (0, 200, 220)
START_SCRAP_CAMPAIGN = 100
# espelha robots_ui.TEAM_NAMES (o modulo da UI importa pygame)
TEAM_NAMES = ("Meu Time", "Os Cabos Soltos", "Pó de Ferro", "Aspira Mais", "Sucata FC",
              "Turbo Rodinhas", "Faísca Elétrica", "Zumbidos", "Engrenagem", "Rolo Compressor")
STAGE_NAMES = {"G1": "Grupo - rodada 1", "G2": "Grupo - rodada 2", "G3": "Grupo - rodada 3",
               "QF": "Quartas de final", "SF": "Semifinal", "F": "Final"}
PEN_SLOPE, PEN_BASE, PEN_CAP = 0.008, 0.72, 60

# --- persistencia (padrao de garage.py; chave PROPRIA, nunca a do modo livre) ---------------
SAVE_KEY = "soccerpy_campaign_v1"
SAVE_PATH = os.path.join(os.path.expanduser("~"), ".soccerpy_campaign.json")
VERSION = 1
MAX_SAVE_CHARS = 2_000_000
SAVE_NONE, SAVE_OK, SAVE_BAD = "none", "ok", "bad"
# Migracoes: chave ("v", n) = formato n -> n+1; ("sv", n) = roteiro n -> n+1. Cada uma recebe e devolve
# o dict inteiro do save. Sem migracao para um `sv` antigo => reparo por rewind (aviso). `v` antigo
# sem migracao => bad.
MIGRATIONS = {}
MAX_DONE, MAX_DONE_RAW, MAX_RESULTS = 300, 1000, 12
SEED_MAX, STAT_MAX = 2 ** 53, 10 ** 9
STAT_KEYS = ("ev", "matches", "sims", "trained")


# --- funcoes puras ------------------------------------------------------------------
def shootout(rating_h, rating_a, rng):
    """Penaltis: (pen_h, pen_a), nunca empata. 5 cobrancas cada + morte subita; chance de converter
    sobe com a diferenca de rating. Determinístico dado o rng."""
    d = (rating_h - rating_a) * PEN_SLOPE
    ph = G.clamp(PEN_BASE + d, 0.45, 0.92)
    pa = G.clamp(PEN_BASE - d, 0.45, 0.92)
    h = a = 0
    for _ in range(5):
        h += 1 if rng.random() < ph else 0
        a += 1 if rng.random() < pa else 0
    n = 0
    while h == a:
        n += 1
        if n > PEN_CAP:                       # seguranca (probabilisticamente inalcancavel)
            return (h + 1, a) if rating_h >= rating_a else (h, a + 1)
        sh = rng.random() < ph
        sa = rng.random() < pa
        h += 1 if sh else 0
        a += 1 if sa else 0
    return h, a


def sim_match(user_F, O, rng):
    """Simula (my, opp) por Poisson com o vies do motor: quick_sim(F - SIM_BIAS, O)."""
    return RL.quick_sim(user_F - SIM_BIAS, O, rng)


def stages_of(tr):
    if tr["format"] == "single":
        return ["F"]
    return ["G1", "G2", "G3"] + (["QF"] if tr.get("qf") else []) + ["SF", "F"]


def new_campaign(rng):
    """Campanha nova: Garage do modo livre ajustado (heroi base 38 + 4 robos base 45, 5 pecas Comuns,
    100 sucata). O RNG do argumento so e usado aqui (nome da equipe, nomes dos robos, loja, semente)."""
    g = G.new_game(rng, rng.choice(TEAM_NAMES))
    g.scrap = START_SCRAP_CAMPAIGN
    hero = next(r for r in g.robots if r["role"] == "MID")
    for r in g.robots:
        base = HERO_BASE if r is hero else OTHER_BASE
        r["base"] = robots.from_overall(base, r["role"], r["chassis"], seed=r["id"])
    hero["name"] = HERO_NAME
    hero["paint"] = list(HERO_PAINT)
    return Campaign(g, hero["id"], seed=rng.getrandbits(31))


class Campaign:
    def __init__(self, garage, hero_id, seed=1):
        self.garage = garage
        self.ch = story.CHAPTERS[0]["id"]
        self.node = 0
        self.done = []
        self.tour = None
        self.pity = 0
        self.hero = hero_id
        self.stats = {"ev": 0, "matches": 0, "sims": 0, "trained": 0}
        self.seed = int(seed)
        self._reports = {}                  # relatorios de recompensa (so memoria)
        self.warnings = []                  # avisos de reparo ao carregar (so memoria, para a UI)
        self.repaired = False

    # ------------------------------------------------------------------ serializacao
    def to_dict(self):
        return {"v": 1, "sv": story.STORY_VERSION, "garage": self.garage.to_dict(),
                "c": {"ch": self.ch, "node": self.node, "done": list(self.done),
                      "tour": copy.deepcopy(self.tour), "pity": self.pity, "hero": self.hero,
                      "stats": dict(self.stats), "seed": self.seed}}

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=True, separators=(",", ":"))

    @staticmethod
    def sanitize(data):
        """Dict (qualquer coisa vinda do JSON) -> dict limpo {"v","sv","garage","c"} ou None se
        irrecuperavel (reparos por rewind devolvem o dict ja reparado). Nunca levanta."""
        try:
            r = _sanitize(data)
            return None if r is None else r[0]
        except Exception as ex:  # noqa: BLE001  (inclui RecursionError)
            print("campaign sanitize error:", ex)
            return None

    @classmethod
    def from_dict(cls, data):
        """Campaign a partir de um dict (migra, sanitiza, repara). None se invalido. Nunca levanta.
        So le campos conhecidos (nunca setattr em loop sobre o JSON). `warnings`/`repaired` informam
        reparos."""
        try:
            r = _sanitize(data)
            if r is None:
                return None
            clean, warns = r
            g = G.Garage.from_dict(clean["garage"])
            if g is None:
                return None
            c = clean["c"]
            o = cls(g, c["hero"], c["seed"])
            o.ch, o.node, o.pity = c["ch"], c["node"], c["pity"]
            o.done = list(c["done"])
            o.tour = copy.deepcopy(c["tour"])
            o.stats = dict(c["stats"])
            o.warnings = list(warns)
            o.repaired = bool(warns)
            return o
        except Exception as ex:  # noqa: BLE001
            print("campaign from_dict error:", ex)
            return None

    def save(self):
        """Grava em SAVE_KEY. So grava um estado que passa no sanitize SEM reparo (senao o save
        gravado diferiria do estado em memoria; o save anterior e preservado). True se gravou.
        Nunca toca a chave do modo livre nem chama garage.save()."""
        try:
            r = _sanitize(self.to_dict())
            if r is None or r[1]:
                return False
            text = json.dumps(r[0], ensure_ascii=True, separators=(",", ":"))
            if len(text) > MAX_SAVE_CHARS:
                return False
            return bool(_store_set(text))
        except Exception as ex:  # noqa: BLE001
            print("campaign save error:", ex)
            return False

    @classmethod
    def load(cls):
        """Campaign salva ou None (ausente/invalida). Save invalido NUNCA e sobrescrito: o texto
        cru vai para `<SAVE_KEY>.bad`. Nunca faz save(). Veja load_status()."""
        c, status, raw = _load_core()
        if status == SAVE_BAD and raw is not None:
            _store_set_bad(raw)
        return c

    @staticmethod
    def load_status():
        """"none" | "ok" | "bad". Sem efeitos colaterais (nao grava nada)."""
        return _load_core()[1]

    @staticmethod
    def has_save():
        return _store_get() is not None

    # ------------------------------------------------------------------ helpers
    def _rng(self, tag):
        n = self.stats["ev"]
        self.stats["ev"] = n + 1
        return random.Random("%d|%s|%d" % (self.seed, tag, n))

    def chapter(self):
        return next(c for c in story.CHAPTERS if c["id"] == self.ch)

    def econ_tier(self):
        return self.chapter()["econ_tier"]

    def hero_robot(self):
        return self.garage.robot(self.hero)

    def is_done(self, sid):
        """True se `sid` ou alguma ocorrencia "sid#n" esta em done."""
        if sid in self.done:
            return True
        pre = sid + "#"
        return any(k.startswith(pre) for k in self.done)

    def check_cond(self, cond):
        if cond is None:
            return True
        kind, arg = cond
        if kind == "flag":
            return bool(self.garage.flags.get(arg))
        if kind == "noflag":
            return not self.garage.flags.get(arg)
        if kind == "done":
            return self.is_done(arg)
        return False

    def scene_lines(self, scene_id):
        """Itens da cena visiveis agora (falas cujo cond e falso saem; escolhas ficam)."""
        out = []
        for it in story.SCENES[scene_id]["lines"]:
            if isinstance(it, dict) or len(it) < 4 or self.check_cond(it[3]):
                out.append(it)
        return out

    # ------------------------------------------------------------------ cenas
    def _scene_key(self, scene_id):
        tr = self.tour
        if tr is not None:
            h = story.TOURNAMENTS[tr["id"]]["hooks"]
            if scene_id == h.get("elim"):
                return "%s#%d" % (scene_id, tr["attempt"] - 1)
            if scene_id == h.get("lose"):
                return "%s#%d" % (scene_id, tr["loses"])
        return scene_id

    def finish_scene(self, scene_id, choice_index=None):
        """Marca a cena como jogada e aplica o fx da escolha (so na primeira ocorrencia da cena).
        choice_index None = sem escolha (nenhum fx); fora da faixa levanta ValueError.
        Devolve True se registrou agora, False se esta ocorrencia ja estava em done."""
        if scene_id not in story.SCENES:
            raise KeyError(scene_id)
        key = self._scene_key(scene_id)
        if key in self.done:
            return False
        first = not self.is_done(scene_id)
        opt = None
        choice = next((it for it in self.scene_lines(scene_id) if isinstance(it, dict)), None)
        if choice_index is not None:
            if choice is None or not (0 <= choice_index < len(choice["opts"])):
                raise ValueError("escolha invalida")
            opt = choice["opts"][choice_index]
        self.done.append(key)
        if first and opt is not None:
            self.apply_fx(opt.get("fx") or {})
        return True

    def apply_fx(self, fx):
        g = self.garage
        if "flag" in fx and (fx["flag"] in g.flags or len(g.flags) < G.MAX_FLAGS):
            g.flags[fx["flag"]] = 1
        if fx.get("scrap"):
            g.scrap = G.clamp(g.scrap + int(fx["scrap"]), 0, G.SCRAP_MAX)
        if fx.get("xp_hero") and self.hero_robot() is not None:
            G.add_xp(self.hero_robot(), fx["xp_hero"])
        if fx.get("xp_team"):
            for r in g.robots:
                G.add_xp(r, fx["xp_team"])
        if fx.get("piece"):
            self._give_piece(fx["piece"])

    def _give_piece(self, spec):
        g = self.garage
        if len(g.inventory) >= G.MAX_INVENTORY:
            return None
        pc = g.new_piece(spec["model"], spec["rar"])
        g.inventory.append(pc)
        return pc

    # ------------------------------------------------------------------ caminhada dos nos
    def next_action(self):
        """Proxima acao da campanha (avanca nos concluidos e cria o torneio quando preciso):
        {"kind":"scene","id","key","scene"} | {"kind":"match",...} |
        {"kind":"chapter_end","chapter","report"} | {"kind":"end","draft"?}.
        O "match" traz: tournament, stage, stage_name, boss, knockout, training(False), opp (time),
        home/away (cfgs para Game.start_robot_match), user_F, O (ovr efetivo c/ pity), F_rec, pity."""
        for _ in range(64):
            nodes = self.chapter()["nodes"]
            if self.node >= len(nodes):
                return {"kind": "end", "draft": True}
            kind, arg = nodes[self.node]
            if kind == "scene":
                if self.is_done(arg):
                    self.node += 1
                    continue
                return self._scene_action(arg)
            if kind == "tournament":
                if self.tour is None or self.tour["id"] != arg:
                    self.start_tournament(arg)
                act = self._tournament_step()
                if act is None:
                    continue
                return act
            if kind == "chapter_end":
                rep = self.apply_chapter_rewards()
                return {"kind": "chapter_end", "chapter": arg, "report": rep,
                        "warnings": list(rep.get("warnings", []))}
            if kind == "end":
                if not self.is_done(arg):
                    return self._scene_action(arg)
                return {"kind": "end", "draft": False}
            raise ValueError("no desconhecido: %r" % (kind,))
        raise RuntimeError("next_action: laco de nos")

    def _scene_action(self, sid):
        return {"kind": "scene", "id": sid, "key": self._scene_key(sid), "scene": story.SCENES[sid]}

    def advance_chapter(self):
        """Do no chapter_end para o proximo capitulo. Devolve o id novo ou None (nao esta no
        chapter_end ou nao ha proximo)."""
        nodes = self.chapter()["nodes"]
        if self.node >= len(nodes) or nodes[self.node][0] != "chapter_end":
            return None
        self.apply_chapter_rewards()
        ids = [c["id"] for c in story.CHAPTERS]
        i = ids.index(self.ch)
        if i + 1 >= len(ids):
            return None
        self.ch, self.node, self.tour, self.pity = ids[i + 1], 0, None, 0
        return self.ch

    # ------------------------------------------------------------------ torneio
    def start_tournament(self, tid=None, attempt=0):
        if tid is None:
            nodes = self.chapter()["nodes"]
            kind, tid = nodes[self.node]
            if kind != "tournament":
                raise ValueError("no atual nao e torneio")
        seed = self._rng("tour").getrandbits(31)
        self.tour = {"id": tid, "attempt": attempt, "seed": seed, "stage": stages_of(story.TOURNAMENTS[tid])[0],
                     "results": [], "loses": 0}
        return self.tour

    def _stage_team(self, tr, stage):
        if stage[0] == "G":
            return tr["group"][int(stage[1]) - 1]
        return {"QF": tr.get("qf"), "SF": tr.get("sf"), "F": tr["final"]}[stage]

    def _is_boss(self, tr, stage):
        return tr["format"] == "cup" and stage == "F"

    def pity_delta(self):
        return -min(self.pity, PITY_MAX) * PITY_STEP

    def _opp_ovr(self, tr, stage):
        spec = story.TEAMS[self._stage_team(tr, stage)]
        d = self.pity_delta() if self._is_boss(tr, stage) else 0
        return spec["ovr"] + d

    def _opp_team(self, tr, stage, seed):
        tid = self._stage_team(tr, stage)
        spec = story.TEAMS[tid]
        si = stages_of(tr).index(stage)
        t = RL.opponent_team(spec["name"], spec["color"], self._opp_ovr(tr, stage),
                             seed * 10 + si, names=spec["names"], chassis=spec["chassis"],
                             jitter=not spec["perfect"])
        for e in t["squad"]:
            e["paint"] = tuple(spec["paint"])
        return t

    def _tournament_step(self):
        """Proxima acao do torneio atual; None se concluiu (no avancado)."""
        tour = self.tour
        tr = story.TOURNAMENTS[tour["id"]]
        hooks = tr["hooks"]
        stages = stages_of(tr)
        idx = len(stages) if tour["stage"] == DONE else stages.index(tour["stage"])
        if tour["attempt"] > 0 and idx == 0 and not tour["results"]:
            sid = hooks.get("elim")
            if sid and ("%s#%d" % (sid, tour["attempt"] - 1)) not in self.done:
                return self._scene_action(sid)
        for i in range(min(idx, len(stages))):
            sid = hooks["after"].get(stages[i])
            if sid and not self.is_done(sid):
                return self._scene_action(sid)
        if idx >= len(stages):
            sid = hooks.get("win")
            if sid and not self.is_done(sid):
                return self._scene_action(sid)
            self.node += 1
            self.tour = None
            return None
        stage = stages[idx]
        if stage == "F" and tour["loses"] > 0:
            sid = hooks.get("lose")
            if sid and ("%s#%d" % (sid, tour["loses"])) not in self.done:
                return self._scene_action(sid)
        sid = hooks["before"].get(stage)
        if sid and not self.is_done(sid):
            return self._scene_action(sid)
        return self._match_action(tr, stage)

    def _match_action(self, tr, stage):
        tour = self.tour
        ch = self.chapter()
        stages = stages_of(tr)
        opp = self._opp_team(tr, stage, tour["seed"])
        frac = stages.index(stage) / max(1, len(stages) - 1)
        return {"kind": "match", "tournament": tour["id"], "stage": stage,
                "stage_name": STAGE_NAMES[stage], "boss": self._is_boss(tr, stage),
                "knockout": stage[0] != "G", "training": False, "opp": opp,
                "home": self.garage.match_cfg(), "away": RL.match_cfg(opp),
                "user_F": self.garage.rating(), "O": opp["ovr"],
                "F_rec": ch["F_start"] + (ch["F_end"] - ch["F_start"]) * frac,
                "pity": self.pity, "attempt": tour["attempt"]}

    # ---- grupo -------------------------------------------------------------------------
    def group_league(self):
        """Dict liga-like {"teams":[user,g0,g1,g2],"results":[[rodada,h,a,hg,ag],..]} do grupo atual:
        resultados do usuario (do tour) + outros jogos simulados (re-derivados da semente)."""
        tour = self.tour
        tr = story.TOURNAMENTS[tour["id"]]
        gid = tr["group"]
        specs = [story.TEAMS[t] for t in gid]
        teams = [{"name": self.garage.team["name"], "color": list(self.garage.team["color"])}]
        teams += [{"name": s["name"], "color": list(s["color"])} for s in specs]
        results = []
        for r in tour["results"]:
            if r[0][0] != "G":
                continue
            i = int(r[0][1]) - 1
            results.append([i, 0, i + 1, r[1], r[2]])
            a, b = [j for j in (1, 2, 3) if j != i + 1]
            rng = random.Random("%d|grp|%d" % (tour["seed"], i))
            hg, ag = RL.quick_sim(specs[a - 1]["ovr"], specs[b - 1]["ovr"], rng)
            results.append([i, a, b, hg, ag])
        return {"teams": teams, "results": results}

    def group_table(self):
        return RL.table(self.group_league())

    def user_group_pos(self):
        return next(i for i, r in enumerate(self.group_table()) if r["idx"] == 0) + 1

    # ---- registrar partida ---------------------------------------------------------------
    def record_match(self, my, opp, pen=None, events=None, simulated=False):
        """Registra a partida do estagio atual (usuario = mandante). `events` = eventos do motor
        (so gols com team==0 e pid contam para o XP). Empate no mata-mata: pen (pm,po) ou sorteado por
        shootout(). Devolve {"result","my","opp","pen","stage","outcome","advanced","rewards",...};
        outcome: "next" | "elim" | "retry" | "done" | "champion"."""
        tour = self.tour
        if tour is None or tour["stage"] == DONE:
            raise RuntimeError("sem partida pendente")
        g = self.garage
        tr = story.TOURNAMENTS[tour["id"]]
        stages = stages_of(tr)
        stage = tour["stage"]
        si = stages.index(stage)
        single = tr["format"] == "single"
        ko = stage[0] != "G"
        my, opp = G.clamp(int(my), 0, 99), G.clamp(int(opp), 0, 99)
        O = self._opp_ovr(tr, stage)
        pids = [e["pid"] for e in (events or ()) if e.get("team") == 0 and not e.get("own")
                and e.get("pid") is not None]
        tier = self.econ_tier()
        rew = G.match_rewards(g, my, opp, pids, tier, self._rng("rw"))
        g.refresh_shop(tier, self._rng("shop"))
        self.stats["matches"] += 1
        if simulated:
            self.stats["sims"] += 1
        pm = po = 0
        if ko and not single and my == opp:
            if pen is None:
                pen = shootout(g.rating(), O, self._rng("pen"))
            pm, po = int(pen[0]), int(pen[1])
            if pm == po or pm < 0 or po < 0:
                raise ValueError("penaltis nao podem empatar")
        out = {"result": rew["result"], "my": my, "opp": opp, "pen": (pm, po) if (pm or po) else None,
               "stage": stage, "rewards": rew, "advanced": False, "outcome": "next",
               "tournament": tour["id"], "boss": self._is_boss(tr, stage)}
        win = my > opp or (my == opp and pm > po)
        if single:
            tour["results"].append([stage, my, opp, pm, po])
            tour["stage"] = DONE
            out.update(outcome="done", advanced=True)
            return out
        if not ko:                                         # grupo
            tour["results"].append([stage, my, opp, 0, 0])
            if stage == stages[2]:                         # G3: decide
                pos = self.user_group_pos()
                out["group_pos"] = pos
                if pos <= 2:
                    tour["stage"] = stages[si + 1]
                    out["advanced"] = True
                else:
                    self.start_tournament(tour["id"], attempt=tour["attempt"] + 1)
                    out["outcome"] = "elim"
            else:
                tour["stage"] = stages[si + 1]
                out["advanced"] = True
            return out
        if win:
            tour["results"].append([stage, my, opp, pm, po])
            tour["loses"] = 0
            out["advanced"] = True
            if stage == "F":
                tour["stage"] = DONE
                self.pity = 0
                out["outcome"] = "champion"
            else:
                tour["stage"] = stages[si + 1]
        else:
            tour["loses"] += 1
            out["outcome"] = "retry"
            if self._is_boss(tr, stage):
                self.pity = min(PITY_MAX, self.pity + 1)
        return out

    def simulate_current(self):
        """Simula a partida pendente (Poisson com SIM_BIAS) e registra. Devolve o dict de record_match."""
        act = self._peek_match()
        my, opp = sim_match(act["user_F"], act["O"], self._rng("sim"))
        return self.record_match(my, opp, simulated=True)

    def _peek_match(self):
        act = self.next_action()
        if act["kind"] != "match":
            raise RuntimeError("proxima acao nao e partida: %s" % act["kind"])
        return act

    # ------------------------------------------------------------------ treino
    def training_ovr(self):
        return max(30, int(round(self.chapter()["F_start"])) - TRAIN_DELTA)

    def training_econ_tier(self):
        return G.clamp(self.econ_tier() - 1, 0, len(G.TIER_MUL) - 1)

    def training_cfg(self):
        """Adversario de treino (Forca de inicio do capitulo - 7; recompensa com tier-1): nao avanca nada.
        {"home","away","opp","O","user_F","econ_tier","training":True}."""
        rng = self._rng("train")
        name = rng.choice(RL.TEAM_NAMES)
        color = rng.choice(RL.TEAM_COLORS)
        team = RL.opponent_team(name, color, self.training_ovr(), rng.randrange(1, 100000))
        return {"home": self.garage.match_cfg(), "away": RL.match_cfg(team), "opp": team,
                "O": team["ovr"], "user_F": self.garage.rating(), "econ_tier": self.training_econ_tier(),
                "training": True}

    def record_training(self, my, opp, events=None, simulated=False):
        """Recompensas de um treino (tier-1); nao mexe em torneio, pity nem nos."""
        g = self.garage
        my, opp = G.clamp(int(my), 0, 99), G.clamp(int(opp), 0, 99)
        pids = [e["pid"] for e in (events or ()) if e.get("team") == 0 and not e.get("own")
                and e.get("pid") is not None]
        tier = self.training_econ_tier()
        rew = G.match_rewards(g, my, opp, pids, tier, self._rng("rw"))
        g.refresh_shop(tier, self._rng("shop"))
        self.stats["trained"] += 1
        return {"result": rew["result"], "my": my, "opp": opp, "rewards": rew, "training": True}

    # ------------------------------------------------------------------ recompensas de capitulo
    def apply_chapter_rewards(self, cid=None):
        """Aplica UMA vez (chave "reward:<id>" em done) as REWARDS do capitulo. Devolve o relatorio
        {"applied", "scrap","piece","recruits":[nomes],"unlocked":[..],"xp_hero","xp_team",
        "equip","tier_done","warnings":[..]}; chamadas seguintes: o mesmo relatorio com applied=False
        (ou vazio se foi carregado de um save)."""
        ch = self.chapter() if cid is None else next(c for c in story.CHAPTERS if c["id"] == cid)
        rid = ch.get("reward")
        key = "reward:%s" % rid
        empty = {"applied": False, "scrap": 0, "piece": None, "recruits": [], "unlocked": [],
                 "xp_hero": 0, "xp_team": 0, "equip": None, "tier_done": self.garage.tier_done,
                 "warnings": []}
        if rid is None or key in self.done:
            rep = dict(self._reports.get(rid) or empty)
            rep["applied"] = False
            return rep
        rw = story.REWARDS[rid]
        g = self.garage
        self.done.append(key)
        rep = dict(empty, applied=True, recruits=[], unlocked=[], warnings=[])
        if rw.get("scrap"):
            g.scrap = G.clamp(g.scrap + rw["scrap"], 0, G.SCRAP_MAX)
            rep["scrap"] = rw["scrap"]
        if rw.get("piece"):
            pc = self._give_piece(rw["piece"])
            rep["piece"] = parts.part_name(pc) if pc else None
        for spec in rw.get("recruits", ()):
            warn = self._recruit(spec)
            rep["recruits"].append(spec["name"])
            if warn:
                rep["warnings"].append(warn)
        for c in rw.get("unlock", ()):
            if c in robots.CHASSIS and c not in g.unlocked:
                g.unlocked.append(c)
                rep["unlocked"].append(c)
        if rw.get("xp_hero") and self.hero_robot() is not None:
            G.add_xp(self.hero_robot(), rw["xp_hero"])
            rep["xp_hero"] = rw["xp_hero"]
        if rw.get("xp_team"):
            for r in g.robots:
                G.add_xp(r, rw["xp_team"])
            rep["xp_team"] = rw["xp_team"]
        if rw.get("equip_hero_piece") and self.hero_robot() is not None:
            pc = self._give_piece(rw["equip_hero_piece"])
            if pc is not None:
                g.equip(self.hero, pc["id"])
                rep["equip"] = parts.part_name(pc)
        if rw.get("title"):
            g.stats["titles"] += 1
        g.tier_done = max(g.tier_done, G.clamp(ch["tier_done_on_close"], -1, len(G.TIER_OVR) - 1))
        g.refresh_shop(g.tier(), self._rng("shop"))
        rep["tier_done"] = g.tier_done
        self._reports[rid] = rep
        return dict(rep)

    def _recruit(self, spec):
        """Cria o recruta (nivel/chassis/peca ja prontos). Elenco cheio: sai o reserva de MENOR nivel
        (nunca o heroi nem titular); devolve o aviso (str) ou None."""
        g = self.garage
        warn = None
        if len(g.robots) >= G.MAX_SQUAD:
            pb = g.pieces_by_id()
            reserves = [r for r in g.robots if r["id"] not in g.lineup and r["id"] != self.hero]
            if reserves:
                out = min(reserves, key=lambda r: (r["level"], robots.mean_attr(G.effective_attrs(r, pb)),
                                                   r["id"]))
                g.robots.remove(out)
                warn = "Elenco cheio: %s (nv %d) saiu para %s entrar." % (out["name"], out["level"], spec["name"])
            else:
                return "Elenco cheio sem reservas: %s nao entrou." % spec["name"]
        rb = g.make_robot(spec["name"], spec["role"], spec["chassis"], spec["base_ovr"],
                          spec.get("paint"))
        rb["level"] = G.clamp(int(spec.get("level", 1)), 1, G.MAX_LEVEL)
        g.robots.append(rb)
        if spec.get("piece"):
            pc = self._give_piece(spec["piece"])
            if pc is not None:
                g.equip(rb["id"], pc["id"])
        return warn


# --- persistencia: armazenamento (monkeypatchavel nos testes) -------------------------------
def _store_get():
    return store.read(SAVE_KEY, SAVE_PATH)


def _store_set(text):
    return store.write(SAVE_KEY, SAVE_PATH, text)


def _store_set_bad(text):
    return store.write(SAVE_KEY + ".bad", SAVE_PATH + ".bad", text)


def _load_core():
    """(Campaign|None, status, texto_cru|None)."""
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
        c = Campaign.from_dict(json.loads(raw))
    except Exception:  # noqa: BLE001  (JSON invalido, recursao, etc.)
        c = None
    if c is None:
        return None, SAVE_BAD, raw
    return c, SAVE_OK, raw


# --- persistencia: validacao ----------------------------------------------------------------
def _sint(v, lo, hi):
    """int exato (nao bool, sem coagir) em [lo, hi]; senao None."""
    if isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi:
        return v
    return None


def _migrate(data):
    """Aplica MIGRATIONS de formato (v). Devolve (dict, sv_ok) ou None. sv_ok=False => roteiro
    antigo sem migracao (reparo por rewind)."""
    if not isinstance(data, dict):
        return None
    v = _sint(data.get("v"), 1, VERSION)
    sv = _sint(data.get("sv"), 1, story.STORY_VERSION)
    if v is None or sv is None:
        return None                              # ausente/zero/negativo/futuro/tipo errado
    while v < VERSION:
        fn = MIGRATIONS.get(("v", v))
        if fn is None:
            return None
        data = fn(copy.deepcopy(data))
        if not isinstance(data, dict):
            return None
        v += 1
    sv_ok = True
    while sv < story.STORY_VERSION:
        fn = MIGRATIONS.get(("sv", sv))
        if fn is None:
            sv_ok = False
            break
        data = fn(copy.deepcopy(data))
        if not isinstance(data, dict):
            return None
        sv += 1
    return data, sv_ok


def _valid_chapters():
    return [c for c in story.CHAPTERS if not c.get("draft") and c["nodes"]]


def _repair_chapter(done):
    """Capitulo de reparo quando `ch` e invalido/draft: o primeiro jogavel cuja recompensa ainda nao
    esta em done; se todos ja foram fechados, o ultimo jogavel."""
    play = _valid_chapters()
    for c in play:
        if c.get("reward") is None or ("reward:%s" % c["reward"]) not in done:
            return c["id"]
    return play[-1]["id"]


def _done_keys(raw):
    """Lista de chaves validas (ordem preservada, sem duplicatas) ou None se `raw` nao e lista/enorme.
    Aceitas: id de cena, "<cena>#<n>" (n 0..99) e "reward:<id>" (id em story.REWARDS)."""
    if not isinstance(raw, list) or len(raw) > MAX_DONE_RAW:
        return None
    out, seen = [], set()
    for k in raw:
        if not isinstance(k, str) or len(k) > 80 or k in seen:
            continue
        ok = False
        if k in story.SCENES:
            ok = True
        elif k.startswith("reward:"):
            ok = k[7:] in story.REWARDS
        elif "#" in k:
            pre, _, n = k.partition("#")
            ok = (pre in story.SCENES and n.isascii() and n.isdigit() and len(n) <= 2
                  and (n == "0" or not n.startswith("0")))
        if ok:
            seen.add(k)
            out.append(k)
    if len(out) > MAX_DONE:                      # mantem recompensas/cenas unicas, depois as repeticoes mais novas
        fixed = [k for k in out if "#" not in k]
        rep = [k for k in out if "#" in k]
        keep = set(fixed[:MAX_DONE]) | set(rep[-max(0, MAX_DONE - len(fixed)):])
        out = [k for k in out if k in keep]
    return out


def _tour(t, ch_id, node_entry):
    """tour limpo ou None se inconsistente."""
    if not isinstance(t, dict):
        return None
    tid = t.get("id")
    tr = story.TOURNAMENTS.get(tid) if isinstance(tid, str) else None
    if tr is None or tr["chapter"] != ch_id or tuple(node_entry) != ("tournament", tid):
        return None
    stages = stages_of(tr)
    attempt, seed = _sint(t.get("attempt"), 0, 999), _sint(t.get("seed"), 0, 2 ** 31 - 1)
    loses, stage = _sint(t.get("loses"), 0, 99), t.get("stage")
    if None in (attempt, seed, loses) or not isinstance(stage, str) or stage not in stages + [DONE]:
        return None
    cur = len(stages) if stage == DONE else stages.index(stage)
    raw = t.get("results")
    if not isinstance(raw, list) or len(raw) > MAX_RESULTS:
        return None
    results, last = [], -1
    for r in raw:
        if not isinstance(r, (list, tuple)) or len(r) != 5 or not isinstance(r[0], str) or r[0] not in stages:
            return None
        vals = [_sint(x, 0, 99) for x in r[1:]]
        i = stages.index(r[0])
        if None in vals or i <= last or i >= cur:
            return None
        last = i
        results.append([r[0]] + vals)
    return {"id": tid, "attempt": attempt, "seed": seed, "stage": stage, "results": results,
            "loses": loses}


def _sanitize(data):
    """(clean, warnings) ou None. Pode levantar (os chamadores publicos capturam)."""
    mg = _migrate(data)
    if mg is None:
        return None
    data, sv_ok = mg
    gobj = G.Garage.from_dict(data.get("garage"))
    if gobj is None:
        return None
    c = data.get("c")
    if not isinstance(c, dict):
        return None
    done = _done_keys(c.get("done"))
    if done is None:
        return None
    warns = []
    rewind = not sv_ok
    if not sv_ok:
        warns.append("Roteiro atualizado: voltando ao inicio do capitulo.")
    ch = c.get("ch")
    chapter = next((x for x in story.CHAPTERS if x["id"] == ch), None) if isinstance(ch, str) else None
    if chapter is None or chapter.get("draft") or not chapter["nodes"]:
        ch = _repair_chapter(done)
        chapter = next(x for x in story.CHAPTERS if x["id"] == ch)
        rewind = True
        warns.append("Capitulo salvo invalido: voltando ao inicio do capitulo %s." % ch)
        node, tour, pity = 0, None, 0
    else:
        node = _sint(c.get("node"), 0, len(chapter["nodes"]) - 1)
        pity = _sint(c.get("pity"), 0, story.PITY_MAX)
        tour = None
        if node is not None and c.get("tour") is not None:
            tour = _tour(c.get("tour"), ch, chapter["nodes"][node])
            if tour is None:
                node = None
        if node is None or pity is None:
            rewind = True
            warns.append("Campanha inconsistente: voltando ao inicio do capitulo.")
    if rewind:
        node, tour, pity = 0, None, 0
    rids = [r["id"] for r in gobj.robots]
    hero = c.get("hero")
    if not (isinstance(hero, int) and not isinstance(hero, bool) and hero in rids):
        hero = gobj.lineup[0] if gobj.lineup else rids[0]
        warns.append("Heroi nao encontrado: usando o primeiro titular.")
    seed = _sint(c.get("seed"), 0, SEED_MAX)
    if seed is None:
        seed = 1
        warns.append("Semente invalida: usando uma semente padrao.")
    sraw = c.get("stats")
    sraw = sraw if isinstance(sraw, dict) else {}
    stats = {}
    for k in STAT_KEYS:
        v = _sint(sraw.get(k), 0, STAT_MAX)
        if v is None:
            if k in sraw or k == "ev":
                warns.append("Contador %s invalido: zerado." % k)
            v = 0
        stats[k] = v
    clean = {"v": VERSION, "sv": story.STORY_VERSION, "garage": gobj.to_dict(),
             "c": {"ch": ch, "node": node, "done": done, "tour": tour, "pity": pity, "hero": hero,
                   "stats": stats, "seed": seed}}
    return clean, warns
