import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import {
  listudyBoardStyle,
  listudyDarkSquareStyle,
  listudyLightSquareStyle,
  listudyNotationStyle,
  listudyPieces,
} from './listudyAssets';

describe('listudyAssets', () => {
  it('defines board and square styles', () => {
    expect(listudyBoardStyle.backgroundImage).toContain(
      'listudy-board-texture',
    );
    expect(listudyLightSquareStyle.backgroundColor).toBe('transparent');
    expect(listudyDarkSquareStyle.backgroundColor).toBe('transparent');
    expect(listudyNotationStyle.fontFamily).toContain('Space Grotesk');
  });

  it('renders listudy pieces with the expected image source', () => {
    const Piece = listudyPieces.wK;
    render(<Piece squareWidth={42} />);

    const img = screen.getByRole('img', { name: 'wK' });
    expect(img).toHaveAttribute('src', '/pieces/cburnett/wK.svg');
    expect(img).toHaveStyle({ width: '42px', height: '42px' });
  });
});
