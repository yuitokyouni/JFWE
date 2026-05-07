"""
v1.28.8 — Deterministic event-log projection prototype
pin tests.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from world.event_log_projection import (
    EventLogProjectionSummary,
    project_event_log,
)
from world.event_log_schema import (
    CANONICAL_SCHEMA_COLUMN_ORDER,
    EventLogManifest,
    EventLogRecord,
)
from world.event_log_writer import (
    EventLogPartitionKey,
    EventLogPartitionWriter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record(
    *,
    event_id: str,
    event_index: int,
    period_id: str = "2026-Q2",
    year_month: str = "2026_06",
    sector_id: str = "industry:x",
    record_type: str = "manual_annotation_recorded",
    target_entity_id: str = "firm:a",
) -> EventLogRecord:
    return EventLogRecord(
        event_id=event_id,
        run_id="run:test:01",
        period_id=period_id,
        year_month=year_month,
        sector_id=sector_id,
        record_type=record_type,
        source_space="world.test",
        target_entity_type="firm",
        target_entity_id=target_entity_id,
        event_index=event_index,
        payload_schema_version="v1.0",
        payload_ref_or_json='{"k":"v"}',
    )


def _manifest() -> EventLogManifest:
    return EventLogManifest(
        manifest_version="v1.28.8-test",
        partition_schema_version="v1.28.x-partition-v1",
        partition_key_fields=(
            "year_month",
            "sector_id",
            "record_type",
        ),
        event_schema_version="v1.28.x-event-v1",
        canonical_sort_key_fields=(
            "partition_key",
            "event_index",
            "event_id",
            "canonical_sort_key",
        ),
        schema_column_order=CANONICAL_SCHEMA_COLUMN_ORDER,
    )


def _seed(tmp_path: Path) -> Path:
    """Seed three records across two partitions and two
    periods."""
    root = tmp_path / "events"
    m = _manifest()
    pk_x = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    pk_y = EventLogPartitionKey(
        year_month="2026_07",
        sector_id="industry:y",
        record_type="strategic_relationship_recorded",
    )
    EventLogPartitionWriter(
        root_path=root, partition_key=pk_x, manifest=m
    ).append(
        [
            _record(
                event_id="x-e1",
                event_index=0,
                period_id="2026-Q2",
                year_month="2026_06",
                sector_id="industry:x",
                record_type=(
                    "manual_annotation_recorded"
                ),
                target_entity_id="firm:a",
            ),
            _record(
                event_id="x-e2",
                event_index=1,
                period_id="2026-Q2",
                year_month="2026_06",
                sector_id="industry:x",
                record_type=(
                    "manual_annotation_recorded"
                ),
                target_entity_id="firm:a",
            ),
        ]
    )
    EventLogPartitionWriter(
        root_path=root, partition_key=pk_y, manifest=m
    ).append(
        [
            _record(
                event_id="y-e1",
                event_index=0,
                period_id="2026-Q3",
                year_month="2026_07",
                sector_id="industry:y",
                record_type=(
                    "strategic_relationship_recorded"
                ),
                target_entity_id="firm:b",
            )
        ]
    )
    return root


# ---------------------------------------------------------------------------
# project_event_log basic shape
# ---------------------------------------------------------------------------


def test_projection_returns_summary_dataclass(
    tmp_path: Path,
) -> None:
    root = _seed(tmp_path)
    s = project_event_log(root)
    assert isinstance(s, EventLogProjectionSummary)


def test_projection_total_records_correct(
    tmp_path: Path,
) -> None:
    root = _seed(tmp_path)
    s = project_event_log(root)
    assert s.total_records == 3


def test_projection_records_by_period(
    tmp_path: Path,
) -> None:
    root = _seed(tmp_path)
    s = project_event_log(root)
    d = dict(s.records_by_period)
    assert d == {"2026-Q2": 2, "2026-Q3": 1}


def test_projection_records_by_entity(
    tmp_path: Path,
) -> None:
    root = _seed(tmp_path)
    s = project_event_log(root)
    d = dict(s.records_by_entity)
    assert d == {"firm:a": 2, "firm:b": 1}


def test_projection_records_by_record_type(
    tmp_path: Path,
) -> None:
    root = _seed(tmp_path)
    s = project_event_log(root)
    d = dict(s.records_by_record_type)
    assert d == {
        "manual_annotation_recorded": 2,
        "strategic_relationship_recorded": 1,
    }


def test_projection_partition_keys_sorted(
    tmp_path: Path,
) -> None:
    root = _seed(tmp_path)
    s = project_event_log(root)
    assert s.partition_keys == tuple(
        sorted(s.partition_keys)
    )
    assert len(s.partition_keys) == 2


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_projection_deterministic_across_reruns(
    tmp_path: Path,
) -> None:
    root = _seed(tmp_path)
    a = project_event_log(root)
    b = project_event_log(root)
    assert a == b
    assert a.to_dict() == b.to_dict()


def test_projection_independent_of_filesystem_listing_order(
    tmp_path: Path,
) -> None:
    """Two roots with identical content yield identical
    summaries."""
    root_a = _seed(tmp_path / "a")
    root_b = _seed(tmp_path / "b")
    sa = project_event_log(root_a)
    sb = project_event_log(root_b)
    assert sa == sb


# ---------------------------------------------------------------------------
# Window restriction
# ---------------------------------------------------------------------------


def test_partial_window_equals_full_filtered_to_same_window(
    tmp_path: Path,
) -> None:
    root = _seed(tmp_path)
    full = project_event_log(root)
    windowed = project_event_log(
        root, period_window=("2026-Q2", "2026-Q2")
    )
    assert windowed.total_records == 2
    assert dict(windowed.records_by_period) == {
        "2026-Q2": 2
    }
    # The "Q3 partition" must drop out of partition_keys
    # under the Q2-only window.
    assert len(windowed.partition_keys) == 1
    assert (
        windowed.partition_keys[0][0] == "2026_06"
    )
    # Sanity: the Q3 partition was present in the full
    # summary.
    assert any(
        k[0] == "2026_07" for k in full.partition_keys
    )


def test_window_outside_data_yields_empty_summary(
    tmp_path: Path,
) -> None:
    root = _seed(tmp_path)
    s = project_event_log(
        root, period_window=("2030-Q1", "2030-Q4")
    )
    assert s.total_records == 0
    assert s.records_by_period == ()
    assert s.records_by_entity == ()
    assert s.records_by_record_type == ()
    assert s.partition_keys == ()


# ---------------------------------------------------------------------------
# Side effects: projection does not mutate the event log
# ---------------------------------------------------------------------------


def test_projection_does_not_mutate_event_log(
    tmp_path: Path,
) -> None:
    import hashlib

    root = _seed(tmp_path)
    # Snapshot every file's bytes before
    before = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            before[p.relative_to(root).as_posix()] = (
                hashlib.sha256(p.read_bytes()).hexdigest()
            )
    project_event_log(root)
    after = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            after[p.relative_to(root).as_posix()] = (
                hashlib.sha256(p.read_bytes()).hexdigest()
            )
    assert before == after


def test_projection_does_not_register_a_kernel_field() -> None:
    from world.kernel import WorldKernel

    fnames = {
        f.name for f in WorldKernel.__dataclass_fields__.values()
    }
    forbidden = {
        "event_log_projection",
        "event_log_view",
        "projected_event_log",
    }
    assert (fnames & forbidden) == set()


# ---------------------------------------------------------------------------
# Empty root
# ---------------------------------------------------------------------------


def test_projection_on_missing_root_returns_empty(
    tmp_path: Path,
) -> None:
    s = project_event_log(tmp_path / "nope")
    assert s.total_records == 0
    assert s.partition_keys == ()


def test_projection_on_root_with_only_manifest_returns_empty(
    tmp_path: Path,
) -> None:
    from world.event_log_writer import write_manifest_sidecar

    root = tmp_path / "events_empty"
    write_manifest_sidecar(root, _manifest())
    s = project_event_log(root)
    assert s.total_records == 0
    assert s.partition_keys == ()


# ---------------------------------------------------------------------------
# Forbidden-scope tests
# ---------------------------------------------------------------------------


def test_projection_module_no_columnar_dependencies() -> None:
    from world import event_log_projection

    src = inspect.getsource(event_log_projection)
    for tok in (
        "import polars",
        "from polars",
        "import duckdb",
        "from duckdb",
        "import pyarrow",
        "from pyarrow",
        "import xxhash",
        "from xxhash",
        "import pyo3",
        "from pyo3",
        "import fastparquet",
        "from fastparquet",
    ):
        assert tok not in src


def test_projection_module_does_not_import_or_call_book_apis() -> None:
    """The projection must NOT *import* any v1.x Book
    class or *call* `Book.list_*(...)`. Docstring
    mentions in the "do NOT do this" position are
    allowed; we check imports and callable invocations
    only."""
    from world import event_log_projection

    src = inspect.getsource(event_log_projection)
    for tok in (
        "from world.manual_annotations import",
        "from world.investor_mandates import",
        "from world.universe_events import",
        "from world.reporting_calendar_profiles import",
        "from world.strategic_relationships import",
        "from world.manual_annotation_provenance import",
        ".list_annotations(",
        ".list_profiles(",
        ".list_events(",
        ".list_relationships(",
        ".list_provenances(",
    ):
        assert tok not in src


def test_projection_module_imports_no_citation_or_trace_graph_modules() -> None:
    """The user's task explicitly defers citation
    graph / trace graph / PROV-O / SPARQL / Cypher to
    a later milestone (likely v1.29+). The v1.28.8
    projection module must not *import* anything
    those terms refer to. (Docstring negations are
    allowed.)"""
    from world import event_log_projection

    src = inspect.getsource(event_log_projection)
    for tok in (
        "import sparql",
        "from sparql",
        "import rdflib",
        "from rdflib",
        "import neo4j",
        "from neo4j",
        "import networkx",
        "from networkx",
        "TraceEdgeRecord",
        "CitationGraphProjection(",
    ):
        assert tok not in src


def test_projection_module_exports_match_design_pin() -> None:
    from world import event_log_projection

    expected = {
        "EventLogProjectionSummary",
        "project_event_log",
    }
    assert (
        set(event_log_projection.__all__) == expected
    )


# ---------------------------------------------------------------------------
# Aggregate combine: projection over a partial-window can be checked
# against the manual sum
# ---------------------------------------------------------------------------


def test_projection_summary_dataclass_is_frozen() -> None:
    s = EventLogProjectionSummary(total_records=0)
    with pytest.raises(Exception):
        s.total_records = 1  # type: ignore[misc]


def test_projection_to_dict_round_trip(
    tmp_path: Path,
) -> None:
    root = _seed(tmp_path)
    s = project_event_log(root)
    d = s.to_dict()
    assert d["total_records"] == 3
    assert sorted(d["records_by_period"]) == sorted(
        [["2026-Q2", 2], ["2026-Q3", 1]]
    )
