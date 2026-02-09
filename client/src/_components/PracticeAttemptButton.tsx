import BaseButton from './BaseButton';

interface PracticeAttemptButtonProps {
  onPracticeAttempt: () => void;
  practiceSubmitting: boolean;
}

/**
 * Renders a button for submitting a practice attempt.
 *
 * @param onPracticeAttempt - Function to handle the practice attempt submission.
 * @param practiceSubmitting - Boolean indicating whether the submission is in progress. Disables the button and shows a loading state when true.
 *
 * The button displays "Submit attempt" by default, and "Submitting…" while the submission is in progress.
 */
export default function PracticeAttemptButton({
  onPracticeAttempt,
  practiceSubmitting,
}: PracticeAttemptButtonProps) {
  return (
    <BaseButton
      className="button bg-teal text-night px-4 py-2 rounded-md font-display"
      onClick={onPracticeAttempt}
      disabled={practiceSubmitting}
    >
      {practiceSubmitting ? 'Submitting…' : 'Submit attempt'}
    </BaseButton>
  );
}
