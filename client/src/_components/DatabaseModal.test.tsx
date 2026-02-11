import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DatabaseModal from './DatabaseModal';

vi.mock('react-dom', () => ({
  createPortal: (node: React.ReactNode) => node,
}));

const baseStatus = {
  enabled: true,
  status: 'ok' as const,
  latency_ms: 12,
  error: null,
  schema: 'public',
  tables: ['games'],
  events: [],
};

const baseRawPgns = {
  status: 'ok',
  total_rows: 10,
  distinct_games: 5,
  latest_ingested_at: '2026-02-01T12:00:00Z',
  sources: [],
};

const baseAnalysisRows = [
  {
    tactic_id: 1,
    motif: 'mate',
    result: 'missed',
    best_uci: 'e2e4',
    severity: 1.2,
  },
];

describe('DatabaseModal', () => {
  it('returns null when closed', () => {
    render(
      <DatabaseModal
        open={false}
        onClose={vi.fn()}
        status={baseStatus as any}
        statusLoading={false}
        rawPgns={baseRawPgns as any}
        rawPgnsLoading={false}
        analysisRows={baseAnalysisRows as any}
        analysisLoading={false}
      />,
    );

    expect(screen.queryByTestId('database-modal')).not.toBeInTheDocument();
  });

  it('renders errors when provided', () => {
    render(
      <DatabaseModal
        open
        onClose={vi.fn()}
        status={null}
        statusLoading={false}
        statusError="Status failed"
        rawPgns={null}
        rawPgnsLoading={false}
        rawPgnsError="Raw PGNs failed"
        analysisRows={[]}
        analysisLoading={false}
        analysisError="Analysis failed"
      />,
    );

    expect(screen.getByTestId('database-modal')).toBeInTheDocument();
    expect(screen.getAllByText('Status failed').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Raw PGNs failed').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Analysis failed').length).toBeGreaterThan(0);
  });

  it('renders database cards when data is available', () => {
    render(
      <DatabaseModal
        open
        onClose={vi.fn()}
        status={baseStatus as any}
        statusLoading={false}
        rawPgns={baseRawPgns as any}
        rawPgnsLoading={false}
        analysisRows={baseAnalysisRows as any}
        analysisLoading={false}
      />,
    );

    expect(screen.getByTestId('database-modal')).toBeInTheDocument();
    expect(screen.getByTestId('postgres-status')).toBeInTheDocument();
    expect(screen.getByTestId('postgres-raw-pgns')).toBeInTheDocument();
    expect(screen.getByTestId('postgres-analysis')).toBeInTheDocument();
  });
});
