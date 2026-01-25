import { SetStateAction } from 'react';

interface PracticeMoveInputProps {
  practiceMove: string;
  setPracticeMove: React.Dispatch<SetStateAction<string>>;
  practiceSubmitting: boolean;
}

/**
 * Renders an input field for entering a chess move in UCI format.
 *
 * @param practiceMove - The current value of the move input.
 * @param setPracticeMove - Function to update the move input value.
 * @param practiceSubmitting - Boolean indicating if the move is being submitted, disables input when true.
 *
 * @returns A styled input element for move entry.
 */
export default function PracticeMoveInput({
  practiceMove,
  setPracticeMove,
  practiceSubmitting,
}: PracticeMoveInputProps) {
  return (
    <input
      value={practiceMove}
      onChange={(event) => setPracticeMove(event.target.value)}
      placeholder="Enter your move (UCI e.g., e2e4)"
      className="flex-1 min-w-[220px] rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand placeholder:text-sand/40"
      disabled={practiceSubmitting}
    />
  );
}
