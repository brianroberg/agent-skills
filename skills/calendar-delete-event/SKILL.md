---
name: calendar-delete-event
description: Delete a calendar event (requires approval)
allowed-tools: Bash
---

# Delete Calendar Event

Delete a calendar event. This is a **destructive write operation** that removes an event.

**This skill requires your explicit approval before executing the deletion.**

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

## Read this before you delete anything

Three things about deletion are counter-intuitive and each one has caused a real
incident. Read them before writing a command.

**1. A deletion blocks while a human approves it.** Every mutation goes through
api-proxy, which holds the request open while a human operator says yes or no.
calendar-agent waits `PROXY_CONFIRM_TIMEOUT` seconds for that answer (default
330s = a 300s operator window plus a 30s margin), then re-reads the event to
verify — another read budget of up to 30s. **A delete that sits there for four
minutes is working normally, not hung.** Do not kill it, do not retry it (a retry
enqueues a *second* approval request for the same operation), and do not report
it as failed. The wrapper script gives curl `--max-time 420` so it outlives the
server's own budget.

🚨 **You must pass `timeout: 450000` on the Bash tool call that runs the wrapper
script.** The Bash tool's own timeout defaults to **120000 ms** (max 600000) —
*shorter than the operator's approval window*. At the default the tool kills the
call at two minutes, the script never prints its outcome line or exit code, and
you are left in exactly the ambiguous "did it happen?" state this contract exists
to remove, while the operator's approval lands at minute three and the deletion
goes through anyway. The script's `--max-time 420` without `timeout: 450000` on
the tool call buys nothing.

**2. There are three outcomes, not two.** Success, failure, and **unknown**. An
unknown deletion may still be applied minutes later when the operator gets to it.
Reporting unknown as "failed" is exactly what produced the 2026-08-07 duplicate-event
incident: a delete was reported failed, a replacement event was created, and then
the original deletion landed after all.

**3. Never compensate before you have verified.** See *Sequencing invariant* below.

## The outcome contract

`DELETE /calendars/{calendar_id}/events/{event_id}` returns an `ActionResponse`:

```json
{"success": true, "outcome": "succeeded", "message": "Event deleted successfully", "error": null}
```

**`outcome` is the authoritative field — read it first.** It is a required field on
`ActionResponse` and takes one of four values:

| `outcome` | Meaning | What to do next |
|-----------|---------|-----------------|
| `succeeded` | calendar-agent re-read the event and it is gone | Report the deletion done |
| `failed` | Definitively did not happen; nothing is outstanding | Report the failure and the `error` text |
| `unknown` | **Outcome not established.** May still be applied when the operator approves it | Do NOT report failure. Do NOT compensate. Verify (below), and re-verify later |
| `not_attempted` | Bulk only: never sent because an earlier operation came back `unknown` | Treat as not done and not attempted; re-run after the earlier one resolves |

`unknown` and `not_attempted` must **never** be collapsed into a failure count or
described to the user as a failure.

**HTTP status is the fallback**, for a calendar-agent old enough not to send
`outcome`, and for responses that are not an envelope at all:

| Status | Meaning |
|--------|---------|
| `200` | Deleted, and confirmed gone by calendar-agent's own re-read |
| `403` | Operator rejected it, or policy blocked it. **Do not retry** — tell the user |
| `404` | No such event or calendar; nothing was deleted (check the id before assuming success) |
| `422` | Malformed request. Body is a FastAPI validation error, not the `{success, outcome}` envelope |
| `500` | Unexpected server fault |
| `502` | Upstream proxy or LLM failure |
| `504` | **Outcome unknown** — no answer in time, or the verifying re-read failed |
| curl exit != 0 | **Outcome unknown** — transport timeout or connection failure |

**Read `outcome` first, then the status table; the body's shape is only a
fallback.** A `422` is a **definite failure**, not an unknown, even though its
FastAPI body (`{"detail": [...]}`) carries no `success`/`outcome` key: the request
was rejected by validation before it reached the calendar, nothing is outstanding,
and the fix is to correct the payload and send it again. Reporting it as "the
deletion may still be applied" both misleads the user and blocks, under the
sequencing invariant below, the retry that would actually fix it.

