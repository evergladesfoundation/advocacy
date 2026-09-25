from __future__ import annotations

import json
from pathlib import Path

from cdmp_monitor.models import Attachment

DEFAULT_STATE_PATH = Path("data/cdmp/state.json")


def load_state(path: Path = DEFAULT_STATE_PATH) -> dict:
    if not path.exists():
        return {"plans": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("plans", {})
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plans = {
        plan_guid: sorted(rows, key=lambda row: (row["uploadedDate"], row["fileName"]))
        for plan_guid, rows in sorted(state.get("plans", {}).items())
    }
    payload = {"plans": plans}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def known_keys(state: dict, plan_guid: str) -> set[tuple[str, str]]:
    rows = state.get("plans", {}).get(plan_guid, [])
    return {(row["fileName"], row["uploadedDate"]) for row in rows}


def remember(state: dict, plan_guid: str, attachments: list[Attachment]) -> None:
    plans = state.setdefault("plans", {})
    rows = list(plans.get(plan_guid, []))
    seen = {(row["fileName"], row["uploadedDate"]) for row in rows}
    for item in attachments:
        if item.key in seen:
            continue
        rows.append({"fileName": item.file_name, "uploadedDate": item.uploaded_date})
        seen.add(item.key)
    plans[plan_guid] = rows
