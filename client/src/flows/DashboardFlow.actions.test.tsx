import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, it, vi, expect, beforeEach } from 'vitest';

const TestButton = (props: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
  <button type="button" {...props} />
);

vi.mock('@hello-pangea/dnd', () => ({
  DragDropContext: ({ children }: any) => <div>{children}</div>,
  Droppable: ({ children }: any) =>
    children({
      droppableProps: {},
      innerRef: () => {},
      placeholder: null,
    }),
  Draggable: ({ children }: any) =>
    children(
      {
        draggableProps: { style: {} },
        dragHandleProps: {},
        innerRef: () => {},
      },
      { isDragging: false },
    ),
}));

vi.mock('react-chessboard', () => ({
  Chessboard: () => <div data-testid="mock-chessboard" />,
}));

vi.mock('../_components/Hero', () => ({
  default: ({
    onRun,
    onBackfill,
    onMigrate,
    onRefresh,
    onPractice,
    version,
    user,
  }: any) => (
    <div>
      <div data-testid="metrics-version">{`metrics version ${version} | user ${user}`}</div>
      <TestButton data-testid="action-practice" onClick={onPractice}>
        Practice
      </TestButton>
      <TestButton data-testid="action-run" onClick={onRun}>
        Run
      </TestButton>
      <TestButton data-testid="action-backfill" onClick={onBackfill}>
        Backfill
      </TestButton>
      <TestButton data-testid="action-migrate" onClick={onMigrate}>
        Migrate
      </TestButton>
      <TestButton data-testid="action-refresh" onClick={onRefresh}>
        Refresh
      </TestButton>
    </div>
  ),
}));

vi.mock('../_components/FiltersCard', () => ({
  default: ({ onSourceChange }: any) => (
    <TestButton
      data-testid="filters-set-chesscom"
      onClick={() => onSourceChange('chesscom')}
    >
      Set source
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

const { fetchDashboard } = await import('../client/dashboard');
const { fetchPracticeQueue } = await import('../client/practice');
const { fetchPostgresStatus, fetchPostgresAnalysis, fetchPostgresRawPgns } =
  await import('../client/postgres');
const { openEventStream } = await import('../client/streams');

const DashboardFlow = (await import('./DashboardFlow')).default;

const baseDashboard = {
  source: 'chesscom',
  user: 'andy',
  metrics_version: 7,
  metrics: [],
  recent_games: [],
  positions: [],
  tactics: [],
};

const buildReader = (chunks: string[]) => {
  const encoder = new TextEncoder();
  let index = 0;
  return {
    read: vi.fn(async () => {
      if (index >= chunks.length) {
        return {
          done: true,
          value: undefined,
        } as ReadableStreamReadResult<Uint8Array>;
      }
      const value = encoder.encode(chunks[index]);
      index += 1;
      return { done: false, value } as ReadableStreamReadResult<Uint8Array>;
    }),
  } as unknown as ReadableStreamDefaultReader<Uint8Array>;
};

const buildDeferredReader = () => {
  let resolveRead:
    | ((value: ReadableStreamReadResult<Uint8Array>) => void)
    | null = null;
  return {
    reader: {
      read: vi.fn(
        () =>
          new Promise<ReadableStreamReadResult<Uint8Array>>((resolve) => {
            resolveRead = resolve;
          }),
      ),
    } as ReadableStreamDefaultReader<Uint8Array>,
    resolve: (result: ReadableStreamReadResult<Uint8Array>) => {
      resolveRead?.(result);
    },
  };
};

beforeEach(() => {
  vi.clearAllMocks();
  (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
    baseDashboard,
  );
  (fetchPracticeQueue as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
    {
      source: 'chesscom',
      include_failed_attempt: false,
      items: [],
    },
  );
  (
    fetchPostgresStatus as unknown as ReturnType<typeof vi.fn>
  ).mockResolvedValue(null);
  (
    fetchPostgresAnalysis as unknown as ReturnType<typeof vi.fn>
  ).mockResolvedValue({ status: 'ok', tactics: [] });
  (
    fetchPostgresRawPgns as unknown as ReturnType<typeof vi.fn>
  ).mockResolvedValue(null);
  (openEventStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
    read: vi.fn(async () => ({ done: true, value: undefined })),
  });
});

describe('DashboardFlow action guards', () => {
  it('blocks pipeline actions when source is all', async () => {
    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchDashboard).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByTestId('action-run'));
    expect(
      screen.getByText('Select a specific site to run the pipeline.'),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('action-backfill'));
    expect(
      screen.getByText('Select a specific site to run a backfill.'),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('action-migrate'));
    expect(
      screen.getByText('Select a specific site to run migrations.'),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('action-refresh'));
    expect(
      screen.getByText('Select a specific site to refresh metrics.'),
    ).toBeInTheDocument();
  });

  it('applies metrics updates before initial load resolves', async () => {
    let resolveDashboard: ((value: any) => void) | null = null;
    const pending = new Promise((resolve) => {
      resolveDashboard = resolve as (value: any) => void;
    });

    const metricsUpdate = { ...baseDashboard, metrics_version: 9 };

    (fetchDashboard as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      () => pending,
    );
    (openEventStream as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      buildReader([
        'event: metrics_update\n' +
          `data: ${JSON.stringify(metricsUpdate)}\n\n`,
        'event: complete\n' + 'data: {"step":"done"}\n\n',
      ]),
    );

    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchDashboard).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByTestId('filters-set-chesscom'));

    fireEvent.click(screen.getByTestId('action-run'));

    await waitFor(() => {
      expect(openEventStream).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByTestId('metrics-version')).toHaveTextContent(
        'metrics version 9',
      );
    });

    if (resolveDashboard) {
      resolveDashboard(baseDashboard);
    }
  });

  it('keeps practice modal closed when no queue items exist', async () => {
    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchDashboard).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByTestId('action-practice'));

    await waitFor(() => {
      expect(screen.queryByTestId('chessboard-modal')).not.toBeInTheDocument();
    });
  });

  it('keeps the abort ref when a newer metrics stream starts', async () => {
    const deferred = buildDeferredReader();
    const quick = buildReader([
      'event: complete\n' + 'data: {"step":"done"}\n\n',
    ]);
    (openEventStream as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(deferred.reader)
      .mockResolvedValueOnce(quick);

    render(<DashboardFlow />);

    await waitFor(() => {
      expect(fetchDashboard).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByTestId('filters-set-chesscom'));

    fireEvent.click(screen.getByTestId('action-refresh'));
    fireEvent.click(screen.getByTestId('action-refresh'));

    await waitFor(() => {
      expect(openEventStream).toHaveBeenCalledTimes(2);
    });

    await waitFor(() => {
      expect(deferred.reader.read).toHaveBeenCalled();
    });

    deferred.resolve({ done: true, value: undefined });
  });
});
