"""
v1.23.3 — Attention-crowding / uncited-stress case study helper.

Read-only helper that builds a deterministic case-study
report over an already stress-applied kernel. The report
surfaces, per ``docs/case_study_001_attention_crowding_uncited_stress.md``:

- which stress steps entered the citation trail
  (``cited_step_ids`` mirrors the v1.21.3 readout's
  ``active_step_ids``);
- which stress steps remained uncited or unresolved
  (``uncited_step_ids`` mirrors the v1.21.3 readout's
  ``unresolved_step_ids``);
- whether partial application is visible
  (``is_partial_application`` flag carried from the v1.21.3
  readout);
- whether the v1.22.1 export-shaped projection preserves the
  v1.21.0a / v1.22.0 boundary
  (``boundary_preservation_pin_satisfied`` flag, computed by
  scanning the v1.22.1 export entry against the v1.23.1
  canonical ``FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS``);
- whether every cited id resolves to an extant kernel record
  (``citation_completeness_pin_satisfied`` flag, computed by
  walking the readout's plain-id citations against the
  corresponding kernel books).

Read-only discipline (binding):

- The helper does **not** call
  :func:`world.stress_applications.apply_stress_program`,
  does **not** call
  :func:`world.scenario_applications.apply_scenario_driver`,
  does **not** mutate any kernel book, and does **not** emit
  a ledger record. Tests pin the no-mutation / no-ledger
  contract.
- Same kernel state + same arguments → byte-identical report.
  The v1.23.2 Cat 1 determinism pin applies verbatim — the
  case study is just one more deterministic projection over
  the same readout.
- The helper introduces **no** new dataclass, **no** new
  ledger event type, **no** new label vocabulary, **no** new
  closed-set, **no** new RecordType, **no** UI surface, and
  **no** new export schema field.
- The helper's report contains **no** outcome / impact /
  amplification / dampening / dominant-stress / net-pressure /
  composite-risk / forecast / prediction / recommendation /
  expected-response / expected-return / target-price /
  trading-verb token at any depth. The boundary scan re-pins
  this against
  :data:`world.forbidden_tokens.FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS`.

The case study aligns with
``docs/research_note_002_validating_stress_citation_graphs_without_price_prediction.md``
§2 (validation as audit-object property checking, not
predictive-accuracy scoring): the report carries no number
to RMSE against, only structural properties of the citation
graph the engine emitted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from world.forbidden_tokens import (
    FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS,
)
from world.stress_readout import (
    StressFieldReadout,
    build_stress_field_readout,
)
from world.stress_readout_export import (
    stress_field_readout_to_export_entry,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


# v1.23.3 — boundary statement carried verbatim into every
# case-study report. Mirrors the v1.21.3 stress-readout
# boundary block but is scoped to the case-study surface; the
# rendered text lists each anti-claim under its negation form.
_CASE_STUDY_BOUNDARY_STATEMENT_LINES: tuple[str, ...] = (
    "Read-only attention-crowding / uncited-stress case study. ",
    "Citation-graph projection only — no causality claim. ",
    "No magnitude. No probability. No aggregate / combined / ",
    "net / dominant / composite stress result. ",
    "No interaction inference (no `amplify` / `dampen` / ",
    "`offset` / `coexist` label). ",
    "No price formation. No trading. No order. No execution. ",
    "No clearing. No settlement. No financing execution. ",
    "No firm decision. No investor action. No bank approval ",
    "logic. No investment advice. No real data ingestion. ",
    "No real institutional identifiers. No Japan calibration. ",
    "No LLM execution. No LLM prose as source-of-truth.",
)


__all__ = (
    "build_attention_crowding_case_study_report",
    "render_attention_crowding_case_study_markdown",
)


def _walk_keys_and_string_values(value: Any):
    """Walk a JSON-like value and yield every dict key + every
    string value at any depth."""
    if isinstance(value, str):
        yield ("value", value)
        return
    if isinstance(value, Mapping):
        for k, v in value.items():
            if isinstance(k, str):
                yield ("key", k)
            yield from _walk_keys_and_string_values(v)
        return
    if isinstance(value, (list, tuple)):
        for entry in value:
            yield from _walk_keys_and_string_values(entry)


def _check_boundary_preservation(export_entry: Mapping[str, Any]) -> dict[str, Any]:
    """Scan the v1.22.1 export entry against the v1.23.1
    canonical ``FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS``.

    Pin pass: zero forbidden tokens at any key + zero
    forbidden tokens as whole-string values."""
    key_offenders: list[str] = []
    value_offenders: list[str] = []
    for kind, item in _walk_keys_and_string_values(export_entry):
        if kind == "key" and item in FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS:
            key_offenders.append(item)
        if kind == "value" and item in FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS:
            value_offenders.append(item)
    return {
        "satisfied": (
            not key_offenders and not value_offenders
        ),
        "forbidden_key_count": len(key_offenders),
        "forbidden_value_count": len(value_offenders),
    }


def _check_citation_completeness(
    kernel: "WorldKernel", readout: StressFieldReadout
) -> dict[str, Any]:
    """Walk every plain-id citation in the readout and confirm
    it resolves to a record in a corresponding kernel book.

    Surfaces:

    - ``scenario_application_resolution`` —
      ``scenario_application_ids`` resolve to v1.18.2
      :class:`world.scenario_applications.ScenarioDriverApplicationRecord`
      records via ``kernel.scenario_applications.list_applications()``;
    - ``scenario_context_shift_resolution`` —
      ``scenario_context_shift_ids`` resolve via
      ``kernel.scenario_applications.list_context_shifts()``;
    - ``stress_program_application_resolution`` —
      ``stress_program_application_id`` resolves via
      ``kernel.stress_applications.list_applications()``.

    A "dangling citation" is a cited id that does not match
    any extant record. The pin's ``satisfied`` flag is True
    iff every category has zero dangling ids."""
    extant_app_ids = {
        a.scenario_application_id
        for a in kernel.scenario_applications.list_applications()
    }
    extant_shift_ids = {
        s.scenario_context_shift_id
        for s in kernel.scenario_applications.list_context_shifts()
    }
    extant_stress_app_ids = {
        a.stress_program_application_id
        for a in kernel.stress_applications.list_applications()
    }
    dangling_app_ids = sorted(
        sid
        for sid in readout.scenario_application_ids
        if sid not in extant_app_ids
    )
    dangling_shift_ids = sorted(
        sid
        for sid in readout.scenario_context_shift_ids
        if sid not in extant_shift_ids
    )
    receipt_resolves = (
        readout.stress_program_application_id
        in extant_stress_app_ids
    )
    return {
        "satisfied": (
            not dangling_app_ids
            and not dangling_shift_ids
            and receipt_resolves
        ),
        "dangling_scenario_application_id_count": len(
            dangling_app_ids
        ),
        "dangling_scenario_context_shift_id_count": len(
            dangling_shift_ids
        ),
        "stress_program_application_id_resolves": (
            receipt_resolves
        ),
    }


def _check_partial_application_visibility(
    readout: StressFieldReadout,
) -> dict[str, Any]:
    """Confirm the v1.21.3 readout surfaces every required
    visibility field when ``is_partial`` is True. The check
    re-asserts the v1.21.3 dataclass-level invariants at the
    case-study surface."""
    visibility_fields_present = (
        # length invariants pinned by StressFieldReadout
        # __post_init__; re-checked here for case-study
        # diagnostic clarity.
        len(readout.unresolved_step_ids)
        == readout.unresolved_step_count
        and len(readout.unresolved_reason_labels)
        == readout.unresolved_step_count
        and len(readout.active_step_ids)
        == readout.resolved_step_count
    )
    # Partial-application warning visibility: when partial,
    # the readout must surface at least one warning whose
    # text starts with "partial application" (the v1.21.3
    # contract).
    has_partial_warning = (
        not readout.is_partial
        or any(
            w.lower().startswith("partial application")
            for w in readout.warnings
        )
    )
    return {
        "satisfied": (
            visibility_fields_present
            and has_partial_warning
        ),
        "is_partial_application": readout.is_partial,
        "unresolved_step_count": readout.unresolved_step_count,
        "resolved_step_count": readout.resolved_step_count,
        "total_step_count": readout.total_step_count,
    }


def build_attention_crowding_case_study_report(
    kernel: "WorldKernel",
    *,
    stress_program_application_id: str,
    case_study_id: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic case-study report over a
    stress-applied kernel.

    Read-only discipline (binding):

    - The helper does NOT call
      :func:`world.stress_applications.apply_stress_program`,
      does NOT call
      :func:`world.scenario_applications.apply_scenario_driver`,
      does NOT mutate any kernel book, does NOT emit any
      ledger record.
    - Same kernel state + same arguments → byte-identical
      report.

    The report is a plain ``dict`` (no new dataclass, no new
    RecordType). Every value is one of: a plain-id string,
    a non-negative int, a tuple of plain-id strings, a tuple
    of human-readable warning strings, a small dict of
    pin-result flags, or the boundary statement.

    Raises :class:`world.stress_applications.UnknownStressProgramApplicationError`
    when the cited ``stress_program_application_id`` is not
    present in :attr:`world.kernel.WorldKernel.stress_applications`.
    """
    readout: StressFieldReadout = build_stress_field_readout(
        kernel,
        stress_program_application_id=(
            stress_program_application_id
        ),
    )
    export_entry = stress_field_readout_to_export_entry(readout)

    boundary_pin = _check_boundary_preservation(export_entry)
    citation_pin = _check_citation_completeness(kernel, readout)
    partial_pin = _check_partial_application_visibility(readout)

    if case_study_id is None:
        case_study_id = (
            f"attention_crowding_case_study:"
            f"{stress_program_application_id}"
        )

    # Stress readout summary — selected v1.21.3 fields. List-
    # typed fields are converted to lists for JSON-shaped
    # round-trip; the case study is read-only so the order
    # must be preserved verbatim from the readout.
    stress_readout_summary: dict[str, Any] = {
        "readout_id": readout.readout_id,
        "as_of_date": readout.as_of_date,
        "total_step_count": readout.total_step_count,
        "resolved_step_count": readout.resolved_step_count,
        "unresolved_step_count": (
            readout.unresolved_step_count
        ),
        "is_partial_application": readout.is_partial,
        "scenario_driver_template_ids": list(
            readout.scenario_driver_template_ids
        ),
        "context_surface_labels": list(
            readout.context_surface_labels
        ),
        "shift_direction_labels": list(
            readout.shift_direction_labels
        ),
        "scenario_family_labels": list(
            readout.scenario_family_labels
        ),
        "unresolved_reason_labels": list(
            readout.unresolved_reason_labels
        ),
    }

    validation_report_summary: dict[str, Any] = {
        # Cat 1 (determinism) — the case study is itself a
        # deterministic projection. Pin-pass means the helper
        # was called; the byte-identity assertion lives at the
        # test surface.
        "determinism_pin_v1_23_2": "deterministic_projection",
        "boundary_preservation_pin_v1_23_2": boundary_pin,
        "citation_completeness_pin_v1_23_2": citation_pin,
        "partial_application_visibility_pin_v1_23_2": (
            partial_pin
        ),
    }

    return {
        "case_study_id": case_study_id,
        "stress_program_application_id": (
            stress_program_application_id
        ),
        "stress_program_template_id": (
            readout.stress_program_template_id
        ),
        "stress_step_ids": (
            list(readout.active_step_ids)
            + list(readout.unresolved_step_ids)
        ),
        "cited_step_ids": list(readout.active_step_ids),
        "uncited_step_ids": list(readout.unresolved_step_ids),
        "scenario_application_ids": list(
            readout.scenario_application_ids
        ),
        "scenario_context_shift_ids": list(
            readout.scenario_context_shift_ids
        ),
        "stress_readout_summary": stress_readout_summary,
        "validation_report_summary": validation_report_summary,
        "warnings": list(readout.warnings),
        "boundary_statement": "".join(
            _CASE_STUDY_BOUNDARY_STATEMENT_LINES
        ),
    }


