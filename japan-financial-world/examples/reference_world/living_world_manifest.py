"""
v1.9.2 Living-world reproducibility manifest.

Mirrors v1.7-era ``examples/reference_world/manifest.py`` for the
multi-period v1.9.0 sweep. A manifest is a small JSON document
that captures *just enough* metadata to identify a living-world
run later: the code version, the Python runtime, the canonical
living-world digest, and a short structural summary.

This is **not** an experiment-tracking system. It does not carry
client data, expert input, paid-data outputs, plot images, or any
content covered by the public / restricted boundary
(``docs/public_private_boundary.md``). It carries only what is
needed to answer:

- *"is this the same run as that one?"* → check ``living_world_digest``;
- *"if I re-run on the same code, do I get the same trace?"* →
  re-run the demo and compare the digest.

Two entry points:

- :func:`build_living_world_manifest` returns a dict.
- :func:`write_living_world_manifest` writes it as deterministic
  JSON (``sort_keys=True``, ``indent=2``, ``ensure_ascii=False``,
  trailing newline) atomically (temp sibling + rename).

The manifest is jurisdiction-neutral. It does not embed any
real-institution name, paid-data identifier, or proprietary
provenance. If a future v3 (JFWE Proprietary) needs richer
provenance, that lives in a separate, private manifest schema —
not here.
"""

from __future__ import annotations

import json
import platform as platform_module
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from world.reference_living_world import LivingReferenceWorldResult

from examples.reference_world.living_world_replay import (
    LIVING_WORLD_BOUNDARY_STATEMENT,
    canonicalize_living_world_result,
    living_world_digest,
)


MANIFEST_VERSION: str = "living_world_manifest.v1"
RUN_TYPE: str = "living_reference_world"

_REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Git probe (best-effort; never raises)
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
# Builder
# ---------------------------------------------------------------------------


def _summary_from_result(result: LivingReferenceWorldResult) -> dict[str, Any]:
    """Compact summary echoing the result's headline fields. Kept
    intentionally narrow so the manifest stays small.

    v1.10.5 additive: engagement-layer counts (industries,
    stewardship themes, dialogues, escalation candidates,
    corporate strategic response candidates) are echoed when the
    result carries them; they fall through to 0 for older result
    objects without the v1.10 fields.
    """
    industry_count = len(getattr(result, "industry_ids", ()))
    theme_count = len(getattr(result, "stewardship_theme_ids", ()))
    dialogue_total = sum(
        len(getattr(p, "dialogue_ids", ()))
        for p in result.per_period_summaries
    )
    escalation_total = sum(
        len(getattr(p, "investor_escalation_candidate_ids", ()))
        for p in result.per_period_summaries
    )
    response_total = sum(
        len(getattr(p, "corporate_strategic_response_candidate_ids", ()))
        for p in result.per_period_summaries
    )
    industry_condition_total = sum(
        len(getattr(p, "industry_condition_ids", ()))
        for p in result.per_period_summaries
    )
    return {
        "run_id": result.run_id,
        "period_count": result.period_count,
        "period_dates": [
            ps.as_of_date for ps in result.per_period_summaries
        ],
        "firm_count": len(result.firm_ids),
        "investor_count": len(result.investor_ids),
        "bank_count": len(result.bank_ids),
        "industry_count": industry_count,
        "stewardship_theme_count": theme_count,
        "industry_condition_total": industry_condition_total,
        "dialogue_total": dialogue_total,
        "investor_escalation_candidate_total": escalation_total,
        "corporate_strategic_response_candidate_total": response_total,
        "created_record_count": result.created_record_count,
    }


