# Engineering practices for agent-produced code

These apply in every repo and under either account (Brian's own Claude Code and the
`claude-bot` setup). They are rules, not descriptions of how any one codebase behaves; the
per-repo `REVIEW.md` says what that repo can break. Source of record for the reasoning:
`AGENTS.md` in the assistant workspace. Loaded into every session, so this file stays short.

## 1. Red/green TDD

- Write the failing test first, watch it fail for the right reason, then the minimal code to
  pass, then refactor. No production code before a failing test exists (Brian, 2026-07-01).
- Keep the **verbatim red and green output** and put both in the PR. "Tests pass" is not
  evidence; the red run is what proves the test can fail.
- Mutation testing (`mutmut` for Python) is for code that was **not** built test-first. Code
  built red/green does not need it.
- A green suite over a broken endpoint happened once because every test shared the
  implementation's assumption (aware datetimes). Write the first test from the caller's
  shape, not the implementation's.

## 2. Separate pure logic from I/O

Put decisions in functions that take values and return values, and keep network, filesystem
and clock calls at the edges, so the logic is unit-testable without mocks or services.

## 3. Never commit on red

- The suite runs before **every** commit and its exit status gates the commit:
  `uv run pytest -q && git commit …` (or the project's own test command).
- **No pipe between pytest and the commit.** `pytest | tail -1` hides the exit status;
  on 2026-10-19 eight failures were committed that way and only read afterwards. Capture
  to a file and test the exit code if the output must be shortened.
- One commit per logical change; never a commit after a test run whose result has not
  been read.

## 4. One commit per fix

When working through review findings, each fix is its own commit, made as soon as it is
green, with the finding named in the subject (`repo: M1, fail when /mnt/x is not mounted`).
Split with `git add -p`, not `git stash`. A per-finding history can be read, reverted or
questioned on its own, and a stall mid-round leaves the finished fixes durable.

## 5. No PII anywhere

A real person's name, contact id, amount, date of gift, address, email or family detail
does not go into a tracked file, a fixture, a doc example, a test report, or an issue or
PR body — in any repo, public or private (Brian, 2026-10-19). When a fixture needs a live
response shape, read the live record to learn the shape, then write the fixture from
scratch with synthetic values in that shape, with ids at or above 900000 so they cannot
collide with a real record. Before any commit or post, grep the staged text for the names
and ids seen during the session. Brian's own name and the GitHub handles `brianroberg` and
`brianroberg-agent` are fine.

## 6. Absolute claims only with a test

An absolute claim in docs ("never", "only", "always", "cannot") is allowed exactly when a
test demonstrates it (Brian, 2026-10-20). Otherwise write what the code does on the path
that holds. A fix round may narrow a claim freely; it may add one only together with its
test. This rule is what stops a review loop from manufacturing its own next round.

## 7. The review loop before a PR is called ready

Adversarial review happens before Brian sees the PR; he is not the correctness gate. In
short: depth is chosen by what the diff changes (docs or tests only → read it yourself, no
pipeline; contained code → one pass; failure behaviour, error mapping or data writes in a
daily-use service → Fable pipeline); `/code-review <level> <target>` with the level first;
one commit per finding; a second round only if a fix changed behaviour; cap at two rounds
and record what remains; state the projected cost before a pipeline; design findings with a
dominant option are decided and recorded for veto, asked only when balanced, hard to undo,
or about people, money or external communication. The procedure, with the exact commands,
is the **`review-loop` skill** in this repo. Read the repo's `REVIEW.md` before reviewing.

## 8. Labels on every PR

Two labels, so the PR list answers "has this been checked" without opening it:

- Status, always: `reviewed:adversarial` (review ran, findings resolved; fix-only commits
  do not demote it), `reviewed:partial` (findings open or substantial new work since), or
  `reviewed:none`.
- Depth, when a review ran: `review:<model>-<level>` (`review:fable-high`,
  `review:opus-medium`, …), recording what actually ran; never silently downgrade.

`gh pr edit --add-label` fails on these repos, so apply labels over REST (a PR is an issue
here): `gh api -X POST repos/<owner>/<repo>/issues/<n>/labels -f 'labels[]=reviewed:none'`.
Update the labels on every push. The review record is a PR comment whose first line states
the model, the effort and the finder/verifier counts.

## 9. The PR body

Every PR says, in plain language Brian can act on: **what breaks if the change is wrong**,
**how he would notice**, and **how it is rolled back** (one line; if it cannot be undone in
two minutes, say so — that is the case where his sign-off carries weight). Plus the
verbatim test output, and "not live until pulled/deployed" where that applies. Every PR
carries `--reviewer brianroberg --assignee brianroberg` so it reaches his GitHub inbox.
If the diff touches a user-facing surface, the `regression-test` result goes in too.

## 10. Per-repo REVIEW.md

A repo's `REVIEW.md` is its own reviewer guide: what the repo is, what a change there can
break, what counts as an interface, what reviewers tend to miss. Read it before reviewing;
add one when a repo has none and a review is about to run.

## Environment notes: Brian's MacBook

Facts about Claude Code's macOS sandbox on Brian's MacBook (2026-10-19), which differ from
the agent container:

- `gh` verifies TLS through the keychain, which the sandbox blocks; the fix is
  `"env": {"SSL_CERT_FILE": "/etc/ssl/cert.pem"}` in `~/.claude/settings.json`. Without it
  `gh auth status` reports an invalid token — a consequence, not the cause.
- `.git/config` is not writable in the sandbox, so `git config user.*` and `git push -u`
  fail with "could not lock config file". Set the identity with `GIT_AUTHOR_NAME`,
  `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, `GIT_COMMITTER_EMAIL`, and push without `-u`.
- The shell is fish: `set VAR value`, not `VAR=value`; `; and`, not `&&`.

PRACTICES LOADED
