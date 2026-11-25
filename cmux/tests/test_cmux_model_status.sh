#!/bin/bash
# Tests for cmux-model-status.sh (installed as ~/.claude/cmux-model-status.sh), written from the caller's shape:
# Claude Code pipes a JSON object on stdin and shows whatever stdout prints.
# A fake cmux records its arguments so no real sidebar is touched.
SCRIPT="${1:-$(cd "$(dirname "$0")/.." && pwd)/cmux-model-status.sh}"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
fake="$work/cmux"
calls="$work/calls"
printf '#!/bin/bash\nprintf "%%s\\n" "$*" >> "%s"\n' "$calls" > "$fake"
chmod +x "$fake"

fails=0
check() { # name, expected, actual
  if [ "$2" == "$3" ]; then echo "ok   $1"; else echo "FAIL $1"; echo "       expected: $2"; echo "       actual:   $3"; fails=$((fails + 1)); fi
}
run() { # stdin json; remaining args are VAR=value for the environment
  local json="$1"; shift
  printf '%s' "$json" | env -i PATH="/usr/bin:/bin" HOME="$HOME" TMPDIR="$work" "$@" "$SCRIPT" 2>"$work/stderr"
}
in_cmux=(CMUX_WORKSPACE_ID=WS-1 CMUX_SURFACE_ID=AAAAAAAA-1111 CMUX_BUNDLED_CLI_PATH="$fake")

both='{"model":{"id":"claude-x","display_name":"Fable 5.2"},"effort":{"level":"high"}}'
no_effort='{"model":{"id":"claude-x","display_name":"Fable 5.2"}}'

# 1. Outside cmux: a clean line, and cmux is not called.
: > "$calls"
check "outside cmux prints model and effort" "Fable 5.2 · high" "$(run "$both" CMUX_BUNDLED_CLI_PATH="$fake")"
check "outside cmux does not call cmux" "" "$(cat "$calls")"

# 2. No effort in the input: the model alone, no dangling separator.
check "no effort prints the model alone" "Fable 5.2" "$(run "$no_effort")"

# 3. Inside cmux: one set-status, keyed by surface, aimed at the workspace.
: > "$calls"
check "inside cmux prints the same line" "Fable 5.2 · high" "$(run "$both" "${in_cmux[@]}")"
check "inside cmux sets a per-surface status" \
  "set-status model_AAAAAAAA Fable 5.2 · high --workspace WS-1 --priority 1" "$(cat "$calls")"

# 4. Same label again: no second call. A changed label: one more call.
run "$both" "${in_cmux[@]}" > /dev/null
check "unchanged label does not call cmux again" "1" "$(wc -l < "$calls" | tr -d ' ')"
run "$no_effort" "${in_cmux[@]}" > /dev/null
check "changed label calls cmux again" "2" "$(wc -l < "$calls" | tr -d ' ')"

# 4b. A cache entry older than five minutes is re-sent, so a restarted cmux gets the pill back.
: > "$calls"
run "$both" CMUX_WORKSPACE_ID=WS-3 CMUX_SURFACE_ID=DDDDDDDD-4444 CMUX_BUNDLED_CLI_PATH="$fake" > /dev/null
touch -t 202001010000 "$work/cmux-model-status-DDDDDDDD-4444"
run "$both" CMUX_WORKSPACE_ID=WS-3 CMUX_SURFACE_ID=DDDDDDDD-4444 CMUX_BUNDLED_CLI_PATH="$fake" > /dev/null
check "an old cache entry is re-sent" "2" "$(wc -l < "$calls" | tr -d ' ')"

# 5. A second session in the same workspace gets its own entry.
: > "$calls"
run "$both" CMUX_WORKSPACE_ID=WS-1 CMUX_SURFACE_ID=BBBBBBBB-2222 CMUX_BUNDLED_CLI_PATH="$fake" > /dev/null
check "second surface gets its own key" \
  "set-status model_BBBBBBBB Fable 5.2 · high --workspace WS-1 --priority 1" "$(cat "$calls")"

