"""Task loading and weighted score aggregation (programmatic checks + VLM rubric)."""
from __future__ import annotations

import glob
from pathlib import Path

import yaml

REQUIRED = {"id", "discipline", "mode", "tools", "prompt", "inputs", "checks", "difficulty"}
MODES = {"computer_use", "code_gen", "hybrid"}


def load_tasks(root: str | Path = "tasks") -> list[dict]:
    tasks = []
    for f in sorted(glob.glob(str(Path(root) / "*.yaml"))):
        tasks.extend(yaml.safe_load(open(f)))
    for t in tasks:
        missing = REQUIRED - t.keys()
        if missing:
            raise ValueError(f"{t.get('id')}: missing {missing}")
        if t["mode"] not in MODES:
            raise ValueError(f"{t['id']}: bad mode {t['mode']}")
        if abs(sum(c["weight"] for c in t["checks"]) - 1.0) > 1e-6:
            raise ValueError(f"{t['id']}: check weights must sum to 1")
    return tasks


def aggregate(task: dict, results: dict[str, float]) -> float:
    """results: check name -> [0,1]. Missing checks score 0 (no credit for skipped work)."""
    return sum(c["weight"] * results.get(c["name"], 0.0) for c in task["checks"])
