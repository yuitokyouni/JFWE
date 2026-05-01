"""
Tests for the FWE Reference Demo reproducibility manifest.

The manifest is a small JSON document that captures just enough
metadata to identify a demo run later: code version, Python
runtime, input file hashes, ledger digest, and a short summary.

These tests verify the manifest's shape, the integrity of its
hashes / digest, the deterministic-write contract, and that
unavailability of git does not crash the builder. They do not
assert any specific git_sha or platform string — those are
environment-dependent.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest


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


def _load_modules() -> tuple[ModuleType, ModuleType, ModuleType]:
    """Load demo, replay_utils, and manifest modules together."""
    # Order matters: replay_utils registers itself in sys.modules so
    # the manifest module can find it through ``_load_replay_utils``.
    replay = _load("fwe_reference_replay_utils", "replay_utils.py")
    demo = _load("fwe_demo_run_for_manifest", "run_reference_loop.py")
    manifest = _load("fwe_manifest_module", "manifest.py")
    return demo, replay, manifest


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------


_REQUIRED_TOP_LEVEL_FIELDS = (
    "manifest_version",
    "run_type",
    "git_sha",
    "git_dirty",
    "git_status",
    "python_version",
    "platform",
    "input_files",
    "ledger_digest",
    "ledger_record_count",
    "summary",
)


def test_manifest_contains_required_fields():
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()
    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)

    for field in _REQUIRED_TOP_LEVEL_FIELDS:
        assert field in manifest, f"manifest is missing required field: {field}"

    assert manifest["run_type"] == "fwe_reference_demo"
    assert manifest["manifest_version"] == "fwe_reference_demo_manifest.v1"


def test_manifest_python_version_is_dotted_string():
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()
    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)

    py = manifest["python_version"]
    assert isinstance(py, str)
    assert re.fullmatch(r"\d+\.\d+\.\d+", py), (
        f"python_version must look like 'X.Y.Z'; got {py!r}"
    )


def test_manifest_platform_is_nonempty_string():
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()
    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)

    plat = manifest["platform"]
    assert isinstance(plat, str)
    assert plat


# ---------------------------------------------------------------------------
# Ledger digest matches replay_utils.ledger_digest(kernel)
# ---------------------------------------------------------------------------


def test_manifest_ledger_digest_matches_replay_utils():
    demo, replay, manifest_mod = _load_modules()
    kernel, summary = demo.run()
    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)

    assert manifest["ledger_digest"] == replay.ledger_digest(kernel), (
        "manifest ledger_digest must match replay_utils.ledger_digest(kernel)"
    )


def test_manifest_ledger_record_count_matches_kernel():
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()
    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)

    assert manifest["ledger_record_count"] == len(kernel.ledger.records)


# ---------------------------------------------------------------------------
# Input file hash is 64-char SHA-256
# ---------------------------------------------------------------------------


def test_manifest_input_files_default_includes_entities_yaml():
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()
    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)

    inputs = manifest["input_files"]
    assert isinstance(inputs, dict)
    # The default input is examples/reference_world/entities.yaml,
    # recorded as a path relative to the repo root.
    assert any(
        path.endswith("entities.yaml") for path in inputs
    ), f"expected entities.yaml among input_files; got {sorted(inputs)}"


def test_manifest_input_file_hash_is_64_char_sha256_hex(tmp_path: Path):
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()

    # Use an explicit synthetic input so the test does not depend on
    # the default path's contents.
    payload = b"reference demo manifest test fixture\n"
    target = tmp_path / "fixture.txt"
    target.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()

    manifest = manifest_mod.build_reference_demo_manifest(
        kernel, summary, input_paths=[target]
    )
    inputs = manifest["input_files"]
    assert len(inputs) == 1
    entry = next(iter(inputs.values()))
    assert entry["status"] == "ok"
    sha = entry["sha256"]
    assert isinstance(sha, str)
    assert len(sha) == 64
    assert all(c in "0123456789abcdef" for c in sha)
    assert sha == expected


def test_manifest_handles_missing_input_path(tmp_path: Path):
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()
    missing = tmp_path / "does_not_exist.txt"

    manifest = manifest_mod.build_reference_demo_manifest(
        kernel, summary, input_paths=[missing]
    )
    inputs = manifest["input_files"]
    assert len(inputs) == 1
    entry = next(iter(inputs.values()))
    assert entry["status"] == "missing"
    assert entry["sha256"] is None


# ---------------------------------------------------------------------------
# write_manifest produces deterministic JSON
# ---------------------------------------------------------------------------


def test_write_manifest_produces_stable_json(tmp_path: Path):
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()
    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)

    out_a = tmp_path / "manifest_a.json"
    out_b = tmp_path / "manifest_b.json"
    manifest_mod.write_manifest(manifest, out_a)
    manifest_mod.write_manifest(manifest, out_b)

    bytes_a = out_a.read_bytes()
    bytes_b = out_b.read_bytes()
    assert bytes_a == bytes_b, "two writes of the same manifest must be byte-identical"

    text = bytes_a.decode("utf-8")
    assert text.endswith("\n"), "manifest file must end with a trailing newline"

    # Manifest must round-trip through json.loads back to a dict that
    # matches the input (modulo dict ordering, which sort_keys handles).
    decoded = json.loads(text)
    assert isinstance(decoded, dict)
    assert decoded["manifest_version"] == manifest["manifest_version"]
    assert decoded["ledger_digest"] == manifest["ledger_digest"]


def test_write_manifest_creates_parent_dirs(tmp_path: Path):
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()
    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)

    nested = tmp_path / "a" / "b" / "c" / "manifest.json"
    assert not nested.parent.exists()
    manifest_mod.write_manifest(manifest, nested)
    assert nested.is_file()


# ---------------------------------------------------------------------------
# Git unavailable does not crash
# ---------------------------------------------------------------------------


def test_manifest_handles_git_unavailable(monkeypatch: pytest.MonkeyPatch):
    """
    If ``git`` is not on PATH, the builder must still return a
    well-formed manifest with git_sha / git_dirty set to None.
    """
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()

    def _raise(*args, **kwargs):
        raise FileNotFoundError("git not found (simulated)")

    monkeypatch.setattr(manifest_mod.subprocess, "run", _raise)

    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)
    assert manifest["git_sha"] is None
    assert manifest["git_dirty"] is None
    assert manifest["git_status"] == "git_unavailable"
    # Other fields still populated.
    assert manifest["ledger_digest"]
    assert manifest["ledger_record_count"] > 0


def test_manifest_handles_not_a_repo(monkeypatch: pytest.MonkeyPatch):
    """
    If we are not inside a git work tree, status must be
    ``"not_a_repo"`` and git_sha / git_dirty must be None.
    """
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()

    class _FakeProcess:
        def __init__(self, returncode=128, stdout="", stderr="not a git repository"):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def _fake_run(*args, **kwargs):
        # rev-parse --is-inside-work-tree -> non-zero
        return _FakeProcess(returncode=128, stdout="", stderr="fatal: not a git repository")

    monkeypatch.setattr(manifest_mod.subprocess, "run", _fake_run)

    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)
    assert manifest["git_status"] == "not_a_repo"
    assert manifest["git_sha"] is None
    assert manifest["git_dirty"] is None


# ---------------------------------------------------------------------------
# No simulation behavior change
# ---------------------------------------------------------------------------


def test_building_a_manifest_does_not_change_the_ledger_digest():
    """
    Building (and writing) a manifest reads from the kernel; it
    must not append, mutate, or otherwise change the ledger.
    """
    demo, replay, manifest_mod = _load_modules()
    kernel, summary = demo.run()

    digest_before = replay.ledger_digest(kernel)
    record_count_before = len(kernel.ledger.records)

    _ = manifest_mod.build_reference_demo_manifest(kernel, summary)

    digest_after = replay.ledger_digest(kernel)
    record_count_after = len(kernel.ledger.records)

    assert digest_before == digest_after, (
        "building a manifest must not change the ledger"
    )
    assert record_count_before == record_count_after


def test_summary_is_dataclass_serializable():
    """The DemoSummary dataclass must serialize cleanly into the manifest."""
    demo, _, manifest_mod = _load_modules()
    kernel, summary = demo.run()
    manifest = manifest_mod.build_reference_demo_manifest(kernel, summary)

    summary_field = manifest["summary"]
    assert isinstance(summary_field, dict)
    # DemoSummary fields are setup_record_count, loop_record_ids,
    # delivery_targets, record_type_counts.
    assert "setup_record_count" in summary_field
    assert "loop_record_ids" in summary_field
    assert "delivery_targets" in summary_field
    assert "record_type_counts" in summary_field
