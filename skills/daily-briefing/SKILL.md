---
name: daily-briefing
description: Get a summary of your calendar for today
allowed-tools: Bash
---

# Daily Briefing

Get a summary of your calendar for today. This is a convenience skill that
provides a quick overview of your schedule (calendar only, no email).

## Prerequisites

Requires `CALENDAR_AGENT_URL` environment variable to be set.

## Usage

When this skill is invoked, run:

```bash
curl -s -X POST "$CALENDAR_AGENT_URL/ask" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Give me a briefing on my schedule for today. Include any important meetings, note if I have back-to-back meetings, and mention any gaps where I have free time.", "auto_approve": true}' \
    | jq -r 'if .success then .response else "Error: " + .error end'
```

## Difference from /morning-briefing

- `/daily-briefing` - Calendar only
- `/morning-briefing` - Calendar + Email combined
