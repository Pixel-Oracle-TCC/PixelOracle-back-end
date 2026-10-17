-- Pixel Oracle — foco em reviews (substitui o score de vendas)
-- Idempotente: pode rodar em banco novo (após 001) ou em banco já populado.
-- Conformidade: nenhuma tabela abaixo guarda steamid ou qualquer identificador de autor.

-- Agregados públicos de reviews por jogo (query_summary da Steam), não estimativas.
ALTER TABLE games ADD COLUMN IF NOT EXISTS total_positive INT;
ALTER TABLE games ADD COLUMN IF NOT EXISTS total_negative INT;
ALTER TABLE games ADD COLUMN IF NOT EXISTS total_reviews_steam INT;
ALTER TABLE games ADD COLUMN IF NOT EXISTS review_score_desc TEXT;
ALTER TABLE games ADD COLUMN IF NOT EXISTS reviews_collected_at TIMESTAMP;

-- Metadados da review (não do autor). playtime_at_review é o único dado vindo de author.*,
-- e não identifica a pessoa.
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS timestamp_created BIGINT;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS early_access BOOLEAN;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS steam_purchase BOOLEAN;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS votes_funny INT;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS weighted_vote_score NUMERIC;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS comment_count INT;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS developer_response TEXT;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS timestamp_dev_responded BIGINT;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS absa_processed_at TIMESTAMP;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS absa_model TEXT;

-- Aspecto único por review foi substituído por review_aspects (multi-aspecto).
ALTER TABLE reviews DROP COLUMN IF EXISTS aspecto;
ALTER TABLE reviews DROP COLUMN IF EXISTS sentimento;

CREATE INDEX IF NOT EXISTS reviews_game_id_idx ON reviews (game_id);

-- Temas recorrentes: cluster de resumos dentro de (categoria, polaridade).
CREATE TABLE IF NOT EXISTS themes (
    id SERIAL PRIMARY KEY,
    categoria TEXT NOT NULL,
    polaridade TEXT NOT NULL,          -- 'positivo' | 'negativo'
    rotulo TEXT NOT NULL,
    tamanho INT NOT NULL DEFAULT 0,
    centroide VECTOR(384),
    rotulo_fonte TEXT,                 -- 'gemini' | 'representante'
    created_at TIMESTAMP DEFAULT now()
);

-- Um registro por aspecto extraído. Sem colunas de autor: o vínculo é só com a review.
CREATE TABLE IF NOT EXISTS review_aspects (
    id SERIAL PRIMARY KEY,
    review_id INT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    categoria TEXT NOT NULL,
    sentimento TEXT NOT NULL,          -- 'positivo' | 'negativo' | 'neutro'
    trecho TEXT,                       -- citação literal da review
    trecho_literal BOOLEAN DEFAULT FALSE,
    resumo TEXT,                       -- paráfrase curta em português (base do cluster)
    embedding VECTOR(384),
    theme_id INT REFERENCES themes(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS review_aspects_review_idx ON review_aspects (review_id);
CREATE INDEX IF NOT EXISTS review_aspects_theme_idx ON review_aspects (theme_id);

-- Recorrência de cada tema por gênero (pré-calculada por scripts/compute_theme_stats.py).
CREATE TABLE IF NOT EXISTS theme_stats (
    id SERIAL PRIMARY KEY,
    genre_id INT NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    theme_id INT NOT NULL REFERENCES themes(id) ON DELETE CASCADE,
    reviews_com_tema INT NOT NULL,
    total_reviews INT NOT NULL,
    prevalencia NUMERIC,
    wilson_low NUMERIC,
    wilson_high NUMERIC,
    jogos_distintos INT,
    total_jogos INT,
    votos_uteis INT,
    pct_recomendadas_com_tema NUMERIC,
    p_value NUMERIC,
    p_value_ajustado NUMERIC,          -- Benjamini-Hochberg dentro do gênero
    log_odds NUMERIC,
    significativo BOOLEAN,
    jogos_exemplo JSONB,
    citacoes JSONB,
    contexto JSONB,
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE (genre_id, theme_id)
);

-- Importância de cada feature no RF de recomendação. genre_id NULL = modelo global.
CREATE TABLE IF NOT EXISTS genre_drivers (
    id SERIAL PRIMARY KEY,
    genre_id INT REFERENCES genres(id) ON DELETE CASCADE,
    feature TEXT NOT NULL,
    rotulo TEXT NOT NULL,
    tipo TEXT NOT NULL,                -- 'tema' | 'contexto'
    importancia NUMERIC,
    importancia_std NUMERIC,
    direcao TEXT,                      -- 'aumenta' | 'reduz' a recomendação
    taxa_recomendacao_com NUMERIC,
    taxa_recomendacao_sem NUMERIC,
    suporte INT,
    modelo_f1 NUMERIC,
    modelo_roc_auc NUMERIC,
    n_amostras INT,
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS genre_drivers_genre_idx ON genre_drivers (genre_id);

-- genre_insights (um aspecto fixo por gênero) foi substituído por theme_stats.
DROP TABLE IF EXISTS genre_insights;

-- Gold standard multi-aspecto: cada anotação é uma lista JSON de {categoria, sentimento}.
-- Só derruba a versão antiga (um aspecto por anotador); reexecuções preservam as anotações.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'absa_gold_standard' AND column_name = 'aspecto_anotador1'
    ) THEN
        DROP TABLE absa_gold_standard;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS absa_gold_standard (
    id SERIAL PRIMARY KEY,
    review_id INT NOT NULL UNIQUE REFERENCES reviews(id) ON DELETE CASCADE,
    anotador1 JSONB,
    anotador2 JSONB,
    consenso JSONB,
    gemini JSONB,
    updated_at TIMESTAMP DEFAULT now()
);
