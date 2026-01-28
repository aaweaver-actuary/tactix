import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseCard from './BaseCard';
import Text from './Text';

interface PositionsListProps {
  positionsData: DashboardPayload['positions'];
}

/**
 * Renders a list of chess positions with their FEN strings, move numbers, SAN notation, and clock times.
 *
 * @param positionsData - An array of position objects containing details for each chess position.
 *
 * Each position object should have the following properties:
 * - position_id: Unique identifier for the position.
 * - fen: FEN string representing the chess board state.
 * - move_number: The move number in the game.
 * - san: The move in Standard Algebraic Notation.
 * - clock_seconds: (Optional) Number of seconds remaining on the clock for the position.
 *
 * Displays a header with a badge, and for each position, shows its FEN, move details, and clock time.
 */
export default function PositionsList({ positionsData }: PositionsListProps) {
  const header = (
    <div className="flex items-center justify-between">
      <h3 className="text-lg font-display text-sand">Latest positions</h3>
      <Badge label="Fen" />
    </div>
  );

  return (
    <BaseCard className="p-4" header={header} contentClassName="pt-3">
      <div className="flex flex-col gap-3">
        {positionsData.map((pos) => (
          <div
            key={pos.position_id}
            className="flex items-center justify-between text-sm border-b border-white/10 pb-2"
          >
            <div>
              <Text mode="monospace" size="xs" value={pos.fen} />
              <Text mt="2" value={`Move ${pos.move_number} · ${pos.san}`} />
            </div>
            <Badge label={`${pos.clock_seconds ?? '--'}s`} />
          </div>
        ))}
      </div>
    </BaseCard>
  );
}
