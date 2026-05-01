"""
Replay-determinism gate for the FWE Reference Demo.

Two runs of ``examples.reference_world.run_reference_loop.run()``
must produce the same canonical ledger trace. This is the
test-side guardrail behind the v1 invariant that the ledger is a
reproducible, byte-stable causal record for a given input.

The canonicalization helpers live in
``examples/reference_world/replay_utils.py``. They strip
``record_id`` and ``timestamp`` (both wall-clock-derived) and
rewrite ``parent_record_ids`` as ``parent_sequences``. The volatility
profile that motivated this list is documented in the
``replay_utils`` module docstring.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


_DEMO_DIR = (
    Path(__file__).resolve().parents[1] / "examples" / "reference_world"
)


def _load(name: str, file_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, _DEMO_DIR / file_name
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# Loaded once per test invocation — exec'ing the demo module twice
# in a single test instead would still work (the module has no
# global state), but loading once is the smaller footprint.
def _load_demo_modules() -> tuple[ModuleType, ModuleType]:
    demo = _load("fwe_reference_demo_run_replay", "run_reference_loop.py")
    replay = _load("fwe_reference_replay_utils", "replay_utils.py")
    return demo, replay


# ---------------------------------------------------------------------------
# Two runs produce equal canonical ledger traces
# ---------------------------------------------------------------------------


def test_two_runs_produce_equal_canonical_ledger():
    demo, replay = _load_demo_modules()
    kernel_a, _ = demo.run()
    kernel_b, _ = demo.run()

    canonical_a = replay.canonicalize_ledger(kernel_a)
    canonical_b = replay.canonicalize_ledger(kernel_b)

    assert len(canonical_a) == len(canonical_b), (
        "two runs of the demo produced different ledger record counts"
    )
    assert canonical_a == canonical_b, (
        "two runs of the demo produced different canonical ledger traces"
    )


def test_two_runs_produce_equal_digest():
    demo, replay = _load_demo_modules()
    kernel_a, _ = demo.run()
    kernel_b, _ = demo.run()

    digest_a = replay.ledger_digest(kernel_a)
    digest_b = replay.ledger_digest(kernel_b)

    assert digest_a == digest_b, (
        f"ledger digest changed across runs:\n"
        f"  run A: {digest_a}\n"
        f"  run B: {digest_b}"
    )


def test_digest_is_a_sha256_hex_string():
    """Sanity: the digest is a 64-char lowercase hex string."""
    demo, replay = _load_demo_modules()
    kernel, _ = demo.run()
    digest = replay.ledger_digest(kernel)
    assert isinstance(digest, str)
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


# ---------------------------------------------------------------------------
# Volatile fields are excluded from the canonical view
# ---------------------------------------------------------------------------


def test_canonical_ledger_excludes_volatile_fields():
    """
    The canonical view must not carry ``record_id`` or ``timestamp``;
    those vary across runs and would defeat replay determinism.
    """
    demo, replay = _load_demo_modules()
    kernel, _ = demo.run()
    canonical = replay.canonicalize_ledger(kernel)

    assert canonical, "demo produced an empty ledger"
    for entry in canonical:
        assert "record_id" not in entry, (
            "canonical ledger must not include record_id"
        )
        assert "timestamp" not in entry, (
            "canonical ledger must not include timestamp"
        )


def test_canonical_ledger_rewrites_parent_record_ids_as_sequences():
    """
    ``parent_record_ids`` is a tuple of volatile record_ids, so it
    is replaced by ``parent_sequences``: integer indices that map
    each parent to its position in the same ledger. This preserves
    the causal lineage as deterministic data.
    """
    demo, replay = _load_demo_modules()
    kernel, _ = demo.run()
    canonical = replay.canonicalize_ledger(kernel)

    found_record_with_parents = False
    for entry in canonical:
        assert "parent_record_ids" not in entry, (
            "canonical ledger must not retain raw parent_record_ids"
        )
        assert "parent_sequences" in entry, (
            "canonical ledger must include parent_sequences"
        )
        if entry["parent_sequences"]:
            found_record_with_parents = True
            for seq in entry["parent_sequences"]:
                # Every parent reference resolves to an int sequence
                # within the same ledger; nothing in the demo points
                # to an external record_id.
                assert isinstance(seq, int), (
                    f"parent_sequences entries must be ints; "
                    f"got {seq!r}"
                )
                assert 0 <= seq < entry["sequence"], (
                    f"parent sequence {seq} must precede record "
                    f"sequence {entry['sequence']}"
                )

    assert found_record_with_parents, (
        "the demo's institutional action record should have parents"
    )


# ---------------------------------------------------------------------------
# Canonical view round-trips through JSON
# ---------------------------------------------------------------------------


def test_canonical_ledger_is_json_serializable():
    """
    The canonical view must serialize to JSON with sort_keys=True
    so the digest computation is stable across Python versions and
    OS dict-ordering implementations.
    """
    demo, replay = _load_demo_modules()
    kernel, _ = demo.run()
    canonical = replay.canonicalize_ledger(kernel)
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    assert encoded
    # And decodes back to a structurally-equal value.
    decoded = json.loads(encoded)
    assert isinstance(decoded, list)
    assert len(decoded) == len(canonical)
