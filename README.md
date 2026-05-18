# Pixel Oracle (Monorepo)

**Pixel Oracle** auxilia o **desenvolvimento de jogos indie** e ajuda o desenvolvedor a **analisar riscos e chances de sucesso** antes do lançamento na Steam — com base em dados do mercado brasileiro, Machine Learning e orientação por IA.

Desenvolvido como parte do **TCC — Pixel Oracle**.

---

## Visão do produto

| Pergunta do desenvolvedor | Como o Pixel Oracle responde |
|---------------------------|------------------------------|
| “Qual o risco do meu jogo flopped?” | Classificação ML: **Alto Risco**, **Risco Médio** ou **Baixo Risco (Sucesso)** + probabilidades |
| “O que posso melhorar antes de lançar?” | Dicas do **Gemini** sobre pitch, preço, página Steam, escopo e visibilidade |
| “Meu jogo ainda não existe na Steam” | Modo **pré-lançamento**: nome, descrição da ideia e metadados planejados (sem reviews) |

O fluxo não substitui o trabalho do dev — **apoia a decisão** com dados e sugestões práticas para aumentar as chances de sucesso comercial.

---

## Arquitetura

```text
Frontend (Angular, repo separado)  →  api/ BFF :3000  →  ml-service/ :8000
                                              ↘ Gemini (dicas comerciais)
```

| Serviço | Stack | Porta | Função |
|---------|-------|-------|--------|
| **ml-service** | Python, FastAPI, scikit-learn | 8000 | Predição ML (uso interno / BFF) |
| **api** | Node.js, Express, Gemini | 3000 | BFF — **única API que o frontend consome** |

> O frontend Angular fica em **outro repositório** (ex.: `Pixel-Oracle-FrontEnd`). Este monorepo expõe apenas `ml-service` + `api`.

---

## Estrutura do repositório

```
pixel-oracle/   (PixelOracle-API)
├── ml-service/                 # Python — Clean Architecture
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── presentation/
│   ├── ml/                     # features.py + train.py
│   ├── artifacts/
│   ├── data/
│   ├── main.py
│   └── Dockerfile
├── api/                        # Node.js BFF — Clean Architecture
│   ├── src/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   ├── services/           # mlService + geminiService
│   │   ├── presentation/
│   │   └── index.ts
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .gitignore
```

---

## Início rápido (Docker)

Para outros desenvolvedores: guia completo em **[DOCKER.md](DOCKER.md)**.

```bash
# 1. Treinar modelo (obrigatório — artifacts/ não está no Git)
cd ml-service && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python ml/train.py

# 2. Na raiz do repositório
cp .env.example .env    # GEMINI_API_KEY opcional

# 3. Subir tudo
docker compose up --build
# ou: ./scripts/docker-up.sh
```

| URL | Serviço |
|-----|---------|
| http://localhost:3000/api/health | BFF |
| http://localhost:3000/api/report | Relatório (POST) |
| http://localhost:8000/docs | ML Swagger |

---

## BFF Node.js (`api/`)

### Instalação (Mac / Windows)

```bash
cd api
npm install
cp .env.example .env
```

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `PORT` | `3000` | Porta do BFF |
| `ML_SERVICE_URL` | `http://localhost:8000` | URL do Python |
| `GEMINI_API_KEY` | — | Chave Google AI (opcional) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Modelo Gemini |

### Rodar em desenvolvimento

Terminal 1 — ML:

```bash
cd ml-service && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

Terminal 2 — BFF:

```bash
cd api && npm run dev
```

### `POST /api/report` (fluxo completo)

1. BFF recebe dados do jogo  
2. Chama `ml-service` → risco + probabilidades  
3. Monta prompt e chama **Gemini** → 3 dicas práticas  
4. Retorna JSON unificado  

Sem `GEMINI_API_KEY`, o BFF usa dicas **fallback** estáticas.

Estrutura interna do BFF (`api/src/`):

```
domain/          → entidades e portas (contratos)
application/     → GenerateFullReportUseCase
services/        → mlService (Axios) e geminiService
infrastructure/  → prompts Gemini
presentation/    → rotas e controllers Express
index.ts         → composição
```

#### Rotas do BFF (Postman)

| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `http://127.0.0.1:3000/api/health` | Status BFF + ML |
| POST | `http://127.0.0.1:3000/api/predict` | Proxy para ML `/predict` |
| POST | `http://127.0.0.1:3000/api/report` | ML + dicas (Gemini ou fallback) |

