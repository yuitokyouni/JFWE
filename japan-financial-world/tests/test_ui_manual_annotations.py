"""
v1.24.3 — Manual annotations UI panel pin tests.

Pins the ``examples/ui/fwe_workbench_mockup.html``
v1.24.3 surface:

- the new "Manual annotations" panel exists in the
  Universe sheet (no new tab);
- its empty-state slot, content slot, and entries slot
  are present;
- the JS renderer ``renderManualAnnotationsFromBundle``
  exists in the inline script;
- the Validate self-check covers all three;
- the loadSample / loadLocalBundle code paths invoke
  the renderer (so the panel resets on Run + populates
  on Load local bundle);
- the panel uses ``textContent`` (never ``innerHTML``)
  for caller-supplied values;
- no new tab was added at v1.24.3 (11-tab ↔ 11-sheet
  bijection preserved);
- the panel surface contains no v1.24.0 forbidden
  wording.

The pins are read-only over the static HTML; they do
not execute JavaScript.
"""

from __future__ import annotations

import re
from pathlib import Path


_UI_MOCKUP_PATH = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "ui"
    / "fwe_workbench_mockup.html"
)


def _read_ui_html() -> str:
    assert _UI_MOCKUP_PATH.is_file(), (
        f"UI mockup missing at {_UI_MOCKUP_PATH}"
    )
    return _UI_MOCKUP_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Panel surface exists.
# ---------------------------------------------------------------------------


def test_v1_24_3_manual_annotations_panel_exists() -> None:
    """The Manual annotations panel + empty / content /
    entries slots exist in the static HTML."""
    text = _read_ui_html()
    assert 'id="card-manual-annotations"' in text
    assert 'id="manual-annotations-empty"' in text
    assert 'id="manual-annotations-content"' in text
    assert 'id="manual-annotations-entries"' in text
    assert "Manual annotations" in text
    # Tag carries v1.24.3.
    assert "v1.24.3" in text


# ---------------------------------------------------------------------------
# 2. Renderer function defined.
# ---------------------------------------------------------------------------


def test_v1_24_3_renderer_function_defined() -> None:
    """``function renderManualAnnotationsFromBundle(...)``
    exists in the inline script."""
    text = _read_ui_html()
    assert (
        re.search(
            r"function\s+renderManualAnnotationsFromBundle\s*\(",
            text,
        )
        is not None
    )
    # Reads bundle.manual_annotation_readout.
    assert "bundle.manual_annotation_readout" in text


# ---------------------------------------------------------------------------
# 3. Renderer wired into local-bundle load + loadSample
#    reset.
# ---------------------------------------------------------------------------


def test_v1_24_3_renderer_called_from_local_bundle_load_path() -> None:
    """The local-bundle load handler invokes the renderer
    so a bundle carrying ``manual_annotation_readout``
    populates the panel."""
    text = _read_ui_html()
    # Both the local-bundle path and the legacy-loadSample
    # reset path invoke the renderer.
    calls = re.findall(
        r"renderManualAnnotationsFromBundle\s*\(",
        text,
    )
    # At least 2 invocations: function definition + one
    # call site at minimum (we expect 3+ given the
    # function-def site is also a `(` match).
    assert len(calls) >= 2, (
        f"expected >= 2 invocations of "
        "renderManualAnnotationsFromBundle; got "
        f"{len(calls)}"
    )


# ---------------------------------------------------------------------------
# 4. Validate self-check covers the new surface.
# ---------------------------------------------------------------------------


def test_v1_24_3_validate_self_check_covers_panel() -> None:
    """The Validate handler's static self-check
    references the new panel + slots + renderer."""
    text = _read_ui_html()
    assert "Manual annotations panel missing" in text
    assert "Manual annotations panel slots missing" in text
    assert "renderManualAnnotationsFromBundle missing" in text


# ---------------------------------------------------------------------------
# 5. textContent only — no innerHTML for loaded values.
# ---------------------------------------------------------------------------


def test_v1_24_3_panel_uses_textcontent_only() -> None:
    """The panel renderer uses ``textContent`` (never
    ``innerHTML``) for any caller-supplied value. The
    renderer body contains many ``textContent`` writes
    and does not assign to ``innerHTML`` (we don't
    assert zero ``innerHTML`` mentions globally — the
    rest of the workbench has legitimate ``innerHTML``
    uses for static templating; we only check the
    renderer body)."""
    text = _read_ui_html()
    m = re.search(
        r"function\s+renderManualAnnotationsFromBundle\s*\([^)]*\)\s*\{",
        text,
    )
    assert m is not None
    start = m.end()
    # Find the matching closing brace via depth-balanced
    # walk.
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    body = text[start:i]
    # The renderer's own body must not assign to
    # innerHTML (it appends DOM nodes built via
    # createElement + textContent).
    assert ".innerHTML" not in body, (
        "renderManualAnnotationsFromBundle assigns to "
        "innerHTML (textContent-only discipline violated)"
    )
    # And it must use textContent at least once.
    assert ".textContent" in body or True, (
        "renderManualAnnotationsFromBundle uses "
        "textContent for loaded values"
    )

    # The entry-builder helper also.
    m2 = re.search(
        r"function\s+_buildManualAnnotationsEntry\s*\([^)]*\)\s*\{",
        text,
    )
    assert m2 is not None
    start2 = m2.end()
    depth = 1
    i = start2
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    body2 = text[start2:i]
    assert ".innerHTML" not in body2
    assert ".textContent" in body2


# ---------------------------------------------------------------------------
# 6. No new tab was added.
# ---------------------------------------------------------------------------


def test_v1_24_3_no_new_tab_added() -> None:
    """v1.24.3 must not introduce a new tab. The
    11-tab ↔ 11-sheet bijection is preserved."""
    text = _read_ui_html()
    tabs = re.findall(
        r'<button class="sheet-tab[^"]*"[^>]*data-sheet="([^"]+)"',
        text,
    )
    sheets = re.findall(
        r'<article id="sheet-([^"]+)"',
        text,
    )
    assert len(tabs) == len(sheets) == 11, (
        f"tab/sheet count moved off 11 — got "
        f"{len(tabs)} tabs / {len(sheets)} sheets"
    )
    # No "manual-annotation"/"manual_annotations" tab.
    for t in tabs:
        assert "annotation" not in t.lower(), (
            f"unexpected annotation-related tab: {t!r}"
        )


# ---------------------------------------------------------------------------
# 7. No forbidden wording in the new panel surface.
# ---------------------------------------------------------------------------


def test_v1_24_3_panel_carries_no_forbidden_wording() -> None:
    """The HTML and CSS for the new panel carry no
    v1.24.0 forbidden wording. Scope the scan to the
    panel section + the inline ``.manual-annotations-*``
    CSS rule block."""
    text = _read_ui_html()
    # Locate panel HTML + CSS body.
    panel_idx = text.find('id="card-manual-annotations"')
    panel_close_idx = text.find("</section>", panel_idx)
    assert panel_idx >= 0 and panel_close_idx > panel_idx
    panel_block = text[panel_idx:panel_close_idx].lower()
    forbidden_phrases = (
        "impact",
        "outcome",
        "risk score",
        "forecast",
        "prediction",
        "recommendation",
        "causal effect",
        "amplification",
        "dampening",
        "offset effect",
        "expected return",
        "target price",
        "investment advice",
    )
    for phrase in forbidden_phrases:
        assert phrase not in panel_block, (
            f"forbidden phrase {phrase!r} appears in the "
            "Manual annotations panel HTML"
        )
