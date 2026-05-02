"""
v1.9.1 Living World Trace Report.

A read-only reporting layer over the v1.9.0 multi-period living
reference world. Turns a ``LivingReferenceWorldResult`` plus the
matching slice of ``kernel.ledger.records`` into:

- a deterministic, immutable :class:`LivingWorldTraceReport`,
- a deterministic dict via :meth:`LivingWorldTraceReport.to_dict`,
  and
- a deterministic compact Markdown rendering via
  :func:`render_living_world_markdown`.

The reporter exists for **explainability**, not modeling. It
introduces no new ledger types, no new economic behavior, no new
routines, no scheduler hooks, no kernel mutation. Every walk over
``kernel.ledger.records`` and every read on
``kernel.attention.get_selection(...)`` is read-only.

Relationship to v1.8.15
-----------------------

This module mirrors `world/ledger_trace_report.py` (the v1.8.15
single-chain reporter) for the v1.9.0 multi-period sweep. The
design contract was audited in v1.9.1-prep and lives in
``docs/v1_9_living_world_report_contract.md``; v1.9.1 implements
that contract.

The infra prelude
-----------------

v1.9.0's ``run_living_reference_world`` does idempotent
registration (interactions + per-firm corporate routines + per-
actor profiles + review interactions + review routines)
**before** entering the period loop. Those writes form an
**infra prelude** between
``result.ledger_record_count_before`` and
``per_period_summaries[0].metadata["ledger_record_count_before"]``.
The reporter computes ``infra_record_count`` from the algebraic
relationship pinned in v1.9.1-prep:

    infra_record_count
        = result.created_record_count
            - sum(p.record_count_created for p in per_period_summaries)

and surfaces it separately in the Setup section so the per-period
table's totals add up honestly.

Determinism
-----------

For a given (kernel, living_world_result) pair, the report and
its ``to_dict`` / Markdown projections are byte-identical across
fresh process invocations. The reporter:

- sorts `record_type_counts` by event type;
- preserves ledger order in `ordered_record_ids` and the
  per-period `corporate_signal_ids` / review-signal id tuples;
- sorts `shared_selected_refs` / `investor_only_refs` /
  `bank_only_refs` alphabetically (set differences have no
  natural order, so we pick a stable one);
- sorts `investor_selected_ref_counts` and
  `bank_selected_ref_counts` by `(period_id, actor_id)`.

No timestamps, no wall-clock dependencies, no floating-point
accumulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from world.ledger import RecordType
from world.reference_living_world import (
    LivingReferencePeriodSummary,
    LivingReferenceWorldResult,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


_DEFAULT_CHAIN_NAME: str = "living_reference_world"


# The seven event types the v1.9.0 sweep emits across the infra
# prelude and the period loop. Used by the validation pass to flag
# missing components without crashing.
_EXPECTED_LIVING_WORLD_EVENT_TYPES: tuple[str, ...] = (
    RecordType.INTERACTION_ADDED.value,
    RecordType.ROUTINE_ADDED.value,
    RecordType.ROUTINE_RUN_RECORDED.value,
    RecordType.SIGNAL_ADDED.value,
    RecordType.ATTENTION_PROFILE_ADDED.value,
    RecordType.OBSERVATION_MENU_CREATED.value,
    RecordType.OBSERVATION_SET_SELECTED.value,
)


# Hard-boundary statement. Emitted verbatim under the
# `## Boundaries` section of the Markdown report. Per the v1.9.1
# task spec, extended at v1.10.5 to cover the engagement /
# strategic-response layer (no voting / proxy filing / public
# campaign / corporate-action execution / disclosure filing /
# demand or revenue forecasting / firm financial-statement
# updates). The v1.9.1 preamble is preserved verbatim so existing
# canonical snapshots that read the prefix still match.
_BOUNDARY_STATEMENT: str = (
    "No price formation, no trading, no lending decisions, "
    "no valuation behavior, no Japan calibration, no real data, "
    "no investment advice. "
    "v1.10.5 engagement / strategic-response layer: no voting, "
    "no proxy filing, no public-campaign execution, no exit "
    "execution, no AGM/EGM action, no corporate-action execution "
    "(buyback / dividend / divestment / merger / governance "
    "change), no disclosure-filing execution, no demand / sales "
    "/ revenue forecasting, no firm financial-statement updates. "
    "v1.11.0 capital-market surface: no price formation, no "
    "yield-curve calibration, no order matching, no clearing, no "
    "quote dissemination, no security recommendation, no DCM / "
    "ECM execution, no portfolio-allocation decisions; market "
    "conditions are synthetic context only. "
    "v1.11.1 capital-market readout: deterministic banker-"
    "readable labels derived from v1.11.0 conditions; no spread "
    "calibration, no yield calibration, no market forecast, no "
    "deal advice, no transaction recommendation; readout / "
    "report only. "
    "v1.12.0 firm financial latent state: synthetic [0, 1] "
    "ordering scalars updated period-over-period by a small "
    "documented rule set; no revenue, no sales, no EBITDA, no "
    "net income, no cash balance, no debt amount, no real "
    "financial statement, no forecast, no actual / accounting "
    "value, no investment recommendation; latent ordering only. "
    "v1.12.1 investor intent signal: pre-action / pre-decision "
    "review posture labels conditioned on cited evidence; no "
    "order submission, no trade, no rebalancing, no buy / sell "
    "/ overweight / underweight execution, no target weights, "
    "no expected return, no target price, no security "
    "recommendation, no investment advice, no portfolio "
    "allocation; non-binding labels only. "
    "v1.12.2 market environment state: nine compact "
    "jurisdiction-neutral regime labels (liquidity / volatility "
    "/ credit / funding / risk_appetite / rate_environment / "
    "refinancing_window / equity_valuation / "
    "overall_market_access) derived from v1.11.0 conditions + "
    "v1.11.1 readout; no price, no yield, no spread, no index "
    "level, no forecast, no expected return, no recommendation, "
    "no target price, no target weight, no order, no trade, no "
    "allocation; labels-only context for downstream agents."
)


# ---------------------------------------------------------------------------
# Per-period report record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LivingWorldPeriodReport:
    """
    Immutable summary of one living-world period as projected into
    the report.

    Mirrors ``LivingReferencePeriodSummary`` plus per-period event-
    type counts and any per-period warnings the reporter detected.
    Counts derived from collections (``record_type_counts``) are
    sorted for determinism; ledger-order tuples
    (``corporate_signal_ids`` / review-signal id tuples) preserve
    the order each component helper wrote them in.
    """

    period_id: str
    as_of_date: str
    record_count_created: int
    corporate_report_count: int
    corporate_signal_ids: tuple[str, ...]
    investor_menu_count: int
    bank_menu_count: int
    investor_selection_count: int
    bank_selection_count: int
    investor_review_count: int
    bank_review_count: int
    investor_review_signal_ids: tuple[str, ...]
    bank_review_signal_ids: tuple[str, ...]
    # v1.9.6 additive: pressure assessment + valuation refresh.
    # Default 0 so older v1.9.0 result objects (without these
    # fields) still construct cleanly.
    pressure_signal_count: int = 0
    valuation_count: int = 0
    # v1.9.7 additive: bank credit review lite. Default 0 for
    # backwards compat.
    credit_review_signal_count: int = 0
    # v1.10.5 additive: engagement / strategic-response layer.
    # Default 0 for backwards compat with pre-v1.10 result objects.
    industry_condition_count: int = 0
    stewardship_theme_count: int = 0
    dialogue_count: int = 0
    investor_escalation_candidate_count: int = 0
    corporate_strategic_response_candidate_count: int = 0
    # v1.11.0 additive: capital-market condition surface count.
    # Default 0 for backwards compat with pre-v1.11 result objects.
    market_condition_count: int = 0
    # v1.11.1 additive: capital-market readout count (one per
    # period; the period summary carries one readout id per
    # period when v1.11.1 is wired).
    capital_market_readout_count: int = 0
    # v1.12.2 additive: market-environment-state record count
    # (one per period when v1.12.2 is wired) plus the period's
    # nine compact regime labels (lifted from the
    # ``MarketEnvironmentStateRecord``). When the period has no
    # environment state, the labels default to empty strings —
    # the renderer skips empty values.
    market_environment_state_count: int = 0
    liquidity_regime: str = ""
    volatility_regime: str = ""
    credit_regime: str = ""
    funding_regime: str = ""
    risk_appetite_regime: str = ""
    rate_environment: str = ""
    refinancing_window: str = ""
    equity_valuation_regime: str = ""
    overall_market_access_regime_label: str = ""
    # v1.12.0 additive: firm-financial-state record counts +
    # average pressure scalars across the period's firms. Used
    # by the Markdown renderer's "## Firm financial states"
    # section.
    firm_financial_state_count: int = 0
    avg_margin_pressure: float = 0.0
    avg_liquidity_pressure: float = 0.0
    avg_debt_service_pressure: float = 0.0
    avg_market_access_pressure: float = 0.0
    avg_funding_need_intensity: float = 0.0
    avg_response_readiness: float = 0.0
    # v1.12.1 additive: investor-intent record counts + a
    # histogram of intent_direction labels (sorted tuple of
    # (label, count) pairs for determinism). Used by the
    # Markdown renderer's "## Investor intent" section.
    investor_intent_count: int = 0
    investor_intent_direction_counts: tuple[tuple[str, int], ...] = field(
        default_factory=tuple
    )
    # v1.11.1 additive: per-period banker-readable labels lifted
    # from the period's CapitalMarketReadoutRecord (if any). When
    # the period has no readout, the labels default to empty
    # strings — the report renderer skips empty values.
    rates_tone: str = ""
    credit_tone: str = ""
    equity_tone: str = ""
    funding_window_tone: str = ""
    liquidity_tone: str = ""
    volatility_tone: str = ""
    overall_market_access_label: str = ""
    record_type_counts: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.period_id, str) or not self.period_id:
            raise ValueError("period_id must be a non-empty string")
        if not isinstance(self.as_of_date, str) or not self.as_of_date:
            raise ValueError("as_of_date must be a non-empty string")
        for name in (
            "record_count_created",
            "corporate_report_count",
            "investor_menu_count",
            "bank_menu_count",
            "investor_selection_count",
            "bank_selection_count",
            "investor_review_count",
            "bank_review_count",
            "pressure_signal_count",
            "valuation_count",
            "credit_review_signal_count",
            "industry_condition_count",
            "stewardship_theme_count",
            "dialogue_count",
            "investor_escalation_candidate_count",
            "corporate_strategic_response_candidate_count",
            "market_condition_count",
            "capital_market_readout_count",
            "market_environment_state_count",
            "firm_financial_state_count",
            "investor_intent_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"{name} must be a non-negative int; got {value!r}"
                )

        for tuple_field_name in (
            "corporate_signal_ids",
            "investor_review_signal_ids",
            "bank_review_signal_ids",
            "warnings",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            object.__setattr__(self, tuple_field_name, value)

        normalized_counts: list[tuple[str, int]] = []
        for entry in self.record_type_counts:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not isinstance(entry[0], str)
                or not entry[0]
                or not isinstance(entry[1], int)
                or entry[1] < 0
            ):
                raise ValueError(
                    "record_type_counts entries must be (non-empty str, "
                    f"non-negative int); got {entry!r}"
                )
            normalized_counts.append((entry[0], entry[1]))
        object.__setattr__(
            self,
            "record_type_counts",
            tuple(sorted(normalized_counts)),
        )

        # v1.12.0 — bounded synthetic average pressures in [0, 1].
        # Reject bool to match the v1.11.0 / v1.11.1 / v1.12.0
        # bounded-numeric idiom.
        for name in (
            "avg_margin_pressure",
            "avg_liquidity_pressure",
            "avg_debt_service_pressure",
            "avg_market_access_pressure",
            "avg_funding_need_intensity",
            "avg_response_readiness",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number")
            if not (0.0 <= float(value) <= 1.0):
                raise ValueError(
                    f"{name} must be between 0 and 1 inclusive"
                )
            object.__setattr__(self, name, float(value))

        # v1.12.1 — investor-intent direction histogram. Each entry
        # is a (label, count) tuple; the sorted tuple is what we
        # store, for determinism.
        normalized_intent_counts: list[tuple[str, int]] = []
        for entry in self.investor_intent_direction_counts:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not isinstance(entry[0], str)
                or not entry[0]
                or not isinstance(entry[1], int)
                or entry[1] < 0
            ):
                raise ValueError(
                    "investor_intent_direction_counts entries must be "
                    "(non-empty str, non-negative int); "
                    f"got {entry!r}"
                )
            normalized_intent_counts.append((entry[0], entry[1]))
        object.__setattr__(
            self,
            "investor_intent_direction_counts",
            tuple(sorted(normalized_intent_counts)),
        )

        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_id": self.period_id,
            "as_of_date": self.as_of_date,
            "record_count_created": self.record_count_created,
            "corporate_report_count": self.corporate_report_count,
            "corporate_signal_ids": list(self.corporate_signal_ids),
            "investor_menu_count": self.investor_menu_count,
            "bank_menu_count": self.bank_menu_count,
            "investor_selection_count": self.investor_selection_count,
            "bank_selection_count": self.bank_selection_count,
            "investor_review_count": self.investor_review_count,
            "bank_review_count": self.bank_review_count,
            "investor_review_signal_ids": list(self.investor_review_signal_ids),
            "bank_review_signal_ids": list(self.bank_review_signal_ids),
            "pressure_signal_count": self.pressure_signal_count,
            "valuation_count": self.valuation_count,
            "credit_review_signal_count": self.credit_review_signal_count,
            "industry_condition_count": self.industry_condition_count,
            "stewardship_theme_count": self.stewardship_theme_count,
            "dialogue_count": self.dialogue_count,
            "investor_escalation_candidate_count": (
                self.investor_escalation_candidate_count
            ),
            "corporate_strategic_response_candidate_count": (
                self.corporate_strategic_response_candidate_count
            ),
            "market_condition_count": self.market_condition_count,
            "capital_market_readout_count": self.capital_market_readout_count,
            "market_environment_state_count": (
                self.market_environment_state_count
            ),
            "liquidity_regime": self.liquidity_regime,
            "volatility_regime": self.volatility_regime,
            "credit_regime": self.credit_regime,
            "funding_regime": self.funding_regime,
            "risk_appetite_regime": self.risk_appetite_regime,
            "rate_environment": self.rate_environment,
            "refinancing_window": self.refinancing_window,
            "equity_valuation_regime": self.equity_valuation_regime,
            "overall_market_access_regime_label": (
                self.overall_market_access_regime_label
            ),
            "firm_financial_state_count": self.firm_financial_state_count,
            "avg_margin_pressure": self.avg_margin_pressure,
            "avg_liquidity_pressure": self.avg_liquidity_pressure,
            "avg_debt_service_pressure": self.avg_debt_service_pressure,
            "avg_market_access_pressure": self.avg_market_access_pressure,
            "avg_funding_need_intensity": self.avg_funding_need_intensity,
            "avg_response_readiness": self.avg_response_readiness,
            "investor_intent_count": self.investor_intent_count,
            "investor_intent_direction_counts": [
                [label, count]
                for label, count in self.investor_intent_direction_counts
            ],
            "rates_tone": self.rates_tone,
            "credit_tone": self.credit_tone,
            "equity_tone": self.equity_tone,
            "funding_window_tone": self.funding_window_tone,
            "liquidity_tone": self.liquidity_tone,
            "volatility_tone": self.volatility_tone,
            "overall_market_access_label": self.overall_market_access_label,
            "record_type_counts": [
                [event_type, count]
                for event_type, count in self.record_type_counts
            ],
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Aggregate report record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LivingWorldTraceReport:
    """
    Immutable aggregate report over one ``LivingReferenceWorldResult``.

    Field semantics
    ---------------
    - ``report_id`` is a stable id derived from the chain. Default
      is ``"report:living_reference_world:" + run_id``; the caller
      may override.
    - ``run_id`` mirrors the result.
    - ``period_count``, ``firm_count``, ``investor_count``,
      ``bank_count`` are setup-summary integers.
    - ``ledger_record_count_before`` / ``ledger_record_count_after``
      mirror the result so the slice can be re-walked from the
      report alone.
    - ``created_record_count`` is the total ledger delta.
    - ``infra_record_count`` is computed from the v1.9.1-prep
      algebraic relationship.
    - ``per_period_record_count_total`` is
      ``sum(p.record_count_created)`` and is provided so the
      Markdown's per-period totals row is reachable from the
      report alone.
    - ``record_type_counts`` is the **overall** ledger-slice
      event-type breakdown, sorted by event type.
    - ``period_summaries`` carries one
      :class:`LivingWorldPeriodReport` per period, in input order.
    - ``investor_selected_ref_counts`` and
      ``bank_selected_ref_counts`` are tuples of
      ``(actor_id, period_id, selected_ref_count)`` triples sorted
      by ``(period_id, actor_id)``.
    - ``shared_selected_refs`` / ``investor_only_refs`` /
      ``bank_only_refs`` are aggregated set differences over the
      union of investor selections and the union of bank selections
      across all periods. Sorted alphabetically for determinism.
    - ``ordered_record_ids`` is the ledger slice's ``object_id``
      tuple in ledger order (matches
      ``LivingReferenceWorldResult.created_record_ids`` when the
      ledger has not been touched).
    - ``warnings`` is a tuple of free-form strings for
      non-fatal validation issues.
    - ``metadata`` carries audit fields (renderer version, format
      version, the boundary statement, echoed counts).
    """

    report_id: str
    run_id: str
    period_count: int
    firm_count: int
    investor_count: int
    bank_count: int
    ledger_record_count_before: int
    ledger_record_count_after: int
    created_record_count: int
    infra_record_count: int
    per_period_record_count_total: int
    record_type_counts: tuple[tuple[str, int], ...]
    period_summaries: tuple[LivingWorldPeriodReport, ...]
    investor_selected_ref_counts: tuple[tuple[str, str, int], ...] = field(
        default_factory=tuple
    )
    bank_selected_ref_counts: tuple[tuple[str, str, int], ...] = field(
        default_factory=tuple
    )
    shared_selected_refs: tuple[str, ...] = field(default_factory=tuple)
    investor_only_refs: tuple[str, ...] = field(default_factory=tuple)
    bank_only_refs: tuple[str, ...] = field(default_factory=tuple)
    ordered_record_ids: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.report_id, str) or not self.report_id:
            raise ValueError("report_id must be a non-empty string")
        if not isinstance(self.run_id, str) or not self.run_id:
            raise ValueError("run_id must be a non-empty string")
        for name in (
            "period_count",
            "firm_count",
            "investor_count",
            "bank_count",
            "ledger_record_count_before",
            "ledger_record_count_after",
            "created_record_count",
            "infra_record_count",
            "per_period_record_count_total",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"{name} must be a non-negative int; got {value!r}"
                )

        if (
            self.ledger_record_count_after - self.ledger_record_count_before
            != self.created_record_count
        ):
            raise ValueError(
                "ledger_record_count_after - ledger_record_count_before must "
                "equal created_record_count"
            )
        if (
            self.infra_record_count + self.per_period_record_count_total
            != self.created_record_count
        ):
            raise ValueError(
                "infra_record_count + per_period_record_count_total must "
                "equal created_record_count"
            )
        if len(self.period_summaries) != self.period_count:
            raise ValueError(
                "period_summaries length must equal period_count"
            )

        for tuple_field_name in (
            "shared_selected_refs",
            "investor_only_refs",
            "bank_only_refs",
            "ordered_record_ids",
            "warnings",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            object.__setattr__(self, tuple_field_name, value)

        normalized_overall_counts: list[tuple[str, int]] = []
        for entry in self.record_type_counts:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not isinstance(entry[0], str)
                or not entry[0]
                or not isinstance(entry[1], int)
                or entry[1] < 0
            ):
                raise ValueError(
                    "record_type_counts entries must be (non-empty str, "
                    f"non-negative int); got {entry!r}"
                )
            normalized_overall_counts.append((entry[0], entry[1]))
        object.__setattr__(
            self,
            "record_type_counts",
            tuple(sorted(normalized_overall_counts)),
        )

        for triple_field_name in (
            "investor_selected_ref_counts",
            "bank_selected_ref_counts",
        ):
            value = tuple(getattr(self, triple_field_name))
            for entry in value:
                if (
                    not isinstance(entry, tuple)
                    or len(entry) != 3
                    or not isinstance(entry[0], str)
                    or not entry[0]
                    or not isinstance(entry[1], int)
                    or entry[1] < 0
                ):
                    # entry[1] is the period_id (str), entry[2] is the count.
                    pass  # will re-check below with correct indices.
            normalized_triples: list[tuple[str, str, int]] = []
            for entry in value:
                if (
                    not isinstance(entry, tuple)
                    or len(entry) != 3
                    or not isinstance(entry[0], str)
                    or not entry[0]
                    or not isinstance(entry[1], str)
                    or not entry[1]
                    or not isinstance(entry[2], int)
                    or entry[2] < 0
                ):
                    raise ValueError(
                        f"{triple_field_name} entries must be "
                        "(actor_id, period_id, non-negative int); "
                        f"got {entry!r}"
                    )
                normalized_triples.append((entry[0], entry[1], entry[2]))
            object.__setattr__(
                self,
                triple_field_name,
                tuple(sorted(normalized_triples, key=lambda t: (t[1], t[0]))),
            )

        object.__setattr__(
            self,
            "period_summaries",
            tuple(self.period_summaries),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "run_id": self.run_id,
            "period_count": self.period_count,
            "firm_count": self.firm_count,
            "investor_count": self.investor_count,
            "bank_count": self.bank_count,
            "ledger_record_count_before": self.ledger_record_count_before,
            "ledger_record_count_after": self.ledger_record_count_after,
            "created_record_count": self.created_record_count,
            "infra_record_count": self.infra_record_count,
            "per_period_record_count_total": self.per_period_record_count_total,
            "record_type_counts": [
                [event_type, count]
                for event_type, count in self.record_type_counts
            ],
            "period_summaries": [ps.to_dict() for ps in self.period_summaries],
            "investor_selected_ref_counts": [
                [actor_id, period_id, count]
                for actor_id, period_id, count in self.investor_selected_ref_counts
            ],
            "bank_selected_ref_counts": [
                [actor_id, period_id, count]
                for actor_id, period_id, count in self.bank_selected_ref_counts
            ],
            "shared_selected_refs": list(self.shared_selected_refs),
            "investor_only_refs": list(self.investor_only_refs),
            "bank_only_refs": list(self.bank_only_refs),
            "ordered_record_ids": list(self.ordered_record_ids),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_living_world_trace_report(
    kernel: Any,
    living_world_result: LivingReferenceWorldResult,
    *,
    report_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> LivingWorldTraceReport:
    """
    Build a :class:`LivingWorldTraceReport` for ``living_world_result``
    by re-walking the kernel's ledger between
    ``ledger_record_count_before`` and
    ``ledger_record_count_after`` and reading the per-period
    selections through ``kernel.attention.get_selection``.

    Read-only: ``kernel`` is consulted but never mutated; no new
    ledger record is appended.

    Validation is permissive — slice / chain mismatches and missing
    expected event types yield non-fatal :attr:`warnings` strings
    rather than raising. v1.9.1 prefers "show what is there with
    warnings attached" over "refuse to render."
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(living_world_result, LivingReferenceWorldResult):
        raise TypeError(
            "living_world_result must be a LivingReferenceWorldResult; "
            f"got {type(living_world_result).__name__}"
        )
    if report_id is not None and not (
        isinstance(report_id, str) and report_id
    ):
        raise ValueError("report_id must be a non-empty string or None")

    start_idx = living_world_result.ledger_record_count_before
    end_idx = living_world_result.ledger_record_count_after
    if start_idx < 0 or end_idx < start_idx:
        raise ValueError(
            "living_world_result has invalid ledger indices "
            f"(start={start_idx}, end={end_idx})"
        )

    ledger_records = kernel.ledger.records
    safe_end = min(end_idx, len(ledger_records))
    slice_records = list(ledger_records[start_idx:safe_end])
    record_count = len(slice_records)

    warnings: list[str] = []
    if safe_end != end_idx:
        warnings.append(
            f"living_world_result claims end_record_index={end_idx} but "
            f"kernel.ledger.records has length {len(ledger_records)}; "
            f"slice truncated to {safe_end}"
        )

    # Overall ordered_record_ids + record_type_counts.
    ordered_record_ids: list[str] = []
    overall_counts: dict[str, int] = {}
    for record in slice_records:
        oid = record.object_id
        event_type = record.record_type.value
        overall_counts[event_type] = overall_counts.get(event_type, 0) + 1
        if isinstance(oid, str) and oid:
            ordered_record_ids.append(oid)

    expected_count = living_world_result.created_record_count
    if record_count != expected_count:
        warnings.append(
            f"ledger slice length ({record_count}) does not match "
            f"living_world_result.created_record_count ({expected_count})"
        )
    if (
        tuple(r.object_id for r in slice_records)
        != living_world_result.created_record_ids
    ):
        warnings.append(
            "ledger slice object_ids do not match "
            "living_world_result.created_record_ids"
        )

    seen_event_types = set(overall_counts.keys())
    for expected in _EXPECTED_LIVING_WORLD_EVENT_TYPES:
        if expected not in seen_event_types:
            warnings.append(f"expected event type missing: {expected}")

    # Sum to record_count cross-check.
    counts_sum = sum(overall_counts.values())
    if counts_sum != record_count:
        warnings.append(
            f"record_type_counts sum ({counts_sum}) does not match "
            f"slice length ({record_count})"
        )

    # Per-period reports.
    period_summaries: list[LivingWorldPeriodReport] = []
    for period in living_world_result.per_period_summaries:
        period_summary, period_warnings = _build_period_report(
            kernel, period, ledger_records=ledger_records
        )
        period_summaries.append(period_summary)
        for w in period_warnings:
            warnings.append(w)

    # Per-period record-count-created total + infra algebra.
    per_period_total = sum(
        period.record_count_created
        for period in living_world_result.per_period_summaries
    )
    infra_record_count = living_world_result.created_record_count - per_period_total
    if infra_record_count < 0:
        warnings.append(
            "infra_record_count is negative — per-period totals "
            f"({per_period_total}) exceed chain delta "
            f"({living_world_result.created_record_count})"
        )
        infra_record_count = 0

    # Attention divergence aggregated across all periods.
    investor_union: set[str] = set()
    bank_union: set[str] = set()
    investor_counts: list[tuple[str, str, int]] = []
    bank_counts: list[tuple[str, str, int]] = []

    for period in living_world_result.per_period_summaries:
        for sel_id in period.investor_selection_ids:
            actor_id, refs = _read_selection_refs(kernel, sel_id)
            if actor_id is None:
                warnings.append(
                    f"period {period.period_id}: investor selection "
                    f"{sel_id} does not resolve to a stored selection"
                )
                continue
            investor_union.update(refs)
            investor_counts.append((actor_id, period.period_id, len(refs)))
            if not refs:
                warnings.append(
                    f"period {period.period_id}: investor selection "
                    f"{sel_id} has zero refs"
                )
        for sel_id in period.bank_selection_ids:
            actor_id, refs = _read_selection_refs(kernel, sel_id)
            if actor_id is None:
                warnings.append(
                    f"period {period.period_id}: bank selection "
                    f"{sel_id} does not resolve to a stored selection"
                )
                continue
            bank_union.update(refs)
            bank_counts.append((actor_id, period.period_id, len(refs)))
            if not refs:
                warnings.append(
                    f"period {period.period_id}: bank selection "
                    f"{sel_id} has zero refs"
                )

    shared = sorted(investor_union & bank_union)
    investor_only = sorted(investor_union - bank_union)
    bank_only = sorted(bank_union - investor_union)

    rid = report_id or f"report:living_reference_world:{living_world_result.run_id}"

    final_metadata = {
        "renderer": "v1.9.1",
        "format_version": "1",
        "boundary_statement": _BOUNDARY_STATEMENT,
        "run_id": living_world_result.run_id,
        "firm_ids": list(living_world_result.firm_ids),
        "investor_ids": list(living_world_result.investor_ids),
        "bank_ids": list(living_world_result.bank_ids),
        "claimed_end_record_index": end_idx,
    }
    if metadata:
        final_metadata.update(dict(metadata))

    return LivingWorldTraceReport(
        report_id=rid,
        run_id=living_world_result.run_id,
        period_count=living_world_result.period_count,
        firm_count=len(living_world_result.firm_ids),
        investor_count=len(living_world_result.investor_ids),
        bank_count=len(living_world_result.bank_ids),
        ledger_record_count_before=start_idx,
        # Bound end_record_index to the actual slice we read.
        ledger_record_count_after=start_idx + record_count,
        created_record_count=record_count,
        # Recompute infra from the slice we actually read; if the
        # slice was truncated this stays internally consistent.
        infra_record_count=max(record_count - per_period_total, 0),
        per_period_record_count_total=per_period_total,
        record_type_counts=tuple(sorted(overall_counts.items())),
        period_summaries=tuple(period_summaries),
        investor_selected_ref_counts=tuple(investor_counts),
        bank_selected_ref_counts=tuple(bank_counts),
        shared_selected_refs=tuple(shared),
        investor_only_refs=tuple(investor_only),
        bank_only_refs=tuple(bank_only),
        ordered_record_ids=tuple(ordered_record_ids),
        warnings=tuple(warnings),
        metadata=final_metadata,
    )


