"""
v1.25.3 — Investor mandate context UI panel pin tests.

Pins the ``examples/ui/fwe_workbench_mockup.html``
v1.25.3 surface:

- the new "Investor mandate context" panel exists in
  the Universe sheet (no new tab);
- its empty / content / entries slots are present;
- the JS renderer ``renderInvestorMandateFromBundle``
  exists in the inline script and reads
  ``bundle.investor_mandate_readout``;
- the Validate self-check covers the new panel;
- the panel renderer uses ``textContent`` (never
  ``innerHTML``) for caller-supplied values;
- no new tab was added at v1.25.3 (11-tab ↔ 11-sheet
  bijection preserved);
- the panel surface contains no v1.25.0 forbidden
  wording (no allocation / target weight / performance
  / chart / score / red-or-green / buy / sell / trade /
  order / execution / forecast / recommendation).
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


def test_v1_25_3_investor_mandate_panel_exists() -> None:
    text = _read_ui_html()
    assert 'id="card-investor-mandate"' in text
    assert 'id="investor-mandate-empty"' in text
    assert 'id="investor-mandate-content"' in text
    assert 'id="investor-mandate-entries"' in text
    assert "Investor mandate context" in text
    assert "v1.25.3" in text


def test_v1_25_3_renderer_function_defined() -> None:
    text = _read_ui_html()
    assert (
        re.search(
            r"function\s+renderInvestorMandateFromBundle\s*\(",
            text,
        )
        is not None
    )
    assert "bundle.investor_mandate_readout" in text


def test_v1_25_3_renderer_called_from_local_bundle_load_path() -> None:
    text = _read_ui_html()
    calls = re.findall(
        r"renderInvestorMandateFromBundle\s*\(",
        text,
    )
    assert len(calls) >= 2


def test_v1_25_3_validate_self_check_covers_panel() -> None:
    text = _read_ui_html()
    assert "Investor mandate panel missing" in text
    assert "Investor mandate panel slots missing" in text
    assert "renderInvestorMandateFromBundle missing" in text


def test_v1_25_3_panel_uses_textcontent_only() -> None:
    """The panel entry-builder body uses ``textContent``
    (never ``innerHTML``) for caller-supplied values.
    The render function itself only orchestrates DOM
    insertion and does not write loaded values directly,
    so its body just needs to NOT use ``innerHTML``."""
    text = _read_ui_html()
    # The orchestrator must not assign to innerHTML.
    for fname in (
        "renderInvestorMandateFromBundle",
        "_buildInvestorMandateEntry",
    ):
        m = re.search(
            rf"function\s+{re.escape(fname)}\s*\([^)]*\)\s*\{{",
            text,
        )
        assert m is not None, f"{fname} not found"
        start = m.end()
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
        assert ".innerHTML" not in body, (
            f"{fname} assigns to innerHTML "
            "(textContent-only discipline violated)"
        )
    # The entry-builder must use textContent for caller-
    # supplied values.
    m = re.search(
        r"function\s+_buildInvestorMandateEntry\s*\([^)]*\)\s*\{",
        text,
    )
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    builder_body = text[start:i]
    assert ".textContent" in builder_body, (
        "_buildInvestorMandateEntry does not use "
        "textContent (caller-supplied values would be "
        "rendered via innerHTML)"
    )


def test_v1_25_3_no_new_tab_added() -> None:
    """v1.25.3 must not introduce a new tab."""
    text = _read_ui_html()
    tabs = re.findall(
        r'<button class="sheet-tab[^"]*"[^>]*data-sheet="([^"]+)"',
        text,
    )
    sheets = re.findall(
        r'<article id="sheet-([^"]+)"',
        text,
    )
    assert len(tabs) == len(sheets) == 11
    for t in tabs:
        assert "mandate" not in t.lower(), (
            f"unexpected mandate-related tab: {t!r}"
        )


def test_v1_25_3_panel_carries_no_forbidden_wording() -> None:
    """The HTML for the new panel carries no v1.25.0
    forbidden wording."""
    text = _read_ui_html()
    panel_idx = text.find('id="card-investor-mandate"')
    panel_close_idx = text.find("</section>", panel_idx)
    assert panel_idx >= 0 and panel_close_idx > panel_idx
    panel_block = text[panel_idx:panel_close_idx].lower()
    forbidden_phrases = (
        "allocation",
        "target weight",
        "overweight",
        "underweight",
        "rebalance",
        "performance",
        "alpha",
        "tracking error",
        "expected return",
        "target price",
        "buy",
        "sell",
        "order",
        "trade",
        "execution",
        "forecast",
        "prediction",
        "recommendation",
        "investment advice",
        "impact",
        "outcome",
        "risk score",
        "amplification",
        "dampening",
    )
    for phrase in forbidden_phrases:
        assert phrase not in panel_block, (
            f"forbidden phrase {phrase!r} appears in "
            "the Investor mandate panel HTML"
        )


def test_v1_25_3_existing_panels_still_present() -> None:
    """The v1.22.2 Active Stresses + v1.24.3 Manual
    annotations panels are still present alongside
    the new v1.25.3 panel."""
    text = _read_ui_html()
    assert 'id="card-active-stresses"' in text
    assert 'id="card-manual-annotations"' in text
    assert 'id="card-investor-mandate"' in text
