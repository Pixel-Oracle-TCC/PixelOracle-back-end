# Pixel Oracle API

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

> O antigo **score de viabilidade comercial** foi descartado: as vendas da Steam não são públicas e o
> rótulo dependia de estimativa. O código está em `ml-service/legacy/sales_score/` só como registro.

| Camada | Pasta | Porta | Função |
|--------|-------|-------|--------|
| API principal | `api/` | `3000` | REST para o frontend; orquestra ML + Gemini |
| ML service | `ml-service/` | `8000` | Similares, temas, recorrência, drivers; pipeline offline |
| Postgres + pgvector | Docker `db` | `5433`→`5432` | Jogos, reviews, aspectos, temas, estatísticas |
| Frontend | repo separado | — | Consome **só** `http://localhost:3000/api/*` |

Conformidade: **nenhum dado de autor** é guardado (sem `steamid`, sem perfil). Dedup por
`recommendationid`. Temas são agregados por gênero/jogo, nunca por pessoa (ToS Steam cláusula 2 + LGPD).

Documentação de produto/arquitetura: vault Obsidian `TCC/` · contratos: [`CONTRATOS_API.md`](CONTRATOS_API.md) · Docker: [`DOCKER.md`](DOCKER.md).

---

## Início rápido

```text
1. ml-service/.env + api/.env  →  DATABASE_URL, GEMINI_API_KEY (veja Variáveis)
2. Subir stack                 →  docker compose up --build -d
3. Popular o banco             →  jogos + embeddings + pipeline de reviews (abaixo)
4. Testar                      →  POST http://localhost:3000/api/report
```

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

## Pré-requisitos e instalação

| Ferramenta | Versão | Uso |
|------------|--------|-----|
| Docker Desktop | recente | Stack completa (recomendado) |
| Python | 3.9+ | Scripts offline |
| Node.js | 18+ | API local (`npm run dev`) |

```bash
cd ml-service
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # DATABASE_URL, GEMINI_API_KEY

cd ../api
npm install
cp .env.example .env               # GEMINI_API_KEY
```

---

## Como rodar

### Opção A — Docker (recomendado)

```bash
docker compose up --build -d
docker compose ps                  # db, ml-service, api → healthy
curl -s http://localhost:3000/api/health | jq
```

Banco criado antes desta versão? Aplique as migrations novas (idempotente):

```bash
cd ml-service && source .venv/bin/activate
python scripts/apply_schema.py
```

### Opção B — Local

```bash
docker compose up -d db                                   # só o banco
cd ml-service && uvicorn main:app --reload --port 8000    # terminal 2
cd api && npm run dev                                     # terminal 3
```

---

## Popular o banco

Tudo roda no host, com `ml-service/.env` apontando para `localhost:5433`.

```bash
cd ml-service && source .venv/bin/activate

# 1) Jogos e embeddings (busca de similares)
python scripts/bootstrap_games_from_json.py
python scripts/enrich_descriptions_from_metadata.py   # ou enrich_game_descriptions.py com a Store acessível
python scripts/backfill_embeddings.py

# 2) Reviews (GetAppReviews: mais úteis de todos os tempos + recentes; sem dados de autor)
python scripts/collect_reviews.py                      # retoma de onde parou; --force recoleta

# 3) Aspectos (Gemini): categoria + sentimento + trecho literal + resumo
python scripts/run_absa.py --limit 500                 # repita até zerar as pendentes

# 4) Temas recorrentes (cluster dos resumos + nome dado pela Gemini)
python scripts/cluster_themes.py

# 5) Recorrência por gênero (Wilson, qui-quadrado, Benjamini-Hochberg)
python scripts/compute_theme_stats.py

# 6) Random Forest de drivers de recomendação
python ml/train_drivers.py
```

Os passos 4–6 devem ser rodados juntos (o 4 recria os temas). Métricas de cada execução ficam em
`experiments/*.json`.

Verificar:

```bash
curl -s http://localhost:8000/health | jq .contagens
```

### Validação da ABSA (gold standard)

```bash
python scripts/export_gold_standard.py --size 200      # gera experiments/gold_standard/anotador{1,2}.csv
# dois anotadores preenchem a coluna "anotacao" (ex.: gameplay:positivo; historia:negativo)
python scripts/evaluate_gold_standard.py               # Kappa entre anotadores + F1 da Gemini
```

### Testes sintéticos (sem rede e sem banco)

```bash
python scripts/test_pipeline.py
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

---

## Corpo da requisição

| Campo | Tipo | Obrigatório | Notas |
|-------|------|-------------|-------|
| `titulo` | string | sim | Alias: `name` |
| `descricao` | string | sim | Mín. 10 chars. Aliases: `ideia`, `description` |
| `genres` | string[] | sim | Ex.: `"Indie"`, `"Ação"` |
| `price_brl` | number | não | Preço planejado |
| `top_k` | number | não | Quantos jogos similares (1–20, padrão 5) |

Campos do formulário antigo (`categories`, `release_year`, flags) são aceitos e ignorados.

```bash
curl -s -X POST http://localhost:3000/api/report \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"Floresta Pixel","descricao":"Metroidvania 2D com crafting e exploração cooperativa local.","genres":["Indie","Ação","Aventura"]}' | jq
```

---

## Resposta de `/api/report`

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

## Variáveis de ambiente

### `api/.env`

```env
PORT=3000
ML_SERVICE_URL=http://localhost:8000
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
```

### `ml-service/.env`

```env
DATABASE_URL=postgresql://pixel:pixel@localhost:5433/pixeloracle
EMBEDDING_MODEL=all-MiniLM-L6-v2
ASPECT_EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
SIMILAR_GAMES_TOP_K=5
STEAM_API_KEY=           # opcional (rate limit maior)
GEMINI_API_KEY=          # ABSA e nomeação de temas
GEMINI_MODEL=gemini-2.5-flash
```

---

## Erros comuns

| Sintoma | Causa | Solução |
|--------|-------|---------|
| `503` em `/analyze` | Sem `DATABASE_URL` | Configure o Postgres |
| Alerta `dados_insuficientes` | Pipeline de reviews não rodou | Passos 2–6 de "Popular o banco" |
| `fonte_similares` sem resultado | Jogos sem embedding | `backfill_embeddings.py` |
| `relation "themes" does not exist` | Banco antigo | `python scripts/apply_schema.py` |
| `5432 already in use` | Outro Postgres | Projeto usa **5433** no host |
| `narrativa.fonte: "fallback"` | Sem chave / erro Gemini | `api/.env` + `docker compose up -d --force-recreate api` |
| Report lento na 1ª vez | Carga do MiniLM | Timeout de 120–180s no cliente |

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
│   ├── absa/                   # extração, taxonomia, recorrência, Kappa/F1
│   ├── themes/                 # cluster + nomeação de temas
│   ├── ml/                     # RF de drivers + log de experimentos
│   ├── db/ models/             # migrations SQL + SQLAlchemy
│   ├── scripts/                # pipeline offline e testes
│   └── legacy/sales_score/     # score de vendas descartado (registro)
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
| **Pixel-Oracle-FrontEnd** | UI Angular → ver `docs/FRONTEND_ATUALIZACAO.md` |
| **PixelOracle-data-base** | Scripts legados de coleta → JSON de jogos |

---

Projeto acadêmico (TCC) — mentoria pré-lançamento para jogos indie, fundamentada em reviews reais da Steam.
