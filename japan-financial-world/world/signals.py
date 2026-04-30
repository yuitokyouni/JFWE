from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping

from world.clock import Clock
from world.ledger import Ledger


_VALID_VISIBILITIES = frozenset(
    {
        "public",
        "private",
        "restricted",
        "leaked",
        "rumor",
        "delayed",
    }
)

_PRIVATE_VISIBILITIES = frozenset({"private", "restricted"})


class SignalError(Exception):
    """Base class for signal-book errors."""


class DuplicateSignalError(SignalError):
    """Raised when a signal_id is added twice."""


class UnknownSignalError(SignalError, KeyError):
    """Raised when a signal_id is not found."""


def _coerce_iso_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError("date must be a date or ISO string")


def _coerce_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError("date must be a date or ISO string")


@dataclass(frozen=True)
class InformationSignal:
    """
    First-class information object in the world.

    A signal represents an observation, claim, report, or rumor about
    a subject. It does not change economic state on its own; receivers
    decide how (or whether) to interpret it. v0.7 stores signals,
    controls who can see them, and lets WorldEvents reference them by
    id — but does not implement narrative interpretation, analyst
    reasoning, or price impact.

    Visibility values:
        public      — visible to anyone whose query reaches the effective_date.
        private     — visible only to ids in metadata["allowed_viewers"].
        restricted  — same as private (separate label for traceability).
        leaked      — visible to anyone (tagged for traceability).
        rumor       — visible to anyone (low credibility implied by
                      convention; not enforced numerically).
        delayed     — visible to anyone, but only from effective_date onward.

    For v0.7, all "anyone-visible" labels (public, leaked, rumor,
    delayed) share the same gating rule: visibility passes whenever the
    observer is *not* excluded by allowed_viewers, and the as_of_date
    has reached the signal's effective_date. Narrative differences
    between leaked / rumor / delayed are bookkeeping tags only.
    """

    signal_id: str
    signal_type: str
    subject_id: str
    source_id: str
    published_date: str
    effective_date: str = ""
    visibility: str = "public"
    credibility: float = 1.0
    confidence: float = 1.0
    payload: Mapping[str, Any] = field(default_factory=dict)
    related_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.signal_id:
            raise ValueError("signal_id is required")
        if not self.signal_type:
            raise ValueError("signal_type is required")
        if not self.subject_id:
            raise ValueError("subject_id is required")
        if not self.source_id:
            raise ValueError("source_id is required")
        if not self.published_date:
            raise ValueError("published_date is required")

        published = _coerce_iso_date(self.published_date)
        effective = self.effective_date or published
        effective = _coerce_iso_date(effective)

        if self.visibility not in _VALID_VISIBILITIES:
            raise ValueError(
                f"visibility must be one of {sorted(_VALID_VISIBILITIES)}; "
                f"got {self.visibility!r}"
            )

        if not 0.0 <= self.credibility <= 1.0:
            raise ValueError("credibility must be between 0 and 1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        object.__setattr__(self, "published_date", published)
        object.__setattr__(self, "effective_date", effective)
        object.__setattr__(self, "payload", dict(self.payload))
        object.__setattr__(self, "related_ids", tuple(self.related_ids))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def is_visible_to(
        self,
        observer_id: str,
        *,
        as_of_date: date | str | None = None,
    ) -> bool:
        if as_of_date is not None:
            as_of = _coerce_date(as_of_date)
            if _coerce_date(self.effective_date) > as_of:
                return False

        if self.visibility in _PRIVATE_VISIBILITIES:
            allowed = self.metadata.get("allowed_viewers", ())
            if observer_id not in allowed:
                return False

        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "subject_id": self.subject_id,
            "source_id": self.source_id,
            "published_date": self.published_date,
            "effective_date": self.effective_date,
            "visibility": self.visibility,
            "credibility": self.credibility,
            "confidence": self.confidence,
            "payload": dict(self.payload),
            "related_ids": list(self.related_ids),
            "metadata": dict(self.metadata),
        }


