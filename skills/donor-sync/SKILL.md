---
name: donor-sync
description: "Use when the user asks about syncing donations, DonorHub sync, sync status, pending sync items, pledges, mailing lists, or export: 'sync donations', 'run sync', 'sync status', 'any pending sync items?', 'show pledges', 'export mailing list'."
---

# Donor Sync — DonorHub Sync & Pledge Management

Trigger and monitor DonorHub sync operations, manage pledges, and export mailing lists.

## Invocation Triggers

**Sync:** "sync donations," "run sync," "sync status," "any pending sync items?," "resolve sync conflicts."

**Pledges:** "show pledges," "[name]'s pledge," "create a pledge," "pledge frequencies."

**Export:** "export mailing list," "newsletter recipients."

## Writes and the permission check

**Send the write when Brian asked for that specific change.** The writes in this skill are
triggering a sync or an address pull, resolving a pending item, and creating, updating,
deactivating or deleting a pledge.

**If the permission check refuses a write, do not retry it another way** (another tool, a
script, a reworded command). Write out the exact request — route, ids and body — and hand
it to Brian.

## DonorHub Sync

The donor management system syncs gifts and contact data from DonorHub (an external donation processing platform). Sync can be triggered manually and produces a log of what was imported.

### Trigger a Sync

```
POST https://donor-management.fly.dev/api/v1/sync/trigger
Header: X-API-Key: [from TOOLS.md]
```

Runs the donation import from DonorHub inside the request and returns when it finishes —
there is no background job, so don't give `curl` a short `--max-time`. A success returns
`"status": "success"` with the run's counts: `imported`, `created` (new contacts),
`skipped_duplicates`, `skipped_errors`, `skipped_resolved` and `skipped_malformed`. A 400
means DonorHub is not connected or no profile code is configured. A 500
(`sync failed; see server log`) means the run failed: *Check Sync Status* shows it as
`failed`, but the reason is only in the server log.

