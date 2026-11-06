---
name: regression-test
description: Use before calling any PR ready that touches a user-facing surface (routes, templates, static JS, forms), or when Brian asks to "regression test", "make sure nothing broke", or "check the app still works". Runs the project's browser regression pass against a live, seeded, never-production server via the regression-kit plugin (or the project's own seeded-server skill), and records the result on the PR.
---

# Regression test against a seeded server

**Standing rule (Brian, by voice, 2026-10-15):** one approach across projects, adapted per
project, never forgotten. A PR that touches a user-facing surface is not ready without a
regression result on the record. Unit tests prove logic; this pass proves the pages render,
the flows work and the forms submit, in a real browser, against real-shaped data — and it
does so **before anything touches production data**, which is the containment reason it exists.

## The standard

Two halves, both decided 2026-10-15:

1. **Code: the `regression-kit` pytest plugin** (`brianroberg/regression-kit`, installed per
   project with `uv add --dev "regression-kit @ git+https://github.com/brianroberg/regression-kit"`).
   It provides the `live_app` session fixture (starts the app from a per-project
   `live_app_config`, free port, readiness poll, process-group teardown), the `functional`
   marker, and the browser guard (`pytest -m functional` skips without Chromium;
   `--require-browser` turns that into an error so CI never passes silently). Its README has
   the usage example, the seed convention and the CI job yaml.
2. **Process: this skill.** When to run, what to run, what to record.

Projects that predate the kit keep working their own way until migrated:
training-reports has `seeded-test-server` + `playwright-regression-test` (Playwright MCP walk);
todo-api has `tests/test_functional.py` (the fixture the kit generalises); mlb-scores has
pytest-playwright e2e against a fake upstream.
When you touch one of those, use what it has; **adding regression-kit is the first task of the
next piece of work there**, not an afterthought.

mlbui is on the kit (brianroberg/mlbui#83) and has two checks, and a PR there records both.
`make test-functional` is its kit pass: Chromium through the pages against mlbui on stub
upstreams, with no MLB.tv account. Its `e2e-regression` skill (live Docker stack, a real
MLB.tv feed) stays as the live check before a PR is called done: a stub can show the pages
work, not that a real feed plays.

## The seed (never production data)

- A per-project function writes **one fictional row per state the UI renders** into a temp
  database **before** the server starts (inside `live_app_config`, which is session-scoped).
- Fictional names and addresses only. Never a copy, excerpt or export of a production
  database; never a production `DATABASE_URL`. Pass `inherit_env=False` or set the database
  variable explicitly so an inherited shell variable cannot point the seeded copy at
  production.
- The temp database comes from `tmp_path_factory.mktemp(...)`, so pytest rotates it.

## When

- Before calling a PR ready, if the diff touches routes, templates, static JS, forms, or the
  server's startup/schema path.
- Before each sub-branch merge in a multi-part build, and before the final PR.
- Whenever Brian asks for a regression, smoke or "does it still work" check.

## What to run

```bash
uv run pytest -m functional --require-browser -q      # needs Chromium: uv run playwright install --with-deps chromium
```

The marker is `functional` by default; a project that already uses that name for something
else sets `regression_kit_marker` in its pytest ini options and runs with that name instead
(training-reports uses `browser`, because `functional` is its Node+jsdom marker). Check the
project's README_TESTING or pyproject before assuming.

On a machine without Chromium (this agent container has none), the same command errors at
setup by design. Say so, and run it where a browser exists: Brian's Mac, or CI once the
project's workflow carries `docs/ci/functional-tests.yml` from the kit (Brian copies workflow
files; the bot token cannot push them). Never report a skipped browser pass as a passed one.

## What to record (on the PR, verbatim)

- The command, the machine it ran on, and the summary line (`N passed`), or the exact reason
  it could not run here and where it will.
- For a failure: the test name, the server output tail the fixture prints, and whether the
  failure is in the change or pre-existing on `main`.

## What this does not replace

The adversarial review (AGENTS.md), unit and property tests, and the per-project smoke test
after deploy (`/health` plus a landing page, as training-reports does). This pass sits between
"tests pass" and "deployed": it is the proof that the app, as a user meets it, still works.
