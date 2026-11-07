# -*- coding: utf-8 -*-
"""Audio do jogo: efeitos sintetizados por codigo (stdlib: math/array) + sons gravados em game/audio/.

Trilhas em arquivo (STREAMS, tocadas em stream por pygame.mixer.music, uma faixa depois da outra):
"menu" = menu1/menu2 alternando (comeca logo apos o clique da tela de carregamento), "sub" = tela de
robos, "cups" = carreira e campanha, "match" = torcida durante a partida. Efeitos em arquivo
(FILE_SFX): grito de gol, apito final, torcida na trave (soma ao CLANG sintetizado) e o robo
desligando; o motor dos robos (AMB_FILE) roda em loop num canal proprio enquanto a bola rola.
Faltou arquivo ou nao abriu -> volta o som sintetizado equivalente (music.py / receitas daqui).
Cada som sintetizado nasce em
SR = 22050 Hz mono 16-bit e e convertido UMA vez para o formato real do mixer (pygame.mixer.get_init():
taxa, canais, int16 ou float32) antes de virar pygame.mixer.Sound(buffer=...).

Uso pelo jogo (soccer.py / *_ui.py):
    sfx.pre_init()            antes de pygame.init() (pede 22050 Hz estereo ao mixer)
    sfx.init()                depois de criar o Game: abre o mixer (falhou -> tudo vira no-op)
    sfx.tick(track, amb)      1x por quadro: gera/carrega os buffers aos poucos (orcamento de ms),
                              troca a trilha ("menu", "sub", "cups", "match" ou None) e liga/desliga
                              o motor dos robos (amb)
    sfx.play(id)              efeito (com throttle por id e limite de vozes); id desconhecido = nada
    sfx.result(meus, deles)   jingle de vitoria/derrota (empate = efeito curto)
    sfx.toggle_mute() / cycle("sfx_vol" | "music_vol")   prefs gravadas (tecla M / S / N)

Invariantes: nunca usa o `random` global nem o RNG do motor (ruido com random.Random(semente)
proprio por som); nenhum pygame.Surface; antes de init() (testes, goldens, harness) play/tick
retornam na primeira linha. Qualquer erro do mixer desliga o audio em silencio.
"""
import math
import os
import random
import sys
import time
from array import array

import prefs

