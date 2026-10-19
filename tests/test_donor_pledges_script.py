"""Tests for ``skills/donor-gifts/scripts/pledges.py`` and the pledge section of its SKILL.md.

The script's pure functions are tested against the response shapes the deployed donor
API returned on 2026-10-19 (``GET /api/v1/contacts?search=`` is a bare list;
``GET /api/v1/pledges`` rows carry a nested ``status`` object; frequencies are
``{id, name, months}``). No network. The doc tests read the SKILL.md only.
"""

import datetime as dt
import importlib.util
import re
import sys

import pytest

from tests.conftest import SKILLS_DIR
from tests.conftest import section as _section

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


def test_pick_contact_single_hit_needs_a_whole_word_match(mod):
    # r2-2: the API search is a substring match, so a lone hit is not proof
    assert mod.pick_contact(CONTACTS[1:], "Pat Example")["id"] == 1001
    assert mod.pick_contact(CONTACTS[1:], "example")["id"] == 1001
    patterson = [{"id": 1003, "file_as": "Patterson, Lee", "first_name": "Lee", "last_name": "Patterson"}]
    assert mod.pick_contact(patterson, "Pat") is None
    assert mod.pick_contact(CONTACTS[1:], "P. Example") is None


def test_search_term_is_the_last_word_of_the_query(mod):
    # r2-1: GET /contacts?search= is one %term% match over the name fields
    assert mod.search_term("Pat Example") == "example"
    assert mod.search_term("Example, Pat") == "pat"
    assert mod.search_term("Example") == "example"
    assert mod.search_term("") == ""


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


# ── review round 1 (2026-10-19): behaviour pinned by the fixes ──

TODAY = dt.date(2026, 10, 19)


def test_future_end_date_is_a_running_fixed_term_pledge_not_an_ended_one(mod):
    # r1 finding 2: a pledge with end_date ahead of today still shows its live status
    p = dict(PLEDGE, end_date="2027-06-30", status=dict(PLEDGE["status"], state="behind", good_until=None, behind_periods=2))
    out = mod.format_report(CONTACTS[1], [p], FREQS, today=TODAY)
    assert "ended" not in out
    assert "behind" in out and "through 2027-06-30" in out


def test_past_end_date_or_inactive_is_ended(mod):
    past = dict(PLEDGE, end_date="2026-01-31")
    inactive = dict(PLEDGE, id=502, end_date=None, is_active=False)
    out = mod.format_report(CONTACTS[1], [past, inactive], FREQS, today=TODAY)
    assert "ended 2026-01-31" in out and "ended (date not recorded)" in out


def test_report_flags_a_deceased_contact(mod):
    out = mod.format_report(dict(CONTACTS[1], deceased=True), [PLEDGE], FREQS, today=TODAY)
    assert out.splitlines()[0].endswith("— 1 pledge") and "(deceased)" in out.splitlines()[0]


def test_describe_contacts_says_when_the_list_may_be_cut_off(mod):
    # r1 finding 5: the search is capped; say so instead of presenting the list as complete
    out = mod.describe_contacts(CONTACTS, limit=2)
    assert "first 2" in out
    assert "first" not in mod.describe_contacts(CONTACTS, limit=100)


def test_frequency_table_is_only_fetched_for_an_unknown_id(mod):
    # r1 finding 8: no third request when every frequency_id is in the built-in table
    assert mod.needs_frequency_fetch([PLEDGE]) is False
    assert mod.needs_frequency_fetch([dict(PLEDGE, frequency_id=42)]) is True
    assert mod.needs_frequency_fetch([]) is False


def test_notes_branch_is_gone_list_rows_carry_no_notes(mod):
    # r1 finding 10
    out = mod.format_report(CONTACTS[1], [dict(PLEDGE, notes="Increased from $200")], FREQS, today=TODAY)
    assert "notes:" not in out


# ── main(): the exit-code contract the SKILL.md documents ──


def _run(mod, monkeypatch, argv, responses, capsys):
    """Drive main() with a fake fetch_json: responses maps a path prefix to a payload or an ApiError."""
    calls = []

    def fake(path, params, api_key):
        calls.append((path, params))
        for prefix, payload in responses.items():
            if path.startswith(prefix):
                if isinstance(payload, Exception):
                    raise payload
                return payload
        raise AssertionError(f"unexpected GET {path}")

    monkeypatch.setattr(mod, "fetch_json", fake)
    monkeypatch.setenv("DONOR_API_KEY", "k")
    code = mod.main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err, calls


def test_main_searches_by_surname_and_picks_the_exact_name_with_two_requests(mod, monkeypatch, capsys):
    # r2-8: the fake answers the surname search with every Example, as the live API would
    code, out, _err, calls = _run(mod, monkeypatch, ["Pat Example"],
                                  {"/api/v1/contacts": CONTACTS, "/api/v1/pledges": [PLEDGE]}, capsys)
    assert code == 0 and "1 pledge" in out
    assert [c[0] for c in calls] == ["/api/v1/contacts", "/api/v1/pledges"]
    assert calls[0][1]["search"] == "example"


