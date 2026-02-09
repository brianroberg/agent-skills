---
name: capture
description: "Use when the user asks to 'add to inbox', 'capture this', 'remind me to', 'record a task', 'I need to', or when potential action items or commitments surface in conversation."
---

# Capture to GTD Inbox

Capture tasks and action items to the GTD inbox with appropriate clarification.

## Invocation Triggers

**Explicit capture:** Triggered by phrases like "add to inbox," "capture this," "remind me to," "record a task," "I need to..."

**Proactive capture:** When something surfaces in conversation that sounds like an action item or commitment, ask: "Should I capture that?" Never silently add items.

## Capture Process

### Clarify Before Capturing

Prod for clarity before adding to inbox. Items should enter already reasonably actionable. Useful clarifying questions:

- "What's the concrete first step?"
- "Are you doing this, or is someone else responsible?"
- "Is there a timeline or deadline?"
- "What does 'done' look like?"

Exercise judgment—skip clarification when the item is already clear ("email John about the meeting"). Only prod when something is genuinely vague ("figure out the budget situation").

### Handle Vague Intentions

When phrases like "I should probably..." or "I've been meaning to..." appear, push gently: "What would be the first concrete step toward that?" If no concrete step emerges, suggest Someday/Maybe or acknowledge it's not ready to capture yet.

## Item Format

**Title:** Concise, action-oriented.
- Good: "Email John re: Q3 budget"
- Bad: "Budget stuff"

**Notes:** Any context from clarification—timeline, who's involved, why it matters. Keep brief.

## What NOT to Capture

- Reference material ("remember that the API key is X")
- Things being done right now in this session
- Vague worries that aren't actionable yet

## After Capture

Confirm simply:
> Captured: [title]

No lengthy confirmation. No "anything else?" Just acknowledge and move on.

## API Reference

Endpoint and credentials in `/workspace/TOOLS.md`. Full API spec at https://gtd-api.fly.dev/openapi.json.

**Capture to inbox:**
```
POST https://gtd-api.fly.dev/inbox
Header: X-API-Key: [from TOOLS.md]
Body: { "title": "...", "notes": "...", "area_id": int|null, "project_id": int|null }
```

The `area_id` and `project_id` fields are optional. When the area is obvious from context, set it at capture time to save a step during processing.

**Areas of responsibility:**
```
GET  /areas                — list all areas
POST /areas                — create area: { "name": "...", "description": "..." }
GET  /areas/{id}/actions   — list actions in an area
GET  /areas/{id}/projects  — list projects in an area
```

**Projects:**
```
GET  /projects             — list all projects
POST /projects             — create: { "title": "...", "outcome": "...", "area_id": int|null }
GET  /projects/{id}/actions — list actions in a project
POST /projects/{id}/actions — create action directly in a project
```

**Other key endpoints:**
- `GET /inbox` — list inbox items (`?include_completed=true` to show completed)
- `POST /inbox/{id}/complete` — mark inbox item complete
- `DELETE /inbox/{id}` — permanently delete inbox item
- `POST /inbox/{id}/process` — move to next_action, someday_maybe, tickler, or delete
- `GET /next-actions` — list next actions (`?include_completed=true` to show completed)
- `POST /next-actions/{id}/complete` — mark action complete
- `DELETE /next-actions/{id}` — permanently delete next action
- `POST /someday-maybe/{id}/complete` — mark someday/maybe item complete
- `POST /tickler/{id}/complete` — mark tickler item complete
