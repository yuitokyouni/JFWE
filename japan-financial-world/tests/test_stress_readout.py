"""
Tests for v1.21.3 — Stress field readout: read-only multiset
projection + deterministic markdown summary.

Pins the v1.21.3 contract end-to-end:

- :func:`build_stress_field_readout` produces a
  :class:`StressFieldReadout` from an existing v1.21.2
  :class:`StressProgramApplicationRecord` plus the underlying
  v1.18.2 records, **without** mutating the kernel, **without**
  appending ledger records, and **without** calling
  :func:`apply_stress_program` or
  :func:`apply_scenario_driver`.
- The readout preserves emitted order: per-step
  ``scenario_application_ids`` in step_index order; per-shift
  ``scenario_context_shift_ids`` in v1.18.2 emission order
  (per-step ordinal sub-sequence preserved).
- Partial application is surfaced visibly:
  ``unresolved_step_count`` > 0 ⇒ the readout's
  ``unresolved_step_ids`` lists the affected step ids,
  ``unresolved_reason_labels`` lists a parallel closed-set
  reason label, and ``warnings`` carries one
  ``"partial application:"`` message + one warning per
  unresolved step. The markdown surfaces a **PARTIAL
  APPLICATION** banner before any other section.
- The readout carries no aggregate / combined / net /
  dominant / composite / interaction / expected / predicted /
  forecasted / magnitude / probability field. The boundary
  scan is enforced at the dataclass level, the to_dict()
  level, and the markdown-rendering level.
- Markdown wording is neutral: no ``impact`` / ``outcome`` /
  ``amplification`` / ``dampening`` / ``offset effect`` /
  ``dominant stress`` / ``net pressure`` / ``composite risk``
  / ``forecast`` / ``expected response`` / ``prediction`` /
  ``recommendation``.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scenario_drivers import ScenarioDriverTemplate
from world.scheduler import Scheduler
from world.state import State
from world.stress_applications import (
    apply_stress_program,
)
from world.stress_programs import (
    StressProgramTemplate,
    StressStep,
)
from world.stress_readout import (
    StressFieldReadout,
    UNRESOLVED_REASON_LABELS,
    UnknownStressProgramApplicationError,
    build_stress_field_readout,
    render_stress_field_summary_markdown,
)


_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "world"
    / "stress_readout.py"
)


# Token tables (separate from runtime checks below; the
# test-file scan strips these blocks before scanning).
_jurisdiction_tokens = (
    "toyota",
    "mufg",
    "smbc",
    "mizuho",
    "boj",
    "fsa",
    "jpx",
    "gpif",
    "tse",
    "nikkei",
    "topix",
    "sony",
    "jgb",
    "nyse",
    "nasdaq",
)
_licensed_taxonomy_tokens = (
    "gics",
    "msci",
    "factset",
    "bloomberg",
    "refinitiv",
)


# ---------------------------------------------------------------------------
# Helpers
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
    scenario_family_label: str = "credit_tightening_driver",
    driver_group_label: str = "credit_liquidity",
) -> ScenarioDriverTemplate:
    return ScenarioDriverTemplate(
        scenario_driver_template_id=(
            scenario_driver_template_id
        ),
        scenario_family_label=scenario_family_label,
        driver_group_label=driver_group_label,
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


def _build_step(
    *,
    program_id: str,
    step_index: int = 0,
    scenario_driver_template_id: str = (
        "scenario_driver:credit_tightening:reference"
    ),
) -> StressStep:
    return StressStep(
        stress_step_id=f"{program_id}:step:{step_index}",
        parent_stress_program_template_id=program_id,
        step_index=step_index,
        scenario_driver_template_id=(
            scenario_driver_template_id
        ),
        event_date_policy_label="quarter_end",
        scheduled_month_label="month_04",
    )


def _seed_happy_path_kernel(
    *,
    program_id: str = (
        "stress_program:test_readout:happy_path"
    ),
    step_template_ids: tuple[str, ...] = (
        "scenario_driver:credit_tightening:reference",
    ),
) -> tuple[WorldKernel, str]:
    """Build a kernel with v1.18.1 templates registered for
    each cited driver, register a v1.21.1 program, apply it
    via v1.21.2, and return ``(kernel, receipt_id)``."""
    kernel = _bare_kernel()
    seen: set[str] = set()
    for tpl_id in step_template_ids:
        if tpl_id in seen:
            continue
        seen.add(tpl_id)
        kernel.scenario_drivers.add_template(
            _build_template(
                scenario_driver_template_id=tpl_id,
            )
        )
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="Test program",
        program_purpose_label=(
            "single_credit_tightening_stress"
            if len(step_template_ids) == 1
            else "multi_stress_demonstration"
        ),
        stress_steps=tuple(
            _build_step(
                program_id=program_id,
                step_index=i,
                scenario_driver_template_id=tpl_id,
            )
            for i, tpl_id in enumerate(step_template_ids)
        ),
    )
    kernel.stress_programs.add_program(program)
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=program_id,
        as_of_date="2026-04-30",
    )
    return kernel, receipt.stress_program_application_id


def _seed_partial_kernel(
    *,
    program_id: str = (
        "stress_program:test_readout:partial"
    ),
) -> tuple[WorldKernel, str]:
    """Build a kernel with one valid template and one missing
    template, so apply_stress_program emits a partial-
    application receipt."""
    kernel = _bare_kernel()
    kernel.scenario_drivers.add_template(
        _build_template(
            scenario_driver_template_id=(
                "scenario_driver:credit_tightening:reference"
            ),
        )
    )
    # NB: the second cited template is intentionally NOT
    # registered → step 1 is unresolved.
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="Partial test program",
        program_purpose_label=(
            "multi_stress_demonstration"
        ),
        stress_steps=(
            _build_step(
                program_id=program_id,
                step_index=0,
                scenario_driver_template_id=(
                    "scenario_driver:credit_tightening:reference"
                ),
            ),
            _build_step(
                program_id=program_id,
                step_index=1,
                scenario_driver_template_id=(
                    "scenario_driver:nonexistent:reference"
                ),
            ),
        ),
    )
    kernel.stress_programs.add_program(program)
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=program_id,
        as_of_date="2026-04-30",
    )
    return kernel, receipt.stress_program_application_id


# ---------------------------------------------------------------------------
# 1. test_stress_field_readout_is_read_only
# ---------------------------------------------------------------------------


def test_stress_field_readout_is_read_only():
    """build_stress_field_readout must NOT mutate the kernel.
    Snapshots of every relevant book are byte-identical
    pre / post call. Re-running on the same input produces a
    byte-identical readout."""
    kernel, receipt_id = _seed_happy_path_kernel()
    snap_before = {
        "scenario_drivers": kernel.scenario_drivers.snapshot(),
        "scenario_applications": (
            kernel.scenario_applications.snapshot()
        ),
        "stress_programs": (
            kernel.stress_programs.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "ledger_len": len(kernel.ledger.records),
    }
    readout_a = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    snap_after = {
        "scenario_drivers": kernel.scenario_drivers.snapshot(),
        "scenario_applications": (
            kernel.scenario_applications.snapshot()
        ),
        "stress_programs": (
            kernel.stress_programs.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "ledger_len": len(kernel.ledger.records),
    }
    assert snap_before == snap_after
    # Re-run produces byte-identical readout.
    readout_b = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    assert readout_a.to_dict() == readout_b.to_dict()


# ---------------------------------------------------------------------------
# 2. test_stress_field_readout_does_not_call_apply_stress_program
# ---------------------------------------------------------------------------


def test_stress_field_readout_does_not_call_apply_stress_program():
    kernel, receipt_id = _seed_happy_path_kernel()

    # Patch apply_stress_program in the module's namespace
    # AND in stress_applications (in case the readout module
    # ever imports it). Either patch failing means the
    # readout did not call apply_stress_program — neither
    # patch should be triggered.
    called = {"n": 0}

    def _explode(*args, **kwargs):
        called["n"] += 1
        raise AssertionError(
            "build_stress_field_readout must NOT call "
            "apply_stress_program"
        )

    # The readout module does not import apply_stress_program;
    # patching the source module's symbol is enough.
    with patch(
        "world.stress_applications.apply_stress_program",
        _explode,
    ):
        build_stress_field_readout(
            kernel,
            stress_program_application_id=receipt_id,
        )
    assert called["n"] == 0


# ---------------------------------------------------------------------------
# 3. test_stress_field_readout_does_not_call_apply_scenario_driver
# ---------------------------------------------------------------------------


def test_stress_field_readout_does_not_call_apply_scenario_driver():
    kernel, receipt_id = _seed_happy_path_kernel()
    called = {"n": 0}

    def _explode(*args, **kwargs):
        called["n"] += 1
        raise AssertionError(
            "build_stress_field_readout must NOT call "
            "apply_scenario_driver"
        )

    with patch(
        "world.scenario_applications.apply_scenario_driver",
        _explode,
    ):
        build_stress_field_readout(
            kernel,
            stress_program_application_id=receipt_id,
        )
    assert called["n"] == 0


# ---------------------------------------------------------------------------
# 4. test_stress_field_readout_preserves_scenario_application_order
# ---------------------------------------------------------------------------


def test_stress_field_readout_preserves_scenario_application_order():
    """``scenario_application_ids`` must preserve the v1.21.2
    receipt's order (which is dense step_index order)."""
    pid = "stress_program:test_readout:order_app"
    kernel, receipt_id = _seed_happy_path_kernel(
        program_id=pid,
        step_template_ids=(
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
        ),
    )
    receipt = (
        kernel.stress_applications.get_application(receipt_id)
    )
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    assert (
        readout.scenario_application_ids
        == receipt.scenario_application_ids
    )
    # And ``active_step_ids`` reflects the same step-ordinal
    # ordering (step_index 0, 1, 2).
    assert readout.active_step_ids == (
        f"{pid}:step:0",
        f"{pid}:step:1",
        f"{pid}:step:2",
    )


