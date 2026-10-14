import type { GamePitch } from "../../domain/entities/GamePitch.js";

/**
 * Valida e normaliza o pitch do frontend/dev.
 * Aliases (name, ideia, description) existem para facilitar integração.
 * Campos do formulário antigo (categories, release_year, flags…) são ignorados:
 * o dashboard só precisa do texto do pitch e dos gêneros.
 */
export function parseGamePitch(body: unknown): GamePitch {
  if (!body || typeof body !== "object") {
    throw new Error("Body JSON inválido.");
  }

  const b = body as Record<string, unknown>;
  const titulo = String(b.titulo ?? b.name ?? "").trim();
  const descricao = String(b.descricao ?? b.ideia ?? b.description ?? "").trim();

  if (!titulo) {
    throw new Error("Campo obrigatório: titulo (título do jogo).");
  }
  if (descricao.length < 10) {
    throw new Error("Campo obrigatório: descricao ou ideia (mínimo 10 caracteres).");
  }
  if (!Array.isArray(b.genres) || b.genres.length === 0) {
    throw new Error("Campo obrigatório: genres.");
  }
  if (b.price_brl !== undefined && (typeof b.price_brl !== "number" || b.price_brl < 0)) {
    throw new Error("price_brl deve ser um número >= 0.");
  }
  if (b.top_k !== undefined && (typeof b.top_k !== "number" || b.top_k < 1 || b.top_k > 20)) {
    throw new Error("top_k deve ser um número entre 1 e 20.");
  }

  return {
    titulo,
    descricao,
    genres: b.genres.map(String),
    price_brl: typeof b.price_brl === "number" ? b.price_brl : undefined,
    top_k: typeof b.top_k === "number" ? b.top_k : undefined,
  };
}
