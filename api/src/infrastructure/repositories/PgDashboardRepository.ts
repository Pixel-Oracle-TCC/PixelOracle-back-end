import type { Pool } from "pg";
import type {
  GamesByGenre,
  IDashboardRepository,
  OverviewKpis,
  ReleasesByMonth,
} from "../../domain/ports/IDashboardRepository.js";

type OverviewRow = {
  total_games: number | string | null;
  pct_free: number | string | null;
  median_price: number | string | null;
  avg_positive_rate: number | string | null;
};

type ReleasesRow = {
  month: string;
  releases: number | string | null;
  pct_free: number | string | null;
};

type GenreRow = {
  genre: string;
  games: number | string | null;
  pct: number | string | null;
};

function asNumber(value: number | string | null | undefined, fallback = 0): number {
  if (value === null || value === undefined) {
    return fallback;
  }
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function asNullableNumber(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export class PgDashboardRepository implements IDashboardRepository {
  constructor(private readonly pool: Pool) {}

  async getOverview(): Promise<OverviewKpis> {
    const result = await this.pool.query<OverviewRow>(
      `
      WITH catalog AS (
        SELECT
          COUNT(*)::int AS total_games,
          COALESCE(
            (100.0 * COUNT(*) FILTER (WHERE g.preco_brl = 0) / NULLIF(COUNT(*), 0))::float,
            0
          ) AS pct_free
        FROM games g
      ),
      median AS (
        SELECT
          percentile_cont(0.5) WITHIN GROUP (ORDER BY lp.final_price)::float AS median_price
        FROM latest_prices lp
        WHERE lp.final_price > 0
      ),
      sentiment AS (
        SELECT
          AVG(
            100.0 * lr.total_positive / NULLIF(lr.total_positive + lr.total_negative, 0)
          )::float AS avg_positive_rate
        FROM latest_reviews lr
      )
      SELECT
        catalog.total_games,
        catalog.pct_free,
        median.median_price,
        sentiment.avg_positive_rate
      FROM catalog, median, sentiment
      `
    );

    const row = result.rows[0];
    if (!row) {
      return {
        totalGames: 0,
        pctFree: 0,
        medianPrice: null,
        avgPositiveRate: null,
      };
    }

    return {
      totalGames: asNumber(row.total_games),
      pctFree: asNumber(row.pct_free),
      medianPrice: asNullableNumber(row.median_price),
      avgPositiveRate: asNullableNumber(row.avg_positive_rate),
    };
  }

  async getReleasesByMonth(from: string, to: string): Promise<ReleasesByMonth[]> {
    const result = await this.pool.query<ReleasesRow>(
      `
      SELECT
        to_char(date_trunc('month', g.release_date), 'YYYY-MM') AS month,
        COUNT(*)::int AS releases,
        COALESCE(
          (100.0 * COUNT(*) FILTER (WHERE g.preco_brl = 0) / NULLIF(COUNT(*), 0))::float,
          0
        ) AS pct_free
      FROM games g
      WHERE g.release_date >= $1::date
        AND g.release_date <= $2::date
      GROUP BY 1
      ORDER BY 1
      `,
      [from, to]
    );

    return result.rows.map((row) => ({
      month: row.month,
      releases: asNumber(row.releases),
      pctFree: asNumber(row.pct_free),
    }));
  }

  async getGamesByGenre(): Promise<GamesByGenre[]> {
    const result = await this.pool.query<GenreRow>(
      `
      SELECT
        gen.nome AS genre,
        COUNT(DISTINCT gg.game_id)::int AS games,
        COALESCE(
          (100.0 * COUNT(DISTINCT gg.game_id) / NULLIF((SELECT COUNT(*) FROM games), 0))::float,
          0
        ) AS pct
      FROM genres gen
      INNER JOIN game_genres gg ON gg.genre_id = gen.id
      GROUP BY gen.id, gen.nome
      ORDER BY games DESC, gen.nome
      `
    );

    return result.rows.map((row) => ({
      genre: row.genre,
      games: asNumber(row.games),
      pct: asNumber(row.pct),
    }));
  }
}