# ---------------------------------------------------------------------------
# 5. test_stress_field_readout_preserves_context_shift_order
# ---------------------------------------------------------------------------


def test_stress_field_readout_preserves_context_shift_order():
    """``scenario_context_shift_ids`` must preserve the v1.18.2
    emission order — which the v1.21.2 receipt already
    captured."""
    pid = "stress_program:test_readout:order_shift"
    kernel, receipt_id = _seed_happy_path_kernel(
        program_id=pid,
        step_template_ids=(
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
        ),
    )
    receipt = (
        kernel.stress_applications.get_application(receipt_id)
    )
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    assert (
        readout.scenario_context_shift_ids
        == receipt.scenario_context_shift_ids
    )
    # Per the v1.18.2 _build_shift_specs table, the
    # credit_tightening family emits 2 context shifts per
    # application in this order:
    #   market_environment, financing_review_surface
    # The readout's per-shift label tuples preserve that
    # order across both step calls (4 shifts total = 2 × 2).
    assert readout.context_surface_labels == (
        "market_environment",
        "financing_review_surface",
        "market_environment",
        "financing_review_surface",
    )
    assert readout.shift_direction_labels == (
        "tighten",
        "tighten",
        "tighten",
        "tighten",
    )
    assert readout.scenario_family_labels == (
        "credit_tightening_driver",
        "credit_tightening_driver",
        "credit_tightening_driver",
        "credit_tightening_driver",
    )


