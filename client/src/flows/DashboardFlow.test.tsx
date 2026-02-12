import React from 'react';
import {
  render,
  screen,
  waitFor,
  fireEvent,
  within,
} from '@testing-library/react';
import { vi } from 'vitest';
import DashboardFlow, {
  ensureSourceSelected,
  resolveBackfillWindow,
} from './DashboardFlow';
import buildLichessAnalysisUrl from '../utils/buildLichessAnalysisUrl';
import * as buildPracticeMoveModule from '../utils/buildPracticeMove';
import type {
  DashboardPayload,
  GameDetailResponse,
  PracticeAttemptResponse,
  PracticeQueueResponse,
} from '../api';

type DragEventResult = {
  destination?: { droppableId?: string | null; index?: number | null } | null;
  source?: { droppableId?: string | null; index?: number | null } | null;
  draggableId?: string;
};

const TestButton = (props: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
  <button type="button" {...props} />
);

const dragContextHandlers: {
  onDragUpdate?: (result: DragEventResult) => void;
  onDragEnd?: (result: DragEventResult) => void;
} = {};

let dragIsDragging = false;
let dragHandlePropsValue: Record<string, unknown> | undefined = {};

let chessboardDropArgs: [string, string, string] = ['a2', 'a4', 'wP'];
let lastDropResult: boolean | undefined;

vi.mock('@hello-pangea/dnd', () => ({
  DragDropContext: ({ children, onDragUpdate, onDragEnd }: any) => {
    dragContextHandlers.onDragUpdate = onDragUpdate;
    dragContextHandlers.onDragEnd = onDragEnd;
    return <div>{children}</div>;
  },
  Droppable: ({ children, droppableId }: any) =>
    children({
      droppableProps: { 'data-droppable-id': droppableId },
      innerRef: () => {},
      placeholder: null,
    }),
  Draggable: ({ children, draggableId }: any) =>
    children(
      {
        draggableProps: { 'data-draggable-id': draggableId, style: {} },
        dragHandleProps: dragHandlePropsValue,
        innerRef: () => {},
      },
      { isDragging: dragIsDragging },
    ),
}));

vi.mock('react-chessboard', () => ({
  Chessboard: ({
    onPieceDrop,
  }: {
    onPieceDrop?: (...args: any[]) => boolean;
  }) => (
    <TestButton
      data-testid="mock-chessboard"
      onClick={() => {
        lastDropResult = onPieceDrop?.(...chessboardDropArgs);
      }}
    >
      Chessboard
    </TestButton>
  ),
}));

vi.mock('../client/dashboard', () => ({
  fetchDashboard: vi.fn(),
  fetchGameDetail: vi.fn(),
}));

vi.mock('../client/practice', () => ({
  fetchPracticeQueue: vi.fn(),
  submitPracticeAttempt: vi.fn(),
}));

vi.mock('../client/postgres', () => ({
  fetchPostgresStatus: vi.fn(),
  fetchPostgresAnalysis: vi.fn(),
  fetchPostgresRawPgns: vi.fn(),
}));

vi.mock('../client/streams', () => ({
  getJobStreamUrl: vi.fn(),
  getMetricsStreamUrl: vi.fn(),
  openEventStream: vi.fn(),
}));

const { fetchDashboard, fetchGameDetail } = await import('../client/dashboard');
const { fetchPracticeQueue, submitPracticeAttempt } =
  await import('../client/practice');
const { fetchPostgresStatus, fetchPostgresAnalysis, fetchPostgresRawPgns } =
  await import('../client/postgres');
const { getJobStreamUrl, getMetricsStreamUrl, openEventStream } =
  await import('../client/streams');

const baseDashboard: DashboardPayload = {
  source: 'chesscom',
  user: 'andy',
  metrics_version: 7,
  metrics: [
    {
      source: 'chesscom',
      metric_type: 'motif_breakdown',
      motif: 'hanging_piece',
      window_days: null,
      trend_date: null,
      rating_bucket: 'all',
      time_control: 'all',
      total: 2,
      found: 1,
      missed: 1,
      failed_attempt: 0,
      unclear: 0,
      found_rate: 0.5,
      miss_rate: 0.5,
      updated_at: '2026-02-01T00:00:00Z',
    },
    {
      source: 'chesscom',
      metric_type: 'trend',
      motif: 'hanging_piece',
      window_days: 7,
      trend_date: '2026-02-01T00:00:00Z',
      rating_bucket: 'all',
      time_control: 'all',
      total: 2,
      found: 1,
      missed: 1,
      failed_attempt: 0,
      unclear: 0,
      found_rate: 0.5,
      miss_rate: 0.5,
      updated_at: '2026-02-01T00:00:00Z',
    },
    {
      source: 'chesscom',
      metric_type: 'time_trouble_correlation',
      motif: 'all',
      window_days: null,
      trend_date: null,
      rating_bucket: 'all',
      time_control: 'blitz',
      total: 10,
      found: 0,
      missed: 0,
      failed_attempt: 0,
      unclear: 0,
      found_rate: 0.3,
      miss_rate: 0.2,
      updated_at: '2026-02-01T00:00:00Z',
    },
  ],
  recent_games: [
    {
      game_id: 'g1',
      source: 'chesscom',
      opponent: 'opponent-1',
      result: '1-0',
      played_at: '2026-01-01T00:00:00Z',
      time_control: '300+0',
      user_color: 'white',
    },
    {
      game_id: 'g2',
      source: 'lichess',
      opponent: 'opponent-2',
      result: '0-1',
      played_at: '2026-01-02T00:00:00Z',
      time_control: '300+0',
      user_color: 'black',
    },
  ],
  positions: [
    {
      position_id: 1,
      source: 'chesscom',
      game_id: 'g1',
      fen: '8/8/8/8/8/8/8/8 w - - 0 1',
      san: 'e4',
      uci: 'e2e4',
      move_number: 1,
      clock_seconds: 60,
      created_at: '2026-01-01T00:00:00Z',
    },
  ],
  tactics: [
    {
      tactic_id: 9,
      game_id: 'g1',
      position_id: 1,
      source: 'chesscom',
      motif: 'hanging_piece',
      result: 'missed',
      user_uci: 'e2e4',
      eval_delta: -1.2,
      severity: 3,
      created_at: '2026-01-01T00:00:00Z',
      best_uci: 'e2e4',
    },
  ],
};

const sourceSyncDashboard = {
  ...baseDashboard,
  source_sync: {
    window_days: 90,
    sources: [
      {
        source: 'lichess',
        games_played: 72,
        synced: true,
        latest_played_at: '2026-02-01T12:00:00Z',
      },
      {
        source: 'chesscom',
        games_played: 81,
        synced: true,
        latest_played_at: '2026-02-01T13:00:00Z',
      },
    ],
  },
};

const startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

const basePracticeQueue: PracticeQueueResponse = {
  source: 'chesscom',
  include_failed_attempt: false,
  items: [
    {
      tactic_id: 1,
      game_id: 'g1',
      position_id: 1,
      source: 'chesscom',
      motif: 'hanging_piece',
      result: 'missed',
      best_uci: 'e2e4',
      user_uci: 'e2e3',
      eval_delta: -1.1,
      severity: 2,
      created_at: '2026-01-01T00:00:00Z',
      fen: startingFen,
      position_uci: 'e2e4',
      san: 'e4',
      ply: 1,
      move_number: 1,
      side_to_move: 'w',
      clock_seconds: 60,
    },
    {
      tactic_id: 2,
      game_id: 'g2',
      position_id: 2,
      source: 'chesscom',
      motif: 'mate',
      result: 'missed',
      best_uci: 'g1f3',
      user_uci: 'g1h3',
      eval_delta: -0.7,
      severity: 1,
      created_at: '2026-01-02T00:00:00Z',
      fen: startingFen,
      position_uci: 'g1f3',
      san: 'Nf3',
      ply: 2,
      move_number: 2,
      side_to_move: 'w',
      clock_seconds: 58,
    },
  ],
};

const baseGameDetail: GameDetailResponse = {
  game_id: 'g1',
  source: 'chesscom',
  pgn: '1. e3 e6 2. f3 f6 1/2-1/2',
  metadata: {
    user_rating: 1400,
    time_control: '300',
    white_player: 'Alice',
    black_player: 'Bob',
    white_elo: 1400,
    black_elo: 1380,
    result: '1-0',
    event: 'Test',
    site: 'https://chess.com/game/123',
    utc_date: '2026.01.01',
    utc_time: '12:00:00',
    termination: 'Normal',
    start_timestamp_ms: 1761950400000,
  },
  analysis: [
    {
      tactic_id: 1,
      position_id: 2,
      game_id: 'g1',
      motif: 'hanging_piece',
      severity: 1.5,
      best_uci: 'g1f3',
      best_san: 'Nf3',
      explanation: 'Best line',
      eval_cp: 120,
      created_at: '2026-01-01T00:00:00Z',
      result: 'missed',
      user_uci: 'g1f3',
      eval_delta: -220,
      move_number: 2,
      ply: 3,
      san: 'Nf3',
      uci: 'g1f3',
      side_to_move: 'w',
      fen: 'test',
    },
  ],
};

