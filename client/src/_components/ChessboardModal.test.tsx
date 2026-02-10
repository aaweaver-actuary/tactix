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
});
