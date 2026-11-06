# -*- coding: utf-8 -*-
"""Trilhas sintetizadas (chiptune): melodia (pulso), baixo (triangulo) e bateria (ruido + seno).

Puro (stdlib): cada trilha e escrita como texto, 16 passos (semicolcheias) por compasso, e renderizada
compasso a compasso em array('h') mono a sfx.SR. A parte cara por amostra fica em operacoes de C
(repeticao/fatia de array) e em list comprehensions curtas, para caber no orcamento do WASM.

Notacao de uma voz: tokens separados por espaco, 1 por passo: "C5", "F#4", "Bb3" = nota; "-" = segura
a nota anterior; "." = pausa. Bateria: 1 caractere por passo: k bumbo, s caixa, h chimbal, c prato,
"." nada.

render_chunks(track) gera os pedacos (None = trabalho em andamento, para o chamador ceder o quadro;
array = pedaco pronto, na ordem). render(track) junta tudo (testes/medicao).
"""
import math
import random
from array import array

SR = 22050
NOTE_IDX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LEAD_AMP, BASS_AMP = 6500, 7500
KICK_AMP, SNARE_AMP, HAT_AMP, CRASH_AMP = 8000, 5000, 2200, 3500   # soma dos picos < 32767


def midi(tok):
    """'C5' -> 72, 'F#4' -> 66, 'Bb3' -> 58."""
    n = NOTE_IDX[tok[0]]
    rest = tok[1:]
    if rest[:1] == "#":
        n, rest = n + 1, rest[1:]
    elif rest[:1] == "b":
        n, rest = n - 1, rest[1:]
    return 12 * (int(rest) + 1) + n


