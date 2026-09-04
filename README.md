# Agent Skills

A Claude Code plugin providing skills for interacting with email agents, calendar agents, and a donor management system. These skills enable Claude Code to search emails, manage calendar events, manage donor relationships, and orchestrate multi-agent workflows.

> **Task management is no longer here.** The ten `gtd-*` skills were retired when Brian's task system moved from todo-api (`gtd-api.fly.dev`) to a self-hosted **Vikunja** instance; the replacement `vikunja-*` skills live in his workspace at `/workspace/.claude/skills/`. See `/workspace/vikunja-port/CUTOVER-RUNBOOK.md`.

## Overview

This plugin follows a multi-agent architecture where Claude Code acts as an orchestrator, delegating specialized tasks to dedicated agent servers and APIs:

- **Email Agent** - Handles Gmail operations (search, summarize, label, archive)
- **Calendar Agent** - Handles Google Calendar operations (query, check availability, create events)
- **Donor Management API** - Handles donor/contact management, giving history, interaction logging, pledges, and DonorHub sync

## Features

### Email Skills
| Skill | Description | Access |
|-------|-------------|--------|
| `/email-ask` | Search, list, and ask questions about emails | Read-only |
| `/email-label` | Apply labels to emails | Write (requires approval) |
| `/email-archive` | Archive emails | Write (requires approval) |
| `/email-mark-read` | Mark emails as read | Write (requires approval) |
| `/email-draft` | Create, view, update, or delete email drafts | Write (requires approval) |
| `/email-triage` | Triage unread emails with bulk actions | Write (requires approval) |

### Calendar Skills
| Skill | Description | Access |
|-------|-------------|--------|
| `/calendar-ask` | Query calendar events with natural language | Read-only |
| `/calendar-daily-briefing` | Get a summary of today's calendar | Read-only |
| `/calendar-weekly-briefing` | Get a summary of your week's calendar | Read-only |
| `/calendar-check-availability` | Find available time slots | Read-only |
| `/calendar-search-events` | Search events with structured filters | Read-only |
| `/calendar-summarize-event` | Get AI summary of a specific event | Read-only |
| `/calendar-analyze-schedule` | Analyze schedule patterns and workload | Read-only |
| `/calendar-create-event` | Create new calendar events | Write (requires approval) |
| `/calendar-update-event` | Update existing calendar events | Write (requires approval) |
| `/calendar-delete-event` | Delete calendar events | Write (requires approval) |

### Donor Management Skills
| Skill | Description | Access |
|-------|-------------|--------|
| `/donor-ask` | Look up donors, contacts, giving stats, and activity | Read-only |
| `/donor-log` | Log calls, visits, letters, and other interactions | Write |
| `/donor-gifts` | Query giving data and record manual gifts | Read/Write |
| `/donor-tasks` | Manage donor stewardship tasks (thank-you, follow-up) | Read/Write |
| `/donor-sync` | Trigger DonorHub sync, manage pledges, export mailing lists | Read/Write |
| `/donor-contact-manage` | Create, update, delete contacts and manage groups | Write |

### Utility Skills
| Skill | Description |
|-------|-------------|
| `/briefing-morning` | Combined calendar + email + donor briefing (multi-agent orchestration) |
| `/agent-status` | Health check for all agent servers and APIs |

## Prerequisites

