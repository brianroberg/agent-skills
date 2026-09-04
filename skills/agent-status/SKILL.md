---
name: agent-status
description: Check the health of all agent servers
allowed-tools: Bash
---

# Agent Status

Check the health of all agent servers. Useful for debugging connectivity issues.

## Usage

When this skill is invoked, check each service in turn:

### Check Email Agent

```bash
if [ -n "$EMAIL_AGENT_URL" ]; then
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$EMAIL_AGENT_URL/health" 2>/dev/null)
    if [ "$STATUS" = "200" ]; then
        echo "Email Agent ($EMAIL_AGENT_URL): OK"
    else
        echo "Email Agent ($EMAIL_AGENT_URL): UNREACHABLE (HTTP $STATUS)"
    fi
else
    echo "Email Agent: NOT CONFIGURED (EMAIL_AGENT_URL not set)"
fi
```

### Check Calendar Agent

```bash
if [ -n "$CALENDAR_AGENT_URL" ]; then
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$CALENDAR_AGENT_URL/health" 2>/dev/null)
    if [ "$STATUS" = "200" ]; then
        echo "Calendar Agent ($CALENDAR_AGENT_URL): OK"
    else
        echo "Calendar Agent ($CALENDAR_AGENT_URL): UNREACHABLE (HTTP $STATUS)"
    fi
else
    echo "Calendar Agent: NOT CONFIGURED (CALENDAR_AGENT_URL not set)"
fi
```

### Check Vikunja (the task system)

Brian's task system is a self-hosted Vikunja instance. `$VIKUNJA_URL` is the container
DNS name on the Docker network; `http://vikunja:3456` is the documented fallback while
that variable is still being wired up (runbook step B11a). The retired todo-api at
`gtd-api.fly.dev` is deliberately **not** checked here — it is a read-only archive, and
reporting it "OK" would say the task system is up when it is not.

Check `GET /api/v1/info`, **not** `/health`. Vikunja serves its single-page frontend on
the same port and answers *any* unrecognised root path with HTTP 200 and an HTML page —
so a status-code check on `/health` cannot tell a healthy API from a stray 200. Unknown
paths under `/api/v1/` correctly return 404. `/api/v1/info` needs no token and returns
`version` and `frontend_url`.

```bash
VIKUNJA="${VIKUNJA_URL:-http://vikunja:3456}"
BODY=$(curl -s -m 10 -w "\n%{http_code}" "$VIKUNJA/api/v1/info" 2>/dev/null)
STATUS=$(printf '%s' "$BODY" | tail -n 1)
VERSION=$(printf '%s' "$BODY" | sed '$d' | jq -r '.version // "unknown"' 2>/dev/null)
if [ "$STATUS" = "200" ] && [ -n "$VERSION" ] && [ "$VERSION" != "unknown" ]; then
    echo "Vikunja ($VIKUNJA): OK ($VERSION)"
else
    echo "Vikunja ($VIKUNJA): UNREACHABLE (HTTP $STATUS)"
fi
```

### Check Donor Management DB

```bash
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://donor-management.fly.dev/health" 2>/dev/null)
if [ "$STATUS" = "200" ]; then
    echo "Donor DB (https://donor-management.fly.dev): OK"
else
    echo "Donor DB (https://donor-management.fly.dev): UNREACHABLE (HTTP $STATUS)"
fi
```

## Expected Output

When all services are running:
```
Email Agent (http://100.x.x.x:8081): OK
Calendar Agent (http://localhost:8082): OK
Vikunja (http://vikunja:3456): OK (v2.6.0)
Donor DB (https://donor-management.fly.dev): OK
```

When a service is down:
```
Email Agent (http://100.x.x.x:8081): UNREACHABLE (HTTP 000)
Calendar Agent (http://localhost:8082): OK
Vikunja (http://vikunja:3456): OK (v2.6.0)
Donor DB (https://donor-management.fly.dev): UNREACHABLE (HTTP 503)
```
