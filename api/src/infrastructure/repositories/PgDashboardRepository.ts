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

function genreMatch(placeholder: string): string {
  return `(${placeholder}::text IS NULL OR EXISTS (
        SELECT 1
        FROM game_genres gg
        INNER JOIN genres gen ON gen.id = gg.genre_id
        WHERE gg.game_id = g.id
          AND gen.nome = ${placeholder}
      ))`;
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

  async getOverview(genre: string | null): Promise<OverviewKpis> {
    const match = genreMatch("$1");
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
        WHERE ${match}
      ),
      median AS (
        SELECT
          percentile_cont(0.5) WITHIN GROUP (ORDER BY g.preco_brl)::float AS median_price
        FROM games g
        WHERE g.preco_brl > 0
          AND ${match}
      ),
      sentiment AS (
        SELECT
          AVG(
            100.0 * lr.total_positive / NULLIF(lr.total_positive + lr.total_negative, 0)
          )::float AS avg_positive_rate
        FROM latest_reviews lr
        INNER JOIN games g ON g.id = lr.game_id
        WHERE ${match}
      )
      SELECT
        catalog.total_games,
        catalog.pct_free,
        median.median_price,
        sentiment.avg_positive_rate
      FROM catalog, median, sentiment
      `,
      [genre]
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

  async getReleasesByMonth(
    from: string,
    to: string,
    genre: string | null
  ): Promise<ReleasesByMonth[]> {
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
        AND ${genreMatch("$3")}
      GROUP BY 1
      ORDER BY 1
      `,
      [from, to, genre]
    );

    return result.rows.map((row) => ({
      month: row.month,
      releases: asNumber(row.releases),
      pctFree: asNumber(row.pct_free),
    }));
  }

  async getGamesByGenre(genre: string | null): Promise<GamesByGenre[]> {
    const result = await this.pool.query<GenreRow>(
      `
      WITH scoped AS (
        SELECT g.id
        FROM games g
        WHERE ${genreMatch("$1")}
      )
      SELECT
        gen.nome AS genre,
        COUNT(DISTINCT gg.game_id)::int AS games,
        COALESCE(
          (100.0 * COUNT(DISTINCT gg.game_id) / NULLIF((SELECT COUNT(*) FROM scoped), 0))::float,
          0
        ) AS pct
      FROM genres gen
      INNER JOIN game_genres gg ON gg.genre_id = gen.id
      INNER JOIN scoped s ON s.id = gg.game_id
      GROUP BY gen.id, gen.nome
      ORDER BY games DESC, gen.nome
      `,
      [genre]
    );

    return result.rows.map((row) => ({
      genre: row.genre,
      games: asNumber(row.games),
      pct: asNumber(row.pct),
    }));
  }
}
