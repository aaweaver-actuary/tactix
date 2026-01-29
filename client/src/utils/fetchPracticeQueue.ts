import { PracticeQueueResponse, client } from '../api';

export default async function fetchPracticeQueue(
  source?: string,
  includeFailedAttempt = false,
): Promise<PracticeQueueResponse> {
  const res = await client.get<PracticeQueueResponse>('/api/practice/queue', {
    params: {
      source: source === 'all' ? undefined : source,
      include_failed_attempt: includeFailedAttempt,
    },
  });
  return res.data;
}
