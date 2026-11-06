"""Testes do audio sintetizado (game/sfx.py + game/music.py; Fase 6). Rodar da raiz:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python tests/test_sfx.py [teste ...]

O mixer com o driver dummy pode abrir ou nao: os testes de runtime cobrem os dois casos. NUNCA toca
~/.soccerpy_*.json: prefs/campaign/garage/career usam stores em memoria e store.write e uma sentinela.
"""
import os
import random
import sys
import time
from array import array

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
os.chdir(os.path.join(ROOT, "game"))

import pygame  # noqa: E402

import campaign as cm  # noqa: E402
import career  # noqa: E402
import garage as gm  # noqa: E402
import prefs  # noqa: E402
import store  # noqa: E402

FORBIDDEN = []


def _forbid(name):
    def f(*a, **k):
        FORBIDDEN.append(name)
        raise AssertionError("%s chamada pelos testes de som" % name)
    return f


PREFS = {}
prefs._store_get = lambda: PREFS.get("raw")
prefs._store_set = lambda t: PREFS.__setitem__("raw", t) or True
cm._store_get = lambda: None
cm._store_set = _forbid("campaign._store_set")
gm._store_get = lambda: None
gm._store_set = _forbid("garage._store_set")
career._store_get = lambda: None
career._store_set = _forbid("career._store_set")
store.write = _forbid("store.write")

import music  # noqa: E402
import sfx  # noqa: E402
import soccer  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((soccer.W, soccer.H))
INT16 = 32767


def reset_prefs(raw=None):
    PREFS.clear()
    if raw is not None:
        PREFS["raw"] = raw
    prefs.reset_cache()


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


# ------------------------------------------------------------------ sintese (pura)
def test_every_sfx_buffer_sane():
    for sid in sfx.SFX:
        a = sfx.render(sid)
        assert isinstance(a, array) and a.typecode == "h", sid
        assert 0.02 * sfx.SR <= len(a) <= 3.0 * sfx.SR, (sid, len(a))
        peak = max(abs(v) for v in a)
        assert 0.2 * INT16 < peak <= 0.86 * INT16, (sid, peak)      # audivel e sem saturar
        assert abs(a[-1]) < 0.2 * INT16, (sid, a[-1])               # termina perto do zero (sem estalo)


def test_sfx_deterministic_and_no_global_random():
    st = random.getstate()
    a = {sid: sfx.render(sid).tobytes() for sid in sfx.SFX}
    random.seed(12345)                         # estado global diferente nao muda nada
    b = {sid: sfx.render(sid).tobytes() for sid in sfx.SFX}
    assert a == b
    random.seed(0)
    s0 = random.getstate()
    for sid in ("goal", "ooh", "ole"):
        sfx.render(sid)
    for tr in music.TRACKS:
        music.render(tr)
    assert random.getstate() == s0             # nada consumiu o random global
    random.setstate(st)


def test_music_tracks():
    for tr, spec in music.TRACKS.items():
        a = music.render(tr)
        step = int(sfx.SR * 60.0 / spec["bpm"] / 4)
        assert len(a) == step * 16 * len(spec["bars"]), tr
        assert all(len(b[0].split()) == 16 and len(b[1].split()) == 16 and len(b[2]) == 16 for b in spec["bars"]), tr
        peak = max(abs(v) for v in a)
        assert 0.3 * INT16 < peak < INT16, (tr, peak)
        assert a.tobytes() == music.render(tr).tobytes(), tr          # deterministico
    assert 10.0 <= music.duration("menu") <= 20.0 and 10.0 <= music.duration("match") <= 20.0
    assert music.duration("win") < 5.0 and music.duration("lose") < 6.0
    assert music.TRACKS["menu"]["loop"] and music.TRACKS["match"]["loop"]
    assert music.midi("A4") == 69 and music.midi("C4") == 60 and music.midi("F#4") == 66 and music.midi("Bb3") == 58


def test_amplitude_budget_never_clips():
    """Soma dos picos da musica cabe no int16 por construcao (lead + baixo + o maior golpe da bateria)."""
    worst = (music.LEAD_AMP + music.BASS_AMP
             + max(music.KICK_AMP, music.SNARE_AMP, music.HAT_AMP, music.CRASH_AMP))
    assert worst < INT16


