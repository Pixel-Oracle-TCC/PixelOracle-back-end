-- Pixel Oracle — schema definitivo (PostgreSQL + pgvector)
-- Conformidade: reviews NÃO persistem steamid de autor (dedup por recommendationid).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    steam_appid INT UNIQUE,
    titulo TEXT NOT NULL,
    descricao TEXT,
    preco_brl NUMERIC,
    release_year INT,
    owners_estimados INT,
    raw_metadata JSONB,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS genres (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS game_genres (
    game_id INT REFERENCES games(id) ON DELETE CASCADE,
    genre_id INT REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, genre_id)
);

-- Sem coluna de identificação de autor (steamid). Dedup por recommendationid.
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    game_id INT REFERENCES games(id) ON DELETE CASCADE,
    recommendationid TEXT UNIQUE,
    texto TEXT,
    recomendada BOOLEAN,
    votos_uteis INT,
    playtime_at_review INT,
    tipo_amostra TEXT,          -- 'positiva' | 'negativa' | 'recente'
    aspecto TEXT,
    sentimento TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS genre_insights (
    id SERIAL PRIMARY KEY,
    genre_id INT REFERENCES genres(id) ON DELETE CASCADE,
    aspecto TEXT,
    frequencia_positiva INT DEFAULT 0,
    frequencia_negativa INT DEFAULT 0,
    significancia NUMERIC,
    resumo TEXT,
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE (genre_id, aspecto)
);

CREATE TABLE IF NOT EXISTS triangulation_reports (
    id SERIAL PRIMARY KEY,
    projeto_pitch JSONB,
    resultado JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS absa_gold_standard (
    id SERIAL PRIMARY KEY,
    review_id INT REFERENCES reviews(id) ON DELETE CASCADE,
    aspecto_anotador1 TEXT,
    sentimento_anotador1 TEXT,
    aspecto_anotador2 TEXT,
    sentimento_anotador2 TEXT,
    aspecto_gemini TEXT,
    sentimento_gemini TEXT
);

-- Índice vetorial: criar DEPOIS de popular embeddings (script offline).
-- Em bases vazias/pequenas a query sequencial funciona sem o índice.
-- Exemplo (rode manualmente após backfill):
--   CREATE INDEX IF NOT EXISTS games_embedding_ivfflat_idx
--       ON games USING ivfflat (embedding vector_cosine_ops)
--       WITH (lists = 100);