SR = 22050                                   # taxa interna de sintese (mono, 16-bit)
# taxa pedida ao mixer: 44,1 kHz (a mesma do navegador). Com 22 kHz o SDL_mixer do pygame 2.6.1 devolve
# Sound VAZIO (get_length() == 0) para algumas gravacoes de 44,1 kHz (ex.: vaias, gol, inicio3, palmas3).
# A sintese continua em SR e o fit() converte uma vez (44100 = 2 x 22050: repeticao por fatia).
MIXER_RATE = 44100
TWO_PI = 2.0 * math.pi
LEVEL_GAIN = {"0": 0.0, "1": 0.35, "2": 0.65, "3": 1.0}
LEVEL_NAMES = {"0": "DESL.", "1": "BAIXO", "2": "MÉDIO", "3": "ALTO"}
MATCH_MUSIC_GAIN = 0.85                      # torcida de fundo da partida (um pouco abaixo dos efeitos)
N_CHANNELS = 16                              # canal 0 = musica, 1 = motor dos robos; 14 vozes de efeito
MUSIC_FADE_MS = 400
PUMP_MS = 5.0                                # orcamento de geracao por quadro (ms de relogio)
WEB = sys.platform == "emscripten"
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
STREAMS = {                                  # trilha -> faixas (em ciclo; uma depois da outra)
    "menu": ("menu1.ogg", "menu2.ogg", "menu3.ogg"),            # menu principal
    "sub": ("interno1.ogg", "interno2.ogg", "submenus.ogg"),     # robos
    "cups": ("copas.ogg", "interno1.ogg", "interno2.ogg"),       # carreira e campanha
    "match": ("torcida.ogg", "torcida_boca.ogg", "torcida_estadio.ogg"),   # torcida de fundo, alternando
}
SYNTH_TRACK = {"menu": "menu", "sub": "menu", "cups": "menu", "match": "match"}   # sem arquivo
# TABELA UNICA reacao -> sons gravados. id -> (variacoes, throttle s, vozes max, volume). Cada variacao e
# um arquivo de game/audio ("x.ogg") ou uma variacao DERIVADA em runtime dele: ("x.ogg", velocidade,
# inicio, fim[, max_s]) = reamostra (velocidade != 1 muda tom e andamento: outra "torcida"), recorta o
# trecho [inicio, fim) (fracoes da duracao), no maximo max_s (DERIVE_MAX_S) e suaviza as pontas. As
# derivadas nao viram arquivo (o game.apk nao cresce) e sao geradas aos poucos no _builder. Sorteio:
# "saco embaralhado" por id (RNG privado): toca todas antes de repetir e nunca a mesma duas vezes
# seguidas. Vozes faladas (SPOKEN) tem intervalo proprio maior. Para trocar um som: mexa so aqui.
FILE_SFX = {
    # grito de gol a favor (jogador; no 2P, de qualquer um) e do adversario
    "goal": (("gol.ogg", "gol_grito.ogg", "gol_e_gol.ogg", "gol_olha_o_gol.ogg", "gol_brasil.ogg", "gol_we.ogg",
              ("gol_grito.ogg", 0.92, 0.0, 1.0), ("gol_e_gol.ogg", 1.08, 0.0, 1.0), ("gol.ogg", 0.94, 0.0, 1.0)),
             1.5, 1, 1.0),
    "goal_opp": (("gol_adv1.ogg", "gol_adv2.ogg", "gol_adv3.ogg", "gol_adv4.ogg",
                  ("gol_adv1.ogg", 0.93, 0.0, 1.0), ("gol_adv3.ogg", 1.07, 0.0, 1.0)), 1.5, 1, 1.0),
    # quase gol: do jogador (defesa/trave do rival) e contra o jogador
    "near": (("quase_uh.ogg", "defesa1.ogg", "defesa3.ogg", "derrota2.ogg", ("quase_uh.ogg", 0.9, 0.0, 1.0),
              ("uhhh_torcida.ogg", 1.06, 0.0, 0.45)),
             3.0, 1, 0.9),
    "near_opp": (("quase_nao.ogg", ("quase_nao.ogg", 0.88, 0.0, 1.0), ("quase_nao.ogg", 1.12, 0.0, 1.0)),
                 3.0, 1, 0.9),
    # inicio: "comecou!" / "ja comecou" / vinheta (1o pontape)
    "kickoff_voice": (("comecou.ogg", "inicio2.ogg", "inicio3.ogg"), 2.0, 1, 0.9),
    "applause": (("palmas.ogg", "palmas2.ogg", "palmas3.ogg", ("palmas.ogg", 0.94, 0.0, 0.45)), 4.0, 1, 0.6),
    "crowd_chant": (("palmas3.ogg", "palmas.ogg", ("palmas2.ogg", 1.0, 0.0, 0.4, 4.5)), 6.0, 1, 0.5),
    "ooh": (("uhhh_torcida.ogg", "quase_uh.ogg", "defesa3.ogg", "derrota2.ogg", ("uhhh_torcida.ogg", 0.9, 0.0, 0.55),
             ("quase_uh.ogg", 1.12, 0.0, 1.0)), 1.6, 1, 0.75),          # "uuuh" da chance
    # ole: o coro de 14 s (ole2) entra em dois trechos de ~5 s
    "ole": (("ole.ogg", ("ole2.ogg", 1.0, 0.0, 0.38, 5.0), ("ole2.ogg", 1.0, 0.5, 0.88, 5.0),
             ("ole.ogg", 0.92, 0.0, 1.0)), 3.0, 1, 0.8),
    "boo": (("vaias.ogg", "vaia2.ogg", ("vaias.ogg", 0.9, 0.0, 0.33)), 6.0, 1, 0.6),
    # lamento da torcida da casa (gol sofrido pelo jogador)
    "lament": (("lamento1.ogg", "lamento2.ogg", "lamento3.ogg", ("lamento1.ogg", 0.9, 0.0, 1.0)), 3.0, 1, 0.85),
    # defesa: "uuuh" / exclamacao, palmas (soma a luva sintetizada: FILE_LAYER)
    "save": (("defesa1.ogg", "defesa3.ogg", ("palmas.ogg", 1.0, 0.35, 0.6), ("defesa1.ogg", 0.92, 0.0, 1.0)),
             2.5, 1, 0.6),
    "crowd_cheer": (("palmas3.ogg", "palmas.ogg", ("palmas2.ogg", 1.0, 0.45, 0.8, 4.0)), 5.0, 1, 0.55),
    # fim de jogo do ponto de vista do jogador
    "win_crowd": (("vitoria1.ogg", ("vitoria1.ogg", 0.94, 0.0, 1.0), ("vitoria1.ogg", 1.06, 0.0, 1.0)), 4.0, 1, 0.85),
    "lose_crowd": (("derrota1.ogg", "derrota2.ogg", ("derrota2.ogg", 0.93, 0.0, 1.0)), 4.0, 1, 0.85),
    "click": (("click.ogg",), 0.05, 2, 0.8),
    "whistle_end": (("apito_final.ogg",), 1.5, 1, 0.8),
    "post": (("trave_torcida.ogg", "trave2.ogg", "trave3.ogg", ("trave_torcida.ogg", 0.9, 0.0, 0.9)), 0.4, 1, 0.85),
    "robot_off": (("robo_desligar.ogg",), 3.0, 1, 0.7),
}
# vozes faladas (repetidas cansam): arquivo -> intervalo minimo (s) entre duas vezes dele
SPOKEN = {"inicio2.ogg": 60.0, "lamento3.ogg": 45.0, "defesa3.ogg": 35.0, "trave3.ogg": 35.0,
          "derrota2.ogg": 35.0}
DERIVE_MAX_S = 3.0
DERIVE_CHUNK = 6000             # quadros por pedaco da geracao (um yield do _builder)
DERIVE_FADE_S = 0.03


def file_names(sid=None):
    """Arquivos de game/audio usados pelos efeitos (de `sid` ou de todos), sem repetir."""
    out = []
    for k, v in FILE_SFX.items():
        if sid is None or k == sid:
            for f in v[0]:
                name = f if isinstance(f, str) else f[0]
                if name not in out:
                    out.append(name)
    return out


FILE_LAYER = ("post", "save")                       # o arquivo soma ao sintetizado; os outros substituem
SYNTH_ALIAS = {"goal_opp": "goal"}           # sem arquivo: o efeito sintetizado equivalente
AMB_FILE, AMB_VOL, AMB_FADE_MS = "robo_motor.ogg", 0.35, 300


# ============================================================ sintese (pura, sem pygame)
def _n(dur):
    return max(1, int(dur * SR))


def tone(dur, f0, f1=None, wave="sq", vol=0.5, att=0.004, decay=1.0, vib=0.0, vibf=0.0, duty=0.5,
         glide="exp"):
    """Oscilador com glissando f0->f1 (exp ou lin), envelope (ataque linear + (1-x)**decay) e vibrato.
    wave: sq (pulso com duty), tri, saw, sin. Devolve lista de floats (-vol..vol)."""
    n = _n(dur)
    f1 = f0 if f1 is None else f1
    out = [0.0] * n
    ph = 0.0
    inv = 1.0 / SR
    na = max(1, int(att * SR))
    sin = math.sin
    lnr = math.log(f1 / f0) if glide == "exp" else 0.0
    exp = math.exp
    for i in range(n):
        x = i / n
        f = f0 * exp(lnr * x) if glide == "exp" else f0 + (f1 - f0) * x
        if vib:
            f *= 1.0 + vib * sin(TWO_PI * vibf * i * inv)
        ph += f * inv
        ph -= int(ph)
        if wave == "sq":
            w = 1.0 if ph < duty else -1.0
        elif wave == "tri":
            w = 4.0 * ph - 1.0 if ph < 0.5 else 3.0 - 4.0 * ph
        elif wave == "saw":
            w = 2.0 * ph - 1.0
        else:
            w = sin(TWO_PI * ph)
        e = (1.0 - x) ** decay
        if i < na:
            e *= i / na
        out[i] = w * e * vol
    return out


