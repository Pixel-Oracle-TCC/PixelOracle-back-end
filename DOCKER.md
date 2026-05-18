# Docker — Pixel Oracle

Guia para outros desenvolvedores subirem **ML** (`:8000`) e **BFF** (`:3000`) com um comando.

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) ou Docker Engine + Compose (Linux)
- Artefatos do modelo em `ml-service/artifacts/` (veja abaixo)

## Primeira vez (quem clona o repositório)

### 1. Gerar o modelo (uma vez por máquina)

Os arquivos `.pkl` não vão no Git. Cada dev precisa treinar ou receber a pasta `artifacts/`:

```bash
cd ml-service
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python ml/train.py
```

Confirme: `ls artifacts/modelo_rf.pkl`

### 2. Variáveis de ambiente (Gemini)

Coloque a chave em **`api/.env`** (recomendado):

```env
GEMINI_API_KEY=sua_chave
GEMINI_MODEL=gemini-2.5-flash
```

Ou na raiz: `cp .env.example .env` com a mesma chave.

> O Compose lê `api/.env` dentro do container. Não coloque `GEMINI_API_KEY=` vazio no `.env` da raiz — isso sobrescrevia a chave.

### 3. Subir os containers

```bash
# Na raiz PixelOracle-API/
docker compose up --build
```

Ou use o script com verificação:

```bash
chmod +x scripts/docker-up.sh
./scripts/docker-up.sh
```

### 4. Testar

| URL | Serviço |
|-----|---------|
| http://localhost:8000/docs | ML (Swagger) |
| http://localhost:3000/api/health | BFF |
| http://localhost:3000/api/report | Relatório completo (POST) |

Exemplo Postman: `POST http://localhost:3000/api/report` com body do README (campos `titulo`, `descricao`, etc.).

## Comandos úteis

```bash
# Subir em segundo plano
docker compose up --build -d

# Ver logs
docker compose logs -f

# Parar
docker compose down

# Rebuild forçado
docker compose build --no-cache
docker compose up
```

## Estrutura

```text
docker compose
├── ml-service  →  :8000  (FastAPI + modelo)
└── api         →  :3000  (BFF → chama ml-service na rede interna)
```

O BFF usa `ML_SERVICE_URL=http://ml-service:8000` **dentro** da rede Docker (não use `localhost` no container da API).

## Problemas comuns

| Problema | Solução |
|----------|---------|
| ML unhealthy / 503 | Rode `python ml/train.py` e confira `artifacts/` |
| BFF não sobe | `docker compose logs api` — espere o ML ficar healthy |
| Gemini não responde | Coloque `GEMINI_API_KEY` no `.env` da raiz e `docker compose up` de novo |
| Porta em uso | Pare processos locais em 3000/8000 ou altere ports no `docker-compose.yml` |

## Compartilhar modelo com o time

Como `artifacts/` está no `.gitignore`, opções:

1. Cada dev roda `python ml/train.py` (recomendado)
2. Compartilhar zip da pasta `artifacts/` por drive interno
3. CI que gera artefatos e publica como artefato de release (futuro)
