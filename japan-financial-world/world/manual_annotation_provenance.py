"""
v1.27.3 — Manual annotation provenance hardening storage.

Generic, country-neutral storage-only foundation for the
v1.27 annotation provenance hardening per
[`docs/v1_27_generic_relationship_network_annotation_provenance.md`](../docs/v1_27_generic_relationship_network_annotation_provenance.md)
§3.

v1.27.3 ships one immutable frozen dataclass
(:class:`ManualAnnotationProvenanceRecord`), one append-
only :class:`ManualAnnotationProvenanceBook`, and the
v1.27.0 closed-set ``AUTHORITY_LABELS`` /
``EVIDENCE_ACCESS_SCOPE_LABELS``.

Critical design constraints carried verbatim from the
v1.27.0 design pin (binding):

- **Pseudonymous only.** ``annotator_id_label`` is a
  closed-format pseudonymous plain-id. Storage rejects
  any ``@`` character (anti-email-leak). The composed
  forbidden set hard-forbids real-person tokens (real
  name / personal email / phone / national-id /
  employee-id).
- **No compliance claim.** Storage hard-forbids SOC2 /
  FISC / ISO27001 / regulatory_attestation tokens. The
  ``authority_label`` describes audit context only.
- **No LLM authoring.** v1.24 reasoning_mode = human_authored
  is unchanged; provenance simply records *who* reviewed.
- **Append-only.** No record ever mutates a prior one.
- **Read-only with respect to the world.** Adding a
  provenance record emits exactly one ledger record;
  it mutates no other source-of-truth book — including
  no mutation of the v1.24 ManualAnnotationBook.
- **Empty by default on the kernel.** An empty book
  emits no ledger record, so every existing fixed
  fixture digest stays byte-identical.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Mapping

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_ANNOTATION_PROVENANCE_FIELD_NAMES,
)
from world.ledger import Ledger
from world.manual_annotations import (
    REVIEWER_ROLE_LABELS,
)


# ---------------------------------------------------------------------------
# Closed-set vocabularies (binding for v1.27.3)
# ---------------------------------------------------------------------------


AUTHORITY_LABELS: frozenset[str] = frozenset(
    {
        "self_review",
        "delegated_review",
        "supervisory_review",
        "audit_review",
        "unknown",
    }
)


EVIDENCE_ACCESS_SCOPE_LABELS: frozenset[str] = frozenset(
    {
        "public_synthetic",
        "internal_synthetic",
        "restricted_synthetic",
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
# Default boundary flags (binding per v1.27.0 §3 + inheritance)
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
    # v1.24.0 manual-annotation context (provenance hardens
    # the same surface)
    ("human_authored_only", True),
    ("no_auto_annotation", True),
    ("no_causal_proof", True),
    # v1.26.0 inheritance
    ("no_real_data_ingestion", True),
    ("no_japan_calibration", True),
    ("no_real_company_name", True),
    # v1.27.3 provenance-specific additions
    ("pseudonymous_only", True),
    ("no_real_person_identity", True),
    ("no_compliance_claim", True),
    ("no_llm_authoring", True),
)


def _default_boundary_flags() -> dict[str, bool]:
    return dict(_DEFAULT_BOUNDARY_FLAGS_TUPLE)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ManualAnnotationProvenanceError(Exception):
    """Base class for v1.27.3 provenance storage errors."""


class DuplicateManualAnnotationProvenanceError(
    ManualAnnotationProvenanceError
):
    """Raised when a ``provenance_id`` is added twice."""


class UnknownManualAnnotationProvenanceError(
    ManualAnnotationProvenanceError, KeyError
):
    """Raised when a ``provenance_id`` is not found."""


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


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if (
            key
            in FORBIDDEN_ANNOTATION_PROVENANCE_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} contains forbidden key "
                f"{key!r} (v1.27.3 provenance boundary)"
            )


def _scan_label_value_for_forbidden_tokens(
    value: str, *, field_name: str
) -> None:
    if (
        value
        in FORBIDDEN_ANNOTATION_PROVENANCE_FIELD_NAMES
    ):
        raise ValueError(
            f"{field_name} value {value!r} is in the "
            "v1.27.3 provenance forbidden-name set"
        )


def _validate_pseudonymous_id(
    value: str, *, field_name: str
) -> str:
    """Reject any ``annotator_id_label`` that contains
    ``@`` (anti-email-leak heuristic guard) or matches a
    forbidden token."""
    _validate_required_string(value, field_name=field_name)
    if "@" in value:
        raise ValueError(
            f"{field_name} must be pseudonymous; the "
            f"v1.27.3 anti-email-leak guard rejects "
            f"any '@' character; got {value!r}"
        )
    if (
        value
        in FORBIDDEN_ANNOTATION_PROVENANCE_FIELD_NAMES
    ):
        raise ValueError(
            f"{field_name} value {value!r} is in the "
            "v1.27.3 provenance forbidden-name set"
        )
    return value


# ---------------------------------------------------------------------------
# ManualAnnotationProvenanceRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManualAnnotationProvenanceRecord:
    """Immutable, append-only provenance metadata
    companion record for a v1.24
    :class:`world.manual_annotations.ManualAnnotationRecord`.

    Pseudonymous: ``annotator_id_label`` may not contain
    ``@`` (anti-email-leak) and may not match any
    real-identity / compliance-claim forbidden token. Carries
    no real-person identity. No compliance claim. No LLM
    authoring."""

    provenance_id: str
    annotation_id: str
    annotator_id_label: str
    reviewer_role_label: str
    authority_label: str
    evidence_access_scope_label: str
    audit_period_id: str
    authorization_ref_id: str | None = None
    review_context_id: str | None = None
    status: str = "active"
    visibility: str = "internal"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "provenance_id",
        "annotation_id",
        "reviewer_role_label",
        "authority_label",
        "evidence_access_scope_label",
        "audit_period_id",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("reviewer_role_label", REVIEWER_ROLE_LABELS),
        ("authority_label", AUTHORITY_LABELS),
        (
            "evidence_access_scope_label",
            EVIDENCE_ACCESS_SCOPE_LABELS,
        ),
        ("status", STATUS_LABELS),
        ("visibility", VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if (
                fname
                in FORBIDDEN_ANNOTATION_PROVENANCE_FIELD_NAMES
            ):
                raise ValueError(
                    f"dataclass field {fname!r} is in the "
                    "v1.27.3 provenance forbidden field-"
                    "name set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        # Pseudonymous id — anti-email-leak guard.
        object.__setattr__(
            self,
            "annotator_id_label",
            _validate_pseudonymous_id(
                self.annotator_id_label,
                field_name="annotator_id_label",
            ),
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
        # Optional plain-id fields.
        object.__setattr__(
            self,
            "authorization_ref_id",
            _validate_optional_string(
                self.authorization_ref_id,
                field_name="authorization_ref_id",
            ),
        )
        object.__setattr__(
            self,
            "review_context_id",
            _validate_optional_string(
                self.review_context_id,
                field_name="review_context_id",
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
                    "a v1.27.3 default; cannot be "
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
            "provenance_id": self.provenance_id,
            "annotation_id": self.annotation_id,
            "annotator_id_label": self.annotator_id_label,
            "reviewer_role_label": (
                self.reviewer_role_label
            ),
            "authority_label": self.authority_label,
            "evidence_access_scope_label": (
                self.evidence_access_scope_label
            ),
            "audit_period_id": self.audit_period_id,
            "authorization_ref_id": (
                self.authorization_ref_id
            ),
            "review_context_id": self.review_context_id,
            "status": self.status,
            "visibility": self.visibility,
            "boundary_flags": dict(self.boundary_flags),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ManualAnnotationProvenanceBook
# ---------------------------------------------------------------------------


@dataclass
class ManualAnnotationProvenanceBook:
    """Append-only storage for v1.27.3
    :class:`ManualAnnotationProvenanceRecord` instances.

    Emits exactly one ledger record per successful
    ``add_provenance(...)`` call (a single
    :data:`world.ledger.RecordType.MANUAL_ANNOTATION_PROVENANCE_RECORDED`
    event), no extra ledger record on duplicate id,
    mutates no other source-of-truth book — including no
    mutation of the v1.24 ManualAnnotationBook.

    Empty by default on the kernel — every pre-v1.27.3
    fixed fixture digest stays byte-identical.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _provenances: dict[
        str, ManualAnnotationProvenanceRecord
    ] = field(default_factory=dict)

    def _now(self) -> datetime:
        if self.clock is not None:
            try:
                return self.clock.current_datetime()
            except Exception:
                pass
        return datetime.now(timezone.utc)

    def add_provenance(
        self,
        provenance: ManualAnnotationProvenanceRecord,
        *,
        simulation_date: Any = None,
    ) -> ManualAnnotationProvenanceRecord:
        if not isinstance(
            provenance, ManualAnnotationProvenanceRecord
        ):
            raise TypeError(
                "provenance must be a "
                "ManualAnnotationProvenanceRecord instance"
            )
        if (
            provenance.provenance_id in self._provenances
        ):
            raise DuplicateManualAnnotationProvenanceError(
                "Duplicate provenance_id: "
                f"{provenance.provenance_id!r}"
            )
        self._provenances[
            provenance.provenance_id
        ] = provenance
        if self.ledger is not None:
            payload: dict[str, Any] = {
                "provenance_id": provenance.provenance_id,
                "annotation_id": provenance.annotation_id,
                "annotator_id_label": (
                    provenance.annotator_id_label
                ),
                "reviewer_role_label": (
                    provenance.reviewer_role_label
                ),
                "authority_label": (
                    provenance.authority_label
                ),
                "evidence_access_scope_label": (
                    provenance.evidence_access_scope_label
                ),
                "audit_period_id": (
                    provenance.audit_period_id
                ),
                "authorization_ref_id": (
                    provenance.authorization_ref_id
                ),
                "review_context_id": (
                    provenance.review_context_id
                ),
                "status": provenance.status,
                "visibility": provenance.visibility,
                "boundary_flags": dict(
                    provenance.boundary_flags
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
                event_type=(
                    "manual_annotation_provenance_recorded"
                ),
                simulation_date=sim_date,
                object_id=provenance.provenance_id,
                source=provenance.authority_label,
                payload=payload,
                space_id="manual_annotation_provenance",
                visibility=provenance.visibility,
            )
        return provenance

    def get_provenance(
        self, provenance_id: str
    ) -> ManualAnnotationProvenanceRecord:
        try:
            return self._provenances[provenance_id]
        except KeyError as exc:
            raise UnknownManualAnnotationProvenanceError(
                "manual_annotation_provenance not found: "
                f"{provenance_id!r}"
            ) from exc

    def list_provenances(
        self,
    ) -> tuple[ManualAnnotationProvenanceRecord, ...]:
        return tuple(self._provenances.values())

    def list_by_annotation(
        self, annotation_id: str
    ) -> tuple[ManualAnnotationProvenanceRecord, ...]:
        return tuple(
            p
            for p in self._provenances.values()
            if p.annotation_id == annotation_id
        )

    def list_by_authority(
        self, authority_label: str
    ) -> tuple[ManualAnnotationProvenanceRecord, ...]:
        return tuple(
            p
            for p in self._provenances.values()
            if p.authority_label == authority_label
        )

    def list_by_audit_period(
        self, audit_period_id: str
    ) -> tuple[ManualAnnotationProvenanceRecord, ...]:
        return tuple(
            p
            for p in self._provenances.values()
            if p.audit_period_id == audit_period_id
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "manual_annotation_provenance": [
                p.to_dict()
                for p in self._provenances.values()
            ],
        }


__all__ = [
    "AUTHORITY_LABELS",
    "DuplicateManualAnnotationProvenanceError",
    "EVIDENCE_ACCESS_SCOPE_LABELS",
    "ManualAnnotationProvenanceBook",
    "ManualAnnotationProvenanceError",
    "ManualAnnotationProvenanceRecord",
    "STATUS_LABELS",
    "UnknownManualAnnotationProvenanceError",
    "VISIBILITY_LABELS",
]
