#!/usr/bin/env bash
# Normaliza os audios do jogo: compactos e com o mesmo volume (regra do dono).
#
# Uso (da raiz do repo):
#   tools/normalizar_audio.sh <pasta_de_entrada> [pasta_de_saida]     (saida padrao: game/audio)
#
# Para cada .ogg/.wav/.mp3/.flac da entrada (menos as copias "*-pygbag.*" do build) grava <nome>.ogg na saida:
#   - efeitos (o resto): vorbis MONO 44,1 kHz q3, silencio do inicio cortado (silenceremove) e
#     loudnorm I=-16 LUFS / TP=-1,5 dBTP;
#   - musicas e torcida de fundo (MUSIC, tocadas em stream por pygame.mixer.music, que reamostra sem
#     problema): vorbis MONO 22,05 kHz q2, sem cortar silencio, loudnorm I=-20 (fundo: nao briga com os
#     efeitos);
#   - loop do motor dos robos (LOOPS): MONO 44,1 kHz q2, sem cortar silencio, I=-20. 44,1 kHz porque e um
#     Sound (Sound de 22 kHz/44 kHz convertido pelo SDL_mixer do desktop ja voltou vazio).
# Depois apaga a copia "<nome>-pygbag.ogg" da saida: o pygbag so converte de novo quando ela nao existe
# (com a copia velha, o game.apk levaria o som antigo). Precisa de ffmpeg com libvorbis.
set -euo pipefail

IN="${1:?uso: tools/normalizar_audio.sh <pasta_de_entrada> [pasta_de_saida]}"
OUT="${2:-game/audio}"
MUSIC="menu1 menu2 menu3 copas interno1 interno2 submenus torcida torcida_boca torcida_estadio partida_musica"
LOOPS="robo_motor"
mkdir -p "$OUT"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

has() { case " $1 " in *" $2 "*) return 0 ;; *) return 1 ;; esac; }

n=0
for src in "$IN"/*.ogg "$IN"/*.wav "$IN"/*.mp3 "$IN"/*.flac; do
    [ -f "$src" ] || continue
    base="$(basename "$src")"
    name="${base%.*}"
    case "$name" in *-pygbag) continue ;; esac
    if has "$MUSIC" "$name"; then
        filt="loudnorm=I=-20:TP=-1.5:LRA=11"; rate=22050; q=2
    elif has "$LOOPS" "$name"; then
        filt="loudnorm=I=-20:TP=-1.5:LRA=11"; rate=44100; q=2
    else
        filt="silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.02,loudnorm=I=-16:TP=-1.5:LRA=11"
        rate=44100; q=3
    fi
    ffmpeg -nostdin -v error -y -i "$src" -map_metadata -1 -vn -af "$filt" -ac 1 -ar "$rate" \
        -c:a libvorbis -q:a "$q" "$TMP/$name.ogg"
    mv "$TMP/$name.ogg" "$OUT/$name.ogg"
    rm -f "$OUT/$name-pygbag.ogg"
    printf '%-22s %8d bytes  (%s Hz, q%s)\n' "$name.ogg" "$(stat -c %s "$OUT/$name.ogg")" "$rate" "$q"
    n=$((n + 1))
done
echo "$n arquivos normalizados em $OUT"
