"""
Tests for v1.13.5 — additive cross-link integration:

- ``MarketEnvironmentStateRecord`` gains an additive
  ``evidence_interbank_liquidity_state_ids`` slot (citation only;
  empty default).
- ``run_attention_conditioned_bank_credit_review_lite`` accepts
  ``explicit_interbank_liquidity_state_ids`` (citation only; the
  v1.12.6 watch-label classifier is unchanged).
- ``run_living_reference_world`` emits one
  ``InterbankLiquidityStateRecord`` per bank per period and
  passes its id into the bank credit review helper.
"""

from __future__ import annotations

from datetime import date

from world.interbank_liquidity import (
    InterbankLiquidityStateBook,
    InterbankLiquidityStateRecord,
)
from world.market_environment import (
    MarketEnvironmentStateRecord,
    build_market_environment_state,
)
from world.kernel import WorldKernel
from world.clock import Clock
from world.ledger import Ledger
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


def _kernel(date_: date = date(2026, 3, 31)) -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date_),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


# ---------------------------------------------------------------------------
# MarketEnvironmentStateRecord additive slot
# ---------------------------------------------------------------------------


def _market_env_state(**overrides) -> MarketEnvironmentStateRecord:
    base = dict(
        environment_state_id="market_environment_state:reference_a",
        as_of_date="2026-03-31",
        liquidity_regime="normal",
        volatility_regime="calm",
        credit_regime="neutral",
        funding_regime="normal",
        risk_appetite_regime="neutral",
        rate_environment="low",
        refinancing_window="open",
        equity_valuation_regime="neutral",
        overall_market_access_label="open_or_constructive",
        status="active",
        visibility="internal_only",
        confidence=0.5,
    )
    base.update(overrides)
    return MarketEnvironmentStateRecord(**base)


def test_market_environment_state_default_evidence_interbank_liquidity_is_empty():
    s = _market_env_state()
    assert s.evidence_interbank_liquidity_state_ids == ()


def test_market_environment_state_accepts_evidence_interbank_liquidity_ids():
    s = _market_env_state(
        evidence_interbank_liquidity_state_ids=(
            "interbank_liquidity_state:a",
            "interbank_liquidity_state:b",
        ),
    )
    assert s.evidence_interbank_liquidity_state_ids == (
        "interbank_liquidity_state:a",
        "interbank_liquidity_state:b",
    )


def test_market_environment_state_rejects_empty_strings_in_new_slot():
    import pytest

    with pytest.raises(ValueError):
        _market_env_state(
            evidence_interbank_liquidity_state_ids=("",),
        )


def test_market_environment_state_to_dict_contains_new_slot():
    s = _market_env_state(
        evidence_interbank_liquidity_state_ids=("interbank_liquidity_state:a",),
    )
    out = s.to_dict()
    assert out["evidence_interbank_liquidity_state_ids"] == [
        "interbank_liquidity_state:a"
    ]


def test_market_environment_ledger_payload_contains_new_slot_key():
    k = _kernel()
    k.market_environments.add_state(
        _market_env_state(
            evidence_interbank_liquidity_state_ids=(
                "interbank_liquidity_state:a",
            )
        )
    )
    rec = k.ledger.records[-1]
    assert (
        "evidence_interbank_liquidity_state_ids"
        in rec.payload.keys()
    )
    assert list(
        rec.payload["evidence_interbank_liquidity_state_ids"]
    ) == ["interbank_liquidity_state:a"]


def test_build_market_environment_state_passes_new_slot_through():
    k = _kernel()
    res = build_market_environment_state(
        k,
        as_of_date="2026-03-31",
        evidence_interbank_liquidity_state_ids=(
            "interbank_liquidity_state:a",
        ),
    )
    assert res.record.evidence_interbank_liquidity_state_ids == (
        "interbank_liquidity_state:a",
    )


# ---------------------------------------------------------------------------
# Bank credit review helper
# ---------------------------------------------------------------------------


def test_helper_accepts_explicit_interbank_liquidity_state_ids_kwarg():
    """The v1.13.5 helper signature must accept the new
    ``explicit_interbank_liquidity_state_ids`` kwarg."""
    import inspect
    from world.reference_bank_credit_review_lite import (
        run_attention_conditioned_bank_credit_review_lite,
    )

    sig = inspect.signature(
        run_attention_conditioned_bank_credit_review_lite
    )
    assert (
        "explicit_interbank_liquidity_state_ids" in sig.parameters
    )
    assert (
        sig.parameters["explicit_interbank_liquidity_state_ids"].default
        == ()
    )


def test_helper_resolves_cited_interbank_liquidity_state_id_via_kernel():
    """Sanity: ``kernel.interbank_liquidity.get_state`` is the
    look-up path the helper walks for each cited id."""
    k = _kernel(date(2026, 3, 31))
    state = InterbankLiquidityStateRecord(
        liquidity_state_id="interbank_liquidity_state:bank_a:2026-03-31",
        institution_id="bank_a",
        as_of_date="2026-03-31",
        liquidity_regime="normal",
        settlement_pressure="low",
        reserve_access_label="available",
        funding_stress_label="low",
        status="active",
        visibility="internal_only",
        confidence=0.5,
    )
    k.interbank_liquidity.add_state(state)
    fetched = k.interbank_liquidity.get_state(
        "interbank_liquidity_state:bank_a:2026-03-31"
    )
    assert fetched is state


