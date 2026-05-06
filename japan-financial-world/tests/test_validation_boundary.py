"""
v1.23.2 — Validation Category 2: Boundary preservation.

Every emitted ``StressFieldReadout`` must satisfy the v1.21.0a
+ v1.22.0 forbidden-name boundary at every load-bearing
surface. v1.23.2 promotes the four scans into a named
validation pin:

1. **Dataclass field-name scan** — the ``StressFieldReadout``
   field set has zero overlap with
   ``world.forbidden_tokens.FORBIDDEN_STRESS_READOUT_FIELD_NAMES``
   (already enforced by ``StressFieldReadout.__post_init__``;
   v1.23.2 re-pins the contract against the v1.23.1 canonical
   composition).
2. **Metadata-key scan** — the readout's ``metadata`` mapping
   contains no key in the canonical forbidden set (already
   enforced at construction; v1.23.2 re-pins it).
3. **Markdown-render scan** — the v1.21.3 markdown summary
   does not contain any descriptive forbidden token
   (``aggregate``, ``combined``, ``net``, ``dominant``,
   ``composite``, ``amplification``, etc.) outside the pinned
   boundary-statement disclaimer block (which legitimately
   mentions ``execution``, ``order``, etc. as
   ``No <token>`` anti-claims).
4. **Export-section scan** — the v1.22.1 export entry
   contains no forbidden token at any depth.

The pin reuses the canonical
``world.forbidden_tokens.FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS``
composition (BASE + v1.22.0 export delta + v1.21.0a stress
delta). The boundary-statement section is stripped before the
markdown scan because the v1.21.3 renderer pins a
deterministic anti-claim block that references each forbidden
token under the negation form ("No interaction inference",
"No execution", "No order"); the negation contract is itself
the boundary preservation guarantee.

Pin name: ``test_validation_boundary_preservation_pin_v1_23_2``
(split into named sub-tests for diagnostic clarity).
"""

from __future__ import annotations

import re
from dataclasses import fields as dataclass_fields
from datetime import date

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS as CANONICAL_EXPORT_TOKENS,
    FORBIDDEN_STRESS_READOUT_FIELD_NAMES as CANONICAL_READOUT_FIELDS,
)
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.scenario_drivers import ScenarioDriverTemplate
from world.scheduler import Scheduler
from world.state import State
from world.stress_applications import apply_stress_program
from world.stress_programs import (
    StressProgramTemplate,
    StressStep,
)
from world.stress_readout import (
    StressFieldReadout,
    build_stress_field_readout,
    render_stress_field_summary_markdown,
)
from world.stress_readout_export import (
    stress_field_readout_to_export_entry,
)


# ---------------------------------------------------------------------------
# Local fixture (mirrors the determinism pin's two-step
# program — single-step + multi-step exercises both branches).
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


def _seed_two_step_kernel() -> tuple[WorldKernel, str]:
    kernel = _bare_kernel()
    tpl_ids = (
        "scenario_driver:credit_tightening:reference",
        "scenario_driver:funding_window_closure:reference",
    )
    for tpl_id in tpl_ids:
        kernel.scenario_drivers.add_template(
            _build_template(scenario_driver_template_id=tpl_id)
        )
    program_id = "stress_program:test_validation_boundary:two_step"
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="Two-step boundary pin",
        program_purpose_label="twin_credit_funding_stress",
        stress_steps=(
            StressStep(
                stress_step_id=f"{program_id}:step:0",
                parent_stress_program_template_id=program_id,
                step_index=0,
                scenario_driver_template_id=tpl_ids[0],
                event_date_policy_label="quarter_end",
                scheduled_month_label="month_04",
            ),
            StressStep(
                stress_step_id=f"{program_id}:step:1",
                parent_stress_program_template_id=program_id,
                step_index=1,
                scenario_driver_template_id=tpl_ids[1],
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
    )
    return kernel, receipt.stress_program_application_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_boundary_statement(markdown: str) -> str:
    """Strip the v1.21.3 ``## Boundary statement`` section.

    The boundary statement is a pinned anti-claim disclaimer
    that legitimately references each forbidden token under
    its negation form ("No execution", "No order", "No
    trade"); the negation contract is itself the boundary
    preservation guarantee. Scanning the boundary statement
    for raw forbidden tokens is a false-positive surface."""
    idx = markdown.find("## Boundary statement")
    if idx < 0:
        return markdown
    return markdown[:idx]


def _walk_keys_and_string_values(value):
    """Walk a JSON-like value (dict / list / scalar) and yield
    every dict key + every string value at any depth."""
    if isinstance(value, str):
        yield ("value", value)
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str):
                yield ("key", k)
            yield from _walk_keys_and_string_values(v)
        return
    if isinstance(value, (list, tuple)):
        for entry in value:
            yield from _walk_keys_and_string_values(entry)


