# Docker — Pixel Oracle

Sobe **Postgres+pgvector**, **ML** (`:8000`) e **API principal** (`:3000`) com um comando.
O conteúdo do dashboard vem do pipeline offline de reviews, que grava no banco (ver [README](README.md)).

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) ou Docker Engine + Compose (Linux)

## Primeira vez

### 1. Variáveis de ambiente

Em **`api/.env`**:

```env
GEMINI_API_KEY=sua_chave
GEMINI_MODEL=gemini-2.5-flash
```

Em **`ml-service/.env`** (scripts no host): copie de `.env.example`.

> Não deixe `GEMINI_API_KEY=` vazio no `.env` da raiz — pode sobrescrever a chave.

### 2. Subir os containers

```bash
# Na raiz PixelOracle-API/
docker compose up --build -d
docker compose ps
```

Com volume novo, o Postgres roda **todas** as migrations de `ml-service/db/migrations/` no primeiro start.
Com volume antigo, aplique as novas pelo host:

```bash
cd ml-service && source .venv/bin/activate
python scripts/apply_schema.py
```

### 3. Popular o banco

Siga a seção **Popular o banco** do [README](README.md): jogos + embeddings, depois o pipeline de reviews
(`collect_reviews` → `run_absa` → `cluster_themes` → `compute_theme_stats` → `ml/train_drivers.py`).

Recebeu um dump do grupo? Pule o pipeline: `./scripts/db-import.sh dumps/pixeloracle_<data>.dump`.

### 4. Testar

| URL | Serviço |
|-----|---------|
| http://localhost:8000/docs | ML (Swagger) |
| http://localhost:8000/health | Health do ML + contagens do banco |
| http://localhost:3000/api/health | API principal |
| http://localhost:3000/api/report | Relatório completo (POST) |
| localhost:5433 | Postgres (`pixel` / `pixel` / `pixeloracle`) |

## Estrutura Compose

```text
db          →  host :5433 → container :5432  (pgvector/pg16)
ml-service  →  :8000  (FastAPI: similares + dashboard de evidências)
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
| `relation "themes" does not exist` | Volume antigo: `python scripts/apply_schema.py` |
| Build lento / CUDA | Dockerfile usa Torch CPU; rebuild `--no-cache ml-service` |
| API não sobe | Espere o ML healthy; `docker compose logs api` |
| Gemini fallback | Chave em `api/.env` + `force-recreate api`; ou cota diária esgotada (20 req/dia/modelo no free tier) |
| `Cannot connect to the Docker daemon` | Abra o Docker Desktop |
| Dashboard vazio | Pipeline de reviews ainda não rodou (alerta `dados_insuficientes`) |
