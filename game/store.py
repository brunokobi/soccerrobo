# -*- coding: utf-8 -*-
"""Armazenamento chave/valor de texto (puro: sem pygame).

No navegador (emscripten) usa localStorage; no desktop, um arquivo em ~.
Nunca levanta excecao: read() devolve ERROR (ausente = None) e write() devolve False em erro.
"""
import os
import sys


class _Error:
    """Sentinela: a chave existe/talvez exista, mas a leitura falhou."""
    def __repr__(self):
        return "store.ERROR"


ERROR = _Error()


class InvalidText(str):
    """Texto lido de bytes que nao eram UTF-8 valido (decodificado com U+FFFD).
    O chamador deve trata-lo como save invalido, mesmo que o resultado pareca JSON."""


def read(key, path):
    """Texto salvo (str), None se ausente ou ERROR se a leitura falhou.
    Bytes invalidos em UTF-8 -> InvalidText (str com U+FFFD)."""
    try:
        if sys.platform == "emscripten":
            import platform
            v = platform.window.localStorage.getItem(key)
            return None if v is None or str(v) == "null" else str(v)
        if os.path.exists(path):
            with open(path, "rb") as f:
                data = f.read()
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return InvalidText(data.decode("utf-8", errors="replace"))
        return None
    except Exception as ex:  # noqa: BLE001
        print("store read error:", ex)
        return ERROR


def write(key, path, text):
    """Grava `text`; True se deu certo. No desktop grava em arquivo temporario e troca."""
    try:
        if sys.platform == "emscripten":
            import platform
            platform.window.localStorage.setItem(key, text)
        else:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)
        return True
    except Exception as ex:  # noqa: BLE001
        print("store write error:", ex)
        return False
