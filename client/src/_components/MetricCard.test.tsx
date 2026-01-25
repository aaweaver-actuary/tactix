import React from 'react';
import { render, screen } from '@testing-library/react';
import MetricCard from './MetricCard';

jest.mock('./Text', () => ({
  __esModule: true,
  default: ({ value }: { value: string }) => <span>{value}</span>,
}));

describe('MetricCard', () => {
  it('renders title and value', () => {
    render(<MetricCard title="Revenue" value="$123" />);
    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('$123')).toBeInTheDocument();
  });

  it('renders note when provided', () => {
    render(<MetricCard title="Users" value="42" note="Up 10%" />);
    expect(screen.getByText('Up 10%')).toBeInTheDocument();
  });

  it('does not render note when not provided', () => {
    render(<MetricCard title="Sessions" value="99" />);
    expect(screen.queryByText(/%|note/i)).not.toBeInTheDocument();
  });
});
