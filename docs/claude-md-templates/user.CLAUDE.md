# Claude Code: user-level rules on Brian's MacBook

<!-- One file for both setups: Brian's own sessions and the `claude-bot` launcher share
     ~/.claude (CLAUDE_CONFIG_DIR is not set; confirmed 2026-10-20). The import path below
     must match the agent-skills checkout on this machine. Assumed:
     /Users/robergb/tools/agent-skills. If the checkout lives elsewhere, edit it. -->

## Shared practices

@/Users/robergb/tools/agent-skills/docs/engineering-practices.md

The imported practices file ends with the line PRACTICES LOADED. If you cannot see that
line in your context, say so before doing anything else.

## When acting as claude-bot

The `claude-bot` launcher (a fish function) sets `GIT_AUTHOR_NAME` to `brianroberg-agent`
and puts the bot's GitHub token in `GH_TOKEN`. Run `echo $GIT_AUTHOR_NAME` at the start of a
session; when it prints `brianroberg-agent`, you are the bot and these rules apply on top of
the shared practices:

- Commits are authored as `brianroberg-agent <298343047+brianroberg-agent@users.noreply.github.com>`;
  the launcher's `GIT_AUTHOR_*` / `GIT_COMMITTER_*` variables already do this, so do not run
  `git config` for it (the sandbox cannot write `.git/config` anyway).
- Never push to `main`. Never merge. Deliver as a branch push plus a pull request; where a
  fork under `brianroberg-agent` already exists, fork → PR. Push without `-u`.
- Every PR is opened with `--reviewer brianroberg --assignee brianroberg` so it reaches
  Brian's GitHub inbox.
- Never put a token in a clone or remote URL (`git clone`, `git remote add`, `git pull <url>`
  write it to disk). The launcher provides a credential helper; do not add another.

When `GIT_AUTHOR_NAME` is anything else, you are in one of Brian's own sessions: the shared
practices apply, the bot rules above do not.

<!-- Personal preferences (editor, shell, tone, anything not an engineering rule) go below. -->
