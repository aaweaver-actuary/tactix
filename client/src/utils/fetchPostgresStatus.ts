import { API_BASE, PostgresStatus } from '../api';
import { getAuthHeaders } from './getAuthHeaders';

export default async function fetchPostgresStatus(): Promise<PostgresStatus> {
  const response = await fetch(`${API_BASE}/api/postgres/status`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Postgres status fetch failed: ${response.status}`);
  }
  return (await response.json()) as PostgresStatus;
}
