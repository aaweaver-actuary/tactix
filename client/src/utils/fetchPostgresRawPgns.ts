import { API_BASE, PostgresRawPgnsSummary } from '../api';
import { getAuthHeaders } from './getAuthHeaders';

export default async function fetchPostgresRawPgns(): Promise<PostgresRawPgnsSummary> {
  const response = await fetch(`${API_BASE}/api/postgres/raw_pgns`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Postgres raw PGNs fetch failed: ${response.status}`);
  }
  return (await response.json()) as PostgresRawPgnsSummary;
}