# ---------------------------------------------------------------------------
# 6. test_stress_field_readout_surfaces_unresolved_steps
# ---------------------------------------------------------------------------


def test_stress_field_readout_surfaces_unresolved_steps():
    pid = "stress_program:test_readout:partial_surface"
    kernel, receipt_id = _seed_partial_kernel(
        program_id=pid,
    )
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    assert readout.total_step_count == 2
    assert readout.resolved_step_count == 1
    assert readout.unresolved_step_count == 1
    assert readout.active_step_ids == (f"{pid}:step:0",)
    assert readout.unresolved_step_ids == (f"{pid}:step:1",)
    # The cited template (the missing one) is classified as
    # template_missing.
    assert readout.unresolved_reason_labels == (
        "template_missing",
    )
    # And readout.is_partial = True.
    assert readout.is_partial is True


# ---------------------------------------------------------------------------
# 7. test_stress_field_readout_partial_application_warning
# ---------------------------------------------------------------------------


def test_stress_field_readout_partial_application_warning():
    pid = "stress_program:test_readout:partial_warning"
    kernel, receipt_id = _seed_partial_kernel(
        program_id=pid,
    )
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    # The warnings list must include a "partial application:"
    # banner + one per-unresolved-step warning.
    assert any(
        w.lower().startswith("partial application:")
        for w in readout.warnings
    )
    assert any(
        f"{pid}:step:1" in w and "template_missing" in w
        for w in readout.warnings
    )


# ---------------------------------------------------------------------------
# 8. test_stress_field_readout_has_no_aggregate_combined_net_dominant_fields
# ---------------------------------------------------------------------------


