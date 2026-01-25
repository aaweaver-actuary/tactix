import { authHeaders } from '../api';

export function getAuthHeaders(): Record<string, string> {
  return authHeaders;
}
