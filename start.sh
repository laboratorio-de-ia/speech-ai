#!/usr/bin/env bash
# ====================================================
#  Speech AI - Inicia o frontend
# ----------------------------------------------------
#  Uso:
#    ./start.sh                  -> http://127.0.0.1:8000 (abre o navegador)
#    ./start.sh --port 8080      -> outra porta
#    ./start.sh --no-browser     -> não abre o navegador
#
#  Para encerrar: Ctrl+C
# ====================================================

set -e

# Sempre roda a partir da raiz do projeto, de onde quer que seja chamado.
cd "$(dirname "$0")"

if command -v python >/dev/null 2>&1; then
    PYTHON=python
elif command -v py >/dev/null 2>&1; then
    PYTHON=py
else
    echo "Python não encontrado no PATH." >&2
    exit 1
fi

export PYTHONIOENCODING=utf-8

exec "$PYTHON" -m web "$@"
