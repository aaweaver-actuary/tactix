import {
  PracticeAttemptRequest,
  PracticeAttemptResponse,
  client,
} from '../api';

export default async function submitPracticeAttempt(
  payload: PracticeAttemptRequest,
): Promise<PracticeAttemptResponse> {
  const res = await client.post<PracticeAttemptResponse>(
    '/api/practice/attempt',
    payload,
  );
  return res.data;
}
