"""
v1.27.2 — Strategic relationship read-only readout.

Read-only multiset projection over the kernel's
:class:`world.strategic_relationships.StrategicRelationshipBook`
+ a caller-supplied ``as_of_period_id``.

Per the v1.27.0 design pin §4.1:

- A relationship is *active at* ``as_of_period_id`` iff
  its ``effective_from_period_id <= as_of_period_id`` and
  its ``effective_to_period_id`` is ``None`` or
  ``>= as_of_period_id`` (lexicographic comparison; the
  storage layer already enforces from <= to).
- Counts only — no centrality score, no systemic-
  importance score, no risk score, no rank, no
  percentile.
- ``reciprocal_relationship_count`` counts how many
  active records carry ``direction_label == "reciprocal"``.
- ``relationship_type_counts`` and ``direction_counts``
  are deterministic count pairs ordered by the closed-set
  insertion order in the active records (first-seen).
- Read-only: never emits a ledger record, never mutates
  any source-of-truth book, never calls a v1.18.2 /
  v1.21.x apply or intent helper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Iterable, Mapping

from world.forbidden_tokens import (
    FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES,
)
from world.strategic_relationships import (
    StrategicRelationshipRecord,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


__all__ = (
    "StrategicRelationshipReadout",
    "build_strategic_relationship_readout",
)


def _validate_required_string(
    value: Any, *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )
    return value


def _validate_string_tuple(
    value: Iterable[str], *, field_name: str
) -> tuple[str, ...]:
    normalised = tuple(value)
    for entry in normalised:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty"
            )
    return normalised


def _validate_count_pairs(
    value: Iterable[tuple[str, int]],
    *,
    field_name: str,
) -> tuple[tuple[str, int], ...]:
    normalised = tuple(value)
    for entry in normalised:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise ValueError(
                f"{field_name} entries must be (str, int)"
            )
        label, count = entry
        if not isinstance(label, str) or not label:
            raise ValueError(
                f"{field_name} label must be non-empty"
            )
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
        ):
            raise ValueError(
                f"{field_name} count must be int"
            )
        if count < 0:
            raise ValueError(
                f"{field_name} count must be >= 0"
            )
    return normalised


def _validate_non_neg_int(
    value: Any, *, field_name: str
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be int")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if (
            key
            in FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} contains forbidden key "
                f"{key!r}"
            )


@dataclass(frozen=True)
class StrategicRelationshipReadout:
    """Immutable, read-only strategic-relationship
    multiset projection."""

    readout_id: str
    as_of_period_id: str
    relationship_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    relationship_type_counts: tuple[tuple[str, int], ...]
    direction_counts: tuple[tuple[str, int], ...]
    reciprocal_relationship_count: int
    active_relationship_count: int
    evidence_ref_ids: tuple[str, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "readout_id",
        "as_of_period_id",
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if (
                fname
                in FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES
            ):
                raise ValueError(
                    f"dataclass field {fname!r} forbidden"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name in (
            "relationship_ids",
            "entity_ids",
            "evidence_ref_ids",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string_tuple(
                    getattr(self, name), field_name=name
                ),
            )
        for name in (
            "reciprocal_relationship_count",
            "active_relationship_count",
        ):
            object.__setattr__(
                self,
                name,
                _validate_non_neg_int(
                    getattr(self, name), field_name=name
                ),
            )
        for name in (
            "relationship_type_counts",
            "direction_counts",
        ):
            object.__setattr__(
                self,
                name,
                _validate_count_pairs(
                    getattr(self, name), field_name=name
                ),
            )
        warnings = tuple(self.warnings)
        for entry in warnings:
            if not isinstance(entry, str) or not entry:
                raise ValueError(
                    "warnings must be non-empty strings"
                )
        object.__setattr__(self, "warnings", warnings)
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "readout_id": self.readout_id,
            "as_of_period_id": self.as_of_period_id,
            "relationship_ids": list(self.relationship_ids),
            "entity_ids": list(self.entity_ids),
            "relationship_type_counts": [
                list(p)
                for p in self.relationship_type_counts
            ],
            "direction_counts": [
                list(p) for p in self.direction_counts
            ],
            "reciprocal_relationship_count": (
                self.reciprocal_relationship_count
            ),
            "active_relationship_count": (
                self.active_relationship_count
            ),
            "evidence_ref_ids": list(self.evidence_ref_ids),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


def _ordered_count_pairs(
    items: Iterable[str],
) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return tuple(counts.items())


def _is_active_at(
    record: StrategicRelationshipRecord,
    *,
    as_of_period_id: str,
) -> bool:
    if record.effective_from_period_id > as_of_period_id:
        return False
    if (
        record.effective_to_period_id is not None
        and record.effective_to_period_id < as_of_period_id
    ):
        return False
    return True


def build_strategic_relationship_readout(
    kernel: "WorldKernel",
    *,
    as_of_period_id: str,
    readout_id: str | None = None,
) -> StrategicRelationshipReadout:
    """Read-only projection of the kernel's
    :class:`StrategicRelationshipBook` at
    ``as_of_period_id``.

    Counts only — no centrality, no rank, no risk
    score.
    """

    book = getattr(kernel, "strategic_relationships", None)
    records: tuple[StrategicRelationshipRecord, ...] = (
        () if book is None else book.list_relationships()
    )
    active = tuple(
        r
        for r in records
        if _is_active_at(
            r, as_of_period_id=as_of_period_id
        )
    )
    relationship_ids = tuple(
        sorted(r.relationship_id for r in active)
    )
    entity_ids_set: list[str] = []
    seen: set[str] = set()
    for r in active:
        for e in (r.source_entity_id, r.target_entity_id):
            if e not in seen:
                seen.add(e)
                entity_ids_set.append(e)
    entity_ids = tuple(sorted(entity_ids_set))
    type_counts = _ordered_count_pairs(
        r.relationship_type_label for r in active
    )
    direction_counts = _ordered_count_pairs(
        r.direction_label for r in active
    )
    reciprocal_count = sum(
        1
        for r in active
        if r.direction_label == "reciprocal"
    )
    evidence_set: list[str] = []
    seen_ev: set[str] = set()
    for r in active:
        for ev in r.evidence_ref_ids:
            if ev not in seen_ev:
                seen_ev.add(ev)
                evidence_set.append(ev)
    evidence_ref_ids = tuple(sorted(evidence_set))
    warnings_list: list[str] = []
    for r in active:
        if r.relationship_type_label == "unknown":
            warnings_list.append(
                "unknown_relationship_type_label "
                f"observed in {r.relationship_id}"
            )
        if r.direction_label == "unknown":
            warnings_list.append(
                "unknown_direction_label observed in "
                f"{r.relationship_id}"
            )
    rid: str = (
        readout_id
        if readout_id is not None
        else (
            "strategic_relationship_readout:"
            f"{as_of_period_id}"
        )
    )
    return StrategicRelationshipReadout(
        readout_id=rid,
        as_of_period_id=as_of_period_id,
        relationship_ids=relationship_ids,
        entity_ids=entity_ids,
        relationship_type_counts=type_counts,
        direction_counts=direction_counts,
        reciprocal_relationship_count=reciprocal_count,
        active_relationship_count=len(active),
        evidence_ref_ids=evidence_ref_ids,
        warnings=tuple(warnings_list),
        metadata={},
    )
