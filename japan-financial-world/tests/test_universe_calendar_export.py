"""
v1.26.4 — Universe / calendar export + UI pin tests.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES,
)
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.reporting_calendar_profiles import (
    ReportingCalendarProfile,
)
from world.run_export import (
    build_run_export_bundle,
    bundle_to_dict,
)
from world.scheduler import Scheduler
from world.state import State
from world.universe_calendar_export import (
    UNIVERSE_CALENDAR_READOUT_EXPORT_REQUIRED_KEYS,
    build_universe_calendar_readout_export_section,
)
from world.universe_calendar_readout import (
    build_universe_calendar_readout,
)
from world.universe_events import UniverseEventRecord

from _canonical_digests import (
    QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
)


_UI_MOCKUP_PATH = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "ui"
    / "fwe_workbench_mockup.html"
)


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _bundle(**kw):
    return build_run_export_bundle(
        bundle_id="run_bundle:v1_26_4:test",
        run_profile_label="quarterly_default",
        regime_label="constrained",
        period_count=4,
        digest=QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
        **kw,
    )


def test_export_omits_universe_calendar_readout_when_absent() -> None:
    b = _bundle()
    d = bundle_to_dict(b)
    assert "universe_calendar_readout" not in d
    assert b.universe_calendar_readout == ()


def test_no_universe_calendar_bundle_digest_unchanged() -> None:
    b = _bundle()
    d = bundle_to_dict(b)
    assert d["digest"] == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST
    assert "universe_calendar_readout" not in d


def test_export_includes_universe_calendar_readout_when_present() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        UniverseEventRecord(
            universe_event_id="ue:1",
            effective_period_id="2026-Q1-month_03",
            event_type_label="entity_listed",
            affected_entity_ids=("firm:a",),
        )
    )
    kernel.reporting_calendars.add_profile(
        ReportingCalendarProfile(
            reporting_calendar_profile_id="rcp:a",
            entity_id="firm:a",
            fiscal_year_end_month_label="month_03",
            quarterly_reporting_month_labels=("month_03",),
            disclosure_cluster_label="moderate",
            reporting_intensity_label="medium",
        )
    )
    section = build_universe_calendar_readout_export_section(
        kernel, as_of_period_id="2026-Q4-month_12"
    )
    assert len(section) == 1
    b = _bundle(universe_calendar_readout=section)
    d = bundle_to_dict(b)
    assert "universe_calendar_readout" in d
    assert len(d["universe_calendar_readout"]) == 1
    entry = d["universe_calendar_readout"][0]
    assert "firm:a" in entry["active_entity_ids"]


def test_export_keys_are_descriptive_only() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        UniverseEventRecord(
            universe_event_id="ue:1",
            effective_period_id="2026-Q1-month_03",
            event_type_label="entity_listed",
            affected_entity_ids=("firm:a",),
        )
    )
    readout = build_universe_calendar_readout(
        kernel, as_of_period_id="2026-Q4-month_12"
    )
    from world.universe_calendar_export import (
        universe_calendar_readout_to_export_entry,
    )
    entry = universe_calendar_readout_to_export_entry(readout)
    assert (
        set(entry.keys())
        == UNIVERSE_CALENDAR_READOUT_EXPORT_REQUIRED_KEYS
    )


def test_forbidden_wording_absent_from_export() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        UniverseEventRecord(
            universe_event_id="ue:1",
            effective_period_id="2026-Q1-month_03",
            event_type_label="entity_listed",
            affected_entity_ids=("firm:a",),
        )
    )
    section = build_universe_calendar_readout_export_section(
        kernel, as_of_period_id="2026-Q4-month_12"
    )
    entry = section[0]

    def walk(value):
        if isinstance(value, str):
            assert value not in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES
            return
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(k, str):
                    assert k not in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES
                walk(v)
            return
        if isinstance(value, (list, tuple)):
            for x in value:
                walk(x)

    walk(entry)
    with pytest.raises(ValueError):
        _bundle(
            universe_calendar_readout=[{"as_of_period_id": "x", "alpha": 0.0}]
        )


def test_export_does_not_emit_ledger_records() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        UniverseEventRecord(
            universe_event_id="ue:1",
            effective_period_id="2026-Q1-month_03",
            event_type_label="entity_listed",
            affected_entity_ids=("firm:a",),
        )
    )
    n = len(kernel.ledger.records)
    build_universe_calendar_readout_export_section(
        kernel, as_of_period_id="2026-Q4-month_12"
    )
    assert len(kernel.ledger.records) == n


def test_v1_26_4_ui_panel_exists() -> None:
    text = _UI_MOCKUP_PATH.read_text(encoding="utf-8")
    assert 'id="card-universe-calendar"' in text
    assert 'id="universe-calendar-empty"' in text
    assert 'id="universe-calendar-content"' in text
    assert 'id="universe-calendar-entries"' in text
    assert "Universe / calendar" in text
    assert "v1.26.4" in text


def test_v1_26_4_renderer_function_defined() -> None:
    text = _UI_MOCKUP_PATH.read_text(encoding="utf-8")
    assert re.search(
        r"function\s+renderUniverseCalendarFromBundle\s*\(",
        text,
    ) is not None
    assert "bundle.universe_calendar_readout" in text


def test_v1_26_4_no_new_tab_added() -> None:
    text = _UI_MOCKUP_PATH.read_text(encoding="utf-8")
    tabs = re.findall(
        r'<button class="sheet-tab[^"]*"[^>]*data-sheet="([^"]+)"',
        text,
    )
    sheets = re.findall(
        r'<article id="sheet-([^"]+)"', text
    )
    assert len(tabs) == len(sheets) == 11
    for t in tabs:
        assert "calendar" not in t.lower()
        assert "universe-calendar" not in t.lower()


def test_v1_26_4_existing_panels_still_present() -> None:
    text = _UI_MOCKUP_PATH.read_text(encoding="utf-8")
    assert 'id="card-active-stresses"' in text
    assert 'id="card-manual-annotations"' in text
    assert 'id="card-investor-mandate"' in text
    assert 'id="card-universe-calendar"' in text
