import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import BaseChessboard from './BaseChessboard';

let lastProps: any = null;

vi.mock('react-chessboard', () => ({
  Chessboard: (props: any) => {
    lastProps = props;
    return <div data-testid="mock-chessboard" />;
  },
}));

describe('BaseChessboard', () => {
  it('applies the listudy board defaults', () => {
    render(<BaseChessboard position="start" boardWidth={300} />);

    expect(screen.getByTestId('mock-chessboard')).toBeInTheDocument();
    expect(lastProps).toMatchObject({
      customBoardStyle: expect.objectContaining({
        backgroundImage: expect.stringContaining('listudy-board-texture'),
      }),
      customLightSquareStyle: { backgroundColor: 'transparent' },
      customDarkSquareStyle: { backgroundColor: 'transparent' },
    });
    expect(typeof lastProps.customPieces?.wK).toBe('function');
  });

  it('merges provided board overrides', () => {
    render(
      <BaseChessboard
        position="start"
        boardWidth={320}
        customBoardStyle={{ borderRadius: '2px' }}
        customLightSquareStyle={{ backgroundColor: 'rgb(255, 0, 0)' }}
      />,
    );

    expect(lastProps.customBoardStyle?.backgroundImage).toContain(
      'var(--listudy-board-texture)',
    );
    expect(lastProps.customBoardStyle?.borderRadius).toBe('2px');
    expect(lastProps.customLightSquareStyle?.backgroundColor).toBe(
      'rgb(255, 0, 0)',
    );
  });
});