# 6. A failing cmux leaves the line intact and stderr quiet, and is retried next time.
printf '#!/bin/bash\necho boom >&2\nexit 1\n' > "$work/broken"; chmod +x "$work/broken"
out=$(run "$both" CMUX_WORKSPACE_ID=WS-2 CMUX_SURFACE_ID=CCCCCCCC-3333 CMUX_BUNDLED_CLI_PATH="$work/broken")
check "failing cmux still prints the line" "Fable 5.2 · high" "$out"
check "failing cmux prints nothing on stderr" "" "$(cat "$work/stderr")"
: > "$calls"
run "$both" CMUX_WORKSPACE_ID=WS-2 CMUX_SURFACE_ID=CCCCCCCC-3333 CMUX_BUNDLED_CLI_PATH="$fake" > /dev/null
check "a failed update is retried" "1" "$(wc -l < "$calls" | tr -d ' ')"

# 7. Empty or broken input: no crash, no "null" on the line.
check "empty input prints a placeholder" "Claude" "$(run '')"
check "null model prints a placeholder" "Claude" "$(run '{"model":null}')"

# 8. Context use follows the effort level, as a whole percent; absent or null, it is left out.
#    Zero is left out too: after a compaction, until the next model reply, Claude Code
#    sends 0 with all-zero token counts, and its docs say to treat that as empty.
ctx='{"model":{"display_name":"Fable 5.2"},"effort":{"level":"high"},"context_window":{"used_percentage":12}}'
ctx_frac='{"model":{"display_name":"Fable 5.2"},"effort":{"level":"high"},"context_window":{"used_percentage":41.6}}'
ctx_null='{"model":{"display_name":"Fable 5.2"},"effort":{"level":"high"},"context_window":{"used_percentage":null}}'
ctx_only='{"model":{"display_name":"Fable 5.2"},"context_window":{"used_percentage":1}}'
ctx_compacted='{"model":{"display_name":"Fable 5.2"},"effort":{"level":"high"},"context_window":{"total_input_tokens":0,"total_output_tokens":0,"context_window_size":1000000,"current_usage":{"input_tokens":0,"output_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0},"used_percentage":0,"remaining_percentage":100}}'
ctx_half='{"model":{"display_name":"Fable 5.2"},"effort":{"level":"high"},"context_window":{"used_percentage":0.5}}'
ctx_tiny='{"model":{"display_name":"Fable 5.2"},"effort":{"level":"high"},"context_window":{"used_percentage":0.3}}'
check "context percent follows the effort" "Fable 5.2 · high · Context 12%" "$(run "$ctx")"
check "context percent is rounded" "Fable 5.2 · high · Context 42%" "$(run "$ctx_frac")"
check "null context percent is left out" "Fable 5.2 · high" "$(run "$ctx_null")"
check "context percent without effort" "Fable 5.2 · Context 1%" "$(run "$ctx_only")"
check "zero percent after a compaction is left out" "Fable 5.2 · high" "$(run "$ctx_compacted")"
check "a percent that rounds to one is shown" "Fable 5.2 · high · Context 1%" "$(run "$ctx_half")"
check "a percent that rounds to zero is left out" "Fable 5.2 · high" "$(run "$ctx_tiny")"
: > "$calls"
run "$ctx_compacted" CMUX_WORKSPACE_ID=WS-5 CMUX_SURFACE_ID=LLLLLLLL-2222 CMUX_BUNDLED_CLI_PATH="$fake" > /dev/null
check "the sidebar entry leaves out a zero percent too" \
  "set-status model_LLLLLLLL Fable 5.2 · high --workspace WS-5 --priority 1" "$(cat "$calls")"
: > "$calls"
run "$ctx" CMUX_WORKSPACE_ID=WS-4 CMUX_SURFACE_ID=EEEEEEEE-5555 CMUX_BUNDLED_CLI_PATH="$fake" > /dev/null
check "the sidebar gets the context percent too" \
  "set-status model_EEEEEEEE Fable 5.2 · high · Context 12% --workspace WS-4 --priority 1" "$(cat "$calls")"

