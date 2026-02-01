import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import fetchDashboard from './utils/fetchDashboard';
import fetchPracticeQueue from './utils/fetchPracticeQueue';
import fetchPostgresStatus from './utils/fetchPostgresStatus';
import fetchPostgresAnalysis from './utils/fetchPostgresAnalysis';
import fetchPostgresRawPgns from './utils/fetchPostgresRawPgns';
import fetchGameDetail from './utils/fetchGameDetail';
import triggerMetricsRefresh from './utils/triggerMetricsRefresh';
import submitPracticeAttempt from './utils/submitPracticeAttempt';
import getJobStreamUrl from './utils/getJobStreamUrl';
import { getAuthHeaders } from './utils/getAuthHeaders';

vi.mock('./utils/fetchDashboard', () => ({ default: vi.fn() }));
vi.mock('./utils/fetchPracticeQueue', () => ({ default: vi.fn() }));
vi.mock('./utils/fetchPostgresStatus', () => ({ default: vi.fn() }));
vi.mock('./utils/fetchPostgresAnalysis', () => ({ default: vi.fn() }));
vi.mock('./utils/fetchPostgresRawPgns', () => ({ default: vi.fn() }));
vi.mock('./utils/fetchGameDetail', () => ({ default: vi.fn() }));
vi.mock('./utils/triggerMetricsRefresh', () => ({ default: vi.fn() }));
vi.mock('./utils/submitPracticeAttempt', () => ({ default: vi.fn() }));
vi.mock('./utils/getJobStreamUrl', () => ({ default: vi.fn() }));
vi.mock('./utils/getAuthHeaders', () => ({ getAuthHeaders: vi.fn() }));

const dashboardPayload = {
  source: 'lichess',
  user: 'test-user',
  metrics: [],
  recent_games: [],
  positions: [],
  tactics: [],
  metrics_version: 1,
};

const postgresStatus = {
  enabled: false,
  status: 'disabled',
};

const postgresAnalysis = {
  status: 'ok',
  tactics: [],
};

const postgresRawPgns = {
  status: 'ok',
  total_rows: 0,
  distinct_games: 0,
  latest_ingested_at: null,
  sources: [],
};

const practiceQueue = {
  source: 'lichess',
  include_failed_attempt: false,
  items: [],
};

describe('App job stream', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.mocked(fetchDashboard).mockResolvedValue(dashboardPayload as any);
    vi.mocked(fetchPracticeQueue).mockResolvedValue(practiceQueue as any);
    vi.mocked(fetchPostgresStatus).mockResolvedValue(postgresStatus as any);
    vi.mocked(fetchPostgresAnalysis).mockResolvedValue(postgresAnalysis as any);
    vi.mocked(fetchPostgresRawPgns).mockResolvedValue(postgresRawPgns as any);
    vi.mocked(fetchGameDetail).mockResolvedValue({} as any);
    vi.mocked(triggerMetricsRefresh).mockResolvedValue(dashboardPayload as any);
    vi.mocked(submitPracticeAttempt).mockResolvedValue({} as any);
    vi.mocked(getJobStreamUrl).mockReturnValue(
      '/api/jobs/stream?job=daily_game_sync',
    );
    vi.mocked(getAuthHeaders).mockReturnValue({});

    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders progress entries from the job SSE stream', async () => {
    const encoder = new TextEncoder();
    const ssePayload = `event: progress\ndata: ${JSON.stringify({
      step: 'Fetch games',
      message: 'Streaming update',
      timestamp: 123,
    })}\n\n`;
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(ssePayload));
        controller.close();
      },
    });

    fetchMock.mockResolvedValue(new Response(stream, { status: 200 }));

    render(<App />);

    const lichessButton = screen.getByRole('button', {
      name: 'Lichess · Rapid',
    });
    await waitFor(() => expect(lichessButton).toBeEnabled());
    fireEvent.click(lichessButton);

    const runButton = screen.getByTestId('action-run');
    await waitFor(() => expect(runButton).toBeEnabled());

    fireEvent.click(runButton);

    expect(await screen.findByText('Job progress')).toBeInTheDocument();
    expect(await screen.findByText('Fetch games')).toBeInTheDocument();
    expect(await screen.findByText('Streaming update')).toBeInTheDocument();
    expect(await screen.findByText('Running')).toBeInTheDocument();

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/jobs/stream?job=daily_game_sync',
      expect.objectContaining({
        headers: {},
        signal: expect.any(AbortSignal),
      }),
    );
  });
});
