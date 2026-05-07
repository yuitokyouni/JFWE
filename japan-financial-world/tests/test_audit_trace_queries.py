"""
v1.29.4 — Deterministic audit trace query helpers pin
tests.
"""

from __future__ import annotations

import inspect

import pytest

from world.audit_trace_queries import (
    AuditTraceSummary,
    CONTRADICTION_EDGE_TYPE_LABELS,
    COUNTERFACTUAL_REPLAY_NOT_IMPLEMENTED_MESSAGE,
    LINEAGE_EDGE_TYPE_LABELS,
    PROPAGATION_EDGE_TYPE_LABELS,
    list_contradiction_pairs,
    list_edges_by_actor,
    list_edges_for_event,
    list_events_citing_evidence,
    list_evidence_for_judgment_event,
    list_propagation_edges,
    summarize_audit_questions,
    trace_lineage_to_origin,
)
from world.citation_graph_projection import (
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


def _evt(*, event_id: str) -> EventLogRecord:
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
    """A small lineage / propagation / contradiction
    seed.

    Edge graph:

        e1 --cited_as_evidence--> e2
        e2 --propagated_to-------> e3
        e1 --reviewed_under------> e3
        e2 --contradicted_by-----> e1
        e3 --derived_from--------> e2  (lineage backward)
    """
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
        _edge(
            edge_id="te:5",
            source_event_id="evt:e2",
            target_event_id="evt:e3",
            edge_type_label="derived_from",
            edge_category_label="lineage",
        ),
    ]
    return edges


# ---------------------------------------------------------------------------
# Edge-type label sets
# ---------------------------------------------------------------------------


def test_lineage_edge_type_labels_are_subset_of_trace_edge_type_labels() -> None:
    from world.trace_edges import TRACE_EDGE_TYPE_LABELS

    assert (
        LINEAGE_EDGE_TYPE_LABELS
        <= TRACE_EDGE_TYPE_LABELS
    )


def test_propagation_edge_type_labels_subset() -> None:
    from world.trace_edges import TRACE_EDGE_TYPE_LABELS

    assert (
        PROPAGATION_EDGE_TYPE_LABELS
        <= TRACE_EDGE_TYPE_LABELS
    )


def test_contradiction_edge_type_labels_subset() -> None:
    from world.trace_edges import TRACE_EDGE_TYPE_LABELS

    assert (
        CONTRADICTION_EDGE_TYPE_LABELS
        <= TRACE_EDGE_TYPE_LABELS
    )


# ---------------------------------------------------------------------------
# list_edges_for_event
# ---------------------------------------------------------------------------


def test_list_edges_for_event_finds_source_and_target() -> None:
    edges = _seed()
    out = list_edges_for_event("evt:e1", edges)
    ids = {e.edge_id for e in out}
    # te:1 (source), te:3 (source), te:4 (target)
    assert ids == {"te:1", "te:3", "te:4"}


def test_list_edges_for_event_deterministic() -> None:
    edges = _seed()
    a = list_edges_for_event("evt:e1", edges)
    b = list_edges_for_event(
        "evt:e1", list(reversed(edges))
    )
    assert a == b


def test_list_edges_for_event_unknown_id_returns_empty() -> None:
    edges = _seed()
    assert list_edges_for_event("evt:phantom", edges) == ()


def test_list_edges_for_event_rejects_empty_id() -> None:
    edges = _seed()
    with pytest.raises(ValueError):
        list_edges_for_event("", edges)


# ---------------------------------------------------------------------------
# list_evidence_for_judgment_event
# ---------------------------------------------------------------------------


def test_list_evidence_for_judgment_event_correct() -> None:
    edges = _seed()
    # e2 is the target of te:1 (evidence_ref_ids=("ev:x",))
    out = list_evidence_for_judgment_event(
        "evt:e2", edges
    )
    assert out == ("ev:x",)


def test_list_evidence_for_judgment_event_deterministic() -> None:
    edges = _seed()
    a = list_evidence_for_judgment_event(
        "evt:e2", edges
    )
    b = list_evidence_for_judgment_event(
        "evt:e2", list(reversed(edges))
    )
    assert a == b


# ---------------------------------------------------------------------------
# list_events_citing_evidence
# ---------------------------------------------------------------------------


def test_list_events_citing_evidence_includes_evidence_ref_and_citation_ids() -> None:
    edges = _seed()
    # ev:x appears in te:1 (target=evt:e2) and te:2
    # (target=evt:e3); c:1 appears in te:1 only.
    out_evx = list_events_citing_evidence("ev:x", edges)
    assert out_evx == ("evt:e2", "evt:e3")
    out_c1 = list_events_citing_evidence("c:1", edges)
    assert out_c1 == ("evt:e2",)


def test_list_events_citing_evidence_deterministic() -> None:
    edges = _seed()
    a = list_events_citing_evidence("ev:x", edges)
    b = list_events_citing_evidence(
        "ev:x", list(reversed(edges))
    )
    assert a == b


