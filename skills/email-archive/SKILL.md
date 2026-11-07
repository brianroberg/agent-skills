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

**Token.** When `EMAIL_AGENT_TOKEN` is set, every call to `$EMAIL_AGENT_URL` below except `/health` sends it as `Authorization: Bearer <token>`, which `curl` reads from standard input (`-H @-`), so the token is never on a command line. When it is unset or empty, no `Authorization` header is sent. Do not add `-v`, `--trace` or `set -x` to these calls: each one prints the header.

## Usage

When this skill is invoked with an email ID, run:

```bash
printf '%s' "${EMAIL_AGENT_TOKEN:+Authorization: Bearer $EMAIL_AGENT_TOKEN}" | curl -H @- -s -X POST "$EMAIL_AGENT_URL/archive" \
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
