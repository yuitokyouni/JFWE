"""
v1.28.2 — Append-only local event-log writer pin tests.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from world.event_log_schema import (
    CANONICAL_SCHEMA_COLUMN_ORDER,
    EventLogManifest,
    EventLogRecord,
)
from world.event_log_writer import (
    AlreadySealedError,
    EventLogPartitionKey,
    EventLogPartitionWriter,
    EventLogValidationError,
    EventLogWriteResult,
    PART_FILE_INDEX_DIGITS,
    PART_FILE_NAME_PREFIX,
    PART_FILE_NAME_SUFFIX,
    SEALED_MARKER_FILE_NAME,
    SealedPartitionWriteError,
    read_partition_part_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record(
    *,
    event_id: str = "evt:test:001",
    event_index: int = 0,
    sector_id: str = "industry:x",
    record_type: str = "manual_annotation_recorded",
    year_month: str = "2026_06",
) -> EventLogRecord:
    return EventLogRecord(
        event_id=event_id,
        run_id="run:test:01",
        period_id="2026-Q2",
        year_month=year_month,
        sector_id=sector_id,
        record_type=record_type,
        source_space="world.test",
        target_entity_type="firm",
        target_entity_id="firm:a",
        event_index=event_index,
        payload_schema_version="v1.0",
        payload_ref_or_json='{"k":"v"}',
    )


def _manifest() -> EventLogManifest:
    return EventLogManifest(
        manifest_version="v1.28.2-test",
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


def _writer(tmp_path: Path) -> EventLogPartitionWriter:
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    return EventLogPartitionWriter(
        root_path=tmp_path / "events",
        partition_key=pk,
        manifest=_manifest(),
    )


# ---------------------------------------------------------------------------
# EventLogPartitionKey
# ---------------------------------------------------------------------------


def test_partition_key_validates_required_fields() -> None:
    with pytest.raises(ValueError):
        EventLogPartitionKey(
            year_month="",
            sector_id="industry:x",
            record_type="t",
        )
    with pytest.raises(ValueError):
        EventLogPartitionKey(
            year_month="2026_06",
            sector_id="",
            record_type="t",
        )
    with pytest.raises(ValueError):
        EventLogPartitionKey(
            year_month="2026_06",
            sector_id="industry:x",
            record_type="",
        )


def test_partition_key_path_segments() -> None:
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    assert pk.to_path_segments() == (
        "year_month=2026_06",
        "sector_id=industry:x",
        "record_type=manual_annotation_recorded",
    )


def test_partition_key_from_record_round_trip() -> None:
    r = _record()
    pk = EventLogPartitionKey.from_record(r)
    assert pk.year_month == "2026_06"
    assert pk.sector_id == "industry:x"
    assert pk.record_type == "manual_annotation_recorded"


# ---------------------------------------------------------------------------
# Writer basic behavior
# ---------------------------------------------------------------------------


def test_writer_creates_partition_directory_on_first_append(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    assert not w.partition_dir.exists()
    w.append([_record()])
    assert w.partition_dir.is_dir()


def test_first_append_creates_part_000001(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    result = w.append([_record(event_id="e1")])
    assert isinstance(result, EventLogWriteResult)
    assert result.part_file_index == 1
    expected_name = (
        f"{PART_FILE_NAME_PREFIX}"
        f"{1:0{PART_FILE_INDEX_DIGITS}d}"
        f"{PART_FILE_NAME_SUFFIX}"
    )
    assert result.part_file_path.name == expected_name
    assert result.part_file_path.is_file()


def test_second_append_creates_part_000002(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    w.append([_record(event_id="e1")])
    r2 = w.append([_record(event_id="e2", event_index=1)])
    assert r2.part_file_index == 2
    assert r2.part_file_path.name == (
        f"{PART_FILE_NAME_PREFIX}"
        f"{2:0{PART_FILE_INDEX_DIGITS}d}"
        f"{PART_FILE_NAME_SUFFIX}"
    )


def test_existing_part_file_checksum_unchanged_after_subsequent_append(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    r1 = w.append([_record(event_id="e1")])
    sha_before = hashlib.sha256(
        r1.part_file_path.read_bytes()
    ).hexdigest()
    size_before = r1.part_file_path.stat().st_size
    w.append([_record(event_id="e2", event_index=1)])
    sha_after = hashlib.sha256(
        r1.part_file_path.read_bytes()
    ).hexdigest()
    size_after = r1.part_file_path.stat().st_size
    assert sha_before == sha_after
    assert size_before == size_after


def test_part_files_listed_in_lex_ascending_order(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    for i in range(5):
        w.append(
            [_record(event_id=f"e{i}", event_index=i)]
        )
    files = w.list_part_files()
    assert len(files) == 5
    names = [f.name for f in files]
    assert names == sorted(names)
    assert names[0].startswith(
        f"{PART_FILE_NAME_PREFIX}000001"
    )
    assert names[-1].startswith(
        f"{PART_FILE_NAME_PREFIX}000005"
    )


def test_event_log_total_size_grows_monotonically_under_append(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    last_total = 0
    for i in range(5):
        w.append(
            [_record(event_id=f"e{i}", event_index=i)]
        )
        total = sum(
            p.stat().st_size for p in w.list_part_files()
        )
        assert total >= last_total
        last_total = total
    assert last_total > 0


def test_jsonl_lines_are_canonical_json_round_trip(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    rec = _record(event_id="e1")
    result = w.append([rec])
    raw = result.part_file_path.read_bytes()
    # File ends with a newline; parsing each line back
    # via json.loads must succeed.
    lines = [
        line for line in raw.split(b"\n") if line
    ]
    assert len(lines) == 1
    d = json.loads(lines[0])
    assert d["event_id"] == "e1"
    # Insertion order preserved: keys equal canonical
    # column order.
    assert tuple(d.keys()) == CANONICAL_SCHEMA_COLUMN_ORDER


def test_records_in_single_append_are_sorted_by_canonical_sort_key(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    r2 = _record(event_id="e2", event_index=2)
    r0 = _record(event_id="e0", event_index=0)
    r1 = _record(event_id="e1", event_index=1)
    result = w.append([r2, r0, r1])
    raw = result.part_file_path.read_bytes()
    lines = [
        line for line in raw.split(b"\n") if line
    ]
    assert len(lines) == 3
    parsed = [json.loads(line) for line in lines]
    sorted_event_ids = [d["event_id"] for d in parsed]
    assert sorted_event_ids == ["e0", "e1", "e2"]


# ---------------------------------------------------------------------------
# Sealing
# ---------------------------------------------------------------------------


def test_sealing_creates_marker_file(tmp_path: Path) -> None:
    w = _writer(tmp_path)
    w.append([_record()])
    assert not w.is_sealed()
    w.seal()
    assert w.is_sealed()
    assert w.sealed_marker.is_file()
    assert w.sealed_marker.name == SEALED_MARKER_FILE_NAME


def test_sealed_partition_cannot_be_appended_to(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    w.append([_record()])
    w.seal()
    with pytest.raises(SealedPartitionWriteError):
        w.append([_record(event_id="e2", event_index=1)])


def test_sealing_twice_raises_already_sealed(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    w.append([_record()])
    w.seal()
    with pytest.raises(AlreadySealedError):
        w.seal()


def test_sealing_an_empty_partition_is_allowed_but_blocks_future_writes(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    # seal before any append
    w.seal()
    assert w.is_sealed()
    with pytest.raises(SealedPartitionWriteError):
        w.append([_record()])


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_append_rejects_empty_record_list(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    with pytest.raises(EventLogValidationError):
        w.append([])


def test_append_rejects_non_record_items(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    with pytest.raises(EventLogValidationError):
        w.append(["not a record"])  # type: ignore[list-item]


def test_append_rejects_record_with_wrong_partition_key(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    bad = _record(sector_id="industry:y")
    with pytest.raises(EventLogValidationError):
        w.append([bad])


def test_writer_rejects_invalid_partition_key_type() -> None:
    with pytest.raises(EventLogValidationError):
        EventLogPartitionWriter(
            root_path=Path("/tmp/x"),
            partition_key="not a partition key",  # type: ignore[arg-type]
            manifest=_manifest(),
        )


def test_writer_rejects_invalid_manifest_type(
    tmp_path: Path,
) -> None:
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    with pytest.raises(EventLogValidationError):
        EventLogPartitionWriter(
            root_path=tmp_path,
            partition_key=pk,
            manifest="not a manifest",  # type: ignore[arg-type]
        )


def test_writer_rejects_empty_root_path() -> None:
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    with pytest.raises(EventLogValidationError):
        EventLogPartitionWriter(
            root_path="",
            partition_key=pk,
            manifest=_manifest(),
        )


# ---------------------------------------------------------------------------
# Reader helper
# ---------------------------------------------------------------------------


def test_read_partition_part_file_round_trip(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    r0 = _record(event_id="e0", event_index=0)
    r1 = _record(event_id="e1", event_index=1)
    result = w.append([r1, r0])
    parsed = read_partition_part_file(result.part_file_path)
    assert len(parsed) == 2
    # Sort order preserved (sorted by canonical_sort_key
    # at write time).
    assert parsed[0]["event_id"] == "e0"
    assert parsed[1]["event_id"] == "e1"


def test_read_partition_part_file_empty_file(
    tmp_path: Path,
) -> None:
    p = tmp_path / "empty.jsonl"
    p.write_bytes(b"")
    assert read_partition_part_file(p) == ()


def test_read_partition_part_file_tolerates_trailing_newline(
    tmp_path: Path,
) -> None:
    p = tmp_path / "ok.jsonl"
    p.write_bytes(b'{"a": 1}\n{"b": 2}\n')
    out = read_partition_part_file(p)
    assert out == ({"a": 1}, {"b": 2})


# ---------------------------------------------------------------------------
# Forbidden-scope tests
# ---------------------------------------------------------------------------


def test_event_log_writer_module_no_columnar_dependencies() -> None:
    from world import event_log_writer

    src = inspect.getsource(event_log_writer)
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


def test_event_log_writer_module_no_real_data_adapter_imports() -> None:
    from world import event_log_writer

    src = inspect.getsource(event_log_writer).lower()
    for adapter in (
        "edinet",
        "tdnet",
        "j_quants",
        "jquants",
        "fsa_filing",
        "topix",
        "nikkei",
        "jpx",
        "edgar",
        "bloomberg",
        "refinitiv",
        "factset",
    ):
        assert f"import {adapter}" not in src
        assert f"from {adapter}" not in src


def test_event_log_writer_does_not_use_wall_clock_in_record_payload(
    tmp_path: Path,
) -> None:
    """The writer must not inject any wall-clock value
    into the record payload. Records carry only the
    fields their constructor specified."""
    w = _writer(tmp_path)
    rec = _record(event_id="e1")
    result = w.append([rec])
    parsed = read_partition_part_file(result.part_file_path)
    assert parsed[0]["created_at_logical"] == ""


def test_event_log_writer_module_exports_match_design_pin() -> None:
    from world import event_log_writer

    expected = {
        "AlreadySealedError",
        "EventLogPartitionKey",
        "EventLogPartitionWriter",
        "EventLogValidationError",
        "EventLogWriteError",
        "EventLogWriteResult",
        "MANIFEST_SIDECAR_FILE_NAME",
        "ManifestMismatchError",
        "PART_FILE_INDEX_DIGITS",
        "PART_FILE_NAME_PREFIX",
        "PART_FILE_NAME_SUFFIX",
        "SEALED_MARKER_FILE_NAME",
        "SealedPartitionWriteError",
        "ensure_manifest_sidecar",
        "manifest_sidecar_path",
        "read_manifest_sidecar",
        "read_partition_part_file",
        "write_manifest_sidecar",
    }
    assert set(event_log_writer.__all__) == expected


def test_writer_does_not_overwrite_existing_part_file(
    tmp_path: Path,
) -> None:
    """Defensive: pre-create part-000001.jsonl manually
    and verify the writer's exclusive-open refuses to
    clobber it (via the auxiliary 'next index' check)."""
    w = _writer(tmp_path)
    w.partition_dir.mkdir(parents=True, exist_ok=True)
    # Pre-existing file at index 1
    pre = w.partition_dir / (
        f"{PART_FILE_NAME_PREFIX}"
        f"{1:0{PART_FILE_INDEX_DIGITS}d}"
        f"{PART_FILE_NAME_SUFFIX}"
    )
    pre.write_bytes(b'{"poison": true}\n')
    # Append one record — should write to index 2, not 1
    w.append([_record(event_id="e1")])
    assert pre.read_bytes() == b'{"poison": true}\n'
    files = w.list_part_files()
    assert len(files) == 2
    assert files[0].name.endswith("000001.jsonl")
    assert files[1].name.endswith("000002.jsonl")


def test_event_log_writer_does_not_register_a_kernel_field() -> None:
    """Sanity: importing the writer module does not add a
    field to WorldKernel. Existing kernel fields are
    unchanged at v1.28.2."""
    from world.kernel import WorldKernel

    fnames = {f.name for f in WorldKernel.__dataclass_fields__.values()}
    forbidden_at_v1_28_2 = {
        "event_log_writer",
        "event_log_partition_writer",
        "event_log",
        "event_log_records",
        "event_log_root_path",
    }
    leaked = fnames & forbidden_at_v1_28_2
    assert leaked == set()