def build_living_world_manifest(
    kernel: Any,
    result: LivingReferenceWorldResult,
    *,
    report: Any = None,
    input_profile: str | None = None,
    preset_name: str | None = None,
    variable_count: int | None = None,
    exposure_count: int | None = None,
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the reproducibility manifest for a single living-world run.

    Parameters
    ----------
    kernel
        The populated ``WorldKernel`` returned by
        ``run_living_reference_world(...)``'s caller (the kernel
        the run wrote into).
    result
        The :class:`LivingReferenceWorldResult` returned by
        ``run_living_reference_world``.
    report
        Optional :class:`world.living_world_report.LivingWorldTraceReport`.
        If supplied, the manifest carries a ``report_digest`` field;
        otherwise that field is omitted.
    input_profile
        Optional caller-supplied label naming the input fixture
        (e.g., ``"reference_world_default"``). Free-form string.
    preset_name
        Optional caller-supplied preset name. Free-form string.
    variable_count / exposure_count
        Optional caller-supplied counts of the seed variables /
        exposures. Reported in the manifest as written; the
        manifest does not query them from the kernel because the
        kernel may have other variables / exposures unrelated to
        this run.
    summary
        Optional caller-supplied summary mapping that overrides
        the default summary derived from ``result``. Useful when
        a caller wants to attach extra fields without changing the
        manifest schema.

    Returns
    -------
    A dict suitable for JSON serialization. See the module
    docstring for the field set. The dict is fully deterministic
    given a deterministic kernel + result.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(result, LivingReferenceWorldResult):
        raise TypeError(
            "result must be a LivingReferenceWorldResult; "
            f"got {type(result).__name__}"
        )

    git_info = _git_probe()
    digest = living_world_digest(kernel, result, report=report)
    summary_payload: dict[str, Any]
    if summary is not None:
        summary_payload = dict(summary)
    else:
        summary_payload = _summary_from_result(result)

    per_period_total = sum(
        p.record_count_created for p in result.per_period_summaries
    )
    infra_record_count = max(
        result.created_record_count - per_period_total, 0
    )

    manifest: dict[str, Any] = {
        "manifest_version": MANIFEST_VERSION,
        "run_type": RUN_TYPE,
        "git_sha": git_info["sha"],
        "git_dirty": git_info["dirty"],
        "git_status": git_info["status"],
        "python_version": sys.version.split()[0],
        "platform": platform_module.platform(),
        "input_profile": input_profile,
        "preset_name": preset_name,
        "period_count": result.period_count,
        "firm_count": len(result.firm_ids),
        "investor_count": len(result.investor_ids),
        "bank_count": len(result.bank_ids),
        "variable_count": variable_count,
        "exposure_count": exposure_count,
        "ledger_record_count_before": result.ledger_record_count_before,
        "ledger_record_count_after": result.ledger_record_count_after,
        "created_record_count": result.created_record_count,
        "infra_record_count": infra_record_count,
        "per_period_record_count_total": per_period_total,
        "living_world_digest": digest,
        "boundary_statement": LIVING_WORLD_BOUNDARY_STATEMENT,
        "summary": summary_payload,
    }

    if report is not None:
        canonical = canonicalize_living_world_result(
            kernel, result, report=report
        )
        # The report_digest cross-check confirms the v1.9.1 reporter
        # observed the same canonical structure the manifest digest
        # was computed over. Useful as a sanity check; not a
        # substitute for the canonical digest itself.
        report_view = {
            "record_type_counts": canonical["record_type_counts"],
            "shared_selected_refs": canonical["shared_selected_refs"],
            "investor_only_refs": canonical["investor_only_refs"],
            "bank_only_refs": canonical["bank_only_refs"],
        }
        import hashlib

        manifest["report_digest"] = hashlib.sha256(
            json.dumps(
                report_view,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    return manifest


# ---------------------------------------------------------------------------
# Writer (deterministic, atomic)
# ---------------------------------------------------------------------------


def write_living_world_manifest(
    manifest: Mapping[str, Any],
    output_path: Path | str,
) -> Path:
    """
    Write the manifest to ``output_path`` as deterministic JSON:
    ``sort_keys=True``, ``indent=2``, ``ensure_ascii=False``, and a
    trailing newline. Two byte-identical writes for the same
    manifest dict are guaranteed (modulo dict insertion order,
    which sort_keys=True normalizes).

    Parent directories are created if missing. The file is written
    atomically via a temporary sibling + rename so a crashed write
    does not leave a half-empty manifest at the target path.

    Returns the resolved target ``Path`` for caller convenience.
    """
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    encoded = json.dumps(
        dict(manifest),
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
    return target
