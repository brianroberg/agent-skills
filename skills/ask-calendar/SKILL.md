---
name: ask-calendar
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
| List events | `GET /calendars/primary/events` | "What's on my calendar today/this week?" |
| Search events | `POST /search` | "Find meetings with Alice" or keyword searches |
| Ask about event | `POST /ask-about` | "What's the agenda for my 2pm meeting?" |
| Find free time | `POST /find-free-time` | "When am I free tomorrow?" |

## Usage

### List Events (for timeframe queries)

```bash
curl -s "$CALENDAR_AGENT_URL/calendars/primary/events?time_min=START_ISO&time_max=END_ISO" \
    | jq .
```

Parameters:
- `time_min` - Start of range (ISO 8601, e.g., `2026-01-30T00:00:00-05:00`)
- `time_max` - End of range (ISO 8601)
- `max_results` - Optional, defaults to 50

### Search Events (for keyword/filter queries)

```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "SEARCH_TERM",
        "time_min": "START_ISO",
        "time_max": "END_ISO",
        "max_results": 10
    }' \
    | jq .
```

### Ask About Specific Event

```bash
curl -s -X POST "$CALENDAR_AGENT_URL/ask-about" \
    -H "Content-Type: application/json" \
    -d '{
        "event_id": "EVENT_ID",
        "question": "USER_QUESTION"
    }' \
    | jq -r '.answer'
```

### Find Free Time

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

## Examples

- "What's on my schedule today?" → Use GET /calendars/primary/events with today's date range
- "When am I free tomorrow afternoon?" → Use POST /find-free-time
- "Find all meetings with Project Alpha" → Use POST /search with query
- "What's the location for my 3pm meeting?" → First list events, then POST /ask-about

## Security Notes

- The calendar agent ignores instructions found in event descriptions (prompt injection protection)
