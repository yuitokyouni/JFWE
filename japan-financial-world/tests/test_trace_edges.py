"""
v1.29.1 — TraceEdgeRecord schema + canonical serializer
+ leaf-digest pin tests.
"""

from __future__ import annotations

import hashlib
import inspect
import json

import pytest

from world.trace_edges import (
    CANONICAL_TRACE_EDGE_COLUMN_ORDER,
    TRACE_EDGE_CATEGORY_LABELS,
    TRACE_EDGE_CONFIDENCE_LABELS,
    TRACE_EDGE_PROV_COMPAT_MAPPING,
    TRACE_EDGE_SCHEMA_VERSION,
    TRACE_EDGE_TYPE_LABELS,
    TraceEdgeRecord,
    compute_trace_edge_leaf_digest,
    serialize_trace_edges_canonical_json,
    trace_edge_to_canonical_dict,
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
    evidence_ref_ids: tuple[str, ...] = (),
    citation_ids: tuple[str, ...] = (),
    actor_id: str = "",
    period_id: str = "",
    provenance_kind: str = "synthetic",
    confidence_label: str = "synthetic",
    notes: str = "",
    canonical_sort_key: str = "",
) -> TraceEdgeRecord:
    return TraceEdgeRecord(
        edge_id=edge_id,
        run_id=run_id,
        source_event_id=source_event_id,
        target_event_id=target_event_id,
        edge_type_label=edge_type_label,
        edge_category_label=edge_category_label,
        evidence_ref_ids=evidence_ref_ids,
        citation_ids=citation_ids,
        actor_id=actor_id,
        period_id=period_id,
        provenance_kind=provenance_kind,
        confidence_label=confidence_label,
        notes=notes,
        canonical_sort_key=canonical_sort_key,
    )


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


def test_trace_edge_type_labels_match_design_pin() -> None:
    assert TRACE_EDGE_TYPE_LABELS == frozenset(
        {
            "attended_to",
            "cited_as_evidence",
            "constrained_by",
            "reviewed_under",
            "propagated_to",
            "contradicted_by",
            "superseded_by",
            "derived_from",
            "related_to",
            "unknown",
        }
    )


def test_trace_edge_category_labels_match_design_pin() -> None:
    assert TRACE_EDGE_CATEGORY_LABELS == frozenset(
        {
            "evidence",
            "attention",
            "review",
            "constraint",
            "propagation",
            "contradiction",
            "lineage",
            "annotation",
            "unknown",
        }
    )


def test_trace_edge_confidence_labels_match_design_pin() -> None:
    assert TRACE_EDGE_CONFIDENCE_LABELS == frozenset(
        {
            "asserted",
            "inferred",
            "weak",
            "unknown",
            "synthetic",
        }
    )


@pytest.mark.parametrize(
    "forbidden_label",
    [
        "bullish",
        "bearish",
        "optimistic",
        "pessimistic",
        "buy",
        "sell",
        "hold",
        "target_price",
        "target_return",
        "alpha",
        "expected_alpha",
        "recommendation",
        "advice",
    ],
)
def test_no_sentiment_or_investment_labels_in_closed_sets(
    forbidden_label: str,
) -> None:
    assert forbidden_label not in TRACE_EDGE_TYPE_LABELS
    assert forbidden_label not in TRACE_EDGE_CATEGORY_LABELS
    assert (
        forbidden_label not in TRACE_EDGE_CONFIDENCE_LABELS
    )


# ---------------------------------------------------------------------------
# TraceEdgeRecord
# ---------------------------------------------------------------------------


def test_valid_minimal_trace_edge_record_accepted() -> None:
    e = _edge()
    assert e.edge_id == "te:test:001"
    assert e.evidence_ref_ids == ()
    assert e.citation_ids == ()
    # Default canonical_sort_key derivation
    assert e.canonical_sort_key == (
        "run_id=run:test:01"
        "/source=evt:src:001"
        "/target=evt:tgt:001"
        "/type=cited_as_evidence"
        "/edge_id=te:test:001"
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "edge_id",
        "run_id",
        "source_event_id",
        "target_event_id",
        "provenance_kind",
    ],
)
def test_rejects_empty_required_string(
    field_name: str,
) -> None:
    with pytest.raises(ValueError):
        _edge(**{field_name: ""})


def test_rejects_invalid_edge_type_label() -> None:
    for bad in ("bullish", "buy", "alpha", "forecast", ""):
        with pytest.raises(ValueError):
            _edge(edge_type_label=bad)


def test_rejects_invalid_edge_category_label() -> None:
    for bad in ("price_impact", "alpha_signal", ""):
        with pytest.raises(ValueError):
            _edge(edge_category_label=bad)


def test_rejects_invalid_confidence_label() -> None:
    for bad in ("0.95", "high_probability", ""):
        with pytest.raises(ValueError):
            _edge(confidence_label=bad)


