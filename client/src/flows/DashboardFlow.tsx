import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';
import { DragDropContext, Draggable, Droppable } from '@hello-pangea/dnd';
import { ColumnDef } from '@tanstack/react-table';
import {
  DashboardPayload,
  DashboardFilters,
  GameDetailResponse,
  PostgresAnalysisRow,
  PostgresRawPgnsSummary,
  PostgresStatus,
  PracticeAttemptResponse,
  PracticeQueueItem,
} from '../api';
import {
  fetchDashboard,
  fetchGameDetail,
  fetchPostgresAnalysis,
  fetchPostgresRawPgns,
  fetchPostgresStatus,
  fetchPracticeQueue,
  submitPracticeAttempt,
  getJobStreamUrl,
  getMetricsStreamUrl,
  openEventStream,
} from '../client';
import formatPgnMoveList from '../utils/formatPgnMoveList';
import buildLichessAnalysisUrl from '../utils/buildLichessAnalysisUrl';
import buildPracticeMove from '../utils/buildPracticeMove';
import {
  ChessPlatform,
  ChesscomProfile,
  JobProgressItem,
  LichessProfile,
} from '../types';
import type { MetricsTrendsRow } from '../_components/MetricsTrends';
import {
  Badge,
  ErrorCard,
  FiltersCard,
  MetricsSummaryCard,
  MetricsGrid,
  MotifTrendsCard,
  TimeTroubleCorrelationCard,
  PracticeQueueCard,
  RecentGamesCard,
  RecentTacticsCard,
  JobProgressCard,
  PracticeAttemptCard,
  PositionsList,
  Hero,
  GameDetailModal,
  ChessboardModal,
  DatabaseModal,
  ActionButton,
  FloatingActionButton,
} from '../components';
import {
  PracticeSessionStats,
  applyPracticeAttemptResult,
  resetPracticeSessionStats,
} from '../utils/practiceSession';
import {
  normalizeOrder,
  readCardOrder,
  reorderList,
  writeCardOrder,
} from '../utils/cardOrder';
import {
  ALLOWED_MOTIFS,
  isAllowedMotifFilter,
  isScopedMotif,
} from '../utils/motifScope';
import type { FloatingAction } from '../_components/FloatingActionButton';

const DASHBOARD_CARD_STORAGE_KEY = 'tactix.dashboard.mainCardOrder';
const MOTIF_CARD_STORAGE_KEY = 'tactix.dashboard.motifCardOrder';
const DASHBOARD_CARD_DROPPABLE_ID = 'dashboard-main-cards';
const MOTIF_CARD_DROPPABLE_ID = 'dashboard-motif-cards';
const PRACTICE_FEEDBACK_DELAY_MS = 600;
const DAY_MS = 24 * 60 * 60 * 1000;
const BACKFILL_WINDOW_DAYS = 900;
const DEFAULT_TIME_CONTROLS = [
  'bullet',
  'blitz',
  'rapid',
  'classical',
  'unknown',
];
const DEFAULT_FILTERS = {
  motif: 'all',
  timeControl: 'all',
  ratingBucket: 'all',
  startDate: '',
  endDate: '',
};
const DASHBOARD_CARD_IDS = [
  'metrics-summary',
  'job-progress',
  'metrics-grid',
  'metrics-trends',
  'time-trouble-correlation',
  'practice-queue',
  'recent-games',
  'tactics-table',
  'positions-list',
  'practice-attempt',
];

const areArraysEqual = (left: string[], right: string[]) => {
  if (left.length !== right.length) return false;
  return left.every((value, index) => value === right[index]);
};

const formatPercent = (value: number | null) =>
  value === null || Number.isNaN(value) ? '--' : `${(value * 100).toFixed(1)}%`;

const formatCorrelation = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  const rounded = value.toFixed(2);
  return value > 0 ? `+${rounded}` : rounded;
};

const formatRate = (value: number | null) =>
  value === null || Number.isNaN(value) ? '--' : `${(value * 100).toFixed(1)}%`;

type PracticeButtonState = {
  label: string;
  helper: string;
  disabled: boolean;
};

type PracticeButtonStateInput = {
  loading: boolean;
  error: string | null;
  hasPractice: boolean;
  queueLength: number;
  modalOpen: boolean;
  sessionTotal: number;
};

const PRACTICE_LOADING_STATE: PracticeButtonState = {
  label: 'Loading practice...',
  helper: 'Fetching the daily practice queue.',
  disabled: true,
};

const PRACTICE_COMPLETE_STATE: PracticeButtonState = {
  label: 'Practice complete',
  helper: 'Daily set complete. Great work.',
  disabled: true,
};

const PRACTICE_EMPTY_STATE: PracticeButtonState = {
  label: 'No practice items',
  helper: 'Refresh metrics to find new tactics.',
  disabled: true,
};

const createPracticeErrorState = (message: string): PracticeButtonState => ({
  label: 'Practice unavailable',
  helper: message,
  disabled: true,
});

const createPracticeReadyState = (
  count: number,
  modalOpen: boolean,
): PracticeButtonState => {
  const label = modalOpen ? 'Continue practice' : 'Start practice';
  const helper = `${count} tactic${count === 1 ? '' : 's'} ready.`;
  return { label, helper, disabled: false };
};

const buildPracticeButtonState = (
  input: PracticeButtonStateInput,
): PracticeButtonState => {
  if (input.loading) return PRACTICE_LOADING_STATE;
  if (input.error) return createPracticeErrorState(input.error);
  if (input.hasPractice) {
    return createPracticeReadyState(input.queueLength, input.modalOpen);
  }
  if (input.sessionTotal > 0) return PRACTICE_COMPLETE_STATE;
  return PRACTICE_EMPTY_STATE;
};

const filterScopedMetrics = (metrics: DashboardPayload['metrics']) =>
  metrics.filter((row) => isAllowedMotifFilter(row.motif));

const ensureMotifBreakdownDefaults = (
  metrics: DashboardPayload['metrics'],
  source: ChessPlatform,
) => {
  const motifRows = metrics.filter(
    (row) => row.metric_type === 'motif_breakdown',
  );
  const existing = new Set(motifRows.map((row) => row.motif));
  if (ALLOWED_MOTIFS.every((motif) => existing.has(motif))) {
    return metrics;
  }
  const template = motifRows[0];
  const ratingBucket = template?.rating_bucket ?? 'all';
  const timeControl = template?.time_control ?? 'all';
  const updatedAt = template?.updated_at ?? new Date().toISOString();
  const baseSource = template?.source ?? source;

  const defaults = ALLOWED_MOTIFS.filter((motif) => !existing.has(motif)).map(
    (motif) => ({
      source: baseSource,
      metric_type: 'motif_breakdown',
      motif,
      window_days: null,
      trend_date: null,
      rating_bucket: ratingBucket,
      time_control: timeControl,
      total: 0,
      found: 0,
      missed: 0,
      failed_attempt: 0,
      unclear: 0,
      found_rate: 0,
      miss_rate: 0,
      updated_at: updatedAt,
    }),
  );

  return [...metrics, ...defaults];
};

