import { PostgresRawPgnsSummary } from '../api';
import { fetchPostgresResource } from './fetchPostgresResource';

export default async function fetchPostgresRawPgns(): Promise<PostgresRawPgnsSummary> {
  return fetchPostgresResource<PostgresRawPgnsSummary>('raw_pgns', 'raw PGNs');
}
