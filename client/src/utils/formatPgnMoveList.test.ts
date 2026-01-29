import formatPgnMoveList from './formatPgnMoveList';

describe('formatPgnMoveList', () => {
  it('returns move pairs from a PGN', () => {
    const pgn = `
[Event "Test"]
[Site "https://lichess.org/abcd1234"]
[Date "2024.01.01"]
[Round "-"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 1-0
`;
    const moves = formatPgnMoveList(pgn);
    expect(moves).toEqual([
      '1. e4 e5',
      '2. Nf3 Nc6',
      '3. Bb5 a6',
      '4. Ba4 Nf6',
    ]);
  });

  it('returns empty list for invalid PGN', () => {
    expect(formatPgnMoveList('not a pgn')).toEqual([]);
  });
});
