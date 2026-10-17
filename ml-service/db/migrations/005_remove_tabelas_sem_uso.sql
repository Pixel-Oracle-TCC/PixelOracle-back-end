-- Pixel Oracle — remove tabelas que nenhum código grava ou lê. Idempotente.

-- Histórico de pitches: o /analyze nunca persistiu os relatórios.
DROP TABLE IF EXISTS triangulation_reports;
