"""Doc-parity pins for the review-loop process skill.

The skill is a procedure an agent follows before calling a PR ready. These tests pin
the facts that must survive any rewording, because an agent copies them: the
two-round cap, the status-label vocabulary, the REST label command (the `gh pr edit`
form fails on these repos), and the first-line rule for the review-record comment.
"""

import re

from tests.conftest import SKILLS_DIR, parse_frontmatter

SKILL = SKILLS_DIR / "review-loop" / "SKILL.md"


def _text() -> str:
    """The skill body with markdown emphasis stripped, so a pin reads through **bold**."""
    assert SKILL.exists(), f"{SKILL} is missing"
    return SKILL.read_text().replace("**", "")


def test_frontmatter_names_the_skill_and_its_triggers():
    fm = parse_frontmatter(SKILL)
    assert fm.get("name") == "review-loop"
    desc = fm.get("description", "")
    for phrase in ("review loop", "ready"):
        assert phrase in desc, f"description does not mention {phrase!r}"


def test_names_the_two_round_cap():
    text = _text()
    assert re.search(r"\btwo rounds\b", text, re.IGNORECASE), "the two-round cap is not stated"
    assert re.search(r"second round only if", text, re.IGNORECASE), (
        "must say a second round runs only if a fix changed behaviour"
    )


def test_names_the_three_status_labels():
    text = _text()
    for label in ("reviewed:adversarial", "reviewed:partial", "reviewed:none"):
        assert f"`{label}`" in text, f"status label {label} is not named"
    assert re.search(r"`review:(fable|opus)-(xhigh|high|medium)`", text), (
        "a depth label of the form review:<model>-<level> must be shown"
    )


def test_contains_the_rest_label_command_not_the_broken_one():
    text = _text()
    assert re.search(
        r"gh api -X POST repos/\S+/issues/<n>/labels -f 'labels\[\]=", text
    ), "the REST label command (gh api -X POST .../issues/<n>/labels) is missing"
    assert "gh pr edit --add-label" in text, (
        "must name the broken form so an agent does not reach for it"
    )


def test_review_comment_first_line_states_model_effort_and_counts():
    text = _text()
    m = re.search(r"first line[^\n]*", text, re.IGNORECASE)
    assert m, "no sentence about the review comment's first line"
    line = m.group(0).lower()
    for word in ("model", "effort"):
        assert word in line, f"the first-line rule does not mention {word}"
    assert "verifier" in line or "count" in line, "the first-line rule does not mention agent counts"


def test_comment_is_posted_from_a_file_with_capital_f():
    text = _text()
    assert "-F body=@" in text, "the comment/body command must use -F body=@file"
    assert "-f body=@" not in text, "-f body=@file sends the literal string; must not appear"


# ── section 1, the review model (Brian's 2026-11-06 rulings) ──


def _section_one() -> str:
    """Section 1 with wrapping collapsed, so a pin reads across a line break."""
    m = re.search(r"^## 1\. .*?(?=^## 2\. )", _text(), re.MULTILINE | re.DOTALL)
    assert m, "section 1 is missing"
    return re.sub(r"\s+", " ", m.group(0))


def test_depth_table_names_personal_projects_and_opus():
    text = _section_one()
    assert "| Personal side project, any depth |" in text, "the table needs a row for personal side projects"
    assert "Opus with Fable as advisor" in text, "the middle rung is not named"
    assert "Sonnet" not in text.replace("not Sonnet", ""), "Sonnet is no longer a review tier"


def test_fable_row_is_scoped_to_work_projects():
    assert re.search(r"in a service Brian uses daily, in a work project \| Fable pipeline", _section_one())


def test_contained_code_runs_on_opus_alone():
    assert re.search(r"run once, on Opus \(not Sonnet", _section_one()), (
        "the workspace rule is contained code on Opus; a worker does not pick Fable on its own"
    )


def test_opus_of_any_size_needs_no_approval():
    assert re.search(r"Opus review of any size[^.]*needs no approval from Brian", _section_one())


def test_fable_decision_goes_to_the_coordinating_session():
    text = _section_one()
    assert re.search(r"Fable pipeline, send a `question` report to the coordinating session", text)
    assert re.search(r"holds the week's Fable figure and decides", text)
    assert re.search(r"[Ii]f no coordinating session is reachable, state the cost and ask Brian", text)


def test_worker_is_not_told_to_spend_from_the_figure():
    text = _section_one()
    assert "Fable is the default" not in text
    assert not re.search(r"spen[dt]\w*[^.]*figure", text, re.IGNORECASE), (
        "a worker session does not hold the figure, so it cannot spend from it"
    )
    assert re.search(r"worker session does not hold the plan's usage figure", text)


def test_opus_pipeline_cost_line_does_not_wait_for_a_yes():
    assert re.search(r"nothing waits on it", _section_one()), (
        "stating the cost must not read as asking leave for an Opus review"
    )


def test_unknown_repo_counts_as_work():
    assert re.search(r"if you have not been told, count it as work", _section_one(), re.IGNORECASE), (
        "the work/personal table is not public, so a worker needs the default"
    )


def test_middle_rung_is_the_coordinating_sessions_call():
    assert re.search(r"Opus with Fable as advisor[^.]*coordinating session's call", _section_one())


def test_never_silently_downgrade_stays():
    assert re.search(r"never silently downgrade", _section_one(), re.IGNORECASE)
