# Contratos de API — Pixel Oracle

Fonte canônica também no vault: `arquitetura/Contratos de API.md` e o guia `arquitetura/Guia Ponta a Ponta da API.md`.
Atualize este arquivo em toda mudança de schema de request/response.

> **v3 (2026-10-14) — breaking change.** O score de viabilidade comercial foi descartado.
> Saíram `/predict`, `/api/predict`, `/triangulate`, `predicao_ml` e `pontos_fortes/fracos/oportunidades/riscos`.
> O relatório agora é um dashboard de evidências de reviews reais: destaques (elogios/reclamações
> recorrentes), fatores decisivos (RF), alertas, reviews de referência e jogos similares.

Nenhum campo de resposta identifica autores de reviews (ToS Steam cláusula 2 + LGPD): só texto,
votos, horas jogadas e idioma.

---

## GET /health (ml-service, consumido por: api principal)

Sempre responde 200 (o healthcheck do Docker não pode cair por banco vazio).

### Response
```json
{
  "status": "online",
  "modo": "pre-lancamento",
  "database_configured": true,
  "endpoints": ["/", "/health", "/retrieve-similar", "/analyze"],
  "database_ok": true,
  "contagens": {
    "games": 110, "reviews": 1200, "review_aspects": 2500,
    "themes": 60, "theme_stats": 300, "genre_drivers": 40
  }
}
```

### Histórico de mudanças
- 2026-10-14: removidos `model_loaded`, `features`, `include_review_features`, `mensagem`; adicionados `database_ok` e `contagens`.
- 2026-09-10: endpoint `/health` explícito; campo `database_configured` adicionado.

---

## POST /retrieve-similar (ml-service, consumido por: uso interno / debug)

### Request
```json
{ "titulo": "string", "descricao": "string", "genres": ["Indie"], "top_k": 5 }
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
      "review_score_desc": "Very Positive",
      "total_reviews_steam": 1008,
      "pct_positivas": 0.9048,
      "similaridade": 0.82
    }
  ],
  "k": 1
}
```

### Histórico de mudanças
- 2026-10-14: removido `owners_estimados` (estimativa de vendas pelo método Boxleiter, sem base empírica). Afeta também `jogos_similares` do `/analyze` e do `/api/report`.
- 2026-10-14: `review_score_desc`, `total_reviews_steam` e `pct_positivas` (query_summary real da Steam; `null` se o jogo ainda não teve reviews coletadas).
- 2026-09-10: endpoint criado (RAG via pgvector).

---

## POST /analyze (ml-service, consumido por: api principal `/api/report`)

Substitui `/triangulate`. Exige `DATABASE_URL` (sem banco → 503).

### Request (`GamePitchInput`, campos extras são ignorados)
```json
{
  "titulo": "string",
  "descricao": "string (mín. 10)",
  "genres": ["Indie", "Ação"],
  "price_brl": 36.99,
  "top_k": 5
}
```
Obrigatórios: `titulo` (alias `name`), `descricao` (aliases `ideia`, `description`), `genres`.

### Response
```json
{
  "status": "sucesso",
  "modo": "pre-lancamento",
  "jogo": { "titulo": "string", "descricao": "string", "genres": ["Indie"] },
  "dashboard": {
    "destaques": {
      "elogios": [
        {
          "id": "similares:similares:12",
          "escopo": "similares",
          "genero": null,
          "tema": { "theme_id": 12, "rotulo": "história profunda e emocionante", "categoria": "historia", "polaridade": "positivo" },
          "frase": "Jogadores valorizam história profunda e emocionante: o tema aparece em 23% das reviews dos jogos similares ao seu, em 4 jogos diferentes, como em Hollow Knight e Hades.",
          "jogos_exemplo": [{ "game_id": 3, "titulo": "Hollow Knight", "mencoes": 14, "prevalencia_no_jogo": 0.28 }],
          "metricas": {
            "reviews_com_tema": 46, "total_reviews": 200, "prevalencia": 0.23,
            "wilson_low": 0.177, "wilson_high": 0.293,
            "jogos_distintos": 4, "total_jogos": 5, "votos_uteis": 1830,
            "pct_recomendadas_com_tema": 0.95, "p_value_ajustado": 0.0012,
            "log_odds": 1.9, "significativo": true
          },
          "citacoes": [
            { "review_id": 881, "jogo": "Hollow Knight", "trecho": "the lore is incredibly deep", "recomendada": true, "votos_uteis": 412, "horas_jogadas": 63.5 }
          ],
          "contexto": { "pct_menos_2h": 0.04, "pct_early_access": 0.0 }
        }
      ],
      "reclamacoes": []
    },
    "fatores_decisivos": [
      {
        "genero": "Indie", "escopo": "genero",
        "feature": "tema:31", "rotulo": "Reclamação: controles imprecisos", "tipo": "tema",
        "importancia": 0.041, "importancia_std": 0.006, "direcao": "reduz",
        "taxa_recomendacao_com": 0.22, "taxa_recomendacao_sem": 0.81, "suporte": 57,
        "modelo": { "f1_macro": 0.74, "roc_auc": 0.83, "n_amostras": 900 }
      }
    ],
    "alertas": [
      { "tipo": "primeiras_horas", "mensagem": "string", "evidencia": { "destaque_id": "string", "pct_menos_2h": 0.6 } }
    ],
    "reviews_referencia": [
      {
        "jogo": { "id": 3, "titulo": "Hollow Knight", "steam_appid": 367520 },
        "positivas": [
          {
            "review_id": 881, "recomendada": true, "texto": "string (até 600)",
            "votos_uteis": 412, "votes_funny": 3, "weighted_vote_score": 0.93,
            "horas_jogadas": 63.5, "idioma": "english", "early_access": false,
            "resposta_desenvolvedor": null
          }
        ],
        "negativas": []
      }
    ],
    "jogos_similares": []
  },
  "cobertura": {
    "reviews_analisadas_similares": 200,
    "reviews_analisadas_genero": 900,
    "temas_disponiveis": 60
  },
  "evidencias": {
    "fonte_similares": "pgvector_cosine",
    "fonte_temas": "absa_gemini + cluster_agglomerative",
    "fonte_recorrencia": "wilson + qui_quadrado + benjamini_hochberg",
    "fonte_fatores": "random_forest_permutation_importance",
    "fonte_reviews": "steam_get_app_reviews (sem dados de autor)"
  }
}
```

