#!/usr/bin/env bash
set -euo pipefail

if ! command -v pkg >/dev/null 2>&1; then
    echo "Este script está pensado para Termux (no se encontró pkg)." >&2
    exit 1
fi

pkg update -y
pkg install -y python git

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Se creó .env desde .env.example. Completá tokens y configuración."
fi

mkdir -p data logs
chmod +x scripts/*.sh

# Para el respaldo automático en Termux:
#   pkg install cronie termux-services
#   sv-enable crond
#   crontab -e
#   (agregar la línea de scripts/backup.sh documentada en docs/despliegue.md)

echo "Instalación lista. Editá .env y ejecutá scripts/start.sh."
