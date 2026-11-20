#!/usr/bin/env bash
set -euo pipefail

PROYECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! git -C "$PROYECTO" rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "No estás dentro de un repositorio git." >&2
    exit 1
fi

REPO="$(git -C "$PROYECTO" rev-parse --show-toplevel)"
DESTINO="$REPO/dist"
mkdir -p "$DESTINO"

FECHA="$(date +%Y%m%d-%H%M)"
ARCHIVO="$DESTINO/gastosBot-termux-$FECHA.tar.gz"

tar -czf "$ARCHIVO" \
    -C "$REPO" \
    --exclude='Desarrollo/.env' \
    --exclude='Desarrollo/.venv' \
    --exclude='Desarrollo/venv' \
    --exclude='Desarrollo/data' \
    --exclude='Desarrollo/logs' \
    --exclude='Desarrollo/bot.pid' \
    --exclude='Desarrollo/.pytest_cache' \
    --exclude='Desarrollo/.coverage' \
    --exclude='Desarrollo/htmlcov' \
    --exclude='Desarrollo/__pycache__' \
    --exclude='*/__pycache__' \
    --exclude='*.pyc' \
    --exclude='Desarrollo/tests/fixtures/*.png' \
    --exclude='Desarrollo/tests/fixtures/*.pdf' \
    --exclude='Desarrollo/tests/fixtures/*.jpg' \
    --exclude='Desarrollo/tests/fixtures/*.jpeg' \
    --exclude='Desarrollo/tests/fixtures/*.webp' \
    README.md Desarrollo

echo "Paquete listo: $ARCHIVO"
echo "Tamaño: $(du -h "$ARCHIVO" | cut -f1)"
echo "Recordá transferir el .env por separado (no se incluye por seguridad)."
