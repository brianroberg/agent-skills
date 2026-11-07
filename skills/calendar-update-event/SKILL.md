---
name: calendar-update-event
description: Update an existing calendar event (requires approval)
allowed-tools: Bash
---

# Update Calendar Event

Update an existing calendar event. This is a **write operation** that modifies your calendar.

**This skill requires your approval before executing the update.**

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

**Token.** When `CALENDAR_AGENT_TOKEN` is set, every call to `$CALENDAR_AGENT_URL` below except `/health` sends it as `Authorization: Bearer <token>`, which `curl` reads from standard input (`-H @-`), so the token is never on a command line. When it is unset or empty, no `Authorization` header is sent. Do not add `-v`, `--trace` or `set -x` to these calls: each one prints the header.

## Read this before you update anything

**An update blocks while a human approves it.** Every mutation goes through
api-proxy, which holds the request open while a human operator says yes or no.
calendar-agent waits `PROXY_CONFIRM_TIMEOUT` seconds for that answer (default
330s = a 300s operator window plus a 30s margin). **An update that sits there for
four minutes is working normally, not hung.** Do not kill it and do not retry it —
a retry enqueues a *second* approval request for the same operation. Give curl
`--max-time 420` so it outlives the server's own budget instead of dying first
with an ambiguous transport error.

🚨 **You must also pass `timeout: 450000` on the Bash tool call that runs it.** The
Bash tool's own timeout defaults to **120000 ms** (max 600000) — *shorter than the
operator's approval window*. At the default the tool kills the call at two minutes,
curl never prints its `%{http_code}`, and you are left in exactly the ambiguous
"did it happen?" state this contract exists to remove, while the operator's approval
lands at minute three and the update is applied anyway. `--max-time 420` without
`timeout: 450000` buys nothing.

**There are three outcomes, not two:** success, failure, and **unknown**. An update
whose answer never arrived may still be applied minutes later when the operator
approves it. Never report unknown as failure, and never issue a second write to
"put it back".

## The outcome contract

`PATCH` and `PUT /calendars/{calendar_id}/events/{event_id}` return an
`EventDetailResponse`:

```json
{"success": true, "event": {"id": "abc123", "status": "confirmed", "...": "..."}, "error": null}
```

**Note the asymmetry with deletion:** `EventDetailResponse` has no `outcome` field
— only `DELETE` (and `/bulk-actions`) carry the tri-state `outcome` enum. So for
updates **the HTTP status is the authoritative signal**, read together with the
body's `success`:

| Status | Outcome | What to do next |
|--------|---------|-----------------|
| `200` + `success: true` | **succeeded** | Report the change, echoing the fields from `.event` |
| `403` | **failed** — the operator rejected it, or policy blocked it | Do not retry; tell the user it was rejected |
| `404` | **failed** — no such event or calendar | Check the ids |
| `422` | **failed** — malformed request. Body is a FastAPI validation error, not the envelope | Fix the payload |
| `500` | **failed** — unexpected server fault | Report it |
| `502` | **failed** — upstream proxy or LLM failure | Report it |
| `504` | **UNKNOWN** — no answer before calendar-agent's timeout | Verify by re-reading the event; the change may still land |
| curl exit != 0 | **UNKNOWN** — transport timeout or connection failure | Same: verify by re-reading |

If a future calendar-agent adds `outcome` to this envelope, prefer it over the
status table: it is the field the server computes, and the table is the
client-side re-derivation of it. When it appears, `unknown` and `not_attempted`
must never be reported as failure.

**The status table decides first; the body's shape is only a fallback.** A `422` is
a **definite failure**, not an unknown, even though its FastAPI body
(`{"detail": [...]}`) carries no `success` key: the request was rejected by
validation before it reached the calendar, nothing is outstanding, and the fix is
to correct the payload and send it again. It is the most likely non-200 in
practice — reporting it as "it may still have been applied" both misleads the user and
blocks, under the sequencing invariant below, the retry that would actually fix it.

Only for a status *not* in the table above does the body's shape matter: a response
with no boolean `success` key and no recognised status is not calendar-agent's
answer at all (most likely a wrong `CALENDAR_AGENT_URL`). Treat that as unknown.

## Sequencing invariant (binding)

> **Never issue a follow-on or compensating mutation until the prior mutation has
> been observed complete by a read.**

If an update came back `504` or timed out, do **not** re-send it, revert it, or
delete and recreate the event. Re-read the event and compare the fields you
intended to change. If the read is inconclusive, wait and re-read; do not act.
Compensating for an outcome that was never established is what produced the
2026-08-07 duplicate-event incident.

## Workflow

Brian's calendar id is `robergb@dm.org` — **name it explicitly, do not use
`primary`.** `primary` is not an id: it resolves to whichever account the proxy
happens to be authenticated as, so it can silently address a different calendar
than the one intended, and it is not the documented id for this deployment. Path
segments must be URL-encoded, so `robergb@dm.org` becomes `robergb%40dm.org`
inside a URL.