def test_stress_field_readout_has_no_aggregate_combined_net_dominant_fields():
    """Trip-wire: the dataclass + to_dict() output MUST NOT
    carry aggregate / combined / net / dominant / composite /
    expected / predicted / forecasted / magnitude /
    probability / amplification / intensity / outcome /
    impact / risk_score fields."""
    forbidden_prefixes = (
        "aggregate_",
        "combined_",
        "net_",
        "dominant_",
        "composite_",
        "expected_",
        "predicted_",
        "forecasted_",
    )
    forbidden_exact = (
        "stress_magnitude",
        "stress_probability_weight",
        "stress_amplification_score",
        "total_stress_intensity",
        "stress_intensity_score",
        "outcome",
        "impact",
        "result_score",
        "risk_score",
    )
    # Dataclass fields.
    for fname in StressFieldReadout.__dataclass_fields__:
        for prefix in forbidden_prefixes:
            assert not fname.startswith(prefix), (
                f"StressFieldReadout.{fname} starts with "
                f"forbidden prefix {prefix!r}"
            )
        for exact in forbidden_exact:
            assert fname != exact, (
                f"StressFieldReadout.{fname} equals "
                f"forbidden exact name {exact!r}"
            )

    # Build a readout to scan its rendered to_dict() too.
    kernel, receipt_id = _seed_happy_path_kernel()
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )

    def scan_keys(d, path=""):
        if isinstance(d, dict):
            for k, v in d.items():
                ks = str(k)
                for prefix in forbidden_prefixes:
                    assert not ks.startswith(prefix), (
                        f"forbidden prefix {prefix!r} key at "
                        f"{path}/{ks}"
                    )
                for exact in forbidden_exact:
                    assert ks != exact, (
                        f"forbidden exact key {exact!r} at "
                        f"{path}/{ks}"
                    )
                scan_keys(v, path + "/" + ks)
        elif isinstance(d, list):
            for i, e in enumerate(d):
                scan_keys(e, path + f"[{i}]")

    scan_keys(readout.to_dict(), "readout")


# ---------------------------------------------------------------------------
# 9. test_stress_field_readout_has_no_interaction_label
# ---------------------------------------------------------------------------


def test_stress_field_readout_has_no_interaction_label():
    """The dataclass + to_dict() output MUST NOT carry
    ``interaction_label`` / ``composition_label`` /
    ``output_context_label`` / ``dominant_shift_direction_label``
    / any of the v1.21.0a-deferred interaction tokens."""
    interaction_tokens = (
        "interaction_label",
        "composition_label",
        "output_context_label",
        "dominant_shift_direction_label",
        "amplify",
        "dampen",
        "offset",
        "coexist",
    )
    for fname in StressFieldReadout.__dataclass_fields__:
        assert (
            fname not in interaction_tokens
        ), (
            f"StressFieldReadout.{fname} is an interaction "
            "token (deferred to v1.22+)"
        )

    kernel, receipt_id = _seed_happy_path_kernel()
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )

    def scan(d, path=""):
        if isinstance(d, dict):
            for k, v in d.items():
                assert (
                    str(k) not in interaction_tokens
                ), (
                    f"interaction token {k!r} appears at "
                    f"{path}/{k}"
                )
                scan(v, path + "/" + str(k))
        elif isinstance(d, list):
            for i, e in enumerate(d):
                scan(e, path + f"[{i}]")

    scan(readout.to_dict(), "readout")


# ---------------------------------------------------------------------------
# 10. test_stress_field_readout_metadata_rejects_forbidden_keys
# ---------------------------------------------------------------------------


def test_stress_field_readout_metadata_rejects_forbidden_keys():
    """Metadata mappings on the readout dataclass + the
    helper's caller-supplied metadata MUST reject any
    forbidden key."""
    kernel, receipt_id = _seed_happy_path_kernel()
    forbidden_samples: tuple[str, ...] = (
        "stress_magnitude",
        "stress_probability_weight",
        "expected_field_response",
        "stress_forecast_path",
        "aggregate_shift_direction",
        "combined_context_label",
        "net_pressure_label",
        "dominant_stress_label",
        "composite_risk_label",
        "stress_amplification_score",
        "interaction_label",
        "amplify",
        "dampen",
        "offset",
        "coexist",
        "buy",
        "sell",
        "order",
        "japan_calibration",
        "llm_output",
        "firm_decision",
        "investor_action",
        "bank_approval",
    )
    for token in forbidden_samples:
        with pytest.raises(ValueError):
            build_stress_field_readout(
                kernel,
                stress_program_application_id=receipt_id,
                metadata={token: "any value"},
            )

    # And the dataclass directly rejects forbidden metadata
    # keys (in case a future caller bypasses the helper).
    for token in forbidden_samples:
        with pytest.raises(ValueError):
            StressFieldReadout(
                readout_id="r",
                stress_program_application_id="a",
                stress_program_template_id="t",
                as_of_date="2026-04-30",
                total_step_count=0,
                resolved_step_count=0,
                unresolved_step_count=0,
                active_step_ids=(),
                unresolved_step_ids=(),
                unresolved_reason_labels=(),
                scenario_driver_template_ids=(),
                scenario_application_ids=(),
                scenario_context_shift_ids=(),
                context_surface_labels=(),
                shift_direction_labels=(),
                scenario_family_labels=(),
                source_context_record_ids=(),
                metadata={token: "v"},
            )


