"""
v1.23.x — Refresh ``docs/test_inventory.md`` substrate-hardening
+ validation-foundation entries.

Runs ``pytest --collect-only -q`` from the repo's
``japan-financial-world`` directory, parses the
``NNNN tests collected`` line, and writes /
overwrites the ``v1.23.1`` and ``v1.23.2`` entries in
``docs/test_inventory.md``.

Idempotent: running twice produces the same output.

Usage:

    cd japan-financial-world
    python examples/tools/refresh_test_inventory.py

The script does not commit / push anything; it only
rewrites the doc in-place. Future contributors run this
as part of every milestone freeze checklist (per
``RELEASE_CHECKLIST.md``).

The script is **read-only with respect to runtime**: it
runs ``pytest --collect-only`` (no test execution) and
mutates only ``docs/test_inventory.md``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DOC_PATH = _REPO_ROOT / "docs" / "test_inventory.md"


# Lines emitted / parsed by the refresh script. The
# freshness test in
# ``tests/test_test_inventory_currency.py`` parses the same
# regex.
_V1_23_1_LINE_PREFIX = "v1.23.1 test count: "
_V1_23_1_BLOCK_RE = re.compile(
    r"<!-- v1\.23\.1 test inventory pin: BEGIN -->"
    r".*?"
    r"<!-- v1\.23\.1 test inventory pin: END -->",
    re.DOTALL,
)
_PYTEST_COLLECTED_RE = re.compile(
    r"^(\d+)\s+tests?\s+collected", re.MULTILINE
)


def _run_pytest_collect_only() -> int:
    """Run ``pytest --collect-only`` and parse the test
    count from its output. Returns the integer count."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
        ],
        check=False,
        capture_output=True,
        cwd=str(_REPO_ROOT),
        text=True,
    )
    combined = result.stdout + "\n" + result.stderr
    # ``pytest -q`` does not print the summary by default
    # but ``--collect-only`` does. Try matching either.
    m = _PYTEST_COLLECTED_RE.search(combined)
    if m is None:
        # Fallback: re-run without -q so we can get the
        # detailed collection summary.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
            ],
            check=False,
            capture_output=True,
            cwd=str(_REPO_ROOT),
            text=True,
        )
        combined = result.stdout + "\n" + result.stderr
        m = _PYTEST_COLLECTED_RE.search(combined)
    if m is None:
        raise RuntimeError(
            "Could not parse 'NNNN tests collected' from "
            f"pytest --collect-only output:\n{combined[:2000]}"
        )
    return int(m.group(1))


def _format_v1_23_1_block(test_count: int) -> str:
    """Return the v1.23.1 inventory block in the canonical
    format. The block is marked with HTML comments so the
    refresh script can replace it idempotently."""
    return (
        "<!-- v1.23.1 test inventory pin: BEGIN -->\n"
        "\n"
        "## v1.23.1 — Substrate hardening\n"
        "\n"
        "v1.23.1 ships:\n"
        "\n"
        "- ``tests/_canonical_digests.py`` — canonical "
        "living-world digest module (single source of "
        "truth for the four canonical digests);\n"
        "- ``world/forbidden_tokens.py`` — composable "
        "forbidden-name vocabulary (BASE + per-milestone "
        "deltas + canonical composed sets, including "
        "the v1.23.1 run-export leak-fix);\n"
        "- v1.21.2 ↔ v1.21.3 metadata-stamp contract "
        "constants in ``world/stress_applications.py`` "
        "(``STRESS_PROGRAM_APPLICATION_ID_METADATA_KEY``, "
        "``STRESS_STEP_ID_METADATA_KEY``);\n"
        "- runtime cardinality cap "
        "``STRESS_PROGRAM_RUN_RECORD_CAP = 60`` + "
        "``StressProgramRecordCapExceededError`` "
        "trip-wire in ``apply_stress_program(...)``;\n"
        "- this v1.23.1 inventory entry + the freshness "
        "pin in "
        "``tests/test_test_inventory_currency.py``;\n"
        "- the refresh generator at "
        "``examples/tools/refresh_test_inventory.py``.\n"
        "\n"
        "No digest movement: the v1.18.last / v1.19.last / "
        "v1.20.last / v1.21.last / v1.22.last canonical "
        "``living_world_digest`` values remain "
        "byte-identical at v1.23.1.\n"
        "\n"
        f"{_V1_23_1_LINE_PREFIX}{test_count}\n"
        "\n"
        "<!-- v1.23.1 test inventory pin: END -->\n"
    )


