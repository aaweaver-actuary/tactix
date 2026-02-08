import {
  PracticeAttemptRequest,
  PracticeAttemptResponse,
  PracticeQueueResponse,
  client,
} from '../api';

export async function fetchPracticeQueue(
  source?: string,
  includeFailedAttempt = false,
): Promise<PracticeQueueResponse> {
  const rawLimit = (import.meta.env.VITE_PRACTICE_QUEUE_LIMIT || '').trim();
  const parsedLimit = rawLimit ? Number(rawLimit) : null;
  const limit =
    parsedLimit && Number.isFinite(parsedLimit) && parsedLimit > 0
      ? parsedLimit
      : undefined;
  const params = Object.fromEntries(
    Object.entries({
      source: source === 'all' ? undefined : source,
      include_failed_attempt: includeFailedAttempt,
      limit,
    }).filter(([, value]) => value !== undefined),
  );
  const res = await client.get<PracticeQueueResponse>('/api/practice/queue', {
    params,
  });
  return res.data;
}

export async function submitPracticeAttempt(
  payload: PracticeAttemptRequest,
): Promise<PracticeAttemptResponse> {
  const res = await client.post<PracticeAttemptResponse>(
    '/api/practice/attempt',
    payload,
  );
  return res.data;
}
