---
name: donor-gifts
description: "Use when the user asks about giving data: 'who gave recently?', 'giving report', 'how much has [name] given?', 'record a gift', 'gift history', 'donations this year', 'how is the [appeal] campaign doing?', or wants to query or record gifts in the donor management system."
---

# Donor Gifts — Giving Data & Manual Entry

Query giving history and record manual gifts (e.g., IRA distributions, stock transfers) that don't come through the automated DonorHub sync.

## Invocation Triggers

**Queries:** "who gave recently?," "giving report," "how much has [name] given?," "gift history," "donations this year."

**Recording:** "record a gift," "log a donation," "enter an IRA distribution," "[name] gave $500."

**Campaigns:** "how is the [appeal] campaign doing?," "set up a campaign for the spring appeal," "which gifts came in under [campaign]?"

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
python3 /home/claude/.claude/skills/agent-skills/skills/donor-gifts/scripts/pledges.py "Pat Example"
python3 /home/claude/.claude/skills/agent-skills/skills/donor-gifts/scripts/pledges.py --contact-id 900001
```

(The absolute path is the deployed checkout; sessions run from `/workspace`, so a
repo-relative path would not resolve. `900001` is a placeholder, not a real contact.)

```
Example, Pat (contact 900001) — 1 pledge
  #501  $1,200.00 Annual since 2024-02-01 — current, good until 2026-12-31; last gift $1,250.00 on 2025-12-15
