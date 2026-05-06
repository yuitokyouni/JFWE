"""
v1.27.1 — StrategicRelationship storage pin tests.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES,
)
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.strategic_relationships import (
    DIRECTION_LABELS,
    DuplicateStrategicRelationshipError,
    RELATIONSHIP_TYPE_LABELS,
    StrategicRelationshipBook,
    StrategicRelationshipRecord,
    UnknownStrategicRelationshipError,
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


def _relationship(
    *,
    relationship_id: str = "rel:test:01",
    source_entity_id: str = "firm:a",
    target_entity_id: str = "firm:b",
    relationship_type_label: str = "strategic_holding_like",
    direction_label: str = "directed",
    effective_from_period_id: str = "2026-Q1",
    effective_to_period_id: str | None = None,
    evidence_ref_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> StrategicRelationshipRecord:
    return StrategicRelationshipRecord(
        relationship_id=relationship_id,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        relationship_type_label=relationship_type_label,
        direction_label=direction_label,
        effective_from_period_id=effective_from_period_id,
        effective_to_period_id=effective_to_period_id,
        evidence_ref_ids=evidence_ref_ids,
        metadata=metadata or {},
    )


def test_strategic_relationship_record_validates_required_fields() -> None:
    r = _relationship()
    assert r.relationship_id == "rel:test:01"
    with pytest.raises(ValueError):
        _relationship(relationship_id="")
    with pytest.raises(ValueError):
        _relationship(source_entity_id="")
    with pytest.raises(ValueError):
        _relationship(target_entity_id="")
    with pytest.raises(ValueError):
        _relationship(effective_from_period_id="")
    # Default boundary flags include v1.27-specific anti-claim
    # flags.
    for flag in (
        "no_ownership_percentage",
        "no_voting_power",
        "no_market_value",
        "no_centrality_score",
        "no_real_company_relationship",
    ):
        assert r.boundary_flags[flag] is True


def test_strategic_relationship_record_validates_relationship_type_label() -> None:
    for forbidden in (
        "majority_owner",
        "controlling_shareholder",
        "subsidiary",
        "parent_company",
    ):
        with pytest.raises(ValueError):
            _relationship(relationship_type_label=forbidden)
    # Every label in the closed set is accepted.
    for label in RELATIONSHIP_TYPE_LABELS:
        if label == "unknown":
            continue
        rec = _relationship(
            relationship_id=f"rel:test:{label}",
            relationship_type_label=label,
        )
        assert rec.relationship_type_label == label


def test_strategic_relationship_record_validates_direction_label() -> None:
    for forbidden in ("forward", "backward", "asymmetric"):
        with pytest.raises(ValueError):
            _relationship(direction_label=forbidden)
    for label in DIRECTION_LABELS:
        if label == "unknown":
            continue
        rec = _relationship(
            relationship_id=f"rel:test:dir:{label}",
            direction_label=label,
        )
        assert rec.direction_label == label


def test_strategic_relationship_record_rejects_inverted_period_range() -> None:
    with pytest.raises(ValueError):
        _relationship(
            effective_from_period_id="2026-Q4",
            effective_to_period_id="2026-Q1",
        )
    # Equal endpoints are allowed (single-period
    # relationship).
    r = _relationship(
        effective_from_period_id="2026-Q2",
        effective_to_period_id="2026-Q2",
    )
    assert r.effective_to_period_id == "2026-Q2"


def test_strategic_relationship_record_rejects_forbidden_field_names() -> None:
    from dataclasses import fields as dc_fields
    field_names = {
        f.name
        for f in dc_fields(StrategicRelationshipRecord)
    }
    overlap = (
        field_names
        & FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES
    )
    assert overlap == set()


def test_strategic_relationship_record_rejects_forbidden_metadata_keys() -> None:
    for forbidden_key in (
        "ownership_percentage",
        "voting_power",
        "fair_value",
        "centrality_score",
        "systemic_importance_score",
        "edgar_filing",
        "tepco_holding",
        "edinet_filing_id",
        "buy",
        "forecast",
        "alpha",
        "japan_calibration",
        "amplify",
    ):
        with pytest.raises(ValueError):
            _relationship(metadata={forbidden_key: "x"})


def test_strategic_relationship_book_add_get_list_snapshot() -> None:
    book = StrategicRelationshipBook()
    a = _relationship(
        relationship_id="rel:a",
        relationship_type_label="strategic_holding_like",
        direction_label="directed",
    )
    b = _relationship(
        relationship_id="rel:b",
        relationship_type_label="supplier_customer_like",
        direction_label="reciprocal",
    )
    book.add_relationship(a)
    book.add_relationship(b)
    assert book.get_relationship("rel:a") is a
    assert len(book.list_relationships()) == 2
    assert book.list_by_relationship_type(
        "strategic_holding_like"
    ) == (a,)
    assert book.list_by_direction("reciprocal") == (b,)
    assert book.list_by_effective_period("2026-Q1") == (
        a, b,
    )
    snap = book.snapshot()
    assert "strategic_relationships" in snap
    assert len(snap["strategic_relationships"]) == 2
    with pytest.raises(UnknownStrategicRelationshipError):
        book.get_relationship("rel:nonexistent")


def test_strategic_relationship_book_list_by_entity_includes_source_and_target() -> None:
    book = StrategicRelationshipBook()
    e1 = _relationship(
        relationship_id="rel:1",
        source_entity_id="firm:a",
        target_entity_id="firm:b",
    )
    e2 = _relationship(
        relationship_id="rel:2",
        source_entity_id="firm:c",
        target_entity_id="firm:a",
    )
    book.add_relationship(e1)
    book.add_relationship(e2)
    # firm:a is in source of rel:1 and target of rel:2
    assert {
        r.relationship_id
        for r in book.list_by_entity("firm:a")
    } == {"rel:1", "rel:2"}
    assert {
        r.relationship_id
        for r in book.list_by_entity("firm:b")
    } == {"rel:1"}
    assert book.list_by_entity("firm:nonexistent") == ()


def test_duplicate_strategic_relationship_emits_no_extra_ledger_record() -> None:
    kernel = _bare_kernel()
    r = _relationship()
    kernel.strategic_relationships.add_relationship(r)
    n = len(kernel.ledger.records)
    assert n >= 1
    assert (
        kernel.ledger.records[-1].event_type
        == RecordType.STRATEGIC_RELATIONSHIP_RECORDED.value
    )
    with pytest.raises(
        DuplicateStrategicRelationshipError
    ):
        kernel.strategic_relationships.add_relationship(r)
    assert len(kernel.ledger.records) == n


def test_strategic_relationship_storage_does_not_mutate_source_of_truth_books() -> None:
    kernel = _bare_kernel()
    snap_before = {
        "scenario_drivers": kernel.scenario_drivers.snapshot(),
        "scenario_applications": kernel.scenario_applications.snapshot(),
        "stress_applications": kernel.stress_applications.snapshot(),
        "manual_annotations": kernel.manual_annotations.snapshot(),
        "investor_mandates": kernel.investor_mandates.snapshot(),
        "universe_events": kernel.universe_events.snapshot(),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
        "constraints": kernel.constraints.snapshot(),
    }
    kernel.strategic_relationships.add_relationship(
        _relationship()
    )
    snap_after = {
        "scenario_drivers": kernel.scenario_drivers.snapshot(),
        "scenario_applications": kernel.scenario_applications.snapshot(),
        "stress_applications": kernel.stress_applications.snapshot(),
        "manual_annotations": kernel.manual_annotations.snapshot(),
        "investor_mandates": kernel.investor_mandates.snapshot(),
        "universe_events": kernel.universe_events.snapshot(),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
        "constraints": kernel.constraints.snapshot(),
    }
    assert snap_before == snap_after


def test_world_kernel_strategic_relationships_empty_by_default() -> None:
    kernel = _bare_kernel()
    assert (
        kernel.strategic_relationships.list_relationships()
        == ()
    )
    types = {r.event_type for r in kernel.ledger.records}
    assert (
        RecordType.STRATEGIC_RELATIONSHIP_RECORDED.value
        not in types
    )


def test_strategic_relationship_storage_does_not_call_apply_or_intent_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import world.scenario_applications as sa
    import world.stress_applications as sap

    def _forbid(*a, **kw):
        raise AssertionError("forbidden helper called")

    monkeypatch.setattr(sap, "apply_stress_program", _forbid)
    monkeypatch.setattr(sa, "apply_scenario_driver", _forbid)
    kernel = _bare_kernel()
    kernel.strategic_relationships.add_relationship(
        _relationship()
    )
    assert (
        len(
            kernel.strategic_relationships.list_relationships()
        )
        == 1
    )


def test_existing_digests_unchanged_with_empty_strategic_relationship_book() -> None:
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
    assert (
        k_q.strategic_relationships.list_relationships()
        == ()
    )
    assert (
        living_world_digest(k_q, r_q)
        == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST
    )

    k_m = _seed_kernel()
    r_m = _run_monthly_reference(k_m)
    assert (
        k_m.strategic_relationships.list_relationships()
        == ()
    )
    assert (
        living_world_digest(k_m, r_m)
        == MONTHLY_REFERENCE_LIVING_WORLD_DIGEST
    )

    k_s = _seed_v1_20_3_kernel()
    r_s = _run_v1_20_3(k_s)
    assert (
        k_s.strategic_relationships.list_relationships()
        == ()
    )
    assert (
        living_world_digest(k_s, r_s)
        == SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST
    )
