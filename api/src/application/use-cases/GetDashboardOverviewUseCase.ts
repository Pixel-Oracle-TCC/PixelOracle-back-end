import type {
  GamesByGenre,
  IDashboardRepository,
  OverviewKpis,
  ReleasesByMonth,
} from "../../domain/ports/IDashboardRepository.js";

export type DashboardOverviewResult = {
  overview: OverviewKpis;
  releases: ReleasesByMonth[];
  genres: GamesByGenre[];
};

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function lastTwelveMonthsRange(): { from: string; to: string } {
  const to = new Date();
  const from = new Date(to);
  from.setUTCMonth(from.getUTCMonth() - 12);
  return { from: toIsoDate(from), to: toIsoDate(to) };
}

export class GetDashboardOverviewUseCase {
  constructor(private readonly dashboardRepository: IDashboardRepository) {}

  async execute(genre: string | null = null): Promise<DashboardOverviewResult> {
    const { from, to } = lastTwelveMonthsRange();
    const [overview, releases, genres] = await Promise.all([
      this.dashboardRepository.getOverview(genre),
      this.dashboardRepository.getReleasesByMonth(from, to, genre),
      this.dashboardRepository.getGamesByGenre(genre),
    ]);
    return { overview, releases, genres };
  }
}
