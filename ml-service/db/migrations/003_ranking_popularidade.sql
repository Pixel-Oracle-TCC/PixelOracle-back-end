-- Pixel Oracle — ranking de popularidade para popular o catálogo dos mais vendidos para os menos.
-- Idempotente. Conformidade: o top sellers da Steam é agregado por jogo, sem vínculo a usuário.

-- Posição do jogo no ranking de mais vendidos (top sellers semanal da Steam somado em N semanas;
-- 1 = mais vendido). NULL = jogo fora do ranking da última execução de scripts/collect_top_games.py.
ALTER TABLE games ADD COLUMN IF NOT EXISTS rank_popularidade INT;
CREATE INDEX IF NOT EXISTS games_rank_popularidade_idx ON games (rank_popularidade);

-- Apps do ranking que não viram jogo no catálogo (software, DLC, sem página na Store BR).
-- Guardados só para não reconsultar a Store a cada execução.
CREATE TABLE IF NOT EXISTS apps_ignorados (
    steam_appid INT PRIMARY KEY,
    titulo TEXT,
    motivo TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);