def _build_period_report(
    kernel: Any,
    period: LivingReferencePeriodSummary,
    *,
    ledger_records,
) -> tuple[LivingWorldPeriodReport, list[str]]:
    """Build the per-period report. Returns the immutable record
    plus any warning strings detected for this period."""
    period_warnings: list[str] = []

    period_before = period.metadata.get("ledger_record_count_before")
    period_after = period.metadata.get("ledger_record_count_after")
    period_record_type_counts: tuple[tuple[str, int], ...] = ()

    if isinstance(period_before, int) and isinstance(period_after, int):
        safe_period_after = min(period_after, len(ledger_records))
        period_slice = list(ledger_records[period_before:safe_period_after])
        per_period_counts: dict[str, int] = {}
        for record in period_slice:
            event_type = record.record_type.value
            per_period_counts[event_type] = (
                per_period_counts.get(event_type, 0) + 1
            )
        period_record_type_counts = tuple(sorted(per_period_counts.items()))
        if len(period_slice) != period.record_count_created:
            period_warnings.append(
                f"period {period.period_id}: ledger slice length "
                f"({len(period_slice)}) does not match "
                f"record_count_created ({period.record_count_created})"
            )
    else:
        period_warnings.append(
            f"period {period.period_id}: metadata is missing "
            "ledger_record_count_before / ledger_record_count_after"
        )

    return (
        LivingWorldPeriodReport(
            period_id=period.period_id,
            as_of_date=period.as_of_date,
            record_count_created=period.record_count_created,
            corporate_report_count=len(period.corporate_signal_ids),
            corporate_signal_ids=period.corporate_signal_ids,
            investor_menu_count=len(period.investor_menu_ids),
            bank_menu_count=len(period.bank_menu_ids),
            investor_selection_count=len(period.investor_selection_ids),
            bank_selection_count=len(period.bank_selection_ids),
            investor_review_count=len(period.investor_review_run_ids),
            bank_review_count=len(period.bank_review_run_ids),
            investor_review_signal_ids=period.investor_review_signal_ids,
            bank_review_signal_ids=period.bank_review_signal_ids,
            pressure_signal_count=len(
                getattr(period, "firm_pressure_signal_ids", ())
            ),
            valuation_count=len(getattr(period, "valuation_ids", ())),
            credit_review_signal_count=len(
                getattr(period, "bank_credit_review_signal_ids", ())
            ),
            industry_condition_count=len(
                getattr(period, "industry_condition_ids", ())
            ),
            stewardship_theme_count=len(
                getattr(period, "stewardship_theme_ids", ())
            ),
            dialogue_count=len(getattr(period, "dialogue_ids", ())),
            investor_escalation_candidate_count=len(
                getattr(period, "investor_escalation_candidate_ids", ())
            ),
            corporate_strategic_response_candidate_count=len(
                getattr(period, "corporate_strategic_response_candidate_ids", ())
            ),
            market_condition_count=len(
                getattr(period, "market_condition_ids", ())
            ),
            capital_market_readout_count=len(
                getattr(period, "capital_market_readout_ids", ())
            ),
            **_extract_firm_state_averages(kernel, period),
            **_extract_investor_intent_summary(kernel, period),
            **_extract_readout_labels(kernel, period),
            **_extract_market_environment_summary(kernel, period),
            record_type_counts=period_record_type_counts,
            warnings=tuple(period_warnings),
            metadata={
                "ledger_record_count_before": (
                    period_before if isinstance(period_before, int) else None
                ),
                "ledger_record_count_after": (
                    period_after if isinstance(period_after, int) else None
                ),
            },
        ),
        period_warnings,
    )


