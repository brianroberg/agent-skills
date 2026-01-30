# Email Triage Implementation Plan

This document outlines the implementation plan for adding email triage capabilities, split between the skills layer (this repository) and the Email Agent server.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code (Opus)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              /email-triage skill                         │   │
│  │  - Fetches batch of unread emails                       │   │
│  │  - Classifies by urgency, topic, action-needed          │   │
│  │  - Generates triage recommendations                      │   │
│  │  - Presents suggestions for user approval               │   │
│  │  - Executes approved bulk actions                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP REST API
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Email Agent Server                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  New Endpoints:                                          │   │
│  │  - POST /batch-search   (return multiple email stubs)   │   │
│  │  - POST /batch-summarize (summarize multiple emails)    │   │
│  │  - POST /bulk-actions   (apply actions to multiple)     │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Existing Endpoints (unchanged):                         │   │
│  │  - /search, /summarize, /ask-about                      │   │
│  │  - /apply-label, /mark-read, /archive                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Skills Layer (This Repository)

### New Skill: `/email-triage`

**Purpose:** Interactive email triage workflow that classifies unread emails and helps the user quickly process their inbox.

**File Location:** `/workspace/skills/email-triage/SKILL.md`

#### Skill Specification

```yaml
---
name: email-triage
description: Triage unread emails by classifying urgency, suggesting actions, and bulk-processing with user approval
allowed-tools: Bash
---
```

#### Workflow Steps

1. **Fetch Unread Emails**
   - Call `/batch-search` with `query: "is:unread"` and configurable limit (default: 25)
   - If batch endpoint unavailable, fall back to existing `/search`

2. **Get Summaries**
   - Call `/batch-summarize` with list of message IDs
   - If batch endpoint unavailable, call `/summarize` for each (with progress indication)

3. **Classify Emails (Opus does this)**

   Categories:
   - **Urgent/Action Required:** Deadlines, direct requests, time-sensitive
   - **Needs Response:** Questions directed at user, awaiting reply
   - **FYI/Informational:** Newsletters, notifications, CC'd threads
   - **Likely Archive:** Automated notifications, marketing, old threads

   Priority signals to detect:
   - Sender importance (manager, client, family vs. marketing)
   - Subject line urgency markers (URGENT, ACTION, DEADLINE)
   - Action verbs in summary (please review, need your input, approve)
   - Recency and thread activity

4. **Present Triage Recommendations**

   Display grouped by category:
   ```
   URGENT (2 emails):
   • [ID: abc123] From: boss@company.com - "Q4 Report Review Needed"
     → Suggested: Keep unread, label IMPORTANT

   LIKELY ARCHIVE (5 emails):
   • [ID: def456] From: notifications@github.com - "PR merged"
   • [ID: ghi789] From: marketing@service.com - "Weekly digest"
     → Suggested: Archive all, mark as read
   ```

5. **Get User Approval**
   - Use AskUserQuestion tool to confirm actions
   - Options: "Apply all suggestions", "Review one by one", "Skip"

6. **Execute Bulk Actions**
   - Call `/bulk-actions` endpoint with approved operations
   - Report results

#### Edge Cases

- If any email is ambiguous, use `/ask-about` to get clarifying details before classifying
- If batch endpoints not available, gracefully degrade to sequential calls with progress updates
- Handle empty inbox gracefully

---

### New Skill: `/email-triage-rules`

**Purpose:** Let users define persistent triage rules (e.g., "always archive emails from noreply@")

**File Location:** `/workspace/skills/email-triage-rules/SKILL.md`

This is a future enhancement - not part of initial implementation.

---

## Part 2: Email Agent Server Changes

### New Endpoint: `POST /batch-search`

**Purpose:** Return multiple email stubs in a single request (same as `/search` but optimized for bulk retrieval).

**Request:**
```json
{
  "query": "is:unread",
  "folder": "INBOX",
  "limit": 50,
  "include_snippet": true
}
```