def freq(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


# --------------------------------------------------------------- trilhas
# cada trilha: bpm, onda/duty do lead, compassos (lead, baixo, bateria)
_DR_MENU = "k.h.s.h.k.h.s.hh"
_DR_MENU_FILL = "k.h.s.h.k.k.s.ss"
_DR_MATCH = "k.hhs.hhk.kks.hh"
_DR_MATCH_FILL = "k.hhs.hhk.kkssss"


def _b8(root, up):
    """Baixo em colcheias alternando fundamental e oitava."""
    return " ".join([root, ".", up, "."] * 4)


TRACKS = {
    "menu": {
        "bpm": 128, "duty": 0.25, "loop": True,
        "bars": [
            ("E5 - G5 - C6 - - - G5 - E5 - G5 - - -", _b8("C3", "C4"), _DR_MENU),
            ("A5 - - - G5 - E5 - C5 - - - E5 - - -", _b8("A2", "A3"), _DR_MENU),
            ("F5 - A5 - C6 - A5 - G5 - F5 - E5 - D5 -", _b8("F2", "F3"), _DR_MENU),
            ("D5 - - - G4 - B4 - D5 - - - . . . .", _b8("G2", "G3"), _DR_MENU_FILL),
            ("E5 - G5 - C6 - - - D6 - C6 - B5 - G5 -", _b8("C3", "C4"), _DR_MENU),
            ("A5 - - - C6 - A5 - E5 - - - G5 - A5 -", _b8("A2", "A3"), _DR_MENU),
            ("F5 - A5 - G5 - F5 - E5 - D5 - E5 - F5 -", _b8("F2", "F3"), _DR_MENU),
            ("G5 - - - B4 - D5 - C5 - - - . . . .", _b8("G2", "G3"), _DR_MENU_FILL),
        ],
    },
    "match": {
        "bpm": 150, "duty": 0.5, "loop": True,
        "bars": [
            ("A4 . C5 . E5 . A5 . G5 . E5 . C5 . E5 .", _b8("A2", "A3"), _DR_MATCH),
            ("F5 . A5 . C6 - - . A5 . F5 . C5 . F5 .", _b8("F2", "F3"), _DR_MATCH),
            ("E5 . G5 . C6 . G5 . E5 . G5 . C6 . E6 .", _b8("C3", "C4"), _DR_MATCH),
            ("D6 - - . B5 . G5 . D5 . G5 . B5 . D6 .", _b8("G2", "G3"), _DR_MATCH_FILL),
            ("E6 - . . C6 . A5 . E5 . A5 . C6 . E6 .", _b8("A2", "A3"), _DR_MATCH),
            ("F6 - . . C6 . A5 . F5 . A5 . C6 . A5 .", _b8("F2", "F3"), _DR_MATCH),
            ("G5 . E5 . G5 . C6 . E6 - D6 - C6 - G5 -", _b8("C3", "C4"), _DR_MATCH),
            ("B5 - - - D6 - - - G5 - A5 - B5 - D6 -", _b8("G2", "G3"), _DR_MATCH_FILL),
        ],
    },
    "win": {
        "bpm": 140, "duty": 0.25, "loop": False,
        "bars": [
            ("C5 . E5 . G5 . C6 - - - G5 . C6 - - -", "C3 - - - . . . . G2 - - - . . . .", "ssssssssk...s.s."),
            ("E6 - - - - - - - - - - - . . . .", "C3 - - - - - - - . . . . . . . .", "c..............."),
        ],
    },
    "lose": {
        "bpm": 96, "duty": 0.5, "loop": False,
        "bars": [
            ("G4 - - . F#4 - - . F4 - - . E4 - - -", "C3 - - . B2 - - . Bb2 - - . A2 - - -", "k.......k......."),
            ("E4 - - - - - - - . . . . . . . .", "A2 - - - - - - - . . . . . . . .", "k..............."),
        ],
    },
}


# --------------------------------------------------------------- instrumentos
_TABLES = {}
_ENVS = {}


def _table(m, wave, duty):
    """Varios periodos da nota numa tabela de ~>=300 amostras (erro de afinacao < 0,2%)."""
    key = (m, wave, duty)
    t = _TABLES.get(key)
    if t is not None:
        return t
    f = freq(m)
    per = SR / f
    k = max(1, int(math.ceil(300.0 / per)))
    n = int(round(k * per))
    fr = k / n                                  # ciclos por amostra exatos dentro da tabela
    vals = []
    for i in range(n):
        ph = (i * fr) % 1.0
        if wave == "sq":
            w = 1.0 if ph < duty else -1.0
        else:                                   # tri
            w = 4.0 * ph - 1.0 if ph < 0.5 else 3.0 - 4.0 * ph
        vals.append(w)
    amp = LEAD_AMP if wave == "sq" else BASS_AMP
    t = array("h", [int(v * amp) for v in vals])
    _TABLES[key] = t
    return t


def _env(n, kind):
    """Envelope inteiro 0..256: ataque curto, decaimento ate o sustain e soltura no fim (sem clique)."""
    key = (n, kind)
    e = _ENVS.get(key)
    if e is not None:
        return e
    att = min(n // 4, int(0.004 * SR)) or 1
    rel = min(n // 3, int(0.03 * SR)) or 1
    sus = 0.55 if kind == "lead" else 0.8
    out = [0] * n
    for i in range(n):
        if i < att:
            g = i / att
        else:
            x = (i - att) / max(1, n - att)
            g = sus + (1.0 - sus) * (1.0 - x) ** 3
        if i >= n - rel:
            g *= (n - i) / rel
        out[i] = int(g * 256)
    _ENVS[key] = out
    return out


def _note(m, n, wave, duty, kind):
    t = _table(m, wave, duty)
    raw = (t * (n // len(t) + 1))[:n]
    env = _env(n, kind)
    return array("h", [(v * e) >> 8 for v, e in zip(raw, env)])


def _drums(rng):
    """Amostras da bateria (uma vez por trilha; rng privado)."""
    def hit(dur, fn):
        n = int(dur * SR)
        return array("h", [fn(i, i / n) for i in range(n)])
    rnd = rng.random
    ph = [0.0]

    def kick(i, x):
        f = 150.0 * (1.0 - x) + 45.0
        ph[0] += f / SR
        return int(math.sin(2 * math.pi * ph[0]) * (1.0 - x) ** 2 * KICK_AMP)

    kick_a = hit(0.11, kick)
    snare_a = hit(0.12, lambda i, x: int((rnd() * 2 - 1) * (1.0 - x) ** 2.5 * SNARE_AMP))
    hat_a = hit(0.035, lambda i, x: int((rnd() * 2 - 1) * (1.0 - x) ** 3 * HAT_AMP))
    crash_a = hit(0.9, lambda i, x: int((rnd() * 2 - 1) * (1.0 - x) ** 2 * CRASH_AMP))
    return {"k": kick_a, "s": snare_a, "h": hat_a, "c": crash_a}


def _voice(tokens, step, wave, duty, kind):
    """Uma voz de 1 compasso (16 passos) em array('h')."""
    n = step * len(tokens)
    buf = array("h", bytes(2 * n))
    i = 0
    toks = tokens
    while i < len(toks):
        tk = toks[i]
        if tk in (".", "-"):
            i += 1
            continue
        j = i + 1
        while j < len(toks) and toks[j] == "-":
            j += 1
        ln = (j - i) * step
        buf[i * step:i * step + ln] = _note(midi(tk), ln, wave, duty, kind)
        i = j
    return buf


def render_chunks(track):
    """Gera a trilha compasso a compasso. Yield None = pedaco de trabalho feito; array = compasso pronto."""
    spec = TRACKS[track]
    step = int(SR * 60.0 / spec["bpm"] / 4)
    drums = _drums(random.Random(1000 + len(track)))
    for lead, bass, dr in spec["bars"]:
        lt = lead.split()
        bt = bass.split()
        n = step * 16
        a = _voice(lt, step, "sq", spec["duty"], "lead")
        yield None
        b = _voice(bt, step, "tri", 0.5, "bass")
        yield None
        d = array("h", bytes(2 * n))
        for k, ch in enumerate(dr):
            h = drums.get(ch)
            if h is None:
                continue
            s = k * step
            ln = min(len(h), n - s)
            d[s:s + ln] = h[:ln]
        out = array("h", [x + y + z for x, y, z in zip(a, b, d)])
        yield out


def render(track):
    """Trilha inteira (array('h') mono a SR)."""
    out = array("h")
    for c in render_chunks(track):
        if c is not None:
            out.extend(c)
    return out


def duration(track):
    spec = TRACKS[track]
    return int(SR * 60.0 / spec["bpm"] / 4) * 16 * len(spec["bars"]) / SR
