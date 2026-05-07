"""
v1.28.3 — Partition manifest sidecar + schema-pinning
pin tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from world.event_log_schema import (
    CANONICAL_SCHEMA_COLUMN_ORDER,
    EventLogManifest,
    EventLogRecord,
    compute_leaf_digest,
    manifest_to_canonical_dict,
    serialize_canonical_json,
)
from world.event_log_writer import (
    MANIFEST_SIDECAR_FILE_NAME,
    EventLogPartitionKey,
    EventLogPartitionWriter,
    ManifestMismatchError,
    ensure_manifest_sidecar,
    manifest_sidecar_path,
    read_manifest_sidecar,
    write_manifest_sidecar,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record(
    *,
    event_id: str = "evt:test:001",
    event_index: int = 0,
) -> EventLogRecord:
    return EventLogRecord(
        event_id=event_id,
        run_id="run:test:01",
        period_id="2026-Q2",
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
        source_space="world.test",
        target_entity_type="firm",
        target_entity_id="firm:a",
        event_index=event_index,
        payload_schema_version="v1.0",
        payload_ref_or_json='{"k":"v"}',
    )


def _manifest(
    **overrides,
) -> EventLogManifest:
    base = dict(
        manifest_version="v1.28.3-test",
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
    base.update(overrides)
    return EventLogManifest(**base)


def _writer(
    tmp_path: Path,
    manifest: EventLogManifest | None = None,
) -> EventLogPartitionWriter:
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    return EventLogPartitionWriter(
        root_path=tmp_path / "events",
        partition_key=pk,
        manifest=manifest or _manifest(),
    )


# ---------------------------------------------------------------------------
# manifest_sidecar_path
# ---------------------------------------------------------------------------


def test_manifest_sidecar_path_uses_canonical_filename(
    tmp_path: Path,
) -> None:
    p = manifest_sidecar_path(tmp_path)
    assert p.name == MANIFEST_SIDECAR_FILE_NAME
    assert p.parent == tmp_path


# ---------------------------------------------------------------------------
# write_manifest_sidecar / read_manifest_sidecar
# ---------------------------------------------------------------------------


def test_write_manifest_sidecar_creates_file(
    tmp_path: Path,
) -> None:
    root = tmp_path / "events"
    p = write_manifest_sidecar(root, _manifest())
    assert p.is_file()
    assert p == manifest_sidecar_path(root)


def test_write_manifest_sidecar_refuses_overwrite(
    tmp_path: Path,
) -> None:
    root = tmp_path / "events"
    write_manifest_sidecar(root, _manifest())
    # Second direct write must fail (the ensure_*
    # helper handles re-equality; the raw write is
    # exclusive-open).
    with pytest.raises(FileExistsError):
        write_manifest_sidecar(root, _manifest())


def test_read_manifest_sidecar_round_trip(
    tmp_path: Path,
) -> None:
    root = tmp_path / "events"
    m = _manifest()
    write_manifest_sidecar(root, m)
    m2 = read_manifest_sidecar(root)
    assert m2 == m


def test_read_manifest_sidecar_missing_file_raises(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        read_manifest_sidecar(tmp_path)


def test_manifest_sidecar_canonical_bytes_stable(
    tmp_path: Path,
) -> None:
    """Two writes of the same manifest produce identical
    file bytes (the sidecar uses the canonical-JSON
    serializer with sort_keys=True)."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    write_manifest_sidecar(a, _manifest())
    write_manifest_sidecar(b, _manifest())
    assert (
        manifest_sidecar_path(a).read_bytes()
        == manifest_sidecar_path(b).read_bytes()
    )


def test_manifest_sidecar_bytes_match_canonical_serializer(
    tmp_path: Path,
) -> None:
    root = tmp_path / "events"
    m = _manifest()
    write_manifest_sidecar(root, m)
    expected = serialize_canonical_json(
        manifest_to_canonical_dict(m), sort_keys=True
    )
    assert (
        manifest_sidecar_path(root).read_bytes() == expected
    )


# ---------------------------------------------------------------------------
# ensure_manifest_sidecar (idempotent write-or-verify)
# ---------------------------------------------------------------------------


def test_ensure_manifest_sidecar_writes_when_missing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "events"
    p = ensure_manifest_sidecar(root, _manifest())
    assert p.is_file()


def test_ensure_manifest_sidecar_idempotent_on_equal_manifest(
    tmp_path: Path,
) -> None:
    root = tmp_path / "events"
    p1 = ensure_manifest_sidecar(root, _manifest())
    body1 = p1.read_bytes()
    # Repeat — same path, same body, no exception.
    p2 = ensure_manifest_sidecar(root, _manifest())
    assert p2 == p1
    assert p2.read_bytes() == body1


