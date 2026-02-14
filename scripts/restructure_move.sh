#!/usr/bin/env bash
set -e

echo "Iniciando reorganización: mover archivos a backend/ y frontend/ usando git mv (si es posible)..."

mkdir -p backend frontend

# Intentar mover con git mv para conservar historial cuando sea posible
mv_or_git() {
  if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    git mv -k "$1" "$2" 2>/dev/null || mv -v "$1" "$2"
  else
    mv -v "$1" "$2"
  fi
}

# Archivos y carpetas backend
for p in asgi.py run.py entrypoint.sh populate_datos.py requirements.txt Dockerfile; do
  if [ -e "$p" ]; then
    mv_or_git "$p" backend/
  fi
done

for d in bunkerlabs dockerlabs database; do
  if [ -e "$d" ]; then
    mv_or_git "$d" backend/
  fi
done

# Mover frontend (assets + plantillas) al frontend/
for p in templates static; do
  if [ -e "$p" ]; then
    mv_or_git "$p" frontend/
  fi
done

echo "Reorganización completada. Revisa cambios con 'git status' y ajusta imports/rutas si es necesario."
