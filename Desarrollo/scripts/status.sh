#!/usr/bin/env bash
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

if [ -f bot.pid ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
    echo "Bot corriendo (PID $(cat bot.pid))."
else
    echo "Bot detenido."
fi

if [ -f data/gastos.db ]; then
    echo "Base: $(du -h data/gastos.db | cut -f1)"
else
    echo "Base: no creada."
fi

if [ -f logs/bot.log ]; then
    echo "Última línea del log:"
    tail -n 1 logs/bot.log
fi
