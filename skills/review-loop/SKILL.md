---
name: review-loop
description: Use before calling any PR ready, or when Brian asks to "review this PR", "run the review loop", "is this PR ready", or "has this been reviewed". Chooses the review depth from what the diff changes, runs the adversarial review, fixes findings one commit each, caps the loop at two rounds, and records model, effort, agent counts and labels on the PR so the PR list says whether it has been checked.
---

# The review loop: from "tests pass" to "ready"

**Standing rule (AGENTS.md, "Handing Code Work to Brian"):** adversarial review happens before
Brian sees a PR, not after. He is not the correctness gate; the PR list is where he decides,
and a label there is what tells him a review ran. This skill is the procedure. The repo's own
`REVIEW.md`, where one exists, is read first: it says what that repo can break and what
reviewers there tend to miss.

## 1. Choose the depth from the diff, not from "it's a PR"

| The diff changes… | Depth |
|---|---|
| Docs, comments, tests, prose only | **No pipeline.** Read the diff yourself once, carefully, for contradictions with the rules it describes and for unbacked absolute claims. Label `reviewed:none` and say in the PR why. |
| Contained code, not in a daily-use failure path | **Single pass**: `/code-review high <target>`, run once, on Opus or Fable (not Sonnet; Brian, 2026-09-09). |
| Failure behaviour, error mapping, or data writes in a service Brian uses daily | **Fable pipeline**: `/code-review high <target>` with finders and verifiers. |

Put the level **first**: `/code-review high <target>`. A level after the target is not parsed
and the skill silently reuses the last level (that is how one review ran at `xhigh` by
accident). One pipeline per batch when several small PRs touch the same code.

**State the projected cost in one line before starting a pipeline**, so Brian can decline:
a Fable pipeline has measured 1–3M tokens (an Opus pipeline of the same shape can exceed
that); a single-agent `/code-review` is roughly 100–150k at `medium`, and one measured
`high` single pass on Opus was about 186k. The agent cannot read the plan
meter; saying the number out loud is the only budget control.

**The reviewer ladder is Fable, then Opus.** Fable is the default; Opus is the substitute
when Fable is unavailable. Never silently downgrade: if the intended tier did not run, say so
in the review comment and label the tier that actually ran.

## 2. Run the review

1. Read the repo's `REVIEW.md` (if any) and the PR diff.
2. A security-focused pass first: credentials printed or committed, writes to production
   data, PII in fixtures or text, token in a URL. (`/security-review` where available.)
3. `/code-review <level> <target>`.
4. Verify each candidate against the code before calling it a finding. A review record
   lists what was confirmed and what was refuted.

## 3. Fix, one commit per finding

- Each real finding is its own commit, the finding named in the subject
  (`repo: M2, fail closed when the config value is missing`), made as soon as it is green.
- The suite runs before every commit and its exit status gates the commit:
  `uv run pytest -q && git commit …`. No pipe between pytest and the commit.
- Design findings with a clearly dominant option: decide, fix, and record the decision in
  the PR under its own heading ("Decided in the fix round, veto by comment"), with what
  breaks if it is wrong and how Brian would notice. Ask him only when the options are
  balanced on his priorities, the change is hard to undo, or it touches people, money or
  external communication; then one question at a time, with context and a recommendation.
- A fix may narrow an absolute claim in docs; it may add one only together with the test
  that demonstrates it.

## 4. Second round, and the cap

A second round **only if a fix changed behaviour** (not prose). **Cap the loop at
two rounds.** After that, ship with the remaining findings recorded in the PR, not fixed, and
let Brian decide. (calendar-agent #11 ran four rounds; rounds 3 and 4 were findings the
previous round's own fixes had introduced.)

## 5. Record it on the PR

**The review comment's first line states the model, the effort and the finder/verifier
counts** — e.g. `Fable, high, 8 finders + 15 verifiers` or `Opus single pass, high, 1 agent`.
The level does not determine the counts, so they go in the comment, never in a label.
Then: findings confirmed/refuted, what was fixed (commit per finding), what remains, decisions
taken for veto, and the verbatim test output.

```bash
gh pr comment <n> -R <owner>/<repo> --body-file review-record.md
# or, editing the PR body from a file: capital -F, never -f (which sends the literal "@file")
gh api -X PATCH repos/<owner>/<repo>/pulls/<n> -F body=@pr-body.md
```

## 6. Labels: two per PR, updated on every push

Status — is the substance covered?

| label | meaning |
|---|---|
| `reviewed:adversarial` | a review ran and its findings are resolved; fix-only commits in response do not demote it |
| `reviewed:partial` | findings still open, or substantial new work landed after the review |
| `reviewed:none` | no adversarial review has run |

Depth — who reviewed and how hard: `review:fable-high`, `review:opus-high`, and so on
(`review:{fable,opus}-{xhigh,high,medium}`); the bare `review:fable` / `review:opus` when the
level was not recorded. The label records what actually ran.

`gh pr edit --add-label` fails on these repos (a GraphQL deprecation), so apply labels over
REST — a PR is an issue for this purpose. The endpoints are GitHub's
`POST /repos/{owner}/{repo}/issues/{n}/labels` and
`DELETE /repos/{owner}/{repo}/issues/{n}/labels/{name}`:

```bash
gh api -X POST repos/<owner>/<repo>/issues/<n>/labels -f 'labels[]=reviewed:adversarial' -f 'labels[]=review:fable-high'
gh api -X DELETE repos/<owner>/<repo>/issues/<n>/labels/reviewed:none
```

A stale green label is worse than none, because it is the one Brian trusts: re-label after
every push.

## 7. Make it reach him

Every PR carries a reviewer request and an assignee, so it lands in his GitHub inbox:

```bash
gh pr create --base main --head <branch> --reviewer brianroberg --assignee brianroberg --body-file pr-body.md
# on an existing PR
gh api -X POST repos/<owner>/<repo>/pulls/<n>/requested_reviewers -f 'reviewers[]=brianroberg'
gh api -X POST repos/<owner>/<repo>/issues/<n>/assignees -f 'assignees[]=brianroberg'
```

The PR body says, in plain language, what breaks if the change is wrong, how Brian would
notice, and how it is rolled back. A PR touching a user-facing surface also carries the
`regression-test` result. A change that cannot be cheaply undone says so: that is the case
where his sign-off carries weight.