def noise(dur, rng, vol=0.5, lp=1.0, hp=0.0, att=0.002, decay=1.0, swell=0.0):
    """Ruido branco (rng privado) com passa-baixa (lp: 0..1, 1 = aberto) e passa-alta de 1 polo (hp).
    swell > 0: envelope sobe ate `swell` da duracao e cai depois (rugido da torcida)."""
    n = _n(dur)
    out = [0.0] * n
    rnd = rng.random
    y = 0.0
    low = 0.0
    na = max(1, int(att * SR))
    for i in range(n):
        x = i / n
        y += lp * ((rnd() * 2.0 - 1.0) - y)
        v = y
        if hp:
            low += hp * (y - low)
            v = y - low
        if swell:
            e = x / swell if x < swell else ((1.0 - x) / (1.0 - swell)) ** decay
        else:
            e = (1.0 - x) ** decay
        if i < na:
            e *= i / na
        out[i] = v * e * vol
    return out


def mix(dst, src, at=0.0, gain=1.0):
    """Soma src em dst a partir de `at` segundos (dst cresce se preciso)."""
    o = int(at * SR)
    need = o + len(src)
    if need > len(dst):
        dst.extend([0.0] * (need - len(dst)))
    for i, v in enumerate(src):
        dst[o + i] += v * gain
    return dst


def finish(buf, peak=0.85):
    """Normaliza para `peak` do fundo de escala e devolve array('h') (nunca satura)."""
    m = max((abs(v) for v in buf), default=0.0)
    k = (peak * 32767.0 / m) if m > 0 else 0.0
    return array("h", [int(v * k) for v in buf])


def _chord_voices(dur, freqs, wave, vol, decay, att=0.01, vib=0.0, vibf=0.0):
    out = []
    for f in freqs:
        mix(out, tone(dur, f, wave=wave, vol=vol, decay=decay, att=att, vib=vib, vibf=vibf))
    return out


# ------------------------------------------------------------- receitas dos efeitos
def s_kick(rng):                              # chute forte: "tum" grave + estalo
    b = tone(0.11, 190, 55, wave="sin", vol=0.9, decay=1.6)
    mix(b, noise(0.03, rng, vol=0.6, lp=0.6, decay=2.0))
    return finish(b, 0.8)


def s_touch(rng):                             # toque / passe: "tic" curto
    b = tone(0.045, 320, 150, wave="sin", vol=0.8, decay=2.0)
    mix(b, noise(0.012, rng, vol=0.3, lp=0.5, decay=2.0))
    return finish(b, 0.55)


def s_post(rng):                              # trave: CLANG metalico (parciais inarmonicas)
    b = []
    for f, a, d in ((523, 0.5, 2.2), (1231, 0.35, 2.8), (1873, 0.25, 3.5), (2641, 0.18, 4.0), (3390, 0.1, 5.0)):
        mix(b, tone(0.7, f, wave="sin", vol=a, decay=d, att=0.001))
    mix(b, noise(0.03, rng, vol=0.5, lp=0.9, decay=1.5))
    return finish(b, 0.8)


def _whistle(dur, rng, vol=0.5):
    b = tone(dur, 2750, 2700, wave="sin", vol=vol, att=0.02, decay=0.25, vib=0.035, vibf=28.0)
    mix(b, noise(dur, rng, vol=0.06, lp=0.7, hp=0.3, decay=0.3))
    return b


def s_whistle(rng):                           # apito de inicio
    return finish(_whistle(0.38, rng), 0.6)


def s_whistle_end(rng):                       # fim de jogo: curto, curto, longo
    b = []
    mix(b, _whistle(0.16, rng), 0.0)
    mix(b, _whistle(0.16, rng), 0.24)
    mix(b, _whistle(0.75, rng), 0.48)
    return finish(b, 0.6)


def _crowd(dur, rng, vol=0.5, swell=0.25, decay=1.2):
    b = noise(dur, rng, vol=vol, lp=0.22, hp=0.02, swell=swell, decay=decay)
    mix(b, noise(dur, rng, vol=vol * 0.5, lp=0.5, hp=0.15, swell=swell, decay=decay))
    return b


def s_goal(rng):                              # explosao da torcida + buzina (acorde de saw)
    b = _crowd(2.2, rng, vol=0.7, swell=0.12)
    for t0 in (0.05, 0.5):
        mix(b, _chord_voices(0.38, (233.1, 293.7, 349.2), "saw", 0.16, 0.4, att=0.01), t0)
    return finish(b, 0.85)


def s_ooh(rng):                               # "uuuh" da chance: coro de vozes graves descendo
    b = _crowd(0.9, rng, vol=0.35, swell=0.3, decay=1.5)
    for k, f in enumerate((180, 186, 174, 192, 168)):
        mix(b, tone(0.9, f, f * 0.78, wave="tri", vol=0.12, att=0.12, decay=1.2, vib=0.01, vibf=5 + k))
    return finish(b, 0.6)


def s_save(rng):                              # defesa: luva "tump" + "olé" curto da torcida
    b = tone(0.09, 140, 70, wave="sin", vol=0.8, decay=1.5)
    mix(b, noise(0.05, rng, vol=0.5, lp=0.35, decay=2.0))
    mix(b, _crowd(0.6, rng, vol=0.35, swell=0.35, decay=1.4), 0.06)
    return finish(b, 0.7)


def _clap(rng, b, at):
    for k in range(5):                         # varias maos quase juntas
        mix(b, noise(0.035, rng, vol=0.5, lp=0.8, hp=0.25, decay=3.0), at + k * 0.006)


def s_ole(rng):                               # palmas ritmadas (fim de jogo / festa)
    b = []
    for t0 in (0.0, 0.22, 0.44, 0.78, 1.0, 1.22):
        _clap(rng, b, t0)
    mix(b, _crowd(1.4, rng, vol=0.15, swell=0.4), 0.0)
    return finish(b, 0.6)


