# Pixel Oracle API

Monorepo do **Pixel Oracle** (TCC): mentoria pré-lançamento para desenvolvedores indie brasileiros.

A partir de um **pitch** (título, descrição, gênero, preço, metadados planejados), o sistema:

1. **Estima risco comercial** com Random Forest (sem data leakage de reviews/vendas no input)
2. **Recupera jogos similares** via embeddings + PostgreSQL/`pgvector` (RAG)
3. **Triangula evidências** (RF + similares + insights de gênero/ABSA quando disponíveis)
4. **Redige** o dashboard com Google Gemini (a LLM não analisa do zero — só narra evidências)

| Camada | Pasta | Porta | Função |
|--------|-------|-------|--------|
| API principal | `api/` | `3000` | REST para o frontend; orquestra ML + Gemini |
| ML service | `ml-service/` | `8000` | RF, RAG, triangulação, coleta offline |
| Postgres + pgvector | Docker `db` | `5433`→`5432` | Jogos, embeddings, reviews, `genre_insights` |
| Frontend | repo separado | — | Consome **só** `http://localhost:3000/api/*` |

**Modo:** pré-lançamento — **não** envie reviews, scores ou vendas reais no body.

Documentação de produto/arquitetura: vault Obsidian `TCC/` · guia do front: [`FRONTEND_ATUALIZACAO.md`](FRONTEND_ATUALIZACAO.md) · contratos: [`CONTRATOS_API.md`](CONTRATOS_API.md).

---

## Início rápido

```text
1. Artefatos RF          →  cd ml-service && python ml/train.py   (se não houver artifacts/)
2. api/.env              →  GEMINI_API_KEY (opcional; sem chave = narrativa fallback)
3. Subir stack           →  docker compose up --build -d
4. (Opcional) popular DB →  bootstrap + embeddings (veja abaixo)
5. Testar                →  POST http://localhost:3000/api/report
```

---

## Sumário

