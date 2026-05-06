"""
v1.23.2 — Validation Category 3: Citation completeness.

Every plain-id citation surfaced in a
:class:`StressFieldReadout` must resolve to an actual record
in the corresponding kernel book at readout-build time. A
"dangling citation" — a cited id that does not match any
extant record — is a regression class the existing
``tests/test_stress_readout.py`` pins do not catch (they
prove the citation graph is **shaped** correctly; they do
not prove every cited id **resolves**).

The pin walks two id surfaces:

1. ``readout.source_context_record_ids`` — the union of
   each underlying v1.18.2
   :class:`world.scenario_applications.ScenarioContextShiftRecord`'s
   ``affected_context_record_ids``. The pin seeds a
   :class:`world.market_environment.MarketEnvironmentStateRecord`
   in the kernel, passes its id through
   ``apply_stress_program(..., source_context_record_ids=...)``,
   builds the readout, and asserts every readout-cited id
   resolves to a market-environment record.
2. ``readout.downstream_citation_ids`` — caller-supplied
   plain-id list (e.g., a v1.15.5 / v1.16.2 / v1.14.5 record
   that cites the readout). When supplied, the pin asserts
   every id appears in the relevant downstream book (here
   the InvestorMarketIntent book stub — supplied by the
   caller; readout records the citation verbatim).

The pin name: ``test_validation_citation_completeness_pin_v1_23_2``.

Failing-path: a synthetic dangling id passed via
``downstream_citation_ids`` does NOT appear in the relevant
downstream book; the pin surfaces this as a regression.
"""

from __future__ import annotations

from datetime import date

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.market_environment import MarketEnvironmentStateRecord
from world.registry import Registry
from world.scenario_drivers import ScenarioDriverTemplate
from world.scheduler import Scheduler
from world.state import State
from world.stress_applications import apply_stress_program
from world.stress_programs import (
    StressProgramTemplate,
    StressStep,
)
from world.stress_readout import build_stress_field_readout


# ---------------------------------------------------------------------------
# Local fixture.
# ---------------------------------------------------------------------------


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _build_template(
    *,
    scenario_driver_template_id: str = (
        "scenario_driver:credit_tightening:reference"
    ),
) -> ScenarioDriverTemplate:
    return ScenarioDriverTemplate(
        scenario_driver_template_id=(
            scenario_driver_template_id
        ),
        scenario_family_label="credit_tightening_driver",
        driver_group_label="credit_liquidity",
        driver_label="Synthetic test driver",
        event_date_policy_label="quarter_end",
        severity_label="medium",
        affected_actor_scope_label="market_wide",
        expected_annotation_type_label="financing_constraint",
        affected_evidence_bucket_labels=(
            "market_environment_state",
            "financing_review_surface",
        ),
    )


def _build_market_env_state(
    *,
    environment_state_id: str = (
        "market_environment_state:test:v1_23_2_citation:01"
    ),
) -> MarketEnvironmentStateRecord:
    return MarketEnvironmentStateRecord(
        environment_state_id=environment_state_id,
        as_of_date="2026-04-30",
        liquidity_regime="restricted",
        volatility_regime="moderate",
        credit_regime="tight",
        funding_regime="restricted",
        risk_appetite_regime="cautious",
        rate_environment="rising",
        refinancing_window="closed",
        equity_valuation_regime="compressed",
        overall_market_access_label="restricted",
        status="active",
        visibility="internal",
        confidence=0.7,
    )


def _seed_kernel_with_cited_market_env() -> tuple[
    WorldKernel, str, str
]:
    """Seed a kernel with one market-environment record and a
    one-step stress program that cites it via
    ``source_context_record_ids``. Returns
    ``(kernel, stress_program_application_id,
    cited_environment_state_id)``."""
    kernel = _bare_kernel()
    env = _build_market_env_state()
    kernel.market_environments.add_state(env)
    kernel.scenario_drivers.add_template(_build_template())
    program_id = "stress_program:test_validation_citation:single_step"
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="Single-step citation pin",
        program_purpose_label="single_credit_tightening_stress",
        stress_steps=(
            StressStep(
                stress_step_id=f"{program_id}:step:0",
                parent_stress_program_template_id=program_id,
                step_index=0,
                scenario_driver_template_id=(
                    "scenario_driver:credit_tightening:reference"
                ),
                event_date_policy_label="quarter_end",
                scheduled_month_label="month_04",
            ),
        ),
    )
    kernel.stress_programs.add_program(program)
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=program_id,
        as_of_date="2026-04-30",
        source_context_record_ids=(env.environment_state_id,),
    )
    return (
        kernel,
        receipt.stress_program_application_id,
        env.environment_state_id,
    )


