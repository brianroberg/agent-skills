---
name: calendar-analyze-schedule
description: Analyze schedule patterns and workload
allowed-tools: Bash
---

# Analyze Schedule

Get AI-powered analysis of your schedule patterns and workload. This is a **read-only**
operation that provides insights without modifying your calendar.

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

**Token.** When `CALENDAR_AGENT_TOKEN` is set, every call to `$CALENDAR_AGENT_URL` below except `/health` sends it as `Authorization: Bearer <token>`, which `curl` reads from standard input (`-H @-`), so the token is never on a command line. When it is unset or empty, no `Authorization` header is sent. Do not add `-v`, `--trace` or `set -x` to these calls: each one prints the header.

## Usage

When this skill is invoked, run:

```bash
resp=$(printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -sS --max-time 60 -X POST "$CALENDAR_AGENT_URL/analyze-schedule" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "time_min": "START_ISO",
        "time_max": "END_ISO",
        "analysis_type": "ANALYSIS_TYPE"
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

## Analysis Types

| Type | Description |
|------|-------------|
| `overview` | General summary of the schedule |
| `workload` | Meeting load analysis (hours per day, back-to-backs) |
| `patterns` | Recurring patterns and habits |
| `conflicts` | Overlapping events and scheduling issues |

## Request Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `calendar_id` | Yes | - | Calendar to analyze. Name it explicitly (`robergb@dm.org`); `primary` resolves to whatever account the proxy is authenticated as |
| `time_min` | Yes | - | Start of analysis range (ISO 8601) |
| `time_max` | Yes | - | End of analysis range (ISO 8601) |
| `analysis_type` | No | `overview` | Type of analysis to perform |

## Examples

**Get overview for this week:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s -X POST "$CALENDAR_AGENT_URL/analyze-schedule" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "time_min": "2026-01-27T00:00:00-05:00",
        "time_max": "2026-01-31T23:59:59-05:00",
        "analysis_type": "overview"
    }' \
    | jq .
```

**Analyze workload for the month:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s -X POST "$CALENDAR_AGENT_URL/analyze-schedule" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "time_min": "2026-01-01T00:00:00-05:00",
        "time_max": "2026-01-31T23:59:59-05:00",
        "analysis_type": "workload"
    }' \
    | jq .
```

**Find scheduling conflicts:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s -X POST "$CALENDAR_AGENT_URL/analyze-schedule" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "time_min": "2026-01-27T00:00:00-05:00",
        "time_max": "2026-02-07T23:59:59-05:00",
        "analysis_type": "conflicts"
    }' \
    | jq .
```

**Identify recurring patterns:**
```bash
printf '%s' "${CALENDAR_AGENT_TOKEN:+Authorization: Bearer $CALENDAR_AGENT_TOKEN}" | curl -H @- -s -X POST "$CALENDAR_AGENT_URL/analyze-schedule" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "robergb@dm.org",
        "time_min": "2026-01-01T00:00:00-05:00",
        "time_max": "2026-01-31T23:59:59-05:00",
        "analysis_type": "patterns"
    }' \
    | jq .
```

## Response Format

The envelope is `LLMResponse` — `{success, data, error}`. **`analysis_type` and the
analysis itself are not top-level fields**; everything is under `data`:

```json
{
  "success": true,
  "data": {
    "time_range": "2026-01-27T00:00:00-05:00 to 2026-01-31T23:59:59-05:00",
    "metrics": {"total_events": 15, "total_hours": 12.5},
    "analysis_type": "workload",
    "insights": "Free-text analysis: back-to-back blocks, busiest day, where the focus time is."
  },
  "error": null
}
```

Two things the old shape got wrong, both of which change how you read it: `insights`
is a single **string**, not an array of bullet points (`jq -r '.data.insights'`, not
`jq '.data.insights[]'`), and `metrics` carries only `total_events` and
`total_hours` — there is no `avg_per_day`, `busiest_day` or `back_to_back_count`
field. Anything of that kind lives inside the prose, written by the model, not as a
field you can index.

## Use Cases

- "How busy is my week looking?"
- "Do I have any scheduling conflicts?"
- "What are my meeting patterns this month?"
- "Am I spending too much time in meetings?"

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
