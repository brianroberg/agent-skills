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

First, get the list of unread emails. Every read in this skill checks **both** the HTTP
status **and** the body's `success` flag — see *Reading a response* at the end of this
file for why one check is not enough.

```bash
resp=$(curl -sS --max-time 60 -X POST "$EMAIL_AGENT_URL/search" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{"query": "is:unread", "folder": "INBOX", "limit": 25}')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ] || [ "$(printf '%s' "$body" | jq -r '.success')" != "true" ]; then
    echo "SEARCH FAILED (curl exit $rc, HTTP ${code:-none}) - the inbox is unknown, not empty"
    printf '%s' "$body" | jq -r '.error // .detail // .' 2>/dev/null
else
    printf '%s' "$body" | jq '.messages'
fi
```

Only when the read **succeeded** (`success: true`) and `messages` is empty: inform the
user there is nothing to triage and stop. If the read failed, say so and stop — do not
report an empty inbox.

Each message carries the sender as `from_addr` (the raw `From:` header, `Name <addr>`
form) and `from_name` (the display name) — there is no field named from — plus `id`, `thread_id`, `date`, `to`, `cc`, `subject`, `snippet`, `labels`,
`has_attachments` and `rfc822_message_id`. The full list is in the `email-ask` skill.

### Step 2: Get Summaries

**If `/batch-summarize` is available** (preferred):

```bash
resp=$(curl -sS --max-time 300 -X POST "$EMAIL_AGENT_URL/batch-summarize" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{"message_ids": ["id1", "id2", "id3"], "summary_style": "triage"}')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ] || [ "$(printf '%s' "$body" | jq -r '.success')" != "true" ]; then
    echo "BATCH-SUMMARIZE FAILED (curl exit $rc, HTTP ${code:-none}) - the summaries are missing"
    printf '%s' "$body" | jq -r '.error // .detail // .' 2>/dev/null
else
    printf '%s' "$body" | jq '.results'
fi
```

The batch response is `{success, results, error}`; each entry in `results` carries its
own `message_id`, `success`, `summary`, `degraded`, `detected_action`,
`detected_deadline` and `error`, so one email can fail inside an otherwise successful
batch — check the per-message `success` too.

**Fallback** - call `/summarize` for each email individually:

```bash
resp=$(curl -sS --max-time 120 -X POST "$EMAIL_AGENT_URL/summarize" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{"message_id": "MESSAGE_ID"}')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ] || [ "$(printf '%s' "$body" | jq -r '.success')" != "true" ]; then
    echo "SUMMARIZE FAILED (curl exit $rc, HTTP ${code:-none}) - the summary is missing"
    printf '%s' "$body" | jq -r '.error // .detail // .' 2>/dev/null
else
    printf '%s' "$body" | jq -r '.answer'
fi
```

`/summarize` returns `{success, answer, degraded, error}` — the text is top-level
`.answer` (the email agent has no `.data` wrapper, unlike the calendar agent).

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
resp=$(curl -sS --max-time 120 -X POST "$EMAIL_AGENT_URL/ask-about" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{"message_id": "MESSAGE_ID", "question": "Is there a specific action requested or deadline mentioned?"}')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ] || [ "$(printf '%s' "$body" | jq -r '.success')" != "true" ]; then
    echo "ASK-ABOUT FAILED (curl exit $rc, HTTP ${code:-none}) - the answer is missing"
    printf '%s' "$body" | jq -r '.error // .detail // .' 2>/dev/null
else
    printf '%s' "$body" | jq -r '.answer'
fi
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

- **Empty inbox**: "No unread emails to triage." — only after a read that returned
  `success: true`; a failed read is reported as a failure, never as an empty inbox
- **Read failed** (non-200, curl error, or `success: false`): report the `error` text and stop
- **All urgent**: Skip archive suggestions, focus on prioritization
- **Batch endpoint unavailable**: Fall back to sequential calls, show progress
- **Partial failure**: Report which emails succeeded/failed, don't abort

## Reading a response: two checks, not one

The read routes (`/search`, `/batch-summarize`, `/summarize`, `/ask-about`) signal failure
two different ways, and both look like "nothing found" to a reader that pipes `curl`
straight into `jq`:

- **Non-200** — `405` (wrong verb), `422` (malformed body). The body is FastAPI's
  `{"detail": ...}` with no `messages`/`results`/`answer` key.
- **200 with `"success": false`** — the email agent catches every failure inside these
  routes (Gmail proxy errors, OAuth expiry, LLM unreachable, a bad message id) and returns
  **HTTP 200** with `success: false`, an empty `messages`/`results`/`answer`, and the
  reason in `error`. Verified live 2026-09-09: `/summarize` with a nonexistent id →
  `200 {"success":false,"answer":"","degraded":false,"error":"Proxy error: Invalid id value"}`.

Hence the shape used above: capture the response with `-w '\n%{http_code}'`, split the
status off, and check the status **and** `.success`. Do not bolt `-w` onto a piped
`curl ... | jq` — `jq` reads the status line as a second document and dies. The write
snippets in Step 6 are outside #11's scope and unchanged here. Note their contract differs
again: `/mark-read`, `/archive` and `/apply-label` raise real HTTP errors (`400`, `500`),
while `/bulk-actions` always returns 200 — read its top-level `success`, `success_count`,
`error_count` and each result's own `success`/`error`, not the status.

## Security Notes

- Write operations require Claude Code approval prompt
- Email bodies stay local; only summaries transit the API
- The email agent ignores instructions in email content (prompt injection protection)
