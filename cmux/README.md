# cmux sidebar scripts

Three small bash scripts that connect Claude Code to the cmux sidebar on Brian's MacBook,
with their tests. They are not skills: they are installed by hand as a status line
command, as Claude Code hooks and as a cmux notification hook.

This directory is where they are edited. The installed copies are separate files (see
[Installing](#installing)), so a change here does nothing until it is installed.

## The scripts

| Script | Installed as | Called by |
| --- | --- | --- |
| `cmux-model-status.sh` | `~/.claude/cmux-model-status.sh` | Claude Code status line; `SessionEnd` hook with `--clear` |
| `cmux-clear-answered.sh` | `~/.claude/cmux-clear-answered.sh` | Claude Code hooks: `Notification` (`mark`); `UserPromptSubmit`, `Stop`, `PostToolUse` of `AskUserQuestion` (`clear`) |
| `drop-idle-notice.sh` | `~/.config/cmux/drop-idle-notice.sh` | cmux notification hook |

### `cmux-model-status.sh`

As the status line, it reads Claude Code's status JSON on stdin and prints
`<model> · <effort> · Context N%`. The effort and context parts are left out when the
input does not carry them, and a missing model prints `Claude`. Inside cmux
(`CMUX_WORKSPACE_ID` set) it also:

- mirrors that line to one sidebar status entry per terminal, keyed `model_` plus the
  first 8 characters of the surface id (of the workspace id when `CMUX_SURFACE_ID` is
  unset), at priority 1;
- sets the workspace title to the session's name, when the session has one and the
  workspace has no custom title or still has the title this script set.

With `--clear` it removes the terminal's entry and, if the workspace title is still the
one it set, hands the title back.

It keeps a cache per terminal and per workspace under `TMPDIR`, so an unchanged line
makes no cmux call. An entry older than five minutes is sent again, and a cmux call that
failed is not cached, so the next refresh retries it. A failing cmux does not change
what is printed.

Fields read from the status JSON: `model.display_name`, `model.id`, `effort.level`,
`context_window.used_percentage`, `session_name`.

### `cmux-clear-answered.sh`

Clears a terminal's cmux notifications once the prompt they announced has been dealt
with. `mark` records that this terminal raised a notification; `clear` clears the
terminal's notifications if that record exists. It prints nothing, because Claude Code
can show or inject a hook's stdout, and it does not read the hook payload.

`clear` is deliberately not wired to every tool call. A tool finishing in a subagent or
in the background could then clear a permission alert whose prompt is still open. The
script's header comment carries the same reasoning; keep the two in step.

### `drop-idle-notice.sh`

cmux pipes a notification policy JSON to the hook. For a notification titled
`Claude Code` whose body is exactly `Claude is waiting for your input`, the script
prints a patch that turns off each of the seven effects. For the other inputs the tests
cover (a permission prompt, a question notice, the same words from another sender, a
longer body, empty or malformed input) it prints nothing, which leaves cmux's default
behaviour in place.

The accepted trade-off (Brian, 2026-11-25) is in the script's header: the idle notice is
also the alert for a turn that ends with a question written as ordinary text.

## Configuration that goes with them

The settings files themselves are not in this repo and must not be copied here: the
Claude Code user settings file holds a credential. These are the entries the scripts
depend on, written out from scratch.

Claude Code user settings (`~/.claude/settings.json`):

```json
{
  "statusLine": { "type": "command", "command": "~/.claude/cmux-model-status.sh" },
  "hooks": {
    "SessionEnd":       [{ "hooks": [{ "type": "command", "command": "\"$HOME/.claude/cmux-model-status.sh\" --clear", "timeout": 5 }] }],
    "Notification":     [{ "hooks": [{ "type": "command", "command": "\"$HOME/.claude/cmux-clear-answered.sh\" mark", "timeout": 5 }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "\"$HOME/.claude/cmux-clear-answered.sh\" clear", "timeout": 5 }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "\"$HOME/.claude/cmux-clear-answered.sh\" clear", "timeout": 5 }] }],
    "PostToolUse":      [{ "matcher": "AskUserQuestion",
                           "hooks": [{ "type": "command", "command": "\"$HOME/.claude/cmux-clear-answered.sh\" clear", "timeout": 5 }] }]
  }
}
```

Merge these into the existing keys; other hooks in the file (the `PreToolUse` ones, for
instance) are unrelated.

cmux config (`~/.config/cmux/cmux.json`), inside `notifications`:

```json
{
  "agentIdleReminder": false,
  "hooks": [
    { "id": "drop-claude-idle-notice", "command": "\"$HOME/.config/cmux/drop-idle-notice.sh\"", "timeoutSeconds": 5 }
  ]
}
```

`agentIdleReminder` turns off cmux's own reminder; the hook drops the one Claude Code
sends. Run `cmux reload-config` after changing the file.

## Tests

```bash
uv run pytest tests/test_cmux_scripts.py -v          # all three suites, as CI runs them
bash cmux/tests/test_cmux_model_status.sh            # one suite, against the repo copy
bash cmux/tests/test_cmux_model_status.sh ~/.claude/cmux-model-status.sh   # against the installed copy
```

Each suite prints one `ok` or `FAIL` line per case and exits with the number of
failures. The script under test runs under `env -i` with `PATH=/usr/bin:/bin`, and where
a case sets the cmux variables it points `CMUX_BUNDLED_CLI_PATH` at a fake `cmux` that
records its arguments in place of the real one. They need
`jq` (in `/usr/bin`, `/opt/homebrew/bin` or `/usr/local/bin`; the scripts add the last
two to `PATH` themselves) and `git` for one fixture. Fixture values are synthetic
(workspace ids like `WS-1`, made-up surface ids, a model named `M`).

Change a script test-first: add the failing case to its suite, watch it fail, then edit
the script.

## Installing

The installed files are copies, not symlinks into this checkout. A symlink would make
whichever branch is checked out here, a half-finished one included, the status line and
hooks of the sessions running at the time. After a change is merged and pulled:

```bash
install -m 755 cmux/cmux-model-status.sh cmux/cmux-clear-answered.sh ~/.claude/
install -m 755 cmux/drop-idle-notice.sh ~/.config/cmux/
```

To see whether an installed copy has drifted from the repo:

```bash
cmp cmux/cmux-model-status.sh   ~/.claude/cmux-model-status.sh
cmp cmux/cmux-clear-answered.sh ~/.claude/cmux-clear-answered.sh
cmp cmux/drop-idle-notice.sh    ~/.config/cmux/drop-idle-notice.sh
```

## For a maintainer

- Written against cmux 0.65.2 and the Claude Code status line input as of 2026-11-25.
- cmux commands used: `set-status`, `clear-status`, `workspace list --json --id-format
  both`, `workspace rename --title`, `workspace-action --action clear-name`,
  `clear-notifications --workspace --surface`.
- Trying a script by hand against the real cmux with a made-up surface id misleads: the
  session that wrote these scripts found that `workspace list` returns nothing when the
  caller's surface id is not real. Use the suites, or a real terminal.

Known limits, from the session that wrote the scripts and from the review of the move
into this repo, both on 2026-11-25. No test covers these:

- Two named sessions in one workspace share one workspace title, and each renames it to
  its own name when its status line refreshes, so the title alternates (reproduced in
  review with a fake cmux).
- A session that dies without `SessionEnd` leaves its sidebar entry and title behind.
- Two sessions prompting at the same moment produced one notification in a trial.
- An approved permission prompt's sidebar line stays until the turn ends or the next
  prompt is submitted.

Removed at Brian's request on 2026-11-25, so not to be brought back from older outputs:
an icon on the model entry, and `Branch:` and `CWD:` entries. cmux's own branch and
directory rows cover those and also show outside agent sessions; the last block of
`test_cmux_model_status.sh` checks that a directory in the input adds no entries.
