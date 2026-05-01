"""
v1.8.14 Endogenous chain harness.

A pure orchestration helper that runs the existing v1.8.7 / v1.8.12
/ v1.8.13 endogenous reference chain end-to-end:

    corporate quarterly reporting
        → heterogeneous investor / bank attention
            → investor review
                → bank review

The harness is **orchestration only** — it does not duplicate any
component logic, does not introduce any new economic behavior, and
does not register any new ledger record types. Every write goes
through the existing component helpers
(``register_corporate_reporting_interaction`` /
``register_corporate_quarterly_reporting_routine`` /
``run_corporate_quarterly_reporting``,
``run_investor_bank_attention_demo``,
``register_investor_review_interaction`` /
``register_investor_review_routine`` / ``run_investor_review``,
and the bank-side equivalents).

What v1.8.14 deliberately does NOT do
-------------------------------------

- No new economic behavior. No price formation, trading, lending
  decisions, valuation refresh, impact estimation, sensitivity
  calculation, DSCR / LTV updates, covenant enforcement, corporate
  actions, policy reactions.
- No scheduler auto-firing. The chain is caller-initiated; it
  does not register a scheduler task and does not hook into
  ``tick()`` / ``run()``.
- No year-long simulation. v1.8.14 runs one chain on one
  ``as_of_date``; the v1.9 Living Reference World Demo will sweep
  this harness over a full calendar year.
- No real Japan calibration; no scenario engine; no real data
  ingestion. All ids are synthetic and v1's forbidden-token list
  (``world/experiment.py::_FORBIDDEN_TOKENS``) is honored.

What v1.8.14 ships
------------------

- :func:`run_reference_endogenous_chain` — the orchestration
  helper. Calls the four component flows in order and returns a
  deterministic :class:`EndogenousChainResult`.
- :class:`EndogenousChainResult` — immutable summary that names
  every record the chain wrote. The summary is **not the source
  of truth**; it is a convenience surface. The same chain is
  fully reconstructable from the kernel's ledger by slicing the
  records produced between the call's start and end.

Determinism
-----------

Given two fresh kernels seeded identically, two calls with the
same arguments produce byte-identical results: every id in the
chain is derived from the actor / firm / as-of-date inputs, and
the component helpers are themselves deterministic. The chain
does not consult the wall clock; ``as_of_date`` defaults to
``kernel.clock.current_date`` when omitted.

Anti-scenario discipline
------------------------

A chain whose corporate routine has no inputs, or whose investor /
bank selection contains zero refs, runs to completion with the
relevant phase recorded as ``"degraded"`` rather than ``"failed"``.
Empty input is *partial coverage*, not silent failure. The
harness reports the mix faithfully through the underlying
phase results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping

from world.reference_attention import (
    InvestorBankAttentionDemoResult,
    run_investor_bank_attention_demo,
)
from world.reference_reviews import (
    ReviewRoutineResult,
    register_bank_review_interaction,
    register_bank_review_routine,
    register_investor_review_interaction,
    register_investor_review_routine,
    run_bank_review,
    run_investor_review,
)
from world.reference_routines import (
    CorporateReportingResult,
    register_corporate_quarterly_reporting_routine,
    register_corporate_reporting_interaction,
    run_corporate_quarterly_reporting,
)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EndogenousChainResult:
    """
    Aggregate summary of one ``run_reference_endogenous_chain`` call.

    Names every id the chain wrote so callers can correlate run
    records, signals, menus, and selections without re-querying
    the kernel. The summary is **convenience**, not truth — the
    same chain is reconstructable from the kernel ledger alone:

    - ``ledger_record_count_before`` and ``ledger_record_count_after``
      are the ledger lengths immediately before the chain started
      and immediately after the chain finished. ``after - before``
      equals ``len(created_record_ids)``.
    - ``created_record_ids`` is the *ordered* tuple of
      ``LedgerRecord.object_id`` values for every record written
      during the chain. v1.8.14 does not introduce new record
      types, so each entry resolves to one of:
      ``RoutineRunRecord`` / ``InformationSignal`` /
      ``ObservationMenu`` / ``SelectedObservationSet`` /
      ``AttentionProfile``.

    Selection-overlap fields mirror the v1.8.12 demo result so
    callers do not have to recompute set differences:

    - ``shared_selected_refs`` — refs in both investor and bank
      selections, in investor-order.
    - ``investor_only_selected_refs`` / ``bank_only_selected_refs``
      — refs unique to each actor, preserving menu order.
    """

    firm_id: str
    investor_id: str
    bank_id: str
    as_of_date: str
    phase_id: str | None
    corporate_routine_run_id: str
    corporate_signal_id: str
    investor_profile_id: str
    bank_profile_id: str
    investor_menu_id: str
    bank_menu_id: str
    investor_selection_id: str
    bank_selection_id: str
    investor_review_run_id: str
    bank_review_run_id: str
    investor_review_signal_id: str
    bank_review_signal_id: str
    investor_selected_refs: tuple[str, ...] = field(default_factory=tuple)
    bank_selected_refs: tuple[str, ...] = field(default_factory=tuple)
    shared_selected_refs: tuple[str, ...] = field(default_factory=tuple)
    investor_only_selected_refs: tuple[str, ...] = field(default_factory=tuple)
    bank_only_selected_refs: tuple[str, ...] = field(default_factory=tuple)
    corporate_status: str = "completed"
    investor_review_status: str = "completed"
    bank_review_status: str = "completed"
    ledger_record_count_before: int = 0
    ledger_record_count_after: int = 0
    created_record_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for tuple_field_name in (
            "investor_selected_refs",
            "bank_selected_refs",
            "shared_selected_refs",
            "investor_only_selected_refs",
            "bank_only_selected_refs",
            "created_record_ids",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            object.__setattr__(self, tuple_field_name, value)
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def created_record_count(self) -> int:
        """``len(created_record_ids)``. Provided so callers don't
        have to compute the diff themselves."""
        return len(self.created_record_ids)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_required_string(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} is required and must be a non-empty string")
    return value


def _resolve_as_of_date(
    as_of_date: date | str | None, *, kernel: Any
) -> str:
    if isinstance(as_of_date, date):
        return as_of_date.isoformat()
    if isinstance(as_of_date, str) and as_of_date:
        return as_of_date
    if as_of_date is None:
        if (
            kernel.clock is not None
            and kernel.clock.current_date is not None
        ):
            return kernel.clock.current_date.isoformat()
        raise ValueError(
            "as_of_date is None and the kernel clock has no current_date; "
            "supply as_of_date explicitly."
        )
    raise TypeError(
        f"as_of_date must be a date / ISO string / None; got {as_of_date!r}"
    )


def _ledger_record_count(kernel: Any) -> int:
    return len(kernel.ledger.records)


def _ledger_object_ids_since(
    kernel: Any, *, since_index: int
) -> tuple[str, ...]:
    return tuple(
        record.object_id for record in kernel.ledger.records[since_index:]
    )


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def run_reference_endogenous_chain(
    kernel: Any,
    *,
    firm_id: str,
    investor_id: str,
    bank_id: str,
    as_of_date: date | str | None = None,
    phase_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EndogenousChainResult:
    """
    Run the full v1.8.14 endogenous chain on ``kernel``.

    The kernel must already be wired (variables / exposures / etc.
    seeded). The harness does **not** seed the world for the
    caller — that is by design; v1.8.14 is orchestration over
    existing helpers, not a world-building helper. Tests build
    their own kernel; the v1.9 demo will build the year-long
    seed.

    Phases (each delegates entirely to existing component helpers):

    1. **Corporate**: register the corporate-reporting interaction
       and per-firm routine spec (idempotent), then call
       :func:`run_corporate_quarterly_reporting`.
    2. **Attention**: call
       :func:`run_investor_bank_attention_demo`, which registers
       the per-actor attention profiles (idempotent), builds menus
       through the v1.8.11 ``ObservationMenuBuilder``, and writes
       one ``SelectedObservationSet`` per actor.
    3. **Investor review**: register the investor review interaction
       + routine (idempotent), then call
       :func:`run_investor_review` against the investor's
       selection.
    4. **Bank review**: register the bank review interaction +
       routine (idempotent), then call :func:`run_bank_review`
       against the bank's selection.

    The harness records ``len(kernel.ledger.records)`` before and
    after the chain and captures the ordered sequence of
    ``LedgerRecord.object_id`` values created during the call into
    ``EndogenousChainResult.created_record_ids``. Callers that
    want byte-level audit can re-walk
    ``kernel.ledger.records[before:after]`` themselves.

    Side effects (delegated to component helpers — the harness
    itself never writes):

    - One ``RoutineRunRecord`` + one ``InformationSignal`` for the
      corporate report.
    - Up to two ``AttentionProfile`` records (skipped if already
      registered), two ``ObservationMenu`` records, and two
      ``SelectedObservationSet`` records for the attention phase.
    - One ``RoutineRunRecord`` + one ``InformationSignal`` per
      review (so two of each).
    - The corresponding ledger entries (in the order shown above).

    Anti-scope: no price, valuation, ownership, contract,
    constraint, exposure, variable, institution, or
    external-process state is mutated. v1.8.14 reviewers should
    reject any chain PR that crosses any of these boundaries —
    the harness is forbidden from doing economic work.
    """
    if kernel is None:
        raise ValueError(
            "kernel is required; v1.8.14 is orchestration only and does "
            "not build a kernel for the caller. Construct one and seed "
            "the variables / exposures the chain will touch."
        )
    _validate_required_string(firm_id, name="firm_id")
    _validate_required_string(investor_id, name="investor_id")
    _validate_required_string(bank_id, name="bank_id")

    iso_date = _resolve_as_of_date(as_of_date, kernel=kernel)
    ledger_count_before = _ledger_record_count(kernel)

    # ------------------------------------------------------------------
    # 1. Corporate quarterly reporting
    # ------------------------------------------------------------------
    register_corporate_reporting_interaction(kernel)
    register_corporate_quarterly_reporting_routine(kernel, firm_id=firm_id)
    corporate_result: CorporateReportingResult = (
        run_corporate_quarterly_reporting(
            kernel, firm_id=firm_id, as_of_date=iso_date
        )
    )

    # ------------------------------------------------------------------
    # 2. Heterogeneous attention
    # ------------------------------------------------------------------
    attention_result: InvestorBankAttentionDemoResult = (
        run_investor_bank_attention_demo(
            kernel,
            firm_id=firm_id,
            investor_id=investor_id,
            bank_id=bank_id,
            as_of_date=iso_date,
            phase_id=phase_id,
        )
    )

    # ------------------------------------------------------------------
    # 3. Investor review
    # ------------------------------------------------------------------
    register_investor_review_interaction(kernel)
    register_investor_review_routine(kernel, investor_id=investor_id)
    investor_review_result: ReviewRoutineResult = run_investor_review(
        kernel,
        investor_id=investor_id,
        selected_observation_set_ids=(attention_result.investor_selection_id,),
        as_of_date=iso_date,
    )

    # ------------------------------------------------------------------
    # 4. Bank review
    # ------------------------------------------------------------------
    register_bank_review_interaction(kernel)
    register_bank_review_routine(kernel, bank_id=bank_id)
    bank_review_result: ReviewRoutineResult = run_bank_review(
        kernel,
        bank_id=bank_id,
        selected_observation_set_ids=(attention_result.bank_selection_id,),
        as_of_date=iso_date,
    )

    ledger_count_after = _ledger_record_count(kernel)
    created_record_ids = _ledger_object_ids_since(
        kernel, since_index=ledger_count_before
    )

    return EndogenousChainResult(
        firm_id=firm_id,
        investor_id=investor_id,
        bank_id=bank_id,
        as_of_date=iso_date,
        phase_id=phase_id,
        corporate_routine_run_id=corporate_result.run_id,
        corporate_signal_id=corporate_result.signal_id,
        investor_profile_id=attention_result.investor_profile_id,
        bank_profile_id=attention_result.bank_profile_id,
        investor_menu_id=attention_result.investor_menu_id,
        bank_menu_id=attention_result.bank_menu_id,
        investor_selection_id=attention_result.investor_selection_id,
        bank_selection_id=attention_result.bank_selection_id,
        investor_review_run_id=investor_review_result.run_id,
        bank_review_run_id=bank_review_result.run_id,
        investor_review_signal_id=investor_review_result.signal_id,
        bank_review_signal_id=bank_review_result.signal_id,
        investor_selected_refs=attention_result.investor_selected_refs,
        bank_selected_refs=attention_result.bank_selected_refs,
        shared_selected_refs=attention_result.shared_refs,
        investor_only_selected_refs=attention_result.investor_only_refs,
        bank_only_selected_refs=attention_result.bank_only_refs,
        corporate_status=corporate_result.status,
        investor_review_status=investor_review_result.status,
        bank_review_status=bank_review_result.status,
        ledger_record_count_before=ledger_count_before,
        ledger_record_count_after=ledger_count_after,
        created_record_ids=created_record_ids,
        metadata=dict(metadata or {}),
    )
