#!/usr/bin/env bash
# Sobe Postgres + ML + API principal com Docker Compose.
# O dashboard depende do pipeline de reviews (coleta → ABSA → temas → métricas → drivers);
# ver DOCKER.md para a ordem dos scripts.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "${ROOT}/.env" ]] && [[ -f "${ROOT}/.env.example" ]]; then
  echo "ℹ️  Dica: cp .env.example .env e configure GEMINI_API_KEY (opcional)"
fi

cd "$ROOT"
docker compose up --build "$@"
