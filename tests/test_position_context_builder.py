import chess
import chess.pgn

from tactix.PgnContext import PgnContext
from tactix.position_context_builder import (
    DEFAULT_POSITION_CONTEXT_BUILDER,
    PositionContextInputs,
)


def _build_fixture_context() -> tuple[PgnContext, chess.pgn.Game, chess.Board, chess.pgn.ChildNode]:
    pgn = """[Event \"Test\"]
[Site \"https://lichess.org/abc\"]
[White \"User\"]
[Black \"Opp\"]
[Result \"*\"]

1. e4 { %clk 0:10:00 } e5 *
"""
    ctx = PgnContext(pgn=pgn, user="User", source="lichess", game_id="game-1")
    game = ctx.game
    assert game is not None
    board = game.board()
    node = game.variations[0]
    return ctx, game, board, node


def test_position_context_builder_builds_expected_payload() -> None:
    builder = DEFAULT_POSITION_CONTEXT_BUILDER
    ctx, game, board, node = _build_fixture_context()
    move = node.move
    assert move is not None
    side_to_move = builder.side_from_turn(board.turn)

    payload = builder.build(
        PositionContextInputs(
            ctx=ctx,
            game=game,
            board=board,
            node=node,
            move=move,
            side_to_move=side_to_move,
        )
    )

    assert payload["game_id"] == "game-1"
    assert payload["user"] == "user"
    assert payload["source"] == "lichess"
    assert payload["fen"] == board.fen()
    assert payload["ply"] == 0
    assert payload["move_number"] == 1
    assert payload["side_to_move"] == "white"
    assert payload["user_to_move"] is True
    assert payload["uci"] == "e2e4"
    assert payload["san"] == "e4"
    assert payload["clock_seconds"] == 600
    assert payload["is_legal"] is True


def test_position_context_builder_rules() -> None:
    builder = DEFAULT_POSITION_CONTEXT_BUILDER
    board = chess.Board()

    assert builder.get_user_color("user", "User") == chess.WHITE
    assert builder.side_from_turn(chess.BLACK) == "black"
    assert builder.should_skip_for_turn(board, chess.BLACK) is True
    assert builder.should_skip_for_turn(board, chess.WHITE) is False
    assert builder.should_skip_for_side("white", "black") is True
    assert builder.should_skip_for_side("white", None) is False

    illegal_move = chess.Move.from_uci("e2e5")
    assert builder.is_illegal_move(board, illegal_move) is True