def s_steal(rng):                             # roubo de bola: "shk" descendo
    b = noise(0.13, rng, vol=0.6, lp=0.45, hp=0.2, decay=1.2)
    mix(b, tone(0.08, 520, 260, wave="sq", vol=0.18, duty=0.25, decay=1.5))
    return finish(b, 0.55)


def s_dribble(rng):                           # drible: "fwip" subindo
    b = noise(0.16, rng, vol=0.5, lp=0.35, hp=0.15, att=0.05, decay=0.8)
    mix(b, tone(0.14, 300, 900, wave="tri", vol=0.25, att=0.03, decay=1.0))
    return finish(b, 0.55)


def s_skill(rng):                             # skill ativada: BUZZ (saw grave com trinado)
    b = tone(0.32, 110, 165, wave="saw", vol=0.5, att=0.01, decay=0.7, vib=0.08, vibf=24.0)
    mix(b, tone(0.32, 220, 330, wave="sq", vol=0.15, duty=0.3, att=0.01, decay=0.9))
    return finish(b, 0.6)


def s_dash(rng):                              # arrancada: ZOOM (varredura subindo + vento)
    b = tone(0.36, 180, 1300, wave="saw", vol=0.3, att=0.02, decay=0.9)
    mix(b, noise(0.36, rng, vol=0.5, lp=0.3, hp=0.08, att=0.08, decay=1.2))
    return finish(b, 0.6)


def s_click(rng):                             # clique / escolha em menu
    b = tone(0.035, 1250, 1050, wave="sq", vol=0.4, duty=0.5, att=0.001, decay=1.5)
    return finish(b, 0.45)


def s_back(rng):                              # voltar / Esc
    b = tone(0.06, 700, 420, wave="sq", vol=0.4, duty=0.5, att=0.001, decay=1.2)
    return finish(b, 0.4)


def s_blip(rng):                              # avanco de dialogo (discreto)
    return finish(tone(0.028, 980, wave="tri", vol=0.4, att=0.002, decay=1.5), 0.25)


def s_toggle(rng):                            # opcao alternada (T/C/S/N/M)
    b = tone(0.05, 880, wave="sq", vol=0.3, duty=0.25, decay=1.2)
    mix(b, tone(0.07, 1320, wave="sq", vol=0.3, duty=0.25, decay=1.2), 0.05)
    return finish(b, 0.4)


def _arp(notes, step, dur, wave="sq", vol=0.3, duty=0.25, decay=1.3):
    b = []
    for k, f in enumerate(notes):
        mix(b, tone(dur, f, wave=wave, vol=vol, duty=duty, decay=decay), k * step)
    return b


def s_reward(rng):                            # recompensa / subiu de nivel: arpejo brilhante
    b = _arp((523.3, 659.3, 784.0, 1046.5, 1318.5, 1568.0), 0.06, 0.22)
    mix(b, tone(0.5, 2093.0, wave="tri", vol=0.12, decay=1.5), 0.36)
    return finish(b, 0.55)


def s_buy(rng):                               # compra: moeda "ka-ching"
    b = tone(0.07, 987.8, wave="sq", vol=0.35, duty=0.5, decay=0.6)
    mix(b, tone(0.38, 1318.5, wave="sq", vol=0.35, duty=0.5, decay=1.4), 0.07)
    return finish(b, 0.5)


def s_upgrade(rng):                           # upgrade: power-up subindo
    b = tone(0.3, 300, 1200, wave="sq", vol=0.25, duty=0.25, decay=0.6, vib=0.05, vibf=30.0)
    mix(b, _arp((784.0, 1046.5, 1568.0), 0.05, 0.18, vol=0.25), 0.25)
    return finish(b, 0.5)


def s_error(rng):                             # acao recusada (sem sucata, etc.)
    b = tone(0.16, 150, 120, wave="sq", vol=0.4, duty=0.5, decay=0.8)
    return finish(b, 0.4)


def s_draw(rng):                              # empate: "plim-plom" neutro
    b = tone(0.3, 659.3, wave="tri", vol=0.4, decay=1.2)
    mix(b, tone(0.45, 523.3, wave="tri", vol=0.4, decay=1.4), 0.22)
    return finish(b, 0.5)


# id -> (receita, semente do ruido, intervalo minimo entre disparos em s, vozes simultaneas, ganho)
SFX = {
    "kick": (s_kick, 11, 0.06, 2, 0.8),
    "touch": (s_touch, 12, 0.08, 2, 0.5),
    "post": (s_post, 13, 0.4, 1, 0.9),
    "whistle": (s_whistle, 14, 0.5, 1, 0.8),
    "whistle_end": (s_whistle_end, 15, 1.5, 1, 0.8),
    "goal": (s_goal, 16, 1.5, 1, 1.0),
    "ooh": (s_ooh, 17, 1.2, 1, 0.8),
    "save": (s_save, 18, 0.8, 1, 0.85),
    "ole": (s_ole, 19, 2.0, 1, 0.8),
    "steal": (s_steal, 20, 0.25, 1, 0.6),
    "dribble": (s_dribble, 21, 0.3, 1, 0.6),
    "skill": (s_skill, 22, 0.3, 2, 0.6),
    "dash": (s_dash, 23, 0.3, 2, 0.6),
    "click": (s_click, 24, 0.05, 2, 0.7),
    "back": (s_back, 25, 0.08, 1, 0.7),
    "blip": (s_blip, 26, 0.05, 1, 0.5),
    "toggle": (s_toggle, 27, 0.08, 1, 0.7),
    "reward": (s_reward, 28, 0.5, 1, 0.8),
    "buy": (s_buy, 29, 0.15, 1, 0.8),
    "upgrade": (s_upgrade, 30, 0.2, 1, 0.8),
    "error": (s_error, 31, 0.2, 1, 0.6),
    "draw": (s_draw, 32, 0.5, 1, 0.8),
}
UI_FIRST = ("click", "back", "blip", "toggle")   # gerados primeiro (menu responde ja no boot)


def render(sid):
    """Buffer mono SR 16-bit (array('h')) do efeito `sid` (deterministico: rng proprio)."""
    fn, seed = SFX[sid][0], SFX[sid][1]
    return fn(random.Random(seed))


