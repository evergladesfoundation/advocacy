from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from cdmp_monitor.dates import is_recent
from cdmp_monitor.models import Attachment


@dataclass
class PlanDiff:
    alertable: list[Attachment] = field(default_factory=list)
    recorded_only: list[Attachment] = field(default_factory=list)

    @property
    def new_items(self) -> list[Attachment]:
        return [*self.alertable, *self.recorded_only]


def diff_attachments(
    current: list[Attachment],
    seen: set[tuple[str, str]],
    run_date: date,
) -> PlanDiff:
    """Split attachments that are new to the state store.

    Items uploaded within the last 7 days are alertable. Older items are
    recorded so a later run does not flag them, and they are not alerted.
    """
    result = PlanDiff()
    fresh: set[tuple[str, str]] = set()
    for item in current:
        if item.key in seen or item.key in fresh:
            continue
        fresh.add(item.key)
        if is_recent(item.uploaded_date, run_date):
            result.alertable.append(item)
        else:
            result.recorded_only.append(item)
    return result
