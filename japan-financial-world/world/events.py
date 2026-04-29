from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Mapping


_VALID_VISIBILITIES: frozenset[str] = frozenset({"public", "private", "internal"})


def _coerce_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"date must be date or ISO string, got {type(value)!r}")


@dataclass(frozen=True)
class WorldEvent:
    """
    Inter-space message in the v0.3 transport layer.

    A WorldEvent is the only legitimate way one space communicates with
    another. It carries no business logic — only identity, addressing,
    timing, payload, and provenance metadata.

    Fields:
        event_id        Stable unique identifier supplied by the publisher.
        simulation_date ISO date string at the moment of publication.
        source_space    space_id of the publishing space.
        target_spaces   tuple of space_ids; empty tuple means broadcast.
        event_type      domain-neutral string tag (e.g. "rate_change").
        payload         arbitrary mapping of event-specific data.
        visibility      "public", "private", or "internal".
        delay_days      integer days from simulation_date until delivery.
        confidence      float in [0, 1].
        related_ids     tuple of WorldIDs the event references.
    """

    event_id: str
    simulation_date: str
    source_space: str
    target_spaces: tuple[str, ...] = field(default_factory=tuple)
    event_type: str = "generic"
    payload: Mapping[str, Any] = field(default_factory=dict)
    visibility: str = "public"
    delay_days: int = 0
    confidence: float = 1.0
    related_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id:
            raise ValueError("event_id must be a non-empty string")

        if not isinstance(self.simulation_date, str):
            object.__setattr__(self, "simulation_date", _coerce_date(self.simulation_date).isoformat())
        else:
            _coerce_date(self.simulation_date)  # validate format

        if self.visibility not in _VALID_VISIBILITIES:
            raise ValueError(
                f"visibility must be one of {sorted(_VALID_VISIBILITIES)}, got {self.visibility!r}"
            )

        if self.delay_days < 0:
            raise ValueError("delay_days must be non-negative")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        object.__setattr__(self, "target_spaces", tuple(self.target_spaces))
        object.__setattr__(self, "related_ids", tuple(self.related_ids))
        object.__setattr__(self, "payload", dict(self.payload))

    @property
    def delivery_date(self) -> date:
        return _coerce_date(self.simulation_date) + timedelta(days=self.delay_days)

    def is_targeted_at(self, space_id: str) -> bool:
        if self.target_spaces:
            return space_id in self.target_spaces
        # Broadcast (no explicit targets) reaches every space except the source.
        return space_id != self.source_space

    def is_ready(self, current_date: date) -> bool:
        return self.delivery_date <= current_date
