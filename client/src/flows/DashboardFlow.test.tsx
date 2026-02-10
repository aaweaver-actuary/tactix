import React from 'react';
import {
  render,
  screen,
  waitFor,
  fireEvent,
  within,
} from '@testing-library/react';
import { vi } from 'vitest';
import DashboardFlow from './DashboardFlow';
import buildLichessAnalysisUrl from '../utils/buildLichessAnalysisUrl';
import type {
  DashboardPayload,
  GameDetailResponse,
  PracticeQueueResponse,
} from '../api';

vi.mock('@hello-pangea/dnd', () => ({
  DragDropContext: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
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
        dragHandleProps: {},
        innerRef: () => {},
      },
      { isDragging: false },
    ),
}));

vi.mock('react-chessboard', () => ({
  Chessboard: () => <div data-testid="mock-chessboard" />,
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

const { fetchDashboard, fetchGameDetail } = await import('../client/dashboard');
const { fetchPracticeQueue, submitPracticeAttempt } =
  await import('../client/practice');
const { fetchPostgresStatus, fetchPostgresAnalysis, fetchPostgresRawPgns } =
  await import('../client/postgres');

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
      fen: '8/8/8/8/8/8/8/8 w - - 0 1',
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
      fen: '8/8/8/8/8/8/8/8 w - - 0 1',
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

const startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

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
      expect(screen.getAllByTestId(/practice-queue-row-/)).toHaveLength(2);
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

    const practiceRows = await screen.findAllByTestId(/practice-queue-row-/);
    expect(practiceRows).toHaveLength(1);
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
    const pending = new Promise<PracticeQueueResponse>(() => {});
    (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      pending,
    );

    render(<DashboardFlow />);

    expect(screen.getByText('Loading…')).toBeInTheDocument();
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
      within(modal).getByText(baseDashboard.positions[0].fen),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('chessboard-modal-close'));

    await waitFor(() => {
      expect(screen.queryByTestId('chessboard-modal')).not.toBeInTheDocument();
    });
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

    await waitFor(() => {
      expect(screen.getByText('0 of 5 attempts')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('practice-start'));

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

    const practiceRows = await screen.findAllByTestId(/practice-queue-row-/);
    expect(practiceRows).toHaveLength(2);
    practiceRows.forEach((row) => {
      expect(within(row).getByText('missed')).toBeInTheDocument();
      fireEvent.click(row);
    });

    await waitFor(() => {
      const lossCalls = (
        fetchGameDetail as unknown as ReturnType<typeof vi.fn>
      ).mock.calls.filter(([gameId]) => gameId === lossGameId);
      expect(lossCalls).toHaveLength(2);
    });
  });
});
