"""Doc-parity pins for the calendar-* skills (agent-skills issues #2 and #3).

These tests read the SKILL.md files as text and pin the specific facts an agent
cannot guess and has got wrong before:

- #3: `calendar-delete-event` must route deletion through the whitelisted wrapper
  script, not a raw `curl -X DELETE` (which the permission classifier refuses), and
  must carry the wrapper's five exit codes, the Bash-tool timeout the wrapper needs,
  and the never-retry rule on exit 4 (outcome UNKNOWN).
- #2: `calendar-search-events` must document the `EventSummary` row calendar-agent
  actually returns (flat `start`/`end`, `attendee_count`, no `attendees[]`) and the
  organizer / RSVP perspective fields from calendar-agent PR #11, with the
  service-defined RSVP states named so an agent knows they exist.
"""

import re
from pathlib import Path

import pytest

from tests.conftest import SKILLS_DIR

CALENDAR_SKILLS = sorted(SKILLS_DIR.glob("calendar-*/SKILL.md"))
DELETE_SKILL = SKILLS_DIR / "calendar-delete-event" / "SKILL.md"
SEARCH_SKILL = SKILLS_DIR / "calendar-search-events" / "SKILL.md"
ASK_SKILL = SKILLS_DIR / "calendar-ask" / "SKILL.md"

WRAPPER_SCRIPT = "scripts/calendar-delete-event.sh"


def _section(text: str, heading: str) -> str:
    """Return the body of the markdown section whose heading line is `heading`.

    Runs from the heading to the next heading of the same or higher level, so a
    `##` section includes its `###` children but stops at the next `##`.
    """
    lines = text.splitlines()
    level = len(heading) - len(heading.lstrip("#"))
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i
            break
    assert start is not None, f"heading {heading!r} not found"
    body = []
    for line in lines[start + 1 :]:
        m = re.match(r"^(#+)\s", line)
        if m and len(m.group(1)) <= level:
            break
        body.append(line)
    return "\n".join(body)


def _fenced_blocks(text: str) -> list[str]:
    return re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.DOTALL)


# ── Issue #3: calendar-delete-event uses the wrapper script ──


def test_delete_skill_names_the_wrapper_script():
    content = DELETE_SKILL.read_text()
    assert WRAPPER_SCRIPT in content, (
        f"calendar-delete-event must name the whitelisted wrapper {WRAPPER_SCRIPT}"
    )


def test_delete_skill_runs_the_wrapper_not_a_raw_delete():
    """The runnable path is the wrapper; no fenced code block issues `-X DELETE`.

    A bare `curl -X DELETE` against the calendar agent is refused by the
    auto-mode permission classifier, so a code block containing one is a
    command the agent will copy and then fail on.
    """
    content = DELETE_SKILL.read_text()
    offending = [b for b in _fenced_blocks(content) if re.search(r"-X\s+DELETE", b)]
    assert not offending, (
        "calendar-delete-event still has a runnable raw DELETE:\n" + offending[0]
    )
    runnable = [b for b in _fenced_blocks(content) if WRAPPER_SCRIPT in b]
    assert runnable, "no fenced code block invokes the wrapper script"


@pytest.mark.parametrize(
    "code, meaning_pattern",
    [
        ("0", r"succeeded"),
        ("2", r"usage|config"),
        ("3", r"failed"),
        ("4", r"unknown"),
        ("5", r"not_attempted"),
    ],
)
def test_delete_skill_documents_each_exit_code(code: str, meaning_pattern: str):
    """Each wrapper exit code appears as a table row with its meaning on the same line."""
    content = DELETE_SKILL.read_text()
    rows = [
        line
        for line in content.splitlines()
        if re.match(rf"^\|\s*`?{code}`?\s*\|", line)
    ]
    assert rows, f"no table row for exit code {code}"
    assert any(re.search(meaning_pattern, r, re.IGNORECASE) for r in rows), (
        f"exit code {code} row does not say {meaning_pattern!r}: {rows}"
    )


def test_delete_skill_exit_4_forbids_retry_and_compensation():
    """Exit 4 (outcome UNKNOWN) is the case that produced the 2026-08-07 duplicate.

    The row for exit 4 must itself say not to retry and not to compensate, and to
    re-read the event first -- an agent reading only the table must see it.
    """
    content = DELETE_SKILL.read_text()
    rows = [line for line in content.splitlines() if re.match(r"^\|\s*`?4`?\s*\|", line)]
    assert rows, "no table row for exit code 4"
    row = " ".join(rows).lower()
    assert "retry" in row and ("compensat" in row or "create" in row) and "re-read" in row, (
        f"exit 4 row must forbid retry and compensation and require a re-read: {rows}"
    )


