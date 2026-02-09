import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import PracticeAttemptCard from './PracticeAttemptCard';
import type { PracticeQueueItem } from '../api';
import type { PracticeSessionStats } from '../utils/practiceSession';

let lastProps: any = null;

vi.mock('react-chessboard', () => ({
  Chessboard: (props: any) => {
    lastProps = props;
    return <div data-testid="mock-chessboard" />;
  },
}));

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

const renderCard = () =>
  render(
    <PracticeAttemptCard
      currentPractice={basePractice}
      practiceSession={baseSession}
      practiceFen=""
      practiceMove=""
      practiceMoveRef={React.createRef<HTMLInputElement>()}
      practiceSubmitting={false}
      practiceFeedback={null}
      practiceSubmitError={null}
      practiceHighlightStyles={{}}
      practiceOrientation="white"
      onPracticeMoveChange={() => {}}
      handlePracticeAttempt={async () => {}}
      handlePracticeDrop={() => true}
    />,
  );

describe('PracticeAttemptCard', () => {
  it('passes listudy board and piece assets to the chessboard', () => {
    renderCard();

    expect(screen.getByTestId('mock-chessboard')).toBeInTheDocument();
    expect(lastProps.customBoardStyle?.backgroundImage).toContain(
      'var(--listudy-board-texture)',
    );
    expect(lastProps.customPieces?.wK).toBeDefined();
    expect(lastProps.customLightSquareStyle?.backgroundColor).toBe(
      'transparent',
    );
    expect(lastProps.customDarkSquareStyle?.backgroundColor).toBe(
      'transparent',
    );
  });

  it('renders listudy piece imagery with the cburnett set', () => {
    renderCard();

    const Piece = lastProps.customPieces.wK as React.ComponentType<{
      squareWidth: number;
    }>;

    render(<Piece squareWidth={32} />);

    const img = screen.getByRole('img');
    expect(img.getAttribute('src')).toBe('/pieces/cburnett/wK.svg');
  });
});
