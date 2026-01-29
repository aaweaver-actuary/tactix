import { GameDetailResponse, client } from '../api';

export default async function fetchGameDetail(
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