def _extract_investor_intent_summary(
    kernel: Any, period: LivingReferencePeriodSummary
) -> dict[str, Any]:
    """v1.12.1 — read the period's InvestorIntentRecords (if any)
    and return a count + a sorted histogram of intent_direction
    labels. When the period has no intents, returns the empty
    histogram so the renderer skips the section."""
    intent_ids = getattr(period, "investor_intent_ids", ())
    if not intent_ids:
        return {
            "investor_intent_count": 0,
            "investor_intent_direction_counts": (),
        }
    book = getattr(kernel, "investor_intents", None)
    if book is None:
        return {
            "investor_intent_count": 0,
            "investor_intent_direction_counts": (),
        }
    counts: dict[str, int] = {}
    resolved = 0
    for iid in intent_ids:
        try:
            rec = book.get_intent(iid)
        except Exception:
            continue
        counts[rec.intent_direction] = counts.get(rec.intent_direction, 0) + 1
        resolved += 1
    return {
        "investor_intent_count": resolved,
        "investor_intent_direction_counts": tuple(sorted(counts.items())),
    }


def _extract_firm_state_averages(
    kernel: Any, period: LivingReferencePeriodSummary
) -> dict[str, float]:
    """v1.12.0 — read the period's FirmFinancialStateRecords (if
    any) and return the arithmetic average of each pressure /
    readiness scalar across the cited firms. When the period has
    no states, every average defaults to 0.0 — the renderer skips
    the section."""
    state_ids = getattr(period, "firm_financial_state_ids", ())
    if not state_ids:
        return {
            "firm_financial_state_count": 0,
            "avg_margin_pressure": 0.0,
            "avg_liquidity_pressure": 0.0,
            "avg_debt_service_pressure": 0.0,
            "avg_market_access_pressure": 0.0,
            "avg_funding_need_intensity": 0.0,
            "avg_response_readiness": 0.0,
        }
    book = getattr(kernel, "firm_financial_states", None)
    if book is None:
        return {
            "firm_financial_state_count": 0,
            "avg_margin_pressure": 0.0,
            "avg_liquidity_pressure": 0.0,
            "avg_debt_service_pressure": 0.0,
            "avg_market_access_pressure": 0.0,
            "avg_funding_need_intensity": 0.0,
            "avg_response_readiness": 0.0,
        }
    margins: list[float] = []
    liquidities: list[float] = []
    debt_services: list[float] = []
    market_accesses: list[float] = []
    funding_needs: list[float] = []
    response_readinesses: list[float] = []
    for sid in state_ids:
        try:
            rec = book.get_state(sid)
        except Exception:
            continue
        margins.append(rec.margin_pressure)
        liquidities.append(rec.liquidity_pressure)
        debt_services.append(rec.debt_service_pressure)
        market_accesses.append(rec.market_access_pressure)
        funding_needs.append(rec.funding_need_intensity)
        response_readinesses.append(rec.response_readiness)
    n = len(margins)
    if n == 0:
        return {
            "firm_financial_state_count": 0,
            "avg_margin_pressure": 0.0,
            "avg_liquidity_pressure": 0.0,
            "avg_debt_service_pressure": 0.0,
            "avg_market_access_pressure": 0.0,
            "avg_funding_need_intensity": 0.0,
            "avg_response_readiness": 0.0,
        }
    return {
        "firm_financial_state_count": n,
        "avg_margin_pressure": sum(margins) / n,
        "avg_liquidity_pressure": sum(liquidities) / n,
        "avg_debt_service_pressure": sum(debt_services) / n,
        "avg_market_access_pressure": sum(market_accesses) / n,
        "avg_funding_need_intensity": sum(funding_needs) / n,
        "avg_response_readiness": sum(response_readinesses) / n,
    }


