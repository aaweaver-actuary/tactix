import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MetricsSummaryGrid from './MetricsSummaryGrid';
import BaseMetricsCards from './BaseMetricsCards';
import SourceSyncCards from './SourceSyncCards';
import type { DashboardPayload } from '../api';

vi.mock('./MetricCard', () => ({
  __esModule: true,
  default: ({
    title,
    value,
    note,
    dataTestId,
  }: {
    title: string;
    value: string;
    note?: string;
    dataTestId?: string;
  }) => (
    <div data-testid={dataTestId ?? 'metric-card'}>
      <span>{title}</span>
      <span>{value}</span>
      {note ? <span>{note}</span> : null}
    </div>
  ),
}));

describe('MetricsSummaryGrid', () => {
  it('renders base metrics via the extracted cards', () => {
    render(<BaseMetricsCards positions={4} tactics={2} metricsVersion={9} />);

    const baseCards = screen.getAllByTestId('metric-card');
    expect(baseCards).toHaveLength(3);
    expect(screen.getByText('Positions')).toBeInTheDocument();
    expect(screen.getByText('Tactics')).toBeInTheDocument();
    expect(screen.getByText('Metrics ver.')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('9')).toBeInTheDocument();
  });

  it('renders source sync cards only when sources exist', () => {
    const emptySync: DashboardPayload['source_sync'] = {
      window_days: 7,
      sources: [],
    };

    const { container, rerender } = render(
      <SourceSyncCards sourceSync={emptySync} />,
    );

    expect(container.firstChild).toBeNull();

    rerender(
      <SourceSyncCards
        sourceSync={{
          window_days: 7,
          sources: [
            { source: 'lichess', games_played: 3, synced: true },
            { source: 'custom', games_played: 2, synced: false },
          ],
        }}
      />,
    );

    expect(screen.getByTestId('source-sync-lichess')).toBeInTheDocument();
    expect(screen.getByText('Lichess (7d)')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByTestId('source-sync-custom')).toBeInTheDocument();
    expect(screen.getByText('custom (7d)')).toBeInTheDocument();
  });

  it('renders an empty state with base metrics only', () => {
    const sourceSync: DashboardPayload['source_sync'] = {
      window_days: 7,
      sources: [],
    };

    render(
      <MetricsSummaryGrid
        positions={0}
        tactics={0}
        metricsVersion={0}
        sourceSync={sourceSync}
      />,
    );

    const baseCards = screen.getAllByTestId('metric-card');
    expect(baseCards).toHaveLength(3);
    expect(screen.getByText('Positions')).toBeInTheDocument();
    expect(screen.getByText('Tactics')).toBeInTheDocument();
    expect(screen.getByText('Metrics ver.')).toBeInTheDocument();
    expect(screen.getAllByText('0')).toHaveLength(3);
    expect(screen.queryByTestId('source-sync-lichess')).not.toBeInTheDocument();
  });

  it('renders a loading state without source sync cards', () => {
    render(
      <MetricsSummaryGrid
        positions={12}
        tactics={9}
        metricsVersion={3}
        sourceSync={undefined}
      />,
    );

    expect(screen.getByText('Positions')).toBeInTheDocument();
    expect(screen.getByText('Tactics')).toBeInTheDocument();
    expect(screen.getByText('Metrics ver.')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('9')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.queryByTestId('source-sync-lichess')).not.toBeInTheDocument();
  });

  it('renders source sync metrics when populated', () => {
    const sourceSync: DashboardPayload['source_sync'] = {
      window_days: 14,
      sources: [
        {
          source: 'lichess',
          games_played: 24,
          synced: true,
        },
        {
          source: 'chesscom',
          games_played: 5,
          synced: false,
        },
      ],
    };

    render(
      <MetricsSummaryGrid
        positions={32}
        tactics={11}
        metricsVersion={8}
        sourceSync={sourceSync}
      />,
    );

    expect(screen.getByTestId('source-sync-lichess')).toBeInTheDocument();
    expect(screen.getByTestId('source-sync-chesscom')).toBeInTheDocument();

    expect(screen.getByText('Lichess (14d)')).toBeInTheDocument();
    expect(screen.getByText('Chess.com (14d)')).toBeInTheDocument();
    expect(screen.getByText('24')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Synced from imported games')).toBeInTheDocument();
    expect(
      screen.getByText('No games synced in this window'),
    ).toBeInTheDocument();
  });

  it('keeps the grid layout intact', () => {
    const { container } = render(
      <MetricsSummaryGrid positions={1} tactics={1} metricsVersion={1} />,
    );

    expect(container.firstChild).toHaveClass('grid');
    expect(container.firstChild).toHaveClass('grid-cols-1');
  });
});
