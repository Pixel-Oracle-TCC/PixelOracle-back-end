# Contratos de API — Pixel Oracle

Fonte canônica também no vault: `arquitetura/Contratos de API.md` e o guia `arquitetura/Guia Ponta a Ponta da API.md`.
Atualize este arquivo em toda mudança de schema de request/response.

---

## GET /health (ml-service, consumido por: api principal)

### Response
```json
{
  "status": "online",
  "model_loaded": true,
  "modo": "pre-lancamento",
  "features": 0,
  "include_review_features": false,
  "database_configured": true,
  "endpoints": ["/", "/health", "/predict", "/retrieve-similar", "/triangulate"],
  "mensagem": "string"
}
```

### Histórico de mudanças
- 2026-09-10: endpoint `/health` explícito; campo `database_configured` adicionado.

---

## POST /predict (ml-service, consumido por: api principal)

### Request
Pitch pré-lançamento (`GamePitchInput`): `titulo`, `descricao`, `price_brl`, `genres`, `categories`, `release_year`, flags booleanas de metadados planejados. **Sem** reviews/vendas reais.

### Response
```json
{
  "status": "sucesso",
  "modo": "pre-lancamento",
  "jogo": { "titulo": "string", "descricao": "string" },
  "kpis_analisados": 0,
  "previsao_pixel_oracle": {
    "risco_comercial": "string",
    "chance_sucesso_estimada_pct": 0.0,
    "probabilidades": { "Baixo Risco": 0.0 }
  }
}
```

### Histórico de mudanças
- Mantido para compatibilidade; núcleo RF inalterado nesta reformulação.

---

## POST /retrieve-similar (ml-service, consumido por: uso interno / debug)

### Request
```json
{
  "titulo": "string",
  "descricao": "string",
  "genres": ["Indie"],
  "top_k": 5
}
```

### Response
```json
{
  "status": "sucesso",
  "query": { "titulo": "string", "genres": ["Indie"] },
  "jogos_similares": [
    {
      "id": 1,
      "steam_appid": 123,
      "titulo": "string",
      "descricao": "string",
      "preco_brl": 29.9,
      "release_year": 2020,
      "owners_estimados": 100000,
      "similaridade": 0.82
    }
  ],
  "k": 1
}
```

### Histórico de mudanças
- 2026-09-10: endpoint criado (RAG via pgvector).

---

## POST /triangulate (ml-service, consumido por: api principal `/api/report`)

### Request
Mesmo schema de `/predict` (`GamePitchInput`).

### Response
```json
{
  "status": "sucesso",
  "modo": "pre-lancamento",
  "jogo": { "titulo": "string", "descricao": "string" },
  "predicao_ml": {
    "risco_comercial": "string",
    "chance_sucesso_estimada_pct": 0.0,
    "probabilidades": {}
  },
  "dashboard": {
    "pontos_fortes": [{ "ponto": "string", "evidencia": {} }],
    "pontos_fracos": [{ "ponto": "string", "evidencia": {} }],
    "oportunidades": [{ "ponto": "string", "evidencia": {} }],
    "riscos": [{ "ponto": "string", "evidencia": {} }],
    "jogos_similares": [],
    "insights_genero": []
  },
  "evidencias": {
    "fonte_predicao": "random_forest",
    "fonte_similares": "pgvector_cosine",
    "fonte_aspectos": "genre_insights_absa"
  },
  "aviso": "opcional — ex.: DB ausente"
}
```

### Histórico de mudanças
- 2026-09-10: endpoint criado; fallback parcial sem DATABASE_URL (só RF).

---

## POST /api/report (api principal, consumido por: frontend)

### Request
Mesmo pitch pré-lançamento (validação em `parseGamePitch`).

### Response
```json
{
  "status": "sucesso",
  "modo": "pre-lancamento",
  "jogo": { "titulo": "string", "descricao": "string" },
  "predicao_ml": {},
  "dashboard": {
    "pontos_fortes": [],
    "pontos_fracos": [],
    "oportunidades": [],
    "riscos": [],
    "jogos_similares": [],
    "insights_genero": []
  },
  "narrativa": {
    "resumo": "string",
    "pontos_fortes": ["string"],
    "pontos_fracos": ["string"],
    "oportunidades": ["string"],
    "riscos": ["string"],
    "fonte": "gemini"
  },
  "evidencias": {},
  "aviso": "opcional"
}
```

### Breaking change
- 2026-09-10: resposta deixa de expor `insights: { resumo, dicas }` e passa a `dashboard` + `narrativa`. Frontend precisa acompanhar.

### Histórico de mudanças
- 2026-09-10: `/api/report` chama `/triangulate`; Gemini só redige o dashboard.