# ============================================================ formato do mixer
def fit(mono, rate=SR, chans=2, kind="h"):
    """Converte array('h') mono em SR para bytes no formato do mixer.

    rate: taxa do mixer (multiplo inteiro de SR -> repeticao por fatia; outra -> vizinho mais proximo);
    chans: canais (amostra repetida); kind: "h" int16 ou "f" float32 (-1..1)."""
    n = len(mono)
    if rate == SR:
        m = mono
    elif rate % SR == 0:
        k = rate // SR
        m = array("h", bytes(2 * n * k))
        for j in range(k):
            m[j::k] = mono
    else:
        n2 = n * rate // SR
        m = array("h", [mono[(i * SR) // rate] for i in range(n2)])
    if chans > 1:
        out = array("h", bytes(2 * len(m) * chans))
        for c in range(chans):
            out[c::chans] = m
    else:
        out = m
    if kind == "f":
        out = array("f", [v / 32768.0 for v in out])
    return out.tobytes()


# ============================================================ runtime (pygame.mixer)
def _log(msg):
    """Uma linha no stdout (desktop) e, no navegador, tambem no console do JS (evidencia/diagnostico)."""
    print(msg)
    if WEB:
        try:
            import platform as _pf             # modulo do pygbag (window = objeto JS)
            _pf.window.console.log(msg)
        except Exception:  # noqa: BLE001
            pass


class _State:
    def __init__(self):
        self.ok = False              # mixer aberto e utilizavel
        self.fmt = None              # (rate, chans, kind)
        self.sounds = {}             # id -> pygame.mixer.Sound (efeitos e trilhas)
        self.gen = None              # gerador da construcao em segundo plano
        self.last = {}               # id -> instante do ultimo disparo (throttle)
        self.chan = None             # canal reservado da musica
        self.want = None             # trilha pedida pelo jogo
        self.cur = None              # trilha tocando
        self.jingle = False          # jingle tocando no canal da musica
        self.build_ms = {}           # id -> ms gastos gerando (medicao)
        self.err = None
        self.t0 = 0.0                # inicio da geracao (relogio)
        self.done_ms = 0.0           # ms somados de geracao quando tudo ficou pronto
        self.stream_ok = {}          # trilha -> faixas em arquivo disponiveis
        self.stream = None           # trilha tocando em stream (pygame.mixer.music)
        self.pl_idx = {}             # trilha -> proxima faixa
        self.files = {}              # id -> [Sound] carregados de arquivo (variacoes de FILE_SFX)
        self.var_last = {}           # id -> indice da ultima variacao tocada
        self.vrng = random.Random(4242)   # sorteio das variacoes (nunca o random global)
        self.src = {}                # arquivo -> Sound carregado (fonte das variacoes derivadas)
        self.derived = {}            # (id, especificacao derivada) -> Sound
        self.names = {}              # id -> [arquivo de cada variacao carregada] (vozes faladas)
        self.bag = {}                # id -> indices ainda nao tocados nesta volta (saco embaralhado)
        self.spoke = {}              # arquivo falado -> instante em que tocou
        self.amb = None              # Sound do motor dos robos
        self.amb_chan = None         # canal reservado do motor
        self.amb_on = False


S = _State()
clock = time.perf_counter            # trocavel nos testes (throttle)
_mixer = None                        # pygame.mixer (import tardio)


def _pref(name, ok, dflt):
    try:
        v = prefs.get(name)
    except Exception:  # noqa: BLE001
        v = None
    return v if v in ok else dflt


def muted():
    return _pref("mute", ("0", "1"), "0") == "1"


def level(name):
    """Nivel "0".."3" de "sfx_vol" ou "music_vol" (prefs; invalido -> "2")."""
    return _pref(name, LEVEL_GAIN, "2")


def sfx_gain():
    return 0.0 if muted() else LEVEL_GAIN[level("sfx_vol")]


def music_gain(track=None):
    g = 0.0 if muted() else LEVEL_GAIN[level("music_vol")]
    return g * (MATCH_MUSIC_GAIN if (track or S.cur) == "match" else 1.0)


def toggle_mute():
    """Tecla M: mudo geral liga/desliga (gravado). Devolve True se ficou mudo."""
    nxt = "0" if muted() else "1"
    try:
        prefs.set("mute", nxt)
    except Exception:  # noqa: BLE001
        pass
    _apply_volumes()
    if nxt == "0":
        play("toggle")
    return nxt == "1"


def cycle(name):
    """Teclas S (efeitos) e N (musica): 0 -> 1 -> 2 -> 3 -> 0 (gravado). Devolve o novo nivel."""
    order = ("0", "1", "2", "3")
    nxt = order[(order.index(level(name)) + 1) % 4]
    try:
        prefs.set(name, nxt)
    except Exception:  # noqa: BLE001
        pass
    _apply_volumes()
    if name == "sfx_vol":
        play("toggle")
    return nxt


def labels():
    """(mudo, efeitos, musica) para a UI (Latin-1)."""
    return ("M: som " + ("MUDO" if muted() else "LIGADO"),
            "S: efeitos " + LEVEL_NAMES[level("sfx_vol")],
            "N: música " + LEVEL_NAMES[level("music_vol")])


def pre_init():
    """Antes de pygame.init(): pede MIXER_RATE (44,1 kHz) estereo 16-bit (o navegador pode impor outro)."""
    try:
        import pygame
        pygame.mixer.pre_init(MIXER_RATE, -16, 2, 2048 if WEB else 512)
    except Exception:  # noqa: BLE001
        pass


def init():
    """Abre o mixer e agenda a geracao dos sons. Falhou -> audio desligado (no-op silencioso)."""
    global _mixer
    S.__init__()
    try:
        import pygame
        mx = pygame.mixer
        if not mx.get_init():
            mx.init(MIXER_RATE, -16, 2, 2048 if WEB else 512)
        rate, size, chans = mx.get_init()
        if abs(size) == 16:
            kind = "h"
        elif abs(size) == 32:
            kind = "f"                      # AUDIO_F32 (comum no navegador)
        else:
            raise RuntimeError("formato de audio nao suportado: %r" % (size,))
        mx.set_num_channels(N_CHANNELS)
        mx.set_reserved(2)
        S.chan = mx.Channel(0)
        S.amb_chan = mx.Channel(1)
        S.fmt = (int(rate), max(1, int(chans)), kind)
        _mixer = mx
        S.stream_ok = {t: _stream_ok(t) for t in STREAMS}
        S.gen = _builder()
        S.t0 = time.perf_counter()
        S.ok = True
        _log("[som] mixer %r: gerando efeitos e trilhas" % (mx.get_init(),))
    except Exception as e:  # noqa: BLE001
        S.ok = False
        S.err = repr(e)
        _log("[som] desligado: %s" % S.err)
    return S.ok


def shutdown():
    """Volta ao estado inicial (testes)."""
    _stream_stop()
    try:
        if S.ok and _mixer is not None:
            _mixer.stop()                       # efeitos longos (gritos, vaias) nao seguram canais
        elif S.amb_chan is not None:
            S.amb_chan.stop()
    except Exception:  # noqa: BLE001
        pass
    S.__init__()


def _path(name):
    return os.path.join(AUDIO_DIR, name)


def _stream_ok(track):
    """True se as faixas da trilha existem e a primeira abre no mixer (formato suportado)."""
    try:
        names = STREAMS[track]
        if not all(os.path.isfile(_path(f)) for f in names):
            return False
        _mixer.music.load(_path(names[0]))
        return True
    except Exception as e:  # noqa: BLE001
        _log("[som] trilha %s em arquivo indisponivel: %r" % (track, e))
        return False


def _stream_next(track, gain):
    """Toca a proxima faixa da trilha (uma vez; music_tick emenda a seguinte quando acabar)."""
    names = STREAMS[track]
    i = S.pl_idx.get(track, 0)
    name = names[i % len(names)]
    S.pl_idx[track] = i + 1
    try:
        _mixer.music.load(_path(name))
        _mixer.music.set_volume(gain)
        _mixer.music.play(fade_ms=MUSIC_FADE_MS)
        S.stream = track
        return True
    except Exception as e:  # noqa: BLE001  (arquivo nao abriu: cai para a trilha sintetizada)
        _log("[som] trilha %s falhou (%s): %r" % (track, name, e))
        S.stream_ok[track] = False
        S.stream = None
        return False


def _stream_stop():
    """Para a trilha em stream NA HORA. Nunca usa music.fadeout: o SDL_mixer espera o fade terminar
    (laco com SDL_Delay) ao carregar/tocar a proxima faixa, e no navegador (sem thread de audio) essa
    espera nunca acaba e trava o jogo. A faixa seguinte entra com fade-in (MUSIC_FADE_MS)."""
    if not S.stream or _mixer is None:
        S.stream = None
        return
    try:
        _mixer.music.stop()
    except Exception:  # noqa: BLE001
        pass
    S.stream = None


def _load_file(sid):
    """Carrega as variacoes do efeito `sid` (FILE_SFX). Nenhuma abriu -> fica o sintetizado."""
    names, _thr, _voices, vol = FILE_SFX[sid]
    out, used = [], []
    for name in names:
        if not isinstance(name, str):
            continue                            # derivada: gerada depois (_derive)
        try:
            if os.path.isfile(_path(name)):
                snd = _mixer.Sound(_path(name))
                if snd.get_length() <= 0:       # nao decodificou (ex.: ogg 44,1 kHz num mixer de 22 kHz)
                    raise RuntimeError("arquivo vazio depois de decodificar")
                snd.set_volume(vol * sfx_gain())
                S.src.setdefault(name, snd)
                out.append(snd)
                used.append(name)
        except Exception as e:  # noqa: BLE001
            _log("[som] efeito %s em arquivo falhou: %r" % (name, e))
    if out:
        S.files[sid] = out
        S.names[sid] = used


def _source(name):
    """Sound da gravacao `name` (o carregado pelo FILE_SFX ou um novo). None se nao abrir."""
    snd = S.src.get(name)
    if snd is None:
        try:
            snd = _mixer.Sound(_path(name)) if os.path.isfile(_path(name)) else None
            if snd is not None and snd.get_length() <= 0:
                snd = None
        except Exception:  # noqa: BLE001
            snd = None
        S.src[name] = snd
    return snd


def derive_frames(src, speed, a, b, chans, rate, maxs=DERIVE_MAX_S, chunk=DERIVE_CHUNK, fade_s=DERIVE_FADE_S):
    """Gerador puro (sem pygame): `src` = array intercalado (chans canais). Reamostra o trecho [a, b) com
    passo `speed` (vizinho mais proximo; so o canal 0, copiado nos outros: as gravacoes sao mono),
    no maximo maxs segundos, com rampa de fade_s nas pontas. Cada yield = um pedaco; o ultimo valor
    gerado e o array pronto (use `for out in ...: pass`)."""
    frames = len(src) // chans
    f0 = max(0, min(frames - 1, int(frames * a)))
    f1 = max(f0 + 1, min(frames, int(frames * b)))
    n = max(1, min(int((f1 - f0) / speed), int(maxs * rate)))
    tc = src.typecode
    mono = array(tc, bytes(n * src.itemsize))
    j = 0
    while j < n:
        m = min(chunk, n - j)
        mono[j:j + m] = array(tc, [src[(f0 + int((j + i) * speed)) * chans] for i in range(m)])
        j += m
        if j < n:
            yield None
    fl = min(n // 4, int(fade_s * rate))
    conv = int if tc == "h" else float
    for i in range(fl):
        g = i / fl
        mono[i] = conv(mono[i] * g)
        mono[n - 1 - i] = conv(mono[n - 1 - i] * g)
    if chans == 1:
        yield mono
        return
    out = array(tc, bytes(n * chans * src.itemsize))
    for c in range(chans):
        out[c::chans] = mono
    yield out


def _derive(sid, spec):
    """Gera (aos poucos) a variacao derivada `spec` e a soma as variacoes de `sid`."""
    snd = S.derived.get((sid, spec))
    if snd is None:
        base = _source(spec[0])
        if base is None or not S.files.get(sid):
            return
        rate, chans, kind = S.fmt
        tc = "h" if kind == "h" else "f"
        raw = base.get_raw()
        step = array(tc).itemsize * chans
        src = array(tc)
        src.frombytes(raw[:len(raw) // step * step])
        if len(src) < chans * 8:
            return
        out = None
        maxs = spec[4] if len(spec) > 4 else DERIVE_MAX_S
        for out in derive_frames(src, spec[1], spec[2], spec[3], chans, rate, maxs):
            if out is None:
                yield
        snd = S.derived[(sid, spec)] = _mixer.Sound(buffer=out.tobytes())
    snd.set_volume(FILE_SFX[sid][3] * sfx_gain())
    S.files[sid].append(snd)
    S.names[sid].append(spec[0])
    yield


def n_variants(sid):
    """Quantas variacoes o id tem agora (gravadas + derivadas carregadas)."""
    return len(S.files.get(sid, ()))


def _pick_variant(sid, n):
    """Indice da variacao: "saco embaralhado" (RNG privado) -- toca todas antes de repetir e nunca a mesma
    duas vezes seguidas; voz falada (SPOKEN) so volta depois do seu intervalo."""
    if n <= 1:
        return 0
    names = S.names.get(sid) or ()
    last = S.var_last.get(sid)
    now = clock()

    def ok(k):
        nm = names[k] if k < len(names) else None
        t = S.spoke.get(nm)
        return nm not in SPOKEN or t is None or now - t >= SPOKEN[nm]

    bag = [k for k in S.bag.get(sid, ()) if k < n]
    if not any(k != last and ok(k) for k in bag):
        bag = list(range(n))                    # volta nova (variacoes derivadas entram aqui tambem)
    cand = [k for k in bag if k != last and ok(k)] or [k for k in range(n) if k != last] or [0]
    k = cand[S.vrng.randrange(len(cand))]
    bag.remove(k) if k in bag else None
    S.bag[sid] = bag
    S.var_last[sid] = k
    if k < len(names) and names[k] in SPOKEN:
        S.spoke[names[k]] = now
    return k


def _load_amb():
    try:
        if os.path.isfile(_path(AMB_FILE)):
            S.amb = _mixer.Sound(_path(AMB_FILE))
    except Exception as e:  # noqa: BLE001
        _log("[som] motor dos robos falhou: %r" % (e,))


def _build_sfx(sid):
    t = time.perf_counter()
    snd = _mixer.Sound(buffer=fit(render(sid), *S.fmt))
    S.sounds[sid] = snd
    snd.set_volume(SFX[sid][4] * sfx_gain())
    S.build_ms[sid] = (time.perf_counter() - t) * 1000
    return snd


def _builder():
    """Constroi tudo aos poucos (cada yield = um pedaco de poucos ms no desktop)."""
    import music
    for sid in UI_FIRST:
        if sid in FILE_SFX:
            _load_file(sid)                     # clique gravado: pronto ja no boot
        if sid not in S.sounds and sid not in S.files:
            _build_sfx(sid)
        yield
    for sid in FILE_SFX:
        if sid not in S.files:
            _load_file(sid)
            yield
    for sid, (variants, _t, _v, _g) in FILE_SFX.items():   # variacoes derivadas das gravacoes (runtime)
        for spec in variants:
            if isinstance(spec, str):
                continue
            try:
                yield from _derive(sid, spec)
            except Exception as e:  # noqa: BLE001  (sem a variacao: ficam as gravadas)
                _log("[som] variacao %s %r falhou: %r" % (sid, spec, e))
    S.src.clear()                               # fontes so de derivadas (ex.: ole2 de 14 s) saem da memoria
    _load_amb()
    yield
    need = {SYNTH_TRACK[t] for t in STREAMS if not S.stream_ok.get(t)}   # so as trilhas sem arquivo
    replaced = {k for k in S.files if k not in FILE_LAYER}              # gravado substitui
    order = ([t for t in ("menu",) if t in need]
             + [k for k in SFX if k not in UI_FIRST and k not in replaced]
             + [t for t in ("match",) if t in need] + ["win", "lose"])
    for sid in order:
        if sid in S.sounds:
            continue
        if sid in SFX:
            _build_sfx(sid)
            yield
            continue
        t, parts = 0.0, []
        it = music.render_chunks(sid)
        while True:
            t0 = time.perf_counter()
            try:
                chunk = next(it)
            except StopIteration:
                break
            if chunk is not None:
                parts.append(fit(chunk, *S.fmt))
            t += time.perf_counter() - t0
            yield
        t0 = time.perf_counter()
        S.sounds[sid] = _mixer.Sound(buffer=b"".join(parts))
        S.build_ms[sid] = (t + time.perf_counter() - t0) * 1000
        _apply_volumes()
        yield


def pump(budget_ms=PUMP_MS):
    """Avanca a construcao ate gastar budget_ms. True quando tudo esta pronto."""
    if S.gen is None:
        return True
    t0 = time.perf_counter()
    try:
        while (time.perf_counter() - t0) * 1000 < budget_ms:
            next(S.gen)
    except StopIteration:
        S.gen = None
        S.done_ms = sum(S.build_ms.values())
        _log("[som] pronto: %d sons, %.0f ms de geracao (%.1f s de relogio)"
              % (len(S.sounds), S.done_ms, time.perf_counter() - S.t0))
        return True
    except Exception as e:  # noqa: BLE001  (falha na geracao: desliga o audio)
        S.err = repr(e)
        S.gen = None
        S.ok = False
    return S.gen is None


def ready(sid):
    return sid in S.sounds


def play(sid):
    """Toca o efeito `sid` (throttle por id, limite de vozes, volume das prefs). Nunca levanta."""
    if not S.ok:
        return False
    variants = S.files.get(sid)
    if not variants and sid in SYNTH_ALIAS:
        sid = SYNTH_ALIAS[sid]
        variants = S.files.get(sid)
    spec = SFX.get(sid)
    if spec is None and not variants:
        return False
    try:
        now = clock()
        last = S.last.get(sid)
        thr = FILE_SFX[sid][1] if variants else spec[2]
        if last is not None and now - last < thr:
            return False
        if sfx_gain() <= 0.0:
            return False
        ok = False
        if variants and sum(v.get_num_channels() for v in variants) < FILE_SFX[sid][2]:
            ok = variants[_pick_variant(sid, len(variants))].play() is not None
        if spec is not None and (not variants or sid in FILE_LAYER):
            snd = S.sounds.get(sid)
            if snd is None:
                snd = _build_sfx(sid)           # ainda nao gerado: gera agora (poucos ms)
            if snd.get_num_channels() < spec[3]:
                ok = (snd.play() is not None) or ok
        if ok:
            S.last[sid] = now
        return ok
    except Exception as e:  # noqa: BLE001
        S.err = repr(e)
        return False


def stop(sids, fade_ms=250):
    """Corta (fade curto) os efeitos `sids` que ainda estejam tocando (ex.: grito de gol no reinicio).
    Sound.fadeout e por canal e nao bloqueia (diferente de music.fadeout). Nunca levanta."""
    if not S.ok:
        return 0
    n = 0
    try:
        for sid in sids:
            for snd in S.files.get(sid, ()):
                if snd.get_num_channels():
                    snd.fadeout(fade_ms)
                    n += 1
            snd = S.sounds.get(sid)
            if snd is not None and snd.get_num_channels():
                snd.fadeout(fade_ms)
                n += 1
    except Exception as e:  # noqa: BLE001
        S.err = repr(e)
    return n


def jingle(jid):
    """Jingle ("win"/"lose") no canal da musica; depois a trilha pedida volta sozinha."""
    if not S.ok or S.chan is None:
        return False
    try:
        snd = S.sounds.get(jid)
        g = 0.0 if muted() else max(LEVEL_GAIN[level("music_vol")], LEVEL_GAIN[level("sfx_vol")])
        if snd is None or g <= 0.0:
            return False
        S.chan.stop()
        S.chan.set_volume(g)
        S.chan.play(snd)
        S.jingle = True
        S.cur = jid
        return True
    except Exception as e:  # noqa: BLE001
        S.err = repr(e)
        return False


def result(mine, theirs):
    """Fim de partida do ponto de vista do jogador: vitoria/derrota = jingle, empate = efeito."""
    try:
        a, b = int(mine), int(theirs)
    except (TypeError, ValueError):
        return False
    if a == b:
        return play("draw")
    return jingle("win" if a > b else "lose")


def _apply_volumes():
    if not S.ok:
        return
    try:
        g = sfx_gain()
        for sid, spec in SFX.items():
            snd = S.sounds.get(sid)
            if snd is not None:
                snd.set_volume(spec[4] * g)
        for sid, snds in S.files.items():
            for snd in snds:
                snd.set_volume(FILE_SFX[sid][3] * g)
        if S.amb_chan is not None:
            if g <= 0.0:
                S.amb_chan.stop()
                S.amb_on = False
            else:
                S.amb_chan.set_volume(AMB_VOL * g)
        if S.stream:
            mg = music_gain(S.stream)
            if mg <= 0.0:
                _stream_stop()
            else:
                _mixer.music.set_volume(mg)
        if S.chan is not None and not S.jingle:
            mg = music_gain()
            if mg <= 0.0 and S.cur is not None:
                S.chan.stop()
                S.cur = None
            else:
                S.chan.set_volume(mg)
    except Exception as e:  # noqa: BLE001
        S.err = repr(e)


def music_tick(track):
    """Trilha pedida neste quadro ("menu", "sub", "cups", "match" ou None). Em arquivo: stream com as
    faixas em ciclo; sem arquivo: a trilha sintetizada equivalente no canal 0. Troca so quando muda."""
    S.want = track
    mg = music_gain(track) if track else 0.0
    want_stream = track if (track in STREAMS and S.stream_ok.get(track)) else None
    want_synth = None if (want_stream or not track) else SYNTH_TRACK.get(track, track)
    if mg <= 0.0 or S.stream != want_stream:
        if S.stream:
            _stream_stop()
        if want_stream and mg > 0.0 and not _stream_next(want_stream, mg):
            want_synth = SYNTH_TRACK.get(track, track)          # arquivo nao abriu agora
    elif S.stream and not _mixer.music.get_busy():
        _stream_next(S.stream, mg)                  # faixa acabou: emenda a proxima
    if S.jingle:
        if S.chan.get_busy():
            return
        S.jingle = False
        S.cur = None
    if want_synth == S.cur:
        return
    snd = S.sounds.get(want_synth) if want_synth else None
    if want_synth and snd is None:
        if S.cur is not None:                       # ainda gerando: a anterior nao fica tocando
            S.chan.fadeout(MUSIC_FADE_MS)
            S.cur = None
        return
    if want_synth is None or mg <= 0.0:
        if S.cur is not None:
            S.chan.fadeout(MUSIC_FADE_MS)
            S.cur = None
        return
    S.chan.set_volume(mg)
    S.chan.play(snd, loops=-1, fade_ms=MUSIC_FADE_MS)
    S.cur = want_synth


def amb_tick(on):
    """Motor dos robos em loop no canal 1 enquanto `on` (bola rolando); fade ao parar."""
    if S.amb is None or S.amb_chan is None:
        return
    g = sfx_gain()
    if on and g > 0.0:
        if not S.amb_on:
            S.amb_chan.set_volume(AMB_VOL * g)
            S.amb_chan.play(S.amb, loops=-1, fade_ms=AMB_FADE_MS)
            S.amb_on = True
    elif S.amb_on:
        S.amb_chan.fadeout(AMB_FADE_MS)
        S.amb_on = False


def tick(track, amb=False):
    """1x por quadro (loop principal): geracao em segundo plano + musica + motor. Nunca levanta."""
    if not S.ok:
        return
    try:
        if S.gen is not None:
            pump()
        music_tick(track)
        amb_tick(amb)
    except Exception as e:  # noqa: BLE001
        S.err = repr(e)
