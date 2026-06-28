#!/usr/bin/env bash
set -e
SOURCE="${1:-codigos pagina}"
TARGET="${2:-www}"

echo "Sincronizando contenido de '$SOURCE' a '$TARGET'..."
mkdir -p "$TARGET"

rsync -av --delete \
  --exclude "android" \
  --exclude "ios" \
  --exclude "node_modules" \
  --exclude "storage" \
  --exclude ".git" \
  --exclude ".next" \
  --exclude ".out" \
  --exclude ".cache" \
  "$SOURCE"/ "$TARGET"/

echo "Sync completado."

