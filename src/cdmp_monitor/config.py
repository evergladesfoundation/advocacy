from __future__ import annotations

import json
from pathlib import Path

from cdmp_monitor.models import Application

DEFAULT_APPLICATIONS_PATH = Path("data/cdmp/applications.json")
CONFIRMED_CDMP_NUMBER = "CDMP20250017"


def load_applications(path: Path = DEFAULT_APPLICATIONS_PATH) -> list[Application]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must be a list of applications")
    applications = [_application(item) for item in payload]
    if not applications:
        raise ValueError(f"{path} has no applications")
    return applications


def find_application(
    applications: list[Application],
    *,
    cdmp_number: str | None = None,
    plan_guid: str | None = None,
) -> Application:
    if cdmp_number:
        matches = [item for item in applications if item.cdmp_number == cdmp_number]
        label = cdmp_number
    elif plan_guid:
        matches = [item for item in applications if item.plan_guid == plan_guid]
        label = plan_guid
    else:
        raise ValueError("Provide a CDMP number or a plan GUID")
    if len(matches) != 1:
        raise ValueError(f"Expected one application for {label}, found {len(matches)}")
    return matches[0]


def _application(item: object) -> Application:
    if not isinstance(item, dict):
        raise ValueError("Each application must be an object")
    plan_guid = str(item.get("planGuid") or "").strip()
    if not plan_guid:
        raise ValueError("Each application needs a planGuid")
    return Application(
        cdmp_number=str(item.get("cdmpNumber") or "").strip(),
        plan_guid=plan_guid,
        sharepoint_folder_url=str(item.get("sharepointFolderUrl") or "").strip(),
        notes=str(item.get("notes") or "").strip(),
    )
