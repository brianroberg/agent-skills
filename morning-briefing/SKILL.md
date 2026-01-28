---
name: morning-briefing
description: Get a comprehensive morning briefing combining calendar and email summaries
allowed-tools: Bash
---

# Morning Briefing

Get a comprehensive morning briefing combining calendar and email summaries.
This demonstrates multi-agent orchestration where Claude Code synthesizes
information from multiple specialist agents.

## Prerequisites

Requires both environment variables:
- `EMAIL_AGENT_URL` - Email agent server
- `CALENDAR_AGENT_URL` - Calendar agent server

## Usage

When this skill is invoked, run both queries and present the combined results:

### Step 1: Get Calendar Summary

```bash
curl -s -X POST "$CALENDAR_AGENT_URL/ask" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "What is on my calendar today? Note any back-to-back meetings or conflicts.", "auto_approve": true}' \
    | jq -r 'if .success then .response else "Calendar error: " + .error end'
```

### Step 2: Get Unread Emails

```bash
curl -s -X POST "$EMAIL_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "is:unread", "folder": "INBOX", "limit": 10}' \
    | jq .
```

Review the returned message stubs (subject, sender, snippet). For any that look urgent or important, get a summary:

```bash
curl -s -X POST "$EMAIL_AGENT_URL/summarize" \
    -H "Content-Type: application/json" \
    -d '{"message_id": "MESSAGE_ID_HERE"}' \
    | jq -r '.answer'
```

### Step 3: Synthesize

After getting both responses, synthesize them into a coherent briefing that:
- Highlights priorities for the day
- Notes any conflicts between meetings and email deadlines
- Suggests time blocks for email responses

## Follow-up Suggestions

After presenting the briefing, the user might ask:
- "Based on that briefing, what should I prioritize today?"
- "Are there any conflicts between my meetings and email deadlines?"
- "Summarize my day in one paragraph"
