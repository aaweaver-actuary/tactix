import React from 'react';
import { render, screen } from '@testing-library/react';
import PracticeSessionProgress from './PracticeSessionProgress';

const stats = {
  completed: 4,
  total: 10,
  streak: 2,
  bestStreak: 3,
};

describe('PracticeSessionProgress', () => {
  it('renders streaks and progress text', () => {
    render(<PracticeSessionProgress stats={stats} />);

    expect(screen.getByText('Session progress')).toBeInTheDocument();
    expect(screen.getByText('4 of 10 attempts')).toBeInTheDocument();
    expect(screen.getByText('4 / 10 complete')).toBeInTheDocument();
    expect(screen.getByTestId('practice-session-streak')).toHaveTextContent(
      'Streak 2',
    );
    expect(screen.getByTestId('practice-session-best')).toHaveTextContent(
      'Best 3',
    );
    expect(screen.getByText('Streak momentum')).toBeInTheDocument();
  });

  it('sets progress bar width based on stats', () => {
    render(<PracticeSessionProgress stats={stats} />);
    const fill = screen.getByTestId('practice-progress-fill');
    expect(fill).toHaveStyle({ width: '40%' });
    const streakFill = screen.getByTestId('practice-streak-fill');
    expect(streakFill).toHaveStyle({ width: '67%' });
  });
});
