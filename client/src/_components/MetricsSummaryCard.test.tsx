import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MetricsSummaryCard from './MetricsSummaryCard';
import type { DashboardPayload } from '../api';

describe('MetricsSummaryCard', () => {
  it('renders header and base metrics for an empty state', () => {
    const sourceSync: DashboardPayload['source_sync'] = {
      window_days: 7,
      sources: [],
    };

    render(
      <MetricsSummaryCard
        positions={0}
        tactics={0}
        metricsVersion={0}
        sourceSync={sourceSync}
      />,
    );

    expect(screen.getByText('Metrics summary')).toBeInTheDocument();
    expect(screen.getByText('Positions')).toBeInTheDocument();
    expect(screen.getByText('Tactics')).toBeInTheDocument();
    expect(screen.getByText('Metrics ver.')).toBeInTheDocument();
    expect(screen.getAllByText('0')).toHaveLength(3);
    expect(screen.queryByTestId('source-sync-lichess')).not.toBeInTheDocument();
  });

  it('renders a loading state without source sync cards', () => {
    render(
      <MetricsSummaryCard
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

  it('renders optional source sync cards when populated', () => {
    const sourceSync: DashboardPayload['source_sync'] = {
      window_days: 14,
      sources: [
        { source: 'lichess', games_played: 24, synced: true },
        { source: 'chesscom', games_played: 5, synced: false },
      ],
    };

    render(
      <MetricsSummaryCard
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
});
