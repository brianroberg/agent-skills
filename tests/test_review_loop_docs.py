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
