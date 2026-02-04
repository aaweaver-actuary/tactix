"""PGN parsing context and helpers."""

# pylint: disable=invalid-name

from dataclasses import dataclass
from io import StringIO

import chess
import chess.pgn


@dataclass
class PgnContext:
    """Holds parsed PGN data and cached derived values."""

    pgn: str
    user: str
    source: str
    game_id: str | None = None
    side_to_move_filter: str | None = None
    _game: chess.pgn.Game | None = None
    _board: chess.Board | None = None

    def __post_init__(self):
        """Normalize user name and initialize cached game."""
        self.user = self.user.lower()
        if self._game is None:
            self._get_game()

    def _get_game(self):
        """Parse the PGN text into a game if needed."""
        if self._game is None:
            self._game = chess.pgn.read_game(StringIO(self.pgn))

    @property
    def game(self) -> chess.pgn.Game | None:
        """Return the parsed PGN game."""
        self._get_game()
        return self._game

    @property
    def headers(self) -> dict[str, str]:
        """Return PGN headers as a dictionary."""
        self._get_game()
        if self._game is None:
            return {}
        return dict(self._game.headers)

    @property
    def fen(self) -> str | None:
        """Return the current board FEN for the PGN."""
        board = self.board
        if board is None:
            return None
        return board.fen()

    @property
    def board(self) -> chess.Board | None:
        """Return the cached board for the PGN."""
        if self._game is None:
            self._get_game()
        if self._game is None:
            return None
        if self._board is None:
            self._board = self._game.board()
        return self._board

    @property
    def white(self) -> str:
        """Return the normalized white player name."""
        game = self.game
        if game is None:
            return ""
        return game.headers.get("White", "").lower()

    @property
    def black(self) -> str:
        """Return the normalized black player name."""
        game = self.game
        if game is None:
            return ""
        return game.headers.get("Black", "").lower()

    @property
    def ply(self) -> int:
        """Return the current ply count for the PGN."""
        board = self.board
        if board is None:
            return 0
        return board.ply()

    @property
    def move_number(self) -> int:
        """Return the current fullmove number for the PGN."""
        board = self.board
        if board is None:
            return 0
        return board.fullmove_number

    @property
    def side_to_move(self) -> str | None:
        """Return which side is to move at the current board state."""
        board = self.board
        if board is None:
            return None
        return "white" if board.turn == chess.WHITE else "black"
