from datetime import date

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.scheduler import Scheduler
from world.signals import (
    DuplicateSignalError,
    InformationSignal,
    SignalBook,
    SignalError,
    UnknownSignalError,
)
from world.state import State


def _signal(
    *,
    signal_id: str = "signal:001",
    signal_type: str = "rating_action",
    subject_id: str = "agent:firm_x",
    source_id: str = "agent:rating_agency",
    published_date: str = "2026-01-01",
    effective_date: str = "",
    visibility: str = "public",
    credibility: float = 0.9,
    confidence: float = 0.8,
    payload: dict | None = None,
    related_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> InformationSignal:
    return InformationSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        subject_id=subject_id,
        source_id=source_id,
        published_date=published_date,
        effective_date=effective_date,
        visibility=visibility,
        credibility=credibility,
        confidence=confidence,
        payload=payload or {},
        related_ids=related_ids,
        metadata=metadata or {},
    )


def _book(with_ledger: bool = False) -> SignalBook:
    if with_ledger:
        return SignalBook(
            ledger=Ledger(),
            clock=Clock(current_date=date(2026, 1, 1)),
        )
    return SignalBook()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_signal():
    book = _book()
    signal = _signal()
    book.add_signal(signal)
    assert book.get_signal("signal:001") is signal


def test_duplicate_signal_id_rejected():
    book = _book()
    book.add_signal(_signal())
    with pytest.raises(DuplicateSignalError):
        book.add_signal(_signal())


def test_get_signal_raises_for_unknown_id():
    book = _book()
    with pytest.raises(UnknownSignalError):
        book.get_signal("signal:does_not_exist")


def test_list_by_subject_filters_correctly():
    book = _book()
    book.add_signal(_signal(signal_id="signal:1", subject_id="agent:firm_x"))
    book.add_signal(_signal(signal_id="signal:2", subject_id="agent:firm_x"))
    book.add_signal(_signal(signal_id="signal:3", subject_id="agent:firm_y"))

    firm_x_signals = book.list_by_subject("agent:firm_x")
    assert {s.signal_id for s in firm_x_signals} == {"signal:1", "signal:2"}


def test_list_by_type_filters_correctly():
    book = _book()
    book.add_signal(_signal(signal_id="signal:r1", signal_type="rating_action"))
    book.add_signal(_signal(signal_id="signal:r2", signal_type="rating_action"))
    book.add_signal(_signal(signal_id="signal:e1", signal_type="earnings_report"))

    ratings = book.list_by_type("rating_action")
    assert {s.signal_id for s in ratings} == {"signal:r1", "signal:r2"}


def test_list_by_source_filters_correctly():
    book = _book()
    book.add_signal(_signal(signal_id="signal:1", source_id="agent:reference_rating_agency_a"))
    book.add_signal(_signal(signal_id="signal:2", source_id="agent:sp"))
    book.add_signal(_signal(signal_id="signal:3", source_id="agent:reference_rating_agency_a"))

    from_moodys = book.list_by_source("agent:reference_rating_agency_a")
    assert {s.signal_id for s in from_moodys} == {"signal:1", "signal:3"}


def test_effective_date_defaults_to_published_date():
    signal = _signal(published_date="2026-01-01", effective_date="")
    assert signal.effective_date == "2026-01-01"


def test_signal_rejects_invalid_visibility():
    with pytest.raises(ValueError):
        _signal(visibility="cosmic")


def test_signal_rejects_out_of_range_credibility():
    with pytest.raises(ValueError):
        _signal(credibility=1.2)


def test_signal_rejects_out_of_range_confidence():
    with pytest.raises(ValueError):
        _signal(confidence=-0.1)


def test_signal_rejects_missing_required_fields():
    with pytest.raises(ValueError):
        _signal(signal_id="")
    with pytest.raises(ValueError):
        _signal(subject_id="")
    with pytest.raises(ValueError):
        _signal(source_id="")
    with pytest.raises(ValueError):
        _signal(published_date="")


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


def test_public_signal_visible_to_anyone():
    book = _book()
    book.add_signal(_signal(visibility="public"))
    assert len(book.list_visible_to("agent:somebody")) == 1
    assert len(book.list_visible_to("agent:nobody")) == 1


def test_leaked_and_rumor_visible_to_anyone():
    book = _book()
    book.add_signal(_signal(signal_id="signal:leaked", visibility="leaked"))
    book.add_signal(_signal(signal_id="signal:rumor", visibility="rumor"))

    visible = book.list_visible_to("agent:anyone")
    assert {s.signal_id for s in visible} == {"signal:leaked", "signal:rumor"}


