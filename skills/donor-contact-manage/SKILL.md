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
brianroberg/sr-assistant#46, merged as `b9d1f13`; the address keys match the live
`AddressCreate` schema, which has no street or zip key):

- `address_type` — one of `home`, `business`, `other`, `spouse_business`
- `phone_type` — one of `home`, `mobile`, `business`, `spouse_mobile`
- `email_type` — one of `personal`, `business`, `spouse`
- Address keys: `address_type`, `street_address`, `city`, `state`, `postal_code`, `country`,
  `is_primary`, `is_deliverable`
- Phone keys: `phone_type`, `number`, `is_primary`, `is_valid`
- Email keys: `email_type`, `address`, `is_primary`, `is_valid`

A value outside these lists — notably *work*, which an earlier version of this skill
documented for all three, and *other* for phones and emails — is rejected with a **422** by
the sub-resource routes below. `POST /api/v1/contacts` is looser in two ways, and both
failures are **silent**: its nested lists accept any type string (deliberately left alone
by #46; tightening is sr-assistant #19), and its nested schemas do not forbid unknown keys
(no `additionalProperties: false` in the live `openapi.json`), so the old street / zip keys
produced a 201 and an address with no street or postal code rather than an error. A row
stored with an undocumented type cannot have that type echoed back through PATCH either.
Send only the listed keys and values on create as well.

A row read back from GET is **not** a valid write body: it also carries `id` and
`contact_id` (and `address_block` for addresses), which the sub-resource routes reject
with a 422. Send only the keys you are changing.

## Writes and the permission check

**Send the write when Brian asked for that specific change.** Every write in this skill
except the contact PUT is a plain request with the agent key; `PUT /api/v1/contacts/{id}`
goes through its wrapper (see *Update a Contact's own fields*).

**If the permission check refuses a write, do not retry it another way** (another tool, a
script, a reworded command). Write out the exact change — route, ids and body — and hand
it to Brian.

What that rests on: on 2026-09-24 the assistant sent these as raw `curl` from its main
session, each named by Brian, and none was refused or needed approval — contact create and
delete, address POST / PATCH / DELETE, group create / rename / delete, and adding and
removing group members (the request log is in the commit that added this section). The
email and phone routes were not tried. The permission check's rules are not known, so other
sessions, subagents, untried routes and writes Brian did not name may be treated
differently: a `POST /api/v1/sync/trigger` was refused on 2026-09-22 (sr-assistant#67,
which does not say how it was requested).

No wrapper means no automatic diff: GET the record before and after a write and compare.

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
(`exclude_unset` semantics, sr-assistant #19), an explicit JSON `null` clears a nullable
field (`file_as: null` instead regenerates the label from the name fields, and `null` on
a boolean such as `deceased` or `file_as_custom` is a 422). It
takes the contact's own fields only — `ContactUpdate` has no `addresses`, `phones` or
`emails` keys, so a nested list in the body does not update those rows. Address, email
and phone corrections go through the sub-resource routes in the next section.

Send this PUT through the sanctioned wrapper, not raw `curl`: a raw PUT has been refused
by the permission check before (recorded in `/workspace/TOOLS.md`), and the wrapper is
pre-approved by an allow rule in `.claude/settings.local.json`:

```
/workspace/scripts/donor-update-contact.sh <contact_id> '<json_object>'
```

It refuses a non-numeric id or a non-object body, backs the record up to
`local/donor-backups/` first, then prints a field-level diff of what changed. **Read the
diff, not the status code** — the diff is what proves the write did only what was asked.
Invoke it as a standalone Bash command (a compound command defeats the allow rule).
The body is single-quoted, so an apostrophe in a value (O'Brien) would end the quote:
write it as the JSON escape `\u0027` instead — `'{"last_name": "O\u0027Brien"}'` —
which keeps the call a single standalone command.

To find the contact ID first:
```
GET https://donor-management.fly.dev/api/v1/contacts?search=<name>
Header: X-API-Key: [from TOOLS.md]
```

### Addresses, emails and phones (sub-resource routes)

**Availability:** these routes come from brianroberg/sr-assistant#46, merged and live since
2026-09-24 (sr-assistant deploys to Fly on every push to `main`). If one of them
unexpectedly 404s, check the live spec:

```bash
curl -fsS --max-time 20 https://donor-management.fly.dev/openapi.json \
    | jq -r '[.paths | keys[] | select(test("/contacts/\\{contact_id\\}/(addresses|emails|phones)"))] | length'
```

`6` means the routes are live. `0` means they are gone from the live spec: a contact's
addresses, emails and phones can then only be set at creation and cannot be corrected
through the API at all (sr-assistant #21) — say so rather than improvising a PUT. **No
number at all** (an error on stderr instead) means the check itself failed — report that;
it says nothing about whether the routes exist.

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
  row flagged usable (`is_deliverable: true` for addresses, `is_valid: true` for
  emails/phones); a row flagged unusable is promoted only when no usable row remains. A
  collection that already had rows but no primary (importer output) is repaired by the
  first write through these routes.
- **409** on PATCHing the *only* row to `is_primary: false`, whether or not it is currently
  primary — "cannot store is_primary:false on the only address: the only row of a
  collection is its primary; omit the key, send true, add another row, or delete this
  one". Omit `is_primary`, add a row, or delete instead.
- **409** on a write that loses a race against a concurrent promotion — re-read the
  collection and retry.
- **404** for a row reached through the wrong contact's URL; #46's tests pin that a PATCH
  or DELETE through the wrong contact cannot reach another contact's row.
- **422** for a type value outside the lists above or an unknown key.
- The contact row itself (`file_as`, names, `updated_at`) is untouched by a sub-resource
  write.

**To correct an address, PATCH it — do not DELETE and re-POST.** The DonorHub address sync
compares its record with the contact's primary address and, when the contact has no
primary address, creates one from DonorHub's (possibly stale) record. A PATCH keeps the row
and its id in place, so a differing DonorHub value is only queued as an `address_conflict`
review item (sr-assistant #44 defines how that gets resolved). A DELETE opens a window —
permanent if the re-POST never happens — in which a sync run recreates the address from
DonorHub.

**How to call them from here:** as plain requests, like the rest of this skill (see
*Writes and the permission check*). The contact wrapper, `/workspace/scripts/donor-update-contact.sh`,
is scoped to `PUT /api/v1/contacts/{id}` and cannot reach these routes, so diff by hand:
GET the collection before and after the write and compare the rows.

### Delete a Contact

```
DELETE https://donor-management.fly.dev/api/v1/contacts/{id}
Header: X-API-Key: [from TOOLS.md]
```

**Confirm before deleting, and say what will be lost.** A delete that succeeds also
permanently deletes the contact's gifts (with their splits), pledges, addresses, emails
and phones, and its DonorHub donor link, in the same request. Its history entries, tasks
and groups are kept; the contact is unlinked from each of them. None of it can be undone.
If the contact was linked to DonorHub, the next gift the DonorHub sync imports for that
donor creates a new contact holding only a name. (sr-assistant `models/contact.py` at
`b9d1f13`: those collections are `cascade="all, delete-orphan"`; history, tasks and
groups are joined through link tables.) Before asking, check
`GET /api/v1/contacts/{id}/summary` — its `giving` block has the lifetime gift count and
total that the delete would remove.

**A contact with gifts imported by the DonorHub sync cannot be deleted** at `b9d1f13`: the
request fails with a 500 (a foreign-key error between those gifts and the DonorHub donor
link) and nothing is deleted. Reproduced against a copy of the server code, not tried on
the live API. Do not work around it — for example by deleting the gifts or the link
first; tell Brian.

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
  "name": "Board Members"
}
```

`name` is required. Optional: `parent_group_id` (nests it under another group; 400 if that
group does not exist) and `contact_ids` (initial members; 400 if any id does not exist).
Groups have no description field. The group schemas ignore keys they do not define, so a
`description`, or a misspelt optional key (`contact_idz` leaves the group with no
members), gets a 201 and is silently dropped (sr-assistant `schemas/group.py` at
`b9d1f13`). A missing or misspelt `name` is a 422.

### Update a Group

```
PUT https://donor-management.fly.dev/api/v1/groups/{id}
Header: X-API-Key: [from TOOLS.md]
Body: { "name": "..." }
```

Takes `name` and/or `parent_group_id`; omitted keys are left alone. Unknown keys are
dropped silently, as on create.

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

- Agent API keys cannot read or write `confidential_notes`, a field on history entries and
  tasks (contacts have none): it is left out of responses and silently dropped from writes.
  This is by design.
- Always diff a donor write; never trust the response status. The contact wrapper prints
  the diff for you; for every other write, GET the record before and after and compare.
- `PUT /api/v1/contacts/{id}` updates the contact's own fields only and leaves omitted
  fields alone; it does not touch addresses, phones or emails (`ContactUpdate` has no such
  keys; #46's `test_update_contact_cannot_touch_nested_rows` pins it). Those are corrected one row
  at a time through the sub-resource routes above (sr-assistant#46).
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
