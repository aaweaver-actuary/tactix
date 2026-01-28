import { useEffect, useMemo, useRef, useState } from 'react';
import { Chess, Square } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import {
  DashboardPayload,
  DashboardFilters,
  PostgresAnalysisRow,
  PostgresRawPgnsSummary,
  PostgresStatus,
  PracticeAttemptResponse,
  PracticeQueueItem,
} from './api';
import { getAuthHeaders } from './utils/getAuthHeaders';
import getJobStreamUrl from './utils/getJobStreamUrl';
import fetchDashboard from './utils/fetchDashboard';
import fetchPostgresAnalysis from './utils/fetchPostgresAnalysis';
import fetchPostgresRawPgns from './utils/fetchPostgresRawPgns';
import fetchPostgresStatus from './utils/fetchPostgresStatus';
import triggerMetricsRefresh from './utils/triggerMetricsRefresh';
import submitPracticeAttempt from './utils/submitPracticeAttempt';
import fetchPracticeQueue from './utils/fetchPracticeQueue';
import buildPracticeFeedback from './utils/buildPracticeFeedback';
import {
  ChessPlatform,
  ChesscomProfile,
  JobProgressItem,
  LichessProfile,
} from './types';
import {
  Badge,
  Text,
  MetricCard,
  TacticsTable,
  PracticeQueue,
  MetricsGrid,
  MetricsTrends,
  TimeTroubleCorrelation,
  PositionsList,
  Hero,
  PracticeAttemptButton,
  PracticeMoveInput,
  PracticeSessionProgress,
} from './components';
import { SOURCE_OPTIONS } from './utils/SOURCE_OPTIONS';
import { LICHESS_PROFILE_OPTIONS } from './utils/LICHESS_PROFILE_OPTIONS';
import { CHESSCOM_PROFILE_OPTIONS } from './utils/CHESSCOM_PROFILE_OPTIONS';
import isPiecePlayable from './utils/isPiecePlayable';
import {
  PracticeSessionStats,
  resetPracticeSessionStats,
  updatePracticeSessionStats,
} from './utils/practiceSession';

