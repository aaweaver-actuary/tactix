import { createElement, type CSSProperties } from 'react';

const listudyPiecePathPrefix = '/pieces/cburnett/';
const listudyBoardTextureVar = 'var(--listudy-board-texture)';

const listudyPieceIds = [
  'bB',
  'bK',
  'bN',
  'bP',
  'bQ',
  'bR',
  'wB',
  'wK',
  'wN',
  'wP',
  'wQ',
  'wR',
] as const;

export const listudyPreviewPieceIds = [
  'wK',
  'wQ',
  'wB',
  'wN',
  'wR',
  'wP',
] as const;

export const listudyBoardStyle: CSSProperties = {
  backgroundImage: listudyBoardTextureVar,
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

export const listudyPieces = listudyPieceIds.reduce(
  (acc, pieceId) => {
    acc[pieceId] = buildPiece(pieceId);
    return acc;
  },
  {} as Record<(typeof listudyPieceIds)[number], ReturnType<typeof buildPiece>>,
);

function buildPiece(pieceId: string) {
  const Piece = ({ squareWidth }: { squareWidth: number }) =>
    createElement('img', {
      src: `${listudyPiecePathPrefix}${pieceId}.svg`,
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
