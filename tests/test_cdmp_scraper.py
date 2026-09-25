from pathlib import Path

import pytest

from cdmp_monitor.config import find_application, load_applications
from cdmp_monitor.models import Attachment
from cdmp_monitor.scraper import parse_attachment_card, plan_attachments_url

ROOT = Path(__file__).resolve().parents[1]
APPLICATIONS = ROOT / "data" / "cdmp" / "applications.json"

CARD = """
Attachment

Traffic Impact Study v3.pdf

Uploaded: 08/20/2026

Notes: Other
"""

SAME_NAME_LATER = """
Attachment

CDMP20250017 MDFR.pdf

Uploaded: 03/31/2026

Notes: Comment Response Letter
"""

SAME_NAME_EARLIER = """
Attachment

CDMP20250017 MDFR.pdf

Uploaded: 08/27/2025

Notes: MDSO
"""

DROP_ZONE = """
click or drag files
Add Attachment
Supported:
"""


def test_plan_url_uses_the_attachments_tab():
    url = plan_attachments_url("c9762e73-fa94-4c81-be60-9d14a52dbd8c")
    assert url.endswith("/plan/c9762e73-fa94-4c81-be60-9d14a52dbd8c?tab=attachments")
    assert url.startswith("https://energov.miamidade.gov/EnerGov_Prod/SelfService#")


def test_parse_attachment_card_reads_name_date_and_notes():
    attachment = parse_attachment_card(CARD)
    assert attachment == Attachment(
        file_name="Traffic Impact Study v3.pdf",
        uploaded_date="08/20/2026",
        notes="Other",
    )


def test_same_filename_on_different_dates_stays_distinct():
    later = parse_attachment_card(SAME_NAME_LATER)
    earlier = parse_attachment_card(SAME_NAME_EARLIER)
    assert later is not None and earlier is not None
    assert later.file_name == earlier.file_name
    assert later.key != earlier.key


def test_upload_drop_zone_is_not_an_attachment():
    assert parse_attachment_card(DROP_ZONE) is None


def test_seed_config_has_the_seven_plans_and_the_confirmed_number():
    applications = load_applications(APPLICATIONS)
    assert len(applications) == 7
    confirmed = find_application(applications, cdmp_number="CDMP20250017")
    assert confirmed.plan_guid == "c9762e73-fa94-4c81-be60-9d14a52dbd8c"
    assert confirmed.sharepoint_folder_url == ""
    assert {item.cdmp_number for item in applications} == {
        "CDMP20210005",
        "CDMP20250016",
        "CDMP20250019",
        "CDMP20250017",
        "CDMP20230013",
        "CDMP20230016",
        "CDMP20230017",
    }


def test_unknown_cdmp_number_is_rejected():
    applications = load_applications(APPLICATIONS)
    with pytest.raises(ValueError):
        find_application(applications, cdmp_number="CDMP00000000")
