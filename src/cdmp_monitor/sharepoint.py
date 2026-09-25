from __future__ import annotations

import os
import urllib.parse
from pathlib import Path

import httpx

GRAPH = "https://graph.microsoft.com/v1.0"
SIMPLE_UPLOAD_LIMIT = 4 * 1024 * 1024


class SharePointConfigError(RuntimeError):
    pass


def upload_file(path: Path, folder: str) -> str:
    """Upload a PDF with Microsoft Graph. Returns the file's web URL when Graph provides one."""
    drive_id = os.environ.get("GRAPH_DRIVE_ID", "").strip()
    tenant_id = os.environ.get("GRAPH_TENANT_ID", "").strip()
    client_id = os.environ.get("GRAPH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GRAPH_CLIENT_SECRET", "").strip()
    folder = folder.strip().strip("/")
    if not folder:
        raise SharePointConfigError("SharePoint folder is not set for this application")
    if not all([drive_id, tenant_id, client_id, client_secret]):
        raise SharePointConfigError(
            "Graph upload needs GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, and GRAPH_DRIVE_ID"
        )
    token = _token(tenant_id, client_id, client_secret)
    content = path.read_bytes()
    item_path = f"{folder}/{path.name}"
    if len(content) < SIMPLE_UPLOAD_LIMIT:
        return _put_small(token, drive_id, item_path, content)
    return _upload_session(token, drive_id, item_path, content)


def content_url(drive_id: str, item_path: str) -> str:
    quoted = urllib.parse.quote(item_path, safe="/")
    return f"{GRAPH}/drives/{drive_id}/root:/{quoted}:/content"


def _token(tenant_id: str, client_id: str, client_secret: str) -> str:
    response = httpx.post(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _put_small(token: str, drive_id: str, item_path: str, content: bytes) -> str:
    response = httpx.put(
        content_url(drive_id, item_path),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/pdf"},
        content=content,
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("webUrl") or ""


def _upload_session(token: str, drive_id: str, item_path: str, content: bytes) -> str:
    quoted = urllib.parse.quote(item_path, safe="/")
    start = httpx.post(
        f"{GRAPH}/drives/{drive_id}/root:/{quoted}:/createUploadSession",
        headers={"Authorization": f"Bearer {token}"},
        json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
        timeout=30,
    )
    start.raise_for_status()
    upload_url = start.json()["uploadUrl"]
    chunk = 5 * 1024 * 1024
    web_url = ""
    for offset in range(0, len(content), chunk):
        piece = content[offset : offset + chunk]
        end = offset + len(piece) - 1
        response = httpx.put(
            upload_url,
            headers={
                "Content-Length": str(len(piece)),
                "Content-Range": f"bytes {offset}-{end}/{len(content)}",
            },
            content=piece,
            timeout=120,
        )
        response.raise_for_status()
        web_url = response.json().get("webUrl") or web_url
    return web_url
