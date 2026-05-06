"""
v1.24.3 — Manual annotation export pin tests.

Pins ``world/manual_annotation_export.py`` and the
``RunExportBundle.manual_annotation_readout`` payload
section per the v1.24.0 design pin §17:

- the section is **omitted** from
  ``RunExportBundle.to_dict()`` when empty (so every
  v1.21.last canonical living-world digest stays byte-
  identical at v1.24.3);
- the section is **present** when the kernel carries
  manual annotations;
- the export keys are descriptive-only (the v1.24.3
  whitelist matches the pinned set);
- forbidden tokens are absent from any key + any whole-
  string value at any depth;
- unresolved citations are preserved verbatim from the
  v1.24.2 readout;
- the export helper does not emit a ledger record;
- the export helper does not mutate any kernel book.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES,
)
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.manual_annotation_export import (
    MANUAL_ANNOTATION_READOUT_EXPORT_REQUIRED_KEYS,
    build_manual_annotation_readout_export_section,
    manual_annotation_readout_to_export_entry,
)
from world.manual_annotation_readout import (
    build_manual_annotation_readout,
)
from world.manual_annotations import (
    ManualAnnotationRecord,
)
from world.registry import Registry
from world.run_export import (
    RunExportBundle,
    build_run_export_bundle,
    bundle_to_dict,
    bundle_to_json,
)
from world.scheduler import Scheduler
from world.state import State

from _canonical_digests import (
    QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
)


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _annotation(
    annotation_id: str = "manual_annotation:test:01",
    *,
    annotation_label: str = "same_review_frame",
    annotation_scope_label: str = "stress_readout",
    cited_record_ids: tuple[str, ...] = (
        "stress_field_readout:nonexistent",
    ),
) -> ManualAnnotationRecord:
    return ManualAnnotationRecord(
        annotation_id=annotation_id,
        annotation_scope_label=annotation_scope_label,
        annotation_label=annotation_label,
        cited_record_ids=cited_record_ids,
        reviewer_role_label="reviewer",
    )


def _basic_bundle(**kwargs) -> RunExportBundle:
    return build_run_export_bundle(
        bundle_id="run_bundle:v1_24_3:test",
        run_profile_label="quarterly_default",
        regime_label="constrained",
        period_count=4,
        digest=QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 1. Empty by default — section omitted from to_dict.
# ---------------------------------------------------------------------------


def test_export_omits_manual_annotation_readout_when_absent() -> None:
    """A bundle constructed without
    ``manual_annotation_readout`` defaults to an empty
    tuple; ``to_dict()`` omits the
    ``manual_annotation_readout`` key entirely. JSON
    serialisation likewise contains no
    ``manual_annotation_readout`` key."""
    b = _basic_bundle()
    d = bundle_to_dict(b)
    assert "manual_annotation_readout" not in d
    j = bundle_to_json(b)
    assert "manual_annotation_readout" not in j
    # Bundle's underlying field is the empty tuple.
    assert b.manual_annotation_readout == ()


# ---------------------------------------------------------------------------
# 2. Existing no-annotation bundle digests unchanged.
# ---------------------------------------------------------------------------


def test_existing_no_annotation_bundle_digest_unchanged() -> None:
    """A bundle constructed with the v1.21.last canonical
    digest as its ``digest`` field must still serialise
    without a ``manual_annotation_readout`` key. The
    actual living-world digest preservation is pinned by
    the v1.24.1 ``test_existing_digests_unchanged_with_empty_annotation_book``
    test; this test re-asserts the export-side
    omission rule."""
    b = _basic_bundle()
    d = bundle_to_dict(b)
    assert d["digest"] == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST
    assert "manual_annotation_readout" not in d


# ---------------------------------------------------------------------------
# 3. Section is present when annotations exist.
# ---------------------------------------------------------------------------


def test_export_includes_manual_annotation_readout_when_present() -> None:
    """A bundle constructed with a non-empty
    ``manual_annotation_readout`` exposes the section in
    ``to_dict()`` output. The section entry preserves the
    readout's plain-id citations + count lists verbatim."""
    kernel = _bare_kernel()
    kernel.manual_annotations.add_annotation(
        _annotation("manual_annotation:test:a")
    )
    kernel.manual_annotations.add_annotation(
        _annotation(
            "manual_annotation:test:b",
            annotation_label="citation_gap_note",
            annotation_scope_label="case_study",
        )
    )
    section = build_manual_annotation_readout_export_section(
        kernel
    )
    assert len(section) == 1
    b = _basic_bundle(manual_annotation_readout=section)
    d = bundle_to_dict(b)
    assert "manual_annotation_readout" in d
    assert len(d["manual_annotation_readout"]) == 1
    entry = d["manual_annotation_readout"][0]
    assert (
        entry["annotation_ids"]
        == [
            "manual_annotation:test:a",
            "manual_annotation:test:b",
        ]
    )
    label_counts = dict(
        (k, v) for k, v in entry["annotation_label_counts"]
    )
    assert label_counts == {
        "same_review_frame": 1,
        "citation_gap_note": 1,
    }


