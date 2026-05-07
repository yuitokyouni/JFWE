"""
v1.28.4 — Merkle digest core pin tests.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from world.event_log_merkle import (
    EventLogDigestTree,
    build_event_log_digest_tree,
    compute_event_log_root_digest,
    compute_inner_digest,
    compute_manifest_digest,
    compute_partition_leaf_digest,
    discover_partitions,
)
from world.event_log_schema import (
    CANONICAL_SCHEMA_COLUMN_ORDER,
    EventLogManifest,
    EventLogRecord,
    compute_leaf_digest,
)
from world.event_log_writer import (
    EventLogPartitionKey,
    EventLogPartitionWriter,
    write_manifest_sidecar,
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
    target_entity_id: str = "firm:a",
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
        target_entity_id=target_entity_id,
        event_index=event_index,
        payload_schema_version="v1.0",
        payload_ref_or_json='{"k":"v"}',
    )


def _manifest(**overrides) -> EventLogManifest:
    base = dict(
        manifest_version="v1.28.4-test",
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


def _seed_event_log(tmp_path: Path) -> Path:
    """Seed two partitions with two records each."""
    root = tmp_path / "events"
    m = _manifest()
    pk_a = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    pk_b = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:y",
        record_type="strategic_relationship_recorded",
    )
    w_a = EventLogPartitionWriter(
        root_path=root, partition_key=pk_a, manifest=m
    )
    w_b = EventLogPartitionWriter(
        root_path=root, partition_key=pk_b, manifest=m
    )
    w_a.append(
        [
            _record(event_id="a-e1", event_index=0),
            _record(event_id="a-e2", event_index=1),
        ]
    )
    w_b.append(
        [
            _record(
                event_id="b-e1",
                event_index=0,
                sector_id="industry:y",
                record_type=(
                    "strategic_relationship_recorded"
                ),
            ),
            _record(
                event_id="b-e2",
                event_index=1,
                sector_id="industry:y",
                record_type=(
                    "strategic_relationship_recorded"
                ),
            ),
        ]
    )
    return root


# ---------------------------------------------------------------------------
# compute_manifest_digest
# ---------------------------------------------------------------------------


def test_manifest_digest_is_lowercase_hex_64() -> None:
    d = compute_manifest_digest(_manifest())
    assert len(d) == 64
    assert d == d.lower()
    int(d, 16)


def test_manifest_digest_stable_across_reruns() -> None:
    a = compute_manifest_digest(_manifest())
    b = compute_manifest_digest(_manifest())
    assert a == b


def test_manifest_digest_changes_with_field_change() -> None:
    base = compute_manifest_digest(_manifest())
    bumped = compute_manifest_digest(
        _manifest(partition_schema_version="v9")
    )
    assert base != bumped


def test_manifest_digest_rejects_non_manifest() -> None:
    with pytest.raises(TypeError):
        compute_manifest_digest("not a manifest")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# compute_partition_leaf_digest
# ---------------------------------------------------------------------------


def test_partition_leaf_digest_matches_in_memory_compute_leaf_digest(
    tmp_path: Path,
) -> None:
    """The filesystem-walk path must produce the same
    digest as computing compute_leaf_digest directly on
    the in-memory records — i.e. read-write-read does
    not mutate the canonical material."""
    root = tmp_path / "events"
    m = _manifest()
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    in_memory = [
        _record(event_id="e0", event_index=0),
        _record(event_id="e1", event_index=1),
        _record(event_id="e2", event_index=2),
    ]
    w = EventLogPartitionWriter(
        root_path=root, partition_key=pk, manifest=m
    )
    w.append(in_memory)
    expected = compute_leaf_digest(in_memory, m)
    actual = compute_partition_leaf_digest(root, pk, m)
    assert actual == expected


def test_partition_leaf_digest_independent_of_part_file_split(
    tmp_path: Path,
) -> None:
    """Splitting the same logical record set across two
    appends (= two part files) must yield the same
    leaf digest as a single append (= one part file).
    The leaf digest sorts globally, so file boundaries
    do not appear in the canonical material."""
    m = _manifest()
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    records_full = [
        _record(event_id="e0", event_index=0),
        _record(event_id="e1", event_index=1),
        _record(event_id="e2", event_index=2),
        _record(event_id="e3", event_index=3),
    ]
    # Single-append root
    root_a = tmp_path / "single"
    EventLogPartitionWriter(
        root_path=root_a, partition_key=pk, manifest=m
    ).append(records_full)
    # Split-append root
    root_b = tmp_path / "split"
    w_b = EventLogPartitionWriter(
        root_path=root_b, partition_key=pk, manifest=m
    )
    w_b.append(records_full[:2])
    w_b.append(records_full[2:])
    da = compute_partition_leaf_digest(root_a, pk, m)
    db = compute_partition_leaf_digest(root_b, pk, m)
    assert da == db


def test_partition_leaf_digest_changes_when_record_changes(
    tmp_path: Path,
) -> None:
    m = _manifest()
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    base_root = tmp_path / "base"
    EventLogPartitionWriter(
        root_path=base_root, partition_key=pk, manifest=m
    ).append([_record(event_id="e0", event_index=0)])
    mutated_root = tmp_path / "mutated"
    EventLogPartitionWriter(
        root_path=mutated_root,
        partition_key=pk,
        manifest=m,
    ).append(
        [
            _record(
                event_id="e0",
                event_index=0,
                target_entity_id="firm:b",
            )
        ]
    )
    assert compute_partition_leaf_digest(
        base_root, pk, m
    ) != compute_partition_leaf_digest(
        mutated_root, pk, m
    )


def test_partition_leaf_digest_empty_partition_dir_matches_empty_records(
    tmp_path: Path,
) -> None:
    """An on-disk partition directory with no part files
    yields the same leaf digest as
    ``compute_leaf_digest((), manifest)``."""
    m = _manifest()
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    pk.to_partition_dir(tmp_path).mkdir(
        parents=True, exist_ok=True
    )
    expected = compute_leaf_digest((), m)
    actual = compute_partition_leaf_digest(tmp_path, pk, m)
    assert actual == expected


def test_partition_leaf_digest_rejects_non_partition_key() -> None:
    with pytest.raises(TypeError):
        compute_partition_leaf_digest(
            Path("/tmp"),
            "not a partition key",  # type: ignore[arg-type]
            _manifest(),
        )


def test_partition_leaf_digest_rejects_non_manifest(
    tmp_path: Path,
) -> None:
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    with pytest.raises(TypeError):
        compute_partition_leaf_digest(
            tmp_path, pk, "not a manifest"  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# compute_inner_digest
# ---------------------------------------------------------------------------


def test_inner_digest_lowercase_hex_64() -> None:
    d = compute_inner_digest(
        [("k1", "a" * 64), ("k2", "b" * 64)]
    )
    assert len(d) == 64
    assert d == d.lower()
    int(d, 16)


def test_inner_digest_independent_of_insertion_order() -> None:
    children = [
        ("a", "1" * 64),
        ("b", "2" * 64),
        ("c", "3" * 64),
    ]
    permutations = [
        children,
        list(reversed(children)),
        [children[1], children[0], children[2]],
    ]
    digests = {
        compute_inner_digest(p) for p in permutations
    }
    assert len(digests) == 1


def test_inner_digest_independent_of_dict_iteration_order() -> None:
    a = {"a": "1" * 64, "b": "2" * 64, "c": "3" * 64}
    b = {"c": "3" * 64, "a": "1" * 64, "b": "2" * 64}
    assert compute_inner_digest(a) == compute_inner_digest(b)


def test_inner_digest_changes_when_a_child_changes() -> None:
    base = compute_inner_digest(
        [("a", "1" * 64), ("b", "2" * 64)]
    )
    mutated = compute_inner_digest(
        [("a", "1" * 64), ("b", "9" * 64)]
    )
    assert base != mutated


def test_inner_digest_rejects_invalid_entries() -> None:
    with pytest.raises(ValueError):
        compute_inner_digest([("k", "")])
    with pytest.raises(ValueError):
        compute_inner_digest([("", "h" * 64)])
    with pytest.raises(ValueError):
        compute_inner_digest([("k",)])  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# discover_partitions
# ---------------------------------------------------------------------------


def test_discover_partitions_walks_the_three_level_layout(
    tmp_path: Path,
) -> None:
    root = _seed_event_log(tmp_path)
    keys = discover_partitions(root)
    assert len(keys) == 2
    by_sector = {k.sector_id for k in keys}
    assert by_sector == {"industry:x", "industry:y"}


def test_discover_partitions_returns_sorted_result(
    tmp_path: Path,
) -> None:
    root = _seed_event_log(tmp_path)
    keys = discover_partitions(root)
    sorted_keys = sorted(
        keys,
        key=lambda k: (
            k.year_month,
            k.sector_id,
            k.record_type,
        ),
    )
    assert keys == tuple(sorted_keys)


def test_discover_partitions_skips_unrelated_directories(
    tmp_path: Path,
) -> None:
    root = _seed_event_log(tmp_path)
    # Add a nonsense top-level directory and verify
    # discovery ignores it.
    (root / "garbage_dir").mkdir()
    (root / "year_month=").mkdir()  # empty year_month
    keys = discover_partitions(root)
    assert len(keys) == 2


def test_discover_partitions_missing_root_returns_empty(
    tmp_path: Path,
) -> None:
    keys = discover_partitions(tmp_path / "does_not_exist")
    assert keys == ()


# ---------------------------------------------------------------------------
# compute_event_log_root_digest + build_event_log_digest_tree
# ---------------------------------------------------------------------------


def test_root_digest_stable_across_reruns(
    tmp_path: Path,
) -> None:
    root = _seed_event_log(tmp_path)
    a = compute_event_log_root_digest(root)
    b = compute_event_log_root_digest(root)
    assert a == b


def test_root_digest_independent_of_filesystem_listing_order(
    tmp_path: Path,
) -> None:
    """Building the same logical event-log under two
    different roots must produce the same root digest;
    discovery is sorted, so OS-level listing order
    cannot leak into the digest."""
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    # Seed same content into both
    for r in (root_a, root_b):
        m = _manifest()
        for pk_args in (
            dict(
                year_month="2026_06",
                sector_id="industry:x",
                record_type=(
                    "manual_annotation_recorded"
                ),
            ),
            dict(
                year_month="2026_06",
                sector_id="industry:y",
                record_type=(
                    "strategic_relationship_recorded"
                ),
            ),
        ):
            pk = EventLogPartitionKey(**pk_args)
            w = EventLogPartitionWriter(
                root_path=r, partition_key=pk, manifest=m
            )
            w.append(
                [
                    _record(
                        event_id="e0",
                        event_index=0,
                        **pk_args,
                    ),
                    _record(
                        event_id="e1",
                        event_index=1,
                        **pk_args,
                    ),
                ]
            )
    da = compute_event_log_root_digest(root_a)
    db = compute_event_log_root_digest(root_b)
    assert da == db


def test_root_digest_changes_when_record_changes(
    tmp_path: Path,
) -> None:
    base_root = _seed_event_log(tmp_path / "base")
    mutated_root = _seed_event_log(tmp_path / "mutated")
    # Add an extra record to one partition only.
    m = _manifest()
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    EventLogPartitionWriter(
        root_path=mutated_root,
        partition_key=pk,
        manifest=m,
    ).append([_record(event_id="extra", event_index=99)])
    base_d = compute_event_log_root_digest(base_root)
    mut_d = compute_event_log_root_digest(mutated_root)
    assert base_d != mut_d


def test_root_digest_unchanged_partition_keeps_same_leaf(
    tmp_path: Path,
) -> None:
    """Mutate one partition, leave the other untouched.
    The unchanged partition's leaf digest must remain
    the same; only the mutated leaf and the root
    change."""
    root = _seed_event_log(tmp_path)
    pk_x = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    pk_y = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:y",
        record_type="strategic_relationship_recorded",
    )
    m = _manifest()
    leaf_y_before = compute_partition_leaf_digest(
        root, pk_y, m
    )
    root_before = compute_event_log_root_digest(root)
    # Mutate partition x only
    EventLogPartitionWriter(
        root_path=root,
        partition_key=pk_x,
        manifest=m,
    ).append([_record(event_id="a-e3", event_index=2)])
    leaf_y_after = compute_partition_leaf_digest(
        root, pk_y, m
    )
    root_after = compute_event_log_root_digest(root)
    assert leaf_y_before == leaf_y_after
    assert root_before != root_after


def test_root_digest_changes_when_manifest_changes(
    tmp_path: Path,
) -> None:
    """Same on-disk events, two different manifests,
    different root digests. The manifest is part of
    the leaf material AND part of the inner-digest
    children, so changes propagate twice over."""
    root = _seed_event_log(tmp_path)
    m_base = _manifest()
    m_bumped = _manifest(partition_schema_version="v9")
    a = compute_event_log_root_digest(root, m_base)
    b = compute_event_log_root_digest(root, m_bumped)
    assert a != b


def test_root_digest_empty_event_log_is_deterministic_and_manifest_only(
    tmp_path: Path,
) -> None:
    """Empty event log: only the sidecar exists. The
    root digest is deterministic and a function of the
    manifest only."""
    root = tmp_path / "events_empty"
    m = _manifest()
    write_manifest_sidecar(root, m)
    a = compute_event_log_root_digest(root, m)
    b = compute_event_log_root_digest(root, m)
    assert a == b
    # Different manifest → different digest
    other = compute_event_log_root_digest(
        root, _manifest(partition_schema_version="v9")
    )
    assert a != other


def test_root_digest_loads_manifest_from_sidecar_when_omitted(
    tmp_path: Path,
) -> None:
    root = _seed_event_log(tmp_path)
    explicit = compute_event_log_root_digest(
        root, _manifest()
    )
    implicit = compute_event_log_root_digest(root)
    assert explicit == implicit


def test_build_event_log_digest_tree_round_trip(
    tmp_path: Path,
) -> None:
    root = _seed_event_log(tmp_path)
    tree = build_event_log_digest_tree(root)
    assert isinstance(tree, EventLogDigestTree)
    assert tree.root_digest == (
        compute_event_log_root_digest(root)
    )
    assert tree.manifest_digest == compute_manifest_digest(
        _manifest()
    )
    # Two partitions seeded
    assert len(tree.partition_digests) == 2
    # Sorted by child-key (which starts with year_month
    # then sector_id then record_type)
    child_keys = [k for (k, _) in tree.partition_digests]
    assert child_keys == sorted(child_keys)


# ---------------------------------------------------------------------------
# Forbidden-scope + single-leaf-implementation tests
# ---------------------------------------------------------------------------


def test_event_log_merkle_module_no_columnar_dependencies() -> None:
    from world import event_log_merkle

    src = inspect.getsource(event_log_merkle)
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


def test_event_log_merkle_routes_through_compute_leaf_digest(
    tmp_path: Path,
) -> None:
    """Single leaf-hash implementation pin: monkey-patch
    compute_leaf_digest to a raise-on-call sentinel and
    verify the Merkle path explodes when it would
    otherwise compute a partition leaf. (i.e. no
    independent leaf-hash code path exists.)"""
    from world import event_log_merkle

    root = _seed_event_log(tmp_path)
    pk = EventLogPartitionKey(
        year_month="2026_06",
        sector_id="industry:x",
        record_type="manual_annotation_recorded",
    )
    sentinel_called = {"hit": False}

    def _sentinel(*a, **kw):
        sentinel_called["hit"] = True
        raise RuntimeError("sentinel triggered")

    real = event_log_merkle.compute_leaf_digest
    event_log_merkle.compute_leaf_digest = _sentinel
    try:
        with pytest.raises(RuntimeError):
            compute_partition_leaf_digest(
                root, pk, _manifest()
            )
    finally:
        event_log_merkle.compute_leaf_digest = real
    assert sentinel_called["hit"] is True


def test_root_digest_matches_explicit_recomputed_inner_digest(
    tmp_path: Path,
) -> None:
    """End-to-end check: the root digest equals the
    inner digest over
    [("__manifest__", manifest_digest), (child_key,
    partition_leaf_digest), ...]. Confirms the public
    boundary uses no other composition rule."""
    root = _seed_event_log(tmp_path)
    m = _manifest()
    md = compute_manifest_digest(m)
    pks = discover_partitions(root)
    children: list[tuple[str, str]] = [
        ("__manifest__", md)
    ]
    for pk in pks:
        leaf = compute_partition_leaf_digest(root, pk, m)
        children.append(
            (
                f"{pk.year_month}|{pk.sector_id}"
                f"|{pk.record_type}",
                leaf,
            )
        )
    expected = compute_inner_digest(children)
    actual = compute_event_log_root_digest(root, m)
    assert actual == expected


def test_event_log_merkle_module_exports_match_design_pin() -> None:
    from world import event_log_merkle

    expected = {
        "EventLogDigestTree",
        "build_event_log_digest_tree",
        "compute_event_log_root_digest",
        "compute_inner_digest",
        "compute_manifest_digest",
        "compute_partition_leaf_digest",
        "discover_partitions",
    }
    assert set(event_log_merkle.__all__) == expected


def test_event_log_merkle_does_not_call_legacy_living_world_digest() -> None:
    """The Merkle module must not import or call the
    legacy ``living_world_digest`` callable — the two
    surfaces are separate per design pin §L.3.
    Docstring mentions in the "do NOT ship" position
    are allowed; we check for imports + callable
    invocation only."""
    from world import event_log_merkle

    src = inspect.getsource(event_log_merkle)
    # No import of the legacy digest entry point.
    assert "living_world_replay" not in src
    assert "from examples.reference_world" not in src
    # No callable invocation site like
    # ``living_world_digest(...)``.
    assert "living_world_digest(" not in src