Regras de leitura:
- `escopo: "similares"` = reviews dos jogos mais parecidos com o pitch; `"genero"` = todas as reviews do gênero.
- Um destaque só aparece se o tema surgir em pelo menos 2 jogos distintos.
- `significativo` usa o p-valor ajustado (Benjamini-Hochberg) < 0,05.
- `log_odds > 0`: o tema aparece mais em reviews que recomendam o jogo.
- `alertas[].tipo`: `dados_insuficientes` | `primeiras_horas` | `early_access` | `nicho_exigente`.
- Listas podem vir vazias enquanto o pipeline de reviews não foi rodado (ver alerta `dados_insuficientes`).

### Histórico de mudanças
- 2026-10-14: endpoint criado (substitui `/triangulate`).

---

## POST /api/report (api principal, consumido por: frontend)

### Request
Mesmo body de `/analyze`. Campos do formulário antigo (`categories`, `release_year`, flags…) são aceitos e ignorados.

### Response
```json
{
  "status": "sucesso",
  "modo": "pre-lancamento",
  "jogo": { "titulo": "string", "descricao": "string", "genres": ["Indie"] },
  "dashboard": { "...": "idêntico a /analyze" },
  "narrativa": {
    "resumo": "string",
    "destaques": [
      { "id": "similares:similares:12", "frase": "Muitos jogadores valorizam ...", "fonte": "gemini" }
    ],
    "fonte": "gemini",
    "validacao": { "frases_substituidas": 1, "motivos": ["<id>: citou Hades fora dos jogos-exemplo"] }
  },
  "cobertura": { "...": "idêntico a /analyze" },
  "evidencias": {}
}
```

- `narrativa.destaques[].id` casa com `dashboard.destaques.*[].id`.
- `narrativa.destaques[].fonte`: `"gemini"` (texto da LLM aprovado no validador) | `"modelo"` (frase determinística do ml-service).
- `narrativa.fonte`: `"gemini"` | `"fallback"` (sem chave ou erro da Gemini — o relatório continua funcional).

### Breaking change
- 2026-10-14: sai `predicao_ml`; `dashboard` muda de `pontos_fortes/pontos_fracos/oportunidades/riscos/insights_genero` para `destaques/fatores_decisivos/alertas/reviews_referencia/jogos_similares`; `narrativa` muda para `resumo + destaques[] + validacao`; entra `cobertura`. Rota `/api/predict` removida.
- 2026-09-10: resposta deixa de expor `insights: { resumo, dicas }` e passa a `dashboard` + `narrativa`.

### Histórico de mudanças
- 2026-10-14: `/api/report` chama `/analyze`; validador pós-Gemini de jogos citados.
- 2026-09-10: `/api/report` chama `/triangulate`; Gemini só redige o dashboard.

---

## GET /kpis/dashboard (api principal, consumido por: frontend)

Agregados do catálogo Steam no Postgres. Exige `DATABASE_URL`. Só dados de jogo (sem autor).

`releases` cobre os últimos 12 meses (data de lançamento em `games.release_date`).
`pctFree` usa `preco_brl = 0`. `medianPrice` ignora preço 0. `avgPositiveRate` usa o último `review_snapshots` por jogo.
`genres` é a fatia do catálogo com cada gênero Steam (`games` ⋈ `game_genres` ⋈ `genres`). Um jogo pode ter vários gêneros, então a soma das `%` passa de 100.

### Response
```json
{
  "status": "sucesso",
  "data": {
    "overview": {
      "totalGames": 110,
      "pctFree": 12.5,
      "medianPrice": 29.99,
      "avgPositiveRate": 84.2
    },
    "releases": [
      { "month": "2025-10", "releases": 4, "pctFree": 25.0 }
    ],
    "genres": [
      { "genre": "Indie", "games": 80, "pct": 72.7 }
    ]
  }
}
```

`medianPrice` e `avgPositiveRate` podem ser `null` se não houver preço pago ou snapshot de reviews.

### Histórico de mudanças
- 2026-10-20: `genres` adicionado à resposta (retrocompatível).
- 2026-10-20: endpoint criado.

---

## GET /kpis/releases (api principal, consumido por: frontend)

Série mensal de lançamentos. Query: `from` e `to` em `YYYY-MM-DD`, `from <= to`, intervalo máximo de 5 anos.

### Request
`GET /kpis/releases?from=2024-01-01&to=2024-12-31`

### Response (200)
```json
{
  "status": "sucesso",
  "data": [
    { "month": "2024-01", "releases": 8, "pctFree": 12.5 }
  ]
}
```

### Response (400)
```json
{
  "status": "erro",
  "mensagem": "Parâmetros de data inválidos.",
  "erros": [{ "campo": "from", "mensagem": "Use o formato YYYY-MM-DD." }]
}
```

### Histórico de mudanças
- 2026-10-20: endpoint criado.
