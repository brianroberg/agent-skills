---
name: process-inbox
description: "Use when the user asks to 'process inbox', 'clear inbox', 'triage inbox', 'go through the inbox', 'sort the inbox', or during a weekly/daily review that involves working through inbox items. Also use when there are inbox items that need to be moved to their proper GTD destination."
---

# Process GTD Inbox

Work through inbox items and move each to its proper GTD destination: next action, someday/maybe, tickler, or delete.

## Invocation Triggers

**Explicit processing:** "Process my inbox," "let's clear the inbox," "triage inbox," "go through inbox items."

**During review:** Weekly review (Friday morning) or daily mini-review when inbox has items.

**Proactive:** After checking inbox count (`GET /review/inbox-count`), if items are waiting.

## Processing Workflow

### 1. Fetch the Inbox and Context

Before processing, load:
- `GET /inbox` — all inbox items
- `GET /areas` — areas of responsibility (for assignment)
- `GET /projects` — active projects (for linking items)
- `GET /next-actions` — current next actions (for awareness)

### 2. Propose a Triage Plan

Rather than going one-by-one, review all items and present a batch recommendation:
- For each item, suggest a destination (next action, someday/maybe, tickler, delete)
- Suggest an area of responsibility
- Flag items that might belong to an existing project or need a new project
- Present the plan and let the user adjust before executing

This respects the user's time — they can approve the whole batch with tweaks rather than making 11 individual decisions.

### 3. For Each Item, Decide the Destination

Apply the GTD processing questions:
- **Is it actionable?** If no → someday/maybe or delete
- **Is it a single step?** If yes → next action. If no → needs a project
- **Should I do it, or someone else?** If delegated → next action with `delegated_to` set
- **Does it need to wait for a specific date?** If yes → tickler with `tickler_date`

### 4. Execute the Processing

For each item, use the process endpoint:
```
POST /inbox/{item_id}/process
Header: X-API-Key: [from TOOLS.md]
Body: {
  "destination": "next_action" | "someday_maybe" | "tickler" | "delete",
  "project_id": int | null,
  "tag_ids": [int]
}
```

**CRITICAL: area_id is NOT preserved through processing.** The process endpoint moves the item but drops the `area_id`. After processing, you MUST patch each item on its destination list to restore the area:

```
PATCH /next-actions/{item_id}
Body: { "area_id": int }

PATCH /someday-maybe/{item_id}
Body: { "area_id": int }
```

The recommended approach: process all items first, then batch-update area_ids on the destination lists.

### 5. Create Projects When Needed

If an item breaks down into multiple steps, create a project first, then process the item as a next action under that project:

```
POST /projects
Body: { "title": "...", "outcome": "...", "area_id": int | null }
```

Then process the inbox item with `"project_id"` set to the new project ID. Consider renaming the item to be a concrete first step (PATCH the item on its destination list after processing).

### 6. Update Item Details

Use PATCH to update items before or after processing:
```
PATCH /inbox/{item_id}        — before processing
PATCH /next-actions/{item_id} — after processing to next_action
PATCH /someday-maybe/{item_id} — after processing to someday_maybe
PATCH /tickler/{item_id}      — after processing to tickler

Body (all fields optional): {
  "title": "...",
  "notes": "...",
  "area_id": int,
  "project_id": int,
  "due_date": "ISO datetime",
  "due_date_is_hard": bool,
  "delegated_to": "name",
  "energy_level": "low" | "medium" | "high",
  "time_estimate": int (minutes),
  "priority": int,
  "tag_ids": [int]
}
```

## After Processing

Confirm with a summary:
- How many items moved to next actions (grouped by area)
- How many to someday/maybe
- How many to tickler
- Any new projects created
- Inbox count should be 0

## API Reference

Endpoint and credentials in `/workspace/TOOLS.md`. Full API spec at https://gtd-api.fly.dev/openapi.json.

**Key endpoints for processing:**
- `GET /inbox` — list inbox items
- `POST /inbox/{id}/process` — move item to destination
- `PATCH /next-actions/{id}` — update item after processing (set area_id, etc.)
- `PATCH /someday-maybe/{id}` — update someday item after processing
- `PATCH /tickler/{id}` — update tickler item after processing
- `GET /areas` — list areas of responsibility
- `GET /projects` — list active projects
- `POST /projects` — create a new project
- `GET /review/inbox-count` — quick check if inbox has items
