import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import PracticeAttemptCard from './PracticeAttemptCard';
import type { PracticeQueueItem } from '../api';
import type { PracticeSessionStats } from '../utils/practiceSession';

const basePractice: PracticeQueueItem = {
  tactic_id: 1,
  game_id: 'g1',
  position_id: 10,
  source: 'chesscom',
  motif: 'hanging_piece',
  result: 'missed',
  best_uci: 'e2e4',
  user_uci: 'e2e3',
  eval_delta: -50,
  severity: 1,
  created_at: '2026-02-08T00:00:00Z',
  fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  position_uci: 'e2e4',
  san: 'e4',
  ply: 1,
  move_number: 1,
  side_to_move: 'white',
  clock_seconds: 300,
};

const baseSession: PracticeSessionStats = {
  completed: 0,
  total: 5,
  streak: 0,
  bestStreak: 0,
};

const renderCard = (
  overrides?: Partial<React.ComponentProps<typeof PracticeAttemptCard>>,
) =>
  render(
    <PracticeAttemptCard
      currentPractice={basePractice}
      practiceSession={baseSession}
      practiceLoading={false}
      practiceModalOpen={false}
      onStartPractice={vi.fn()}
      {...overrides}
    />,
  );

describe('PracticeAttemptCard', () => {
  it('renders a start button when practice items are available', () => {
    renderCard();

    expect(screen.getByTestId('practice-start')).toBeInTheDocument();
    expect(screen.getByText('Start practice')).toBeInTheDocument();
  });

  it('shows a completion message when the daily set is finished', () => {
    renderCard({
      currentPractice: null,
      practiceSession: { ...baseSession, total: 3 },
    });

    expect(
      screen.getByText('Daily set complete. Great work.'),
    ).toBeInTheDocument();
  });
});
