"""
v1.18.1 — ``ScenarioDriverTemplate`` storage.

Storage-only foundation for the v1.18 scenario-driver / exogenous
context-template layer. A :class:`ScenarioDriverTemplate` names a
synthetic exogenous condition (``rate_repricing_driver``,
``liquidity_stress_driver``, ``customer_churn_driver``, …) that
v1.18.2 will project onto pre-existing FWE evidence / context
surfaces. v1.18.1 itself **does not apply** any scenario; it
only stores templates.

Critical design constraint pinned at v1.18.0 (binding):

- A scenario template **never** carries a sentence of the form
  "actor decides X". The closest a template gets to actor
  behaviour is an :class:`expected_annotation_type_label` that
  names the *category* of inspection annotation a downstream
  mechanism may emit — never the response itself.
- Decision criteria stay modular and replaceable. v1.18.x
  classifier / mapping rules are explicitly tagged
  ``reasoning_mode = "rule_based_fallback"`` so a future audited
  reasoning policy (potentially LLM-backed in private JFWE) can
  replace them. v1.18.1 only stores the marker; no LLM call,
  no learned model, no stochastic behaviour rule.
- Six concerns are kept structurally separate: evidence
  collection, driver classification, ``ActorReasoningInputFrame``,
  ``ReasoningPolicySlot``, output label, audit metadata.

The module is **runtime-book-free** beyond the v0/v1 ledger +
clock convention shared by every other storage book — it does
not import any source-of-truth book on the engine side.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set vocabularies
#
# Every label tuple here is the v1.18.0 design pin. v1.18+ may
# extend a vocabulary via a single coordinated change; the
# closed-set discipline is binding (every record validates against
# these frozensets at construction).
# ---------------------------------------------------------------------------


SCENARIO_FAMILY_LABELS: frozenset[str] = frozenset(
    {
        "rate_repricing_driver",
        "credit_tightening_driver",
        "funding_window_closure_driver",
        "liquidity_stress_driver",
        "risk_off_driver",
        "sector_demand_deterioration_driver",
        "market_access_reopening_driver",
        "refinancing_wall_driver",
        "input_cost_pressure_driver",
        "information_gap_driver",
        "regulatory_risk_driver",
        "litigation_risk_driver",
        "supply_constraint_driver",
        "customer_churn_driver",
        "technology_substitution_driver",
        "policy_subsidy_driver",
        "thematic_attention_driver",
        "short_squeeze_attention_driver",
        "index_inclusion_exclusion_driver",
        "capital_policy_uncertainty_driver",
        "unknown",
    }
)


DRIVER_GROUP_LABELS: frozenset[str] = frozenset(
    {
        "macro_rates",
        "credit_liquidity",
        "demand_earnings",
        "cost_supply",
        "regulation_legal",
        "ownership_market_structure",
        "technology_competition",
        "capital_structure_refinancing",
        "information_attention",
        "unknown",
    }
)


EVENT_DATE_POLICY_LABELS: frozenset[str] = frozenset(
    {
        "quarter_start",
        "quarter_end",
        "nearest_reporting_date",
        "explicit_date",
        "display_only_date",
        "unknown",
    }
)


SEVERITY_LABELS: frozenset[str] = frozenset(
    {
        "low",
        "medium",
        "high",
        "stress",
        "unknown",
    }
)


AFFECTED_ACTOR_SCOPE_LABELS: frozenset[str] = frozenset(
    {
        "market_wide",
        "all_actors",
        "firms_only",
        "investors_only",
        "banks_only",
        "selected_firms",
        "selected_investors",
        "selected_banks",
        "selected_securities",
        "unknown",
    }
)


EXPECTED_ANNOTATION_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "market_environment_change",
        "attention_shift",
        "market_pressure_change",
        "financing_constraint",
        "causal_checkpoint",
        "synthetic_event",
        "unknown",
    }
)


REASONING_MODE_LABELS: frozenset[str] = frozenset(
    {
        "rule_based_fallback",
        "future_llm_compatible",
        "external_policy_slot",
        "unknown",
    }
)


REASONING_SLOT_LABELS: frozenset[str] = frozenset(
    {
        "future_llm_compatible",
        "rule_based_only",
        "not_applicable",
        "unknown",
    }
)


STATUS_LABELS: frozenset[str] = frozenset(
    {
        "draft",
        "active",
        "stale",
        "superseded",
        "archived",
        "unknown",
    }
)


VISIBILITY_LABELS: frozenset[str] = frozenset(
    {
        "internal_only",
        "shared_internal",
        "external_audit",
    }
)


# v1.18.0 hard naming boundary on payload + metadata. Tests scan
# dataclass field names, payload keys, and metadata keys for any
# of the forbidden names below. Anything that would read as
# canonical business judgment, an actor decision, a price, a
# forecast, real data, a Japan calibration, or LLM execution is
# disjoint from the scenario-template surface by construction.
FORBIDDEN_SCENARIO_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "firm_decision",
        "investor_action",
        "bank_approval",
        "trading_decision",
        "optimal_capital_structure",
        "buy",
        "sell",
        "order",
        "trade",
        "execution",
        "price",
        "market_price",
        "predicted_index",
        "forecast_path",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "real_data_value",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
    }
)


# v1.18.0 default reasoning-mode binding. Every template ships
# with this default unless the caller explicitly overrides; the
# v1.18.0 design note pins this choice and the
# `test_default_reasoning_mode_is_rule_based_fallback` regression
# test enforces it.
DEFAULT_REASONING_MODE: str = "rule_based_fallback"
DEFAULT_REASONING_SLOT: str = "future_llm_compatible"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ScenarioDriverError(Exception):
    """Base class for scenario-driver storage errors."""


class DuplicateScenarioDriverTemplateError(ScenarioDriverError):
    """Raised when a scenario_driver_template_id is added twice."""


class UnknownScenarioDriverTemplateError(
    ScenarioDriverError, KeyError
):
    """Raised when a scenario_driver_template_id is not found."""


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


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    """Reject any v1.18.0 forbidden field name appearing in a
    metadata or payload mapping. Tests pin this trip-wire."""
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_SCENARIO_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key {key!r} "
                "(v1.18.0 hard naming boundary — scenario templates "
                "do not carry actor-decision / price / forecast / "
                "advice / real-data / Japan-calibration / LLM "
                "fields)"
            )


# ---------------------------------------------------------------------------
# ScenarioDriverTemplate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioDriverTemplate:
    """Immutable template naming a synthetic exogenous scenario
    driver. v1.18.1 stores templates only; v1.18.2 will project
    them by **emitting new evidence / context records that cite
    the scenario driver via plain-id citations** — never mutating
    a pre-existing context record.

    The dataclass:

    - has **no** ``confidence`` field — templates are not
      predictions.
    - has **no** numeric magnitude field — templates are
      *category* shifts, not magnitudes (magnitudes, if any,
      land in ``metadata`` as bounded ordinal scalars at
      v1.18.2; never as prices, rates, or spreads).
    - has **no** actor-decision field — templates do not decide.
    - is jurisdiction-neutral by construction; tests pin the
      absence of forbidden tokens in the module text and
      payload keys.

    Reasoning fields (``reasoning_mode``, ``reasoning_policy_id``,
    ``reasoning_slot``) carry the v1.18.0 audit shape so a future
    LLM-mode reasoning policy can replace the v1.18.x rule-based
    fallback without changing the audit surface.
    """

    scenario_driver_template_id: str
    scenario_family_label: str
    driver_group_label: str
    driver_label: str
    event_date_policy_label: str
    severity_label: str
    affected_actor_scope_label: str
    expected_annotation_type_label: str
    affected_context_surface_labels: tuple[str, ...] = field(
        default_factory=tuple
    )
    affected_evidence_bucket_labels: tuple[str, ...] = field(
        default_factory=tuple
    )
    reasoning_mode: str = DEFAULT_REASONING_MODE
    reasoning_policy_id: str = "v1.18.1:storage_only:rule_based_fallback"
    reasoning_slot: str = DEFAULT_REASONING_SLOT
    status: str = "active"
    visibility: str = "internal_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "scenario_driver_template_id",
        "scenario_family_label",
        "driver_group_label",
        "driver_label",
        "event_date_policy_label",
        "severity_label",
        "affected_actor_scope_label",
        "expected_annotation_type_label",
        "reasoning_mode",
        "reasoning_policy_id",
        "reasoning_slot",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[tuple[tuple[str, frozenset[str]], ...]] = (
        ("scenario_family_label",          SCENARIO_FAMILY_LABELS),
        ("driver_group_label",             DRIVER_GROUP_LABELS),
        ("event_date_policy_label",        EVENT_DATE_POLICY_LABELS),
        ("severity_label",                 SEVERITY_LABELS),
        ("affected_actor_scope_label",     AFFECTED_ACTOR_SCOPE_LABELS),
        ("expected_annotation_type_label", EXPECTED_ANNOTATION_TYPE_LABELS),
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
        # Field-name guard against any future field rename that
        # might collide with the v1.18.0 forbidden list. Pinned
        # by ``test_dataclass_field_names_disjoint_from_forbidden``.
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_SCENARIO_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the v1.18.0 "
                    "forbidden field-name set"
                )
        object.__setattr__(
            self,
            "affected_context_surface_labels",
            _validate_string_tuple(
                self.affected_context_surface_labels,
                field_name="affected_context_surface_labels",
            ),
        )
        object.__setattr__(
            self,
            "affected_evidence_bucket_labels",
            _validate_string_tuple(
                self.affected_evidence_bucket_labels,
                field_name="affected_evidence_bucket_labels",
            ),
        )
        # Metadata is opaque but cannot smuggle a forbidden key.
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(metadata_dict, field_name="metadata")
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_driver_template_id": self.scenario_driver_template_id,
            "scenario_family_label": self.scenario_family_label,
            "driver_group_label": self.driver_group_label,
            "driver_label": self.driver_label,
            "event_date_policy_label": self.event_date_policy_label,
            "severity_label": self.severity_label,
            "affected_actor_scope_label": self.affected_actor_scope_label,
            "expected_annotation_type_label": (
                self.expected_annotation_type_label
            ),
            "affected_context_surface_labels": list(
                self.affected_context_surface_labels
            ),
            "affected_evidence_bucket_labels": list(
                self.affected_evidence_bucket_labels
            ),
            "reasoning_mode": self.reasoning_mode,
            "reasoning_policy_id": self.reasoning_policy_id,
            "reasoning_slot": self.reasoning_slot,
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ScenarioDriverTemplateBook
# ---------------------------------------------------------------------------


@dataclass
class ScenarioDriverTemplateBook:
    """Append-only storage for v1.18.1
    :class:`ScenarioDriverTemplate` instances. Mirrors the
    v1.15.4 / v1.15.6 storage-book convention: emits exactly
    one ledger record per :meth:`add_template` call
    (``RecordType.SCENARIO_DRIVER_TEMPLATE_RECORDED``) with
    ``source = scenario_family_label``. The book mutates no
    other source-of-truth book, including the ``PriceBook``.

    Idempotency: re-adding a template with the same id raises
    :class:`DuplicateScenarioDriverTemplateError` and emits
    **no** additional ledger record (pinned by
    ``test_duplicate_template_emits_no_extra_ledger_record``).
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _templates: dict[str, ScenarioDriverTemplate] = field(
        default_factory=dict
    )

    def _now(self) -> datetime:
        if self.clock is not None:
            try:
                return self.clock.current_datetime()
            except Exception:
                pass
        return datetime.now(timezone.utc)

    def add_template(
        self,
        template: ScenarioDriverTemplate,
        *,
        simulation_date: Any = None,
    ) -> ScenarioDriverTemplate:
        if template.scenario_driver_template_id in self._templates:
            raise DuplicateScenarioDriverTemplateError(
                "Duplicate scenario_driver_template_id: "
                f"{template.scenario_driver_template_id}"
            )
        self._templates[
            template.scenario_driver_template_id
        ] = template

        if self.ledger is not None:
            payload = {
                "scenario_driver_template_id": (
                    template.scenario_driver_template_id
                ),
                "scenario_family_label": template.scenario_family_label,
                "driver_group_label": template.driver_group_label,
                "driver_label": template.driver_label,
                "event_date_policy_label": (
                    template.event_date_policy_label
                ),
                "severity_label": template.severity_label,
                "affected_actor_scope_label": (
                    template.affected_actor_scope_label
                ),
                "expected_annotation_type_label": (
                    template.expected_annotation_type_label
                ),
                "affected_context_surface_labels": list(
                    template.affected_context_surface_labels
                ),
                "affected_evidence_bucket_labels": list(
                    template.affected_evidence_bucket_labels
                ),
                "reasoning_mode": template.reasoning_mode,
                "reasoning_policy_id": template.reasoning_policy_id,
                "reasoning_slot": template.reasoning_slot,
                "status": template.status,
                "visibility": template.visibility,
            }
            # Trip-wire: the ledger payload must never carry a
            # forbidden field name. Pinned by a regression test.
            _scan_for_forbidden_keys(
                payload, field_name="ledger payload"
            )
            sim_date: Any = (
                simulation_date
                if simulation_date is not None
                else self._now()
            )
            self.ledger.append(
                event_type="scenario_driver_template_recorded",
                simulation_date=sim_date,
                object_id=template.scenario_driver_template_id,
                source=template.scenario_family_label,
                payload=payload,
                space_id="scenario_drivers",
                visibility=template.visibility,
            )
        return template

    def get_template(
        self, scenario_driver_template_id: str
    ) -> ScenarioDriverTemplate:
        try:
            return self._templates[scenario_driver_template_id]
        except KeyError as exc:
            raise UnknownScenarioDriverTemplateError(
                "scenario_driver_template not found: "
                f"{scenario_driver_template_id!r}"
            ) from exc

    def list_templates(
        self,
    ) -> tuple[ScenarioDriverTemplate, ...]:
        return tuple(self._templates.values())

    def list_by_family(
        self, scenario_family_label: str
    ) -> tuple[ScenarioDriverTemplate, ...]:
        return tuple(
            t
            for t in self._templates.values()
            if t.scenario_family_label == scenario_family_label
        )

    def list_by_group(
        self, driver_group_label: str
    ) -> tuple[ScenarioDriverTemplate, ...]:
        return tuple(
            t
            for t in self._templates.values()
            if t.driver_group_label == driver_group_label
        )

    def list_by_severity(
        self, severity_label: str
    ) -> tuple[ScenarioDriverTemplate, ...]:
        return tuple(
            t
            for t in self._templates.values()
            if t.severity_label == severity_label
        )

    def list_by_actor_scope(
        self, affected_actor_scope_label: str
    ) -> tuple[ScenarioDriverTemplate, ...]:
        return tuple(
            t
            for t in self._templates.values()
            if t.affected_actor_scope_label == affected_actor_scope_label
        )

    def list_by_status(
        self, status: str
    ) -> tuple[ScenarioDriverTemplate, ...]:
        return tuple(
            t for t in self._templates.values() if t.status == status
        )

    def list_by_expected_annotation_type(
        self, expected_annotation_type_label: str
    ) -> tuple[ScenarioDriverTemplate, ...]:
        return tuple(
            t
            for t in self._templates.values()
            if t.expected_annotation_type_label
            == expected_annotation_type_label
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "scenario_driver_templates": [
                t.to_dict() for t in self._templates.values()
            ],
        }
