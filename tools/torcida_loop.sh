#!/usr/bin/env bash
# Torcida de fundo da partida em LOOP SEM EMENDA (Sound em loop num canal reservado; ver game/sfx.py BED_FILE).
#
# Uso (da raiz do repo):
#   tools/torcida_loop.sh <pasta_com_torcida*.ogg> [saida]        (saida padrao: game/audio/torcida_loop.ogg)
#
# Entrada: as 3 gravacoes de torcida ja normalizadas (-20 LUFS; tools/normalizar_audio.sh, lista MUSIC):
# torcida.ogg, torcida_estadio.ogg e torcida_boca.ogg (estao no historico do git, commit 3d6d029, se sairem de
# game/audio). Mistura os trechos mais estaveis das tres (a do canto "boca" mais baixa), com LOOP_S segundos
# de loop e XFADE_S de crossfade de potencia constante entre o fim e o comeco (o fim do arquivo emenda no
# comeco sem clique nem salto de volume). Ganho ESTATICO depois (medido em 2 passadas) para -20 LUFS: o
# loudnorm dinamico mudaria o ganho ao longo do arquivo e a emenda apareceria.
# Saida: vorbis MONO 44,1 kHz q2 (Sound: mesma regra do robo_motor; 22 kHz convertido pelo SDL_mixer do
# desktop ja voltou vazio). Decodificado no mixer (44,1 kHz estereo 16-bit) ocupa ~172 KB/s: 24 s = ~4,1 MB.
# Depois apaga a copia "<nome>-pygbag.ogg" (o pygbag so reconverte quando ela nao existe).
set -euo pipefail

IN="${1:?uso: tools/torcida_loop.sh <pasta_com_torcida*.ogg> [saida]}"
OUT="${2:-game/audio/torcida_loop.ogg}"
# loop com N quadros MULTIPLO DE 2048: o libvorbis do ffmpeg completa o ultimo bloco com silencio (24 s exatos
# decodificavam com 32 quadros a mais e o loop dava um clique na emenda). 517 x 2048 = 1.058.816 = ~24,01 s.
N=$((517 * 2048))
XFADE_S=3
XS=$((XFADE_S * 44100))
LOOP_S=24
SEG=$((LOOP_S + XFADE_S + 1))
# (arquivo, inicio s, peso): trechos de menor variacao de volume (medidos por RMS de 1 s)
A="$IN/torcida.ogg";         A0=14; AW=0.75
B="$IN/torcida_estadio.ogg"; B0=12; BW=0.75
C="$IN/torcida_boca.ogg";    C0=0;  CW=0.30
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1) mistura dos 3 trechos (44,1 kHz mono; o amix divide por 3, o ganho estatico do passo 3 compensa)
ffmpeg -nostdin -v error -y -ss "$A0" -t "$SEG" -i "$A" -ss "$B0" -t "$SEG" -i "$B" -ss "$C0" -t "$SEG" -i "$C" \
    -filter_complex "[0:a]aresample=44100,volume=$AW[a];[1:a]aresample=44100,volume=$BW[b];[2:a]aresample=44100,volume=$CW[c];[a][b][c]amix=inputs=3:duration=shortest" \
    -ac 1 -ar 44100 -c:a pcm_s16le "$TMP/mix.wav"
# 2) loop: [XS, XS + N) com o fim cruzado (sai) sobre o comeco [0, XS) (entra) -> N quadros sem emenda
ffmpeg -nostdin -v error -y -i "$TMP/mix.wav" -i "$TMP/mix.wav" -filter_complex \
    "[0:a]atrim=start_sample=$XS:end_sample=$((XS + N)),asetpts=PTS-STARTPTS[body];[1:a]atrim=end_sample=$XS,asetpts=PTS-STARTPTS[head];[body][head]acrossfade=ns=$XS:c1=qsin:c2=qsin" \
    -c:a pcm_s16le "$TMP/loop.wav"
# 3) ganho estatico para -20 LUFS (integrado medido na passada 1)
I=$(ffmpeg -nostdin -hide_banner -i "$TMP/loop.wav" -af loudnorm=I=-20:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 \
    | sed -n 's/.*"input_i" : "\(-*[0-9.]*\)".*/\1/p')
GAIN=$(awk -v i="$I" 'BEGIN { printf "%.2f", -20 - i }')
mkdir -p "$(dirname "$OUT")"
ffmpeg -nostdin -v error -y -i "$TMP/loop.wav" -map_metadata -1 -af "volume=${GAIN}dB" \
    -ac 1 -ar 44100 -c:a libvorbis -q:a 2 "$TMP/out.ogg"
mv "$TMP/out.ogg" "$OUT"
rm -f "${OUT%.ogg}-pygbag.ogg"
printf '%s: %d bytes, %ss de loop, integrado antes %s LUFS, ganho %s dB\n' "$OUT" "$(stat -c %s "$OUT")" "$LOOP_S" "$I" "$GAIN"
