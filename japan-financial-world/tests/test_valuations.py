from datetime import date

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.prices import PriceBook
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.valuations import (
    DuplicateValuationError,
    UnknownValuationError,
    ValuationBook,
    ValuationComparator,
    ValuationGap,
    ValuationRecord,
)


def _valuation(
    valuation_id: str = "valuation:001",
    *,
    subject_id: str = "firm:reference_manufacturer_a",
    valuer_id: str = "valuer:reference_dcf_model",
    valuation_type: str = "equity",
    purpose: str = "investment_research",
    method: str = "dcf",
    as_of_date: str = "2026-01-01",
    estimated_value: float | None = 100.0,
    currency: str = "USD",
    numeraire: str = "USD",
    confidence: float = 0.8,
    assumptions: dict | None = None,
    inputs: dict | None = None,
    related_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> ValuationRecord:
    return ValuationRecord(
        valuation_id=valuation_id,
        subject_id=subject_id,
        valuer_id=valuer_id,
        valuation_type=valuation_type,
        purpose=purpose,
        method=method,
        as_of_date=as_of_date,
        estimated_value=estimated_value,
        currency=currency,
        numeraire=numeraire,
        confidence=confidence,
        assumptions=assumptions or {},
        inputs=inputs or {},
        related_ids=related_ids,
        metadata=metadata or {},
    )


def _book(with_ledger: bool = False) -> ValuationBook:
    if with_ledger:
        return ValuationBook(
            ledger=Ledger(),
            clock=Clock(current_date=date(2026, 1, 1)),
        )
    return ValuationBook()


# ---------------------------------------------------------------------------
# ValuationRecord dataclass
# ---------------------------------------------------------------------------


def test_valuation_record_carries_all_fields():
    v = _valuation()
    assert v.valuation_id == "valuation:001"
    assert v.subject_id == "firm:reference_manufacturer_a"
    assert v.valuer_id == "valuer:reference_dcf_model"
    assert v.valuation_type == "equity"
    assert v.purpose == "investment_research"
    assert v.method == "dcf"
    assert v.as_of_date == "2026-01-01"
    assert v.estimated_value == 100.0
    assert v.currency == "USD"
    assert v.numeraire == "USD"
    assert v.confidence == 0.8


def test_valuation_record_rejects_missing_required_fields():
    with pytest.raises(ValueError):
        _valuation(valuation_id="")
    with pytest.raises(ValueError):
        _valuation(subject_id="")
    with pytest.raises(ValueError):
        _valuation(valuer_id="")
    with pytest.raises(ValueError):
        _valuation(valuation_type="")
    with pytest.raises(ValueError):
        _valuation(purpose="")
    with pytest.raises(ValueError):
        _valuation(method="")


def test_valuation_record_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        _valuation(confidence=1.5)
    with pytest.raises(ValueError):
        _valuation(confidence=-0.1)


def test_valuation_record_allows_none_estimated_value():
    """Qualitative or failed valuations may report no number."""
    v = _valuation(estimated_value=None)
    assert v.estimated_value is None


def test_valuation_record_is_immutable():
    v = _valuation()
    with pytest.raises(Exception):
        v.estimated_value = 200.0  # type: ignore[misc]


def test_valuation_record_to_dict_is_serializable():
    v = _valuation(
        assumptions={"discount_rate": 0.08},
        inputs={"fcf": [100, 110, 121]},
        related_ids=("firm:reference_manufacturer_a",),
    )
    payload = v.to_dict()
    assert payload["valuation_id"] == "valuation:001"
    assert payload["assumptions"] == {"discount_rate": 0.08}
    assert payload["inputs"] == {"fcf": [100, 110, 121]}
    assert payload["related_ids"] == ["firm:reference_manufacturer_a"]


# ---------------------------------------------------------------------------
# ValuationBook CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_valuation():
    book = _book()
    v = _valuation()
    book.add_valuation(v)
    assert book.get_valuation("valuation:001") is v


def test_get_valuation_raises_for_unknown_id():
    book = _book()
    with pytest.raises(UnknownValuationError):
        book.get_valuation("valuation:does_not_exist")


def test_duplicate_valuation_id_rejected():
    book = _book()
    book.add_valuation(_valuation())
    with pytest.raises(DuplicateValuationError):
        book.add_valuation(_valuation())


def test_list_by_subject_filters_correctly():
    book = _book()
    book.add_valuation(
        _valuation(valuation_id="valuation:a", subject_id="firm:x")
    )
    book.add_valuation(
        _valuation(valuation_id="valuation:b", subject_id="firm:x")
    )
    book.add_valuation(
        _valuation(valuation_id="valuation:c", subject_id="firm:y")
    )

    on_x = book.list_by_subject("firm:x")
    on_y = book.list_by_subject("firm:y")

    assert {v.valuation_id for v in on_x} == {"valuation:a", "valuation:b"}
    assert {v.valuation_id for v in on_y} == {"valuation:c"}


def test_list_by_valuer_filters_correctly():
    book = _book()
    book.add_valuation(
        _valuation(valuation_id="valuation:a", valuer_id="valuer:moodys_dcf")
    )
    book.add_valuation(
        _valuation(valuation_id="valuation:b", valuer_id="valuer:moodys_dcf")
    )
    book.add_valuation(
        _valuation(valuation_id="valuation:c", valuer_id="valuer:internal_audit")
    )

    moodys = book.list_by_valuer("valuer:moodys_dcf")
    audit = book.list_by_valuer("valuer:internal_audit")

    assert {v.valuation_id for v in moodys} == {"valuation:a", "valuation:b"}
    assert {v.valuation_id for v in audit} == {"valuation:c"}


def test_list_by_type_filters_correctly():
    book = _book()
    book.add_valuation(
        _valuation(valuation_id="valuation:a", valuation_type="equity")
    )
    book.add_valuation(
        _valuation(valuation_id="valuation:b", valuation_type="equity")
    )
    book.add_valuation(
        _valuation(valuation_id="valuation:c", valuation_type="real_estate")
    )

    equity = book.list_by_type("equity")
    re = book.list_by_type("real_estate")

    assert {v.valuation_id for v in equity} == {"valuation:a", "valuation:b"}
    assert {v.valuation_id for v in re} == {"valuation:c"}


def test_list_by_purpose_filters_correctly():
    book = _book()
    book.add_valuation(
        _valuation(valuation_id="valuation:a", purpose="underwriting")
    )
    book.add_valuation(
        _valuation(valuation_id="valuation:b", purpose="financial_reporting")
    )

    underwriting = book.list_by_purpose("underwriting")
    reporting = book.list_by_purpose("financial_reporting")

    assert {v.valuation_id for v in underwriting} == {"valuation:a"}
    assert {v.valuation_id for v in reporting} == {"valuation:b"}


def test_list_by_method_filters_correctly():
    book = _book()
    book.add_valuation(_valuation(valuation_id="valuation:a", method="dcf"))
    book.add_valuation(_valuation(valuation_id="valuation:b", method="comparables"))
    book.add_valuation(_valuation(valuation_id="valuation:c", method="dcf"))

    dcf = book.list_by_method("dcf")
    comps = book.list_by_method("comparables")

    assert {v.valuation_id for v in dcf} == {"valuation:a", "valuation:c"}
    assert {v.valuation_id for v in comps} == {"valuation:b"}


def test_get_latest_by_subject_picks_highest_as_of_date():
    book = _book()
    book.add_valuation(
        _valuation(
            valuation_id="valuation:earlier",
            subject_id="firm:x",
            as_of_date="2026-01-01",
        )
    )
    book.add_valuation(
        _valuation(
            valuation_id="valuation:later",
            subject_id="firm:x",
            as_of_date="2026-06-01",
        )
    )
    book.add_valuation(
        _valuation(
            valuation_id="valuation:other_firm",
            subject_id="firm:y",
            as_of_date="2027-01-01",
        )
    )

    latest = book.get_latest_by_subject("firm:x")
    assert latest is not None
    assert latest.valuation_id == "valuation:later"


def test_get_latest_by_subject_returns_none_for_unknown_subject():
    book = _book()
    book.add_valuation(_valuation(subject_id="firm:x"))
    assert book.get_latest_by_subject("firm:y") is None


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_lists_all_valuations_sorted():
    book = _book()
    book.add_valuation(_valuation(valuation_id="valuation:b"))
    book.add_valuation(_valuation(valuation_id="valuation:a"))

    snap = book.snapshot()
    assert snap["count"] == 2
    assert [item["valuation_id"] for item in snap["valuations"]] == [
        "valuation:a",
        "valuation:b",
    ]


def test_snapshot_returns_empty_structure_for_empty_book():
    snap = ValuationBook().snapshot()
    assert snap == {"count": 0, "valuations": []}


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_add_valuation_records_to_ledger():
    book = _book(with_ledger=True)
    book.add_valuation(
        _valuation(
            estimated_value=12_500_000_000.0,
            confidence=0.65,
            currency="JPY",
        )
    )

    records = book.ledger.filter(event_type="valuation_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "valuation:001"
    assert record.target == "firm:reference_manufacturer_a"
    assert record.agent_id == "valuer:reference_dcf_model"
    assert record.confidence == 0.65
    assert record.payload["estimated_value"] == 12_500_000_000.0
    assert record.payload["currency"] == "JPY"
    assert record.simulation_date == "2026-01-01"
    assert record.space_id == "valuations"


def test_add_valuation_does_not_record_when_no_ledger():
    book = ValuationBook()
    book.add_valuation(_valuation())
    assert book.get_valuation("valuation:001") is not None


# ---------------------------------------------------------------------------
# ValuationComparator — successful gap
# ---------------------------------------------------------------------------


def test_compare_to_latest_price_computes_absolute_and_relative_gap():
    book = _book()
    prices = PriceBook()
    book.add_valuation(
        _valuation(
            subject_id="firm:reference_a",
            estimated_value=110.0,
            currency="USD",
        )
    )
    prices.set_price("firm:reference_a", 100.0, "2026-01-02", "exchange")

    comparator = ValuationComparator(valuations=book, prices=prices)
    gap = comparator.compare_to_latest_price("valuation:001")

    assert gap.estimated_value == 110.0
    assert gap.observed_price == 100.0
    assert gap.absolute_gap == 10.0
    assert abs(gap.relative_gap - 0.1) < 1e-9
    assert gap.currency == "USD"
    assert gap.metadata == {}


def test_compare_subject_latest_uses_latest_valuation():
    book = _book()
    prices = PriceBook()
    book.add_valuation(
        _valuation(
            valuation_id="valuation:earlier",
            subject_id="firm:x",
            as_of_date="2026-01-01",
            estimated_value=90.0,
        )
    )
    book.add_valuation(
        _valuation(
            valuation_id="valuation:later",
            subject_id="firm:x",
            as_of_date="2026-06-01",
            estimated_value=110.0,
        )
    )
    prices.set_price("firm:x", 100.0, "2026-06-02", "exchange")

    comparator = ValuationComparator(valuations=book, prices=prices)
    gap = comparator.compare_subject_latest("firm:x")

    assert gap is not None
    assert gap.valuation_id == "valuation:later"
    assert gap.absolute_gap == 10.0


def test_compare_subject_latest_returns_none_when_no_valuation_exists():
    book = _book()
    prices = PriceBook()
    comparator = ValuationComparator(valuations=book, prices=prices)
    assert comparator.compare_subject_latest("firm:nobody") is None


# ---------------------------------------------------------------------------
# ValuationComparator — failure paths
# ---------------------------------------------------------------------------


def test_compare_handles_missing_price_without_crashing():
    book = _book()
    prices = PriceBook()  # no prices recorded
    book.add_valuation(_valuation(subject_id="firm:x", estimated_value=100.0))

    comparator = ValuationComparator(valuations=book, prices=prices)
    gap = comparator.compare_to_latest_price("valuation:001")

    assert gap.observed_price is None
    assert gap.absolute_gap is None
    assert gap.relative_gap is None
    assert gap.estimated_value == 100.0
    assert gap.metadata["reason"] == "missing_price"


def test_compare_handles_none_estimated_value_without_crashing():
    book = _book()
    prices = PriceBook()
    book.add_valuation(_valuation(subject_id="firm:x", estimated_value=None))
    prices.set_price("firm:x", 100.0, "2026-01-01", "exchange")

    comparator = ValuationComparator(valuations=book, prices=prices)
    gap = comparator.compare_to_latest_price("valuation:001")

    assert gap.estimated_value is None
    assert gap.observed_price == 100.0
    assert gap.absolute_gap is None
    assert gap.relative_gap is None
    assert gap.metadata["reason"] == "estimated_value_unavailable"


def test_compare_currency_mismatch_does_not_convert():
    book = _book()
    prices = PriceBook()
    book.add_valuation(
        _valuation(
            subject_id="firm:x",
            estimated_value=110.0,
            currency="USD",
        )
    )
    # Price record explicitly declares a different currency.
    prices.set_price(
        "firm:x", 16_500.0, "2026-01-02", "exchange", metadata={"currency": "JPY"}
    )

    comparator = ValuationComparator(valuations=book, prices=prices)
    gap = comparator.compare_to_latest_price("valuation:001")

    assert gap.estimated_value == 110.0
    assert gap.observed_price == 16_500.0  # raw, not converted
    assert gap.absolute_gap is None
    assert gap.relative_gap is None
    assert gap.metadata["reason"] == "currency_mismatch"
    assert gap.metadata["valuation_currency"] == "USD"
    assert gap.metadata["price_currency"] == "JPY"


def test_compare_observed_price_zero_returns_absolute_gap_only():
    book = _book()
    prices = PriceBook()
    book.add_valuation(_valuation(subject_id="firm:x", estimated_value=10.0))
    prices.set_price("firm:x", 0.0, "2026-01-02", "exchange")

    comparator = ValuationComparator(valuations=book, prices=prices)
    gap = comparator.compare_to_latest_price("valuation:001")

    assert gap.absolute_gap == 10.0
    assert gap.relative_gap is None
    assert gap.metadata["reason"] == "observed_price_zero"


# ---------------------------------------------------------------------------
# Comparison ledger record
# ---------------------------------------------------------------------------


def test_compare_records_valuation_compared_to_ledger():
    ledger = Ledger()
    book = ValuationBook(ledger=ledger, clock=Clock(current_date=date(2026, 1, 1)))
    prices = PriceBook()
    book.add_valuation(_valuation(subject_id="firm:x", estimated_value=110.0))
    prices.set_price("firm:x", 100.0, "2026-01-02", "exchange")

    comparator = ValuationComparator(
        valuations=book,
        prices=prices,
        ledger=ledger,
        clock=Clock(current_date=date(2026, 1, 2)),
    )
    comparator.compare_to_latest_price("valuation:001")

    compared = ledger.filter(event_type="valuation_compared")
    assert len(compared) == 1
    record = compared[0]
    assert record.object_id == "valuation:001"
    assert record.target == "firm:x"
    assert record.payload["absolute_gap"] == 10.0
    assert record.correlation_id == "valuation:001"
    # Causal chain: the comparison record references the valuation_added record.
    valuation_added = ledger.filter(event_type="valuation_added")[0]
    assert valuation_added.record_id in record.parent_record_ids


# ---------------------------------------------------------------------------
# Subject id flexibility
# ---------------------------------------------------------------------------


def test_subject_id_can_be_non_firm():
    """v1.1 explicitly supports non-firm subjects."""
    book = _book()
    book.add_valuation(
        _valuation(
            valuation_id="valuation:fx_view",
            subject_id="fx:usd_jpy",
            valuation_type="fx_view",
            method="reference_macro_model",
        )
    )
    book.add_valuation(
        _valuation(
            valuation_id="valuation:portfolio_nav",
            subject_id="portfolio:etf_global",
            valuation_type="fund_nav",
            method="lookthrough_aggregation",
        )
    )
    book.add_valuation(
        _valuation(
            valuation_id="valuation:property_appraisal",
            subject_id="asset:reference_office_a",
            valuation_type="real_estate",
            method="cap_rate",
        )
    )

    assert book.get_valuation("valuation:fx_view").subject_id == "fx:usd_jpy"
    assert (
        book.get_valuation("valuation:portfolio_nav").subject_id
        == "portfolio:etf_global"
    )
    assert (
        book.get_valuation("valuation:property_appraisal").subject_id
        == "asset:reference_office_a"
    )


# ---------------------------------------------------------------------------
# Multiple conflicting claims about the same subject
# ---------------------------------------------------------------------------


def test_multiple_valuations_for_same_subject_coexist():
    """
    v1.1 explicitly supports conflicting claims about the same subject.
    A bank, an investor, an appraiser, and a covenant-test calculator
    can all produce different numbers for the same building, and the
    book stores all of them.
    """
    book = _book()
    book.add_valuation(
        _valuation(
            valuation_id="valuation:bank_underwriting",
            subject_id="asset:office_a",
            valuer_id="valuer:bank_a_credit",
            purpose="underwriting",
            method="cap_rate",
            estimated_value=950.0,
        )
    )
    book.add_valuation(
        _valuation(
            valuation_id="valuation:investor_view",
            subject_id="asset:office_a",
            valuer_id="valuer:investor_b_model",
            purpose="investment_research",
            method="dcf",
            estimated_value=1_100.0,
        )
    )
    book.add_valuation(
        _valuation(
            valuation_id="valuation:appraisal",
            subject_id="asset:office_a",
            valuer_id="valuer:appraiser_c",
            purpose="financial_reporting",
            method="comparable_sales",
            estimated_value=1_000.0,
        )
    )

    on_subject = book.list_by_subject("asset:office_a")
    estimates = {v.valuation_id: v.estimated_value for v in on_subject}
    assert estimates == {
        "valuation:bank_underwriting": 950.0,
        "valuation:investor_view": 1_100.0,
        "valuation:appraisal": 1_000.0,
    }


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def test_valuation_layer_does_not_mutate_other_books():
    kernel = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )

    kernel.ownership.add_position("agent:alice", "asset:x", 100)
    kernel.prices.set_price("asset:x", 50.0, "2026-01-01", "exchange")

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    signals_before = kernel.signals.snapshot()

    kernel.valuations.add_valuation(
        _valuation(subject_id="asset:x", estimated_value=60.0)
    )
    kernel.valuation_comparator.compare_to_latest_price("valuation:001")
    kernel.valuation_comparator.compare_subject_latest("asset:x")
    kernel.valuations.snapshot()

    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.signals.snapshot() == signals_before


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_valuations_with_default_wiring():
    kernel = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )

    kernel.valuations.add_valuation(_valuation())

    assert kernel.valuations.ledger is kernel.ledger
    assert kernel.valuations.clock is kernel.clock
    assert kernel.valuation_comparator is not None
    assert kernel.valuation_comparator.valuations is kernel.valuations
    assert kernel.valuation_comparator.prices is kernel.prices
    assert len(kernel.ledger.filter(event_type="valuation_added")) == 1


# ---------------------------------------------------------------------------
# ValuationGap dataclass
# ---------------------------------------------------------------------------


def test_valuation_gap_to_dict_is_serializable():
    gap = ValuationGap(
        subject_id="asset:x",
        valuation_id="valuation:001",
        as_of_date="2026-01-01",
        estimated_value=110.0,
        observed_price=100.0,
        absolute_gap=10.0,
        relative_gap=0.1,
        currency="USD",
    )
    payload = gap.to_dict()
    assert payload["absolute_gap"] == 10.0
    assert payload["relative_gap"] == 0.1


def test_valuation_gap_is_immutable():
    gap = ValuationGap(
        subject_id="asset:x",
        valuation_id="valuation:001",
        as_of_date="2026-01-01",
        estimated_value=None,
        observed_price=None,
        absolute_gap=None,
        relative_gap=None,
    )
    with pytest.raises(Exception):
        gap.absolute_gap = 1.0  # type: ignore[misc]
