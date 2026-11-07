---
name: calendar-create-event
description: Create a new calendar event (requires approval)
allowed-tools: Bash
---

# Create Calendar Event

Create a new calendar event. This is a **write operation** that modifies your calendar.

**This skill requires your approval before executing the curl command.**

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

**Token.** When `CALENDAR_AGENT_TOKEN` is set, every call to `$CALENDAR_AGENT_URL` below except `/health` sends it as `Authorization: Bearer <token>`, which `curl` reads from standard input (`-H @-`), so the token is never on a command line. When it is unset or empty, no `Authorization` header is sent. Do not add `-v`, `--trace` or `set -x` to these calls: each one prints the header.

## Read this before you create anything

**A creation blocks while a human approves it.** Every mutation goes through
api-proxy, which holds the request open while a human operator says yes or no.
calendar-agent waits `PROXY_CONFIRM_TIMEOUT` seconds for that answer (default
330s = a 300s operator window plus a 30s margin). **A create that sits there for
four minutes is working normally, not hung.** Do not kill it and do not retry it —
a retry enqueues a *second* approval request and can produce two events. Give curl
`--max-time 420` so it outlives the server's own budget instead of dying first
with an ambiguous transport error.

🚨 **You must also pass `timeout: 450000` on the Bash tool call that runs it.** The
Bash tool's own timeout defaults to **120000 ms** (max 600000) — *shorter than the
operator's approval window*. At the default the tool kills the call at two minutes,
curl never prints its `%{http_code}`, and you are left in exactly the ambiguous
"did it happen?" state this contract exists to remove, while the operator's approval
lands at minute three and the event is created anyway. `--max-time 420` without
`timeout: 450000` buys nothing.

**There are three outcomes, not two:** success, failure, and **unknown**. A create
whose answer never arrived may still be applied minutes later when the operator
approves it. Never report unknown as failure, and never create a second event to
"fix" the first.

## The outcome contract

`POST /calendars/{calendar_id}/events` returns an `EventDetailResponse`:

```json
{"success": true, "event": {"id": "abc123", "status": "confirmed", "...": "..."}, "error": null}
```

**Note the asymmetry with deletion:** `EventDetailResponse` has no `outcome` field
— only `DELETE` (and `/bulk-actions`) carry the tri-state `outcome` enum. So for
creation **the HTTP status is the authoritative signal**, read together with the
body's `success`:

| Status | Outcome | What to do next |
|--------|---------|-----------------|
| `200` + `success: true` | **succeeded** | Report the event id from `.event.id` |
| `403` | **failed** — the operator rejected it, or policy blocked it | Do not retry; tell the user it was rejected |
| `404` | **failed** — no such calendar | Check the calendar id |
| `422` | **failed** — malformed request. Body is a FastAPI validation error, not the envelope | Fix the payload |
| `500` | **failed** — unexpected server fault | Report it |
| `502` | **failed** — upstream proxy or LLM failure | Report it |
| `504` | **UNKNOWN** — no answer before calendar-agent's timeout | Verify by reading the calendar back; the event may still appear |
| curl exit != 0 | **UNKNOWN** — transport timeout or connection failure | Same: verify by reading back |

If a future calendar-agent adds `outcome` to this envelope, prefer it over the
status table: it is the field the server computes, and the table is the
client-side re-derivation of it.

**The status table decides first; the body's shape is only a fallback.** A `422` is
a **definite failure**, not an unknown, even though its FastAPI body
(`{"detail": [...]}`) carries no `success` key: the request was rejected by
validation before it reached the calendar, nothing is outstanding, and the fix is
to correct the payload and send it again. It is the most likely non-200 in
practice — reporting it as "it may still have been created" both misleads the user and
blocks, under the sequencing invariant below, the retry that would actually fix it.

Only for a status *not* in the table above does the body's shape matter: a response
with no boolean `success` key and no recognised status is not calendar-agent's
answer at all (most likely a wrong `CALENDAR_AGENT_URL`). Treat that as unknown.

## Sequencing invariant (binding)

> **Never issue a follow-on or compensating mutation until the prior mutation has
> been observed complete by a read.**

If a create came back `504` or timed out, do **not** create it again, and do not
delete-and-recreate. List the calendar over the event's own time window and see
what is actually there. If the read is inconclusive, wait and re-read; do not act.
Two events where the user asked for one is the failure this rule exists to prevent
(the 2026-08-07 incident).

## Usage

Brian's calendar id is `robergb@dm.org` — **name it explicitly, do not use
`primary`.** `primary` is not an id: it resolves to whichever account the proxy
happens to be authenticated as, so it can silently address a different calendar
than the one intended, and it is not the documented id for this deployment. Path
segments must be URL-encoded, so `robergb@dm.org` becomes `robergb%40dm.org`
inside a URL.

