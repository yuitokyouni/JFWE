"""
Reproducibility manifest for the FWE Reference Demo.

A manifest is a small JSON document that captures *just enough*
metadata to identify a demo run later: the code version, the Python
runtime, the input files (hashed), the canonical ledger digest, and
a short run summary.

This is **not** an experiment-tracking system. It does not carry
client data, expert input, paid-data outputs, plot images, or any
other content covered by the public / restricted boundary
(``docs/public_private_boundary.md``). It carries only what is
needed to answer "is this the same run as that one?" and "if I
re-run on the same code, do I get the same ledger?"

Two entry points:

- ``build_reference_demo_manifest(kernel, summary, *, input_paths=None)``
  — return a manifest dict.
- ``write_manifest(manifest, output_path)`` — write the manifest
  as deterministic JSON (``sort_keys=True``, ``indent=2``,
  ``ensure_ascii=False``, trailing newline).

The manifest is jurisdiction-neutral. It does not embed any
real-institution name, paid-data identifier, or proprietary
provenance. If a future v3 (JFWE Proprietary) needs richer
provenance, that lives in a separate, private manifest schema —
not here.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import platform as platform_module
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


MANIFEST_VERSION: str = "fwe_reference_demo_manifest.v1"
RUN_TYPE: str = "fwe_reference_demo"

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Default input file the manifest hashes if no input_paths are
# provided. The reference demo's entities.yaml is its only
# user-visible input file; ``run_reference_loop.py`` itself is
# tracked via the git_sha field rather than file-hashed.
_DEFAULT_INPUT_PATHS: tuple[Path, ...] = (
    Path(__file__).resolve().parent / "entities.yaml",
)


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """Return the hex-encoded SHA-256 of the file at ``path``."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_input_files(
    input_paths: tuple[Path, ...] | list[Path] | tuple[str, ...] | list[str],
) -> dict[str, dict[str, str | None]]:
    """
    Return a mapping ``{path_string: {"sha256": ..., "status": ...}}``.

    A missing file does not crash; its entry has ``status="missing"``
    and ``sha256=None``. This keeps the manifest a complete artifact
    even in degraded environments.

    Path strings are stored relative to the repository root when
    possible, falling back to the absolute path otherwise. This makes
    manifests portable across checkouts at the same code revision.
    """
    result: dict[str, dict[str, str | None]] = {}
    for raw in input_paths:
        path = Path(raw)
        # Normalize: resolve once for deterministic hashing input,
        # but record the relative-to-repo string for portability.
        resolved = path.resolve() if path.exists() else path
        try:
            display = str(resolved.relative_to(_REPO_ROOT))
        except (ValueError, OSError):
            display = str(resolved)

        if not resolved.is_file():
            result[display] = {"sha256": None, "status": "missing"}
            continue

        result[display] = {
            "sha256": _sha256_file(resolved),
            "status": "ok",
        }
    return result


# ---------------------------------------------------------------------------
# Git probe (best-effort)
# ---------------------------------------------------------------------------


