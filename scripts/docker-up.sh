#!/usr/bin/env bash
# Sobe ML + API principal com Docker Compose (verifica artefatos do modelo antes).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT="${ROOT}/ml-service/artifacts/modelo_rf.pkl"

if [[ ! -f "$ARTIFACT" ]]; then
  echo "❌ Artefato não encontrado: $ARTIFACT"
  echo ""
  echo "Gere o modelo antes do Docker:"
  echo "  cd ml-service"
  echo "  python3 -m venv .venv && source .venv/bin/activate"
  echo "  pip install -r requirements.txt"
  echo "  python ml/train.py"
  exit 1
fi

if [[ ! -f "${ROOT}/.env" ]] && [[ -f "${ROOT}/.env.example" ]]; then
  echo "ℹ️  Dica: cp .env.example .env e configure GEMINI_API_KEY (opcional)"
fi

cd "$ROOT"
docker compose up --build "$@"
