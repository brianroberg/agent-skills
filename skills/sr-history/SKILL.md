---
name: sr-history
description: "Use when the user asks about contact/donor interaction history, past communications, when they last called or visited someone, or wants to log a new interaction. Triggers: 'history for [name]', 'when did I last call', 'log a call', 'record a visit', 'log thank-you', 'interaction history', 'what have I done with [name]', 'communication log'."
---

# SR Contact History

View and log interaction history in the SR Assistant (Donor Management) system.
Covers calls, visits, letters, emails, thank-yous, and other contact activities.

## Prerequisites

Connection details (URL and API key) are in `/workspace/TOOLS.md` under "SR Assistant".
The URL may change between Codespace sessions — always read from TOOLS.md.

## History Types

| ID | Name | Updates Last Call | Updates Last Letter | Updates Last Visit |
|----|------|:-:|:-:|:-:|
| 1 | Appointment | | | Yes |
| 2 | Call | Yes | | |
| 3 | Email | | | |
| 4 | Letter | | Yes | |
| 5 | Text | | | |
| 6 | Visit | | | Yes |
| 7 | Thank | | | |
| 8 | Newsletter | | Yes | |

Legacy TntConnect types (imported data may reference these):

| ID | Name | Updates Last Letter |
|----|------|:-:|
| 20 | Call (legacy) | |
| 30 | Reminder Letter | Yes |
| 40 | Support Letter | Yes |
| 50 | Letter (legacy) | Yes |
| 60 | Newsletter (legacy) | Yes |
| 65 | E-Newsletter | Yes |
| 70 | Pre Call Letter | Yes |
| 100 | Email (legacy) | Yes |
| 120 | Unscheduled Visit | (updates last visit) |
| 130 | Note | |
| 140 | Facebook | Yes |
| 150 | Text/SMS (legacy) | Yes |
| 160 | Present | |
| 170 | MailChimp | |
| 180 | WhatsApp | |
| 190 | Data Change | |

## History Results

| ID | Name |
|----|------|
| 1 | Done |
| 2 | Attempted |
| 3 | Received |
| 4 | Left Message |

## Read Endpoints

### 1. List History for a Contact

```bash
curl -s "$SR_URL/api/v1/history?contact_id={contact_id}&limit=30" \
    -H "X-API-Key: $SR_KEY" | jq .
```

Parameters:
- `contact_id`: Filter by contact (strongly recommended)
- `skip`: Pagination offset (default: 0)
- `limit`: Max results (default: 100, max: 500)

Returns: `id`, `history_date`, `history_type_id`, `description`, `is_thank`

### 2. Get History Detail

```bash
curl -s "$SR_URL/api/v1/history/{history_id}" \
    -H "X-API-Key: $SR_KEY" | jq .
```

Full detail includes: `history_date`, `history_type_id`, `history_result_id`,
`description`, `notes`, `confidential_notes`, `is_thank`, `is_challenge`,
`history_type` (expanded), `history_result` (expanded), `contacts[]` (linked contacts)

## Write Endpoints

**Important:** Always confirm with the user before creating history entries.

### 3. Log New History Entry

```bash
curl -s -X POST "$SR_URL/api/v1/history" \
    -H "X-API-Key: $SR_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "history_date": "2026-02-24T10:30:00",
        "history_type_id": 2,
        "history_result_id": 1,
        "description": "Caught up on family news",
        "notes": "Kids are doing well in school",
        "is_thank": false,
        "contact_ids": [42]
    }' | jq .
```

Required fields:
- `history_date`: ISO datetime (YYYY-MM-DDTHH:MM:SS)
- `history_type_id`: From history types table above

Optional fields:
- `history_result_id`: 1=Done, 2=Attempted, 3=Received, 4=Left Message
- `description`: Brief summary of the interaction
- `notes`: Detailed notes
- `confidential_notes`: Private notes
- `is_thank`: Mark as thank-you interaction
- `is_challenge`: Mark as challenge/ask interaction
- `campaign_id`: Link to campaign
- `contact_ids`: Array of contact IDs involved

### 4. Update History Entry

```bash
curl -s -X PUT "$SR_URL/api/v1/history/{history_id}" \
    -H "X-API-Key: $SR_KEY" \
    -H "Content-Type: application/json" \
    -d '{"notes": "Updated notes"}' | jq .
```

### 5. Delete History Entry

```bash
curl -s -X DELETE "$SR_URL/api/v1/history/{history_id}" \
    -H "X-API-Key: $SR_KEY"
```

## Common Workflows

### "What's my history with [name]?"

1. Search contact: `GET /api/v1/contacts?search=[name]`
2. List history: `GET /api/v1/history?contact_id={id}&limit=20`
3. For each entry, resolve the `history_type_id` to a name using the table above
4. Present chronologically with type, date, description

### "Log a call with [name]"

1. Search contact to get ID
2. Ask user: What did you talk about? What was the result? (Done / Left Message / etc.)
3. Create history entry with `history_type_id: 2` (Call)
4. Set `history_date` to now (or ask if it was earlier)
5. Confirm creation

### "Record a thank-you to [name]"

1. Search contact to get ID
2. Create history entry with `history_type_id: 7` (Thank), `is_thank: true`
3. Include description of what you thanked them for

### "When did I last reach out to [name]?"

Use the contact summary endpoint instead (faster):
```bash
curl -s "$SR_URL/api/v1/contacts/{id}/summary" \
    -H "X-API-Key: $SR_KEY" | jq .activity
```

This gives `last_call_date`, `last_letter_date`, `last_visit_date`, `last_thank_date`, `last_activity_date`.

## Presentation Tips

- When showing history, group by year or show most recent first
- Include the history type name (not just the ID) — use the table above to resolve
- For "last contact" queries, note how long ago it was
- Flag if a thank-you is overdue (e.g., last gift was months ago with no thank recorded)
- When logging, default `history_date` to the current time unless the user specifies otherwise
