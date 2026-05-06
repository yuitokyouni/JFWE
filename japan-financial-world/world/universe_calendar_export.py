"""
v1.26.4 — Universe / calendar readout export section.

Read-only descriptive-only export-side projection of the
v1.26.3 :class:`UniverseCalendarReadout`. The section is
omitted when empty so every pre-v1.26 bundle digest stays
byte-identical.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from world.forbidden_tokens import (
    FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES,
)
from world.universe_calendar_readout import (
    UniverseCalendarReadout,
    build_universe_calendar_readout,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


__all__ = (
    "UNIVERSE_CALENDAR_READOUT_EXPORT_REQUIRED_KEYS",
    "build_universe_calendar_readout_export_section",
    "universe_calendar_readout_to_export_entry",
)


UNIVERSE_CALENDAR_READOUT_EXPORT_REQUIRED_KEYS: frozenset[str] = (
    frozenset(
        {
            "as_of_period_id",
            "active_entity_ids",
            "inactive_entity_ids",
            "lifecycle_event_ids",
            "reporting_calendar_profile_ids",
            "reporting_due_entity_ids",
            "fiscal_year_end_month_counts",
            "reporting_intensity_counts",
            "disclosure_cluster_counts",
            "warnings",
        }
    )
)


def _walk_keys_and_string_values(value: Any):
    if isinstance(value, str):
        yield ("value", value)
        return
    if isinstance(value, Mapping):
        for k, v in value.items():
            if isinstance(k, str):
                yield ("key", k)
            yield from _walk_keys_and_string_values(v)
        return
    if isinstance(value, (list, tuple)):
        for entry in value:
            yield from _walk_keys_and_string_values(entry)


def _scan_export_entry_for_forbidden(
    entry: Mapping[str, Any],
    *,
    field_name: str = "universe_calendar_readout",
) -> None:
    for kind, item in _walk_keys_and_string_values(entry):
        if (
            kind == "key"
            and item in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} entry contains forbidden "
                f"key {item!r}"
            )
        if (
            kind == "value"
            and item in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} entry contains forbidden "
                f"whole-string value {item!r}"
            )


def universe_calendar_readout_to_export_entry(
    readout: UniverseCalendarReadout,
) -> dict[str, Any]:
    if not isinstance(readout, UniverseCalendarReadout):
        raise TypeError(
            "expects a UniverseCalendarReadout"
        )
    entry: dict[str, Any] = {
        "as_of_period_id": readout.as_of_period_id,
        "active_entity_ids": list(
            readout.active_entity_ids
        ),
        "inactive_entity_ids": list(
            readout.inactive_entity_ids
        ),
        "lifecycle_event_ids": list(
            readout.lifecycle_event_ids
        ),
        "reporting_calendar_profile_ids": list(
            readout.reporting_calendar_profile_ids
        ),
        "reporting_due_entity_ids": list(
            readout.reporting_due_entity_ids
        ),
        "fiscal_year_end_month_counts": [
            [label, count]
            for label, count in (
                readout.fiscal_year_end_month_counts
            )
        ],
        "reporting_intensity_counts": [
            [label, count]
            for label, count in (
                readout.reporting_intensity_counts
            )
        ],
        "disclosure_cluster_counts": [
            [label, count]
            for label, count in (
                readout.disclosure_cluster_counts
            )
        ],
        "warnings": list(readout.warnings),
    }
    _scan_export_entry_for_forbidden(entry)
    return entry


def build_universe_calendar_readout_export_section(
    kernel: "WorldKernel",
    *,
    as_of_period_id: str,
) -> tuple[dict[str, Any], ...]:
    universe_book = getattr(kernel, "universe_events", None)
    calendar_book = getattr(
        kernel, "reporting_calendars", None
    )
    has_events = (
        universe_book is not None
        and len(universe_book.list_events()) > 0
    )
    has_calendars = (
        calendar_book is not None
        and len(calendar_book.list_profiles()) > 0
    )
    if not (has_events or has_calendars):
        return ()
    readout = build_universe_calendar_readout(
        kernel, as_of_period_id=as_of_period_id
    )
    return (
        universe_calendar_readout_to_export_entry(readout),
    )
