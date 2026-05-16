# Pixel Oracle API

API de Machine Learning para estimar o **risco comercial** de jogos brasileiros na Steam, com base em metadados da loja, categorias, gêneros e sinais de avaliação.

Desenvolvido como parte do ecossistema **Pixel Oracle** (TCC).

---

## Estrutura do repositório

```
PixelOracle-API/
├── api/                    # API Node.js (em desenvolvimento)
└── ml-service/             # Serviço Python (ML + FastAPI)
    ├── .venv/              # Ambiente virtual Python (não versionar)
    ├── artifacts/          # Modelo treinado (.pkl) — gerado pelo train.py
    ├── data/
    │   └── database_steam_br.json
    ├── model/
    │   ├── features.py     # Engenharia de features (treino + inferência)
    │   └── train.py        # Pipeline de treinamento
    ├── main.py             # API FastAPI
    ├── requirements.txt
    └── .env.example
```

---

## Pré-requisitos

| Ferramenta | Versão mínima |
|------------|----------------|
| Python | 3.9+ |
| pip | incluso com Python |
| Git | opcional (clone) |

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
python model/train.py
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
| `INCLUDE_REVIEW_FEATURES` | `true` | `false` = modelo só com metadados (sem reviews) |
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

## Como usar a API

### 1. Health check

**GET** `http://127.0.0.1:8000/`

```json
{
  "status": "online",
  "model_loaded": true,
  "features": 99,
  "include_review_features": true
}
```

### 2. Predição de risco

**POST** `http://127.0.0.1:8000/predict`  
**Header:** `Content-Type: application/json`

#### Campos obrigatórios

| Campo | Tipo | Exemplo |
|-------|------|---------|
| `price_brl` | número | `11.39` |
| `genres` | lista de strings | `["Ação", "Indie"]` |
| `categories` | lista de strings | `["Um jogador", "Proezas Steam"]` |
| `release_year` | inteiro | `2023` |

Use **gêneros e categorias em português**, como no `database_steam_br.json`.

#### Exemplo completo (Postman / Insomnia / curl)

```json
{
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
  "dlc": 2,
  "achievements": 44,
  "metacritic": 0,
  "required_age_num": 0,
  "singleplayer": true,
  "multiplayer": false,
  "is_online": false,
  "indie": true,
  "early_access": false,
  "trading_cards": false,
  "workshop": false,
  "is_free": false,
  "coming_soon": false,
  "adult_content": true,
  "controller_support": "full",
  "type": "game",
  "score_desc": "Mixed",
  "total_positive": 18,
  "total_reviews": 38,
  "user_score": 47.37,
  "multiplicador_boxleiter": 30
}
```

#### Resposta

```json
{
  "status": "sucesso",
  "kpis_analisados": 99,
  "previsao_pixel_oracle": {
    "risco_comercial": "Alto Risco",
    "probabilidades": {
      "Alto Risco": 0.82,
      "Baixo Risco (Sucesso)": 0.05,
      "Risco Médio": 0.13
    }
  }
}
```

#### Classes de risco

| Classe | Regra (vendas estimadas) |
|--------|---------------------------|
| Baixo Risco (Sucesso) | ≥ 50.000 |
| Risco Médio | ≥ 10.000 |
| Alto Risco | < 10.000 |

### 3. Exemplo com curl

**macOS / Linux / Windows (Git Bash):**

```bash
curl -X POST "http://127.0.0.1:8000/predict" \
  -H "Content-Type: application/json" \
  -d "{\"price_brl\":49.99,\"genres\":[\"Indie\",\"Ação\"],\"categories\":[\"Um jogador\",\"Proezas Steam\"],\"release_year\":2021,\"total_reviews\":500,\"total_positive\":450,\"user_score\":90.0,\"multiplicador_boxleiter\":30}"
```

### 4. Postman

1. Método **POST** → URL `http://127.0.0.1:8000/predict`
2. Body → **raw** → **JSON**
3. Cole o JSON de exemplo acima
4. **Send**

---

## Fluxo recomendado (do zero)

```text
1. Instalar Python e clonar o repositório
2. cd ml-service && python3/python -m venv .venv
3. Ativar .venv e pip install -r requirements.txt
4. python model/train.py
5. uvicorn main:app --reload
6. Testar em http://127.0.0.1:8000/docs ou Postman
```

---

## Solução de problemas

| Problema | Solução |
|----------|---------|
| `python: command not found` (Mac) | Use `python3` |
| `ModuleNotFoundError` | Ative o `.venv` e rode `pip install -r requirements.txt` |
| API retorna **503** | Execute `python model/train.py` para gerar `artifacts/` |
| `FileNotFoundError` no JSON | Confirme `data/database_steam_br.json` |
| Predição estranha / sempre igual | Verifique gêneros/categorias em **português** |
| PowerShell não ativa o venv | Use `Set-ExecutionPolicy RemoteSigned` ou CMD |

---

## Relação com outros repositórios

- **PixelOracle-data-base** — coleta Steam (Selenium + API) e gera o `database_steam_br.json`
- **PixelOracle-API** (este repo) — treina o modelo e expõe a predição via FastAPI
- **Pixel-Oracle-FrontEnd** — interface (consumirá esta API)

Para melhorar a acurácia, aumente o dataset no repositório de coleta e substitua `ml-service/data/database_steam_br.json`, depois rode o treino novamente.

---

## Licença e uso acadêmico

Projeto desenvolvido para fins de pesquisa acadêmica (TCC) e análise do mercado de games brasileiros na Steam.
