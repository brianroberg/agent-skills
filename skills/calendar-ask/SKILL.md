---
name: calendar-ask
description: Ask a question about your calendar (read-only)
allowed-tools: Bash
---

# Ask Calendar

Ask a question about your calendar. This is a **read-only** operation that
queries your schedule without modifying anything.

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set to your calendar agent server.

## Endpoint Selection

Choose the appropriate endpoint based on the user's question:

| Question Type | Endpoint | Use When |
|---------------|----------|----------|
| List events | `GET /calendars/robergb%40dm.org/events` | "What's on my calendar today/this week?" |
| Search events | `POST /search` | "Find meetings with Alice" or keyword searches |
| RSVP / organizer | `POST /search` or `GET .../events`, then read the row's `calendar_rsvp_state` / `calendar_is_organizer` | "Have I responded to X?", "Who organizes X?" — on `robergb@dm.org` these are Brian's; on another calendar they are **that calendar's**. Rows without these keys predate calendar-agent PR #11: fall back to `POST /ask-about`. Field meanings: `calendar-search-events` skill |
| Ask about event | `POST /ask-about` | "What's the agenda for my 2pm meeting?" |
| Find free time | `POST /find-free-time` | "When am I free tomorrow?" |

## Usage

Every read below captures the HTTP status and checks it before touching the body.
A read that fails returns a well-formed envelope with an empty payload
(`{"success": false, "events": [], "error": "..."}`), so without the status a failed
read is indistinguishable from an empty calendar.

### List Events (for timeframe queries)

```bash
resp=$(curl -sS --max-time 35 -w '\n%{http_code}' \
    "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events?time_min=START_ISO&time_max=END_ISO")
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

Parameters:
- `time_min` - Start of range (ISO 8601, e.g., `2026-01-30T00:00:00-05:00`)
- `time_max` - End of range (ISO 8601)
- `max_results` - Optional, defaults to `100` (verified against the deployed
  `openapi.json`: the `max_results` query parameter on
  `GET /calendars/{calendar_id}/events` has `"default": 100`)

### Search Events (for keyword/filter queries)

```bash
resp=$(curl -sS --max-time 35 -X POST "$CALENDAR_AGENT_URL/search" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "filters": {
            "query": "SEARCH_TERM",
            "time_min": "START_ISO",
            "time_max": "END_ISO",
            "max_results": 10
        }
    }')
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

### Ask About Specific Event

`/ask-about` returns an `LLMResponse` — `{success, data, error}` — and the answer
is at **`.data.answer`**, not `.answer`. (`data` is
`{event_id, question, answer}`; a top-level `.answer` prints literal `null` on a
fully successful call.)

```bash
resp=$(curl -sS --max-time 60 -X POST "$CALENDAR_AGENT_URL/ask-about" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "event_id": "EVENT_ID",
        "question": "USER_QUESTION"
    }')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ]; then
    echo "READ FAILED (curl exit $rc, HTTP ${code:-none}) - the answer is missing, not empty"
    printf '%s' "$body" | jq -r '.error // .' 2>/dev/null
else
    printf '%s' "$body" | jq -r '.data.answer'
fi
```

### Find Free Time

`duration_minutes` is **required** on this endpoint (it is in the deployed
`FindFreeTimeRequest.required` list) — omitting it is a `422`, not a default.

```bash
resp=$(curl -sS --max-time 60 -X POST "$CALENDAR_AGENT_URL/find-free-time" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "time_min": "START_ISO",
        "time_max": "END_ISO",
        "duration_minutes": 30,
        "working_hours_only": true
    }')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ]; then
    echo "READ FAILED (curl exit $rc, HTTP ${code:-none}) - the answer is missing, not empty"
    printf '%s' "$body" | jq -r '.error // .' 2>/dev/null
else
    printf '%s' "$body" | jq '.data'
fi
```

## Examples

- "What's on my schedule today?" → Use GET /calendars/robergb%40dm.org/events with today's date range
- "When am I free tomorrow afternoon?" → Use POST /find-free-time
- "Find all meetings with Project Alpha" → Use POST /search with query
- "Have I responded to the Thursday review?" → POST /search on `robergb@dm.org`, read `calendar_rsvp_state` on the row (see the `calendar-search-events` skill for the values)
- "What's the location for my 3pm meeting?" → First list events, then POST /ask-about

## Security Notes

- The calendar agent ignores instructions found in event descriptions (prompt injection protection)

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
