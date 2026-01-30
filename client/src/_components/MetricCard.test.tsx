import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import MetricCard from './MetricCard';

vi.mock('./Text', () => ({
  __esModule: true,
  default: ({ value }: { value: string }) => <span>{value}</span>,
}));

describe('MetricCard', () => {
  it('renders title and value', () => {
    render(<MetricCard title="Revenue" value="$123" />);
    const header = screen.getByRole('button', { name: /revenue/i });
    expect(header).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('$123')).toBeInTheDocument();
  });

  it('renders note when provided', () => {
    render(<MetricCard title="Users" value="42" note="Up 10%" />);
    const header = screen.getByRole('button', { name: /users/i });
    fireEvent.click(header);
    expect(header).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Up 10%')).toBeInTheDocument();
  });

  it('does not render note when not provided', () => {
    render(<MetricCard title="Sessions" value="99" />);
    const header = screen.getByRole('button', { name: /sessions/i });
    fireEvent.click(header);
    expect(screen.queryByText(/%|note/i)).not.toBeInTheDocument();
  });
});
