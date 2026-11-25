#!/bin/bash
# Tests for drop-idle-notice.sh (installed as ~/.config/cmux/drop-idle-notice.sh), the cmux notification hook that drops Claude Code's idle notice.
# cmux pipes a notification policy JSON on stdin; the hook prints a patch or nothing.
SCRIPT="${1:-$(cd "$(dirname "$0")/.." && pwd)/drop-idle-notice.sh}"
fails=0
check() { if [ "$2" == "$3" ]; then echo "ok   $1"; else echo "FAIL $1"; echo "       expected: $2"; echo "       actual:   $3"; fails=$((fails + 1)); fi; }
run() { printf '%s' "$1" | env -i PATH="/usr/bin:/bin" HOME="$HOME" "$SCRIPT" 2>&1; }
policy() { # title, body
  printf '{"version":1,"notification":{"title":"%s","subtitle":"","body":"%s"},"effects":{"record":true,"markUnread":true,"reorderWorkspace":true,"desktop":true,"sound":true,"command":true,"paneFlash":true}}' "$1" "$2"
}
all_off='{"effects":{"record":false,"markUnread":false,"reorderWorkspace":false,"desktop":false,"sound":false,"command":false,"paneFlash":false}}'

check "the idle notice has every effect turned off" "$all_off" "$(run "$(policy "Claude Code" "Claude is waiting for your input")")"
check "a permission prompt is left alone" "" "$(run "$(policy "Claude Code" "Claude needs your permission")")"
check "a question notice is left alone" "" "$(run "$(policy "Claude Code" "Claude Code needs your attention")")"
check "the same words from another sender are left alone" "" "$(run "$(policy "Build" "Claude is waiting for your input")")"
check "a longer body that contains the phrase is left alone" "" "$(run "$(policy "Claude Code" "Claude is waiting for your input on the deploy")")"
check "empty input prints nothing" "" "$(run "")"
check "malformed input prints nothing" "" "$(run "{not json")"
echo "failures=$fails"
exit "$fails"