def _extract_readout_labels(
    kernel: Any, period: LivingReferencePeriodSummary
) -> dict[str, str]:
    """v1.11.1 — read the period's capital-market readout (if any)
    and surface the banker-readable labels into the period
    report. Returns the empty-string defaults when the period has
    no readout, so the renderer can skip empty rows."""
    readout_ids = getattr(period, "capital_market_readout_ids", ())
    if not readout_ids:
        return {
            "rates_tone": "",
            "credit_tone": "",
            "equity_tone": "",
            "funding_window_tone": "",
            "liquidity_tone": "",
            "volatility_tone": "",
            "overall_market_access_label": "",
        }
    book = getattr(kernel, "capital_market_readouts", None)
    if book is None:
        return {
            "rates_tone": "",
            "credit_tone": "",
            "equity_tone": "",
            "funding_window_tone": "",
            "liquidity_tone": "",
            "volatility_tone": "",
            "overall_market_access_label": "",
        }
    try:
        rec = book.get_readout(readout_ids[0])
    except Exception:
        return {
            "rates_tone": "",
            "credit_tone": "",
            "equity_tone": "",
            "funding_window_tone": "",
            "liquidity_tone": "",
            "volatility_tone": "",
            "overall_market_access_label": "",
        }
    return {
        "rates_tone": rec.rates_tone,
        "credit_tone": rec.credit_tone,
        "equity_tone": rec.equity_tone,
        "funding_window_tone": rec.funding_window_tone,
        "liquidity_tone": rec.liquidity_tone,
        "volatility_tone": rec.volatility_tone,
        "overall_market_access_label": rec.overall_market_access_label,
    }