# 9. --clear (the SessionEnd hook): removes this surface's pill and cache, prints nothing,
#    and the next status line refresh sets the pill again. (Stdin is checked in 9b.)
clear_run() { env -i PATH="/usr/bin:/bin" HOME="$HOME" TMPDIR="$work" "$@" "$SCRIPT" --clear < /dev/null 2>"$work/stderr"; }
: > "$calls"
out=$(clear_run CMUX_WORKSPACE_ID=WS-4 CMUX_SURFACE_ID=EEEEEEEE-5555 CMUX_BUNDLED_CLI_PATH="$fake"); rc=$?
check "--clear clears this surface's pill" "clear-status model_EEEEEEEE --workspace WS-4" "$(cat "$calls")"
check "--clear prints nothing" "" "$out$(cat "$work/stderr")"
check "--clear exits 0" "0" "$rc"
check "--clear removes the cache" "gone" "$([ -e "$work/cmux-model-status-EEEEEEEE-5555" ] && echo present || echo gone)"
run "$ctx" CMUX_WORKSPACE_ID=WS-4 CMUX_SURFACE_ID=EEEEEEEE-5555 CMUX_BUNDLED_CLI_PATH="$fake" > /dev/null
check "a refresh after --clear sets the pill again" "2" "$(wc -l < "$calls" | tr -d ' ')"
: > "$calls"
clear_run CMUX_BUNDLED_CLI_PATH="$fake"; rc=$?
check "--clear outside cmux does not call cmux" "" "$(cat "$calls")"
check "--clear outside cmux exits 0" "0" "$rc"
clear_run CMUX_WORKSPACE_ID=WS-4 CMUX_SURFACE_ID=EEEEEEEE-5555 CMUX_BUNDLED_CLI_PATH="$work/broken"; rc=$?
check "--clear with a failing cmux exits 0 quietly" "0" "$rc$(cat "$work/stderr")"

# 9b. A hook's stdin is a pipe that may stay open, so --clear gets a FIFO that never
#     reaches end of file; a run that waits on it is killed after 2 s and reports 143.
mkfifo "$work/fifo"; exec 9<>"$work/fifo"
env -i PATH="/usr/bin:/bin" HOME="$HOME" TMPDIR="$work" CMUX_WORKSPACE_ID=WS-4 CMUX_SURFACE_ID=EEEEEEEE-5555 \
  CMUX_BUNDLED_CLI_PATH="$fake" "$SCRIPT" --clear < "$work/fifo" > /dev/null 2>&1 &
pid=$!; ( sleep 2; kill "$pid" 2>/dev/null ) & wd=$!
wait "$pid" 2>/dev/null; rc=$?; kill "$wd" 2>/dev/null; wait "$wd" 2>/dev/null
check "--clear does not wait on an open stdin" "0" "$rc"

# 10. Workspace title: a named session's name becomes the workspace title while it runs,
#     and --clear hands the title back. A title the script did not set is left alone.
#     This fake cmux also answers "workspace list" from a file the test controls.
fake2="$work/cmux2"
printf '#!/bin/bash\nprintf "%%s\\n" "$*" >> "%s"\nif [ "$1 $2" == "workspace list" ]; then cat "%s"; fi\n' "$calls" "$work/wslist.json" > "$fake2"
chmod +x "$fake2"
ws_list() { # workspace id, custom title ("" for none)
  if [ -n "$2" ]; then printf '{"workspaces":[{"id":"%s","custom_title":"%s","has_custom_title":true}]}' "$1" "$2"
  else printf '{"workspaces":[{"id":"%s","custom_title":null,"has_custom_title":false}]}' "$1"; fi > "$work/wslist.json"
}
title_calls() { grep -E '^workspace rename|clear-name' "$calls" 2>/dev/null; }
named='{"model":{"display_name":"M"},"session_name":"my session"}'
renamed='{"model":{"display_name":"M"},"session_name":"other"}'
unnamed='{"model":{"display_name":"M"}}'
ws9=(CMUX_WORKSPACE_ID=WS-9 CMUX_SURFACE_ID=FFFFFFFF-6666 CMUX_BUNDLED_CLI_PATH="$fake2")
ws10=(CMUX_WORKSPACE_ID=WS-10 CMUX_SURFACE_ID=GGGGGGGG-7777 CMUX_BUNDLED_CLI_PATH="$fake2")