### Step 1: Find the event

```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s --max-time 35 "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events?time_min=START_ISO&time_max=END_ISO" \
    | jq '.events[] | {id, summary, start, end}'
```

Or search by keyword. `calendar_id` is **required** on `POST /search`, and the
search terms go inside `filters`:

```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s --max-time 35 -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "filters": {"query": "SEARCH_TERM", "max_results": 10}
    }' \
    | jq '.events[] | {id, summary, start, end}'
```

Extract the `id` field from the event you want to update.

Both of these finding commands discard the HTTP status. If one prints nothing, that
is **not** evidence the event is absent — a failed read looks identical to an empty
result (`EventsListResponse` is `{"success": false, "events": [], "error": ...}`).
Before concluding an event does not exist, re-run the read in the status-capturing
form used in Step 3.

### Step 2: Update the event, capturing status and body

Use `PATCH` to change only the fields that need to change:

```bash
resp=$(printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 420 -w '\n%{http_code}' \
    -X PATCH "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events/EVENT_ID" \
    -H "Content-Type: application/json" \
    -d '{
        "summary": "NEW_TITLE",
        "start": {"dateTime": "NEW_START_ISO", "timeZone": "America/New_York"},
        "end": {"dateTime": "NEW_END_ISO", "timeZone": "America/New_York"}
    }')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ]; then
    echo "UNKNOWN: no response (curl exit $rc). The update may still be applied."
else
    echo "HTTP $code"
    printf '%s' "$body" | jq '{success, summary: .event.summary, start: .event.start, end: .event.end, error}'
fi
```

Then branch on `code` per the table above. Only `HTTP 200` with `success: true`
means the change took effect.

### Step 3: Verify after an unknown outcome

The read must carry its own status: `EventDetailResponse` is
`{"success": false, "event": null, "error": "..."}` on failure, so a bare
`curl -s ... | jq ...` cannot tell "unchanged" from "not read".

```bash
vresp=$(printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 35 -w '\n%{http_code}' \
    "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events/EVENT_ID")
vrc=$?
vcode="${vresp##*$'\n'}"
vbody="${vresp%$'\n'*}"
if [ "$vrc" -ne 0 ] || [ "$vcode" != "200" ]; then
    echo "INCONCLUSIVE: could not read the event (curl exit $vrc, HTTP ${vcode:-none})"
    printf '%s' "$vbody" | jq -r '.error // .' 2>/dev/null
else
    printf '%s' "$vbody" | jq '{success, summary: .event.summary, start: .event.start, end: .event.end, status: .event.status}'
fi
```

Compare against what you intended, and report only the branch you reached — "the
change is present", "the event is unchanged", or "could not read the event" — not
what you assume happened. An unchanged event after a `504` is still **unknown**, not failed:
the operator may approve it later.

## Updatable fields

| Field | Description |
|-------|-------------|
| `summary` | Event title |
| `start` | Start time object with dateTime and timeZone |
| `end` | End time object with dateTime and timeZone |
| `description` | Event description/notes |
| `location` | Event location |
| `attendees` | Array of attendee objects |

Only include fields you want to change. Omitted fields remain unchanged under
`PATCH`. `PUT` is a full replacement — prefer `PATCH` unless you mean to replace.

## Examples

**Change meeting time:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 420 -w '\n%{http_code}' \
    -X PATCH "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events/abc123" \
    -H "Content-Type: application/json" \
    -d '{
        "start": {"dateTime": "2026-01-31T15:00:00", "timeZone": "America/New_York"},
        "end": {"dateTime": "2026-01-31T16:00:00", "timeZone": "America/New_York"}
    }'
```

**Update title and add location:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 420 -w '\n%{http_code}' \
    -X PATCH "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events/abc123" \
    -H "Content-Type: application/json" \
    -d '{
        "summary": "Updated Meeting Title",
        "location": "Conference Room B"
    }'
```

**Add attendees:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 420 -w '\n%{http_code}' \
    -X PATCH "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events/abc123" \
    -H "Content-Type: application/json" \
    -d '{
        "attendees": [
            {"email": "alice@example.com"},
            {"email": "bob@example.com"}
        ]
    }'
```

In each example the trailing line of output is the HTTP status; read it, do not
discard it. A discarded status is how a non-200 gets read as success. Each of these calls
also needs `timeout: 450000` on the Bash tool call itself — the tool's 120000 ms
default expires before the operator's approval window closes.

## Security notes

- Claude Code's approval prompt is a gate on issuing the request; the operator
  approval at the proxy is a second, independent gate on it taking effect.
- Always confirm the event details with the user before updating: show the current
  event and the proposed change.
- Never retry a mutation that timed out. Verify, then decide.
