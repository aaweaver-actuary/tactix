import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import PostgresAnalysisCard from './PostgresAnalysisCard';

describe('PostgresAnalysisCard', () => {
  it('returns null when there are no rows and not loading', () => {
    const { container } = render(
      <PostgresAnalysisCard rows={[]} loading={false} />,
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders loading placeholder when no rows are available', () => {
    render(<PostgresAnalysisCard rows={[]} loading={true} />);

    expect(screen.getByText('Postgres analysis results')).toBeInTheDocument();
    expect(screen.getByText('Loading analysis rows...')).toBeInTheDocument();
  });

  it('renders analysis rows with badges', () => {
    render(
      <PostgresAnalysisCard
        rows={[
          {
            tactic_id: 42,
            motif: 'mate',
            result: 'missed',
            best_uci: 'e2e4',
            severity: 1.5,
          },
          {
            tactic_id: 43,
            motif: null,
            result: null,
            best_uci: null,
            severity: null,
          },
        ]}
        loading={false}
      />,
    );

    expect(screen.getByTestId('postgres-analysis')).toBeInTheDocument();
    expect(screen.getByText('#42')).toBeInTheDocument();
    expect(screen.getByText('mate · missed')).toBeInTheDocument();
    expect(screen.getByText('e2e4')).toBeInTheDocument();
    expect(screen.getByText('sev 1.50')).toBeInTheDocument();
    expect(screen.getByText('unknown · n/a')).toBeInTheDocument();
  });
});