@dataclass
class SignalBook:
    """
    Storage for InformationSignals.

    Stores facts. Filters by subject / type / source / visibility.
    Records signal_added (and optionally signal_observed) to the ledger.
    Holds no opinion about what any signal means.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _signals: dict[str, InformationSignal] = field(default_factory=dict)

    def add_signal(self, signal: InformationSignal) -> InformationSignal:
        if signal.signal_id in self._signals:
            raise DuplicateSignalError(f"Duplicate signal_id: {signal.signal_id}")
        self._signals[signal.signal_id] = signal

        if self.ledger is not None:
            simulation_date = (
                self.clock.current_date if self.clock is not None else None
            )
            self.ledger.append(
                event_type="signal_added",
                simulation_date=simulation_date,
                object_id=signal.signal_id,
                source=signal.source_id,
                target=signal.subject_id,
                payload={
                    "signal_id": signal.signal_id,
                    "signal_type": signal.signal_type,
                    "subject_id": signal.subject_id,
                    "source_id": signal.source_id,
                    "published_date": signal.published_date,
                    "effective_date": signal.effective_date,
                    "visibility": signal.visibility,
                    "credibility": signal.credibility,
                    "related_ids": list(signal.related_ids),
                },
                space_id="signals",
                confidence=signal.confidence,
                visibility=signal.visibility,
            )
        return signal

    def get_signal(self, signal_id: str) -> InformationSignal:
        try:
            return self._signals[signal_id]
        except KeyError as exc:
            raise UnknownSignalError(f"Signal not found: {signal_id!r}") from exc

    def list_by_subject(self, subject_id: str) -> tuple[InformationSignal, ...]:
        return tuple(
            signal
            for signal in self._signals.values()
            if signal.subject_id == subject_id
        )

    def list_by_type(self, signal_type: str) -> tuple[InformationSignal, ...]:
        return tuple(
            signal
            for signal in self._signals.values()
            if signal.signal_type == signal_type
        )

    def list_by_source(self, source_id: str) -> tuple[InformationSignal, ...]:
        return tuple(
            signal
            for signal in self._signals.values()
            if signal.source_id == source_id
        )

    def list_visible_to(
        self,
        observer_id: str,
        *,
        as_of_date: date | str | None = None,
    ) -> tuple[InformationSignal, ...]:
        effective = as_of_date
        if effective is None and self.clock is not None:
            effective = self.clock.current_date

        return tuple(
            signal
            for signal in self._signals.values()
            if signal.is_visible_to(observer_id, as_of_date=effective)
        )

    def all_signals(self) -> tuple[InformationSignal, ...]:
        return tuple(self._signals.values())

    def mark_observed(
        self,
        signal_id: str,
        observer_id: str,
        *,
        as_of_date: date | str | None = None,
    ) -> InformationSignal:
        signal = self.get_signal(signal_id)

        effective = as_of_date
        if effective is None and self.clock is not None:
            effective = self.clock.current_date

        if not signal.is_visible_to(observer_id, as_of_date=effective):
            raise SignalError(
                f"signal {signal_id!r} is not visible to {observer_id!r}"
            )

        if self.ledger is not None:
            simulation_date = (
                _coerce_iso_date(effective)
                if effective is not None
                else None
            )
            self.ledger.append(
                event_type="signal_observed",
                simulation_date=simulation_date,
                object_id=signal_id,
                source=signal.source_id,
                target=observer_id,
                agent_id=observer_id,
                payload={
                    "signal_id": signal_id,
                    "signal_type": signal.signal_type,
                    "observer_id": observer_id,
                    "subject_id": signal.subject_id,
                    "visibility": signal.visibility,
                },
                space_id="signals",
                confidence=signal.confidence,
                visibility=signal.visibility,
            )
        return signal

    def snapshot(self) -> dict[str, Any]:
        signals = sorted(
            (signal.to_dict() for signal in self._signals.values()),
            key=lambda item: item["signal_id"],
        )
        return {"count": len(signals), "signals": signals}
