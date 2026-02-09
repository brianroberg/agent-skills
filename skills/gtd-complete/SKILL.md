---
name: complete
description: "Use when the user says 'done', 'finished', 'complete that task', 'mark it done', 'check that off', 'I did it', or otherwise indicates a GTD task has been completed. Also use when reviewing a list and the user wants to close out items."
---

# Complete GTD Task

Mark tasks as complete across any GTD list (inbox, next-actions, someday-maybe, tickler).

## Invocation Triggers

**Explicit completion:** "Mark that done," "complete it," "check that off," "I finished [task]," "done with [task]."

**During review:** When reviewing a list and the user indicates items are finished.

## Completion Process

### Identify the Item

If the user references a task by name but you don't have the ID:
1. Query the appropriate list endpoint to find the item
2. If ambiguous, show matching items and ask which one

If the user just says "done" or "mark it complete" after recently discussing a specific task, use context to identify it.

### Confirm Before Completing

Always confirm which item you're completing before calling the API:
> Complete: [title]?

Skip confirmation only when the item is unambiguous from context (e.g., you just captured it or they referenced it by exact name).

### Choose the Right List

Items live on different lists. Match the endpoint to where the item lives:
- **Inbox items** → `POST /inbox/{id}/complete`
- **Next actions** → `POST /next-actions/{id}/complete`
- **Someday/maybe** → `POST /someday-maybe/{id}/complete`
- **Tickler items** → `POST /tickler/{id}/complete`

If you're unsure which list an item is on, check `next-actions` first (most common), then `inbox`.

### After Completing

Confirm simply:
> Done: [title]

No lengthy confirmation. Move on.

## Deleting vs. Completing

**Default to completing** — this preserves the item with a `completed_at` timestamp for review and history.

Only use DELETE (`DELETE /{list}/{id}`) when the user explicitly wants to **remove** an item entirely (e.g., "delete that," "remove it," "that was a mistake, get rid of it"). Deletion is permanent with no record.

## API Reference

Endpoint and credentials in `/workspace/TOOLS.md`. Full API spec at https://gtd-api.fly.dev/openapi.json.

**Complete an item:**
```
POST https://gtd-api.fly.dev/{list}/{item_id}/complete
Header: X-API-Key: [from TOOLS.md]
```

Where `{list}` is one of: `inbox`, `next-actions`, `someday-maybe`, `tickler`.

Returns the updated item with `completed_at` timestamp set.

**List items (to find IDs):**
```
GET https://gtd-api.fly.dev/{list}
Header: X-API-Key: [from TOOLS.md]
```

Add `?include_completed=true` to also show already-completed items.

**Delete an item (only when explicitly requested):**
```
DELETE https://gtd-api.fly.dev/{list}/{item_id}
Header: X-API-Key: [from TOOLS.md]
```
