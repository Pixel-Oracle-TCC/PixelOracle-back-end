#!/usr/bin/env bash
# Exporta o banco do Pixel Oracle para compartilhar com o grupo.
#
# Gera dumps/pixeloracle_<data>.dump (formato custom do pg_dump, comprimido; restaura com
# scripts/db-import.sh). Com --csv, gera também dumps/csv_<data>/ com uma planilha por tabela,
# sem as colunas de embedding (vetores não são legíveis em planilha).
#
# Nenhuma tabela guarda identificador de autor de review (ToS Steam + LGPD), então o dump
# pode circular no grupo. Ele não contém chaves de API (.env fica fora do banco).
#
# Uso: ./scripts/db-export.sh [--csv]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER="${PIXEL_DB_CONTAINER:-pixel-oracle-db}"
DB_USER="pixel"
DB_NAME="${PIXEL_DB_NAME:-pixeloracle}"
OUT_DIR="${ROOT}/dumps"
STAMP="$(date +%Y%m%d_%H%M)"
WITH_CSV=false

for arg in "$@"; do
  case "$arg" in
    --csv) WITH_CSV=true ;;
    *) echo "Argumento desconhecido: $arg" >&2; exit 1 ;;
  esac
done

if [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" != "true" ]]; then
  echo "❌ Container $CONTAINER não está rodando. Suba com: docker compose up -d db" >&2
  exit 1
fi

psql_exec() {
  docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -At "$@"
}

mkdir -p "$OUT_DIR"
DUMP_FILE="${OUT_DIR}/pixeloracle_${STAMP}.dump"

echo "📦 Exportando $DB_NAME → $DUMP_FILE"
docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc --no-owner --no-acl > "$DUMP_FILE"

echo "📊 Conteúdo:"
psql_exec -F ' | ' -c "
  SELECT 'games', count(*) FROM games UNION ALL
  SELECT 'reviews', count(*) FROM reviews UNION ALL
  SELECT 'review_aspects', count(*) FROM review_aspects UNION ALL
  SELECT 'themes', count(*) FROM themes UNION ALL
  SELECT 'theme_stats', count(*) FROM theme_stats UNION ALL
  SELECT 'genre_drivers', count(*) FROM genre_drivers;" | sed 's/^/   /'

if $WITH_CSV; then
  CSV_DIR="${OUT_DIR}/csv_${STAMP}"
  mkdir -p "$CSV_DIR"
  echo "🧾 CSVs → $CSV_DIR"
  for table in games genres game_genres categories game_categories developers game_developers publishers game_publishers languages game_languages reviews review_aspects review_snapshots themes theme_stats genre_drivers absa_gold_standard apps_ignorados; do
    cols="$(psql_exec -c "
      SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position)
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = '${table}' AND udt_name <> 'vector';")"
    [[ -z "$cols" ]] && continue
    psql_exec -c "COPY (SELECT ${cols} FROM ${table} ORDER BY 1) TO STDOUT WITH CSV HEADER" \
      > "${CSV_DIR}/${table}.csv"
    echo "   ${table}.csv"
  done
fi

echo "✅ Pronto ($(du -h "$DUMP_FILE" | cut -f1)). Envie o arquivo .dump ao grupo; para restaurar:"
echo "   ./scripts/db-import.sh dumps/$(basename "$DUMP_FILE")"
