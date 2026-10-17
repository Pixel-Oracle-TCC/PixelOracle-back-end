#!/usr/bin/env bash
# Restaura um dump gerado por scripts/db-export.sh no Postgres local do projeto.
#
# ATENÇÃO: apaga e recria o banco de destino — os dados locais são substituídos pelos do dump.
#
# Uso: ./scripts/db-import.sh [arquivo.dump] [--yes]
#      sem arquivo, usa o .dump mais recente de dumps/

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER="${PIXEL_DB_CONTAINER:-pixel-oracle-db}"
DB_USER="pixel"
DB_NAME="${PIXEL_DB_NAME:-pixeloracle}"
DUMP_FILE=""
ASSUME_YES=false

for arg in "$@"; do
  case "$arg" in
    --yes|-y) ASSUME_YES=true ;;
    *) DUMP_FILE="$arg" ;;
  esac
done

if [[ -z "$DUMP_FILE" ]]; then
  DUMP_FILE="$(ls -t "${ROOT}"/dumps/*.dump 2>/dev/null | head -1 || true)"
fi
if [[ -z "$DUMP_FILE" || ! -f "$DUMP_FILE" ]]; then
  echo "❌ Dump não encontrado. Uso: ./scripts/db-import.sh caminho/para/pixeloracle_XXXX.dump" >&2
  exit 1
fi

cd "$ROOT"
if [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" != "true" ]]; then
  echo "🐳 Subindo o banco (docker compose up -d db)..."
  docker compose up -d db >/dev/null
fi
until docker exec "$CONTAINER" pg_isready -U "$DB_USER" -q 2>/dev/null; do sleep 1; done

if ! $ASSUME_YES; then
  read -r -p "⚠️  Isso substitui o banco '${DB_NAME}' local por '$(basename "$DUMP_FILE")'. Continuar? [s/N] " answer
  [[ "$answer" =~ ^[sSyY]$ ]] || { echo "Cancelado."; exit 0; }
fi

admin() { docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -q -c "$1"; }

echo "🗑️  Recriando ${DB_NAME}..."
admin "DROP DATABASE IF EXISTS \"$DB_NAME\" WITH (FORCE);"
admin "CREATE DATABASE \"$DB_NAME\" OWNER $DB_USER;"

echo "📥 Restaurando $(basename "$DUMP_FILE")..."
docker exec -i "$CONTAINER" pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl --exit-on-error < "$DUMP_FILE"

echo "📊 Conteúdo restaurado:"
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At -F ' | ' -c "
  SELECT 'games', count(*) FROM games UNION ALL
  SELECT 'reviews', count(*) FROM reviews UNION ALL
  SELECT 'review_aspects', count(*) FROM review_aspects UNION ALL
  SELECT 'themes', count(*) FROM themes UNION ALL
  SELECT 'theme_stats', count(*) FROM theme_stats UNION ALL
  SELECT 'genre_drivers', count(*) FROM genre_drivers;" | sed 's/^/   /'

echo "✅ Banco restaurado. Se o ml-service estiver rodando: docker compose restart ml-service"