# ---------------------------------------------------------------------------
# 4. Export keys are descriptive-only (whitelist).
# ---------------------------------------------------------------------------


def test_export_keys_are_descriptive_only() -> None:
    """The export entry's top-level keys exactly match
    the v1.24.3 descriptive-only whitelist (no
    ``metadata`` / ``boundary_flags`` / ``note_text`` /
    free-form caller fields)."""
    kernel = _bare_kernel()
    kernel.manual_annotations.add_annotation(_annotation())
    readout = build_manual_annotation_readout(kernel)
    entry = manual_annotation_readout_to_export_entry(readout)
    assert (
        set(entry.keys())
        == MANUAL_ANNOTATION_READOUT_EXPORT_REQUIRED_KEYS
    )


# ---------------------------------------------------------------------------
# 5. Forbidden wording absent from export at any depth.
# ---------------------------------------------------------------------------


def test_forbidden_wording_absent_from_export() -> None:
    """The export entry contains no v1.24.0 forbidden
    token at any key + any whole-string value at any
    depth."""
    kernel = _bare_kernel()
    kernel.manual_annotations.add_annotation(_annotation())
    readout = build_manual_annotation_readout(kernel)
    entry = manual_annotation_readout_to_export_entry(readout)

    def walk(value, path="entry"):
        if isinstance(value, str):
            assert (
                value
                not in FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES
            ), (
                f"forbidden whole-string value at {path}: "
                f"{value!r}"
            )
            return
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(k, str):
                    assert (
                        k
                        not in FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES
                    ), (
                        f"forbidden key at {path}: {k!r}"
                    )
                walk(v, f"{path}.{k}")
            return
        if isinstance(value, (list, tuple)):
            for i, x in enumerate(value):
                walk(x, f"{path}[{i}]")
    walk(entry)
    # And construction rejects forbidden keys.
    with pytest.raises(ValueError):
        build_run_export_bundle(
            bundle_id="run_bundle:bad",
            run_profile_label="quarterly_default",
            regime_label="constrained",
            period_count=4,
            digest=QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
            manual_annotation_readout=[
                {
                    "readout_id": "r:1",
                    "amplify": "no",
                }
            ],
        )


# ---------------------------------------------------------------------------
# 6. Export preserves unresolved citations.
# ---------------------------------------------------------------------------


def test_export_preserves_unresolved_citations() -> None:
    """An unresolved cited record id surfaces in the
    export entry's ``unresolved_cited_record_ids`` list,
    preserving order."""
    kernel = _bare_kernel()
    kernel.manual_annotations.add_annotation(
        _annotation(
            "manual_annotation:test:dangling",
            cited_record_ids=(
                "scenario_application:nope_1",
                "totally_unknown_prefix:nope_2",
            ),
        )
    )
    section = build_manual_annotation_readout_export_section(
        kernel
    )
    assert len(section) == 1
    entry = section[0]
    assert (
        "scenario_application:nope_1"
        in entry["unresolved_cited_record_ids"]
    )
    assert (
        "totally_unknown_prefix:nope_2"
        in entry["unresolved_cited_record_ids"]
    )


# ---------------------------------------------------------------------------
# 7. Export does not emit a ledger record.
# ---------------------------------------------------------------------------


def test_export_does_not_emit_ledger_records() -> None:
    """Building the export section must not emit any
    ledger record."""
    kernel = _bare_kernel()
    kernel.manual_annotations.add_annotation(_annotation())
    ledger_len_before = len(kernel.ledger.records)
    build_manual_annotation_readout_export_section(kernel)
    assert len(kernel.ledger.records) == ledger_len_before


# ---------------------------------------------------------------------------
# 8. Export does not mutate source-of-truth books.
# ---------------------------------------------------------------------------


def test_export_does_not_mutate_source_of_truth_books() -> None:
    """Snapshots of every relevant kernel book are byte-
    identical pre / post export-section build."""
    kernel = _bare_kernel()
    kernel.manual_annotations.add_annotation(_annotation())
    snap_before = {
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
        "scenario_applications": (
            kernel.scenario_applications.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "stress_programs": (
            kernel.stress_programs.snapshot()
        ),
        "ledger_len": len(kernel.ledger.records),
    }
    build_manual_annotation_readout_export_section(kernel)
    snap_after = {
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
        "scenario_applications": (
            kernel.scenario_applications.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "stress_programs": (
            kernel.stress_programs.snapshot()
        ),
        "ledger_len": len(kernel.ledger.records),
    }
    assert snap_before == snap_after
