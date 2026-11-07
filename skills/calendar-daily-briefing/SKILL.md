---
name: calendar-daily-briefing
description: Get a summary of your calendar for today
allowed-tools: Bash
---

# Daily Briefing

Get a summary of your calendar for today. This is a convenience skill that
provides a quick overview of your schedule (calendar only, no email).

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

**Token.** When `CALENDAR_AGENT_TOKEN` is set, every call to `$CALENDAR_AGENT_URL` below except `/health` sends it as `Authorization: Bearer <token>`, which `curl` reads from standard input (`-H @-`), so the token is never on a command line. When it is unset or empty, no `Authorization` header is sent. Do not add `-v`, `--trace` or `set -x` to these calls: each one prints the header.

## Usage

When this skill is invoked, run:

The briefing text is at **`.data.briefing`**. `/prepare-briefing` returns an
`LLMResponse` — `{success, data, error}` — so a filter reading `.briefing` prints
literal `null` on a fully successful `200` and the briefing silently comes back
empty.

```bash
resp=$(printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 120 -X POST "$CALENDAR_AGENT_URL/prepare-briefing" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{
        "briefing_type": "daily",
        "calendar_id": "robergb@dm.org"
    }')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ]; then
    echo "Error: read failed (curl exit $rc, HTTP ${code:-none}) - not an empty calendar"
    printf '%s' "$body" | jq -r '.error // .' 2>/dev/null
else
    printf '%s' "$body" | jq -r '.data.briefing'
fi
```

`data` also carries `briefing_type`, `period` and `event_count`; when the calendar
is clear it is `{"briefing": "Your daily calendar is clear...", "highlights": [],
"preparation_notes": []}` instead. `.data.briefing` is present either way.

## Response Format

The briefing includes:
- Summary of today's events
- Key meetings and their times
- Back-to-back meeting warnings
- Free time blocks
- Preparation reminders

## Difference from Other Briefings

- `/daily-briefing` - Calendar only, today
- `/weekly-briefing` - Calendar only, this week
- `/morning-briefing` - Calendar + Email combined

## Non-200 responses

calendar-agent's HTTP status now agrees with the body instead of always being
`200`: `403` blocked by policy or rejected by the operator, `404` no such calendar
or event, `422` malformed request, `500` unexpected fault, `502` upstream proxy or
LLM failure, `504` no answer in time. For a read, a non-200 means *the answer is
missing*, not that the calendar is empty. Never present a failed read as "nothing
scheduled".

**Do not bolt `-w '\n%{http_code}'` onto a piped `curl ... | jq ...` command.** `jq`
then reads the trailing status line as a second JSON document and dies on it —
`jq: error (at <stdin>:1): Cannot index number with string "events"`, exit status 5,
with whatever it managed to print from the real body left tangled up with the error.
Verified live 2026-09-04 against the deployed agent. Capture the response into a
variable, split off the status, and pipe only the body to `jq`:

```bash
resp=$(curl -sS --max-time 35 -w '\n%{http_code}' "$CALENDAR_AGENT_URL/health")
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ]; then
    echo "READ FAILED (curl exit $rc, HTTP ${code:-none}) - the answer is missing, not empty"
    printf '%s' "$body" | jq -r '.error // .' 2>/dev/null
else
    printf '%s' "$body" | jq .
fi
```

The commands under *Usage* above are already in this form — copy one and change the
URL, the payload and the final `jq` filter. Any remaining `curl -s ... | jq ...`
snippet in this file illustrates request shape only; do not run it as the real read.
