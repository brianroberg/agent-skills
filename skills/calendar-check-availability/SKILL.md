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
curl -s -X POST "$CALENDAR_AGENT_URL/find-free-time" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "primary",
        "time_min": "START_ISO",
        "time_max": "END_ISO",
        "duration_minutes": 30,
        "working_hours_only": true
    }' \
    | jq .
```

## Request Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `calendar_id` | No | `primary` | Calendar to check |
| `time_min` | Yes | - | Start of search range (ISO 8601) |
| `time_max` | Yes | - | End of search range (ISO 8601) |
| `duration_minutes` | No | `30` | Minimum slot duration needed |
| `working_hours_only` | No | `true` | Only return 9am-5pm slots |

## Response Format

Returns an array of available time slots:

```json
{
  "success": true,
  "free_slots": [
    {
      "start": "2026-01-30T10:00:00-05:00",
      "end": "2026-01-30T11:30:00-05:00",
      "duration_minutes": 90
    },
    {
      "start": "2026-01-30T14:00:00-05:00",
      "end": "2026-01-30T17:00:00-05:00",
      "duration_minutes": 180
    }
  ]
}
```

## Examples

**Check availability tomorrow:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/find-free-time" \
    -H "Content-Type: application/json" \
    -d '{
        "calendar_id": "primary",
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
        "calendar_id": "primary",
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
        "calendar_id": "primary",
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
2. Use ISO 8601 format with timezone: `YYYY-MM-DDTHH:MM:SS-05:00`
3. For full day, use `00:00:00` to `23:59:59`