const filterScopedTactics = (tactics: DashboardPayload['tactics']) =>
  tactics.filter((row) => isScopedMotif(row.motif));

const filterScopedPracticeQueue = (items: PracticeQueueItem[]) =>
  items.filter((item) => isScopedMotif(item.motif));

const formatGameResult = (result: string | null, userColor: string | null) => {
  if (!result) return '--';
  if (result === '1/2-1/2') return 'Draw';
  if (result === '1-0') {
    if (userColor === 'white') return 'Win';
    if (userColor === 'black') return 'Loss';
  }
  if (result === '0-1') {
    if (userColor === 'black') return 'Win';
    if (userColor === 'white') return 'Loss';
  }
  return result;
};

const formatGameDate = (value: string | null) => {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
};

const openLichessAnalysisWindow = (url: string) => {
  window.open(url, '_blank', 'noopener,noreferrer');
};

const waitForPracticeFeedback = () =>
  new Promise((resolve) => setTimeout(resolve, PRACTICE_FEEDBACK_DELAY_MS));

const parseBackfillDate = (value: string, fallbackMs: number) => {
  const date = value ? new Date(`${value}T00:00:00`) : new Date(fallbackMs);
  return date.getTime();
};

const resolveBackfillWindow = (
  startDate: string,
  endDate: string,
  nowMs: number,
) => {
  const startMs = parseBackfillDate(
    startDate,
    nowMs - BACKFILL_WINDOW_DAYS * DAY_MS,
  );
  const endMs = parseBackfillDate(endDate, nowMs);
  const cappedEnd = Math.min(endMs + DAY_MS, nowMs);
  if (Number.isNaN(startMs) || Number.isNaN(cappedEnd)) {
    throw new Error('Invalid backfill date range');
  }
  if (startMs >= cappedEnd) {
    throw new Error('Backfill range must end after the start date');
  }
  return { startMs, endMs: cappedEnd };
};

type BaseCardDragHandleProps = React.ButtonHTMLAttributes<HTMLButtonElement>;
type BaseCardRenderProps = {
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
};

type BaseCardEntry = {
  id: string;
  label: string;
  visible: boolean;
  render: (props: BaseCardRenderProps) => JSX.Element | null;
};
type PositionEntry = DashboardPayload['positions'][number];