def test_fit_formats():
    mono = array("h", [0, 1000, -1000, 32767, -32768] * 10)
    n = len(mono)
    b = sfx.fit(mono, sfx.SR, 1, "h")
    assert b == mono.tobytes()
    st = array("h")
    st.frombytes(sfx.fit(mono, sfx.SR, 2, "h"))
    assert len(st) == 2 * n and st[0::2] == mono and st[1::2] == mono
    up = array("h")
    up.frombytes(sfx.fit(mono, 2 * sfx.SR, 2, "h"))
    assert len(up) == 4 * n and up[0::4] == mono and up[2::4] == mono
    odd = array("h")
    odd.frombytes(sfx.fit(mono, 48000, 2, "h"))
    assert len(odd) == 2 * (n * 48000 // sfx.SR)
    fl = array("f")
    fl.frombytes(sfx.fit(mono, 44100, 2, "f"))
    assert len(fl) == 4 * n and all(-1.0 <= v < 1.0 for v in fl)


def test_generation_time_budget():
    """Geracao total (efeitos + trilhas + conversao 44100 estereo) < ~1 s no desktop."""
    t = time.perf_counter()
    for sid in sfx.SFX:
        sfx.fit(sfx.render(sid), 44100, 2, "h")
    t_sfx = time.perf_counter() - t
    t = time.perf_counter()
    for tr in music.TRACKS:
        sfx.fit(music.render(tr), 44100, 2, "h")
    t_mus = time.perf_counter() - t
    print("   geracao: efeitos %.0f ms, trilhas %.0f ms (total %.0f ms)"
          % (t_sfx * 1000, t_mus * 1000, (t_sfx + t_mus) * 1000))
    assert t_sfx + t_mus < 2.0                 # folga para maquina carregada (meta < 1 s)


# ------------------------------------------------------------------ runtime
def test_noop_before_init():
    sfx.shutdown()
    assert sfx.S.ok is False
    assert sfx.play("kick") is False and sfx.play("nao_existe") is False
    assert sfx.result(2, 0) is False and sfx.jingle("win") is False
    sfx.tick("menu")                           # nao levanta
    assert sfx.pump() is True


def test_noop_when_mixer_fails():
    mx = pygame.mixer
    orig = (mx.get_init, mx.init)
    mx.get_init = lambda: None

    def boom(*a, **k):
        raise pygame.error("sem dispositivo de audio")
    mx.init = boom
    try:
        assert sfx.init() is False
        assert sfx.S.ok is False and "sem dispositivo" in (sfx.S.err or "")
        assert sfx.play("goal") is False
        sfx.tick("match")
    finally:
        mx.get_init, mx.init = orig
        sfx.shutdown()


def _init_or_skip():
    ok = sfx.init()
    if not ok:
        print("   (mixer indisponivel com este driver: %s; runtime vira no-op)" % sfx.S.err)
    return ok


def test_runtime_build_throttle_and_mute():
    reset_prefs()
    clk = FakeClock()
    sfx.clock = clk
    try:
        if not _init_or_skip():
            assert sfx.play("kick") is False
            return
        rate, chans, kind = sfx.S.fmt
        t = time.perf_counter()
        frames = 0
        while not sfx.pump(5.0):
            frames += 1
            assert frames < 5000
        print("   mixer %s: tudo gerado em %.0f ms (%d quadros de 5 ms)"
              % (pygame.mixer.get_init(), (time.perf_counter() - t) * 1000, frames + 1))
        for sid in list(sfx.SFX) + list(music.TRACKS):
            assert sfx.ready(sid), sid
        snd = sfx.S.sounds["kick"]
        assert snd.get_length() > 0.05
        assert sfx.play("kick") is True
        assert sfx.play("kick") is False                  # throttle (mesmo instante)
        clk.t += sfx.SFX["kick"][2] + 0.01
        sfx.play("kick")                                   # depois do intervalo pode tocar (se houver voz)
        assert sfx.play("nao_existe") is False
        assert sfx.toggle_mute() is True and sfx.muted()
        clk.t += 5.0
        assert sfx.play("goal") is False                   # mudo
        assert sfx.toggle_mute() is False and not sfx.muted()
        assert sfx.play("goal") is True
        sfx.music_tick("menu")
        assert sfx.S.cur == "menu"
        sfx.music_tick("match")
        assert sfx.S.cur == "match"
        assert sfx.result(3, 1) is True and sfx.S.jingle and sfx.S.cur == "win"
        sfx.music_tick("match")                            # jingle em curso: nao troca
        assert sfx.S.cur == "win"
        clk.t += 5.0
        assert sfx.result(1, 1) is True                    # empate = efeito "draw"
        prefs.set("music_vol", "0")
        sfx._apply_volumes()
        sfx.S.chan.stop()
        sfx.music_tick("menu")
        assert sfx.S.cur is None                           # musica desligada
        prefs.set("music_vol", "2")
        sfx.music_tick("menu")
        assert sfx.S.cur == "menu"
    finally:
        sfx.clock = time.perf_counter
        sfx.shutdown()
        reset_prefs()


def test_prefs_cycle_and_labels():
    reset_prefs()
    sfx.shutdown()                                         # sem mixer: prefs continuam funcionando
    assert sfx.level("sfx_vol") == "2" and sfx.level("music_vol") == "2" and not sfx.muted()
    assert [sfx.cycle("sfx_vol") for _ in range(4)] == ["3", "0", "1", "2"]
    assert sfx.cycle("music_vol") == "3" and prefs.get("music_vol") == "3"
    assert '"music_vol": "3"' in PREFS["raw"]
    assert sfx.toggle_mute() is True and prefs.get("mute") == "1"
    for lab in sfx.labels():
        lab.encode("latin-1")
    assert sfx.labels()[0] == "M: som MUDO"
    reset_prefs('{"v": 1, "sfx_vol": "7", "mute": "x"}')  # invalido -> padrao
    assert sfx.level("sfx_vol") == "2" and not sfx.muted()
    assert sfx.labels() == ("M: som LIGADO", "S: efeitos MÉDIO", "N: música MÉDIO")
    reset_prefs()


# ------------------------------------------------------------------ integracao com o jogo
def _run(g, seed, steps):
    random.seed(seed)
    g.new_match(1, None)
    g.teams[0].human = None                    # CPU x CPU (sem teclado)
    for _ in range(steps):
        g.step(1 / 60)
    return list(g.score), g.ball.pos.x, g.ball.pos.y, g.time_left, random.random()


def test_simulation_identical_with_sound_on_off():
    reset_prefs()
    g = soccer.Game(screen)
    sfx.shutdown()
    off = _run(g, 7, 3000)
    _init_or_skip()
    sfx.pump(10_000)
    try:
        on = _run(g, 7, 3000)
    finally:
        sfx.shutdown()
    assert off == on, (off, on)


def test_game_hooks_and_keys():
    reset_prefs()
    g = soccer.Game(screen)
    clk = FakeClock()
    sfx.clock = clk
    try:
        ok = _init_or_skip()
        sfx.pump(10_000)
        g.new_match(1, None)
        if ok:
            assert "whistle" in sfx.S.last             # apito do pontape inicial
        g.speed_idx = 3                                # MAX: nenhum som de lance
        sfx.S.last.clear()
        clk.t += 10
        g.crowd_event("goal", 0)
        g.snd("kick")
        assert sfx.S.last == {}
        g.speed_idx = 0
        g.crowd_event("goal", 0)
        if ok:
            assert "goal" in sfx.S.last
        assert g.music_track() == "match"
        g.state = "menu"
        assert g.music_track() == "menu"
        for st in ("career", "robots", "campaign"):
            g.state = st
            assert g.music_track() == "menu"
        g.state = "menu"
        assert g.audio_key(pygame.K_m) is True and prefs.get("mute") == "1"
        assert g.audio_key(pygame.K_m) is True and prefs.get("mute") == "0"
        assert g.audio_key(pygame.K_s) is True and prefs.get("sfx_vol") == "3"
        assert g.audio_key(pygame.K_n) is True and prefs.get("music_vol") == "3"
        g.new_match(1, None)
        g.state = "play"
        assert g.audio_key(pygame.K_s) is False        # S joga (P1) fora da pausa
        g.paused = True
        assert g.audio_key(pygame.K_s) is True and prefs.get("sfx_vol") == "0"
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, mod=0, unicode="m"))
        assert prefs.get("mute") == "1"
        g.paused = False
        g.state = "menu"
        g.draw()                                       # rodape com a linha do som
        assert g.audio_label() in [k[0] for k in g.text_cache]
    finally:
        sfx.clock = time.perf_counter
        sfx.shutdown()
        reset_prefs()


def test_never_touched_real_store():
    assert FORBIDDEN == []


def main():
    names = sys.argv[1:] or [n for n in globals() if n.startswith("test_")]
    names = [n for n in names if n != "test_never_touched_real_store"] + \
        (["test_never_touched_real_store"] if "test_never_touched_real_store" in names else [])
    fails = 0
    for n in names:
        try:
            globals()[n]()
            print("ok %s" % n)
        except Exception:  # noqa: BLE001
            import traceback
            fails += 1
            print("FAIL %s" % n)
            traceback.print_exc()
    print("%d testes passaram" % (len(names) - fails) if not fails else "%d falhas" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