# ---------------------------------------------------------------------------
# list_edges_by_actor
# ---------------------------------------------------------------------------


def test_list_edges_by_actor_correct() -> None:
    edges = _seed()
    out_a = list_edges_by_actor("reviewer_a", edges)
    assert {e.edge_id for e in out_a} == {"te:1", "te:2"}
    out_b = list_edges_by_actor("reviewer_b", edges)
    assert {e.edge_id for e in out_b} == {"te:3"}


def test_list_edges_by_actor_deterministic() -> None:
    edges = _seed()
    a = list_edges_by_actor("reviewer_a", edges)
    b = list_edges_by_actor(
        "reviewer_a", list(reversed(edges))
    )
    assert a == b


# ---------------------------------------------------------------------------
# list_propagation_edges / list_contradiction_pairs
# ---------------------------------------------------------------------------


def test_list_propagation_edges_correct() -> None:
    edges = _seed()
    out = list_propagation_edges(edges)
    # te:2 is propagated_to AND propagation category.
    assert {e.edge_id for e in out} == {"te:2"}


def test_list_propagation_edges_includes_category_only_match() -> None:
    """An edge with edge_category_label='propagation'
    but a non-propagated_to edge_type_label must
    still be included."""
    edges = [
        _edge(
            edge_id="te:cat-only",
            source_event_id="evt:a",
            target_event_id="evt:b",
            edge_type_label="related_to",
            edge_category_label="propagation",
        )
    ]
    out = list_propagation_edges(edges)
    assert {e.edge_id for e in out} == {"te:cat-only"}


def test_list_contradiction_pairs_correct() -> None:
    edges = _seed()
    pairs = list_contradiction_pairs(edges)
    assert pairs == (("evt:e2", "evt:e1"),)


def test_list_contradiction_pairs_deterministic() -> None:
    edges = _seed()
    a = list_contradiction_pairs(edges)
    b = list_contradiction_pairs(list(reversed(edges)))
    assert a == b


# ---------------------------------------------------------------------------
# trace_lineage_to_origin
# ---------------------------------------------------------------------------


def test_trace_lineage_to_origin_walks_lineage_edges() -> None:
    """Lineage edges in seed:
        cited_as_evidence: e1 → e2
        reviewed_under:    e1 → e3
        derived_from:      e2 → e3
    Walking ancestors of e3 with these edges gives:
        depth 1: e1 (via reviewed_under), e2 (via derived_from)
        depth 2: e1 (via cited_as_evidence from e2; already visited)
    Result: {e1, e2}.
    """
    edges = _seed()
    ancestors = trace_lineage_to_origin(
        "evt:e3", edges, max_depth=16
    )
    assert ancestors == ("evt:e1", "evt:e2")


def test_trace_lineage_to_origin_respects_max_depth() -> None:
    edges = _seed()
    # max_depth=0 → no walk performed; empty result.
    assert (
        trace_lineage_to_origin(
            "evt:e3", edges, max_depth=0
        )
        == ()
    )
    # max_depth=1 → only direct ancestors of e3:
    # {e1, e2}.
    assert (
        trace_lineage_to_origin(
            "evt:e3", edges, max_depth=1
        )
        == ("evt:e1", "evt:e2")
    )


def test_trace_lineage_to_origin_handles_cycle_safely() -> None:
    """A → B (cited_as_evidence), B → A (cited_as_evidence)
    forms a 2-cycle. The walk must terminate."""
    edges = [
        _edge(
            edge_id="te:1",
            source_event_id="evt:a",
            target_event_id="evt:b",
            edge_type_label="cited_as_evidence",
            edge_category_label="evidence",
        ),
        _edge(
            edge_id="te:2",
            source_event_id="evt:b",
            target_event_id="evt:a",
            edge_type_label="cited_as_evidence",
            edge_category_label="evidence",
        ),
    ]
    out = trace_lineage_to_origin(
        "evt:b", edges, max_depth=1024
    )
    assert out == ("evt:a",)


def test_trace_lineage_to_origin_deterministic() -> None:
    edges = _seed()
    a = trace_lineage_to_origin(
        "evt:e3", edges, max_depth=16
    )
    b = trace_lineage_to_origin(
        "evt:e3", list(reversed(edges)), max_depth=16
    )
    assert a == b


def test_trace_lineage_to_origin_rejects_negative_max_depth() -> None:
    with pytest.raises(ValueError):
        trace_lineage_to_origin(
            "evt:e3", [], max_depth=-1
        )


def test_trace_lineage_to_origin_rejects_non_int_max_depth() -> None:
    with pytest.raises(ValueError):
        trace_lineage_to_origin(
            "evt:e3", [], max_depth=1.5  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError):
        trace_lineage_to_origin(
            "evt:e3", [], max_depth=True  # type: ignore[arg-type]
        )


