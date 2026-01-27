import { API_BASE, PostgresAnalysisResponse } from '../api';
import { getAuthHeaders } from './getAuthHeaders';

export default async function fetchPostgresAnalysis(): Promise<PostgresAnalysisResponse> {
  const response = await fetch(`${API_BASE}/api/postgres/analysis`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Postgres analysis fetch failed: ${response.status}`);
  }
  return (await response.json()) as PostgresAnalysisResponse;
}
