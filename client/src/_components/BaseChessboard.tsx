import type { CSSProperties } from 'react';
import {
  listudyBoardStyle,
  listudyDarkSquareStyle,
  listudyLightSquareStyle,
  listudyNotationStyle,
  listudyPieces,
} from '../utils/listudyAssets';
import Chessboard, { ChessboardProps } from './Chessboard';

type BaseChessboardProps = ChessboardProps;

const mergeStyles = (
  base: CSSProperties,
  override?: CSSProperties,
): CSSProperties => (override ? { ...base, ...override } : base);

export default function BaseChessboard({
  customBoardStyle,
  customLightSquareStyle,
  customDarkSquareStyle,
  customNotationStyle,
  customPieces,
  ...props
}: BaseChessboardProps) {
  const boardStyle = mergeStyles(listudyBoardStyle, customBoardStyle);
  const lightSquareStyle = mergeStyles(
    listudyLightSquareStyle,
    customLightSquareStyle,
  );
  const darkSquareStyle = mergeStyles(
    listudyDarkSquareStyle,
    customDarkSquareStyle,
  );
  const notationStyle = mergeStyles(listudyNotationStyle, customNotationStyle);

  return (
    <Chessboard
      {...props}
      customBoardStyle={boardStyle}
      customLightSquareStyle={lightSquareStyle}
      customDarkSquareStyle={darkSquareStyle}
      customNotationStyle={notationStyle}
      customPieces={customPieces ?? listudyPieces}
    />
  );
}