```

Read-only; `DONOR_API_KEY` from the environment, sent only over https and never on a
redirect; two requests, one at a time (a third, the frequency table, only for a
`frequency_id` outside the table below). Several name matches are listed with their ids
and the script exits 2 — rerun with `--contact-id`; an unknown `--contact-id` is also
exit 2 (`no contact N`), and 3 means the API failed. Ended pledges print `ended <date>`;
a fixed-term pledge still running prints its status and `through <date>`; a raised or
new pledge with no gift yet prints `awaiting first gift since <date>` — a raise sets that
field by TntConnect's Pledge Received rule; the retroactive-raise correction is in the
workspace `TOOLS.md`, SR Assistant section. `--json` prints the raw rows.

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

## Campaigns

A campaign is TntConnect's appeal idea: a label that gifts (through their splits), pledges,
history entries and tasks can carry, so one appeal's asks, commitments and giving can be
read together. The routes are live (brianroberg/sr-assistant#42, merged 2026-09-17), but
**as of 2026-10-19 no campaigns exist in production** (`GET /api/v1/campaigns` returned `[]`
that day). That is a snapshot, not a rule: call the list rather than assume, and treat an
empty result as expected rather than an error until Brian has created one.

Reads:

```
GET https://donor-management.fly.dev/api/v1/campaigns?is_active=true
GET https://donor-management.fly.dev/api/v1/campaigns/{id}
GET https://donor-management.fly.dev/api/v1/campaigns/{id}/summary
Header: X-API-Key: [from TOOLS.md]
```

The list comes newest first; `is_active` is optional, and `skip`/`limit` page it (default
100, max 500). A list row carries `id`, `name`, `is_active`, `begin_date`, `end_date` and
`goal`; the detail adds `description`, `created_at` and `updated_at`. `goal` and the
summary's amounts are strings, as pledge amounts are.

The summary is computed server-side, like the contact summary above. It returns
`campaign_id`, `as_of` (the server's date when it answered; the summary takes no date
parameter, so a figure as of a past date is not available from it) and three objects:
- `asks` — history entries carrying the campaign: `total`, `challenge`, `non_challenge`,
  `by_result` (rows of `{history_result_id, count}`, the null result last),
  `distinct_contacts_asked` (people on `is_challenge` entries, each once) and
  `distinct_contacts_all`.
- `commitments` — pledges carrying it: `count`, `active_count`, `monthly_equivalent`,
  `active_monthly_equivalent` (amount ÷ frequency months, summed; the active pair counts
  pledges still in force on `as_of`).
- `gifts` — gift splits carrying it: `split_count`, `total`.

A gift gets its label when it is created: `POST /api/v1/gifts` (under *Recording Manual
Gifts*) takes a `splits` array, each entry `{"campaign_id": 900010, "amount": 500.00}`
(a split may also carry `promise_id`, applying that same split to a pledge; the two keys
go together on one split when an appeal gift is also a pledge gift). `PUT /api/v1/gifts/{id}` has no
`splits` field, so a gift recorded without one stays unattributed short of deleting and
re-creating it; when Brian asks for a gift "under" an appeal, send the split in the POST.

Attribution changes how the pledge standing reads the gift (TntConnect's rule, in the
API's commitment-status service): a campaign-linked gift counts toward a pledge whose
period is six months or longer (semi-annual, annual, biennial) and is left out of the
standing of a shorter one (weekly through quad-monthly). A monthly donor's regular gift
recorded under an appeal therefore reads as a missed period. Attribute a gift when Brian
means it as an appeal gift, and say so when the donor has a short-period pledge.

Each list endpoint that carries the label filters by it (`900010` is a placeholder, not a
real campaign). The history, task and pledge reads and writes themselves are documented
in `donor-log`, `donor-tasks` and `donor-sync` without the campaign label; the label is
this section's. `campaign_id` is an optional key on the POST and PUT bodies for history
entries (`donor-log`), tasks (`donor-tasks`) and pledges (`donor-sync`): add it to that
skill's body to log an ask, task or commitment under an appeal, send `"campaign_id": null`
on PUT to detach one, and expect a 400 `Invalid campaign_id` for an id that does not exist:

```
GET /api/v1/gifts?campaign_id=900010
GET /api/v1/pledges?campaign_id=900010
GET /api/v1/history?campaign_id=900010
GET /api/v1/tasks?campaign_id=900010
Header: X-API-Key: [from TOOLS.md]
```

An ask counts in the summary's `challenge` and `distinct_contacts_asked` when the history
entry carries `is_challenge: true` as well as `campaign_id`; with `campaign_id` alone it
counts in `total` and `distinct_contacts_all`. Set `is_challenge` when logging an ask under
an appeal (`donor-log`'s example body leaves it false).

The gifts filter lists whole gifts that have at least one split under the campaign (each
once), with the gift's full `amount`; the summary's `gifts.total` sums the attributed split
amounts. The two differ when a gift is split across campaigns, so report the summary
figure as the campaign's giving and the list as the gifts behind it.

**Writes** (agent_readwrite key). Send one when Brian asked for that specific change; if
the permission check refuses it, write out the exact request — route, id and body — and
hand it to him rather than retrying another way.

```
POST https://donor-management.fly.dev/api/v1/campaigns
Header: X-API-Key: [from TOOLS.md]
Body: {
  "name": "Spring Appeal (example)",
  "description": "Placeholder campaign for the skill text",
  "begin_date": "2026-03-01",
  "end_date": "2026-05-31",
  "goal": 25000.00
}
```

`name` is required (1–100 characters); `description`, `begin_date`, `end_date` and `goal`
are optional and `is_active` defaults to true. `goal`, when sent, is a positive amount with
at most two decimal places (`0` and `25000.005` are each a 422); to remove a goal on PUT
send `null`, not `0`. Returns 201 with the full campaign. Both writes run the begin/end
ordering check and answer 422 when it fails.

```
PUT https://donor-management.fly.dev/api/v1/campaigns/{id}
Header: X-API-Key: [from TOOLS.md]
Body: { "is_active": false }
```

PUT has PATCH semantics: an omitted key is untouched, and an explicit null for
`begin_date`, `end_date` or `goal` clears it. A null `name` or `is_active` is a 422.

```
DELETE https://donor-management.fly.dev/api/v1/campaigns/{id}
Header: X-API-Key: [from TOOLS.md]
```

Deletes the campaign row itself (204). While a gift split, pledge, history entry or task
still references it the API refuses with 409; its `detail` names each kind of referrer in
prose (history entries, pledges, tasks, gift splits) with what can be done about it, and
the attributions are not nulled. A second 409, "still referenced by rows written after the
reference check", means a reference landed mid-delete: retry once those rows are
reassigned. Pledges, history entries and tasks can be moved off it
with their own PUT (`campaign_id`); a gift split cannot be re-pointed through the API (the
409 says so), so a gift under the campaign stays there short of deleting and re-creating
the gift, which *Deleting Gifts* rules out for a synced one. To retire an appeal that has
activity under it, set `is_active: false` instead.

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
- `splits` — optional list of `{campaign_id, promise_id, amount}` allocations (see
  *Campaigns*); split amounts may sum to less than `amount` but not more (422), and a
  `campaign_id` or `promise_id` that does not exist is a 400

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
GET /api/v1/campaigns               — list campaigns (?is_active=true|false)
GET /api/v1/campaigns/{id}          — campaign detail
GET /api/v1/campaigns/{id}/summary  — asks, commitments and gifts attributed to a campaign
```

`?campaign_id=N` also filters `GET /api/v1/gifts`, `/pledges`, `/history` and `/tasks`.

**Write:**
```
POST   /api/v1/gifts                — create manual gift
PUT    /api/v1/gifts/{id}           — update gift (memo, payment_method only)
DELETE /api/v1/gifts/{id}           — delete gift
POST   /api/v1/campaigns            — create campaign (201)
PUT    /api/v1/campaigns/{id}       — update campaign (omitted keys untouched)
DELETE /api/v1/campaigns/{id}       — delete campaign (204; 409 while anything references it)
```
