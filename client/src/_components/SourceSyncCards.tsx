import MetricCard from './MetricCard';
import { DashboardPayload } from '../api';

interface SourceSyncCardsProps {
  sourceSync?: DashboardPayload['source_sync'];
}

const formatSourceLabel = (source: string) => {
  if (source === 'lichess') return 'Lichess';
  if (source === 'chesscom') return 'Chess.com';
  return source;
};

export default function SourceSyncCards({ sourceSync }: SourceSyncCardsProps) {
  if (!sourceSync?.sources.length) return null;
  return (
    <>
      {sourceSync.sources.map((row) => (
        <MetricCard
          key={row.source}
          title={`${formatSourceLabel(row.source)} (${sourceSync.window_days}d)`}
          value={`${row.games_played}`}
          note={
            row.synced
              ? 'Synced from imported games'
              : 'No games synced in this window'
          }
          dataTestId={`source-sync-${row.source}`}
        />
      ))}
    </>
  );
}
