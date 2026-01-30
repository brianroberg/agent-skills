---
name: summarize-event
description: Get an AI summary of a specific calendar event
allowed-tools: Bash
---

# Summarize Event

Get an AI-powered summary of a specific calendar event. This is a **read-only**
operation that provides insights about an event.

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

## Workflow

This is a two-step process:

### Step 1: Find the Event

First, identify the event to summarize:

**List upcoming events:**
```bash
curl -s "$CALENDAR_AGENT_URL/calendars/primary/events?time_min=START_ISO&time_max=END_ISO" \
    | jq '.events[] | {id, summary, start}'
```

**Or search by keyword:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "SEARCH_TERM"}' \
    | jq '.events[] | {id, summary, start}'
```

### Step 2: Get Summary

Use the event ID to get a summary:

```bash
curl -s -X POST "$CALENDAR_AGENT_URL/summarize" \
    -H "Content-Type: application/json" \
    -d '{
        "event_id": "EVENT_ID",
        "format": "detailed"
    }' \
    | jq .
```

## Request Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `event_id` | Yes | - | The event ID to summarize |
| `format` | No | `brief` | Summary format: `brief` or `detailed` |

## Response Format

```json
{
  "success": true,
  "event": {
    "id": "abc123",
    "summary": "Q1 Planning Meeting"
  },
  "summary": {
    "format": "detailed",
    "content": "This is a 2-hour planning meeting for Q1 objectives. Key participants include the leadership team. The agenda covers budget review, team goals, and resource allocation. Based on the description, you should prepare the Q4 metrics report before attending."
  }
}
```

## Summary Formats

| Format | Description |
|--------|-------------|
| `brief` | One-sentence overview of the event |
| `detailed` | Full summary including participants, agenda, preparation notes |

## Examples

**Brief summary of next meeting:**
```bash
# Find next meeting
curl -s "$CALENDAR_AGENT_URL/calendars/primary/events?time_min=$(date -Iseconds)&max_results=1" \
    | jq '.events[0].id'

# Get brief summary
curl -s -X POST "$CALENDAR_AGENT_URL/summarize" \
    -H "Content-Type: application/json" \
    -d '{
        "event_id": "abc123",
        "format": "brief"
    }' \
    | jq -r '.summary.content'
```

**Detailed summary with preparation notes:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/summarize" \
    -H "Content-Type: application/json" \
    -d '{
        "event_id": "abc123",
        "format": "detailed"
    }' \
    | jq .
```

## Use Cases

- "What's my next meeting about?"
- "Summarize my 2pm meeting"
- "What should I prepare for the project review?"
- "Give me details about the team offsite"

## Tips

- Use `format: "detailed"` when you need preparation information
- Combine with `/search-events` to find specific meetings first
- The summary analyzes event description, attendees, and context
