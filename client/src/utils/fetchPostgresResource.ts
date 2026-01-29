import { API_BASE } from '../api';
import { getAuthHeaders } from './getAuthHeaders';

/**
 * Fetch a Postgres API resource with auth headers and shared error handling.
 */
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
