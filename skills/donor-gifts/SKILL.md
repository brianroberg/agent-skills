---
name: donor-gifts
description: "Use when the user asks about giving data: 'who gave recently?', 'giving report', 'how much has [name] given?', 'record a gift', 'gift history', 'donations this year', or wants to query or record gifts in the donor management system."
---

# Donor Gifts — Giving Data & Manual Entry

Query giving history and record manual gifts (e.g., IRA distributions, stock transfers) that don't come through the automated DonorHub sync.

## Invocation Triggers

**Queries:** "who gave recently?," "giving report," "how much has [name] given?," "gift history," "donations this year."

**Recording:** "record a gift," "log a donation," "enter an IRA distribution," "[name] gave $500."

## Querying Gifts

### List Gifts

```
GET https://donor-management.fly.dev/api/v1/gifts
Header: X-API-Key: [from TOOLS.md]
```

Returns all gifts. Filter by contact:

```
GET https://donor-management.fly.dev/api/v1/gifts?contact_id={id}
Header: X-API-Key: [from TOOLS.md]
```

### Gift Detail

```
GET https://donor-management.fly.dev/api/v1/gifts/{id}
Header: X-API-Key: [from TOOLS.md]
```

Returns full gift record including splits (campaign/promise allocation).

### Contact Giving Summary

The most efficient way to get giving stats — computed server-side:

```
GET https://donor-management.fly.dev/api/v1/contacts/{id}/summary
Header: X-API-Key: [from TOOLS.md]
```

Returns:
- Lifetime giving total
- Year-to-date giving
- Last 12-month giving
- Last gift date and amount
- Average gift amount
- Active pledge totals

## Pledges

A pledge is what a donor has said they will give, on a schedule; gifts are what arrived.
For "what pledge is recorded for [name]?" run the script, which does the search, the
pledge read and the frequency lookup in one go and prints one line per pledge:

```
python3 skills/donor-gifts/scripts/pledges.py "Pat Example"
python3 skills/donor-gifts/scripts/pledges.py --contact-id 1001
```

```
Example, Pat (contact 1001) — 1 pledge
  #501  $1,200.00 Annual since 2024-02-01 — current, good until 2026-12-31; last gift $1,250.00 on 2025-12-15
```

Read-only; `DONOR_API_KEY` from the environment; three requests at most, one at a time.
Several name matches are listed with their ids and the script exits 2 — rerun with
`--contact-id`. Ended pledges print `ended <date>`; a raised or new pledge with no gift yet
prints `awaiting first gift since <date>` (see `donor-sync` for why a raise sets that).
`--json` prints the raw rows.

The raw reads, if you need a field the report leaves out:

```
GET /api/v1/pledges?contact_id={id}&active_only=false
GET /api/v1/pledges/frequencies
Header: X-API-Key: [from TOOLS.md]
```

`GET /api/v1/pledges` defaults to `active_only=true`. Each row carries `amount` (a string),
`frequency_id`, `start_date`, `end_date`, `is_active`, `awaiting_first_gift_since`,
`campaign_id`, and a `status` object (`state` such as `current` or `outstanding`,
`good_until`, `last_gift_date`, `last_gift_amount`, `behind_periods`), computed by TntConnect's
Good Until rule. `frequency_id` maps through the frequency table, stable since the
February 2026 migration (the script reads the live table and falls back to this one):

| id | name | months |
|---|---|---|
| 1 | Monthly | 1 |
| 2 | Quarterly | 3 |
| 3 | Semi-Annual | 6 |
| 4 | Annual | 12 |
| 5 | Bi-Monthly | 2 |
| 6 | Quad-Monthly | 4 |
| 7 | Biennial | 24 |
| 8 | Weekly | 0.23 |
| 9 | Fortnightly | 0.46 |

Pledge writes (create, raise, end) are in `donor-sync`.

## Recording Manual Gifts

For gifts that don't come through DonorHub sync (IRA distributions, stock transfers, in-kind gifts, checks received directly):

### Step 1: Find the Contact

```
GET https://donor-management.fly.dev/api/v1/contacts?search=<name>
Header: X-API-Key: [from TOOLS.md]
```

### Step 2: Create the Gift

```
POST https://donor-management.fly.dev/api/v1/gifts
Header: X-API-Key: [from TOOLS.md]
Body: {
  "contact_id": 42,
  "gift_date": "2026-03-01",
  "amount": 500.00,
  "memo": "IRA distribution",
  "payment_method": "check"
}
```

**Fields:**
- `contact_id` (required) — donor's contact ID
- `gift_date` (required) — date the gift was received (ISO date)
- `amount` (required) — gift amount as a decimal
- `memo` — description/purpose of the gift
- `payment_method` — how the gift was made (check, cash, stock, wire, etc.)

**Important:** Do NOT set `external_gift_code` for manual gifts — leave it null. This field is used by the DonorHub sync to track imported gifts. Setting it on a manual gift could cause sync conflicts.

### Step 3: Confirm

> Recorded: $500.00 gift from John Smith on Mar 1 (IRA distribution)

## Updating Gifts

```
PUT https://donor-management.fly.dev/api/v1/gifts/{id}
Header: X-API-Key: [from TOOLS.md]
Body: { "memo": "...", "payment_method": "..." }
```

Only `memo` and `payment_method` are updatable on existing gifts. Amount and date changes require deleting and re-creating.

## Deleting Gifts

```
DELETE https://donor-management.fly.dev/api/v1/gifts/{id}
Header: X-API-Key: [from TOOLS.md]
```

Only for manual gifts entered in error. Never delete synced gifts (those with `external_gift_code` set) — the sync will re-import them.

## Presentation

Format currency amounts consistently:
- `$1,250.00` (always two decimal places)
- Use comma separators for thousands

When showing giving history, format as a table:

```
Giving History — John Smith
─────────────────────────────────
Date        Amount      Memo
Mar 1       $500.00     IRA distribution
Jan 15      $200.00     Monthly pledge
Dec 20      $1,000.00   Year-end gift
─────────────────────────────────
YTD: $700.00 · Lifetime: $12,500.00
```

## API Reference

Endpoint and credentials in `/workspace/TOOLS.md`.
Auth: `X-API-Key` header (agent_readwrite key required for writes).
Base URL: `https://donor-management.fly.dev`

**Query:**
```
GET /api/v1/gifts                   — list gifts (?contact_id=N)
GET /api/v1/gifts/{id}              — gift detail (with splits)
GET /api/v1/contacts/{id}/summary   — computed giving stats
GET /api/v1/pledges                 — list pledges (?contact_id=N&active_only=false)
GET /api/v1/pledges/frequencies     — frequency ids → names (table above)
```

**Write:**
```
POST   /api/v1/gifts                — create manual gift
PUT    /api/v1/gifts/{id}           — update gift (memo, payment_method only)
DELETE /api/v1/gifts/{id}           — delete gift
```
