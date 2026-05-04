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
from world.interbank_liquidity import (
    DuplicateInterbankLiquidityStateError,
    InterbankLiquidityStateRecord,
)
from world.attention_feedback import (
    FOCUS_LABEL_DIALOGUE,
    FOCUS_LABEL_ENGAGEMENT,
    FOCUS_LABEL_ESCALATION,
    FOCUS_LABEL_FIRM_STATE,
    FOCUS_LABEL_MARKET_ENVIRONMENT,
    FOCUS_LABEL_VALUATION,
    apply_attention_budget,
    build_attention_feedback,
)
from world.investor_intent import (
    run_attention_conditioned_investor_intent_signal,
)
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
    run_attention_conditioned_bank_credit_review_lite,
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
    run_attention_conditioned_valuation_refresh_lite,
)
from world.corporate_financing import (
    CorporateFinancingNeedRecord,
    DuplicateCorporateFinancingNeedError,
)
from world.funding_options import (
    DuplicateFundingOptionCandidateError,
    FundingOptionCandidate,
)
from world.capital_structure import (
    CapitalStructureReviewCandidate,
    DuplicateCapitalStructureReviewError,
)
from world.financing_paths import (
    DuplicateCorporateFinancingPathError,
    build_corporate_financing_path,
)
from world.securities import (
    DuplicateListedSecurityError,
    DuplicateMarketVenueError,
    ListedSecurityRecord,
    MarketVenueRecord,
    SAFE_INTENT_LABELS,
)
from world.market_intents import (
    DuplicateInvestorMarketIntentError,
    InvestorMarketIntentRecord,
)
from world.market_interest import (
    DuplicateAggregatedMarketInterestError,
    build_aggregated_market_interest,
)
from world.market_pressure import (
    DuplicateIndicativeMarketPressureError,
    build_indicative_market_pressure,
)
from world.market_intent_classifier import (
    classify_market_intent_direction,
)
from world.information_release import (
    DuplicateInformationArrivalError,
    DuplicateInformationReleaseCalendarError,
    DuplicateScheduledIndicatorReleaseError,
    InformationArrivalRecord,
    InformationReleaseCalendar,
    ScheduledIndicatorRelease,
)
from world.reference_universe import (
    DuplicateGenericSectorReferenceError,
    DuplicateReferenceUniverseProfileError,
    DuplicateSyntheticSectorFirmProfileError,
    build_generic_11_sector_reference_universe,
    default_firm_id_order,
)
from world.scenario_applications import apply_scenario_driver
from world.scenario_drivers import (
    DuplicateScenarioDriverTemplateError,
    ScenarioDriverTemplate,
)
from world.scenario_schedule import (
    DuplicateScenarioScheduleError,
    DuplicateScheduledScenarioApplicationError,
    build_default_scenario_monthly_schedule,
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
    # v1.12.8 additive: one ActorAttentionStateRecord +
    # AttentionFeedbackRecord per actor per period (one per
    # investor + one per bank). The records describe what the
    # actor will *focus on* in the next period; the
    # ``previous_attention_state_id`` chains every actor's
    # series across periods. Synthetic, deterministic,
    # non-binding labels — never a forecast, never a behavior
    # probability.
    investor_attention_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    investor_attention_feedback_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    bank_attention_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    bank_attention_feedback_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    # v1.12.8 additive: per-period **memory selection** —
    # one extra `SelectedObservationSet` per actor that the
    # orchestrator builds at period N+1 from the actor's
    # prior-period attention state. Empty in period 0 (no
    # prior state yet). Carries the prior-period evidence the
    # actor's focus_labels point at, so the v1.12.4 / v1.12.5
    # / v1.12.6 helpers see *wider* selected evidence than
    # they would without feedback.
    investor_memory_selection_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    bank_memory_selection_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    # v1.14.5 additive: corporate financing reasoning chain.
    # ``corporate_financing_need_ids`` carries one entry per
    # firm per period; ``funding_option_candidate_ids`` carries
    # the full set of option-candidate ids the period emitted
    # (default: 2 per need); ``capital_structure_review_candidate_ids``
    # carries one entry per firm per period; ``corporate_financing_path_ids``
    # carries one entry per firm per period and links the
    # need / option / review ids into one auditable subgraph
    # via :func:`world.financing_paths.build_corporate_financing_path`.
    # Storage / audit / graph-linking only — never an order, trade,
    # allocation, loan approval, security issuance, pricing, or
    # recommendation.
    corporate_financing_need_ids: tuple[str, ...] = field(default_factory=tuple)
    funding_option_candidate_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    capital_structure_review_candidate_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    corporate_financing_path_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    # v1.15.5 additive: securities market intent chain.
    # ``investor_market_intent_ids`` carries one entry per
    # (investor, listed security) pair per period (default
    # I × F = 6 per period); ``aggregated_market_interest_ids``
    # carries one entry per security per period (default F = 3);
    # ``indicative_market_pressure_ids`` carries one entry per
    # security per period (default F = 3). Storage / aggregation
    # only — never an order, trade, allocation, price, quote,
    # clearing, settlement, or recommendation.
    investor_market_intent_ids: tuple[str, ...] = field(default_factory=tuple)
    aggregated_market_interest_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    indicative_market_pressure_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    # v1.19.3 additive: synthetic information-release citations for
    # the monthly_reference run profile. Both tuples are empty for
    # the default quarterly_default profile so the v1.18.last
    # canonical view stays byte-identical. ``scheduled_release_ids``
    # carries the calendar entries scheduled for this period;
    # ``information_arrival_ids`` carries the arrival records
    # emitted during this period (one per scheduled release that
    # arrived). Storage / citation only — never an actor decision,
    # never a price record.
    scheduled_release_ids: tuple[str, ...] = field(default_factory=tuple)
    information_arrival_ids: tuple[str, ...] = field(default_factory=tuple)
    # v1.20.3 additive: scenario-monthly-reference-universe profile
    # citations. Empty for ``quarterly_default`` /
    # ``monthly_reference``. ``reference_universe_ids`` carries at
    # most one profile id (echoed on every period summary so a
    # downstream consumer can correlate the period with the
    # universe without joining against the result-level setup);
    # ``sector_ids`` / ``firm_profile_ids`` echo the run-wide
    # 11-sector / 11-firm reference set; ``scenario_schedule_ids``
    # / ``scheduled_scenario_application_ids`` echo the run-wide
    # default schedule;
    # ``scenario_application_ids`` / ``scenario_context_shift_ids``
    # carry the *per-period* scenario application + bounded
    # context shifts emitted by the apply_scenario_driver helper —
    # only populated in the scheduled month
    # (``period_index == 3`` / ``month_04``); empty otherwise.
    # Storage / citation only — never a price record, never an
    # actor decision, never an order, trade, or financing
    # execution.
    reference_universe_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    sector_ids: tuple[str, ...] = field(default_factory=tuple)
    firm_profile_ids: tuple[str, ...] = field(default_factory=tuple)
    scenario_schedule_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    scheduled_scenario_application_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    scenario_application_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    scenario_context_shift_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
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
            "investor_attention_state_ids",
            "investor_attention_feedback_ids",
            "bank_attention_state_ids",
            "bank_attention_feedback_ids",
            "investor_memory_selection_ids",
            "bank_memory_selection_ids",
            "corporate_financing_need_ids",
            "funding_option_candidate_ids",
            "capital_structure_review_candidate_ids",
            "corporate_financing_path_ids",
            "investor_market_intent_ids",
            "aggregated_market_interest_ids",
            "indicative_market_pressure_ids",
            "scheduled_release_ids",
            "information_arrival_ids",
            "reference_universe_ids",
            "sector_ids",
            "firm_profile_ids",
            "scenario_schedule_ids",
            "scheduled_scenario_application_ids",
            "scenario_application_ids",
            "scenario_context_shift_ids",
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
    # v1.15.5 additive: setup-level securities-market context.
    # The ``listed_security_ids`` tuple names the synthetic
    # listed securities the run registered (one per firm by
    # default); ``market_venue_ids`` names the venues. Both
    # tuples are setup-once — they are not multiplied per period.
    listed_security_ids: tuple[str, ...] = field(default_factory=tuple)
    market_venue_ids: tuple[str, ...] = field(default_factory=tuple)
    # v1.20.3 additive: setup-level scenario-monthly-reference-
    # universe context. All tuples are empty for
    # ``quarterly_default`` / ``monthly_reference`` so the
    # corresponding pinned digests stay byte-identical.
    # ``reference_universe_ids`` carries the registered universe
    # profile id (singleton); ``sector_ids`` / ``firm_profile_ids``
    # name the 11 sectors and 11 representative firms; the
    # ``scenario_schedule_ids`` / ``scheduled_scenario_application_ids``
    # tuples name the v1.20.2 schedule rows registered once at
    # setup. Run-time scenario applications + context shifts live
    # on the per-period summary, not here.
    reference_universe_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    sector_ids: tuple[str, ...] = field(default_factory=tuple)
    firm_profile_ids: tuple[str, ...] = field(default_factory=tuple)
    scenario_schedule_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    scheduled_scenario_application_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
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
            "listed_security_ids",
            "market_venue_ids",
            "reference_universe_ids",
            "sector_ids",
            "firm_profile_ids",
            "scenario_schedule_ids",
            "scheduled_scenario_application_ids",
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


# v1.19.3 — closed-set of run-profile labels accepted by the
# orchestrator. v1.20.3 added the opt-in
# ``scenario_monthly_reference_universe`` profile alongside the
# pre-existing ``quarterly_default`` and ``monthly_reference``
# profiles; the v1.18.last canonical digest for
# ``quarterly_default`` and the v1.19.3 pinned digest for
# ``monthly_reference`` remain byte-identical.
_SUPPORTED_RUN_PROFILE_LABELS: frozenset[str] = frozenset(
    {
        "quarterly_default",
        "monthly_reference",
        "scenario_monthly_reference_universe",
    }
)


# v1.20.3 — default identifiers for the
# ``scenario_monthly_reference_universe`` run profile. The
# orchestrator does **not** auto-substitute these defaults; a
# caller must pass ``firm_ids`` / ``investor_ids`` / ``bank_ids``
# explicitly. The constants are exposed so tests / examples can
# build the canonical fixture.
#
# Investors and banks are bounded synthetic *archetypes* —
# **not** real institutions. The bank prefix (``bank:reference_``)
# and investor prefix (``investor:reference_``) match the
# pre-existing v1.9 / v1.18 naming convention.
_DEFAULT_SCENARIO_UNIVERSE_INVESTOR_IDS: tuple[str, ...] = (
    "investor:reference_benchmark_sensitive_institutional",
    "investor:reference_active_fund_like",
    "investor:reference_liquidity_sensitive_investor",
    "investor:reference_stewardship_oriented_investor",
)
_DEFAULT_SCENARIO_UNIVERSE_BANK_IDS: tuple[str, ...] = (
    "bank:reference_relationship_bank_like",
    "bank:reference_credit_conservative_bank",
    "bank:reference_market_liquidity_sensitive_bank",
)
# v1.20.3 — default firm ids resolve through the v1.20.1
# generic 11-sector universe builder. Names mirror sector labels
# minus the ``_like`` suffix.
_DEFAULT_SCENARIO_UNIVERSE_FIRM_IDS: tuple[str, ...] = (
    default_firm_id_order()
)


# v1.20.3 — pinned identifiers for the credit-tightening scenario
# template + the default scheduled scenario application. The
# storage layer (v1.20.2) emits the schedule + scheduled
# application; the run profile (v1.20.3) emits the actual
# :class:`ScenarioDriverApplicationRecord` and bounded
# :class:`ScenarioContextShiftRecord` set.
_DEFAULT_SCENARIO_DRIVER_TEMPLATE_ID: str = (
    "scenario_driver:credit_tightening:reference"
)
_DEFAULT_SCENARIO_SCHEDULED_PERIOD_INDEX: int = 3
_DEFAULT_SCENARIO_SCHEDULED_MONTH_LABEL: str = "month_04"


# v1.19.3 — synthetic 12-month period schedule for the
# ``monthly_reference`` profile. Month-end ISO strings, no real
# release dates. Calendar year 2026 is a deterministic synthetic
# choice mirroring v1.9 / v1.18 fixtures; it is not a forecast
# horizon.
_DEFAULT_MONTHLY_PERIOD_DATES: tuple[str, ...] = (
    "2026-01-31",
    "2026-02-28",
    "2026-03-31",
    "2026-04-30",
    "2026-05-31",
    "2026-06-30",
    "2026-07-31",
    "2026-08-31",
    "2026-09-30",
    "2026-10-31",
    "2026-11-30",
    "2026-12-31",
)


# v1.19.3 — default monthly information-release fixture. Each
# entry is ``(indicator_family_label, release_cadence_label,
# release_importance_label, scheduled_period_indices_1based,
# expected_attention_surface_labels)``. Months use 1-based
# indexing (1 = January) to match the v1.19.0 design table. Only
# ``central_bank_policy`` / ``inflation`` / ``labor_market`` /
# ``production_supply`` / ``consumption_demand`` /
# ``gdp_national_accounts`` / ``market_liquidity`` families are
# populated; ``capex_investment`` / ``fiscal_policy`` /
# ``sector_specific`` / ``information_gap`` are intentionally
# omitted from the default fixture so the per-month arrival count
# stays in [3, 5] and the run total stays in [36, 60].
#
# Per-month arrival counts (with the default fixture):
#   month 1 (Jan): inflation, labor_market, production_supply,
#                  market_liquidity                       = 4
#   month 2 (Feb): inflation, labor_market, production_supply,
#                  market_liquidity                       = 4
#   month 3 (Mar): inflation, labor_market, production_supply,
#                  consumption_demand, gdp_national_accounts,
#                  market_liquidity                       = 6  -> trim
#   month 4 (Apr): central_bank_policy, inflation,
#                  labor_market, production_supply,
#                  market_liquidity                       = 5
#   ...
#
# To respect the [3, 5] per-month bound we drop
# ``production_supply`` from the four "quarterly closing" months
# (3 / 6 / 9 / 12) where ``consumption_demand`` and
# ``gdp_national_accounts`` already fire.
_DefaultReleaseSpec = tuple[str, str, str, tuple[int, ...], tuple[str, ...]]

_DEFAULT_MONTHLY_RELEASE_SPECS: tuple[_DefaultReleaseSpec, ...] = (
    (
        "central_bank_policy",
        "meeting_based",
        "regime_relevant",
        (4, 8, 12),
        ("market_environment", "attention_surface"),
    ),
    (
        "inflation",
        "monthly",
        "regime_relevant",
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
        ("market_environment", "firm_financial_state"),
    ),
    (
        "labor_market",
        "monthly",
        "routine",
        # Trim months 3, 6, 9, 12 where the quarterly cluster
        # already fires; per-month arrival count stays bounded
        # at [3, 5].
        (1, 2, 4, 5, 7, 8, 10, 11),
        ("firm_financial_state",),
    ),
    (
        "production_supply",
        "monthly",
        "routine",
        # Trim months 3, 6, 9, 12 where the quarterly cluster
        # already fires; per-month arrival count stays bounded
        # at [3, 5].
        (1, 2, 4, 5, 7, 8, 10, 11),
        ("firm_financial_state",),
    ),
    (
        "consumption_demand",
        "monthly",
        "routine",
        (3, 6, 9, 12),
        ("firm_financial_state",),
    ),
    (
        "gdp_national_accounts",
        "quarterly",
        "high_attention",
        (3, 6, 9, 12),
        ("market_environment",),
    ),
    (
        "market_liquidity",
        "monthly",
        "routine",
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
        ("market_environment",),
    ),
)


_DEFAULT_INFORMATION_RELEASE_CALENDAR_ID: str = (
    "calendar:reference_monthly_synthetic"
)
_DEFAULT_INFORMATION_RELEASE_CALENDAR_LABEL: str = (
    "Reference monthly synthetic information-release calendar"
)


def _scheduled_release_id_for(
    calendar_id: str,
    indicator_family_label: str,
    period_index_1based: int,
) -> str:
    return (
        f"scheduled_release:{calendar_id}:"
        f"{indicator_family_label}:period_{period_index_1based:02d}"
    )


def _information_arrival_id_for(
    scheduled_release_id: str, as_of_date: str
) -> str:
    return f"arrival:{scheduled_release_id}:{as_of_date}"


def _scheduled_month_label_for(period_index_1based: int) -> str:
    return f"period_{period_index_1based:02d}"


def _ensure_default_monthly_release_calendar(
    kernel: Any,
    *,
    iso_dates: tuple[str, ...],
    calendar_id: str = _DEFAULT_INFORMATION_RELEASE_CALENDAR_ID,
) -> tuple[str, dict[int, tuple[ScheduledIndicatorRelease, ...]]]:
    """Idempotently register the v1.19.3 default monthly release
    calendar + scheduled releases on the kernel's
    ``information_releases`` book. Returns
    ``(calendar_id, releases_by_month_index_0based)`` where the
    second element maps the 0-based period index for
    ``iso_dates`` to the tuple of scheduled-release records due
    in that month.

    The number of monthly periods is whatever the caller passed
    in. The default fixture pins 12 months; if the caller passes
    fewer, only the matching prefix of scheduled releases is
    registered. If the caller passes *more* than 12 months, the
    extra months simply have no scheduled releases (the caller
    is responsible for any extension).

    Setup ledger events use ``iso_dates[0]`` as their
    ``simulation_date`` so two kernels with the same fixture
    produce byte-identical ledger slices.
    """
    setup_simulation_date = iso_dates[0] if iso_dates else None
    try:
        kernel.information_releases.add_calendar(
            InformationReleaseCalendar(
                calendar_id=calendar_id,
                calendar_label=(
                    _DEFAULT_INFORMATION_RELEASE_CALENDAR_LABEL
                ),
                jurisdiction_scope_label="jurisdiction_neutral",
                release_cadence_labels=(
                    "monthly",
                    "quarterly",
                    "meeting_based",
                ),
                indicator_family_labels=tuple(
                    spec[0] for spec in _DEFAULT_MONTHLY_RELEASE_SPECS
                ),
                status="active",
                visibility="internal_only",
            ),
            simulation_date=setup_simulation_date,
        )
    except DuplicateInformationReleaseCalendarError:
        kernel.information_releases.get_calendar(calendar_id)

    releases_by_period_idx_0based: dict[
        int, list[ScheduledIndicatorRelease]
    ] = {idx: [] for idx in range(len(iso_dates))}

    for (
        family_label,
        cadence_label,
        importance_label,
        scheduled_months_1based,
        attention_surface_labels,
    ) in _DEFAULT_MONTHLY_RELEASE_SPECS:
        for month_1based in scheduled_months_1based:
            period_idx_0based = month_1based - 1
            if period_idx_0based >= len(iso_dates):
                continue
            scheduled_id = _scheduled_release_id_for(
                calendar_id, family_label, month_1based
            )
            try:
                release = kernel.information_releases.add_scheduled_release(
                    ScheduledIndicatorRelease(
                        scheduled_release_id=scheduled_id,
                        calendar_id=calendar_id,
                        indicator_family_label=family_label,
                        release_cadence_label=cadence_label,
                        release_importance_label=importance_label,
                        scheduled_month_label=(
                            _scheduled_month_label_for(month_1based)
                        ),
                        scheduled_period_index=period_idx_0based,
                        expected_attention_surface_labels=(
                            attention_surface_labels
                        ),
                        status="active",
                        visibility="internal_only",
                    ),
                    simulation_date=setup_simulation_date,
                )
            except DuplicateScheduledIndicatorReleaseError:
                release = (
                    kernel.information_releases.get_scheduled_release(
                        scheduled_id
                    )
                )
            releases_by_period_idx_0based[period_idx_0based].append(release)

    return (
        calendar_id,
        {
            idx: tuple(records)
            for idx, records in releases_by_period_idx_0based.items()
        },
    )


def _emit_period_information_arrivals(
    kernel: Any,
    *,
    calendar_id: str,
    iso_date: str,
    scheduled_releases: tuple[ScheduledIndicatorRelease, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Emit one :class:`InformationArrivalRecord` per scheduled
    release in the given month. Returns
    ``(scheduled_release_ids, information_arrival_ids)`` —
    parallel tuples in the same order.
    """
    scheduled_ids: list[str] = []
    arrival_ids: list[str] = []
    for release in scheduled_releases:
        arrival_id = _information_arrival_id_for(
            release.scheduled_release_id, iso_date
        )
        try:
            kernel.information_releases.add_arrival(
                InformationArrivalRecord(
                    information_arrival_id=arrival_id,
                    calendar_id=calendar_id,
                    scheduled_release_id=release.scheduled_release_id,
                    as_of_date=iso_date,
                    indicator_family_label=(
                        release.indicator_family_label
                    ),
                    release_cadence_label=release.release_cadence_label,
                    release_importance_label=(
                        release.release_importance_label
                    ),
                    arrival_status_label="arrived",
                    affected_context_surface_labels=(
                        release.expected_attention_surface_labels
                    ),
                    expected_attention_surface_labels=(
                        release.expected_attention_surface_labels
                    ),
                    status="active",
                    visibility="internal_only",
                )
            )
        except DuplicateInformationArrivalError:
            pass
        scheduled_ids.append(release.scheduled_release_id)
        arrival_ids.append(arrival_id)
    return tuple(scheduled_ids), tuple(arrival_ids)


# ---------------------------------------------------------------------------
# v1.20.3 — Scenario monthly reference universe setup helpers
#
# Setup-time, idempotent registration of the v1.20.1 generic
# 11-sector reference universe + the v1.18.1 credit-tightening
# scenario driver template + the v1.20.2 default scenario
# schedule. The helpers are read-only against pre-existing books
# and only write to the four v1.20.x books named below — never
# to PriceBook, ContractBook, or any other source-of-truth book.
#
# Each helper returns the deterministic ids the run profile cites
# in period summaries.
# ---------------------------------------------------------------------------


def _ensure_v1_20_3_reference_universe(
    kernel: Any,
    *,
    simulation_date: Any = None,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Idempotently register the v1.20.1 generic 11-sector
    reference universe on the kernel's ``reference_universe``
    book. Returns ``(universe_profile_id, sector_ids,
    firm_profile_ids)`` in deterministic order. Re-running with
    the same kernel is a no-op.

    Setup overhead: 1 ``ReferenceUniverseProfile`` + 11
    :class:`GenericSectorReference` + 11
    :class:`SyntheticSectorFirmProfile` records on first call;
    zero records on subsequent calls.
    """
    fixture = build_generic_11_sector_reference_universe()
    try:
        kernel.reference_universe.add_universe_profile(
            fixture.universe_profile,
            simulation_date=simulation_date,
        )
    except DuplicateReferenceUniverseProfileError:
        pass
    sector_ids: list[str] = []
    for sector in fixture.sector_references:
        try:
            kernel.reference_universe.add_sector_reference(
                sector, simulation_date=simulation_date
            )
        except DuplicateGenericSectorReferenceError:
            pass
        sector_ids.append(sector.sector_id)
    firm_profile_ids: list[str] = []
    for firm in fixture.firm_profiles:
        try:
            kernel.reference_universe.add_firm_profile(
                firm, simulation_date=simulation_date
            )
        except DuplicateSyntheticSectorFirmProfileError:
            pass
        firm_profile_ids.append(firm.firm_profile_id)
    return (
        fixture.universe_profile.reference_universe_id,
        tuple(sector_ids),
        tuple(firm_profile_ids),
    )


def _ensure_v1_20_3_scenario_template(
    kernel: Any,
    *,
    simulation_date: Any = None,
) -> str:
    """Idempotently register the synthetic
    ``credit_tightening`` scenario driver template on the
    kernel's ``scenario_drivers`` book. Returns the template id.
    Setup overhead: 1 record on first call; zero on subsequent
    calls. The template carries the v1.18.0 audit shape
    (``reasoning_mode`` / ``reasoning_policy_id`` /
    ``reasoning_slot``)."""
    template = ScenarioDriverTemplate(
        scenario_driver_template_id=_DEFAULT_SCENARIO_DRIVER_TEMPLATE_ID,
        scenario_family_label="credit_tightening_driver",
        driver_group_label="credit_liquidity",
        driver_label=(
            "Reference credit-tightening scenario driver "
            "(synthetic)"
        ),
        event_date_policy_label="quarter_start",
        severity_label="medium",
        affected_actor_scope_label="market_wide",
        expected_annotation_type_label="financing_constraint",
        affected_context_surface_labels=(
            "market_environment",
            "financing_review_surface",
        ),
        affected_evidence_bucket_labels=(
            "market_environment_state",
            "financing_review_surface",
        ),
    )
    try:
        kernel.scenario_drivers.add_template(
            template, simulation_date=simulation_date
        )
    except DuplicateScenarioDriverTemplateError:
        pass
    return _DEFAULT_SCENARIO_DRIVER_TEMPLATE_ID


def _ensure_v1_20_3_scenario_schedule(
    kernel: Any,
    *,
    simulation_date: Any = None,
) -> tuple[str, str]:
    """Idempotently register the v1.20.2 default scenario
    schedule on the kernel's ``scenario_schedule`` book. Returns
    ``(scenario_schedule_id, scheduled_scenario_application_id)``.
    Setup overhead: 2 records on first call; zero on subsequent
    calls."""
    schedule, scheduled_app = build_default_scenario_monthly_schedule()
    try:
        kernel.scenario_schedule.add_schedule(
            schedule, simulation_date=simulation_date
        )
    except DuplicateScenarioScheduleError:
        pass
    try:
        kernel.scenario_schedule.add_scheduled_application(
            scheduled_app, simulation_date=simulation_date
        )
    except DuplicateScheduledScenarioApplicationError:
        pass
    return (
        schedule.scenario_schedule_id,
        scheduled_app.scheduled_scenario_application_id,
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


# v1.14.5 — deterministic per-firm label cycles for the corporate
# financing chain. The rotations are small, generic, and chosen so
# that the per-period markdown report carries non-trivial histograms
# (mixed purposes, mixed review types, mixed market-access postures
# even though the funding-option set is uniform). Every label is
# drawn from the v1.14 closed sets.
_CORPORATE_FINANCING_PURPOSE_BY_FIRM_INDEX: tuple[str, ...] = (
    "working_capital",
    "refinancing",
    "growth_capex",
)

_CORPORATE_FINANCING_REVIEW_TYPE_BY_FIRM_INDEX: tuple[str, ...] = (
    "liquidity_review",
    "refinancing_review",
    "leverage_review",
)

_CORPORATE_FINANCING_MARKET_ACCESS_BY_FIRM_INDEX: tuple[str, ...] = (
    "open",
    "selective",
    "open",
)


# v1.15.5 / v1.16.2 — securities-market-intent setup defaults.
# The default fixture registers one generic exchange-shaped venue
# and one equity-like security per firm. v1.16.2 replaced the
# v1.15.5 four-cycle ``(period_idx + investor_idx + firm_idx) %
# 4`` rotation with the v1.16.1
# ``classify_market_intent_direction(...)`` pure function — see
# §116 in ``docs/world_model.md``. The classifier reads cited
# evidence (investor intent direction, valuation confidence,
# firm market-access pressure, market-environment overall access
# label, attention focus labels) and returns one of
# ``SAFE_INTENT_LABELS ∪ {"unknown"}`` along with an audit
# (``rule_id``, ``status``, ``confidence``,
# ``unresolved_or_missing_count``) carried in the record's
# ``metadata``. The forbidden trade-instruction verbs (``buy`` /
# ``sell`` / ``order`` / ``target_weight`` / ``overweight`` /
# ``underweight`` / ``execution``) are disjoint from
# ``INTENT_DIRECTION_LABELS`` and rejected at construction.
_DEFAULT_PRIMARY_MARKET_VENUE_ID: str = "venue:reference_exchange_a"

# v1.16.2 classifier-confidence → intensity mapping. The
# classifier returns a synthetic ``[0.0, 1.0]`` confidence —
# ``0.0`` for evidence-deficient outcomes, ``0.3`` for the
# default fallback, and ``0.5 + 0.05 × evidence_count`` clamped
# to ``[0.5, 0.75]`` when a specific rule fires. The mapping
# below is deterministic and lives in
# ``world.market_intents.INTENSITY_LABELS``.
def _intensity_label_for_classifier_confidence(
    classifier_status: str, classifier_confidence: float
) -> str:
    if classifier_status == "evidence_deficient":
        return "unknown"
    if classifier_status == "default_fallback":
        return "low"
    if classifier_confidence >= 0.7:
        return "elevated"
    if classifier_confidence >= 0.6:
        return "moderate"
    return "low"


def _listed_security_id_for(firm_id: str) -> str:
    """Default per-firm equity-like security id used by the
    v1.15.5 securities-market-intent setup phase."""
    return f"security:{firm_id}:equity:line_1"


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


# v1.12.8 — focus-label → prior-state-source-attribute map. The
# v1.12.8 memory selection's selected_refs are drawn from the
# prior attention state's source_*_ids tuples, gated by which
# focus_labels the prior state carried. Mapping is deterministic
# and additive; first-seen order preserved.
_MEMORY_FOCUS_TO_SOURCE_ATTR: tuple[tuple[str, str], ...] = (
    (FOCUS_LABEL_FIRM_STATE, "source_firm_state_ids"),
    (FOCUS_LABEL_MARKET_ENVIRONMENT, "source_market_environment_state_ids"),
    (FOCUS_LABEL_VALUATION, "source_valuation_ids"),
    (FOCUS_LABEL_DIALOGUE, "source_dialogue_ids"),
    (FOCUS_LABEL_ENGAGEMENT, "source_dialogue_ids"),
    (FOCUS_LABEL_ESCALATION, "source_escalation_candidate_ids"),
)


def _memory_selection_id_for(
    actor_kind: str, actor_id: str, as_of_date: str
) -> str:
    return f"selection:memory:{actor_kind}:{actor_id}:{as_of_date}"


def _build_memory_selection_if_any(
    kernel: Any,
    *,
    actor_kind: str,
    actor_id: str,
    as_of_date: str,
    phase_id: str | None,
) -> str | None:
    """v1.12.8 — build one memory ``SelectedObservationSet`` for
    the actor at period N, drawn from the actor's prior-period
    attention state's source_*_ids gated by its focus_labels.

    Returns the new selection's id when a prior state exists,
    or ``None`` otherwise (e.g., period 0 — no prior feedback).
    Idempotent on the deterministic memory-selection-id formula.
    """
    book = getattr(kernel, "attention_feedback", None)
    if book is None:
        return None
    prior_state = book.get_latest_for_actor(actor_id)
    if prior_state is None:
        return None
    if prior_state.as_of_date >= as_of_date:
        # Defensive: only feed forward from strictly-prior periods.
        return None

    # v1.12.9 — apply the attention budget. Build a
    # ``candidate_refs_by_focus`` mapping from the prior state's
    # source-id tuples gated by which focus labels point at each
    # source attribute, then call ``apply_attention_budget`` to
    # bound the result by ``per_dimension_budget`` per focus and
    # ``max_selected_refs`` total. Two periods with byte-identical
    # prior states produce byte-identical memory selections.
    candidate_refs_by_focus: dict[str, list[str]] = {}
    focus_set = set(prior_state.focus_labels)
    for focus_label, source_attr in _MEMORY_FOCUS_TO_SOURCE_ATTR:
        if focus_label not in focus_set:
            continue
        candidate_refs_by_focus.setdefault(focus_label, []).extend(
            list(getattr(prior_state, source_attr, ()))
        )

    bounded = apply_attention_budget(
        focus_labels=prior_state.focus_labels,
        focus_weights=prior_state.focus_weights,
        candidate_refs_by_focus=candidate_refs_by_focus,
        max_selected_refs=prior_state.max_selected_refs,
        per_dimension_budget=prior_state.per_dimension_budget,
    )
    selected_refs = list(bounded)

    if not selected_refs:
        # Focus labels carried no concrete source ids (e.g.,
        # only "memory" or "liquidity"); skip — no memory
        # selection adds value here.
        return None

    selection_id = _memory_selection_id_for(actor_kind, actor_id, as_of_date)
    try:
        kernel.attention.get_selection(selection_id)
        return selection_id
    except Exception:
        pass

    # Reuse the actor's existing attention profile if any (no
    # new profile is created for memory selections — the
    # attention profile is the actor's, the memory selection
    # just augments which refs the resolver sees).
    profile_ids = list(prior_state.base_profile_ids) or []
    if profile_ids:
        profile_id = profile_ids[0]
    else:
        # Fall back to a synthetic placeholder; the v1.8.5
        # SelectedObservationSet contract requires
        # attention_profile_id to be a non-empty string. The
        # v1.12.4 / v1.12.5 / v1.12.6 helpers do not look up
        # the profile — they only read selected_refs — so the
        # placeholder is a recordable label, not a behavior.
        profile_id = f"profile:memory:{actor_kind}:{actor_id}"

    # Memory selections need a menu_id — reuse the actor's
    # current-period menu so the lineage is explicit.
    menu_id = _menu_id_for(actor_kind, actor_id, as_of_date)

    selection = SelectedObservationSet(
        selection_id=selection_id,
        actor_id=actor_id,
        attention_profile_id=profile_id,
        menu_id=menu_id,
        selected_refs=tuple(selected_refs),
        selection_reason="attention_feedback_memory",
        as_of_date=as_of_date,
        phase_id=phase_id,
        status="completed",
        metadata={
            "v1_12_8_memory_selection": True,
            "previous_attention_state_id": prior_state.attention_state_id,
        },
    )
    kernel.attention.add_selection(selection)
    return selection_id


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
    profile: str = "quarterly_default",
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

    if not isinstance(profile, str) or not profile:
        raise ValueError("profile must be a non-empty string")
    if profile not in _SUPPORTED_RUN_PROFILE_LABELS:
        raise ValueError(
            f"profile must be one of "
            f"{sorted(_SUPPORTED_RUN_PROFILE_LABELS)!r}; got {profile!r}"
        )

    if period_dates is None:
        if profile in (
            "monthly_reference",
            "scenario_monthly_reference_universe",
        ):
            period_dates = _DEFAULT_MONTHLY_PERIOD_DATES
        else:
            period_dates = _DEFAULT_QUARTER_END_DATES

    # v1.20.3 — profile-conditional flag that gates the
    # engagement / strategic-response / valuation / investor-
    # intent layer. Skipped under
    # ``scenario_monthly_reference_universe`` so the per-period
    # record count stays bounded under the v1.20.0 budget. The
    # closed-loop chain (attention → investor market intent →
    # aggregated market interest → indicative market pressure →
    # capital structure review / financing path → next-period
    # attention) still runs.
    is_scenario_universe_profile: bool = (
        profile == "scenario_monthly_reference_universe"
    )
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
    # v1.20.3 — under ``scenario_monthly_reference_universe`` the
    # engagement / dialogue / escalation / strategic-response
    # / valuation / investor-intent layer is skipped to keep the
    # per-period record count under the v1.20.0 budget. Stewardship
    # themes feed only that layer, so we skip them here too. The
    # other profiles continue to register the default themes
    # (eight records on first call) so their pinned digests stay
    # byte-identical.
    if is_scenario_universe_profile:
        stewardship_theme_ids: tuple[str, ...] = ()
    else:
        stewardship_theme_ids = _ensure_stewardship_themes(
            kernel,
            investor_ids=investors,
            theme_types=theme_types,
            effective_from=iso_dates[0],
        )

    # ------------------------------------------------------------------
    # v1.15.5 — securities-market surface setup. Register one
    # generic exchange venue + one equity-like listed security per
    # firm, once for the run (idempotent). Bounded:
    # ``1 venue + F securities`` setup records on top of the v1.10.5
    # / v1.13.5 setup overhead. Storage / surface only — never an
    # order book, a quote stream, a match engine, or a fee schedule.
    # ------------------------------------------------------------------
    primary_market_venue_id = _DEFAULT_PRIMARY_MARKET_VENUE_ID
    try:
        kernel.security_market.add_venue(
            MarketVenueRecord(
                venue_id=primary_market_venue_id,
                venue_type_label="exchange",
                venue_role_label="listing_venue",
                status="active",
                visibility="public",
                supported_security_type_labels=("equity",),
                supported_intent_labels=tuple(sorted(SAFE_INTENT_LABELS)),
            )
        )
    except DuplicateMarketVenueError:
        pass

    listed_security_id_by_firm: dict[str, str] = {}
    for firm_id in firms:
        security_id = _listed_security_id_for(firm_id)
        try:
            kernel.security_market.add_security(
                ListedSecurityRecord(
                    security_id=security_id,
                    issuer_firm_id=firm_id,
                    security_type_label="equity",
                    listing_status_label="listed",
                    primary_market_venue_id=primary_market_venue_id,
                    currency_label="synthetic_currency_a",
                    issue_profile_label="seasoned",
                    liquidity_profile_label="moderate",
                    investor_access_label="broad",
                    status="active",
                    visibility="public",
                )
            )
        except DuplicateListedSecurityError:
            pass
        listed_security_id_by_firm[firm_id] = security_id

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
    # v1.19.3 — monthly_reference profile information-release setup.
    # Quarterly_default skips this block entirely so the v1.18.last
    # canonical view is byte-identical. For monthly_reference, we
    # idempotently register the default synthetic calendar +
    # scheduled releases on the kernel's
    # ``information_releases`` book; the per-period sweep below
    # then emits one ``InformationArrivalRecord`` per scheduled
    # release for the matching month. Bounded budget: 3-5
    # arrivals per month, total in [36, 60] for 12 months.
    # ------------------------------------------------------------------
    monthly_release_calendar_id: str | None = None
    monthly_releases_by_period_idx: dict[
        int, tuple[ScheduledIndicatorRelease, ...]
    ] = {}
    if profile in ("monthly_reference", "scenario_monthly_reference_universe"):
        (
            monthly_release_calendar_id,
            monthly_releases_by_period_idx,
        ) = _ensure_default_monthly_release_calendar(
            kernel, iso_dates=iso_dates
        )

    # v1.20.3 — opt-in scenario-monthly-reference-universe setup.
    # Registers the v1.20.1 11-sector / 11-firm reference
    # universe + the credit-tightening scenario template +
    # the v1.20.2 default scenario schedule. The block is a
    # **no-op** for any profile other than
    # ``scenario_monthly_reference_universe`` so the
    # ``quarterly_default`` and ``monthly_reference`` digests
    # remain byte-identical.
    run_reference_universe_id: str | None = None
    run_sector_ids: tuple[str, ...] = ()
    run_firm_profile_ids: tuple[str, ...] = ()
    run_scenario_schedule_id: str | None = None
    run_scheduled_scenario_application_id: str | None = None
    if is_scenario_universe_profile:
        setup_simulation_date = iso_dates[0] if iso_dates else None
        (
            run_reference_universe_id,
            run_sector_ids,
            run_firm_profile_ids,
        ) = _ensure_v1_20_3_reference_universe(
            kernel, simulation_date=setup_simulation_date
        )
        _ensure_v1_20_3_scenario_template(
            kernel, simulation_date=setup_simulation_date
        )
        (
            run_scenario_schedule_id,
            run_scheduled_scenario_application_id,
        ) = _ensure_v1_20_3_scenario_schedule(
            kernel, simulation_date=setup_simulation_date
        )

    # ------------------------------------------------------------------
    # Per-period sweep
    # ------------------------------------------------------------------
    period_summaries: list[LivingReferencePeriodSummary] = []

    # v1.16.3 — closes the v1.12 attention-feedback loop with the
    # v1.15 securities-market-pressure / financing-path loop. The
    # per-period attention-feedback phase reads the *previous*
    # period's ``IndicativeMarketPressureRecord`` ids and
    # ``CorporateFinancingPathRecord`` ids; the deterministic
    # mappings in :func:`world.attention_feedback._classify_market_pressure_focus`
    # and :func:`world.attention_feedback._classify_financing_path_focus`
    # add fresh focus labels (``risk`` / ``financing`` /
    # ``dilution`` / ``market_interest`` / ``information_gap``)
    # that influence next-period evidence selection and therefore
    # next-period market-intent classification — without ever
    # creating an order, trade, price update, financing approval,
    # or recommendation.
    prev_period_indicative_market_pressure_ids: tuple[str, ...] = ()
    prev_period_corporate_financing_path_ids: tuple[str, ...] = ()

    for period_idx, iso_date in enumerate(iso_dates):
        period_id = f"period:{rid}:{iso_date}"
        period_start_idx = len(kernel.ledger.records)

        # v1.19.3 — emit information arrivals first so any
        # downstream per-period helper that wants to cite them
        # (future milestone; v1.19.3 keeps the citation surface
        # passive) sees them in the kernel before its own
        # records land. For quarterly_default profile both
        # tuples stay empty.
        period_scheduled_release_ids: tuple[str, ...] = ()
        period_information_arrival_ids: tuple[str, ...] = ()
        if (
            profile in (
                "monthly_reference",
                "scenario_monthly_reference_universe",
            )
            and monthly_release_calendar_id is not None
        ):
            scheduled_for_period = monthly_releases_by_period_idx.get(
                period_idx, ()
            )
            (
                period_scheduled_release_ids,
                period_information_arrival_ids,
            ) = _emit_period_information_arrivals(
                kernel,
                calendar_id=monthly_release_calendar_id,
                iso_date=iso_date,
                scheduled_releases=scheduled_for_period,
            )

        # v1.20.3 — opt-in scheduled scenario application. The
        # ``scenario_monthly_reference_universe`` profile fires
        # the v1.20.2 default scenario (``credit_tightening`` at
        # ``period_index == 3`` / ``month_04``) **once per run**.
        # Any other period — and any other profile — emits zero
        # scenario application records and zero context shifts.
        # The shift count is bounded by ``apply_scenario_driver``:
        # 1 application + 2 context shifts (one per affected
        # context surface for the credit-tightening family). This
        # is well under the
        # ``O(scheduled_app_count × F)`` budget.
        period_scenario_application_ids: tuple[str, ...] = ()
        period_scenario_context_shift_ids: tuple[str, ...] = ()
        if (
            is_scenario_universe_profile
            and period_idx == _DEFAULT_SCENARIO_SCHEDULED_PERIOD_INDEX
        ):
            scenario_application = apply_scenario_driver(
                kernel,
                scenario_driver_template_id=(
                    _DEFAULT_SCENARIO_DRIVER_TEMPLATE_ID
                ),
                as_of_date=iso_date,
                source_context_record_ids=period_information_arrival_ids,
                metadata={
                    "scenario_schedule_id": run_scenario_schedule_id,
                    "scheduled_scenario_application_id": (
                        run_scheduled_scenario_application_id
                    ),
                    "reference_universe_id": run_reference_universe_id,
                    "scheduled_month_label": (
                        _DEFAULT_SCENARIO_SCHEDULED_MONTH_LABEL
                    ),
                    "scheduled_period_index": (
                        _DEFAULT_SCENARIO_SCHEDULED_PERIOD_INDEX
                    ),
                    "no_actor_decision": True,
                    "no_price_formation": True,
                    "no_financing_execution": True,
                    "synthetic_only": True,
                },
            )
            period_scenario_application_ids = (
                scenario_application.scenario_application_id,
            )
            period_scenario_context_shift_ids = (
                scenario_application.emitted_context_shift_ids
            )

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
        # v1.12.8 — memory selection phase.
        # For each investor and bank, look up the actor's prior
        # attention state (created at the end of period N-1). If
        # one exists, build a *memory* SelectedObservationSet
        # whose selected_refs include the prior-period evidence
        # the actor's focus_labels point at. The memory selection
        # is passed alongside the regular per-period selection to
        # the v1.12.4 / v1.12.5 / v1.12.6 helpers, so the resolved
        # `ActorContextFrame` for period N is *wider* than it
        # would be without feedback.
        #
        # No memory selection is built in period 0 (no prior
        # state yet), so the v1.12.8 effect on resolved evidence
        # only fires from period 1 onwards. This is the headline
        # cross-period feedback loop the v1.12.8 task spec
        # requires.
        # ------------------------------------------------------------------
        investor_memory_selection_by_investor: dict[str, str] = {}
        bank_memory_selection_by_bank: dict[str, str] = {}
        for actor_kind, actor_ids, target_dict in (
            ("investor", investors, investor_memory_selection_by_investor),
            ("bank", banks, bank_memory_selection_by_bank),
        ):
            for actor_id in actor_ids:
                memory_id = _build_memory_selection_if_any(
                    kernel,
                    actor_kind=actor_kind,
                    actor_id=actor_id,
                    as_of_date=iso_date,
                    phase_id=phase_id,
                )
                if memory_id is not None:
                    target_dict[actor_id] = memory_id
        # Order-preserving lists for the period summary.
        investor_memory_selection_ids = [
            investor_memory_selection_by_investor[a]
            for a in investors
            if a in investor_memory_selection_by_investor
        ]
        bank_memory_selection_ids = [
            bank_memory_selection_by_bank[a]
            for a in banks
            if a in bank_memory_selection_by_bank
        ]

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
        # v1.12.7 — orchestrator wires the v1.12.5
        # attention-conditioned valuation helper. Each (investor,
        # firm) pair routes evidence through the v1.12.3
        # `EvidenceResolver` substrate by calling
        # ``run_attention_conditioned_valuation_refresh_lite``. The
        # investor's `SelectedObservationSet` is the attention
        # surface; transitional explicit-id kwargs cover firm
        # states, market environment states, market readouts,
        # corporate signals, and pressure signals which the
        # v1.8.x menu builder does not yet surface through the
        # menu / selection pipeline. The v1.9.5 anti-claim metadata
        # (`no_price_movement` / `no_investment_advice` /
        # `synthetic_only`) is preserved bit-for-bit on every
        # produced record.
        # ------------------------------------------------------------------
        valuation_ids: list[str] = []
        valuation_mechanism_run_ids: list[str] = []
        baselines = dict(firm_baseline_values or {})

        # v1.20.3 — skipped under
        # ``scenario_monthly_reference_universe`` to keep the
        # per-period record count bounded under the v1.20.0
        # budget. Downstream phases that read ``valuation_ids``
        # gracefully accept an empty list.
        valuation_iter = (
            zip(investors, investor_selection_ids)
            if not is_scenario_universe_profile
            else ()
        )
        for investor_id, investor_selection_id in valuation_iter:
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
                firm_state_for_pair = firm_state_id_by_firm.get(firm_id)
                inv_memory = investor_memory_selection_by_investor.get(
                    investor_id
                )
                valuation_selection_ids = (
                    (investor_selection_id, inv_memory)
                    if inv_memory
                    else (investor_selection_id,)
                )
                valuation_result: ValuationRefreshLiteResult = (
                    run_attention_conditioned_valuation_refresh_lite(
                        kernel,
                        firm_id=firm_id,
                        valuer_id=investor_id,
                        as_of_date=iso_date,
                        selected_observation_set_ids=(
                            valuation_selection_ids
                        ),
                        explicit_pressure_signal_ids=(
                            pressure_signal_by_firm[firm_id],
                        ),
                        explicit_corporate_signal_ids=(
                            corp_signal_by_firm[firm_id],
                        ),
                        explicit_firm_state_ids=(
                            (firm_state_for_pair,)
                            if firm_state_for_pair
                            else ()
                        ),
                        explicit_market_readout_ids=tuple(
                            capital_market_readout_ids
                        ),
                        explicit_market_environment_state_ids=tuple(
                            market_environment_state_ids
                        ),
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
        # v1.12.7 — orchestrator wires the v1.12.6
        # attention-conditioned bank credit review helper. Each
        # (bank, firm) pair routes evidence through the v1.12.3
        # `EvidenceResolver` substrate by calling
        # ``run_attention_conditioned_bank_credit_review_lite``.
        # The bank's `SelectedObservationSet` is the attention
        # surface; transitional explicit-id kwargs cover firm
        # states, market environment states, market readouts,
        # valuations, and corporate / pressure signals. Every
        # v1.9.7 boundary anti-claim is preserved bit-for-bit
        # on every produced ``bank_credit_review_note`` signal:
        # `no_lending_decision` / `no_covenant_enforcement` /
        # `no_contract_mutation` / `no_constraint_mutation` /
        # `no_default_declaration` / `no_internal_rating` /
        # `no_probability_of_default` / `synthetic_only`.
        bank_credit_review_signal_ids: list[str] = []
        bank_credit_review_mechanism_run_ids: list[str] = []

        # v1.13.5 — emit one synthetic InterbankLiquidityStateRecord
        # per bank per period. Storage only; the labels are fixed
        # (``normal`` / ``low`` / ``available`` / ``low``) and a
        # synthetic ``confidence=0.5`` so the per-period content is
        # deterministic and bit-identical across runs. The state's
        # provenance cites this period's market-environment state
        # ids; it is **not** computed from any model — it is a
        # placeholder reference state that lets v1.13.5 wire the
        # cross-link slot. The bank credit review helper records
        # the ids on the produced note's audit payload + metadata
        # without changing the v1.12.6 watch-label classifier.
        interbank_liquidity_state_id_by_bank: dict[str, str] = {}
        for bank_id in banks:
            ils_id = (
                f"interbank_liquidity_state:{bank_id}:{iso_date}"
            )
            try:
                kernel.interbank_liquidity.add_state(
                    InterbankLiquidityStateRecord(
                        liquidity_state_id=ils_id,
                        institution_id=bank_id,
                        as_of_date=iso_date,
                        liquidity_regime="normal",
                        settlement_pressure="low",
                        reserve_access_label="available",
                        funding_stress_label="low",
                        status="active",
                        visibility="internal_only",
                        confidence=0.5,
                        source_market_environment_state_ids=tuple(
                            market_environment_state_ids
                        ),
                    )
                )
            except DuplicateInterbankLiquidityStateError:
                pass
            interbank_liquidity_state_id_by_bank[bank_id] = ils_id

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
                firm_state_for_pair = firm_state_id_by_firm.get(firm_id)
                bank_memory = bank_memory_selection_by_bank.get(bank_id)
                review_selection_ids = (
                    (bank_selection_id, bank_memory)
                    if bank_memory
                    else (bank_selection_id,)
                )
                review_result: BankCreditReviewLiteResult = (
                    run_attention_conditioned_bank_credit_review_lite(
                        kernel,
                        bank_id=bank_id,
                        firm_id=firm_id,
                        as_of_date=iso_date,
                        selected_observation_set_ids=(
                            review_selection_ids
                        ),
                        explicit_pressure_signal_ids=(
                            pressure_signal_by_firm[firm_id],
                        ),
                        explicit_corporate_signal_ids=(
                            corp_signal_by_firm[firm_id],
                        ),
                        explicit_valuation_ids=firm_valuation_ids,
                        explicit_firm_state_ids=(
                            (firm_state_for_pair,)
                            if firm_state_for_pair
                            else ()
                        ),
                        explicit_market_readout_ids=tuple(
                            capital_market_readout_ids
                        ),
                        explicit_market_environment_state_ids=tuple(
                            market_environment_state_ids
                        ),
                        explicit_interbank_liquidity_state_ids=(
                            interbank_liquidity_state_id_by_bank[bank_id],
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

        # v1.20.3 — engagement layer (dialogue / escalation /
        # investor-intent / strategic-response) is skipped under
        # ``scenario_monthly_reference_universe`` to keep the
        # per-period record count bounded. Downstream phases that
        # filter by ``valuation_ids`` / ``investor_intent_ids`` /
        # ``dialogue_ids`` / ``investor_escalation_candidate_ids``
        # gracefully accept empty lists — they were already designed
        # to drop unresolved citations.
        engagement_investor_iter = (
            investors if not is_scenario_universe_profile else ()
        )
        for investor_id in engagement_investor_iter:
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
        escalation_investor_iter = (
            investors if not is_scenario_universe_profile else ()
        )
        for investor_id in escalation_investor_iter:
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
        # v1.12.4 — attention-conditioned investor intent phase.
        # For each (investor, firm) pair, the orchestrator now
        # routes evidence through the v1.12.3
        # :class:`world.evidence.EvidenceResolver` substrate by
        # calling ``run_attention_conditioned_investor_intent_signal``.
        # The investor's ``SelectedObservationSet`` is the
        # *attention surface* — its ``selected_refs`` (signals,
        # variable observations, exposures) drive the resolver's
        # signal / variable-observation / exposure buckets.
        #
        # **Transitional explicits.** The v1.8.x menu builder does
        # not yet surface firm states, market environment states,
        # market readouts, valuations, dialogues, escalation
        # candidates, or stewardship themes through the menu /
        # selection pipeline. v1.12.4 keeps these as explicit-id
        # kwargs so the integration is honest rather than silent.
        # A future milestone may extend the menu builder to make
        # them selectable and drop the explicit kwargs; until
        # then, the explicit-kwarg path is documented and pinned
        # by tests so a contributor cannot accidentally turn
        # silent global scanning back on.
        #
        # The helper itself never scans the kernel's other books;
        # its only inputs are the resolver's frame plus the
        # caller-supplied ids.
        # ------------------------------------------------------------------
        investor_intent_ids: list[str] = []
        investor_selection_id_by_investor = dict(
            zip(investors, investor_selection_ids)
        )
        intent_investor_iter = (
            investors if not is_scenario_universe_profile else ()
        )
        for investor_id in intent_investor_iter:
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
                inv_memory = investor_memory_selection_by_investor.get(
                    investor_id
                )
                intent_selection_ids: tuple[str, ...] = ()
                if inv_selection:
                    intent_selection_ids = (inv_selection,)
                if inv_memory:
                    intent_selection_ids = intent_selection_ids + (
                        inv_memory,
                    )
                intent_result = (
                    run_attention_conditioned_investor_intent_signal(
                        kernel,
                        investor_id=investor_id,
                        target_company_id=firm_id,
                        as_of_date=iso_date,
                        selected_observation_set_ids=(
                            intent_selection_ids
                        ),
                        explicit_market_readout_ids=tuple(
                            capital_market_readout_ids
                        ),
                        explicit_market_condition_ids=tuple(
                            market_condition_ids
                        ),
                        explicit_market_environment_state_ids=tuple(
                            market_environment_state_ids
                        ),
                        explicit_firm_state_ids=(
                            (firm_state,) if firm_state else ()
                        ),
                        explicit_valuation_ids=pair_valuation,
                        explicit_dialogue_ids=(
                            (pair_dialogue,) if pair_dialogue else ()
                        ),
                        explicit_escalation_candidate_ids=(
                            (pair_escalation,)
                        ),
                        explicit_stewardship_theme_ids=inv_themes,
                    )
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
        strategic_firm_iter = (
            firms if not is_scenario_universe_profile else ()
        )
        for firm_id in strategic_firm_iter:
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

        # ------------------------------------------------------------------
        # v1.12.8 — attention feedback phase.
        # Build one ActorAttentionStateRecord +
        # AttentionFeedbackRecord per actor (every investor +
        # every bank), conditioned on the period's outcomes:
        # the actor's intents (investor) or credit review
        # signals (bank), the period's market environment, and
        # the relevant firm states / valuations / dialogues /
        # escalation candidates. Each record chains via
        # ``previous_attention_state_id`` to the actor's prior
        # attention state (if any). Every actor's series is
        # therefore a deterministic sequence of attention
        # states across periods. The records are read at the
        # *next* period's memory-selection phase to widen the
        # actor's selected_refs — closing the cross-period
        # feedback loop.
        # ------------------------------------------------------------------
        investor_attention_state_ids: list[str] = []
        investor_attention_feedback_ids: list[str] = []
        for investor_id in investors:
            inv_intents = tuple(
                iid
                for iid in investor_intent_ids
                if f":{investor_id}:" in iid
            )
            inv_valuations = tuple(
                vid
                for vid in valuation_ids
                if f":{investor_id}:" in vid
            )
            inv_dialogues = tuple(
                did
                for did in dialogue_ids
                if f":{investor_id}:" in did
            )
            inv_escalations = tuple(
                eid
                for eid in investor_escalation_candidate_ids
                if f":{investor_id}:" in eid
            )
            fb = build_attention_feedback(
                kernel,
                actor_id=investor_id,
                actor_type="investor",
                as_of_date=iso_date,
                investor_intent_ids=inv_intents,
                market_environment_state_ids=tuple(
                    market_environment_state_ids
                ),
                firm_state_ids=tuple(firm_financial_state_ids),
                valuation_ids=inv_valuations,
                dialogue_ids=inv_dialogues,
                escalation_candidate_ids=inv_escalations,
                # v1.16.3 — prior-period pressure / financing path
                # citations close the v1.12 ↔ v1.15 attention loop.
                indicative_market_pressure_ids=(
                    prev_period_indicative_market_pressure_ids
                ),
                corporate_financing_path_ids=(
                    prev_period_corporate_financing_path_ids
                ),
            )
            investor_attention_state_ids.append(fb.attention_state_id)
            investor_attention_feedback_ids.append(fb.feedback_id)

        bank_attention_state_ids: list[str] = []
        bank_attention_feedback_ids: list[str] = []
        for bank_id in banks:
            bank_credit_subset = tuple(
                sid
                for sid in bank_credit_review_signal_ids
                if f":{bank_id}:" in sid
            )
            fb = build_attention_feedback(
                kernel,
                actor_id=bank_id,
                actor_type="bank",
                as_of_date=iso_date,
                credit_review_signal_ids=bank_credit_subset,
                market_environment_state_ids=tuple(
                    market_environment_state_ids
                ),
                firm_state_ids=tuple(firm_financial_state_ids),
                # v1.16.3 — banks also widen attention on prior-
                # period market pressure / financing path so the
                # next-period bank credit review observes the same
                # pressure-driven focus shifts as investors.
                indicative_market_pressure_ids=(
                    prev_period_indicative_market_pressure_ids
                ),
                corporate_financing_path_ids=(
                    prev_period_corporate_financing_path_ids
                ),
            )
            bank_attention_state_ids.append(fb.attention_state_id)
            bank_attention_feedback_ids.append(fb.feedback_id)

        # Shared per-period evidence-id tuples used by both the
        # v1.15.5 securities market intent chain and the v1.14.5
        # corporate financing chain. Defined once at the top of
        # the chain region so the v1.15.5 phase can run **before**
        # the v1.14.5 phase (v1.15.6 reorder — see §112 in
        # ``docs/world_model.md``).
        mes_ids_period = tuple(market_environment_state_ids)
        ibl_ids_period = tuple(interbank_liquidity_state_id_by_bank.values())

        # ------------------------------------------------------------------
        # v1.15.5 / v1.16.2 — securities market intent chain phase.
        #
        # Per investor × listed security: emit one
        # ``InvestorMarketIntentRecord`` (v1.15.2). Per listed
        # security: build one ``AggregatedMarketInterestRecord``
        # (v1.15.3) and one ``IndicativeMarketPressureRecord``
        # (v1.15.4) via their deterministic helpers. Bounded by
        # ``P × I × F + 2 × P × F``. No `P × I × F × venue` or
        # `P × I × F × option_count` dense loop.
        #
        # v1.16.2 replaces the v1.15.5 ``(period_idx + inv_idx +
        # firm_idx) % 4`` rotation with the v1.16.1 pure-function
        # ``classify_market_intent_direction(...)`` classifier.
        # The chosen ``intent_direction_label`` is now derived
        # from cited evidence: the investor's intent direction,
        # valuation confidence, firm market-access pressure, the
        # period's market-environment overall access label, and
        # the investor's actor-attention focus labels — all read
        # from records already created earlier in the same
        # period. No global scan; no kernel mutation outside the
        # books listed below; no new record types; per-period
        # record count unchanged.
        #
        # Storage / aggregation only. There is **no order
        # submission, no buy / sell labels, no order book, no
        # matching, no execution, no clearing, no settlement, no
        # quote dissemination, no bid / ask, no price update, no
        # PriceBook mutation, no target price, no expected return,
        # no recommendation, no portfolio allocation, no real
        # exchange mechanics, no real data ingestion, no Japan
        # calibration**.
        #
        # The synthesis uses safe-only labels — the forbidden
        # trading verbs (``buy`` / ``sell`` / ``order`` /
        # ``target_weight`` / ``overweight`` / ``underweight`` /
        # ``execution``) are disjoint from
        # ``INTENT_DIRECTION_LABELS`` and rejected at
        # construction.
        # ------------------------------------------------------------------
        investor_market_intent_ids: list[str] = []
        market_intent_ids_by_security: dict[str, list[str]] = {
            sid: [] for sid in listed_security_id_by_firm.values()
        }

        # v1.16.2 — resolve the period's market-environment
        # overall access label once per period from the first
        # cited MES id (typically the only one in the default
        # fixture). Permissive: the classifier only checks small
        # fixed-set membership.
        period_market_access_label: str = "unknown"
        if mes_ids_period:
            mes_record = kernel.market_environments.get_state(
                mes_ids_period[0]
            )
            period_market_access_label = (
                mes_record.overall_market_access_label
            )

        for inv_idx, investor_id in enumerate(investors):
            # v1.16.2 — resolve attention focus labels for this
            # investor in this period. The id format is the
            # default ``attention_state:{actor_id}:{as_of_date}``
            # built by the v1.12.8 helper. If the actor has no
            # attention state for this period, fall back to ``()``.
            attention_focus_labels: tuple[str, ...] = ()
            attention_state_id = f"attention_state:{investor_id}:{iso_date}"
            try:
                attention_state_record = (
                    kernel.attention_feedback.get_attention_state(
                        attention_state_id
                    )
                )
                attention_focus_labels = tuple(
                    attention_state_record.focus_labels
                )
            except Exception:
                attention_focus_labels = ()

            for firm_idx, firm_id in enumerate(firms):
                security_id = listed_security_id_by_firm.get(firm_id)
                if security_id is None:
                    continue

                # Filter upstream evidence to this (investor, firm)
                # pair. Existing v1.12.1 / v1.9.5 ids embed both
                # investor_id and firm_id substrings.
                pair_intent_evidence = tuple(
                    iid
                    for iid in investor_intent_ids
                    if f":{investor_id}:" in iid and f":{firm_id}:" in iid
                )
                pair_valuation_evidence = tuple(
                    vid
                    for vid in valuation_ids
                    if f":{investor_id}:" in vid and f":{firm_id}:" in vid
                )
                firm_state_for_pair = firm_state_id_by_firm.get(firm_id)
                firm_state_evidence = (
                    (firm_state_for_pair,) if firm_state_for_pair else ()
                )

                # v1.16.2 — resolve the four remaining classifier
                # inputs by reading the cited records.
                investor_intent_direction: str = "unknown"
                if pair_intent_evidence:
                    intent_record = kernel.investor_intents.get_intent(
                        pair_intent_evidence[0]
                    )
                    investor_intent_direction = (
                        intent_record.intent_direction
                    )

                valuation_confidence: float | None = None
                if pair_valuation_evidence:
                    valuation_record = kernel.valuations.get_valuation(
                        pair_valuation_evidence[0]
                    )
                    valuation_confidence = float(valuation_record.confidence)

                firm_market_access_pressure: float | None = None
                if firm_state_for_pair:
                    firm_state_record = (
                        kernel.firm_financial_states.get_state(
                            firm_state_for_pair
                        )
                    )
                    firm_market_access_pressure = float(
                        firm_state_record.market_access_pressure
                    )

                classifier_result = classify_market_intent_direction(
                    investor_intent_direction=investor_intent_direction,
                    valuation_confidence=valuation_confidence,
                    firm_market_access_pressure=firm_market_access_pressure,
                    market_environment_access_label=(
                        period_market_access_label
                    ),
                    attention_focus_labels=attention_focus_labels,
                )

                intent_direction = classifier_result.intent_direction_label
                intensity = _intensity_label_for_classifier_confidence(
                    classifier_result.status,
                    classifier_result.confidence,
                )

                classifier_metadata: dict[str, Any] = {
                    "classifier_version": "v1.16.1",
                    "classifier_rule_id": classifier_result.rule_id,
                    "classifier_status": classifier_result.status,
                    "classifier_confidence": classifier_result.confidence,
                    "classifier_unresolved_or_missing_count": (
                        classifier_result.unresolved_or_missing_count
                    ),
                    "classifier_evidence_summary": dict(
                        classifier_result.evidence_summary
                    ),
                }

                market_intent_id = (
                    f"market_intent:{investor_id}:{security_id}:{iso_date}"
                )
                try:
                    kernel.investor_market_intents.add_intent(
                        InvestorMarketIntentRecord(
                            market_intent_id=market_intent_id,
                            investor_id=investor_id,
                            security_id=security_id,
                            as_of_date=iso_date,
                            intent_direction_label=intent_direction,
                            intensity_label=intensity,
                            horizon_label="near_term",
                            status="active",
                            visibility="internal_only",
                            confidence=classifier_result.confidence,
                            evidence_investor_intent_ids=(
                                pair_intent_evidence
                            ),
                            evidence_valuation_ids=pair_valuation_evidence,
                            evidence_market_environment_state_ids=(
                                mes_ids_period
                            ),
                            evidence_firm_state_ids=firm_state_evidence,
                            evidence_security_ids=(security_id,),
                            evidence_venue_ids=(primary_market_venue_id,),
                            metadata=classifier_metadata,
                        )
                    )
                except DuplicateInvestorMarketIntentError:
                    pass
                investor_market_intent_ids.append(market_intent_id)
                market_intent_ids_by_security.setdefault(
                    security_id, []
                ).append(market_intent_id)

        # Aggregated market interest — one per listed security per
        # period via the v1.15.3 helper. The helper reads only the
        # cited investor-market-intent ids; mismatched and
        # unresolved ids are recorded in metadata.
        aggregated_market_interest_ids: list[str] = []
        aggregated_id_by_security: dict[str, str] = {}
        for firm_id in firms:
            security_id = listed_security_id_by_firm.get(firm_id)
            if security_id is None:
                continue
            intent_ids_for_security = tuple(
                market_intent_ids_by_security.get(security_id, ())
            )
            try:
                agg = build_aggregated_market_interest(
                    kernel,
                    venue_id=primary_market_venue_id,
                    security_id=security_id,
                    as_of_date=iso_date,
                    source_market_intent_ids=intent_ids_for_security,
                    source_market_environment_state_ids=mes_ids_period,
                )
                aggregated_id = agg.aggregated_interest_id
            except DuplicateAggregatedMarketInterestError:
                aggregated_id = (
                    f"aggregated_market_interest:"
                    f"{primary_market_venue_id}:{security_id}:{iso_date}"
                )
            aggregated_market_interest_ids.append(aggregated_id)
            aggregated_id_by_security[security_id] = aggregated_id

        # Indicative market pressure — one per listed security per
        # period via the v1.15.4 helper. The helper does not mutate
        # the PriceBook (pinned by a dedicated test in
        # tests/test_market_pressure.py).
        indicative_market_pressure_ids: list[str] = []
        for firm_id in firms:
            security_id = listed_security_id_by_firm.get(firm_id)
            if security_id is None:
                continue
            agg_for_security = aggregated_id_by_security.get(security_id)
            agg_refs = (agg_for_security,) if agg_for_security else ()
            try:
                pressure = build_indicative_market_pressure(
                    kernel,
                    security_id=security_id,
                    as_of_date=iso_date,
                    source_aggregated_interest_ids=agg_refs,
                    source_market_environment_state_ids=mes_ids_period,
                    source_security_ids=(security_id,),
                    source_venue_ids=(primary_market_venue_id,),
                )
                indicative_market_pressure_ids.append(
                    pressure.market_pressure_id
                )
            except DuplicateIndicativeMarketPressureError:
                indicative_market_pressure_ids.append(
                    f"indicative_market_pressure:{security_id}:{iso_date}"
                )

        # ------------------------------------------------------------------
        # v1.14.5 — corporate financing chain phase.
        #
        # For each firm, emit one CorporateFinancingNeedRecord, two
        # FundingOptionCandidate records (bank loan + bond issuance),
        # one CapitalStructureReviewCandidate, and one
        # CorporateFinancingPathRecord (via the v1.14.4 deterministic
        # builder). The chain is bounded — no investor × firm × option
        # explosion — and every record cross-references the period's
        # firm state, market environment, interbank liquidity, bank
        # credit review, and investor intent ids where available.
        #
        # Storage / audit / graph-linking only. There is **no
        # financing execution, no loan approval, no bond / equity
        # issuance, no underwriting, no syndication, no bookbuilding,
        # no allocation, no interest rate / spread / fee / coupon /
        # offering price, no optimal capital structure decision, no
        # capital structure optimisation, no real leverage / D/E /
        # WACC calculation, no lending decision, no investment
        # recommendation, no trading, no price formation, no real
        # data ingestion, no Japan calibration**.
        #
        # Synthetic labels vary by firm position so the per-period
        # report carries non-trivial histograms. The exact mapping is
        # deterministic.
        #
        # **v1.15.6 update.** This phase now runs *after* the
        # v1.15.5 securities-market-intent chain phase (above) so
        # each firm's review and path can cite the same period's
        # `IndicativeMarketPressureRecord`. ``mes_ids_period`` and
        # ``ibl_ids_period`` are defined once at the top of the
        # chain region (just before the v1.15.5 phase).
        # ------------------------------------------------------------------
        # Per-firm pressure-id lookup populated by the v1.15.5
        # phase above. The v1.14.5 chain consumes it below to
        # cite this period's pressure record on the firm's
        # equity-like security.
        pressure_id_by_security: dict[str, str] = {}
        pressure_record_by_security: dict[str, Any] = {}
        for pid in indicative_market_pressure_ids:
            try:
                pressure = kernel.indicative_market_pressure.get_record(pid)
            except Exception:  # pragma: no cover - defensive
                continue
            pressure_id_by_security[pressure.security_id] = pid
            pressure_record_by_security[pressure.security_id] = pressure

        corporate_financing_need_ids: list[str] = []
        funding_option_candidate_ids: list[str] = []
        capital_structure_review_candidate_ids: list[str] = []
        corporate_financing_path_ids: list[str] = []

        for firm_idx, firm_id in enumerate(firms):
            firm_state_id = firm_state_id_by_firm.get(firm_id)
            firm_state_refs = (firm_state_id,) if firm_state_id else ()
            firm_corp_signal = corp_signal_by_firm.get(firm_id)
            firm_corp_signal_refs = (
                (firm_corp_signal,) if firm_corp_signal else ()
            )

            purpose = _CORPORATE_FINANCING_PURPOSE_BY_FIRM_INDEX[
                firm_idx % len(_CORPORATE_FINANCING_PURPOSE_BY_FIRM_INDEX)
            ]
            review_type = _CORPORATE_FINANCING_REVIEW_TYPE_BY_FIRM_INDEX[
                firm_idx
                % len(_CORPORATE_FINANCING_REVIEW_TYPE_BY_FIRM_INDEX)
            ]
            mkt_access = _CORPORATE_FINANCING_MARKET_ACCESS_BY_FIRM_INDEX[
                firm_idx
                % len(_CORPORATE_FINANCING_MARKET_ACCESS_BY_FIRM_INDEX)
            ]
            dilution_concern = "low"

            # v1.15.6 — pressure feedback. If the firm's listed
            # security has a same-period
            # ``IndicativeMarketPressureRecord`` (built by the
            # v1.15.5 phase above), cite it on the review and the
            # path and let it influence two label fields:
            #
            # - ``market_access_label`` is overridden to match the
            #   pressure's ``market_access_label`` whenever the
            #   pressure says ``constrained`` or ``closed`` — the
            #   market surface dominates when access is actually
            #   constrained.
            # - ``dilution_concern_label`` is bumped from ``low``
            #   to ``moderate`` when the pressure's
            #   ``financing_relevance_label`` is
            #   ``caution_for_dilution``, and to ``high`` when it
            #   is ``adverse_for_market_access``.
            #
            # Pressure can NOT cause approval, pricing, or any
            # execution effect — only label drift on these two
            # closed-set axes. The full
            # ``MARKET_ACCESS_LABELS`` vocabulary alignment
            # pinned by v1.15.4's ``is``-identity test makes the
            # market_access override mechanical (no conversion).
            firm_security_id = listed_security_id_by_firm.get(firm_id)
            firm_pressure_id = (
                pressure_id_by_security.get(firm_security_id)
                if firm_security_id
                else None
            )
            firm_pressure_record = (
                pressure_record_by_security.get(firm_security_id)
                if firm_security_id
                else None
            )
            firm_pressure_ids: tuple[str, ...] = (
                (firm_pressure_id,) if firm_pressure_id else ()
            )
            if firm_pressure_record is not None:
                if firm_pressure_record.market_access_label in (
                    "constrained",
                    "closed",
                ):
                    mkt_access = firm_pressure_record.market_access_label
                if (
                    firm_pressure_record.financing_relevance_label
                    == "caution_for_dilution"
                ):
                    dilution_concern = "moderate"
                elif (
                    firm_pressure_record.financing_relevance_label
                    == "adverse_for_market_access"
                ):
                    dilution_concern = "high"

            # Per-firm filtering of cross-references (avoids citing
            # other firms' bank credit reviews / investor intents on
            # this firm's path).
            firm_bcr_ids = tuple(
                sid
                for sid in bank_credit_review_signal_ids
                if f":{firm_id}:" in sid
            )
            firm_intent_ids = tuple(
                iid
                for iid in investor_intent_ids
                if f":{firm_id}:" in iid
            )

            # 1. Corporate financing need (one per firm per period).
            need_id = f"corporate_financing_need:{firm_id}:{iso_date}"
            try:
                kernel.corporate_financing_needs.add_need(
                    CorporateFinancingNeedRecord(
                        need_id=need_id,
                        firm_id=firm_id,
                        as_of_date=iso_date,
                        funding_horizon_label="near_term",
                        funding_purpose_label=purpose,
                        urgency_label="moderate",
                        synthetic_size_label="reference_size_medium",
                        status="active",
                        visibility="internal_only",
                        confidence=0.5,
                        source_firm_financial_state_ids=firm_state_refs,
                        source_market_environment_state_ids=mes_ids_period,
                        source_corporate_signal_ids=firm_corp_signal_refs,
                    )
                )
            except DuplicateCorporateFinancingNeedError:
                pass
            corporate_financing_need_ids.append(need_id)

            # 2. Two funding option candidates per need
            #    (bank_loan_candidate + bond_issuance_candidate). The
            #    label set is deliberately small and generic — the
            #    point is to show a bounded, non-binding set of
            #    routes, not to enumerate exhaustively.
            firm_option_ids: list[str] = []
            for kind, instrument_class in (
                ("bank_loan", "loan"),
                ("bond_issuance", "bond"),
            ):
                option_id = (
                    f"funding_option:{firm_id}:{kind}:{iso_date}"
                )
                try:
                    kernel.funding_options.add_candidate(
                        FundingOptionCandidate(
                            funding_option_id=option_id,
                            firm_id=firm_id,
                            as_of_date=iso_date,
                            option_type_label=f"{kind}_candidate",
                            instrument_class_label=instrument_class,
                            maturity_band_label="medium_term",
                            seniority_label="senior",
                            accessibility_label="accessible",
                            urgency_fit_label="near_term",
                            market_fit_label="supportive",
                            status="candidate",
                            visibility="internal_only",
                            confidence=0.5,
                            source_need_ids=(need_id,),
                            source_market_environment_state_ids=mes_ids_period,
                            source_interbank_liquidity_state_ids=ibl_ids_period,
                            source_firm_state_ids=firm_state_refs,
                            source_bank_credit_review_signal_ids=firm_bcr_ids,
                            source_investor_intent_ids=firm_intent_ids,
                        )
                    )
                except DuplicateFundingOptionCandidateError:
                    pass
                firm_option_ids.append(option_id)
                funding_option_candidate_ids.append(option_id)

            # 3. Capital structure review (one per firm per period).
            review_id = f"capital_structure_review:{firm_id}:{iso_date}"
            try:
                kernel.capital_structure_reviews.add_candidate(
                    CapitalStructureReviewCandidate(
                        review_candidate_id=review_id,
                        firm_id=firm_id,
                        as_of_date=iso_date,
                        review_type_label=review_type,
                        leverage_pressure_label="moderate",
                        liquidity_pressure_label="moderate",
                        maturity_wall_label="manageable",
                        dilution_concern_label=dilution_concern,
                        covenant_headroom_label="comfortable",
                        market_access_label=mkt_access,
                        rating_perception_label="stable",
                        status="candidate",
                        visibility="internal_only",
                        confidence=0.5,
                        source_need_ids=(need_id,),
                        source_funding_option_ids=tuple(firm_option_ids),
                        source_firm_state_ids=firm_state_refs,
                        source_market_environment_state_ids=mes_ids_period,
                        source_interbank_liquidity_state_ids=ibl_ids_period,
                        source_bank_credit_review_signal_ids=firm_bcr_ids,
                        source_investor_intent_ids=firm_intent_ids,
                        source_indicative_market_pressure_ids=(
                            firm_pressure_ids
                        ),
                    )
                )
            except DuplicateCapitalStructureReviewError:
                pass
            capital_structure_review_candidate_ids.append(review_id)

            # 4. Financing path (one per firm per period). Built via
            #    the v1.14.4 deterministic helper, which derives
            #    ``path_type`` / ``coherence`` / ``constraint`` /
            #    ``next_review`` from the cited records — without any
            #    global scan and without choosing an optimal option.
            try:
                path = build_corporate_financing_path(
                    kernel,
                    firm_id=firm_id,
                    as_of_date=iso_date,
                    need_ids=(need_id,),
                    funding_option_ids=tuple(firm_option_ids),
                    capital_structure_review_ids=(review_id,),
                    market_environment_state_ids=mes_ids_period,
                    interbank_liquidity_state_ids=ibl_ids_period,
                    bank_credit_review_signal_ids=firm_bcr_ids,
                    investor_intent_ids=firm_intent_ids,
                    indicative_market_pressure_ids=firm_pressure_ids,
                )
                corporate_financing_path_ids.append(
                    path.financing_path_id
                )
            except DuplicateCorporateFinancingPathError:
                corporate_financing_path_ids.append(
                    f"corporate_financing_path:{firm_id}:{iso_date}"
                )

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
                investor_attention_state_ids=tuple(
                    investor_attention_state_ids
                ),
                investor_attention_feedback_ids=tuple(
                    investor_attention_feedback_ids
                ),
                bank_attention_state_ids=tuple(bank_attention_state_ids),
                bank_attention_feedback_ids=tuple(
                    bank_attention_feedback_ids
                ),
                investor_memory_selection_ids=tuple(
                    investor_memory_selection_ids
                ),
                bank_memory_selection_ids=tuple(
                    bank_memory_selection_ids
                ),
                corporate_financing_need_ids=tuple(
                    corporate_financing_need_ids
                ),
                funding_option_candidate_ids=tuple(
                    funding_option_candidate_ids
                ),
                capital_structure_review_candidate_ids=tuple(
                    capital_structure_review_candidate_ids
                ),
                corporate_financing_path_ids=tuple(
                    corporate_financing_path_ids
                ),
                investor_market_intent_ids=tuple(investor_market_intent_ids),
                aggregated_market_interest_ids=tuple(
                    aggregated_market_interest_ids
                ),
                indicative_market_pressure_ids=tuple(
                    indicative_market_pressure_ids
                ),
                scheduled_release_ids=period_scheduled_release_ids,
                information_arrival_ids=period_information_arrival_ids,
                reference_universe_ids=(
                    (run_reference_universe_id,)
                    if run_reference_universe_id
                    else ()
                ),
                sector_ids=run_sector_ids,
                firm_profile_ids=run_firm_profile_ids,
                scenario_schedule_ids=(
                    (run_scenario_schedule_id,)
                    if run_scenario_schedule_id
                    else ()
                ),
                scheduled_scenario_application_ids=(
                    (run_scheduled_scenario_application_id,)
                    if run_scheduled_scenario_application_id
                    else ()
                ),
                scenario_application_ids=period_scenario_application_ids,
                scenario_context_shift_ids=period_scenario_context_shift_ids,
                record_count_created=period_end_idx - period_start_idx,
                metadata={
                    "period_index": period_idx,
                    "ledger_record_count_before": period_start_idx,
                    "ledger_record_count_after": period_end_idx,
                },
            )
        )

        # v1.16.3 — capture this period's pressure / financing
        # path ids so the next period's attention-feedback phase
        # can cite them. The variables are read at the *next*
        # iteration's investor / bank attention-feedback build.
        prev_period_indicative_market_pressure_ids = tuple(
            indicative_market_pressure_ids
        )
        prev_period_corporate_financing_path_ids = tuple(
            corporate_financing_path_ids
        )

    ledger_count_after = len(kernel.ledger.records)
    created_record_ids = _ledger_object_ids_since(
        kernel, since_index=ledger_count_before
    )

    listed_security_ids = tuple(
        sorted(listed_security_id_by_firm.values())
    )
    market_venue_ids = (primary_market_venue_id,)

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
        listed_security_ids=listed_security_ids,
        market_venue_ids=market_venue_ids,
        reference_universe_ids=(
            (run_reference_universe_id,)
            if run_reference_universe_id
            else ()
        ),
        sector_ids=run_sector_ids,
        firm_profile_ids=run_firm_profile_ids,
        scenario_schedule_ids=(
            (run_scenario_schedule_id,)
            if run_scenario_schedule_id
            else ()
        ),
        scheduled_scenario_application_ids=(
            (run_scheduled_scenario_application_id,)
            if run_scheduled_scenario_application_id
            else ()
        ),
        metadata=dict(metadata or {}),
    )
