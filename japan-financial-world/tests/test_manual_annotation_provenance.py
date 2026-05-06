"""
v1.27.3 — Manual annotation provenance pin tests.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_ANNOTATION_PROVENANCE_FIELD_NAMES,
)
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.manual_annotation_provenance import (
    AUTHORITY_LABELS,
    DuplicateManualAnnotationProvenanceError,
    EVIDENCE_ACCESS_SCOPE_LABELS,
    ManualAnnotationProvenanceBook,
    ManualAnnotationProvenanceRecord,
    UnknownManualAnnotationProvenanceError,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State

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


def _provenance(
    *,
    provenance_id: str = "prov:test:01",
    annotation_id: str = "manual_annotation:x",
    annotator_id_label: str = "reviewer_lead_a",
    reviewer_role_label: str = "reviewer",
    authority_label: str = "self_review",
    evidence_access_scope_label: str = "public_synthetic",
    audit_period_id: str = "2026-Q2",
    authorization_ref_id: str | None = None,
    review_context_id: str | None = None,
    metadata: dict | None = None,
) -> ManualAnnotationProvenanceRecord:
    return ManualAnnotationProvenanceRecord(
        provenance_id=provenance_id,
        annotation_id=annotation_id,
        annotator_id_label=annotator_id_label,
        reviewer_role_label=reviewer_role_label,
        authority_label=authority_label,
        evidence_access_scope_label=(
            evidence_access_scope_label
        ),
        audit_period_id=audit_period_id,
        authorization_ref_id=authorization_ref_id,
        review_context_id=review_context_id,
        metadata=metadata or {},
    )


def test_provenance_record_validates_required_fields() -> None:
    p = _provenance()
    assert p.provenance_id == "prov:test:01"
    with pytest.raises(ValueError):
        _provenance(provenance_id="")
    with pytest.raises(ValueError):
        _provenance(annotation_id="")
    with pytest.raises(ValueError):
        _provenance(audit_period_id="")
    # Default boundary flags include v1.27.3 anti-claim flags.
    for flag in (
        "pseudonymous_only",
        "no_real_person_identity",
        "no_compliance_claim",
        "no_llm_authoring",
    ):
        assert p.boundary_flags[flag] is True


def test_provenance_record_validates_closed_set_labels() -> None:
    for forbidden in (
        "regulator_review",
        "third_party_audit",
        "external_attestation",
    ):
        with pytest.raises(ValueError):
            _provenance(authority_label=forbidden)
    for label in AUTHORITY_LABELS:
        if label == "unknown":
            continue
        rec = _provenance(
            provenance_id=f"prov:auth:{label}",
            authority_label=label,
        )
        assert rec.authority_label == label
    for forbidden in (
        "internal_real",
        "external_real",
        "live_data",
    ):
        with pytest.raises(ValueError):
            _provenance(
                evidence_access_scope_label=forbidden
            )
    for label in EVIDENCE_ACCESS_SCOPE_LABELS:
        if label == "unknown":
            continue
        rec = _provenance(
            provenance_id=f"prov:scope:{label}",
            evidence_access_scope_label=label,
        )
        assert rec.evidence_access_scope_label == label


def test_provenance_record_anti_email_leak_guard() -> None:
    # Any '@' in annotator_id_label is rejected.
    with pytest.raises(ValueError):
        _provenance(
            annotator_id_label="alice@example.com"
        )
    with pytest.raises(ValueError):
        _provenance(annotator_id_label="@reviewer")
    # Pseudonymous ids without @ are accepted.
    rec = _provenance(annotator_id_label="reviewer_lead_a")
    assert rec.annotator_id_label == "reviewer_lead_a"


def test_provenance_record_rejects_forbidden_field_names() -> None:
    from dataclasses import fields as dc_fields
    field_names = {
        f.name
        for f in dc_fields(ManualAnnotationProvenanceRecord)
    }
    overlap = (
        field_names
        & FORBIDDEN_ANNOTATION_PROVENANCE_FIELD_NAMES
    )
    assert overlap == set()


def test_provenance_record_rejects_forbidden_metadata_keys() -> None:
    for forbidden_key in (
        "real_person_name",
        "personal_email",
        "phone_number",
        "national_id",
        "employee_id",
        "soc2_compliance",
        "fisc_compliance",
        "iso27001_certified",
        "regulatory_attestation",
        # Inherited from earlier deltas
        "ownership_percentage",
        "centrality_score",
        "edinet_filing_id",
        "amplify",
        "japan_calibration",
    ):
        with pytest.raises(ValueError):
            _provenance(metadata={forbidden_key: "x"})


def test_provenance_book_add_get_list_snapshot() -> None:
    book = ManualAnnotationProvenanceBook()
    a = _provenance(
        provenance_id="prov:a",
        annotation_id="manual_annotation:1",
        authority_label="self_review",
        audit_period_id="2026-Q1",
    )
    b = _provenance(
        provenance_id="prov:b",
        annotation_id="manual_annotation:1",
        authority_label="supervisory_review",
        audit_period_id="2026-Q2",
    )
    book.add_provenance(a)
    book.add_provenance(b)
    assert book.get_provenance("prov:a") is a
    assert len(book.list_provenances()) == 2
    assert book.list_by_annotation(
        "manual_annotation:1"
    ) == (a, b)
    assert book.list_by_authority("supervisory_review") == (
        b,
    )
    assert book.list_by_audit_period("2026-Q1") == (a,)
    snap = book.snapshot()
    assert "manual_annotation_provenance" in snap
    assert len(snap["manual_annotation_provenance"]) == 2
    with pytest.raises(
        UnknownManualAnnotationProvenanceError
    ):
        book.get_provenance("prov:nonexistent")


def test_duplicate_provenance_emits_no_extra_ledger_record() -> None:
    kernel = _bare_kernel()
    p = _provenance()
    kernel.manual_annotation_provenance.add_provenance(p)
    n = len(kernel.ledger.records)
    assert n >= 1
    assert (
        kernel.ledger.records[-1].event_type
        == RecordType.MANUAL_ANNOTATION_PROVENANCE_RECORDED.value
    )
    with pytest.raises(
        DuplicateManualAnnotationProvenanceError
    ):
        kernel.manual_annotation_provenance.add_provenance(
            p
        )
    assert len(kernel.ledger.records) == n


def test_provenance_storage_does_not_mutate_manual_annotations_or_other_books() -> None:
    kernel = _bare_kernel()
    snap_before = {
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
        "scenario_drivers": (
            kernel.scenario_drivers.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "investor_mandates": (
            kernel.investor_mandates.snapshot()
        ),
        "universe_events": (
            kernel.universe_events.snapshot()
        ),
        "strategic_relationships": (
            kernel.strategic_relationships.snapshot()
        ),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
        "constraints": kernel.constraints.snapshot(),
    }
    kernel.manual_annotation_provenance.add_provenance(
        _provenance()
    )
    snap_after = {
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
        "scenario_drivers": (
            kernel.scenario_drivers.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "investor_mandates": (
            kernel.investor_mandates.snapshot()
        ),
        "universe_events": (
            kernel.universe_events.snapshot()
        ),
        "strategic_relationships": (
            kernel.strategic_relationships.snapshot()
        ),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
        "constraints": kernel.constraints.snapshot(),
    }
    assert snap_before == snap_after


def test_world_kernel_manual_annotation_provenance_empty_by_default() -> None:
    kernel = _bare_kernel()
    assert (
        kernel.manual_annotation_provenance.list_provenances()
        == ()
    )
    types = {r.event_type for r in kernel.ledger.records}
    assert (
        RecordType.MANUAL_ANNOTATION_PROVENANCE_RECORDED.value
        not in types
    )


def test_provenance_storage_does_not_call_apply_or_intent_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import world.scenario_applications as sa
    import world.stress_applications as sap

    def _forbid(*a, **kw):
        raise AssertionError("forbidden helper called")

    monkeypatch.setattr(
        sap, "apply_stress_program", _forbid
    )
    monkeypatch.setattr(
        sa, "apply_scenario_driver", _forbid
    )
    kernel = _bare_kernel()
    kernel.manual_annotation_provenance.add_provenance(
        _provenance()
    )
    assert (
        len(
            kernel.manual_annotation_provenance.list_provenances()
        )
        == 1
    )


def test_existing_digests_unchanged_with_empty_provenance_book() -> None:
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
        k_q.manual_annotation_provenance.list_provenances()
        == ()
    )
    assert (
        living_world_digest(k_q, r_q)
        == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST
    )

    k_m = _seed_kernel()
    r_m = _run_monthly_reference(k_m)
    assert (
        k_m.manual_annotation_provenance.list_provenances()
        == ()
    )
    assert (
        living_world_digest(k_m, r_m)
        == MONTHLY_REFERENCE_LIVING_WORLD_DIGEST
    )

    k_s = _seed_v1_20_3_kernel()
    r_s = _run_v1_20_3(k_s)
    assert (
        k_s.manual_annotation_provenance.list_provenances()
        == ()
    )
    assert (
        living_world_digest(k_s, r_s)
        == SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST
    )