export default function DashboardFlow() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [source, setSource] = useState<ChessPlatform>('all');
  const [lichessProfile, setLichessProfile] = useState<LichessProfile>('rapid');
  const [chesscomProfile, setChesscomProfile] =
    useState<ChesscomProfile>('blitz');
  const [filters, setFilters] = useState(() => ({ ...DEFAULT_FILTERS }));
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
  const practiceMoveRef = useRef<HTMLInputElement | null>(null);
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
  const practiceSessionCompletedRef = useRef(0);
  const practiceSessionTotalRef = useRef<number | null>(null);
  const practiceScopeRef = useRef(`${source}:${includeFailedAttempt}`);
  const practiceSessionScopeRef = useRef(`${source}:${includeFailedAttempt}`);
  const practiceSessionInitializedRef = useRef(false);
  const [jobProgress, setJobProgress] = useState<JobProgressItem[]>([]);
  const [jobStatus, setJobStatus] = useState<
    'idle' | 'running' | 'error' | 'complete'
  >('idle');
  const [dashboardCardOrder, setDashboardCardOrder] = useState(() => {
    const stored = readCardOrder(
      DASHBOARD_CARD_STORAGE_KEY,
      DASHBOARD_CARD_IDS,
    );
    return normalizeOrder(stored, DASHBOARD_CARD_IDS);
  });
  const [dropIndicatorIndex, setDropIndicatorIndex] = useState<number | null>(
    null,
  );
  const [motifDropIndicatorIndex, setMotifDropIndicatorIndex] = useState<
    number | null
  >(null);
  const [motifCardOrder, setMotifCardOrder] = useState<string[]>([]);
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
  const [gameDetailOpen, setGameDetailOpen] = useState(false);
  const [gameDetail, setGameDetail] = useState<GameDetailResponse | null>(null);
  const [gameDetailLoading, setGameDetailLoading] = useState(false);
  const [gameDetailError, setGameDetailError] = useState<string | null>(null);
  const [chessboardModalOpen, setChessboardModalOpen] = useState(false);
  const [chessboardPosition, setChessboardPosition] =
    useState<PositionEntry | null>(null);
  const [filtersModalOpen, setFiltersModalOpen] = useState(false);
  const [databaseModalOpen, setDatabaseModalOpen] = useState(false);
  const [practiceModalOpen, setPracticeModalOpen] = useState(false);
  const practiceStatusId = useId();

  const resetPracticeSessionScope = useCallback(
    (nextSource: ChessPlatform, nextIncludeFailed: boolean) => {
      practiceScopeRef.current = `${nextSource}:${nextIncludeFailed}`;
      practiceSessionTotalRef.current = null;
      practiceSessionCompletedRef.current = 0;
    },
    [],
  );

  const currentPractice = useMemo(
    () => (practiceQueue.length ? practiceQueue[0] : null),
    [practiceQueue],
  );

  const practiceButtonState = useMemo(
    () =>
      buildPracticeButtonState({
        loading: practiceLoading,
        error: practiceError,
        hasPractice: Boolean(currentPractice),
        queueLength: practiceQueue.length,
        modalOpen: practiceModalOpen,
        sessionTotal: practiceSession.total,
      }),
    [
      currentPractice,
      practiceError,
      practiceLoading,
      practiceModalOpen,
      practiceQueue.length,
      practiceSession.total,
    ],
  );

  const floatingActions = useMemo<FloatingAction[]>(
    () => [
      {
        id: 'filters',
        label: 'Filters',
        ariaLabel: 'Open filters',
        testId: 'filters-open',
        onClick: () => setFiltersModalOpen(true),
      },
      {
        id: 'database',
        label: 'Database',
        ariaLabel: 'Open database details',
        testId: 'database-open',
        onClick: () => setDatabaseModalOpen(true),
      },
    ],
    [setDatabaseModalOpen, setFiltersModalOpen],
  );

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

  const handleSourceChange = useCallback(
    (next: ChessPlatform) => {
      resetPracticeSessionScope(next, includeFailedAttempt);
      setSource(next);
    },
    [includeFailedAttempt, resetPracticeSessionScope],
  );

  const ensureSourceSelected = (message: string) => {
    if (source !== 'all') return true;
    setError(message);
    return false;
  };

  const startJob = () => {
    setLoading(true);
    setError(null);
    setJobProgress([]);
    setJobStatus('running');
  };

  const handleJobError = (message: string, err: unknown) => {
    console.error(err);
    setError(message);
    setJobStatus('error');
  };

  const handleLichessProfileChange = (next: LichessProfile) => {
    setLichessProfile(next);
  };

  const handleChesscomProfileChange = (next: ChesscomProfile) => {
    setChesscomProfile(next);
  };

  const handleFiltersChange = useCallback(
    (next: typeof filters) => {
      setFilters(next);
    },
    [setFilters],
  );

  const resolveGameSource = useCallback(
    (rowSource?: string | null) =>
      rowSource ?? (source === 'all' ? undefined : source),
    [source],
  );

  const handleOpenChessboardModal = useCallback((position: PositionEntry) => {
    setChessboardPosition(position);
    setChessboardModalOpen(true);
    setPracticeModalOpen(false);
  }, []);

  const handleCloseChessboardModal = useCallback(() => {
    setChessboardModalOpen(false);
    setChessboardPosition(null);
  }, []);

  const handleOpenPracticeModal = useCallback(() => {
    if (!currentPractice) return;
    setChessboardModalOpen(false);
    setPracticeModalOpen(true);
  }, [currentPractice]);

  const handleClosePracticeModal = useCallback(() => {
    setPracticeModalOpen(false);
    setPracticeFeedback(null);
    setPracticeSubmitError(null);
  }, [setPracticeFeedback, setPracticeModalOpen, setPracticeSubmitError]);

  const handleOpenLichess = useCallback(
    async (row: { game_id?: string | null; source?: string | null }) => {
      if (!row.game_id) return;
      const popup = window.open('about:blank', '_blank');
      try {
        const detail = await fetchGameDetail(
          row.game_id,
          resolveGameSource(row.source),
        );
        const url = buildLichessAnalysisUrl(detail.pgn);
        if (!url) {
          console.warn('Unable to build Lichess analysis URL for game.', {
            gameId: row.game_id,
          });
          if (popup) popup.close();
          return;
        }
        if (popup) {
          popup.location.href = url;
          popup.opener = null;
        } else {
          openLichessAnalysisWindow(url);
        }
      } catch (err) {
        if (popup) popup.close();
        console.error(err);
      }
    },
    [resolveGameSource],
  );

  const handleOpenGameDetail = useCallback(
    async (row: { game_id?: string | null; source?: string | null }) => {
      if (!row.game_id) {
        setGameDetailError('Selected game is missing a game id.');
        setGameDetailOpen(true);
        return;
      }
      setGameDetailOpen(true);
      setGameDetailLoading(true);
      setGameDetailError(null);
      setGameDetail(null);
      try {
        const detail = await fetchGameDetail(
          row.game_id,
          resolveGameSource(row.source),
        );
        setGameDetail(detail);
      } catch (err) {
        console.error(err);
        setGameDetailError('Failed to load game details.');
      } finally {
        setGameDetailLoading(false);
      }
    },
    [resolveGameSource],
  );

  const handleResetFilters = useCallback(() => {
    setFilters({ ...DEFAULT_FILTERS });
  }, [setFilters]);

  const handleBackfillStartChange = (value: string) => {
    setBackfillStartDate(value);
  };

  const handleBackfillEndChange = (value: string) => {
    setBackfillEndDate(value);
  };

  const handleIncludeFailedAttemptChange = useCallback(
    (next: boolean) => {
      resetPracticeSessionScope(source, next);
      setIncludeFailedAttempt(next);
    },
    [resetPracticeSessionScope, source],
  );

  const handlePracticeMoveChange = useCallback(
    (value: string) => {
      setPracticeMove(value);
    },
    [setPracticeMove],
  );

  async function load(
    nextSource: ChessPlatform = source,
    nextFilters: DashboardFilters = normalizedFilters,
  ) {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchDashboard(nextSource, nextFilters);
      const scopedMetrics = ensureMotifBreakdownDefaults(
        filterScopedMetrics(payload.metrics),
        nextSource,
      );
      setData({
        ...payload,
        metrics: scopedMetrics,
        tactics: filterScopedTactics(payload.tactics),
      });
    } catch (err) {
      console.error(err);
      setError('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }

  const loadPracticeQueue = useCallback(
    async (
      nextSource: ChessPlatform = source,
      includeFailed = includeFailedAttempt,
      resetSession = false,
      excludeTacticIds?: Set<number>,
    ): Promise<void> => {
      setPracticeLoading(true);
      setPracticeError(null);
      try {
        const requestScope = `${nextSource}:${includeFailed}`;
        const payload = await fetchPracticeQueue(nextSource, includeFailed);
        if (practiceScopeRef.current !== requestScope) {
          return;
        }
        const scopedItems = filterScopedPracticeQueue(payload.items);
        const filteredItems = excludeTacticIds?.size
          ? scopedItems.filter((item) => !excludeTacticIds.has(item.tactic_id))
          : scopedItems;
        setPracticeQueue(filteredItems);
        if (resetSession) {
          practiceSessionScopeRef.current = requestScope;
        }
        setPracticeSession((prev) => {
          if (prev.total > 0) return prev;
          practiceSessionInitializedRef.current = true;
          practiceSessionCompletedRef.current = 0;
          practiceSessionTotalRef.current = filteredItems.length;
          return resetPracticeSessionStats(filteredItems.length);
        });
      } catch (err) {
        console.error(err);
        setPracticeError('Failed to load practice queue');
      } finally {
        setPracticeLoading(false);
      }
    },
    [includeFailedAttempt, source],
  );

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
      setPostgresAnalysis(filterScopedTactics(payload.tactics || []));
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

  useEffect(() => {
    practiceScopeRef.current = `${source}:${includeFailedAttempt}`;
  }, [source, includeFailedAttempt]);

  useEffect(() => {
    function resetPracticeData(): void {
      setPracticeMove('');
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
    if (!practiceModalOpen) return;
    if (
      practiceQueue.length === 0 &&
      practiceSessionInitializedRef.current &&
      !practiceFeedback
    ) {
      setPracticeModalOpen(false);
    }
  }, [practiceFeedback, practiceModalOpen, practiceQueue.length]);

  useEffect(() => {
    resetJobState();
  }, [source, lichessProfile, chesscomProfile]);

  const pushJobProgress__payload = useCallback(
    (payload: Record<string, unknown>) => {
      setJobProgress((prev) => [...prev, payload as JobProgressItem]);
    },
    [],
  );

  const applyMetricsUpdate__payload = useCallback(
    (payload: Record<string, unknown>) => {
      setData((prev) => {
        if (!prev) {
          return payload as DashboardPayload;
        }
        return {
          ...prev,
          metrics:
            (payload?.metrics as DashboardPayload['metrics']) ?? prev.metrics,
          metrics_version:
            (payload?.metrics_version as number | undefined) ??
            prev.metrics_version,
          source:
            (payload?.source as DashboardPayload['source']) ?? prev.source,
        };
      });
    },
    [],
  );

  const consumeEventStream = async (
    streamUrl: string,
    controller: AbortController,
    handleEvent: (
      eventName: string,
      data: string,
    ) => Promise<boolean | void> | boolean | void,
  ) => {
    const reader = await openEventStream(streamUrl, controller.signal);
    const decoder = new TextDecoder();
    let buffer = '';
    let streamFinished = false;

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
        if (!data) continue;
        const shouldFinish = await handleEvent(eventName, data);
        if (shouldFinish) {
          streamFinished = true;
          return;
        }
      }
    }

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        await parseChunk(decoder.decode(value, { stream: true }));
        if (streamFinished) {
          break;
        }
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      throw err;
    }
  };

  const streamJobEvents = async (
    job: string,
    nextSource: ChessPlatform,
    disconnectMessage: string,
    nextFilters: DashboardFilters = normalizedFilters,
    profile?: LichessProfile | ChesscomProfile,
    backfillStartMs?: number,
    backfillEndMs?: number,
    refreshDashboardOnComplete = true,
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
    try {
      await consumeEventStream(
        streamUrl,
        controller,
        async (eventName, data) => {
          let payload: Record<string, unknown> | null = null;
          try {
            payload = JSON.parse(data) as Record<string, unknown>;
          } catch (parseError) {
            console.error(parseError);
            return false;
          }

          if (
            eventName === 'progress' ||
            eventName === 'error' ||
            eventName === 'complete'
          ) {
            pushJobProgress__payload(payload);
          }

          if (eventName === 'metrics_update') {
            applyMetricsUpdate__payload(payload);
          }

          if (eventName === 'complete') {
            setJobStatus('complete');
            if (refreshDashboardOnComplete) {
              const dashboard = await fetchDashboard(nextSource, nextFilters);
              setData(dashboard);
              await loadPracticeQueue(nextSource, includeFailedAttempt, true);
              await loadPostgres();
              await loadPostgresAnalysis();
            }
            setLoading(false);
            return true;
          }

          if (eventName === 'error') {
            setJobStatus('error');
            setLoading(false);
            setError(disconnectMessage);
            if (refreshDashboardOnComplete) {
              await loadPostgres();
              await loadPostgresAnalysis();
            }
            return true;
          }

          return false;
        },
      );
    } finally {
      if (streamAbortRef.current === controller) {
        streamAbortRef.current = null;
      }
    }
  };

  const streamMetricsEvents = async (
    nextSource: ChessPlatform,
    nextFilters: DashboardFilters = normalizedFilters,
  ): Promise<boolean> => {
    streamAbortRef.current?.abort();
    const controller = new AbortController();
    streamAbortRef.current = controller;
    let succeeded = true;

    const streamUrl = getMetricsStreamUrl(nextSource, nextFilters);
    try {
      await consumeEventStream(
        streamUrl,
        controller,
        async (eventName, data) => {
          let payload: Record<string, unknown> | null = null;
          try {
            payload = JSON.parse(data) as Record<string, unknown>;
          } catch (parseError) {
            console.error(parseError);
            return false;
          }

          if (
            eventName === 'progress' ||
            eventName === 'error' ||
            eventName === 'complete'
          ) {
            pushJobProgress__payload(payload);
          }

          if (eventName === 'metrics_update') {
            applyMetricsUpdate__payload(payload);
          }

          if (eventName === 'complete') {
            setJobStatus('complete');
            setLoading(false);
            return true;
          }

          if (eventName === 'error') {
            succeeded = false;
            setJobStatus('error');
            setLoading(false);
            setError('Metrics stream disconnected');
            return true;
          }

          return false;
        },
      );
    } finally {
      if (streamAbortRef.current === controller) {
        streamAbortRef.current = null;
      }
    }
    return succeeded;
  };

  const handleRun = async () => {
    if (!ensureSourceSelected('Select a specific site to run the pipeline.')) {
      return;
    }
    startJob();
    try {
      const profile = source === 'lichess' ? lichessProfile : chesscomProfile;
      await streamJobEvents(
        'daily_game_sync',
        source,
        'Pipeline stream disconnected',
        normalizedFilters,
        profile,
      );
    } catch (err) {
      handleJobError('Pipeline run failed', err);
      setLoading(false);
    }
  };

  const handleBackfill = async () => {
    if (!ensureSourceSelected('Select a specific site to run a backfill.')) {
      return;
    }
    startJob();
    try {
      const { startMs, endMs } = resolveBackfillWindow(
        backfillStartDate,
        backfillEndDate,
        Date.now(),
      );
      const profile = source === 'lichess' ? lichessProfile : chesscomProfile;
      await streamJobEvents(
        'daily_game_sync',
        source,
        'Backfill stream disconnected',
        normalizedFilters,
        profile,
        startMs,
        endMs,
      );
    } catch (err) {
      handleJobError('Backfill run failed', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMigrations = async () => {
    if (!ensureSourceSelected('Select a specific site to run migrations.')) {
      return;
    }
    startJob();
    try {
      await streamJobEvents(
        'migrations',
        source,
        'Migration stream disconnected',
        normalizedFilters,
      );
    } catch (err) {
      handleJobError('Migration run failed', err);
      setLoading(false);
    }
  };

  const handleRefreshMetrics = async () => {
    if (!ensureSourceSelected('Select a specific site to refresh metrics.')) {
      return;
    }
    startJob();
    try {
      const ok = await streamMetricsEvents(source, normalizedFilters);
      if (ok) {
        await loadPracticeQueue(source, includeFailedAttempt);
      }
    } catch (err) {
      handleJobError('Metrics refresh failed', err);
    } finally {
      setLoading(false);
    }
  };

  function resetJobState(): void {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    setJobProgress([]);
    setJobStatus('idle');
  }

  const getPracticeBaseFen = useCallback(
    () => practiceFen || currentPractice?.fen || '',
    [currentPractice, practiceFen],
  );

  const submitPracticeMove = useCallback(
    async (payload: {
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
        setPracticeSession((prev) => {
          const { stats, shouldReschedule } = applyPracticeAttemptResult(prev, {
            correct: response.correct,
            rescheduled: response.rescheduled,
          });
          practiceSessionCompletedRef.current = stats.completed;
          if (shouldReschedule) {
            practiceSessionTotalRef.current = stats.total;
          }
          return stats;
        });
        const excludeTacticIds = response.correct
          ? new Set([currentPractice.tactic_id])
          : undefined;
        if (excludeTacticIds) {
          setPracticeQueue((prev) =>
            prev.filter((item) => !excludeTacticIds.has(item.tactic_id)),
          );
        }
        // Allow feedback to render before queue refresh resets practice state.
        await waitForPracticeFeedback();
        await loadPracticeQueue(
          source,
          includeFailedAttempt,
          false,
          excludeTacticIds,
        );
      } catch (err) {
        console.error(err);
        setPracticeSubmitError('Failed to submit practice attempt');
      } finally {
        setPracticeSubmitting(false);
      }
    },
    [
      currentPractice,
      includeFailedAttempt,
      loadPracticeQueue,
      practiceServedAtMs,
      setPracticeFeedback,
      setPracticeFen,
      setPracticeLastMove,
      setPracticeMove,
      setPracticeSession,
      setPracticeSubmitError,
      setPracticeSubmitting,
      source,
    ],
  );

  const handlePracticeAttempt = useCallback(
    async (overrideMove?: string) => {
      if (!currentPractice) return;
      const candidate = overrideMove ?? practiceMove;
      if (!candidate.trim()) {
        setPracticeSubmitError('Enter a move in UCI notation (e.g., e2e4).');
        return;
      }
      const baseFen = getPracticeBaseFen();
      const moveResult = buildPracticeMove(baseFen, candidate);
      if (!moveResult) {
        setPracticeSubmitError(
          'Illegal move for this position. Try a legal UCI move.',
        );
        return;
      }
      await submitPracticeMove(moveResult);
    },
    [
      currentPractice,
      getPracticeBaseFen,
      practiceMove,
      setPracticeSubmitError,
      submitPracticeMove,
    ],
  );

  const handlePracticeDrop = useCallback(
    (from: string, to: string, piece: string) => {
      if (!currentPractice || practiceSubmitting) return false;
      const baseFen = getPracticeBaseFen();
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
    },
    [
      currentPractice,
      getPracticeBaseFen,
      practiceSubmitting,
      setPracticeSubmitError,
      submitPracticeMove,
    ],
  );

  const totals = useMemo(() => {
    if (!data) return { positions: 0, tactics: 0 };
    return {
      positions: data.positions.length,
      tactics: data.tactics.length,
    };
  }, [data]);

  const selectedRatingBucket =
    filters.ratingBucket === 'all' ? null : filters.ratingBucket;
  const selectedTimeControl =
    filters.timeControl === 'all' ? null : filters.timeControl;

  const motifBreakdown = useMemo(() => {
    if (!data) return [];
    return data.metrics.filter((row) => {
      if (row.metric_type !== 'motif_breakdown') return false;
      if (selectedRatingBucket && row.rating_bucket !== selectedRatingBucket) {
        return false;
      }
      if (selectedTimeControl && row.time_control !== selectedTimeControl) {
        return false;
      }
      return true;
    });
  }, [data, selectedRatingBucket, selectedTimeControl]);

  const motifCardIds = useMemo(() => {
    if (!data) return [];
    const motifs = new Set<string>();
    data.metrics.forEach((row) => {
      if (row.metric_type === 'motif_breakdown' && row.motif) {
        motifs.add(row.motif);
      }
    });
    return Array.from(motifs);
  }, [data]);

  useEffect(() => {
    if (!motifCardIds.length) return;
    setMotifCardOrder((prev) => {
      const base = prev.length
        ? prev
        : readCardOrder(MOTIF_CARD_STORAGE_KEY, motifCardIds);
      const normalized = normalizeOrder(base, motifCardIds);
      return areArraysEqual(normalized, prev) ? prev : normalized;
    });
  }, [motifCardIds]);

  const trendRows = useMemo(() => {
    if (!data) return [];
    return data.metrics.filter((row) => {
      if (row.metric_type !== 'trend') return false;
      if (selectedRatingBucket && row.rating_bucket !== selectedRatingBucket) {
        return false;
      }
      if (selectedTimeControl && row.time_control !== selectedTimeControl) {
        return false;
      }
      return true;
    });
  }, [data, selectedRatingBucket, selectedTimeControl]);

  const trendLatestRows = useMemo<MetricsTrendsRow[]>(() => {
    if (!trendRows.length) return [];
    const map = new Map<string, MetricsTrendsRow>();
    trendRows.forEach((row) => {
      if (!row.trend_date) return;
      const current = map.get(row.motif) || { motif: row.motif };
      const slot =
        row.window_days === 7
          ? 'seven'
          : row.window_days === 30
            ? 'thirty'
            : null;
      if (!slot) return;
      const existing = current[slot];
      if (
        !existing ||
        new Date(row.trend_date) > new Date(existing.trend_date || 0)
      ) {
        current[slot] = row;
      }
      map.set(row.motif, current);
    });
    return Array.from(map.values());
  }, [trendRows]);

  const timeTroubleRows = useMemo(() => {
    if (!data) return [];
    return data.metrics.filter((row) => {
      if (row.metric_type !== 'time_trouble_correlation') return false;
      if (row.rating_bucket && row.rating_bucket !== 'all') return false;
      if (!selectedTimeControl) {
        return row.time_control !== 'all';
      }
      return row.time_control === selectedTimeControl;
    });
  }, [data, selectedTimeControl]);

  const timeTroubleSortedRows = useMemo(() => {
    if (!timeTroubleRows.length) return [];
    return [...timeTroubleRows].sort((a, b) => {
      const left = a.time_control ?? 'unknown';
      const right = b.time_control ?? 'unknown';
      return left.localeCompare(right);
    });
  }, [timeTroubleRows]);

  const gameDetailMoves = useMemo(() => {
    if (!gameDetail?.pgn) return [];
    return formatPgnMoveList(gameDetail.pgn);
  }, [gameDetail]);

  const tacticsColumns = useMemo<
    ColumnDef<DashboardPayload['tactics'][number]>[]
  >(
    () => [
      {
        header: 'Motif',
        accessorKey: 'motif',
        cell: (info) => (
          <span className="font-display text-sm uppercase tracking-wide">
            {String(info.getValue())}
          </span>
        ),
      },
      {
        header: 'Result',
        accessorKey: 'result',
        cell: (info) => <Badge label={String(info.getValue() || '--')} />,
      },
      {
        header: 'Move',
        accessorKey: 'user_uci',
        cell: (info) => (
          <span className="font-mono text-xs">
            {String(info.getValue() || '--')}
          </span>
        ),
      },
      {
        header: 'Delta (cp)',
        accessorKey: 'eval_delta',
        cell: (info) => (
          <span className="font-mono text-xs text-rust">
            {String(info.getValue() ?? '--')}
          </span>
        ),
      },
      {
        header: 'Actions',
        id: 'tactics-actions',
        cell: ({ row }) => {
          const hasGameId = Boolean(row.original.game_id);
          const gameId = row.original.game_id ?? 'unknown';
          const buttonClasses =
            'rounded border border-white/10 px-2 py-1 text-xs text-sand/80 hover:border-white/30 disabled:cursor-not-allowed disabled:border-white/5 disabled:text-sand/40';
          return (
            <div className="flex flex-wrap gap-2">
              <ActionButton
                className={buttonClasses}
                data-testid={`tactics-go-to-game-${gameId}`}
                aria-label="Go to game"
                disabled={!hasGameId}
                onClick={(event) => {
                  event.stopPropagation();
                  if (!hasGameId) return;
                  void handleOpenGameDetail(row.original);
                }}
              >
                Go to Game
              </ActionButton>
              <ActionButton
                className={buttonClasses}
                data-testid={`tactics-open-lichess-${gameId}`}
                aria-label="Open in Lichess"
                disabled={!hasGameId}
                onClick={(event) => {
                  event.stopPropagation();
                  if (!hasGameId) return;
                  void handleOpenLichess(row.original);
                }}
              >
                Open in Lichess
              </ActionButton>
            </div>
          );
        },
      },
    ],
    [handleOpenGameDetail, handleOpenLichess],
  );

  const practiceQueueColumns = useMemo<ColumnDef<PracticeQueueItem>[]>(
    () => [
      {
        header: 'Motif',
        accessorKey: 'motif',
        cell: (info) => (
          <span className="font-display text-sm uppercase tracking-wide">
            {String(info.getValue())}
          </span>
        ),
      },
      {
        header: 'Result',
        accessorKey: 'result',
        cell: (info) => <Badge label={String(info.getValue())} />,
      },
      {
        header: 'Best',
        accessorKey: 'best_uci',
        cell: (info) => (
          <span className="font-mono text-xs text-teal">
            {String(info.getValue() || '--')}
          </span>
        ),
      },
      {
        header: 'Your move',
        accessorKey: 'user_uci',
        cell: (info) => (
          <span className="font-mono text-xs">{String(info.getValue())}</span>
        ),
      },
      {
        header: 'Move',
        accessorFn: (row) => `${row.move_number}.${row.ply}`,
        cell: (info) => (
          <span className="font-mono text-xs">{String(info.getValue())}</span>
        ),
      },
      {
        header: 'Delta',
        accessorKey: 'eval_delta',
        cell: (info) => (
          <span className="font-mono text-xs text-rust">
            {String(info.getValue())}
          </span>
        ),
      },
    ],
    [],
  );

  const metricsTrendsColumns = useMemo<ColumnDef<MetricsTrendsRow>[]>(
    () => [
      {
        header: 'Motif',
        accessorKey: 'motif',
        cell: (info) => (
          <span className="font-display text-sm uppercase tracking-wide">
            {String(info.getValue())}
          </span>
        ),
      },
      {
        header: '7g found',
        accessorFn: (row) => row.seven?.found_rate ?? null,
        cell: (info) => (
          <span className="font-mono text-xs text-teal">
            {formatPercent(info.getValue() as number | null)}
          </span>
        ),
      },
      {
        header: '30g found',
        accessorFn: (row) => row.thirty?.found_rate ?? null,
        cell: (info) => (
          <span className="font-mono text-xs text-teal">
            {formatPercent(info.getValue() as number | null)}
          </span>
        ),
      },
      {
        header: 'Last update',
        accessorFn: (row) =>
          row.seven?.trend_date || row.thirty?.trend_date || '--',
        cell: (info) => (
          <span className="font-mono text-xs text-sand/70">
            {String(info.getValue())}
          </span>
        ),
      },
    ],
    [],
  );

  const timeTroubleColumns = useMemo<
    ColumnDef<DashboardPayload['metrics'][number]>[]
  >(
    () => [
      {
        header: 'Time control',
        accessorKey: 'time_control',
        cell: (info) => (
          <span className="text-sand">
            {String(info.getValue() ?? 'unknown')}
          </span>
        ),
      },
      {
        header: 'Correlation',
        accessorFn: (row) => row.found_rate ?? null,
        cell: (info) => (
          <span className="text-sand">
            {formatCorrelation(info.getValue() as number | null)}
          </span>
        ),
      },
      {
        header: 'Time trouble rate',
        accessorFn: (row) => row.miss_rate ?? null,
        cell: (info) => (
          <span className="text-sand">
            {formatRate(info.getValue() as number | null)}
          </span>
        ),
      },
      {
        header: 'Samples',
        accessorKey: 'total',
        cell: (info) => (
          <span className="text-sand/80">{String(info.getValue())}</span>
        ),
      },
    ],
    [],
  );

  const recentGamesColumns = useMemo<
    ColumnDef<DashboardPayload['recent_games'][number]>[]
  >(
    () => [
      {
        header: 'Source',
        accessorKey: 'source',
        cell: (info) => (
          <span className="text-sand/80">
            {String(info.getValue() ?? 'unknown')}
          </span>
        ),
      },
      {
        header: 'Opponent',
        accessorKey: 'opponent',
        cell: (info) => (
          <span className="text-sand">{String(info.getValue() ?? '--')}</span>
        ),
      },
      {
        header: 'Result',
        accessorFn: (row) =>
          formatGameResult(row.result ?? null, row.user_color ?? null),
        cell: (info) => <Badge label={String(info.getValue() ?? '--')} />,
      },
      {
        header: 'Date',
        accessorFn: (row) => formatGameDate(row.played_at ?? null),
        cell: (info) => (
          <span className="text-sand/70">
            {String(info.getValue() ?? '--')}
          </span>
        ),
      },
      {
        header: 'Time control',
        accessorKey: 'time_control',
        cell: (info) => (
          <span className="text-sand/70">
            {String(info.getValue() ?? '--')}
          </span>
        ),
      },
      {
        header: 'Actions',
        id: 'lichess-actions',
        cell: ({ row }) => {
          if (!row.original.game_id) {
            return <span className="text-sand/40">--</span>;
          }
          return (
            <ActionButton
              className="rounded border border-white/10 px-2 py-1 text-xs text-sand/80 hover:border-white/30"
              data-testid={`open-lichess-${row.original.game_id}`}
              onClick={(event) => {
                event.stopPropagation();
                void handleOpenLichess(row.original);
              }}
            >
              Open in Lichess
            </ActionButton>
          );
        },
      },
    ],
    [handleOpenLichess],
  );

  const practiceOrientation = useMemo(() => {
    const side = currentPractice?.fen?.split(' ')[1];
    return side === 'b' ? 'black' : 'white';
  }, [currentPractice]);

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
    const values = new Set<string>(DEFAULT_TIME_CONTROLS);
    data?.metrics.forEach((row) => {
      const value = row.time_control || 'unknown';
      if (value !== 'all') values.add(value);
    });
    const custom = Array.from(values).filter(
      (value) => value !== 'all' && !DEFAULT_TIME_CONTROLS.includes(value),
    );
    return [
      'all',
      ...DEFAULT_TIME_CONTROLS.filter((value) => values.has(value)),
      ...custom.sort(),
    ];
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

  useEffect(() => {
    writeCardOrder(DASHBOARD_CARD_STORAGE_KEY, dashboardCardOrder);
  }, [dashboardCardOrder]);

  useEffect(() => {
    if (!motifCardOrder.length) return;
    writeCardOrder(MOTIF_CARD_STORAGE_KEY, motifCardOrder);
  }, [motifCardOrder]);

  const orderedMotifBreakdown = useMemo(() => {
    if (!motifBreakdown.length) return [];
    if (!motifCardOrder.length) return motifBreakdown;
    const motifMap = new Map(
      motifBreakdown.map((row) => [row.motif, row] as const),
    );
    return motifCardOrder
      .map((id) => motifMap.get(id))
      .filter((row): row is (typeof motifBreakdown)[number] => Boolean(row));
  }, [motifBreakdown, motifCardOrder]);

  const dashboardCardEntries: BaseCardEntry[] = useMemo(() => {
    return [
      {
        id: 'metrics-summary',
        label: 'Metrics summary',
        visible: true,
        render: (props) => (
          <MetricsSummaryCard
            positions={totals.positions}
            tactics={totals.tactics}
            metricsVersion={data?.metrics_version ?? 0}
            sourceSync={data?.source_sync}
            {...props}
          />
        ),
      },
      {
        id: 'job-progress',
        label: 'Job progress',
        visible: jobProgress.length > 0,
        render: (props) => (
          <JobProgressCard
            entries={jobProgress}
            status={jobStatus}
            {...props}
          />
        ),
      },
      {
        id: 'metrics-grid',
        label: 'Motif breakdown',
        visible: Boolean(data),
        render: (props) => (
          <MetricsGrid
            metricsData={orderedMotifBreakdown}
            droppableId={MOTIF_CARD_DROPPABLE_ID}
            dropIndicatorIndex={motifDropIndicatorIndex}
            {...props}
          />
        ),
      },
      {
        id: 'metrics-trends',
        label: 'Motif trends',
        visible: Boolean(data) && trendLatestRows.length > 0,
        render: (props) => (
          <MotifTrendsCard
            data={trendLatestRows}
            columns={metricsTrendsColumns}
            {...props}
          />
        ),
      },
      {
        id: 'time-trouble-correlation',
        label: 'Time-trouble correlation',
        visible: Boolean(data) && timeTroubleSortedRows.length > 0,
        render: (props) => (
          <TimeTroubleCorrelationCard
            data={timeTroubleSortedRows}
            columns={timeTroubleColumns}
            {...props}
          />
        ),
      },
      {
        id: 'practice-queue',
        label: 'Practice queue',
        visible: true,
        render: (props) => (
          <PracticeQueueCard
            data={practiceLoading ? null : practiceQueue}
            columns={practiceQueueColumns}
            includeFailedAttempt={includeFailedAttempt}
            loading={practiceLoading}
            onIncludeFailedAttemptChange={handleIncludeFailedAttemptChange}
            onRowClick={handleOpenGameDetail}
            rowTestId={(row, index) =>
              `practice-queue-row-${row.source ?? 'unknown'}-${index}`
            }
            {...props}
          />
        ),
      },
      {
        id: 'recent-games',
        label: 'Recent games',
        visible: Boolean(data),
        render: (props) =>
          data ? (
            <RecentGamesCard
              data={data.recent_games}
              columns={recentGamesColumns}
              onRowClick={handleOpenGameDetail}
              rowTestId={(row, index) =>
                `recent-games-row-${row.source ?? 'unknown'}-${index}`
              }
              {...props}
            />
          ) : null,
      },
      {
        id: 'tactics-table',
        label: 'Recent tactics',
        visible: Boolean(data),
        render: (props) =>
          data ? (
            <RecentTacticsCard
              data={data.tactics}
              columns={tacticsColumns}
              onRowClick={handleOpenGameDetail}
              rowTestId={(row) =>
                row.game_id
                  ? `dashboard-game-row-${row.game_id}`
                  : 'dashboard-game-row-unknown'
              }
              {...props}
            />
          ) : null,
      },
      {
        id: 'positions-list',
        label: 'Latest positions',
        visible: Boolean(data),
        render: (props) =>
          data ? (
            <PositionsList
              positionsData={data.positions}
              onPositionClick={handleOpenChessboardModal}
              rowTestId={(row) => `positions-row-${row.position_id}`}
              {...props}
            />
          ) : null,
      },
      {
        id: 'practice-attempt',
        label: 'Practice attempt',
        visible: true,
        render: (props) => (
          <PracticeAttemptCard
            currentPractice={currentPractice ?? null}
            practiceSession={practiceSession}
            practiceLoading={practiceLoading}
            practiceModalOpen={practiceModalOpen}
            onStartPractice={handleOpenPracticeModal}
            {...props}
          />
        ),
      },
    ];
  }, [
    currentPractice,
    data,
    handleIncludeFailedAttemptChange,
    handleOpenChessboardModal,
    handleOpenGameDetail,
    includeFailedAttempt,
    jobProgress,
    jobStatus,
    metricsTrendsColumns,
    motifDropIndicatorIndex,
    orderedMotifBreakdown,
    practiceLoading,
    practiceModalOpen,
    practiceQueue,
    practiceQueueColumns,
    practiceSession,
    handleOpenPracticeModal,
    recentGamesColumns,
    resolveGameSource,
    tacticsColumns,
    timeTroubleColumns,
    timeTroubleSortedRows,
    totals.positions,
    totals.tactics,
    trendLatestRows,
  ]);

  const dashboardCardIds = useMemo(
    () => dashboardCardEntries.map((entry) => entry.id),
    [dashboardCardEntries],
  );

  useEffect(() => {
    const normalized = normalizeOrder(dashboardCardOrder, dashboardCardIds);
    if (!areArraysEqual(normalized, dashboardCardOrder)) {
      setDashboardCardOrder(normalized);
    }
  }, [dashboardCardIds, dashboardCardOrder]);

  const orderedDashboardCards = useMemo(() => {
    const cardMap = new Map(
      dashboardCardEntries.map((entry) => [entry.id, entry]),
    );
    const visibleIds = dashboardCardEntries
      .filter((entry) => entry.visible)
      .map((entry) => entry.id);
    const orderedVisible = dashboardCardOrder.filter((id) =>
      visibleIds.includes(id),
    );
    return orderedVisible
      .map((id) => cardMap.get(id))
      .filter((entry): entry is BaseCardEntry => Boolean(entry));
  }, [dashboardCardEntries, dashboardCardOrder]);

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
        backfillStartDate={backfillStartDate}
        backfillEndDate={backfillEndDate}
        onBackfillStartChange={handleBackfillStartChange}
        onBackfillEndChange={handleBackfillEndChange}
      />

      <div className="card p-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-display text-sand">Practice</h2>
          <p
            id={practiceStatusId}
            className="text-xs text-sand/60"
            role="status"
            aria-live="polite"
            data-testid="practice-button-status"
          >
            {practiceButtonState.helper}
          </p>
        </div>
        <ActionButton
          type="button"
          className="rounded-lg border border-white/10 px-4 py-3 text-sm text-sand hover:border-white/30 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={handleOpenPracticeModal}
          disabled={practiceButtonState.disabled}
          aria-describedby={practiceStatusId}
          data-testid="practice-button"
        >
          {practiceButtonState.label}
        </ActionButton>
      </div>

      {error ? <ErrorCard message={error} /> : null}

      <DragDropContext
        onDragUpdate={(result) => {
          if (result.destination?.droppableId === DASHBOARD_CARD_DROPPABLE_ID) {
            setDropIndicatorIndex(result.destination?.index ?? null);
          } else {
            setDropIndicatorIndex(null);
          }
          if (result.destination?.droppableId === MOTIF_CARD_DROPPABLE_ID) {
            setMotifDropIndicatorIndex(result.destination?.index ?? null);
          } else {
            setMotifDropIndicatorIndex(null);
          }
        }}
        onDragEnd={(result) => {
          setDropIndicatorIndex(null);
          setMotifDropIndicatorIndex(null);
          if (!result.destination) return;
          if (
            result.destination.index === result.source.index &&
            result.destination.droppableId === result.source.droppableId
          ) {
            return;
          }

          if (result.destination.droppableId === DASHBOARD_CARD_DROPPABLE_ID) {
            const visibleIds = orderedDashboardCards.map((card) => card.id);
            if (!visibleIds.length) return;
            const visibleSet = new Set(visibleIds);
            const currentVisibleOrder = dashboardCardOrder.filter((id) =>
              visibleSet.has(id),
            );
            const reorderedVisible = reorderList(
              currentVisibleOrder,
              result.source.index,
              result.destination.index,
            );
            let nextVisibleIndex = 0;
            const nextOrder = dashboardCardOrder.map((id) =>
              visibleSet.has(id)
                ? (reorderedVisible[nextVisibleIndex++] ?? id)
                : id,
            );
            setDashboardCardOrder(nextOrder);
            return;
          }

          if (result.destination.droppableId === MOTIF_CARD_DROPPABLE_ID) {
            const visibleIds = orderedMotifBreakdown
              .map((row) => row.motif)
              .filter((motif): motif is string => Boolean(motif));
            if (!visibleIds.length || !motifCardOrder.length) return;
            const visibleSet = new Set(visibleIds);
            const currentVisibleOrder = motifCardOrder.filter((id) =>
              visibleSet.has(id),
            );
            const reorderedVisible = reorderList(
              currentVisibleOrder,
              result.source.index,
              result.destination.index,
            );
            let nextVisibleIndex = 0;
            const nextOrder = motifCardOrder.map((id) =>
              visibleSet.has(id)
                ? (reorderedVisible[nextVisibleIndex++] ?? id)
                : id,
            );
            setMotifCardOrder(nextOrder);
          }
        }}
      >
        <Droppable droppableId={DASHBOARD_CARD_DROPPABLE_ID}>
          {(dropProvided) => (
            <div
              ref={dropProvided.innerRef}
              {...dropProvided.droppableProps}
              className="space-y-3"
            >
              {orderedDashboardCards.map((card, index) => {
                const dragLabel = `Reorder ${card.label}`;
                return (
                  <div key={card.id}>
                    {dropIndicatorIndex === index ? (
                      <div
                        className="h-0.5 rounded-full bg-teal/60"
                        data-testid="card-drop-indicator"
                      />
                    ) : null}
                    <Draggable
                      draggableId={card.id}
                      index={index}
                      isDragDisabled={false}
                      disableInteractiveElementBlocking
                    >
                      {(dragProvided, dragSnapshot) => (
                        <div
                          ref={dragProvided.innerRef}
                          {...dragProvided.draggableProps}
                          style={dragProvided.draggableProps.style}
                          data-card-id={card.id}
                          data-testid={`dashboard-card-${card.id}`}
                          className={
                            dragSnapshot.isDragging
                              ? 'rounded-xl ring-2 ring-teal/40 shadow-lg'
                              : undefined
                          }
                        >
                          {(() => {
                            const renderProps: BaseCardRenderProps = {
                              dragHandleLabel: dragLabel,
                            };
                            if (dragProvided.dragHandleProps) {
                              renderProps.dragHandleProps =
                                dragProvided.dragHandleProps as BaseCardDragHandleProps;
                            }
                            return card.render(renderProps);
                          })()}
                        </div>
                      )}
                    </Draggable>
                  </div>
                );
              })}
              {dropIndicatorIndex === orderedDashboardCards.length ? (
                <div
                  className="h-0.5 rounded-full bg-teal/60"
                  data-testid="card-drop-indicator"
                />
              ) : null}
              {dropProvided.placeholder}
            </div>
          )}
        </Droppable>
      </DragDropContext>
      {practiceError ? <ErrorCard message={practiceError} /> : null}
      <FiltersCard
        source={source}
        loading={loading}
        lichessProfile={lichessProfile}
        chesscomProfile={chesscomProfile}
        filters={filters}
        motifOptions={motifOptions}
        timeControlOptions={timeControlOptions}
        ratingOptions={ratingOptions}
        onSourceChange={handleSourceChange}
        onLichessProfileChange={handleLichessProfileChange}
        onChesscomProfileChange={handleChesscomProfileChange}
        onFiltersChange={handleFiltersChange}
        onResetFilters={handleResetFilters}
        modalOpen={filtersModalOpen}
        onModalOpenChange={setFiltersModalOpen}
        showOpenButton={false}
        showCard={false}
      />
      <DatabaseModal
        open={databaseModalOpen}
        onClose={() => setDatabaseModalOpen(false)}
        status={postgresStatus}
        statusLoading={postgresLoading}
        statusError={postgresError}
        rawPgns={postgresRawPgns}
        rawPgnsLoading={postgresRawPgnsLoading}
        rawPgnsError={postgresRawPgnsError}
        analysisRows={postgresAnalysis}
        analysisLoading={postgresAnalysisLoading}
        analysisError={postgresAnalysisError}
      />
      <FloatingActionButton label="Open settings" actions={floatingActions} />
      <ChessboardModal
        open={chessboardModalOpen}
        position={chessboardPosition}
        onClose={handleCloseChessboardModal}
      />
      <ChessboardModal
        open={practiceModalOpen}
        position={null}
        practice={
          practiceModalOpen
            ? {
                currentPractice,
                practiceSession,
                practiceFen,
                practiceMove,
                practiceMoveRef,
                practiceSubmitting,
                practiceFeedback,
                practiceSubmitError,
                practiceHighlightStyles,
                practiceOrientation,
                onPracticeMoveChange: handlePracticeMoveChange,
                handlePracticeAttempt,
                handlePracticeDrop,
              }
            : null
        }
        onClose={handleClosePracticeModal}
      />
      <GameDetailModal
        open={gameDetailOpen}
        onClose={() => setGameDetailOpen(false)}
        game={gameDetail}
        moves={gameDetailMoves}
        loading={gameDetailLoading}
        error={gameDetailError}
      />
    </div>
  );
}
