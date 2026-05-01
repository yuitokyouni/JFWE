"""
v1.6 First Closed-loop Reference System.

This test file demonstrates that the v1 record types
(ExternalFactorObservation, InformationSignal, ValuationRecord,
ValuationGap, InstitutionalActionRecord, WorldEvent) can be linked
into a single end-to-end causal chain through the existing books,
without any module mutating state outside its own book and without
any economic decision being made.

The chain:

    ExternalFactorObservation
      -> InformationSignal (related_ids contains observation)
      -> ValuationRecord    (related_ids/inputs contain signal)
      -> ValuationGap       (comparator output, parent links to valuation_added)
      -> InstitutionalActionRecord (input_refs include valuation;
                                    parent_record_ids link valuation_added
                                    and valuation_compared; output_refs name
                                    the planned follow-up signal)
      -> InformationSignal  (follow-up; related_ids contain action)
      -> WorldEvent         (payload signal_id; delivered next tick)
      -> Ledger trace with event_published / event_delivered records.
"""

from datetime import date

from spaces.banking.space import BankSpace
from spaces.investors.space import InvestorSpace
from world.clock import Clock
from world.external_processes import ExternalFactorProcess
from world.institutions import InstitutionProfile
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.reference_loop import ReferenceLoopRunner
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _setup_loop_world() -> tuple[WorldKernel, ReferenceLoopRunner]:
    """
    Build a kernel ready to run the reference loop:
    - one external process with a base value
    - one priced subject so the comparator can compute a gap
    - one institution registered (to satisfy convention)
    - banking and investors spaces registered as event targets (both DAILY)
    """
    kernel = _kernel()
    runner = ReferenceLoopRunner(kernel=kernel)

    kernel.external_processes.add_process(
        ExternalFactorProcess(
            process_id="process:reference_macro",
            factor_id="factor:reference_macro_index",
            factor_type="macro_indicator",
            process_type="constant",
            unit="index_points",
            base_value=100.0,
        )
    )

    kernel.prices.set_price(
        "firm:reference_a", 95.0, "2026-01-01", "exchange"
    )

    kernel.institutions.add_institution_profile(
        InstitutionProfile(
            institution_id="institution:reference_authority",
            institution_type="reference_authority",
            jurisdiction_label="neutral_jurisdiction",
            mandate_summary="reference",
        )
    )

    kernel.register_space(BankSpace())
    kernel.register_space(InvestorSpace())

    return kernel, runner


# ---------------------------------------------------------------------------
# End-to-end loop
# ---------------------------------------------------------------------------


