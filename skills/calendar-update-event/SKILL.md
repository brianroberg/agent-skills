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

## Workflow

This is a two-step process:

### Step 1: Find the Event

First, identify the event to update using list or search:

**List events to find the one to update:**
```bash
curl -s "$CALENDAR_AGENT_URL/calendars/primary/events?time_min=START_ISO&time_max=END_ISO" \
    | jq '.events[] | {id, summary, start, end}'
```

**Or search by keyword:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "SEARCH_TERM"}' \
    | jq '.events[] | {id, summary, start, end}'
```

Extract the `id` field from the event you want to update.

### Step 2: Update the Event

Use PATCH to update only the fields that need to change:

```bash
curl -s -X PATCH "$CALENDAR_AGENT_URL/calendars/primary/events/EVENT_ID" \
    -H "Content-Type: application/json" \
    -d '{
        "summary": "NEW_TITLE",
        "start": {
            "dateTime": "NEW_START_ISO",
            "timeZone": "America/New_York"
        },
        "end": {
            "dateTime": "NEW_END_ISO",
            "timeZone": "America/New_York"
        }
    }' \
    | jq .
```

## Updatable Fields

| Field | Description |
|-------|-------------|
| `summary` | Event title |
| `start` | Start time object with dateTime and timeZone |
| `end` | End time object with dateTime and timeZone |
| `description` | Event description/notes |
| `location` | Event location |
| `attendees` | Array of attendee objects |

Only include fields you want to change. Omitted fields remain unchanged.

## Examples

**Change meeting time:**
```bash
curl -s -X PATCH "$CALENDAR_AGENT_URL/calendars/primary/events/abc123" \
    -H "Content-Type: application/json" \
    -d '{
        "start": {"dateTime": "2026-01-31T15:00:00", "timeZone": "America/New_York"},
        "end": {"dateTime": "2026-01-31T16:00:00", "timeZone": "America/New_York"}
    }' \
    | jq .
```

**Update title and add location:**
```bash
curl -s -X PATCH "$CALENDAR_AGENT_URL/calendars/primary/events/abc123" \
    -H "Content-Type: application/json" \
    -d '{
        "summary": "Updated Meeting Title",
        "location": "Conference Room B"
    }' \
    | jq .
```

**Add attendees:**
```bash
curl -s -X PATCH "$CALENDAR_AGENT_URL/calendars/primary/events/abc123" \
    -H "Content-Type: application/json" \
    -d '{
        "attendees": [
            {"email": "alice@example.com"},
            {"email": "bob@example.com"}
        ]
    }' \
    | jq .
```

## Security Notes

- Claude Code's approval prompt is the security gate
- Always confirm the event details with the user before updating
- Show the current event details and the proposed changes
