#!/usr/bin/env bash
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

if [ ! -f bot.pid ]; then
    echo "No hay bot.pid; el bot no está corriendo (o no se inició con scripts/start.sh)."
    exit 0
fi

PID="$(cat bot.pid)"
if ! kill -0 "$PID" 2>/dev/null; then
    echo "El proceso $PID no está corriendo."
    rm -f bot.pid
    exit 0
fi

kill "$PID"
for _ in 1 2 3 4 5; do
    if ! kill -0 "$PID" 2>/dev/null; then
        break
    fi
    sleep 1
done

if kill -0 "$PID" 2>/dev/null; then
    echo "El proceso no terminó; enviando SIGKILL."
    kill -9 "$PID" 2>/dev/null || true
fi

rm -f bot.pid
echo "Bot detenido (PID $PID)."
