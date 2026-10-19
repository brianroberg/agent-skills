"""Tests for ``skills/donor-gifts/scripts/pledges.py`` and the pledge section of its SKILL.md.

The script's pure functions are tested against the response shapes the deployed donor
API returned on 2026-10-19 (``GET /api/v1/contacts?search=`` is a bare list;
``GET /api/v1/pledges`` rows carry a nested ``status`` object; frequencies are
``{id, name, months}``). No network. The doc tests read the SKILL.md only.
"""

import importlib.util
import re
import sys

import pytest

from tests.conftest import SKILLS_DIR

SCRIPT = SKILLS_DIR / "donor-gifts" / "scripts" / "pledges.py"
SKILL = SKILLS_DIR / "donor-gifts" / "SKILL.md"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("pledges", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["pledges"] = m
    spec.loader.exec_module(m)
    return m


FREQS = [
    {"id": 1, "name": "Monthly", "months": 1.0},
    {"id": 2, "name": "Quarterly", "months": 3.0},
    {"id": 4, "name": "Annual", "months": 12.0},
]

# Synthetic records in the live response shapes. No real donor appears in this file.
CONTACTS = [
    {"id": 1002, "file_as": "Example, Chris and Sam", "first_name": "Chris", "last_name": "Example",
     "spouse_first_name": "Sam", "is_organization": False, "org_name": None, "deceased": False},
    {"id": 1001, "file_as": "Example, Pat", "first_name": "Pat", "last_name": "Example",
     "spouse_first_name": None, "is_organization": False, "org_name": None, "deceased": False},
]

PLEDGE = {
    "id": 501, "contact_id": 1001, "amount": "1200.00", "frequency": None, "frequency_id": 4,
    "start_date": "2024-02-01", "end_date": None, "is_active": True,
    "awaiting_first_gift_since": None, "campaign_id": None, "notes": None,
    "status": {"state": "current", "good_until": "2026-12-31", "covered_for_good": False,
               "days_past": -73, "late_bucket": "none", "last_gift_date": "2025-12-15",
               "last_gift_amount": "1250.00", "as_of": "2026-10-19", "behind_periods": 0},
}


# ── response shapes ──


def test_rows_accepts_a_bare_list_and_a_wrapped_list(mod):
    assert mod.rows([{"id": 1}]) == [{"id": 1}]
    assert mod.rows({"items": [{"id": 2}]}) == [{"id": 2}]
    assert mod.rows({"contacts": [{"id": 3}]}) == [{"id": 3}]
    assert mod.rows({"total": 0}) == []


# ── picking the contact ──


def test_pick_contact_exact_file_as_or_first_last_wins_over_a_looser_match(mod):
    assert mod.pick_contact(CONTACTS, "Pat Example")["id"] == 1001
    assert mod.pick_contact(CONTACTS, "example, pat")["id"] == 1001


def test_pick_contact_single_match_is_returned(mod):
    assert mod.pick_contact(CONTACTS[1:], "P. Example")["id"] == 1001


def test_pick_contact_is_none_when_ambiguous_or_empty(mod):
    assert mod.pick_contact(CONTACTS, "Example") is None
    assert mod.pick_contact([], "Nobody") is None


def test_describe_contacts_lists_id_and_label_for_the_caller_to_choose(mod):
    out = mod.describe_contacts(CONTACTS)
    assert "1001" in out and "Example, Pat" in out
    assert "1002" in out and "Example, Chris and Sam" in out


# ── frequency names ──


def test_frequency_name_from_live_table_then_builtin_fallback(mod):
    assert mod.frequency_name(4, FREQS) == "Annual"
    assert mod.frequency_name(9, FREQS) == "Fortnightly"  # not in the live list; built-in table
    assert mod.frequency_name(42, FREQS) == "frequency 42"


def test_builtin_frequency_table_matches_the_live_ids_seen_2026_10_19(mod):
    assert mod.FREQUENCIES == {
        1: "Monthly", 2: "Quarterly", 3: "Semi-Annual", 4: "Annual", 5: "Bi-Monthly",
        6: "Quad-Monthly", 7: "Biennial", 8: "Weekly", 9: "Fortnightly",
    }


# ── the report ──


def test_format_report_one_line_per_pledge_with_status_and_last_gift(mod):
    out = mod.format_report(CONTACTS[1], [PLEDGE], FREQS)
    assert out.splitlines()[0] == "Example, Pat (contact 1001) — 1 pledge"
    body = out.lower()
    assert "$1,200.00 annual" in body
    assert "since 2024-02-01" in body
    assert "current" in body and "good until 2026-12-31" in body
    assert "last gift $1,250.00 on 2025-12-15" in body


def test_format_report_marks_ended_and_awaiting_first_gift_pledges(mod):
    ended = dict(PLEDGE, id=502, is_active=False, end_date="2024-01-01", status=None)
    waiting = dict(PLEDGE, id=503, awaiting_first_gift_since="2026-10-08",
                   status=dict(PLEDGE["status"], state="outstanding", good_until=None))
    out = mod.format_report(CONTACTS[1], [ended, waiting], FREQS)
    assert "— 2 pledges" in out
    assert "ended 2024-01-01" in out
    assert "awaiting first gift since 2026-10-08" in out


def test_format_report_says_so_when_there_are_no_pledges(mod):
    out = mod.format_report(CONTACTS[1], [], FREQS)
    assert out == "Example, Pat (contact 1001) — no pledges on record"


def test_money_formats_api_strings_and_numbers(mod):
    assert mod.money("1200.00") == "$1,200.00"
    assert mod.money(25) == "$25.00"
    assert mod.money(None) == "?"


# ── SKILL.md parity ──


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^(#+) {re.escape(heading)}\n", text, re.MULTILINE)
    assert m, f"no '{heading}' section"
    end = re.compile(rf"^#{{1,{len(m.group(1))}}} ", re.MULTILINE).search(text, m.end())
    return text[m.end(): end.start() if end else len(text)]


def test_skill_has_a_pledges_section_that_leads_with_the_script():
    sec = _section(SKILL.read_text(), "Pledges")
    first_code = re.search(r"```\n(.*?)\n```", sec, re.DOTALL)
    assert first_code and "scripts/pledges.py" in first_code.group(1), "the first command shown must be the script"
    assert "GET /api/v1/pledges?contact_id=" in sec or "/api/v1/pledges?contact_id=" in sec
    assert "/api/v1/pledges/frequencies" in sec


def test_skill_inlines_the_frequency_table():
    sec = _section(SKILL.read_text(), "Pledges")
    for fid, name in {1: "Monthly", 2: "Quarterly", 3: "Semi-Annual", 4: "Annual", 5: "Bi-Monthly",
                      6: "Quad-Monthly", 7: "Biennial", 8: "Weekly", 9: "Fortnightly"}.items():
        assert re.search(rf"\b{fid}\b[^\n]*\b{re.escape(name)}\b", sec), f"frequency {fid} {name} not in the table"
    assert "check the API for current frequency" not in sec.lower()


def test_skill_api_reference_lists_the_pledge_reads():
    ref = _section(SKILL.read_text(), "API Reference")
    assert "GET /api/v1/pledges" in ref
    assert "GET /api/v1/pledges/frequencies" in ref


def test_script_never_prints_the_key():
    src = SCRIPT.read_text()
    assert "DONOR_API_KEY" in src
    # the key VALUE must never reach stdout/stderr: no print or f-string carrying the variable
    assert not re.search(r"print\([^)]*\bapi_key\b", src)
    assert not re.search(r"\{api_key\}", src)
