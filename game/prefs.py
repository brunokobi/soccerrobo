# -*- coding: utf-8 -*-
"""Preferencias do jogador (puro: sem pygame).

Chave pequena `soccerpy_prefs_v1`: localStorage no navegador, ~/.soccerpy_prefs.json no
desktop (via store.py). Formato: JSON {"v": 1, <campo>: <valor>, ...}.

Sanitize por lista de campos conhecidos (FIELDS): campo desconhecido e descartado, valor
fora da lista vira o padrao. Ausente, ilegivel ou corrompido -> padroes; nunca levanta
excecao. Preferencia corrompida nao e copiada para ".bad" (nao e progresso): so e
sobrescrita quando o jogador muda alguma opcao (set/save).

Uso: prefs.get("crowd") -> "ALTA"; prefs.set("crowd", "OFF") -> True se gravou.
Som (Fase 6): "sfx_vol"/"music_vol" em "0".."3" (padrao "2" = medio) e "mute" "0"/"1" (padrao "0").

Campos OPCIONAIS (padrao None em FIELDS): ausentes = "o jogador nunca escolheu". Nao aparecem em
load()/no JSON gravado ate o primeiro set(); unset(campo) volta ao automatico. Hoje: a ultima escolha do
amistoso ("fr_t0"/"fr_t1" = ids de friendly.TEAMS, "fr_f0"/"fr_f1" = ids de friendly.FORMATIONS; gravados
juntos por update() quando a partida comeca). O antigo "camera" saiu (toda partida comeca na camera ESTADIO;
ver soccer.Game.camera_mode) e, se ainda estiver num JSON antigo, o sanitize o descarta.
"""
import json
import os

import friendly
import store

PREFS_KEY = "soccerpy_prefs_v1"
PREFS_PATH = os.path.join(os.path.expanduser("~"), ".soccerpy_prefs.json")
VERSION = 1
MAX_CHARS = 10_000                          # prefs sao minusculas; maior que isso = lixo

CROWD_LEVELS = ("ALTA", "MEDIA", "OFF")     # torcida: completa / sem ondas / desligada
VOLUME_LEVELS = ("0", "1", "2", "3")        # som: desligado / baixo / medio / alto (ver sfx.LEVEL_GAIN)
MUTE_VALUES = ("0", "1")                    # mudo geral (tecla M)

# campo -> (valores aceitos, padrao). Campos futuros entram aqui (o sanitize ja os trata).
FIELDS = {
    "crowd": (CROWD_LEVELS, "ALTA"),
    "sfx_vol": (VOLUME_LEVELS, "2"),        # volume dos efeitos (tecla S)
    "music_vol": (VOLUME_LEVELS, "2"),      # volume da musica (tecla N)
    "mute": (MUTE_VALUES, "0"),             # mudo geral (tecla M)
    # amistoso: ultima escolha de times e formacoes (opcionais: ausentes = padrao do jogo)
    "fr_t0": (friendly.TEAM_IDS, None),
    "fr_t1": (friendly.TEAM_IDS, None),
    "fr_f0": (friendly.FORMATION_ORDER, None),
    "fr_f1": (friendly.FORMATION_ORDER, None),
}

_cur = None                                 # cache em memoria (None = ainda nao carregado)


def defaults():
    """Padroes dos campos obrigatorios (os opcionais, padrao None, ficam de fora ate serem escolhidos)."""
    return {k: d for k, (_, d) in FIELDS.items() if d is not None}


def sanitize(d):
    """Dict so com os campos conhecidos; valor invalido (ou d que nao e dict) -> padrao."""
    out = defaults()
    if not isinstance(d, dict):
        return out
    for k, (ok, _) in FIELDS.items():
        v = d.get(k)
        if isinstance(v, str) and v in ok:
            out[k] = v
    return out


# --- armazenamento (monkeypatchavel nos testes) ----------------------------------------------
def _store_get():
    return store.read(PREFS_KEY, PREFS_PATH)


def _store_set(text):
    return store.write(PREFS_KEY, PREFS_PATH, text)


def _parse(raw):
    if raw is None or raw is store.ERROR or isinstance(raw, store.InvalidText):
        return defaults()
    if not isinstance(raw, str) or len(raw) > MAX_CHARS:
        return defaults()
    try:
        return sanitize(json.loads(raw))
    except Exception:  # noqa: BLE001  (JSON invalido, recursao, etc.)
        return defaults()


def load():
    """Rele o store e devolve uma copia das preferencias (sempre completas e validas)."""
    global _cur
    try:
        raw = _store_get()
    except Exception:  # noqa: BLE001
        raw = store.ERROR
    _cur = _parse(raw)
    return dict(_cur)


def _prefs():
    if _cur is None:
        load()
    return _cur


def save():
    """Grava as preferencias atuais; True se deu certo (nunca levanta excecao)."""
    d = {"v": VERSION}
    d.update(_prefs())
    try:
        return bool(_store_set(json.dumps(d, sort_keys=True)))
    except Exception:  # noqa: BLE001
        return False


def get(name):
    """Valor atual do campo (carrega na primeira chamada). Campo desconhecido -> None."""
    return _prefs().get(name)


def set(name, value):  # noqa: A001  (API do modulo: prefs.set)
    """Muda um campo e grava. Campo desconhecido ou valor invalido: nada muda, devolve False."""
    spec = FIELDS.get(name)
    if spec is None or not isinstance(value, str) or value not in spec[0]:
        return False
    _prefs()[name] = value
    return save()


def update(values):
    """Muda varios campos e grava UMA vez. Algum campo/valor invalido: nada muda, devolve False."""
    if not isinstance(values, dict) or not values:
        return False
    for name, value in values.items():
        spec = FIELDS.get(name)
        if spec is None or not isinstance(value, str) or value not in spec[0]:
            return False
    _prefs().update(values)
    return save()


def unset(name):
    """Esquece a escolha de um campo OPCIONAL (volta ao automatico) e grava. False se nao e opcional."""
    spec = FIELDS.get(name)
    if spec is None or spec[1] is not None:
        return False
    _prefs().pop(name, None)
    return save()


def reset_cache():
    """Esquece o cache (o proximo get() rele o store). Usado nos testes."""
    global _cur
    _cur = None