_V1_23_2_LINE_PREFIX = "v1.23.2 test count: "
_V1_23_2_BLOCK_RE = re.compile(
    r"<!-- v1\.23\.2 test inventory pin: BEGIN -->"
    r".*?"
    r"<!-- v1\.23\.2 test inventory pin: END -->",
    re.DOTALL,
)


_V1_23_3_LINE_PREFIX = "v1.23.3 test count: "
_V1_23_3_BLOCK_RE = re.compile(
    r"<!-- v1\.23\.3 test inventory pin: BEGIN -->"
    r".*?"
    r"<!-- v1\.23\.3 test inventory pin: END -->",
    re.DOTALL,
)


_V1_23_LAST_LINE_PREFIX = "v1.23.last test count: "
_V1_23_LAST_BLOCK_RE = re.compile(
    r"<!-- v1\.23\.last test inventory pin: BEGIN -->"
    r".*?"
    r"<!-- v1\.23\.last test inventory pin: END -->",
    re.DOTALL,
)


_V1_24_LAST_LINE_PREFIX = "v1.24.last test count: "
_V1_24_LAST_BLOCK_RE = re.compile(
    r"<!-- v1\.24\.last test inventory pin: BEGIN -->"
    r".*?"
    r"<!-- v1\.24\.last test inventory pin: END -->",
    re.DOTALL,
)


def _format_v1_24_last_block(test_count: int) -> str:
    """Return the v1.24.last final-freeze inventory block."""
    return (
        "<!-- v1.24.last test inventory pin: BEGIN -->\n"
        "\n"
        "## v1.24.last — Manual Annotation Interaction "
        "Layer freeze (docs-only)\n"
        "\n"
        "Final freeze section for the v1.24 sequence. "
        "v1.24.last ships **no** new code, **no** new "
        "tests, **no** new RecordTypes, **no** new "
        "dataclasses, **no** new label vocabularies, "
        "**no** UI regions, **no** export-schema changes. "
        "The v1.24 sequence is closed.\n"
        "\n"
        "Sub-milestones shipped:\n"
        "\n"
        "- v1.24.0 (docs-only design pin — manual "
        "annotation layer)\n"
        "- v1.24.1 (storage — ManualAnnotationRecord + "
        "ManualAnnotationBook + closed-set vocabularies + "
        "MANUAL_ANNOTATION_RECORDED ledger event type + "
        "empty-by-default kernel field)\n"
        "- v1.24.2 (read-only readout — "
        "ManualAnnotationReadout + markdown renderer + "
        "optional non-mandatory v1.23.2 validation hook)\n"
        "- v1.24.3 (descriptive-only export section "
        "(omitted when empty) + minimal Universe-sheet "
        "Manual annotations panel; no new tab; "
        "textContent only)\n"
        "- v1.24.last (this freeze)\n"
        "\n"
        "Hard boundary re-pinned: human-authored only "
        "(``source_kind = \"human\"`` / "
        "``reasoning_mode = \"human_authored\"``); no "
        "auto-annotation; no LLM-authored annotation in "
        "public v1.x; no causal proof; no stress "
        "interaction inference (``amplify`` / "
        "``dampen`` / ``offset`` / ``coexist`` "
        "explicitly excluded from ANNOTATION_LABELS); no "
        "actor-behavior trigger; no source-of-truth "
        "book mutation. All v1.21.last canonical "
        "``living_world_digest`` values remain byte-"
        "identical at every v1.24.x sub-milestone.\n"
        "\n"
        f"{_V1_24_LAST_LINE_PREFIX}{test_count}\n"
        "\n"
        "<!-- v1.24.last test inventory pin: END -->\n"
    )