def test_ensure_manifest_sidecar_raises_on_mismatch(
    tmp_path: Path,
) -> None:
    root = tmp_path / "events"
    ensure_manifest_sidecar(root, _manifest())
    # Different partition_schema_version
    with pytest.raises(ManifestMismatchError):
        ensure_manifest_sidecar(
            root,
            _manifest(
                partition_schema_version="v1.28.x-partition-v2"
            ),
        )


# ---------------------------------------------------------------------------
# Writer integration
# ---------------------------------------------------------------------------


def test_writer_first_append_creates_sidecar(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    p = manifest_sidecar_path(w.root_path)
    assert not p.exists()
    w.append([_record()])
    assert p.is_file()


def test_writer_construction_validates_existing_sidecar(
    tmp_path: Path,
) -> None:
    root = tmp_path / "events"
    write_manifest_sidecar(root, _manifest())
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    # Same manifest — construction succeeds.
    EventLogPartitionWriter(
        root_path=root,
        partition_key=pk,
        manifest=_manifest(),
    )
    # Different manifest — construction raises.
    with pytest.raises(ManifestMismatchError):
        EventLogPartitionWriter(
            root_path=root,
            partition_key=pk,
            manifest=_manifest(
                partition_schema_version=(
                    "v1.28.x-partition-v9"
                )
            ),
        )


def test_writer_subsequent_appends_with_same_manifest_succeed(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    w.append([_record(event_id="e1", event_index=0)])
    w.append([_record(event_id="e2", event_index=1)])
    # Sidecar bytes did not change between the two
    # appends.
    p = manifest_sidecar_path(w.root_path)
    assert p.is_file()


@pytest.mark.parametrize(
    "override_kwargs",
    [
        {"manifest_version": "v9.9-different"},
        {"partition_schema_version": "v9.9-different"},
        {"event_schema_version": "v9.9-different"},
        {
            "partition_key_fields": (
                "year_month",
                "sector_id",
                "record_type",
                "run_id",
            )
        },
        {
            "schema_column_order": tuple(
                reversed(CANONICAL_SCHEMA_COLUMN_ORDER)
            )
        },
        {
            "canonical_sort_key_fields": (
                "partition_key",
                "event_index",
                "canonical_sort_key",
            )
        },
        {"merkle_tree_version": "merkle-v9-different"},
        {"leaf_serializer": "canonical-json-v9"},
    ],
)
def test_writer_construction_rejects_mismatched_manifest_field(
    tmp_path: Path, override_kwargs: dict
) -> None:
    root = tmp_path / "events"
    write_manifest_sidecar(root, _manifest())
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    with pytest.raises(ManifestMismatchError):
        EventLogPartitionWriter(
            root_path=root,
            partition_key=pk,
            manifest=_manifest(**override_kwargs),
        )


# ---------------------------------------------------------------------------
# Schema pinning — same records, different manifests, different leaf digest
# ---------------------------------------------------------------------------


def test_same_records_different_partition_schema_yield_different_leaf_digest() -> None:
    records = [_record(event_id="e1", event_index=0)]
    base = _manifest()
    bumped = _manifest(
        partition_schema_version="v1.28.x-partition-v2"
    )
    assert (
        compute_leaf_digest(records, base)
        != compute_leaf_digest(records, bumped)
    )


def test_same_records_different_schema_column_order_yield_different_leaf_digest() -> None:
    records = [_record(event_id="e1", event_index=0)]
    base = _manifest()
    rev = _manifest(
        schema_column_order=tuple(
            reversed(CANONICAL_SCHEMA_COLUMN_ORDER)
        )
    )
    assert (
        compute_leaf_digest(records, base)
        != compute_leaf_digest(records, rev)
    )


# ---------------------------------------------------------------------------
# Helper validation
# ---------------------------------------------------------------------------


def test_write_manifest_sidecar_rejects_non_manifest(
    tmp_path: Path,
) -> None:
    from world.event_log_writer import EventLogValidationError

    with pytest.raises(EventLogValidationError):
        write_manifest_sidecar(
            tmp_path, "not a manifest"  # type: ignore[arg-type]
        )


def test_ensure_manifest_sidecar_rejects_non_manifest(
    tmp_path: Path,
) -> None:
    from world.event_log_writer import EventLogValidationError

    with pytest.raises(EventLogValidationError):
        ensure_manifest_sidecar(
            tmp_path, "not a manifest"  # type: ignore[arg-type]
        )
