import { PostgresStatus } from '../api';
import { fetchPostgresResource } from './fetchPostgresResource';

export default async function fetchPostgresStatus(): Promise<PostgresStatus> {
  return fetchPostgresResource<PostgresStatus>('status', 'status');
}