# ---------------------------------------------------------------------------
# 1. Dataclass field-name scan.
# ---------------------------------------------------------------------------


def test_validation_boundary_preservation_pin_v1_23_2_dataclass_fields() -> None:
    """The :class:`StressFieldReadout` dataclass field set
    has zero overlap with the canonical
    ``FORBIDDEN_STRESS_READOUT_FIELD_NAMES``."""
    field_names = {f.name for f in dataclass_fields(StressFieldReadout)}
    overlap = field_names & CANONICAL_READOUT_FIELDS
    assert overlap == set(), (
        "StressFieldReadout fields overlap with canonical "
        f"forbidden set: {sorted(overlap)!r}"
    )


# ---------------------------------------------------------------------------
# 2. Metadata-key scan (already enforced at construction;
#    re-pinned against the canonical composition).
# ---------------------------------------------------------------------------


def test_validation_boundary_preservation_pin_v1_23_2_metadata_keys() -> None:
    """A readout's metadata mapping carries no key in the
    canonical forbidden set."""
    kernel, receipt_id = _seed_two_step_kernel()
    readout = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    md = readout.metadata or {}
    overlap = set(md.keys()) & CANONICAL_READOUT_FIELDS
    assert overlap == set(), (
        f"readout.metadata keys overlap with canonical "
        f"forbidden set: {sorted(overlap)!r}"
    )


# ---------------------------------------------------------------------------
# 3. Markdown-render scan against the canonical composed
#    export-token set, with the boundary-statement section
#    stripped.
# ---------------------------------------------------------------------------


def test_validation_boundary_preservation_pin_v1_23_2_markdown_render() -> None:
    """The v1.21.3 markdown summary contains no canonical
    forbidden token outside the pinned boundary-statement
    disclaimer block. Scan is whole-word (``\\btoken\\b``) so
    legitimate substrings like ``stress_program_application``
    do not false-positive on the bare token ``program``."""
    kernel, receipt_id = _seed_two_step_kernel()
    readout = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    md = render_stress_field_summary_markdown(readout)
    body = _strip_boundary_statement(md).lower()
    offenders: list[str] = []
    for token in CANONICAL_EXPORT_TOKENS:
        pattern = rf"\b{re.escape(token.lower())}\b"
        if re.search(pattern, body):
            offenders.append(token)
    assert offenders == [], (
        "Markdown summary (excluding boundary statement) "
        "contains canonical forbidden tokens: "
        f"{sorted(offenders)!r}"
    )


# ---------------------------------------------------------------------------
# 4. v1.22.1 export-entry scan — every key + every string
#    value at any depth must satisfy the canonical forbidden
#    set discipline (keys: no exact-equality match; values:
#    no whole-string equality match — the existing v1.22.1
#    runtime scan already enforces this).
# ---------------------------------------------------------------------------


def test_validation_boundary_preservation_pin_v1_23_2_export_entry() -> None:
    """The v1.22.1 stress-readout export entry contains no
    canonical forbidden token at any depth — neither as a
    key nor as a whole-string value."""
    kernel, receipt_id = _seed_two_step_kernel()
    readout = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    entry = stress_field_readout_to_export_entry(readout)
    key_offenders: list[str] = []
    value_offenders: list[str] = []
    for kind, item in _walk_keys_and_string_values(entry):
        if kind == "key" and item in CANONICAL_EXPORT_TOKENS:
            key_offenders.append(item)
        if kind == "value" and item in CANONICAL_EXPORT_TOKENS:
            value_offenders.append(item)
    assert key_offenders == [], (
        "Export entry has keys in the canonical forbidden "
        f"set: {sorted(set(key_offenders))!r}"
    )
    assert value_offenders == [], (
        "Export entry has whole-string values in the "
        f"canonical forbidden set: "
        f"{sorted(set(value_offenders))!r}"
    )
