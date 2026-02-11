import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import PracticeModalContent from './PracticeModalContent';

describe('PracticeModalContent', () => {
  it('renders feedback details with explanation and fallback best move', () => {
    render(
      <PracticeModalContent
        currentPractice={{
          tactic_id: 1,
          game_id: 'g1',
          position_id: 1,
          source: 'chesscom',
          motif: 'mate',
          result: 'missed',
          best_uci: 'e2e4',
          user_uci: 'e2e3',
          eval_delta: -1,
          severity: 2,
          created_at: '2026-01-01T00:00:00Z',
          fen: '8/8/8/8/8/8/4K3/7k w - - 0 1',
          position_uci: 'e2e4',
          san: 'e4',
          ply: 1,
          move_number: 1,
          side_to_move: 'w',
          clock_seconds: null,
        }}
        practiceSession={{ completed: 1, total: 2, streak: 0, bestStreak: 1 }}
        practiceFen=""
        practiceMove=""
        practiceMoveRef={React.createRef<HTMLInputElement>()}
        practiceSubmitting={false}
        practiceFeedback={
          {
            correct: false,
            best_uci: '',
            message: 'Try again',
            explanation: 'Mate in 1',
            line: '1...Qh2#',
            rescheduled: false,
          } as any
        }
        practiceSubmitError={null}
        practiceHighlightStyles={{}}
        practiceOrientation="white"
        onPracticeMoveChange={vi.fn()}
        handlePracticeAttempt={vi.fn()}
        handlePracticeDrop={vi.fn()}
      />,
    );

    expect(screen.getByText('Daily practice')).toBeInTheDocument();
    expect(screen.getByTestId('practice-best-move')).toBeInTheDocument();
    expect(screen.getByText('Mate in 1')).toBeInTheDocument();
    expect(screen.getByText('Best --')).toBeInTheDocument();
  });
});