Only for a status *not* in the table above does the body's shape matter: a response
with no boolean `success` key is then not calendar-agent's answer at all (most
likely a wrong `CALENDAR_AGENT_URL` hitting a bare FastAPI 404, whose status code
tells you nothing about the event). Treat that as unknown.

### If you use `POST /bulk-actions`

No skill in this repo wraps `/bulk-actions`, but if you call it directly: each
entry in `results` carries its own `outcome`, and the envelope carries
`success_count`, `error_count`, **`unknown_count`** and **`not_attempted_count`**.
Report the last two separately — collapsing them into the failure tally is the
same mistake as calling a `504` a failure. Once one operation comes back
`unknown`, calendar-agent stops sending the rest (each would hold the connection
for another full timeout and enqueue another approval) and marks them
`not_attempted`; the batch's status code is the most urgent of its operations,
with `504` outranking every definite failure.

## Sequencing invariant (binding)

> **Never issue a follow-on or compensating mutation until the prior mutation has
> been observed complete by a read.**

Concretely: no replacement event, no re-create, no second delete, no "fix it up"
update while any earlier mutation is `unknown`. Read the event back first. If the
read is inconclusive, the answer is still "wait and re-read", never "act anyway".
This is the control that would have prevented the 2026-08-07 overlapping events.

## Workflow

### Step 1: Find the event

```bash
curl -s --max-time 35 "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events?time_min=START_ISO&time_max=END_ISO" \
    | jq '.events[] | {id, summary, start, end}'
```

Or search by keyword. `calendar_id` is **required** on `POST /search`, and the
search terms go inside `filters`:

```bash
curl -s --max-time 35 -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "filters": {"query": "SEARCH_TERM", "max_results": 10}
    }' \
    | jq '.events[] | {id, summary, start, end}'
```

Brian's calendar id is `robergb@dm.org` — **name it explicitly, do not use
`primary`.** `primary` is not an id: it resolves to whichever account the proxy
happens to be authenticated as, so it can silently address a different calendar
than the one intended, and it is not the documented id for this deployment. Path
segments must be URL-encoded, so `robergb@dm.org` becomes `robergb%40dm.org`
inside a URL.

Both of these finding commands discard the HTTP status. If one prints nothing, that
is **not** evidence the event is absent — a failed read looks identical to an empty
result (`EventsListResponse` is `{"success": false, "events": [], "error": ...}`).
Before concluding an event does not exist, re-run the read in the status-capturing
form used in Step 4.

### Step 2: Confirm the event details with the user

```bash
curl -s --max-time 35 "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events/EVENT_ID" \
    | jq .
```

Present summary, time, location and attendees, and ask before deleting.

### Step 3: Delete — run the wrapper script, standalone, with the long timeout

Deletion goes through the whitelisted wrapper script in Brian's assistant
workspace, **not** a hand-written curl:

```bash
/workspace/scripts/calendar-delete-event.sh EVENT_ID
```

Pass **`timeout: 450000`** on the Bash tool call (see *Read this before you
delete anything*, point 1). Usage is `calendar-delete-event.sh <event_id>
[calendar_id]`; `calendar_id` defaults to `robergb@dm.org` and is URL-encoded by
the script, so pass it raw (`robergb@dm.org`, not `robergb%40dm.org`) if you
name it. The script is tightly scoped: the only request it can issue is
`DELETE /calendars/{calendar_id}/events/{event_id}` on calendar-agent.

**Why the wrapper and not curl.** Claude Code's auto-mode permission classifier
refuses a bare `curl -X DELETE` against the calendar agent as
`[Modify Shared Resources]`; the wrapper carries an explicit allow rule in
`.claude/settings.local.json`. That rule matches the *whole* command string, so
**invoke the script as a standalone Bash command** — wrapping it in a compound
command (`echo …; script …; curl …`) stops the rule matching and the classifier
evaluates the whole line, and may block it. Do the finding (Step 1), the
confirmation (Step 2) and the verification (Step 4) as separate calls.

#### What the wrapper prints and returns

One line, then an exit code that encodes the outcome. The line looks like:

```
DELETE robergb@dm.org event EVENT_ID -> HTTP 200, outcome: succeeded (Event deleted successfully)
```

