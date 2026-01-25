import { useEffect, useMemo, useRef, useState } from 'react';
import { Chess } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import {
  DashboardPayload,
  DashboardFilters,
  PracticeAttemptResponse,
  PracticeQueueItem,
  fetchDashboard,
  fetchPracticeQueue,
  getAuthHeaders,
  getJobStreamUrl,
  submitPracticeAttempt,
  triggerMetricsRefresh,
} from './api';

const SOURCE_OPTIONS: { id: 'lichess' | 'chesscom'; label: string; note: string }[] = [
  { id: 'lichess', label: 'Lichess · Rapid', note: 'Perf: rapid' },
  { id: 'chesscom', label: 'Chess.com · Blitz', note: 'Time class: blitz' },
];

type JobProgressItem = {
  step: string;
  timestamp?: number;
  message?: string;
  analyzed?: number;
  total?: number;
  fetched_games?: number;
  positions?: number;
  metrics_version?: number;
  schema_version?: number;
  job?: string;
};

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
    <div className="card p-4" data-testid="motif-breakdown">
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
  onMigrate,
  loading,
  version,
  source,
  user,
  onSourceChange,
}: {
  onRun: () => void;
  onRefresh: () => void;
  onMigrate: () => void;
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
          {source === 'lichess'
            ? 'Lichess rapid pipeline'
            : 'Chess.com blitz pipeline'}
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
          onClick={onMigrate}
          disabled={loading}
        >
          Run migrations
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
  const [filters, setFilters] = useState({
    motif: 'all',
    timeControl: 'all',
    ratingBucket: 'all',
    startDate: '',
    endDate: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [practiceQueue, setPracticeQueue] = useState<PracticeQueueItem[]>([]);
  const [practiceLoading, setPracticeLoading] = useState(false);
  const [practiceError, setPracticeError] = useState<string | null>(null);
  const [includeFailedAttempt, setIncludeFailedAttempt] = useState(false);
  const [practiceMove, setPracticeMove] = useState('');
  const [practiceFen, setPracticeFen] = useState('');
  const [practiceLastMove, setPracticeLastMove] = useState<
    { from: string; to: string } | null
  >(null);
  const [practiceSubmitting, setPracticeSubmitting] = useState(false);
  const [practiceFeedback, setPracticeFeedback] = useState<PracticeAttemptResponse | null>(
    null,
  );
  const [practiceSubmitError, setPracticeSubmitError] = useState<string | null>(
    null,
  );
  const [jobProgress, setJobProgress] = useState<JobProgressItem[]>([]);
  const [jobStatus, setJobStatus] = useState<'idle' | 'running' | 'error' | 'complete'>(
    'idle',
  );
  const streamAbortRef = useRef<AbortController | null>(null);

  const normalizedFilters = useMemo<DashboardFilters>(
    () => ({
      motif: filters.motif !== 'all' ? filters.motif : undefined,
      time_control:
        filters.timeControl !== 'all' ? filters.timeControl : undefined,
      rating_bucket:
        filters.ratingBucket !== 'all' ? filters.ratingBucket : undefined,
      start_date: filters.startDate || undefined,
      end_date: filters.endDate || undefined,
    }),
    [filters],
  );

  const load = async (
    nextSource: 'lichess' | 'chesscom' = source,
    nextFilters: DashboardFilters = normalizedFilters,
  ) => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchDashboard(nextSource, nextFilters);
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
    load(source, normalizedFilters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, normalizedFilters]);

  useEffect(() => {
    loadPracticeQueue(source, includeFailedAttempt);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, includeFailedAttempt]);

  const currentPractice = useMemo(
    () => (practiceQueue.length ? practiceQueue[0] : null),
    [practiceQueue],
  );

  useEffect(() => {
    setPracticeMove('');
    setPracticeFeedback(null);
    setPracticeSubmitError(null);
    setPracticeLastMove(null);
    setPracticeFen(currentPractice?.fen ?? '');
  }, [currentPractice?.tactic_id, currentPractice?.fen]);

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
      streamAbortRef.current = null;
    };
  }, []);

  useEffect(() => {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    setJobProgress([]);
    setJobStatus('idle');
  }, [source]);

  const streamJobEvents = async (
    job: string,
    nextSource: 'lichess' | 'chesscom',
    disconnectMessage: string,
    nextFilters: DashboardFilters = normalizedFilters,
  ) => {
    streamAbortRef.current?.abort();
    const controller = new AbortController();
    streamAbortRef.current = controller;

    const streamUrl = getJobStreamUrl(job, nextSource);
    const response = await fetch(streamUrl, {
      headers: getAuthHeaders(),
      signal: controller.signal,
    });

    if (!response.ok || !response.body) {
      throw new Error(`Stream failed with status ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const handleEvent = async (eventName: string, data: string) => {
      if (!data) return;
      let payload: Record<string, unknown> | null = null;
      try {
        payload = JSON.parse(data) as Record<string, unknown>;
      } catch (parseError) {
        console.error(parseError);
        return;
      }

      if (
        eventName === 'progress' ||
        eventName === 'error' ||
        eventName === 'complete'
      ) {
        setJobProgress((prev) => [...prev, payload as JobProgressItem]);
      }

      if (eventName === 'complete') {
        setJobStatus('complete');
        const dashboard = await fetchDashboard(nextSource, nextFilters);
        setData(dashboard);
        await loadPracticeQueue(nextSource, includeFailedAttempt);
        setLoading(false);
        controller.abort();
        streamAbortRef.current = null;
      }

      if (eventName === 'error') {
        setJobStatus('error');
        setLoading(false);
        setError(disconnectMessage);
        controller.abort();
        streamAbortRef.current = null;
      }
    };

    const parseChunk = async (chunk: string) => {
      buffer += chunk;
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';

      for (const part of parts) {
        let eventName = 'message';
        let data = '';
        for (const line of part.split('\n')) {
          if (!line || line.startsWith(':')) continue;
          if (line.startsWith('event:')) {
            eventName = line.replace('event:', '').trim();
          } else if (line.startsWith('data:')) {
            data += line.replace('data:', '').trim();
          }
        }
        await handleEvent(eventName, data);
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      await parseChunk(decoder.decode(value, { stream: true }));
    }
  };

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      setJobProgress([]);
      setJobStatus('running');
      await streamJobEvents(
        'daily_game_sync',
        source,
        'Pipeline stream disconnected',
        normalizedFilters,
      );
    } catch (err) {
      console.error(err);
      setError('Pipeline run failed');
      setJobStatus('error');
      setLoading(false);
    }
  };

  const handleMigrations = async () => {
    setLoading(true);
    setError(null);
    try {
      setJobProgress([]);
      setJobStatus('running');
      await streamJobEvents(
        'migrations',
        source,
        'Migration stream disconnected',
        normalizedFilters,
      );
    } catch (err) {
      console.error(err);
      setError('Migration run failed');
      setJobStatus('error');
      setLoading(false);
    }
  };

  const handleRefreshMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await triggerMetricsRefresh(source, normalizedFilters);
      setData(payload);
      await loadPracticeQueue(source, includeFailedAttempt);
    } catch (err) {
      console.error(err);
      setError('Metrics refresh failed');
    } finally {
      setLoading(false);
    }
  };

  const buildPracticeMove = (fen: string, rawMove: string) => {
    const trimmed = rawMove.trim().toLowerCase();
    if (trimmed.length < 4) return null;
    const from = trimmed.slice(0, 2);
    const to = trimmed.slice(2, 4);
    const board = new Chess(fen);
    const piece = board.get(from);
    const needsPromotion =
      piece?.type === 'p' && (to.endsWith('8') || to.endsWith('1'));
    const promotion = trimmed.length > 4 ? trimmed[4] : needsPromotion ? 'q' : undefined;
    let move = null;
    try {
      move = board.move({ from, to, promotion });
    } catch (err) {
      console.warn('Invalid move attempt', err);
      return null;
    }
    if (!move) return null;
    return {
      uci: `${from}${to}${promotion ?? ''}`,
      nextFen: board.fen(),
      from,
      to,
    };
  };

  const submitPracticeMove = async (payload: {
    uci: string;
    nextFen?: string;
    from?: string;
    to?: string;
  }) => {
    if (!currentPractice) return;
    setPracticeSubmitting(true);
    setPracticeSubmitError(null);
    setPracticeFeedback(null);
    setPracticeMove(payload.uci);
    if (payload.nextFen) {
      setPracticeFen(payload.nextFen);
    }
    if (payload.from && payload.to) {
      setPracticeLastMove({ from: payload.from, to: payload.to });
    }
    try {
      const response = await submitPracticeAttempt({
        tactic_id: currentPractice.tactic_id,
        position_id: currentPractice.position_id,
        attempted_uci: payload.uci,
        source,
      });
      setPracticeFeedback(response);
      await loadPracticeQueue(source, includeFailedAttempt);
    } catch (err) {
      console.error(err);
      setPracticeSubmitError('Failed to submit practice attempt');
    } finally {
      setPracticeSubmitting(false);
    }
  };

  const handlePracticeAttempt = async (overrideMove?: string) => {
    if (!currentPractice) return;
    const candidate = overrideMove ?? practiceMove;
    if (!candidate.trim()) {
      setPracticeSubmitError('Enter a move in UCI notation (e.g., e2e4).');
      return;
    }
    const baseFen = practiceFen || currentPractice.fen;
    const moveResult = buildPracticeMove(baseFen, candidate);
    if (!moveResult) {
      setPracticeSubmitError('Illegal move for this position. Try a legal UCI move.');
      return;
    }
    await submitPracticeMove(moveResult);
  };

  const handlePracticeDrop = (from: string, to: string, piece: string) => {
    if (!currentPractice || practiceSubmitting) return false;
    const baseFen = practiceFen || currentPractice.fen;
    const isPawn = typeof piece === 'string' && piece.endsWith('P');
    const promotion = isPawn && (to.endsWith('8') || to.endsWith('1')) ? 'q' : '';
    const moveResult = buildPracticeMove(baseFen, `${from}${to}${promotion}`);
    if (!moveResult) {
      setPracticeSubmitError('Illegal move for this position.');
      return false;
    }
    void submitPracticeMove(moveResult);
    return true;
  };

  const totals = useMemo(() => {
    if (!data) return { positions: 0, tactics: 0 };
    return {
      positions: data.positions.length,
      tactics: data.tactics.length,
    };
  }, [data]);

  const selectedRatingBucket =
    filters.ratingBucket === 'all' ? 'all' : filters.ratingBucket;
  const selectedTimeControl =
    filters.timeControl === 'all' ? 'all' : filters.timeControl;

  const motifBreakdown = useMemo(() => {
    if (!data) return [];
    return data.metrics.filter(
      (row) =>
        row.metric_type === 'motif_breakdown' &&
        row.rating_bucket === selectedRatingBucket &&
        row.time_control === selectedTimeControl,
    );
  }, [data, selectedRatingBucket, selectedTimeControl]);

  const trendRows = useMemo(() => {
    if (!data) return [];
    return data.metrics.filter(
      (row) =>
        row.metric_type === 'trend' &&
        row.rating_bucket === selectedRatingBucket &&
        row.time_control === selectedTimeControl,
    );
  }, [data, selectedRatingBucket, selectedTimeControl]);

  const practiceOrientation =
    currentPractice?.side_to_move === 'b' ? 'black' : 'white';

  const practiceHighlightStyles = useMemo(() => {
    if (!practiceLastMove) return {};
    return {
      [practiceLastMove.from]: {
        backgroundColor: 'rgba(14, 116, 144, 0.4)',
      },
      [practiceLastMove.to]: {
        backgroundColor: 'rgba(14, 116, 144, 0.4)',
      },
    };
  }, [practiceLastMove]);

  const motifOptions = useMemo(() => {
    const values = new Set<string>();
    data?.metrics.forEach((row) => {
      if (row.motif) values.add(row.motif);
    });
    return ['all', ...Array.from(values).sort()];
  }, [data]);

  const timeControlOptions = useMemo(() => {
    const values = new Set<string>();
    data?.metrics.forEach((row) => {
      const value = row.time_control || 'unknown';
      if (value !== 'all') values.add(value);
    });
    return ['all', ...Array.from(values).sort()];
  }, [data]);

  const ratingOptions = useMemo(() => {
    const values = new Set<string>();
    data?.metrics.forEach((row) => {
      const value = row.rating_bucket || 'unknown';
      if (value !== 'all') values.add(value);
    });
    const ordered = ['<1200', '1200-1399', '1400-1599', '1600-1799', '1800+', 'unknown'];
    const custom = Array.from(values).filter((value) => !ordered.includes(value));
    return ['all', ...ordered.filter((value) => values.has(value)), ...custom.sort()];
  }, [data]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <Hero
        onRun={handleRun}
        onMigrate={handleMigrations}
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
                        : entry.schema_version !== undefined
                          ? `schema v${entry.schema_version}`
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
                  {detail ? <Badge label={detail} /> : null}
                </li>
              );
            })}
          </ol>
        </div>
      ) : null}

      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-display text-sand">Filters</h3>
          <Badge label="Live" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
          <label className="text-xs text-sand/60 flex flex-col gap-2">
            Site / source
            <select
              className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
              value={source}
              onChange={(event) =>
                setSource(event.target.value as 'lichess' | 'chesscom')
              }
              disabled={loading}
              data-testid="filter-source"
            >
              {SOURCE_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-sand/60 flex flex-col gap-2">
            Motif
            <select
              className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
              value={filters.motif}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, motif: event.target.value }))
              }
              disabled={loading}
              data-testid="filter-motif"
            >
              {motifOptions.map((motif) => (
                <option key={motif} value={motif}>
                  {motif === 'all' ? 'All motifs' : motif}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-sand/60 flex flex-col gap-2">
            Time control
            <select
              className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
              value={filters.timeControl}
              onChange={(event) =>
                setFilters((prev) => ({
                  ...prev,
                  timeControl: event.target.value,
                }))
              }
              disabled={loading}
              data-testid="filter-time-control"
            >
              {timeControlOptions.map((value) => (
                <option key={value} value={value}>
                  {value === 'all' ? 'All time controls' : value}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-sand/60 flex flex-col gap-2">
            Rating band
            <select
              className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
              value={filters.ratingBucket}
              onChange={(event) =>
                setFilters((prev) => ({
                  ...prev,
                  ratingBucket: event.target.value,
                }))
              }
              disabled={loading}
              data-testid="filter-rating"
            >
              {ratingOptions.map((value) => (
                <option key={value} value={value}>
                  {value === 'all' ? 'All ratings' : value}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-col gap-2 text-xs text-sand/60">
            Date range
            <div className="flex gap-2">
              <input
                type="date"
                value={filters.startDate}
                onChange={(event) =>
                  setFilters((prev) => ({
                    ...prev,
                    startDate: event.target.value,
                  }))
                }
                className="flex-1 rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
                disabled={loading}
                data-testid="filter-start-date"
              />
              <input
                type="date"
                value={filters.endDate}
                onChange={(event) =>
                  setFilters((prev) => ({
                    ...prev,
                    endDate: event.target.value,
                  }))
                }
                className="flex-1 rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
                disabled={loading}
                data-testid="filter-end-date"
              />
            </div>
            <button
              className="self-start text-xs text-sand/50 hover:text-sand"
              onClick={() =>
                setFilters({
                  motif: 'all',
                  timeControl: 'all',
                  ratingBucket: 'all',
                  startDate: '',
                  endDate: '',
                })
              }
              disabled={loading}
            >
              Reset filters
            </button>
          </div>
        </div>
      </div>

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
      <div className="card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-display text-sand">Practice attempt</h3>
            <p className="text-xs text-sand/60">
              Play the best move for the current tactic.
            </p>
          </div>
          {currentPractice ? <Badge label={currentPractice.motif} /> : null}
        </div>
        {currentPractice ? (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
              <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                <Chessboard
                  id="practice-board"
                  position={practiceFen || currentPractice.fen}
                  onPieceDrop={handlePracticeDrop}
                  boardOrientation={practiceOrientation}
                  arePiecesDraggable={!practiceSubmitting}
                  isDraggablePiece={(piece) => {
                    const fen = practiceFen || currentPractice.fen;
                    if (!fen) return false;
                    if (typeof piece !== 'string') return false;
                    const board = new Chess(fen);
                    const turn = board.turn();
                    const pieceColor = piece.startsWith('w') ? 'w' : 'b';
                    return turn === pieceColor;
                  }}
                  customSquareStyles={practiceHighlightStyles}
                />
                <p className="mt-2 text-xs text-sand/60">
                  Legal moves only. Drag a piece to submit.
                </p>
              </div>
              <div className="space-y-3">
                <div className="space-y-1">
                  <p className="text-xs text-sand/60">FEN</p>
                  <p className="font-mono text-xs text-sand/80">
                    {currentPractice.fen}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-sand/70">
                  <Badge
                    label={`Move ${currentPractice.move_number}.${currentPractice.ply}`}
                  />
                  <Badge label={`Best ${currentPractice.best_uci || '--'}`} />
                  {currentPractice.clock_seconds !== null ? (
                    <Badge label={`${currentPractice.clock_seconds}s`} />
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <input
                    value={practiceMove}
                    onChange={(event) => setPracticeMove(event.target.value)}
                    placeholder="Enter your move (UCI e.g., e2e4)"
                    className="flex-1 min-w-[220px] rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand placeholder:text-sand/40"
                    disabled={practiceSubmitting}
                  />
                  <button
                    className="button bg-teal text-night px-4 py-2 rounded-md font-display"
                    onClick={() => handlePracticeAttempt()}
                    disabled={practiceSubmitting}
                  >
                    {practiceSubmitting ? 'Submitting…' : 'Submit attempt'}
                  </button>
                </div>
                {practiceSubmitError ? (
                  <p className="text-sm text-rust">{practiceSubmitError}</p>
                ) : null}
                {practiceFeedback ? (
                  <div className="rounded-md border border-white/10 bg-white/5 p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <Badge
                        label={practiceFeedback.correct ? 'Correct' : 'Missed'}
                      />
                      <span className="text-sand/80">
                        {practiceFeedback.message}
                      </span>
                    </div>
                    {practiceFeedback.explanation ? (
                      <p className="mt-2 text-xs text-sand/70">
                        {practiceFeedback.explanation}
                      </p>
                    ) : null}
                    <p className="mt-2 font-mono text-xs text-sand/70">
                      You played {practiceFeedback.attempted_uci} · best{' '}
                      {practiceFeedback.best_san
                        ? `${practiceFeedback.best_san} (${practiceFeedback.best_uci || '--'})`
                        : practiceFeedback.best_uci || '--'}
                    </p>
                  </div>
                ) : null}
              </div>
            </div>
          </>
        ) : (
          <p className="text-sm text-sand/60">No practice items queued yet.</p>
        )}
      </div>
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
