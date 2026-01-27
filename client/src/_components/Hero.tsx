import { SOURCE_OPTIONS } from '../utils/SOURCE_OPTIONS';
import { LICHESS_PROFILE_LABELS } from '../utils/LICHESS_PROFILE_OPTIONS';
import { CHESSCOM_PROFILE_LABELS } from '../utils/CHESSCOM_PROFILE_OPTIONS';
import { ChessPlatform, ChesscomProfile, LichessProfile } from '../types';
import Text from './Text';

interface HeroProps {
  onRun: () => void;
  onBackfill: () => void;
  onRefresh: () => void;
  onMigrate: () => void;
  loading: boolean;
  version: number;
  source: ChessPlatform;
  profile?: LichessProfile;
  chesscomProfile?: ChesscomProfile;
  user: string;
  onSourceChange: (next: ChessPlatform) => void;
  backfillStartDate: string;
  backfillEndDate: string;
  onBackfillStartChange: (value: string) => void;
  onBackfillEndChange: (value: string) => void;
}

/**
 * Hero component displays the main controls and information for managing an Airflow DAG pipeline.
 *
 * @param onRun - Callback invoked when the "Run + Refresh" button is clicked.
 * @param onBackfill - Callback invoked when the "Backfill history" button is clicked.
 * @param onRefresh - Callback invoked when the "Refresh metrics" button is clicked.
 * @param onMigrate - Callback invoked when the "Run migrations" button is clicked.
 * @param loading - Boolean indicating if an operation is currently in progress, disabling buttons.
 * @param version - Metrics version string displayed in the component.
 * @param source - Current data source identifier (e.g., 'lichess' or 'chess.com').
 * @param user - User identifier displayed in the component.
 * @param onSourceChange - Callback invoked when the data source selection changes.
 *
 * The component renders pipeline information, source selection buttons, and action buttons for running, backfilling, migrating, and refreshing metrics.
 */
export default function Hero({
  onRun,
  onBackfill,
  onRefresh,
  onMigrate,
  loading,
  version,
  source,
  profile,
  chesscomProfile,
  user,
  onSourceChange,
  backfillStartDate,
  backfillEndDate,
  onBackfillStartChange,
  onBackfillEndChange,
}: HeroProps) {
  const lichessLabel = profile ? LICHESS_PROFILE_LABELS[profile] : 'Rapid';
  const chesscomLabel = chesscomProfile
    ? CHESSCOM_PROFILE_LABELS[chesscomProfile]
    : 'Blitz';

  return (
    <div className="card p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <Text mode="normal" size="sm" value="Airflow DAG · daily_game_sync" />
        <h1 className="text-3xl md:text-4xl font-display text-sand mt-2">
          {source === 'lichess'
            ? `Lichess ${lichessLabel.toLowerCase()} pipeline`
            : `Chess.com ${chesscomLabel.toLowerCase()} pipeline`}
        </h1>
        <Text
          mode="normal"
          size="sm"
          mt="2"
          value={`Execution stamped via metrics version ${version} · user ${user}`}
        />
        <div className="flex gap-2 mt-3 flex-wrap">
          {SOURCE_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              className={`button px-3 py-2 rounded-md border text-sm ${
                source === opt.id
                  ? 'bg-teal text-night border-teal'
                  : 'border-sand/30 text-sand'
              }`}
              onClick={() => onSourceChange(opt.id)}
              disabled={loading}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-3">
          <button
            className="button bg-teal text-night px-4 py-3 rounded-lg font-display"
            onClick={onRun}
            disabled={loading}
            data-testid="action-run"
          >
            {loading ? 'Running…' : 'Run + Refresh'}
          </button>
          <button
            className="button border border-teal/50 text-teal px-4 py-3 rounded-lg"
            onClick={onBackfill}
            disabled={loading}
            data-testid="action-backfill"
          >
            Backfill history
          </button>
          <button
            className="button border border-sand/40 text-sand px-4 py-3 rounded-lg"
            onClick={onMigrate}
            disabled={loading}
            data-testid="action-migrate"
          >
            Run migrations
          </button>
          <button
            className="button border border-sand/40 text-sand px-4 py-3 rounded-lg"
            onClick={onRefresh}
            disabled={loading}
            data-testid="action-refresh"
          >
            Refresh metrics
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-sand/70">
          <span className="uppercase tracking-wide">Backfill range</span>
          <label className="flex items-center gap-2">
            <span className="sr-only">Backfill start date</span>
            <input
              type="date"
              value={backfillStartDate}
              onChange={(event) => onBackfillStartChange(event.target.value)}
              className="rounded border border-sand/20 bg-night px-2 py-1 text-sand"
              data-testid="backfill-start"
              disabled={loading}
            />
          </label>
          <span>to</span>
          <label className="flex items-center gap-2">
            <span className="sr-only">Backfill end date</span>
            <input
              type="date"
              value={backfillEndDate}
              onChange={(event) => onBackfillEndChange(event.target.value)}
              className="rounded border border-sand/20 bg-night px-2 py-1 text-sand"
              data-testid="backfill-end"
              disabled={loading}
            />
          </label>
        </div>
      </div>
    </div>
  );
}
