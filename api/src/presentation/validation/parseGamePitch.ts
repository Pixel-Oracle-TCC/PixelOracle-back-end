import type { GamePitch } from "../../domain/entities/GamePitch.js";

const POST_LAUNCH_KEYS = [
  "total_reviews",
  "total_positive",
  "user_score",
  "score_desc",
  "multiplicador_boxleiter",
  "vendas_estimadas",
] as const;

export function parseGamePitch(body: unknown): GamePitch {
  if (!body || typeof body !== "object") {
    throw new Error("Body JSON inválido.");
  }

  const b = body as Record<string, unknown>;

  for (const key of POST_LAUNCH_KEYS) {
    if (b[key] !== undefined) {
      throw new Error(
        `Campo "${key}" não é aceito: o jogo ainda não foi lançado na Steam. ` +
          "Use titulo, descricao e metadados planejados."
      );
    }
  }

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
  if (!Array.isArray(b.categories) || b.categories.length === 0) {
    throw new Error("Campo obrigatório: categories.");
  }
  if (typeof b.price_brl !== "number" || b.price_brl < 0) {
    throw new Error("Campo obrigatório: price_brl (número >= 0).");
  }
  if (typeof b.release_year !== "number") {
    throw new Error("Campo obrigatório: release_year.");
  }

  return {
    titulo,
    descricao,
    price_brl: b.price_brl,
    genres: b.genres.map(String),
    categories: b.categories.map(String),
    release_year: b.release_year,
    period_time: b.period_time != null ? String(b.period_time) : undefined,
    platforms: num(b.platforms, 1),
    supported_languages: num(b.supported_languages, 1),
    dlc: num(b.dlc, 0),
    achievements: num(b.achievements, 0),
    metacritic: num(b.metacritic, 0),
    required_age_num: num(b.required_age_num, 0),
    singleplayer: bool(b.singleplayer, true),
    multiplayer: bool(b.multiplayer, false),
    is_online: bool(b.is_online, false),
    indie: bool(b.indie, true),
    early_access: bool(b.early_access, false),
    trading_cards: bool(b.trading_cards, false),
    workshop: bool(b.workshop, false),
    is_free: bool(b.is_free, false),
    coming_soon: bool(b.coming_soon, true),
    adult_content: bool(b.adult_content, false),
    controller_support: String(b.controller_support ?? "none"),
    type: String(b.type ?? "game"),
  };
}

function num(value: unknown, fallback: number): number {
  return typeof value === "number" ? value : fallback;
}

function bool(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}
