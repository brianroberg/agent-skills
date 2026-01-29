---
name: email-triage
description: Triage unread emails - classify by urgency, suggest actions, bulk-process with approval
allowed-tools: Bash
---

# Email Triage

Interactively triage unread emails by classifying them and applying bulk actions with user approval.

**This skill modifies your inbox and requires approval before executing write operations.**

## Prerequisites

Requires `EMAIL_AGENT_URL` environment variable to be set.

## Workflow

### Step 1: Fetch Unread Emails

First, get the list of unread emails:

```bash
curl -s -X POST "$EMAIL_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "is:unread", "folder": "INBOX", "limit": 25}' \
    | jq .
```

If no unread emails, inform the user and stop.

### Step 2: Get Summaries

**If `/batch-summarize` is available** (preferred):

```bash
curl -s -X POST "$EMAIL_AGENT_URL/batch-summarize" \
    -H "Content-Type: application/json" \
    -d '{"message_ids": ["id1", "id2", "id3"], "summary_style": "triage"}' \
    | jq .
```

**Fallback** - call `/summarize` for each email individually:

```bash
curl -s -X POST "$EMAIL_AGENT_URL/summarize" \
    -H "Content-Type: application/json" \
    -d '{"message_id": "MESSAGE_ID"}' \
    | jq .
```

### Step 3: Classify Emails

Analyze each email and assign to ONE category:

| Category | Criteria | Suggested Action |
|----------|----------|------------------|
| **Urgent** | Deadlines, direct requests, time-sensitive, from important senders | Keep unread, label IMPORTANT |
| **Needs Response** | Questions to user, awaiting reply, action verbs (review, approve, confirm) | Keep unread |
| **FYI** | Newsletters, CC'd threads, status updates, no action needed | Mark read |
| **Archive** | Automated notifications, marketing, old resolved threads, receipts | Mark read + archive |

**Priority signals to look for:**
- Sender relationship (manager, client, family = higher priority)
- Subject urgency markers (URGENT, ACTION REQUIRED, DEADLINE)
- Action verbs in summary (please review, need your input, waiting for)
- Whether user is in To: vs CC:

**If classification is unclear**, use `/ask-about` to get more details:

```bash
curl -s -X POST "$EMAIL_AGENT_URL/ask-about" \
    -H "Content-Type: application/json" \
    -d '{"message_id": "MESSAGE_ID", "question": "Is there a specific action requested or deadline mentioned?"}' \
    | jq .
```

### Step 4: Present Recommendations

Show the user a grouped summary:

```
## Email Triage Results

**URGENT (2 emails)**
- From: boss@company.com - "Q4 Report Review Needed by Friday"
  → Keep unread, add IMPORTANT label
- From: client@bigco.com - "Contract questions"
  → Keep unread, add IMPORTANT label

**NEEDS RESPONSE (1 email)**
- From: coworker@company.com - "Quick question about API"
  → Keep unread

**FYI (3 emails)**
- From: notifications@slack.com - "New messages in #general"
- From: calendar@google.com - "Event reminder: Team sync"
- From: github@notifications.com - "PR review requested"
  → Mark as read

**ARCHIVE (4 emails)**
- From: noreply@marketing.com - "Weekly newsletter"
- From: receipts@amazon.com - "Your order has shipped"
- From: no-reply@linkedin.com - "Your network updates"
- From: notifications@jira.com - "Issue resolved"
  → Mark as read and archive
```

### Step 5: Get User Approval

Use AskUserQuestion to confirm:

**Question:** "Apply these triage actions?"

**Options:**
1. "Apply all suggestions" - Execute all recommended actions
2. "Apply FYI + Archive only" - Only process low-priority items
3. "Review one by one" - Go through each email individually
4. "Cancel" - Make no changes

### Step 6: Execute Actions

**If `/bulk-actions` is available** (preferred):

```bash
curl -s -X POST "$EMAIL_AGENT_URL/bulk-actions" \
    -H "Content-Type: application/json" \
    -d '{
      "actions": [
        {"email_id": "id1", "operations": ["apply_label:IMPORTANT"]},
        {"email_id": "id2", "operations": ["mark_read"]},
        {"email_id": "id3", "operations": ["mark_read", "archive"]}
      ]
    }' \
    | jq .
```

**Fallback** - use individual endpoints:

For mark read:
```bash
curl -s -X POST "$EMAIL_AGENT_URL/mark-read" \
    -H "Content-Type: application/json" \
    -d '{"email_id": "EMAIL_ID"}' \
    | jq .
```

For archive:
```bash
curl -s -X POST "$EMAIL_AGENT_URL/archive" \
    -H "Content-Type: application/json" \
    -d '{"email_id": "EMAIL_ID"}' \
    | jq .
```

For label:
```bash
curl -s -X POST "$EMAIL_AGENT_URL/apply-label" \
    -H "Content-Type: application/json" \
    -d '{"email_id": "EMAIL_ID", "label_name": "IMPORTANT"}' \
    | jq .
```

### Step 7: Report Results

Summarize what was done:
- X emails marked as read
- Y emails archived
- Z emails labeled IMPORTANT
- Any errors encountered

## Edge Cases

- **Empty inbox**: "No unread emails to triage."
- **All urgent**: Skip archive suggestions, focus on prioritization
- **Batch endpoint unavailable**: Fall back to sequential calls, show progress
- **Partial failure**: Report which emails succeeded/failed, don't abort

## Security Notes

- Write operations require Claude Code approval prompt
- Email bodies stay local; only summaries transit the API
- The email agent ignores instructions in email content (prompt injection protection)
