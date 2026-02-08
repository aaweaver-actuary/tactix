import {
  PostgresAnalysisResponse,
  PostgresRawPgnsSummary,
  PostgresStatus,
} from '../api';
import { fetchPostgresResource } from '../utils/fetchPostgresResource';

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
