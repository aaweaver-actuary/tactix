import { createElement, type CSSProperties } from 'react';

export const listudyBoardStyle: CSSProperties = {
  backgroundImage: 'url(/boards/listudy-brown.svg)',
  backgroundSize: 'cover',
  backgroundPosition: 'center',
  borderRadius: '14px',
  overflow: 'hidden',
  boxShadow: '0 12px 32px rgba(0, 0, 0, 0.35)',
};

// Squares stay transparent to let the SVG board art show through.
export const listudyLightSquareStyle: CSSProperties = {
  backgroundColor: 'transparent',
};

export const listudyDarkSquareStyle: CSSProperties = {
  backgroundColor: 'transparent',
};

export const listudyNotationStyle: CSSProperties = {
  color: '#203038',
  fontWeight: 600,
  fontFamily: '"Space Grotesk", "Helvetica Neue", sans-serif',
};

export const listudyPieces = {
  bB: buildPiece('bB'),
  bK: buildPiece('bK'),
  bN: buildPiece('bN'),
  bP: buildPiece('bP'),
  bQ: buildPiece('bQ'),
  bR: buildPiece('bR'),
  wB: buildPiece('wB'),
  wK: buildPiece('wK'),
  wN: buildPiece('wN'),
  wP: buildPiece('wP'),
  wQ: buildPiece('wQ'),
  wR: buildPiece('wR'),
};

function buildPiece(pieceId: string) {
  const Piece = ({ squareWidth }: { squareWidth: number }) =>
    createElement('img', {
      src: `/pieces/cburnett/${pieceId}.svg`,
      alt: pieceId,
      draggable: false,
      style: {
        width: squareWidth,
        height: squareWidth,
        userSelect: 'none',
        filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.35))',
      },
    });

  Piece.displayName = `ListudyPiece_${pieceId}`;
  return Piece;
}
