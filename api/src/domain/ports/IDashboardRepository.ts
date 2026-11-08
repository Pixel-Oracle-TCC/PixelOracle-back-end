export type OverviewKpis = {
  totalGames: number;
  pctFree: number;
  medianPrice: number | null;
  avgPositiveRate: number | null;
};

export type ReleasesByMonth = {
  month: string;
  releases: number;
  pctFree: number;
};

export type GamesByGenre = {
  genre: string;
  games: number;
  pct: number;
};

export interface IDashboardRepository {
  getOverview(): Promise<OverviewKpis>;
  getReleasesByMonth(from: string, to: string): Promise<ReleasesByMonth[]>;
  getGamesByGenre(): Promise<GamesByGenre[]>;
}