# ---------------------------------------------------------------------------
# 11. test_markdown_summary_contains_no_forecast_or_recommendation_language
# ---------------------------------------------------------------------------


def test_markdown_summary_contains_no_forecast_or_recommendation_language():
    """The markdown rendering MUST NOT contain any of:
    impact, outcome, amplification, dampening, offset effect,
    dominant stress, net pressure, composite risk, forecast,
    expected response, prediction, recommendation."""
    forbidden_phrases = (
        "impact",
        "outcome",
        "amplification",
        "dampening",
        "offset effect",
        "dominant stress",
        "net pressure",
        "composite risk",
        "forecast",
        "expected response",
        "prediction",
        "recommendation",
    )
    # Render both happy-path and partial-application markdown.
    kernel_happy, receipt_happy = _seed_happy_path_kernel(
        program_id=(
            "stress_program:test_readout:happy_md"
        ),
    )
    md_happy = render_stress_field_summary_markdown(
        build_stress_field_readout(
            kernel_happy,
            stress_program_application_id=receipt_happy,
        )
    )
    kernel_partial, receipt_partial = _seed_partial_kernel(
        program_id=(
            "stress_program:test_readout:partial_md"
        ),
    )
    md_partial = render_stress_field_summary_markdown(
        build_stress_field_readout(
            kernel_partial,
            stress_program_application_id=receipt_partial,
        )
    )
    for md, label in (
        (md_happy, "happy"),
        (md_partial, "partial"),
    ):
        lower = md.lower()
        for phrase in forbidden_phrases:
            assert phrase not in lower, (
                f"forbidden phrase {phrase!r} appears in the "
                f"{label}-path markdown summary"
            )


# ---------------------------------------------------------------------------
# 12. test_markdown_summary_contains_partial_application_status_when_unresolved
# ---------------------------------------------------------------------------


def test_markdown_summary_contains_partial_application_status_when_unresolved():
    """When ``readout.is_partial`` is True, the markdown
    rendering must surface a clear partial-application
    banner before any other section, and list each
    unresolved step's reason label."""
    kernel, receipt_id = _seed_partial_kernel()
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    md = render_stress_field_summary_markdown(readout)
    assert "PARTIAL APPLICATION" in md
    assert "Unresolved step ids" in md
    # The reason label for the unresolved step is rendered.
    assert "template_missing" in md
    # Step counts visible (markdown renders the labels in bold,
    # so the rendered substring is e.g. ``**Total step count**: 2``).
    assert "Total step count**: 2" in md
    assert "Resolved step count**: 1" in md
    assert "Unresolved step count**: 1" in md


def test_markdown_summary_omits_partial_banner_when_fully_resolved():
    """When every step resolved, the markdown rendering must
    not include the **PARTIAL APPLICATION** banner."""
    kernel, receipt_id = _seed_happy_path_kernel()
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    assert readout.is_partial is False
    md = render_stress_field_summary_markdown(readout)
    assert "PARTIAL APPLICATION" not in md


# ---------------------------------------------------------------------------
# 13. test_existing_profiles_unchanged_without_explicit_stress_program
# ---------------------------------------------------------------------------


