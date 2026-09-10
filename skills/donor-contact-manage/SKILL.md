---
name: donor-contact-manage
description: "Use when the user wants to create, update, or delete a contact in the donor system, or manage groups: 'add a new contact', 'update [name]'s address', 'create a group', 'add [name] to the [group] group', 'remove contact', 'manage groups'."
---

# Donor Contact Manage — Contact CRUD & Groups

Create, update, and delete contacts in the donor management system, correct their
addresses / emails / phones, and manage contact groups.

## Invocation Triggers

**Contacts:** "add a new contact," "create a contact for [name]," "update [name]'s address," "change [name]'s phone number," "delete [name]'s record."

**Groups:** "create a group," "show groups," "add [name] to [group]," "remove [name] from [group]."

## Vocabulary the API actually accepts

These are the values and keys the API defines (`schemas/contact_subresources.py` at
brianroberg/sr-assistant#46, head `162e128`; the address keys have been these since the
schema was written — the API has never accepted `"street"` or `"zip"`):

- `address_type` — one of `home`, `business`, `other`, `spouse_business`
- `phone_type` — one of `home`, `mobile`, `business`, `spouse_mobile`
- `email_type` — one of `personal`, `business`, `spouse`
- Address keys: `address_type`, `street_address`, `city`, `state`, `postal_code`, `country`,
  `is_primary`, `is_deliverable`
- Phone keys: `phone_type`, `number`, `is_primary`, `is_valid`
- Email keys: `email_type`, `address`, `is_primary`, `is_valid`