export default function App() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [source, setSource] = useState<ChessPlatform>('lichess');
  const [lichessProfile, setLichessProfile] = useState<LichessProfile>('rapid');
  const [chesscomProfile, setChesscomProfile] =
    useState<ChesscomProfile>('blitz');
  const [filters, setFilters] = useState({
    motif: 'all',
    timeControl: 'all',
    ratingBucket: 'all',
    startDate: '',
    endDate: '',
  });
  const [backfillStartDate, setBackfillStartDate] = useState(() => {
    const date = new Date(Date.now() - 900 * 24 * 60 * 60 * 1000);
    return date.toISOString().slice(0, 10);
  });
  const [backfillEndDate, setBackfillEndDate] = useState(() => {
    return new Date().toISOString().slice(0, 10);
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [practiceQueue, setPracticeQueue] = useState<PracticeQueueItem[]>([]);
  const [practiceLoading, setPracticeLoading] = useState(false);
  const [practiceError, setPracticeError] = useState<string | null>(null);
  const [includeFailedAttempt, setIncludeFailedAttempt] = useState(false);
  const [practiceMove, setPracticeMove] = useState('');
  const [practiceFen, setPracticeFen] = useState('');
  const [practiceLastMove, setPracticeLastMove] = useState<{
    from: string;
    to: string;
  } | null>(null);
  const [practiceSubmitting, setPracticeSubmitting] = useState(false);
  const [practiceFeedback, setPracticeFeedback] =
    useState<PracticeAttemptResponse | null>(null);
  const [practiceSubmitError, setPracticeSubmitError] = useState<string | null>(
    null,
  );
  const [practiceServedAtMs, setPracticeServedAtMs] = useState<number | null>(
    null,
  );
  const [practiceSession, setPracticeSession] = useState<PracticeSessionStats>(
    () => resetPracticeSessionStats(0),
  );
  const [jobProgress, setJobProgress] = useState<JobProgressItem[]>([]);
  const [jobStatus, setJobStatus] = useState<
    'idle' | 'running' | 'error' | 'complete'
  >('idle');
  const streamAbortRef = useRef<AbortController | null>(null);
  const [postgresStatus, setPostgresStatus] = useState<PostgresStatus | null>(
    null,
  );
  const [postgresError, setPostgresError] = useState<string | null>(null);
  const [postgresLoading, setPostgresLoading] = useState(false);
  const [postgresAnalysis, setPostgresAnalysis] = useState<
    PostgresAnalysisRow[]
  >([]);
  const [postgresAnalysisError, setPostgresAnalysisError] = useState<
    string | null
  >(null);
  const [postgresAnalysisLoading, setPostgresAnalysisLoading] = useState(false);
  const [postgresRawPgns, setPostgresRawPgns] =
    useState<PostgresRawPgnsSummary | null>(null);
  const [postgresRawPgnsError, setPostgresRawPgnsError] = useState<
    string | null
  >(null);
  const [postgresRawPgnsLoading, setPostgresRawPgnsLoading] = useState(false);

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

  async function load(
    nextSource: ChessPlatform = source,
    nextFilters: DashboardFilters = normalizedFilters,
  ) {
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
  }

  async function loadPracticeQueue(
    nextSource: ChessPlatform = source,
    includeFailed = includeFailedAttempt,
    resetSession = false,
  ): Promise<void> {
    setPracticeLoading(true);
    setPracticeError(null);
    try {
      const payload = await fetchPracticeQueue(nextSource, includeFailed);
      setPracticeQueue(payload.items);
      if (resetSession) {
        setPracticeSession(resetPracticeSessionStats(payload.items.length));
      } else {
        setPracticeSession((prev) => {
          const nextTotal = Math.max(
            prev.total,
            prev.completed + payload.items.length,
          );
          if (nextTotal === prev.total) return prev;
          return { ...prev, total: nextTotal };
        });
      }
    } catch (err) {
      console.error(err);
      setPracticeError('Failed to load practice queue');
    } finally {
      setPracticeLoading(false);
    }
  }

  async function loadPostgres(): Promise<void> {
    setPostgresLoading(true);
    setPostgresError(null);
    try {
      const payload = await fetchPostgresStatus();
      setPostgresStatus(payload);
    } catch (err) {
      console.error(err);
      setPostgresError('Failed to load Postgres status');
    } finally {
      setPostgresLoading(false);
    }
  }

  async function loadPostgresAnalysis(): Promise<void> {
    setPostgresAnalysisLoading(true);
    setPostgresAnalysisError(null);
    try {
      const payload = await fetchPostgresAnalysis();
      setPostgresAnalysis(payload.tactics || []);
    } catch (err) {
      console.error(err);
      setPostgresAnalysisError('Failed to load Postgres analysis results');
    } finally {
      setPostgresAnalysisLoading(false);
    }
  }

  async function loadPostgresRawPgns(): Promise<void> {
    setPostgresRawPgnsLoading(true);
    setPostgresRawPgnsError(null);
    try {
      const payload = await fetchPostgresRawPgns();
      setPostgresRawPgns(payload);
    } catch (err) {
      console.error(err);
      setPostgresRawPgnsError('Failed to load Postgres raw PGN summary');
    } finally {
      setPostgresRawPgnsLoading(false);
    }
  }

  useEffect(() => {
    load(source, normalizedFilters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, normalizedFilters]);

  useEffect(() => {
    loadPostgres();
    loadPostgresAnalysis();
    loadPostgresRawPgns();
  }, []);

  useEffect(() => {
    loadPracticeQueue(source, includeFailedAttempt, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, includeFailedAttempt]);

  const currentPractice = useMemo(
    () => (practiceQueue.length ? practiceQueue[0] : null),
    [practiceQueue],
  );

  useEffect(() => {
    function resetPracticeData(): void {
      setPracticeMove('');
      setPracticeFeedback(null);
      setPracticeSubmitError(null);
      setPracticeLastMove(null);
      setPracticeFen(currentPractice?.fen ?? '');
      setPracticeServedAtMs(currentPractice ? Date.now() : null);
    }
    resetPracticeData();
  }, [currentPractice]);

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
      streamAbortRef.current = null;
    };
  }, []);

  useEffect(() => {
    resetJobState();
  }, [source, lichessProfile, chesscomProfile]);

  const streamJobEvents = async (
    job: string,
    nextSource: ChessPlatform,
    disconnectMessage: string,
    nextFilters: DashboardFilters = normalizedFilters,
    profile?: LichessProfile | ChesscomProfile,
    backfillStartMs?: number,
    backfillEndMs?: number,
  ) => {
    streamAbortRef.current?.abort();
    const controller = new AbortController();
    streamAbortRef.current = controller;

    const streamUrl = getJobStreamUrl(
      job,
      nextSource,
      profile,
      backfillStartMs,
      backfillEndMs,
    );
    const response = await fetch(streamUrl, {
      headers: getAuthHeaders(),
      signal: controller.signal,
    });

    validateResponse(response);
    const body = response.body;
    if (!body) {
      throw new Error('Response body is null');
    }

    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    async function handleEvent(eventName: string, data: string) {
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
        await loadPracticeQueue(nextSource, includeFailedAttempt, true);
        setLoading(false);
        controller.abort();
        streamAbortRef.current = null;
        await loadPostgres();
        await loadPostgresAnalysis();
      }

      if (eventName === 'error') {
        setJobStatus('error');
        setLoading(false);
        setError(disconnectMessage);
        controller.abort();
        streamAbortRef.current = null;
        await loadPostgres();
        await loadPostgresAnalysis();
      }
    }

    async function parseChunk(chunk: string): Promise<void> {
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
    }

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
      const profile = source === 'lichess' ? lichessProfile : chesscomProfile;
      await streamJobEvents(
        'daily_game_sync',
        source,
        'Pipeline stream disconnected',
        normalizedFilters,
        profile,
      );
    } catch (err) {
      console.error(err);
      setError('Pipeline run failed');
      setJobStatus('error');
      setLoading(false);
    }
  };

  const handleBackfill = async () => {
    setLoading(true);
    setError(null);
    try {
      setJobProgress([]);
      setJobStatus('running');
      const nowMs = Date.now();
      const startDate = backfillStartDate
        ? new Date(`${backfillStartDate}T00:00:00`)
        : new Date(nowMs - 900 * 24 * 60 * 60 * 1000);
      const endDate = backfillEndDate
        ? new Date(`${backfillEndDate}T00:00:00`)
        : new Date(nowMs);
      const windowStart = startDate.getTime();
      let windowEnd = endDate.getTime() + 24 * 60 * 60 * 1000;
      if (Number.isNaN(windowStart) || Number.isNaN(windowEnd)) {
        throw new Error('Invalid backfill date range');
      }
      if (windowEnd > nowMs) {
        windowEnd = nowMs;
      }
      if (windowStart >= windowEnd) {
        throw new Error('Backfill range must end after the start date');
      }
      const profile = source === 'lichess' ? lichessProfile : chesscomProfile;
      await streamJobEvents(
        'daily_game_sync',
        source,
        'Backfill stream disconnected',
        normalizedFilters,
        profile,
        windowStart,
        windowEnd,
      );
    } catch (err) {
      console.error(err);
      setError('Backfill run failed');
      setJobStatus('error');
    } finally {
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

  function validateResponse(response: Response) {
    if (!response.ok || !response.body) {
      throw new Error(`Stream failed with status ${response.status}`);
    }
    if (!response.body) {
      throw new Error('Response body is null');
    }
  }

  function resetJobState(): void {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    setJobProgress([]);
    setJobStatus('idle');
  }

  function buildPracticeMove(
    fen: string,
    rawMove: string,
  ): { uci: string; nextFen: string; from: string; to: string } | null {
    const trimmed = rawMove.trim().toLowerCase();
    if (trimmed.length < 4) return null;
    const from = trimmed.slice(0, 2) as Square;
    const to = trimmed.slice(2, 4) as Square;
    const board = new Chess(fen);
    const piece = board.get(from);
    const needsPromotion =
      piece?.type === 'p' && (to.endsWith('8') || to.endsWith('1'));
    const promotion =
      trimmed.length > 4 ? trimmed[4] : needsPromotion ? 'q' : undefined;
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
  }

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
        served_at_ms: practiceServedAtMs ?? undefined,
      });
      setPracticeFeedback(response);
      setPracticeSession((prev) =>
        updatePracticeSessionStats(prev, response.correct),
      );
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
      setPracticeSubmitError(
        'Illegal move for this position. Try a legal UCI move.',
      );
      return;
    }
    await submitPracticeMove(moveResult);
  };

  const handlePracticeDrop = (from: string, to: string, piece: string) => {
    if (!currentPractice || practiceSubmitting) return false;
    const baseFen = practiceFen || currentPractice.fen;
    const isPawn = typeof piece === 'string' && piece.endsWith('P');
    const promotion =
      isPawn && (to.endsWith('8') || to.endsWith('1')) ? 'q' : '';
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

  const timeTroubleRows = useMemo(() => {
    if (!data) return [];
    return data.metrics.filter(
      (row) =>
        row.metric_type === 'time_trouble_correlation' &&
        row.rating_bucket === 'all' &&
        (selectedTimeControl === 'all'
          ? row.time_control !== 'all'
          : row.time_control === selectedTimeControl),
    );
  }, [data, selectedTimeControl]);

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
      if (row.motif && row.motif !== 'all') values.add(row.motif);
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
    const ordered = [
      '<1200',
      '1200-1399',
      '1400-1599',
      '1600-1799',
      '1800+',
      'unknown',
    ];
    const custom = Array.from(values).filter(
      (value) => value !== 'all' && !ordered.includes(value),
    );
    return [
      'all',
      ...ordered.filter((value) => values.has(value)),
      ...custom.sort(),
    ];
  }, [data]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <Hero
        onRun={handleRun}
        onBackfill={handleBackfill}
        onMigrate={handleMigrations}
        onRefresh={handleRefreshMetrics}
        loading={loading}
        version={data?.metrics_version ?? 0}
        source={source}
        profile={source === 'lichess' ? lichessProfile : undefined}
        chesscomProfile={source === 'chesscom' ? chesscomProfile : undefined}
        user={data?.user ?? 'unknown'}
        onSourceChange={setSource}
        backfillStartDate={backfillStartDate}
        backfillEndDate={backfillEndDate}
        onBackfillStartChange={setBackfillStartDate}
        onBackfillEndChange={setBackfillEndDate}
      />

      {error ? <div className="card p-3 text-rust">{error}</div> : null}

      {postgresError ? (
        <div className="card p-3 text-rust">{postgresError}</div>
      ) : null}

      {postgresAnalysisError ? (
        <div className="card p-3 text-rust">{postgresAnalysisError}</div>
      ) : null}

      {postgresRawPgnsError ? (
        <div className="card p-3 text-rust">{postgresRawPgnsError}</div>
      ) : null}

      {postgresStatus ? (
        <div className="card p-4" data-testid="postgres-status">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-display text-sand">Postgres status</h3>
            <Badge
              label={
                postgresStatus.status === 'ok'
                  ? 'Connected'
                  : postgresStatus.status === 'disabled'
                    ? 'Disabled'
                    : 'Unreachable'
              }
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="flex flex-col gap-1">
              <Text mode="uppercase" value="Latency" />
              <Text
                size="sm"
                mode="normal"
                value={
                  postgresStatus.latency_ms !== undefined
                    ? `${postgresStatus.latency_ms.toFixed(2)} ms`
                    : 'n/a'
                }
              />
            </div>
            <div className="flex flex-col gap-1">
              <Text mode="uppercase" value="Schema" />
              <Text
                size="sm"
                mode="normal"
                value={postgresStatus.schema ?? 'n/a'}
              />
            </div>
            <div className="flex flex-col gap-1">
              <Text mode="uppercase" value="Tables" />
              <Text
                size="sm"
                mode="normal"
                value={
                  postgresStatus.tables && postgresStatus.tables.length
                    ? postgresStatus.tables.join(', ')
                    : 'n/a'
                }
              />
            </div>
          </div>
          {postgresStatus.error ? (
            <Text mode="error" value={postgresStatus.error} mt="2" />
          ) : null}
          <div className="mt-4">
            <Text mode="uppercase" value="Recent ops events" />
            {postgresStatus.events && postgresStatus.events.length ? (
              <ul className="mt-2 space-y-2 text-xs text-sand/70">
                {postgresStatus.events.slice(0, 5).map((event) => (
                  <li key={event.id} className="flex flex-wrap gap-2">
                    <span className="font-mono text-sand/50">
                      {new Date(event.created_at).toLocaleTimeString()}
                    </span>
                    <span className="text-sand">
                      {event.component}:{event.event_type}
                    </span>
                    {event.source ? <Badge label={event.source} /> : null}
                  </li>
                ))}
              </ul>
            ) : (
              <Text
                size="xs"
                mode="normal"
                value={postgresLoading ? 'Loading events...' : 'No events yet'}
                mt="2"
              />
            )}
          </div>
        </div>
      ) : postgresLoading ? (
        <div className="card p-4 text-sand/70">Loading Postgres status...</div>
      ) : null}

      {postgresRawPgns || postgresRawPgnsLoading || postgresRawPgnsError ? (
        <div className="card p-4" data-testid="postgres-raw-pgns">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-display text-sand">
              Postgres raw PGNs
            </h3>
            <Badge label={postgresRawPgns?.status ?? 'loading'} />
          </div>
          {postgresRawPgnsError ? (
            <Text mode="error" value={postgresRawPgnsError} mt="2" />
          ) : null}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="flex flex-col gap-1">
              <Text mode="uppercase" value="Total rows" />
              <Text
                size="sm"
                mode="normal"
                value={
                  postgresRawPgns
                    ? postgresRawPgns.total_rows.toLocaleString()
                    : '...'
                }
              />
            </div>
            <div className="flex flex-col gap-1">
              <Text mode="uppercase" value="Distinct games" />
              <Text
                size="sm"
                mode="normal"
                value={
                  postgresRawPgns
                    ? postgresRawPgns.distinct_games.toLocaleString()
                    : '...'
                }
              />
            </div>
            <div className="flex flex-col gap-1">
              <Text mode="uppercase" value="Latest ingest" />
              <Text
                size="sm"
                mode="normal"
                value={
                  postgresRawPgns?.latest_ingested_at
                    ? new Date(
                        postgresRawPgns.latest_ingested_at,
                      ).toLocaleString()
                    : 'n/a'
                }
              />
            </div>
          </div>
          <div className="mt-4">
            <Text mode="uppercase" value="By source" />
            {postgresRawPgns?.sources?.length ? (
              <ul className="mt-2 space-y-2 text-xs text-sand/70">
                {postgresRawPgns.sources.map((row) => (
                  <li key={row.source} className="flex flex-wrap gap-2">
                    <Badge label={row.source} />
                    <span className="text-sand">
                      {row.total_rows.toLocaleString()} rows
                    </span>
                    <span className="text-sand/60">
                      {row.distinct_games.toLocaleString()} games
                    </span>
                    {row.latest_ingested_at ? (
                      <span className="text-sand/50">
                        {new Date(row.latest_ingested_at).toLocaleString()}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <Text
                size="xs"
                mode="normal"
                value={
                  postgresRawPgnsLoading
                    ? 'Loading raw PGNs...'
                    : 'No raw PGN rows yet'
                }
                mt="2"
              />
            )}
          </div>
        </div>
      ) : null}

      {postgresAnalysis.length || postgresAnalysisLoading ? (
        <div className="card p-4" data-testid="postgres-analysis">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-display text-sand">
              Postgres analysis results
            </h3>
            <Badge label={`${postgresAnalysis.length} rows`} />
          </div>
          {postgresAnalysis.length ? (
            <ul className="space-y-2 text-xs text-sand/70">
              {postgresAnalysis.slice(0, 5).map((row) => (
                <li key={row.tactic_id} className="flex flex-wrap gap-2">
                  <span className="font-mono text-sand/50">
                    #{row.tactic_id}
                  </span>
                  <span className="text-sand">
                    {row.motif ?? 'unknown'} · {row.result ?? 'n/a'}
                  </span>
                  {row.best_uci ? <Badge label={row.best_uci} /> : null}
                  {row.severity !== null && row.severity !== undefined ? (
                    <Badge label={`sev ${row.severity.toFixed(2)}`} />
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <Text
              size="xs"
              mode="normal"
              value={
                postgresAnalysisLoading
                  ? 'Loading analysis rows...'
                  : 'No analysis rows yet'
              }
              mt="2"
            />
          )}
        </div>
      ) : null}

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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
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
          {source === 'lichess' ? (
            <label className="text-xs text-sand/60 flex flex-col gap-2">
              Lichess profile
              <select
                className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
                value={lichessProfile}
                onChange={(event) =>
                  setLichessProfile(event.target.value as LichessProfile)
                }
                disabled={loading}
                data-testid="filter-lichess-profile"
              >
                {LICHESS_PROFILE_OPTIONS.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          {source === 'chesscom' ? (
            <label className="text-xs text-sand/60 flex flex-col gap-2">
              Chess.com time class
              <select
                className="rounded-md border border-sand/30 bg-night px-3 py-2 text-sm text-sand"
                value={chesscomProfile}
                onChange={(event) =>
                  setChesscomProfile(event.target.value as ChesscomProfile)
                }
                disabled={loading}
                data-testid="filter-chesscom-profile"
              >
                {CHESSCOM_PROFILE_OPTIONS.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
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

      {data ? <MetricsGrid metricsData={motifBreakdown} /> : null}
      {data ? <MetricsTrends metricsData={trendRows} /> : null}
      {data ? <TimeTroubleCorrelation metricsData={timeTroubleRows} /> : null}
      {practiceError ? (
        <div className="card p-3 text-rust">{practiceError}</div>
      ) : null}
      <div className="card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-display text-sand">Practice attempt</h3>
            <Text value={'Play the best move for the current tactic.'} />
          </div>
          {currentPractice ? <Badge label={currentPractice.motif} /> : null}
        </div>
        {currentPractice ? (
          <>
            <PracticeSessionProgress stats={practiceSession} />
            <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
              <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                <Chessboard
                  id="practice-board"
                  position={practiceFen || currentPractice.fen}
                  onPieceDrop={handlePracticeDrop}
                  boardOrientation={practiceOrientation}
                  arePiecesDraggable={!practiceSubmitting}
                  isDraggablePiece={isPiecePlayable(
                    practiceFen,
                    currentPractice,
                  )}
                  customSquareStyles={practiceHighlightStyles}
                />
                <Text
                  mt={'2'}
                  value={'Legal moves only. Drag a piece to submit.'}
                />
              </div>
              <div className="space-y-3">
                <div className="space-y-1">
                  <Text value={'FEN'} />
                  <Text value={currentPractice.fen} mode={'monospace'} />
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
                  <PracticeMoveInput
                    practiceMove={practiceMove}
                    setPracticeMove={setPracticeMove}
                    practiceSubmitting={practiceSubmitting}
                  />
                  <PracticeAttemptButton
                    handlePracticeAttempt={handlePracticeAttempt}
                    practiceSubmitting={practiceSubmitting}
                  />
                </div>
                {practiceSubmitError ? (
                  <Text mode="error" value={practiceSubmitError} />
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
                    <PracticeFeedbackExplanation feedback={practiceFeedback} />
                    <PracticeFeedback feedback={practiceFeedback} />
                  </div>
                ) : null}
              </div>
            </div>
          </>
        ) : (
          <Text value={'No practice items queued yet.'} />
        )}
      </div>
      <PracticeQueue
        data={practiceQueue}
        includeFailedAttempt={includeFailedAttempt}
        onToggleIncludeFailedAttempt={setIncludeFailedAttempt}
        loading={practiceLoading}
      />
      {data ? <TacticsTable tacticsData={data.tactics} /> : null}
      {data ? <PositionsList positionsData={data.positions} /> : null}
    </div>
  );
}

function PracticeFeedbackExplanation({
  feedback,
}: {
  feedback: PracticeAttemptResponse;
}) {
  return feedback.explanation ? (
    <Text mt={'2'} value={feedback.explanation} />
  ) : null;
}

function PracticeFeedback({
  feedback,
}: {
  feedback: PracticeAttemptResponse;
}): JSX.Element {
  return (
    <Text
      mt={'2'}
      mode="monospace"
      size="xs"
      value={buildPracticeFeedback(feedback)}
    />
  );
}
