#!/usr/bin/env bash
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "No estás dentro de un repositorio git." >&2
    exit 1
fi

REPO="$(git rev-parse --show-toplevel)"

# Copia local consistente de la base (no se versiona; data/ está ignorado).
PYTHON="$RAIZ/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON="$(command -v python3 || command -v python || true)"
fi
if [ -n "${PYTHON:-}" ] && [ -f "$RAIZ/data/gastos.db" ]; then
    mkdir -p "$RAIZ/data/backups"
    DESTINO_DB="$RAIZ/data/backups/gastos-$(date +%Y-%m-%d).db"
    "$PYTHON" - "$RAIZ/data/gastos.db" "$DESTINO_DB" <<'PY'
import sqlite3
import sys

origen, destino = sys.argv[1], sys.argv[2]
with sqlite3.connect(origen) as src, sqlite3.connect(destino) as dst:
    src.backup(dst)
PY
    echo "Copia local de la base: $DESTINO_DB"
fi

cd "$REPO"

git add -A
if git diff --cached --quiet; then
    echo "Sin cambios para respaldar."
    exit 0
fi

FECHA="$(date +%Y-%m-%d_%H-%M-%S)"
git commit -m "backup: $FECHA"
git push origin main
echo "Respaldo completado: $FECHA"
