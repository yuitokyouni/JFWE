from datetime import datetime, timezone

from world.ledger import Ledger, RecordType


def test_append_and_query_ledger_record():
    ledger = Ledger()

    record = ledger.append(
        "object_registered",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        simulation_date="2026-01-01",
        source="registry",
        object_id="firm:reference_manufacturer_001",
        payload={"kind": "firm"},
        metadata={"schema_version": "v1"},
    )

    assert record.sequence == 0
    assert record.record_type == RecordType.OBJECT_REGISTERED
    assert record.object_id == "firm:reference_manufacturer_001"
    assert record.payload["kind"] == "firm"

    result = ledger.query(
        record_type="object_registered",
        object_id="firm:reference_manufacturer_001",
    )

    assert result == (record,)


def test_ledger_jsonl_roundtrip():
    ledger = Ledger()

    ledger.append(
        "signal_emitted",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        simulation_date="2026-01-01",
        source="media:nikkei_like",
        target="investor:macro_fund_a",
        object_id="signal:earnings_warning_001",
        payload={"topic": "earnings_warning"},
    )

    jsonl = ledger.to_jsonl()
    restored = Ledger.from_jsonl(jsonl)

    assert len(restored.records) == 1
    assert restored.records[0].to_dict() == ledger.records[0].to_dict()


def test_warning_and_error_records():
    ledger = Ledger()

    warning = ledger.warning(
        "liquidity dropped below threshold",
        simulation_date="2026-01-02",
        source="market:equity",
        object_id="firm:sample_001",
    )

    error = ledger.error(
        "contract settlement failed",
        simulation_date="2026-01-02",
        source="contract_engine",
        object_id="contract:loan_001",
    )

    assert warning.record_type == RecordType.WARNING
    assert error.record_type == RecordType.ERROR
    assert ledger.query(record_type="warning") == (warning,)
    assert ledger.query(record_type="error") == (error,)