from tactix.domain.conversion_payload import (
    build_conversion_payload,
    conversion_payload_from_lists,
)


def test_build_conversion_payload() -> None:
    payload = build_conversion_payload(
        "chesscom",
        games=2,
        inserted_games=1,
        positions=5,
    )
    assert payload == {
        "source": "chesscom",
        "games": 2,
        "inserted_games": 1,
        "positions": 5,
    }


def test_conversion_payload_from_lists() -> None:
    payload = conversion_payload_from_lists(
        "lichess",
        raw_pgns=[{}, {}],
        to_process=[{}],
        positions=[{}, {}, {}],
    )
    assert payload["source"] == "lichess"
    assert payload["games"] == 2
    assert payload["inserted_games"] == 1
    assert payload["positions"] == 3
