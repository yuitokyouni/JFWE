"""
v1.27.2 — Strategic relationship readout export section.

Read-only descriptive-only export-side projection of the
v1.27.2 :class:`StrategicRelationshipReadout`. The section
is omitted when empty so every pre-v1.27 bundle digest stays
byte-identical.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from world.forbidden_tokens import (
    FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES,
)
from world.strategic_relationship_readout import (
    StrategicRelationshipReadout,
    build_strategic_relationship_readout,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


__all__ = (
    "STRATEGIC_RELATIONSHIP_READOUT_EXPORT_REQUIRED_KEYS",
    "build_strategic_relationship_readout_export_section",
    "strategic_relationship_readout_to_export_entry",
)


STRATEGIC_RELATIONSHIP_READOUT_EXPORT_REQUIRED_KEYS: frozenset[
    str
] = frozenset(
    {
        "as_of_period_id",
        "relationship_ids",
        "entity_ids",
        "relationship_type_counts",
        "direction_counts",
        "reciprocal_relationship_count",
        "active_relationship_count",
        "evidence_ref_ids",
        "warnings",
    }
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
    field_name: str = "strategic_relationship_readout",
) -> None:
    for kind, item in _walk_keys_and_string_values(entry):
        if (
            kind == "key"
            and item
            in FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} entry contains forbidden "
                f"key {item!r}"
            )
        if (
            kind == "value"
            and item
            in FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} entry contains forbidden "
                f"whole-string value {item!r}"
            )


def strategic_relationship_readout_to_export_entry(
    readout: StrategicRelationshipReadout,
) -> dict[str, Any]:
    if not isinstance(
        readout, StrategicRelationshipReadout
    ):
        raise TypeError(
            "expects a StrategicRelationshipReadout"
        )
    entry: dict[str, Any] = {
        "as_of_period_id": readout.as_of_period_id,
        "relationship_ids": list(readout.relationship_ids),
        "entity_ids": list(readout.entity_ids),
        "relationship_type_counts": [
            [label, count]
            for label, count in (
                readout.relationship_type_counts
            )
        ],
        "direction_counts": [
            [label, count]
            for label, count in readout.direction_counts
        ],
        "reciprocal_relationship_count": (
            readout.reciprocal_relationship_count
        ),
        "active_relationship_count": (
            readout.active_relationship_count
        ),
        "evidence_ref_ids": list(readout.evidence_ref_ids),
        "warnings": list(readout.warnings),
    }
    _scan_export_entry_for_forbidden(entry)
    return entry


def build_strategic_relationship_readout_export_section(
    kernel: "WorldKernel",
    *,
    as_of_period_id: str,
) -> tuple[dict[str, Any], ...]:
    book = getattr(kernel, "strategic_relationships", None)
    if book is None or len(book.list_relationships()) == 0:
        return ()
    readout = build_strategic_relationship_readout(
        kernel, as_of_period_id=as_of_period_id
    )
    return (
        strategic_relationship_readout_to_export_entry(
            readout
        ),
    )
