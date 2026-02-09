import MetricCard from './MetricCard';
import { DashboardPayload } from '../api';

interface MetricsSummaryGridProps {
  positions: number;
  tactics: number;
  metricsVersion: number;
  sourceSync?: DashboardPayload['source_sync'];
}

const formatSourceLabel = (source: string) => {
  if (source === 'lichess') return 'Lichess';
  if (source === 'chesscom') return 'Chess.com';
  return source;
};

export default function MetricsSummaryGrid({
  positions,
  tactics,
  metricsVersion,
  sourceSync,
}: MetricsSummaryGridProps) {
  const sourceCards = sourceSync?.sources ?? [];
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <MetricCard
        title="Positions"
        value={`${positions}`}
        note="Captured when you were to move"
      />
      <MetricCard
        title="Tactics"
        value={`${tactics}`}
        note="Analyzed via Stockfish"
      />
      <MetricCard
        title="Metrics ver."
        value={`${metricsVersion}`}
        note="Cache bust signal"
      />
      {sourceCards.map((row) => (
        <MetricCard
          key={row.source}
          title={`${formatSourceLabel(row.source)} (${sourceSync?.window_days}d)`}
          value={`${row.games_played}`}
          note={
            row.synced
              ? 'Synced from imported games'
              : 'No games synced in this window'
          }
          dataTestId={`source-sync-${row.source}`}
        />
      ))}
    </div>
  );
}
