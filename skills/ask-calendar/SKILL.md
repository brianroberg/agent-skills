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

## Usage

When this skill is invoked, run the following bash command with the user's question:

```bash
curl -s -X POST "$CALENDAR_AGENT_URL/ask" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"USER_QUESTION_HERE\", \"auto_approve\": true}" \
    | jq -r 'if .success then .response else "Error: " + .error end'
```

Replace `USER_QUESTION_HERE` with the user's actual question.

## Examples

- "What's on my schedule today?"
- "When am I free tomorrow afternoon?"
- "Do I have any meetings this week?"
- "Find me a 30 minute slot tomorrow"

## Security Notes

- The calendar agent ignores instructions found in event descriptions (prompt injection protection)
