"""Doc-parity pins for ``skills/donor-sync/SKILL.md``.

- The write rule proposed for ``donor-contact-manage`` in agent-skills PR #15: send a write
  when Brian asked for that specific change, and if the permission check refuses it, do
  not retry it another way. Write out the exact request and hand it to Brian. The sync
  trigger is the case on record: the assistant's ``POST /api/v1/sync/trigger`` was
  refused by its own permission rules on 2026-09-22 (sr-assistant#67).
- ``POST /api/v1/export/mailing-list`` is human-only: ``require_human_read`` in
  sr-assistant ``api/export.py`` returns 403 "Human access required" to agent keys, and
  sr-assistant#51 records the 403 against the assistant's key.

These tests read the SKILL.md only; they make no network calls.
"""

import re

from tests.conftest import SKILLS_DIR

SKILL = SKILLS_DIR / "donor-sync" / "SKILL.md"


def _text() -> str:
    return SKILL.read_text()


def _section(text: str, heading: str) -> str:
    """The body under `heading`, up to the next heading of the same or a higher level."""
    m = re.search(rf"^(#+) {re.escape(heading)}\n", text, re.MULTILINE)
    assert m, f"no '{heading}' section"
    end = re.compile(rf"^#{{1,{len(m.group(1))}}} ", re.MULTILINE).search(text, m.end())
    body = text[m.end() : end.start() if end else len(text)]
    assert body.strip(), f"the '{heading}' section is empty"
    return body


def _norm(text: str) -> str:
    return " ".join(text.split())


def test_write_rule_is_stated():
    section = _norm(_section(_text(), "Writes and the permission check"))
    assert "Send the write when Brian asked for that specific change" in section, "the write rule is missing"
    assert re.search(
        r"If the permission check refuses a write, do not retry it another way\**\s*\([^)]*\)\. "
        r"Write out the exact request\W+route, ids and body\W+and hand it to Brian",
        section,
    ), "does not say to write out a refused request and hand it to Brian, rather than work around it"


def test_sync_trigger_carries_the_refusal_on_record():
    section = _norm(_section(_text(), "Trigger a Sync"))
    assert "sr-assistant#67" in section, "the sync trigger section does not cite the 2026-09-22 refusal"
    assert "not by the API" in section, "does not say the refusal came from the permission rules, not the API"
    assert "Writes and the permission check" in section, "does not point at the write rule"
    assert re.search(r"(?i)ask Brian to run the sync", section), "does not hand a refused trigger to Brian"
    assert re.search(r"(?i)Sync Now", section), "does not name the web page's Sync Now button"


def test_mailing_list_export_is_human_only():
    text = _text()
    section = _norm(_section(text, "Mailing List"))
    assert "403" in section and "Human access required" in section, (
        "does not say the export returns 403 'Human access required' to the agent key"
    )
    assert re.search(r"(?i)do not retry it another way", section) and re.search(r"(?i)ask Brian to run the export", section), (
        "does not say to hand the export to Brian rather than work around the 403"
    )
    assert "human key only" in _section(text, "API Reference"), "the API Reference does not mark the export human-only"


# sr-assistant api/sync.py at b9d1f13: trigger_sync and trigger_address_sync are plain `def`
# routes that run the import inside the request and return its counts -- no background task.
def test_sync_triggers_are_not_described_as_asynchronous():
    text = _norm(_text())
    assert "asynchronously" not in text and "job status" not in text, (
        "describes the sync trigger as returning a job status for an asynchronous import"
    )
    for heading in ("Trigger a Sync", "Pull Addresses from DonorHub"):
        assert "inside the request" in _norm(_section(_text(), heading)), f"'{heading}' does not say the import runs inside the request"


# sr-assistant#46 (live 2026-09-24) added the contact address routes that donor-contact-manage documents;
# services/donorhub/sync.py sync_addresses creates an address only when the contact has no primary one.
SUBRESOURCE_HEADING = "Addresses, emails and phones (sub-resource routes)"


def test_address_pull_points_at_the_subresource_routes():
    section = _norm(_section(_text(), "Pull Addresses from DonorHub"))
    for stale in ("only address-related route", "cannot be created or edited", "cannot be corrected from here"):
        assert stale not in section, f"still says '{stale}'; sr-assistant#46 added address write routes"
    assert "donor-contact-manage" in section and SUBRESOURCE_HEADING in section, (
        "does not point at donor-contact-manage's address routes for corrections"
    )
    assert f"### {SUBRESOURCE_HEADING}" in (SKILLS_DIR / "donor-contact-manage" / "SKILL.md").read_text(), (
        "points at a donor-contact-manage section that does not exist"
    )
    assert re.search(r"only \*?creates\*? an address for a contact with no primary address", section), (
        "does not say the pull creates an address only when the contact has no primary one"
    )


# sr-assistant api/sync.py at b9d1f13: get_pending_items names the only three item types src/ writes.
PENDING_TYPES = ("error_skipped_donation", "unmatched_donor", "address_conflict")


def test_pending_item_types_are_the_ones_the_sync_writes():
    section = _norm(_section(_text(), "Pending Sync Items"))
    for kind in PENDING_TYPES:
        assert f"`{kind}`" in section, f"does not name the {kind} item type"
    for invented in ("duplicate contacts", "unmatched gifts"):
        assert invented not in section, f"lists '{invented}', a type the sync never writes"


def test_unmatched_donor_is_not_a_missing_contact():
    """sync_addresses matches a DonorHub row to an ExternalDonor link, not to a contact."""
    section = _norm(_section(_text(), "Pull Addresses from DonorHub"))
    assert "no matching contact" not in section, "calls an unmatched donor a missing contact"
    assert re.search(r"(?i)don't create a contact", section), "does not warn against creating a contact to match it"


def test_resolving_a_skipped_donation_is_not_bookkeeping():
    """resolve_pending_item: resolving an error_skipped_donation releases the donation watermark."""
    section = _norm(_section(_text(), "Resolve Pending Item"))
    assert "watermark" in section and "missing gift" in section, (
        "does not say resolving an error_skipped_donation releases the watermark and can accept a missing gift"
    )


def test_sync_status_fields_are_the_api_fields():
    section = _norm(_section(_text(), "Check Sync Status"))
    for field in ("`connected`", "`last_sync`", "`recent_syncs`"):
        assert field in section, f"does not name the {field} field"
    assert "watermark" in section, "does not say last_sync is the donation watermark, not the last run time"
    assert "disconnected" not in section, "describes connected as a three-state value; it is a boolean"
