import { getAuthHeaders } from '../utils/getAuthHeaders';
import getJobStreamUrl from '../utils/getJobStreamUrl';
import getMetricsStreamUrl from '../utils/getMetricsStreamUrl';

export { getJobStreamUrl, getMetricsStreamUrl };

export async function openEventStream(
  streamUrl: string,
  signal: AbortSignal,
): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const response = await fetch(streamUrl, {
    headers: getAuthHeaders(),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`Stream failed with status ${response.status}`);
  }
  return response.body.getReader();
}
