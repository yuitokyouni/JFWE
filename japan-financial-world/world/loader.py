"""YAML data loading for sample and scenario worlds."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .registry import Registry


def load_yaml(path: str | Path) -> Any:
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError("PyYAML is required to load YAML data") from exc

    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or []


def load_sample_world(sample_dir: str | Path) -> Registry:
    base = Path(sample_dir)
    registry = Registry()
    for filename, collection in [
        ("firms.yaml", "agents"),
        ("investors.yaml", "agents"),
        ("banks.yaml", "agents"),
        ("assets.yaml", "assets"),
        ("contracts.yaml", "contracts"),
        ("markets.yaml", "markets"),
    ]:
        for item in load_yaml(base / filename):
            registry.add(collection, item)
    return registry
