from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from world.events import WorldEvent, _coerce_date


class EventBusError(Exception):
    """Base class for event bus errors."""


class DuplicateEventError(EventBusError):
    """Raised when publishing an event whose event_id is already in the bus."""


@dataclass
class EventBus:
    """
    Date-aware delivery channel for inter-space events.

    Delivery semantics:
        Events published on date D are visible to other spaces only from
        date D + 1 onward (subject to delay_days). This rules out same-tick
        delivery and makes inter-space communication independent of the
        scheduler's task execution order within a tick.

        An event is delivered to a space when:
            current_date > publication_date  (strict)
            AND current_date >= delivery_date  (sim_date + delay_days)
            AND event.is_targeted_at(space_id) is true
            AND (event_id, space_id) has not been delivered before.

    Responsibility:
        - accept events via publish()
        - hand the right events to a space via collect_for_space()
        - never deliver the same event to the same space twice
        - never deliver an event before its delivery_date
        - never deliver an event in the same tick it was published
        - track which events are still pending vs already delivered

    Non-responsibility:
        - no business logic
        - no inspection of payload contents
        - no decision about who should react to what
        - no mutation of event payloads
        - no cross-space side effects beyond delivery
    """

    _events: list[WorldEvent] = field(default_factory=list)
    _event_ids: set[str] = field(default_factory=set)
    _publication_dates: dict[str, date] = field(default_factory=dict)
    _delivered_pairs: set[tuple[str, str]] = field(default_factory=set)

    def publish(
        self,
        event: WorldEvent,
        *,
        on_date: date | str | None = None,
    ) -> WorldEvent:
        if event.event_id in self._event_ids:
            raise DuplicateEventError(f"Duplicate event_id: {event.event_id}")

        if on_date is None:
            publication_date = _coerce_date(event.simulation_date)
        else:
            publication_date = _coerce_date(on_date)

        self._event_ids.add(event.event_id)
        self._publication_dates[event.event_id] = publication_date
        self._events.append(event)
        return event

    def collect_for_space(
        self,
        space_id: str,
        current_date: date,
    ) -> tuple[WorldEvent, ...]:
        delivered: list[WorldEvent] = []
        for event in self._events:
            key = (event.event_id, space_id)
            if key in self._delivered_pairs:
                continue
            if not event.is_targeted_at(space_id):
                continue
            if current_date <= self._publication_dates[event.event_id]:
                continue
            if not event.is_ready(current_date):
                continue
            delivered.append(event)
            self._delivered_pairs.add(key)
        return tuple(delivered)

    def pending_events(self) -> tuple[WorldEvent, ...]:
        delivered_event_ids = {pair[0] for pair in self._delivered_pairs}
        return tuple(
            event for event in self._events if event.event_id not in delivered_event_ids
        )

    def delivered_events(self) -> tuple[WorldEvent, ...]:
        delivered_event_ids = {pair[0] for pair in self._delivered_pairs}
        seen: set[str] = set()
        result: list[WorldEvent] = []
        for event in self._events:
            if event.event_id in delivered_event_ids and event.event_id not in seen:
                result.append(event)
                seen.add(event.event_id)
        return tuple(result)

    def all_events(self) -> tuple[WorldEvent, ...]:
        return tuple(self._events)