1. [Arquitetura](#arquitetura)
2. [Pré-requisitos e instalação](#pré-requisitos-e-instalação)
3. [Como rodar](#como-rodar)
4. [Popular o banco (RAG)](#popular-o-banco-rag)
5. [Treinar o modelo](#treinar-o-modelo)
6. [Rotas](#rotas)
7. [Corpo da requisição](#corpo-da-requisição)
8. [Resposta de `/api/report`](#resposta-de-apireport)
9. [Variáveis de ambiente](#variáveis-de-ambiente)
10. [Erros comuns](#erros-comuns)
11. [Estrutura do código](#estrutura-do-código)
12. [Repositórios relacionados](#repositórios-relacionados)

---

## Arquitetura

```text
  Frontend (Angular)
        │
        │  POST /api/report | /api/predict | GET /api/health
        ▼
  api/ :3000  ──►  ml-service/ :8000  ──►  Postgres+pgvector :5433
        │                │
        │                ├── Random Forest (/predict, parte do /triangulate)
        │                ├── RAG pgvector (/retrieve-similar)
        │                └── TriangulationEngine (/triangulate)
        └── Gemini (redige narrativa a partir do dashboard)
```

| URL | Serviço | Quem usa |
|-----|---------|----------|
| `http://localhost:3000/api` | API principal | **Frontend e Postman** |
| `http://localhost:8000` | ML (+ `/docs` Swagger) | Debug interno |
| `localhost:5433` | Postgres | Scripts offline / `psql` |

> A porta **5433** no host evita conflito com outro Postgres na 5432. Dentro do Compose o ML usa o hostname `db:5432`.

---

## Pré-requisitos e instalação

| Ferramenta | Versão | Uso |
|------------|--------|-----|
| Docker Desktop | recente | Stack completa (recomendado) |
| Python | 3.9+ | Treino + scripts offline |
| Node.js | 18+ | API local (`npm run dev`) |

### Python (ml-service)

```bash
cd ml-service
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ml/train.py                 # gera artifacts/*.pkl (não vão no Git)
```

### Node (api)

```bash
cd api
npm install
cp .env.example .env               # preencha GEMINI_API_KEY
```

### ml-service/.env (scripts no host)

```bash
cp ml-service/.env.example ml-service/.env
# DATABASE_URL=postgresql://pixel:pixel@localhost:5433/pixeloracle
```

---

## Como rodar

Não misture Docker e processos locais nas **mesmas** portas.

### Opção A — Docker (recomendado)

```bash
# na raiz PixelOracle-API/
docker compose up --build -d
docker compose ps                  # db, ml, api → healthy

curl -s http://localhost:3000/api/health | jq
```

Detalhes: [`DOCKER.md`](DOCKER.md).

Primeiro build do `ml-service` baixa Torch CPU (pode demorar alguns minutos). O Dockerfile evita pacotes CUDA.

### Opção B — Local

```bash
# Terminal 1 — só o banco
docker compose up -d db

# Terminal 2 — ML
cd ml-service && source .venv/bin/activate
export DATABASE_URL=postgresql://pixel:pixel@localhost:5433/pixeloracle
uvicorn main:app --reload --port 8000

# Terminal 3 — API
cd api && npm run dev
```

---

## Popular o banco (RAG)

Sem dados no Postgres, `/predict` funciona; `/api/report` vem **parcial** (só RF, listas vazias / `aviso`).

```bash
cd ml-service && source .venv/bin/activate

python scripts/bootstrap_games_from_json.py      # ~110 jogos do JSON
python scripts/enrich_descriptions_from_metadata.py   # texto sintético (se Steam estiver bloqueada)
# ou, com Steam acessível:
# python scripts/enrich_game_descriptions.py --reset-embeddings

python scripts/backfill_embeddings.py
# python scripts/collect_reviews.py --limit-games 20   # requer Steam Store
```

Verificar:

```bash
docker compose exec db psql -U pixel -d pixeloracle -c \
  "SELECT COUNT(*) AS games, COUNT(embedding) AS embeddings FROM games;"
```

> Em algumas redes (ex.: Wi‑Fi da faculdade) `store.steampowered.com` pode resetar a conexão. Use hotspot/VPN ou as descrições sintéticas acima.

---

## Treinar o modelo

| Item | Valor |
|------|--------|
| Dataset | `ml-service/data/database_steam_br.json` |
| Features | Metadados planejáveis (**sem** reviews no X) |
| Saída | `ml-service/artifacts/*.pkl` |

```bash
cd ml-service && source .venv/bin/activate
python ml/train.py
```

Manter `INCLUDE_REVIEW_FEATURES=false` no modo pré-lançamento (evita data leakage).

---

## Rotas

### API principal (`:3000`)

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/health` | API + ping no ML |
| `POST` | `/api/predict` | Só Random Forest |
| `POST` | `/api/report` | **Principal:** triangulação + narrativa Gemini |

### ML (`:8000`, interno)

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Status do modelo + `database_configured` |
| `POST` | `/predict` | RF isolado |
| `POST` | `/retrieve-similar` | Top-k jogos similares (pgvector) |
| `POST` | `/triangulate` | Dashboard estruturado (consumido pelo report) |
| — | `/docs` | Swagger |

---

## Corpo da requisição

### Obrigatórios

| Campo | Tipo | Notas |
|-------|------|--------|
| `titulo` | string | Alias: `name` |
| `descricao` | string | Mín. 10 chars. Aliases: `ideia`, `description` |
| `price_brl` | number | Preço planejado (R$) |
| `genres` | string[] | Ex.: `"Indie"`, `"Ação"` |
| `categories` | string[] | Ex.: `"Single-player"`, `"Um jogador"` |
| `release_year` | number | Ano previsto |

### Opcionais

`platforms`, `supported_languages`, `dlc`, `achievements`, `metacritic` (use `0`), `indie`, `coming_soon`, `singleplayer`, `multiplayer`, `early_access`, `is_free`, `controller_support`, etc.

### Não enviar (erro)

`total_reviews`, `total_positive`, `user_score`, `score_desc`, `multiplicador_boxleiter`, `vendas_estimadas`

### Exemplo

```json
{
  "titulo": "Floresta Pixel",
  "descricao": "Metroidvania 2D com crafting e exploração cooperativa local.",
  "genres": ["Indie", "Ação", "Aventura"],
  "categories": ["Single-player"],
  "price_brl": 36.99,
  "release_year": 2026,
  "indie": true,
  "coming_soon": true
}
```

```bash
curl -s -X POST http://localhost:3000/api/report \
  -H 'Content-Type: application/json' \
  -d @- <<'EOF'
{ "titulo":"Floresta Pixel", "descricao":"Metroidvania 2D com crafting e exploração cooperativa local.",
  "genres":["Indie","Ação","Aventura"], "categories":["Single-player"],
  "price_brl":36.99, "release_year":2026 }
EOF
```

---

## Resposta de `/api/report`

**Breaking change:** não existe mais `insights: { resumo, dicas }`.

```json
{
  "status": "sucesso",
  "modo": "pre-lancamento",
  "jogo": { "titulo": "...", "descricao": "..." },
  "predicao_ml": {
    "risco_comercial": "Alto Risco",
    "chance_sucesso_estimada_pct": 68,
    "probabilidades": {
      "Alto Risco": 0.68,
      "Risco Médio": 0.12,
      "Baixo Risco (Sucesso)": 0.20
    }
  },
  "dashboard": {
    "pontos_fortes": [{ "ponto": "...", "evidencia": {} }],
    "pontos_fracos": [],
    "oportunidades": [],
    "riscos": [],
    "jogos_similares": [],
    "insights_genero": []
  },
  "narrativa": {
    "resumo": "...",
    "pontos_fortes": [],
    "pontos_fracos": [],
    "oportunidades": [],
    "riscos": [],
    "fonte": "gemini"
  },
  "evidencias": {
    "fonte_predicao": "random_forest",
    "fonte_similares": "pgvector_cosine",
    "fonte_aspectos": "genre_insights_absa"
  },
  "aviso": null
}
```

- `narrativa.fonte`: `"gemini"` | `"fallback"` (API continua útil se a LLM falhar)
- `insights_genero` pode ser `[]` até o pipeline ABSA popular o banco
- Guia completo para o Angular: [`FRONTEND_ATUALIZACAO.md`](FRONTEND_ATUALIZACAO.md)

### Classes de risco (ML)

| Classe | Interpretação |
|--------|----------------|
| Baixo Risco (Sucesso) | Melhor faixa no histórico BR usado no treino |
| Risco Médio | Intermediário |
| Alto Risco | Faixa mais frágil |

`chance_sucesso_estimada_pct` = % na **classe prevista** (não é “probabilidade de sucesso” absoluta).

---

## Variáveis de ambiente

### `api/.env`

```env
PORT=3000
ML_SERVICE_URL=http://localhost:8000
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
```

No Docker, `ML_SERVICE_URL` é sobrescrito para `http://ml-service:8000`.

### `ml-service/.env`

```env
DATABASE_URL=postgresql://pixel:pixel@localhost:5433/pixeloracle
DATA_SOURCE=json
INCLUDE_REVIEW_FEATURES=false
EMBEDDING_MODEL=all-MiniLM-L6-v2
SIMILAR_GAMES_TOP_K=5
STEAM_API_KEY=
GEMINI_API_KEY=
```

---

## Erros comuns

| Sintoma | Causa | Solução |
|--------|-------|---------|
| Body sem `titulo`/`descricao` | Validação | Inclua os campos |
| Campos de review rejeitados | Modo pré-lançamento | Remova `user_score`, `total_reviews`, … |
| `502` / `origem: ml-service` | ML parado | `docker compose up -d ml-service` |
| `503` modelo | Sem `artifacts/` | `python ml/train.py` |
| `5432 already in use` | Outro Postgres | Projeto usa **5433** no host |
| Steam `Connection reset` | Rede bloqueando Store | Hotspot/VPN ou `enrich_descriptions_from_metadata.py` |
| `fonte: "fallback"` | Sem chave / erro Gemini | Configure `api/.env` e recrie o container `api` |
| Report lento na 1ª vez | Carga do MiniLM | Timeout 120–180s no cliente |
| Build Docker puxando CUDA | deps antigas | Dockerfile já força Torch CPU; rebuild `--no-cache ml-service` |

---

## Estrutura do código

```text
PixelOracle-API/
├── api/                         # Express + TypeScript
│   └── src/
│       ├── application/         # GenerateFullReportUseCase
│       ├── domain/              # FullReport, GamePitch, ports
│       ├── services/            # MlService, GeminiService
│       ├── presentation/        # rotas, parseGamePitch
│       └── infrastructure/prompts/
├── ml-service/
│   ├── presentation/            # FastAPI routes + schemas
│   ├── application/             # predict, triangulate
│   ├── triangulation/           # motor do dashboard
│   ├── embeddings/ + retrieval/ # MiniLM + pgvector
│   ├── absa/                    # extração / Kappa / F1 / significância
│   ├── collection/              # Steam / SteamSpy / reviews (sem steamid)
│   ├── db/ + models/            # SQLAlchemy + schema SQL
│   ├── ml/                      # train.py, features.py
│   ├── scripts/                 # bootstrap, embeddings, reviews, …
│   ├── artifacts/               # .pkl (gitignore)
│   └── data/database_steam_br.json
├── CONTRATOS_API.md
├── FRONTEND_ATUALIZACAO.md
├── docker-compose.yml
├── DOCKER.md
└── README.md
```

Conformidade: reviews **não** persistem `author.steamid` (ToS Steam + LGPD). Dedup por `recommendationid`.

---

## Repositórios relacionados

| Repositório | Papel |
|-------------|--------|
| **PixelOracle-API** (este) | ML, triangulação, API principal, Postgres |
| **Pixel-Oracle-FrontEnd** | UI Angular → ver `docs/FRONTEND_ATUALIZACAO.md` |
| **PixelOracle-data-base** | Scripts legados de coleta → JSON de jogos |

---

Projeto acadêmico (TCC) — viabilidade comercial de jogos indie no mercado Steam BR, com mentoria fundamentada (ML + RAG + ABSA).
