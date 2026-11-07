---
name: calendar-summarize-event
description: Get an AI summary of a specific calendar event
allowed-tools: Bash
---

# Summarize Event

Get an AI-powered summary of a specific calendar event. This is a **read-only**
operation that provides insights about an event.

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

**Token.** When `CALENDAR_AGENT_TOKEN` is set, every call to `$CALENDAR_AGENT_URL` below except `/health` sends it as `Authorization: Bearer <token>`, which `curl` reads from standard input (`-H @-`), so the token is never on a command line. When it is unset or empty, no `Authorization` header is sent. Do not add `-v`, `--trace` or `set -x` to these calls: each one prints the header.

## Workflow

This is a two-step process:

### Step 1: Find the Event

First, identify the event to summarize:

**List upcoming events:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events?time_min=START_ISO&time_max=END_ISO" \
    | jq '.events[] | {id, summary, start}'
```

**Or search by keyword:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{"calendar_id": "robergb@dm.org", "filters": {"query": "SEARCH_TERM"}}' \
    | jq '.events[] | {id, summary, start}'
```

### Step 2: Get Summary

Use the event ID to get a summary:

```bash
resp=$(printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 60 -X POST "$CALENDAR_AGENT_URL/summarize" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "event_id": "EVENT_ID",
        "format": "detailed"
    }')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ]; then
    echo "READ FAILED (curl exit $rc, HTTP ${code:-none}) - the answer is missing, not empty"
    printf '%s' "$body" | jq -r '.error // .' 2>/dev/null
else
    printf '%s' "$body" | jq -r '.data.summary'
fi
```

## Request Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `calendar_id` | Yes | - | Calendar holding the event (`robergb@dm.org`) |
| `event_id` | Yes | - | The event ID to summarize |
| `format` | No | `brief` | Summary format: `brief` or `detailed` |

## Response Format

The envelope is `LLMResponse` — `{success, data, error}` — and the summary text is a
**string at `.data.summary`**. There is no top-level `event`, and no
`.summary.content` object:

```json
{
  "success": true,
  "data": {
    "event_id": "abc123",
    "summary": "This is a 2-hour planning meeting for Q1 objectives. Key participants include the leadership team. The agenda covers budget review, team goals, and resource allocation. Based on the description, you should prepare the Q4 metrics report before attending."
  },
  "error": null
}
```

Read it with `jq -r '.data.summary'`. The requested `format` is not echoed back.

## Summary Formats

| Format | Description |
|--------|-------------|
| `brief` | One-sentence overview of the event |
| `detailed` | Full summary including participants, agenda, preparation notes |

## Examples

**Brief summary of next meeting:**
```bash
# Find next meeting
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events?time_min=$(date -Iseconds)&max_results=1" \
    | jq '.events[0].id'

# Get brief summary
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s -X POST "$CALENDAR_AGENT_URL/summarize" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "event_id": "abc123",
        "format": "brief"
    }' \
    | jq -r '.data.summary'
```

**Detailed summary with preparation notes:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s -X POST "$CALENDAR_AGENT_URL/summarize" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "event_id": "abc123",
        "format": "detailed"
    }' \
    | jq .
```

## Use Cases

- "What's my next meeting about?"
- "Summarize my 2pm meeting"
- "What should I prepare for the project review?"
- "Give me details about the team offsite"

## Tips

- Use `format: "detailed"` when you need preparation information
- Combine with `/search-events` to find specific meetings first
- The summary analyzes event description, attendees, and context

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
