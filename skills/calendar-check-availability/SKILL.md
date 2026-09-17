---
name: calendar-check-availability
description: Check calendar availability for a given timeframe
allowed-tools: Bash
---

# Check Availability

Check calendar availability for scheduling. Useful when someone asks to meet
and you want to propose times.

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

## Usage

When this skill is invoked with a timeframe, run:

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

## Request Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `calendar_id` | Yes | - | Calendar to check. Name it explicitly (`robergb@dm.org`); `primary` resolves to whatever account the proxy is authenticated as |
| `time_min` | Yes | - | Start of search range (ISO 8601) |
| `time_max` | Yes | - | End of search range (ISO 8601) |
| `duration_minutes` | **Yes** | - | Minimum slot duration needed. **Required** — it is in `FindFreeTimeRequest.required` on the deployed spec (`[calendar_id, time_min, time_max, duration_minutes]`); omitting it returns `422`, it does not default to 30 |
| `working_hours_only` | No | `true` | Only return 9am-5pm slots |

## Response Format

The envelope is `LLMResponse` — `{success, data, error}`. **There is no top-level
`free_slots`**; everything is under `data`:

```json
{
  "success": true,
  "data": {
    "available_slots": [
      {"start": "2026-01-30T10:00:00-05:00", "end": "2026-01-30T11:30:00-05:00", "duration_minutes": 90},
      {"start": "2026-01-30T14:00:00-05:00", "end": "2026-01-30T17:00:00-05:00", "duration_minutes": 180}
    ],
    "suggestions": "Free-text recommendation of the best 2-3 slots, with reasoning.",
    "duration_requested": 30
  },
  "error": null
}
```

`suggestions` is **prose, not a list**, and `available_slots` holds at most the top
five slots. Read them with `jq '.data.available_slots'` and
`jq -r '.data.suggestions'`.

**One shape change to expect:** when no slot in the range is long enough, `data` is
`{"suggestions": [], "reasoning": "No slots available with at least N minutes free."}`
instead — `available_slots` is absent and `suggestions` is an empty array. Handle
both, and note this is a *successful* `200`: it means "no room", not "read failed".

## Examples

**Check availability tomorrow:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/find-free-time" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "time_min": "2026-01-31T00:00:00-05:00",
        "time_max": "2026-01-31T23:59:59-05:00",
        "duration_minutes": 30,
        "working_hours_only": true
    }' \
    | jq .
```

**Find 1-hour slots next week:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/find-free-time" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "time_min": "2026-02-02T00:00:00-05:00",
        "time_max": "2026-02-06T23:59:59-05:00",
        "duration_minutes": 60,
        "working_hours_only": true
    }' \
    | jq .
```

**Check afternoon availability (including outside work hours):**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/find-free-time" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "time_min": "2026-01-31T12:00:00-05:00",
        "time_max": "2026-01-31T20:00:00-05:00",
        "duration_minutes": 30,
        "working_hours_only": false
    }' \
    | jq .
```

## Date Calculation

When user says "tomorrow", "next week", etc.:

1. Calculate actual dates based on current date
2. Use ISO 8601 format with a UTC offset (`YYYY-MM-DDTHH:MM:SS±HH:MM`). **Derive the
   offset for the date in question; do not hard-code it.** America/New_York is `-04:00`
   from mid-March to early November (EDT) and `-05:00` the rest of the year (EST); a
   window written with the wrong one is shifted by an hour. The container's `date`
   resolves it:

   ```bash
   TZ=America/New_York date -d '2026-09-14 00:00' -Iseconds     # 2026-09-14T00:00:00-04:00
   TZ=America/New_York date -d '2026-09-14 23:59:59' -Iseconds  # 2026-09-14T23:59:59-04:00
   ```
3. For full day, use `00:00:00` to `23:59:59` (with that day's offset). All-day
   events match any window that overlaps their date, evaluated in the calendar's own
   time zone (`America/New_York` for Brian's calendars), so a local-offset day window
   returns exactly that day's all-day events. A UTC-midnight window (`00:00:00Z` to
   `23:59:59Z`) starts at 20:00 local the evening before and so also returns the
   previous day's all-day events.

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
