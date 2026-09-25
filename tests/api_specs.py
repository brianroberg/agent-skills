"""Registry of all API endpoints from the Donor Management API.

Used by test_api_coverage.py to verify every endpoint is referenced
in at least one skill file.
"""

DONOR_ENDPOINTS = {
    # Contacts
    "GET /api/v1/contacts": {"description": "List/search contacts", "domain": "donor"},
    "GET /api/v1/contacts/{id}": {"description": "Get contact detail", "domain": "donor"},
    "GET /api/v1/contacts/{id}/summary": {"description": "Get contact summary (giving, activity, pledges)", "domain": "donor"},
    "POST /api/v1/contacts": {"description": "Create contact", "domain": "donor"},
    "PUT /api/v1/contacts/{id}": {"description": "Update contact", "domain": "donor"},
    "DELETE /api/v1/contacts/{id}": {"description": "Delete contact", "domain": "donor"},
    # Contact sub-resources — brianroberg/sr-assistant#46 (merged as b9d1f13, live 2026-09-24).
    "GET /api/v1/contacts/{contact_id}/addresses": {"description": "List a contact's addresses", "domain": "donor"},
    "POST /api/v1/contacts/{contact_id}/addresses": {"description": "Add an address (201)", "domain": "donor"},
    "PATCH /api/v1/contacts/{contact_id}/addresses/{address_id}": {"description": "Partially update an address", "domain": "donor"},
    "DELETE /api/v1/contacts/{contact_id}/addresses/{address_id}": {"description": "Delete an address (204)", "domain": "donor"},
    "GET /api/v1/contacts/{contact_id}/emails": {"description": "List a contact's email addresses", "domain": "donor"},
    "POST /api/v1/contacts/{contact_id}/emails": {"description": "Add an email address (201)", "domain": "donor"},
    "PATCH /api/v1/contacts/{contact_id}/emails/{email_id}": {"description": "Partially update an email address", "domain": "donor"},
    "DELETE /api/v1/contacts/{contact_id}/emails/{email_id}": {"description": "Delete an email address (204)", "domain": "donor"},
    "GET /api/v1/contacts/{contact_id}/phones": {"description": "List a contact's phone numbers", "domain": "donor"},
    "POST /api/v1/contacts/{contact_id}/phones": {"description": "Add a phone number (201)", "domain": "donor"},
    "PATCH /api/v1/contacts/{contact_id}/phones/{phone_id}": {"description": "Partially update a phone number", "domain": "donor"},
    "DELETE /api/v1/contacts/{contact_id}/phones/{phone_id}": {"description": "Delete a phone number (204)", "domain": "donor"},
    # Gifts
    "GET /api/v1/gifts": {"description": "List gifts", "domain": "donor"},
    "GET /api/v1/gifts/{id}": {"description": "Get gift detail", "domain": "donor"},
    "POST /api/v1/gifts": {"description": "Create gift", "domain": "donor"},
    "PUT /api/v1/gifts/{id}": {"description": "Update gift", "domain": "donor"},
    "DELETE /api/v1/gifts/{id}": {"description": "Delete gift", "domain": "donor"},
    # History
    "GET /api/v1/history": {"description": "List interaction history", "domain": "donor"},
    "GET /api/v1/history/{id}": {"description": "Get history entry", "domain": "donor"},
    "POST /api/v1/history": {"description": "Create history entry", "domain": "donor"},
    "PUT /api/v1/history/{id}": {"description": "Update history entry", "domain": "donor"},
    "DELETE /api/v1/history/{id}": {"description": "Delete history entry", "domain": "donor"},
    "GET /api/v1/history/types": {"description": "List history types", "domain": "donor"},
    "GET /api/v1/history/results": {"description": "List history results", "domain": "donor"},
    # Tasks
    "GET /api/v1/tasks": {"description": "List donor tasks", "domain": "donor"},
    "GET /api/v1/tasks/{id}": {"description": "Get donor task", "domain": "donor"},
    "POST /api/v1/tasks": {"description": "Create donor task", "domain": "donor"},
    "PUT /api/v1/tasks/{id}": {"description": "Update donor task", "domain": "donor"},
    "DELETE /api/v1/tasks/{id}": {"description": "Delete donor task", "domain": "donor"},
    "GET /api/v1/tasks/types": {"description": "List task types", "domain": "donor"},
    "POST /api/v1/tasks/{id}/complete": {"description": "Complete donor task", "domain": "donor"},
    # Pledges
    "GET /api/v1/pledges": {"description": "List pledges", "domain": "donor"},
    "GET /api/v1/pledges/{id}": {"description": "Get pledge detail", "domain": "donor"},
    "POST /api/v1/pledges": {"description": "Create pledge", "domain": "donor"},
    "PUT /api/v1/pledges/{id}": {"description": "Update pledge", "domain": "donor"},
    "DELETE /api/v1/pledges/{id}": {"description": "Delete pledge", "domain": "donor"},
    "GET /api/v1/pledges/frequencies": {"description": "List pledge frequencies", "domain": "donor"},
    "POST /api/v1/pledges/{id}/deactivate": {"description": "Deactivate pledge", "domain": "donor"},
    # Groups
    "GET /api/v1/groups": {"description": "List groups", "domain": "donor"},
    "GET /api/v1/groups/{id}": {"description": "Get group with members", "domain": "donor"},
    "POST /api/v1/groups": {"description": "Create group", "domain": "donor"},
    "PUT /api/v1/groups/{id}": {"description": "Update group", "domain": "donor"},
    "DELETE /api/v1/groups/{id}": {"description": "Delete group", "domain": "donor"},
    "POST /api/v1/groups/{id}/contacts": {"description": "Add contacts to group", "domain": "donor"},
    "DELETE /api/v1/groups/{id}/contacts": {"description": "Remove contacts from group", "domain": "donor"},
    # Sync
    "POST /api/v1/sync/trigger": {"description": "Trigger DonorHub sync", "domain": "donor"},
    "GET /api/v1/sync/status": {"description": "Get sync status", "domain": "donor"},
    "GET /api/v1/sync/pending": {"description": "List pending sync items", "domain": "donor"},
    "POST /api/v1/sync/pending/{id}/resolve": {"description": "Resolve pending sync item", "domain": "donor"},
    "POST /api/v1/sync/trigger-addresses": {"description": "Pull contact addresses from DonorHub", "domain": "donor"},
    # Export
    "POST /api/v1/export/mailing-list": {"description": "Export mailing list CSV", "domain": "donor"},
}

