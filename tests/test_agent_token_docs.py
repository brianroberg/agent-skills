"""Bearer-token pins for every skill that calls the email agent or the calendar agent.

Both services check a bearer token on every route except ``GET /health``. The skills
read the token from ``EMAIL_AGENT_TOKEN`` / ``CALENDAR_AGENT_TOKEN`` and hand it to
``curl`` on standard input, one fixed idiom per service::

    printf '%s' "${EMAIL_AGENT_TOKEN:+Authorization: Bearer $EMAIL_AGENT_TOKEN}" | curl ... -H @- ...

``printf`` is a shell builtin, so the token is in no process's argv. When the variable
is unset or empty, stdin is empty and curl sends no ``Authorization`` header at all; a
bare ``Bearer `` would be refused as a wrong token.

Two kinds of test:

- the idiom itself, run by bash against a local stub server that records the
  ``Authorization`` header it receives (synthetic token only, environment built from
  scratch so a real token in the caller's shell never reaches the stub);
- static checks over the SKILL.md text: every non-``/health`` call carries its own
  service's idiom, each calling skill states the token note, and no call reads a body
  from stdin, runs verbose or traced, or puts an ``Authorization`` header on argv.
"""

import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from tests.conftest import SKILLS_DIR

SYNTHETIC = "test-token-not-real-" + "0" * 24

TOKEN_VAR = {"EMAIL": "EMAIL_AGENT_TOKEN", "CALENDAR": "CALENDAR_AGENT_TOKEN"}

IDIOM = {
    "EMAIL": """printf '%s' "${EMAIL_AGENT_TOKEN:+Authorization: Bearer $EMAIL_AGENT_TOKEN}" | curl""",
    "CALENDAR": """printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl""",
}

NOTE = {
    svc: (
        f"**Token.** When `{var}` is set, every call to `${svc}_AGENT_URL` below except `/health` sends it as "
        "`Authorization: Bearer <token>`, which `curl` reads from standard input (`-H @-`), so the "
        "token is never on a command line. When it is unset or empty, no `Authorization` header is "
        "sent. Do not add `-v`, `--trace` or `set -x` to these calls: each one prints the header."
    )
    for svc, var in TOKEN_VAR.items()
}

SERVICES_UNDER_TEST: tuple[str, ...] = ("EMAIL", "CALENDAR")

_FENCE = re.compile(r"^[ \t]*```[^\n]*\n(.*?)^[ \t]*```", re.MULTILINE | re.DOTALL)
_SERVICE_URL = re.compile(r"\$\{?(EMAIL|CALENDAR)_AGENT_URL\}?([^\"'\s)]*)")


def _fenced_blocks(text: str) -> list[str]:
    return _FENCE.findall(text)


def _quote_state(line: str, state: str | None) -> str | None:
    """The shell quote still open at the end of ``line`` (``'``, ``"`` or None).

    Enough of bash for these blocks: backslash escapes outside single quotes, and a ``#``
    that starts a word outside quotes begins a comment.
    """
    i = 0
    while i < len(line):
        ch = line[i]
        if state is None:
            if ch == "\\":
                i += 2
                continue
            if ch == "#" and (i == 0 or line[i - 1].isspace()):
                break
            if ch in "'\"":
                state = ch
        elif state == "'":
            if ch == "'":
                state = None
        else:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                state = None
        i += 1
    return state


def _curl_spans(lines: list[str]) -> list[tuple[int, int]]:
    """(first, last) line index of each ``curl`` invocation in a block's lines.

    An invocation is the line holding ``curl`` plus the lines it continues onto: by a
    trailing backslash, or because a quoted argument (a multi-line ``-d '{...}'`` body)
    is still open.
    """
    spans = []
    i = 0
    while i < len(lines):
        if not re.search(r"\bcurl\b", lines[i]):
            i += 1
            continue
        j = i
        state = _quote_state(lines[i], None)
        while j + 1 < len(lines) and (state is not None or lines[j].rstrip().endswith("\\")):
            j += 1
            state = _quote_state(lines[j], state)
        spans.append((i, j))
        i = j + 1
    return spans


