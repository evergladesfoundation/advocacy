from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Application:
    cdmp_number: str
    plan_guid: str
    sharepoint_folder_url: str = ""
    notes: str = ""


@dataclass(frozen=True)
class Attachment:
    file_name: str
    uploaded_date: str
    notes: str = ""

    @property
    def key(self) -> tuple[str, str]:
        """Minimum dedup key. Filenames alone are not unique."""
        return (self.file_name, self.uploaded_date)
