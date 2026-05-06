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
    """Replace (or append) the v1.23.1 + v1.23.2 inventory
    blocks in ``docs/test_inventory.md``. Both blocks carry
    the same current ``test_count`` — the most recent
    milestone's pin reflects the post-milestone collection
    total."""
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
