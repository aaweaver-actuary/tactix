import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ChessboardModal from './ChessboardModal';

let lastProps: any = null;

vi.mock('react-dom', () => ({
  createPortal: (node: React.ReactNode) => node,
}));

vi.mock('./BaseChessboard', () => ({
  default: (props: any) => {
    lastProps = props;
    return <div data-testid="base-chessboard" />;
  },
}));

describe('ChessboardModal', () => {
  beforeEach(() => {
    lastProps = null;
  });

  it('returns null when closed', () => {
    render(<ChessboardModal open={false} position={null} onClose={vi.fn()} />);

    expect(screen.queryByTestId('chessboard-modal')).not.toBeInTheDocument();
  });

  it('renders empty state when no position is selected', () => {
    render(<ChessboardModal open position={null} onClose={vi.fn()} />);

    expect(screen.getByTestId('chessboard-modal')).toBeInTheDocument();
    expect(
      screen.getByText('Select a position to view the board.'),
    ).toBeInTheDocument();
  });

  it('renders the board and forwards orientation and position', () => {
    const handleClose = vi.fn();
    render(
      <ChessboardModal
        open
        position={
          {
            fen: '8/8/8/8/8/8/8/8 b - - 0 1',
            move_number: 12,
            san: 'Qh5',
            clock_seconds: 42,
          } as any
        }
        onClose={handleClose}
      />,
    );

    expect(screen.getByTestId('chessboard-modal-board')).toBeInTheDocument();
    expect(screen.getByTestId('base-chessboard')).toBeInTheDocument();
    expect(lastProps).toMatchObject({
      position: '8/8/8/8/8/8/8/8 b - - 0 1',
      boardOrientation: 'black',
    });

    fireEvent.click(screen.getByTestId('chessboard-modal-close'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('renders practice mode content when provided', () => {
    render(
      <ChessboardModal
        open
        position={null}
        practice={{
          currentPractice: {
            tactic_id: 1,
            game_id: 'g1',
            position_id: 9,
            source: 'chesscom',
            motif: 'hanging_piece',
            result: 'missed',
            best_uci: 'e2e4',
            user_uci: 'e2e3',
            eval_delta: -1,
            severity: 2,
            created_at: '2026-02-01T00:00:00Z',
            fen: '8/8/8/8/8/8/8/8 w - - 0 1',
            position_uci: 'e2e4',
            san: 'e4',
            ply: 1,
            move_number: 1,
            side_to_move: 'w',
            clock_seconds: 60,
          },
          practiceSession: { completed: 0, total: 1, streak: 0, bestStreak: 0 },
          practiceFen: '',
          practiceMove: '',
          practiceMoveRef: React.createRef<HTMLInputElement>(),
          practiceSubmitting: false,
          practiceFeedback: null,
          practiceSubmitError: null,
          practiceHighlightStyles: {},
          practiceOrientation: 'white',
          onPracticeMoveChange: vi.fn(),
          handlePracticeAttempt: vi.fn(),
          handlePracticeDrop: vi.fn(),
        }}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText('Daily practice')).toBeInTheDocument();
    expect(screen.getByTestId('chessboard-modal')).toBeInTheDocument();
    expect(screen.queryByTestId('practice-best-move')).not.toBeInTheDocument();
  });
});