def test_reference_loop_creates_full_causal_chain():
    """
    Walk the entire 7-step loop and verify each record carries the
    forward and backward references that turn the ledger into a
    causal graph.
    """
    kernel, runner = _setup_loop_world()

    # -- Step 1: external observation, stamped to overnight phase.
    obs = runner.record_external_observation(
        process_id="process:reference_macro",
        as_of_date="2026-01-01",
        phase_id="overnight",
    )
    assert obs.factor_id == "factor:reference_macro_index"
    assert obs.value == 100.0
    assert obs.phase_id == "overnight"

    # -- Step 2: signal referencing the observation.
    signal_obs = runner.emit_signal_from_observation(
        observation=obs,
        signal_id="signal:macro_observed",
        signal_type="macro_indicator",
        source_id="source:reference_macro_feed",
        subject_id="factor:reference_macro_index",
    )
    assert signal_obs.related_ids == ("observation:process:reference_macro:2026-01-01:overnight",)
    assert signal_obs.payload["observation_id"] == obs.observation_id

    # -- Step 3: valuation referencing the signal.
    valuation = runner.record_valuation_from_signal(
        signal=signal_obs,
        valuation_id="valuation:loop_001",
        subject_id="firm:reference_a",
        valuer_id="valuer:reference_dcf",
        valuation_type="equity",
        purpose="investment_research",
        method="dcf",
        as_of_date="2026-01-01",
        estimated_value=110.0,
        currency="reference_unit",
        confidence=0.7,
    )
    assert valuation.related_ids == (signal_obs.signal_id,)
    assert valuation.inputs["signal_id"] == signal_obs.signal_id

    # -- Step 4: comparator → gap. Price 95, valuation 110 → gap +15 (~15.8%).
    gap = runner.compare_valuation_to_price(valuation.valuation_id)
    assert gap.estimated_value == 110.0
    assert gap.observed_price == 95.0
    assert gap.absolute_gap == 15.0
    assert abs(gap.relative_gap - 15.0 / 95.0) < 1e-9

    # -- Step 5: institutional action referencing valuation + gap.
    action = runner.record_institutional_action(
        action_id="action:loop_announcement_001",
        institution_id="institution:reference_authority",
        action_type="reference_announcement",
        as_of_date="2026-01-01",
        valuation=valuation,
        gap=gap,
        phase_id="post_close",
        planned_output_signal_id="signal:loop_followup_001",
    )
    assert action.input_refs == ("valuation:loop_001",)
    assert action.output_refs == ("signal:loop_followup_001",)
    assert action.target_ids == ("firm:reference_a",)
    assert action.phase_id == "post_close"
    assert action.payload["absolute_gap"] == 15.0

    # parent_record_ids on the action point to the valuation_added and
    # valuation_compared ledger records.
    valuation_added = kernel.ledger.filter(
        event_type="valuation_added", task_id=None
    )
    valuation_added_ids = {r.record_id for r in valuation_added}
    valuation_compared = kernel.ledger.filter(
        event_type="valuation_compared"
    )
    valuation_compared_ids = {r.record_id for r in valuation_compared}
    parent_set = set(action.parent_record_ids)
    assert parent_set & valuation_added_ids, "action must link to valuation_added"
    assert (
        parent_set & valuation_compared_ids
    ), "action must link to valuation_compared"

    # -- Step 6: follow-up signal referencing the action.
    signal_followup = runner.emit_signal_from_action(
        action=action,
        signal_id="signal:loop_followup_001",
        signal_type="reference_announcement",
        source_id="institution:reference_authority",
        subject_id="firm:reference_a",
    )
    assert signal_followup.related_ids == (action.action_id,)
    assert signal_followup.payload["action_id"] == action.action_id
    # action.output_refs already names this signal.
    assert signal_followup.signal_id in action.output_refs

    # -- Step 7: publish a WorldEvent that carries the follow-up signal.
    event = runner.publish_signal_event(
        signal=signal_followup,
        event_id="event:loop_announcement",
        source_space="information",
        target_spaces=("banking", "investors"),
    )
    assert event.payload["signal_id"] == signal_followup.signal_id
    assert event.related_ids == (signal_followup.signal_id,)

    # -- Day 1 tick: publication_date == current_date, so no delivery yet.
    kernel.run(days=1)
    delivered_after_day_1 = kernel.ledger.filter(event_type="event_delivered")
    assert len(delivered_after_day_1) == 0

    # -- Day 2 tick: published_on < current_date, both targets receive.
    kernel.run(days=1)
    delivered = kernel.ledger.filter(event_type="event_delivered")
    targets = {r.target for r in delivered}
    assert targets == {"banking", "investors"}


def test_reference_loop_ledger_has_all_expected_record_types():
    """The loop run must populate the full set of expected ledger types."""
    kernel, runner = _setup_loop_world()

    obs = runner.record_external_observation(
        "process:reference_macro", "2026-01-01", phase_id="overnight"
    )
    sig1 = runner.emit_signal_from_observation(
        obs, "signal:o1", "macro_indicator",
        "source:macro", "factor:reference_macro_index",
    )
    val = runner.record_valuation_from_signal(
        sig1, "valuation:loop", "firm:reference_a",
        "valuer:reference_dcf", "equity", "investment_research", "dcf",
        "2026-01-01", 110.0, "reference_unit",
    )
    gap = runner.compare_valuation_to_price(val.valuation_id)
    act = runner.record_institutional_action(
        "action:loop", "institution:reference_authority", "reference_announcement",
        "2026-01-01", val, gap,
        phase_id="post_close",
        planned_output_signal_id="signal:f1",
    )
    sig2 = runner.emit_signal_from_action(
        act, "signal:f1", "reference_announcement",
        "institution:reference_authority", "firm:reference_a",
    )
    runner.publish_signal_event(
        sig2, "event:loop", "information", ("banking", "investors")
    )
    kernel.run(days=2)  # advance past the delivery boundary

    expected_event_types = {
        "external_observation_added",
        "signal_added",
        "valuation_added",
        "valuation_compared",
        "institution_action_recorded",
        "event_published",
        "event_delivered",
    }
    actual = {r.event_type for r in kernel.ledger.records}
    missing = expected_event_types - actual
    assert missing == set(), f"Missing ledger event types: {missing}"


# ---------------------------------------------------------------------------
# Causal chain reachability
# ---------------------------------------------------------------------------


