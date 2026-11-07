#!/usr/bin/env bash
# Versiona os pacotes do jogo no index.html do build (cache busting):
#   "game.apk" -> "game.apk?v=<versao>"  e  "game.tar.gz" -> "game.tar.gz?v=<versao>"
# Cada deploy pede uma URL nova, entao nem o Cloudflare nem o navegador servem o pacote antigo.
# A versao padrao e o sha256 curto do game.apk (muda so quando o jogo muda).
#
# Uso (da raiz do repo, depois do build do pygbag):
#   tools/versionar_build.sh [pasta_do_build]          (padrao: game/build/web)
set -euo pipefail

DIR="${1:-game/build/web}"
IDX="$DIR/index.html"
[ -f "$IDX" ] && [ -f "$DIR/game.apk" ] || { echo "build nao encontrado em $DIR" >&2; exit 1; }
VER="$(sha256sum "$DIR/game.apk" | cut -c1-12)"
# idempotente: remove versao anterior antes de aplicar a nova
sed -i -E "s/\"game\.(apk|tar\.gz)(\?v=[0-9a-f]+)?\"/\"game.\1?v=$VER\"/g" "$IDX"
n="$(grep -c "?v=$VER\"" "$IDX" || true)"
[ "$n" -ge 1 ] || { echo "nenhuma referencia versionada em $IDX" >&2; exit 1; }
echo "index.html versionado: v=$VER ($n referencias)"