: > "$calls"; ws_list WS-9 ""
check "a named session still prints the usual line" "M" "$(run "$named" "${ws9[@]}")"
check "a named session sets the workspace title" "workspace rename WS-9 --title my session" "$(title_calls)"
ws_list WS-9 "my session"
before=$(wc -l < "$calls" | tr -d ' ')
run "$named" "${ws9[@]}" > /dev/null
check "an unchanged name makes no further cmux calls" "$before" "$(wc -l < "$calls" | tr -d ' ')"
: > "$calls"
run "$renamed" "${ws9[@]}" > /dev/null
check "a changed session name replaces the title it set" "workspace rename WS-9 --title other" "$(title_calls)"

: > "$calls"; ws_list WS-10 "mine"
run "$named" "${ws10[@]}" > /dev/null
check "a title someone else set is left alone" "" "$(title_calls)"
: > "$calls"
clear_run "${ws10[@]}"
check "--clear leaves someone else's title alone" "" "$(title_calls)"

: > "$calls"; ws_list WS-9 "mine"
clear_run "${ws9[@]}"
check "--clear leaves a title renamed by hand since" "" "$(title_calls)"

: > "$calls"; ws_list WS-9 ""
run "$named" "${ws9[@]}" > /dev/null
: > "$calls"; ws_list WS-9 "my session"
clear_run "${ws9[@]}"
check "--clear hands back the title it set" "workspace-action --action clear-name --workspace WS-9" "$(title_calls)"
: > "$calls"
clear_run "${ws9[@]}"
check "a second --clear does not clear the name again" "" "$(title_calls)"

: > "$calls"; ws_list WS-9 ""
run "$unnamed" "${ws9[@]}" > /dev/null
check "an unnamed session does not touch the title" "" "$(grep -E '^workspace' "$calls")"

: > "$calls"; ws_list SOME-OTHER ""
run "$named" CMUX_WORKSPACE_ID=WS-11 CMUX_SURFACE_ID=HHHHHHHH-8888 CMUX_BUNDLED_CLI_PATH="$fake2" > /dev/null
check "a workspace missing from the list is not renamed" "" "$(title_calls)"

: > "$calls"; ws_list ws-12 ""
run "$named" CMUX_WORKSPACE_ID=WS-12 CMUX_SURFACE_ID=IIIIIIII-9999 CMUX_BUNDLED_CLI_PATH="$fake2" > /dev/null
check "workspace ids match regardless of case" "workspace rename WS-12 --title my session" "$(title_calls)"

out=$(run "$named" CMUX_WORKSPACE_ID=WS-13 CMUX_SURFACE_ID=JJJJJJJJ-0000 CMUX_BUNDLED_CLI_PATH="$work/broken")
check "a failing cmux still prints the line for a named session" "M" "$out$(cat "$work/stderr")"

# 11. Branch and directory are left to cmux's own sidebar rows (they also show outside
#     agent sessions), so a directory in the input adds no pills, and --clear removes
#     only the model pill.
home="$work/Home"; mkdir -p "$home/code/proj"
git init -q -b feature-x "$home/code/proj" 2>/dev/null
dirjson='{"model":{"display_name":"M"},"cwd":"'"$home"'/code/proj","workspace":{"current_dir":"'"$home"'/code/proj"}}'
ws20=(HOME="$home" CMUX_WORKSPACE_ID=WS-20 CMUX_SURFACE_ID=KKKKKKKK-1111 CMUX_BUNDLED_CLI_PATH="$fake")
: > "$calls"
check "directory input still prints only the usual line" "M" "$(run "$dirjson" "${ws20[@]}")"
check "the model pill is the only pill set" "set-status model_KKKKKKKK M --workspace WS-20 --priority 1" "$(cat "$calls")"
: > "$calls"
clear_run "${ws20[@]}"
check "--clear removes only the model pill" "clear-status model_KKKKKKKK --workspace WS-20" "$(cat "$calls")"

echo "failures=$fails"
exit "$fails"
