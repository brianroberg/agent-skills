#!/bin/bash
# Tests for cmux-clear-answered.sh (installed as ~/.claude/cmux-clear-answered.sh), from the caller's shape: Claude Code runs
# it as a hook command with one argument ("mark" on Notification; "clear" on
# UserPromptSubmit, Stop, and PostToolUse of AskUserQuestion), a JSON payload on stdin it does not need,
# and treats stdout as text to show or inject, so it must print nothing.
SCRIPT="${1:-$(cd "$(dirname "$0")/.." && pwd)/cmux-clear-answered.sh}"
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
calls="$work/calls"; : > "$calls"
printf '#!/bin/bash\nprintf "%%s\\n" "$*" >> "%s"\n' "$calls" > "$work/cmux"; chmod +x "$work/cmux"
printf '#!/bin/bash\necho boom >&2\nexit 1\n' > "$work/broken"; chmod +x "$work/broken"
fails=0
check() { if [ "$2" == "$3" ]; then echo "ok   $1"; else echo "FAIL $1"; echo "       expected: $2"; echo "       actual:   $3"; fails=$((fails + 1)); fi; }
# A hook's stdin is a pipe that may stay open, so the script gets a FIFO that never
# reaches end of file; a run that waits on it is killed after 2 s and reports rc=143.
mkfifo "$work/fifo"; exec 9<>"$work/fifo"
run() {
  local mode="$1"; shift
  env -i PATH="/usr/bin:/bin" HOME="$HOME" TMPDIR="$work" "$@" "$SCRIPT" "$mode" < "$work/fifo" > "$work/out" 2>&1 &
  local pid=$!; ( sleep 2; kill "$pid" 2>/dev/null ) & local wd=$!
  wait "$pid" 2>/dev/null; local rc=$?; kill "$wd" 2>/dev/null; wait "$wd" 2>/dev/null
  out="$(cat "$work/out")rc=$rc"
}
in_cmux=(CMUX_WORKSPACE_ID=WS-1 CMUX_SURFACE_ID=SF-1 CMUX_BUNDLED_CLI_PATH="$work/cmux")

run clear "${in_cmux[@]}"
check "clear with nothing marked calls nothing and prints nothing" "rc=0|" "$out|$(cat "$calls")"

run mark "${in_cmux[@]}"
check "mark prints nothing and does not call cmux" "rc=0|" "$out|$(cat "$calls")"
run clear "${in_cmux[@]}"
check "clear after mark clears this terminal's notifications" \
  "rc=0|clear-notifications --workspace WS-1 --surface SF-1" "$out|$(cat "$calls")"
run clear "${in_cmux[@]}"
check "a second clear does not call cmux again" "1" "$(wc -l < "$calls" | tr -d ' ')"

: > "$calls"
run mark CMUX_WORKSPACE_ID=WS-1 CMUX_SURFACE_ID=SF-2 CMUX_BUNDLED_CLI_PATH="$work/cmux"
run clear "${in_cmux[@]}"
check "a mark in another terminal does not clear this one" "" "$(cat "$calls")"

: > "$calls"
run mark CMUX_BUNDLED_CLI_PATH="$work/cmux"; a="$out"
run clear CMUX_BUNDLED_CLI_PATH="$work/cmux"
check "outside cmux both modes do nothing" "rc=0|rc=0|" "$a|$out|$(cat "$calls")"

run mark CMUX_WORKSPACE_ID=WS-3 CMUX_SURFACE_ID=SF-3 CMUX_BUNDLED_CLI_PATH="$work/broken"
run clear CMUX_WORKSPACE_ID=WS-3 CMUX_SURFACE_ID=SF-3 CMUX_BUNDLED_CLI_PATH="$work/broken"
check "a failing cmux is quiet and exits 0" "rc=0" "$out"
: > "$calls"
run clear CMUX_WORKSPACE_ID=WS-3 CMUX_SURFACE_ID=SF-3 CMUX_BUNDLED_CLI_PATH="$work/cmux"
check "a failed clear is retried next time" "clear-notifications --workspace WS-3 --surface SF-3" "$(cat "$calls")"

: > "$calls"
run mark "${in_cmux[@]}"; run "" "${in_cmux[@]}"
check "an unknown mode does nothing" "rc=0|" "$out|$(cat "$calls")"

echo "failures=$fails"
exit "$fails"
