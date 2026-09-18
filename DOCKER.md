# Docker — Pixel Oracle

Sobe **Postgres+pgvector**, **ML** (`:8000`) e **API principal** (`:3000`) com um comando.

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) ou Docker Engine + Compose (Linux)
- Artefatos do modelo em `ml-service/artifacts/` (veja abaixo)

## Primeira vez

### 1. Gerar o modelo (uma vez por máquina)

Os `.pkl` não vão no Git:

```bash
cd ml-service
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python ml/train.py
```

Confirme: `ls artifacts/modelo_rf.pkl`

### 2. Variáveis de ambiente (Gemini)

Em **`api/.env`**:

```env
GEMINI_API_KEY=sua_chave
GEMINI_MODEL=gemini-2.5-flash
```

> Não deixe `GEMINI_API_KEY=` vazio no `.env` da raiz — pode sobrescrever a chave.

### 3. Subir os containers

```bash
# Na raiz PixelOracle-API/
docker compose up --build -d
docker compose ps
```

Ou: `./scripts/docker-up.sh`

### 4. (Opcional) Popular jogos + embeddings

Com o `db` healthy (porta host **5433**):

```bash
cd ml-service && source .venv/bin/activate
# DATABASE_URL=postgresql://pixel:pixel@localhost:5433/pixeloracle no .env
python scripts/bootstrap_games_from_json.py
python scripts/enrich_descriptions_from_metadata.py
python scripts/backfill_embeddings.py
```

### 5. Testar

| URL | Serviço |
|-----|---------|
| http://localhost:8000/docs | ML (Swagger) |
| http://localhost:8000/health | Health do ML |
| http://localhost:3000/api/health | API principal |
| http://localhost:3000/api/report | Relatório completo (POST) |
| localhost:5433 | Postgres (`pixel` / `pixel` / `pixeloracle`) |

Body de exemplo: ver [README.md](README.md).

## Estrutura Compose

```text
db          →  host :5433 → container :5432  (pgvector/pg16)
ml-service  →  :8000  (FastAPI + RF + RAG)
api         →  :3000  (orquestra ml-service + Gemini)
```

Dentro da rede Docker a API usa `ML_SERVICE_URL=http://ml-service:8000` (não `localhost`).

## Comandos úteis

```bash
docker compose up --build -d
docker compose logs -f
docker compose down          # mantém volume pgdata
docker compose down -v       # apaga o banco
docker compose build --no-cache ml-service
docker compose up -d --force-recreate api
```

## Problemas comuns

| Problema | Solução |
|----------|---------|
| `5432 already in use` | Normal — o projeto mapeia **5433** no host |
| ML unhealthy / 503 | `python ml/train.py` + confira `artifacts/` |
| Build lento / CUDA | Dockerfile usa Torch CPU; rebuild `--no-cache ml-service` |
| API não sobe | Espere o ML healthy; `docker compose logs api` |
| Gemini fallback | Chave em `api/.env` + `force-recreate api` |
| Steam Connection reset | Rede bloqueando Store; use scripts sintéticos (README) |

## Compartilhar modelo com o time

1. Cada dev roda `python ml/train.py` (recomendado)
2. Ou compartilhar zip de `artifacts/` internamente
