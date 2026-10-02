# -*- coding: utf-8 -*-
"""Armazenamento chave/valor de texto (puro: sem pygame).

No navegador (emscripten) usa localStorage; no desktop, um arquivo em ~.
Nunca levanta excecao: read() devolve None e write() devolve False em erro.
"""
import os
import sys


def read(key, path):
    """Texto salvo (str) ou None se ausente/erro."""
    try:
        if sys.platform == "emscripten":
            import platform
            v = platform.window.localStorage.getItem(key)
            return None if v is None or str(v) == "null" else str(v)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
    except Exception as ex:  # noqa: BLE001
        print("store read error:", ex)
    return None


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
