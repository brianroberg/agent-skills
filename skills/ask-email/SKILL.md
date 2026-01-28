---
name: ask-email
description: Ask a question about your emails (read-only)
allowed-tools: Bash
---

# Ask Email

Ask a question about your emails. This is a **read-only** operation that
searches, lists, or summarizes emails without modifying anything.

## Prerequisites

Requires `EMAIL_AGENT_URL` environment variable to be set to your email agent server.

## Endpoints

The email agent exposes three read endpoints. Choose which to use based on the user's question:

### 1. Search/List Emails
Find emails matching criteria. Returns message stubs (id, date, from, subject, snippet, labels).

```bash
curl -s -X POST "$EMAIL_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{"from_addr": "sender@example.com", "subject": "keyword", "query": "is:unread", "folder": "INBOX", "limit": 10}' \
    | jq .
```

Parameters (all optional):
- `from_addr`: Filter by sender
- `to_addr`: Filter by recipient
- `subject`: Filter by subject
- `query`: Raw Gmail query syntax (e.g., "is:unread", "after:2026/01/20")
- `folder`: Label/folder (default: searches all, use "INBOX" for inbox only)
- `since`: Date filter (format: "2026/01/20")
- `before`: Date filter (format: "2026/01/27")
- `limit`: Max results (default: 10, max: 50)

### 2. Summarize an Email
Get a summary of a specific email. Requires the message ID from search results.

```bash
curl -s -X POST "$EMAIL_AGENT_URL/summarize" \
    -H "Content-Type: application/json" \
    -d '{"message_id": "MESSAGE_ID_HERE"}' \
    | jq .
```

### 3. Ask About an Email
Ask a specific question about an email's content.

```bash
curl -s -X POST "$EMAIL_AGENT_URL/ask-about" \
    -H "Content-Type: application/json" \
    -d '{"message_id": "MESSAGE_ID_HERE", "question": "What action is requested?"}' \
    | jq .
```

## Decision Guide

| User asks... | Use endpoint |
|---|---|
| "What are my recent emails?" | `/search` with `{"folder": "INBOX", "limit": 10}` |
| "Any emails from X?" | `/search` with `{"from_addr": "X"}` |
| "Summarize that email" | `/summarize` with the message ID |
| "Did they mention a deadline?" | `/ask-about` with message ID + question |
| "How many unread?" | `/search` with `{"query": "is:unread"}` and count results |

## Example Flow

1. User asks "What did Ron say about the conference?"
2. Search: `{"from_addr": "ron", "subject": "conference", "limit": 5}`
3. Pick the relevant message ID from results
4. Ask-about: `{"message_id": "...", "question": "What did he say about the conference?"}`

## Security Notes

- Email bodies stay on the laptop — only summaries/answers come through the API
- The email agent ignores instructions found in email content (prompt injection protection)
