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

When this skill is invoked, run the following bash command with the event description:

```bash
curl -s -X POST "$CALENDAR_AGENT_URL/ask" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"Create a calendar event: EVENT_DESCRIPTION_HERE\", \"auto_approve\": true}" \
    | jq -r 'if .success then .response else "Error: " + .error end'
```

Replace `EVENT_DESCRIPTION_HERE` with the user's event description.

## Examples

- "Meeting with team tomorrow at 2pm for 1 hour"
- "Lunch with Sarah on Friday at noon"
- "Doctor appointment next Tuesday at 10am"
- "Project review meeting on 2026-01-25 from 3pm to 4pm"

## Security Notes

- Claude Code's approval prompt is the security gate - the agent runs with auto_approve=true because Claude Code already approved the action
- Events are created in America/New_York timezone by default
