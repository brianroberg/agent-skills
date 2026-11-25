#!/bin/bash
# Claude Code hook: removes this terminal's notifications from cmux once the prompt
# they announced has been dealt with, so "Claude needs your permission" does not
# linger in the cmux sidebar after it has been answered.
#
#   mark   on Notification: remember that this terminal has raised a notification.
#   clear  on UserPromptSubmit, Stop, and PostToolUse of AskUserQuestion only: if one
#          was raised, clear it.
#
# "clear" is deliberately not run after every tool call: a tool finishing in a subagent
# or in the background could then clear a permission alert whose prompt is still open.
# So an approved permission prompt's line stays until the turn ends or the next prompt.
# The marker file keeps "clear" to a file test when there is nothing to clear. The script prints nothing (hook stdout can be shown or injected)
# and does not read the hook payload on stdin.
[ -n "$CMUX_WORKSPACE_ID" ] && [ -n "$CMUX_SURFACE_ID" ] || exit 0
marker="${TMPDIR:-/tmp}/cmux-notice-pending-$CMUX_SURFACE_ID"

case "$1" in
  mark)
    : > "$marker" ;;
  clear)
    # A failed clear keeps the marker, so the next hook tries again.
    if [ -e "$marker" ] && "${CMUX_BUNDLED_CLI_PATH:-cmux}" clear-notifications \
        --workspace "$CMUX_WORKSPACE_ID" --surface "$CMUX_SURFACE_ID" >/dev/null 2>&1; then
      rm -f "$marker"
    fi ;;
esac
exit 0
