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
    # Export
    "POST /api/v1/export/mailing-list": {"description": "Export mailing list CSV", "domain": "donor"},
}

# Endpoints intentionally NOT covered by skills (admin/infra only)
EXCLUDED_ENDPOINTS = {
    # OAuth flow — browser-based, not suitable for CLI skill
    "GET /api/v1/sync/oauth/authorize",
    "GET /api/v1/sync/oauth/callback",
}
