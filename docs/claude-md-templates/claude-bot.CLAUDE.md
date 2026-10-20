# Claude Code: the `claude-bot` setup

<!-- The import path below must match the agent-skills checkout on this machine.
     Assumed: /Users/robergb/tools/agent-skills. If the checkout lives elsewhere, edit it. -->

## Identity and delivery

- Commits are authored as `brianroberg-agent <298343047+brianroberg-agent@users.noreply.github.com>`.
  If `git config` cannot write (sandboxed `.git/config`), set `GIT_AUTHOR_NAME`,
  `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME` and `GIT_COMMITTER_EMAIL` instead.
- Never push to `main`. Never merge. Deliver as a branch push plus a pull request; where a
  fork under `brianroberg-agent` already exists, fork → PR.
- Every PR is opened with `--reviewer brianroberg --assignee brianroberg` so it reaches
  Brian's GitHub inbox.
- No PII in any tracked file, fixture, example, test report, issue or PR body.
- Never put a token in a clone or remote URL (`git clone`, `git remote add`, `git pull <url>`
  write it to disk). Supply it on the push or fetch command line only, or use `gh`.

## Shared practices

@/Users/robergb/tools/agent-skills/docs/engineering-practices.md

The imported practices file ends with the line PRACTICES LOADED. If you cannot see that
line in your context, say so before doing anything else.
