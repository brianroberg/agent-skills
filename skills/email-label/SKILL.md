---
name: email-label
description: Apply a label to an email (requires approval)
allowed-tools: Bash
---

# Label Email

Apply a label to an email. This is a **write operation** that modifies your inbox.

**This skill requires your approval before executing the curl command.**

## Prerequisites

Requires `EMAIL_AGENT_URL` environment variable to be set.

**Token.** When `EMAIL_AGENT_TOKEN` is set, every call to `$EMAIL_AGENT_URL` below except `/health` sends it as `Authorization: Bearer <token>`, which `curl` reads from standard input (`-H @-`), so the token is never on a command line. When it is unset or empty, no `Authorization` header is sent. Do not add `-v`, `--trace` or `set -x` to these calls: each one prints the header.

## Usage

When this skill is invoked with an email ID and label name, run:

```bash
printf '%s' "${EMAIL_AGENT_TOKEN:+Authorization: Bearer $EMAIL_AGENT_TOKEN}" | curl -H @- -s -X POST "$EMAIL_AGENT_URL/apply-label" \
    -H "Content-Type: application/json" \
    -d '{"email_id": "EMAIL_ID_HERE", "label_name": "LABEL_NAME_HERE"}' \
    | jq .
```

Replace `EMAIL_ID_HERE` and `LABEL_NAME_HERE` with the actual values.

Common labels: `STARRED`, `IMPORTANT`, or custom label names.

## Example

`/email-label 18d4a2b3c4e5f6g7 STARRED`

## Security Notes

- Claude Code's approval prompt is the security gate
