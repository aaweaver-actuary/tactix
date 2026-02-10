import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import { fetchDashboard, fetchGameDetail } from './client/dashboard';
import { fetchPracticeQueue, submitPracticeAttempt } from './client/practice';
import {
  fetchPostgresStatus,
  fetchPostgresAnalysis,
  fetchPostgresRawPgns,
} from './client/postgres';
import {
  getJobStreamUrl,
  getMetricsStreamUrl,
  getAuthHeaders,
} from './client/streams';

vi.mock('./client/dashboard', () => ({
  fetchDashboard: vi.fn(),
  fetchGameDetail: vi.fn(),
}));
vi.mock('./client/practice', () => ({
  fetchPracticeQueue: vi.fn(),
  submitPracticeAttempt: vi.fn(),
}));
vi.mock('./client/postgres', () => ({
  fetchPostgresStatus: vi.fn(),
  fetchPostgresAnalysis: vi.fn(),
  fetchPostgresRawPgns: vi.fn(),
}));
vi.mock('./client/streams', async () => {
  const actual =
    await vi.importActual<typeof import('./client/streams')>(
      './client/streams',
    );
  return {
    ...actual,
    getJobStreamUrl: vi.fn(),
    getMetricsStreamUrl: vi.fn(),
    getAuthHeaders: vi.fn(),
  };
});

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
    vi.mocked(submitPracticeAttempt).mockResolvedValue({} as any);
    vi.mocked(getJobStreamUrl).mockReturnValue(
      '/api/jobs/stream?job=daily_game_sync',
    );
    vi.mocked(getMetricsStreamUrl).mockReturnValue(
      '/api/metrics/stream?source=lichess',
    );
    vi.mocked(getAuthHeaders).mockReturnValue({});

    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  const openFiltersModal = async () => {
    const fabToggle = await screen.findByTestId('fab-toggle');
    if (fabToggle.getAttribute('aria-expanded') !== 'true') {
      fireEvent.click(fabToggle);
    }
    fireEvent.click(screen.getByTestId('filters-open'));
    await waitFor(() => {
      expect(screen.getByTestId('filters-modal')).toBeInTheDocument();
    });
  };

  const selectLichessRapid = async () => {
    await openFiltersModal();
    const sourceSelect = screen.getByTestId('filter-source');
    await waitFor(() => expect(sourceSelect).toBeEnabled());
    fireEvent.change(sourceSelect, { target: { value: 'lichess' } });
  };

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

    await selectLichessRapid();

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
        headers: {
          Authorization: 'Bearer local-dev-token',
        },
        signal: expect.any(AbortSignal),
      }),
    );
  });

  it('updates metrics version from the metrics SSE stream', async () => {
    const encoder = new TextEncoder();
    const metricsPayload = `event: metrics_update\ndata: ${JSON.stringify({
      step: 'metrics_update',
      metrics_version: 5,
      metrics: [],
      source: 'lichess',
    })}\n\n`;
    const completePayload = `event: complete\ndata: ${JSON.stringify({
      step: 'complete',
      message: 'Metrics refresh complete',
    })}\n\n`;
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(metricsPayload));
        controller.enqueue(encoder.encode(completePayload));
        controller.close();
      },
    });

    fetchMock.mockResolvedValue(new Response(stream, { status: 200 }));

    render(<App />);

    await selectLichessRapid();

    const refreshButton = screen.getByTestId('action-refresh');
    await waitFor(() => expect(refreshButton).toBeEnabled());
    fireEvent.click(refreshButton);

    expect(
      await screen.findByText(
        'Execution stamped via metrics version 5 · user test-user',
      ),
    ).toBeInTheDocument();

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/metrics/stream?source=lichess',
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer local-dev-token',
        },
        signal: expect.any(AbortSignal),
      }),
    );
  });
});
