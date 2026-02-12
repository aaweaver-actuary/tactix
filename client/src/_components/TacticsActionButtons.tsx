import type { MouseEvent } from 'react';
import { DashboardPayload } from '../api';
import ActionButton from './ActionButton';

const BUTTON_CLASSES =
  'rounded border border-white/10 px-2 py-1 text-xs text-sand/80 hover:border-white/30 disabled:cursor-not-allowed disabled:border-white/5 disabled:text-sand/40';

const handleActionClick = (
  event: MouseEvent<HTMLButtonElement>,
  enabled: boolean,
  action: () => void,
) => {
  event.stopPropagation();
  if (!enabled) return;
  action();
};

export const __test__ = { handleActionClick };

type TacticsActionButtonsProps = {
  tactic: DashboardPayload['tactics'][number];
  onOpenGameDetail: (tactic: DashboardPayload['tactics'][number]) => void;
  onOpenLichess: (tactic: DashboardPayload['tactics'][number]) => void;
};

export default function TacticsActionButtons({
  tactic,
  onOpenGameDetail,
  onOpenLichess,
}: TacticsActionButtonsProps) {
  const hasGameId = Boolean(tactic.game_id);
  const gameId = tactic.game_id ?? 'unknown';

  return (
    <div className="flex flex-wrap gap-2">
      <ActionButton
        className={BUTTON_CLASSES}
        data-testid={`tactics-go-to-game-${gameId}`}
        aria-label="Go to game"
        disabled={!hasGameId}
        onClick={(event) =>
          handleActionClick(event, hasGameId, () => onOpenGameDetail(tactic))
        }
      >
        Go to Game
      </ActionButton>
      <ActionButton
        className={BUTTON_CLASSES}
        data-testid={`tactics-open-lichess-${gameId}`}
        aria-label="Open in Lichess"
        disabled={!hasGameId}
        onClick={(event) =>
          handleActionClick(event, hasGameId, () => onOpenLichess(tactic))
        }
      >
        Open in Lichess
      </ActionButton>
    </div>
  );
}
