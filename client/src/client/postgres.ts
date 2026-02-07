import {
  API_BASE,
  PostgresAnalysisResponse,
  PostgresRawPgnsSummary,
  PostgresStatus,
} from '../api';
import { getAuthHeaders } from './streams';

export async function fetchPostgresResource<T>(
  path: string,
  errorLabel: string,
): Promise<T> {
  const response = await fetch(`${API_BASE}/api/postgres/${path}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Postgres ${errorLabel} fetch failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchPostgresStatus(): Promise<PostgresStatus> {
  return fetchPostgresResource<PostgresStatus>('status', 'status');
}

export async function fetchPostgresAnalysis(): Promise<PostgresAnalysisResponse> {
  return fetchPostgresResource<PostgresAnalysisResponse>(
    'analysis',
    'analysis',
  );
}

export async function fetchPostgresRawPgns(): Promise<PostgresRawPgnsSummary> {
  return fetchPostgresResource<PostgresRawPgnsSummary>('raw_pgns', 'raw PGNs');
}
