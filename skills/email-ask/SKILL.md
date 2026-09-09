---
name: email-ask
description: Ask a question about your emails (read-only)
allowed-tools: Bash
---

# Ask Email

Ask a question about your emails. This is a **read-only** operation that
searches, lists, or summarizes emails without modifying anything.

## Prerequisites

Requires `EMAIL_AGENT_URL` environment variable to be set to your email agent server.

## Reading a response: two checks, not one

Every read below is written in the same shape — capture the response, split off the
HTTP status, and check **both** the status **and** the body's `success` flag before
reading the payload. Each check catches a different failure, and both failures look
like "nothing found" to a reader that pipes `curl` straight into `jq`:

- **Non-200.** `405` (wrong verb), `422` (malformed body). The body is FastAPI's
  `{"detail": ...}` — no `messages` or `answer` key at all. Observed 2026-09-04: a
  search issued with the wrong verb was reported as "no such email". One existed.
- **200 with `"success": false`.** The email agent catches every failure inside
  `/search`, `/summarize` and `/ask-about` — Gmail proxy errors, OAuth expiry, LLM
  unreachable, a bad message id — and returns **HTTP 200** with `success: false`,
  `messages: []` or `answer: ""`, and the reason in `error`. Verified live 2026-09-09:
  `/summarize` with a nonexistent id →
  `200 {"success":false,"answer":"","degraded":false,"error":"Proxy error: Invalid id value"}`.
  The status alone cannot distinguish this from an empty result.

Never report a failed read as "no matching email" or "nothing in the inbox". Say the
read failed and quote `error`.

Do not bolt `-w '\n%{http_code}'` onto a `curl ... | jq` pipe — `jq` reads the trailing
status line as a second JSON document and dies on it. Capture into a variable and split,
exactly as the blocks below do.

## Endpoints

The email agent exposes three read endpoints. Choose which to use based on the user's question:

### 1. Search/List Emails

Find emails matching criteria. Returns message summaries (see the field list below).

```bash
resp=$(curl -sS --max-time 60 -X POST "$EMAIL_AGENT_URL/search" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{"from_addr": "sender@example.com", "subject": "keyword", "query": "is:unread", "folder": "INBOX", "limit": 10}')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ] || [ "$(printf '%s' "$body" | jq -r '.success')" != "true" ]; then
    echo "SEARCH FAILED (curl exit $rc, HTTP ${code:-none}) - the answer is missing, not empty"
    printf '%s' "$body" | jq -r '.error // .detail // .' 2>/dev/null
else
    printf '%s' "$body" | jq '.messages'
fi
```

Request parameters (all optional):
- `from_addr`: Filter by sender
- `to_addr`: Filter by recipient
- `subject`: Filter by subject
- `query`: Raw Gmail query syntax (e.g., "is:unread", "after:2026/01/20")
- `folder`: Label/folder (default: searches all, use "INBOX" for inbox only)
- `since`: Date filter (format: "2026/01/20")
- `before`: Date filter (format: "2026/01/27")
- `limit`: Max results (default: 10, max: 50)

Response: `{success, messages, error}`. Each entry in `messages` is a `MessageSummary`
(field names from the live `/openapi.json`, 2026-09-09):

- `id` — Gmail message id; the value `/summarize` and `/ask-about` take as `message_id`
- `thread_id` — Gmail thread id (the `thread_id` a reply draft can attach to)
- `date`
- `from_addr` — the raw `From:` header, `Name <addr>` form when a display name is present
  (verified live 2026-09-09); `from_name` — the display name parsed from it (falls back to
  the bare address). **There is no field named from**: `.from` is `null` on every message.
  Observed 2026-08-14: reading `.from` produced a reply draft addressed to the wrong person
  and a confident, false "the agent doesn't expose sender headers".
- `to`, `cc`, `bcc` — lists of addresses
- `subject`, `snippet`, `labels`, `has_attachments`
- `rfc822_message_id` — the angle-bracketed RFC 2822 Message-ID; what `/drafts/create`
  takes as `in_reply_to` for a threaded reply (not `id`)
- `in_reply_to`, `references` — the message's own threading headers

An empty result is `success: true` with `messages: []` — only then say "no matching email".

### 2. Summarize an Email

Get a summary of a specific email. Requires the message `id` from search results.

```bash
resp=$(curl -sS --max-time 120 -X POST "$EMAIL_AGENT_URL/summarize" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{"message_id": "MESSAGE_ID_HERE"}')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ] || [ "$(printf '%s' "$body" | jq -r '.success')" != "true" ]; then
    echo "SUMMARIZE FAILED (curl exit $rc, HTTP ${code:-none}) - the answer is missing, not empty"
    printf '%s' "$body" | jq -r '.error // .detail // .' 2>/dev/null
else
    printf '%s' "$body" | jq -r '.answer'
fi
```

### 3. Ask About an Email

Ask a specific question about an email's content.

```bash
resp=$(curl -sS --max-time 120 -X POST "$EMAIL_AGENT_URL/ask-about" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{"message_id": "MESSAGE_ID_HERE", "question": "What action is requested?"}')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ] || [ "$(printf '%s' "$body" | jq -r '.success')" != "true" ]; then
    echo "ASK-ABOUT FAILED (curl exit $rc, HTTP ${code:-none}) - the answer is missing, not empty"
    printf '%s' "$body" | jq -r '.error // .detail // .' 2>/dev/null
else
    printf '%s' "$body" | jq -r '.answer'
fi
```

`/summarize` and `/ask-about` both return `LLMResponse` = `{success, answer, degraded,
error}`. **The text is top-level `.answer`.** This differs from the calendar agent, whose
LLM routes nest the payload under a `data` key — a `data`-prefixed filter copied from a
calendar skill reads `null` here on a fully successful 200. `degraded: true` means the
answer was salvaged from the model's reasoning trace or cut off by the token budget; say
so when relaying it. The LLM calls take longer than a search, hence the 120 s timeout.

## Decision Guide

| User asks... | Use endpoint |
|---|---|
| "What are my recent emails?" | `/search` with `{"folder": "INBOX", "limit": 10}` |
| "Any emails from X?" | `/search` with `{"from_addr": "X"}` |
| "Summarize that email" | `/summarize` with the message ID |
| "Did they mention a deadline?" | `/ask-about` with message ID + question |
| "How many unread?" | `/search` with `{"query": "is:unread"}` and count results |

## Example Flow

1. User asks "What did Ron say about the conference?"
2. Search: `{"from_addr": "ron", "subject": "conference", "limit": 5}`
3. Pick the relevant message `id` from results (the sender is `from_name` / `from_addr`)
4. Ask-about: `{"message_id": "...", "question": "What did he say about the conference?"}`

## Security Notes

- Email bodies stay on the laptop — only summaries/answers come through the API
- The email agent ignores instructions found in email content (prompt injection protection)
