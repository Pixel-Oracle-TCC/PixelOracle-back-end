# Pixel Oracle API

Monorepo do **Pixel Oracle** (TCC): apoia o desenvolvedor indie a estimar **risco comercial** e **chances de sucesso** **antes do lançamento** na Steam, com dados do mercado brasileiro.

| Camada | Função |
|--------|--------|
| **ml-service** (Python) | Random Forest sobre metadados planejados (preço, gêneros, categorias, etc.) |
| **api** (API principal, Node.js) | Expõe REST para o frontend; chama o ML e o **Google Gemini** (resumo + dicas) |
| **Frontend** | Repositório separado (`Pixel-Oracle-FrontEnd`) — consome só a API principal |

**Modo atual:** pré-lançamento — o dev informa **título**, **descrição da ideia** e o que planeja na página da Steam. **Não** envia reviews (jogo ainda não existe na loja).

---

## Início rápido

```text
1. Treinar modelo (uma vez)     →  python ml/train.py
2. Configurar api/.env          →  GEMINI_API_KEY (opcional)
3. Subir serviços               →  Docker OU dois terminais (ML + API principal)
4. Testar                       →  POST http://localhost:3000/api/report
```

---

## Sumário

1. [Arquitetura e portas](#arquitetura-e-portas)
2. [Pré-requisitos e instalação](#pré-requisitos-e-instalação)
3. [Como rodar](#como-rodar)
4. [Treinar o modelo](#treinar-o-modelo)
5. [Rotas da API](#rotas-da-api)
6. [Corpo da requisição](#corpo-da-requisição)
7. [Postman](#postman)
8. [Variáveis de ambiente](#variáveis-de-ambiente)
9. [Erros comuns](#erros-comuns)
10. [Docker](#docker)
11. [Repositórios relacionados](#repositórios-relacionados)

---

## Arquitetura e portas

```text
  Frontend (Angular)     api/ :3000          ml-service/ :8000
        │                    │                      │
        │    POST /api/report│   POST /predict      │
        │                    ├──────────────────────┘
        │                    │  http://ml-service:8000  (rede Docker)
        │                    └──────────► Gemini API (dicas)
        └──────────────────────► só use a API principal em produção/dev front
```

| URL base | Serviço | Uso |
|----------|---------|-----|
| `http://localhost:3000/api` | **API principal** | **Use sempre no Postman e no frontend** |
| `http://localhost:8000` | ML | Debug / Swagger; o front **não** chama direto |

---

## Pré-requisitos e instalação

### Ferramentas

| Ferramenta | Versão | Obrigatório |
|------------|--------|-------------|
| Python | 3.9+ | Sim (treino + ML local) |
| Node.js | 18+ | Sim (API principal local) |
| npm | vem com Node | Sim |
| Docker Desktop | recente | Recomendado para o time |
| Git | — | Clone do repo |

No Mac use `python3`. No Windows, marque **Add Python to PATH** na instalação.

### 1. Clone e entre na pasta

```bash
cd PixelOracle-API
```

### 2. Ambiente Python + dependências (ml-service)

**macOS / Linux:**

```bash
cd ml-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
cd ml-service
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Treinar o modelo (obrigatório na primeira vez)

```bash
# Com .venv ativado, dentro de ml-service/
python ml/train.py
```

Deve existir `ml-service/artifacts/modelo_rf.pkl`. A pasta `artifacts/` **não está no Git**.

### 4. Ambiente Node (api)

```bash
cd api
npm install
cp .env.example .env
```

Edite `api/.env` e coloque sua `GEMINI_API_KEY` (opcional; sem chave, `/api/report` usa dicas fallback).

---

## Como rodar

Escolha **uma** opção. Não rode Docker e `npm run dev`/`uvicorn` ao mesmo tempo nas mesmas portas.

### Opção A — Docker (time / demonstração)

Na **raiz** do repositório:

```bash
docker compose up --build -d
docker compose ps    # pixel-oracle-ml e pixel-oracle-api → healthy
```

Detalhes: **[DOCKER.md](DOCKER.md)**. Gemini: use **`api/.env`** com a chave (não deixe `GEMINI_API_KEY` vazio no `.env` da raiz).

### Opção B — Local (desenvolvimento)

**Terminal 1 — ML (porta 8000):**

```bash
cd ml-service
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Aguarde: `✅ Modelo pronto` e `Uvicorn running on http://0.0.0.0:8000`.

**Terminal 2 — API principal (porta 3000):**

```bash
cd api
npm run dev
```

Aguarde: `🚀 Pixel Oracle — API principal` **sem** o aviso `GEMINI_API_KEY não definida` (se a chave estiver no `.env`).

**Teste rápido:**

```bash
curl http://127.0.0.1:3000/api/health
```

---

## Treinar o modelo

| Item | Valor |
|------|--------|
| Dataset padrão | `ml-service/data/database_steam_br.json` (~110 jogos BR) |
| Features no treino | Metadados planejáveis (sem reviews) |
| Saída | `ml-service/artifacts/*.pkl` |

```bash
cd ml-service && source .venv/bin/activate
python ml/train.py
```

| Variável (`ml-service/.env`, opcional) | Padrão |
|---------------------------------------|--------|
| `DATA_SOURCE` | `json` |
| `INCLUDE_REVIEW_FEATURES` | `false` (manter para pré-lançamento) |

Para atualizar o modelo: substitua o JSON (repo **PixelOracle-data-base**) e rode `python ml/train.py` de novo.

---

## Rotas da API

Todas as rotas da API principal têm prefixo **`/api`**. Base: `http://127.0.0.1:3000` ou `http://localhost:3000`.

| Método | Rota | Descrição |
|--------|------|-----------|
| **GET** | `/api/health` | API principal + ML no ar? |
| **POST** | `/api/predict` | Só classificação ML |
| **POST** | `/api/report` | **Principal:** ML + Gemini (resumo + dicas) |

### `GET /api/health`

Sem body.

```bash
curl http://127.0.0.1:3000/api/health
```

### `POST /api/predict`

Mesmo body da seção [Corpo da requisição](#corpo-da-requisição). Retorna só `predicao_ml` (sem Gemini).

### `POST /api/report` (recomendado)

Mesmo body. Retorna `predicao_ml` + `insights` (`fonte`: `"gemini"` ou `"fallback"`).

**Exemplo de resposta (trecho):**

```json
{
  "status": "sucesso",
  "modo": "pre-lancamento",
  "jogo": { "titulo": "...", "descricao": "..." },
  "predicao_ml": {
    "previsao_pixel_oracle": {
      "risco_comercial": "Alto Risco",
      "chance_sucesso_estimada_pct": 90.4,
      "probabilidades": { "Alto Risco": 0.904, "Risco Médio": 0.071, "Baixo Risco (Sucesso)": 0.026 }
    }
  },
  "insights": { "resumo": "...", "dicas": ["...", "..."], "fonte": "gemini" }
}
```

### ML direto (opcional)

| Método | URL |
|--------|-----|
| GET | `http://127.0.0.1:8000/` |
| POST | `http://127.0.0.1:8000/predict` |
| Docs | `http://127.0.0.1:8000/docs` |

O ML usa o mesmo JSON, mas **não** usa `titulo`/`descricao` no modelo — só metadados numéricos/categóricos.

---

## Corpo da requisição

### Obrigatórios (sempre)

| Campo | Tipo | Notas |
|-------|------|--------|
| **`titulo`** | string | Nome do jogo. Alias: `name` |
| **`descricao`** | string | Ideia / pitch, **mín. 10 caracteres**. Aliases: `ideia`, `description` |
| **`price_brl`** | number | Preço planejado (R$) |
| **`genres`** | string[] | Em português: `"Ação"`, `"Indie"`, … |
| **`categories`** | string[] | Ex.: `"Um jogador"`, `"Proezas Steam"` |
| **`release_year`** | number | Ano previsto de lançamento |

### Opcionais (têm valor padrão)

`platforms`, `supported_languages`, `dlc`, `achievements`, `metacritic`, `indie`, `coming_soon`, `singleplayer`, `multiplayer`, `is_online`, `early_access`, `trading_cards`, `workshop`, `is_free`, `adult_content`, `controller_support`, `type`, `period_time`, etc.

### Não enviar (causa erro)

Campos de **jogo já publicado** — rejeitados no modo pré-lançamento:

`total_reviews`, `total_positive`, `user_score`, `score_desc`, `multiplicador_boxleiter`, `vendas_estimadas`

### Classes de risco (saída do ML)

| Classe | Interpretação (histórico BR) |
|--------|----------------------------|
| Baixo Risco (Sucesso) | Melhor desempenho comercial estimado |
| Risco Médio | Intermediário |
| Alto Risco | Desempenho fraco |

`chance_sucesso_estimada_pct` = probabilidade (%) da classe que o modelo escolheu.

---

## Postman

### Configuração

1. **Method:** `POST` para `/predict` e `/report`
2. **URL principal:** `http://127.0.0.1:3000/api/report`
3. **Headers:** `Content-Type: application/json`
4. **Body:** raw → JSON abaixo (não use o body antigo só com preço/gêneros — faltam `titulo` e `descricao`)

### Body de referência (copiar e colar)

```json
{
  "titulo": "What The Duck",
  "descricao": "Jogo de ação e aventura indie com elementos de RPG. Planejado para comando e conquistas na Steam, preço acessível no mercado BR.",
  "price_brl": 11.39,
  "genres": ["Ação", "Aventura", "Indie", "RPG"],
  "categories": [
    "Um jogador",
    "Proezas Steam",
    "Compat. total c/ comando",
    "Steam Cloud",
    "Partilha de Biblioteca"
  ],
  "release_year": 2023,
  "platforms": 1,
  "supported_languages": 3,
  "achievements": 44,
  "indie": true,
  "coming_soon": false,
  "controller_support": "full"
}
```

### Collection sugerida

| # | Método | URL |
|---|--------|-----|
| 1 | GET | `http://127.0.0.1:3000/api/health` |
| 2 | POST | `http://127.0.0.1:3000/api/predict` |
| 3 | POST | `http://127.0.0.1:3000/api/report` |

---

## Variáveis de ambiente

### `api/.env` (API principal)

```env
PORT=3000
ML_SERVICE_URL=http://localhost:8000
GEMINI_API_KEY=sua_chave_google_ai
GEMINI_MODEL=gemini-2.5-flash
```

| Variável | Local | Docker |
|----------|-------|--------|
| `ML_SERVICE_URL` | `http://localhost:8000` | Definido no `docker-compose.yml` (`http://ml-service:8000`) |
| `GEMINI_API_KEY` | `api/.env` | Lido via `env_file: ./api/.env` |

### `ml-service/.env` (opcional)

```env
DATA_SOURCE=json
INCLUDE_REVIEW_FEATURES=false
```

---

## Erros comuns

| Sintoma | Causa | Solução |
|--------|-------|---------|
| **500** `Campo obrigatório: titulo` (API principal) | Body sem `titulo` / `descricao` | Inclua os dois campos no JSON |
| **500** reviews não aceitas (API principal) | Body com `total_reviews`, `user_score`, etc. | Remova campos de review |
| **422** (ML direto `:8000`) | Schema Pydantic: campo faltando ou extra | Use só campos documentados acima |
| **502** / `origem: ml-service` | ML parado ou URL errada | Suba ML na 8000; confira `ML_SERVICE_URL` |
| **503** (ML) | Sem `artifacts/modelo_rf.pkl` | Rode `python ml/train.py` |
| **429** / `origem: gemini` | Cota Google esgotada | Nova chave, billing ou outro modelo |
| `fonte: "fallback"` no 200 OK | Sem `GEMINI_API_KEY` ou erro Gemini | Configure `api/.env` |
| Porta em uso | Docker + local ao mesmo tempo | `docker compose down` ou pare `uvicorn`/`npm run dev` |

---

## Docker

```bash
# Na raiz do repositório
docker compose up --build -d
curl http://localhost:3000/api/health
```

Recriar só a API após mudar `api/.env`:

```bash
docker compose up -d --force-recreate api
```

Script com checagem de artefatos: `./scripts/docker-up.sh`

---

## Repositórios relacionados

| Repositório | Papel |
|-------------|--------|
| **PixelOracle-data-base** | Coleta Steam → gera `database_steam_br.json` |
| **PixelOracle-API** (este) | Treino, ML, API principal |
| **Pixel-Oracle-FrontEnd** | UI → `POST {API_URL}/api/report` |

---

## Estrutura do código

```
PixelOracle-API/
├── ml-service/
│   ├── domain/           # Risco, período
│   ├── application/      # Casos de uso, payload pré-lançamento
│   ├── infrastructure/   # Artefatos, repositório JSON
│   ├── ml/               # features.py, train.py
│   ├── presentation/     # FastAPI, GamePitchInput
│   ├── artifacts/        # .pkl (gitignore)
│   └── data/
├── api/                    # API principal (Node.js)
│   └── src/
│       ├── services/       # mlService, geminiService
│       ├── presentation/   # rotas, validação
│       └── application/    # GenerateFullReportUseCase
├── docker-compose.yml
├── scripts/docker-up.sh
├── DOCKER.md
└── README.md
```

---

Projeto acadêmico (TCC) — Steam, mercado brasileiro de jogos indie.
