---
name: calendar-search-events
description: Search calendar events with structured filters
allowed-tools: Bash
---

# Search Events

Search for calendar events using structured filters. This is a **read-only**
operation for finding specific events.

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

## Usage

When this skill is invoked, run:

```bash
resp=$(curl -sS --max-time 35 -X POST "$CALENDAR_AGENT_URL/search" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "filters": {
            "query": "SEARCH_TERM",
            "time_min": "START_ISO",
            "time_max": "END_ISO",
            "max_results": 10,
            "order_by": "startTime"
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

## Request Fields

`calendar_id` is a required top-level field; every search term goes inside
`filters`. Terms sent at the top level are silently ignored, which returns an
unfiltered result set that looks like a successful search.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `calendar_id` | Yes | - | Calendar to search. Name it explicitly (`robergb@dm.org`); `primary` resolves to whatever account the proxy is authenticated as |
| `filters.query` | No | - | Search term (matches title, description, location) |
| `filters.time_min` | No | - | Start of search range (ISO 8601) |
| `filters.time_max` | No | - | End of search range (ISO 8601) |
| `filters.max_results` | No | `100` | Maximum number of results |
| `filters.order_by` | No | - | Sort order (`startTime` or `updated`) |
| `filters.show_deleted` | No | `false` | Include cancelled events |

## Response Format

Each row is an `EventSummary` — metadata only. `start` and `end` are **flat ISO
strings** (not Google's nested `{dateTime}` objects; an empty string when the row
has no start, e.g. a cancelled recurring-instance stub), and there is **no
`attendees` list** — only `attendee_count`. Attendee addresses and the description
are available only from the single-event detail route
(`GET /calendars/{calendar_id}/events/{event_id}`), which returns the full Google
event.

```json
{
  "success": true,
  "events": [
    {
      "id": "abc123",
      "calendar_id": "robergb@dm.org",
      "summary": "Team Meeting",
      "start": "2026-01-30T14:00:00-05:00",
      "end": "2026-01-30T15:00:00-05:00",
      "location": "Conference Room A",
      "attendee_count": 5,
      "is_all_day": false,
      "status": "confirmed",
      "html_link": "https://www.google.com/calendar/event?eid=YWJjMTIz",
      "organizer_email": "alice@example.com",
      "creator_email": "alice@example.com",
      "calendar_is_organizer": false,
      "calendar_rsvp_state": "accepted"
    }
  ],
  "next_page_token": null,
  "error": null
}
```

The envelope is `EventsListResponse` = `{success, events, next_page_token, error}`.
**There is no `total_count`** — count the array yourself (`jq '.events | length'`).
An empty `events` array with `"success": false` is a *failed read*, not an empty
calendar; see *Non-200 responses* below.

### Row fields

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | Event id — the value the detail, update, delete and `/ask-about` routes take |
| `calendar_id` | string | The calendar this row was read from |
| `summary` | string | Title |
| `start`, `end` | string | Flat ISO 8601; `""` when the row has none |
| `location` | string or null | |
| `attendee_count` | int | Number of attendees. There is no attendee list on this row |
| `is_all_day` | bool | |
| `status` | string or null | Google's event status: `confirmed`, `tentative` or `cancelled`. On `/search`, cancelled rows come back only with `filters.show_deleted: true` |
| `html_link` | string or null | The Google Calendar link |
| `organizer_email` | string or null | The organizer's address as Google reports it. For an event created directly on a group calendar this is the group calendar's own id. `null` when the event carries no organizer |
| `creator_email` | string or null | The account that created the event. Usually equals `organizer_email`; differs on group calendars (organizer = the calendar) and for events moved between calendars. `null` when absent |
| `calendar_is_organizer` | bool | Google's `organizer.self`: whether **the calendar named by `calendar_id`** organizes the event |
| `calendar_rsvp_state` | string | The RSVP of **the calendar's own** attendee entry (Google's `attendees[].self`), classified — see below |

`calendar_rsvp_state` is one of Google's four `responseStatus` values verbatim —
`accepted`, `declined`, `tentative`, `needsAction` — or one of three values this
service defines so the caller never has to decode a missing value:

| Value | Meaning |
|-------|---------|
| `organizer_no_rsvp` | The calendar organizes the event and has nothing to answer — its own event |
| `not_attendee` | The calendar neither organizes the event nor appears in its attendee list (an event copied onto the calendar, or an invitation addressed to a group) |
| `unknown` | A `responseStatus` the service does not recognise; or the calendar's own entry has no `responseStatus` and the calendar is not the organizer; or a stub with no organizer and no attendees |

Only `accepted`, `declined` and `tentative` can be sent back to
`POST /calendars/{calendar_id}/events/{event_id}/respond`; `needsAction` and the
three derived values cannot be echoed to it.

### Whose perspective the `calendar_*` fields report

**The `calendar_*` fields describe the calendar named by `calendar_id`, not
Brian.** Google's `self` flags mark "the calendar on which this copy of the event
appears", so:

- Reading `robergb@dm.org`, `calendar_rsvp_state` is Brian's RSVP and
  `calendar_is_organizer` says whether he organizes it.
- Reading a colleague's calendar, they describe **the colleague** — their RSVP,
  whether they organize it. Brian's own RSVP on that event is not on that row; it
  is knowable only from his own calendar.
- Reading a group calendar, they describe the group calendar: an event created
  directly on one has the calendar itself as organizer (`organizer_email` is the
  calendar's id, `calendar_is_organizer` is `true`); `creator_email` is then the
  person who created it.

`POST .../respond` takes the opposite perspective: it always writes the
**authenticated user's** attendee entry, and for that reason accepts only the
user's own `calendar_id` (`primary` or `robergb@dm.org`) and refuses any other
with `400` without forwarding anything. So to answer "have I responded to X?",
search `robergb@dm.org` and read `calendar_rsvp_state` on the row; a state read
from any other calendar is that calendar's answer, not Brian's.

### Which fields the deployed agent actually sends

`status` and `html_link` are already in the deployed agent's `EventSummary` schema
(checked against the live `/openapi.json` on 2026-09-09). The four
perspective fields — `organizer_email`, `creator_email`, `calendar_is_organizer`,
`calendar_rsvp_state` — arrive with
[calendar-agent PR #11](https://github.com/brianroberg/calendar-agent/pull/11)
(documented here against its head as of 2026-09-09). Until that PR is merged and
deployed, rows do not carry those keys at all. **A row without
`calendar_rsvp_state` means the deployment predates PR #11, not that there is no
RSVP** — check `jq '.events[0] | has("calendar_rsvp_state")'` before reading it,
and fall back to `POST /ask-about` with the event id for RSVP questions on an
older deployment. The authoritative per-field text is the `EventSummary` schema in
the agent's `/openapi.json`.

## Examples

**Search for meetings with a person:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "filters": {"query": "Alice"}
    }' \
    | jq .
```

**Search for project meetings this month:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "filters": {
            "query": "Project Alpha",
            "time_min": "2026-01-01T00:00:00-05:00",
            "time_max": "2026-01-31T23:59:59-05:00"
        }
    }' \
    | jq .
```

**Find recent standup meetings:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "filters": {"query": "standup", "max_results": 5, "order_by": "startTime"}
    }' \
    | jq .
```

**Search by location:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "filters": {"query": "Conference Room B"}
    }' \
    | jq .
```

## Use Cases

- "Find all meetings with John"
- "Search for 1-on-1 meetings"
- "Show me all project review meetings"
- "Find events at the downtown office"

## Tips

- The query searches across event title, description, and location
- RSVP questions ("have I responded to X?"): read `calendar_rsvp_state` on the
  `robergb@dm.org` row — see *Whose perspective* above
- Use time range filters to narrow results to a specific period
- Combine with `/summarize-event` to get details about found events
- Use `/ask-calendar` for more complex natural language queries

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
