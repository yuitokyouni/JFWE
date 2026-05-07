"""
v1.29.2 — Append-only trace-edge storage pin tests.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from world.trace_edges import (
    TraceEdgeRecord,
)
from world.trace_edge_store import (
    PERIOD_ID_UNKNOWN_PATH_VALUE,
    TRACE_EDGES_PART_FILE_INDEX_DIGITS,
    TRACE_EDGES_PART_FILE_NAME_PREFIX,
    TRACE_EDGES_PART_FILE_NAME_SUFFIX,
    TRACE_EDGES_SEALED_MARKER_FILE_NAME,
    TraceEdgeAlreadySealedError,
    TraceEdgeManifest,
    TraceEdgeManifestMismatchError,
    TraceEdgePartitionKey,
    TraceEdgePartitionWriter,
    TraceEdgeSealedPartitionError,
    TraceEdgeValidationError,
    TraceEdgeWriteResult,
    compute_partition_trace_edge_leaf_digest,
    default_trace_edge_manifest,
    ensure_trace_edges_manifest_sidecar,
    read_trace_edge_part_file,
    read_trace_edges_manifest_sidecar,
    trace_edges_manifest_sidecar_path,
    write_trace_edges_manifest_sidecar,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _edge(
    *,
    edge_id: str = "te:test:001",
    run_id: str = "run:test:01",
    source_event_id: str = "evt:src:001",
    target_event_id: str = "evt:tgt:001",
    edge_type_label: str = "cited_as_evidence",
    edge_category_label: str = "evidence",
    period_id: str = "2026-Q2",
    actor_id: str = "",
    evidence_ref_ids: tuple[str, ...] = (),
    citation_ids: tuple[str, ...] = (),
) -> TraceEdgeRecord:
    return TraceEdgeRecord(
        edge_id=edge_id,
        run_id=run_id,
        source_event_id=source_event_id,
        target_event_id=target_event_id,
        edge_type_label=edge_type_label,
        edge_category_label=edge_category_label,
        period_id=period_id,
        actor_id=actor_id,
        evidence_ref_ids=evidence_ref_ids,
        citation_ids=citation_ids,
    )


def _writer(
    tmp_path: Path,
    manifest: TraceEdgeManifest | None = None,
) -> TraceEdgePartitionWriter:
    pk = TraceEdgePartitionKey(
        run_id="run:test:01",
        period_id_or_unknown="2026-Q2",
        edge_category_label="evidence",
    )
    return TraceEdgePartitionWriter(
        root_path=tmp_path / "trace_edges",
        partition_key=pk,
        manifest=(
            manifest if manifest is not None
            else default_trace_edge_manifest()
        ),
    )


# ---------------------------------------------------------------------------
# TraceEdgePartitionKey
# ---------------------------------------------------------------------------


def test_partition_key_validates_required_fields() -> None:
    with pytest.raises(TraceEdgeValidationError):
        TraceEdgePartitionKey(
            run_id="",
            period_id_or_unknown="2026-Q2",
            edge_category_label="evidence",
        )
    with pytest.raises(TraceEdgeValidationError):
        TraceEdgePartitionKey(
            run_id="r",
            period_id_or_unknown="",
            edge_category_label="evidence",
        )
    with pytest.raises(TraceEdgeValidationError):
        TraceEdgePartitionKey(
            run_id="r",
            period_id_or_unknown="p",
            edge_category_label="not_in_set",
        )


def test_partition_key_path_segments() -> None:
    pk = TraceEdgePartitionKey(
        run_id="run:test:01",
        period_id_or_unknown="2026-Q2",
        edge_category_label="evidence",
    )
    assert pk.to_path_segments() == (
        "run_id=run:test:01",
        "period_id=2026-Q2",
        "edge_category=evidence",
    )


def test_partition_key_from_record_uses_period_id() -> None:
    r = _edge(period_id="2026-Q3")
    pk = TraceEdgePartitionKey.from_record(r)
    assert pk.period_id_or_unknown == "2026-Q3"


def test_partition_key_from_record_uses_unknown_for_empty_period_id() -> None:
    r = _edge(period_id="")
    pk = TraceEdgePartitionKey.from_record(r)
    assert (
        pk.period_id_or_unknown
        == PERIOD_ID_UNKNOWN_PATH_VALUE
    )


# ---------------------------------------------------------------------------
# TraceEdgeManifest
# ---------------------------------------------------------------------------


def test_default_trace_edge_manifest_valid() -> None:
    m = default_trace_edge_manifest()
    assert m.digest_algorithm == "sha256"
    assert "run_id" in m.partition_key_fields
    assert "period_id" in m.partition_key_fields
    assert (
        "edge_category_label" in m.partition_key_fields
    )


def test_manifest_rejects_non_sha256() -> None:
    with pytest.raises(TraceEdgeValidationError):
        TraceEdgeManifest(
            manifest_version="v",
            trace_edge_schema_version="v1",
            partition_key_fields=(
                "run_id",
                "period_id",
                "edge_category_label",
            ),
            canonical_sort_key_fields=(
                "canonical_sort_key",
            ),
            schema_column_order=(
                default_trace_edge_manifest().schema_column_order
            ),
            digest_algorithm="md5",
        )


def test_manifest_rejects_missing_partition_dimension() -> None:
    with pytest.raises(TraceEdgeValidationError):
        TraceEdgeManifest(
            manifest_version="v",
            trace_edge_schema_version="v1",
            partition_key_fields=("run_id", "period_id"),
            canonical_sort_key_fields=(
                "canonical_sort_key",
            ),
            schema_column_order=(
                default_trace_edge_manifest().schema_column_order
            ),
        )


def test_manifest_rejects_invalid_schema_column_order() -> None:
    bad = tuple(
        c
        for c in default_trace_edge_manifest().schema_column_order
        if c != "edge_id"
    )
    with pytest.raises(TraceEdgeValidationError):
        TraceEdgeManifest(
            manifest_version="v",
            trace_edge_schema_version="v1",
            partition_key_fields=(
                "run_id",
                "period_id",
                "edge_category_label",
            ),
            canonical_sort_key_fields=(
                "canonical_sort_key",
            ),
            schema_column_order=bad,
        )


# ---------------------------------------------------------------------------
# Manifest sidecar
# ---------------------------------------------------------------------------


def test_sidecar_round_trip(tmp_path: Path) -> None:
    root = tmp_path / "trace_edges"
    m = default_trace_edge_manifest()
    write_trace_edges_manifest_sidecar(root, m)
    m2 = read_trace_edges_manifest_sidecar(root)
    assert m2 == m


def test_sidecar_canonical_bytes_stable(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    write_trace_edges_manifest_sidecar(
        a, default_trace_edge_manifest()
    )
    write_trace_edges_manifest_sidecar(
        b, default_trace_edge_manifest()
    )
    assert (
        trace_edges_manifest_sidecar_path(a).read_bytes()
        == trace_edges_manifest_sidecar_path(b).read_bytes()
    )


def test_ensure_sidecar_idempotent_on_equal(tmp_path: Path) -> None:
    root = tmp_path / "trace_edges"
    p1 = ensure_trace_edges_manifest_sidecar(
        root, default_trace_edge_manifest()
    )
    p2 = ensure_trace_edges_manifest_sidecar(
        root, default_trace_edge_manifest()
    )
    assert p1 == p2


def test_ensure_sidecar_raises_on_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "trace_edges"
    ensure_trace_edges_manifest_sidecar(
        root, default_trace_edge_manifest()
    )
    different = TraceEdgeManifest(
        manifest_version="v9-DIFFERENT",
        trace_edge_schema_version="v9",
        partition_key_fields=(
            "run_id",
            "period_id",
            "edge_category_label",
        ),
        canonical_sort_key_fields=(
            "canonical_sort_key",
        ),
        schema_column_order=(
            default_trace_edge_manifest().schema_column_order
        ),
    )
    with pytest.raises(TraceEdgeManifestMismatchError):
        ensure_trace_edges_manifest_sidecar(
            root, different
        )


# ---------------------------------------------------------------------------
# Writer basic behavior
# ---------------------------------------------------------------------------


def test_writer_creates_partition_dir_on_first_append(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    assert not w.partition_dir.exists()
    w.append([_edge()])
    assert w.partition_dir.is_dir()


def test_first_append_creates_part_000001(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    res = w.append([_edge(edge_id="e1")])
    assert isinstance(res, TraceEdgeWriteResult)
    expected_name = (
        f"{TRACE_EDGES_PART_FILE_NAME_PREFIX}"
        f"{1:0{TRACE_EDGES_PART_FILE_INDEX_DIGITS}d}"
        f"{TRACE_EDGES_PART_FILE_NAME_SUFFIX}"
    )
    assert res.part_file_path.name == expected_name
    assert res.part_file_index == 1


def test_second_append_creates_part_000002(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    w.append([_edge(edge_id="e1")])
    res = w.append([_edge(edge_id="e2")])
    assert res.part_file_index == 2


def test_existing_part_file_checksum_unchanged(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    res1 = w.append([_edge(edge_id="e1")])
    sha_before = hashlib.sha256(
        res1.part_file_path.read_bytes()
    ).hexdigest()
    size_before = res1.part_file_path.stat().st_size
    w.append([_edge(edge_id="e2")])
    sha_after = hashlib.sha256(
        res1.part_file_path.read_bytes()
    ).hexdigest()
    size_after = res1.part_file_path.stat().st_size
    assert sha_before == sha_after
    assert size_before == size_after


def test_part_files_sorted_lex(tmp_path: Path) -> None:
    w = _writer(tmp_path)
    for i in range(4):
        w.append([_edge(edge_id=f"e{i}")])
    files = w.list_part_files()
    names = [f.name for f in files]
    assert names == sorted(names)


def test_jsonl_round_trip_via_reader(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    a = _edge(edge_id="e0")
    b = _edge(edge_id="e1")
    res = w.append([b, a])
    parsed = read_trace_edge_part_file(res.part_file_path)
    # Sorted by canonical_sort_key at write time;
    # canonical_sort_key includes edge_id so e0 < e1.
    assert len(parsed) == 2
    assert parsed[0]["edge_id"] == "e0"
    assert parsed[1]["edge_id"] == "e1"


def test_records_in_single_append_sorted_by_canonical_sort_key(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    res = w.append(
        [
            _edge(edge_id="e2"),
            _edge(edge_id="e0"),
            _edge(edge_id="e1"),
        ]
    )
    raw = res.part_file_path.read_bytes()
    lines = [line for line in raw.split(b"\n") if line]
    parsed = [json.loads(line) for line in lines]
    ids = [d["edge_id"] for d in parsed]
    assert ids == ["e0", "e1", "e2"]


# ---------------------------------------------------------------------------
# Sealing
# ---------------------------------------------------------------------------


def test_sealing_creates_marker(tmp_path: Path) -> None:
    w = _writer(tmp_path)
    w.append([_edge()])
    assert not w.is_sealed()
    w.seal()
    assert w.is_sealed()
    assert w.sealed_marker.is_file()
    assert (
        w.sealed_marker.name
        == TRACE_EDGES_SEALED_MARKER_FILE_NAME
    )


def test_sealed_partition_cannot_be_appended(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    w.append([_edge()])
    w.seal()
    with pytest.raises(TraceEdgeSealedPartitionError):
        w.append([_edge(edge_id="e2")])


def test_sealing_twice_raises_already_sealed(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    w.append([_edge()])
    w.seal()
    with pytest.raises(TraceEdgeAlreadySealedError):
        w.seal()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_append_rejects_empty_record_list(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    with pytest.raises(TraceEdgeValidationError):
        w.append([])


def test_append_rejects_non_record_items(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    with pytest.raises(TraceEdgeValidationError):
        w.append(["not a record"])  # type: ignore[list-item]


def test_append_rejects_record_with_wrong_partition_key(
    tmp_path: Path,
) -> None:
    w = _writer(tmp_path)
    bad = _edge(edge_category_label="review")
    with pytest.raises(TraceEdgeValidationError):
        w.append([bad])


def test_writer_rejects_invalid_partition_key_type() -> None:
    with pytest.raises(TraceEdgeValidationError):
        TraceEdgePartitionWriter(
            root_path=Path("/tmp/x"),
            partition_key="not a partition key",  # type: ignore[arg-type]
            manifest=default_trace_edge_manifest(),
        )


def test_writer_rejects_invalid_manifest_type(
    tmp_path: Path,
) -> None:
    pk = TraceEdgePartitionKey(
        run_id="run:test:01",
        period_id_or_unknown="p",
        edge_category_label="evidence",
    )
    with pytest.raises(TraceEdgeValidationError):
        TraceEdgePartitionWriter(
            root_path=tmp_path / "trace_edges",
            partition_key=pk,
            manifest="not a manifest",  # type: ignore[arg-type]
        )


def test_writer_eager_manifest_mismatch_at_construction(
    tmp_path: Path,
) -> None:
    root = tmp_path / "trace_edges"
    write_trace_edges_manifest_sidecar(
        root, default_trace_edge_manifest()
    )
    different = TraceEdgeManifest(
        manifest_version="v9-DIFFERENT",
        trace_edge_schema_version="v9",
        partition_key_fields=(
            "run_id",
            "period_id",
            "edge_category_label",
        ),
        canonical_sort_key_fields=(
            "canonical_sort_key",
        ),
        schema_column_order=(
            default_trace_edge_manifest().schema_column_order
        ),
    )
    pk = TraceEdgePartitionKey(
        run_id="run:test:01",
        period_id_or_unknown="2026-Q2",
        edge_category_label="evidence",
    )
    with pytest.raises(TraceEdgeManifestMismatchError):
        TraceEdgePartitionWriter(
            root_path=root,
            partition_key=pk,
            manifest=different,
        )


# ---------------------------------------------------------------------------
# Tamper-evidence digest hook
# ---------------------------------------------------------------------------


def test_partition_digest_matches_in_memory_compute(
    tmp_path: Path,
) -> None:
    """The on-disk partition digest equals the
    in-memory `compute_trace_edge_leaf_digest` over
    the same records — i.e. write-read round-trip
    preserves the canonical leaf material."""
    from world.trace_edges import (
        compute_trace_edge_leaf_digest,
    )

    w = _writer(tmp_path)
    in_memory = [
        _edge(edge_id="e0"),
        _edge(edge_id="e1"),
        _edge(edge_id="e2"),
    ]
    w.append(in_memory)
    expected = compute_trace_edge_leaf_digest(in_memory)
    actual = compute_partition_trace_edge_leaf_digest(
        w.root_path, w.partition_key
    )
    assert actual == expected


def test_partition_digest_changes_when_edge_changes(
    tmp_path: Path,
) -> None:
    w_a = _writer(tmp_path / "a")
    w_b = _writer(tmp_path / "b")
    w_a.append([_edge(edge_id="e1")])
    w_b.append(
        [_edge(edge_id="e1", actor_id="reviewer_a")]
    )
    da = compute_partition_trace_edge_leaf_digest(
        w_a.root_path, w_a.partition_key
    )
    db = compute_partition_trace_edge_leaf_digest(
        w_b.root_path, w_b.partition_key
    )
    assert da != db


def test_partition_digest_independent_of_part_split(
    tmp_path: Path,
) -> None:
    w_a = _writer(tmp_path / "single")
    w_b = _writer(tmp_path / "split")
    edges = [_edge(edge_id=f"e{i}") for i in range(4)]
    w_a.append(edges)
    w_b.append(edges[:2])
    w_b.append(edges[2:])
    da = compute_partition_trace_edge_leaf_digest(
        w_a.root_path, w_a.partition_key
    )
    db = compute_partition_trace_edge_leaf_digest(
        w_b.root_path, w_b.partition_key
    )
    assert da == db


# ---------------------------------------------------------------------------
# Forbidden-scope tests
# ---------------------------------------------------------------------------


def test_module_no_graph_database_or_columnar_imports() -> None:
    from world import trace_edge_store

    src = inspect.getsource(trace_edge_store)
    for tok in (
        "import polars",
        "from polars",
        "import duckdb",
        "from duckdb",
        "import pyarrow",
        "from pyarrow",
        "import xxhash",
        "from xxhash",
        "import rdflib",
        "from rdflib",
        "import sparql",
        "from sparql",
        "import neo4j",
        "from neo4j",
        "import networkx",
        "from networkx",
        "import gremlin",
        "from gremlin",
    ):
        assert tok not in src


def test_module_no_real_data_adapter_imports() -> None:
    from world import trace_edge_store

    src = inspect.getsource(trace_edge_store).lower()
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


def test_module_does_not_register_a_kernel_field() -> None:
    from world.kernel import WorldKernel

    fnames = {
        f.name
        for f in WorldKernel.__dataclass_fields__.values()
    }
    forbidden = {
        "trace_edge_store",
        "trace_edge_writer",
        "trace_edge_partition_writer",
    }
    assert (fnames & forbidden) == set()


def test_module_no_prev_or_self_hash_field_in_record_dataclass() -> None:
    """v1.29.2 must not introduce prev_hash / self_hash
    on TraceEdgeRecord. Tamper evidence rides through
    `compute_trace_edge_leaf_digest` (v1.29.1 boundary)."""
    from dataclasses import fields as dc_fields

    field_names = {
        f.name for f in dc_fields(TraceEdgeRecord)
    }
    forbidden = {
        "prev_hash",
        "self_hash",
        "edge_chain_hash",
    }
    assert (field_names & forbidden) == set()


def test_module_exports_match_design_pin() -> None:
    from world import trace_edge_store

    expected = {
        "PERIOD_ID_UNKNOWN_PATH_VALUE",
        "TRACE_EDGES_MANIFEST_SIDECAR_FILE_NAME",
        "TRACE_EDGES_PART_FILE_INDEX_DIGITS",
        "TRACE_EDGES_PART_FILE_NAME_PREFIX",
        "TRACE_EDGES_PART_FILE_NAME_SUFFIX",
        "TRACE_EDGES_SEALED_MARKER_FILE_NAME",
        "TraceEdgeAlreadySealedError",
        "TraceEdgeManifest",
        "TraceEdgeManifestMismatchError",
        "TraceEdgePartitionKey",
        "TraceEdgePartitionWriter",
        "TraceEdgeSealedPartitionError",
        "TraceEdgeValidationError",
        "TraceEdgeWriteError",
        "TraceEdgeWriteResult",
        "compute_partition_trace_edge_leaf_digest",
        "default_trace_edge_manifest",
        "ensure_trace_edges_manifest_sidecar",
        "file_sha256",
        "read_trace_edge_part_file",
        "read_trace_edges_manifest_sidecar",
        "trace_edges_manifest_sidecar_path",
        "write_trace_edges_manifest_sidecar",
    }
    assert set(trace_edge_store.__all__) == expected


def test_v1_28_event_log_modules_unaffected() -> None:
    """Sanity: importing the v1.29.2 trace-edge writer
    has no side effects on the v1.28 event-log
    modules. Their public exports remain unchanged."""
    from world.event_log_writer import (
        EventLogPartitionKey,
        EventLogPartitionWriter,
    )

    assert EventLogPartitionKey is not None
    assert EventLogPartitionWriter is not None
