"""
v1.28.1 — Event-log schema + canonical serializer +
leaf-digest function boundary pin tests.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from world.event_log_schema import (
    CANONICAL_SCHEMA_COLUMN_NAMES,
    CANONICAL_SCHEMA_COLUMN_ORDER,
    EventLogManifest,
    EventLogRecord,
    compute_leaf_digest,
    event_log_record_to_canonical_dict,
    manifest_to_canonical_dict,
    serialize_canonical_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record(
    *,
    event_id: str = "evt:test:001",
    run_id: str = "run:test:01",
    period_id: str = "2026-Q2",
    year_month: str = "2026_06",
    sector_id: str = "industry:x",
    record_type: str = "manual_annotation_recorded",
    source_space: str = "world.manual_annotations",
    target_entity_type: str = "firm",
    target_entity_id: str = "firm:a",
    event_index: int = 0,
    payload_schema_version: str = "v1.24.1",
    payload_ref_or_json: str = '{"k":"v"}',
    parent_event_ids: tuple[str, ...] = (),
    provenance_kind: str = "synthetic",
    synthetic_seed: str = "",
    created_at_logical: str = "",
    partition_key: str = "",
    canonical_sort_key: str = "",
) -> EventLogRecord:
    return EventLogRecord(
        event_id=event_id,
        run_id=run_id,
        period_id=period_id,
        year_month=year_month,
        sector_id=sector_id,
        record_type=record_type,
        source_space=source_space,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        event_index=event_index,
        payload_schema_version=payload_schema_version,
        payload_ref_or_json=payload_ref_or_json,
        parent_event_ids=parent_event_ids,
        provenance_kind=provenance_kind,
        synthetic_seed=synthetic_seed,
        created_at_logical=created_at_logical,
        partition_key=partition_key,
        canonical_sort_key=canonical_sort_key,
    )


def _manifest(
    *,
    manifest_version: str = "v1.28.1-prototype",
    partition_schema_version: str = "v1.28.1-partition-v1",
    partition_key_fields: tuple[str, ...] = (
        "year_month",
        "sector_id",
        "record_type",
    ),
    event_schema_version: str = "v1.28.1-event-v1",
    canonical_sort_key_fields: tuple[str, ...] = (
        "partition_key",
        "event_index",
        "event_id",
        "canonical_sort_key",
    ),
    schema_column_order: tuple[str, ...] = (
        CANONICAL_SCHEMA_COLUMN_ORDER
    ),
    digest_algorithm: str = "sha256",
    leaf_serializer: str = "canonical-json-v1",
    merkle_tree_version: str = "merkle-v1-prototype",
) -> EventLogManifest:
    return EventLogManifest(
        manifest_version=manifest_version,
        partition_schema_version=partition_schema_version,
        partition_key_fields=partition_key_fields,
        event_schema_version=event_schema_version,
        canonical_sort_key_fields=(
            canonical_sort_key_fields
        ),
        schema_column_order=schema_column_order,
        digest_algorithm=digest_algorithm,
        leaf_serializer=leaf_serializer,
        merkle_tree_version=merkle_tree_version,
    )


# ---------------------------------------------------------------------------
# EventLogRecord
# ---------------------------------------------------------------------------


def test_event_log_record_accepts_valid_minimal_record() -> None:
    r = _record()
    assert r.event_id == "evt:test:001"
    assert r.event_index == 0
    assert r.parent_event_ids == ()
    # Defaults derived for partition_key / canonical_sort_key
    assert r.partition_key == (
        "year_month=2026_06"
        "/sector_id=industry:x"
        "/record_type=manual_annotation_recorded"
    )
    assert r.canonical_sort_key == (
        f"{r.partition_key}"
        "/event_index=000000000000"
        "/event_id=evt:test:001"
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "event_id",
        "run_id",
        "period_id",
        "year_month",
        "sector_id",
        "record_type",
        "source_space",
        "target_entity_type",
        "target_entity_id",
        "payload_schema_version",
        "payload_ref_or_json",
        "provenance_kind",
    ],
)
def test_event_log_record_rejects_empty_required_string(
    field_name: str,
) -> None:
    with pytest.raises(ValueError):
        _record(**{field_name: ""})


def test_event_log_record_rejects_negative_event_index() -> None:
    with pytest.raises(ValueError):
        _record(event_index=-1)


def test_event_log_record_rejects_non_int_event_index() -> None:
    with pytest.raises(ValueError):
        _record(event_index="0")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        _record(event_index=True)  # type: ignore[arg-type]


def test_event_log_record_rejects_non_tuple_parent_event_ids() -> None:
    # Bare string is rejected (project style: explicit
    # tuple/list of non-empty strings).
    with pytest.raises(ValueError):
        _record(parent_event_ids="evt:parent")  # type: ignore[arg-type]
    # set is not accepted (no deterministic order).
    with pytest.raises(ValueError):
        _record(parent_event_ids={"evt:p"})  # type: ignore[arg-type]


def test_event_log_record_rejects_empty_string_in_parent_event_ids() -> None:
    with pytest.raises(ValueError):
        _record(parent_event_ids=("evt:p", ""))


def test_event_log_record_accepts_explicit_partition_key_and_sort_key() -> None:
    r = _record(
        partition_key="custom-partition-key",
        canonical_sort_key="custom-sort-key",
    )
    assert r.partition_key == "custom-partition-key"
    assert r.canonical_sort_key == "custom-sort-key"


def test_event_log_record_canonical_sort_key_pads_event_index() -> None:
    r = _record(event_index=42)
    # 12-digit zero-padding is binding for sort stability.
    assert "/event_index=000000000042/" in r.canonical_sort_key


def test_event_log_record_is_frozen() -> None:
    r = _record()
    with pytest.raises(Exception):
        r.event_index = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# EventLogManifest
# ---------------------------------------------------------------------------


def test_event_log_manifest_accepts_valid_manifest() -> None:
    m = _manifest()
    assert m.digest_algorithm == "sha256"
    assert m.leaf_serializer == "canonical-json-v1"
    assert m.merkle_tree_version == "merkle-v1-prototype"
    assert "year_month" in m.partition_key_fields
    assert "sector_id" in m.partition_key_fields
    assert "record_type" in m.partition_key_fields
    assert "canonical_sort_key" in m.canonical_sort_key_fields


@pytest.mark.parametrize(
    "field_name",
    [
        "manifest_version",
        "partition_schema_version",
        "event_schema_version",
        "leaf_serializer",
        "merkle_tree_version",
    ],
)
def test_event_log_manifest_rejects_empty_required_string(
    field_name: str,
) -> None:
    with pytest.raises(ValueError):
        _manifest(**{field_name: ""})


def test_event_log_manifest_rejects_non_sha256_digest_algorithm() -> None:
    for bad in ("md5", "sha1", "sha512", "blake3", "xxhash", ""):
        with pytest.raises(ValueError):
            _manifest(digest_algorithm=bad)


def test_event_log_manifest_rejects_partition_key_fields_missing_required() -> None:
    # Missing year_month
    with pytest.raises(ValueError):
        _manifest(
            partition_key_fields=("sector_id", "record_type")
        )
    # Missing sector_id
    with pytest.raises(ValueError):
        _manifest(
            partition_key_fields=("year_month", "record_type")
        )
    # Missing record_type
    with pytest.raises(ValueError):
        _manifest(
            partition_key_fields=("year_month", "sector_id")
        )


def test_event_log_manifest_rejects_canonical_sort_key_fields_missing_required() -> None:
    with pytest.raises(ValueError):
        _manifest(
            canonical_sort_key_fields=(
                "partition_key",
                "event_index",
            )
        )


def test_event_log_manifest_rejects_schema_column_order_with_missing_field() -> None:
    bad_order = tuple(
        c for c in CANONICAL_SCHEMA_COLUMN_ORDER if c != "event_id"
    )
    with pytest.raises(ValueError):
        _manifest(schema_column_order=bad_order)


def test_event_log_manifest_rejects_schema_column_order_with_extra_field() -> None:
    bad_order = CANONICAL_SCHEMA_COLUMN_ORDER + (
        "phantom_field",
    )
    with pytest.raises(ValueError):
        _manifest(schema_column_order=bad_order)


def test_event_log_manifest_rejects_schema_column_order_with_duplicates() -> None:
    bad_order = CANONICAL_SCHEMA_COLUMN_ORDER + (
        "event_id",
    )
    with pytest.raises(ValueError):
        _manifest(schema_column_order=bad_order)


def test_event_log_manifest_accepts_alternate_valid_column_order() -> None:
    # Reverse order — same set, different sequence; the
    # manifest must accept it (and the leaf digest will
    # differ, by design — see leaf-digest tests below).
    rev = tuple(reversed(CANONICAL_SCHEMA_COLUMN_ORDER))
    m = _manifest(schema_column_order=rev)
    assert m.schema_column_order == rev


def test_event_log_manifest_rejects_empty_tuple_field() -> None:
    with pytest.raises(ValueError):
        _manifest(partition_key_fields=())


# ---------------------------------------------------------------------------
# Canonical serialization
# ---------------------------------------------------------------------------


def test_canonical_dict_uses_explicit_column_order() -> None:
    r = _record()
    d = event_log_record_to_canonical_dict(r)
    assert tuple(d.keys()) == CANONICAL_SCHEMA_COLUMN_ORDER


def test_canonical_dict_serialises_tuples_as_lists() -> None:
    r = _record(parent_event_ids=("evt:a", "evt:b"))
    d = event_log_record_to_canonical_dict(r)
    assert d["parent_event_ids"] == ["evt:a", "evt:b"]


def test_canonical_dict_construction_order_does_not_change_canonical_bytes() -> None:
    # Build the same record's canonical dict twice and
    # confirm byte-identical JSON output across reruns.
    r = _record()
    d1 = event_log_record_to_canonical_dict(r)
    d2 = event_log_record_to_canonical_dict(r)
    b1 = serialize_canonical_json(d1)
    b2 = serialize_canonical_json(d2)
    assert b1 == b2


def test_canonical_dict_with_alternate_column_order_produces_different_bytes() -> None:
    r = _record()
    d_default = event_log_record_to_canonical_dict(r)
    rev = tuple(reversed(CANONICAL_SCHEMA_COLUMN_ORDER))
    d_rev = event_log_record_to_canonical_dict(
        r, column_order=rev
    )
    assert serialize_canonical_json(d_default) != (
        serialize_canonical_json(d_rev)
    )


def test_canonical_dict_rejects_invalid_column_order() -> None:
    r = _record()
    with pytest.raises(ValueError):
        event_log_record_to_canonical_dict(
            r,
            column_order=tuple(
                c
                for c in CANONICAL_SCHEMA_COLUMN_ORDER
                if c != "event_id"
            ),
        )


def test_serialize_canonical_json_uses_compact_separators_and_utf8() -> None:
    # No whitespace between keys / values, no extra
    # spaces. Non-ASCII characters survive as UTF-8
    # bytes (ensure_ascii=False).
    payload = {"a": "x", "b": [1, 2, 3]}
    out = serialize_canonical_json(payload)
    assert b' ' not in out
    # Non-ASCII via canonical bytes (smoke-test
    # ensure_ascii=False).
    out2 = serialize_canonical_json({"k": "α"})
    assert "α".encode("utf-8") in out2


def test_serialize_canonical_json_repeated_calls_are_byte_identical() -> None:
    payload = {"b": 2, "a": 1, "c": [3, 2, 1]}
    out1 = serialize_canonical_json(payload)
    out2 = serialize_canonical_json(payload)
    assert out1 == out2


def test_manifest_canonical_dict_has_alphabetic_keys() -> None:
    m = _manifest()
    d = manifest_to_canonical_dict(m)
    keys = tuple(d.keys())
    assert keys == tuple(sorted(keys))


def test_manifest_canonical_dict_bytes_are_stable() -> None:
    m1 = _manifest()
    m2 = _manifest()
    b1 = serialize_canonical_json(
        manifest_to_canonical_dict(m1), sort_keys=True
    )
    b2 = serialize_canonical_json(
        manifest_to_canonical_dict(m2), sort_keys=True
    )
    assert b1 == b2


# ---------------------------------------------------------------------------
# Leaf digest
# ---------------------------------------------------------------------------


def test_leaf_digest_is_lowercase_hex_64() -> None:
    digest = compute_leaf_digest([_record()], _manifest())
    assert isinstance(digest, str)
    assert len(digest) == 64
    assert digest == digest.lower()
    int(digest, 16)  # parses as hex


def test_leaf_digest_is_stable_across_reruns() -> None:
    d1 = compute_leaf_digest(
        [_record(event_id="e1"), _record(event_id="e2", event_index=1)],
        _manifest(),
    )
    d2 = compute_leaf_digest(
        [_record(event_id="e1"), _record(event_id="e2", event_index=1)],
        _manifest(),
    )
    assert d1 == d2


def test_leaf_digest_is_insertion_order_independent() -> None:
    a = _record(event_id="e1", event_index=0)
    b = _record(event_id="e2", event_index=1)
    c = _record(event_id="e3", event_index=2)
    d_ab_c = compute_leaf_digest([a, b, c], _manifest())
    d_c_ba = compute_leaf_digest([c, b, a], _manifest())
    d_b_ac = compute_leaf_digest([b, a, c], _manifest())
    assert d_ab_c == d_c_ba == d_b_ac


def test_leaf_digest_changes_when_a_record_changes() -> None:
    base = compute_leaf_digest(
        [_record(event_id="e1"), _record(event_id="e2", event_index=1)],
        _manifest(),
    )
    mutated = compute_leaf_digest(
        [
            _record(event_id="e1"),
            _record(
                event_id="e2",
                event_index=1,
                target_entity_id="firm:b",
            ),
        ],
        _manifest(),
    )
    assert base != mutated


def test_leaf_digest_changes_when_manifest_partition_schema_version_changes() -> None:
    records = [_record()]
    base = compute_leaf_digest(records, _manifest())
    bumped = compute_leaf_digest(
        records,
        _manifest(partition_schema_version="v1.28.1-partition-v2"),
    )
    assert base != bumped


def test_leaf_digest_changes_when_manifest_event_schema_version_changes() -> None:
    records = [_record()]
    base = compute_leaf_digest(records, _manifest())
    bumped = compute_leaf_digest(
        records,
        _manifest(event_schema_version="v1.28.1-event-v2"),
    )
    assert base != bumped


def test_leaf_digest_changes_when_manifest_partition_key_fields_changes() -> None:
    records = [_record()]
    base = compute_leaf_digest(records, _manifest())
    expanded = compute_leaf_digest(
        records,
        _manifest(
            partition_key_fields=(
                "year_month",
                "sector_id",
                "record_type",
                "run_id",
            )
        ),
    )
    assert base != expanded


def test_leaf_digest_changes_when_schema_column_order_changes() -> None:
    records = [_record()]
    base = compute_leaf_digest(records, _manifest())
    rev = tuple(reversed(CANONICAL_SCHEMA_COLUMN_ORDER))
    bumped = compute_leaf_digest(
        records, _manifest(schema_column_order=rev)
    )
    assert base != bumped


def test_leaf_digest_empty_list_is_deterministic_and_manifest_only() -> None:
    d1 = compute_leaf_digest([], _manifest())
    d2 = compute_leaf_digest((), _manifest())
    d3 = compute_leaf_digest(iter(()), _manifest())
    assert d1 == d2 == d3
    # An empty leaf with a different manifest must
    # produce a different digest (manifest-only
    # surface).
    d_other = compute_leaf_digest(
        [],
        _manifest(partition_schema_version="alt"),
    )
    assert d1 != d_other


def test_leaf_digest_rejects_non_record_iterable() -> None:
    with pytest.raises(TypeError):
        compute_leaf_digest(["not a record"], _manifest())  # type: ignore[list-item]


def test_leaf_digest_rejects_non_manifest() -> None:
    with pytest.raises(TypeError):
        compute_leaf_digest([_record()], "not a manifest")  # type: ignore[arg-type]


def test_leaf_digest_matches_explicit_recomputed_sha256() -> None:
    """End-to-end check: the leaf digest equals the
    SHA-256 of the canonical JSON of
    ``{"manifest": manifest_canonical_dict,
       "records": [record_canonical_dict, ...]}``
    with records sorted by ``canonical_sort_key``.
    """
    a = _record(event_id="e1", event_index=0)
    b = _record(event_id="e2", event_index=1)
    m = _manifest()
    sorted_records = sorted(
        [b, a], key=lambda r: r.canonical_sort_key
    )
    leaf_material = {
        "manifest": manifest_to_canonical_dict(m),
        "records": [
            event_log_record_to_canonical_dict(
                r, column_order=m.schema_column_order
            )
            for r in sorted_records
        ],
    }
    expected = hashlib.sha256(
        json.dumps(
            leaf_material,
            ensure_ascii=False,
            sort_keys=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert compute_leaf_digest([b, a], m) == expected


# ---------------------------------------------------------------------------
# Forbidden-scope tests (v1.28.1 boundary)
# ---------------------------------------------------------------------------


def test_event_log_schema_module_does_not_import_forbidden_dependencies() -> None:
    """Ensure the v1.28.1 module text does not import
    Polars / DuckDB / PyArrow / xxhash / Rust / PyO3 /
    Parquet-writer libraries. The v1.28.0 design pin
    forbids these at v1.28.1."""
    import inspect

    from world import event_log_schema

    src = inspect.getsource(event_log_schema)
    forbidden_imports = (
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
    )
    for tok in forbidden_imports:
        assert tok not in src, (
            f"v1.28.1 module must not contain {tok!r}; "
            "see docs/v1_28_scale_substrate_event_log_columnar_merkle.md "
            "§T (dependency policy)"
        )


def test_event_log_schema_module_does_not_mention_real_data_adapters() -> None:
    """Ensure the v1.28.1 module text does not mention
    real-data adapter names as implementation
    targets. Mentioning them in a forbidden-list
    position is allowed; using them as code is not."""
    import inspect

    from world import event_log_schema

    src = inspect.getsource(event_log_schema)
    # No `import ...` or `from ... import` lines for
    # any real-data adapter.
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
        assert (
            f"import {adapter}" not in src.lower()
        ), f"v1.28.1 module must not import {adapter!r}"
        assert (
            f"from {adapter}" not in src.lower()
        ), f"v1.28.1 module must not import from {adapter!r}"


def test_event_log_schema_module_does_not_write_or_read_files() -> None:
    """Ensure the v1.28.1 module does not perform
    filesystem I/O. v1.28.2+ adds the writer; v1.28.1
    is in-memory only."""
    import inspect

    from world import event_log_schema

    src = inspect.getsource(event_log_schema)
    forbidden_io = (
        "open(",
        "Path(",
        "os.makedirs",
        "os.path",
        "shutil.",
        ".write_parquet",
        ".to_parquet",
        ".read_parquet",
    )
    for tok in forbidden_io:
        assert tok not in src, (
            f"v1.28.1 module must not perform I/O ({tok!r})"
        )


def test_event_log_schema_canonical_digests_module_still_importable() -> None:
    """v1.28.1 must not change any canonical
    living_world_digest value. The v1.28.1 module is a
    new file with no kernel field; this test sanity-
    checks the canonical-digests module can still be
    imported and that the three constants are valid
    64-character lowercase hex SHA-256 strings. The
    *exact* expected hex values are pinned by the
    canonical-digests module's own tests; duplicating
    them here would trip the
    test_no_duplicate_canonical_digest_literals_outside_canonical_module
    pin."""
    from _canonical_digests import (
        MONTHLY_REFERENCE_LIVING_WORLD_DIGEST,
        QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
        SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST,
    )

    for digest in (
        QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
        MONTHLY_REFERENCE_LIVING_WORLD_DIGEST,
        SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST,
    ):
        assert isinstance(digest, str)
        assert len(digest) == 64
        assert digest == digest.lower()
        int(digest, 16)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


def test_module_exports_match_design_pin() -> None:
    """The single public leaf-digest boundary is
    :func:`compute_leaf_digest`. The module's public
    surface is pinned by ``__all__``."""
    from world import event_log_schema

    expected = {
        "CANONICAL_SCHEMA_COLUMN_NAMES",
        "CANONICAL_SCHEMA_COLUMN_ORDER",
        "EventLogManifest",
        "EventLogRecord",
        "compute_leaf_digest",
        "event_log_record_to_canonical_dict",
        "manifest_to_canonical_dict",
        "serialize_canonical_json",
    }
    assert set(event_log_schema.__all__) == expected


def test_canonical_schema_column_names_matches_order_set() -> None:
    assert CANONICAL_SCHEMA_COLUMN_NAMES == frozenset(
        CANONICAL_SCHEMA_COLUMN_ORDER
    )
    # 18 fields in the canonical schema (per v1.28.0 §D.3
    # candidate event schema).
    assert len(CANONICAL_SCHEMA_COLUMN_ORDER) == 18
