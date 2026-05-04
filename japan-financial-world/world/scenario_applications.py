"""
v1.18.2 — Scenario driver application helper.

Append-only application of v1.18.1
:class:`ScenarioDriverTemplate` records onto FWE evidence /
context surfaces. v1.18.2 lands two immutable record types and
the deterministic helper :func:`apply_scenario_driver`:

- :class:`ScenarioDriverApplicationRecord` — the per-call
  application receipt.
- :class:`ScenarioContextShiftRecord` — one or more append-only
  shift records emitted by the helper.

Critical design constraint pinned at v1.18.0 (binding) and
re-pinned at v1.18.2:

- Application is **append-only**. The helper **never** mutates a
  pre-existing context record. Pre-existing
  :class:`MarketEnvironmentStateRecord` /
  :class:`FirmFinancialStateRecord` /
  :class:`InterbankLiquidityStateRecord` /
  :class:`IndustryConditionRecord` payloads are byte-identical
  pre / post call.
- The helper does **not** decide actor behaviour. Every shift is
  a *category* of context input that an existing mechanism (or a
  future audited reasoning policy) may read.
- All v1.18.2 mapping rules ship as ``reasoning_mode =
  "rule_based_fallback"``. They are *fallbacks* — replaceable by
  a future audited reasoning policy that fills the same audit
  shape (``reasoning_mode`` / ``reasoning_policy_id`` /
  ``reasoning_slot`` / ``evidence_ref_ids`` /
  ``unresolved_ref_count`` / ``boundary_flags``).
- No LLM execution. No price formation. No trading. No order /
  trade / quote / clearing / settlement. No financing execution.
  No investment advice. No real data ingestion. No Japan
  calibration. The closed-set boundary-flag default carried on
  every emitted record names each invariant.

The module is **runtime-book-free** beyond the v0/v1 ledger +
clock convention shared by every other storage book — it does
not import any source-of-truth book on the engine side. The
helper takes the kernel as an argument and reads only via
:meth:`ScenarioDriverTemplateBook.get_template`; it does **not**
scan kernel books globally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, ClassVar, Iterable, Mapping, TYPE_CHECKING

from world.clock import Clock
from world.ledger import Ledger
from world.scenario_drivers import (
    AFFECTED_ACTOR_SCOPE_LABELS,
    DEFAULT_REASONING_MODE,
    DEFAULT_REASONING_SLOT,
    DRIVER_GROUP_LABELS,
    EXPECTED_ANNOTATION_TYPE_LABELS,
    FORBIDDEN_SCENARIO_FIELD_NAMES,
    REASONING_MODE_LABELS,
    REASONING_SLOT_LABELS,
    SCENARIO_FAMILY_LABELS,
    SEVERITY_LABELS,
    STATUS_LABELS,
    VISIBILITY_LABELS,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


# ---------------------------------------------------------------------------
# Closed-set vocabularies new at v1.18.2
# ---------------------------------------------------------------------------


APPLICATION_STATUS_LABELS: frozenset[str] = frozenset(
    {
        "prepared",
        "applied_as_context_shift",
        "degraded_missing_template",
        "degraded_unresolved_refs",
        "rejected",
        "unknown",
    }
)


CONTEXT_SURFACE_LABELS: frozenset[str] = frozenset(
    {
        "market_environment",
        "firm_financial_state",
        "interbank_liquidity",
        "industry_condition",
        "attention_surface",
        "market_pressure_surface",
        "financing_review_surface",
        "display_annotation_surface",
        "unknown",
    }
)


SHIFT_DIRECTION_LABELS: frozenset[str] = frozenset(
    {
        "tighten",
        "loosen",
        "deteriorate",
        "improve",
        "increase_uncertainty",
        "reduce_uncertainty",
        "attention_amplify",
        "information_gap",
        "no_direct_shift",
        "unknown",
    }
)


# v1.18.2 default reasoning policy id. The audit shape is
# forward-compatible: a future LLM-mode reasoning policy must
# populate the same fields under a different policy id.
DEFAULT_APPLICATION_REASONING_POLICY_ID: str = (
    "v1.18.2:scenario_application:rule_based_fallback"
)


# Boundary-flag defaults stamped onto every emitted record. The
# tuple form keeps the pinned default order stable and the dict
# returned by the factory is mutable per-instance.
_DEFAULT_BOUNDARY_FLAGS_TUPLE: tuple[tuple[str, bool], ...] = (
    ("no_actor_decision", True),
    ("no_llm_execution", True),
    ("no_price_formation", True),
    ("no_trading", True),
    ("no_financing_execution", True),
    ("no_investment_advice", True),
    ("synthetic_only", True),
)


def _default_boundary_flags() -> dict[str, bool]:
    return dict(_DEFAULT_BOUNDARY_FLAGS_TUPLE)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ScenarioApplicationError(Exception):
    """Base class for scenario-application errors."""


class DuplicateScenarioApplicationError(ScenarioApplicationError):
    """Raised when a scenario_application_id is added twice."""


class DuplicateScenarioContextShiftError(ScenarioApplicationError):
    """Raised when a scenario_context_shift_id is added twice."""


class UnknownScenarioApplicationError(
    ScenarioApplicationError, KeyError
):
    """Raised when a scenario_application_id is not found."""


class UnknownScenarioContextShiftError(
    ScenarioApplicationError, KeyError
):
    """Raised when a scenario_context_shift_id is not found."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_label(
    value: Any, allowed: frozenset[str], *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)!r}; "
            f"got {value!r}"
        )
    return value


