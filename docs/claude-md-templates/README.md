# CLAUDE.md templates

Two user-level `CLAUDE.md` files, one per Claude Code setup on Brian's MacBook. Both import
`docs/engineering-practices.md` from this repo, so one rule change lands in both setups and
in the agent container, which reads the same rules from its workspace `AGENTS.md`.

| file | for | what it holds |
|---|---|---|
| `personal.CLAUDE.md` | Brian's own account (`~/.claude/CLAUDE.md`) | the import line, the canary check, and a place for personal preferences |
| `claude-bot.CLAUDE.md` | the `claude-bot` setup | inline: commit identity, never push `main` / never merge, reviewer + assignee on every PR, no PII, no token in URLs; then the same import and canary |

The canary: the practices file ends with the line `PRACTICES LOADED`, and each template tells
the session to say so if that line is not in its context. A broken import path then shows up
as the first thing the session says, not as missing rules three hours later.

## Install

Assumption: the repo is checked out at `/Users/robergb/tools/agent-skills` (the import path
in both templates). If it is elsewhere, edit the `@/…/engineering-practices.md` line first.

**Personal account** (`~/.claude/CLAUDE.md`): copy the template if there is no file yet,
otherwise append it.

```fish
set R /Users/robergb/tools/agent-skills
test -f ~/.claude/CLAUDE.md; and cat $R/docs/claude-md-templates/personal.CLAUDE.md >> ~/.claude/CLAUDE.md; or cp $R/docs/claude-md-templates/personal.CLAUDE.md ~/.claude/CLAUDE.md
```

**`claude-bot` setup.** Assumption: it runs with its own `CLAUDE_CONFIG_DIR` (a separate
config directory, so a separate user-level `CLAUDE.md`). Install into that directory:

```fish
set R /Users/robergb/tools/agent-skills
set BOT $CLAUDE_CONFIG_DIR   # or the directory the claude-bot launcher sets
test -f $BOT/CLAUDE.md; and cat $R/docs/claude-md-templates/claude-bot.CLAUDE.md >> $BOT/CLAUDE.md; or cp $R/docs/claude-md-templates/claude-bot.CLAUDE.md $BOT/CLAUDE.md
```

If `claude-bot` is instead the same account and config directory as the personal one, there
is one user-level `CLAUDE.md`: append the `claude-bot` template's "Identity and delivery"
section to it as well, under a heading that says it applies when acting as the bot, and keep
a single import line.

**Verify:** start a session in each setup and ask "what is the last line of the imported
practices file?" The answer is `PRACTICES LOADED`; anything else means the import did not
resolve.

## Changing a rule later

A rule change is a PR to this repo (editing `docs/engineering-practices.md`), merged by Brian,
then `git pull` in `/Users/robergb/tools/agent-skills` on the Mac. The templates themselves
only change when the identity or delivery facts change.
