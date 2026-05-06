"""
v1.27.1 — Generic Strategic Relationship Network storage.

Generic, country-neutral storage-only foundation for the
v1.27 strategic relationship substrate per
[`docs/v1_27_generic_relationship_network_annotation_provenance.md`](../docs/v1_27_generic_relationship_network_annotation_provenance.md)
§2.

v1.27.1 ships one immutable frozen dataclass
(:class:`StrategicRelationshipRecord`), one append-only
:class:`StrategicRelationshipBook`, and the v1.27.0
closed-set ``RELATIONSHIP_TYPE_LABELS`` /
``DIRECTION_LABELS``. Read-only readout (v1.27.2) and
freeze (v1.27.last) are strictly later sub-milestones.

Critical design constraints carried verbatim from the
v1.27.0 design pin (binding):

- **Generic and country-neutral.** No Japan
  calibration, no real company name, no real-data
  adapter. The
  :data:`world.forbidden_tokens.FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES`
  composed set hard-forbids ownership / voting /
  market-value tokens; hard-forbids network centrality /
  systemic-importance scoring; hard-forbids real-data
  adapter names; hard-forbids real-company-relationship
  claims; plus the full v1.18.0–v1.26.0 inherited
  boundary.
- **No percentages, no voting power, no market value.**
  A relationship record carries an archetype label
  (``strategic_holding_like`` / ``supplier_customer_like``
  / ...) and plain-id citations only.
- **No network-centrality / systemic-importance score.**
  v1.27.2 readout exposes counts only.
- **Append-only.** No relationship ever mutates a prior
  one; revisions append a new record citing the prior
  one.
- **Empty by default on the kernel.** An empty book
  emits no ledger record, so every existing fixed-
  universe fixture continues to behave statically and
  every v1.21.last canonical ``living_world_digest``
  stays byte-identical.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES,
)
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set vocabularies (binding for v1.27.1)
# ---------------------------------------------------------------------------


RELATIONSHIP_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "strategic_holding_like",
        "supplier_customer_like",
        "group_affiliation_like",
        "lender_relationship_like",
        "governance_relationship_like",
        "commercial_relationship_like",
        "unknown",
    }
)


DIRECTION_LABELS: frozenset[str] = frozenset(
    {
        "directed",
        "reciprocal",
        "undirected",
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
# Default boundary flags (binding per v1.27.0 §2.4)
# ---------------------------------------------------------------------------


_DEFAULT_BOUNDARY_FLAGS_TUPLE: tuple[tuple[str, bool], ...] = (
    # v1.18.0 boundary
    ("no_actor_decision", True),
    ("no_llm_execution", True),
    ("no_price_formation", True),
    ("no_trading", True),
    ("no_financing_execution", True),
    ("no_investment_advice", True),
    ("synthetic_only", True),
    # v1.21.0a additions
    ("no_aggregate_stress_result", True),
    ("no_interaction_inference", True),
    ("no_field_value_claim", True),
    ("no_field_magnitude_claim", True),
    ("descriptive_only", True),
    # v1.26.0 inheritance (real-data / Japan / market-effect)
    ("no_real_data_ingestion", True),
    ("no_japan_calibration", True),
    ("no_real_company_name", True),
    ("no_market_effect_inference", True),
    ("no_event_to_price_mapping", True),
    ("no_forecast_from_calendar", True),
    # v1.27.0 strategic-relationship additions
    ("no_ownership_percentage", True),
    ("no_voting_power", True),
    ("no_market_value", True),
    ("no_centrality_score", True),
    ("no_real_company_relationship", True),
)


def _default_boundary_flags() -> dict[str, bool]:
    return dict(_DEFAULT_BOUNDARY_FLAGS_TUPLE)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StrategicRelationshipError(Exception):
    """Base class for v1.27.1 strategic-relationship
    storage errors."""


class DuplicateStrategicRelationshipError(
    StrategicRelationshipError
):
    """Raised when a ``relationship_id`` is added twice."""


class UnknownStrategicRelationshipError(
    StrategicRelationshipError, KeyError
):
    """Raised when a ``relationship_id`` is not found."""


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


def _validate_optional_string(
    value: Any, *, field_name: str
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name}, when present, must be a "
            "non-empty string"
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
        if (
            key
            in FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} contains forbidden key "
                f"{key!r} (v1.27.0 strategic-relationship "
                "boundary)"
            )


def _scan_label_value_for_forbidden_tokens(
    value: str, *, field_name: str
) -> None:
    if (
        value
        in FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES
    ):
        raise ValueError(
            f"{field_name} value {value!r} is in the "
            "v1.27.0 strategic-relationship forbidden-name "
            "set"
        )


# ---------------------------------------------------------------------------
# StrategicRelationshipRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategicRelationshipRecord:
    """Immutable, append-only record of one generic
    strategic relationship between two entities.

    Carries a closed-set ``relationship_type_label``
    (archetype) + ``direction_label`` + plain-id
    citations only. **No** ownership percentage, **no**
    voting power, **no** market value, **no** centrality
    score.
    """

    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type_label: str
    direction_label: str
    effective_from_period_id: str
    effective_to_period_id: str | None = None
    evidence_ref_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    status: str = "active"
    visibility: str = "internal"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "relationship_id",
        "source_entity_id",
        "target_entity_id",
        "relationship_type_label",
        "direction_label",
        "effective_from_period_id",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        (
            "relationship_type_label",
            RELATIONSHIP_TYPE_LABELS,
        ),
        ("direction_label", DIRECTION_LABELS),
        ("status", STATUS_LABELS),
        ("visibility", VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if (
                fname
                in FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES
            ):
                raise ValueError(
                    f"dataclass field {fname!r} is in the "
                    "v1.27.0 strategic-relationship "
                    "forbidden field-name set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, name),
                allowed,
                field_name=name,
            )
        for name, _ in self.LABEL_FIELDS:
            _scan_label_value_for_forbidden_tokens(
                getattr(self, name), field_name=name
            )
        # source / target self-loop: allowed only when
        # direction_label == "reciprocal" or "undirected"
        # — but a self-loop is generally unusual; we permit
        # it under the same label set for generic-substrate
        # flexibility but keep it explicit.
        # effective_to_period_id — optional, must be ≥
        # effective_from_period_id when present.
        object.__setattr__(
            self,
            "effective_to_period_id",
            _validate_optional_string(
                self.effective_to_period_id,
                field_name="effective_to_period_id",
            ),
        )
        if (
            self.effective_to_period_id is not None
            and self.effective_to_period_id
            < self.effective_from_period_id
        ):
            raise ValueError(
                "effective_to_period_id must be >= "
                "effective_from_period_id "
                "lexicographically; got "
                f"{self.effective_to_period_id!r} < "
                f"{self.effective_from_period_id!r}"
            )
        # evidence_ref_ids — may be empty
        object.__setattr__(
            self,
            "evidence_ref_ids",
            _validate_string_tuple(
                self.evidence_ref_ids,
                field_name="evidence_ref_ids",
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
                    "a v1.27.0 default; cannot be "
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
            "relationship_id": self.relationship_id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relationship_type_label": (
                self.relationship_type_label
            ),
            "direction_label": self.direction_label,
            "effective_from_period_id": (
                self.effective_from_period_id
            ),
            "effective_to_period_id": (
                self.effective_to_period_id
            ),
            "evidence_ref_ids": list(
                self.evidence_ref_ids
            ),
            "status": self.status,
            "visibility": self.visibility,
            "boundary_flags": dict(self.boundary_flags),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# StrategicRelationshipBook
# ---------------------------------------------------------------------------


@dataclass
class StrategicRelationshipBook:
    """Append-only storage for v1.27.1
    :class:`StrategicRelationshipRecord` instances.

    Emits exactly one ledger record per successful
    ``add_relationship(...)`` call (a single
    :data:`world.ledger.RecordType.STRATEGIC_RELATIONSHIP_RECORDED`
    event), no extra ledger record on duplicate id,
    mutates no other source-of-truth book.

    Empty by default on the kernel — every pre-v1.27.1
    fixed fixture digest stays byte-identical.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _relationships: dict[
        str, StrategicRelationshipRecord
    ] = field(default_factory=dict)

    def _now(self) -> datetime:
        if self.clock is not None:
            try:
                return self.clock.current_datetime()
            except Exception:
                pass
        return datetime.now(timezone.utc)

    def add_relationship(
        self,
        relationship: StrategicRelationshipRecord,
        *,
        simulation_date: Any = None,
    ) -> StrategicRelationshipRecord:
        if not isinstance(
            relationship, StrategicRelationshipRecord
        ):
            raise TypeError(
                "relationship must be a "
                "StrategicRelationshipRecord instance"
            )
        if (
            relationship.relationship_id
            in self._relationships
        ):
            raise DuplicateStrategicRelationshipError(
                "Duplicate relationship_id: "
                f"{relationship.relationship_id!r}"
            )
        self._relationships[
            relationship.relationship_id
        ] = relationship
        if self.ledger is not None:
            payload: dict[str, Any] = {
                "relationship_id": (
                    relationship.relationship_id
                ),
                "source_entity_id": (
                    relationship.source_entity_id
                ),
                "target_entity_id": (
                    relationship.target_entity_id
                ),
                "relationship_type_label": (
                    relationship.relationship_type_label
                ),
                "direction_label": (
                    relationship.direction_label
                ),
                "effective_from_period_id": (
                    relationship.effective_from_period_id
                ),
                "effective_to_period_id": (
                    relationship.effective_to_period_id
                ),
                "evidence_ref_ids": list(
                    relationship.evidence_ref_ids
                ),
                "status": relationship.status,
                "visibility": relationship.visibility,
                "boundary_flags": dict(
                    relationship.boundary_flags
                ),
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
                event_type="strategic_relationship_recorded",
                simulation_date=sim_date,
                object_id=relationship.relationship_id,
                source=relationship.relationship_type_label,
                payload=payload,
                space_id="strategic_relationships",
                visibility=relationship.visibility,
            )
        return relationship

    def get_relationship(
        self, relationship_id: str
    ) -> StrategicRelationshipRecord:
        try:
            return self._relationships[relationship_id]
        except KeyError as exc:
            raise UnknownStrategicRelationshipError(
                "strategic_relationship not found: "
                f"{relationship_id!r}"
            ) from exc

    def list_relationships(
        self,
    ) -> tuple[StrategicRelationshipRecord, ...]:
        return tuple(self._relationships.values())

    def list_by_relationship_type(
        self, relationship_type_label: str
    ) -> tuple[StrategicRelationshipRecord, ...]:
        return tuple(
            r
            for r in self._relationships.values()
            if r.relationship_type_label
            == relationship_type_label
        )

    def list_by_direction(
        self, direction_label: str
    ) -> tuple[StrategicRelationshipRecord, ...]:
        return tuple(
            r
            for r in self._relationships.values()
            if r.direction_label == direction_label
        )

    def list_by_entity(
        self, entity_id: str
    ) -> tuple[StrategicRelationshipRecord, ...]:
        """Return every relationship that names
        ``entity_id`` in source_entity_id OR
        target_entity_id."""
        return tuple(
            r
            for r in self._relationships.values()
            if (
                r.source_entity_id == entity_id
                or r.target_entity_id == entity_id
            )
        )

    def list_by_effective_period(
        self, effective_from_period_id: str
    ) -> tuple[StrategicRelationshipRecord, ...]:
        return tuple(
            r
            for r in self._relationships.values()
            if r.effective_from_period_id
            == effective_from_period_id
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "strategic_relationships": [
                r.to_dict()
                for r in self._relationships.values()
            ],
        }


__all__ = [
    "DIRECTION_LABELS",
    "DuplicateStrategicRelationshipError",
    "RELATIONSHIP_TYPE_LABELS",
    "STATUS_LABELS",
    "StrategicRelationshipBook",
    "StrategicRelationshipError",
    "StrategicRelationshipRecord",
    "UnknownStrategicRelationshipError",
    "VISIBILITY_LABELS",
]
