import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import FiltersCard from './FiltersCard';

vi.mock('react-dom', () => ({
  createPortal: (node: React.ReactNode) => node,
}));

const baseFilters = {
  motif: 'all',
  timeControl: 'all',
  ratingBucket: 'all',
  startDate: '',
  endDate: '',
};

const baseProps = {
  source: 'lichess' as const,
  loading: false,
  lichessProfile: 'rapid' as const,
  chesscomProfile: 'blitz' as const,
  filters: baseFilters,
  motifOptions: ['all', 'fork'],
  timeControlOptions: ['all', 'rapid'],
  ratingOptions: ['all', '1200'],
  onSourceChange: vi.fn(),
  onLichessProfileChange: vi.fn(),
  onChesscomProfileChange: vi.fn(),
  onFiltersChange: vi.fn(),
  onResetFilters: vi.fn(),
};

describe('FiltersCard', () => {
  it('opens and closes the modal from the card action', () => {
    render(<FiltersCard {...baseProps} />);

    expect(screen.queryByTestId('filters-modal')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('filters-open'));
    expect(screen.getByTestId('filters-modal')).toBeInTheDocument();
    expect(screen.getByTestId('filter-lichess-profile')).toBeInTheDocument();
    expect(
      screen.queryByTestId('filter-chesscom-profile'),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('filters-modal-close'));
    expect(screen.queryByTestId('filters-modal')).not.toBeInTheDocument();
  });

  it('fires callbacks when filter inputs change', () => {
    const onSourceChange = vi.fn();
    const onFiltersChange = vi.fn();
    const onResetFilters = vi.fn();

    render(
      <FiltersCard
        {...baseProps}
        modalOpen
        showCard={false}
        onSourceChange={onSourceChange}
        onFiltersChange={onFiltersChange}
        onResetFilters={onResetFilters}
      />,
    );

    fireEvent.change(screen.getByTestId('filter-source'), {
      target: { value: 'chesscom' },
    });
    expect(onSourceChange).toHaveBeenCalledWith('chesscom');

    fireEvent.change(screen.getByTestId('filter-motif'), {
      target: { value: 'fork' },
    });
    expect(onFiltersChange).toHaveBeenCalledWith({
      ...baseFilters,
      motif: 'fork',
    });

    fireEvent.click(screen.getByText('Reset filters'));
    expect(onResetFilters).toHaveBeenCalledTimes(1);
  });
});
