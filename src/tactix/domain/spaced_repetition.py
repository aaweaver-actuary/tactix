"""Spaced repetition scheduler adapters."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

FsrsCard: type | None = None
FsrsRating: type | None = None
FsrsScheduler: type | None = None

try:
    from fsrs import Card as _FsrsCard
    from fsrs import Rating as _FsrsRating
    from fsrs import Scheduler as _FsrsScheduler
except ImportError:  # pragma: no cover - optional dependency
    pass
else:
    FsrsCard = _FsrsCard
    FsrsRating = _FsrsRating
    FsrsScheduler = _FsrsScheduler

SM2_FIRST_REP = 1
SM2_SECOND_REP = 2


@dataclass(frozen=True)
class ScheduleState:
    """Represents the scheduling state for a practice item."""

    scheduler: str
    due_at: datetime
    interval_days: float
    ease: float | None
    state_payload: dict[str, object]


class SchedulerAdapter(Protocol):
    """Small adapter interface for spaced repetition schedulers."""

    name: str

    def init_state(self, now: datetime) -> ScheduleState:
        """Return the initial schedule state for a new item."""
        raise NotImplementedError

    def review(
        self,
        state_payload: dict[str, object],
        correct: bool,
        reviewed_at: datetime,
    ) -> ScheduleState:
        """Return the updated schedule state after a review."""
        raise NotImplementedError


class Sm2SchedulerAdapter:
    """Minimal SM-2 scheduler fallback."""

    name = "sm2"

    def init_state(self, now: datetime) -> ScheduleState:
        return ScheduleState(
            scheduler=self.name,
            due_at=now,
            interval_days=0.0,
            ease=2.5,
            state_payload={"interval_days": 0.0, "ease": 2.5, "reps": 0},
        )

    def review(
        self,
        state_payload: dict[str, object],
        correct: bool,
        reviewed_at: datetime,
    ) -> ScheduleState:
        interval, ease, reps = self._resolve_sm2_state(state_payload)
        if correct:
            interval, ease, reps = self._apply_sm2_correct(interval, ease, reps)
        else:
            interval, ease, reps = self._apply_sm2_incorrect(interval, ease, reps)
        return self._build_sm2_state(interval, ease, reps, reviewed_at)

    def _resolve_sm2_state(self, payload: dict[str, object]) -> tuple[float, float, int]:
        interval = float(payload.get("interval_days", 0.0) or 0.0)
        ease = float(payload.get("ease", 2.5) or 2.5)
        reps = int(payload.get("reps", 0) or 0)
        return interval, ease, reps

    def _apply_sm2_correct(
        self,
        interval: float,
        ease: float,
        reps: int,
    ) -> tuple[float, float, int]:
        reps += 1
        interval = self._next_sm2_interval(interval, ease, reps)
        ease = max(1.3, ease + 0.1)
        return interval, ease, reps

    def _apply_sm2_incorrect(
        self,
        _interval: float,
        ease: float,
        _reps: int,
    ) -> tuple[float, float, int]:
        return 0.0, max(1.3, ease - 0.2), 0

    def _next_sm2_interval(self, interval: float, ease: float, reps: int) -> float:
        if reps == SM2_FIRST_REP:
            return 1.0
        if reps == SM2_SECOND_REP:
            return 6.0
        return max(1.0, round(interval * ease))

    def _build_sm2_state(
        self,
        interval: float,
        ease: float,
        reps: int,
        reviewed_at: datetime,
    ) -> ScheduleState:
        due_at = reviewed_at + timedelta(days=interval)
        return ScheduleState(
            scheduler=self.name,
            due_at=due_at,
            interval_days=interval,
            ease=ease,
            state_payload={"interval_days": interval, "ease": ease, "reps": reps},
        )


class FsrsSchedulerAdapter:
    """FSRS scheduler adapter backed by the fsrs package."""

    name = "fsrs"

    def __init__(self) -> None:
        if FsrsCard is None or FsrsRating is None or FsrsScheduler is None:
            raise ImportError("fsrs is not installed")

        self._Card: Any = FsrsCard
        self._Rating: Any = FsrsRating
        self._scheduler: Any = FsrsScheduler()

    def init_state(self, now: datetime) -> ScheduleState:
        card = self._Card()
        if hasattr(card, "due"):
            card.due = now
        return _state_from_fsrs_card(self.name, card)

    def review(
        self,
        state_payload: dict[str, object],
        correct: bool,
        reviewed_at: datetime,
    ) -> ScheduleState:
        card = _card_from_state(self._Card, state_payload, reviewed_at)
        rating = self._resolve_rating(correct)
        card = self._apply_review(card, rating, reviewed_at)
        return _state_from_fsrs_card(self.name, card)

    def _resolve_rating(self, correct: bool) -> Any:
        return self._Rating.Good if correct else self._Rating.Again

    def _apply_review(self, card: Any, rating: Any, reviewed_at: datetime) -> Any:
        review_card = getattr(self._scheduler, "review_card", None)
        if review_card is None:
            return self._repeat_review(card, rating, reviewed_at)
        return self._review_with_card(review_card, card, rating, reviewed_at)

    def _repeat_review(self, card: Any, rating: Any, reviewed_at: datetime) -> Any:
        repeat = getattr(self._scheduler, "repeat", None)  # pylint: disable=no-member
        if repeat is None:
            raise AttributeError("FSRS scheduler missing repeat")
        scheduling_cards = repeat(card, reviewed_at)  # pylint: disable=not-callable
        return scheduling_cards[rating].card

    def _review_with_card(
        self,
        review_card: Any,
        card: Any,
        rating: Any,
        reviewed_at: datetime,
    ) -> Any:
        try:
            card, _ = review_card(card, rating, reviewed_at)
        except TypeError:
            card, _ = review_card(card, rating)
        return card


def get_practice_scheduler(preferred: str | None = None) -> SchedulerAdapter:
    """Return an FSRS scheduler when available, otherwise fall back to SM-2."""

    if preferred == FsrsSchedulerAdapter.name:
        try:
            return FsrsSchedulerAdapter()
        except ImportError:
            return Sm2SchedulerAdapter()
    if preferred == Sm2SchedulerAdapter.name:
        return Sm2SchedulerAdapter()
    try:
        return FsrsSchedulerAdapter()
    except ImportError:
        return Sm2SchedulerAdapter()


def encode_state_payload(payload: dict[str, object] | None) -> str:
    """Serialize a scheduler payload into JSON."""

    return json.dumps(payload or {}, separators=(",", ":"), default=str)


def decode_state_payload(raw: str | None) -> dict[str, object]:
    """Deserialize a scheduler payload from JSON."""

    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def end_of_day(now: datetime) -> datetime:
    """Return the end of day timestamp in UTC for the given datetime."""

    utc_now = now.astimezone(UTC)
    next_day = utc_now.date() + timedelta(days=1)
    return datetime.combine(next_day, datetime.min.time(), tzinfo=UTC) - timedelta(seconds=1)


def _state_from_fsrs_card(scheduler: str, card: Any) -> ScheduleState:
    state_payload = _serialize_fsrs_card(card)
    due_at = state_payload.get("due_at")
    resolved_due_at = due_at if isinstance(due_at, datetime) else datetime.now(UTC)
    interval_days = float(state_payload.get("scheduled_days", 0.0) or 0.0)
    ease = state_payload.get("difficulty")
    return ScheduleState(
        scheduler=scheduler,
        due_at=resolved_due_at,
        interval_days=interval_days,
        ease=float(ease) if ease is not None else None,
        state_payload=state_payload,
    )


def _serialize_fsrs_card(card: Any) -> dict[str, object]:
    payload: dict[str, object] = {}
    for field in (
        "due",
        "stability",
        "difficulty",
        "elapsed_days",
        "scheduled_days",
        "reps",
        "lapses",
        "state",
        "last_review",
    ):
        value = getattr(card, field, None)
        if isinstance(value, datetime):
            payload[f"{field}_at"] = value.astimezone(UTC)
        else:
            payload[field] = value
    due_at = getattr(card, "due", None)
    if isinstance(due_at, datetime):
        payload["due_at"] = due_at.astimezone(UTC)
    return payload


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _card_from_state(card_cls: Any, payload: dict[str, object], now: datetime) -> Any:
    card = card_cls()
    due_at = _parse_datetime(payload.get("due_at")) or now
    card.due = due_at
    for field in (
        "stability",
        "difficulty",
        "elapsed_days",
        "scheduled_days",
        "reps",
        "lapses",
        "state",
    ):
        value = payload.get(field)
        if value is not None:
            setattr(card, field, value)
    last_review_at = _parse_datetime(payload.get("last_review_at"))
    if last_review_at is not None:
        attr = "last_" + "review"
        setattr(card, attr, last_review_at)
    return card


__all__ = [
    "FsrsSchedulerAdapter",
    "ScheduleState",
    "SchedulerAdapter",
    "Sm2SchedulerAdapter",
    "decode_state_payload",
    "encode_state_payload",
    "end_of_day",
    "get_practice_scheduler",
]
