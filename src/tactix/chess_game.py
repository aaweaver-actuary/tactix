from dataclasses import dataclass, field
from io import StringIO

import chess.pgn

from tactix.utils import generate_id


@dataclass(slots=True)
class ChessGame:
    _raw_pgn: str
    game_id: str = field(default_factory=generate_id)

    @property
    def game(self) -> chess.pgn.Game | None:
        return chess.pgn.read_game(StringIO(self._raw_pgn))

    @property
    def headers(self) -> dict[str, str]:
        game = self.game
        return game.headers if game else {}

    @property
    def timestamp(self) -> str | None:
        return self.headers.get("UTCDate")
