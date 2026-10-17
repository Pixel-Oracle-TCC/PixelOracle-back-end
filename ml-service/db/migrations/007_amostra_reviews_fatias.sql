-- Pixel Oracle — amostra de reviews: fatias múltiplas, received_for_free, snapshots dual.
-- Idempotente. Conformidade: sem colunas de autor.

-- Uma review, várias fatias (util_positiva ∩ proporcional, etc.). Métricas usam
-- 'proporcional' = ANY(fatias); úteis ficam para citações.
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS fatias TEXT[] NOT NULL DEFAULT '{}';
UPDATE reviews
SET fatias = ARRAY[tipo_amostra]
WHERE tipo_amostra IS NOT NULL
  AND tipo_amostra <> ''
  AND (fatias IS NULL OR fatias = '{}');

CREATE INDEX IF NOT EXISTS reviews_fatias_gin_idx ON reviews USING GIN (fatias);

-- Metadado público da review (não identifica o autor)
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS received_for_free BOOLEAN;

-- Totais sem filtro de offtopic (quando a Steam diferenciar) — review bombing
ALTER TABLE review_snapshots ADD COLUMN IF NOT EXISTS total_positive_unfiltered INT;
ALTER TABLE review_snapshots ADD COLUMN IF NOT EXISTS total_negative_unfiltered INT;
ALTER TABLE review_snapshots ADD COLUMN IF NOT EXISTS total_reviews_unfiltered INT;

-- Jogos com poucas reviews na Steam: fora das métricas (ainda podem ter citações)
ALTER TABLE games ADD COLUMN IF NOT EXISTS elegivel_metricas BOOLEAN NOT NULL DEFAULT TRUE;
