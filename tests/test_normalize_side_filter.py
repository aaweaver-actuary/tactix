from tactix._normalize_side_filter import _normalize_side_filter


def test_normalize_side_filter_valid() -> None:
    assert _normalize_side_filter("White") == "white"
    assert _normalize_side_filter("black") == "black"
    assert _normalize_side_filter(None) is None


def test_normalize_side_filter_invalid() -> None:
    assert _normalize_side_filter("green") is None
