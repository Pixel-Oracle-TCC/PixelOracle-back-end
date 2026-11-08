#!/usr/bin/env bash
# Roda na EC2, depois que o GitHub enviou o código e o .env.
# Sobe o Postgres, aplica o schema e, se RUN_COLLECT=true, coleta o lote.
set -euo pipefail

cd /opt/pixel-oracle
bash scripts/bootstrap-collect-host.sh

sudo docker compose -f docker-compose.collect.yml --profile collect up -d db
sudo docker compose -f docker-compose.collect.yml --profile collect build collect
sudo docker compose -f docker-compose.collect.yml --profile collect run --rm collect \
  python scripts/apply_schema.py

if [ "${RUN_COLLECT:-false}" = "true" ]; then
  sudo env COLLECT_LIMIT="${COLLECT_LIMIT:-1}" bash scripts/collect-steam.sh
fi

sudo docker compose -f docker-compose.collect.yml exec -T db pg_isready -U pixel -d pixeloracle
echo "Postgres respondendo em 127.0.0.1:5432 nesta máquina."