# Endpoints intentionally NOT covered by skills, each with the reason it is excluded.
#
# Keys are written exactly as the live OpenAPI spec writes them (including its own
# placeholder names, e.g. `{contact_id}`); test_openapi_sync.py normalizes placeholder
# names before comparing, so `{contact_id}` here and `{id}` in DONOR_ENDPOINTS match.
# A reason is required: an exclusion with no stated reason is indistinguishable from an
# oversight a year later.
EXCLUDED_ENDPOINTS = {
    # OAuth flow — browser-based, not suitable for CLI skill
    "GET /api/v1/sync/oauth/authorize": "OAuth flow — browser-based, not usable from a CLI skill",
    "GET /api/v1/sync/oauth/callback": "OAuth flow — browser-based, not usable from a CLI skill",
    # Infrastructure — no skill will ever call these
    "GET /": "Infrastructure — service root/index page, nothing for a skill to call",
    "GET /health": "Infrastructure — liveness probe, nothing for a skill to call",
    # Browser session auth — skills authenticate with the X-API-Key header instead
    "GET /login": "Browser session auth — skills use the X-API-Key header, not a login form",
    "POST /login": "Browser session auth — skills use the X-API-Key header, not a login form",
    "GET /logout": "Browser session auth — skills use the X-API-Key header, not a login form",
    # Unversioned aliases — legacy/convenience duplicates of the /api/v1 routes.
    # Skills always use the /api/v1 form, which is the one the registry above covers.
    "GET /contacts": "Unversioned alias of GET /api/v1/contacts",
    "GET /contacts/{contact_id}": "Unversioned alias of GET /api/v1/contacts/{id}",
    "GET /groups": "Unversioned alias of GET /api/v1/groups",
    "GET /groups/{group_id}": "Unversioned alias of GET /api/v1/groups/{id}",
    "GET /sync/pending": "Unversioned alias of GET /api/v1/sync/pending",
    "GET /sync/status": "Unversioned alias of GET /api/v1/sync/status",
    "POST /sync/trigger": "Unversioned alias of POST /api/v1/sync/trigger",
    "POST /sync/pending/{item_id}/resolve": "Unversioned alias of POST /api/v1/sync/pending/{id}/resolve",
}
