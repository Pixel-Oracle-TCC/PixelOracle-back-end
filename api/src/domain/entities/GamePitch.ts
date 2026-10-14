/**
 * Pitch do desenvolvedor antes do lançamento na Steam.
 * Só o necessário para achar jogos parecidos e os gêneros de referência.
 */
export interface GamePitch {
  titulo: string;
  descricao: string;
  genres: string[];
  price_brl?: number;
  /** Quantos jogos similares usar (padrão do ml-service: 5). */
  top_k?: number;
}
