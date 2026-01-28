---
name: check-availability
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
curl -s -X POST "$CALENDAR_AGENT_URL/ask" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"When am I free TIMEFRAME_HERE? List specific available time slots.\", \"auto_approve\": true}" \
    | jq -r 'if .success then .response else "Calendar error: " + .error end'
```

Replace `TIMEFRAME_HERE` with the user's requested timeframe (e.g., "tomorrow", "next week", "Friday afternoon").

## Examples

- `/check-availability tomorrow`
- `/check-availability next week`
- `/check-availability Friday afternoon`