def test_accepts_every_closed_set_label() -> None:
    for t in TRACE_EDGE_TYPE_LABELS:
        for c in TRACE_EDGE_CATEGORY_LABELS:
            for cl in TRACE_EDGE_CONFIDENCE_LABELS:
                rec = _edge(
                    edge_type_label=t,
                    edge_category_label=c,
                    confidence_label=cl,
                )
                assert rec.edge_type_label == t
                assert rec.edge_category_label == c
                assert rec.confidence_label == cl


def test_rejects_non_tuple_evidence_ref_ids() -> None:
    with pytest.raises(ValueError):
        _edge(evidence_ref_ids="just-a-string")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        _edge(evidence_ref_ids={"manual_annotation:x"})  # type: ignore[arg-type]


def test_rejects_empty_string_in_evidence_ref_ids() -> None:
    with pytest.raises(ValueError):
        _edge(evidence_ref_ids=("manual_annotation:x", ""))


def test_rejects_non_tuple_citation_ids() -> None:
    with pytest.raises(ValueError):
        _edge(citation_ids="just-a-string")  # type: ignore[arg-type]


def test_accepts_optional_actor_id_and_period_id_empty() -> None:
    """The default behavior is to allow actor_id /
    period_id / notes to be empty strings (matching the
    v1.28.1 EventLogRecord style for synthetic_seed /
    created_at_logical)."""
    e = _edge()
    assert e.actor_id == ""
    assert e.period_id == ""
    assert e.notes == ""


def test_accepts_explicit_canonical_sort_key() -> None:
    e = _edge(canonical_sort_key="custom-key")
    assert e.canonical_sort_key == "custom-key"


def test_record_is_frozen() -> None:
    e = _edge()
    with pytest.raises(Exception):
        e.edge_id = "different"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Canonical serialization
# ---------------------------------------------------------------------------


def test_canonical_dict_uses_explicit_column_order() -> None:
    e = _edge()
    d = trace_edge_to_canonical_dict(e)
    assert tuple(d.keys()) == CANONICAL_TRACE_EDGE_COLUMN_ORDER


def test_canonical_dict_serialises_tuples_as_lists() -> None:
    e = _edge(
        evidence_ref_ids=("ev:a", "ev:b"),
        citation_ids=("c:1",),
    )
    d = trace_edge_to_canonical_dict(e)
    assert d["evidence_ref_ids"] == ["ev:a", "ev:b"]
    assert d["citation_ids"] == ["c:1"]


def test_canonical_dict_repeated_calls_byte_identical() -> None:
    e = _edge()
    a = serialize_trace_edges_canonical_json([e])
    b = serialize_trace_edges_canonical_json([e])
    assert a == b


def test_serialize_trace_edges_uses_explicit_field_order() -> None:
    e = _edge()
    raw = serialize_trace_edges_canonical_json([e])
    parsed = json.loads(raw)
    assert tuple(parsed[0].keys()) == (
        CANONICAL_TRACE_EDGE_COLUMN_ORDER
    )


def test_canonical_dict_rejects_non_record() -> None:
    with pytest.raises(TypeError):
        trace_edge_to_canonical_dict("not a record")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Leaf digest
# ---------------------------------------------------------------------------


def test_leaf_digest_is_lowercase_hex_64() -> None:
    d = compute_trace_edge_leaf_digest([_edge()])
    assert len(d) == 64
    assert d == d.lower()
    int(d, 16)


def test_leaf_digest_stable_across_reruns() -> None:
    a = compute_trace_edge_leaf_digest([_edge()])
    b = compute_trace_edge_leaf_digest([_edge()])
    assert a == b


def test_leaf_digest_insertion_order_independent() -> None:
    e0 = _edge(edge_id="te:0")
    e1 = _edge(edge_id="te:1")
    e2 = _edge(edge_id="te:2")
    d_012 = compute_trace_edge_leaf_digest([e0, e1, e2])
    d_210 = compute_trace_edge_leaf_digest([e2, e1, e0])
    d_120 = compute_trace_edge_leaf_digest([e1, e2, e0])
    assert d_012 == d_210 == d_120


def test_leaf_digest_changes_when_an_edge_changes() -> None:
    base = compute_trace_edge_leaf_digest(
        [_edge(edge_id="te:1")]
    )
    mutated = compute_trace_edge_leaf_digest(
        [_edge(edge_id="te:1", actor_id="reviewer_a")]
    )
    assert base != mutated


def test_leaf_digest_changes_when_evidence_ref_ids_change() -> None:
    base = compute_trace_edge_leaf_digest([_edge()])
    bumped = compute_trace_edge_leaf_digest(
        [_edge(evidence_ref_ids=("ev:1",))]
    )
    assert base != bumped


def test_leaf_digest_changes_when_citation_ids_change() -> None:
    base = compute_trace_edge_leaf_digest([_edge()])
    bumped = compute_trace_edge_leaf_digest(
        [_edge(citation_ids=("c:x",))]
    )
    assert base != bumped


