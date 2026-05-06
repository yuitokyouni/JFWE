"""
v1.23.2 — Validation Categories 5 + 6 (placeholder).

These two categories are **scaffolding only** at v1.23.2 —
no actual reviewer panel exists for Category 5, and the
null-model diff format is deferred for Category 6. The pins
assert only what the v1.23.2 design pin commits to:

**Category 5 — Inter-reviewer reproducibility (placeholder).**
- A ``tests/fixtures/inter_reviewer/`` directory exists with
  a stub format for reviewer notes.
- The example reviewer note parses as YAML.
- The example carries the v1.23.2-pinned closed-set
  ``reviewer_kind`` (``"human"``) and ``reasoning_mode``
  (``"human_authored"``) discipline.
- The example contains no v1.21.0a / v1.22.0 forbidden
  token anywhere in the YAML text (boundary scan).

**Category 6 — Null-model comparison (placeholder).**
- A fixture pair exists: a kernel with one stress program
  applied, and a kernel with no stress program applied.
- ``build_stress_readout_export_section`` returns a
  non-empty section for the with-stress kernel, and an
  empty section for the without-stress kernel.
- Both calls succeed (no exception). The diff itself is
  deferred.

The placeholders are additive scaffolding; v1.23.2 ships
**no** outcome metric, **no** statistical test, **no** real-
world series comparison, **no** new dataclass, **no** new
ledger event, **no** new label vocabulary.

Pin names:
- ``test_validation_placeholder_inter_reviewer_format_parseable``
- ``test_validation_placeholder_null_model_export_section_pair``
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS as CANONICAL_EXPORT_TOKENS,
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
from world.stress_readout_export import (
    build_stress_readout_export_section,
)


_INTER_REVIEWER_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "inter_reviewer"
)


# Closed-set discipline pinned at v1.23.2 for the placeholder
# format. v1.24+'s manual_annotation interaction layer will
# enforce these closed sets at runtime.
_REVIEWER_KIND_CLOSED_SET: frozenset[str] = frozenset(
    {"human"}
)
_REASONING_MODE_CLOSED_SET: frozenset[str] = frozenset(
    {"human_authored"}
)


# ---------------------------------------------------------------------------
# Local kernel fixtures.
# ---------------------------------------------------------------------------


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _build_template() -> ScenarioDriverTemplate:
    return ScenarioDriverTemplate(
        scenario_driver_template_id=(
            "scenario_driver:credit_tightening:reference"
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


def _seed_with_stress_kernel() -> WorldKernel:
    """Kernel with one stress program applied — non-empty
    stress-readout export section."""
    kernel = _bare_kernel()
    kernel.scenario_drivers.add_template(_build_template())
    program_id = (
        "stress_program:test_validation_null_model:with_stress"
    )
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="With-stress null-model fixture",
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
    apply_stress_program(
        kernel,
        stress_program_template_id=program_id,
        as_of_date="2026-04-30",
    )
    return kernel


def _seed_without_stress_kernel() -> WorldKernel:
    """Kernel with no stress program applied — empty
    stress-readout export section. The natural null model."""
    return _bare_kernel()


# ---------------------------------------------------------------------------
# Category 5 — inter-reviewer format placeholder.
# ---------------------------------------------------------------------------


def test_validation_placeholder_inter_reviewer_directory_exists() -> None:
    """The ``tests/fixtures/inter_reviewer/`` directory ships
    a README + at least one example reviewer note."""
    assert _INTER_REVIEWER_DIR.is_dir(), (
        "tests/fixtures/inter_reviewer/ missing — v1.23.2 "
        "placeholder scaffolding"
    )
    yaml_files = sorted(_INTER_REVIEWER_DIR.glob("*.yaml"))
    assert len(yaml_files) >= 1, (
        "tests/fixtures/inter_reviewer/ has no example "
        "reviewer note"
    )
    readme = _INTER_REVIEWER_DIR / "README.md"
    assert readme.is_file(), (
        "tests/fixtures/inter_reviewer/README.md missing"
    )


def test_validation_placeholder_inter_reviewer_format_parseable() -> None:
    """Every example reviewer note in
    ``tests/fixtures/inter_reviewer/`` parses as YAML and
    carries the v1.23.2 closed-set discipline; the YAML text
    contains no canonical forbidden token."""
    yaml_files = sorted(_INTER_REVIEWER_DIR.glob("*.yaml"))
    assert yaml_files, "no example reviewer notes found"
    for path in yaml_files:
        text = path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        assert isinstance(parsed, dict), (
            f"reviewer note {path.name!r} did not parse as a "
            "top-level mapping"
        )
        # v1.23.2 closed-set discipline.
        assert (
            parsed.get("reviewer_kind")
            in _REVIEWER_KIND_CLOSED_SET
        ), (
            f"reviewer note {path.name!r} reviewer_kind "
            f"{parsed.get('reviewer_kind')!r} is not in the "
            f"v1.23.2 closed set "
            f"{sorted(_REVIEWER_KIND_CLOSED_SET)!r}"
        )
        assert (
            parsed.get("reasoning_mode")
            in _REASONING_MODE_CLOSED_SET
        ), (
            f"reviewer note {path.name!r} reasoning_mode "
            f"{parsed.get('reasoning_mode')!r} is not in the "
            f"v1.23.2 closed set "
            f"{sorted(_REASONING_MODE_CLOSED_SET)!r}"
        )
        # Boundary scan: the YAML text contains no canonical
        # forbidden token (whole-word, case-insensitive).
        # ``human`` and ``human_authored`` are not in the
        # forbidden set, and the example notes deliberately
        # avoid trading-verb / outcome / forecast tokens.
        import re

        body = text.lower()
        for token in CANONICAL_EXPORT_TOKENS:
            pattern = rf"\b{re.escape(token.lower())}\b"
            assert re.search(pattern, body) is None, (
                f"reviewer note {path.name!r} contains "
                f"forbidden token {token!r}"
            )


# ---------------------------------------------------------------------------
# Category 6 — null-model comparison placeholder.
# ---------------------------------------------------------------------------


def test_validation_placeholder_null_model_export_section_pair() -> None:
    """The natural null model is a kernel with **no** stress
    program applied. v1.23.2 pins:

    - ``build_stress_readout_export_section`` returns a
      non-empty tuple for a kernel with one stress program
      applied;
    - ``build_stress_readout_export_section`` returns an
      empty tuple ``()`` for a kernel with no stress program
      applied;
    - both calls succeed without raising.

    The diff itself (which categories of citations differ
    between with-stress and without-stress) is deferred."""
    with_stress = _seed_with_stress_kernel()
    without_stress = _seed_without_stress_kernel()

    section_with = build_stress_readout_export_section(
        with_stress
    )
    section_without = build_stress_readout_export_section(
        without_stress
    )
    assert isinstance(section_with, tuple)
    assert isinstance(section_without, tuple)
    assert len(section_with) >= 1, (
        "with-stress kernel produced an empty "
        "stress_readout export section — fixture broken"
    )
    assert section_without == (), (
        "without-stress kernel produced a non-empty "
        f"stress_readout export section: {section_without!r}"
    )
