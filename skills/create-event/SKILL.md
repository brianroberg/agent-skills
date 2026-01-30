---
name: create-event
description: Create a new calendar event (requires approval)
allowed-tools: Bash
---

# Create Calendar Event

Create a new calendar event. This is a **write operation** that modifies your calendar.

**This skill requires your approval before executing the curl command.**

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

## Usage

When this skill is invoked, construct an EventCreateRequest and run:

```bash
curl -s -X POST "$CALENDAR_AGENT_URL/calendars/primary/events" \
    -H "Content-Type: application/json" \
    -d '{
        "summary": "EVENT_TITLE",
        "start": {
            "dateTime": "START_DATETIME",
            "timeZone": "America/New_York"
        },
        "end": {
            "dateTime": "END_DATETIME",
            "timeZone": "America/New_York"
        },
        "description": "OPTIONAL_DESCRIPTION",
        "location": "OPTIONAL_LOCATION",
        "attendees": [
            {"email": "attendee@example.com"}
        ]
    }' \
    | jq .
```

## Request Fields

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

## Date/Time Formatting

Use ISO 8601 format: `YYYY-MM-DDTHH:MM:SS`

Examples:
- `2026-01-30T14:00:00` (2pm on Jan 30, 2026)
- `2026-01-30T09:30:00` (9:30am on Jan 30, 2026)

## Examples

**Simple 1-hour meeting:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/calendars/primary/events" \
    -H "Content-Type: application/json" \
    -d '{
        "summary": "Team standup",
        "start": {"dateTime": "2026-01-31T09:00:00", "timeZone": "America/New_York"},
        "end": {"dateTime": "2026-01-31T10:00:00", "timeZone": "America/New_York"}
    }' \
    | jq .
```

**Meeting with attendees:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/calendars/primary/events" \
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
    }' \
    | jq .
```

## Parsing Natural Language

When the user provides natural language like "Meeting with team tomorrow at 2pm for 1 hour":

1. Calculate the actual date/time based on current date
2. Convert to ISO 8601 format
3. Calculate end time based on duration (default 1 hour if not specified)
4. Build the structured request

## Security Notes

- Claude Code's approval prompt is the security gate
- Events are created in America/New_York timezone by default