The script reads `outcome` from the `ActionResponse` envelope (see *The outcome
contract*); only when the body carries no `outcome` string does it fall back to
the HTTP status, as: `200`/`204` → succeeded, `504`/`408` → unknown, any other
`4xx`/`5xx` → failed, anything else → unknown — and a `200` whose body is not
parseable JSON is demoted to unknown, because it proves nothing.

| Exit | Outcome | What to do next |
|------|---------|-----------------|
| `0` | **succeeded** — calendar-agent re-read the event and verified it is gone | Report the deletion done |
| `2` | **usage / config error** — missing `event_id`, or `CALENDAR_AGENT_URL` unset. Nothing was sent | Fix the invocation and run it again |
| `3` | **failed** — definitively not deleted; nothing is outstanding | Read the printed `HTTP <code>` and the message: `403` operator rejected or policy blocked — **do not retry**, tell the user; `404` no such event or calendar — check the id; `422` malformed request — correct it and send again |
| `4` | **UNKNOWN** — the outcome was not established; the delete may still complete after a late operator approval. Also what a curl transport timeout or connection failure maps to | **Do NOT retry and do NOT issue a compensating create.** Re-read the event (Step 4) before doing anything else, and re-read again later if it is still present |
| `5` | **not_attempted** — the envelope said `not_attempted`: never sent, nothing changed | Treat as not done; re-run once whatever blocked it has resolved |

Exit `3` means *definitively not deleted*; it does **not** mean *retry*. Whether a
second attempt is appropriate depends on the status the line reports — a `403`
is the operator saying no, and re-sending it re-asks the same question.

Exit `4` is the code the whole script exists for. On 2026-08-07 a delete reported
as failed completed minutes later when the operator approved it out of band,
while a compensating create had already run, leaving overlapping events. A
transport timeout is treated the same way: curl giving up is **not** evidence the
proxy gave up.

Then branch on the exit code per the table; the outcome and status tables above
explain what the underlying envelope meant.

### Step 4: Verify before you report or act

Whenever the wrapper exits with anything other than `0`, re-read the event. The
re-read, not the delete's own answer, is the evidence:

```bash
vresp=$(curl -sS --max-time 35 -w '\n%{http_code}' \
    "$CALENDAR_AGENT_URL/calendars/robergb%40dm.org/events/EVENT_ID")
vrc=$?
vcode="${vresp##*$'\n'}"
vbody="${vresp%$'\n'*}"
if [ "$vrc" -ne 0 ]; then
    echo "INCONCLUSIVE: could not re-read the event (curl exit $vrc)"
else
    echo "HTTP $vcode"
    printf '%s' "$vbody" | jq '{success, status: .event.status, error}'
fi
```

- HTTP `404`, or HTTP `200` with `.event.status == "cancelled"` → **gone**.
  Google keeps a deleted event readable as `cancelled` for a while before it 404s,
  so both count as gone. (calendar-agent's `error_status_code()` emits only 403,
  404, 500, 502 and 504 — a `410` from this server would itself be the anomaly, so
  do not treat one as evidence of anything.)
- HTTP `200` with any other `.event.status` → **still present**. That is a failure
  only if nothing is outstanding; if the delete came back `unknown`, it is still
  unknown.
- Anything else → **inconclusive**. Report unknown; do not act.

## The envelope behind the exit code

The wrapper does not print the JSON body; it condenses it to the one line and the
exit code above. For reference, the `ActionResponse` it is reading in the exit-4
case looks like:

```json
{
  "success": false,
  "outcome": "unknown",
  "message": "Deletion outcome unknown: no response before timeout and the event is still present; it may yet be applied when the operator approves it. Re-verify before acting",
  "error": "Outcome unknown: No response from proxy after 330s..."
}
```

There is no `event_id` field in this envelope — an older version of this skill
claimed one. The fields are `success`, `outcome`, `message`, `error`; the
wrapper's parenthetical is `error` if set, else `message`.

## Safety notes

- **Always confirm** with the user before deleting; show attendees.
- Deletion is permanent — there is no undo.
- If the event has attendees, cancellation notices may be sent.
- Claude Code's approval prompt is a gate on issuing the request; the operator
  approval at the proxy is a second, independent gate on the request taking effect.
- Never retry a mutation that came back exit `4` / outcome `unknown`. Verify, then decide.

## Cancellation vs deletion

- This endpoint deletes the event entirely.
- For recurring events, consider whether to delete one instance or the whole series.
