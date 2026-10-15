-- Pixel Oracle — remove a estimativa de vendas (método Boxleiter: total de reviews × multiplicador
-- pelo ano de lançamento). Sem base empírica para o mercado estudado; não é usada em nenhuma análise.
-- Idempotente: em banco novo a coluna já não existe (001 não a cria mais).

ALTER TABLE games DROP COLUMN IF EXISTS owners_estimados;

UPDATE games
SET raw_metadata = raw_metadata - 'vendas_estimadas' - 'multiplicador_boxleiter'
WHERE raw_metadata ?| ARRAY['vendas_estimadas', 'multiplicador_boxleiter'];
