-- Pixel Oracle — views e índices para KPIs do dashboard (API).
-- Idempotente. Não altera tabelas. Conformidade: só dados de jogo.
--
-- Schema real (migrations 001–007): `games` + `review_snapshots`.
-- Não existem `game`, `price_snapshot` nem `review_snapshot`.
-- Gratuito = `games.preco_brl = 0` (enrich da Steam grava 0.0 quando is_free).

CREATE OR REPLACE VIEW latest_prices AS
SELECT
    g.id AS game_id,
    g.steam_appid,
    g.preco_brl AS final_price
FROM games g;

CREATE OR REPLACE VIEW latest_reviews AS
SELECT DISTINCT ON (rs.game_id)
    rs.game_id,
    rs.total_positive,
    rs.total_negative,
    rs.collected_at
FROM review_snapshots rs
ORDER BY rs.game_id, rs.collected_at DESC;

CREATE INDEX IF NOT EXISTS games_release_date_idx ON games (release_date);

-- Já criado em 006; IF NOT EXISTS torna este arquivo seguro de reexecutar.
CREATE INDEX IF NOT EXISTS review_snapshots_game_collected_idx
    ON review_snapshots (game_id, collected_at DESC);
