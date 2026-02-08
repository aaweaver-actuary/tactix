import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import DashboardFlow from './DashboardFlow';
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
const { fetchPracticeQueue } = await import('../client/practice');
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
      source: 'chesscom',
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
  pgn: '1. e4 e5 2. Nf3 Nc6 1-0',
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
});
