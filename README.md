# Agent Skills

A Claude Code plugin providing skills for interacting with email and calendar agents. These skills enable Claude Code to search emails, manage calendar events, and orchestrate multi-agent workflows.

## Overview

This plugin follows a multi-agent architecture where Claude Code acts as an orchestrator, delegating specialized tasks to dedicated agent servers:

- **Email Agent** - Handles Gmail operations (search, summarize, label, archive)
- **Calendar Agent** - Handles Google Calendar operations (query, check availability, create events)

Claude Code uses these skills to coordinate between agents, synthesize information, and present unified responses.

## Features

### Email Skills
| Skill | Description | Access |
|-------|-------------|--------|
| `/ask-email` | Search, list, and ask questions about emails | Read-only |
| `/email-label` | Apply labels to emails | Write (requires approval) |
| `/email-archive` | Archive emails | Write (requires approval) |
| `/email-mark-read` | Mark emails as read | Write (requires approval) |

### Calendar Skills
| Skill | Description | Access |
|-------|-------------|--------|
| `/ask-calendar` | Query calendar events with natural language | Read-only |
| `/daily-briefing` | Get a summary of today's calendar | Read-only |
| `/check-availability` | Find available time slots | Read-only |
| `/create-event` | Create new calendar events | Write (requires approval) |

### Utility Skills
| Skill | Description |
|-------|-------------|
| `/morning-briefing` | Combined calendar + email briefing (multi-agent orchestration) |
| `/agent-status` | Health check for agent servers |

## Prerequisites

- [Claude Code](https://github.com/anthropics/claude-code) CLI installed
- Email agent server running (for email skills)
- Calendar agent server running (for calendar skills)

## Installation

1. **Clone the repository:**
   ```bash
   git clone git@github.com:brianroberg/agent-skills.git
   cd agent-skills
   ```

2. **Install the plugin in Claude Code:**
   ```bash
   claude mcp add-plugin /path/to/agent-skills
   ```

3. **Configure environment variables** (add to your shell profile):
   ```bash
   export EMAIL_AGENT_URL="http://localhost:8081"
   export CALENDAR_AGENT_URL="http://localhost:8082"
   ```

4. **Verify installation:**
   ```bash
   claude
   # Then use: /agent-status
   ```

## Configuration

Set these environment variables to point to your agent servers:

| Variable | Description | Example |
|----------|-------------|---------|
| `EMAIL_AGENT_URL` | Email agent server endpoint | `http://localhost:8081` |
| `CALENDAR_AGENT_URL` | Calendar agent server endpoint | `http://localhost:8082` |

## Usage

Once installed, invoke skills in Claude Code using slash commands:

```
/ask-email What emails did I get from Alice this week?
/daily-briefing
/check-availability Find a 30-minute slot tomorrow afternoon
/morning-briefing
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
│   └── plugin.json       # Plugin manifest
├── skills/
│   ├── agent-status/     # Health check skill
│   ├── ask-calendar/     # Calendar queries
│   ├── ask-email/        # Email queries
│   ├── check-availability/
│   ├── create-event/
│   ├── daily-briefing/
│   ├── email-archive/
│   ├── email-label/
│   ├── email-mark-read/
│   └── morning-briefing/
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
