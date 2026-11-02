"""Testes das preferencias do jogador (game/prefs.py). Sem pygame.

Rodar da raiz: .venv/bin/python tests/test_prefs.py [teste ...]
Store em memoria (prefs._store_*); store.read/store.write reais falham se chamados fora do
teste de arquivo, que usa tempfile.mkdtemp (removido ao final). Nunca grava em ~.
"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))

import prefs  # noqa: E402
import store  # noqa: E402

PASS, FAIL = [], []
FORBIDDEN = []
ORIG = {"get": prefs._store_get, "set": prefs._store_set, "path": prefs.PREFS_PATH,
        "read": store.read, "write": store.write}
MEM = {}


def _boom(*a, **k):
    FORBIDDEN.append(a)
    raise AssertionError("acesso proibido ao store real")


store.read = _boom
store.write = _boom


def _mem_get():
    return MEM.get("raw")


def _mem_set(text):
    MEM["raw"] = text
    MEM["writes"] = MEM.get("writes", 0) + 1
    return True


def fresh(raw=None):
    """Store em memoria com `raw` e cache zerado."""
    MEM.clear()
    if raw is not None:
        MEM["raw"] = raw
    prefs._store_get = _mem_get
    prefs._store_set = _mem_set
    prefs.reset_cache()


def test_defaults_when_absent():
    fresh()
    assert prefs.load() == {"crowd": "ALTA"}
    assert prefs.get("crowd") == "ALTA"
    assert "writes" not in MEM                  # ler nao grava


def test_round_trip():
    fresh()
    for v in prefs.CROWD_LEVELS:
        assert prefs.set("crowd", v) is True
        assert json.loads(MEM["raw"]) == {"v": 1, "crowd": v}
        prefs.reset_cache()
        assert prefs.get("crowd") == v
        assert prefs.load() == {"crowd": v}


def test_set_invalid_value_or_field_is_ignored():
    fresh()
    prefs.set("crowd", "MEDIA")
    n = MEM["writes"]
    for name, val in (("crowd", "media"), ("crowd", "MÉDIA"), ("crowd", None), ("crowd", 2),
                      ("crowd", ["OFF"]), ("volume", "ALTA"), (None, "OFF")):
        assert prefs.set(name, val) is False
    assert prefs.get("crowd") == "MEDIA" and MEM["writes"] == n


def test_invalid_stored_value_falls_back():
    for d in ({"crowd": "ULTRA"}, {"crowd": 1}, {"crowd": None}, {"crowd": ["ALTA"]},
              {"crowd": "alta"}, {}, {"v": 99}):
        fresh(json.dumps(d))
        assert prefs.load() == {"crowd": "ALTA"}, d


def test_unknown_fields_dropped_known_kept():
    fresh(json.dumps({"v": 1, "crowd": "OFF", "lixo": 1, "__class__": "x"}))
    assert prefs.load() == {"crowd": "OFF"}
    assert prefs.get("lixo") is None
    assert prefs.save() is True
    assert json.loads(MEM["raw"]) == {"v": 1, "crowd": "OFF"}


def test_corrupt_inputs_never_raise():
    bad = ["", "{", "null", "[]", "42", '"ALTA"', "{\"crowd\": ", "[" * 5000,
           "x" * (prefs.MAX_CHARS + 1), store.ERROR, store.InvalidText('{"crowd": "OFF"}'),
           b'{"crowd": "OFF"}', 123]
    for raw in bad:
        fresh()
        MEM["raw"] = raw
        assert prefs.load() == {"crowd": "ALTA"}, repr(raw)[:40]
        assert prefs.get("crowd") == "ALTA"


def test_store_get_exception_falls_back():
    fresh()

    def explode():
        raise OSError("disco sumiu")
    prefs._store_get = explode
    assert prefs.load() == {"crowd": "ALTA"}


def test_write_failure_returns_false_never_raises():
    fresh()
    prefs._store_set = lambda text: False
    assert prefs.set("crowd", "OFF") is False
    assert prefs.get("crowd") == "OFF"          # vale na sessao mesmo sem gravar

    def explode(text):
        raise OSError("cheio")
    prefs._store_set = explode
    assert prefs.set("crowd", "MEDIA") is False
    assert prefs.save() is False


def test_get_returns_copy_safe_load():
    fresh(json.dumps({"crowd": "OFF"}))
    d = prefs.load()
    d["crowd"] = "LIXO"
    assert prefs.get("crowd") == "OFF"


def test_real_file_store_in_tempdir():
    """Caminho real de store.py (arquivo), mas num diretorio temporario; ~ nunca e tocado."""
    tmp = tempfile.mkdtemp(prefix="soccerpy_prefs_")
    home_file = os.path.join(os.path.expanduser("~"), ".soccerpy_prefs.json")
    existed = os.path.exists(home_file)
    mtime = os.path.getmtime(home_file) if existed else None
    try:
        store.read, store.write = ORIG["read"], ORIG["write"]
        prefs._store_get, prefs._store_set = ORIG["get"], ORIG["set"]
        prefs.PREFS_PATH = os.path.join(tmp, "prefs.json")
        prefs.reset_cache()
        assert prefs.get("crowd") == "ALTA"                    # arquivo ausente
        assert prefs.set("crowd", "MEDIA") is True
        assert os.path.exists(prefs.PREFS_PATH)
        prefs.reset_cache()
        assert prefs.get("crowd") == "MEDIA"
        with open(prefs.PREFS_PATH, "wb") as f:               # bytes invalidos em UTF-8
            f.write(b'{"crowd": "OFF"\xff\xfe}')
        assert prefs.load() == {"crowd": "ALTA"}
        with open(prefs.PREFS_PATH, "w") as f:                # JSON corrompido
            f.write('{"crowd": "OFF"')
        assert prefs.load() == {"crowd": "ALTA"}
    finally:
        prefs.PREFS_PATH = ORIG["path"]
        store.read = store.write = _boom
        shutil.rmtree(tmp, ignore_errors=True)
    assert os.path.exists(home_file) == existed
    if existed:
        assert os.path.getmtime(home_file) == mtime


def test_default_path_and_key():
    assert prefs.PREFS_KEY == "soccerpy_prefs_v1"
    assert ORIG["path"] == os.path.join(os.path.expanduser("~"), ".soccerpy_prefs.json")
    assert prefs.FIELDS["crowd"] == (("ALTA", "MEDIA", "OFF"), "ALTA")


def test_never_touched_real_store():
    assert FORBIDDEN == []


def main():
    names = sys.argv[1:] or [n for n in globals() if n.startswith("test_")]
    names = [n for n in names if n != "test_never_touched_real_store"] + \
        (["test_never_touched_real_store"] if "test_never_touched_real_store" in names else [])
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
