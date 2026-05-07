"""
v1.28.9 — Opt-in synthetic scale smoke run.

Generate synthetic event-log records, write them
through the v1.28.2 / v1.28.3 writer, compute the
v1.28.4 Merkle root digest, and print a tiny summary.

Synthetic only. No real Japanese identifier. No real
sector name. No real securities code. No real prices.
No real holdings. No real filings. No adapter. No
investment output.

CLI usage from the git root::

    python japan-financial-world/examples/tools/run_v1_28_scale_smoke.py \
        --firms 3000 --periods 60 --seed synthetic_001 \
        --output .tmp/v1_28_scale

Default invocation runs a small smoke (10 firms × 4
periods) so that copy-pasting the bare command does
not accidentally generate gigabytes of files.

Performance budgets are intentionally **not** asserted
here — the smoke run prints elapsed time and on-disk
size so a human can compare to the design pin §Q
provisional targets without brittle hard-coded
thresholds.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Ensure ``world`` is importable when this script is
# invoked directly from the git root rather than via
# pytest (which adds the source root via the project
# pyproject.toml).
_HERE = Path(__file__).resolve()
_SOURCE_ROOT = _HERE.parents[2]  # japan-financial-world/
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from world.event_log_merkle import (  # noqa: E402
    compute_event_log_root_digest,
)
from world.event_log_schema import (  # noqa: E402
    CANONICAL_SCHEMA_COLUMN_ORDER,
    EventLogManifest,
    EventLogRecord,
)
from world.event_log_writer import (  # noqa: E402
    EventLogPartitionKey,
    EventLogPartitionWriter,
)


# ---------------------------------------------------------------------------
# Synthetic generators (deterministic, seed-driven)
# ---------------------------------------------------------------------------


def _synthetic_firm_id(idx: int) -> str:
    return f"firm:synthetic_{idx:06d}"


def _synthetic_sector_id(idx: int, n_sectors: int = 6) -> str:
    # synthetic_like archetypes only; no real sector name.
    return f"industry:synthetic_{idx % n_sectors:02d}"


def _synthetic_period_id(idx: int) -> str:
    # YYYY-Qn rotating quarterly synthetic periods
    # starting at 2026-Q1.
    base_year = 2026
    year = base_year + (idx // 4)
    quarter = (idx % 4) + 1
    return f"{year}-Q{quarter}"


def _synthetic_year_month(idx: int) -> str:
    # YYYY_MM matching the Q1=03 / Q2=06 / Q3=09 /
    # Q4=12 quarter-end month convention.
    base_year = 2026
    year = base_year + (idx // 4)
    quarter_end_month = ((idx % 4) + 1) * 3
    return f"{year}_{quarter_end_month:02d}"


def _make_record(
    *,
    firm_idx: int,
    period_idx: int,
    sector_idx: int,
    seed: str,
    record_type: str = "manual_annotation_recorded",
) -> EventLogRecord:
    return EventLogRecord(
        event_id=(
            f"evt:synthetic:{seed}:f{firm_idx:06d}"
            f":p{period_idx:03d}"
        ),
        run_id=f"run:synthetic:{seed}",
        period_id=_synthetic_period_id(period_idx),
        year_month=_synthetic_year_month(period_idx),
        sector_id=_synthetic_sector_id(sector_idx),
        record_type=record_type,
        source_space="examples.tools.run_v1_28_scale_smoke",
        target_entity_type="firm",
        target_entity_id=_synthetic_firm_id(firm_idx),
        event_index=period_idx,
        payload_schema_version="v1.28.9-synthetic",
        payload_ref_or_json=(
            f'{{"firm":{firm_idx},"period":{period_idx}}}'
        ),
        synthetic_seed=seed,
    )


def _make_manifest() -> EventLogManifest:
    return EventLogManifest(
        manifest_version="v1.28.9-synthetic",
        partition_schema_version=(
            "v1.28.x-partition-v1"
        ),
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


# ---------------------------------------------------------------------------
# Smoke run
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScaleSmokeRunSummary:
    firms: int
    periods: int
    investors: int
    banks: int
    seed: str
    output_dir: Path
    records_written: int
    partitions_written: int
    root_digest: str
    elapsed_seconds: float
    on_disk_bytes: int


def _on_disk_bytes(root: Path) -> int:
    if not root.is_dir():
        return 0
    return sum(
        p.stat().st_size
        for p in root.rglob("*")
        if p.is_file()
    )


def run_scale_smoke(
    *,
    firms: int,
    periods: int,
    investors: int = 0,
    banks: int = 0,
    seed: str,
    output_dir: Path,
) -> ScaleSmokeRunSummary:
    """Generate ``firms × periods`` synthetic records,
    plus optional ``investors`` and ``banks`` overlay
    records, write them through the v1.28.2 writer,
    and return a summary including the v1.28.4 root
    digest.

    All record content is purely a function of the
    inputs (``firms``, ``periods``, ``investors``,
    ``banks``, ``seed``); the same inputs always
    produce the same root digest.
    """
    if firms <= 0 or periods <= 0:
        raise ValueError(
            "firms and periods must both be > 0"
        )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = _make_manifest()
    t0 = time.perf_counter()

    # Group records by partition key for efficient
    # per-partition writers. Partition fan-out =
    # periods × n_sectors × distinct_record_types.
    by_partition: dict[
        EventLogPartitionKey, list[EventLogRecord]
    ] = {}

    def _push(rec: EventLogRecord) -> None:
        pk = EventLogPartitionKey.from_record(rec)
        by_partition.setdefault(pk, []).append(rec)

    for firm_idx in range(firms):
        sector_idx = firm_idx
        for period_idx in range(periods):
            _push(
                _make_record(
                    firm_idx=firm_idx,
                    period_idx=period_idx,
                    sector_idx=sector_idx,
                    seed=seed,
                )
            )
    for inv_idx in range(investors):
        for period_idx in range(periods):
            _push(
                _make_record(
                    firm_idx=10_000_000 + inv_idx,
                    period_idx=period_idx,
                    sector_idx=inv_idx,
                    seed=seed,
                    record_type=(
                        "investor_mandate_profile_recorded"
                    ),
                )
            )
    for bank_idx in range(banks):
        for period_idx in range(periods):
            _push(
                _make_record(
                    firm_idx=20_000_000 + bank_idx,
                    period_idx=period_idx,
                    sector_idx=bank_idx,
                    seed=seed,
                    record_type=(
                        "central_bank_signal_recorded"
                    ),
                )
            )

    records_written = 0
    for pk, recs in by_partition.items():
        w = EventLogPartitionWriter(
            root_path=output_dir,
            partition_key=pk,
            manifest=manifest,
        )
        result = w.append(recs)
        records_written += result.record_count

    root_digest = compute_event_log_root_digest(
        output_dir, manifest
    )
    t1 = time.perf_counter()

    return ScaleSmokeRunSummary(
        firms=firms,
        periods=periods,
        investors=investors,
        banks=banks,
        seed=seed,
        output_dir=output_dir,
        records_written=records_written,
        partitions_written=len(by_partition),
        root_digest=root_digest,
        elapsed_seconds=t1 - t0,
        on_disk_bytes=_on_disk_bytes(output_dir),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_v1_28_scale_smoke",
        description=(
            "v1.28.9 — Opt-in synthetic scale smoke run. "
            "Synthetic only. No real Japanese identifier. "
            "No real-data adapter."
        ),
    )
    parser.add_argument(
        "--firms",
        type=int,
        default=10,
        help="Number of synthetic firms (default: 10).",
    )
    parser.add_argument(
        "--periods",
        type=int,
        default=4,
        help="Number of synthetic periods (default: 4).",
    )
    parser.add_argument(
        "--investors",
        type=int,
        default=0,
        help=(
            "Optional synthetic investors overlay "
            "(default: 0)."
        ),
    )
    parser.add_argument(
        "--banks",
        type=int,
        default=0,
        help=(
            "Optional synthetic banks overlay "
            "(default: 0)."
        ),
    )
    parser.add_argument(
        "--seed",
        type=str,
        default="synthetic_smoke_default",
        help=(
            "Synthetic seed string (default: "
            "'synthetic_smoke_default')."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path(".tmp") / "v1_28_scale"
        ),
        help=(
            "Output directory (default: "
            "'.tmp/v1_28_scale')."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = run_scale_smoke(
        firms=args.firms,
        periods=args.periods,
        investors=args.investors,
        banks=args.banks,
        seed=args.seed,
        output_dir=args.output,
    )
    print(
        "v1.28.9 synthetic scale smoke run summary"
    )
    print("-" * 50)
    print(f"firms              : {summary.firms}")
    print(f"periods            : {summary.periods}")
    print(f"investors          : {summary.investors}")
    print(f"banks              : {summary.banks}")
    print(f"seed               : {summary.seed}")
    print(f"output_dir         : {summary.output_dir}")
    print(
        f"records_written    : {summary.records_written}"
    )
    print(
        "partitions_written : "
        f"{summary.partitions_written}"
    )
    print(
        f"root_digest        : {summary.root_digest}"
    )
    print(
        "elapsed_seconds    : "
        f"{summary.elapsed_seconds:.3f}"
    )
    print(
        f"on_disk_bytes      : {summary.on_disk_bytes}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
