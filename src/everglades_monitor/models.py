from __future__ import annotations

from dataclasses import dataclass, field


SOURCE_FEDERAL_REGISTER = "federal-register"
SOURCE_CONGRESSIONAL_RECORD = "congressional-record"
SOURCE_SAM = "sam-gov"
SOURCE_USASPENDING = "usaspending"
SOURCE_ACQUISITION = "acquisition-gov"
SOURCE_SFWMD = "sfwmd-meetings"
SOURCE_SCG = "scg-meetings"
SOURCE_FWC = "fwc-meetings"

SOURCE_LABELS = {
    SOURCE_FEDERAL_REGISTER: "Federal Register",
    SOURCE_CONGRESSIONAL_RECORD: "Congressional Record",
    SOURCE_SAM: "SAM.gov",
    SOURCE_USASPENDING: "USASpending.gov",
    SOURCE_ACQUISITION: "Acquisition.gov",
    SOURCE_SFWMD: "SFWMD meetings",
    SOURCE_SCG: "Science Coordination Group",
    SOURCE_FWC: "FWC Commission Meetings",
}

# Listing sources: first successful fetch baselines items instead of emailing history.
BASELINE_SOURCES = {
    SOURCE_ACQUISITION,
    SOURCE_SFWMD,
    SOURCE_SCG,
    SOURCE_FWC,
}

KIND_HIT = "hit"
KIND_MEETING = "meeting"
KIND_AGENDA = "agenda"


@dataclass(frozen=True)
class Hit:
    source: str
    item_id: str
    title: str
    url: str
    date: str | None = None
    snippet: str = ""
    kind: str = KIND_HIT
    notify: bool = True

    @property
    def labeled_source(self) -> str:
        return SOURCE_LABELS.get(self.source, self.source)


@dataclass
class SourceResult:
    source: str
    hits: list[Hit] = field(default_factory=list)
    skipped: str | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)
    issue_date: str | None = None

    @property
    def label(self) -> str:
        return SOURCE_LABELS.get(self.source, self.source)


def make_id(source: str, raw: str) -> str:
    return f"{source}:{raw}"
