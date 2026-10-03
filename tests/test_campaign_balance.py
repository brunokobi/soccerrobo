# -*- coding: utf-8 -*-
"""Balanco da campanha "A Garagem do Vo" por SIMULACAO DE CAMPANHA (sem pygame, sem motor, sem disco).

Rodar da raiz: .venv/bin/python tests/test_campaign_balance.py [teste ...]   (N=300 por politica)
Usa Campaign.simulate_current (Poisson com o vies dependente do ovr, campaign.sim_bias(O), calibrado contra
o motor real por tests/calib_campaign.py), seeds fixas e a API pura do garage. Cobre todo capitulo NAO
draft de story.CHAPTERS (P e 1-5). "Aproveitamento" = (V + E/2) / jogos pelo placar dos 90 min (penaltis
nao contam). "regular" = jogos do grupo + quartas; "SF" = semifinal; "chefe" = final (inclui as
retentativas com pity, por isso fica ~2-4 pontos acima da primeira tentativa).

Politicas
---------
GULOSA   apos cada partida (e ao abrir cada capitulo) gasta a sucata na peca/upgrade de melhor
         custo-beneficio (ganho de Forca por sucata), equipa pecas livres, auto_lineup; escolhas de
         cena sorteadas.
PASSIVA  nunca gasta sucata nem mexe no elenco: so XP (+ recrutas que ficam no banco).
GRINDER  como a gulosa, mas faz GRIND_N treinos (Poisson, adversario de treino) ao abrir cada capitulo.

Alvos numericos sao SOFT (imprimem [ALVO OK] / [ALVO NAO ATINGIDO]); asserts duros so de seguranca:
termina, sem excecao, sem laco infinito, pity funciona (passiva conclui; alvo soft <=12 tentativas por
chefe, limite duro PASSIVE_MAX_TRIES),
Forca cresce entre capitulos, aproveitamento do chefe nem >90% nem <15%.
Variavel de ambiente CAMPAIGN_BAL_N sobrescreve N (padrao 300).
"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import campaign as cm  # noqa: E402
import career  # noqa: E402
import garage as gm  # noqa: E402
import robots  # noqa: E402
import store  # noqa: E402
import story  # noqa: E402

PASS, FAIL = [], []
N = int(os.environ.get("CAMPAIGN_BAL_N", "300"))
GRIND_N = 15                 # treinos por capitulo da politica GRINDER
MAX_MATCHES = 400            # guarda anti laco infinito (partidas da campanha)
MAX_STEPS = 4000
PASSIVE_MAX_TRIES = 25       # limite duro de tentativas por chefe na passiva (medido: 19 com as seeds fixas)


def _boom(*a, **k):
    raise AssertionError("gravacao proibida na simulacao de campanha")


for _m, _n in ((gm, "_store_set"), (gm, "_store_set_bad"), (cm, "_store_set"), (cm, "_store_set_bad"),
               (career, "_store_set"), (store, "write")):
    if hasattr(_m, _n):
        setattr(_m, _n, _boom)


def playable():
    return [c for c in story.CHAPTERS if not c.get("draft") and c["nodes"]]


# ---------------------------------------------------------------- politica de gasto (API pura do garage)
def _mean(r, pb):
    return robots.mean_attr(gm.effective_attrs(r, pb))


def _best_spend(g):
    """Melhor acao de gasto: (ratio, gain, kind, args) ou None. gain = ganho de Forca do time."""
    pb = g.pieces_by_id()
    lineup = g.lineup_robots()
    n = max(1, len(lineup))
    base = {r["id"]: _mean(r, pb) for r in lineup}
    free = g.free_pieces()
    best = None

    def consider(gain, cost, kind, args):
        nonlocal best
        if gain <= 1e-9:
            return
        ratio = gain / cost if cost > 0 else 1e9 + gain
        if best is None or ratio > best[0]:
            best = (ratio, gain, kind, args)

    for r in lineup:
        for pc in free:                                     # pecas livres (gratis)
            slot = gm.parts.part_slot(pc)
            r2 = dict(r, slots=dict(r["slots"], **{slot: pc["id"]}))
            consider((_mean(r2, pb) - base[r["id"]]) * 100.0 / n, 0, "equip", (r["id"], pc["id"]))
        for pc in g.shop["stock"]:                          # loja
            price = gm.parts.buy_price(pc)
            if price > g.scrap or len(g.inventory) >= gm.MAX_INVENTORY:
                continue
            slot = gm.parts.part_slot(pc)
            pb2 = dict(pb)
            pb2[pc["id"]] = pc
            r2 = dict(r, slots=dict(r["slots"], **{slot: pc["id"]}))
            consider((_mean(r2, pb2) - base[r["id"]]) * 100.0 / n, price, "buy", (r["id"], pc["id"]))
        for slot, pid in r["slots"].items():                # upgrades das pecas equipadas
            pc = pb.get(pid)
            if pc is None:
                continue
            cost = gm.parts.upgrade_cost(pc["rar"], pc["lvl"])
            if cost is None or cost > g.scrap:
                continue
            pc["lvl"] += 1
            try:
                after = _mean(r, pb)
            finally:
                pc["lvl"] -= 1
            consider((after - base[r["id"]]) * 100.0 / n, cost, "up", (pid,))
    return best


def greedy_spend(g):
    for _ in range(80):
        b = _best_spend(g)
        if b is None:
            break
        _, _, kind, a = b
        if kind == "equip":
            ok, _m = g.equip(a[0], a[1])
        elif kind == "buy":
            ok, _m = g.buy_part(a[1])
            if ok:
                ok, _m = g.equip(a[0], a[1])
        else:
            ok, _m = g.upgrade(a[0])
        assert ok, "gasto invalido: %s %s" % (kind, _m)
    g.auto_lineup()


# ---------------------------------------------------------------- simulacao
def run_campaign(policy, seed):
    """Joga a campanha (capitulos jogaveis) ate o ultimo capitulo nao-draft. Devolve o registro."""
    c = cm.new_campaign(random.Random(seed))
    prng = random.Random(seed * 7919 + 13)
    chapters = playable()
    last = chapters[-1]["id"]
    rec = {"ch": {}, "matches": 0, "boss_tries": {}, "done": False, "c": c}

    def ch_rec(cid):
        return rec["ch"].setdefault(cid, {"reg": [0, 0, 0], "boss": [0, 0, 0], "sf": [0, 0, 0], "clean": True,
                                          "F0": None, "F0_raw": None, "attempts": 0})

    def open_chapter():
        cr = ch_rec(c.ch)
        cr["F0_raw"] = c.garage.rating()
        if policy == "grinder":
            for _ in range(GRIND_N):
                tc = c.training_cfg()
                my, opp = cm.sim_match(tc["user_F"], tc["O"], prng)
                c.record_training(my, opp, simulated=True)
                greedy_spend(c.garage)
        if policy in ("greedy", "grinder"):
            greedy_spend(c.garage)
        cr["F0"] = c.garage.rating()

    open_chapter()
    for _ in range(MAX_STEPS):
        a = c.next_action()
        k = a["kind"]
        if k == "scene":
            ch = next((i for i in c.scene_lines(a["id"]) if isinstance(i, dict)), None)
            c.finish_scene(a["id"], prng.randrange(len(ch["opts"])) if ch else None)
        elif k == "match":
            cr = ch_rec(c.ch)
            boss = a["boss"]
            out = c.simulate_current()
            rec["matches"] += 1
            assert rec["matches"] <= MAX_MATCHES, "laco infinito de partidas"
            slot = cr["boss" if boss else ("sf" if a["stage"] == "SF" else "reg")]
            slot["wdl".index(out["result"])] += 1
            if boss:
                rec["boss_tries"][c.ch] = rec["boss_tries"].get(c.ch, 0) + 1
            if out["outcome"] in ("elim", "retry"):
                cr["clean"] = False
            if policy in ("greedy", "grinder"):
                greedy_spend(c.garage)
        elif k == "chapter_end":
            if c.ch == last:
                rec["done"] = True
                break
            nxt = c.advance_chapter()
            assert nxt is not None
            open_chapter()
        elif k == "end":
            rec["done"] = not a.get("draft") or c.ch == last
            break
        else:
            raise AssertionError(k)
    else:
        raise AssertionError("laco infinito de passos")
    return rec


_CACHE = {}


def campaigns(policy):
    if policy not in _CACHE:
        base = {"greedy": 1000, "passive": 5000, "grinder": 9000}[policy]
        _CACHE[policy] = [run_campaign(policy, base + i) for i in range(N)]
    return _CACHE[policy]


def pct(w):
    n = sum(w)
    return 100.0 * (w[0] + w[1] / 2.0) / n if n else None


def agg(recs, cid, key):
    w = [0, 0, 0]
    for r in recs:
        for i in range(3):
            w[i] += r["ch"].get(cid, {}).get(key, [0, 0, 0])[i]
    return w


def soft(name, value, lo, hi):
    ok = value is not None and lo <= value <= hi
    print("  %-46s %7s  (alvo %g-%g)  %s" % (name, "-" if value is None else "%.1f" % value, lo, hi,
                                            "[ALVO OK]" if ok else "[ALVO NAO ATINGIDO]"), flush=True)
    return ok


def table(policy):
    recs = campaigns(policy)
    print("\n== politica %s (%d campanhas) ==" % (policy.upper(), len(recs)))
    print("  %-4s %-9s %-9s %-9s %-10s %-9s %-9s %-9s" % ("cap", "regular%", "SF%", "chefe%", "P(1a vez)%", "F inicio", "F tabela", "F cru"))
    rows = {}
    for ch in playable():
        cid = ch["id"]
        reg, bos, sfp = pct(agg(recs, cid, "reg")), pct(agg(recs, cid, "boss")), pct(agg(recs, cid, "sf"))
        has_boss = any(sum(r["ch"][cid]["boss"]) for r in recs if cid in r["ch"])
        pc = 100.0 * sum(1 for r in recs if r["ch"].get(cid, {}).get("clean")) / len(recs)
        f0 = sum(r["ch"][cid]["F0"] for r in recs) / len(recs)
        fr = sum(r["ch"][cid]["F0_raw"] for r in recs) / len(recs)
        rows[cid] = {"reg": reg, "boss": bos, "sf": sfp, "pc": pc if has_boss else None, "F0": f0, "has_boss": has_boss}
        print("  %-4s %-9s %-9s %-9s %-10s %-9.1f %-9.1f %-9.1f" % (
            cid, "-" if reg is None else "%.1f" % reg, "-" if sfp is None else "%.1f" % sfp,
            "-" if bos is None else "%.1f" % bos,
            "-" if not has_boss else "%.1f" % pc, f0, ch["F_start"], fr))
    tot = sorted(r["matches"] for r in recs)
    print("  partidas/campanha: media %.1f  p95 %d  max %d" % (sum(tot) / len(tot), tot[int(0.95 * (len(tot) - 1))], tot[-1]))
    return rows


# ---------------------------------------------------------------- testes
def test_greedy_campaign():
    recs = campaigns("greedy")
    assert all(r["done"] for r in recs), "campanha gulosa nao terminou"
    rows = table("greedy")
    chs = playable()
    print("  -- alvos soft (gulosa) --")
    for ch in chs:
        cid, r = ch["id"], rows[ch["id"]]
        if r["has_boss"]:                                   # o Prologo so tem o treino
            soft("cap %s: aproveitamento regular (grupo/QF)" % cid, r["reg"], 58, 68)
        if r["sf"] is not None:
            soft("cap %s: aproveitamento da semifinal" % cid, r["sf"], 52, 62)
        if r["has_boss"]:
            soft("cap %s: aproveitamento do chefe" % cid, r["boss"], 44, 56)
            soft("cap %s: P(completar de primeira)" % cid, r["pc"], 20, 60)
        soft("cap %s: Forca inicio vs tabela (+-3)" % cid, r["F0"] - ch["F_start"], -3, 3)
    tot = sorted(r["matches"] for r in recs)
    soft("partidas por campanha (p95)", float(tot[int(0.95 * (len(tot) - 1))]), 0, 60)
    # duros
    for ch in chs:
        r = rows[ch["id"]]
        if r["has_boss"]:
            assert 15 <= r["boss"] <= 90, "chefe do cap %s fora de 15-90%%: %.1f" % (ch["id"], r["boss"])
    f0 = [rows[c["id"]]["F0"] for c in chs]
    assert all(b > a for a, b in zip(f0, f0[1:])), "Forca nao cresce entre capitulos: %s" % f0
    assert max(r["matches"] for r in recs) <= 150


def test_passive_pity_terminates():
    recs = campaigns("passive")
    assert all(r["done"] for r in recs), "campanha passiva nao concluiu"
    rows = table("passive")
    worst = max((t for r in recs for t in r["boss_tries"].values()), default=0)
    print("  max tentativas por chefe: %d (limite 12)" % worst)
    soft("max tentativas por chefe", float(worst), 0, 12)
    # duro: so garante terminacao (pity + sorte). O alvo de <=12 e soft: a passiva (so XP, sem gastar
    # sucata) fica ~8-10 pontos de Forca abaixo da gulosa nos Caps. 4-5 (passo 16: nao ha como baixar
    # isso sem trivializar a gulosa).
    assert worst <= PASSIVE_MAX_TRIES, "chefe exigiu %d tentativas (pity nao resolveu)" % worst
    assert max(r["matches"] for r in recs) <= 150
    for r in recs:                                          # a passiva nunca gastou sucata
        assert r["c"].garage.stats["played"] == r["matches"]


def test_grinder_campaign():
    recs = campaigns("grinder")
    assert all(r["done"] for r in recs)
    rows = table("grinder")
    print("  -- alvos soft (grinder, %d treinos/capitulo) --" % GRIND_N)
    for ch in playable():
        cid, r = ch["id"], rows[ch["id"]]
        soft("cap %s: aproveitamento regular (>=75)" % cid, r["reg"], 75, 100)
        if r["has_boss"]:
            ok = r["pc"] < 100.0
            print("  cap %s: P(completar de primeira) %.1f%%  %s" % (
                cid, r["pc"], "[ALVO OK] (<100)" if ok else "[ALVO NAO ATINGIDO] (=100)"))
    assert max(r["matches"] for r in recs) <= 150


def test_policies_ordering():
    """Sanidade: Forca no inicio dos capitulos (apos o capitulo 1): grinder >= gulosa >= passiva."""
    ch = playable()[-1]["id"]
    f = {p: sum(r["ch"][ch]["F0"] for r in campaigns(p)) / N for p in ("passive", "greedy", "grinder")}
    print("  F inicio cap %s: passiva %.1f | gulosa %.1f | grinder %.1f" % (ch, f["passive"], f["greedy"], f["grinder"]))
    assert f["grinder"] >= f["greedy"] - 0.5 and f["greedy"] > f["passive"]


def test_determinism():
    a, b = run_campaign("greedy", 4242), run_campaign("greedy", 4242)
    assert a["matches"] == b["matches"] and a["c"].to_dict() == b["c"].to_dict()


def main():
    names = sys.argv[1:] or [n for n in globals() if n.startswith("test_")]
    for n in names:
        try:
            globals()[n]()
            PASS.append(n)
            print("OK   %s" % n)
        except Exception as e:  # noqa: BLE001
            import traceback
            FAIL.append(n)
            print("FAIL %s: %r" % (n, e))
            traceback.print_exc()
    print("\n%d testes passaram, %d falhas" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