def test_reference_loop_causal_chain_reachable_from_every_link():
    """
    Build the loop and verify each forward link is preserved on the
    record. A single test that walks observation → signal → valuation
    → gap → action → follow-up signal → event payload.
    """
    kernel, runner = _setup_loop_world()

    obs = runner.record_external_observation(
        "process:reference_macro", "2026-01-01"
    )
    sig1 = runner.emit_signal_from_observation(
        obs, "signal:o", "x", "source:s", "factor:reference_macro_index"
    )
    val = runner.record_valuation_from_signal(
        sig1, "valuation:v", "firm:reference_a",
        "valuer:r", "equity", "purpose", "method",
        "2026-01-01", 110.0,
    )
    gap = runner.compare_valuation_to_price(val.valuation_id)
    act = runner.record_institutional_action(
        "action:a", "institution:reference_authority", "x",
        "2026-01-01", val, gap, planned_output_signal_id="signal:f",
    )
    sig2 = runner.emit_signal_from_action(
        act, "signal:f", "x", "institution:reference_authority",
        "firm:reference_a",
    )
    event = runner.publish_signal_event(
        sig2, "event:e", "information", ("banking",)
    )

    # Forward chain via record fields (not ledger):
    # obs --(related_ids)--> sig1
    assert obs.observation_id in sig1.related_ids
    # sig1 --(related_ids/inputs)--> val
    assert sig1.signal_id in val.related_ids
    assert val.inputs["signal_id"] == sig1.signal_id
    # val --(input_refs)--> act
    assert val.valuation_id in act.input_refs
    # gap.valuation_id == val.valuation_id
    assert gap.valuation_id == val.valuation_id
    # act --(output_refs)--> sig2
    assert sig2.signal_id in act.output_refs
    # sig2 --(related_ids)--> back to act (back-reference)
    assert act.action_id in sig2.related_ids
    # event --(payload + related_ids)--> sig2
    assert event.payload["signal_id"] == sig2.signal_id
    assert sig2.signal_id in event.related_ids


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def test_reference_loop_does_not_mutate_unrelated_books():
    """
    The reference loop writes only to the books it explicitly uses
    (external_processes, signals, valuations, institutions, ledger,
    event_bus). Unrelated books — ownership, contracts, prices,
    constraints, relationships — must be byte-identical before and
    after the loop runs.
    """
    kernel, runner = _setup_loop_world()

    # Seed unrelated books with one entry each so snapshot equality is
    # meaningful (an empty before/after comparison is trivially true).
    kernel.ownership.add_position("agent:alice", "asset:cash", 100)
    kernel.contracts  # touch attribute; nothing to add for v1.6
    kernel.constraints  # ditto
    kernel.relationships  # ditto

    # The price for "firm:reference_a" was already set by _setup_loop_world.
    # We snapshot AFTER seed but BEFORE the loop.
    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    relationships_before = kernel.relationships.snapshot()

    # Run the full loop.
    obs = runner.record_external_observation(
        "process:reference_macro", "2026-01-01", phase_id="overnight"
    )
    sig1 = runner.emit_signal_from_observation(
        obs, "signal:o", "x", "source:s", "factor:reference_macro_index"
    )
    val = runner.record_valuation_from_signal(
        sig1, "valuation:v", "firm:reference_a",
        "valuer:r", "equity", "purpose", "method",
        "2026-01-01", 110.0,
    )
    gap = runner.compare_valuation_to_price(val.valuation_id)
    act = runner.record_institutional_action(
        "action:a", "institution:reference_authority", "x",
        "2026-01-01", val, gap,
        phase_id="post_close",
        planned_output_signal_id="signal:f",
    )
    sig2 = runner.emit_signal_from_action(
        act, "signal:f", "x", "institution:reference_authority",
        "firm:reference_a",
    )
    runner.publish_signal_event(
        sig2, "event:e", "information", ("banking", "investors")
    )
    kernel.run(days=2)

    # Unrelated books are unchanged. (Prices, contracts, ownership,
    # constraints, relationships are not touched by any step.)
    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.relationships.snapshot() == relationships_before


# ---------------------------------------------------------------------------
# Phase stamping
# ---------------------------------------------------------------------------


def test_reference_loop_uses_phase_id_on_observation_and_action():
    """
    External observations may be stamped with overnight; institutional
    actions with post_close. v1.6 records the phase_id on the records;
    actual phase-aware dispatch via run_day_with_phases is the v1.2
    feature that v1.6 does not exercise.
    """
    kernel, runner = _setup_loop_world()

    obs = runner.record_external_observation(
        "process:reference_macro", "2026-01-01", phase_id="overnight"
    )
    assert obs.phase_id == "overnight"

    sig1 = runner.emit_signal_from_observation(
        obs, "signal:o", "x", "source:s", "factor:reference_macro_index"
    )
    val = runner.record_valuation_from_signal(
        sig1, "valuation:v", "firm:reference_a",
        "valuer:r", "equity", "purpose", "method",
        "2026-01-01", 110.0,
    )
    gap = runner.compare_valuation_to_price(val.valuation_id)
    act = runner.record_institutional_action(
        "action:a", "institution:reference_authority", "x",
        "2026-01-01", val, gap,
        phase_id="post_close",
    )
    assert act.phase_id == "post_close"