def _format_v1_23_last_block(test_count: int) -> str:
    """Return the v1.23.last final-freeze inventory block."""
    return (
        "<!-- v1.23.last test inventory pin: BEGIN -->\n"
        "\n"
        "## v1.23.last — Substrate Hardening + Validation "
        "Foundation freeze (docs-only)\n"
        "\n"
        "Final freeze section for the v1.23 sequence. "
        "v1.23.last ships **no** new code, **no** new tests, "
        "**no** new RecordTypes, **no** new dataclasses, "
        "**no** new label vocabularies, **no** UI regions, "
        "**no** export-schema changes. The v1.23 sequence is "
        "closed.\n"
        "\n"
        "Sub-milestones shipped in the v1.23 sequence:\n"
        "\n"
        "- v1.23.0 (docs-only design pin)\n"
        "- v1.23.1 (substrate hardening — canonical digest "
        "module + composable forbidden-token vocabulary + "
        "cross-layer metadata stamp constants + "
        "``STRESS_PROGRAM_RUN_RECORD_CAP = 60`` + "
        "test-inventory currency pin)\n"
        "- v1.23.2 (validation foundation — four pinnable "
        "categories + two placeholder categories + research "
        "note 002)\n"
        "- v1.23.2a / v1.23.2b (static-UI maintenance — "
        "single Run button, ribbon overflow hardened, "
        "inline fixture labelled legacy, Meta trail "
        "extended)\n"
        "- v1.23.3 (attention-crowding / uncited-stress "
        "case study — read-only helper + deterministic "
        "markdown + companion narrative)\n"
        "- v1.23.last (this freeze)\n"
        "\n"
        "All v1.21.last canonical ``living_world_digest`` "
        "values remain byte-identical at every v1.23.x "
        "sub-milestone. v1.23.x ships a validation "
        "foundation, not a validation proof.\n"
        "\n"
        f"{_V1_23_LAST_LINE_PREFIX}{test_count}\n"
        "\n"
        "<!-- v1.23.last test inventory pin: END -->\n"
    )


def _format_v1_23_3_block(test_count: int) -> str:
    """Return the v1.23.3 inventory block in the canonical
    format. Marked with HTML comments for idempotent
    replacement."""
    return (
        "<!-- v1.23.3 test inventory pin: BEGIN -->\n"
        "\n"
        "## v1.23.3 — Attention-crowding / uncited-stress "
        "case study\n"
        "\n"
        "v1.23.3 ships:\n"
        "\n"
        "- ``world/stress_case_study.py`` — read-only helper "
        "that builds a deterministic case-study report dict "
        "(cited / uncited step ids, scenario application + "
        "shift ids, v1.21.3 readout summary, v1.23.2 "
        "Cat 1-4 pin summary, boundary statement) over an "
        "already stress-applied kernel + a deterministic "
        "markdown renderer for the report;\n"
        "- ``tests/test_attention_crowding_case_study.py`` "
        "— pin tests covering determinism / uncited-stress "
        "visibility / citation completeness / boundary "
        "preservation / no-mutation / no-ledger-emission / "
        "no-apply-helper-call / required markdown sections "
        "/ Cat 4 visibility;\n"
        "- ``docs/case_study_001_attention_crowding_uncited_stress.md`` "
        "— narrative case-study doc framing the report as a "
        "research-defensible read-only demonstration of what "
        "the v1.21.3 stress citation graph reveals.\n"
        "\n"
        "Read-only / no-mutation discipline: the helper does "
        "**not** call ``apply_stress_program`` or "
        "``apply_scenario_driver``, does **not** mutate any "
        "kernel book, does **not** emit a ledger record, and "
        "introduces **no** new dataclass / RecordType / label "
        "vocabulary / UI surface / export-schema field. All "
        "v1.18.last / v1.19.last / v1.20.last / v1.21.last / "
        "v1.22.last canonical ``living_world_digest`` values "
        "remain byte-identical at v1.23.3.\n"
        "\n"
        f"{_V1_23_3_LINE_PREFIX}{test_count}\n"
        "\n"
        "<!-- v1.23.3 test inventory pin: END -->\n"
    )