def service_calls(text: str) -> list[tuple[str, str, str]]:
    """Every ``curl`` invocation in a fenced block that names a service URL variable.

    Returns ``(service, path, invocation)``; ``path`` is the text after the variable up to
    a quote, a space or ``)``.
    """
    calls = []
    for block in _fenced_blocks(text):
        lines = block.splitlines()
        for i, j in _curl_spans(lines):
            invocation = "\n".join(lines[i : j + 1])
            m = _SERVICE_URL.search(invocation)
            if m:
                calls.append((m.group(1), m.group(2), invocation))
    return calls


def stray_service_urls(text: str) -> list[str]:
    """Fenced-block lines that name a service route (``$X_AGENT_URL/...``) outside any curl
    invocation, e.g. a URL kept in a variable: a call made that way escapes the checks."""
    stray = []
    for block in _fenced_blocks(text):
        lines = block.splitlines()
        inside = {k for i, j in _curl_spans(lines) for k in range(i, j + 1)}
        stray += [line.strip() for k, line in enumerate(lines)
                  if k not in inside and re.search(r"\$\{?(EMAIL|CALENDAR)_AGENT_URL\}?/", line)]
    return stray


def _is_health(path: str) -> bool:
    return path.startswith("/health")


SKILL_PATHS = sorted(SKILLS_DIR.glob("*/SKILL.md"))


def _calling_pairs() -> list[tuple[Path, str]]:
    """(skill, service) for each skill with a non-/health call of a service under test."""
    pairs = []
    for path in SKILL_PATHS:
        services = {s for s, p, _ in service_calls(path.read_text()) if not _is_health(p)}
        pairs += [(path, s) for s in SERVICES_UNDER_TEST if s in services]
    return pairs


CALLING_PAIRS = _calling_pairs()
_pair_id = lambda pair: f"{pair[0].parent.name}-{pair[1]}"


# ── the stub server ──


class _Stub:
    def __init__(self):
        self.auth: list[list[str] | None] = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def _answer(self):
                stub.auth.append(self.headers.get_all("Authorization"))
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    self.rfile.read(length)
                body = b'{"success": true, "error": null}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _answer

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/probe"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def stub():
    s = _Stub()
    yield s
    s.close()


def _run_idiom(stub: _Stub, service: str, value: str | None) -> subprocess.CompletedProcess:
    # Built from scratch, not from os.environ: a real token in the caller's shell must
    # never reach the stub or an assertion message.
    env = {"PATH": os.environ["PATH"], "STUB": stub.url}
    if value is not None:
        env[TOKEN_VAR[service]] = value
    return subprocess.run(
        ["bash", "-uc", f'{IDIOM[service]} -sS --max-time 5 -H @- "$STUB"'],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )


# ── the harness and the idiom ──


def test_extractor_finds_brace_form_continuations_and_health():
    md = ('```bash\ncurl -s "${EMAIL_AGENT_URL}/search" -d \'{}\'\n'
          'resp=$(curl -sS \\\n    "$CALENDAR_AGENT_URL/calendars")\n'
          'curl -s "$VIKUNJA_URL/api/v1/info"\n'
          'curl -s "$CALENDAR_AGENT_URL/health"\n```\n')
    calls = service_calls(md)
    assert [(s, p) for s, p, _ in calls] == [("EMAIL", "/search"), ("CALENDAR", "/calendars"), ("CALENDAR", "/health")]



def test_extractor_follows_a_quoted_multiline_body_to_the_url():
    """A body in single quotes spans lines with no backslash; the call goes on after it."""
    md = ("```bash\n"
          "resp=$(curl -sS -X POST -d '{\n"
          '    "q": "x"\n'
          "  }' \\\n"
          '    -v "$EMAIL_AGENT_URL/search")\n'
          "echo done\n"
          "```\n")
    calls = service_calls(md)
    assert [(s, p) for s, p, _ in calls] == [("EMAIL", "/search")]
    assert _VERBOSE.search(calls[0][2]), "a flag after the body must be inside the invocation"
    assert "echo done" not in calls[0][2]


def test_stray_service_urls_finds_a_url_outside_any_curl_invocation():
    md = ('```bash\nURL="$CALENDAR_AGENT_URL/calendars"\ncurl -s "$URL"\n'
          'echo "Calendar ($CALENDAR_AGENT_URL): OK"\ncurl -s "$EMAIL_AGENT_URL/labels"\n```\n')
    assert stray_service_urls(md) == ['URL="$CALENDAR_AGENT_URL/calendars"']


@pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: p.parent.name)
def test_every_service_url_is_inside_a_curl_invocation(skill_path):
    """A route reached any other way (a URL in a variable, say) escapes every check above."""
    stray = stray_service_urls(skill_path.read_text())
    assert not stray, f"{skill_path.parent.name}: service URL outside a curl invocation:\n" + "\n".join(stray)


@pytest.mark.parametrize("service", ["EMAIL", "CALENDAR"])
@pytest.mark.parametrize("value", [None, ""], ids=["absent", "empty"])
def test_idiom_sends_no_header_without_a_token(stub, service, value):
    r = _run_idiom(stub, service, value)
    assert r.returncode == 0, r.stderr
    assert stub.auth == [None]


@pytest.mark.parametrize("service", ["EMAIL", "CALENDAR"])
def test_idiom_sends_exactly_the_token(stub, service):
    r = _run_idiom(stub, service, SYNTHETIC)
    assert r.returncode == 0, r.stderr
    assert stub.auth == [["Bearer " + SYNTHETIC]]


# ── every call of a service under test carries its own token ──


@pytest.mark.parametrize("pair", CALLING_PAIRS, ids=_pair_id)
def test_every_service_call_sends_its_own_token(pair):
    path, service = pair
    other = next(v for s, v in TOKEN_VAR.items() if s != service)
    bad = []
    for s, p, invocation in service_calls(path.read_text()):
        if s != service or _is_health(p):
            continue
        first = invocation.splitlines()[0]
        if IDIOM[service] not in first or not re.search(r"(?<!\S)-H @-(?!\S)", invocation) or other in invocation:
            bad.append(invocation)
    assert not bad, (
        f"{path.parent.name}: {len(bad)} {service} call(s) without the token idiom "
        f"({IDIOM[service]} ... -H @- on the curl line):\n\n" + "\n\n".join(bad)
    )


@pytest.mark.parametrize("pair", CALLING_PAIRS, ids=_pair_id)
def test_skill_states_the_token_note(pair):
    path, service = pair
    assert NOTE[service] in path.read_text(), f"{path.parent.name}: missing the {service} token note:\n{NOTE[service]}"


# ── /health stays headerless; agent-status says what its 200 does not show ──

HEALTH_NOTE = ("`/health` answers without a token, so these two checks send none: "
               "a 200 here shows the service is up, not that a token is accepted.")


def test_agent_status_says_health_checks_prove_nothing_about_tokens():
    text = (SKILLS_DIR / "agent-status" / "SKILL.md").read_text()
    assert HEALTH_NOTE in text
    assert all(path.startswith("/health") for _, path, _ in service_calls(text))


# ── pointers that would lead an agent to a call without the header ──


def _flat(text: str) -> str:
    """Whitespace collapsed, so a pinned sentence may wrap anywhere in the Markdown."""
    return " ".join(text.split())


OPENAPI_NOTE = ("the agent's `/openapi.json`, which needs the token like every route except `/health`: "
                "fetch it with the token idiom, as the commands under *Usage* do.")


def test_search_skill_says_openapi_needs_the_token():
    """The skill sends the agent to its `/openapi.json` for field definitions; that route is checked too."""
    text = (SKILLS_DIR / "calendar-search-events" / "SKILL.md").read_text()
    assert OPENAPI_NOTE in _flat(text)


def test_readme_documents_both_token_variables(readme_content):
    for var in ("EMAIL_AGENT_TOKEN", "CALENDAR_AGENT_TOKEN"):
        assert f"`{var}`" in readme_content
    assert not _ARGV_AUTH.search(readme_content)


# ── invariants over every skill ──

# Anything that makes curl read standard input would compete with the header for it.
_STDIN_READERS = re.compile(
    r"(-d|--data(-binary|-raw|-urlencode|-ascii)?|--json)\s*[\"']?@-"
    r"|(-T|--upload-file)\s+[\"']?-(?![\w-])"
    r"|(-F|--form)\s+[\"']?[^\s\"'=]+=[@<]-"
    r"|(-K|--config)\s+[\"']?-(?![\w-])"
)


@pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: p.parent.name)
def test_no_service_call_reads_another_body_from_stdin(skill_path):
    bad = [inv for _, _, inv in service_calls(skill_path.read_text()) if _STDIN_READERS.search(inv)]
    assert not bad, f"{skill_path.parent.name}: a service call reads stdin, which carries the header:\n\n" + "\n\n".join(bad)


_VERBOSE = re.compile(r"\s(--verbose|--trace(-ascii)?)\b|\s-[A-Za-z]*v[A-Za-z]*(?=\s|$)")
_XTRACE = re.compile(r"\bset\s+(-[A-Za-z]*x[A-Za-z]*|-o\s+xtrace)\b")


@pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: p.parent.name)
def test_no_service_call_is_verbose_or_traced(skill_path):
    text = skill_path.read_text()
    calls = service_calls(text)
    bad = [inv for _, _, inv in calls if _VERBOSE.search(inv)]
    assert not bad, f"{skill_path.parent.name}: a verbose or traced service call prints the header:\n\n" + "\n\n".join(bad)
    if calls:
        traced = [b for b in _fenced_blocks(text) if _XTRACE.search(b)]
        assert not traced, f"{skill_path.parent.name}: a block turns on xtrace, which prints the token:\n\n" + traced[0]


_ARGV_AUTH = re.compile(r"(-H|--header)\s*[\"']?Authorization|--oauth2-bearer", re.IGNORECASE)


@pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: p.parent.name)
def test_no_skill_puts_an_authorization_header_on_the_command_line(skill_path):
    m = _ARGV_AUTH.search(skill_path.read_text())
    assert not m, f"{skill_path.parent.name}: an Authorization header on a command line ({m.group(0)!r}) is visible in ps"


# ── the invariant patterns can fail: each catches a known violation, none flags the idiom ──


@pytest.mark.parametrize(
    "pattern, sample",
    [
        (_STDIN_READERS, 'curl -s -d @- "$EMAIL_AGENT_URL/x"'),
        (_STDIN_READERS, 'curl -s --data-binary @- "$EMAIL_AGENT_URL/x"'),
        (_STDIN_READERS, 'curl -s --json @- "$EMAIL_AGENT_URL/x"'),
        (_STDIN_READERS, 'curl -s -T - "$EMAIL_AGENT_URL/x"'),
        (_STDIN_READERS, 'curl -s -F "file=@-" "$EMAIL_AGENT_URL/x"'),
        (_STDIN_READERS, 'curl -s -K - "$EMAIL_AGENT_URL/x"'),
        (_VERBOSE, 'curl -sv "$EMAIL_AGENT_URL/x"'),
        (_VERBOSE, 'curl --verbose "$EMAIL_AGENT_URL/x"'),
        (_VERBOSE, 'curl --trace-ascii out.txt "$EMAIL_AGENT_URL/x"'),
        (_XTRACE, "set -x"),
        (_XTRACE, "set -exo pipefail"),
        (_XTRACE, "set -o xtrace"),
        (_ARGV_AUTH, 'curl -H "Authorization: Bearer $EMAIL_AGENT_TOKEN" "$EMAIL_AGENT_URL/x"'),
        (_ARGV_AUTH, "curl --header 'authorization: Bearer x' \"$EMAIL_AGENT_URL/x\""),
        (_ARGV_AUTH, 'curl --oauth2-bearer "$EMAIL_AGENT_TOKEN" "$EMAIL_AGENT_URL/x"'),
    ],
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_invariant_patterns_catch_known_violations(pattern, sample):
    assert pattern.search(sample)


@pytest.mark.parametrize("service", ["EMAIL", "CALENDAR"])
def test_invariant_patterns_pass_the_idiom(service):
    call = (f'resp=$({IDIOM[service]} -H @- -sS --max-time 60 -X POST "${service}_AGENT_URL/search" '
            "-w '\\n%{http_code}' -H \"Content-Type: application/json\" -d '{}')")
    assert [p.pattern for p in (_STDIN_READERS, _VERBOSE, _XTRACE, _ARGV_AUTH) if p.search(call)] == []
    assert len(service_calls(f"```bash\n{call}\n```\n")) == 1