def _extract_market_environment_summary(
    kernel: Any, period: LivingReferencePeriodSummary
) -> dict[str, Any]:
    """v1.12.2 — read the period's MarketEnvironmentStateRecord
    (if any) and surface its nine compact regime labels into the
    period report. When the period has no environment state, the
    labels default to empty strings — the renderer skips empty
    rows."""
    empty: dict[str, Any] = {
        "market_environment_state_count": 0,
        "liquidity_regime": "",
        "volatility_regime": "",
        "credit_regime": "",
        "funding_regime": "",
        "risk_appetite_regime": "",
        "rate_environment": "",
        "refinancing_window": "",
        "equity_valuation_regime": "",
        "overall_market_access_regime_label": "",
    }
    state_ids = getattr(period, "market_environment_state_ids", ())
    if not state_ids:
        return empty
    book = getattr(kernel, "market_environments", None)
    if book is None:
        return empty
    try:
        rec = book.get_state(state_ids[0])
    except Exception:
        return empty
    return {
        "market_environment_state_count": len(state_ids),
        "liquidity_regime": rec.liquidity_regime,
        "volatility_regime": rec.volatility_regime,
        "credit_regime": rec.credit_regime,
        "funding_regime": rec.funding_regime,
        "risk_appetite_regime": rec.risk_appetite_regime,
        "rate_environment": rec.rate_environment,
        "refinancing_window": rec.refinancing_window,
        "equity_valuation_regime": rec.equity_valuation_regime,
        "overall_market_access_regime_label": rec.overall_market_access_label,
    }


