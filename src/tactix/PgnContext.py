from dataclasses import dataclass
from io import StringIO

import chess
import chess.pgn


@dataclass
class PgnContext:
    pgn: str
    user: str
    source: str
    game_id: str | None = None
    side_to_move_filter: str | None = None
    _game: chess.pgn.Game | None = None
    _board: chess.Board | None = None

    def __post_init__(self):
        self.user = self.user.lower()
        if self._game is None:
            self._get_game()

    def _get_game(self):
        if self._game is None:
            self._game = chess.pgn.read_game(StringIO(self.pgn))

    @property
    def game(self) -> chess.pgn.Game | None:
        self._get_game()
        return self._game

    @property
    def headers(self) -> dict[str, str]:
        self._get_game()
        if self._game is None:
            return {}
        return dict(self._game.headers)

    @property
    def fen(self) -> str | None:
        board = self.board
        if board is None:
            return None
        return board.fen()

    @property
    def board(self) -> chess.Board | None:
        if self._game is None:
            self._get_game()
        if self._game is None:
            return None
        if self._board is None:
            self._board = self._game.board()
        return self._board

    @property
    def white(self) -> str:
        game = self.game
        if game is None:
            return ""
        return game.headers.get("White", "").lower()

    @property
    def black(self) -> str:
        game = self.game
        if game is None:
            return ""
        return game.headers.get("Black", "").lower()

    @property
    def ply(self) -> int:
        board = self.board
        if board is None:
            return 0
        return board.ply()

    @property
    def move_number(self) -> int:
        board = self.board
        if board is None:
            return 0
        return board.fullmove_number

    @property
    def side_to_move(self) -> str | None:
        board = self.board
        if board is None:
            return None
        return "white" if board.turn == chess.WHITE else "black"
