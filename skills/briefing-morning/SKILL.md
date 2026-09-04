---
name: briefing-morning
description: Get a comprehensive morning briefing combining calendar and email summaries
allowed-tools: Bash
---

# Morning Briefing

Get a comprehensive morning briefing combining calendar and email summaries.
This demonstrates multi-agent orchestration where Claude Code synthesizes
information from multiple specialist agents.

## Prerequisites

Requires environment variables:
- `EMAIL_AGENT_URL` - Email agent server
- `CALENDAR_AGENT_URL` - Calendar agent server

Donor Management credentials in `/workspace/TOOLS.md`.

The task-status step does not run its own queries: it calls the `vikunja-*` skills in
Brian's workspace (`/workspace/.claude/skills/`), which carry their own configuration
(`$VIKUNJA_URL`, `$VIKUNJA_TOKEN`).

## Usage

When this skill is invoked, run both queries and present the combined results:

### Step 1: Get Calendar Briefing

The briefing text is at **`.data.briefing`**. `/prepare-briefing` returns an
`LLMResponse` — `{success, data, error}` — so a filter reading `.briefing` prints
literal `null` on a fully successful `200` and the briefing silently comes back
empty.

```bash
resp=$(curl -sS --max-time 120 -X POST "$CALENDAR_AGENT_URL/prepare-briefing" -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d '{
        "briefing_type": "daily",
        "calendar_id": "robergb@dm.org"
    }')
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ]; then
    echo "Calendar error: read failed (curl exit $rc, HTTP ${code:-none}) - not an empty calendar"
    printf '%s' "$body" | jq -r '.error // .' 2>/dev/null
else
    printf '%s' "$body" | jq -r '.data.briefing'
fi
```

`data` also carries `briefing_type`, `period` and `event_count`; when the calendar
is clear it is `{"briefing": "Your daily calendar is clear...", "highlights": [],
"preparation_notes": []}` instead. `.data.briefing` is present either way.

### Step 2: Get Unread Emails

```bash
curl -s -X POST "$EMAIL_AGENT_URL/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "is:unread", "folder": "INBOX", "limit": 10}' \
    | jq .
```

Review the returned message stubs (subject, sender, snippet). For any that look urgent or important, get a summary:

```bash
curl -s -X POST "$EMAIL_AGENT_URL/summarize" \
    -H "Content-Type: application/json" \
    -d '{"message_id": "MESSAGE_ID_HERE"}' \
    | jq -r '.answer'
```

### Step 3: Task Status Check

Brian's task system is a self-hosted **Vikunja** instance; the retired todo-api
(`gtd-api.fly.dev`) is a read-only archive. **Do not query the task system with `curl`
from this skill.** The query logic lives in exactly one place — the `vikunja-*` skills in
Brian's workspace — and a second copy here is how the two drift apart. Read the relevant
skill's `SKILL.md` before parsing its output.

**Normally one call is enough.** `vikunja-weekly-review`'s data pack returns everything
this step reports, read-only, in a single call:

```bash
cd /workspace
python3 .claude/skills/vikunja-weekly-review/scripts/weekly_review.py --due-days 1 --json
```

From that pack: `inbox.count` (inbox count), `overdue` (overdue counts, hard vs soft),
`hard_due` (deadlines inside the `--due-days` window), `tickler.arrived` (tickler items
surfacing today or earlier). `waiting`, `projects.stalled` and `someday` are also in the
pack — they belong to the weekly review, not to a morning briefing; ignore them here.

Reach past the pack only when it does not carry what is needed:

| Briefing line | Skill | Command (from `/workspace`) |
|---|---|---|
| Which items are overdue or due today, ranked, with area | `vikunja-review-actions` | `python3 .claude/skills/vikunja-review-actions/scripts/review.py --due-within 0` |
| Tickler detail — what arrived, what arrives next | `vikunja-someday-tickler` | `python3 .claude/skills/vikunja-someday-tickler/scripts/someday_tickler.py tickler` |

All three are read-only. Any action arising from the briefing (capturing, completing,
deferring) goes through the matching `vikunja-*` skill, not through this one.

### Step 4: Donor Task Check

```bash
# Pending donor tasks, straight from the donor system
curl -s "https://donor-management.fly.dev/api/v1/tasks?status=pending" \
    -H "X-API-Key: $DONOR_API_KEY" | jq .
```

The donor system is the source of truth for these. The old cross-system view
(`/donor-tasks` on the retired todo-api) is gone and has no Vikunja replacement yet —
see the `donor-tasks` skill and Phase C of `/workspace/vikunja-port/CUTOVER-RUNBOOK.md`.

### Step 5: Synthesize

After getting all responses, synthesize them into a coherent briefing that:
- Highlights priorities for the day
- Notes any conflicts between meetings and email deadlines
- Suggests time blocks for email responses
- Reports the Vikunja inbox count and any overdue items
- Surfaces today's tickler items and deadlines
- Lists pending donor follow-ups (thank-you calls, etc.)
- Provides a priority ranking across all four domains (calendar, email, tasks, donor)

## Follow-up Suggestions

After presenting the briefing, the user might ask:
- "Based on that briefing, what should I prioritize today?"
- "Are there any conflicts between my meetings and email deadlines?"
- "Summarize my day in one paragraph"
- "Process my inbox" (→ use the `vikunja-process-inbox` skill)
- "Show me those donor tasks" (→ use the `donor-tasks` skill)
- "What's overdue?" (→ use the `vikunja-review-actions` skill)

## Non-200 responses

calendar-agent's HTTP status now agrees with the body instead of always being
`200`: `403` blocked by policy or rejected by the operator, `404` no such calendar
or event, `422` malformed request, `500` unexpected fault, `502` upstream proxy or
LLM failure, `504` no answer in time. For a read, a non-200 means *the answer is
missing*, not that the calendar is empty. Never present a failed read as "nothing
scheduled".

**Do not bolt `-w '\n%{http_code}'` onto a piped `curl ... | jq ...` command.** `jq`
then reads the trailing status line as a second JSON document and dies on it —
`jq: error (at <stdin>:1): Cannot index number with string "events"`, exit status 5,
with whatever it managed to print from the real body left tangled up with the error.
Verified live 2026-09-04 against the deployed agent. Capture the response into a
variable, split off the status, and pipe only the body to `jq`:

```bash
resp=$(curl -sS --max-time 35 -w '\n%{http_code}' "$CALENDAR_AGENT_URL/health")
rc=$?
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$rc" -ne 0 ] || [ "$code" != "200" ]; then
    echo "READ FAILED (curl exit $rc, HTTP ${code:-none}) - the answer is missing, not empty"
    printf '%s' "$body" | jq -r '.error // .' 2>/dev/null
else
    printf '%s' "$body" | jq .
fi
```

The commands under *Usage* above are already in this form — copy one and change the
URL, the payload and the final `jq` filter. Any remaining `curl -s ... | jq ...`
snippet in this file illustrates request shape only; do not run it as the real read.