def _format_v1_23_2_block(test_count: int) -> str:
    """Return the v1.23.2 inventory block in the canonical
    format. Marked with HTML comments for idempotent
    replacement."""
    return (
        "<!-- v1.23.2 test inventory pin: BEGIN -->\n"
        "\n"
        "## v1.23.2 — Validation foundation\n"
        "\n"
        "v1.23.2 ships:\n"
        "\n"
        "- ``tests/test_validation_determinism.py`` — "
        "Validation Category 1 (determinism) pin tests;\n"
        "- ``tests/test_validation_boundary.py`` — "
        "Validation Category 2 (boundary preservation) pin "
        "tests against the v1.23.1 canonical "
        "``world.forbidden_tokens`` composition;\n"
        "- ``tests/test_validation_citation_completeness.py`` "
        "— Validation Category 3 (citation completeness) "
        "pin tests, including a dangling-citation "
        "regression-class detection path;\n"
        "- ``tests/test_validation_partial_application_visibility.py`` "
        "— Validation Category 4 (partial-application "
        "visibility) pin tests covering the v1.21.3 "
        "markdown summary's PARTIAL APPLICATION banner "
        "and the v1.22.1 export-entry visibility "
        "fields;\n"
        "- ``tests/test_validation_placeholder_categories.py`` "
        "— Categories 5 (inter-reviewer reproducibility) "
        "+ 6 (null-model comparison) **placeholder** pins;\n"
        "- ``tests/fixtures/inter_reviewer/`` — Category 5 "
        "format-placeholder directory + example reviewer "
        "note;\n"
        "- ``docs/research_note_002_validating_stress_citation_graphs_without_price_prediction.md`` "
        "— companion research note.\n"
        "\n"
        "Read-only validation only: every pin asserts a "
        "property of the audit object, never compares the "
        "readout to a real-world series. v1.23.2 ships **no** "
        "outcome metric, **no** statistical test, **no** new "
        "dataclass, **no** new ledger event, **no** new label "
        "vocabulary. All v1.18.last / v1.19.last / "
        "v1.20.last / v1.21.last / v1.22.last canonical "
        "``living_world_digest`` values remain byte-identical "
        "at v1.23.2.\n"
        "\n"
        f"{_V1_23_2_LINE_PREFIX}{test_count}\n"
        "\n"
        "<!-- v1.23.2 test inventory pin: END -->\n"
    )


def refresh_inventory(test_count: int) -> None:
    """Replace (or append) the v1.23.1 + v1.23.2 + v1.23.3
    inventory blocks in ``docs/test_inventory.md``. All
    blocks carry the same current ``test_count`` — the most
    recent milestone's pin reflects the post-milestone
    collection total."""
    text = _DOC_PATH.read_text(encoding="utf-8")

    # v1.23.1 block.
    block_1 = _format_v1_23_1_block(test_count)
    if _V1_23_1_BLOCK_RE.search(text):
        text = _V1_23_1_BLOCK_RE.sub(
            block_1.rstrip("\n"), text
        )
    else:
        if not text.endswith("\n"):
            text += "\n"
        text = text + "\n" + block_1

    # v1.23.2 block.
    block_2 = _format_v1_23_2_block(test_count)
    if _V1_23_2_BLOCK_RE.search(text):
        text = _V1_23_2_BLOCK_RE.sub(
            block_2.rstrip("\n"), text
        )
    else:
        if not text.endswith("\n"):
            text += "\n"
        text = text + "\n" + block_2

    # v1.23.3 block.
    block_3 = _format_v1_23_3_block(test_count)
    if _V1_23_3_BLOCK_RE.search(text):
        text = _V1_23_3_BLOCK_RE.sub(
            block_3.rstrip("\n"), text
        )
    else:
        if not text.endswith("\n"):
            text += "\n"
        text = text + "\n" + block_3

    # v1.23.last freeze block.
    block_last = _format_v1_23_last_block(test_count)
    if _V1_23_LAST_BLOCK_RE.search(text):
        text = _V1_23_LAST_BLOCK_RE.sub(
            block_last.rstrip("\n"), text
        )
    else:
        if not text.endswith("\n"):
            text += "\n"
        text = text + "\n" + block_last

    # v1.24.last freeze block.
    block_v1_24_last = _format_v1_24_last_block(test_count)
    if _V1_24_LAST_BLOCK_RE.search(text):
        text = _V1_24_LAST_BLOCK_RE.sub(
            block_v1_24_last.rstrip("\n"), text
        )
    else:
        if not text.endswith("\n"):
            text += "\n"
        text = text + "\n" + block_v1_24_last

    _DOC_PATH.write_text(text, encoding="utf-8")


def main() -> int:
    test_count = _run_pytest_collect_only()
    refresh_inventory(test_count)
    print(
        f"refreshed {_DOC_PATH.relative_to(_REPO_ROOT)} "
        f"with current test count = {test_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