def test_private_signal_visible_only_to_allowed_viewers():
    book = _book()
    book.add_signal(
        _signal(
            signal_id="signal:secret",
            visibility="private",
            metadata={"allowed_viewers": ("agent:bank_a", "agent:auditor")},
        )
    )

    assert len(book.list_visible_to("agent:bank_a")) == 1
    assert len(book.list_visible_to("agent:auditor")) == 1
    assert book.list_visible_to("agent:outsider") == ()


def test_restricted_signal_visible_only_to_allowed_viewers():
    book = _book()
    book.add_signal(
        _signal(
            signal_id="signal:internal",
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:legal",)},
        )
    )

    assert len(book.list_visible_to("agent:legal")) == 1
    assert book.list_visible_to("agent:outsider") == ()


def test_private_with_no_allowed_viewers_visible_to_no_one():
    book = _book()
    book.add_signal(_signal(visibility="private"))  # no allowed_viewers

    assert book.list_visible_to("agent:somebody") == ()


def test_delayed_signal_invisible_until_effective_date():
    book = _book()
    book.add_signal(
        _signal(
            signal_id="signal:future",
            published_date="2026-01-01",
            effective_date="2026-01-10",
            visibility="delayed",
        )
    )

    # Before effective_date -> invisible.
    assert book.list_visible_to("agent:x", as_of_date="2026-01-05") == ()
    # On effective_date -> visible.
    assert len(book.list_visible_to("agent:x", as_of_date="2026-01-10")) == 1
    # After -> still visible.
    assert len(book.list_visible_to("agent:x", as_of_date="2026-02-01")) == 1


def test_list_visible_to_uses_clock_when_no_date_supplied():
    clock = Clock(current_date=date(2026, 1, 5))
    book = SignalBook(clock=clock)
    book.add_signal(
        _signal(
            signal_id="signal:future",
            published_date="2026-01-01",
            effective_date="2026-01-10",
            visibility="delayed",
        )
    )

    # No as_of_date kwarg -> book defers to its clock (2026-01-05) -> invisible.
    assert book.list_visible_to("agent:x") == ()


def test_list_visible_to_without_clock_or_date_skips_effective_date_filter():
    book = SignalBook()  # no clock
    book.add_signal(
        _signal(
            signal_id="signal:future",
            published_date="2026-01-01",
            effective_date="2026-01-10",
            visibility="delayed",
        )
    )

    # Without a date anchor we treat all signals as effective (per v0.7
    # simplification): no narrative interpretation.
    visible = book.list_visible_to("agent:x")
    assert len(visible) == 1


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_lists_all_signals_sorted():
    book = _book()
    book.add_signal(_signal(signal_id="signal:b"))
    book.add_signal(_signal(signal_id="signal:a"))

    snap = book.snapshot()
    assert snap["count"] == 2
    assert [item["signal_id"] for item in snap["signals"]] == [
        "signal:a",
        "signal:b",
    ]


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_add_signal_records_to_ledger():
    book = _book(with_ledger=True)
    book.add_signal(_signal(signal_id="signal:1", credibility=0.7, confidence=0.6))

    records = book.ledger.filter(event_type="signal_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "signal:1"
    assert record.source == "agent:rating_agency"
    assert record.target == "agent:firm_x"
    assert record.confidence == 0.6
    assert record.payload["credibility"] == 0.7
    assert record.simulation_date == "2026-01-01"


def test_mark_observed_records_to_ledger():
    book = _book(with_ledger=True)
    book.add_signal(_signal(signal_id="signal:1"))

    book.mark_observed("signal:1", "agent:bank_a")

    records = book.ledger.filter(event_type="signal_observed")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "signal:1"
    assert record.target == "agent:bank_a"
    assert record.agent_id == "agent:bank_a"


def test_mark_observed_rejects_invisible_signal():
    book = _book(with_ledger=True)
    book.add_signal(
        _signal(
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:legal",)},
        )
    )

    with pytest.raises(SignalError):
        book.mark_observed("signal:001", "agent:outsider")


# ---------------------------------------------------------------------------
# Cross-book isolation
# ---------------------------------------------------------------------------


def test_signal_book_does_not_mutate_other_books():
    kernel = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )

    kernel.ownership.add_position("agent:alice", "asset:aapl", 100)
    kernel.prices.set_price("asset:aapl", 150.0, "2026-01-01", "exchange")

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()

    kernel.signals.add_signal(_signal())
    kernel.signals.list_by_subject("agent:firm_x")
    kernel.signals.list_visible_to("agent:somebody")
    kernel.signals.snapshot()

    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before


def test_kernel_exposes_signal_book_with_default_wiring():
    kernel = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )

    kernel.signals.add_signal(_signal())

    # Signal book inherits ledger and clock from the kernel.
    assert kernel.signals.ledger is kernel.ledger
    assert kernel.signals.clock is kernel.clock
    assert len(kernel.ledger.filter(event_type="signal_added")) == 1
