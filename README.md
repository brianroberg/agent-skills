# Agent Skills

A Claude Code plugin providing skills for interacting with email agents, calendar agents, and a GTD task management API. These skills enable Claude Code to search emails, manage calendar events, process GTD inboxes, and orchestrate multi-agent workflows.

## Overview

This plugin follows a multi-agent architecture where Claude Code acts as an orchestrator, delegating specialized tasks to dedicated agent servers and APIs:

- **Email Agent** - Handles Gmail operations (search, summarize, label, archive)
- **Calendar Agent** - Handles Google Calendar operations (query, check availability, create events)
- **GTD API** - Handles Getting Things Done task management (inbox, next actions, projects, someday/maybe, tickler)

## Features

### Email Skills
| Skill | Description | Access |
|-------|-------------|--------|
| `/email-ask` | Search, list, and ask questions about emails | Read-only |
| `/email-label` | Apply labels to emails | Write (requires approval) |
| `/email-archive` | Archive emails | Write (requires approval) |
| `/email-mark-read` | Mark emails as read | Write (requires approval) |
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

### GTD Skills
| Skill | Description | Access |
|-------|-------------|--------|
| `/gtd-capture` | Capture tasks to GTD inbox with clarification | Write |
| `/gtd-process-inbox` | Process inbox items into next actions, someday/maybe, tickler | Write |
| `/gtd-complete` | Mark tasks complete across any GTD list | Write |

### Utility Skills
| Skill | Description |
|-------|-------------|
| `/morning-briefing` | Combined calendar + email briefing (multi-agent orchestration) |
| `/agent-status` | Health check for agent servers |

## Prerequisites

- [Claude Code](https://github.com/anthropics/claude-code) CLI installed
- Email agent server running (for email skills)
- Calendar agent server running (for calendar skills)
- GTD API accessible (for GTD skills) — endpoint and key configured in `/workspace/TOOLS.md`

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

GTD skills read their API endpoint and key from `/workspace/TOOLS.md`. The full API spec is at https://gtd-api.fly.dev/openapi.json.

## Usage

Once installed, invoke skills in Claude Code using slash commands:

```
/email-ask What emails did I get from Alice this week?
/calendar-daily-briefing
/calendar-check-availability Find a 30-minute slot tomorrow afternoon
/briefing-morning
/gtd-capture Email Doug about the budget meeting
/gtd-process-inbox
/gtd-complete Mark "email Doug" done
```

Or describe what you want naturally and Claude Code will select the appropriate skill.

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
│   ├── agent-status/             # Health check skill
│   ├── briefing-morning/         # Combined calendar + email briefing
│   ├── calendar-analyze-schedule/
│   ├── calendar-ask/             # Calendar queries
│   ├── calendar-check-availability/
│   ├── calendar-create-event/
│   ├── calendar-daily-briefing/
│   ├── calendar-delete-event/
│   ├── calendar-search-events/
│   ├── calendar-summarize-event/
│   ├── calendar-update-event/
│   ├── calendar-weekly-briefing/
│   ├── email-archive/
│   ├── email-ask/                # Email queries
│   ├── email-label/
│   ├── email-mark-read/
│   ├── email-triage/
│   ├── gtd-capture/              # Capture tasks to GTD inbox
│   ├── gtd-complete/             # Mark GTD tasks complete
│   └── gtd-process-inbox/        # Process inbox → next actions/someday/tickler
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

3. Commit and push; run `git pull` on other machines

## License

MIT