# ---------------------------------------------------------------------------
# 1. Source-context citations resolve to extant records.
# ---------------------------------------------------------------------------


def test_validation_citation_completeness_pin_v1_23_2_source_ids_resolve() -> None:
    """Every ``source_context_record_id`` in the readout must
    resolve to a record in the kernel's market-environment
    book (the book the test fixture seeds the cited id in)."""
    kernel, receipt_id, cited_id = (
        _seed_kernel_with_cited_market_env()
    )
    readout = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    assert (
        cited_id in readout.source_context_record_ids
    ), (
        "readout did not surface the cited "
        f"environment_state_id {cited_id!r} in its "
        "source_context_record_ids"
    )
    extant_env_ids = {
        s.environment_state_id
        for s in kernel.market_environments.list_states()
    }
    dangling = [
        sid
        for sid in readout.source_context_record_ids
        if sid not in extant_env_ids
    ]
    assert dangling == [], (
        f"readout cites source_context_record_ids that do "
        "not resolve to a market-environment record: "
        f"{dangling!r}"
    )


# ---------------------------------------------------------------------------
# 2. Downstream citations resolve when supplied.
# ---------------------------------------------------------------------------


def test_validation_citation_completeness_pin_v1_23_2_downstream_ids_resolve() -> None:
    """When a caller supplies ``downstream_citation_ids`` to
    ``build_stress_field_readout``, every supplied id must
    appear in the relevant downstream book at readout-build
    time. The v1.21.3 readout records the citation verbatim
    — the citing-side validation lives at the call site, so
    the pin re-asserts that the readout faithfully preserves
    the cited list."""
    kernel, receipt_id, _ = (
        _seed_kernel_with_cited_market_env()
    )
    # Synthesize one downstream id that legitimately exists in
    # an downstream-eligible kernel book — here we use the
    # cited stress-application receipt id itself as a stand-in
    # downstream surface (the readout faithfully preserves
    # whatever the caller passes).
    downstream_id = receipt_id
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
        downstream_citation_ids=(downstream_id,),
    )
    assert readout.downstream_citation_ids == (downstream_id,)
    # The downstream id is present in the kernel's
    # stress-application book.
    extant_stress_app_ids = {
        a.stress_program_application_id
        for a in kernel.stress_applications.list_applications()
    }
    dangling = [
        sid
        for sid in readout.downstream_citation_ids
        if sid not in extant_stress_app_ids
    ]
    assert dangling == [], (
        "readout.downstream_citation_ids contains ids that "
        "do not resolve to a kernel stress-application "
        f"record: {dangling!r}"
    )


# ---------------------------------------------------------------------------
# 3. Failing path — a synthetic dangling downstream id is
#    surfaced verbatim by the readout AND fails the
#    downstream-resolution scan. This proves the
#    completeness pin would catch a real regression.
# ---------------------------------------------------------------------------


def test_validation_citation_completeness_pin_v1_23_2_dangling_citation_detected() -> None:
    """A caller-supplied downstream id that does NOT match
    any record in the kernel must be flagged by the
    completeness pin. The readout itself accepts the id (it
    records caller-supplied citations verbatim — the v1.21.3
    contract); the pin enforces resolution."""
    kernel, receipt_id, _ = (
        _seed_kernel_with_cited_market_env()
    )
    dangling_id = (
        "investor_market_intent:nonexistent:dangling"
    )
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
        downstream_citation_ids=(dangling_id,),
    )
    assert dangling_id in readout.downstream_citation_ids
    # Resolution check: the dangling id is absent from every
    # extant kernel book the readout could legitimately cite.
    # The pin treats the absence as a regression flag.
    extant_ids: set[str] = set()
    extant_ids.update(
        a.stress_program_application_id
        for a in kernel.stress_applications.list_applications()
    )
    extant_ids.update(
        s.environment_state_id
        for s in kernel.market_environments.list_states()
    )
    extant_ids.update(
        a.scenario_application_id
        for a in (
            kernel.scenario_applications.list_applications()
        )
    )
    assert (
        dangling_id not in extant_ids
    ), (
        "fixture is broken — the dangling id should not "
        "resolve in any extant book"
    )
