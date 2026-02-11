import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import PostgresStatusCard from './PostgresStatusCard';

describe('PostgresStatusCard', () => {
  it('returns null when there is no status and not loading', () => {
    const { container } = render(
      <PostgresStatusCard status={null} loading={false} />,
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders loading state when status is missing', () => {
    render(<PostgresStatusCard status={null} loading={true} />);

    expect(screen.getByText('Loading Postgres status...')).toBeInTheDocument();
  });

  it('renders connected status details and empty events', () => {
    render(
      <PostgresStatusCard
        status={{
          enabled: true,
          status: 'ok',
          latency_ms: 12,
          error: null,
          schema: 'public',
          tables: ['games'],
          events: [],
        }}
        loading={false}
      />,
    );

    expect(screen.getByText('Postgres status')).toBeInTheDocument();
    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getByText('12.00 ms')).toBeInTheDocument();
    expect(screen.getByText('games')).toBeInTheDocument();
    expect(screen.getByText('No events yet')).toBeInTheDocument();
  });

  it('renders disabled and unreachable states with events', () => {
    const baseStatus = {
      enabled: false,
      latency_ms: undefined,
      error: 'Network error',
      schema: null,
      tables: [],
      events: [],
    };

    const { rerender } = render(
      <PostgresStatusCard
        status={{ ...baseStatus, status: 'disabled' } as any}
        loading={true}
      />,
    );

    expect(screen.getByText('Disabled')).toBeInTheDocument();
    expect(screen.getAllByText('n/a').length).toBeGreaterThan(0);
    expect(screen.getByText('Network error')).toBeInTheDocument();
    expect(screen.getByText('Loading events...')).toBeInTheDocument();

    rerender(
      <PostgresStatusCard
        status={
          {
            ...baseStatus,
            status: 'error',
            events: [
              {
                id: 'event-1',
                created_at: '2026-02-01T12:00:00Z',
                component: 'ingest',
                event_type: 'start',
                source: 'lichess',
              },
              {
                id: 'event-2',
                created_at: '2026-02-01T13:00:00Z',
                component: 'sync',
                event_type: 'done',
                source: null,
              },
            ],
          } as any
        }
        loading={false}
      />,
    );

    expect(screen.getByText('Unreachable')).toBeInTheDocument();
    expect(screen.getByText('ingest:start')).toBeInTheDocument();
    expect(screen.getByText('lichess')).toBeInTheDocument();
    expect(screen.getByText('sync:done')).toBeInTheDocument();
  });
});
