"""
v1.9.0 Living Reference World Demo.

A small synthetic, jurisdiction-neutral, **multi-period** living
reference world built entirely from existing v1.8 primitives:

    corporate quarterly reporting   (v1.8.7)
        +
    ObservationMenuBuilder          (v1.8.11)
        +
    investor / bank attention rule  (v1.8.12, public selector)
        +
    investor / bank review routines (v1.8.13)

Where v1.8.14 ran the chain once on a single ``as_of_date``,
v1.9.0 sweeps the chain across **multiple firms** and **multiple
periods**. The point is to show that the v1.8 stack composes over
time as well as over actors: each quarter, every firm publishes a
synthetic report, the investor and the bank rebuild their menus,
their selections diverge along the v1.8.12 attention axes, and
both run a review routine that emits a synthetic note. The
ledger grows quarter by quarter; nothing else changes.

Anti-scope (carried forward verbatim from v1.8)
------------------------------------------------

v1.9.0 does **not** add: price formation, trading, investor buy /
sell decisions, bank lending decisions, covenant enforcement,
valuation refresh, impact estimation, sensitivity calculation,
DSCR / LTV updates, corporate actions, policy reactions, scenario
engines, stochastic shocks, dense all-to-all interaction
traversal, public web UI, real Japan calibration, or real data
ingestion. **Agents are operational actors, not optimizing
decision-makers.** Activity is endogenous and routine-driven.
External shocks are not required and not present.

Complexity discipline
---------------------

v1.9.0 is deliberately bounded. The per-period flow does **not**
walk a Cartesian product:

- **Per firm**: one corporate-reporting routine call. Cost per
  call is dominated by `RoutineBook.add_run_record` and one
  `SignalBook.add_signal`.
- **Per actor (investor / bank)**: one menu build (sparse — the
  builder iterates only the actor's exposures and the visible
  variable observations on the as-of date), one selection
  applied to that menu (filters menu refs against the actor's
  watch fields — no cross-firm enumeration), one review run
  (collects the actor's selection refs into the run record's
  ``input_refs``).
- **Per period overall**: roughly
  ``O(firms + actors × relevant_refs)`` records. With v1.9.0's
  defaults (3–5 firms, 4 actors, ≲ 10 relevant refs each, 4
  periods), the demo finishes in well under a second on a
  developer laptop and produces ~80–120 ledger records total.

There is **no path enumeration**, **no dense tensor
materialisation**, and **no O(N^N) anything**. Tests pin a
budget on the resulting ledger length; if a future change pushes
the count past the budget, the test fails loudly so the loop is
re-examined.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping, Sequence

from world.attention import AttentionProfile, SelectedObservationSet
from world.engagement import (
    DuplicateDialogueError,
    DuplicateEscalationCandidateError,
    InvestorEscalationCandidate,
    PortfolioCompanyDialogueRecord,
)
from world.industry import (
    DuplicateIndustryConditionError,
    IndustryDemandConditionRecord,
)
from world.market_conditions import (
    DuplicateMarketConditionError,
    MarketConditionRecord,
)
from world.market_surface_readout import build_capital_market_readout
from world.market_environment import build_market_environment_state
from world.firm_state import run_reference_firm_financial_state_update
from world.investor_intent import run_reference_investor_intent_signal
from world.observation_menu_builder import ObservationMenuBuildRequest
from world.stewardship import (
    DuplicateStewardshipThemeError,
    StewardshipThemeRecord,
)
from world.strategic_response import (
    CorporateStrategicResponseCandidate,
    DuplicateResponseCandidateError,
)
from world.reference_attention import (
    register_bank_attention_profile,
    register_investor_attention_profile,
    select_observations_for_profile,
)
from world.reference_reviews import (
    register_bank_review_interaction,
    register_bank_review_routine,
    register_investor_review_interaction,
    register_investor_review_routine,
    run_bank_review,
    run_investor_review,
)
from world.reference_bank_credit_review_lite import (
    BankCreditReviewLiteResult,
    run_reference_bank_credit_review_lite,
)
from world.reference_firm_pressure import (
    FirmPressureMechanismResult,
    run_reference_firm_pressure_mechanism,
)
from world.reference_routines import (
    CorporateReportingResult,
    register_corporate_quarterly_reporting_routine,
    register_corporate_reporting_interaction,
    run_corporate_quarterly_reporting,
)
from world.reference_valuation_refresh_lite import (
    ValuationRefreshLiteResult,
    run_reference_valuation_refresh_lite,
)


# ---------------------------------------------------------------------------
# Result records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LivingReferencePeriodSummary:
    """
    Aggregate summary of one period's worth of activity.

    The summary names every primary id the period produced
    (corporate signals, investor / bank menus, selections, review
    signals) plus the count of new ledger records the period
    appended. The ids are stored in the order each component
    helper was invoked, so a downstream consumer can correlate
    summaries with the matching ledger slice.
    """

    period_id: str
    as_of_date: str
    corporate_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    corporate_run_ids: tuple[str, ...] = field(default_factory=tuple)
    # v1.9.6 additive: pressure assessment + valuation refresh integration.
    # firm_pressure_signal_ids and firm_pressure_run_ids carry one entry
    # per firm; valuation_ids and valuation_mechanism_run_ids carry one
    # entry per (investor, firm) pair.
    firm_pressure_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    firm_pressure_run_ids: tuple[str, ...] = field(default_factory=tuple)
    valuation_ids: tuple[str, ...] = field(default_factory=tuple)
    valuation_mechanism_run_ids: tuple[str, ...] = field(default_factory=tuple)
    # v1.9.7 additive: bank credit review lite integration.
    # bank_credit_review_signal_ids and
    # bank_credit_review_mechanism_run_ids carry one entry per
    # (bank, firm) pair.
    bank_credit_review_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    bank_credit_review_mechanism_run_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    investor_menu_ids: tuple[str, ...] = field(default_factory=tuple)
    bank_menu_ids: tuple[str, ...] = field(default_factory=tuple)
    investor_selection_ids: tuple[str, ...] = field(default_factory=tuple)
    bank_selection_ids: tuple[str, ...] = field(default_factory=tuple)
    investor_review_run_ids: tuple[str, ...] = field(default_factory=tuple)
    bank_review_run_ids: tuple[str, ...] = field(default_factory=tuple)
    investor_review_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    bank_review_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    # v1.10.5 additive: engagement / strategic-response integration.
    # ``industry_condition_ids`` carries one entry per industry per
    # period (v1.10.4); ``stewardship_theme_ids`` echoes the
    # setup-level themes registered for the run (the same tuple
    # appears on every period summary so a downstream consumer can
    # see which themes were active for every period without joining
    # against the result-level setup); ``dialogue_ids`` and
    # ``investor_escalation_candidate_ids`` carry one entry per
    # (investor, firm) pair (v1.10.2 / v1.10.3 investor side);
    # ``corporate_strategic_response_candidate_ids`` carries one
    # entry per firm (v1.10.3 corporate side).
    industry_condition_ids: tuple[str, ...] = field(default_factory=tuple)
    stewardship_theme_ids: tuple[str, ...] = field(default_factory=tuple)
    dialogue_ids: tuple[str, ...] = field(default_factory=tuple)
    investor_escalation_candidate_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    corporate_strategic_response_candidate_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    # v1.11.0 additive: capital-market condition surface. One
    # entry per (market, period) pair from the orchestrator's
    # default market set (or the caller's override).
    market_condition_ids: tuple[str, ...] = field(default_factory=tuple)
    # v1.11.1 additive: one capital-market readout id per period.
    # The readout summarizes the same period's market_condition_ids
    # into deterministic per-market tone tags + an overall
    # market-access label + a banker-summary label. Storage /
    # report only — never a recommendation, never a forecast.
    capital_market_readout_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    # v1.12.2 additive: one market-environment-state id per
    # period. The state normalizes the period's market_condition
    # + capital_market_readout into nine compact regime labels
    # (liquidity / volatility / credit / funding /
    # risk_appetite / rate_environment / refinancing_window /
    # equity_valuation / overall_market_access). Storage / report
    # only — never a price, yield, spread, index level, forecast,
    # expected return, recommendation, target price, target
    # weight, order, trade, or allocation.
    market_environment_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    # v1.12.0 additive: one firm-financial-state id per (firm,
    # period) pair. The state is a synthetic latent ordering
    # (margin / liquidity / debt-service / market-access /
    # funding-need / response-readiness scalars in [0, 1])
    # updated from prior period via the v1.12.0 rule set. Not
    # an accounting statement; not a forecast.
    firm_financial_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    # v1.12.1 additive: one investor-intent id per (investor,
    # firm) pair per period. Pre-action review posture only —
    # never an order, trade, allocation, or recommendation.
    investor_intent_ids: tuple[str, ...] = field(default_factory=tuple)
    record_count_created: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for tuple_field_name in (
            "corporate_signal_ids",
            "corporate_run_ids",
            "firm_pressure_signal_ids",
            "firm_pressure_run_ids",
            "valuation_ids",
            "valuation_mechanism_run_ids",
            "bank_credit_review_signal_ids",
            "bank_credit_review_mechanism_run_ids",
            "investor_menu_ids",
            "bank_menu_ids",
            "investor_selection_ids",
            "bank_selection_ids",
            "investor_review_run_ids",
            "bank_review_run_ids",
            "investor_review_signal_ids",
            "bank_review_signal_ids",
            "industry_condition_ids",
            "stewardship_theme_ids",
            "dialogue_ids",
            "investor_escalation_candidate_ids",
            "corporate_strategic_response_candidate_ids",
            "market_condition_ids",
            "capital_market_readout_ids",
            "market_environment_state_ids",
            "firm_financial_state_ids",
            "investor_intent_ids",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            object.__setattr__(self, tuple_field_name, value)
        if self.record_count_created < 0:
            raise ValueError("record_count_created must be >= 0")
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True)
class LivingReferenceWorldResult:
    """
    Aggregate summary of one ``run_living_reference_world`` call.

    Names every actor the sweep touched and carries one
    :class:`LivingReferencePeriodSummary` per period in
    ``per_period_summaries`` (in input order). Ledger counts mirror
    the v1.8.14 chain harness's ``ledger_record_count_before`` /
    ``ledger_record_count_after`` convention so the entire sweep is
    reconstructable from ``kernel.ledger.records[before:after]``.
    """

    run_id: str
    period_count: int
    firm_ids: tuple[str, ...]
    investor_ids: tuple[str, ...]
    bank_ids: tuple[str, ...]
    per_period_summaries: tuple[LivingReferencePeriodSummary, ...]
    created_record_ids: tuple[str, ...]
    ledger_record_count_before: int
    ledger_record_count_after: int
    # v1.10.5 additive: setup-level engagement context. The
    # ``industry_ids`` tuple names the unique industries the run
    # generated demand-condition records against (one record per
    # industry per period; the per-period tuple lives on
    # :class:`LivingReferencePeriodSummary`). The
    # ``stewardship_theme_ids`` tuple names the themes registered
    # once at setup; the same tuple is echoed on every period
    # summary's ``stewardship_theme_ids`` field for convenience.
    industry_ids: tuple[str, ...] = field(default_factory=tuple)
    stewardship_theme_ids: tuple[str, ...] = field(default_factory=tuple)
    # v1.11.0 additive: setup-level capital-market context. The
    # ``market_ids`` tuple names the unique synthetic markets the
    # run generated condition records against (one record per
    # market per period; the per-period tuple lives on
    # :class:`LivingReferencePeriodSummary`).
    market_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id:
            raise ValueError("run_id must be a non-empty string")
        if self.period_count < 0:
            raise ValueError("period_count must be >= 0")
        if len(self.per_period_summaries) != self.period_count:
            raise ValueError(
                "per_period_summaries length must equal period_count"
            )
        for tuple_field_name in (
            "firm_ids",
            "investor_ids",
            "bank_ids",
            "created_record_ids",
            "industry_ids",
            "stewardship_theme_ids",
            "market_ids",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            object.__setattr__(self, tuple_field_name, value)
        object.__setattr__(
            self,
            "per_period_summaries",
            tuple(self.per_period_summaries),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def created_record_count(self) -> int:
        return len(self.created_record_ids)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_DEFAULT_QUARTER_END_DATES: tuple[str, ...] = (
    "2026-03-31",
    "2026-06-30",
    "2026-09-30",
    "2026-12-31",
)


# v1.10.5 — defaults for the engagement / strategic-response layer.
# Every label is generic and jurisdiction-neutral; the orchestrator
# never enforces vocabulary against any country, regulator, code, or
# named institution. Callers may override every default below.

_DEFAULT_STEWARDSHIP_THEME_TYPES: tuple[str, ...] = (
    "capital_allocation_discipline",
    "governance_structure",
)

# Generic substring → industry keyword mapping. Used by
# ``_default_industry_for_firm`` to assign each firm a synthetic,
# jurisdiction-neutral industry id so the v1.10.4 demand-condition
# phase has a non-degenerate fixture out of the box. The list is
# matched in declaration order on the lowercased firm_id.
_DEFAULT_FIRM_INDUSTRY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("manufacturer", "industry:reference_manufacturing_general"),
    ("retailer", "industry:reference_retail_general"),
    ("utility", "industry:reference_utility_general"),
    ("bank", "industry:reference_financial_general"),
    ("real_estate", "industry:reference_real_estate_general"),
    ("property", "industry:reference_real_estate_general"),
    ("energy", "industry:reference_energy_general"),
)

_FALLBACK_INDUSTRY_ID: str = "industry:reference_general"

# v1.10.4: synthetic per-industry demand condition. The triple
# (direction, strength, confidence) is small, deterministic, and
# explicitly *not* a forecast — values are chosen to be visible /
# distinguishable in the report, never calibrated. ``demand_strength``
# and ``confidence`` are bounded in [0.0, 1.0] inclusive per the
# v1.10.4 record contract. If a key is missing the orchestrator
# falls back to ``_DEFAULT_INDUSTRY_DEMAND_STATE`` below.
_INDUSTRY_DEMAND_DEFAULTS: Mapping[str, tuple[str, float, float]] = {
    "industry:reference_manufacturing_general": ("stable", 0.5, 0.5),
    "industry:reference_retail_general": ("contracting", 0.4, 0.5),
    "industry:reference_utility_general": ("expanding", 0.6, 0.5),
    "industry:reference_financial_general": ("stable", 0.5, 0.5),
    "industry:reference_real_estate_general": ("stable", 0.5, 0.5),
    "industry:reference_energy_general": ("expanding", 0.6, 0.5),
    "industry:reference_general": ("stable", 0.5, 0.5),
}
_DEFAULT_INDUSTRY_DEMAND_STATE: tuple[str, float, float] = (
    "stable",
    0.5,
    0.5,
)


def _default_industry_for_firm(firm_id: str) -> str:
    lower = firm_id.lower()
    for keyword, industry_id in _DEFAULT_FIRM_INDUSTRY_KEYWORDS:
        if keyword in lower:
            return industry_id
    return _FALLBACK_INDUSTRY_ID


def _resolve_firm_industry_map(
    firms: Sequence[str],
    firm_industry_map: Mapping[str, str] | None,
) -> dict[str, str]:
    if firm_industry_map is None:
        return {firm_id: _default_industry_for_firm(firm_id) for firm_id in firms}
    out: dict[str, str] = {}
    for firm_id in firms:
        ind = firm_industry_map.get(firm_id)
        if not isinstance(ind, str) or not ind:
            ind = _default_industry_for_firm(firm_id)
        out[firm_id] = ind
    return out


def _theme_id_for(investor_id: str, theme_type: str) -> str:
    return f"theme:{investor_id}:{theme_type}:setup"


def _industry_condition_id_for(industry_id: str, as_of_date: str) -> str:
    return f"industry_condition:{industry_id}:{as_of_date}"


def _industry_label_for(industry_id: str) -> str:
    """Short jurisdiction-neutral display label derived from id."""
    if industry_id.startswith("industry:"):
        suffix = industry_id[len("industry:") :]
    else:
        suffix = industry_id
    return f"reference {suffix.replace('_', ' ')} (synthetic)"


def _dialogue_id_for(
    investor_id: str, firm_id: str, as_of_date: str
) -> str:
    return f"dialogue:{investor_id}:{firm_id}:{as_of_date}"


def _escalation_id_for(
    investor_id: str, firm_id: str, as_of_date: str
) -> str:
    return f"escalation:{investor_id}:{firm_id}:{as_of_date}"


def _response_id_for(firm_id: str, as_of_date: str) -> str:
    return f"response:{firm_id}:{as_of_date}"


# v1.11.0 — default capital-market condition specs. Each entry is
# (market_id, market_type, condition_type, direction, strength,
# confidence, time_horizon). The triple (direction, strength,
# confidence) is small, deterministic, and explicitly *not* a
# forecast — values illustrate ordering only. ``strength`` and
# ``confidence`` are bounded in [0.0, 1.0] inclusive per the
# v1.11.0 record contract. The list is kept short so the
# per-period record budget stays small (5 markets × 4 periods =
# 20 condition records per run).
_MarketConditionSpec = tuple[str, str, str, str, float, float, str]

_DEFAULT_MARKET_CONDITION_SPECS: tuple[_MarketConditionSpec, ...] = (
    (
        "market:reference_rates_general",
        "reference_rates",
        "rate_level",
        "supportive",
        0.5,
        0.5,
        "medium_term",
    ),
    (
        "market:reference_credit_spreads_general",
        "credit_spreads",
        "spread_level",
        "stable",
        0.5,
        0.5,
        "medium_term",
    ),
    (
        "market:reference_equity_general",
        "equity_market",
        "valuation_environment",
        "supportive",
        0.5,
        0.5,
        "medium_term",
    ),
    (
        "market:reference_funding_general",
        "funding_market",
        "funding_window",
        "supportive",
        0.5,
        0.5,
        "short_term",
    ),
    (
        "market:reference_liquidity_general",
        "liquidity_market",
        "liquidity_regime",
        "stable",
        0.5,
        0.5,
        "short_term",
    ),
)


# v1.11.2 — synthetic market-regime presets. Each preset is a
# small, deterministic, jurisdiction-neutral overlay on the default
# 5-market spec set; values change only the synthetic
# (direction, strength, confidence, time_horizon) tuple. No real
# yields, no real spreads, no real index levels, no forecasts, no
# recommendations. The presets are designed so the v1.11.1
# capital-market readout's overall_market_access_label classifier
# reaches a different branch per preset:
#
#   constructive → open_or_constructive
#       (funding supportive AND credit not restrictive)
#   mixed        → mixed
#       (neither classifier branch fires)
#   constrained  → selective_or_constrained
#       (credit restrictive AND liquidity tightening)
#   tightening   → selective_or_constrained
#       (credit widening AND liquidity tightening; rates emphasis)
#
# The "tightening" regime is documented as also landing on
# selective_or_constrained: rates flow through to credit
# (widening) and liquidity (tightening), while funding leaves the
# supportive set, so the second classifier branch fires.

_REGIME_PRESETS: Mapping[str, tuple[_MarketConditionSpec, ...]] = {
    "constructive": (
        (
            "market:reference_rates_general",
            "reference_rates",
            "rate_level",
            "supportive",
            0.6,
            0.6,
            "medium_term",
        ),
        (
            "market:reference_credit_spreads_general",
            "credit_spreads",
            "spread_level",
            "stable",
            0.55,
            0.6,
            "medium_term",
        ),
        (
            "market:reference_equity_general",
            "equity_market",
            "valuation_environment",
            "supportive",
            0.6,
            0.6,
            "medium_term",
        ),
        (
            "market:reference_funding_general",
            "funding_market",
            "funding_window",
            "supportive",
            0.65,
            0.6,
            "short_term",
        ),
        (
            "market:reference_liquidity_general",
            "liquidity_market",
            "liquidity_regime",
            "stable",
            0.55,
            0.6,
            "short_term",
        ),
    ),
    "mixed": (
        (
            "market:reference_rates_general",
            "reference_rates",
            "rate_level",
            "stable",
            0.5,
            0.5,
            "medium_term",
        ),
        (
            "market:reference_credit_spreads_general",
            "credit_spreads",
            "spread_level",
            "stable",
            0.5,
            0.5,
            "medium_term",
        ),
        (
            "market:reference_equity_general",
            "equity_market",
            "valuation_environment",
            "mixed",
            0.5,
            0.5,
            "medium_term",
        ),
        (
            "market:reference_funding_general",
            "funding_market",
            "funding_window",
            "mixed",
            0.5,
            0.5,
            "short_term",
        ),
        (
            "market:reference_liquidity_general",
            "liquidity_market",
            "liquidity_regime",
            "stable",
            0.5,
            0.5,
            "short_term",
        ),
    ),
    "constrained": (
        (
            "market:reference_rates_general",
            "reference_rates",
            "rate_level",
            "tightening",
            0.45,
            0.55,
            "medium_term",
        ),
        (
            "market:reference_credit_spreads_general",
            "credit_spreads",
            "spread_level",
            "restrictive",
            0.55,
            0.55,
            "medium_term",
        ),
        (
            "market:reference_equity_general",
            "equity_market",
            "valuation_environment",
            "restrictive",
            0.5,
            0.55,
            "medium_term",
        ),
        (
            "market:reference_funding_general",
            "funding_market",
            "funding_window",
            "mixed",
            0.45,
            0.55,
            "short_term",
        ),
        (
            "market:reference_liquidity_general",
            "liquidity_market",
            "liquidity_regime",
            "tightening",
            0.55,
            0.55,
            "short_term",
        ),
    ),
    "tightening": (
        (
            "market:reference_rates_general",
            "reference_rates",
            "rate_level",
            "tightening",
            0.6,
            0.55,
            "medium_term",
        ),
        (
            "market:reference_credit_spreads_general",
            "credit_spreads",
            "spread_level",
            "widening",
            0.5,
            0.55,
            "medium_term",
        ),
        (
            "market:reference_equity_general",
            "equity_market",
            "valuation_environment",
            "mixed",
            0.45,
            0.55,
            "medium_term",
        ),
        (
            "market:reference_funding_general",
            "funding_market",
            "funding_window",
            "tightening",
            0.5,
            0.55,
            "short_term",
        ),
        (
            "market:reference_liquidity_general",
            "liquidity_market",
            "liquidity_regime",
            "tightening",
            0.5,
            0.55,
            "short_term",
        ),
    ),
}

_REGIME_NAMES: tuple[str, ...] = tuple(sorted(_REGIME_PRESETS.keys()))


def _market_condition_id_for(market_id: str, as_of_date: str) -> str:
    return f"market_condition:{market_id}:{as_of_date}"


def _ensure_stewardship_themes(
    kernel: Any,
    *,
    investor_ids: Sequence[str],
    theme_types: Sequence[str],
    effective_from: str,
) -> tuple[str, ...]:
    """
    Idempotently register the v1.10.5 default stewardship themes —
    one per (investor, theme_type). Returns the theme ids in
    deterministic (investor, theme_type) order. Re-running with the
    same args is a no-op (the book raises
    ``DuplicateStewardshipThemeError`` and the helper falls back to
    :meth:`StewardshipBook.get_theme`).
    """
    out: list[str] = []
    for investor_id in investor_ids:
        for theme_type in theme_types:
            theme_id = _theme_id_for(investor_id, theme_type)
            try:
                kernel.stewardship.add_theme(
                    StewardshipThemeRecord(
                        theme_id=theme_id,
                        owner_id=investor_id,
                        owner_type="investor",
                        theme_type=theme_type,
                        title=theme_type.replace("_", " ").title(),
                        target_scope="all_holdings",
                        priority="medium",
                        horizon="medium_term",
                        status="active",
                        effective_from=effective_from,
                    )
                )
            except DuplicateStewardshipThemeError:
                kernel.stewardship.get_theme(theme_id)
            out.append(theme_id)
    return tuple(out)


def _validate_required_string(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} is required and must be a non-empty string")
    return value


def _validate_id_list(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise TypeError(f"{name} must be a list or tuple")
    if len(values) == 0:
        raise ValueError(f"{name} must not be empty")
    out: list[str] = []
    for v in values:
        if not isinstance(v, str) or not v:
            raise ValueError(
                f"{name} entries must be non-empty strings; got {v!r}"
            )
        out.append(v)
    return tuple(out)


def _coerce_iso_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"date must be a non-empty ISO string or date; got {value!r}")


def _menu_id_for(actor_kind: str, actor_id: str, as_of_date: str) -> str:
    return f"menu:living:{actor_kind}:{actor_id}:{as_of_date}"


def _selection_id_for(
    actor_kind: str, actor_id: str, as_of_date: str
) -> str:
    return f"selection:living:{actor_kind}:{actor_id}:{as_of_date}"


def _menu_request_id_for(
    actor_kind: str, actor_id: str, as_of_date: str
) -> str:
    return f"req:menu:living:{actor_kind}:{actor_id}:{as_of_date}"


def _ledger_object_ids_since(
    kernel: Any, *, since_index: int
) -> tuple[str, ...]:
    return tuple(
        record.object_id for record in kernel.ledger.records[since_index:]
    )


# ---------------------------------------------------------------------------
# Per-actor menu + selection (uses v1.8.11 builder + v1.8.12 rule directly
# rather than going through v1.8.12's investor+bank pair helper, which is
# tied to a single firm_id; the multi-period sweep needs per-actor menus
# that surface every firm's report on the period's as-of date).
# ---------------------------------------------------------------------------


def _build_actor_menu_and_selection(
    kernel: Any,
    *,
    profile: AttentionProfile,
    actor_kind: str,
    actor_id: str,
    as_of_date: str,
    phase_id: str | None,
) -> tuple[str, str]:
    """Return (menu_id, selection_id). Uses
    ``kernel.observation_menu_builder.build_menu`` + the v1.8.12
    public selector + ``AttentionBook.add_selection``.

    Idempotency: caller is responsible for not re-running the same
    period twice (the menu / selection ids embed the as-of date).
    """
    menu_id = _menu_id_for(actor_kind, actor_id, as_of_date)
    selection_id = _selection_id_for(actor_kind, actor_id, as_of_date)
    request_id = _menu_request_id_for(actor_kind, actor_id, as_of_date)

    request = ObservationMenuBuildRequest(
        request_id=request_id,
        actor_id=actor_id,
        as_of_date=as_of_date,
        phase_id=phase_id,
        metadata={"menu_id": menu_id},
    )
    kernel.observation_menu_builder.build_menu(request)
    menu = kernel.attention.get_menu(menu_id)

    selected_refs = select_observations_for_profile(kernel, profile, menu)
    selection = SelectedObservationSet(
        selection_id=selection_id,
        actor_id=actor_id,
        attention_profile_id=profile.profile_id,
        menu_id=menu_id,
        selected_refs=selected_refs,
        selection_reason="profile_match",
        as_of_date=as_of_date,
        phase_id=phase_id,
        status="completed" if selected_refs else "empty",
    )
    kernel.attention.add_selection(selection)
    return menu_id, selection_id


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


def run_living_reference_world(
    kernel: Any,
    *,
    firm_ids: Sequence[str],
    investor_ids: Sequence[str],
    bank_ids: Sequence[str],
    period_dates: Sequence[date | str] | None = None,
    phase_id: str | None = None,
    run_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    firm_baseline_values: Mapping[str, float] | None = None,
    valuation_baseline_default: float = 1_000_000.0,
    firm_industry_map: Mapping[str, str] | None = None,
    industry_demand_states: Mapping[
        str, tuple[str, float, float]
    ] | None = None,
    stewardship_theme_types: Sequence[str] | None = None,
    market_condition_specs: Sequence[
        tuple[str, str, str, str, float, float, str]
    ] | None = None,
    market_regime: str | None = None,
) -> LivingReferenceWorldResult:
    """
    Sweep the v1.8 endogenous chain plus the v1.9.4 / v1.9.5 / v1.9.7
    review-only mechanisms and the v1.10.1 → v1.10.4 engagement /
    strategic-response storage layer over ``period_dates``.

    The kernel must already be wired (variables / exposures / etc.
    seeded). The orchestrator is composition over existing helpers;
    it does **not** seed the world for the caller. Tests build their
    own kernel; the CLI (`run_living_reference_world.py`) builds a
    tiny inline fixture.

    Per-period flow (each phase invokes only existing component
    helpers — no new behavior is introduced):

    1. **Corporate phase** (v1.8.7) — one corporate quarterly
       report per firm.
    2. **Firm pressure phase** (v1.9.4) — one
       ``FirmPressureMechanismResult`` signal per firm.
    3. **Industry demand condition phase** (v1.10.4) — one
       :class:`IndustryDemandConditionRecord` per unique industry
       in ``firm_industry_map``. Synthetic context evidence;
       *not* a forecast.
    3a. **Capital-market condition phase** (v1.11.0) — one
        :class:`MarketConditionRecord` per market spec
        (reference rates, credit spreads, equity valuation
        environment, funding window, liquidity / volatility
        regime by default). Synthetic context evidence; *not*
        price formation, *not* yield-curve calibration.
    4. **Attention phase** (v1.8.11 + v1.8.12) — one menu + one
       selection per actor.
    5. **Valuation phase** (v1.9.5) — one
       :class:`ValuationRecord` per (investor, firm) pair.
    6. **Bank credit review phase** (v1.9.7) — one bank credit
       review note per (bank, firm) pair.
    7. **Dialogue phase** (v1.10.2) — one
       :class:`PortfolioCompanyDialogueRecord` per (investor, firm)
       pair. **Metadata only**: no transcript, no content, no
       notes, no minutes, no attendees.
    8. **Investor escalation phase** (v1.10.3, investor side) —
       one :class:`InvestorEscalationCandidate` per (investor,
       firm) pair. **Candidate only**: no vote_cast, no
       proposal_filed, no campaign_executed, no exit_executed,
       no letter_sent.
    9. **Corporate strategic response phase** (v1.10.3, corporate
       side) — one :class:`CorporateStrategicResponseCandidate`
       per firm. **Candidate only**: no buyback_executed, no
       dividend_changed, no divestment_executed, no
       merger_executed, no board_change_executed, no
       disclosure_filed. Industry-condition cross-references go
       in ``trigger_industry_condition_ids`` (v1.10.4.1
       type-correct slot); v1.11.0 capital-market condition
       cross-references go in ``trigger_market_condition_ids``
       (v1.11.0 type-correct slot). Neither ever rides in
       ``trigger_signal_ids``.
    10. **Review phase** — one investor review run + one bank
        review run.

    Setup-time (idempotent, fires once per kernel):

    - **Stewardship themes** (v1.10.1) — one
      :class:`StewardshipThemeRecord` per (investor, theme_type).

    Anti-scope (v1.10.5 carries forward verbatim from v1.9.x):
    no ``prices`` / ``ownership`` / ``contracts`` /
    ``constraints`` / ``institutions`` / ``external_processes`` /
    ``relationships`` book is mutated. No corporate-action
    execution, no voting execution, no proxy filing, no
    public-campaign execution, no disclosure-filing execution, no
    investment recommendation, no trading, no price formation, no
    lending decisions, no firm financial-statement updates, no
    demand / sales / revenue forecasting, no Japan calibration,
    no real-data ingestion, no jurisdiction-specific stewardship
    codes, no calibrated behavior probabilities. No scheduler
    hook, no auto-firing from ``tick()`` / ``run()``.
    """
    if kernel is None:
        raise ValueError(
            "kernel is required; v1.9.0 is orchestration only and does "
            "not build a kernel for the caller."
        )
    if kernel.observation_menu_builder is None:
        raise ValueError(
            "kernel.observation_menu_builder is None; "
            "construct WorldKernel through __post_init__ or wire it explicitly."
        )

    firms = _validate_id_list(firm_ids, name="firm_ids")
    investors = _validate_id_list(investor_ids, name="investor_ids")
    banks = _validate_id_list(bank_ids, name="bank_ids")

    if period_dates is None:
        period_dates = _DEFAULT_QUARTER_END_DATES
    raw_dates = list(period_dates)
    if len(raw_dates) == 0:
        raise ValueError("period_dates must not be empty")
    iso_dates = tuple(_coerce_iso_date(d) for d in raw_dates)

    rid = run_id or f"run:living:{iso_dates[0]}:{iso_dates[-1]}"

    ledger_count_before = len(kernel.ledger.records)

    # ------------------------------------------------------------------
    # Idempotent infra setup (interactions + per-actor profiles +
    # per-firm and per-actor routine specs). Each registration is a
    # no-op if it has already been done.
    # ------------------------------------------------------------------
    register_corporate_reporting_interaction(kernel)
    for firm_id in firms:
        register_corporate_quarterly_reporting_routine(kernel, firm_id=firm_id)

    register_investor_review_interaction(kernel)
    register_bank_review_interaction(kernel)

    investor_profiles: dict[str, AttentionProfile] = {}
    for investor_id in investors:
        investor_profiles[investor_id] = register_investor_attention_profile(
            kernel,
            investor_id=investor_id,
        )
        register_investor_review_routine(kernel, investor_id=investor_id)

    bank_profiles: dict[str, AttentionProfile] = {}
    for bank_id in banks:
        bank_profiles[bank_id] = register_bank_attention_profile(
            kernel,
            bank_id=bank_id,
        )
        register_bank_review_routine(kernel, bank_id=bank_id)

    # ------------------------------------------------------------------
    # v1.10.5 — engagement / strategic-response infra setup.
    # Register stewardship themes once for the run (idempotent).
    # Resolve the firm → industry mapping and the per-industry
    # demand-condition state map. These are inputs only; nothing
    # mechanism-shaped happens here.
    # ------------------------------------------------------------------
    theme_types = (
        tuple(stewardship_theme_types)
        if stewardship_theme_types is not None
        else _DEFAULT_STEWARDSHIP_THEME_TYPES
    )
    stewardship_theme_ids = _ensure_stewardship_themes(
        kernel,
        investor_ids=investors,
        theme_types=theme_types,
        effective_from=iso_dates[0],
    )

    firm_to_industry = _resolve_firm_industry_map(firms, firm_industry_map)
    # Deduplicated industry id list, sorted for determinism. Used
    # by the per-period industry-demand phase to emit one condition
    # per (industry, period). Sorting keeps the canonical view
    # stable across whatever insertion order the dict happens to
    # have produced.
    unique_industry_ids = tuple(
        sorted({iid for iid in firm_to_industry.values()})
    )

    industry_demand_state_map: dict[str, tuple[str, float, float]] = {}
    for industry_id in unique_industry_ids:
        if (
            industry_demand_states is not None
            and industry_id in industry_demand_states
        ):
            industry_demand_state_map[industry_id] = tuple(
                industry_demand_states[industry_id]
            )  # type: ignore[arg-type]
        else:
            industry_demand_state_map[industry_id] = (
                _INDUSTRY_DEMAND_DEFAULTS.get(
                    industry_id, _DEFAULT_INDUSTRY_DEMAND_STATE
                )
            )

    # v1.11.0 / v1.11.2 — capital-market condition specs.
    # Resolution order (most specific first):
    #   1. caller-supplied ``market_condition_specs`` — full
    #      override; the regime is ignored if both are provided.
    #   2. caller-supplied ``market_regime`` — selects one of the
    #      v1.11.2 named presets. Unknown names raise ValueError.
    #   3. fall back to the v1.11.0 default 5-market spec set
    #      (preserves backward compatibility for existing tests
    #      and the ``--markdown`` / ``--manifest`` digest).
    if market_regime is not None and market_regime not in _REGIME_PRESETS:
        raise ValueError(
            f"unknown market_regime {market_regime!r}; "
            f"valid options are {list(_REGIME_NAMES)!r}"
        )
    resolved_market_specs: tuple[
        tuple[str, str, str, str, float, float, str], ...
    ]
    if market_condition_specs is not None:
        resolved_market_specs = tuple(
            tuple(s) for s in market_condition_specs  # type: ignore[arg-type]
        )
    elif market_regime is not None:
        resolved_market_specs = _REGIME_PRESETS[market_regime]
    else:
        resolved_market_specs = _DEFAULT_MARKET_CONDITION_SPECS
    # Deduplicated, insertion-order-preserving market-id list.
    seen_market_ids: list[str] = []
    for spec in resolved_market_specs:
        if spec[0] not in seen_market_ids:
            seen_market_ids.append(spec[0])
    unique_market_ids = tuple(seen_market_ids)

    # ------------------------------------------------------------------
    # Per-period sweep
    # ------------------------------------------------------------------
    period_summaries: list[LivingReferencePeriodSummary] = []

    for period_idx, iso_date in enumerate(iso_dates):
        period_id = f"period:{rid}:{iso_date}"
        period_start_idx = len(kernel.ledger.records)

        corporate_run_ids: list[str] = []
        corporate_signal_ids: list[str] = []
        # Map firm_id -> corp signal id so the v1.9.6 pressure +
        # valuation phases can correlate per-firm evidence.
        corp_signal_by_firm: dict[str, str] = {}

        for firm_id in firms:
            result: CorporateReportingResult = run_corporate_quarterly_reporting(
                kernel, firm_id=firm_id, as_of_date=iso_date
            )
            corporate_run_ids.append(result.run_id)
            corporate_signal_ids.append(result.signal_id)
            corp_signal_by_firm[firm_id] = result.signal_id

        # ------------------------------------------------------------------
        # v1.9.6 — firm operating pressure assessment phase.
        # For each firm, resolve the firm's exposures from
        # ExposureBook, the visible variable observations from
        # WorldVariableBook, and pass the corporate signal as
        # optional auxiliary evidence. The mechanism is read-only
        # against the kernel; we resolve evidence ids for it.
        # ------------------------------------------------------------------
        visible_observations = (
            kernel.variables.list_observations_visible_as_of(iso_date)
        )
        visible_observation_ids = tuple(
            obs.observation_id for obs in visible_observations
        )

        firm_pressure_signal_ids: list[str] = []
        firm_pressure_run_ids: list[str] = []
        # Map firm_id -> pressure signal id for downstream valuation.
        pressure_signal_by_firm: dict[str, str] = {}

        for firm_id in firms:
            firm_exposures = kernel.exposures.list_by_subject(firm_id)
            firm_exposure_ids = tuple(e.exposure_id for e in firm_exposures)
            pressure_result: FirmPressureMechanismResult = (
                run_reference_firm_pressure_mechanism(
                    kernel,
                    firm_id=firm_id,
                    as_of_date=iso_date,
                    variable_observation_ids=visible_observation_ids,
                    exposure_ids=firm_exposure_ids,
                    corporate_signal_ids=(corp_signal_by_firm[firm_id],),
                )
            )
            firm_pressure_signal_ids.append(pressure_result.signal_id)
            firm_pressure_run_ids.append(pressure_result.run_record.run_id)
            pressure_signal_by_firm[firm_id] = pressure_result.signal_id

        # ------------------------------------------------------------------
        # v1.10.5 — industry demand condition phase (v1.10.4).
        # For each unique industry, emit one synthetic
        # ``IndustryDemandConditionRecord``. The (direction,
        # strength, confidence) triple is small, deterministic, and
        # explicitly *not* a forecast — values illustrate magnitude
        # ordering only. ``demand_strength`` and ``confidence`` are
        # bounded in [0.0, 1.0] inclusive per the v1.10.4 record
        # contract. The book's no-mutation discipline applies: only
        # ``IndustryConditionBook`` and the ledger are written to.
        # ------------------------------------------------------------------
        industry_condition_ids: list[str] = []
        condition_id_by_industry: dict[str, str] = {}
        for industry_id in unique_industry_ids:
            condition_id = _industry_condition_id_for(industry_id, iso_date)
            direction, strength, confidence = industry_demand_state_map[
                industry_id
            ]
            try:
                kernel.industry_conditions.add_condition(
                    IndustryDemandConditionRecord(
                        condition_id=condition_id,
                        industry_id=industry_id,
                        industry_label=_industry_label_for(industry_id),
                        as_of_date=iso_date,
                        condition_type="demand_assessment",
                        demand_direction=direction,
                        demand_strength=strength,
                        time_horizon="medium_term",
                        confidence=confidence,
                        status="active",
                        visibility="internal_only",
                    )
                )
            except DuplicateIndustryConditionError:
                kernel.industry_conditions.get_condition(condition_id)
            industry_condition_ids.append(condition_id)
            condition_id_by_industry[industry_id] = condition_id

        # ------------------------------------------------------------------
        # v1.11.0 — capital-market condition phase.
        # For each market spec, emit one synthetic
        # ``MarketConditionRecord``. The (direction, strength,
        # confidence) triple is small, deterministic, and explicitly
        # *not* a forecast — values illustrate ordering only.
        # ``strength`` and ``confidence`` are bounded in [0.0, 1.0]
        # inclusive per the v1.11.0 record contract. The book's
        # no-mutation discipline applies: only ``MarketConditionBook``
        # and the ledger are written to. No price formation, no
        # yield-curve calibration, no order matching, no clearing.
        # ------------------------------------------------------------------
        market_condition_ids: list[str] = []
        for (
            market_id,
            market_type,
            condition_type,
            direction,
            strength,
            confidence,
            time_horizon,
        ) in resolved_market_specs:
            mc_id = _market_condition_id_for(market_id, iso_date)
            try:
                kernel.market_conditions.add_condition(
                    MarketConditionRecord(
                        condition_id=mc_id,
                        market_id=market_id,
                        market_type=market_type,
                        as_of_date=iso_date,
                        condition_type=condition_type,
                        direction=direction,
                        strength=strength,
                        time_horizon=time_horizon,
                        confidence=confidence,
                        status="active",
                        visibility="internal_only",
                    )
                )
            except DuplicateMarketConditionError:
                kernel.market_conditions.get_condition(mc_id)
            market_condition_ids.append(mc_id)

        # ------------------------------------------------------------------
        # v1.11.1 — capital-market readout phase.
        # Deterministic banker-readable summary built from the
        # period's market_condition_ids. Per-market tone tags +
        # overall market-access label + banker-summary label.
        # Read-only over MarketConditionBook; writes only to
        # CapitalMarketReadoutBook + the kernel ledger. No
        # recommendation, no forecast, no pricing, no execution.
        # The builder is idempotent on the readout id; re-running
        # the orchestrator on the same kernel does not duplicate.
        # ------------------------------------------------------------------
        capital_market_readout_ids: list[str] = []
        if market_condition_ids:
            readout = build_capital_market_readout(
                kernel,
                as_of_date=iso_date,
                market_condition_ids=tuple(market_condition_ids),
            )
            capital_market_readout_ids.append(readout.readout_id)

        # ------------------------------------------------------------------
        # v1.12.2 — market environment state phase.
        # Normalize the period's market-condition + readout context
        # into nine compact regime labels (liquidity / volatility /
        # credit / funding / risk_appetite / rate_environment /
        # refinancing_window / equity_valuation /
        # overall_market_access). One environment state per period.
        # Cited downstream as the v1.12.2 evidence/trigger slot on
        # firm-state, investor-intent, and corporate strategic
        # response. Read-only over MarketConditionBook +
        # CapitalMarketReadoutBook + IndustryConditionBook; writes
        # only to MarketEnvironmentBook + the kernel ledger. No
        # recommendation, no forecast, no pricing, no execution.
        # Idempotent on the environment-state id; re-running the
        # orchestrator on the same kernel does not duplicate.
        # ------------------------------------------------------------------
        market_environment_state_ids: list[str] = []
        if market_condition_ids or capital_market_readout_ids:
            environment = build_market_environment_state(
                kernel,
                as_of_date=iso_date,
                market_condition_ids=tuple(market_condition_ids),
                market_readout_ids=tuple(capital_market_readout_ids),
                industry_condition_ids=tuple(industry_condition_ids),
            )
            market_environment_state_ids.append(
                environment.environment_state_id
            )

        # ------------------------------------------------------------------
        # v1.12.0 — firm financial latent state update phase.
        # For each firm, compute one synthetic
        # ``FirmFinancialStateRecord`` from prior state (resolved
        # via ``get_latest_for_firm``) plus this period's readout
        # / market-condition / industry-condition / pressure
        # signal evidence. This is the first time-crossing
        # endogenous state-update layer in public FWE: market
        # regimes and pressure evidence accumulate into the next
        # period's state. Not an accounting statement; not a
        # forecast; not a financial-statement update.
        # ------------------------------------------------------------------
        firm_financial_state_ids: list[str] = []
        firm_state_id_by_firm: dict[str, str] = {}
        for firm_id in firms:
            state_result = run_reference_firm_financial_state_update(
                kernel,
                firm_id=firm_id,
                as_of_date=iso_date,
                market_readout_ids=tuple(capital_market_readout_ids),
                market_condition_ids=tuple(market_condition_ids),
                market_environment_state_ids=tuple(
                    market_environment_state_ids
                ),
                industry_condition_ids=(
                    (condition_id_by_industry[firm_to_industry[firm_id]],)
                    if firm_to_industry[firm_id] in condition_id_by_industry
                    else ()
                ),
                pressure_signal_ids=(
                    pressure_signal_by_firm[firm_id],
                ),
            )
            firm_financial_state_ids.append(state_result.state_id)
            firm_state_id_by_firm[firm_id] = state_result.state_id

        # Attention phase. We iterate investors and banks in order so
        # the resulting summary tuples match the input order. Each
        # actor's menu picks up *every* firm's corporate signal that
        # is visible on `iso_date` because the v1.8.12 selection rule
        # filters by signal_type, not by signal_id, and the
        # corporate-quarterly-report signal_type matches both the
        # default investor and the default bank profile. The v1.9.4
        # firm-pressure-assessment signals are emitted with
        # ``visibility="public"`` and so are also visible in any
        # downstream menu query; v1.9.6 surfaces them to the
        # valuation mechanism by direct id-passing rather than via
        # selection (selection of pressure signals would require a
        # v1.9.x AttentionProfile vocabulary extension; we stay
        # additive here).
        investor_menu_ids: list[str] = []
        investor_selection_ids: list[str] = []
        for investor_id in investors:
            menu_id, selection_id = _build_actor_menu_and_selection(
                kernel,
                profile=investor_profiles[investor_id],
                actor_kind="investor",
                actor_id=investor_id,
                as_of_date=iso_date,
                phase_id=phase_id,
            )
            investor_menu_ids.append(menu_id)
            investor_selection_ids.append(selection_id)

        bank_menu_ids: list[str] = []
        bank_selection_ids: list[str] = []
        for bank_id in banks:
            menu_id, selection_id = _build_actor_menu_and_selection(
                kernel,
                profile=bank_profiles[bank_id],
                actor_kind="bank",
                actor_id=bank_id,
                as_of_date=iso_date,
                phase_id=phase_id,
            )
            bank_menu_ids.append(menu_id)
            bank_selection_ids.append(selection_id)

        # ------------------------------------------------------------------
        # v1.9.6 — valuation refresh lite phase.
        # For each (investor, firm) pair, the v1.9.5 valuation
        # mechanism produces one opinionated synthetic
        # `ValuationRecord`. Inputs: the firm's pressure signal,
        # the firm's corporate report, and the investor's per-period
        # selection. The valuation is *one valuer's claim under
        # synthetic assumptions*; it does NOT move any price, NOT
        # make a decision, NOT update any firm financial statement.
        # The v1.9.5 metadata flags `no_price_movement` /
        # `no_investment_advice` / `synthetic_only` are stamped on
        # every produced record. Bank-side valuation is intentionally
        # out of scope for v1.9.6 (a future stakeholder-pressure
        # milestone may extend it).
        # ------------------------------------------------------------------
        valuation_ids: list[str] = []
        valuation_mechanism_run_ids: list[str] = []
        baselines = dict(firm_baseline_values or {})

        for investor_id, investor_selection_id in zip(
            investors, investor_selection_ids
        ):
            for firm_id in firms:
                baseline = baselines.get(firm_id, valuation_baseline_default)
                valuation_id = (
                    f"valuation:reference_lite:{investor_id}:{firm_id}:{iso_date}"
                )
                # The v1.9.5 default request_id formula
                # ``req:valuation_refresh_lite:{firm}:{date}``
                # collides when multiple investors value the same
                # firm on the same date — the resulting
                # ``mechanism_run:`` ids would alias. v1.9.6 passes
                # an explicit request_id that includes the valuer
                # so each (investor, firm, period) gets a unique
                # audit lineage.
                valuation_request_id = (
                    f"req:valuation_refresh_lite:{investor_id}:"
                    f"{firm_id}:{iso_date}"
                )
                valuation_result: ValuationRefreshLiteResult = (
                    run_reference_valuation_refresh_lite(
                        kernel,
                        firm_id=firm_id,
                        valuer_id=investor_id,
                        as_of_date=iso_date,
                        pressure_signal_ids=(pressure_signal_by_firm[firm_id],),
                        corporate_signal_ids=(corp_signal_by_firm[firm_id],),
                        selected_observation_set_ids=(investor_selection_id,),
                        baseline_value=baseline,
                        valuation_id=valuation_id,
                        request_id=valuation_request_id,
                    )
                )
                valuation_ids.append(valuation_result.valuation_id)
                valuation_mechanism_run_ids.append(
                    valuation_result.run_record.run_id
                )

        # ------------------------------------------------------------------
        # v1.9.7 — bank credit review lite phase.
        # For each (bank, firm) pair, the v1.9.7 mechanism produces
        # one synthetic ``bank_credit_review_note`` signal. Inputs:
        # the firm's pressure signal + every valuation on that
        # firm (across all investors) + the firm's corporate
        # report + the bank's per-period selection. The note is
        # *one bank's recordable diagnostic*; it does NOT make a
        # lending decision, NOT enforce a covenant, NOT mutate
        # any contract or constraint, NOT declare default. The
        # v1.9.7 metadata flags
        # `no_lending_decision` / `no_covenant_enforcement` /
        # `no_contract_mutation` / `no_constraint_mutation` /
        # `no_default_declaration` / `no_internal_rating` /
        # `no_probability_of_default` / `synthetic_only` are
        # stamped on every produced record.
        #
        # Complexity note: this phase iterates banks × firms
        # within each period. With the default fixture (2 banks,
        # 3 firms, 4 periods) that is 24 reviews — well within
        # the small-synthetic-demo budget. Larger fixtures should
        # consider a sparser policy (e.g., the bank only reviews
        # firms in its declared exposure scope).
        # ------------------------------------------------------------------
        bank_credit_review_signal_ids: list[str] = []
        bank_credit_review_mechanism_run_ids: list[str] = []

        for bank_id, bank_selection_id in zip(banks, bank_selection_ids):
            for firm_id in firms:
                # All valuations on this firm in this period.
                firm_valuation_ids = tuple(
                    vid
                    for vid in valuation_ids
                    # ids embed both investor and firm; filter by
                    # the firm-suffix marker the v1.9.6 helper
                    # constructs:
                    # ``valuation:reference_lite:<inv>:<firm>:<date>``
                    if f":{firm_id}:" in vid
                )
                review_result: BankCreditReviewLiteResult = (
                    run_reference_bank_credit_review_lite(
                        kernel,
                        bank_id=bank_id,
                        firm_id=firm_id,
                        as_of_date=iso_date,
                        pressure_signal_ids=(
                            pressure_signal_by_firm[firm_id],
                        ),
                        valuation_ids=firm_valuation_ids,
                        corporate_signal_ids=(
                            corp_signal_by_firm[firm_id],
                        ),
                        selected_observation_set_ids=(
                            bank_selection_id,
                        ),
                    )
                )
                bank_credit_review_signal_ids.append(review_result.signal_id)
                bank_credit_review_mechanism_run_ids.append(
                    review_result.run_record.run_id
                )

        # ------------------------------------------------------------------
        # v1.10.5 — dialogue / escalation / response phases (v1.10.2 +
        # v1.10.3). All three are storage-only, candidate-only,
        # content-free. None of them executes voting, proxy filing,
        # public-campaign, exit, AGM/EGM action, corporate-action
        # execution, disclosure filing, investment recommendation,
        # trading, or price formation. Cross-references are recorded
        # as plain ids and not validated against any other book.
        # ------------------------------------------------------------------

        # v1.10.2 dialogue phase — one record per (investor, firm)
        # per period. Carries ``dialogue metadata only``: the
        # initiator, the counterparty, the period, the references to
        # this period's stewardship themes / corporate signals /
        # pressure signals / valuations. No transcript, no content,
        # no notes, no minutes, no attendees.
        dialogue_ids: list[str] = []
        dialogue_id_by_pair: dict[tuple[str, str], str] = {}
        themes_by_investor: dict[str, tuple[str, ...]] = {}
        for investor_id in investors:
            themes_by_investor[investor_id] = tuple(
                _theme_id_for(investor_id, t) for t in theme_types
            )

        for investor_id in investors:
            for firm_id in firms:
                dialogue_id = _dialogue_id_for(investor_id, firm_id, iso_date)
                investor_theme_ids = themes_by_investor[investor_id]
                # The investor's per-period valuations on this firm
                # (filtered by the embedded firm marker). Keeps the
                # link audit-grade without re-running v1.9.5.
                related_valuations = tuple(
                    vid
                    for vid in valuation_ids
                    if f":{investor_id}:{firm_id}:" in vid
                )
                try:
                    kernel.engagement.add_dialogue(
                        PortfolioCompanyDialogueRecord(
                            dialogue_id=dialogue_id,
                            initiator_id=investor_id,
                            counterparty_id=firm_id,
                            initiator_type="investor",
                            counterparty_type="firm",
                            as_of_date=iso_date,
                            dialogue_type="private_meeting",
                            status="logged",
                            outcome_label="acknowledged",
                            next_step_label="continue_monitoring",
                            visibility="internal_only",
                            theme_ids=investor_theme_ids,
                            related_signal_ids=(
                                corp_signal_by_firm[firm_id],
                            ),
                            related_valuation_ids=related_valuations,
                            related_pressure_signal_ids=(
                                pressure_signal_by_firm[firm_id],
                            ),
                        )
                    )
                except DuplicateDialogueError:
                    kernel.engagement.get_dialogue(dialogue_id)
                dialogue_ids.append(dialogue_id)
                dialogue_id_by_pair[(investor_id, firm_id)] = dialogue_id

        # v1.10.3 investor escalation candidate phase — one
        # candidate per (investor, firm) per period. The candidate
        # names the *option*, never the *act*: no vote_cast, no
        # proposal_filed, no campaign_executed, no exit_executed,
        # no letter_sent. References this period's themes,
        # dialogues, corporate signal, pressure signal, and
        # valuations on this (investor, firm) pair.
        investor_escalation_candidate_ids: list[str] = []
        for investor_id in investors:
            investor_theme_ids = themes_by_investor[investor_id]
            for firm_id in firms:
                escalation_id = _escalation_id_for(
                    investor_id, firm_id, iso_date
                )
                related_valuations = tuple(
                    vid
                    for vid in valuation_ids
                    if f":{investor_id}:{firm_id}:" in vid
                )
                dialogue_ref = (
                    dialogue_id_by_pair[(investor_id, firm_id)],
                )
                try:
                    kernel.escalations.add_candidate(
                        InvestorEscalationCandidate(
                            escalation_candidate_id=escalation_id,
                            investor_id=investor_id,
                            target_company_id=firm_id,
                            as_of_date=iso_date,
                            escalation_type="private_letter",
                            status="draft",
                            priority="medium",
                            horizon="medium_term",
                            rationale_label="no_response",
                            next_step_label="continue_monitoring",
                            visibility="internal_only",
                            theme_ids=investor_theme_ids,
                            dialogue_ids=dialogue_ref,
                            related_signal_ids=(
                                corp_signal_by_firm[firm_id],
                                pressure_signal_by_firm[firm_id],
                            ),
                            related_valuation_ids=related_valuations,
                        )
                    )
                except DuplicateEscalationCandidateError:
                    kernel.escalations.get_candidate(escalation_id)
                investor_escalation_candidate_ids.append(escalation_id)

        # ------------------------------------------------------------------
        # v1.12.1 — investor intent signal phase.
        # For each (investor, firm) pair, build one synthetic
        # ``InvestorIntentRecord`` that conditions a pre-action
        # review posture on the cited evidence: the investor's
        # period selection (attention), the period's market
        # readout, the firm's latent state, the (investor, firm)
        # pair's valuation, the (investor, firm) pair's dialogue,
        # the (investor, firm) pair's escalation candidate, and
        # the investor's stewardship themes. Pre-trade /
        # pre-decision posture only — never an order, trade,
        # rebalance, allocation, or recommendation.
        # ------------------------------------------------------------------
        investor_intent_ids: list[str] = []
        investor_selection_id_by_investor = dict(
            zip(investors, investor_selection_ids)
        )
        for investor_id in investors:
            inv_selection = investor_selection_id_by_investor.get(investor_id)
            inv_themes = themes_by_investor[investor_id]
            for firm_id in firms:
                pair_dialogue = dialogue_id_by_pair.get(
                    (investor_id, firm_id)
                )
                pair_escalation = _escalation_id_for(
                    investor_id, firm_id, iso_date
                )
                pair_valuation = tuple(
                    vid
                    for vid in valuation_ids
                    if f":{investor_id}:{firm_id}:" in vid
                )
                firm_state = firm_state_id_by_firm.get(firm_id)
                intent_result = run_reference_investor_intent_signal(
                    kernel,
                    investor_id=investor_id,
                    target_company_id=firm_id,
                    as_of_date=iso_date,
                    selected_observation_set_ids=(
                        (inv_selection,) if inv_selection else ()
                    ),
                    market_readout_ids=tuple(capital_market_readout_ids),
                    market_condition_ids=tuple(market_condition_ids),
                    market_environment_state_ids=tuple(
                        market_environment_state_ids
                    ),
                    firm_state_ids=((firm_state,) if firm_state else ()),
                    valuation_ids=pair_valuation,
                    dialogue_ids=(
                        (pair_dialogue,) if pair_dialogue else ()
                    ),
                    escalation_candidate_ids=(pair_escalation,),
                    stewardship_theme_ids=inv_themes,
                )
                investor_intent_ids.append(intent_result.intent_id)

        # v1.10.3 corporate strategic response candidate phase — one
        # candidate per firm per period. Symmetric to the escalation
        # candidate, but on the corporate side. The candidate names
        # the *option*, never the *act*: no buyback_executed, no
        # dividend_changed, no divestment_executed, no
        # merger_executed, no board_change_executed, no
        # disclosure_filed. References this period's themes (every
        # investor that talked to the firm), dialogues with this
        # firm, corporate signal, pressure signal, valuations on
        # this firm, and the firm's industry's demand condition (via
        # the v1.10.4.1 type-correct ``trigger_industry_condition_ids``
        # slot — never via ``trigger_signal_ids``).
        corporate_strategic_response_candidate_ids: list[str] = []
        for firm_id in firms:
            response_id = _response_id_for(firm_id, iso_date)
            firm_dialogues = tuple(
                dialogue_id_by_pair[(inv, firm_id)]
                for inv in investors
            )
            firm_valuations = tuple(
                vid for vid in valuation_ids if f":{firm_id}:" in vid
            )
            # Themes from every investor (since any investor's
            # theme could shape a corporate response). Sorted so the
            # canonical view stays deterministic.
            firm_theme_refs = tuple(
                sorted(
                    {
                        tid
                        for inv in investors
                        for tid in themes_by_investor[inv]
                    }
                )
            )
            firm_industry_id = firm_to_industry[firm_id]
            firm_condition_ref: tuple[str, ...] = ()
            if firm_industry_id in condition_id_by_industry:
                firm_condition_ref = (
                    condition_id_by_industry[firm_industry_id],
                )
            # v1.11.0 — every period's full set of capital-market
            # condition ids is cited as context for every corporate
            # response candidate (every firm's response is shaped by
            # the same rate / spread / equity / funding / liquidity
            # context this period). Cited via the v1.11.0
            # ``trigger_market_condition_ids`` slot, never via
            # ``trigger_signal_ids`` or
            # ``trigger_industry_condition_ids``.
            firm_market_condition_refs = tuple(market_condition_ids)
            try:
                kernel.strategic_responses.add_candidate(
                    CorporateStrategicResponseCandidate(
                        response_candidate_id=response_id,
                        company_id=firm_id,
                        as_of_date=iso_date,
                        response_type="capital_allocation_review",
                        status="draft",
                        priority="medium",
                        horizon="medium_term",
                        expected_effect_label=(
                            "expected_efficiency_improvement_candidate"
                        ),
                        constraint_label="subject_to_internal_review",
                        visibility="internal_only",
                        trigger_theme_ids=firm_theme_refs,
                        trigger_dialogue_ids=firm_dialogues,
                        trigger_signal_ids=(
                            corp_signal_by_firm[firm_id],
                            pressure_signal_by_firm[firm_id],
                        ),
                        trigger_valuation_ids=firm_valuations,
                        trigger_industry_condition_ids=firm_condition_ref,
                        trigger_market_condition_ids=firm_market_condition_refs,
                        trigger_market_environment_state_ids=tuple(
                            market_environment_state_ids
                        ),
                    )
                )
            except DuplicateResponseCandidateError:
                kernel.strategic_responses.get_candidate(response_id)
            corporate_strategic_response_candidate_ids.append(response_id)

        # Review phase. Each review run consumes exactly the actor's
        # period selection.
        investor_review_run_ids: list[str] = []
        investor_review_signal_ids: list[str] = []
        for investor_id, selection_id in zip(investors, investor_selection_ids):
            review = run_investor_review(
                kernel,
                investor_id=investor_id,
                selected_observation_set_ids=(selection_id,),
                as_of_date=iso_date,
                phase_id=phase_id or "post_close",
            )
            investor_review_run_ids.append(review.run_id)
            investor_review_signal_ids.append(review.signal_id)

        bank_review_run_ids: list[str] = []
        bank_review_signal_ids: list[str] = []
        for bank_id, selection_id in zip(banks, bank_selection_ids):
            review = run_bank_review(
                kernel,
                bank_id=bank_id,
                selected_observation_set_ids=(selection_id,),
                as_of_date=iso_date,
                phase_id=phase_id or "post_close",
            )
            bank_review_run_ids.append(review.run_id)
            bank_review_signal_ids.append(review.signal_id)

        period_end_idx = len(kernel.ledger.records)

        period_summaries.append(
            LivingReferencePeriodSummary(
                period_id=period_id,
                as_of_date=iso_date,
                corporate_signal_ids=tuple(corporate_signal_ids),
                corporate_run_ids=tuple(corporate_run_ids),
                firm_pressure_signal_ids=tuple(firm_pressure_signal_ids),
                firm_pressure_run_ids=tuple(firm_pressure_run_ids),
                valuation_ids=tuple(valuation_ids),
                valuation_mechanism_run_ids=tuple(valuation_mechanism_run_ids),
                bank_credit_review_signal_ids=tuple(
                    bank_credit_review_signal_ids
                ),
                bank_credit_review_mechanism_run_ids=tuple(
                    bank_credit_review_mechanism_run_ids
                ),
                investor_menu_ids=tuple(investor_menu_ids),
                bank_menu_ids=tuple(bank_menu_ids),
                investor_selection_ids=tuple(investor_selection_ids),
                bank_selection_ids=tuple(bank_selection_ids),
                investor_review_run_ids=tuple(investor_review_run_ids),
                bank_review_run_ids=tuple(bank_review_run_ids),
                investor_review_signal_ids=tuple(investor_review_signal_ids),
                bank_review_signal_ids=tuple(bank_review_signal_ids),
                industry_condition_ids=tuple(industry_condition_ids),
                stewardship_theme_ids=stewardship_theme_ids,
                dialogue_ids=tuple(dialogue_ids),
                investor_escalation_candidate_ids=tuple(
                    investor_escalation_candidate_ids
                ),
                corporate_strategic_response_candidate_ids=tuple(
                    corporate_strategic_response_candidate_ids
                ),
                market_condition_ids=tuple(market_condition_ids),
                capital_market_readout_ids=tuple(
                    capital_market_readout_ids
                ),
                market_environment_state_ids=tuple(
                    market_environment_state_ids
                ),
                firm_financial_state_ids=tuple(firm_financial_state_ids),
                investor_intent_ids=tuple(investor_intent_ids),
                record_count_created=period_end_idx - period_start_idx,
                metadata={
                    "period_index": period_idx,
                    "ledger_record_count_before": period_start_idx,
                    "ledger_record_count_after": period_end_idx,
                },
            )
        )

    ledger_count_after = len(kernel.ledger.records)
    created_record_ids = _ledger_object_ids_since(
        kernel, since_index=ledger_count_before
    )

    return LivingReferenceWorldResult(
        run_id=rid,
        period_count=len(iso_dates),
        firm_ids=firms,
        investor_ids=investors,
        bank_ids=banks,
        per_period_summaries=tuple(period_summaries),
        created_record_ids=created_record_ids,
        ledger_record_count_before=ledger_count_before,
        ledger_record_count_after=ledger_count_after,
        industry_ids=unique_industry_ids,
        stewardship_theme_ids=stewardship_theme_ids,
        market_ids=unique_market_ids,
        metadata=dict(metadata or {}),
    )
