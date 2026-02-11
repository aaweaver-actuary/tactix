import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import PostgresRawPgnsCard from './PostgresRawPgnsCard';

describe('PostgresRawPgnsCard', () => {
  it('returns null when data is missing and not loading', () => {
    const { container } = render(
      <PostgresRawPgnsCard data={null} loading={false} />,
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders loading shell when data is missing', () => {
    render(<PostgresRawPgnsCard data={null} loading={true} />);

    expect(screen.getByText('Postgres raw PGNs')).toBeInTheDocument();
    expect(screen.getByText('loading')).toBeInTheDocument();
    expect(screen.getByText('Loading raw PGNs...')).toBeInTheDocument();
  });

  it('renders error and source breakdown details', () => {
    render(
      <PostgresRawPgnsCard
        data={{
          status: 'ok',
          total_rows: 120,
          distinct_games: 25,
          latest_ingested_at: '2026-02-01T12:00:00Z',
          sources: [
            {
              source: 'lichess',
              total_rows: 70,
              distinct_games: 15,
              latest_ingested_at: '2026-02-01T11:00:00Z',
            },
          ],
        }}
        loading={false}
        error="Failed to load raw PGNs"
      />,
    );

    expect(screen.getByTestId('postgres-raw-pgns')).toBeInTheDocument();
    expect(screen.getByText('Failed to load raw PGNs')).toBeInTheDocument();
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('lichess')).toBeInTheDocument();
    expect(screen.getByText('70 rows')).toBeInTheDocument();
    expect(screen.getByText('15 games')).toBeInTheDocument();
    expect(screen.getAllByText(/2026/).length).toBeGreaterThan(0);
  });
});