const basePostgresStatus = {
  enabled: true,
  status: 'ok' as const,
  latency_ms: 12,
  error: null,
  schema: 'public',
  tables: ['games'],
  events: [],
};

const basePostgresAnalysis = {
  status: 'ok',
  tactics: [],
};

const basePostgresRawPgns = {
  status: 'ok',
  total_rows: 0,
  distinct_games: 0,
  latest_ingested_at: null,
  sources: [],
};

const buildPracticeQueue = (count: number): PracticeQueueResponse => ({
  source: 'chesscom',
  include_failed_attempt: false,
  items: Array.from({ length: count }, (_, index) => ({
    tactic_id: index + 1,
    game_id: `g${index + 1}`,
    position_id: index + 1,
    source: 'chesscom',
    motif: index % 2 === 0 ? 'hanging_piece' : 'mate',
    result: 'missed',
    best_uci: 'e2e4',
    user_uci: 'e2e3',
    eval_delta: -0.5,
    severity: 2,
    created_at: '2026-01-02T00:00:00Z',
    fen: startingFen,
    position_uci: 'e2e4',
    san: 'e4',
    ply: 1,
    move_number: 1,
    side_to_move: 'w',
    clock_seconds: 60,
  })),
});

const changeFilter = (testId: string, value: string) => {
  fireEvent.change(screen.getByTestId(testId), {
    target: { value },
  });
};

const openFiltersModal = async () => {
  const fabToggle = screen.getByTestId('fab-toggle');
  if (fabToggle.getAttribute('aria-expanded') !== 'true') {
    fireEvent.click(fabToggle);
  }
  fireEvent.click(screen.getByTestId('filters-open'));
  await waitFor(() => {
    expect(screen.getByTestId('filters-modal')).toBeInTheDocument();
  });
};

const openFabModal = async (actionTestId: string, modalTestId: string) => {
  const fabToggle = screen.getByTestId('fab-toggle');
  if (fabToggle.getAttribute('aria-expanded') !== 'true') {
    fireEvent.click(fabToggle);
  }
  fireEvent.click(screen.getByTestId(actionTestId));
  await waitFor(() => {
    expect(screen.getByTestId(modalTestId)).toBeInTheDocument();
  });
};

const openRecentGamesModal = async () =>
  openFabModal('recent-games-open', 'recent-games-modal');

const openRecentTacticsModal = async () =>
  openFabModal('recent-tactics-open', 'recent-tactics-modal');

const openPracticeModal = async () => {
  const practiceButton = await screen.findByTestId('practice-button');
  await waitFor(() => {
    expect(practiceButton).toBeEnabled();
  });
  fireEvent.click(practiceButton);
  await waitFor(() => {
    expect(screen.getByTestId('chessboard-modal')).toBeInTheDocument();
  });
};

const buildStreamReader = (chunks: string[]) => {
  const encoder = new TextEncoder();
  let index = 0;
  return {
    read: vi.fn(async () => {
      if (index >= chunks.length) {
        return { done: true, value: undefined } as const;
      }
      const value = encoder.encode(chunks[index]);
      index += 1;
      return { done: false, value } as const;
    }),
  } as ReadableStreamDefaultReader<Uint8Array>;
};

const setupBaseMocks = () => {
  (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
    baseDashboard,
  );
  (fetchGameDetail as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
    baseGameDetail,
  );
  (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
    basePracticeQueue,
  );
  (
    fetchPostgresStatus as unknown as ReturnType<typeof vi.fn>
  ).mockResolvedValue(basePostgresStatus);
  (
    fetchPostgresAnalysis as unknown as ReturnType<typeof vi.fn>
  ).mockResolvedValue(basePostgresAnalysis);
  (
    fetchPostgresRawPgns as unknown as ReturnType<typeof vi.fn>
  ).mockResolvedValue(basePostgresRawPgns);
  (getJobStreamUrl as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
    'https://example.com/job-stream',
  );
  (getMetricsStreamUrl as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
    'https://example.com/metrics-stream',
  );
  (openEventStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
    buildStreamReader([]),
  );
};

const waitForDashboardLoad = async () => {
  await waitFor(() => {
    expect(fetchDashboard).toHaveBeenCalled();
  });
};