```bash
resp=$(printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 420 -w '\n%{http_code}' \
    -X POST "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events" \
    -H "Content-Type: application/json" \
    -d '{
        "summary": "EVENT_TITLE",
        "start": {"dateTime": "START_DATETIME", "timeZone": "America/New_York"},
        "end": {"dateTime": "END_DATETIME", "timeZone": "America/New_York"},
        "description": "OPTIONAL_DESCRIPTION",
        "location": "OPTIONAL_LOCATION",
        "attendees": [{"email": "attendee@example.com"}]
    }')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ]; then
    echo "UNKNOWN: no response (curl exit $rc). The event may still be created."
else
    echo "HTTP $code"
    printf '%s' "$body" | jq '{success, id: .event.id, status: .event.status, error}'
fi
```

Then branch on `code` per the table above. Only `HTTP 200` with `success: true`
means the event exists.

## Verifying after an unknown outcome

**The read must carry its own status.** `EventsListResponse` is
`{"success": false, "events": [], "error": "..."}` when the read fails, so a bare
`curl -s ... | jq '.events[] | ...'` prints nothing both when the window is genuinely
empty and when the read returned `502`. Those are opposite answers: "none present"
invites a replacement event, "could not read" forbids one. Capture the status:

```bash
vresp=$(printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 35 -w '\n%{http_code}' \
    "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events?time_min=START_ISO&time_max=END_ISO")
vrc=$?
vcode="${vresp##*$'\n'}"
vbody="${vresp%$'\n'*}"
if [ "$vrc" -ne 0 ] || [ "$vcode" != "200" ]; then
    echo "INCONCLUSIVE: could not read the calendar (curl exit $vrc, HTTP ${vcode:-none})"
    printf '%s' "$vbody" | jq -r '.error // .' 2>/dev/null
else
    printf '%s' "$vbody" | jq '.events[] | {id, summary, start, end}'
fi
```

Match on summary and start time over a window that brackets the intended event.
Report what you actually observed, and only the branch you actually reached:

- `200`, one matching event → **present**. Report the create as done.
- `200`, no matching event → **none present**. The create is still `unknown` if it
  timed out; the operator may approve it later. Do not create a replacement.
- anything else (non-200, or curl failed) → **could not read**. Nothing is known.
  Wait and re-read; do not create anything.

## Request fields

| Field | Required | Description |
|-------|----------|-------------|
| `summary` | Yes | Event title |
| `start.dateTime` | Yes | Start time in ISO 8601 format |
| `start.timeZone` | Yes | Timezone (default: America/New_York) |
| `end.dateTime` | Yes | End time in ISO 8601 format |
| `end.timeZone` | Yes | Timezone (default: America/New_York) |
| `description` | No | Event description/notes |
| `location` | No | Event location |
| `attendees` | No | Array of attendee objects with email |

## Date/time formatting

Use ISO 8601 format: `YYYY-MM-DDTHH:MM:SS`

Examples:
- `2026-01-30T14:00:00` (2pm on Jan 30, 2026)
- `2026-01-30T09:30:00` (9:30am on Jan 30, 2026)

## Examples

**Simple 1-hour meeting:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 420 -w '\n%{http_code}' \
    -X POST "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events" \
    -H "Content-Type: application/json" \
    -d '{
        "summary": "Team standup",
        "start": {"dateTime": "2026-01-31T09:00:00", "timeZone": "America/New_York"},
        "end": {"dateTime": "2026-01-31T10:00:00", "timeZone": "America/New_York"}
    }'
```

**Meeting with attendees:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 420 -w '\n%{http_code}' \
    -X POST "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events" \
    -H "Content-Type: application/json" \
    -d '{
        "summary": "Project review",
        "start": {"dateTime": "2026-01-31T14:00:00", "timeZone": "America/New_York"},
        "end": {"dateTime": "2026-01-31T15:00:00", "timeZone": "America/New_York"},
        "location": "Conference Room A",
        "attendees": [
            {"email": "alice@example.com"},
            {"email": "bob@example.com"}
        ]
    }'
```

In both examples the trailing line of output is the HTTP status; read it, do not
discard it. A discarded status is how a non-200 gets read as success. Each of these calls
also needs `timeout: 450000` on the Bash tool call itself — the tool's 120000 ms
default expires before the operator's approval window closes.

## Parsing natural language

When the user provides natural language like "Meeting with team tomorrow at 2pm for 1 hour":

1. Calculate the actual date/time based on the current date
2. Convert to ISO 8601 format
3. Calculate end time based on duration (default 1 hour if not specified)
4. Build the structured request

## Security notes

- Claude Code's approval prompt is a gate on issuing the request; the operator
  approval at the proxy is a second, independent gate on it taking effect.
- Events are created in America/New_York timezone by default.
- Never retry a mutation that timed out. Verify, then decide.
