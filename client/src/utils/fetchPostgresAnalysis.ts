import { PostgresAnalysisResponse } from '../api';
import { fetchPostgresResource } from './fetchPostgresResource';

export default async function fetchPostgresAnalysis(): Promise<PostgresAnalysisResponse> {
  return fetchPostgresResource<PostgresAnalysisResponse>(
    'analysis',
    'analysis',
  );
}