def test_existing_profiles_unchanged_without_explicit_stress_program():
    """The canonical profile digests must stay byte-identical
    to v1.20.last when no stress program is registered or
    applied. v1.21.3 is opt-in storage / read-only — only the
    v1.21.2 helper writes stress-program-application records,
    and only when explicitly invoked."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (
        _run_default,
        _run_monthly_reference,
        _seed_kernel,
    )

    k_q = _seed_kernel()
    r_q = _run_default(k_q)
    assert k_q.stress_programs.list_programs() == ()
    assert k_q.stress_applications.list_applications() == ()
    assert (
        living_world_digest(k_q, r_q)
        == "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c"
    )

    k_m = _seed_kernel()
    r_m = _run_monthly_reference(k_m)
    assert k_m.stress_applications.list_applications() == ()
    assert (
        living_world_digest(k_m, r_m)
        == "75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d"
    )


def test_existing_profile_unchanged_scenario_monthly_reference_universe():
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world_performance_boundary import (
        _run_v1_20_3,
        _seed_v1_20_3_kernel,
    )

    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert k.stress_applications.list_applications() == ()
    assert (
        living_world_digest(k, r)
        == "5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6"
    )


# ---------------------------------------------------------------------------
# 14. test_record_count_unchanged_by_readout_if_readout_is_not_ledgered
# ---------------------------------------------------------------------------


def test_record_count_unchanged_by_readout_if_readout_is_not_ledgered():
    """v1.21.3 emits NO ledger record. Building a readout
    must leave the kernel ledger length unchanged from the
    pre-readout state."""
    kernel, receipt_id = _seed_happy_path_kernel()
    n_records_before = len(kernel.ledger.records)
    record_types_before = {
        r.record_type for r in kernel.ledger.records
    }
    build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    n_records_after = len(kernel.ledger.records)
    record_types_after = {
        r.record_type for r in kernel.ledger.records
    }
    assert n_records_before == n_records_after
    assert record_types_before == record_types_after
    # No new RecordType enum value was introduced.
    record_type_values = {rt.value for rt in RecordType}
    for forbidden in (
        "stress_field_readout_recorded",
        "stress_field_readout_emitted",
        "stress_readout_recorded",
    ):
        assert forbidden not in record_type_values, (
            f"v1.21.3 must not introduce {forbidden!r} "
            "RecordType"
        )


# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------


def test_unresolved_reason_labels_closed_set():
    assert UNRESOLVED_REASON_LABELS == frozenset(
        {
            "template_missing",
            "unknown_failure",
        }
    )


def test_build_readout_rejects_unknown_application():
    kernel = _bare_kernel()
    with pytest.raises(
        UnknownStressProgramApplicationError
    ):
        build_stress_field_readout(
            kernel,
            stress_program_application_id=(
                "stress_program_application:does_not_exist"
            ),
        )


def test_readout_consistency_constraints():
    """The dataclass enforces that
    resolved_step_count + unresolved_step_count ==
    total_step_count, and that ``active_step_ids`` /
    ``unresolved_step_ids`` lengths match their counts."""
    # Total mismatch.
    with pytest.raises(ValueError):
        StressFieldReadout(
            readout_id="r",
            stress_program_application_id="a",
            stress_program_template_id="t",
            as_of_date="2026-04-30",
            total_step_count=3,
            resolved_step_count=1,
            unresolved_step_count=1,  # 1+1 != 3
            active_step_ids=("x",),
            unresolved_step_ids=("y",),
            unresolved_reason_labels=("template_missing",),
            scenario_driver_template_ids=(),
            scenario_application_ids=(),
            scenario_context_shift_ids=(),
            context_surface_labels=(),
            shift_direction_labels=(),
            scenario_family_labels=(),
            source_context_record_ids=(),
        )
    # active_step_ids length mismatch.
    with pytest.raises(ValueError):
        StressFieldReadout(
            readout_id="r",
            stress_program_application_id="a",
            stress_program_template_id="t",
            as_of_date="2026-04-30",
            total_step_count=2,
            resolved_step_count=1,
            unresolved_step_count=1,
            active_step_ids=(),  # length 0 != 1
            unresolved_step_ids=("y",),
            unresolved_reason_labels=("template_missing",),
            scenario_driver_template_ids=(),
            scenario_application_ids=(),
            scenario_context_shift_ids=(),
            context_surface_labels=(),
            shift_direction_labels=(),
            scenario_family_labels=(),
            source_context_record_ids=(),
        )
    # unresolved_reason_labels length mismatch.
    with pytest.raises(ValueError):
        StressFieldReadout(
            readout_id="r",
            stress_program_application_id="a",
            stress_program_template_id="t",
            as_of_date="2026-04-30",
            total_step_count=2,
            resolved_step_count=1,
            unresolved_step_count=1,
            active_step_ids=("x",),
            unresolved_step_ids=("y",),
            unresolved_reason_labels=(),  # 0 != 1
            scenario_driver_template_ids=(),
            scenario_application_ids=(),
            scenario_context_shift_ids=(),
            context_surface_labels=(),
            shift_direction_labels=(),
            scenario_family_labels=(),
            source_context_record_ids=(),
        )


def test_readout_unresolved_reason_label_unknown_failure_when_template_present():
    """If the v1.18.1 template exists but the v1.21.2 helper
    still failed to apply, the reason label is
    ``unknown_failure`` (not ``template_missing``).

    Implementation note: this test is hard to trigger from a
    real apply because the v1.18.2 helper succeeds whenever
    the template exists. We exercise it by constructing the
    receipt + program directly with a 'pretend unresolved'
    step whose template IS registered."""
    pid = "stress_program:test_readout:unknown_failure"
    kernel = _bare_kernel()
    kernel.scenario_drivers.add_template(
        _build_template(
            scenario_driver_template_id=(
                "scenario_driver:credit_tightening:reference"
            ),
        )
    )
    program = StressProgramTemplate(
        stress_program_template_id=pid,
        program_label="Unknown failure synthetic",
        program_purpose_label=(
            "single_credit_tightening_stress"
        ),
        stress_steps=(
            _build_step(
                program_id=pid,
                step_index=0,
                scenario_driver_template_id=(
                    "scenario_driver:credit_tightening:reference"
                ),
            ),
        ),
    )
    kernel.stress_programs.add_program(program)
    # Synthesise a v1.21.2 receipt that claims zero scenario
    # applications were emitted (i.e. the step never resolved
    # despite the template being present). This pins the
    # readout's classification path.
    from world.stress_applications import (
        StressProgramApplicationRecord,
    )

    fake_receipt = StressProgramApplicationRecord(
        stress_program_application_id=(
            "stress_program_application:fake_unknown"
        ),
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
        scenario_application_ids=(),
        scenario_context_shift_ids=(),
        unresolved_step_count=1,
        application_status_label="rejected",
    )
    kernel.stress_applications.add_application(fake_receipt)
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=(
            fake_receipt.stress_program_application_id
        ),
    )
    assert readout.unresolved_step_count == 1
    assert readout.unresolved_step_ids == (
        f"{pid}:step:0",
    )
    # Template IS present → reason is ``unknown_failure``.
    assert readout.unresolved_reason_labels == (
        "unknown_failure",
    )


def test_readout_id_default_format():
    kernel, receipt_id = _seed_happy_path_kernel()
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    assert readout.readout_id == (
        f"stress_field_readout:{receipt_id}"
    )


def test_readout_accepts_caller_readout_id():
    kernel, receipt_id = _seed_happy_path_kernel()
    custom_id = "stress_field_readout:custom_id_example"
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
        readout_id=custom_id,
    )
    assert readout.readout_id == custom_id


def test_readout_accepts_downstream_citation_ids():
    kernel, receipt_id = _seed_happy_path_kernel()
    downstream = (
        "investor_market_intent:demo:001",
        "indicative_market_pressure:demo:001",
    )
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
        downstream_citation_ids=downstream,
    )
    assert readout.downstream_citation_ids == downstream


def test_render_stress_field_summary_markdown_is_deterministic():
    kernel, receipt_id = _seed_happy_path_kernel()
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    md_a = render_stress_field_summary_markdown(readout)
    md_b = render_stress_field_summary_markdown(readout)
    assert md_a == md_b


def test_render_stress_field_summary_markdown_rejects_non_readout():
    with pytest.raises(TypeError):
        render_stress_field_summary_markdown(
            {"readout_id": "x"}
        )


def test_render_stress_field_summary_markdown_contains_boundary_statement():
    kernel, receipt_id = _seed_happy_path_kernel()
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    md = render_stress_field_summary_markdown(readout)
    assert "## Boundary statement" in md
    assert "no causality claim" in md.lower()
    assert "no aggregate" in md.lower()
    assert "no interaction inference" in md.lower()


def test_render_stress_field_summary_markdown_contains_required_sections():
    kernel, receipt_id = _seed_happy_path_kernel()
    readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=receipt_id,
    )
    md = render_stress_field_summary_markdown(readout)
    for section in (
        "## Program application",
        "## Step resolution",
        "## Emitted scenario applications",
        "## Emitted context shifts",
        "## Context surfaces (multiset)",
        "## Shift directions (multiset)",
        "## Scenario families (multiset)",
        "## Warnings",
        "## Boundary statement",
    ):
        assert section in md, (
            f"required section {section!r} missing from "
            "markdown summary"
        )


def test_v1_21_3_module_does_not_import_apply_helpers():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    forbidden_imports = (
        "from world.stress_applications import "
        "apply_stress_program",
        "from world.scenario_applications import "
        "apply_scenario_driver",
    )
    for imp in forbidden_imports:
        assert imp not in text, (
            f"v1.21.3 must not import {imp!r}"
        )


def test_v1_21_3_module_does_not_import_source_of_truth_books():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    forbidden_imports = (
        "from world.market_environment ",
        "from world.firm_state ",
        "from world.investor_intent ",
        "from world.financing_paths ",
        "from world.prices ",
        "from world.contracts ",
        "from world.constraints ",
        "from world.ownership ",
        "from world.institutions ",
        "from world.indicative_market_pressure ",
        "from world.market_intents ",
    )
    for imp in forbidden_imports:
        assert imp not in text, (
            f"v1.21.3 must not import {imp!r}"
        )


# ---------------------------------------------------------------------------
# Module-text + test-text scans
# ---------------------------------------------------------------------------


def _strip_docstrings(text: str) -> str:
    out: list[str] = []
    i = 0
    while True:
        lo = text.find('"""', i)
        if lo < 0:
            out.append(text[i:])
            break
        out.append(text[i:lo])
        hi = text.find('"""', lo + 3)
        if hi < 0:
            out.append(text[lo:])
            break
        i = hi + 3
    return "".join(out)


