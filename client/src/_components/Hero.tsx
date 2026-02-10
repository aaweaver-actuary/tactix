import { LICHESS_PROFILE_LABELS } from '../utils/LICHESS_PROFILE_OPTIONS';
import { CHESSCOM_PROFILE_LABELS } from '../utils/CHESSCOM_PROFILE_OPTIONS';
import { ChessPlatform, ChesscomProfile, LichessProfile } from '../types';
import BaseButton from './BaseButton';
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
  backfillStartDate: string;
  backfillEndDate: string;
  onBackfillStartChange: (value: string) => void;
  onBackfillEndChange: (value: string) => void;
}

interface HeroActionsProps {
  onRun: () => void;
  onBackfill: () => void;
  onRefresh: () => void;
  onMigrate: () => void;
  loading: boolean;
  disabled: boolean;
}

interface BackfillRangeProps {
  startDate: string;
  endDate: string;
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
  disabled: boolean;
}

const buildHeroTitle = (
  source: ChessPlatform,
  lichessLabel: string,
  chesscomLabel: string,
) => {
  if (source === 'all') return 'All sites overview';
  if (source === 'lichess') {
    return `Lichess ${lichessLabel.toLowerCase()} pipeline`;
  }
  return `Chess.com ${chesscomLabel.toLowerCase()} pipeline`;
};

const HeroActions = ({
  onRun,
  onBackfill,
  onRefresh,
  onMigrate,
  loading,
  disabled,
}: HeroActionsProps) => (
  <div className="flex flex-wrap gap-3">
    <BaseButton
      className="button bg-teal text-night px-4 py-3 rounded-lg font-display"
      onClick={onRun}
      disabled={disabled}
      data-testid="action-run"
    >
      {loading ? 'Running…' : 'Run + Refresh'}
    </BaseButton>
    <BaseButton
      className="button border border-teal/50 text-teal px-4 py-3 rounded-lg"
      onClick={onBackfill}
      disabled={disabled}
      data-testid="action-backfill"
    >
      Backfill history
    </BaseButton>
    <BaseButton
      className="button border border-sand/40 text-sand px-4 py-3 rounded-lg"
      onClick={onMigrate}
      disabled={disabled}
      data-testid="action-migrate"
    >
      Run migrations
    </BaseButton>
    <BaseButton
      className="button border border-sand/40 text-sand px-4 py-3 rounded-lg"
      onClick={onRefresh}
      disabled={disabled}
      data-testid="action-refresh"
    >
      Refresh metrics
    </BaseButton>
  </div>
);

const BackfillRange = ({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
  disabled,
}: BackfillRangeProps) => (
  <div className="flex flex-wrap items-center gap-2 text-xs text-sand/70">
    <span className="uppercase tracking-wide">Backfill range</span>
    <label className="flex items-center gap-2">
      <span className="sr-only">Backfill start date</span>
      <input
        type="date"
        value={startDate}
        onChange={(event) => onStartChange(event.target.value)}
        className="rounded border border-sand/20 bg-night px-2 py-1 text-sand"
        data-testid="backfill-start"
        disabled={disabled}
      />
    </label>
    <span>to</span>
    <label className="flex items-center gap-2">
      <span className="sr-only">Backfill end date</span>
      <input
        type="date"
        value={endDate}
        onChange={(event) => onEndChange(event.target.value)}
        className="rounded border border-sand/20 bg-night px-2 py-1 text-sand"
        data-testid="backfill-end"
        disabled={disabled}
      />
    </label>
  </div>
);

/**
 * Hero component displays the main controls and information for managing an Airflow DAG pipeline.
 *
 * @param onRun - Callback invoked when the "Run + Refresh" button is clicked.
 * @param onBackfill - Callback invoked when the "Backfill history" button is clicked.
 * @param onRefresh - Callback invoked when the "Refresh metrics" button is clicked.
 * @param onMigrate - Callback invoked when the "Run migrations" button is clicked.
 * @param loading - Boolean indicating if an operation is currently in progress, disabling buttons.
 * @param version - Metrics version string displayed in the component.
 * @param source - Current data source identifier (e.g., 'lichess', 'chesscom', or 'all').
 * @param user - User identifier displayed in the component.
 *
 * The component renders pipeline information and action buttons for running, backfilling, migrating, and refreshing metrics.
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
  backfillStartDate,
  backfillEndDate,
  onBackfillStartChange,
  onBackfillEndChange,
}: HeroProps) {
  const lichessLabel = profile ? LICHESS_PROFILE_LABELS[profile] : 'Rapid';
  const chesscomLabel = chesscomProfile
    ? CHESSCOM_PROFILE_LABELS[chesscomProfile]
    : 'Blitz';
  const actionsDisabled = loading || source === 'all';
  const title = buildHeroTitle(source, lichessLabel, chesscomLabel);

  return (
    <div
      className="card p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4"
      data-testid="dashboard-hero"
    >
      <div>
        <Text mode="normal" size="sm" value="Airflow DAG · daily_game_sync" />
        <h1 className="text-3xl md:text-4xl font-display text-sand mt-2">
          {title}
        </h1>
        <Text
          mode="normal"
          size="sm"
          mt="2"
          value={`Execution stamped via metrics version ${version} · user ${user}`}
        />
      </div>
      <div className="flex flex-col gap-3">
        <HeroActions
          onRun={onRun}
          onBackfill={onBackfill}
          onRefresh={onRefresh}
          onMigrate={onMigrate}
          loading={loading}
          disabled={actionsDisabled}
        />
        <BackfillRange
          startDate={backfillStartDate}
          endDate={backfillEndDate}
          onStartChange={onBackfillStartChange}
          onEndChange={onBackfillEndChange}
          disabled={actionsDisabled}
        />
      </div>
    </div>
  );
}