def test_main_contact_id_not_found_is_exit_2_not_an_outage(mod, monkeypatch, capsys):
    # r1 finding 7
    code, out, _err, _calls = _run(mod, monkeypatch, ["--contact-id", "900001"],
                                 {"/api/v1/contacts/900001": mod.ApiError("HTTP 404 on GET /api/v1/contacts/900001", status=404)}, capsys)
    assert code == 2 and "no contact 900001" in out


def test_main_api_failure_is_exit_3(mod, monkeypatch, capsys):
    code, _out, err, _calls = _run(mod, monkeypatch, ["Pat Example"],
                                   {"/api/v1/contacts": mod.ApiError("GET /api/v1/contacts failed: timed out")}, capsys)
    assert code == 3 and "donor API" in err


def test_main_ambiguous_name_lists_candidates_and_exits_2(mod, monkeypatch, capsys):
    code, out, _err, _calls = _run(mod, monkeypatch, ["Example"], {"/api/v1/contacts": CONTACTS}, capsys)
    assert code == 2 and "1001" in out and "1002" in out


def test_main_rejected_key_is_exit_2_with_a_replace_hint(mod, monkeypatch, capsys):
    # r2-4
    code, _out, err, _calls = _run(mod, monkeypatch, ["--contact-id", "900001"],
                                   {"/api/v1/contacts/900001": mod.ApiError("HTTP 401 on GET /api/v1/contacts/900001", status=401)}, capsys)
    assert code == 2 and "DONOR_API_KEY was rejected" in err


def test_fetch_json_turns_a_cut_connection_into_an_api_error(mod, monkeypatch):
    # r2-3: IncompleteRead / RemoteDisconnected are not URLError subclasses
    import http.client

    class Boom:
        def __init__(self, *a, **k): pass
        def __enter__(self): raise http.client.IncompleteRead(b"")
        def __exit__(self, *a): return False

    monkeypatch.setattr(mod._OPENER, "open", lambda *a, **k: Boom())
    with pytest.raises(mod.ApiError):
        mod.fetch_json("/api/v1/pledges", None, "k")


def test_main_without_a_key_is_exit_2(mod, monkeypatch, capsys):
    monkeypatch.delenv("DONOR_API_KEY", raising=False)
    assert mod.main(["Pat Example"]) == 2


# ── security review (2026-10-19): the key must not follow a redirect or travel over http ──


def test_redirects_are_refused(mod):
    import urllib.request
    h = mod._NoRedirect()
    with pytest.raises(mod.ApiError):
        h.redirect_request(urllib.request.Request("https://a.example/x"), None, 302, "Found", {}, "https://b.example/y")


def test_non_https_base_url_is_refused_before_any_request(mod, monkeypatch, capsys):
    monkeypatch.setenv("DONOR_API_KEY", "k")
    monkeypatch.setattr(mod, "BASE_URL", "http://donor-management.fly.dev")
    monkeypatch.setattr(mod, "fetch_json", lambda *a: (_ for _ in ()).throw(AssertionError("must not be called")))
    assert mod.main(["Pat Example"]) == 2
    assert "https" in capsys.readouterr().err


def test_skill_example_contact_id_is_outside_the_production_range():
    sec = _section(SKILL.read_text(), "Pledges")
    ids = [int(x) for x in re.findall(r"--contact-id (\d+)", sec)]
    assert ids and all(i >= 900000 for i in ids), "example ids must not be real contact ids"


def test_skill_command_lines_use_the_deployed_absolute_path():
    # r1 finding 1: the agent copies the line verbatim and runs it from /workspace
    sec = _section(SKILL.read_text(), "Pledges")
    cmds = re.findall(r"^python3 (\S+pledges\.py)", sec, re.MULTILINE)
    assert cmds and all(c.startswith("/home/claude/.claude/skills/agent-skills/") for c in cmds), cmds


def test_skill_points_awaiting_first_gift_explanation_at_tools_md_not_donor_sync():
    # r1 finding 3: donor-sync has no such explanation
    sec = _section(SKILL.read_text(), "Pledges")
    assert "TOOLS.md" in sec
    sync = (SKILLS_DIR / "donor-sync" / "SKILL.md").read_text()
    assert "awaiting" in sync or "donor-sync` for why" not in sec


def test_donor_sync_pledge_reads_agree_with_donor_gifts():
    # r1 finding 4: same endpoint, same documented default and frequency count
    sync = (SKILLS_DIR / "donor-sync" / "SKILL.md").read_text()
    assert "active_only=false" in sync
    assert "Add `?active_only=true` to show only active pledges" not in sync
    assert "monthly, quarterly, semi-annual, annual." not in sync