```bash
curl -X POST http://127.0.0.1:3000/api/report \
  -H "Content-Type: application/json" \
  -d '{"titulo":"Meu Jogo Indie","descricao":"Roguelike 2D com combate rápido e progressão permanente.","price_brl":24.99,"genres":["Ação","Indie"],"categories":["Um jogador","Proezas Steam"],"release_year":2025}'
```

---

## Pré-requisitos

| Ferramenta | Versão mínima |
|------------|----------------|
| Python | 3.9+ |
| Node.js | 18+ |
| npm | incluso com Node |
| Docker | opcional (compose) |
| Git | opcional |

No **Mac**, use `python3` (o comando `python` pode não existir).  
No **Windows**, marque **"Add Python to PATH"** na instalação.

---

## Instalação

### macOS

```bash
# 1. Entre na pasta do serviço ML
cd PixelOracle-API/ml-service

# 2. Crie o ambiente virtual
python3 -m venv .venv

# 3. Ative o ambiente
source .venv/bin/activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. (Opcional) Configure variáveis de ambiente
cp .env.example .env
```

### Windows (PowerShell ou CMD)

```powershell
# 1. Entre na pasta do serviço ML
cd PixelOracle-API\ml-service

# 2. Crie o ambiente virtual
python -m venv .venv

# 3. Ative o ambiente
# PowerShell:
.venv\Scripts\Activate.ps1
# CMD:
# .venv\Scripts\activate.bat

# 4. Instale as dependências
pip install -r requirements.txt

# 5. (Opcional) Configure variáveis de ambiente
copy .env.example .env
```

> **Windows — erro de execução de scripts:** se o PowerShell bloquear a ativação, execute uma vez como administrador:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

## Treinar o modelo

O treino lê `data/database_steam_br.json` por padrão e salva os artefatos em `artifacts/`.

```bash
# Com o .venv ativado, dentro de ml-service/
python ml/train.py
```

Saída esperada:

- Validação cruzada (5-fold)
- Classification report no conjunto de teste
- Arquivos em `artifacts/`:
  - `modelo_rf.pkl`
  - `mlb_genres.pkl` / `mlb_categories.pkl`
  - `feature_columns.pkl` / `feature_config.pkl`

### Variáveis de ambiente (`.env`)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DATA_SOURCE` | `json` | `json` ou `mongo` |
| `DATA_JSON_PATH` | `data/database_steam_br.json` | Caminho do dataset |
| `INCLUDE_REVIEW_FEATURES` | `false` | `true` só para experimentos com reviews no treino |
| `MONGO_URI` | — | Só se `DATA_SOURCE=mongo` |

Copie `.env.example` para `.env` e ajuste se necessário.

---

## Subir a API

```bash
# Dentro de ml-service/, com .venv ativado
uvicorn main:app --reload
```

| URL | Descrição |
|-----|-----------|
| http://127.0.0.1:8000/ | Health check |
| http://127.0.0.1:8000/docs | Swagger (testar no navegador) |
| http://127.0.0.1:8000/predict | Predição de risco (POST) |

Para expor na rede local:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Como usar a API (modo pré-lançamento)

O desenvolvedor informa **nome**, **descrição da ideia** e metadados planejados da Steam.  
**Não envie reviews** (`total_reviews`, `user_score`, etc.) — o jogo ainda não foi lançado.

### Campos obrigatórios

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `titulo` | string | Título do jogo (`name` também aceito) |
| `descricao` | string | Ideia do jogo — mín. 10 caracteres (`ideia` também aceito) |
| `price_brl` | número | Preço planejado em reais |
| `genres` | lista | Gêneros em português |
| `categories` | lista | Categorias Steam planejadas |
| `release_year` | inteiro | Ano de lançamento previsto |

### Body de exemplo (Postman → `POST /api/report`)

