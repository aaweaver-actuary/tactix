"""PGN header parsing and normalization."""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from functools import singledispatch
from io import StringIO

import chess.pgn

from tactix._get_game_result_for_user_from_pgn_headers import (
    _get_game_result_for_user_from_pgn_headers,
)
from tactix._parse_optional_int import _parse_optional_int
from tactix.chess_game_result import ChessGameResult
from tactix.chess_time_control import ChessTimeControl
from tactix.utils import Now


@dataclass
class PgnHeaders:  # pylint: disable=too-many-instance-attributes
    """Dataclass representing PGN headers for a chess game."""

    event: str
    site: str
    date: datetime.date | str | None
    time_control: ChessTimeControl
    round: int | None = None
    white_player: str | None = None
    black_player: str | None = None
    result: ChessGameResult | None = None
    white_elo: int | None = None
    black_elo: int | None = None
    end_time: datetime.datetime | None = None
    termination: str | None = None

    def __post_init__(self):
        """Normalize header fields after initialization."""
        self.date = _coerce_pgn_date(self.date)
        self._convert_round_to_int()
        if not self.result:
            self.result = ChessGameResult.UNKNOWN

    def _convert_round_to_int(self):
        """Normalize the round value into an integer."""
        if self.round is None:
            return
        try:
            self.round = int(self.round)
        except (TypeError, ValueError):
            self.round = None

    @classmethod
    def from_pgn_string(cls, pgn_string: str, game_index: int = 0) -> PgnHeaders:
        """Create a PgnHeaders dataclass directly from a PGN string.

        Parameters
        ----------
        pgn_string : str
            A string containing the PGN data.

        Returns
        -------
        PgnHeaders
            An instance of PgnHeaders populated with data from the PGN string.
        """
        chunks = re.split(r"\n\n(?=\[Event\s+\".*?\"\])", pgn_string)
        if game_index >= len(chunks):
            error_msg = f"Requested game index {game_index} but only {len(chunks)} games found."
            raise IndexError(error_msg)
        headers = chess.pgn.read_headers(StringIO(chunks[game_index]))
        if headers is None:
            headers = chess.pgn.Headers()
        try:
            result = _get_game_result_for_user_from_pgn_headers(headers, "chesscom")
        except ValueError:
            result = None
        return cls(
            event=headers.get("Event", ""),
            site=headers.get("Site", ""),
            date=headers.get("Date", ""),
            round=_parse_optional_int(headers.get("Round")),
            white_player=headers.get("White"),
            black_player=headers.get("Black"),
            result=result,
            white_elo=_parse_optional_int(headers.get("WhiteElo")),
            black_elo=_parse_optional_int(headers.get("BlackElo")),
            time_control=ChessTimeControl.from_pgn_string(headers.get("TimeControl", "-"))
            or ChessTimeControl(initial=0),
            end_time=None,
            termination=headers.get("Termination"),
        )

    @classmethod
    def from_file(cls, file_path: str, game_index: int = 0) -> PgnHeaders:
        """Create a PgnHeaders dataclass directly from a PGN file.

        If the file contains multiple games, this will read the first one by default,
        but you can specify a different game index.

        Parameters
        ----------
        file_path : str
            Path to the PGN file.
        game_index : int, optional
            Index of the game to read (default is 0).

        Returns
        -------
        PgnHeaders
            An instance of PgnHeaders populated with data from the PGN file.
        """
        with open(file_path, encoding="utf-8") as f:
            raw_pgn = f.read()

        chunks = re.split(r"\n\n(?=\[Event\s+\".*?\"\])", raw_pgn)
        if game_index >= len(chunks):
            error_msg = f"Requested game index {game_index} but only {len(chunks)} games found."
            raise IndexError(error_msg)

        if game_index == 0:
            info_message = f"Reading first game of {len(chunks)} from {file_path}."
            print(info_message)

        return cls.from_pgn_string(chunks[game_index])

    @classmethod
    def from_chess_pgn_headers(cls, headers: chess.pgn.Headers) -> PgnHeaders:
        """Create a PgnHeaders dataclass from chess.pgn.Headers.

        Parameters
        ----------
        headers : chess.pgn.Headers
            The PGN headers object from python-chess.

        Returns
        -------
        PgnHeaders
            An instance of PgnHeaders populated with data from the chess.pgn.Headers.
        """
        return cls(
            event=headers.get("Event", ""),
            site=headers.get("Site", ""),
            date=headers.get("Date", ""),
            round=_parse_optional_int(headers.get("Round")),
            white_player=headers.get("White"),
            black_player=headers.get("Black"),
            result=None,
            white_elo=_parse_optional_int(headers.get("WhiteElo")),
            black_elo=_parse_optional_int(headers.get("BlackElo")),
            time_control=ChessTimeControl.from_pgn_string(headers.get("TimeControl", "-"))
            or ChessTimeControl(initial=0),
            end_time=None,
            termination=headers.get("Termination"),
        )

    @staticmethod
    def extract_all_from_str(pgn_string: str) -> list[PgnHeaders]:
        """Extract PGN headers from all games in a PGN file.

        Parameters
        ----------
        pgn_string : str
            String containing PGN data for one or more games.

        Returns
        -------
        list[PgnHeaders]
            A list of PgnHeaders instances, one for each game in the PGN string.
        """

        chunks = re.split(r"\n\n(?=\[Event\s+\".*?\"\])", pgn_string)

        return [PgnHeaders.from_pgn_string(chunk) for chunk in chunks if chunk.strip()]


@singledispatch
def _coerce_pgn_date(_value: object) -> datetime.date | None:
    return None


@_coerce_pgn_date.register
def _coerce_pgn_datetime_dispatch(value: datetime.datetime) -> datetime.date | None:
    return _coerce_pgn_datetime(value)


@_coerce_pgn_date.register
def _coerce_pgn_date_dispatch(value: datetime.date) -> datetime.date | None:
    return value


@_coerce_pgn_date.register
def _coerce_pgn_str_dispatch(value: str) -> datetime.date | None:
    return _parse_pgn_date_str(value)


_VULTURE_USED = (
    PgnHeaders.from_file,
    PgnHeaders.from_chess_pgn_headers,
    PgnHeaders.extract_all_from_str,
    PgnHeaders.termination,
    _coerce_pgn_datetime_dispatch,
    _coerce_pgn_date_dispatch,
    _coerce_pgn_str_dispatch,
)


def _coerce_pgn_datetime(value: datetime.datetime) -> datetime.date | None:
    coerced = Now.to_utc(value)
    return coerced.date() if coerced else None


def _parse_pgn_date_str(value: str) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, "%Y.%m.%d").replace(tzinfo=datetime.UTC).date()
    except ValueError:
        return None
