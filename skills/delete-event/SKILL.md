---
name: delete-event
description: Delete a calendar event (requires approval)
allowed-tools: Bash
---

# Delete Calendar Event

Delete a calendar event. This is a **destructive write operation** that permanently removes an event.

**This skill requires your explicit approval before executing the deletion.**

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

## Workflow

This is a three-step process to ensure safety:

### Step 1: Find the Event

First, identify the event to delete using list or search:

**List events to find the one to delete:**
```bash
curl -s "$CALENDAR_AGENT_URL/calendars/primary/events?time_min=START_ISO&time_max=END_ISO" \
    | jq '.events[] | {id, summary, start, end, attendees}'
```

**Or search by keyword:**
```bash
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "SEARCH_TERM"}' \
    | jq '.events[] | {id, summary, start, end, attendees}'
```

### Step 2: Confirm Event Details

Before deleting, display the full event details to the user and ask for confirmation:

```bash
curl -s "$CALENDAR_AGENT_URL/calendars/primary/events/EVENT_ID" \
    | jq .
```

Present the event summary, time, location, and attendees to the user.

### Step 3: Delete the Event

After user confirmation:

```bash
curl -s -X DELETE "$CALENDAR_AGENT_URL/calendars/primary/events/EVENT_ID" \
    | jq .
```

## Response Format

Successful deletion returns:

```json
{
  "success": true,
  "message": "Event deleted successfully",
  "event_id": "abc123"
}
```

## Examples

**Delete a specific meeting:**
```bash
# Step 1: Find it
curl -s -X POST "$CALENDAR_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "team standup"}' \
    | jq '.events[0] | {id, summary, start}'

# Step 2: Show user the event to confirm (from step 1 output)
# "This will delete 'Team Standup' scheduled for tomorrow at 9am. Proceed?"

# Step 3: Delete after approval
curl -s -X DELETE "$CALENDAR_AGENT_URL/calendars/primary/events/abc123" \
    | jq .
```

## Safety Notes

- **Always confirm** with the user before deleting
- Show complete event details including attendees
- Deletion is permanent - there is no undo
- If the event has attendees, consider warning that cancellation notices may be sent
- Claude Code's approval prompt provides the security gate

## Cancellation vs Deletion

- This endpoint deletes the event entirely
- If the event has attendees, they may receive cancellation notices depending on calendar settings
- For recurring events, consider whether to delete just one instance or the entire series
