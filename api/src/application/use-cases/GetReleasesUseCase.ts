import type {
  IDashboardRepository,
  ReleasesByMonth,
} from "../../domain/ports/IDashboardRepository.js";

export class GetReleasesUseCase {
  constructor(private readonly dashboardRepository: IDashboardRepository) {}

  execute(from: string, to: string): Promise<ReleasesByMonth[]> {
    return this.dashboardRepository.getReleasesByMonth(from, to);
  }
}
