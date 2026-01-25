import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MetricsGrid from './MetricsGrid';

vi.mock('./Badge', () => ({
  default: ({ label }: { label: string }) => (
    <span data-testid="badge">{label}</span>
  ),
}));

vi.mock('./MetricCard', () => ({
  default: ({
    title,
    value,
    note,
  }: {
    title: string;
    value: string;
    note: string;
  }) => (
    <div data-testid="metric-card">
      <span>{title}</span>
      <span>{value}</span>
      <span>{note}</span>
    </div>
  ),
}));

describe('MetricsGrid', () => {
  it('renders header and badge', () => {
    render(
      <MetricsGrid
        metricsData={[
          {
            motif: 'Motif A',
            found: 5,
            total: 10,
            missed: 3,
            failed_attempt: 2,
          },
        ]}
      />,
    );

    expect(screen.getByTestId('motif-breakdown')).toBeInTheDocument();
    expect(screen.getByText('Motif breakdown')).toBeInTheDocument();
    expect(screen.getByTestId('badge')).toHaveTextContent('Updated');
  });

  it('renders a card for each metric with formatted values', () => {
    render(
      <MetricsGrid
        metricsData={[
          {
            motif: 'Motif A',
            found: 5,
            total: 10,
            missed: 3,
            failed_attempt: 2,
          },
          {
            motif: 'Motif B',
            found: 8,
            total: 12,
            missed: 2,
            failed_attempt: 2,
          },
        ]}
      />,
    );

    const cards = screen.getAllByTestId('metric-card');
    expect(cards).toHaveLength(2);

    expect(screen.getByText('Motif A')).toBeInTheDocument();
    expect(screen.getByText('5/10')).toBeInTheDocument();
    expect(screen.getByText('3 missed, 2 failed')).toBeInTheDocument();

    expect(screen.getByText('Motif B')).toBeInTheDocument();
    expect(screen.getByText('8/12')).toBeInTheDocument();
    expect(screen.getByText('2 missed, 2 failed')).toBeInTheDocument();
  });
});
