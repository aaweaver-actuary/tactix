import type { ReactNode } from 'react';
import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseCard, { BaseCardDragProps } from './BaseCard';
import Text from './Text';

type PositionEntry = DashboardPayload['positions'][number];

interface PositionsListProps extends BaseCardDragProps {
  positionsData: DashboardPayload['positions'];
  onPositionClick?: (position: PositionEntry) => void;
  rowTestId?: (position: PositionEntry, index: number) => string;
}

type PositionRowProps = {
  testId: string;
  onClick?: () => void;
  children: ReactNode;
};

const PositionRow = ({ testId, onClick, children }: PositionRowProps) => {
  const baseClassName =
    'flex items-center justify-between text-sm border-b border-white/10 pb-2';
  if (onClick) {
    return (
      <button
        type="button"
        data-testid={testId}
        onClick={onClick}
        className={`${baseClassName} w-full text-left`}
      >
        {children}
      </button>
    );
  }

  return (
    <div data-testid={testId} className={baseClassName}>
      {children}
    </div>
  );
};

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
export default function PositionsList({
  positionsData,
  onPositionClick,
  rowTestId,
  ...dragProps
}: PositionsListProps) {
  const resolveRowTestId =
    rowTestId ?? ((pos: PositionEntry) => `positions-row-${pos.position_id}`);

  const header = (
    <div className="flex items-center justify-between">
      <h3 className="text-lg font-display text-sand">Latest positions</h3>
      <Badge label="Fen" />
    </div>
  );

  return (
    <BaseCard
      className="p-4"
      header={header}
      contentClassName="pt-3"
      {...dragProps}
    >
      <div className="flex flex-col gap-3">
        {positionsData.map((pos, index) => {
          const testId = resolveRowTestId(pos, index);
          const rowContent = (
            <>
              <div>
                <Text mode="monospace" size="xs" value={pos.fen} />
                <Text mt="2" value={`Move ${pos.move_number} · ${pos.san}`} />
              </div>
              <Badge label={`${pos.clock_seconds ?? '--'}s`} />
            </>
          );

          return (
            <PositionRow
              key={pos.position_id}
              testId={testId}
              onClick={onPositionClick ? () => onPositionClick(pos) : undefined}
            >
              {rowContent}
            </PositionRow>
          );
        })}
      </div>
    </BaseCard>
  );
}