def test_leaf_digest_changes_when_schema_version_changes() -> None:
    a = compute_trace_edge_leaf_digest([_edge()])
    b = compute_trace_edge_leaf_digest(
        [_edge()], schema_version="v9.9-test"
    )
    assert a != b


def test_leaf_digest_empty_list_is_deterministic() -> None:
    a = compute_trace_edge_leaf_digest([])
    b = compute_trace_edge_leaf_digest(())
    c = compute_trace_edge_leaf_digest(iter(()))
    assert a == b == c


def test_leaf_digest_rejects_non_record_iterable() -> None:
    with pytest.raises(TypeError):
        compute_trace_edge_leaf_digest(["not a record"])  # type: ignore[list-item]


def test_leaf_digest_rejects_empty_schema_version() -> None:
    with pytest.raises(ValueError):
        compute_trace_edge_leaf_digest(
            [_edge()], schema_version=""
        )


def test_leaf_digest_matches_explicit_recomputed_sha256() -> None:
    """End-to-end equality check: the leaf digest equals
    SHA-256 of the canonical JSON of
    ``{"schema_version": SV, "trace_edges": [...]}``
    with edges sorted by canonical_sort_key."""
    a = _edge(edge_id="te:a")
    b = _edge(edge_id="te:b")
    sorted_records = sorted(
        [b, a], key=lambda r: r.canonical_sort_key
    )
    leaf_material = {
        "schema_version": TRACE_EDGE_SCHEMA_VERSION,
        "trace_edges": [
            trace_edge_to_canonical_dict(r)
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
    assert compute_trace_edge_leaf_digest([b, a]) == expected


# ---------------------------------------------------------------------------
# PROV-O conceptual mapping
# ---------------------------------------------------------------------------


def test_prov_compat_mapping_covers_every_edge_type_label() -> None:
    for t in TRACE_EDGE_TYPE_LABELS:
        assert t in TRACE_EDGE_PROV_COMPAT_MAPPING


def test_prov_compat_mapping_values_are_strings() -> None:
    for k, v in TRACE_EDGE_PROV_COMPAT_MAPPING.items():
        assert isinstance(v, str)
        assert v


def test_prov_compat_mapping_uses_descriptive_namespaces() -> None:
    """Mapping values use ``prov:…Like`` or ``jfwe:…``
    naming. The ``Like`` suffix on prov-derived names
    pins the conceptual-only nature of the mapping."""
    for k, v in TRACE_EDGE_PROV_COMPAT_MAPPING.items():
        assert v.startswith(("prov:", "jfwe:"))
        if v.startswith("prov:"):
            assert v.endswith("Like")


# ---------------------------------------------------------------------------
# Forbidden-scope tests
# ---------------------------------------------------------------------------


def test_module_no_graph_database_or_rdf_imports() -> None:
    from world import trace_edges

    src = inspect.getsource(trace_edges)
    for tok in (
        "import rdflib",
        "from rdflib",
        "import owlready",
        "from owlready",
        "import sparql",
        "from sparql",
        "import neo4j",
        "from neo4j",
        "import networkx",
        "from networkx",
        "import gremlin",
        "from gremlin",
        "import polars",
        "from polars",
        "import duckdb",
        "from duckdb",
        "import pyarrow",
        "from pyarrow",
    ):
        assert tok not in src


def test_module_no_real_data_adapter_imports() -> None:
    from world import trace_edges

    src = inspect.getsource(trace_edges).lower()
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


def test_module_does_not_introduce_prev_or_self_hash_field() -> None:
    """Per the v1.29 design clarification, trace edges
    must not carry a `prev_hash` / `self_hash` chain.
    Tamper evidence is delegated to the v1.28 event-log
    / manifest / Merkle substrate."""
    from dataclasses import fields as dc_fields

    field_names = {
        f.name for f in dc_fields(TraceEdgeRecord)
    }
    forbidden = {"prev_hash", "self_hash", "edge_chain_hash"}
    assert (field_names & forbidden) == set()


def test_module_does_not_register_a_kernel_field() -> None:
    from world.kernel import WorldKernel

    fnames = {
        f.name
        for f in WorldKernel.__dataclass_fields__.values()
    }
    forbidden = {
        "trace_edges",
        "trace_edge_book",
        "trace_edge_store",
    }
    assert (fnames & forbidden) == set()


def test_module_exports_match_design_pin() -> None:
    from world import trace_edges

    expected = {
        "CANONICAL_TRACE_EDGE_COLUMN_ORDER",
        "TRACE_EDGE_CATEGORY_LABELS",
        "TRACE_EDGE_CONFIDENCE_LABELS",
        "TRACE_EDGE_PROV_COMPAT_MAPPING",
        "TRACE_EDGE_SCHEMA_VERSION",
        "TRACE_EDGE_TYPE_LABELS",
        "TraceEdgeRecord",
        "compute_trace_edge_leaf_digest",
        "serialize_trace_edges_canonical_json",
        "trace_edge_to_canonical_dict",
    }
    assert set(trace_edges.__all__) == expected
