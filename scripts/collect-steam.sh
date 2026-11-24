#!/usr/bin/env bash
# Coleta Steam em série, gravando no Postgres do docker-compose.collect.yml.
# COLLECT_LIMIT é o teto de jogos que ainda não têm review (padrão 400).
# Não chama a Gemini e não carrega o modelo de embedding.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LIMIT="${COLLECT_LIMIT:-400}"
COMPOSE=(docker compose -f docker-compose.collect.yml --profile collect)

if ! "${COMPOSE[@]}" exec -T db pg_isready -U pixel -d pixeloracle >/dev/null 2>&1; then
  "${COMPOSE[@]}" up -d db
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    "${COMPOSE[@]}" exec -T db pg_isready -U pixel -d pixeloracle && break
    sleep 3
  done
fi

echo "Catálogo: até ${LIMIT} jogos novos do top sellers."
"${COMPOSE[@]}" run --rm collect python scripts/collect_top_games.py --limit "$LIMIT"

echo "Metadados dos jogos que ainda faltam."
"${COMPOSE[@]}" run --rm collect python scripts/enrich_games.py

echo "Reviews: até ${LIMIT} jogos ainda sem coleta."
"${COMPOSE[@]}" run --rm collect python scripts/collect_reviews.py --all-games --limit-games "$LIMIT"

echo "Coleta encerrada."
