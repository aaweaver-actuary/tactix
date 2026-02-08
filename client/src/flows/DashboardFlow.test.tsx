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
      motif: 'fork',
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
      motif: 'fork',
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
      motif: 'fork',
      result: 'missed',
      user_uci: 'e2e4',
      eval_delta: -1.2,
      severity: 3,
      created_at: '2026-01-01T00:00:00Z',
      best_uci: 'e2e4',
    },
  ],
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
      motif: 'fork',
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
      motif: 'pin',
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
      motif: 'fork',
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
    motif: index % 2 === 0 ? 'fork' : 'pin',
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

describe('DashboardFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupBaseMocks();
  });

  it('renders dashboard rows and reflects filter changes', async () => {
    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchDashboard).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getAllByTestId(/recent-games-row-/)).toHaveLength(2);
      expect(screen.getAllByTestId(/practice-queue-row-/)).toHaveLength(2);
    });

    const motifSelect = screen.getByTestId('filter-motif') as HTMLSelectElement;
    fireEvent.change(motifSelect, { target: { value: 'fork' } });
    expect(motifSelect.value).toBe('fork');
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

  it('opens game detail as an overlay modal from recent games', async () => {
    render(<DashboardFlow />);

    await waitFor(() => {
      expect(screen.getAllByTestId(/recent-games-row-/)).toHaveLength(2);
    });

    fireEvent.click(screen.getAllByTestId(/recent-games-row-/)[0]);

    const modal = await screen.findByTestId('game-detail-modal');
    expect(modal).toHaveAttribute('aria-modal', 'true');
    expect(modal.className).toContain('fixed');
    expect(screen.getByTestId('game-detail-close')).toBeInTheDocument();
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

    await waitFor(() => {
      expect(screen.getAllByTestId(/open-lichess-/)).toHaveLength(2);
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
      motif: 'fork',
      severity: 2,
      eval_delta: -0.5,
      message: 'Correct move!',
    });

    render(<DashboardFlow />);

    await waitFor(() => {
      expect(screen.getByText('0 of 5 attempts')).toBeInTheDocument();
    });

    const practiceHeader = screen
      .getAllByRole('button', { name: /practice attempt/i })
      .find((el) => el.getAttribute('aria-expanded') !== null);
    if (!practiceHeader) {
      throw new Error('Practice attempt header button not found.');
    }
    if (practiceHeader.getAttribute('aria-expanded') === 'false') {
      fireEvent.click(practiceHeader);
    }

    fireEvent.change(
      screen.getByPlaceholderText('Enter your move (UCI e.g., e2e4)'),
      { target: { value: 'e2e4' } },
    );
    fireEvent.click(screen.getByRole('button', { name: /submit attempt/i }));

    await waitFor(() => {
      expect(screen.getByText('1 of 5 attempts')).toBeInTheDocument();
      expect(screen.getByText('1 / 5 complete')).toBeInTheDocument();
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

    await waitFor(() => {
      expect(fetchDashboard).toHaveBeenCalled();
    });

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