def _strip_balanced_parens_after(text: str, marker: str) -> str:
    lower = text.lower()
    open_idx = lower.find(marker.lower())
    if open_idx < 0:
        return text
    paren_open = text.find("(", open_idx)
    if paren_open < 0:
        return text
    depth = 1
    i = paren_open + 1
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        i += 1
    return text[:open_idx] + text[i:]


def test_module_jurisdiction_neutral_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_docstrings(text)
    text = _strip_balanced_parens_after(
        text,
        "FORBIDDEN_STRESS_READOUT_FIELD_NAMES",
    ).lower()
    for token in _jurisdiction_tokens:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "stress_readout.py outside docstring + FORBIDDEN literal"
        )


def test_module_no_licensed_taxonomy_dependency_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_docstrings(text)
    text = _strip_balanced_parens_after(
        text,
        "FORBIDDEN_STRESS_READOUT_FIELD_NAMES",
    ).lower()
    for token in _licensed_taxonomy_tokens:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"licensed-taxonomy token {token!r} appears in "
            "stress_readout.py outside docstring + FORBIDDEN literal"
        )


def test_test_file_jurisdiction_neutral_scan():
    text = Path(__file__).read_text(encoding="utf-8").lower()
    for marker in (
        "_jurisdiction_tokens = (",
        "_licensed_taxonomy_tokens = (",
        "forbidden_samples: tuple",
        "forbidden_imports = (",
        "interaction_tokens = (",
        "forbidden_prefixes = (",
        "forbidden_exact = (",
        "forbidden_phrases = (",
    ):
        idx = text.find(marker)
        if idx != -1:
            close = text.find(")", idx) + 1
            if close > 0:
                text = text[:idx] + text[close:]
    for token in _jurisdiction_tokens:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "test_stress_readout.py outside the token tables"
        )


def test_module_text_does_not_carry_forbidden_phrases():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_docstrings(text)
    text = _strip_balanced_parens_after(
        text,
        "FORBIDDEN_STRESS_READOUT_FIELD_NAMES",
    )
    for phrase in (
        "real_company_name",
        "real_sector_weight",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
        "investment_advice",
        "target_price",
        "expected_return",
        "forecast_path",
        "predicted_index",
        "stress_magnitude_in_basis_points",
        "stress_probability_weight",
        "expected_field_response",
        "stress_forecast_path",
        "aggregate_shift_direction",
        "combined_context_label",
        "net_pressure_label",
        "dominant_stress_label",
        "composite_risk_label",
        "stress_amplification_score",
        "interaction_label",
    ):
        pattern = rf"\b{re.escape(phrase)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden phrase {phrase!r} appears in "
            "stress_readout.py outside docstring + FORBIDDEN literal"
        )
