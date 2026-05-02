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
from world.observation_menu_builder import ObservationMenuBuildRequest
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
) -> LivingReferenceWorldResult:
    """
    Sweep the v1.8.14 endogenous chain over ``period_dates``.

    The kernel must already be wired (variables / exposures / etc.
    seeded). v1.9.0 is orchestration over existing helpers; it does
    **not** seed the world for the caller. Tests build their own
    kernel; the CLI (`run_living_reference_world.py`) builds a tiny
    inline fixture.

    Per-period flow (each phase invokes only existing component
    helpers — no new behavior is introduced):

    1. **Corporate phase** — for each ``firm_id`` in ``firm_ids``,
       call :func:`run_corporate_quarterly_reporting` for the
       period's as-of date. One ``RoutineRunRecord`` + one
       ``corporate_quarterly_report`` ``InformationSignal`` per
       firm per period.
    2. **Attention phase** — for each ``investor_id`` and each
       ``bank_id``, build one ``ObservationMenu`` through the
       v1.8.11 ``ObservationMenuBuilder`` and one
       ``SelectedObservationSet`` through
       :func:`select_observations_for_profile` + the
       ``AttentionBook.add_selection`` ledger path. Investor and
       bank selections diverge along the v1.8.12 attention axes.
    3. **Review phase** — for each investor and each bank, call
       the matching ``run_*_review`` helper with the period's
       selection ids. One ``RoutineRunRecord`` + one
       ``investor_review_note`` / ``bank_review_note``
       ``InformationSignal`` per actor per period.

    Side effects (delegated to component helpers — the harness
    itself never writes):

    - ``len(firm_ids) × len(period_dates)`` corporate
      ``RoutineRunRecord``s + matching ``InformationSignal``s.
    - ``(len(investor_ids) + len(bank_ids)) × len(period_dates)``
      ``ObservationMenu``s.
    - ``(len(investor_ids) + len(bank_ids)) × len(period_dates)``
      ``SelectedObservationSet``s.
    - ``(len(investor_ids) + len(bank_ids)) × len(period_dates)``
      review ``RoutineRunRecord``s + matching review-note
      ``InformationSignal``s.
    - The corresponding ledger entries.

    Anti-scope: no ``valuations`` / ``prices`` / ``ownership`` /
    ``contracts`` / ``constraints`` / ``institutions`` /
    ``external_processes`` / ``relationships`` book is mutated.
    No scheduler hook, no auto-firing from ``tick()`` / ``run()``.
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
        metadata=dict(metadata or {}),
    )
