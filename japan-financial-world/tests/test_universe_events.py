"""
v1.26.1 — UniverseEvent storage pin tests.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES,
)
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.universe_events import (
    DuplicateUniverseEventError,
    UNIVERSE_EVENT_TYPE_LABELS,
    UniverseEventBook,
    UniverseEventRecord,
)

from _canonical_digests import (
    MONTHLY_REFERENCE_LIVING_WORLD_DIGEST,
    QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
    SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST,
)


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _event(
    *,
    universe_event_id: str = "universe_event:test:01",
    effective_period_id: str = "2026-Q2",
    event_type_label: str = "entity_listed",
    affected_entity_ids: tuple[str, ...] = ("firm:a",),
    predecessor_entity_ids: tuple[str, ...] = (),
    successor_entity_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> UniverseEventRecord:
    return UniverseEventRecord(
        universe_event_id=universe_event_id,
        effective_period_id=effective_period_id,
        event_type_label=event_type_label,
        affected_entity_ids=affected_entity_ids,
        predecessor_entity_ids=predecessor_entity_ids,
        successor_entity_ids=successor_entity_ids,
        metadata=metadata or {},
    )


def test_universe_event_record_validates_required_fields() -> None:
    e = _event()
    assert e.universe_event_id == "universe_event:test:01"
    with pytest.raises(ValueError):
        _event(universe_event_id="")
    with pytest.raises(ValueError):
        _event(effective_period_id="")
    # Default boundary flags include v1.26-specific anti-claim
    # flags.
    for flag in (
        "no_real_data_ingestion",
        "no_japan_calibration",
        "no_real_company_name",
        "no_event_to_price_mapping",
        "no_market_effect_inference",
        "no_forecast_from_calendar",
    ):
        assert e.boundary_flags[flag] is True


def test_universe_event_record_validates_event_type_label() -> None:
    for forbidden in (
        "entity_acquired", "ipo", "spinoff", "buyout"
    ):
        with pytest.raises(ValueError):
            _event(event_type_label=forbidden)
    # Every label in the closed set is accepted.
    for label in UNIVERSE_EVENT_TYPE_LABELS:
        if label == "unknown":
            continue
        rec = _event(
            universe_event_id=f"ue:test:{label}",
            event_type_label=label,
        )
        assert rec.event_type_label == label


def test_universe_event_record_rejects_empty_affected_entity_ids() -> None:
    with pytest.raises(ValueError):
        _event(affected_entity_ids=())
    with pytest.raises(ValueError):
        _event(affected_entity_ids=("",))


def test_universe_event_record_rejects_forbidden_field_names() -> None:
    from dataclasses import fields as dc_fields
    field_names = {
        f.name for f in dc_fields(UniverseEventRecord)
    }
    overlap = (
        field_names
        & FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES
    )
    assert overlap == set()


def test_universe_event_record_rejects_forbidden_metadata_keys() -> None:
    for forbidden_key in (
        "earnings_surprise",
        "edinet_filing_id",
        "universe_weight",
        "rebalance_event",
        "buy",
        "forecast",
        "alpha",
        "japan_calibration",
        "amplify",
    ):
        with pytest.raises(ValueError):
            _event(metadata={forbidden_key: "x"})


def test_universe_event_book_add_get_list_snapshot() -> None:
    book = UniverseEventBook()
    a = _event(universe_event_id="ue:a", event_type_label="entity_listed", affected_entity_ids=("firm:a",))
    b = _event(universe_event_id="ue:b", event_type_label="entity_delisted", affected_entity_ids=("firm:b",))
    book.add_event(a)
    book.add_event(b)
    assert book.get_event("ue:a") is a
    assert len(book.list_events()) == 2
    assert book.list_by_event_type("entity_listed") == (a,)
    assert book.list_by_event_type("entity_delisted") == (b,)
    assert book.list_by_effective_period("2026-Q2") == (a, b)
    snap = book.snapshot()
    assert "universe_events" in snap
    assert len(snap["universe_events"]) == 2


def test_universe_event_book_list_by_entity_includes_predecessor_and_successor() -> None:
    book = UniverseEventBook()
    e1 = _event(
        universe_event_id="ue:1",
        event_type_label="entity_merged",
        affected_entity_ids=("firm:successor",),
        predecessor_entity_ids=("firm:old_a", "firm:old_b"),
        successor_entity_ids=("firm:successor",),
    )
    book.add_event(e1)
    # Affected
    assert {e.universe_event_id for e in book.list_by_entity("firm:successor")} == {"ue:1"}
    # Predecessor
    assert {e.universe_event_id for e in book.list_by_entity("firm:old_a")} == {"ue:1"}
    assert {e.universe_event_id for e in book.list_by_entity("firm:old_b")} == {"ue:1"}
    # Unrelated
    assert book.list_by_entity("firm:nonexistent") == ()


def test_duplicate_universe_event_emits_no_extra_ledger_record() -> None:
    kernel = _bare_kernel()
    e = _event()
    kernel.universe_events.add_event(e)
    n = len(kernel.ledger.records)
    assert n >= 1
    assert kernel.ledger.records[-1].event_type == RecordType.UNIVERSE_EVENT_RECORDED.value
    with pytest.raises(DuplicateUniverseEventError):
        kernel.universe_events.add_event(e)
    assert len(kernel.ledger.records) == n


def test_universe_event_storage_does_not_mutate_source_of_truth_books() -> None:
    kernel = _bare_kernel()
    snap_before = {
        "scenario_drivers": kernel.scenario_drivers.snapshot(),
        "scenario_applications": kernel.scenario_applications.snapshot(),
        "stress_applications": kernel.stress_applications.snapshot(),
        "manual_annotations": kernel.manual_annotations.snapshot(),
        "investor_mandates": kernel.investor_mandates.snapshot(),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
        "constraints": kernel.constraints.snapshot(),
    }
    kernel.universe_events.add_event(_event())
    snap_after = {
        "scenario_drivers": kernel.scenario_drivers.snapshot(),
        "scenario_applications": kernel.scenario_applications.snapshot(),
        "stress_applications": kernel.stress_applications.snapshot(),
        "manual_annotations": kernel.manual_annotations.snapshot(),
        "investor_mandates": kernel.investor_mandates.snapshot(),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
        "constraints": kernel.constraints.snapshot(),
    }
    assert snap_before == snap_after


def test_world_kernel_universe_events_empty_by_default() -> None:
    kernel = _bare_kernel()
    assert kernel.universe_events.list_events() == ()
    types = {r.event_type for r in kernel.ledger.records}
    assert RecordType.UNIVERSE_EVENT_RECORDED.value not in types


def test_universe_event_storage_does_not_call_apply_or_intent_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import world.scenario_applications as sa
    import world.stress_applications as sap

    def _forbid(*a, **kw):
        raise AssertionError("forbidden helper called")

    monkeypatch.setattr(sap, "apply_stress_program", _forbid)
    monkeypatch.setattr(sa, "apply_scenario_driver", _forbid)
    kernel = _bare_kernel()
    kernel.universe_events.add_event(_event())
    assert len(kernel.universe_events.list_events()) == 1


def test_existing_digests_unchanged_with_empty_universe_event_book() -> None:
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (
        _run_default,
        _run_monthly_reference,
        _seed_kernel,
    )
    from test_living_reference_world_performance_boundary import (
        _run_v1_20_3,
        _seed_v1_20_3_kernel,
    )

    k_q = _seed_kernel()
    r_q = _run_default(k_q)
    assert k_q.universe_events.list_events() == ()
    assert living_world_digest(k_q, r_q) == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST

    k_m = _seed_kernel()
    r_m = _run_monthly_reference(k_m)
    assert k_m.universe_events.list_events() == ()
    assert living_world_digest(k_m, r_m) == MONTHLY_REFERENCE_LIVING_WORLD_DIGEST

    k_s = _seed_v1_20_3_kernel()
    r_s = _run_v1_20_3(k_s)
    assert k_s.universe_events.list_events() == ()
    assert living_world_digest(k_s, r_s) == SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST
