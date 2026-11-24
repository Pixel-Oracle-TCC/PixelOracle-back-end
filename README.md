# Pixel Oracle API

[![CI](https://github.com/Pixel-Oracle-TCC/PixelOracle-back-end/actions/workflows/ci.yml/badge.svg)](https://github.com/Pixel-Oracle-TCC/PixelOracle-back-end/actions/workflows/ci.yml)

Monorepo do **Pixel Oracle** (TCC): mentoria pré-lançamento para desenvolvedores indie.

O desenvolvedor descreve o jogo (título, ideia, gêneros) e recebe um **dashboard de evidências
reais**, extraídas de reviews públicas da Steam de jogos parecidos com o dele:

1. **Jogos similares** ao pitch, via embeddings + PostgreSQL/`pgvector`
2. **Destaques**: elogios e reclamações que se repetem nesses jogos e no gênero, com % de reviews,
   jogos-exemplo e as citações mais votadas como "útil" (ex.: *"Muitos jogadores valorizam uma
   história profunda, como em Hollow Knight e Hades…"*)
3. **Fatores decisivos**: Random Forest que mostra quais temas mais pesam para a review recomendar
   (ou não) o jogo
4. **Reviews de referência** de cada jogo similar, incluindo como o desenvolvedor respondeu às críticas
5. **Redação** pela Google Gemini, que só reescreve o que já foi calculado; um validador descarta frases
   que citem jogos fora das evidências

| Camada | Pasta | Porta | Função |
|--------|-------|-------|--------|
| API principal | `api/` | `3000` | REST para o frontend; orquestra ML + Gemini |
| ML service | `ml-service/` | `8000` | Similares e dashboard; pipeline offline de reviews |
| Postgres + pgvector | Docker `db` | `5433`→`5432` | Jogos, reviews, aspectos, temas, estatísticas |
| Frontend | repo separado | — | Consome **só** `http://localhost:3000/api/*` |

Conformidade: **nenhum dado de autor** é guardado (sem `steamid`, sem perfil). Dedup por
`recommendationid`. Temas são agregados por gênero/jogo, nunca por pessoa (ToS Steam cláusula 2 + LGPD).

Documentação de produto/arquitetura: vault Obsidian `TCC/` · contratos: [`CONTRATOS_API.md`](CONTRATOS_API.md) · Docker: [`DOCKER.md`](DOCKER.md) · entrega: [`docs/ci-cd.md`](docs/ci-cd.md) · histórico: [`CHANGELOG.md`](CHANGELOG.md).

Mudança na coleta que entra em `develop` dispara o workflow **Entrega da coleta**: empacota a imagem sem Torch e publica esse código na EC2. O botão Run workflow, no Actions, coleta um lote na hora. A Gemini fica no notebook.

---

## Início rápido

```text
1. Instalar dependências      →  venv do ml-service + npm install na api
2. Configurar .env            →  ml-service/.env e api/.env (seção Variáveis)
3. Subir a stack              →  docker compose up --build -d
4. Popular o banco            →  jogos + embeddings + pipeline de reviews
5. Testar                     →  POST http://localhost:3000/api/report
```

Sem o passo 4 a API responde, mas o dashboard vem vazio com o alerta `dados_insuficientes`.

---

## Arquitetura

```text
  Frontend (Angular)
        │  POST /api/report | GET /api/health
        ▼
  api/ :3000  ──►  ml-service/ :8000  ──►  Postgres+pgvector :5433
        │                │
        │                ├── /retrieve-similar  (pgvector)
        │                └── /analyze  → TriangulationEngine (dashboard estruturado)
        └── Gemini (redige) + validador de jogos citados

  Pipeline offline (scripts no host, grava no Postgres):
  GetAppReviews → ABSA (Gemini) → cluster de temas → recorrência por gênero → RF de drivers
```

---

## 1. Pré-requisitos e instalação

| Ferramenta | Versão | Uso |
|------------|--------|-----|
| Docker Desktop | recente | Banco e stack completa |
| Python | 3.9+ | ml-service e scripts offline |
| Node.js | 18+ | API local (`npm run dev`) |
| Chave Gemini | [Google AI Studio](https://aistudio.google.com/apikey) | ABSA, nome dos temas, narrativa |
| Chave Steam (opcional) | [Steam Web API](https://steamcommunity.com/dev/apikey) | Coleta de reviews com rate limit maior |

> **zsh (padrão no macOS):** os blocos abaixo têm linhas de comentário com `#`. Para colá-los direto no
> terminal, rode uma vez `echo 'setopt interactivecomments' >> ~/.zshrc && source ~/.zshrc` (sem isso, o
> zsh trata `#` como argumento e o comando falha).

No Windows, ative o venv com `.venv\Scripts\Activate.ps1` em vez de `source`.

```bash
cd ml-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

cd ../api
npm install
cp .env.example .env
```

## 2. Variáveis de ambiente

### `ml-service/.env` (scripts no host e container do ML)

```env
DATABASE_URL=postgresql://pixel:pixel@localhost:5433/pixeloracle
EMBEDDING_MODEL=all-MiniLM-L6-v2
ASPECT_EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
SIMILAR_GAMES_TOP_K=5
STEAM_API_KEY=                # opcional
GEMINI_API_KEY=               # ABSA e nomeação de temas
GEMINI_MODEL=gemini-2.5-flash
GEMINI_THINKING_BUDGET=0      # 0 = sem raciocínio (lote de 10 reviews: ~10 s vs ~37 s)
# EXPERIMENTS_DIR=            # padrão: <repo>/experiments
```

No Docker, o `DATABASE_URL` é sobrescrito pelo compose para `db:5432`.

### `api/.env`

```env
PORT=3000
ML_SERVICE_URL=http://localhost:8000   # no Docker o compose usa http://ml-service:8000
GEMINI_API_KEY=                        # sem chave: narrativa automática (fallback)
GEMINI_MODEL=gemini-2.5-flash
```

> **Cota gratuita da Gemini:** 20 requisições por dia **por modelo**. O ABSA manda lotes de 10 reviews,
> então rende ~200 reviews/dia por modelo. Se a API e o ml-service usarem a mesma chave e o mesmo
> modelo, dividem essa cota. Quando ela acaba, `run_absa.py` para sozinho e grava o parcial.

## 3. Subir a stack

### Opção A — Docker (recomendado)

```bash
docker compose up --build -d
docker compose ps
curl -s http://localhost:3000/api/health | jq
```

Os três serviços (`db`, `ml-service`, `api`) devem aparecer como `healthy`. Volume do banco já existia? Aplique as migrations (idempotente):

```bash
cd ml-service && source .venv/bin/activate
python scripts/apply_schema.py
```

### Opção B — Local

Um comando por terminal, nesta ordem (banco, ml-service, API):

```bash
docker compose up -d db
```

```bash
cd ml-service && source .venv/bin/activate && uvicorn main:app --reload --port 8000
```

```bash
cd api && npm run dev
```

## 4. Popular o banco

Tudo roda no host, com `ml-service/.env` apontando para `localhost:5433`. Todos os scripts são
idempotentes e retomam de onde pararam.

```bash
cd ml-service && source .venv/bin/activate

# 0) Schema (já roda no 1º docker compose; em volume antigo:)
python scripts/apply_schema.py

# 1) Catálogo e metadados Steam
python scripts/bootstrap_games_from_json.py
python scripts/collect_top_games.py --limit 100
python scripts/enrich_games.py
python scripts/backfill_embeddings.py

# 2) Amostra estratificada (≥200 reviews Steam; só estes entram na coleta)
python scripts/select_sample.py --per-genre 8 --total 80

# 3) Reviews: proporcional 50/idioma + úteis 25/25; fatias TEXT[]; round-robin por gênero
# Métricas/RF usam só fatia proporcional. Em segundo plano:
#   nohup python -u scripts/collect_reviews.py --limit-games 0 > ../logs/collect_reviews.log 2>&1 &
python scripts/collect_reviews.py --limit-games 0

# 4) Aspectos via Gemini (repita no free tier até zerar as pendentes)
python scripts/run_absa.py --limit 200

# 5–7) Temas, métricas, drivers (rode juntos: o 5 recria os temas)
python scripts/cluster_themes.py
python scripts/compute_theme_stats.py
python ml/train_drivers.py
```

Métricas de cada execução ficam em `experiments/*.json`.

**Catálogo.** `collect_top_games.py` soma 52 semanas do top sellers oficial da Steam (BR). Softwares e
DLCs vão para `apps_ignorados`. `enrich_games.py` completa `release_date`, categorias, estúdios e
idiomas via `appdetails`. `select_sample.py` marca `na_amostra` para a coleta de reviews não gastar
tempo em jogos fora da análise.

**Verificar antes do ABSA:**

```bash
docker compose exec db psql -U pixel -d pixeloracle -c "
  SELECT tipo_amostra, count(*) FROM reviews GROUP BY 1;
  SELECT count(*) FILTER (WHERE na_amostra) AS amostra,
         count(*) FILTER (WHERE reviews_collected_at IS NULL AND na_amostra) AS amostra_sem_reviews
  FROM games;
  SELECT count(*) FROM review_snapshots;
"
# \d reviews  — sem coluna de autor
```

### Compartilhar os dados com o grupo

Quem já populou o banco exporta; os demais restauram e pulam a seção acima inteira (inclusive a cota da Gemini).

**Quem tem os dados** (com o banco rodando) gera `dumps/pixeloracle_<data>.dump`; com `--csv`, também
gera `dumps/csv_<data>/`, com um CSV por tabela (sem os vetores) para abrir em planilha:

```bash
./scripts/db-export.sh --csv
```

**Quem recebe** coloca o `.dump` em `dumps/` e restaura. O script sobe o banco se precisar e **substitui**
o banco local. Reinicie o ml-service só se a stack já estava no ar:

```bash
./scripts/db-import.sh dumps/pixeloracle_20261014_2042.dump
docker compose restart ml-service
```

Compartilhe o `.dump` pelo Drive do grupo: a pasta `dumps/` fica fora do git. O dump não tem chaves
de API nem dados de autor de reviews.

### Validação da ABSA (gold standard)

O export gera `experiments/gold_standard/anotador1.csv` e `anotador2.csv`. Dois anotadores preenchem a
coluna `anotacao` (ex.: `gameplay:positivo; historia:negativo`), e o evaluate calcula o Kappa entre eles
e o F1 da Gemini:

```bash
python scripts/export_gold_standard.py --size 200
python scripts/evaluate_gold_standard.py
```

### Testes

São 11 testes sintéticos do ml-service (sem rede e sem banco) e a checagem de tipos da API:

```bash
cd ml-service && python scripts/test_pipeline.py
cd ../api && npx tsc --noEmit
```

## 5. Testar o relatório

```bash
curl -s -X POST http://localhost:3000/api/report \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"Floresta Pixel","descricao":"Metroidvania 2D com crafting e exploração cooperativa local.","genres":["Indie","Ação","Aventura"]}' | jq
```

---

## Rotas

### API principal (`:3000`)

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/health` | API + health do ML (com contagens do banco) |
| `POST` | `/api/report` | **Principal:** dashboard de evidências + narrativa |

### ML (`:8000`, interno)

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Status + contagens das tabelas |
| `POST` | `/retrieve-similar` | Top-k jogos similares (pgvector) |
| `POST` | `/analyze` | Dashboard estruturado (consumido pelo report) |
| — | `/docs` | Swagger |

### Corpo da requisição

| Campo | Tipo | Obrigatório | Notas |
|-------|------|-------------|-------|
| `titulo` | string | sim | Alias: `name` |
| `descricao` | string | sim | Mín. 10 chars. Aliases: `ideia`, `description` |
| `genres` | string[] | sim | Ex.: `"Indie"`, `"Ação"` |
| `price_brl` | number | não | Preço planejado |
| `top_k` | number | não | Quantos jogos similares (1–20, padrão 5) |

Campos extras são ignorados.

### Resposta de `/api/report`

Resumo (contrato completo em [`CONTRATOS_API.md`](CONTRATOS_API.md)):

```json
{
  "status": "sucesso",
  "jogo": { "titulo": "...", "descricao": "...", "genres": ["Indie"] },
  "dashboard": {
    "destaques": { "elogios": [], "reclamacoes": [] },
    "fatores_decisivos": [],
    "alertas": [],
    "reviews_referencia": [],
    "jogos_similares": []
  },
  "narrativa": {
    "resumo": "...",
    "destaques": [{ "id": "...", "frase": "...", "fonte": "gemini" }],
    "fonte": "gemini",
    "validacao": { "frases_substituidas": 0, "motivos": [] }
  },
  "cobertura": { "reviews_analisadas_similares": 0, "reviews_analisadas_genero": 0, "temas_disponiveis": 0 }
}
```

Cada destaque traz `metricas` (prevalência, intervalo de Wilson, jogos distintos, votos úteis,
p-valor ajustado), `jogos_exemplo` e `citacoes` reais.

---

## Erros comuns

| Sintoma | Causa | Solução |
|--------|-------|---------|
| `Cannot connect to the Docker daemon` | Docker Desktop fechado | Abra o Docker Desktop |
| `503` em `/analyze` | Sem banco | `docker compose up -d db` e confira `DATABASE_URL` |
| Alerta `dados_insuficientes` | Pipeline de reviews não rodou | Seção "Popular o banco", passos 2–6 |
| Similares vazios | Jogos sem embedding | `backfill_embeddings.py` |
| `relation "themes" does not exist` | Banco sem as migrations novas | `python scripts/apply_schema.py` |
| `5432 already in use` | Outro Postgres | O projeto usa **5433** no host |
| `Cota diária da Gemini esgotada` | Free tier (20 req/dia/modelo) | Continue no dia seguinte ou troque `GEMINI_MODEL` |
| `Gemini HTTP 503` repetido | Servidor da Gemini sobrecarregado | O cliente já tenta de novo; lote que falha fica pendente |
| `narrativa.fonte: "fallback"` | Sem chave ou erro/cota da Gemini | `api/.env` + `docker compose up -d --force-recreate api` |
| Report lento na 1ª vez | Carga do modelo de embedding | Timeout de 120–180 s no cliente |

---

## Estrutura do código

```text
PixelOracle-API/
├── api/src/
│   ├── application/            # GenerateFullReportUseCase, validador, fallback
│   ├── domain/                 # FullReport, GamePitch, ports
│   ├── services/               # MlService, GeminiService
│   ├── presentation/           # rotas, parseGamePitch
│   └── infrastructure/prompts/
├── ml-service/
│   ├── presentation/           # FastAPI routes + schemas
│   ├── application/analyze.py  # orquestra o /analyze
│   ├── triangulation/          # motor do dashboard
│   ├── embeddings/ retrieval/  # MiniLM + pgvector + leitura de reviews/temas
│   ├── collection/             # GetAppReviews (sem dados de autor)
│   ├── absa/                   # Gemini, taxonomia, extração, recorrência, Kappa/F1
│   ├── themes/                 # cluster + nomeação de temas
│   ├── ml/                     # RF de drivers + log de experimentos
│   ├── db/ models/             # migrations SQL + SQLAlchemy
│   └── scripts/                # pipeline offline e testes
├── scripts/                    # db-export.sh / db-import.sh (compartilhar o banco), docker-up.sh
├── experiments/                # métricas de cada execução (JSON)
├── CONTRATOS_API.md
├── docker-compose.yml
├── DOCKER.md
└── README.md
```

---

## Repositórios relacionados

| Repositório | Papel |
|-------------|--------|
| **PixelOracle-API** (este) | ML, pipeline de reviews, API principal, Postgres |
| **Pixel-Oracle-FrontEnd** | UI Angular — especificação v3 no vault: `arquitetura/Guia de Atualizacao do Frontend.md` |
| **PixelOracle-data-base** | Scripts de coleta → JSON de jogos usado no seed |

---

Projeto acadêmico (TCC) — mentoria pré-lançamento para jogos indie, fundamentada em reviews reais da Steam.
