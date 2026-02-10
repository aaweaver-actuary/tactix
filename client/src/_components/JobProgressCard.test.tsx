import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import JobProgressCard from './JobProgressCard';

describe('JobProgressCard', () => {
  it('returns null when entries are empty', () => {
    const { container } = render(
      <JobProgressCard entries={[]} status="idle" />,
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders status and entry details', () => {
    render(
      <JobProgressCard
        status="running"
        entries={[
          {
            step: 'Analyze games',
            analyzed: 2,
            total: 5,
            message: 'Processing',
          } as any,
          {
            step: 'Fetch games',
            fetched_games: 8,
          } as any,
        ]}
      />,
    );

    expect(screen.getByText('Job progress')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('Analyze games')).toBeInTheDocument();
    expect(screen.getByText('Processing')).toBeInTheDocument();
    expect(screen.getByText('2/5')).toBeInTheDocument();
    expect(screen.getByText('Fetch games')).toBeInTheDocument();
    expect(screen.getByText('8 games')).toBeInTheDocument();
  });
});