def _read_selection_refs(
    kernel: Any, selection_id: str
) -> tuple[str | None, tuple[str, ...]]:
    """Return (actor_id, selected_refs) for a stored selection,
    or (None, ()) if the id does not resolve."""
    try:
        sel = kernel.attention.get_selection(selection_id)
    except Exception:
        return None, ()
    return sel.actor_id, tuple(sel.selected_refs)


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def render_living_world_markdown(report: LivingWorldTraceReport) -> str:
    """
    Compact deterministic Markdown rendering of ``report``.

    Section layout is fixed: title → setup → infra prelude →
    per-period summary → attention divergence → ledger event-type
    counts → warnings → boundary statement. Two reports built from
    byte-identical living-world results render to byte-identical
    Markdown.
    """
    md = report.to_dict()
    lines: list[str] = []

    lines.append("# living_reference_world")
    lines.append("")

    # Setup summary.
    lines.append("## Setup")
    lines.append("")
    lines.append(f"- **report_id**: `{md['report_id']}`")
    lines.append(f"- **run_id**: `{md['run_id']}`")
    lines.append(f"- **period_count**: {md['period_count']}")
    lines.append(f"- **firms**: {md['firm_count']}")
    lines.append(f"- **investors**: {md['investor_count']}")
    lines.append(f"- **banks**: {md['bank_count']}")
    lines.append(
        f"- **ledger_slice**: `[{md['ledger_record_count_before']}, "
        f"{md['ledger_record_count_after']})` "
        f"({md['created_record_count']} records)"
    )
    lines.append("")

    # Infra prelude.
    lines.append("## Infra prelude")
    lines.append("")
    lines.append(
        f"- **infra_record_count**: {md['infra_record_count']} "
        "(idempotent registrations: interactions, per-firm corporate "
        "routines, per-actor profiles, review interactions, review routines)"
    )
    lines.append(
        f"- **per_period_record_count_total**: "
        f"{md['per_period_record_count_total']}"
    )
    lines.append(
        f"- **algebra check**: {md['infra_record_count']} + "
        f"{md['per_period_record_count_total']} = "
        f"{md['created_record_count']}"
    )
    lines.append("")

    # Per-period summary.
    lines.append("## Per-period summary")
    lines.append("")
    if md["period_summaries"]:
        # v1.9.6 / v1.9.7: per-period table carries `pressures`,
        # `valuations`, and `credit_reviews` columns alongside the
        # v1.9.0 baseline. Column order is fixed for determinism.
        lines.append(
            "| period | as_of_date | reports | pressures | "
            "inv_menus | bnk_menus | inv_sel | bnk_sel | valuations | "
            "credit_reviews | inv_rev | bnk_rev | records |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | "
            "--- | --- | --- | --- | --- |"
        )
        for ps in md["period_summaries"]:
            lines.append(
                f"| `{ps['period_id']}` | `{ps['as_of_date']}` | "
                f"{ps['corporate_report_count']} | "
                f"{ps.get('pressure_signal_count', 0)} | "
                f"{ps['investor_menu_count']} | "
                f"{ps['bank_menu_count']} | "
                f"{ps['investor_selection_count']} | "
                f"{ps['bank_selection_count']} | "
                f"{ps.get('valuation_count', 0)} | "
                f"{ps.get('credit_review_signal_count', 0)} | "
                f"{ps['investor_review_count']} | "
                f"{ps['bank_review_count']} | "
                f"{ps['record_count_created']} |"
            )
    else:
        lines.append("- _(none)_")
    lines.append("")

    # v1.11.0 capital-market conditions section. One row per
    # period showing the count of synthetic market-condition
    # records emitted that period. The section is intentionally
    # narrow; full per-condition detail lives on the canonical
    # view, not the rendered report.
    has_v111_signal = any(
        ps.get("market_condition_count", 0) > 0
        for ps in md["period_summaries"]
    )
    if has_v111_signal:
        lines.append("## Capital market conditions")
        lines.append("")
        lines.append("| period | as_of_date | market_conditions |")
        lines.append("| --- | --- | --- |")
        for ps in md["period_summaries"]:
            lines.append(
                f"| `{ps['period_id']}` | `{ps['as_of_date']}` | "
                f"{ps.get('market_condition_count', 0)} |"
            )
        lines.append("")
        lines.append(
            "> Capital-market conditions are synthetic context "
            "evidence only — no price formation, no yield-curve "
            "calibration, no order matching, no clearing, no "
            "quote dissemination, no real market data."
        )
        lines.append("")

    # v1.11.1 capital-market surface readout section. One row per
    # period showing the banker-readable per-market tone tags +
    # the overall market-access label. Sits adjacent to the
    # v1.11.0 conditions section: §"Capital market conditions"
    # gives the count, §"Capital market surface" gives the
    # labels.
    has_v1111_signal = any(
        ps.get("capital_market_readout_count", 0) > 0
        and ps.get("overall_market_access_label", "")
        for ps in md["period_summaries"]
    )
    if has_v1111_signal:
        lines.append("## Capital market surface")
        lines.append("")
        lines.append(
            "| period | as_of_date | rates | credit | equity | "
            "funding window | liquidity | volatility | overall |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        )
        for ps in md["period_summaries"]:
            if not ps.get("overall_market_access_label", ""):
                continue
            lines.append(
                f"| `{ps['period_id']}` | `{ps['as_of_date']}` | "
                f"{ps.get('rates_tone', '')} | "
                f"{ps.get('credit_tone', '')} | "
                f"{ps.get('equity_tone', '')} | "
                f"{ps.get('funding_window_tone', '')} | "
                f"{ps.get('liquidity_tone', '')} | "
                f"{ps.get('volatility_tone', '')} | "
                f"{ps.get('overall_market_access_label', '')} |"
            )
        lines.append("")
        lines.append(
            "> Capital-market surface labels are deterministic "
            "per-market tone tags + an overall market-access "
            "label, derived from the v1.11.0 condition records by "
            "the v1.11.1 rule set. **Not** a market view, **not** "
            "a forecast, **not** a recommendation, **not** deal "
            "advice — readout / report only."
        )
        lines.append("")

    # v1.12.2 market environment state section. One row per
    # period showing the nine compact regime labels lifted from
    # the period's MarketEnvironmentStateRecord. Sits adjacent to
    # the v1.11.1 capital-market surface section: the readout
    # gives the *banker* tone tags; the environment state gives
    # the same context normalized into nine compact *regime*
    # labels future LLM agents and attention-conditioned
    # mechanisms can consume directly.
    has_v1122_signal = any(
        ps.get("market_environment_state_count", 0) > 0
        and ps.get("overall_market_access_regime_label", "")
        for ps in md["period_summaries"]
    )
    if has_v1122_signal:
        lines.append("## Market environment state")
        lines.append("")
        lines.append(
            "| period | as_of_date | liquidity | volatility | credit | "
            "funding | risk appetite | rate env | refinancing | "
            "equity valuation | overall |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | "
            "--- | --- |"
        )
        for ps in md["period_summaries"]:
            if not ps.get("overall_market_access_regime_label", ""):
                continue
            lines.append(
                f"| `{ps['period_id']}` | `{ps['as_of_date']}` | "
                f"{ps.get('liquidity_regime', '')} | "
                f"{ps.get('volatility_regime', '')} | "
                f"{ps.get('credit_regime', '')} | "
                f"{ps.get('funding_regime', '')} | "
                f"{ps.get('risk_appetite_regime', '')} | "
                f"{ps.get('rate_environment', '')} | "
                f"{ps.get('refinancing_window', '')} | "
                f"{ps.get('equity_valuation_regime', '')} | "
                f"{ps.get('overall_market_access_regime_label', '')} |"
            )
        lines.append("")
        lines.append(
            "> Market environment state normalizes the period's "
            "market-condition + readout context into nine compact "
            "regime labels. **Not** a price, **not** a yield, "
            "**not** a spread, **not** an index level, **not** a "
            "forecast, **not** an expected return, **not** a "
            "recommendation, **not** a target price, **not** a "
            "target weight, **not** an order, **not** a trade, "
            "**not** an allocation."
        )
        lines.append("")

    # v1.10.5 engagement / strategic-response section. Per-period
    # counts for stewardship themes (setup-level; same on every
    # period), industry demand conditions, dialogues, escalation
    # candidates, and corporate strategic response candidates. The
    # table is intentionally narrow so it does not crowd the v1.9
    # core flow above.
    has_v110_signal = any(
        ps.get("dialogue_count", 0)
        + ps.get("investor_escalation_candidate_count", 0)
        + ps.get("corporate_strategic_response_candidate_count", 0)
        + ps.get("industry_condition_count", 0)
        + ps.get("stewardship_theme_count", 0)
        > 0
        for ps in md["period_summaries"]
    )
    if has_v110_signal:
        lines.append("## v1.10 engagement / response")
        lines.append("")
        lines.append(
            "| period | as_of_date | themes | industries | "
            "dialogues | escalations | responses |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- |"
        )
        for ps in md["period_summaries"]:
            lines.append(
                f"| `{ps['period_id']}` | `{ps['as_of_date']}` | "
                f"{ps.get('stewardship_theme_count', 0)} | "
                f"{ps.get('industry_condition_count', 0)} | "
                f"{ps.get('dialogue_count', 0)} | "
                f"{ps.get('investor_escalation_candidate_count', 0)} | "
                f"{ps.get('corporate_strategic_response_candidate_count', 0)} |"
            )
        lines.append("")
        lines.append(
            "> All v1.10 entries are storage / metadata / "
            "candidates only — no voting execution, no proxy "
            "filing, no public campaign, no corporate action, no "
            "disclosure filing, no demand / revenue forecast, no "
            "firm financial-statement update."
        )
        lines.append("")

    # v1.12.0 firm financial latent states section. One row per
    # period showing the average of each pressure / readiness
    # scalar across the period's firms. Synthetic ordering only
    # — never an accounting figure, never a forecast.
    has_v120_signal = any(
        ps.get("firm_financial_state_count", 0) > 0
        for ps in md["period_summaries"]
    )
    if has_v120_signal:
        lines.append("## Firm financial states")
        lines.append("")
        lines.append(
            "| period | as_of_date | firms | avg margin | avg liquidity | "
            "avg debt service | avg market access | avg funding need | "
            "avg response readiness |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        )
        for ps in md["period_summaries"]:
            if ps.get("firm_financial_state_count", 0) == 0:
                continue
            lines.append(
                f"| `{ps['period_id']}` | `{ps['as_of_date']}` | "
                f"{ps.get('firm_financial_state_count', 0)} | "
                f"{ps.get('avg_margin_pressure', 0.0):.2f} | "
                f"{ps.get('avg_liquidity_pressure', 0.0):.2f} | "
                f"{ps.get('avg_debt_service_pressure', 0.0):.2f} | "
                f"{ps.get('avg_market_access_pressure', 0.0):.2f} | "
                f"{ps.get('avg_funding_need_intensity', 0.0):.2f} | "
                f"{ps.get('avg_response_readiness', 0.0):.2f} |"
            )
        lines.append("")
        lines.append(
            "> Firm financial states are synthetic latent "
            "ordering scalars in [0, 1] updated period-over-period "
            "by the v1.12.0 rule set. **Not** an accounting "
            "statement, **not** revenue / EBITDA / cash / debt, "
            "**not** a forecast, **not** investment advice."
        )
        lines.append("")

    # v1.12.1 investor intent section. Each row shows the
    # period's per-(investor, firm) intent count plus a sorted
    # histogram of intent_direction labels. Pre-action review
    # posture only — never an order, trade, allocation, or
    # recommendation.
    has_v121_signal = any(
        ps.get("investor_intent_count", 0) > 0
        for ps in md["period_summaries"]
    )
    if has_v121_signal:
        lines.append("## Investor intent")
        lines.append("")
        lines.append(
            "| period | as_of_date | intents | direction histogram |"
        )
        lines.append("| --- | --- | --- | --- |")
        for ps in md["period_summaries"]:
            if ps.get("investor_intent_count", 0) == 0:
                continue
            histogram = ps.get(
                "investor_intent_direction_counts", []
            )
            histogram_str = (
                ", ".join(
                    f"{label}={count}"
                    for label, count in histogram
                )
                if histogram
                else "—"
            )
            lines.append(
                f"| `{ps['period_id']}` | `{ps['as_of_date']}` | "
                f"{ps.get('investor_intent_count', 0)} | "
                f"{histogram_str} |"
            )
        lines.append("")
        lines.append(
            "> Investor intent is pre-action / pre-decision "
            "review posture conditioned on the period's evidence. "
            "**Not** an order, **not** a trade, **not** a "
            "rebalance, **not** a portfolio-allocation decision, "
            "**not** a security recommendation, **not** "
            "investment advice."
        )
        lines.append("")

    # Attention divergence summary.
    lines.append("## Attention divergence")
    lines.append("")
    lines.append(
        f"- shared: {len(md['shared_selected_refs'])} | "
        f"investor_only: {len(md['investor_only_refs'])} | "
        f"bank_only: {len(md['bank_only_refs'])}"
    )
    lines.append("")
    lines.append("### Per-actor selected-ref counts")
    lines.append("")
    if md["investor_selected_ref_counts"]:
        for actor_id, period_id, count in md["investor_selected_ref_counts"]:
            lines.append(
                f"- investor `{actor_id}` @ `{period_id}`: "
                f"{count} ref(s)"
            )
    else:
        lines.append("- _(no investor selections)_")
    if md["bank_selected_ref_counts"]:
        for actor_id, period_id, count in md["bank_selected_ref_counts"]:
            lines.append(
                f"- bank `{actor_id}` @ `{period_id}`: {count} ref(s)"
            )
    else:
        lines.append("- _(no bank selections)_")
    lines.append("")
    if md["shared_selected_refs"]:
        lines.append("### Shared refs (across all periods)")
        lines.append("")
        for ref in md["shared_selected_refs"]:
            lines.append(f"- `{ref}`")
        lines.append("")
    if md["investor_only_refs"]:
        lines.append("### Investor-only refs (across all periods)")
        lines.append("")
        for ref in md["investor_only_refs"]:
            lines.append(f"- `{ref}`")
        lines.append("")
    if md["bank_only_refs"]:
        lines.append("### Bank-only refs (across all periods)")
        lines.append("")
        for ref in md["bank_only_refs"]:
            lines.append(f"- `{ref}`")
        lines.append("")

    # Ledger event-type counts.
    lines.append("## Ledger event-type counts")
    lines.append("")
    if md["record_type_counts"]:
        for event_type, count in md["record_type_counts"]:
            lines.append(f"- `{event_type}`: {count}")
    else:
        lines.append("- _(none)_")
    lines.append("")

    # Warnings.
    lines.append("## Warnings")
    lines.append("")
    if md["warnings"]:
        for warning in md["warnings"]:
            lines.append(f"- {warning}")
    else:
        lines.append("- _(none)_")
    lines.append("")

    # Boundaries.
    lines.append("## Boundaries")
    lines.append("")
    lines.append(f"> {_BOUNDARY_STATEMENT}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
