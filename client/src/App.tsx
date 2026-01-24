import { useEffect, useMemo, useRef, useState } from 'react';
import {
  DashboardPayload,
  PracticeQueueItem,
  fetchDashboard,
  fetchPracticeQueue,
  getJobStreamUrl,
  triggerMetricsRefresh,
} from './api';

const SOURCE_OPTIONS: { id: 'lichess' | 'chesscom'; label: string; note: string }[] = [
  { id: 'lichess', label: 'Lichess · Rapid', note: 'Perf: rapid' },
  { id: 'chesscom', label: 'Chess.com · Blitz', note: 'Time class: blitz' },
];

function Badge({ label }: { label: string }) {
  return (
    <span className="px-2 py-1 text-xs rounded-full bg-rust/30 text-sand border border-rust/60">
      {label}
    </span>
  );
}

function MetricCard({
  title,
  value,
  note,
}: {
  title: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="card p-4 flex flex-col gap-2">
      <p className="text-sm text-sand/70 uppercase tracking-[0.08em]">
        {title}
      </p>
      <p className="text-3xl font-display text-teal">{value}</p>
      {note ? <p className="text-xs text-sand/60">{note}</p> : null}
    </div>
  );
}

function TacticsTable({ data }: { data: DashboardPayload['tactics'] }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-display text-sand">Recent tactics</h3>
        <Badge label="Live" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-sand/60">
            <tr>
              <th className="text-left py-2">Motif</th>
              <th className="text-left">Result</th>
              <th className="text-left">Move</th>
              <th className="text-left">Delta (cp)</th>
            </tr>
          </thead>
          <tbody className="text-sand/90">
            {data.map((row) => (
              <tr
                key={row.tactic_id}
                className="odd:bg-white/0 even:bg-white/5/5 border-b border-white/5"
              >
                <td className="py-2 font-display text-sm uppercase tracking-wide">
                  {row.motif}
                </td>
                <td>
                  <Badge label={row.result} />
                </td>
                <td className="font-mono text-xs">{row.user_uci}</td>
                <td className="font-mono text-xs text-rust">
                  {row.eval_delta}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PracticeQueue({
  data,
  includeFailedAttempt,
  onToggleIncludeFailedAttempt,
  loading,
}: {
  data: PracticeQueueItem[];
  includeFailedAttempt: boolean;
  onToggleIncludeFailedAttempt: (next: boolean) => void;
  loading: boolean;
}) {
  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <h3 className="text-lg font-display text-sand">Practice queue</h3>
          <p className="text-xs text-sand/60">
            Missed tactics from your games, ready to drill.
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs text-sand/70">
          <input
            type="checkbox"
            className="accent-teal"
            checked={includeFailedAttempt}
            onChange={(event) => onToggleIncludeFailedAttempt(event.target.checked)}
            disabled={loading}
          />
          Include failed attempts
        </label>
      </div>
      {data.length ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-sand/60">
              <tr>
                <th className="text-left py-2">Motif</th>
                <th className="text-left">Result</th>
                <th className="text-left">Best</th>
                <th className="text-left">Your move</th>
                <th className="text-left">Move</th>
                <th className="text-left">Delta</th>
              </tr>
            </thead>
            <tbody className="text-sand/90">
              {data.map((row) => (
                <tr
                  key={`${row.tactic_id}-${row.position_id}`}
                  className="odd:bg-white/0 even:bg-white/5/5 border-b border-white/5"
                >
                  <td className="py-2 font-display text-sm uppercase tracking-wide">
                    {row.motif}
                  </td>
                  <td>
                    <Badge label={row.result} />
                  </td>
                  <td className="font-mono text-xs text-teal">
                    {row.best_uci || '--'}
                  </td>
                  <td className="font-mono text-xs">{row.user_uci}</td>
                  <td className="font-mono text-xs">
                    {row.move_number}.{row.ply}
                  </td>
                  <td className="font-mono text-xs text-rust">
                    {row.eval_delta}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-sand/60">
          {loading ? 'Loading practice queue…' : 'No missed tactics queued yet.'}
        </p>
      )}
    </div>
  );
}

function MetricsGrid({ data }: { data: DashboardPayload['metrics'] }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-display text-sand">Motif breakdown</h3>
        <Badge label="Updated" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.map((row) => (
          <MetricCard
            key={row.motif}
            title={row.motif}
            value={`${row.found}/${row.total}`}
            note={`${row.missed} missed, ${row.failed_attempt} failed`}
          />
        ))}
      </div>
    </div>
  );
}

function MetricsTrends({ data }: { data: DashboardPayload['metrics'] }) {
  const latestByMotif = useMemo(() => {
    const map = new Map<
      string,
      { seven?: DashboardPayload['metrics'][number]; thirty?: DashboardPayload['metrics'][number] }
    >();
    data.forEach((row) => {
      if (row.metric_type !== 'trend' || !row.trend_date) return;
      const current = map.get(row.motif) || {};
      const isSeven = row.window_days === 7;
      const slot = isSeven ? 'seven' : row.window_days === 30 ? 'thirty' : null;
      if (!slot) return;
      const existing = current[slot];
      if (!existing || new Date(row.trend_date) > new Date(existing.trend_date || 0)) {
        current[slot] = row;
      }
      map.set(row.motif, current);
    });
    return Array.from(map.entries()).map(([motif, value]) => ({ motif, ...value }));
  }, [data]);

  if (!latestByMotif.length) return null;

  const formatPercent = (value: number | null) =>
    value === null || Number.isNaN(value) ? '--' : `${(value * 100).toFixed(1)}%`;

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-display text-sand">Motif trends</h3>
        <Badge label="Rolling 7/30" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-sand/60">
            <tr>
              <th className="text-left py-2">Motif</th>
              <th className="text-left">7d found</th>
              <th className="text-left">30d found</th>
              <th className="text-left">Last update</th>
            </tr>
          </thead>
          <tbody className="text-sand/90">
            {latestByMotif.map((row) => {
              const lastDate = row.seven?.trend_date || row.thirty?.trend_date || '--';
              return (
                <tr
                  key={row.motif}
                  className="odd:bg-white/0 even:bg-white/5/5 border-b border-white/5"
                >
                  <td className="py-2 font-display text-sm uppercase tracking-wide">
                    {row.motif}
                  </td>
                  <td className="font-mono text-xs text-teal">
                    {formatPercent(row.seven?.found_rate ?? null)}
                  </td>
                  <td className="font-mono text-xs text-teal">
                    {formatPercent(row.thirty?.found_rate ?? null)}
                  </td>
                  <td className="font-mono text-xs text-sand/70">{lastDate}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PositionsList({ data }: { data: DashboardPayload['positions'] }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-display text-sand">Latest positions</h3>
        <Badge label="Fen" />
      </div>
      <div className="flex flex-col gap-3">
        {data.map((pos) => (
          <div
            key={pos.position_id}
            className="flex items-center justify-between text-sm border-b border-white/10 pb-2"
          >
            <div>
              <p className="font-mono text-xs text-sand/70">{pos.fen}</p>
              <p className="text-sand/90">
                Move {pos.move_number} · {pos.san}
              </p>
            </div>
            <Badge label={`${pos.clock_seconds ?? '--'}s`} />
          </div>
        ))}
      </div>
    </div>
  );
}

function Hero({
  onRun,
  onRefresh,
  loading,
  version,
  source,
  user,
  onSourceChange,
}: {
  onRun: () => void;
  onRefresh: () => void;
  loading: boolean;
  version: number;
  source: 'lichess' | 'chesscom';
  user: string;
  onSourceChange: (next: 'lichess' | 'chesscom') => void;
}) {
  return (
    <div className="card p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <p className="text-sm text-sand/70">Airflow DAG · daily_game_sync</p>
        <h1 className="text-3xl md:text-4xl font-display text-sand mt-2">
          {source === 'lichess' ? 'Lichess rapid pipeline' : 'Chess.com blitz pipeline'}
        </h1>
        <p className="text-sand/70 mt-2">
          Execution stamped via metrics version {version} · user {user}
        </p>
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
      <div className="flex gap-3">
        <button
          className="button bg-teal text-night px-4 py-3 rounded-lg font-display"
          onClick={onRun}
          disabled={loading}
        >
          {loading ? 'Running…' : 'Run + Refresh'}
        </button>
        <button
          className="button border border-sand/40 text-sand px-4 py-3 rounded-lg"
          onClick={onRefresh}
          disabled={loading}
        >
          Refresh metrics
        </button>
      </div>
    </div>
  );
}

function App() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [source, setSource] = useState<'lichess' | 'chesscom'>('lichess');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [practiceQueue, setPracticeQueue] = useState<PracticeQueueItem[]>([]);
  const [practiceLoading, setPracticeLoading] = useState(false);
  const [practiceError, setPracticeError] = useState<string | null>(null);
  const [includeFailedAttempt, setIncludeFailedAttempt] = useState(false);
  const [jobProgress, setJobProgress] = useState<
    Array<{
      step: string;
      timestamp?: number;
      message?: string;
      analyzed?: number;
      total?: number;
      fetched_games?: number;
      positions?: number;
      metrics_version?: number;
      job?: string;
    }>
  >([]);
  const [jobStatus, setJobStatus] = useState<'idle' | 'running' | 'error' | 'complete'>(
    'idle',
  );
  const streamRef = useRef<EventSource | null>(null);

  const load = async (nextSource: 'lichess' | 'chesscom' = source) => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchDashboard(nextSource);
      setData(payload);
    } catch (err) {
      console.error(err);
      setError('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const loadPracticeQueue = async (
    nextSource: 'lichess' | 'chesscom' = source,
    includeFailed = includeFailedAttempt,
  ) => {
    setPracticeLoading(true);
    setPracticeError(null);
    try {
      const payload = await fetchPracticeQueue(nextSource, includeFailed);
      setPracticeQueue(payload.items);
    } catch (err) {
      console.error(err);
      setPracticeError('Failed to load practice queue');
    } finally {
      setPracticeLoading(false);
    }
  };

  useEffect(() => {
    load(source);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source]);

  useEffect(() => {
    loadPracticeQueue(source, includeFailedAttempt);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, includeFailedAttempt]);

  useEffect(() => {
    return () => {
      streamRef.current?.close();
      streamRef.current = null;
    };
  }, []);

  useEffect(() => {
    streamRef.current?.close();
    streamRef.current = null;
    setJobProgress([]);
    setJobStatus('idle');
  }, [source]);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      streamRef.current?.close();
      setJobProgress([]);
      setJobStatus('running');

      const streamUrl = getJobStreamUrl('daily_game_sync', source);
      const eventSource = new EventSource(streamUrl);
      streamRef.current = eventSource;

      eventSource.addEventListener('progress', (event) => {
        const messageEvent = event as MessageEvent<string>;
        try {
          const payload = JSON.parse(messageEvent.data);
          setJobProgress((prev) => [...prev, payload]);
        } catch (parseError) {
          console.error(parseError);
        }
      });

      eventSource.addEventListener('complete', async (event) => {
        const messageEvent = event as MessageEvent<string>;
        try {
          const payload = JSON.parse(messageEvent.data);
          setJobProgress((prev) => [...prev, payload]);
        } catch (parseError) {
          console.error(parseError);
        }
        eventSource.close();
        streamRef.current = null;
        setJobStatus('complete');
        const payload = await fetchDashboard(source);
        setData(payload);
        await loadPracticeQueue(source, includeFailedAttempt);
        setLoading(false);
      });

      eventSource.addEventListener('error', (event) => {
        const messageEvent = event as MessageEvent<string>;
        if (messageEvent.data) {
          try {
            const payload = JSON.parse(messageEvent.data);
            setJobProgress((prev) => [...prev, payload]);
          } catch (parseError) {
            console.error(parseError);
          }
        }
        setJobStatus('error');
        setLoading(false);
        setError('Pipeline stream disconnected');
        eventSource.close();
        streamRef.current = null;
      });
    } catch (err) {
      console.error(err);
      setError('Pipeline run failed');
      setJobStatus('error');
      setLoading(false);
    }
  };

  const handleRefreshMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await triggerMetricsRefresh(source);
      setData(payload);
      await loadPracticeQueue(source, includeFailedAttempt);
    } catch (err) {
      console.error(err);
      setError('Metrics refresh failed');
    } finally {
      setLoading(false);
    }
  };

  const totals = useMemo(() => {
    if (!data) return { positions: 0, tactics: 0 };
    return {
      positions: data.positions.length,
      tactics: data.tactics.length,
    };
  }, [data]);

  const motifBreakdown = useMemo(() => {
    if (!data) return [];
    return data.metrics.filter(
      (row) =>
        row.metric_type === 'motif_breakdown' &&
        row.rating_bucket === 'all' &&
        row.time_control === 'all',
    );
  }, [data]);

  const trendRows = useMemo(() => {
    if (!data) return [];
    return data.metrics.filter(
      (row) =>
        row.metric_type === 'trend' &&
        row.rating_bucket === 'all' &&
        row.time_control === 'all',
    );
  }, [data]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <Hero
        onRun={handleRun}
        onRefresh={handleRefreshMetrics}
        loading={loading}
        version={data?.metrics_version ?? 0}
        source={source}
        user={data?.user ?? 'unknown'}
        onSourceChange={setSource}
      />

      {error ? <div className="card p-3 text-rust">{error}</div> : null}

      {jobProgress.length ? (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-display text-sand">Job progress</h3>
            <Badge
              label={
                jobStatus === 'running'
                  ? 'Running'
                  : jobStatus === 'complete'
                    ? 'Complete'
                    : jobStatus === 'error'
                      ? 'Error'
                      : 'Idle'
              }
            />
          </div>
          <ol className="space-y-2 text-sm">
            {jobProgress.map((entry, index) => {
              const detail =
                entry.analyzed !== undefined && entry.total !== undefined
                  ? `${entry.analyzed}/${entry.total}`
                  : entry.fetched_games !== undefined
                    ? `${entry.fetched_games} games`
                    : entry.positions !== undefined
                      ? `${entry.positions} positions`
                      : entry.metrics_version !== undefined
                        ? `v${entry.metrics_version}`
                        : null;
              const timestamp = entry.timestamp
                ? new Date(entry.timestamp * 1000).toLocaleTimeString()
                : null;
              return (
                <li
                  key={`${entry.step}-${entry.timestamp ?? index}`}
                  className="flex flex-wrap items-center gap-2 text-sand/80"
                >
                  {timestamp ? (
                    <span className="font-mono text-xs text-sand/60">
                      {timestamp}
                    </span>
                  ) : null}
                  <span className="font-display text-sand">{entry.step}</span>
                  {entry.message ? (
                    <span className="text-sand/70">{entry.message}</span>
                  ) : null}
                  {detail ? (
                    <Badge label={detail} />
                  ) : null}
                </li>
              );
            })}
          </ol>
        </div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <MetricCard
          title="Positions"
          value={`${totals.positions}`}
          note="Captured when you were to move"
        />
        <MetricCard
          title="Tactics"
          value={`${totals.tactics}`}
          note="Analyzed via Stockfish"
        />
        <MetricCard
          title="Metrics ver."
          value={`${data?.metrics_version ?? 0}`}
          note="Cache bust signal"
        />
      </div>

      {data ? <MetricsGrid data={motifBreakdown} /> : null}
      {data ? <MetricsTrends data={trendRows} /> : null}
      {practiceError ? (
        <div className="card p-3 text-rust">{practiceError}</div>
      ) : null}
      <PracticeQueue
        data={practiceQueue}
        includeFailedAttempt={includeFailedAttempt}
        onToggleIncludeFailedAttempt={setIncludeFailedAttempt}
        loading={practiceLoading}
      />
      {data ? <TacticsTable data={data.tactics} /> : null}
      {data ? <PositionsList data={data.positions} /> : null}
    </div>
  );
}
export default App;
