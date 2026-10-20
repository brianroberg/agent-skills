# CLAUDE.md template

One user-level `CLAUDE.md` for Brian's MacBook. His own sessions and the `claude-bot` launcher
share `~/.claude` (`CLAUDE_CONFIG_DIR` is not set; checked 2026-10-20), so there is one file.
It imports `docs/engineering-practices.md` from this repo, so a rule change lands in both
setups and in the agent container, which reads the same rules from its workspace `AGENTS.md`.

| file | holds |
|---|---|
| `user.CLAUDE.md` | the import line and the canary check; a "When acting as claude-bot" section (commit identity, never push `main` / never merge, reviewer + assignee on every PR, no token in URLs) gated on `GIT_AUTHOR_NAME`, which the launcher sets; a place for personal preferences |

**How the bot section is gated.** The `claude-bot` fish function sets `GIT_AUTHOR_NAME` to
`brianroberg-agent` before running `claude`. The template tells the session to check that
variable at the start, so the same file gives a bot session the containment rules and a
personal session only the shared practices.

**The canary.** The practices file ends with the line `PRACTICES LOADED`, and the template
tells the session to say so if that line is not in its context. A broken import path then
shows up as the first thing the session says, not as missing rules three hours later.

## Install

Assumption: the repo is checked out at `/Users/robergb/tools/agent-skills` (the import path
in the template). If it is elsewhere, edit the `@/…/engineering-practices.md` line first.

Copy the template if there is no `~/.claude/CLAUDE.md` yet, otherwise append it:

```fish
set R /Users/robergb/tools/agent-skills
cd $R; and git pull
test -f ~/.claude/CLAUDE.md; and cat $R/docs/claude-md-templates/user.CLAUDE.md >> ~/.claude/CLAUDE.md; or cp $R/docs/claude-md-templates/user.CLAUDE.md ~/.claude/CLAUDE.md
```

If `~/.claude/CLAUDE.md` already holds the `personal.CLAUDE.md` block from PR #26 (it begins
`# Claude Code: Brian's own sessions`), replace that block rather than appending a second
import:

```fish
set R /Users/robergb/tools/agent-skills
set F ~/.claude/CLAUDE.md
cp $F $F.bak
sed -i '' '/^# Claude Code: Brian.s own sessions/,$d' $F
cat $R/docs/claude-md-templates/user.CLAUDE.md >> $F
```

**Verify:** start one session the normal way and one through `claude-bot`, and ask each
"what is the last line of the imported practices file, and are you acting as claude-bot?"
Expected: `PRACTICES LOADED` from both; "no" from the first, "yes" from the second.

## Changing a rule later

A rule change is a PR to this repo (editing `docs/engineering-practices.md`), merged by Brian,
then `git pull` in `/Users/robergb/tools/agent-skills` on the Mac. The import line reads the
checkout directly, so the pull is enough for the practices. The template itself only changes
when the identity or delivery facts change.

**Skills are different.** On the Mac the repo's `skills/` load through the `agent-skills`
plugin, registered from the checkout as a directory marketplace (`/plugin marketplace add
/Users/robergb/tools/agent-skills`, then `/plugin install agent-skills@brianroberg`; set up
2026-10-20). The install is a cached copy at one commit, so a merged skill change reaches
sessions only after `git pull` **and** `/plugin update agent-skills@brianroberg` (or
`/reload-plugins`). A skill that exists in the checkout but not in a session's list is the
sign the update step was skipped.
