---
name: weekly-briefing
description: Get a summary of your calendar for the week
allowed-tools: Bash
---

# Weekly Briefing

Get a summary of your calendar for the current week. This is a convenience skill that
provides an overview of your weekly schedule (calendar only, no email).

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

## Usage

When this skill is invoked, run:

```bash
curl -s -X POST "$CALENDAR_AGENT_URL/prepare-briefing" \
    -H "Content-Type: application/json" \
    -d '{
        "briefing_type": "weekly",
        "calendar_id": "primary"
    }' \
    | jq -r 'if .success then .briefing else "Error: " + .error end'
```

## Response Format

The briefing includes:
- Summary of events for each day of the week
- Key meetings and commitments
- Busiest days highlighted
- Notable gaps or free time blocks
- Any conflicts or back-to-back meeting warnings
- Preparation reminders for important meetings

## Difference from Other Briefings

- `/daily-briefing` - Calendar only, today
- `/weekly-briefing` - Calendar only, this week
- `/morning-briefing` - Calendar + Email combined (today only)

## Use Cases

- "What does my week look like?"
- "Give me an overview of my schedule"
- "What are my commitments this week?"
- "Help me plan my week"
