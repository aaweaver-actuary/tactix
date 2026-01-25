import { PracticeAttemptResponse } from '../api';

export default function buildPracticeFeedback(
  practiceFeedback: PracticeAttemptResponse,
): string {
  return `You played ${practiceFeedback.attempted_uci} · best ${practiceFeedback.best_uci || '--'}`;
}
