from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EMPTY_STATE: dict[str, Any] = {
    "seen_ids": [],
    "baselined_sources": [],
    "last_run_date": None,
}


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "seen_ids": [],
            "baselined_sources": [],
            "last_run_date": None,
        }
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("seen_ids", [])
    data.setdefault("baselined_sources", [])
    data.setdefault("last_run_date", None)
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seen_ids": sorted(set(state.get("seen_ids", []))),
        "baselined_sources": sorted(set(state.get("baselined_sources", []))),
        "last_run_date": state.get("last_run_date"),
        "last_fr_issue": state.get("last_fr_issue"),
        "last_crec_package": state.get("last_crec_package"),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
