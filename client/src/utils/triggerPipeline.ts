import { DashboardPayload } from '../api';
import triggerDashboardJob from './triggerDashboardJob';

export default async function triggerPipeline(
  source?: string,
): Promise<DashboardPayload> {
  return triggerDashboardJob('/api/jobs/daily_game_sync', { source }, source);
}