def test_trace_lineage_to_origin_ignores_non_lineage_edges() -> None:
    """An edge with edge_type_label='propagated_to' is
    NOT a lineage edge, so it is ignored by the
    ancestor walk."""
    edges = [
        _edge(
            edge_id="te:1",
            source_event_id="evt:a",
            target_event_id="evt:b",
            edge_type_label="propagated_to",
            edge_category_label="propagation",
        )
    ]
    out = trace_lineage_to_origin(
        "evt:b", edges, max_depth=16
    )
    assert out == ()


# ---------------------------------------------------------------------------
# summarize_audit_questions
# ---------------------------------------------------------------------------


def test_summarize_audit_questions_returns_dataclass() -> None:
    edges = _seed()
    events = [
        _evt(event_id="evt:e1"),
        _evt(event_id="evt:e2"),
        _evt(event_id="evt:e3"),
    ]
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    s = summarize_audit_questions(
        p,
        edges,
        event_id="evt:e3",
        actor_id="reviewer_a",
    )
    assert isinstance(s, AuditTraceSummary)
    assert s.event_id == "evt:e3"
    assert s.actor_id == "reviewer_a"
    assert s.projection_digest == p.projection_digest
    assert s.lineage_ancestors == ("evt:e1", "evt:e2")
    assert s.contradiction_pairs == (
        ("evt:e2", "evt:e1"),
    )


def test_summarize_audit_questions_deterministic() -> None:
    edges = _seed()
    events = [
        _evt(event_id="evt:e1"),
        _evt(event_id="evt:e2"),
        _evt(event_id="evt:e3"),
    ]
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    a = summarize_audit_questions(
        p, edges, event_id="evt:e3"
    )
    b = summarize_audit_questions(
        p, list(reversed(edges)), event_id="evt:e3"
    )
    assert a == b


def test_summarize_audit_questions_rejects_non_projection() -> None:
    edges = _seed()
    with pytest.raises(TypeError):
        summarize_audit_questions(
            "not a projection",  # type: ignore[arg-type]
            edges,
            event_id="evt:e3",
        )


def test_summarize_audit_questions_summary_dataclass_is_frozen() -> None:
    edges = _seed()
    events = [
        _evt(event_id="evt:e1"),
        _evt(event_id="evt:e2"),
        _evt(event_id="evt:e3"),
    ]
    p = build_citation_graph_projection(
        events, edges, run_id="run:test:01"
    )
    s = summarize_audit_questions(
        p, edges, event_id="evt:e3"
    )
    with pytest.raises(Exception):
        s.event_id = "different"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Counterfactual boundary
# ---------------------------------------------------------------------------


def test_counterfactual_replay_message_constant_present() -> None:
    assert isinstance(
        COUNTERFACTUAL_REPLAY_NOT_IMPLEMENTED_MESSAGE,
        str,
    )
    assert (
        "counterfactual"
        in COUNTERFACTUAL_REPLAY_NOT_IMPLEMENTED_MESSAGE.lower()
    )
    assert (
        "v1.30"
        in COUNTERFACTUAL_REPLAY_NOT_IMPLEMENTED_MESSAGE.lower()
    )


def test_module_no_counterfactual_replay_callable() -> None:
    from world import audit_trace_queries

    src = inspect.getsource(audit_trace_queries)
    for tok in (
        "def replay(",
        "def counterfactual_replay",
        "def what_if_",
        "def simulate_without_",
    ):
        assert tok not in src


# ---------------------------------------------------------------------------
# Forbidden-scope tests
# ---------------------------------------------------------------------------


def test_module_no_graph_database_or_query_engine_imports() -> None:
    from world import audit_trace_queries

    src = inspect.getsource(audit_trace_queries)
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


def test_module_no_real_data_or_investment_callables() -> None:
    from world import audit_trace_queries

    src = inspect.getsource(audit_trace_queries).lower()
    for tok in (
        "buy_signal",
        "sell_signal",
        "target_price",
        "alpha_claim",
        "backtest_claim",
        "investment_advice",
        "ownership_percentage",
        "voting_power",
    ):
        assert tok not in src


def test_module_does_not_register_a_kernel_field() -> None:
    from world.kernel import WorldKernel

    fnames = {
        f.name
        for f in WorldKernel.__dataclass_fields__.values()
    }
    forbidden = {
        "audit_trace_queries",
        "audit_query",
        "trace_audit",
    }
    assert (fnames & forbidden) == set()


def test_module_exports_match_design_pin() -> None:
    from world import audit_trace_queries

    expected = {
        "AuditTraceSummary",
        "CONTRADICTION_EDGE_TYPE_LABELS",
        "COUNTERFACTUAL_REPLAY_NOT_IMPLEMENTED_MESSAGE",
        "LINEAGE_EDGE_TYPE_LABELS",
        "PROPAGATION_EDGE_TYPE_LABELS",
        "list_contradiction_pairs",
        "list_edges_by_actor",
        "list_edges_for_event",
        "list_events_citing_evidence",
        "list_evidence_for_judgment_event",
        "list_propagation_edges",
        "summarize_audit_questions",
        "trace_lineage_to_origin",
    }
    assert (
        set(audit_trace_queries.__all__) == expected
    )