- [Claude Code](https://github.com/anthropics/claude-code) CLI installed
- Email agent server running (for email skills)
- Calendar agent server running (for calendar skills)
- Donor Management API accessible (for donor skills) — endpoint and key configured in `/workspace/TOOLS.md`

## Installation

1. **Clone the repository:**
   ```bash
   git clone git@github.com:brianroberg/agent-skills.git
   ```

2. **Configure environment variables** (add to your shell profile):
   ```bash
   export EMAIL_AGENT_URL="http://localhost:8081"
   export CALENDAR_AGENT_URL="http://localhost:8082"
   ```

3. **Install the plugin in Claude Code:**
   ```bash
   claude
   ```
   Then inside Claude Code, run these commands (use absolute path):
   ```
   /plugin marketplace add /absolute/path/to/agent-skills
   /plugin install agent-skills@brianroberg
   ```

4. **Verify installation:**
   ```
   /agent-status
   ```

## Configuration

Set these environment variables to point to your agent servers:

| Variable | Description | Example |
|----------|-------------|---------|
| `EMAIL_AGENT_URL` | Email agent server endpoint | `http://localhost:8081` |
| `CALENDAR_AGENT_URL` | Calendar agent server endpoint | `http://localhost:8082` |

Donor Management skills read their API endpoint and key from `/workspace/TOOLS.md`. Auth uses `X-API-Key` header with agent-level keys (`agent_read` or `agent_readwrite`). Base URL: `https://donor-management.fly.dev`.

## Usage

Once installed, invoke skills in Claude Code using slash commands:

```
/email-ask What emails did I get from Alice this week?
/calendar-daily-briefing
/calendar-check-availability Find a 30-minute slot tomorrow afternoon
/briefing-morning
/donor-ask Tell me about John Smith
/donor-log I just called John about his pledge renewal
/donor-gifts How much has John given this year?
```

Or describe what you want naturally and Claude Code will select the appropriate skill.

## Testing

The project includes a test suite that validates skill files structurally and checks API endpoint coverage.

```bash
# Install dependencies
uv sync

# Run structural tests (no network required)
uv run pytest tests/test_skills.py -v

# Run API coverage tests (no network required)
uv run pytest tests/test_api_coverage.py -v

# Run OpenAPI sync tests (requires network access)
uv run pytest tests/test_openapi_sync.py -m network -v

# Run all non-network tests
uv run pytest tests/ -v
```

The API coverage tests ensure every endpoint in the Donor Management API is referenced by at least one skill, preventing future documentation drift.

## Updating

This plugin is designed for easy updates across multiple environments.

**To update on any machine:**
```bash
cd /path/to/agent-skills
git pull
```

Changes take effect in the next Claude Code session.

**Recommended workflow for development:**
1. Make changes to skills on your primary machine
2. Commit and push to GitHub
3. Run `git pull` on other machines when ready to update

## Project Structure

```
agent-skills/
├── .claude-plugin/
│   └── plugin.json               # Plugin manifest
├── skills/
│   ├── agent-status/             # Health check for all services
│   ├── briefing-morning/         # Combined 4-domain morning briefing
│   ├── calendar-analyze-schedule/
│   ├── calendar-ask/
│   ├── calendar-check-availability/
│   ├── calendar-create-event/
│   ├── calendar-daily-briefing/
│   ├── calendar-delete-event/
│   ├── calendar-search-events/
│   ├── calendar-summarize-event/
│   ├── calendar-update-event/
│   ├── calendar-weekly-briefing/
│   ├── donor-ask/                # Query donors and contacts
│   ├── donor-contact-manage/     # Contact CRUD and group management
│   ├── donor-gifts/              # Giving data and manual gift entry
│   ├── donor-log/                # Log interactions with donors
│   ├── donor-sync/               # DonorHub sync and pledge management
│   ├── donor-tasks/              # Donor stewardship tasks
│   ├── email-archive/
│   ├── email-ask/
│   ├── email-draft/
│   ├── email-label/
│   ├── email-mark-read/
│   └── email-triage/
├── tests/
│   ├── conftest.py               # Shared test fixtures
│   ├── api_specs.py              # API endpoint registry
│   ├── test_skills.py            # Structural validation tests
│   ├── test_api_coverage.py      # Endpoint coverage tests
│   └── test_openapi_sync.py      # Live OpenAPI spec sync tests
├── pyproject.toml                # Python dependencies (pytest, pyyaml)
└── README.md
```

Each skill directory contains a `SKILL.md` file with:
- YAML frontmatter (name, description, allowed-tools)
- Usage documentation
- API endpoint details
- Example commands

## Security

- **Approval gates**: Write operations (labeling, archiving, creating events) require explicit user approval in Claude Code
- **Data locality**: Email and calendar data stays on your local machine; only queries and summaries pass through the API
- **Prompt injection protection**: Agent servers ignore instructions embedded in email/event content
- **Agent key isolation**: Donor Management agent keys automatically strip `confidential_notes` from responses and silently drop them on writes

## Adding New Skills

1. Create a new directory under `skills/`:
   ```bash
   mkdir skills/my-new-skill
   ```

2. Add a `SKILL.md` file with frontmatter:
   ```markdown
   ---
   name: my-new-skill
   description: Brief description of what this skill does
   allowed-tools: Bash
   ---

   # My New Skill

   Documentation and usage instructions...
   ```

3. Run tests to validate:
   ```bash
   uv run pytest tests/test_skills.py -v
   ```

4. Commit and push; run `git pull` on other machines

## License

MIT
