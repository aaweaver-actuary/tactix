import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TimeTroubleCorrelation from './TimeTroubleCorrelation';

vi.mock('./Badge', () => ({
  default: ({ label }: { label: string }) => (
    <span data-testid="badge">{label}</span>
  ),
}));

describe('TimeTroubleCorrelation', () => {
  it('renders correlation rows with explanation', () => {
    render(
      <TimeTroubleCorrelation
        metricsData={
          [
            {
              metric_type: 'time_trouble_correlation',
              time_control: '300+0',
              found_rate: 0.5,
              miss_rate: 0.25,
              total: 12,
            },
            {
              metric_type: 'time_trouble_correlation',
              time_control: '600+5',
              found_rate: -0.75,
              miss_rate: 0.4,
              total: 8,
            },
          ] as any
        }
      />,
    );

    expect(screen.getByTestId('time-trouble-correlation')).toBeInTheDocument();
    const header = screen.getByRole('button', {
      name: /time-trouble correlation/i,
    });
    fireEvent.click(header);
    expect(screen.getByText('Time-trouble correlation')).toBeInTheDocument();
    expect(screen.getByTestId('badge')).toHaveTextContent('By time control');
    expect(screen.getByText('300+0')).toBeInTheDocument();
    expect(screen.getByText('600+5')).toBeInTheDocument();
    expect(screen.getByText('+0.50')).toBeInTheDocument();
    expect(screen.getByText('-0.75')).toBeInTheDocument();
    expect(screen.getByText('25.0%')).toBeInTheDocument();
    expect(screen.getByText('40.0%')).toBeInTheDocument();
  });
});
