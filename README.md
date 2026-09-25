# Everglades daily policy monitor

Python CLI plus a GitHub Action that emails the Policy team a daily digest.

## What it searches

**Today’s issue only (keyword `Everglades`)**

- [Federal Register](https://www.federalregister.gov/) current issue via the public documents API
- [Congressional Record](https://www.congress.gov/congressional-record) latest issue via the [GovInfo](https://www.govinfo.gov/) API

If there is no new issue that day, the digest says so instead of scanning the archive.

**New since the last successful run (keyword `Everglades`)**

- [SAM.gov](https://sam.gov/) contract opportunities (title search; requires `SAM_API_KEY`)
- [USASpending.gov](https://www.usaspending.gov/) awards modified in the lookback window
- [Acquisition.gov](https://www.acquisition.gov/) site search (new result URLs only)

**New meetings and agendas (no keyword)**

- [SFWMD Public Meetings and Forums](https://www.sfwmd.gov/news-events/meetings)
- [Science Coordination Group](https://www.evergladesrestoration.gov/scg)
- [FWC Commission Meetings](https://myfwc.com/about/commission/commission-meetings/)

The first successful fetch of Acquisition.gov and the three meeting pages **baselines** current listings so the first email is not a dump of historical items. After that, only new meetings, agenda PDFs, or a newly filled FWC agenda page are flagged.

The job always sends email, including an all-clear.

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m everglades_monitor --dry-run
```

`--dry-run` prints the digest and does not send mail or write `data/state.json`.

```bash
PYTHONPATH=src python -m everglades_monitor --date 2026-09-11 --state data/state.json
```

## GitHub Action

[`.github/workflows/daily.yml`](.github/workflows/daily.yml) runs at 18:00 UTC (2:00 PM Eastern) every day, after the typical Federal Register noon-ET posting, and can be triggered manually. GitHub only runs scheduled workflows on the **default branch**, so this starts after merge to `main`. After a successful send it commits updates to `data/state.json`.

If `main` requires pull-request reviews, allow GitHub Actions to push that state commit (or the job will email correctly but fail while saving seen-item state).

### Required secrets

| Secret | Purpose |
| --- | --- |
| `MAIL_TO` | Recipient(s), comma-separated |
| `MAIL_FROM` | From address |
| `SMTP_HOST` | SMTP server |
| `SMTP_PORT` | Usually `587` (STARTTLS) or `465` (SSL) |
| `SMTP_USERNAME` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |

### Recommended / optional secrets

| Secret | Purpose |
| --- | --- |
| `SAM_API_KEY` | [SAM.gov public API key](https://open.gsa.gov/api/get-opportunities-public-api/). Without it, SAM.gov is reported as skipped. |
| `GOVINFO_API_KEY` | GovInfo / api.data.gov key. Falls back to `DEMO_KEY` (rate-limited). |
| `CONGRESS_API_KEY` | Used only if `GOVINFO_API_KEY` is unset. |

## CDMP attachment check

A separate command reads the public EnerGov attachments tab for the tracked CDMP applications in `data/cdmp/applications.json`. It uses a headless browser because the attachments list is rendered by the portal, not returned to a cold API call.

```bash
.venv/bin/playwright install chromium
PYTHONPATH=src .venv/bin/python -m cdmp_monitor scrape
```

That prints the file name, upload date, and notes for CDMP20250017. The config lists seven plans. SharePoint folders are still blank.

```bash
PYTHONPATH=src python -m cdmp_monitor run --log-only
```

`run` checks every plan in the config. New files older than 7 days are stored and not alerted. Newer files are downloaded, summarized, and uploaded when mail and Graph secrets are set. `--log-only` prints the digest and does not email. See [docs/cdmp-onboarding.md](docs/cdmp-onboarding.md). The daily workflow is [`.github/workflows/cdmp-daily.yml`](.github/workflows/cdmp-daily.yml). It stays in log-only mode until that flag is removed.

## Tests

```bash
PYTHONPATH=src pytest
```

CI runs the same mocked tests; they do not hit the live network.
