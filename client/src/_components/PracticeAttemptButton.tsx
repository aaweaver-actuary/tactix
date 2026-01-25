interface PracticeAttemptButtonProps {
  handlePracticeAttempt: (overrideMove?: string) => Promise<void>;
  practiceSubmitting: boolean;
}

/**
 * Renders a button for submitting a practice attempt.
 *
 * @param handlePracticeAttempt - Function to handle the practice attempt submission. Accepts an optional overrideMove string and returns a Promise.
 * @param practiceSubmitting - Boolean indicating whether the submission is in progress. Disables the button and shows a loading state when true.
 *
 * The button displays "Submit attempt" by default, and "Submitting…" while the submission is in progress.
 */
export default function PracticeAttemptButton({
  handlePracticeAttempt,
  practiceSubmitting,
}: PracticeAttemptButtonProps) {
  return (
    <button
      className="button bg-teal text-night px-4 py-2 rounded-md font-display"
      onClick={() => handlePracticeAttempt()}
      disabled={practiceSubmitting}
    >
      {practiceSubmitting ? 'Submitting…' : 'Submit attempt'}
    </button>
  );
}
