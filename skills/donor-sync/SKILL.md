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

## DonorHub Sync

The donor management system syncs gifts and contact data from DonorHub (an external donation processing platform). Sync can be triggered manually and produces a log of what was imported.

### Trigger a Sync

```
POST https://donor-management.fly.dev/api/v1/sync/trigger
Header: X-API-Key: [from TOOLS.md]
```

Runs the donation import from DonorHub. Returns immediately with a job status — the actual import runs asynchronously.

### Pull Addresses from DonorHub

```
POST https://donor-management.fly.dev/api/v1/sync/trigger-addresses
Header: X-API-Key: [from TOOLS.md]
```

Pulls contact addresses **from** DonorHub (the upstream donation-processing system, which
Brian does not control) into the donor management system. This is the only address-related
route the API has: addresses cannot be created or edited through the contact endpoints, so
a wrong address cannot be corrected from here — see sr-assistant issue #21. The sync only
*creates* an address where a contact has none; a differing remote value becomes a pending
item for manual review rather than an overwrite.

### Check Sync Status

```
GET https://donor-management.fly.dev/api/v1/sync/status
Header: X-API-Key: [from TOOLS.md]
```

Returns:
- Connection state (connected, disconnected, error)
- Last sync timestamp
- Last 10 sync log entries (imported count, errors, etc.)

### Pending Sync Items

```
GET https://donor-management.fly.dev/api/v1/sync/pending
Header: X-API-Key: [from TOOLS.md]
```

Items that need manual review — typically address conflicts, duplicate contacts, or unmatched gifts that couldn't be auto-resolved.

### Resolve Pending Item

```
POST https://donor-management.fly.dev/api/v1/sync/pending/{id}/resolve
Header: X-API-Key: [from TOOLS.md]
```

Marks a pending sync item as resolved after manual review.

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
POST /api/v1/export/mailing-list       — export newsletter mailing list CSV
```