def test_delete_skill_requires_bash_tool_timeout_for_the_wrapper():
    """`timeout: 450000` must be stated for the wrapper call, not only for raw curl.

    The Bash tool's 120 s default is shorter than the operator's approval window;
    without this the tool kills the call and the outcome is exactly the ambiguity
    the exit codes exist to remove.
    """
    content = DELETE_SKILL.read_text()
    # Find every paragraph/line that mentions the timeout and require at least one
    # to be about the wrapper script (within 6 lines of naming it).
    lines = content.splitlines()
    timeout_idx = [i for i, l in enumerate(lines) if "450000" in l]
    assert timeout_idx, "calendar-delete-event does not mention timeout 450000"
    near_wrapper = any(
        any(WRAPPER_SCRIPT in lines[j] or "wrapper" in lines[j].lower()
            for j in range(max(0, i - 6), min(len(lines), i + 7)))
        for i in timeout_idx
    )
    assert near_wrapper, "timeout 450000 is not stated in connection with the wrapper script"


def test_delete_skill_maps_transport_failure_to_exit_4():
    content = DELETE_SKILL.read_text().lower()
    assert re.search(r"(transport|curl)[^\n]{0,80}(exit\s*4|unknown)", content), (
        "skill must say a curl transport timeout/failure is reported as exit 4 / unknown"
    )


# ── Issue #2: calendar-search-events documents EventSummary + perspective fields ──


def test_search_skill_response_format_is_an_event_summary_row():
    """The Response Format example must be the flat EventSummary row, not Google's shape."""
    section = _section(SEARCH_SKILL.read_text(), "## Response Format")
    assert '"attendees"' not in section and "responseStatus" not in section, (
        "Response Format still shows Google's attendees[].responseStatus shape"
    )
    assert '"dateTime"' not in section, "Response Format still nests start/end as {dateTime}"
    assert re.search(r'"start":\s*"', section), "start must be a flat ISO string"
    assert re.search(r'"end":\s*"', section), "end must be a flat ISO string"
    assert '"attendee_count"' in section, "EventSummary carries attendee_count, not attendees[]"
    assert '"next_page_token"' in section


PERSPECTIVE_FIELDS = [
    "organizer_email",
    "creator_email",
    "calendar_is_organizer",
    "calendar_rsvp_state",
    "status",
    "html_link",
]


@pytest.mark.parametrize("field", PERSPECTIVE_FIELDS)
def test_search_skill_documents_perspective_field(field: str):
    """Each of the six fields appears both in the example row and in the field table."""
    text = SEARCH_SKILL.read_text()
    section = _section(text, "## Response Format")
    assert f'"{field}"' in section, f"{field} missing from the Response Format example"
    rows = [l for l in text.splitlines() if l.startswith("|") and f"`{field}`" in l]
    assert rows, f"{field} has no field-table row"


@pytest.mark.parametrize("state", ["organizer_no_rsvp", "not_attendee", "unknown", "needsAction"])
def test_search_skill_names_rsvp_states(state: str):
    """The service-defined RSVP states are the ones an agent cannot guess."""
    assert state in SEARCH_SKILL.read_text(), f"calendar_rsvp_state value {state!r} undocumented"


def test_search_skill_says_calendar_fields_describe_the_calendar_read():
    """The perspective point: calendar_* fields describe calendar_id, not Brian."""
    text = SEARCH_SKILL.read_text()
    assert re.search(r"calendar_\*", text) or "calendar_rsvp_state" in text
    assert re.search(r"describe[s]?\s+(\*\*)?the calendar", text, re.IGNORECASE), (
        "search skill must state that the calendar_* fields describe the calendar being read"
    )


def test_search_skill_scopes_perspective_fields_to_calendar_agent_pr_11():
    """Four of the six fields exist only once calendar-agent PR #11 is deployed.

    The skill must say so, so an agent reading a row without them treats absence
    as 'not deployed yet', not as 'no RSVP'.
    """
    text = SEARCH_SKILL.read_text()
    assert re.search(r"calendar-agent[^\n]{0,40}(PR\s*)?#11|PR #11", text), (
        "search skill must name calendar-agent PR #11 as the source of the perspective fields"
    )


def test_ask_skill_routes_rsvp_questions_to_calendar_rsvp_state():
    """'Have I responded to X?' is answered from search/list via calendar_rsvp_state."""
    text = ASK_SKILL.read_text()
    assert "calendar_rsvp_state" in text, (
        "calendar-ask must say RSVP questions read calendar_rsvp_state on robergb@dm.org"
    )


@pytest.mark.parametrize("skill_path", CALENDAR_SKILLS, ids=lambda p: p.parent.name)
def test_no_calendar_skill_documents_attendees_response_status(skill_path: Path):
    """No calendar skill presents attendees[].responseStatus as a list/search field.

    Naming Google's `responseStatus` in prose (as the thing calendar_rsvp_state
    classifies) is fine; a JSON key `"responseStatus":` in a list/search response is
    not, because those rows carry no attendee list at all.
    """
    content = skill_path.read_text()
    assert '"responseStatus":' not in content, (
        f"{skill_path.parent.name} documents a responseStatus key that list/search rows do not carry"
    )
