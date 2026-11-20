#!/usr/bin/env bash
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

PYTHON="$RAIZ/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON="$(command -v python3 || command -v python || true)"
fi
if [ -z "${PYTHON:-}" ]; then
    echo "No se encontró Python. Creá el venv con scripts/install_termux.sh." >&2
    exit 1
fi

mkdir -p logs data

if [ -f bot.pid ]; then
    PID="$(cat bot.pid)"
    if kill -0 "$PID" 2>/dev/null; then
        echo "El bot ya está corriendo (PID $PID)."
        exit 0
    fi
    rm -f bot.pid
fi

# main.py ya escribe logs/bot.log con rotación; acá se guarda la salida cruda.
nohup "$PYTHON" main.py >> logs/nohup.log 2>&1 &
PID=$!
echo "$PID" > bot.pid
sleep 1

if kill -0 "$PID" 2>/dev/null; then
    echo "Bot iniciado (PID $PID)."
    echo "Log interno: logs/bot.log · salida: logs/nohup.log"
else
    echo "El bot no quedó corriendo. Revisá logs/nohup.log." >&2
    rm -f bot.pid
    exit 1
fi
