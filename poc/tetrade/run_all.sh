#!/usr/bin/env bash
# Repete as provas automáticas da Tétrade. Não treina transformer e não anota review.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="${ROOT}/ml-service/.venv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "Crie o venv em ml-service." >&2
  exit 1
fi

cd "$ROOT"
"$PY" poc/tetrade/01-dados/run.py
"$PY" poc/tetrade/02-regra-do-rotulo/run.py
"$PY" poc/tetrade/03-divisao-por-jogo/run.py
"$PY" poc/tetrade/04-piso-sem-rede/run.py
"$PY" poc/tetrade/05-ajuste-fino/run.py
"$PY" poc/tetrade/06-onde-erra/run.py
"$PY" poc/tetrade/07-textos-dificeis/run.py

echo "Provas automáticas da Tétrade concluídas. A anotação humana fica fora deste script."
