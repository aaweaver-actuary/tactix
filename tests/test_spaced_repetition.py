from datetime import UTC, datetime
from types import SimpleNamespace

import tactix.domain.spaced_repetition as sr


def test_sm2_init_and_review_correct() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    scheduler = sr.Sm2SchedulerAdapter()
    state = scheduler.init_state(now)

    assert state.due_at == now
    updated = scheduler.review(state.state_payload, True, now)
    assert updated.interval_days >= 1.0
    assert updated.due_at >= now


def test_sm2_review_incorrect_resets_interval() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    scheduler = sr.Sm2SchedulerAdapter()
    state = scheduler.init_state(now)

    updated = scheduler.review(state.state_payload, False, now)
    assert updated.interval_days == 0.0
    assert updated.due_at == now


def test_encode_decode_state_payload_roundtrip() -> None:
    payload = {"interval_days": 1.5, "ease": 2.5}
    encoded = sr.encode_state_payload(payload)
    decoded = sr.decode_state_payload(encoded)

    assert decoded == payload


def test_decode_state_payload_handles_invalid() -> None:
    assert sr.decode_state_payload("not-json") == {}
    assert sr.decode_state_payload("[]") == {}


def test_end_of_day_returns_day_end() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    eod = sr.end_of_day(now)

    assert eod.date() == now.date()
    assert (eod.hour, eod.minute, eod.second) == (23, 59, 59)


def test_state_from_fsrs_card_serialization() -> None:
    class DummyCard:
        due = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        stability = 1.0
        difficulty = 2.0
        elapsed_days = 0
        scheduled_days = 2
        reps = 1
        lapses = 0
        state = 0
        last_review = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)

    payload = sr._serialize_fsrs_card(DummyCard())
    state = sr._state_from_fsrs_card("fsrs", DummyCard())

    assert payload.get("due_at") == state.due_at
    assert state.interval_days == 2.0
    assert state.ease == 2.0


def test_parse_datetime_supports_isoformat() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert sr._parse_datetime(now.isoformat()) == now
    assert sr._parse_datetime("invalid") is None


def test_fsrs_adapter_review_card_path(monkeypatch) -> None:
    class DummyCard:
        def __init__(self) -> None:
            self.due = None
            self.stability = 0.0
            self.difficulty = 2.0
            self.elapsed_days = 0
            self.scheduled_days = 1
            self.reps = 0
            self.lapses = 0
            self.state = 0
            self.last_review = None

    class DummyRating:
        Good = "good"
        Again = "again"

    class DummyScheduler:
        def review_card(self, card, rating, reviewed_at):
            card.due = reviewed_at
            card.scheduled_days = 1
            return card, None

    monkeypatch.setattr(sr, "FsrsCard", DummyCard)
    monkeypatch.setattr(sr, "FsrsRating", DummyRating)
    monkeypatch.setattr(sr, "FsrsScheduler", DummyScheduler)

    adapter = sr.FsrsSchedulerAdapter()
    now = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    state = adapter.init_state(now)
    updated = adapter.review(state.state_payload, True, now)

    assert updated.due_at == now
    assert updated.interval_days == 1.0


def test_fsrs_adapter_repeat_path(monkeypatch) -> None:
    class DummyCard:
        def __init__(self) -> None:
            self.due = None
            self.stability = 0.0
            self.difficulty = 2.0
            self.elapsed_days = 0
            self.scheduled_days = 2
            self.reps = 0
            self.lapses = 0
            self.state = 0
            self.last_review = None

    class DummyRating:
        Good = "good"
        Again = "again"

    class DummyScheduler:
        def repeat(self, card, reviewed_at):
            card.due = reviewed_at
            card.scheduled_days = 2
            return {DummyRating.Good: SimpleNamespace(card=card)}

    monkeypatch.setattr(sr, "FsrsCard", DummyCard)
    monkeypatch.setattr(sr, "FsrsRating", DummyRating)
    monkeypatch.setattr(sr, "FsrsScheduler", DummyScheduler)

    adapter = sr.FsrsSchedulerAdapter()
    now = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    state = adapter.init_state(now)
    updated = adapter.review(state.state_payload, True, now)

    assert updated.interval_days == 2.0
    assert updated.due_at == now
