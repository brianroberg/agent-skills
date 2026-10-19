# Reviewing changes to this repo

What a reviewer of a PR here should hold in mind. The shape follows the Claude Code
team's code-review write-up (Osmani, Lunt, Wang, October 2026): say what the repo can
break, what counts as an interface, and what reviewers tend to miss.

## What this repo is

A set of Claude Code skills (`skills/*/SKILL.md`) plus a few scripts those skills run.
A skill is **instructions an agent follows against a live service**: the calendar
agent, the email agent, the donor-management API. The agent reads the SKILL.md and
issues the requests it describes. So the "code" that runs in production is mostly prose,
and a wrong sentence has the same effect as a wrong line of code.

## What a change here can break

- **A wrong endpoint, key or response path silently does the wrong thing.** The
  services answer 200 to a request with an unknown query key (the email agent ignores
  `max_results`; the calendar agent nests its answers under `.data` while the email agent
  does not). A skill that documents the wrong name gets a confident empty result, not an
  error. The doc-parity tests (`tests/test_*_docs.py`) and the endpoint registry
  (`tests/api_specs.py`, `tests/test_api_coverage.py`) exist to catch this; a change that
  names an endpoint must be covered by them.
- **A write documented as safe that is not.** Deletes, PUTs and syncs against production
  data in daily use. Check that every write a skill describes goes through the sanctioned
  path (wrapper script, approval gate, diff-after-write) the workspace `TOOLS.md` names,
  and that the skill says what the write destroys.
- **A script that prints a credential.** Scripts read `DONOR_API_KEY` and the agent
  URLs from the environment. A key must not be printed, logged or written.
  `test_no_hardcoded_credentials` catches a literal key in a SKILL.md and nothing else;
  each script's own tests have to pin its output (as `test_script_never_prints_the_key`
  does for `pledges.py`, by pattern, not by execution). Read the script's error paths.
- **Real people in the repo.** Fixtures, examples and issue text use synthetic records
  in the live response shapes. A donor's name, id, amount or address in a tracked file is
  a defect, whatever the branch (Brian, 2026-10-19).

## What counts as an interface

- The **command lines** a SKILL.md shows. The agent copies them. A renamed flag or moved
  script breaks every session that loads the skill, with no test to say so unless one
  is added.
- The **output lines and exit codes** a script produces. Skills and heartbeat checklists
  relay the lines verbatim and branch on the code (for `pledges.py`, 2 covers every
  caller-side problem: bad input, no key, no or several matches; 3 is the API failing).
  Changing wording or a code is an interface change.
- The **frontmatter** (`name`, `description`): it is what makes a skill load at all.

## What reviewers tend to miss here

- **The skill body a running session sees is the one loaded at session start**, and the
  checkout under `~/.claude/skills/agent-skills` only changes when someone pulls. A merged
  change is not live. Say so in the PR when it matters.
- **An absolute claim in prose** ("always", "never", "only"). Every one is a finding for
  the next reviewer unless a test pins it. Prefer sentences scoped to the code path that
  holds.
- **Response shapes differ by service and by endpoint.** A `jq` path that works on one
  endpoint is not evidence for another; read that service's `/openapi.json`.
- **Scripts must stay single-stream against the donor API.** It is production and does
  not absorb parallel reads (see `TOOLS.md`). A loop that fans out is a defect even if
  it is faster.

## How to run the checks

```
uv run pytest tests/ -q -m "not network"     # structure, doc parity, scripts
uv run pytest tests/test_openapi_sync.py -m network -v   # live spec drift (needs the services)
```
