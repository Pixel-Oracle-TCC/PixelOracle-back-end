-- Pixel Oracle — metadados Steam extras + amostra + snapshots de reviews.
-- Idempotente. Conformidade: só dados de jogo; nenhuma coluna de autor.

-- Data completa de lançamento (além do release_year) e score numérico 1–9.
ALTER TABLE games ADD COLUMN IF NOT EXISTS release_date DATE;
ALTER TABLE games ADD COLUMN IF NOT EXISTS review_score INT;
-- Flag da amostra estratificada: collect_reviews só processa na_amostra = TRUE.
ALTER TABLE games ADD COLUMN IF NOT EXISTS na_amostra BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS games_na_amostra_idx ON games (na_amostra) WHERE na_amostra;

-- Categorias Steam (single-player, co-op, conquistas…) — N:N como genres.
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    steam_category_id INT UNIQUE NOT NULL,
    nome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_categories (
    game_id INT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    category_id INT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, category_id)
);

-- Desenvolvedoras e publicadoras (entidades comerciais do jogo, não pessoas).
CREATE TABLE IF NOT EXISTS developers (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS game_developers (
    game_id INT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    developer_id INT NOT NULL REFERENCES developers(id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, developer_id)
);

CREATE TABLE IF NOT EXISTS publishers (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS game_publishers (
    game_id INT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    publisher_id INT NOT NULL REFERENCES publishers(id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, publisher_id)
);

-- Idiomas suportados (lista limpa do HTML da Store).
CREATE TABLE IF NOT EXISTS languages (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS game_languages (
    game_id INT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    language_id INT NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, language_id)
);

-- Ponto zero e monitoramento de review bombing: totais oficiais da Steam no tempo.
CREATE TABLE IF NOT EXISTS review_snapshots (
    id SERIAL PRIMARY KEY,
    game_id INT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    total_positive INT,
    total_negative INT,
    total_reviews INT,
    review_score INT,
    review_score_desc TEXT,
    collected_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS review_snapshots_game_collected_idx
    ON review_snapshots (game_id, collected_at DESC);
