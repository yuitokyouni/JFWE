"""
v1.27.2 — Strategic relationship readout + export pin tests.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.strategic_relationship_export import (
    STRATEGIC_RELATIONSHIP_READOUT_EXPORT_REQUIRED_KEYS,
    build_strategic_relationship_readout_export_section,
    strategic_relationship_readout_to_export_entry,
)
from world.strategic_relationship_readout import (
    StrategicRelationshipReadout,
    build_strategic_relationship_readout,
)
from world.strategic_relationships import (
    StrategicRelationshipRecord,
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


def _rel(
    *,
    relationship_id: str = "rel:test",
    source_entity_id: str = "firm:a",
    target_entity_id: str = "firm:b",
    relationship_type_label: str = "strategic_holding_like",
    direction_label: str = "directed",
    effective_from_period_id: str = "2026-Q1",
    effective_to_period_id: str | None = None,
    evidence_ref_ids: tuple[str, ...] = (),
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
    )


def test_readout_empty_book_returns_zero_counts() -> None:
    kernel = _bare_kernel()
    readout = build_strategic_relationship_readout(
        kernel, as_of_period_id="2026-Q2"
    )
    assert isinstance(readout, StrategicRelationshipReadout)
    assert readout.active_relationship_count == 0
    assert readout.relationship_ids == ()
    assert readout.entity_ids == ()
    assert readout.relationship_type_counts == ()
    assert readout.direction_counts == ()
    assert readout.reciprocal_relationship_count == 0


def test_readout_active_set_uses_period_window() -> None:
    kernel = _bare_kernel()
    # Active throughout
    kernel.strategic_relationships.add_relationship(
        _rel(
            relationship_id="rel:active",
            effective_from_period_id="2025-Q1",
            effective_to_period_id=None,
        )
    )
    # Already-ended
    kernel.strategic_relationships.add_relationship(
        _rel(
            relationship_id="rel:ended",
            effective_from_period_id="2024-Q1",
            effective_to_period_id="2025-Q4",
        )
    )
    # Not-yet-started
    kernel.strategic_relationships.add_relationship(
        _rel(
            relationship_id="rel:future",
            effective_from_period_id="2027-Q1",
        )
    )
    readout = build_strategic_relationship_readout(
        kernel, as_of_period_id="2026-Q2"
    )
    assert readout.active_relationship_count == 1
    assert readout.relationship_ids == ("rel:active",)


def test_readout_counts_relationship_types_and_directions() -> None:
    kernel = _bare_kernel()
    for i, (rt, dr) in enumerate(
        [
            ("strategic_holding_like", "reciprocal"),
            ("strategic_holding_like", "directed"),
            ("supplier_customer_like", "directed"),
            ("group_affiliation_like", "reciprocal"),
        ]
    ):
        kernel.strategic_relationships.add_relationship(
            _rel(
                relationship_id=f"rel:{i}",
                source_entity_id=f"firm:s{i}",
                target_entity_id=f"firm:t{i}",
                relationship_type_label=rt,
                direction_label=dr,
            )
        )
    readout = build_strategic_relationship_readout(
        kernel, as_of_period_id="2026-Q2"
    )
    type_dict = dict(readout.relationship_type_counts)
    assert type_dict["strategic_holding_like"] == 2
    assert type_dict["supplier_customer_like"] == 1
    assert type_dict["group_affiliation_like"] == 1
    direction_dict = dict(readout.direction_counts)
    assert direction_dict["directed"] == 2
    assert direction_dict["reciprocal"] == 2
    assert readout.reciprocal_relationship_count == 2


def test_readout_aggregates_distinct_entities_and_evidence() -> None:
    kernel = _bare_kernel()
    kernel.strategic_relationships.add_relationship(
        _rel(
            relationship_id="rel:1",
            source_entity_id="firm:a",
            target_entity_id="firm:b",
            evidence_ref_ids=(
                "manual_annotation:x",
                "manual_annotation:y",
            ),
        )
    )
    kernel.strategic_relationships.add_relationship(
        _rel(
            relationship_id="rel:2",
            source_entity_id="firm:b",
            target_entity_id="firm:c",
            evidence_ref_ids=("manual_annotation:y",),
        )
    )
    readout = build_strategic_relationship_readout(
        kernel, as_of_period_id="2026-Q2"
    )
    assert readout.entity_ids == (
        "firm:a", "firm:b", "firm:c",
    )
    assert readout.evidence_ref_ids == (
        "manual_annotation:x",
        "manual_annotation:y",
    )


def test_readout_warnings_on_unknown_labels() -> None:
    kernel = _bare_kernel()
    kernel.strategic_relationships.add_relationship(
        _rel(
            relationship_id="rel:u",
            relationship_type_label="unknown",
            direction_label="unknown",
        )
    )
    readout = build_strategic_relationship_readout(
        kernel, as_of_period_id="2026-Q2"
    )
    assert any(
        "unknown_relationship_type_label" in w
        for w in readout.warnings
    )
    assert any(
        "unknown_direction_label" in w
        for w in readout.warnings
    )


def test_readout_does_not_mutate_kernel_state() -> None:
    kernel = _bare_kernel()
    kernel.strategic_relationships.add_relationship(_rel())
    snap_before = {
        "ledger_records": len(kernel.ledger.records),
        "strategic_relationships": (
            kernel.strategic_relationships.snapshot()
        ),
        "scenario_drivers": (
            kernel.scenario_drivers.snapshot()
        ),
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
    }
    build_strategic_relationship_readout(
        kernel, as_of_period_id="2026-Q2"
    )
    snap_after = {
        "ledger_records": len(kernel.ledger.records),
        "strategic_relationships": (
            kernel.strategic_relationships.snapshot()
        ),
        "scenario_drivers": (
            kernel.scenario_drivers.snapshot()
        ),
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
    }
    assert snap_before == snap_after


def test_export_section_empty_book_returns_empty_tuple() -> None:
    kernel = _bare_kernel()
    section = (
        build_strategic_relationship_readout_export_section(
            kernel, as_of_period_id="2026-Q2"
        )
    )
    assert section == ()


def test_export_entry_keys_match_required_set() -> None:
    kernel = _bare_kernel()
    kernel.strategic_relationships.add_relationship(_rel())
    section = (
        build_strategic_relationship_readout_export_section(
            kernel, as_of_period_id="2026-Q2"
        )
    )
    assert len(section) == 1
    entry = section[0]
    assert (
        STRATEGIC_RELATIONSHIP_READOUT_EXPORT_REQUIRED_KEYS
        <= entry.keys()
    )
    assert entry["active_relationship_count"] == 1
    assert entry["reciprocal_relationship_count"] == 0


def test_export_entry_rejects_forbidden_value_via_to_export_entry() -> None:
    # Build a "tainted" readout via direct dataclass
    # construction with a forbidden token in metadata.
    with pytest.raises(ValueError):
        StrategicRelationshipReadout(
            readout_id="r",
            as_of_period_id="2026-Q2",
            relationship_ids=(),
            entity_ids=(),
            relationship_type_counts=(),
            direction_counts=(),
            reciprocal_relationship_count=0,
            active_relationship_count=0,
            evidence_ref_ids=(),
            metadata={"ownership_percentage": "x"},
        )


def test_run_export_bundle_omits_strategic_relationship_readout_when_empty() -> None:
    from world.run_export import build_run_export_bundle

    bundle = build_run_export_bundle(
        bundle_id="b",
        run_profile_label="quarterly_default",
        regime_label="baseline",
        period_count=1,
        digest="d" * 64,
    )
    out = bundle.to_dict()
    assert "strategic_relationship_readout" not in out


def test_run_export_bundle_carries_strategic_relationship_readout_when_present() -> None:
    from world.run_export import build_run_export_bundle

    kernel = _bare_kernel()
    kernel.strategic_relationships.add_relationship(_rel())
    section = (
        build_strategic_relationship_readout_export_section(
            kernel, as_of_period_id="2026-Q2"
        )
    )
    bundle = build_run_export_bundle(
        bundle_id="b",
        run_profile_label="quarterly_default",
        regime_label="baseline",
        period_count=1,
        digest="d" * 64,
        strategic_relationship_readout=section,
    )
    out = bundle.to_dict()
    assert "strategic_relationship_readout" in out
    assert out["strategic_relationship_readout"][0][
        "active_relationship_count"
    ] == 1


def test_strategic_relationship_readout_to_export_entry_type_check() -> None:
    with pytest.raises(TypeError):
        strategic_relationship_readout_to_export_entry(
            "not a readout"
        )


def test_existing_digests_unchanged_with_v1_27_2_readout_module_imported() -> None:
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
        living_world_digest(k_q, r_q)
        == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST
    )

    k_m = _seed_kernel()
    r_m = _run_monthly_reference(k_m)
    assert (
        living_world_digest(k_m, r_m)
        == MONTHLY_REFERENCE_LIVING_WORLD_DIGEST
    )

    k_s = _seed_v1_20_3_kernel()
    r_s = _run_v1_20_3(k_s)
    assert (
        living_world_digest(k_s, r_s)
        == SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST
    )
