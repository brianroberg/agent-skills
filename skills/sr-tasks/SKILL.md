---
name: sr-tasks
description: "Use when the user asks about support raising tasks, donor follow-ups, thank-you reminders, or when managing tasks in the SR assistant / donor management system. Triggers: 'SR tasks', 'donor tasks', 'follow-up tasks', 'thank-you tasks', 'support raising to-do', 'what do I need to do for donors'."
---

# SR Assistant Tasks

View, create, and complete tasks in the Donor Management (SR Assistant) system.
These are support-raising-specific tasks tied to donor contacts — distinct from GTD tasks.

## Prerequisites

Connection details (URL and API key) are in `/workspace/TOOLS.md` under "SR Assistant".
The URL may change between Codespace sessions — always read from TOOLS.md.

## Task Types

| ID | Name | Notes |
|----|------|-------|
| 1 | Appointment | Time-sensitive |
| 2 | Call | |
| 3 | Email | |
| 4 | Letter | |
| 5 | Thank | Default `is_thank: true` |
| 6 | To Do | General |

Note: Legacy TntConnect data may use different type IDs (e.g., 20, 170).
Status on imported tasks is `"0"` rather than `"pending"`.

## Endpoints

Read the URL and API key from `/workspace/TOOLS.md` before making requests.
All endpoints use the `X-API-Key` header for auth.

### 1. List Tasks

List tasks with optional filtering by contact or status.

```bash
curl -s "$SR_URL/api/v1/tasks?limit=50" \
    -H "X-API-Key: $SR_KEY" | jq .
```

Parameters (all optional):
- `skip`: Pagination offset (default: 0)
- `limit`: Max results (default: 100, max: 500)
- `contact_id`: Filter by contact
- `status`: Filter by status (e.g., `pending`, `completed`)

### 3. Get Task Detail

```bash
curl -s "$SR_ASSISTANT_URL/api/v1/tasks/{task_id}" \
    -H "X-API-Key: $SR_API_KEY" | jq .
```

### 4. Create Task

Create a new task linked to one or more contacts.

```bash
curl -s -X POST "$SR_ASSISTANT_URL/api/v1/tasks" \
    -H "X-API-Key: $SR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "task_type_id": 1,
        "description": "Write thank-you note",
        "task_date": "2026-02-24",
        "notes": "For recent gift increase",
        "is_thank": true,
        "contact_ids": [42]
    }' | jq .
```

Required fields:
- `task_type_id`: ID from task types list
- `description`: What needs to be done
- `task_date`: Date (YYYY-MM-DD)

Optional fields:
- `task_time`: Time (HH:MM:SS) if time-sensitive
- `notes`: Additional context
- `confidential_notes`: Private notes
- `status`: Default `pending`
- `is_thank`: Boolean, marks as thank-you task
- `auto_gen_code`: For system-generated tasks
- `campaign_id`: Link to campaign
- `contact_ids`: Array of contact IDs to link

### 5. Update Task

```bash
curl -s -X PUT "$SR_ASSISTANT_URL/api/v1/tasks/{task_id}" \
    -H "X-API-Key: $SR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"description": "Updated description", "status": "pending"}' | jq .
```

### 6. Complete Task

```bash
curl -s -X POST "$SR_ASSISTANT_URL/api/v1/tasks/{task_id}/complete" \
    -H "X-API-Key: $SR_API_KEY" | jq .
```

### 7. Delete Task

```bash
curl -s -X DELETE "$SR_ASSISTANT_URL/api/v1/tasks/{task_id}" \
    -H "X-API-Key: $SR_API_KEY"
```

## Searching for Contacts

To link tasks to contacts, you'll often need to find the contact ID first.
Use the contacts search endpoint:

```bash
curl -s "$SR_ASSISTANT_URL/api/v1/contacts?search=Johnson&limit=10" \
    -H "X-API-Key: $SR_API_KEY" | jq .
```

Returns: `id`, `file_as`, `first_name`, `last_name`, `spouse_first_name`, `is_organization`, `org_name`

## Decision Guide

| User asks... | Action |
|---|---|
| "What SR tasks do I have?" | List tasks with `status=pending` |
| "Show thank-you tasks" | List tasks, filter for `is_thank: true` |
| "Add a task to call [name]" | Search contacts for name, create task with appropriate type |
| "Mark that done" | Complete the task |
| "What tasks are due today?" | List tasks, filter by `task_date` |

## Relationship to GTD

SR tasks track donor relationship activities (calls, thank-yous, visits).
GTD tasks track broader action items across all areas of responsibility.
They are separate systems. When a user says "task" in the context of support raising
or donors, use this skill. For general productivity tasks, use GTD skills.