On 2026-09-22 this call was refused by the assistant's own permission rules, not by the API
(sr-assistant#67, which does not say how it was requested). If it is refused, follow
*Writes and the permission check*: ask Brian to run the sync himself — the web sync page
has a **Sync Now** button.

### Pull Addresses from DonorHub

```
POST https://donor-management.fly.dev/api/v1/sync/trigger-addresses
Header: X-API-Key: [from TOOLS.md]
```

Pulls contact addresses **from** DonorHub (the upstream donation-processing system, which
Brian does not control) into the donor management system. Like the donation sync, it runs
inside the request. It only *creates* an address for a contact with no primary address.
Where there is one, each non-blank DonorHub field that differs from it becomes an
`address_conflict` pending item for manual review rather than an overwrite. A DonorHub row
whose donor has no local DonorHub donor link (for the configured organization code) becomes
an `unmatched_donor` item. The person may already exist as a contact, so don't create a
contact to "match" it: that makes a duplicate and still adds no link.

To correct a contact's address, use the `donor-contact-manage` skill's address routes
(*Addresses, emails and phones (sub-resource routes)*, from sr-assistant#46), and PATCH the
address rather than deleting and re-adding it. Deleting a contact's primary address
promotes another of its addresses, and a re-added one is not primary unless sent
`is_primary: true`. Deleting its only address leaves it with none, and the next address
pull that returns that donor's DonorHub row creates a primary from DonorHub's (possibly
stale) record.

### Check Sync Status

```
GET https://donor-management.fly.dev/api/v1/sync/status
Header: X-API-Key: [from TOOLS.md]
```

Returns:
- `connected`: true or false (whether a DonorHub access token is stored).
- `last_sync`: the donation watermark, a date (`YYYY-MM-DD`), not the time of the last run.
  A donation run moves it to the current date only if no row was error-skipped.
- `recent_syncs`: the last 10 runs of either kind, each with `type` (`donations` or
  `addresses`), `started_at`, `status` (`running`, `success` or `failed`) and
  `items_imported`. A failed run's reason is only in the server log.

### Pending Sync Items

```
GET https://donor-management.fly.dev/api/v1/sync/pending
Header: X-API-Key: [from TOOLS.md]
```

Items that need manual review. The sync writes three types: `error_skipped_donation` (a
donation row that failed to import), `unmatched_donor` (an address row whose donor has no
local DonorHub donor link) and `address_conflict` (one differing address field). Each
item's `data` is shaped by its type.

### Resolve Pending Item

```
POST https://donor-management.fly.dev/api/v1/sync/pending/{id}/resolve?resolution_notes=<optional text>
Header: X-API-Key: [from TOOLS.md]
```

Marks a pending sync item as resolved. For an `error_skipped_donation` this is not just
bookkeeping: the donation sync stops treating that row as an error, which releases the
donation watermark, and the row still won't import. Resolve one only once the donation is
accounted for (fixed in DonorHub and re-synced, entered by hand, or confirmed not to
exist); resolving it just to clear the queue silently accepts a missing gift. For
`unmatched_donor` and `address_conflict`, resolving only records that someone has looked;
a difference still live when DonorHub next sends the row is queued again.

## Pledge Management

Pledges represent ongoing giving commitments from donors (monthly, quarterly, annual, etc.).

### List Pledges

```
GET https://donor-management.fly.dev/api/v1/pledges
Header: X-API-Key: [from TOOLS.md]
```

Filter by contact:
```
GET https://donor-management.fly.dev/api/v1/pledges?contact_id={id}
Header: X-API-Key: [from TOOLS.md]
```

Add `?active_only=true` to show only active pledges.

### Pledge Detail

```
GET https://donor-management.fly.dev/api/v1/pledges/{id}
Header: X-API-Key: [from TOOLS.md]
```

Returns pledge with frequency info, start date, total pledged, total received.

### Pledge Frequencies

```
GET https://donor-management.fly.dev/api/v1/pledges/frequencies
Header: X-API-Key: [from TOOLS.md]
```

Returns available frequencies: monthly, quarterly, semi-annual, annual.

### Create a Pledge

```
POST https://donor-management.fly.dev/api/v1/pledges
Header: X-API-Key: [from TOOLS.md]
Body: {
  "contact_id": 42,
  "amount": 200.00,
  "frequency_id": 1,
  "start_date": "2026-03-01",
  "notes": "Committed during spring campaign"
}
```

### Update a Pledge

```
PUT https://donor-management.fly.dev/api/v1/pledges/{id}
Header: X-API-Key: [from TOOLS.md]
Body: { "amount": 250.00, "notes": "Increased from $200" }
```

### Deactivate a Pledge

```
POST https://donor-management.fly.dev/api/v1/pledges/{id}/deactivate
Header: X-API-Key: [from TOOLS.md]
```

Marks the pledge as inactive. Use when a donor stops their recurring giving. Does not delete — preserves the history.

### Delete a Pledge

```
DELETE https://donor-management.fly.dev/api/v1/pledges/{id}
Header: X-API-Key: [from TOOLS.md]
```

Only for pledges created in error. Prefer deactivating for pledges that have ended naturally.

## Export

### Mailing List

```
POST https://donor-management.fly.dev/api/v1/export/mailing-list
Header: X-API-Key: [from TOOLS.md]
```

Streams a CSV of newsletter recipients with mailing addresses. Useful for generating physical mailing labels.

**Human keys only.** It returns 403 `Human access required` to the agent key (sr-assistant
`api/export.py` uses `require_human_read`; sr-assistant#51 records the 403 against the
assistant's key). Do not retry it another way; ask Brian to run the export.

## API Reference

Endpoint and credentials in `/workspace/TOOLS.md`.
Auth: `X-API-Key` header (agent_readwrite key required for sync trigger and writes).
Base URL: `https://donor-management.fly.dev`

**Sync:**
```
POST /api/v1/sync/trigger              — trigger DonorHub sync
POST /api/v1/sync/trigger-addresses    — pull contact addresses from DonorHub
GET  /api/v1/sync/status               — connection state + sync log
GET  /api/v1/sync/pending              — items needing manual review
POST /api/v1/sync/pending/{id}/resolve — resolve a pending item
```

**Pledges:**
```
GET    /api/v1/pledges                 — list pledges (?contact_id=, ?active_only=)
GET    /api/v1/pledges/{id}            — pledge detail
POST   /api/v1/pledges                 — create pledge
PUT    /api/v1/pledges/{id}            — update pledge
DELETE /api/v1/pledges/{id}            — delete pledge
GET    /api/v1/pledges/frequencies     — list pledge frequencies
POST   /api/v1/pledges/{id}/deactivate — mark pledge inactive
```

**Export:**
```
POST /api/v1/export/mailing-list       — export newsletter mailing list CSV (human key only)
```
