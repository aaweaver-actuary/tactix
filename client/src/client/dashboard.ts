import {
  DashboardFilters,
  DashboardPayload,
  GameDetailResponse,
  client,
} from '../api';

export async function fetchDashboard(
  source?: string,
  filters: DashboardFilters = {},
): Promise<DashboardPayload> {
  const params = Object.fromEntries(
    Object.entries({
      t: Date.now(),
      source: source === 'all' ? undefined : source,
      ...filters,
    }).filter(([, value]) => value !== undefined && value !== ''),
  );
  const res = await client.get<DashboardPayload>('/api/dashboard', {
    params,
  });
  return res.data;
}

export async function fetchGameDetail(
  gameId: string,
  source?: string,
): Promise<GameDetailResponse> {
  const params = Object.fromEntries(
    Object.entries({
      source: source === 'all' ? undefined : source,
    }).filter(([, value]) => value !== undefined && value !== ''),
  );
  const res = await client.get<GameDetailResponse>(
    `/api/games/${encodeURIComponent(gameId)}`,
    {
      params,
    },
  );
  return res.data;
}