def _git_probe() -> dict[str, Any]:
    """
    Best-effort probe of the current git revision and dirty flag.

    Returns a dict with ``sha`` (hex string or None), ``dirty``
    (bool or None), and ``status`` (one of "ok", "git_unavailable",
    "not_a_repo", "error"). Never raises.
    """
    git_root = _REPO_ROOT

    def _run(args: list[str]) -> tuple[int, str, str]:
        process = subprocess.run(
            ["git", *args],
            cwd=str(git_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return process.returncode, process.stdout, process.stderr

    try:
        rc, stdout, _ = _run(["rev-parse", "--is-inside-work-tree"])
    except FileNotFoundError:
        return {"sha": None, "dirty": None, "status": "git_unavailable"}
    except (subprocess.SubprocessError, OSError):
        return {"sha": None, "dirty": None, "status": "error"}

    if rc != 0 or stdout.strip() != "true":
        return {"sha": None, "dirty": None, "status": "not_a_repo"}

    try:
        rc, stdout, _ = _run(["rev-parse", "HEAD"])
        sha = stdout.strip() if rc == 0 and stdout.strip() else None

        rc, stdout, _ = _run(["status", "--porcelain"])
        dirty = bool(stdout.strip()) if rc == 0 else None
    except (subprocess.SubprocessError, OSError):
        return {"sha": None, "dirty": None, "status": "error"}

    return {"sha": sha, "dirty": dirty, "status": "ok"}


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------


def _summary_to_dict(summary: Any) -> Any:
    """
    Convert a demo summary into a JSON-friendly dict. The reference
    demo uses a ``DemoSummary`` dataclass; if a caller passes a
    plain dict we keep it as-is.
    """
    if dataclasses.is_dataclass(summary):
        return dataclasses.asdict(summary)
    if isinstance(summary, Mapping):
        return dict(summary)
    raise TypeError(
        "summary must be a dataclass instance or a Mapping; "
        f"got {type(summary).__name__}"
    )


# ``examples/reference_world/`` is not a Python package (it has no
# __init__.py and is loaded via importlib in tests and at script
# entry). The manifest module therefore cannot use a relative
# ``from .replay_utils import ...``. Instead, look up replay_utils
# in sys.modules under the names that the demo / tests / direct
# users register it under, then fall back to loading it from the
# sibling file.
def _load_replay_utils() -> Any:
    for mod_name in (
        "fwe_reference_replay_utils",
        "replay_utils",
        "demo_replay_utils",
    ):
        module = sys.modules.get(mod_name)
        if module is not None and hasattr(module, "ledger_digest"):
            return module

    import importlib.util

    sibling = Path(__file__).resolve().parent / "replay_utils.py"
    spec = importlib.util.spec_from_file_location(
        "fwe_reference_replay_utils", sibling
    )
    if spec is None or spec.loader is None:
        raise ImportError(
            f"could not load replay_utils sibling at {sibling}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules["fwe_reference_replay_utils"] = module
    spec.loader.exec_module(module)
    return module


def build_reference_demo_manifest(
    kernel: Any,
    summary: Any,
    *,
    input_paths: tuple[Path | str, ...] | list[Path | str] | None = None,
) -> dict[str, Any]:
    """
    Build the reproducibility manifest for a single reference-demo run.

    Parameters
    ----------
    kernel
        The populated ``WorldKernel`` returned by
        ``run_reference_loop.run()``.
    summary
        The ``DemoSummary`` (or compatible mapping) returned alongside
        the kernel.
    input_paths
        Files to hash into the manifest. Defaults to the demo's
        ``entities.yaml``. Missing files are recorded with
        ``status="missing"``; they do not crash the builder.

    Returns
    -------
    A dict suitable for JSON serialization. See the module docstring
    for the field set.
    """
    replay_utils = _load_replay_utils()

    selected_paths = (
        tuple(Path(p) for p in input_paths)
        if input_paths is not None
        else _DEFAULT_INPUT_PATHS
    )

    git_info = _git_probe()
    record_count = len(kernel.ledger.records)

    manifest: dict[str, Any] = {
        "manifest_version": MANIFEST_VERSION,
        "run_type": RUN_TYPE,
        "git_sha": git_info["sha"],
        "git_dirty": git_info["dirty"],
        "git_status": git_info["status"],
        "python_version": sys.version.split()[0],
        "platform": platform_module.platform(),
        "input_files": _hash_input_files(selected_paths),
        "ledger_digest": replay_utils.ledger_digest(kernel),
        "ledger_record_count": record_count,
        "summary": _summary_to_dict(summary),
    }
    return manifest


# ---------------------------------------------------------------------------
# Manifest writer
# ---------------------------------------------------------------------------


def write_manifest(
    manifest: Mapping[str, Any],
    output_path: Path | str,
) -> None:
    """
    Write the manifest to ``output_path`` as deterministic JSON:
    ``sort_keys=True``, ``indent=2``, ``ensure_ascii=False``, and a
    trailing newline. Two byte-identical writes for the same manifest
    dict are guaranteed (modulo dict insertion order, which
    sort_keys=True normalizes).

    Parent directories are created if missing. The file is written
    atomically via a temporary sibling + rename so a crashed write
    does not leave a half-empty manifest at the target path.
    """
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    encoded = json.dumps(
        manifest,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
    )
    if not encoded.endswith("\n"):
        encoded += "\n"

    tmp = target.with_suffix(target.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(encoded)
    tmp.replace(target)