describe('DashboardFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupBaseMocks();
    chessboardDropArgs = ['a2', 'a4', 'wP'];
    lastDropResult = undefined;
    dragIsDragging = false;
    dragHandlePropsValue = {};
    if (typeof globalThis.localStorage?.clear === 'function') {
      globalThis.localStorage.clear();
    }
  });

  it('renders dashboard rows and reflects filter changes', async () => {
    render(<DashboardFlow />);

    await waitForDashboardLoad();

    expect(
      screen.queryByTestId('dashboard-card-filters'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId('dashboard-card-recent-games'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId('dashboard-card-tactics-table'),
    ).not.toBeInTheDocument();

    await openRecentGamesModal();

    await waitFor(() => {
      expect(screen.getAllByTestId(/recent-games-row-/)).toHaveLength(2);
    });

    fireEvent.click(screen.getByTestId('recent-games-modal-close'));
    await waitFor(() => {
      expect(
        screen.queryByTestId('recent-games-modal'),
      ).not.toBeInTheDocument();
    });

    await openFiltersModal();

    const motifSelect = screen.getByTestId('filter-motif') as HTMLSelectElement;
    fireEvent.change(motifSelect, { target: { value: 'hanging_piece' } });
    expect(motifSelect.value).toBe('hanging_piece');
  });

  it('adds missing allowed motifs to the motif breakdown', async () => {
    render(<DashboardFlow />);

    await waitForDashboardLoad();

    const breakdown = screen.getByTestId('motif-breakdown');

    await waitFor(() => {
      expect(breakdown.querySelector('[data-motif-id="mate"]')).not.toBeNull();
    });
  });

  it('enables the practice button when queue items are available', async () => {
    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchPracticeQueue).toHaveBeenCalled();
    });

    const practiceButton = screen.getByTestId('practice-button');

    await waitFor(() => {
      expect(practiceButton).toBeEnabled();
    });

    expect(practiceButton).toHaveTextContent('Start practice');

    fireEvent.click(practiceButton);

    const modal = await screen.findByTestId('chessboard-modal');
    expect(modal).toBeInTheDocument();
  });

  it('disables the practice button when no queue items are available', async () => {
    (
      fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValue({
      source: 'chesscom',
      include_failed_attempt: false,
      items: [],
    });

    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchPracticeQueue).toHaveBeenCalled();
    });

    const practiceButton = screen.getByTestId('practice-button');

    await waitFor(() => {
      expect(practiceButton).toBeDisabled();
    });

    expect(practiceButton).toHaveTextContent('No practice items');
    expect(screen.getByTestId('practice-button-status')).toHaveTextContent(
      'Refresh metrics to find new tactics.',
    );
  });

  it('keeps the practice modal closed when no queue items are available', async () => {
    (
      fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValue({
      source: 'chesscom',
      include_failed_attempt: false,
      items: [],
    });

    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchPracticeQueue).toHaveBeenCalled();
    });

    const practiceButton = screen.getByTestId('practice-button');
    practiceButton.removeAttribute('disabled');
    fireEvent.click(practiceButton);

    expect(screen.queryByTestId('chessboard-modal')).not.toBeInTheDocument();
  });

  it('filters non-scoped motifs from metrics, tactics, and practice queue', async () => {
    const scopedDashboard: DashboardPayload = {
      ...baseDashboard,
      metrics: [
        { ...baseDashboard.metrics[0], motif: 'hanging_piece' },
        {
          ...baseDashboard.metrics[0],
          motif: 'pin',
          updated_at: '2026-02-02T00:00:00Z',
        },
        {
          ...baseDashboard.metrics[0],
          motif: 'initiative',
          updated_at: '2026-02-03T00:00:00Z',
        },
      ],
      tactics: [
        { ...baseDashboard.tactics[0], game_id: 'g-allowed' },
        { ...baseDashboard.tactics[0], game_id: 'g-pin', motif: 'pin' },
      ],
      recent_games: [],
      positions: [],
    };
    const scopedPracticeQueue: PracticeQueueResponse = {
      ...basePracticeQueue,
      items: [
        { ...basePracticeQueue.items[0], motif: 'hanging_piece' },
        {
          ...basePracticeQueue.items[0],
          tactic_id: 2,
          game_id: 'g-pin',
          position_id: 2,
          motif: 'pin',
        },
      ],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      scopedDashboard,
    );
    (
      fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValue(scopedPracticeQueue);

    render(<DashboardFlow />);

    await waitForDashboardLoad();
    await openFiltersModal();

    const motifSelect = screen.getByTestId('filter-motif') as HTMLSelectElement;
    const motifOptions = Array.from(motifSelect.options).map(
      (option) => option.value,
    );
    expect(motifOptions).toContain('hanging_piece');
    expect(motifOptions).not.toContain('pin');
    expect(motifOptions).not.toContain('initiative');

    await openRecentTacticsModal();

    expect(
      await screen.findByTestId('dashboard-game-row-g-allowed'),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId('dashboard-game-row-g-pin'),
    ).not.toBeInTheDocument();

    const practiceButton = screen.getByTestId('practice-button');
    const practiceStatus = screen.getByTestId('practice-button-status');

    await waitFor(() => {
      expect(practiceButton).toBeEnabled();
    });

    expect(practiceButton).toHaveTextContent('Start practice');
    expect(practiceStatus).toHaveTextContent('1 tactic ready.');
  });

  it('omits the practice queue card from the dashboard layout', async () => {
    render(<DashboardFlow />);

    await waitForDashboardLoad();

    expect(screen.queryByTestId('practice-queue-card')).not.toBeInTheDocument();
    expect(screen.getByTestId('practice-button')).toBeInTheDocument();
  });

  it('closes the filters modal on Escape', async () => {
    render(<DashboardFlow />);

    await waitForDashboardLoad();
    await openFiltersModal();

    fireEvent.keyDown(window, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByTestId('filters-modal')).not.toBeInTheDocument();
    });
  });

  it('shows per-site 90-day sync counts from backend metrics on initial load', async () => {
    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      sourceSyncDashboard,
    );

    render(<DashboardFlow />);

    await waitForDashboardLoad();

    const lichessCard = screen.getByTestId('source-sync-lichess');
    const chesscomCard = screen.getByTestId('source-sync-chesscom');

    expect(lichessCard).toBeVisible();
    expect(chesscomCard).toBeVisible();
    expect(within(lichessCard).getByText('Lichess (90d)')).toBeInTheDocument();
    expect(within(lichessCard).getByText('72')).toBeInTheDocument();
    expect(
      within(chesscomCard).getByText('Chess.com (90d)'),
    ).toBeInTheDocument();
    expect(within(chesscomCard).getByText('81')).toBeInTheDocument();
  });

  it('shows an error when the dashboard load fails', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('nope'),
    );

    render(<DashboardFlow />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load dashboard')).toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });

  it('shows practice loading state while queue fetch is pending', async () => {
    const pending = new Promise<PracticeAttemptResponse>(() => {});
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      pending,
    );

    render(<DashboardFlow />);

    expect(screen.getByTestId('practice-button')).toHaveTextContent(
      'Loading practice...',
    );
  });

  it('opens game detail as a modal overlay from recent games', async () => {
    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchDashboard).toHaveBeenCalled();
    });

    await openRecentGamesModal();

    await waitFor(() => {
      expect(screen.getAllByTestId(/recent-games-row-/)).toHaveLength(2);
    });

    fireEvent.click(screen.getAllByTestId(/recent-games-row-/)[0]);

    const modal = await screen.findByTestId('game-detail-modal');
    expect(modal).toHaveAttribute('aria-modal', 'true');
    expect(modal.className).toContain('fixed');
    expect(modal.className).toContain('inset-0');
    expect(modal.className).toContain('bg-black/60');
    expect(screen.getByTestId('game-detail-close')).toBeInTheDocument();
  });

  it('opens and closes the chessboard modal from latest positions', async () => {
    render(<DashboardFlow />);

    const positionRow = await screen.findByTestId('positions-row-1');
    fireEvent.click(positionRow);

    const modal = await screen.findByTestId('chessboard-modal');
    expect(modal).toHaveAttribute('aria-modal', 'true');
    expect(within(modal).getByTestId('mock-chessboard')).toBeInTheDocument();
    expect(
      within(modal).getAllByText(baseDashboard.positions[0].fen).length,
    ).toBeGreaterThan(0);

    fireEvent.click(screen.getByTestId('chessboard-modal-close'));

    await waitFor(() => {
      expect(screen.queryByTestId('chessboard-modal')).not.toBeInTheDocument();
    });
  });

  it('closes the practice modal when opening a position board', async () => {
    render(<DashboardFlow />);

    await openPracticeModal();

    const positionRow = await screen.findByTestId('positions-row-1');
    fireEvent.click(positionRow);

    await waitFor(() => {
      expect(screen.getByText('Position board')).toBeInTheDocument();
      expect(screen.queryByText('Daily practice')).not.toBeInTheDocument();
    });
  });

  it('closes the practice modal when opening the browser modal', async () => {
    render(<DashboardFlow />);

    await openPracticeModal();

    await openFabModal('browser-open', 'chessboard-modal');

    expect(screen.getByText('Position board')).toBeInTheDocument();
    expect(screen.queryByText('Daily practice')).not.toBeInTheDocument();
  });

  it('opens the Lichess analysis URL from the recent games table', async () => {
    const popup = {
      location: { href: '' },
      opener: 'active',
      close: vi.fn(),
    };
    const openSpy = vi
      .spyOn(window, 'open')
      .mockImplementation(() => popup as unknown as Window);

    render(<DashboardFlow />);

    await openRecentGamesModal();

    await waitFor(() => {
      expect(screen.getAllByTestId(/^open-lichess-/)).toHaveLength(2);
    });

    fireEvent.click(screen.getByTestId('open-lichess-g1'));

    await waitFor(() => {
      expect(fetchGameDetail).toHaveBeenCalledWith('g1', 'chesscom');
    });

    const expectedUrl = buildLichessAnalysisUrl(baseGameDetail.pgn);
    if (!expectedUrl) {
      throw new Error('Expected Lichess analysis URL to be generated.');
    }

    expect(openSpy).toHaveBeenCalledWith('about:blank', '_blank');
    expect(popup.location.href).toBe(expectedUrl);
    expect(popup.opener).toBeNull();

    openSpy.mockRestore();
  });

  it('opens the game detail modal from the recent games Go to Game button', async () => {
    render(<DashboardFlow />);

    await openRecentGamesModal();

    await waitFor(() => {
      expect(screen.getByTestId('go-to-game-g1')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('go-to-game-g1'));

    await waitFor(() => {
      expect(fetchGameDetail).toHaveBeenCalledWith('g1', 'chesscom');
    });

    expect(await screen.findByTestId('game-detail-modal')).toBeInTheDocument();
  });

  it('disables recent games Go to Game when the game id is missing', async () => {
    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...baseDashboard,
      recent_games: [
        baseDashboard.recent_games[0],
        { ...baseDashboard.recent_games[1], game_id: '' },
      ],
    });

    render(<DashboardFlow />);

    await openRecentGamesModal();

    await waitFor(() => {
      expect(screen.getByTestId('go-to-game-g1')).toBeEnabled();
      expect(screen.getByTestId('go-to-game-unknown')).toBeDisabled();
    });
  });

  it('opens the game detail modal from recent tactics actions', async () => {
    render(<DashboardFlow />);

    await openRecentTacticsModal();

    await waitFor(() => {
      expect(screen.getByTestId('tactics-go-to-game-g1')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('tactics-go-to-game-g1'));

    await waitFor(() => {
      expect(fetchGameDetail).toHaveBeenCalledWith('g1', 'chesscom');
    });

    expect(await screen.findByTestId('game-detail-modal')).toBeInTheDocument();
  });

  it('opens the Lichess analysis URL from the recent tactics table', async () => {
    const popup = {
      location: { href: '' },
      opener: 'active',
      close: vi.fn(),
    };
    const openSpy = vi
      .spyOn(window, 'open')
      .mockImplementation(() => popup as unknown as Window);

    render(<DashboardFlow />);

    await openRecentTacticsModal();

    await waitFor(() => {
      expect(screen.getByTestId('tactics-open-lichess-g1')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('tactics-open-lichess-g1'));

    await waitFor(() => {
      expect(fetchGameDetail).toHaveBeenCalledWith('g1', 'chesscom');
    });

    const expectedUrl = buildLichessAnalysisUrl(baseGameDetail.pgn);
    if (!expectedUrl) {
      throw new Error('Expected Lichess analysis URL to be generated.');
    }

    expect(openSpy).toHaveBeenCalledWith('about:blank', '_blank');
    expect(popup.location.href).toBe(expectedUrl);
    expect(popup.opener).toBeNull();

    openSpy.mockRestore();
  });

  it('disables tactics actions when the tactic row has no game id', async () => {
    const missingGameIdDashboard: DashboardPayload = {
      ...baseDashboard,
      tactics: [
        {
          ...baseDashboard.tactics[0],
          game_id: null,
          source: null,
        },
      ],
      recent_games: [],
      positions: [],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      missingGameIdDashboard,
    );

    render(<DashboardFlow />);

    await waitForDashboardLoad();

    await openRecentTacticsModal();

    expect(screen.getByTestId('tactics-go-to-game-unknown')).toBeDisabled();
    expect(screen.getByTestId('tactics-open-lichess-unknown')).toBeDisabled();
  });

  it('ignores open-lichess clicks when a game id is missing', async () => {
    const dashboard: DashboardPayload = {
      ...baseDashboard,
      recent_games: [
        {
          ...baseDashboard.recent_games[0],
          game_id: null,
          source: null,
        },
      ],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      dashboard,
    );

    render(<DashboardFlow />);

    await openRecentGamesModal();

    const openButton = screen.getByTestId('open-lichess-unknown');
    openButton.removeAttribute('disabled');
    fireEvent.click(openButton);

    expect(fetchGameDetail).not.toHaveBeenCalled();
  });

  it('keeps practice session total fixed after a successful attempt', async () => {
    const queue = buildPracticeQueue(5);
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(queue)
      .mockResolvedValueOnce(queue);
    (
      submitPracticeAttempt as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValue({
      attempt_id: 9,
      tactic_id: 1,
      position_id: 1,
      source: 'chesscom',
      attempted_uci: 'e2e4',
      best_uci: 'e2e4',
      correct: true,
      motif: 'hanging_piece',
      severity: 2,
      eval_delta: -0.5,
      message: 'Correct move!',
    });

    render(<DashboardFlow />);

    const practiceButton = await screen.findByTestId('practice-button');
    await waitFor(() => {
      expect(practiceButton).toBeEnabled();
    });

    fireEvent.click(practiceButton);

    const modal = await screen.findByTestId('chessboard-modal');
    const modalScope = within(modal);

    await waitFor(() => {
      expect(modalScope.getByText('0 of 5 attempts')).toBeInTheDocument();
    });

    fireEvent.change(
      modalScope.getByPlaceholderText('Enter your move (UCI e.g., e2e4)'),
      { target: { value: 'e2e4' } },
    );
    fireEvent.click(
      modalScope.getByRole('button', { name: /submit attempt/i }),
    );

    await waitFor(() => {
      expect(submitPracticeAttempt).toHaveBeenCalled();
      const summaries = screen.getAllByTestId('practice-session-summary');
      expect(
        summaries.some((node) =>
          (node.textContent || '').includes('1 of 5 attempts'),
        ),
      ).toBe(true);
      expect(screen.getAllByText('1 / 5 complete').length).toBeGreaterThan(0);
    });
  });

  it('shows practice error state when the queue load fails', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const practiceQueueMock = fetchPracticeQueue as unknown as ReturnType<
      typeof vi.fn
    >;
    practiceQueueMock.mockReset();
    practiceQueueMock.mockRejectedValue(new Error('nope'));

    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchPracticeQueue).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByTestId('practice-button')).toHaveTextContent(
        'Practice unavailable',
      );
    });
    expect(screen.getByTestId('practice-button-status')).toHaveTextContent(
      'Failed to load practice queue',
    );

    consoleSpy.mockRestore();
  });

  it('updates the practice button label when the modal is open', async () => {
    render(<DashboardFlow />);

    const practiceButton = await screen.findByTestId('practice-button');
    await waitFor(() => {
      expect(practiceButton).toBeEnabled();
    });

    fireEvent.click(practiceButton);

    expect(await screen.findByTestId('chessboard-modal')).toBeInTheDocument();
    expect(practiceButton).toHaveTextContent('Continue practice');
  });

  it('marks practice complete once the queue empties', async () => {
    const queue = buildPracticeQueue(1);
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(queue)
      .mockResolvedValueOnce({ ...queue, items: [] });
    (
      submitPracticeAttempt as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValue({
      attempt_id: 9,
      tactic_id: 1,
      position_id: 1,
      source: 'chesscom',
      attempted_uci: 'e2e4',
      best_uci: 'e2e4',
      correct: true,
      motif: 'hanging_piece',
      severity: 2,
      eval_delta: -0.5,
      message: 'Correct move!',
    });

    render(<DashboardFlow />);

    const practiceButton = await screen.findByTestId('practice-button');
    await waitFor(() => {
      expect(practiceButton).toBeEnabled();
    });

    fireEvent.click(practiceButton);

    const modal = await screen.findByTestId('chessboard-modal');
    const modalScope = within(modal);

    fireEvent.change(
      modalScope.getByPlaceholderText('Enter your move (UCI e.g., e2e4)'),
      { target: { value: 'e2e4' } },
    );
    fireEvent.click(
      modalScope.getByRole('button', { name: /submit attempt/i }),
    );

    await waitFor(() => {
      expect(practiceButton).toHaveTextContent('Practice complete');
    });
  });

  it('derives black orientation for practice positions', async () => {
    const queue: PracticeQueueResponse = {
      ...basePracticeQueue,
      items: [
        {
          ...basePracticeQueue.items[0],
          fen: '8/8/8/8/8/8/4K3/7k b - - 0 1',
        },
      ],
    };
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(queue)
      .mockResolvedValueOnce(queue);

    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchPracticeQueue).toHaveBeenCalled();
    });

    expect(screen.getByTestId('practice-button')).toBeInTheDocument();
  });

  it('opens the browser modal from the floating action button', async () => {
    render(<DashboardFlow />);

    await waitForDashboardLoad();

    await openFabModal('browser-open', 'chessboard-modal');

    const modal = screen.getByTestId('chessboard-modal');
    expect(modal).toBeInTheDocument();
    expect(
      within(modal).getAllByText(baseDashboard.positions[0].fen).length,
    ).toBeGreaterThan(0);
  });

  it('opens the database modal from the floating action button', async () => {
    render(<DashboardFlow />);

    await openFabModal('database-open', 'database-modal');

    expect(screen.getByTestId('database-modal')).toBeInTheDocument();
  });

  it('handles recent games with missing source and game id', async () => {
    const dashboard: DashboardPayload = {
      ...baseDashboard,
      recent_games: [
        {
          game_id: null,
          source: 'lichess',
          opponent: 'missing-id',
          result: '1-0',
          played_at: '2026-01-03T00:00:00Z',
          time_control: null,
          user_color: null,
        },
        {
          game_id: 'g-unknown',
          source: undefined,
          opponent: null,
          result: null,
          played_at: null,
          time_control: null,
          user_color: null,
        },
      ],
    };

    (
      fetchDashboard as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValueOnce(dashboard);
    (
      fetchGameDetail as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValueOnce(baseGameDetail);

    render(<DashboardFlow />);

    await openRecentGamesModal();

    fireEvent.click(screen.getByTestId('recent-games-row-unknown-1'));

    await waitFor(() => {
      expect(fetchGameDetail).toHaveBeenCalledWith('g-unknown', undefined);
    });

    const goToGame = screen.getByTestId('go-to-game-unknown');
    const openLichess = screen.getByTestId('open-lichess-unknown');
    fireEvent.click(goToGame);
    fireEvent.click(openLichess);

    expect(fetchGameDetail).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText('--').length).toBeGreaterThan(0);
  });

  it('surfaces game detail fetch failures', async () => {
    (fetchGameDetail as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('boom'),
    );

    render(<DashboardFlow />);

    await openRecentGamesModal();

    fireEvent.click(screen.getByTestId('go-to-game-g1'));

    await waitFor(() => {
      expect(
        screen.getByText('Failed to load game details.'),
      ).toBeInTheDocument();
    });
  });

  it('surfaces Postgres load errors in the database modal', async () => {
    (
      fetchPostgresStatus as unknown as ReturnType<typeof vi.fn>
    ).mockRejectedValueOnce(new Error('status failed'));
    (
      fetchPostgresAnalysis as unknown as ReturnType<typeof vi.fn>
    ).mockRejectedValueOnce(new Error('analysis failed'));
    (
      fetchPostgresRawPgns as unknown as ReturnType<typeof vi.fn>
    ).mockRejectedValueOnce(new Error('raw failed'));

    render(<DashboardFlow />);

    await openFabModal('database-open', 'database-modal');

    expect(
      screen.getByText('Failed to load Postgres status'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Failed to load Postgres analysis results'),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('Failed to load Postgres raw PGN summary').length,
    ).toBeGreaterThan(0);
  });

  it('formats recent games with draw and missing values', async () => {
    const dashboard: DashboardPayload = {
      ...baseDashboard,
      recent_games: [
        {
          game_id: 'g-draw',
          source: 'lichess',
          opponent: 'draw-opponent',
          result: '1/2-1/2',
          played_at: 'not-a-date',
          time_control: '300+0',
          user_color: 'white',
        },
        {
          game_id: 'g-missing',
          source: 'lichess',
          opponent: 'missing-opponent',
          result: null,
          played_at: null,
          time_control: '300+0',
          user_color: null,
        },
        {
          game_id: 'g-raw',
          source: 'lichess',
          opponent: 'raw-opponent',
          result: '1-0',
          played_at: '2026-01-03T00:00:00Z',
          time_control: '300+0',
          user_color: null,
        },
      ],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      dashboard,
    );

    render(<DashboardFlow />);

    await openRecentGamesModal();

    expect(screen.getByText('Draw')).toBeInTheDocument();
    expect(screen.getByText('1-0')).toBeInTheDocument();
    expect(screen.getAllByText('--').length).toBeGreaterThan(0);
    expect(screen.getByText('not-a-date')).toBeInTheDocument();
  });

  it('applies rating filters to dashboard reloads', async () => {
    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...baseDashboard,
      metrics: [
        {
          ...baseDashboard.metrics[0],
          rating_bucket: '1200-1399',
        },
      ],
    });

    render(<DashboardFlow />);

    await openFiltersModal();

    changeFilter('filter-rating', '1200-1399');

    await waitFor(() => {
      expect(fetchDashboard).toHaveBeenLastCalledWith('all', {
        motif: undefined,
        time_control: undefined,
        rating_bucket: '1200-1399',
        start_date: undefined,
        end_date: undefined,
      });
    });
  });

  it('keeps motif breakdown stable when all motifs are present', async () => {
    const dashboard: DashboardPayload = {
      ...baseDashboard,
      metrics: [
        { ...baseDashboard.metrics[0], motif: 'hanging_piece' },
        { ...baseDashboard.metrics[0], motif: 'mate' },
      ],
      recent_games: [],
      positions: [],
      tactics: [],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      dashboard,
    );

    render(<DashboardFlow />);

    await waitForDashboardLoad();

    const breakdown = screen.getByTestId('motif-breakdown');
    expect(breakdown.querySelectorAll('[data-motif-id]').length).toBe(2);
  });

  it('renders metrics trends with missing percentages', async () => {
    const dashboard: DashboardPayload = {
      ...baseDashboard,
      metrics: [
        {
          ...baseDashboard.metrics[0],
          metric_type: 'trend',
          motif: 'hanging_piece',
          window_days: 7,
          found_rate: null,
          trend_date: '2026-02-01T00:00:00Z',
        },
        {
          ...baseDashboard.metrics[0],
          metric_type: 'trend',
          motif: 'hanging_piece',
          window_days: 30,
          found_rate: 0.25,
          trend_date: '2026-02-02T00:00:00Z',
        },
      ],
      recent_games: [],
      positions: [],
      tactics: [],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      dashboard,
    );

    render(<DashboardFlow />);

    await waitForDashboardLoad();

    expect(screen.getByText('--')).toBeInTheDocument();
    expect(screen.getByText('25.0%')).toBeInTheDocument();
  });

  it('falls back to opening Lichess directly when popup is blocked', async () => {
    const openSpy = vi
      .spyOn(window, 'open')
      .mockReturnValueOnce(null)
      .mockReturnValueOnce({ location: { href: '' } } as unknown as Window);

    render(<DashboardFlow />);

    await openRecentGamesModal();

    fireEvent.click(screen.getByTestId('open-lichess-g1'));

    await waitFor(() => {
      expect(fetchGameDetail).toHaveBeenCalledWith('g1', 'chesscom');
    });

    const expectedUrl = buildLichessAnalysisUrl(baseGameDetail.pgn);
    if (!expectedUrl) {
      throw new Error('Expected Lichess analysis URL to be generated.');
    }

    expect(openSpy).toHaveBeenNthCalledWith(
      2,
      expectedUrl,
      '_blank',
      'noopener,noreferrer',
    );

    openSpy.mockRestore();
  });

  it('closes the popup when Lichess URLs cannot be built', async () => {
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const popup = { close: vi.fn() };
    const openSpy = vi
      .spyOn(window, 'open')
      .mockImplementation(() => popup as unknown as Window);

    (fetchGameDetail as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...baseGameDetail,
      pgn: 'invalid pgn',
    });

    render(<DashboardFlow />);

    await openRecentGamesModal();

    fireEvent.click(screen.getByTestId('open-lichess-g1'));

    await waitFor(() => {
      expect(popup.close).toHaveBeenCalled();
    });

    openSpy.mockRestore();
    consoleSpy.mockRestore();
  });

  it('formats time trouble correlation values and null rates', async () => {
    const dashboard: DashboardPayload = {
      ...baseDashboard,
      metrics: [
        {
          ...baseDashboard.metrics[0],
          metric_type: 'motif_breakdown',
          motif: 'mate',
        },
        {
          ...baseDashboard.metrics[0],
          metric_type: 'time_trouble_correlation',
          motif: 'all',
          time_control: 'rapid',
          found_rate: -0.25,
          miss_rate: null,
        },
        {
          ...baseDashboard.metrics[0],
          metric_type: 'time_trouble_correlation',
          motif: 'all',
          time_control: 'blitz',
          found_rate: null,
          miss_rate: 0.1,
        },
      ],
      recent_games: [],
      positions: [],
      tactics: [],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      dashboard,
    );

    render(<DashboardFlow />);

    await waitForDashboardLoad();

    expect(screen.getByText('-0.25')).toBeInTheDocument();
    expect(screen.getAllByText('--').length).toBeGreaterThan(0);
  });

  it('reports backfill errors when the date range is invalid', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(<DashboardFlow />);

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-backfill')).toBeEnabled();
    });

    await waitFor(() => {
      expect(screen.getByTestId('action-backfill')).toBeEnabled();
    });

    fireEvent.change(screen.getByTestId('backfill-start'), {
      target: { value: '2026-02-12' },
    });
    fireEvent.change(screen.getByTestId('backfill-end'), {
      target: { value: '2026-02-01' },
    });

    fireEvent.click(screen.getByTestId('action-backfill'));

    await waitFor(() => {
      expect(screen.getByText('Backfill run failed')).toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });

  it('returns false and sets errors when no source is selected', () => {
    const setError = vi.fn();

    expect(
      ensureSourceSelected('all', setError, 'Select a specific site.'),
    ).toBe(false);
    expect(setError).toHaveBeenCalledWith('Select a specific site.');
  });

  it('throws on invalid backfill date strings', () => {
    expect(() =>
      resolveBackfillWindow('not-a-date', '2026-02-01', Date.now()),
    ).toThrow('Invalid backfill date range');
  });

  it('streams job events and renders progress updates', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const stream = buildStreamReader([
      'event: progress\n' + 'data: not-json\n\n',
      'event: progress\n' +
        'data: {"step":"sync","timestamp":1,"fetched_games":3}\n\n',
      'event: metrics_update\n' +
        'data: {"metrics_version":8,"metrics":[]}\n\n',
      'event: complete\n' + 'data: {"step":"done"}\n\n',
    ]);
    (openEventStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      stream,
    );

    render(<DashboardFlow />);

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-backfill')).toBeEnabled();
    });

    await waitFor(() => {
      expect(screen.getByTestId('action-run')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('action-run'));

    await waitFor(() => {
      expect(getJobStreamUrl).toHaveBeenCalled();
      expect(screen.getByText('Job progress')).toBeInTheDocument();
      expect(screen.getByText('sync')).toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });

  it('surfaces metrics stream errors', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const stream = buildStreamReader([
      'event: error\n' + 'data: {"message":"boom"}\n\n',
    ]);
    (openEventStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      stream,
    );

    render(<DashboardFlow />);

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-run')).toBeEnabled();
    });

    await waitFor(() => {
      expect(screen.getByTestId('action-refresh')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('action-refresh'));

    await waitFor(() => {
      expect(getMetricsStreamUrl).toHaveBeenCalled();
      expect(
        screen.getByText('Metrics stream disconnected'),
      ).toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });

  it('renders the chess.com bullet canonical scenario with filtered games and missed tactics', async () => {
    const lossGameId = 'chesscom-loss-2026-02-01';
    const winGameId = 'chesscom-win-2026-02-01';
    const canonicalDashboard: DashboardPayload = {
      source: 'chesscom',
      user: 'andy',
      metrics_version: 7,
      metrics: [
        {
          source: 'chesscom',
          metric_type: 'motif_breakdown',
          motif: 'hanging_piece',
          window_days: null,
          trend_date: null,
          rating_bucket: 'all',
          time_control: 'bullet',
          total: 2,
          found: 0,
          missed: 2,
          failed_attempt: 0,
          unclear: 0,
          found_rate: 0,
          miss_rate: 1,
          updated_at: '2026-02-01T00:00:00Z',
        },
      ],
      recent_games: [
        {
          game_id: winGameId,
          source: 'chesscom',
          opponent: 'opponent-win',
          result: '1-0',
          played_at: '2026-02-01T12:00:00Z',
          time_control: '60+0',
          user_color: 'white',
        },
        {
          game_id: lossGameId,
          source: 'chesscom',
          opponent: 'opponent-loss',
          result: '0-1',
          played_at: '2026-02-01T13:00:00Z',
          time_control: '60+0',
          user_color: 'white',
        },
      ],
      positions: [],
      tactics: [],
    };
    const canonicalPracticeQueue: PracticeQueueResponse = {
      source: 'chesscom',
      include_failed_attempt: false,
      items: [
        {
          tactic_id: 11,
          game_id: lossGameId,
          position_id: 101,
          source: 'chesscom',
          motif: 'hanging_piece',
          result: 'missed',
          best_uci: 'g1f3',
          user_uci: 'g1h3',
          eval_delta: -1.6,
          severity: 3,
          created_at: '2026-02-01T12:30:00Z',
          fen: startingFen,
          position_uci: 'g1f3',
          san: 'Nf3',
          ply: 12,
          move_number: 6,
          side_to_move: 'w',
          clock_seconds: 18,
        },
        {
          tactic_id: 12,
          game_id: lossGameId,
          position_id: 102,
          source: 'chesscom',
          motif: 'hanging_piece',
          result: 'missed',
          best_uci: 'c4d5',
          user_uci: 'c4b5',
          eval_delta: -1.2,
          severity: 2,
          created_at: '2026-02-01T12:45:00Z',
          fen: startingFen,
          position_uci: 'c4d5',
          san: 'Bxd5',
          ply: 16,
          move_number: 8,
          side_to_move: 'w',
          clock_seconds: 12,
        },
      ],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      canonicalDashboard,
    );
    (
      fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValue(canonicalPracticeQueue);

    render(<DashboardFlow />);

    await waitForDashboardLoad();

    await openFiltersModal();

    changeFilter('filter-source', 'chesscom');
    changeFilter('filter-time-control', 'bullet');
    changeFilter('filter-start-date', '2026-02-01');
    changeFilter('filter-end-date', '2026-02-01');

    await waitFor(() => {
      expect(fetchDashboard).toHaveBeenLastCalledWith('chesscom', {
        motif: undefined,
        time_control: 'bullet',
        rating_bucket: undefined,
        start_date: '2026-02-01',
        end_date: '2026-02-01',
      });
    });

    await openRecentGamesModal();

    const gameRows = await screen.findAllByTestId(/recent-games-row-/);
    expect(gameRows).toHaveLength(2);
    expect(within(gameRows[0]).getByText('Win')).toBeInTheDocument();
    expect(within(gameRows[1]).getByText('Loss')).toBeInTheDocument();

    const practiceButton = screen.getByTestId('practice-button');

    await waitFor(() => {
      expect(practiceButton).toBeEnabled();
    });

    fireEvent.click(practiceButton);

    const practiceModal = await screen.findByTestId('chessboard-modal');
    expect(practiceModal).toBeInTheDocument();
    expect(
      within(practiceModal).getByText(canonicalPracticeQueue.items[0].fen),
    ).toBeInTheDocument();
  });

  it('resets filters back to defaults', async () => {
    render(<DashboardFlow />);

    await waitForDashboardLoad();
    await openFiltersModal();

    changeFilter('filter-motif', 'hanging_piece');
    changeFilter('filter-time-control', 'blitz');
    changeFilter('filter-rating', '1200-1399');
    changeFilter('filter-start-date', '2026-02-01');
    changeFilter('filter-end-date', '2026-02-02');

    await waitFor(() => {
      expect(screen.getByTestId('filter-motif')).not.toBeDisabled();
    });

    const filtersModal = screen.getByTestId('filters-modal');
    fireEvent.click(
      within(filtersModal).getByRole('button', { name: /reset filters/i }),
    );

    await waitFor(() => {
      expect(
        (screen.getByTestId('filter-motif') as HTMLSelectElement).value,
      ).toBe('all');
      expect(
        (screen.getByTestId('filter-time-control') as HTMLSelectElement).value,
      ).toBe('all');
      expect(
        (screen.getByTestId('filter-rating') as HTMLSelectElement).value,
      ).toBe('all');
      expect(
        (screen.getByTestId('filter-start-date') as HTMLInputElement).value,
      ).toBe('');
      expect(
        (screen.getByTestId('filter-end-date') as HTMLInputElement).value,
      ).toBe('');
    });
  });

  it('updates profile selectors from the filters modal', async () => {
    render(<DashboardFlow />);

    await openFiltersModal();

    changeFilter('filter-source', 'lichess');

    const lichessSelect = screen.getByTestId(
      'filter-lichess-profile',
    ) as HTMLSelectElement;
    fireEvent.change(lichessSelect, { target: { value: 'blitz' } });
    expect(lichessSelect.value).toBe('blitz');

    changeFilter('filter-source', 'chesscom');

    const chesscomSelect = screen.getByTestId(
      'filter-chesscom-profile',
    ) as HTMLSelectElement;
    fireEvent.change(chesscomSelect, { target: { value: 'rapid' } });
    expect(chesscomSelect.value).toBe('rapid');
  });

  it('uses undefined source when rows omit source and the filter is all', async () => {
    const dashboard: DashboardPayload = {
      ...baseDashboard,
      recent_games: [
        {
          ...baseDashboard.recent_games[0],
          source: null,
        },
      ],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      dashboard,
    );

    render(<DashboardFlow />);

    await openRecentGamesModal();

    fireEvent.click(screen.getByTestId('go-to-game-g1'));

    await waitFor(() => {
      expect(fetchGameDetail).toHaveBeenCalledWith('g1', undefined);
    });
  });

  it('shows a game detail error when the row is missing a game id', async () => {
    const dashboard: DashboardPayload = {
      ...baseDashboard,
      recent_games: [
        {
          ...baseDashboard.recent_games[0],
          game_id: null,
          source: null,
        },
      ],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      dashboard,
    );

    render(<DashboardFlow />);

    await openRecentGamesModal();

    fireEvent.click(screen.getByTestId('recent-games-row-unknown-0'));

    await waitFor(() => {
      expect(
        screen.getByText('Selected game is missing a game id.'),
      ).toBeInTheDocument();
    });
  });

  it('closes the popup and logs when Lichess fetch fails', async () => {
    const popup = { close: vi.fn() };
    const openSpy = vi
      .spyOn(window, 'open')
      .mockImplementation(() => popup as unknown as Window);
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    (fetchGameDetail as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('boom'),
    );

    render(<DashboardFlow />);

    await openRecentGamesModal();

    fireEvent.click(screen.getByTestId('open-lichess-g1'));

    await waitFor(() => {
      expect(popup.close).toHaveBeenCalled();
    });

    openSpy.mockRestore();
    consoleSpy.mockRestore();
  });

  it('runs backfill with empty date inputs', async () => {
    const stream = buildStreamReader([
      'event: complete\n' + 'data: {"step":"done"}\n\n',
    ]);
    (openEventStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      stream,
    );

    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(1761950400000);

    render(<DashboardFlow />);

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-refresh')).toBeEnabled();
    });

    fireEvent.change(screen.getByTestId('backfill-start'), {
      target: { value: '' },
    });
    fireEvent.change(screen.getByTestId('backfill-end'), {
      target: { value: '' },
    });

    fireEvent.click(screen.getByTestId('action-backfill'));

    await waitFor(() => {
      expect(getJobStreamUrl).toHaveBeenCalled();
    });

    const call = (getJobStreamUrl as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0];
    expect(call[0]).toBe('daily_game_sync');
    expect(call[1]).toBe('chesscom');
    expect(call[3]).toEqual(expect.any(Number));
    expect(call[4]).toEqual(expect.any(Number));

    nowSpy.mockRestore();
  });

  it('uses the chesscom profile for backfill jobs', async () => {
    render(<DashboardFlow />);

    await waitForDashboardLoad();
    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-backfill')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('action-backfill'));

    await waitFor(() => {
      expect(getJobStreamUrl).toHaveBeenCalledWith(
        'daily_game_sync',
        'chesscom',
        'blitz',
        expect.any(Number),
        expect.any(Number),
      );
    });
  });

  it('surfaces invalid backfill date ranges', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(<DashboardFlow />);

    await waitForDashboardLoad();
    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-backfill')).toBeEnabled();
    });

    fireEvent.change(screen.getByTestId('backfill-start'), {
      target: { value: '2026-02-05' },
    });
    fireEvent.change(screen.getByTestId('backfill-end'), {
      target: { value: '2026-02-01' },
    });

    fireEvent.click(screen.getByTestId('action-backfill'));

    await waitFor(() => {
      expect(screen.getByText('Backfill run failed')).toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });

  it('reloads practice queue when include failed attempts toggles', async () => {
    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchPracticeQueue).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByTestId('practice-include-failed'));

    await waitFor(() => {
      expect(fetchPracticeQueue).toHaveBeenLastCalledWith('all', true);
    });
  });

  it('closes the practice modal when the queue empties on source change', async () => {
    const queue = buildPracticeQueue(1);
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(queue)
      .mockResolvedValueOnce({ ...queue, items: [] });

    render(<DashboardFlow />);

    await openPracticeModal();

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-run')).toBeEnabled();
    });

    await waitFor(() => {
      expect(screen.queryByTestId('chessboard-modal')).not.toBeInTheDocument();
    });
  });

  it('resets practice modal state when closed', async () => {
    render(<DashboardFlow />);

    await openPracticeModal();

    fireEvent.click(screen.getByTestId('chessboard-modal-close'));

    await waitFor(() => {
      expect(screen.queryByTestId('chessboard-modal')).not.toBeInTheDocument();
    });
  });

  it('shows practice move validation errors and handles enter submissions', async () => {
    (
      submitPracticeAttempt as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValue({
      attempt_id: 10,
      tactic_id: 1,
      position_id: 1,
      source: 'chesscom',
      attempted_uci: 'e2e4',
      best_uci: 'e2e4',
      correct: true,
      motif: 'hanging_piece',
      severity: 2,
      eval_delta: -0.3,
      message: 'Correct',
    });

    render(<DashboardFlow />);

    await openPracticeModal();

    fireEvent.click(screen.getByRole('button', { name: /submit attempt/i }));

    expect(
      screen.getByText('Enter a move in UCI notation (e.g., e2e4).'),
    ).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText('Enter your move (UCI e.g., e2e4)'),
      { target: { value: 'e2e5' } },
    );
    fireEvent.click(screen.getByRole('button', { name: /submit attempt/i }));

    expect(
      screen.getByText('Illegal move for this position. Try a legal UCI move.'),
    ).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText('Enter your move (UCI e.g., e2e4)'),
      { target: { value: 'e2e4' } },
    );
    fireEvent.keyDown(
      screen.getByPlaceholderText('Enter your move (UCI e.g., e2e4)'),
      { key: 'Enter' },
    );

    await waitFor(() => {
      expect(submitPracticeAttempt).toHaveBeenCalled();
    });
  });

  it('handles rescheduled practice attempts', async () => {
    const queue = buildPracticeQueue(1);
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(queue)
      .mockResolvedValueOnce(queue);
    (
      submitPracticeAttempt as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValue({
      attempt_id: 12,
      tactic_id: 1,
      position_id: 1,
      source: 'chesscom',
      attempted_uci: 'e2e4',
      best_uci: 'e2e4',
      correct: false,
      rescheduled: true,
      motif: 'hanging_piece',
      severity: 2,
      eval_delta: -0.5,
      message: 'Try again.',
    });

    render(<DashboardFlow />);

    await openPracticeModal();

    fireEvent.change(
      screen.getByPlaceholderText('Enter your move (UCI e.g., e2e4)'),
      { target: { value: 'e2e4' } },
    );
    await waitFor(() => {
      expect(screen.getByDisplayValue('e2e4')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /submit attempt/i }));

    await waitFor(() => {
      expect(screen.getByText('1 of 2 attempts')).toBeInTheDocument();
    });
  });

  it('submits promotion drops for practice', async () => {
    const dropQueue: PracticeQueueResponse = {
      ...basePracticeQueue,
      items: [
        {
          ...basePracticeQueue.items[0],
          fen: 'k7/4P3/8/8/8/8/8/7K w - - 0 1',
        },
      ],
    };
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(dropQueue)
      .mockResolvedValueOnce(dropQueue);
    (
      submitPracticeAttempt as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValueOnce({
      attempt_id: 1,
      tactic_id: 1,
      position_id: 1,
      source: 'chesscom',
      attempted_uci: 'e7e8q',
      best_uci: 'e7e8q',
      correct: true,
      rescheduled: false,
      motif: 'hanging_piece',
      severity: 1,
      eval_delta: 0,
      message: 'Nice.',
    });

    render(<DashboardFlow />);

    await openPracticeModal();

    await waitFor(() => {
      expect(
        screen.getByText('Legal moves only. Drag a piece to submit.'),
      ).toBeInTheDocument();
    });

    chessboardDropArgs = ['e7', 'e8', 'wP'];
    fireEvent.click(screen.getByTestId('mock-chessboard'));

    await waitFor(() => {
      expect(lastDropResult).toBe(false);
    });
    expect(submitPracticeAttempt).not.toHaveBeenCalled();
  });

  it('rejects illegal practice drops', async () => {
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(basePracticeQueue)
      .mockResolvedValueOnce(basePracticeQueue);

    render(<DashboardFlow />);

    await openPracticeModal();

    chessboardDropArgs = ['a2', 'a5', 'wP'];
    fireEvent.click(screen.getByTestId('mock-chessboard'));

    await waitFor(() => {
      expect(lastDropResult).toBe(false);
      expect(
        screen.getByText('Illegal move for this position.'),
      ).toBeInTheDocument();
    });
  });

  it('surfaces practice submit errors', async () => {
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(basePracticeQueue)
      .mockResolvedValueOnce(basePracticeQueue);
    const buildPracticeMoveSpy = vi
      .spyOn(buildPracticeMoveModule, 'default')
      .mockReturnValue({
        uci: 'e2e4',
        nextFen: startingFen,
        from: 'e2',
        to: 'e4',
      });
    (
      submitPracticeAttempt as unknown as ReturnType<typeof vi.fn>
    ).mockRejectedValueOnce(new Error('boom'));

    try {
      render(<DashboardFlow />);

      await openPracticeModal();

      await waitFor(() => {
        expect(
          screen.getByText('Legal moves only. Drag a piece to submit.'),
        ).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(
        'Enter your move (UCI e.g., e2e4)',
      );
      fireEvent.change(input, { target: { value: 'e2e4' } });
      fireEvent.keyDown(input, { key: 'Enter', code: 'Enter', charCode: 13 });

      await waitFor(() => {
        expect(submitPracticeAttempt).toHaveBeenCalled();
      });
    } finally {
      buildPracticeMoveSpy.mockRestore();
    }
  });

  it('submits practice drops and ignores drops while submitting', async () => {
    const dropQueue: PracticeQueueResponse = {
      ...basePracticeQueue,
      items: [
        {
          ...basePracticeQueue.items[0],
          fen: '8/P7/8/8/8/8/4P3/3K3k w - - 0 1',
        },
      ],
    };
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(dropQueue)
      .mockResolvedValueOnce(dropQueue);
    const pending = new Promise<PracticeAttemptResponse>(() => {});
    (
      submitPracticeAttempt as unknown as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce(pending);

    render(<DashboardFlow />);

    await openPracticeModal();

    await waitFor(() => {
      expect(
        screen.getByText('Legal moves only. Drag a piece to submit.'),
      ).toBeInTheDocument();
    });

    chessboardDropArgs = ['e2', 'e4', 'wP'];
    fireEvent.click(screen.getByTestId('mock-chessboard'));

    await waitFor(() => {
      expect(lastDropResult).toBe(true);
    });

    chessboardDropArgs = ['e2', 'e4', 'wP'];
    fireEvent.click(screen.getByTestId('mock-chessboard'));
    expect(lastDropResult).toBe(false);
  });

  it('updates drop indicators and reorders dashboard and motif cards', async () => {
    render(<DashboardFlow />);

    await waitForDashboardLoad();

    dragContextHandlers.onDragUpdate?.({
      destination: { droppableId: 'dashboard-main-cards', index: 0 },
    });

    await waitFor(() => {
      expect(screen.getByTestId('card-drop-indicator')).toBeInTheDocument();
    });

    dragContextHandlers.onDragUpdate?.({
      destination: { droppableId: 'dashboard-motif-cards', index: 0 },
    });

    await waitFor(() => {
      expect(screen.getByTestId('motif-drop-indicator')).toBeInTheDocument();
    });

    dragContextHandlers.onDragUpdate?.({ destination: null });

    await waitFor(() => {
      expect(
        screen.queryByTestId('card-drop-indicator'),
      ).not.toBeInTheDocument();
    });

    dragContextHandlers.onDragEnd?.({ destination: null });
    dragContextHandlers.onDragEnd?.({
      source: { droppableId: 'dashboard-main-cards', index: 0 },
      destination: { droppableId: 'dashboard-main-cards', index: 0 },
    });

    const cardsBefore = screen
      .getAllByTestId(/^dashboard-card-/)
      .map((card) => card.getAttribute('data-card-id'));

    dragContextHandlers.onDragEnd?.({
      source: { droppableId: 'dashboard-main-cards', index: 0 },
      destination: { droppableId: 'dashboard-main-cards', index: 1 },
    });

    await waitFor(() => {
      const cardsAfter = screen
        .getAllByTestId(/^dashboard-card-/)
        .map((card) => card.getAttribute('data-card-id'));
      expect(cardsAfter[1]).toBe(cardsBefore[0]);
    });

    const motifContainer = screen.getByTestId('motif-breakdown');
    const motifBefore = Array.from(
      motifContainer.querySelectorAll('[data-motif-id]'),
    ).map((node) => node.getAttribute('data-motif-id'));

    dragContextHandlers.onDragEnd?.({
      source: { droppableId: 'dashboard-motif-cards', index: 0 },
      destination: { droppableId: 'dashboard-motif-cards', index: 1 },
    });

    await waitFor(() => {
      const motifAfter = Array.from(
        motifContainer.querySelectorAll('[data-motif-id]'),
      ).map((node) => node.getAttribute('data-motif-id'));
      expect(motifAfter[1]).toBe(motifBefore[0]);
    });
  });

  it('handles job stream error events with refresh', async () => {
    const stream = buildStreamReader([
      'event: error\n' + 'data: {"message":"boom"}\n\n',
    ]);
    (openEventStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      stream,
    );

    render(<DashboardFlow />);

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-run')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('action-run'));

    await waitFor(() => {
      expect(
        screen.getByText('Pipeline stream disconnected'),
      ).toBeInTheDocument();
    });

    expect(fetchPostgresStatus).toHaveBeenCalledTimes(2);
    expect(fetchPostgresAnalysis).toHaveBeenCalledTimes(2);
  });

  it('handles metrics stream completion and parse errors', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const stream = buildStreamReader([
      'event: progress\n' + ': comment\n\n',
      'event: progress\n\n',
      'event: progress\n' + 'data: not-json\n\n',
      'event: progress\n' + 'data: {"step":"refresh"}\n\npartial',
      '\n\nevent: complete\n' + 'data: {"step":"done"}\n\n',
    ]);
    (openEventStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      stream,
    );

    render(<DashboardFlow />);

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-refresh')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('action-refresh'));

    await waitFor(() => {
      expect(getMetricsStreamUrl).toHaveBeenCalled();
    });

    consoleSpy.mockRestore();
  });

  it('runs migrations with stream updates', async () => {
    const stream = buildStreamReader([
      'event: progress\n' + 'data: {"step":"migrate"}\n\n',
      'event: complete\n' + 'data: {"step":"done"}\n\n',
    ]);
    (openEventStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      stream,
    );

    render(<DashboardFlow />);

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-migrate')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('action-migrate'));

    await waitFor(() => {
      expect(getJobStreamUrl).toHaveBeenCalledWith(
        'migrations',
        'chesscom',
        undefined,
        undefined,
        undefined,
      );
    });
  });

  it('silences stream errors after abort', async () => {
    let rejectRead: ((err: Error) => void) | null = null;
    (openEventStream as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      async (_url: string, signal: AbortSignal) => {
        return {
          read: vi.fn(
            () =>
              new Promise((_, reject) => {
                rejectRead = reject;
                if (signal.aborted) {
                  reject(new Error('aborted'));
                }
              }),
          ),
        } as ReadableStreamDefaultReader<Uint8Array>;
      },
    );

    render(<DashboardFlow />);

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-run')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('action-run'));

    await waitFor(() => {
      expect(openEventStream).toHaveBeenCalled();
    });

    changeFilter('filter-source', 'lichess');

    if (!rejectRead) {
      throw new Error('Expected stream read to be pending.');
    }
    rejectRead(new Error('boom'));

    await waitFor(() => {
      expect(screen.queryByText('Pipeline run failed')).not.toBeInTheDocument();
    });
  });

  it('renders trends, time trouble, and filter fallbacks', async () => {
    const metricBase = {
      source: 'chesscom',
      total: 10,
      found: 5,
      missed: 5,
      failed_attempt: 0,
      unclear: 0,
      found_rate: 0.5,
      miss_rate: 0.5,
      updated_at: '2026-02-01T00:00:00Z',
    };
    const dashboard: DashboardPayload = {
      ...baseDashboard,
      metrics: [
        {
          ...metricBase,
          metric_type: 'motif_breakdown',
          motif: 'hanging_piece',
          window_days: null,
          trend_date: null,
          rating_bucket: '1200-1399',
          time_control: 'blitz',
        },
        {
          ...metricBase,
          metric_type: 'motif_breakdown',
          motif: 'mate',
          window_days: null,
          trend_date: null,
          rating_bucket: '1600-1799',
          time_control: 'rapid',
        },
        {
          ...metricBase,
          metric_type: 'motif_breakdown',
          motif: 'hanging_piece',
          window_days: null,
          trend_date: null,
          rating_bucket: undefined,
          time_control: undefined,
        },
        {
          ...metricBase,
          metric_type: 'trend',
          motif: 'hanging_piece',
          window_days: 7,
          trend_date: '2026-02-01',
          rating_bucket: '1600-1799',
          time_control: 'blitz',
        },
        {
          ...metricBase,
          metric_type: 'trend',
          motif: 'hanging_piece',
          window_days: 30,
          trend_date: '2026-02-10',
          rating_bucket: '1600-1799',
          time_control: 'blitz',
        },
        {
          ...metricBase,
          metric_type: 'trend',
          motif: 'hanging_piece',
          window_days: 30,
          trend_date: '2026-01-10',
          rating_bucket: '1600-1799',
          time_control: 'blitz',
        },
        {
          ...metricBase,
          metric_type: 'trend',
          motif: 'mate',
          window_days: 14,
          trend_date: '2026-01-05',
          rating_bucket: '1200-1399',
          time_control: 'blitz',
        },
        {
          ...metricBase,
          metric_type: 'trend',
          motif: 'mate',
          window_days: 7,
          trend_date: null,
          rating_bucket: '1200-1399',
          time_control: 'blitz',
        },
        {
          ...metricBase,
          metric_type: 'time_trouble_correlation',
          motif: 'all',
          window_days: null,
          trend_date: null,
          rating_bucket: '1200-1399',
          time_control: 'blitz',
          found_rate: 0.2,
          miss_rate: 0.1,
          total: 3,
        },
        {
          ...metricBase,
          metric_type: 'time_trouble_correlation',
          motif: 'all',
          window_days: null,
          trend_date: null,
          rating_bucket: 'all',
          time_control: null,
          found_rate: 0.3,
          miss_rate: 0.2,
          total: 4,
        },
        {
          ...metricBase,
          metric_type: 'time_trouble_correlation',
          motif: 'all',
          window_days: null,
          trend_date: null,
          rating_bucket: 'all',
          time_control: 'blitz',
          found_rate: 0.4,
          miss_rate: 0.3,
          total: 5,
        },
      ],
      recent_games: [
        {
          game_id: 'g-missing',
          source: 'chesscom',
          opponent: null,
          result: null,
          played_at: null,
          time_control: null,
          user_color: null,
        },
      ],
      tactics: [
        {
          ...baseDashboard.tactics[0],
          result: null,
          user_uci: null,
          eval_delta: null,
        },
      ],
    };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(dashboard)
      .mockResolvedValue(dashboard);

    render(<DashboardFlow />);

    await waitForDashboardLoad();
    await openFiltersModal();

    const ratingSelect = screen.getByTestId(
      'filter-rating',
    ) as HTMLSelectElement;
    const timeSelect = screen.getByTestId(
      'filter-time-control',
    ) as HTMLSelectElement;
    expect(Array.from(ratingSelect.options).map((opt) => opt.value)).toContain(
      'unknown',
    );
    expect(Array.from(timeSelect.options).map((opt) => opt.value)).toContain(
      'unknown',
    );

    changeFilter('filter-rating', '1600-1799');

    await waitFor(() => {
      expect(fetchDashboard).toHaveBeenCalledTimes(2);
    });

    fireEvent.click(screen.getByTestId('filters-modal-close'));

    fireEvent.click(
      screen.getAllByRole('button', { name: /motif trends/i })[0],
    );
    expect(screen.getByText('Last update')).toBeInTheDocument();

    fireEvent.click(
      screen.getAllByRole('button', { name: /time-trouble correlation/i })[0],
    );
    expect(screen.getByText('unknown')).toBeInTheDocument();

    await openRecentTacticsModal();
    expect(screen.getAllByText('--').length).toBeGreaterThan(0);
    fireEvent.click(screen.getByTestId('recent-tactics-modal-close'));

    await openRecentGamesModal();
    expect(screen.getAllByText('--').length).toBeGreaterThan(0);
  });

  it('handles migration and refresh stream failures', async () => {
    (openEventStream as unknown as ReturnType<typeof vi.fn>)
      .mockRejectedValueOnce(new Error('migrations fail'))
      .mockRejectedValueOnce(new Error('refresh fail'));

    render(<DashboardFlow />);

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-migrate')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('action-migrate'));

    await waitFor(() => {
      expect(screen.getByText('Migration run failed')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('action-refresh'));

    await waitFor(() => {
      expect(screen.getByText('Metrics refresh failed')).toBeInTheDocument();
    });
  });

  it('closes database, recent tactics, and game detail modals', async () => {
    render(<DashboardFlow />);

    await openFabModal('database-open', 'database-modal');
    fireEvent.click(screen.getByTestId('database-modal-close'));
    await waitFor(() => {
      expect(screen.queryByTestId('database-modal')).not.toBeInTheDocument();
    });

    await openRecentTacticsModal();
    fireEvent.click(screen.getByTestId('recent-tactics-modal-close'));
    await waitFor(() => {
      expect(
        screen.queryByTestId('recent-tactics-modal'),
      ).not.toBeInTheDocument();
    });

    await openRecentGamesModal();
    fireEvent.click(screen.getByTestId('go-to-game-g1'));
    const modal = await screen.findByTestId('game-detail-modal');
    fireEvent.click(within(modal).getByTestId('game-detail-close'));
    await waitFor(() => {
      expect(screen.queryByTestId('game-detail-modal')).not.toBeInTheDocument();
    });
  });

  it('renders drag styling and end indicators', async () => {
    dragIsDragging = true;
    dragHandlePropsValue = undefined;

    render(<DashboardFlow />);

    await waitForDashboardLoad();

    const cards = screen.getAllByTestId(/^dashboard-card-/);
    expect(cards[0]?.className).toContain('ring-2');

    dragContextHandlers.onDragUpdate?.({
      destination: {
        droppableId: 'dashboard-main-cards',
        index: cards.length,
      },
    });

    await waitFor(() => {
      expect(screen.getByTestId('card-drop-indicator')).toBeInTheDocument();
    });

    dragIsDragging = false;
    dragHandlePropsValue = {};
  });

  it('skips motif reordering when no motif order is stored', async () => {
    const dashboard = { ...baseDashboard, metrics: [] } as DashboardPayload;
    (
      fetchDashboard as unknown as ReturnType<typeof vi.fn>
    ).mockResolvedValueOnce(dashboard);

    render(<DashboardFlow />);

    await waitForDashboardLoad();

    dragContextHandlers.onDragEnd?.({
      source: { droppableId: 'dashboard-motif-cards', index: 0 },
      destination: { droppableId: 'dashboard-motif-cards', index: 1 },
    });

    expect(screen.getByTestId('motif-breakdown')).toBeInTheDocument();
  });

  it('handles stream read failures as job errors', async () => {
    (openEventStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      read: vi.fn(async () => {
        throw new Error('stream failure');
      }),
    } as ReadableStreamDefaultReader<Uint8Array>);

    render(<DashboardFlow />);

    await openFiltersModal();
    changeFilter('filter-source', 'chesscom');

    await waitFor(() => {
      expect(screen.getByTestId('action-run')).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId('action-run'));

    await waitFor(() => {
      expect(screen.getByText('Pipeline run failed')).toBeInTheDocument();
    });
  });
});