```json
{
  "titulo": "Pixel Quest BR",
  "descricao": "Roguelike 2D em pixel art com combate rápido, progressão permanente e foco em narrativa local brasileira. Público-alvo: fãs de Hollow Knight e Hades.",
  "price_brl": 24.99,
  "genres": ["Ação", "Indie", "Aventura"],
  "categories": [
    "Um jogador",
    "Proezas Steam",
    "Compat. total c/ comando",
    "Steam Cloud"
  ],
  "release_year": 2025,
  "platforms": 1,
  "supported_languages": 2,
  "achievements": 30,
  "indie": true,
  "coming_soon": true,
  "controller_support": "full"
}
```

### Resposta (`/api/report`)

```json
{
  "status": "sucesso",
  "modo": "pre-lancamento",
  "jogo": {
    "titulo": "Pixel Quest BR",
    "descricao": "..."
  },
  "predicao_ml": {
    "status": "sucesso",
    "modo": "pre-lancamento",
    "kpis_analisados": 95,
    "previsao_pixel_oracle": {
      "risco_comercial": "Risco Médio",
      "chance_sucesso_estimada_pct": 62.5,
      "probabilidades": { }
    }
  },
  "insights": {
    "resumo": "...",
    "dicas": ["...", "...", "..."],
    "fonte": "gemini"
  }
}
```

### ML direto (`POST :8000/predict`)

Aceita o **mesmo JSON**. `titulo` e `descricao` vão para o Gemini; o ML usa só metadados planejados.

#### Classes de risco

| Classe | Regra (vendas estimadas) |
|--------|---------------------------|
| Baixo Risco (Sucesso) | ≥ 50.000 |
| Risco Médio | ≥ 10.000 |
| Alto Risco | < 10.000 |

### 3. Exemplo com curl

**macOS / Linux / Windows (Git Bash):**

```bash
curl -X POST "http://127.0.0.1:3000/api/report" \
  -H "Content-Type: application/json" \
  -d "{\"titulo\":\"Pixel Quest BR\",\"descricao\":\"Aventura indie 2D com exploração e crafting.\",\"price_brl\":19.90,\"genres\":[\"Indie\",\"Aventura\"],\"categories\":[\"Um jogador\"],\"release_year\":2025}"
```

### 4. Postman

**ML direto (porta 8000)**

| # | Método | URL |
|---|--------|-----|
| 1 | GET | `http://127.0.0.1:8000/` |
| 2 | POST | `http://127.0.0.1:8000/predict` |

**BFF (porta 3000)** — suba o `api` com `npm run dev` antes

| # | Método | URL |
|---|--------|-----|
| 3 | GET | `http://127.0.0.1:3000/api/health` |
| 4 | POST | `http://127.0.0.1:3000/api/predict` |
| 5 | POST | `http://127.0.0.1:3000/api/report` |

Em todas as POST: Body → **raw** → **JSON** → cole o exemplo completo da seção 2.

---

## Fluxo recomendado (do zero)

```text
1. Clonar o repositório
2. ml-service: venv + pip install + python ml/train.py
3. ml-service: uvicorn main:app --reload  (porta 8000)
4. api: npm install + cp .env.example .env + npm run dev  (porta 3000)
5. Testar POST http://localhost:3000/api/report
6. (Opcional) docker compose up --build
```

---

## Solução de problemas

| Problema | Solução |
|----------|---------|
| `python: command not found` (Mac) | Use `python3` |
| `ModuleNotFoundError` | Ative o `.venv` e rode `pip install -r requirements.txt` |
| API retorna **503** | Execute `python ml/train.py` para gerar `artifacts/` |
| `FileNotFoundError` no JSON | Confirme `data/database_steam_br.json` |
| Predição estranha / sempre igual | Verifique gêneros/categorias em **português** |
| BFF retorna **502** | Confirme o ml-service na porta 8000 |
| PowerShell não ativa o venv | Use `Set-ExecutionPolicy RemoteSigned` ou CMD |

---

## Relação com outros repositórios

- **PixelOracle-data-base** — coleta Steam e gera `database_steam_br.json`
- **PixelOracle-API** (este monorepo) — ML + BFF
- **Pixel-Oracle-FrontEnd** (repositório separado) — Angular; consome `http://localhost:3000/api`

Para melhorar a acurácia, aumente o dataset no repositório de coleta e substitua `ml-service/data/database_steam_br.json`, depois rode o treino novamente.

---

## Licença e uso acadêmico

Projeto desenvolvido para fins de pesquisa acadêmica (TCC) e análise do mercado de games brasileiros na Steam.
