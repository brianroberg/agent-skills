---
name: email-draft
description: Create, view, update, or delete email drafts (requires approval)
allowed-tools: Bash
---

# Email Drafts

Manage email drafts in Gmail. These are **write operations** that modify your drafts folder.

**This skill requires your approval before executing curl commands.**

## Prerequisites

Requires `EMAIL_AGENT_URL` environment variable to be set.

## Endpoints

### 1. Create a Draft

Create a new draft from structured fields.

```bash
curl -s -X POST "$EMAIL_AGENT_URL/drafts/create" \
    -H "Content-Type: application/json" \
    -d '{"to": ["recipient@example.com"], "subject": "Subject here", "body": "Email body here"}' \
    | jq .
```

Fields:
- `to` (required): List of recipient email addresses
- `subject` (required): Email subject line
- `body` (required): Plain text email body
- `cc`: List of CC recipients
- `bcc`: List of BCC recipients
- `in_reply_to`: Message-ID of the email being replied to (for threading)
- `references`: List of Message-IDs in the conversation thread (for threading)

### 2. List Drafts

List all drafts with preview information.

```bash
curl -s "$EMAIL_AGENT_URL/drafts" | jq .
```

### 3. Get Draft Details

Get the full content of a specific draft.

```bash
curl -s "$EMAIL_AGENT_URL/drafts/DRAFT_ID_HERE" | jq .
```

### 4. Update a Draft

Replace the content of an existing draft.

```bash
curl -s -X POST "$EMAIL_AGENT_URL/drafts/DRAFT_ID_HERE/update" \
    -H "Content-Type: application/json" \
    -d '{"to": ["recipient@example.com"], "subject": "Updated subject", "body": "Updated body"}' \
    | jq .
```

### 5. Delete a Draft

Permanently delete a draft.

```bash
curl -s -X DELETE "$EMAIL_AGENT_URL/drafts/DRAFT_ID_HERE" | jq .
```

## Decision Guide

| User asks... | Use endpoint |
|---|---|
| "Draft an email to X about Y" | Create draft with `to`, `subject`, `body` |
| "Reply to that email" | Create draft with `in_reply_to` and `references` from the original message |
| "Show me my drafts" | List drafts |
| "What's in that draft?" | Get draft details |
| "Change the draft to say..." | Update draft |
| "Delete that draft" | Delete draft |

## Example Flows

### Simple draft
1. User: "Draft an email to alice@example.com about the project update"
2. Create: `{"to": ["alice@example.com"], "subject": "Project update", "body": "..."}`
3. Return the draft ID to the user

### Reply draft
1. User: "Reply to that email from Bob"
2. First, get the original message headers (use `/search` or `/ask-about` to find the message)
3. Create draft with `in_reply_to` set to the original Message-ID and `references` for threading
4. Gmail will thread the reply correctly when sent

### Edit flow
1. User: "Draft an email to the team about Friday's meeting"
2. Create the draft → get `draft_id`
3. User: "Actually, change the subject to 'Meeting postponed'"
4. Update the draft with the new subject

## Security Notes

- Claude Code's approval prompt is the security gate
- The proxy blocks sending emails and sending drafts — only draft CRUD is allowed
- Drafts stay in Gmail's drafts folder; the user must manually send them
