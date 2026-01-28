---
name: email-archive
description: Archive an email (requires approval)
allowed-tools: Bash
---

# Archive Email

Archive an email (remove from inbox). This is a **write operation** that modifies your inbox.

**This skill requires your approval before executing the curl command.**

## Prerequisites

Requires `EMAIL_AGENT_URL` environment variable to be set.

## Usage

When this skill is invoked with an email ID, run:

```bash
curl -s -X POST "$EMAIL_AGENT_URL/archive" \
    -H "Content-Type: application/json" \
    -d '{"email_id": "EMAIL_ID_HERE"}' \
    | jq .
```

Replace `EMAIL_ID_HERE` with the actual email ID.

## Example

`/email-archive 18d4a2b3c4e5f6g7`

## Security Notes

- Claude Code's approval prompt is the security gate
- The email is removed from inbox but not deleted
