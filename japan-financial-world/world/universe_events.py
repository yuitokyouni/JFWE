"""
v1.26.1 — Entity lifecycle (UniverseEvent) storage.

Generic, country-neutral storage-only foundation for the
v1.26 entity lifecycle substrate per
[`docs/v1_26_entity_lifecycle_reporting_calendar_foundation.md`](../docs/v1_26_entity_lifecycle_reporting_calendar_foundation.md)
§3 / §6.

v1.26.1 ships one immutable frozen dataclass
(:class:`UniverseEventRecord`), one append-only
:class:`UniverseEventBook`, and the v1.26.0 closed-set
``UNIVERSE_EVENT_TYPE_LABELS``. Read-only readout
(v1.26.3), export (v1.26.4), and freeze (v1.26.last) are
strictly later sub-milestones.

Critical design constraints carried verbatim from the
v1.26.0 design pin (binding):

- **Generic and country-neutral.** No Japan
  calibration, no real company name, no real-data
  adapter. The :data:`world.forbidden_tokens.FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES`
  composed set hard-forbids EDINET / TDnet / J-Quants
  / FSA-filing tokens, plus all earnings-surprise /
  event-study / portfolio-weight tokens, plus the
  full v1.18.0–v1.25.0 inherited boundary.
- **Append-only.** No event ever mutates a prior
  event; revisions append a new event citing the
  prior one.
- **Read-only with respect to the world.** Adding an
  event does **not** delete or modify the cited
  entity in any other kernel book; the only
  "deactivation" surface is the v1.26.3 readout's
  active-set computation, a pure projection.
- **Empty by default on the kernel.** An empty book
  emits no ledger record, so every existing fixed-
  universe fixture continues to behave as a static
  universe and every v1.21.last canonical
  ``living_world_digest`` stays byte-identical.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES,
)
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set vocabularies (binding for v1.26.1)
# ---------------------------------------------------------------------------


UNIVERSE_EVENT_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "entity_listed",
        "entity_delisted",
        "entity_merged",
        "entity_renamed",
        "entity_split",
        "entity_status_changed",
        "unknown",
    }
)


STATUS_LABELS: frozenset[str] = frozenset(
    {
        "draft",
        "active",
        "superseded",
        "archived",
        "unknown",
    }
)


VISIBILITY_LABELS: frozenset[str] = frozenset(
    {
        "public",
        "restricted",
        "internal",
        "private",
        "unknown",
    }
)


# ---------------------------------------------------------------------------
# Default boundary flags (binding per v1.26.0 §5.1)
# ---------------------------------------------------------------------------


_DEFAULT_BOUNDARY_FLAGS_TUPLE: tuple[tuple[str, bool], ...] = (
    ("no_actor_decision", True),
    ("no_llm_execution", True),
    ("no_price_formation", True),
    ("no_trading", True),
    ("no_financing_execution", True),
    ("no_investment_advice", True),
    ("synthetic_only", True),
    ("no_aggregate_stress_result", True),
    ("no_interaction_inference", True),
    ("no_field_value_claim", True),
    ("no_field_magnitude_claim", True),
    ("descriptive_only", True),
    ("no_real_data_ingestion", True),
    ("no_japan_calibration", True),
    ("no_real_company_name", True),
    ("no_market_effect_inference", True),
    ("no_event_to_price_mapping", True),
    ("no_forecast_from_calendar", True),
)


def _default_boundary_flags() -> dict[str, bool]:
    return dict(_DEFAULT_BOUNDARY_FLAGS_TUPLE)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class UniverseEventError(Exception):
    """Base class for v1.26.1 UniverseEvent storage errors."""


class DuplicateUniverseEventError(UniverseEventError):
    """Raised when a ``universe_event_id`` is added twice."""


class UnknownUniverseEventError(UniverseEventError, KeyError):
    """Raised when a ``universe_event_id`` is not found."""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_required_string(
    value: Any, *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )
    return value


def _validate_label(
    value: Any, allowed: frozenset[str], *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)!r}; "
            f"got {value!r}"
        )
    return value


def _validate_string_tuple(
    value: Iterable[str],
    *,
    field_name: str,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    normalised = tuple(value)
    if not allow_empty and not normalised:
        raise ValueError(
            f"{field_name} must be non-empty"
        )
    for entry in normalised:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty "
                f"strings; got {entry!r}"
            )
    return normalised


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key "
                f"{key!r} (v1.26.0 universe / calendar "
                "boundary)"
            )


def _scan_label_value_for_forbidden_tokens(
    value: str, *, field_name: str
) -> None:
    if value in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES:
        raise ValueError(
            f"{field_name} value {value!r} is in the "
            "v1.26.0 universe / calendar forbidden-name "
            "set"
        )


# ---------------------------------------------------------------------------
# UniverseEventRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UniverseEventRecord:
    """Immutable, append-only record of one entity-
    lifecycle event."""

    universe_event_id: str
    effective_period_id: str
    event_type_label: str
    affected_entity_ids: tuple[str, ...]
    predecessor_entity_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    successor_entity_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    citation_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    status: str = "active"
    visibility: str = "internal"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "universe_event_id",
        "effective_period_id",
        "event_type_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("event_type_label", UNIVERSE_EVENT_TYPE_LABELS),
        ("status",           STATUS_LABELS),
        ("visibility",       VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the "
                    "v1.26.0 universe / calendar forbidden "
                    "field-name set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, name), allowed, field_name=name
            )
        for name, _ in self.LABEL_FIELDS:
            _scan_label_value_for_forbidden_tokens(
                getattr(self, name), field_name=name
            )
        # affected_entity_ids — non-empty
        object.__setattr__(
            self,
            "affected_entity_ids",
            _validate_string_tuple(
                self.affected_entity_ids,
                field_name="affected_entity_ids",
                allow_empty=False,
            ),
        )
        # predecessor / successor / citation — may be empty
        for name in (
            "predecessor_entity_ids",
            "successor_entity_ids",
            "citation_ids",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string_tuple(
                    getattr(self, name),
                    field_name=name,
                ),
            )
        # boundary_flags — defaults non-removable
        bf = dict(self.boundary_flags)
        for key, val in bf.items():
            if not isinstance(key, str) or not key:
                raise ValueError(
                    "boundary_flags keys must be non-empty "
                    "strings"
                )
            if not isinstance(val, bool):
                raise ValueError(
                    f"boundary_flags[{key!r}] must be bool"
                )
        for default_key, default_val in (
            _DEFAULT_BOUNDARY_FLAGS_TUPLE
        ):
            if (
                default_key in bf
                and bf[default_key] != default_val
            ):
                raise ValueError(
                    f"boundary_flags[{default_key!r}] is "
                    "a v1.26.0 default; cannot be "
                    "overridden"
                )
            bf.setdefault(default_key, default_val)
        _scan_for_forbidden_keys(
            bf, field_name="boundary_flags"
        )
        object.__setattr__(self, "boundary_flags", bf)
        # metadata
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe_event_id": self.universe_event_id,
            "effective_period_id": self.effective_period_id,
            "event_type_label": self.event_type_label,
            "affected_entity_ids": list(
                self.affected_entity_ids
            ),
            "predecessor_entity_ids": list(
                self.predecessor_entity_ids
            ),
            "successor_entity_ids": list(
                self.successor_entity_ids
            ),
            "citation_ids": list(self.citation_ids),
            "status": self.status,
            "visibility": self.visibility,
            "boundary_flags": dict(self.boundary_flags),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# UniverseEventBook
# ---------------------------------------------------------------------------


@dataclass
class UniverseEventBook:
    """Append-only storage for v1.26.1
    :class:`UniverseEventRecord` instances."""

    ledger: Ledger | None = None
    clock: Clock | None = None
    _events: dict[str, UniverseEventRecord] = field(
        default_factory=dict
    )

    def _now(self) -> datetime:
        if self.clock is not None:
            try:
                return self.clock.current_datetime()
            except Exception:
                pass
        return datetime.now(timezone.utc)

    def add_event(
        self,
        event: UniverseEventRecord,
        *,
        simulation_date: Any = None,
    ) -> UniverseEventRecord:
        if not isinstance(event, UniverseEventRecord):
            raise TypeError(
                "event must be a UniverseEventRecord"
            )
        if event.universe_event_id in self._events:
            raise DuplicateUniverseEventError(
                "Duplicate universe_event_id: "
                f"{event.universe_event_id!r}"
            )
        self._events[event.universe_event_id] = event
        if self.ledger is not None:
            payload: dict[str, Any] = {
                "universe_event_id": event.universe_event_id,
                "effective_period_id": (
                    event.effective_period_id
                ),
                "event_type_label": event.event_type_label,
                "affected_entity_ids": list(
                    event.affected_entity_ids
                ),
                "predecessor_entity_ids": list(
                    event.predecessor_entity_ids
                ),
                "successor_entity_ids": list(
                    event.successor_entity_ids
                ),
                "citation_ids": list(event.citation_ids),
                "status": event.status,
                "visibility": event.visibility,
                "boundary_flags": dict(event.boundary_flags),
            }
            _scan_for_forbidden_keys(
                payload, field_name="ledger payload"
            )
            sim_date: Any = (
                simulation_date
                if simulation_date is not None
                else self._now()
            )
            self.ledger.append(
                event_type="universe_event_recorded",
                simulation_date=sim_date,
                object_id=event.universe_event_id,
                source=event.event_type_label,
                payload=payload,
                space_id="universe_events",
                visibility=event.visibility,
            )
        return event

    def get_event(
        self, universe_event_id: str
    ) -> UniverseEventRecord:
        try:
            return self._events[universe_event_id]
        except KeyError as exc:
            raise UnknownUniverseEventError(
                f"universe_event not found: "
                f"{universe_event_id!r}"
            ) from exc

    def list_events(
        self,
    ) -> tuple[UniverseEventRecord, ...]:
        return tuple(self._events.values())

    def list_by_event_type(
        self, event_type_label: str
    ) -> tuple[UniverseEventRecord, ...]:
        return tuple(
            e
            for e in self._events.values()
            if e.event_type_label == event_type_label
        )

    def list_by_entity(
        self, entity_id: str
    ) -> tuple[UniverseEventRecord, ...]:
        """Return every event that cites ``entity_id`` in
        affected_entity_ids OR predecessor_entity_ids OR
        successor_entity_ids."""
        return tuple(
            e
            for e in self._events.values()
            if (
                entity_id in e.affected_entity_ids
                or entity_id in e.predecessor_entity_ids
                or entity_id in e.successor_entity_ids
            )
        )

    def list_by_effective_period(
        self, effective_period_id: str
    ) -> tuple[UniverseEventRecord, ...]:
        return tuple(
            e
            for e in self._events.values()
            if e.effective_period_id == effective_period_id
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "universe_events": [
                e.to_dict()
                for e in self._events.values()
            ],
        }


__all__ = [
    "DuplicateUniverseEventError",
    "STATUS_LABELS",
    "UNIVERSE_EVENT_TYPE_LABELS",
    "UniverseEventBook",
    "UniverseEventError",
    "UniverseEventRecord",
    "UnknownUniverseEventError",
    "VISIBILITY_LABELS",
]
