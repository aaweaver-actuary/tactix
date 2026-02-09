import type { CSSProperties } from 'react';
import { Chessboard as ReactChessboard } from 'react-chessboard';

type ChessboardPieceRenderer = ({
  squareWidth,
}: {
  squareWidth: number;
}) => JSX.Element;

type ChessboardProps = {
  id?: string;
  position?: string;
  boardOrientation?: 'white' | 'black';
  boardWidth?: number;
  showBoardNotation?: boolean;
  arePiecesDraggable?: boolean;
  isDraggablePiece?: (args: { piece: string; sourceSquare: string }) => boolean;
  onPieceDrop?: (
    sourceSquare: string,
    targetSquare: string,
    piece: string,
  ) => boolean;
  customBoardStyle?: CSSProperties;
  customLightSquareStyle?: CSSProperties;
  customDarkSquareStyle?: CSSProperties;
  customNotationStyle?: CSSProperties;
  customPieces?: Record<string, ChessboardPieceRenderer>;
  customSquareStyles?: Record<string, CSSProperties>;
};

export default function Chessboard(props: ChessboardProps) {
  return <ReactChessboard {...props} />;
}
