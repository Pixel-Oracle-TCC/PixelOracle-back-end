/**
 * Pitch do desenvolvedor antes do lançamento na Steam.
 * Sem reviews, vendas ou notas de usuários.
 */
export interface GamePitch {
  titulo: string;
  descricao: string;

  price_brl: number;
  genres: string[];
  categories: string[];
  release_year: number;
  period_time?: string;

  platforms?: number;
  supported_languages?: number;
  dlc?: number;
  achievements?: number;
  metacritic?: number;
  required_age_num?: number;

  singleplayer?: boolean;
  multiplayer?: boolean;
  is_online?: boolean;
  indie?: boolean;
  early_access?: boolean;
  trading_cards?: boolean;
  workshop?: boolean;
  is_free?: boolean;
  coming_soon?: boolean;
  adult_content?: boolean;

  controller_support?: string;
  type?: string;
}

export type MlGamePayload = Omit<GamePitch, "titulo" | "descricao">;