A value outside these lists — notably *work*, which an earlier version of this skill
documented for all three, and *other* for phones and emails — is rejected with a **422** by
the sub-resource routes below. `POST /api/v1/contacts`'s nested lists still accept any
string (deliberately left alone by #46; tightening is sr-assistant #19), but a row stored
with an undocumented value will not round-trip through GET-then-PATCH, so send only the
listed values there too.

## Contact Operations

### Create a Contact

```
POST https://donor-management.fly.dev/api/v1/contacts
Header: X-API-Key: [from TOOLS.md]
Body: {
  "first_name": "John",
  "last_name": "Smith",
  "org_name": "",
  "file_as": "Smith, John",
  "addresses": [
    {
      "address_type": "home",
      "street_address": "123 Main St",
      "city": "Portland",
      "state": "OR",
      "postal_code": "97201",
      "country": "USA",
      "is_primary": true,
      "is_deliverable": true
    }
  ],
  "phones": [
    {
      "phone_type": "mobile",
      "number": "503-555-1234",
      "is_primary": true,
      "is_valid": true
    }
  ],
  "emails": [
    {
      "email_type": "personal",
      "address": "john@example.com",
      "is_primary": true,
      "is_valid": true
    }
  ]
}
```

**Fields:**
- `first_name`, `last_name` — at least one is required
- `org_name` — organization name (for org contacts, can be used instead of first/last)
- `file_as` — how the contact is sorted/displayed (auto-generated if omitted)
- `addresses`, `phones`, `emails` — optional arrays using the keys and type values listed
  under *Vocabulary* above. After sr-assistant#46: two `is_primary: true` rows in one list
  are a 422 (nothing written), and a non-empty list with no primary gets its first row
  promoted.

Addresses, phones, and emails are optional — a contact can be created with just a name.

### Update a Contact's own fields

`PUT /api/v1/contacts/{id}` is **partial** despite the verb: omitted fields are left alone
(`exclude_unset` semantics, sr-assistant #19), an explicit JSON `null` clears a field. It
takes the contact's own fields only — `ContactUpdate` has no `addresses`, `phones` or
`emails` keys, so a nested list in the body does not update those rows. Address, email
and phone corrections go through the sub-resource routes in the next section.

Do not issue this PUT with raw `curl` — it is classifier-blocked. Use the sanctioned
wrapper, which is pre-approved by an allow rule in `.claude/settings.local.json`:

```
/workspace/scripts/donor-update-contact.sh <contact_id> '<json_object>'
```

It refuses a non-numeric id or a non-object body, backs the record up to
`local/donor-backups/` first, then prints a field-level diff of what changed. **Read the
diff, not the status code** — the diff is what proves the write did only what was asked.
Invoke it as a standalone Bash command (a compound command defeats the allow rule).

To find the contact ID first:
```
GET https://donor-management.fly.dev/api/v1/contacts?search=<name>
Header: X-API-Key: [from TOOLS.md]
```

### Addresses, emails and phones (sub-resource routes)

**Availability: these routes come from brianroberg/sr-assistant#46, which is not yet
deployed as of 2026-09-09.** Deploys are manual (`fly deploy`), so "merged" and "live" are
different questions. Check before relying on them:

```bash
curl -sS --max-time 20 https://donor-management.fly.dev/openapi.json \
    | jq -r '.paths | keys[] | select(test("/contacts/\\{contact_id\\}/(addresses|emails|phones)"))'
```

Empty output means #46 is not deployed: a contact's addresses, emails and phones can then
only be set at creation and cannot be corrected through the API at all (sr-assistant #21).
Say so rather than improvising a PUT.

One set of routes per collection, nested under the contact:

```
GET    /api/v1/contacts/{contact_id}/addresses               — list the contact's addresses
POST   /api/v1/contacts/{contact_id}/addresses               — add an address (201)
PATCH  /api/v1/contacts/{contact_id}/addresses/{address_id}  — partial update
DELETE /api/v1/contacts/{contact_id}/addresses/{address_id}  — delete (204)

GET    /api/v1/contacts/{contact_id}/emails                  — list the contact's emails
POST   /api/v1/contacts/{contact_id}/emails                  — add an email (201)
PATCH  /api/v1/contacts/{contact_id}/emails/{email_id}       — partial update
DELETE /api/v1/contacts/{contact_id}/emails/{email_id}       — delete (204)

GET    /api/v1/contacts/{contact_id}/phones                  — list the contact's phones
POST   /api/v1/contacts/{contact_id}/phones                  — add a phone (201)
PATCH  /api/v1/contacts/{contact_id}/phones/{phone_id}       — partial update
DELETE /api/v1/contacts/{contact_id}/phones/{phone_id}       — delete (204)
```

Bodies use the keys under *Vocabulary*. PATCH is partial: an omitted key keeps its stored
value; an explicit `null` clears one of the nullable address fields (`street_address`,
`city`, `state`, `postal_code`, `country`); `address_type` / `phone_type` / `email_type` /
`is_primary` and the flags reject `null`; `number` and `address` reject `""`. An unknown
key is a 422 (`extra="forbid"`), so a typo writes nothing.

**Rules the API enforces (from #46):**

- **At most one primary per collection per contact**, enforced by a database index.
  Sending `is_primary: true` on POST or PATCH demotes the previous primary in the same
  transaction.
- **A collection written through these routes has exactly one primary whenever it has
  rows.** The first row added is primary whatever `is_primary` it was sent with. Deleting
  the primary, or PATCHing it to `is_primary: false`, promotes the successor: the oldest
  row flagged usable (`is_deliverable` for addresses, `is_valid` for emails/phones), and a
  flagged row only when nothing else exists. A collection that already had rows but no
  primary (importer output) is repaired by the first write through these routes.
- **409** on PATCHing the *only* row to `is_primary: false` — "cannot demote the only
  address; add another or delete this one". Add a row or delete instead.
- **409** on a write that loses a race against a concurrent promotion — re-read the
  collection and retry.
- **404** for a row reached through the wrong contact's URL; a write can never touch
  another contact's row.
- **422** for a type value outside the lists above or an unknown key.
- The contact row itself (`file_as`, names, `updated_at`) is untouched by a sub-resource
  write.

**To correct an address, PATCH it — do not DELETE and re-POST.** Deleting a contact's only
address then running the DonorHub address sync recreates one from DonorHub's record; a
PATCHed address is kept and a differing DonorHub value is queued as an `address_conflict`
review item instead (sr-assistant #44 defines how that gets resolved).

**How to call them from here:**

- The `GET` list routes are reads and can be issued with `curl` as usual.
- **Raw `curl` writes to this API are classifier-blocked** (`POST`, `PATCH`, `DELETE`
  alike — the same block that made the contact wrapper necessary). The only existing
  wrapper, `/workspace/scripts/donor-update-contact.sh`, is deliberately scoped to
  `PUT /api/v1/contacts/{id}` and cannot reach these routes. **Sub-resource writes need
  new wrapper scripts plus allow rules in `.claude/settings.local.json` that do not exist
  yet** — and the allow rule is Brian's to add, since editing that file is itself blocked.
  Until they exist, do not attempt a raw `curl` write: state the exact change needed
  (contact id, collection, row id, fields) and hand it to Brian.

### Delete a Contact

```
DELETE https://donor-management.fly.dev/api/v1/contacts/{id}
Header: X-API-Key: [from TOOLS.md]
```

**Confirm before deleting.** This removes the contact and disassociates (but does not delete) their gifts, history, and tasks. This action cannot be undone.

## Group Operations

Groups are collections of contacts used for bulk operations (mailings, reports, etc.).

### List Groups

```
GET https://donor-management.fly.dev/api/v1/groups
Header: X-API-Key: [from TOOLS.md]
```

### Get Group with Members

```
GET https://donor-management.fly.dev/api/v1/groups/{id}
Header: X-API-Key: [from TOOLS.md]
```

Returns the group and its member contacts.

### Create a Group

```
POST https://donor-management.fly.dev/api/v1/groups
Header: X-API-Key: [from TOOLS.md]
Body: {
  "name": "Board Members",
  "description": "Current board of directors"
}
```

### Update a Group

```
PUT https://donor-management.fly.dev/api/v1/groups/{id}
Header: X-API-Key: [from TOOLS.md]
Body: { "name": "...", "description": "..." }
```

### Delete a Group

```
DELETE https://donor-management.fly.dev/api/v1/groups/{id}
Header: X-API-Key: [from TOOLS.md]
```

Deleting a group does not delete its member contacts.

### Add Contacts to a Group

```
POST https://donor-management.fly.dev/api/v1/groups/{id}/contacts
Header: X-API-Key: [from TOOLS.md]
Body: {
  "contact_ids": [42, 43, 87]
}
```

### Remove Contacts from a Group

```
DELETE https://donor-management.fly.dev/api/v1/groups/{id}/contacts
Header: X-API-Key: [from TOOLS.md]
Body: {
  "contact_ids": [42]
}
```

## Important Notes

- Agent API keys cannot read or write `confidential_notes` on contacts — this is by design.
- `PUT /api/v1/contacts/{id}` updates the contact's own fields only and leaves omitted
  fields alone; it never touches addresses, phones or emails. Those are corrected one row
  at a time through the sub-resource routes above (once sr-assistant#46 is deployed).
- Always diff a donor write; never trust the response status. The contact wrapper prints
  the diff for you.
- The `file_as` field controls sort order. Convention: "LastName, FirstName" for individuals, org name for organizations.

## API Reference

Endpoint and credentials in `/workspace/TOOLS.md`.
Auth: `X-API-Key` header (agent_readwrite key required for writes).
Base URL: `https://donor-management.fly.dev`

**Contacts:**
```
GET    /api/v1/contacts              — search/list contacts (?search=query)
GET    /api/v1/contacts/{id}         — contact detail
POST   /api/v1/contacts              — create contact
PUT    /api/v1/contacts/{id}         — update contact (partial; own fields only; via the wrapper)
DELETE /api/v1/contacts/{id}         — delete contact
```

**Contact addresses / emails / phones** (sr-assistant#46; see *Availability* above):
```
GET    /api/v1/contacts/{contact_id}/{addresses|emails|phones}
POST   /api/v1/contacts/{contact_id}/{addresses|emails|phones}
PATCH  /api/v1/contacts/{contact_id}/{addresses|emails|phones}/{row_id}
DELETE /api/v1/contacts/{contact_id}/{addresses|emails|phones}/{row_id}
```

**Groups:**
```
GET    /api/v1/groups                — list groups
GET    /api/v1/groups/{id}           — group with members
POST   /api/v1/groups                — create group
PUT    /api/v1/groups/{id}           — update group
DELETE /api/v1/groups/{id}           — delete group
POST   /api/v1/groups/{id}/contacts  — add contacts to group
DELETE /api/v1/groups/{id}/contacts  — remove contacts from group
```