def _validate_string_tuple(
    value: Iterable[str], *, field_name: str
) -> tuple[str, ...]:
    normalized = tuple(value)
    for entry in normalized:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty strings; "
                f"got {entry!r}"
            )
    return normalized


def _validate_boundary_flags(
    value: Mapping[str, Any], *, field_name: str
) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for k, v in dict(value).items():
        if not isinstance(k, str) or not k:
            raise ValueError(
                f"{field_name} keys must be non-empty strings"
            )
        if not isinstance(v, bool):
            raise ValueError(
                f"{field_name} values must be bool; got {type(v).__name__}"
            )
        out[k] = v
    return out


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_SCENARIO_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key {key!r} "
                "(v1.18.0 hard naming boundary — scenario "
                "applications do not carry actor-decision / "
                "price / forecast / advice / real-data / "
                "Japan-calibration / LLM fields)"
            )


def _coerce_iso_date(value: Any) -> str:
    if isinstance(value, str):
        if not value:
            raise ValueError("as_of_date must be a non-empty ISO date")
        return value
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(
        f"as_of_date must be date or str; got {type(value).__name__}"
    )


# ---------------------------------------------------------------------------
# ScenarioDriverApplicationRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioDriverApplicationRecord:
    """Immutable receipt for a single :func:`apply_scenario_driver`
    call. v1.18.2 emits one application record + zero-or-more
    :class:`ScenarioContextShiftRecord` records per call. The
    record cites — never mutates — the pre-existing context
    records the caller passed via ``source_context_record_ids``.

    Reasoning fields (``reasoning_mode``, ``reasoning_policy_id``,
    ``reasoning_slot``) carry the v1.18.0 audit shape so a future
    LLM-mode reasoning policy can replace the v1.18.x rule-based
    fallback without changing the audit surface.
    """

    scenario_application_id: str
    scenario_driver_template_id: str
    as_of_date: str
    application_status_label: str
    reasoning_mode: str = DEFAULT_REASONING_MODE
    reasoning_policy_id: str = DEFAULT_APPLICATION_REASONING_POLICY_ID
    reasoning_slot: str = DEFAULT_REASONING_SLOT
    source_template_ids: tuple[str, ...] = field(default_factory=tuple)
    source_context_record_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    emitted_context_shift_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    unresolved_ref_count: int = 0
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    status: str = "active"
    visibility: str = "internal_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "scenario_application_id",
        "scenario_driver_template_id",
        "as_of_date",
        "application_status_label",
        "reasoning_mode",
        "reasoning_policy_id",
        "reasoning_slot",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("application_status_label", APPLICATION_STATUS_LABELS),
        ("reasoning_mode",            REASONING_MODE_LABELS),
        ("reasoning_slot",            REASONING_SLOT_LABELS),
        ("status",                    STATUS_LABELS),
        ("visibility",                VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")
        for name, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, name), allowed, field_name=name
            )
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_SCENARIO_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the v1.18.0 "
                    "forbidden field-name set"
                )
        object.__setattr__(
            self,
            "as_of_date",
            _coerce_iso_date(self.as_of_date),
        )
        for name in (
            "source_template_ids",
            "source_context_record_ids",
            "emitted_context_shift_ids",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string_tuple(
                    getattr(self, name), field_name=name
                ),
            )
        if (
            not isinstance(self.unresolved_ref_count, int)
            or isinstance(self.unresolved_ref_count, bool)
            or self.unresolved_ref_count < 0
        ):
            raise ValueError(
                "unresolved_ref_count must be a non-negative int"
            )
        bf = _validate_boundary_flags(
            self.boundary_flags, field_name="boundary_flags"
        )
        _scan_for_forbidden_keys(bf, field_name="boundary_flags")
        object.__setattr__(self, "boundary_flags", bf)
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_application_id": self.scenario_application_id,
            "scenario_driver_template_id": (
                self.scenario_driver_template_id
            ),
            "as_of_date": self.as_of_date,
            "application_status_label": self.application_status_label,
            "reasoning_mode": self.reasoning_mode,
            "reasoning_policy_id": self.reasoning_policy_id,
            "reasoning_slot": self.reasoning_slot,
            "source_template_ids": list(self.source_template_ids),
            "source_context_record_ids": list(
                self.source_context_record_ids
            ),
            "emitted_context_shift_ids": list(
                self.emitted_context_shift_ids
            ),
            "unresolved_ref_count": self.unresolved_ref_count,
            "boundary_flags": dict(self.boundary_flags),
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ScenarioContextShiftRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioContextShiftRecord:
    """Immutable append-only context-shift record emitted by a
    :func:`apply_scenario_driver` call. The shift **cites** —
    never mutates — pre-existing context records via plain-id
    references in :attr:`affected_context_record_ids`.

    Future mechanisms may consume the shift's plain id as evidence
    on a downstream record (e.g. an
    :class:`InvestorMarketIntentRecord` may cite a shift id under
    its ``evidence_ref_ids``); the shift record itself never
    decides what an actor does.
    """

    scenario_context_shift_id: str
    scenario_application_id: str
    scenario_driver_template_id: str
    as_of_date: str
    context_surface_label: str
    driver_group_label: str
    scenario_family_label: str
    shift_direction_label: str
    severity_label: str
    affected_actor_scope_label: str
    affected_context_record_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    affected_evidence_bucket_labels: tuple[str, ...] = field(
        default_factory=tuple
    )
    expected_annotation_type_label: str = "synthetic_event"
    reasoning_mode: str = DEFAULT_REASONING_MODE
    reasoning_policy_id: str = DEFAULT_APPLICATION_REASONING_POLICY_ID
    reasoning_slot: str = DEFAULT_REASONING_SLOT
    evidence_ref_ids: tuple[str, ...] = field(default_factory=tuple)
    unresolved_ref_count: int = 0
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    status: str = "active"
    visibility: str = "internal_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "scenario_context_shift_id",
        "scenario_application_id",
        "scenario_driver_template_id",
        "as_of_date",
        "context_surface_label",
        "driver_group_label",
        "scenario_family_label",
        "shift_direction_label",
        "severity_label",
        "affected_actor_scope_label",
        "expected_annotation_type_label",
        "reasoning_mode",
        "reasoning_policy_id",
        "reasoning_slot",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("context_surface_label",          CONTEXT_SURFACE_LABELS),
        ("driver_group_label",             DRIVER_GROUP_LABELS),
        ("scenario_family_label",          SCENARIO_FAMILY_LABELS),
        ("shift_direction_label",          SHIFT_DIRECTION_LABELS),
        ("severity_label",                 SEVERITY_LABELS),
        ("affected_actor_scope_label",     AFFECTED_ACTOR_SCOPE_LABELS),
        (
            "expected_annotation_type_label",
            EXPECTED_ANNOTATION_TYPE_LABELS,
        ),
        ("reasoning_mode",                 REASONING_MODE_LABELS),
        ("reasoning_slot",                 REASONING_SLOT_LABELS),
        ("status",                         STATUS_LABELS),
        ("visibility",                     VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")
        for name, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, name), allowed, field_name=name
            )
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_SCENARIO_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the v1.18.0 "
                    "forbidden field-name set"
                )
        object.__setattr__(
            self,
            "as_of_date",
            _coerce_iso_date(self.as_of_date),
        )
        for name in (
            "affected_context_record_ids",
            "affected_evidence_bucket_labels",
            "evidence_ref_ids",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string_tuple(
                    getattr(self, name), field_name=name
                ),
            )
        if (
            not isinstance(self.unresolved_ref_count, int)
            or isinstance(self.unresolved_ref_count, bool)
            or self.unresolved_ref_count < 0
        ):
            raise ValueError(
                "unresolved_ref_count must be a non-negative int"
            )
        bf = _validate_boundary_flags(
            self.boundary_flags, field_name="boundary_flags"
        )
        _scan_for_forbidden_keys(bf, field_name="boundary_flags")
        object.__setattr__(self, "boundary_flags", bf)
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_context_shift_id": self.scenario_context_shift_id,
            "scenario_application_id": self.scenario_application_id,
            "scenario_driver_template_id": (
                self.scenario_driver_template_id
            ),
            "as_of_date": self.as_of_date,
            "context_surface_label": self.context_surface_label,
            "driver_group_label": self.driver_group_label,
            "scenario_family_label": self.scenario_family_label,
            "shift_direction_label": self.shift_direction_label,
            "severity_label": self.severity_label,
            "affected_actor_scope_label": (
                self.affected_actor_scope_label
            ),
            "affected_context_record_ids": list(
                self.affected_context_record_ids
            ),
            "affected_evidence_bucket_labels": list(
                self.affected_evidence_bucket_labels
            ),
            "expected_annotation_type_label": (
                self.expected_annotation_type_label
            ),
            "reasoning_mode": self.reasoning_mode,
            "reasoning_policy_id": self.reasoning_policy_id,
            "reasoning_slot": self.reasoning_slot,
            "evidence_ref_ids": list(self.evidence_ref_ids),
            "unresolved_ref_count": self.unresolved_ref_count,
            "boundary_flags": dict(self.boundary_flags),
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ScenarioApplicationBook
# ---------------------------------------------------------------------------


