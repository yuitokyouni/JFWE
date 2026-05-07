"""
v1.29.3 — Deterministic CitationGraphProjection pin
tests.
"""

from __future__ import annotations

import inspect

import pytest

from world.citation_graph_projection import (
    CitationGraphProjection,
    build_citation_graph_projection,
)
from world.event_log_schema import (
    EventLogRecord,
)
from world.trace_edges import (
    TraceEdgeRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _evt(
    *,
    event_id: str,
    record_type: str = "manual_annotation_recorded",
    target_entity_id: str = "firm:a",
) -> EventLogRecord:
    return EventLogRecord(
        event_id=event_id,
        run_id="run:test:01",
        period_id="2026-Q2",
        year_month="2026_06",
        sector_id="industry:x",
        record_type=record_type,
        source_space="world.test",
        target_entity_type="firm",
        target_entity_id=target_entity_id,
        event_index=0,
        payload_schema_version="v1.0",
        payload_ref_or_json='{"k":"v"}',
    )


def _edge(
    *,
    edge_id: str,
    source_event_id: str,
    target_event_id: str,
    edge_type_label: str = "cited_as_evidence",
    edge_category_label: str = "evidence",
    actor_id: str = "",
    evidence_ref_ids: tuple[str, ...] = (),
    citation_ids: tuple[str, ...] = (),
) -> TraceEdgeRecord:
    return TraceEdgeRecord(
        edge_id=edge_id,
        run_id="run:test:01",
        source_event_id=source_event_id,
        target_event_id=target_event_id,
        edge_type_label=edge_type_label,
        edge_category_label=edge_category_label,
        period_id="2026-Q2",
        actor_id=actor_id,
        evidence_ref_ids=evidence_ref_ids,
        citation_ids=citation_ids,
    )


def _seed():
    """Seed three events and four edges; return (events,
    edges)."""
    e1 = _evt(event_id="evt:e1")
    e2 = _evt(event_id="evt:e2")
    e3 = _evt(
        event_id="evt:e3",
        record_type="strategic_relationship_recorded",
    )
    edges = [
        _edge(
            edge_id="te:1",
            source_event_id="evt:e1",
            target_event_id="evt:e2",
            edge_type_label="cited_as_evidence",
            edge_category_label="evidence",
            actor_id="reviewer_a",
            evidence_ref_ids=("ev:x",),
            citation_ids=("c:1",),
        ),
        _edge(
            edge_id="te:2",
            source_event_id="evt:e2",
            target_event_id="evt:e3",
            edge_type_label="propagated_to",
            edge_category_label="propagation",
            actor_id="reviewer_a",
            evidence_ref_ids=("ev:x",),
        ),
        _edge(
            edge_id="te:3",
            source_event_id="evt:e1",
            target_event_id="evt:e3",
            edge_type_label="reviewed_under",
            edge_category_label="review",
            actor_id="reviewer_b",
        ),
        _edge(
            edge_id="te:4",
            source_event_id="evt:e2",
            target_event_id="evt:e1",
            edge_type_label="contradicted_by",
            edge_category_label="contradiction",
        ),
    ]
    return [e1, e2, e3], edges


# ---------------------------------------------------------------------------
# Basic shape
# ---------------------------------------------------------------------------


def test_projection_returns_dataclass() -> None:
    events, edges = _seed()
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    assert isinstance(p, CitationGraphProjection)


def test_projection_node_event_ids_sorted() -> None:
    events, edges = _seed()
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    assert p.node_event_ids == (
        "evt:e1",
        "evt:e2",
        "evt:e3",
    )


def test_projection_edge_ids_sorted_by_canonical_sort_key() -> None:
    events, edges = _seed()
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    # Edge ids are ordered by canonical_sort_key
    # (which contains source/target/type, not just
    # edge_id), so the order is NOT alphabetic on
    # edge_id. Compute the expected order explicitly.
    expected_order = tuple(
        e.edge_id
        for e in sorted(
            edges, key=lambda x: x.canonical_sort_key
        )
    )
    assert p.edge_ids == expected_order


def test_projection_nodes_by_record_type_correct() -> None:
    events, edges = _seed()
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    d = dict(p.nodes_by_record_type)
    assert d == {
        "manual_annotation_recorded": 2,
        "strategic_relationship_recorded": 1,
    }


def test_projection_edges_by_type_correct() -> None:
    events, edges = _seed()
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    d = dict(p.edges_by_type)
    assert d == {
        "cited_as_evidence": 1,
        "propagated_to": 1,
        "reviewed_under": 1,
        "contradicted_by": 1,
    }


def test_projection_edges_by_category_correct() -> None:
    events, edges = _seed()
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    d = dict(p.edges_by_category)
    assert d == {
        "evidence": 1,
        "propagation": 1,
        "review": 1,
        "contradiction": 1,
    }


def test_projection_evidence_ref_counts_correct() -> None:
    events, edges = _seed()
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    assert dict(p.evidence_ref_counts) == {"ev:x": 2}


def test_projection_citation_ref_counts_correct() -> None:
    events, edges = _seed()
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    assert dict(p.citation_ref_counts) == {"c:1": 1}


def test_projection_actor_edge_counts_correct() -> None:
    events, edges = _seed()
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    assert dict(p.actor_edge_counts) == {
        "reviewer_a": 2,
        "reviewer_b": 1,
    }


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_projection_deterministic_across_repeated_calls() -> None:
    events, edges = _seed()
    a = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    b = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    assert a == b
    assert a.projection_digest == b.projection_digest


def test_projection_edge_insertion_order_independent() -> None:
    events, edges = _seed()
    a = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    b = build_citation_graph_projection(
        events,
        list(reversed(edges)),
        run_id="run:test:01",
    )
    c = build_citation_graph_projection(
        events,
        [edges[2], edges[0], edges[3], edges[1]],
        run_id="run:test:01",
    )
    assert a == b == c


def test_projection_event_insertion_order_independent() -> None:
    events, edges = _seed()
    a = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    b = build_citation_graph_projection(
        list(reversed(events)),
        edges,
        run_id="run:test:01",
    )
    assert a == b


def test_projection_digest_lowercase_hex_64() -> None:
    events, edges = _seed()
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    assert len(p.projection_digest) == 64
    assert (
        p.projection_digest == p.projection_digest.lower()
    )
    int(p.projection_digest, 16)


def test_projection_digest_changes_when_edge_changes() -> None:
    events, edges = _seed()
    p_base = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    edges_alt = list(edges)
    edges_alt[0] = _edge(
        edge_id="te:1",
        source_event_id="evt:e1",
        target_event_id="evt:e2",
        edge_type_label="cited_as_evidence",
        edge_category_label="evidence",
        actor_id="reviewer_a",
        evidence_ref_ids=("ev:y",),  # changed
        citation_ids=("c:1",),
    )
    p_alt = build_citation_graph_projection(
        events, edges_alt, run_id="run:test:01"
    )
    assert (
        p_base.projection_digest
        != p_alt.projection_digest
    )


def test_projection_digest_changes_when_event_set_changes() -> None:
    events, edges = _seed()
    p_base = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    events_alt = events + [_evt(event_id="evt:extra")]
    p_alt = build_citation_graph_projection(
        events_alt, edges, run_id="run:test:01"
    )
    assert (
        p_base.projection_digest
        != p_alt.projection_digest
    )


def test_projection_digest_changes_when_run_id_changes() -> None:
    events, edges = _seed()
    a = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    b = build_citation_graph_projection(
        events, edges, run_id="run:test:02"
    )
    assert a.projection_digest != b.projection_digest


# ---------------------------------------------------------------------------
# Connectivity / dangling
# ---------------------------------------------------------------------------


def test_projection_disconnected_event_ids_surfaced() -> None:
    events, edges = _seed()
    events_with_extra = events + [
        _evt(event_id="evt:lonely")
    ]
    p = build_citation_graph_projection(
        events_with_extra, edges, run_id="run:test:01"
    )
    assert p.disconnected_event_ids == ("evt:lonely",)


def test_projection_dangling_source_target_surfaced() -> None:
    events = [_evt(event_id="evt:e1")]
    edges = [
        _edge(
            edge_id="te:1",
            source_event_id="evt:e1",
            target_event_id="evt:phantom_target",
        ),
        _edge(
            edge_id="te:2",
            source_event_id="evt:phantom_source",
            target_event_id="evt:e1",
        ),
    ]
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    assert p.dangling_target_event_ids == (
        "evt:phantom_target",
    )
    assert p.dangling_source_event_ids == (
        "evt:phantom_source",
    )


# ---------------------------------------------------------------------------
# Empty inputs
# ---------------------------------------------------------------------------


def test_projection_empty_inputs_deterministic() -> None:
    a = build_citation_graph_projection(
        [], [], run_id="run:test:01"
    )
    b = build_citation_graph_projection(
        (), (), run_id="run:test:01"
    )
    assert a == b
    assert a.node_event_ids == ()
    assert a.edge_ids == ()
    assert a.disconnected_event_ids == ()
    assert a.dangling_source_event_ids == ()
    assert a.dangling_target_event_ids == ()


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------


def test_projection_does_not_mutate_inputs() -> None:
    events, edges = _seed()
    events_snapshot = list(events)
    edges_snapshot = list(edges)
    build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    assert events == events_snapshot
    assert edges == edges_snapshot


# ---------------------------------------------------------------------------
# Type guards
# ---------------------------------------------------------------------------


def test_projection_rejects_non_event_record() -> None:
    with pytest.raises(TypeError):
        build_citation_graph_projection(
            ["not a record"],  # type: ignore[list-item]
            [],
            run_id="r",
        )


def test_projection_rejects_non_trace_edge() -> None:
    events, _ = _seed()
    with pytest.raises(TypeError):
        build_citation_graph_projection(
            events,
            ["not an edge"],  # type: ignore[list-item]
            run_id="r",
        )


def test_projection_rejects_empty_run_id() -> None:
    with pytest.raises(ValueError):
        build_citation_graph_projection(
            [], [], run_id=""
        )


# ---------------------------------------------------------------------------
# Frozen / immutable
# ---------------------------------------------------------------------------


def test_projection_dataclass_is_frozen() -> None:
    p = build_citation_graph_projection(
        [], [], run_id="run:test:01"
    )
    with pytest.raises(Exception):
        p.run_id = "different"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Forbidden-scope tests
# ---------------------------------------------------------------------------


def test_module_no_graph_database_or_rdf_imports() -> None:
    from world import citation_graph_projection

    src = inspect.getsource(citation_graph_projection)
    for tok in (
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
        "import polars",
        "from polars",
        "import duckdb",
        "from duckdb",
        "import pyarrow",
        "from pyarrow",
    ):
        assert tok not in src


def test_module_no_centrality_or_embedding_or_pagerank_functions() -> None:
    """Per design pin §H.2, centrality / PageRank /
    community-detection / embedding surfaces are
    forbidden in CitationGraphProjection. Check for
    function-call / function-definition patterns
    (docstring negations are allowed)."""
    from world import citation_graph_projection

    src = inspect.getsource(citation_graph_projection)
    # Function-definition forbidden patterns
    for tok in (
        "def compute_centrality",
        "def pagerank",
        "def betweenness_centrality",
        "def eigenvector_centrality",
        "def community_detection",
        "def detect_communities",
        "def louvain",
        "def node2vec",
        "def build_embedding",
        "def compute_embedding",
    ):
        assert tok not in src
    # Function-call forbidden patterns
    for tok in (
        "centrality(",
        "pagerank(",
        "betweenness(",
        "eigenvector(",
        "community_detect(",
        "louvain(",
        "node2vec(",
    ):
        assert tok not in src


def test_module_does_not_register_a_kernel_field() -> None:
    from world.kernel import WorldKernel

    fnames = {
        f.name
        for f in WorldKernel.__dataclass_fields__.values()
    }
    forbidden = {
        "citation_graph_projection",
        "citation_graph",
        "trace_graph_projection",
    }
    assert (fnames & forbidden) == set()


def test_module_exports_match_design_pin() -> None:
    from world import citation_graph_projection

    expected = {
        "CitationGraphProjection",
        "build_citation_graph_projection",
    }
    assert (
        set(citation_graph_projection.__all__)
        == expected
    )
