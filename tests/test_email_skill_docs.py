"""Doc-parity tests for the ``email-*`` skills (agent-skills #11).

The email agent's ``MessageSummary`` carries the sender as ``from_addr`` and
``from_name``; there is no ``from`` field (live ``/openapi.json``, 2026-09-09).
Its read routes (``/search``, ``/summarize``, ``/ask-about``,
``/batch-summarize``) signal failure two ways -- a non-200 status from FastAPI
(405, 422) or an HTTP 200 whose body has ``"success": false`` -- and both look
like "nothing found" to a reader that pipes ``curl`` straight into ``jq``.
These tests pin the skill text to those facts; they read the SKILL.md files
only and make no network calls.
"""

import re
from pathlib import Path

import pytest

from tests.conftest import SKILLS_DIR

EMAIL_SKILLS = sorted(SKILLS_DIR.glob("email-*/SKILL.md"))
READ_SKILLS = [SKILLS_DIR / "email-ask" / "SKILL.md", SKILLS_DIR / "email-triage" / "SKILL.md"]
READ_ENDPOINTS = ("search", "summarize", "ask-about", "batch-summarize")

_ids = lambda p: p.parent.name  # noqa: E731


def _bash_blocks(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", text, re.S)


def _read_curl_blocks(text: str) -> list[str]:
    pattern = r"\$EMAIL_AGENT_URL/(" + "|".join(re.escape(e) for e in READ_ENDPOINTS) + r')"'
    return [b for b in _bash_blocks(text) if "curl" in b and re.search(pattern, b)]


def _curl_invocation(block: str) -> str:
    """The ``curl`` line plus its backslash-continued lines, and nothing after."""
    lines = block.splitlines()
    start = next(i for i, line in enumerate(lines) if "curl" in line)
    span = []
    for line in lines[start:]:
        span.append(line)
        if not line.rstrip().endswith("\\"):
            break
    return "\n".join(span)


# ── 1. No email skill documents a bare `from` field ──


@pytest.mark.parametrize("skill_path", EMAIL_SKILLS, ids=_ids)
def test_no_email_skill_documents_a_bare_from_field(skill_path: Path):
    text = skill_path.read_text()
    backticked = re.findall(r"`from`", text)
    assert not backticked, f"{skill_path.parent.name}: documents a `from` field; the schema has from_addr/from_name"
    in_field_list = re.findall(r"[(,]\s*from\s*[,)]", text)
    assert not in_field_list, (
        f"{skill_path.parent.name}: lists 'from' in a field list ({in_field_list[0]!r}); "
        "the schema has from_addr/from_name"
    )


def test_email_ask_names_the_real_sender_fields():
    text = (SKILLS_DIR / "email-ask" / "SKILL.md").read_text()
    for field in ("from_addr", "from_name", "rfc822_message_id", "thread_id"):
        assert field in text, f"email-ask does not name the MessageSummary field {field!r}"


def test_email_draft_reply_flow_names_the_threading_fields():
    """A reply needs the RFC 2822 Message-ID (`rfc822_message_id`), not the Gmail `id`."""
    text = (SKILLS_DIR / "email-draft" / "SKILL.md").read_text()
    assert "rfc822_message_id" in text, "email-draft does not say which search field feeds in_reply_to"
    assert "from_addr" in text, "email-draft does not say which search field carries the sender to reply to"


# ── 2. The read skills gate every read on HTTP status AND the body's success flag ──


@pytest.mark.parametrize("skill_path", READ_SKILLS, ids=_ids)
def test_read_calls_are_gated_on_status_and_success(skill_path: Path):
    text = skill_path.read_text()
    blocks = _read_curl_blocks(text)
    assert blocks, f"{skill_path.parent.name}: no curl block targets a read endpoint"
    for block in blocks:
        invocation = _curl_invocation(block)
        assert "%{http_code}" in invocation, (
            f"{skill_path.parent.name}: read call discards the HTTP status:\n{invocation}"
        )
        assert not re.search(r"\|\s*jq", invocation), (
            f"{skill_path.parent.name}: read call pipes curl straight into jq "
            f"(the status line would be parsed as JSON):\n{invocation}"
        )
        assert ".success" in block, (
            f"{skill_path.parent.name}: read call never checks the body's success flag "
            f"(a 200 with success:false is a failure, not an empty result):\n{block}"
        )


@pytest.mark.parametrize("skill_path", READ_SKILLS, ids=_ids)
def test_read_skills_explain_the_200_success_false_case(skill_path: Path):
    text = skill_path.read_text()
    assert re.search(r'"success":\s*false|success:\s*false|`success` (is )?false', text), (
        f"{skill_path.parent.name}: does not tell the reader that a 200 can carry success:false"
    )


# ── 3. The email agent's LLM answer is top-level `.answer`, not the calendar agent's `.data.answer` ──


@pytest.mark.parametrize("skill_path", EMAIL_SKILLS, ids=_ids)
def test_no_email_skill_reads_a_nested_data_answer(skill_path: Path):
    text = skill_path.read_text()
    assert ".data.answer" not in text and ".data.summary" not in text, (
        f"{skill_path.parent.name}: reads a `.data.*` path; the email agent's LLMResponse is flat"
    )


@pytest.mark.parametrize("skill_path", READ_SKILLS, ids=_ids)
def test_read_skills_extract_top_level_answer(skill_path: Path):
    text = skill_path.read_text()
    assert re.search(r"jq -r '\.answer'", text), (
        f"{skill_path.parent.name}: no jq filter reads the top-level .answer of /summarize or /ask-about"
    )