**Response:**
```json
{
  "emails": [
    {
      "id": "message_id_1",
      "thread_id": "thread_id_1",
      "date": "2026-01-28T09:30:00Z",
      "from": "sender@example.com",
      "from_name": "Sender Name",
      "to": ["recipient@example.com"],
      "subject": "Email subject line",
      "snippet": "First 100 chars of body...",
      "labels": ["INBOX", "UNREAD"],
      "has_attachments": false
    }
  ],
  "total_count": 42,
  "returned_count": 50
}
```

**Notes:**
- This may be identical to existing `/search` - verify current response format
- Ensure snippet is included for quick preview without full summarization

---

### New Endpoint: `POST /batch-summarize`

**Purpose:** Generate summaries for multiple emails in one request.

**Request:**
```json
{
  "message_ids": ["id1", "id2", "id3"],
  "summary_style": "triage"
}
```

**Response:**
```json
{
  "summaries": [
    {
      "message_id": "id1",
      "summary": "Request from manager to review Q4 report by Friday EOD. Contains spreadsheet attachment.",
      "detected_action": "review_requested",
      "detected_deadline": "2026-01-31",
      "key_entities": ["Q4 report", "spreadsheet"]
    },
    {
      "message_id": "id2",
      "summary": "GitHub notification that PR #123 was merged to main branch.",
      "detected_action": "notification",
      "detected_deadline": null,
      "key_entities": ["PR #123", "main branch"]
    }
  ]
}
```

**Notes:**
- The `summary_style: "triage"` option should produce concise summaries focused on action items
- `detected_action` and `detected_deadline` are best-effort extraction by the server model
- These hints help the skill layer but final classification happens in Opus

---

### New Endpoint: `POST /bulk-actions`

**Purpose:** Apply multiple actions to multiple emails in one atomic operation.

**Request:**
```json
{
  "actions": [
    {
      "email_id": "id1",
      "operations": ["mark_read", "apply_label:IMPORTANT"]
    },
    {
      "email_id": "id2",
      "operations": ["mark_read", "archive"]
    },
    {
      "email_id": "id3",
      "operations": ["archive"]
    }
  ]
}
```

**Supported operations:**
- `mark_read`
- `mark_unread`
- `archive`
- `apply_label:<label_name>`
- `remove_label:<label_name>`
- `star`
- `unstar`

**Response:**
```json
{
  "results": [
    {"email_id": "id1", "status": "success"},
    {"email_id": "id2", "status": "success"},
    {"email_id": "id3", "status": "error", "error": "Email not found"}
  ],
  "success_count": 2,
  "error_count": 1
}
```

**Notes:**
- Operations should be applied in order listed
- If one email fails, continue processing others (don't abort entire batch)
- Consider adding `dry_run: true` option for testing

---

## Implementation Order

### Phase 1: Server-Side (Email Agent)
1. Implement `/batch-summarize` endpoint
2. Implement `/bulk-actions` endpoint
3. Verify `/search` returns sufficient data (or add `/batch-search`)
4. Add tests for new endpoints

### Phase 2: Skill Layer (This Repo)
1. Create `/email-triage` skill with graceful degradation
2. Test with existing endpoints first (sequential calls)
3. Update to use batch endpoints once available
4. Add user preference handling (categories to show, default actions)

### Phase 3: Polish
1. Add `/email-triage-rules` for persistent user preferences
2. Performance optimization (caching, pagination)
3. Integration with `/morning-briefing` skill

---

## Open Questions

1. **Rate limiting:** Should batch endpoints have separate rate limits?
2. **Pagination:** For inboxes with 100+ unread, should triage work in pages?
3. **Threading:** Should triage consider entire threads or just individual emails?
4. **Undo:** Should we track triage sessions to allow bulk undo?

---

## Testing Checklist

- [ ] Triage with 0 unread emails (empty state)
- [ ] Triage with 1-5 emails (small batch)
- [ ] Triage with 25+ emails (pagination if needed)
- [ ] Mixed categories (some urgent, some archive)
- [ ] Batch endpoint failure (graceful degradation)
- [ ] User cancels mid-triage
- [ ] Bulk action partial failure
