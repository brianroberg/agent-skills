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