def render_attention_crowding_case_study_markdown(
    report: Mapping[str, Any],
) -> str:
    """Deterministic markdown rendering of a case-study
    report. Same report → byte-identical markdown bytes.

    The renderer emits 8 sections, in this order:

    1. ``## Case study`` — id + cited program / receipt ids.
    2. ``## Cited stress steps`` — plain-id list of step ids
       that produced a v1.18.2 application record.
    3. ``## Uncited stress steps`` — plain-id list of step ids
       that did NOT produce a v1.18.2 application record,
       paired with the v1.21.3 reason label.
    4. ``## Citation graph plain-id surface`` — scenario
       application ids + scenario context shift ids in
       emission order.
    5. ``## Stress readout summary`` — selected v1.21.3
       fields (counts, label tuples).
    6. ``## Validation report summary`` — Cat 1-4 pin
       results.
    7. ``## Warnings`` — human-readable warnings carried
       from the v1.21.3 readout.
    8. ``## Boundary statement`` — pinned anti-claim block.

    The renderer emits no ``impact`` / ``outcome`` /
    ``amplification`` / ``dampening`` / ``offset effect`` /
    ``dominant stress`` / ``net pressure`` / ``composite
    risk`` / ``forecast`` / ``expected response`` /
    ``prediction`` / ``recommendation`` text. Pinned by
    ``test_attention_crowding_case_study``.
    """
    if not isinstance(report, Mapping):
        raise TypeError(
            "report must be a Mapping; "
            f"got {type(report).__name__}"
        )

    out: list[str] = []
    out.append(
        f"# Attention-crowding / uncited-stress case study — "
        f"{report.get('stress_program_template_id', '?')}"
    )
    out.append("")

    # 1. Case study.
    out.append("## Case study")
    out.append("")
    out.append(
        f"- **Case study id**: `{report.get('case_study_id', '?')}`"
    )
    out.append(
        "- **Stress program application id**: "
        f"`{report.get('stress_program_application_id', '?')}`"
    )
    out.append(
        "- **Stress program template id**: "
        f"`{report.get('stress_program_template_id', '?')}`"
    )
    out.append("")

    # 2. Cited stress steps.
    out.append("## Cited stress steps")
    out.append("")
    cited = report.get("cited_step_ids", []) or []
    if not cited:
        out.append("- (none cited — every step uncited)")
    else:
        out.append(f"- **Cited step count**: {len(cited)}")
        for sid in cited:
            out.append(f"  - `{sid}`")
    out.append("")

    # 3. Uncited stress steps.
    out.append("## Uncited stress steps")
    out.append("")
    uncited = report.get("uncited_step_ids", []) or []
    summary = report.get("stress_readout_summary", {}) or {}
    reasons = summary.get("unresolved_reason_labels", []) or []
    if not uncited:
        out.append("- (none uncited — every step cited)")
    else:
        out.append(f"- **Uncited step count**: {len(uncited)}")
        for i, sid in enumerate(uncited):
            reason = reasons[i] if i < len(reasons) else "?"
            out.append(f"  - `{sid}` — reason: `{reason}`")
    out.append("")

    # 4. Citation graph plain-id surface.
    out.append("## Citation graph plain-id surface")
    out.append("")
    app_ids = report.get("scenario_application_ids", []) or []
    shift_ids = (
        report.get("scenario_context_shift_ids", []) or []
    )
    out.append(
        f"- **Scenario application ids** ({len(app_ids)}):"
    )
    if not app_ids:
        out.append("  - (none)")
    else:
        for aid in app_ids:
            out.append(f"  - `{aid}`")
    out.append(
        f"- **Scenario context shift ids** ({len(shift_ids)}):"
    )
    if not shift_ids:
        out.append("  - (none)")
    else:
        for sid in shift_ids:
            out.append(f"  - `{sid}`")
    out.append("")

    # 5. Stress readout summary.
    out.append("## Stress readout summary")
    out.append("")
    out.append(
        f"- **Total step count**: "
        f"{summary.get('total_step_count', '?')}"
    )
    out.append(
        f"- **Resolved step count**: "
        f"{summary.get('resolved_step_count', '?')}"
    )
    out.append(
        f"- **Unresolved step count**: "
        f"{summary.get('unresolved_step_count', '?')}"
    )
    out.append(
        f"- **Is partial application**: "
        f"{summary.get('is_partial_application', '?')}"
    )
    cs_labels = summary.get("context_surface_labels", []) or []
    sd_labels = summary.get("shift_direction_labels", []) or []
    sf_labels = summary.get("scenario_family_labels", []) or []
    out.append(
        "- **Context surface labels (multiset)**: "
        + (", ".join(cs_labels) if cs_labels else "(none)")
    )
    out.append(
        "- **Shift direction labels (multiset)**: "
        + (", ".join(sd_labels) if sd_labels else "(none)")
    )
    out.append(
        "- **Scenario family labels (multiset)**: "
        + (", ".join(sf_labels) if sf_labels else "(none)")
    )
    out.append("")

    # 6. Validation report summary.
    out.append("## Validation report summary")
    out.append("")
    vrs = report.get("validation_report_summary", {}) or {}
    out.append(
        "- **Determinism pin (Cat 1)**: "
        f"`{vrs.get('determinism_pin_v1_23_2', '?')}`"
    )
    bp = vrs.get("boundary_preservation_pin_v1_23_2", {}) or {}
    out.append(
        "- **Boundary preservation pin (Cat 2)**: "
        f"satisfied = {bp.get('satisfied', '?')} · "
        f"forbidden_key_count = {bp.get('forbidden_key_count', '?')} · "
        f"forbidden_value_count = "
        f"{bp.get('forbidden_value_count', '?')}"
    )
    cp = vrs.get("citation_completeness_pin_v1_23_2", {}) or {}
    out.append(
        "- **Citation completeness pin (Cat 3)**: "
        f"satisfied = {cp.get('satisfied', '?')} · "
        "dangling_scenario_application_id_count = "
        f"{cp.get('dangling_scenario_application_id_count', '?')} · "
        "dangling_scenario_context_shift_id_count = "
        f"{cp.get('dangling_scenario_context_shift_id_count', '?')}"
    )
    pp = (
        vrs.get(
            "partial_application_visibility_pin_v1_23_2", {}
        )
        or {}
    )
    out.append(
        "- **Partial-application visibility pin (Cat 4)**: "
        f"satisfied = {pp.get('satisfied', '?')} · "
        "is_partial_application = "
        f"{pp.get('is_partial_application', '?')}"
    )
    out.append("")

    # 7. Warnings.
    out.append("## Warnings")
    out.append("")
    warnings_list = report.get("warnings", []) or []
    if warnings_list:
        for w in warnings_list:
            out.append(f"- {w}")
    else:
        out.append("- (none)")
    out.append("")

    # 8. Boundary statement.
    out.append("## Boundary statement")
    out.append("")
    out.append(
        report.get(
            "boundary_statement",
            "".join(_CASE_STUDY_BOUNDARY_STATEMENT_LINES),
        )
    )
    out.append("")

    return "\n".join(out)