@dataclass
class ScenarioApplicationBook:
    """Append-only storage for v1.18.2
    :class:`ScenarioDriverApplicationRecord` and
    :class:`ScenarioContextShiftRecord` instances.

    Mirrors the v1.15.4 / v1.15.6 / v1.18.1 storage-book
    convention: emits exactly one ledger record per
    :meth:`add_application` call
    (``RecordType.SCENARIO_DRIVER_APPLICATION_RECORDED``) and
    exactly one ledger record per :meth:`add_context_shift` call
    (``RecordType.SCENARIO_CONTEXT_SHIFT_RECORDED``). The book
    mutates no other source-of-truth book — including the
    :class:`PriceBook`, :class:`MarketEnvironmentBook`,
    :class:`FirmFinancialStateBook`,
    :class:`InterbankLiquidityStateBook`, and
    :class:`CorporateFinancingPathBook`.

    Idempotency: re-adding an id raises
    :class:`DuplicateScenarioApplicationError` /
    :class:`DuplicateScenarioContextShiftError` and emits **no**
    additional ledger record (pinned by trip-wire tests).
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _applications: dict[str, ScenarioDriverApplicationRecord] = field(
        default_factory=dict
    )
    _context_shifts: dict[str, ScenarioContextShiftRecord] = field(
        default_factory=dict
    )

    def _now(self) -> datetime:
        if self.clock is not None:
            try:
                return self.clock.current_datetime()
            except Exception:
                pass
        return datetime.now(timezone.utc)

    # -- applications ------------------------------------------------

    def add_application(
        self, application: ScenarioDriverApplicationRecord
    ) -> ScenarioDriverApplicationRecord:
        if application.scenario_application_id in self._applications:
            raise DuplicateScenarioApplicationError(
                "Duplicate scenario_application_id: "
                f"{application.scenario_application_id}"
            )
        self._applications[
            application.scenario_application_id
        ] = application

        if self.ledger is not None:
            payload = {
                "scenario_application_id": (
                    application.scenario_application_id
                ),
                "scenario_driver_template_id": (
                    application.scenario_driver_template_id
                ),
                "as_of_date": application.as_of_date,
                "application_status_label": (
                    application.application_status_label
                ),
                "reasoning_mode": application.reasoning_mode,
                "reasoning_policy_id": application.reasoning_policy_id,
                "reasoning_slot": application.reasoning_slot,
                "source_template_ids": list(
                    application.source_template_ids
                ),
                "source_context_record_ids": list(
                    application.source_context_record_ids
                ),
                "emitted_context_shift_ids": list(
                    application.emitted_context_shift_ids
                ),
                "unresolved_ref_count": (
                    application.unresolved_ref_count
                ),
                "boundary_flags": dict(application.boundary_flags),
                "status": application.status,
                "visibility": application.visibility,
            }
            _scan_for_forbidden_keys(
                payload, field_name="ledger payload"
            )
            self.ledger.append(
                event_type="scenario_driver_application_recorded",
                simulation_date=application.as_of_date,
                object_id=application.scenario_application_id,
                source=application.scenario_driver_template_id,
                payload=payload,
                space_id="scenario_applications",
                visibility=application.visibility,
            )
        return application

    def get_application(
        self, scenario_application_id: str
    ) -> ScenarioDriverApplicationRecord:
        try:
            return self._applications[scenario_application_id]
        except KeyError as exc:
            raise UnknownScenarioApplicationError(
                "scenario_application not found: "
                f"{scenario_application_id!r}"
            ) from exc

    def list_applications(
        self,
    ) -> tuple[ScenarioDriverApplicationRecord, ...]:
        return tuple(self._applications.values())

    def list_by_template(
        self, scenario_driver_template_id: str
    ) -> tuple[ScenarioDriverApplicationRecord, ...]:
        return tuple(
            a
            for a in self._applications.values()
            if a.scenario_driver_template_id
            == scenario_driver_template_id
        )

    def list_by_application_status(
        self, application_status_label: str
    ) -> tuple[ScenarioDriverApplicationRecord, ...]:
        return tuple(
            a
            for a in self._applications.values()
            if a.application_status_label == application_status_label
        )

    def list_by_date(
        self, as_of_date: Any
    ) -> tuple[ScenarioDriverApplicationRecord, ...]:
        iso = _coerce_iso_date(as_of_date)
        return tuple(
            a
            for a in self._applications.values()
            if a.as_of_date == iso
        )

    # -- context shifts ----------------------------------------------

    def add_context_shift(
        self, shift: ScenarioContextShiftRecord
    ) -> ScenarioContextShiftRecord:
        if shift.scenario_context_shift_id in self._context_shifts:
            raise DuplicateScenarioContextShiftError(
                "Duplicate scenario_context_shift_id: "
                f"{shift.scenario_context_shift_id}"
            )
        self._context_shifts[
            shift.scenario_context_shift_id
        ] = shift

        if self.ledger is not None:
            payload = {
                "scenario_context_shift_id": (
                    shift.scenario_context_shift_id
                ),
                "scenario_application_id": (
                    shift.scenario_application_id
                ),
                "scenario_driver_template_id": (
                    shift.scenario_driver_template_id
                ),
                "as_of_date": shift.as_of_date,
                "context_surface_label": shift.context_surface_label,
                "driver_group_label": shift.driver_group_label,
                "scenario_family_label": shift.scenario_family_label,
                "shift_direction_label": shift.shift_direction_label,
                "severity_label": shift.severity_label,
                "affected_actor_scope_label": (
                    shift.affected_actor_scope_label
                ),
                "affected_context_record_ids": list(
                    shift.affected_context_record_ids
                ),
                "affected_evidence_bucket_labels": list(
                    shift.affected_evidence_bucket_labels
                ),
                "expected_annotation_type_label": (
                    shift.expected_annotation_type_label
                ),
                "reasoning_mode": shift.reasoning_mode,
                "reasoning_policy_id": shift.reasoning_policy_id,
                "reasoning_slot": shift.reasoning_slot,
                "evidence_ref_ids": list(shift.evidence_ref_ids),
                "unresolved_ref_count": shift.unresolved_ref_count,
                "boundary_flags": dict(shift.boundary_flags),
                "status": shift.status,
                "visibility": shift.visibility,
            }
            _scan_for_forbidden_keys(
                payload, field_name="ledger payload"
            )
            self.ledger.append(
                event_type="scenario_context_shift_recorded",
                simulation_date=shift.as_of_date,
                object_id=shift.scenario_context_shift_id,
                source=shift.scenario_driver_template_id,
                target=shift.scenario_application_id,
                payload=payload,
                space_id="scenario_applications",
                visibility=shift.visibility,
            )
        return shift

    def get_context_shift(
        self, scenario_context_shift_id: str
    ) -> ScenarioContextShiftRecord:
        try:
            return self._context_shifts[scenario_context_shift_id]
        except KeyError as exc:
            raise UnknownScenarioContextShiftError(
                "scenario_context_shift not found: "
                f"{scenario_context_shift_id!r}"
            ) from exc

    def list_context_shifts(
        self,
    ) -> tuple[ScenarioContextShiftRecord, ...]:
        return tuple(self._context_shifts.values())

    def list_shifts_by_template(
        self, scenario_driver_template_id: str
    ) -> tuple[ScenarioContextShiftRecord, ...]:
        return tuple(
            s
            for s in self._context_shifts.values()
            if s.scenario_driver_template_id
            == scenario_driver_template_id
        )

    def list_shifts_by_application(
        self, scenario_application_id: str
    ) -> tuple[ScenarioContextShiftRecord, ...]:
        return tuple(
            s
            for s in self._context_shifts.values()
            if s.scenario_application_id == scenario_application_id
        )

    def list_shifts_by_context_surface(
        self, context_surface_label: str
    ) -> tuple[ScenarioContextShiftRecord, ...]:
        return tuple(
            s
            for s in self._context_shifts.values()
            if s.context_surface_label == context_surface_label
        )

    def list_shifts_by_driver_group(
        self, driver_group_label: str
    ) -> tuple[ScenarioContextShiftRecord, ...]:
        return tuple(
            s
            for s in self._context_shifts.values()
            if s.driver_group_label == driver_group_label
        )

    def list_shifts_by_scenario_family(
        self, scenario_family_label: str
    ) -> tuple[ScenarioContextShiftRecord, ...]:
        return tuple(
            s
            for s in self._context_shifts.values()
            if s.scenario_family_label == scenario_family_label
        )

    # -- snapshot ----------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        return {
            "scenario_applications": [
                a.to_dict() for a in self._applications.values()
            ],
            "scenario_context_shifts": [
                s.to_dict() for s in self._context_shifts.values()
            ],
        }


# ---------------------------------------------------------------------------
# Family → shift mapping (deterministic, minimal)
#
# v1.18.2 ships exactly the five mappings pinned in the design
# spec. Other families fall back to a single ``no_direct_shift``
# annotation that carries the template's
# ``expected_annotation_type_label`` — so every application emits
# at least one shift, but only the five mapped families project
# onto a concrete context surface.
# ---------------------------------------------------------------------------


def _build_shift_specs(
    template: Any,
) -> tuple[dict[str, str], ...]:
    family = template.scenario_family_label
    if family == "rate_repricing_driver":
        direction = (
            "increase_uncertainty"
            if template.severity_label == "low"
            else "tighten"
        )
        return (
            {
                "context_surface_label": "market_environment",
                "shift_direction_label": direction,
                "expected_annotation_type_label": (
                    "market_environment_change"
                ),
            },
        )
    if family == "credit_tightening_driver":
        return (
            {
                "context_surface_label": "market_environment",
                "shift_direction_label": "tighten",
                "expected_annotation_type_label": (
                    "market_environment_change"
                ),
            },
            {
                "context_surface_label": "financing_review_surface",
                "shift_direction_label": "tighten",
                "expected_annotation_type_label": (
                    "financing_constraint"
                ),
            },
        )
    if family == "funding_window_closure_driver":
        return (
            {
                "context_surface_label": "financing_review_surface",
                "shift_direction_label": "deteriorate",
                "expected_annotation_type_label": (
                    "financing_constraint"
                ),
            },
        )
    if family == "liquidity_stress_driver":
        return (
            {
                "context_surface_label": "interbank_liquidity",
                "shift_direction_label": "deteriorate",
                "expected_annotation_type_label": (
                    "market_environment_change"
                ),
            },
            {
                "context_surface_label": "market_environment",
                "shift_direction_label": "deteriorate",
                "expected_annotation_type_label": (
                    "market_environment_change"
                ),
            },
        )
    if family == "information_gap_driver":
        return (
            {
                "context_surface_label": "attention_surface",
                "shift_direction_label": "information_gap",
                "expected_annotation_type_label": "attention_shift",
            },
        )
    return (
        {
            "context_surface_label": "unknown",
            "shift_direction_label": "no_direct_shift",
            "expected_annotation_type_label": (
                template.expected_annotation_type_label
            ),
        },
    )


# ---------------------------------------------------------------------------
# apply_scenario_driver — deterministic application helper
# ---------------------------------------------------------------------------


def apply_scenario_driver(
    kernel: "WorldKernel",
    *,
    scenario_driver_template_id: str,
    as_of_date: Any,
    source_context_record_ids: Iterable[str] = (),
    application_id: str | None = None,
    unresolved_ref_count: int = 0,
    metadata: Mapping[str, Any] | None = None,
) -> ScenarioDriverApplicationRecord:
    """Deterministic, append-only application of a v1.18.1
    scenario driver template.

    Behaviour pinned by the v1.18.0 design and re-pinned by
    v1.18.2 trip-wire tests:

    - Reads only the named template via
      :meth:`ScenarioDriverTemplateBook.get_template` and uses
      only the cited ``source_context_record_ids``. Performs **no**
      global scan over kernel books.
    - Emits one
      :class:`ScenarioDriverApplicationRecord` and one or more
      :class:`ScenarioContextShiftRecord` records via the existing
      append-only :meth:`ScenarioApplicationBook.add_application`
      / :meth:`ScenarioApplicationBook.add_context_shift`
      interface.
    - **Never mutates** any pre-existing context record. The
      :class:`MarketEnvironmentBook` /
      :class:`FirmFinancialStateBook` / :class:`PriceBook` /
      :class:`InterbankLiquidityStateBook` /
      :class:`CorporateFinancingPathBook` snapshots are
      byte-identical pre / post call.
    - **Does not decide actor behaviour**. No actor decision, no
      investor action, no bank approval, no trading, no financing
      execution, no investment advice, no LLM execution.
    - Carries the v1.18.0 audit metadata on every emitted record:
      ``reasoning_mode = "rule_based_fallback"`` (binding),
      ``reasoning_policy_id``, ``reasoning_slot =
      "future_llm_compatible"``, ``evidence_ref_ids``,
      ``unresolved_ref_count``, ``boundary_flags``.
    """
    template = kernel.scenario_drivers.get_template(
        scenario_driver_template_id
    )
    iso_date = _coerce_iso_date(as_of_date)
    cited_ids = _validate_string_tuple(
        source_context_record_ids,
        field_name="source_context_record_ids",
    )

    if application_id is None:
        application_id = (
            f"scenario_application:{scenario_driver_template_id}:"
            f"{iso_date}"
        )
    if (
        not isinstance(unresolved_ref_count, int)
        or isinstance(unresolved_ref_count, bool)
        or unresolved_ref_count < 0
    ):
        raise ValueError(
            "unresolved_ref_count must be a non-negative int"
        )

    shift_specs = _build_shift_specs(template)
    shift_records: list[ScenarioContextShiftRecord] = []
    base_evidence_refs = (
        scenario_driver_template_id,
    ) + cited_ids
    for idx, spec in enumerate(shift_specs):
        shift_id = (
            f"scenario_context_shift:{application_id}:"
            f"{idx:02d}"
        )
        shift = ScenarioContextShiftRecord(
            scenario_context_shift_id=shift_id,
            scenario_application_id=application_id,
            scenario_driver_template_id=scenario_driver_template_id,
            as_of_date=iso_date,
            context_surface_label=spec["context_surface_label"],
            driver_group_label=template.driver_group_label,
            scenario_family_label=template.scenario_family_label,
            shift_direction_label=spec["shift_direction_label"],
            severity_label=template.severity_label,
            affected_actor_scope_label=(
                template.affected_actor_scope_label
            ),
            affected_context_record_ids=cited_ids,
            affected_evidence_bucket_labels=(
                template.affected_evidence_bucket_labels
            ),
            expected_annotation_type_label=spec[
                "expected_annotation_type_label"
            ],
            evidence_ref_ids=base_evidence_refs,
            unresolved_ref_count=unresolved_ref_count,
        )
        shift_records.append(shift)

    if unresolved_ref_count > 0:
        application_status_label = "degraded_unresolved_refs"
    elif shift_records:
        application_status_label = "applied_as_context_shift"
    else:
        application_status_label = "prepared"

    application = ScenarioDriverApplicationRecord(
        scenario_application_id=application_id,
        scenario_driver_template_id=scenario_driver_template_id,
        as_of_date=iso_date,
        application_status_label=application_status_label,
        source_template_ids=(scenario_driver_template_id,),
        source_context_record_ids=cited_ids,
        emitted_context_shift_ids=tuple(
            s.scenario_context_shift_id for s in shift_records
        ),
        unresolved_ref_count=unresolved_ref_count,
        metadata=dict(metadata or {}),
    )

    kernel.scenario_applications.add_application(application)
    for shift in shift_records:
        kernel.scenario_applications.add_context_shift(shift)

    return application
