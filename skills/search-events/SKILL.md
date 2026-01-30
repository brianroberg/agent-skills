---
name: search-events
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
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "SEARCH_TERM",
        "time_min": "START_ISO",
        "time_max": "END_ISO",
        "max_results": 10,
        "order_by": "startTime"
    }' \
    | jq .
```

## Request Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `query` | Yes | - | Search term (matches title, description, location) |
| `time_min` | No | - | Start of search range (ISO 8601) |
| `time_max` | No | - | End of search range (ISO 8601) |
| `max_results` | No | `25` | Maximum number of results |
| `order_by` | No | `startTime` | Sort order (`startTime` or `updated`) |

## Response Format

```json
{
  "success": true,
  "events": [
    {
      "id": "abc123",
      "summary": "Team Meeting",
      "start": {
        "dateTime": "2026-01-30T14:00:00-05:00"
      },
      "end": {
        "dateTime": "2026-01-30T15:00:00-05:00"
      },
      "location": "Conference Room A",
      "attendees": [
        {"email": "alice@example.com", "responseStatus": "accepted"}
      ]
    }
  ],
  "total_count": 1
}
```

## Examples

**Search for meetings with a person:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "Alice"
    }' \
    | jq .
```

**Search for project meetings this month:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "Project Alpha",
        "time_min": "2026-01-01T00:00:00-05:00",
        "time_max": "2026-01-31T23:59:59-05:00"
    }' \
    | jq .
```

**Find recent standup meetings:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "standup",
        "max_results": 5,
        "order_by": "startTime"
    }' \
    | jq .
```

**Search by location:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "Conference Room B"
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
- Use time range filters to narrow results to a specific period
- Combine with `/summarize-event` to get details about found events
- Use `/ask-calendar` for more complex natural language queries