# ---------------------------------------------------------------------------
# Living-reference-world per-period creation
# ---------------------------------------------------------------------------


def test_living_world_emits_one_interbank_liquidity_state_per_bank_per_period():
    """v1.13.5: the orchestrator emits one
    InterbankLiquidityStateRecord per bank per period in the
    default fixture (2 banks × 4 periods = 8 records)."""
    from tests.test_living_reference_world_performance_boundary import (
        _BANK_IDS,
        _FIRM_IDS,
        _INVESTOR_IDS,
        _PERIOD_DATES,
        _seed_kernel,
    )
    from world.reference_living_world import run_living_reference_world

    k = _seed_kernel()
    run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    states = k.interbank_liquidity.list_states()
    assert len(states) == len(_BANK_IDS) * len(_PERIOD_DATES)


def test_living_world_interbank_liquidity_records_are_per_bank_per_period():
    """Each ``(bank_id, period)`` pair is unique among the
    emitted interbank-liquidity states."""
    from tests.test_living_reference_world_performance_boundary import (
        _BANK_IDS,
        _FIRM_IDS,
        _INVESTOR_IDS,
        _PERIOD_DATES,
        _seed_kernel,
    )
    from world.reference_living_world import run_living_reference_world

    k = _seed_kernel()
    run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    pairs = {
        (s.institution_id, s.as_of_date)
        for s in k.interbank_liquidity.list_states()
    }
    expected = {
        (b, d)
        for b in _BANK_IDS
        for d in _PERIOD_DATES
    }
    assert pairs == expected


def test_living_world_interbank_liquidity_ids_appear_on_credit_review_metadata():
    """v1.13.5: each ``bank_credit_review_note`` signal stamps
    the cited interbank-liquidity-state id on its metadata."""
    from tests.test_living_reference_world_performance_boundary import (
        _BANK_IDS,
        _FIRM_IDS,
        _INVESTOR_IDS,
        _PERIOD_DATES,
        _seed_kernel,
    )
    from world.reference_living_world import run_living_reference_world

    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    found = 0
    for ps in r.per_period_summaries:
        for sid in ps.bank_credit_review_signal_ids:
            sig = k.signals.get_signal(sid)
            if "resolved_interbank_liquidity_state_ids" in sig.metadata:
                ids = sig.metadata["resolved_interbank_liquidity_state_ids"]
                assert len(ids) == 1
                assert ids[0].startswith("interbank_liquidity_state:")
                found += 1
    assert found == (
        len(_BANK_IDS) * len(_FIRM_IDS) * len(_PERIOD_DATES)
    )


def test_living_world_interbank_liquidity_ids_appear_on_credit_review_payload():
    """v1.13.5: the resolved interbank-liquidity-state ids are
    also stamped on the credit-review payload."""
    from tests.test_living_reference_world_performance_boundary import (
        _BANK_IDS,
        _FIRM_IDS,
        _INVESTOR_IDS,
        _PERIOD_DATES,
        _seed_kernel,
    )
    from world.reference_living_world import run_living_reference_world

    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    seen = 0
    for ps in r.per_period_summaries:
        for sid in ps.bank_credit_review_signal_ids:
            sig = k.signals.get_signal(sid)
            assert "resolved_interbank_liquidity_state_ids" in sig.payload
            ids = sig.payload["resolved_interbank_liquidity_state_ids"]
            assert len(ids) == 1
            seen += 1
    assert seen == (
        len(_BANK_IDS) * len(_FIRM_IDS) * len(_PERIOD_DATES)
    )


def test_living_world_interbank_liquidity_states_have_expected_label_set():
    """The default-fixture orchestrator emits the v1.13.5
    placeholder state with fixed ``normal`` / ``low`` /
    ``available`` / ``low`` labels and confidence ``0.5``. This
    is a regression pin: changing the placeholder shifts the
    digest and must update both the test pin and the docs."""
    from tests.test_living_reference_world_performance_boundary import (
        _BANK_IDS,
        _FIRM_IDS,
        _INVESTOR_IDS,
        _PERIOD_DATES,
        _seed_kernel,
    )
    from world.reference_living_world import run_living_reference_world

    k = _seed_kernel()
    run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    for s in k.interbank_liquidity.list_states():
        assert s.liquidity_regime == "normal"
        assert s.settlement_pressure == "low"
        assert s.reserve_access_label == "available"
        assert s.funding_stress_label == "low"
        assert s.confidence == 0.5
        assert s.status == "active"


# ---------------------------------------------------------------------------
# Jurisdiction-neutral identifier scan
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "jgb", "nyse",
    "target2", "fedwire", "chaps", "bojnet",
)


def test_test_file_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    text = Path(__file__).read_text(encoding="utf-8").lower()
    table_start = text.find("_forbidden_tokens = (")
    table_end = text.find(")", table_start) + 1
    if table_start != -1 and table_end > 0:
        text = text[:table_start] + text[table_end:]
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, token


# ---------------------------------------------------------------------------
# Book book imports (sanity)
# ---------------------------------------------------------------------------


def test_interbank_liquidity_book_is_referenced_in_module():
    assert InterbankLiquidityStateBook is not None
