---
name: sr-contact-lookup
description: "Use when the user asks to look up a donor, find contact info, check giving history, view pledges, or get a summary of a ministry partner. Triggers: 'look up [name]', 'who is [name]', 'donor info', 'contact details', 'giving summary', 'how much does [name] give', 'pledge info', 'find donor', 'search contacts'."
---

# SR Contact Lookup

Search for and view donor/contact information in the SR Assistant (Donor Management) system.
Read-only operations for finding contacts, viewing details, and checking giving/activity summaries.

## Prerequisites

Connection details (URL and API key) are in `/workspace/TOOLS.md` under "SR Assistant".
The URL may change between Codespace sessions — always read from TOOLS.md.

## Endpoints

### 1. Search Contacts

Find contacts by name. Returns a compact list for identification.

```bash
curl -s "$SR_URL/api/v1/contacts?search=Johnson&limit=20" \
    -H "X-API-Key: $SR_KEY" | jq .
```

Parameters:
- `search`: Name search (matches first, last, org name, file_as)
- `skip`: Pagination offset (default: 0)
- `limit`: Max results (default: 100, max: 500)

Returns per contact: `id`, `file_as`, `first_name`, `last_name`, `spouse_first_name`, `is_organization`, `org_name`

### 2. Get Full Contact Detail

Get all info for a specific contact — personal info, spouse, addresses, phones, emails, linked external donors.

```bash
curl -s "$SR_URL/api/v1/contacts/{contact_id}" \
    -H "X-API-Key: $SR_KEY" | jq .
```

Key fields in response:
- **Names**: `title`, `first_name`, `last_name`, `nickname`, `file_as`, `greeting`, `salutation`
- **Spouse**: `spouse_title`, `spouse_first_name`, `spouse_last_name`, `spouse_nickname`
- **Personal**: `children`, `interests`, `spouse_interests`, `profession`, `spouse_profession`, `church_name`
- **Relationship**: `referred_by`, `notes`
- **Newsletter**: `send_newsletter`, `newsletter_preference` (email/print/both)
- **MPD**: `mpd_phase_id`, `likely_to_give_id`, `never_ask`, `next_ask_date`, `next_ask_amount`
- **Family**: `family_side_id`, `family_level_id`
- **Status**: `deceased`
- **Sub-objects**: `addresses[]`, `phones[]`, `emails[]`, `external_donors[]`

### 3. Get Contact Summary

Computed summary with giving stats, activity dates, and pledge info — the quick-glance view.

```bash
curl -s "$SR_URL/api/v1/contacts/{contact_id}/summary" \
    -H "X-API-Key: $SR_KEY" | jq .
```

Returns three sections:

**Giving:**
- `first_gift_date`, `last_gift_date`
- `lifetime_total`, `lifetime_gift_count`, `largest_gift`
- `year_to_date_total`, `twelve_month_total`

**Activity:**
- `last_activity_date` (any type)
- `last_call_date`, `last_letter_date`, `last_visit_date`, `last_thank_date`

**Pledges:**
- `monthly_pledge_equivalent` (all active pledges normalized to monthly)

### 4. List Gifts for a Contact

```bash
curl -s "$SR_URL/api/v1/gifts?contact_id={contact_id}&limit=50" \
    -H "X-API-Key: $SR_KEY" | jq .
```

Returns: `id`, `contact_id`, `gift_date`, `amount`, `memo`, `payment_method`

### 5. List Pledges for a Contact

```bash
curl -s "$SR_URL/api/v1/pledges?contact_id={contact_id}" \
    -H "X-API-Key: $SR_KEY" | jq .
```

Add `&active_only=false` to include inactive pledges.

Returns: `id`, `contact_id`, `amount`, `frequency_id`, `start_date`, `end_date`, `is_active`

Pledge frequencies (from `/api/v1/pledges/frequencies`):
- Check the API for current frequency IDs and their month equivalents

## Common Workflows

### "Tell me about [name]"

1. Search: `GET /api/v1/contacts?search=[name]`
2. If multiple results, pick the best match (or ask user to clarify)
3. Get detail: `GET /api/v1/contacts/{id}`
4. Get summary: `GET /api/v1/contacts/{id}/summary`
5. Present: name, spouse, address, giving summary, last activity dates, current pledge

### "How much does [name] give?"

1. Search for contact
2. Get summary for the quick view (monthly pledge equivalent, YTD, lifetime)
3. If user wants more detail, list gifts

### "When did I last contact [name]?"

1. Search for contact
2. Get summary — check `last_call_date`, `last_letter_date`, `last_visit_date`

## Presentation Tips

- Use `greeting` or `file_as` when referring to the contact conversationally
- Format currency with dollar signs and commas
- Convert dates to readable format, note how long ago (e.g., "Last called Nov 30, 2018 — over 7 years ago")
- Flag stale relationships: if last activity is >1 year ago, note it
- If `deceased` is true, note it prominently
