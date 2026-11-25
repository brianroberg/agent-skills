#!/bin/bash
# Claude Code status line: prints "<model> · <effort> · Context N%" and, inside cmux,
# mirrors it to a sidebar pill for this terminal's workspace. It also sets the
# workspace title to the session's name while the session runs. Branch and directory
# are left to cmux's own sidebar rows, which also show outside agent sessions.
#
# As the status line: Claude Code pipes a JSON object on stdin and shows what this
# prints on stdout. With --clear (the SessionEnd hook): removes this terminal's pill
# and hands the title back. The pill's key carries the surface id, so two Claude
# sessions in one workspace each get their own.

# Both callers inherit Claude Code's PATH, which may lack Homebrew.
PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"

cmux_bin="${CMUX_BUNDLED_CLI_PATH:-cmux}"
surface="${CMUX_SURFACE_ID:-$CMUX_WORKSPACE_ID}"
cache="${TMPDIR:-/tmp}/cmux-model-status-$surface"

# set_pill <name> <text> <priority>: calls cmux only when the text changes or the cache
# is over five minutes old (so a restarted cmux gets the pill back). An empty text
# removes the pill. A failed call is not cached, so it is retried.
set_pill() {
  local file="$cache" key="$1_${surface:0:8}"
  if [ -z "$2" ]; then
    if [ -e "$file" ] && "$cmux_bin" clear-status "$key" --workspace "$CMUX_WORKSPACE_ID" >/dev/null 2>&1; then
      rm -f "$file"
    fi
  elif [ "$(cat "$file" 2>/dev/null)" != "$2" ] || [ -z "$(find "$file" -mmin -5 2>/dev/null)" ]; then
    if "$cmux_bin" set-status "$key" "$2" --workspace "$CMUX_WORKSPACE_ID" --priority "$3" >/dev/null 2>&1; then
      printf '%s' "$2" > "$file"
    fi
  fi
}

# Workspace title. The session's name becomes the workspace title while it runs. The
# title cache holds two lines: the title this script set (empty if none) and the
# session name it last acted on. A custom title the script did not set is left alone.
title_cache="${TMPDIR:-/tmp}/cmux-model-title-$CMUX_WORKSPACE_ID"

# Prints "found:<custom title or empty>" for this workspace, or nothing if cmux
# does not list it (so an unknown workspace is never renamed).
workspace_custom_title() {
  "$cmux_bin" workspace list --json --id-format both 2>/dev/null |
    jq -r --arg id "$CMUX_WORKSPACE_ID" '.workspaces[]?
      | select(((.id // "") | ascii_downcase) == ($id | ascii_downcase))
      | "found:" + (.custom_title // "")' 2>/dev/null | head -1
}

if [ "$1" == "--clear" ]; then
  if [ -n "$CMUX_WORKSPACE_ID" ]; then
    rm -f "$cache"
    "$cmux_bin" clear-status "model_${surface:0:8}" --workspace "$CMUX_WORKSPACE_ID" >/dev/null 2>&1
    owned=$(head -1 "$title_cache" 2>/dev/null)
    rm -f "$title_cache"
    if [ -n "$owned" ] && [ "$(workspace_custom_title)" == "found:$owned" ]; then
      "$cmux_bin" workspace-action --action clear-name --workspace "$CMUX_WORKSPACE_ID" >/dev/null 2>&1
    fi
  fi
  exit 0
fi

input=$(cat)
model=$(jq -r '.model.display_name // .model.id // empty' <<<"$input" 2>/dev/null)
effort=$(jq -r '.effort.level // empty' <<<"$input" 2>/dev/null)
# A zero percent is left out like a missing one: after a compaction, until the next
# model reply, Claude Code sends 0.
context=$(jq -r '.context_window.used_percentage | numbers | round | select(. > 0)' <<<"$input" 2>/dev/null)
label="${model:-Claude}${effort:+ · $effort}${context:+ · Context $context%}"

if [ -n "$CMUX_WORKSPACE_ID" ]; then
  set_pill model "$label" 1

  # Ask cmux about the title only when the session name changes or the cache is old.
  name=$(jq -r '.session_name // empty' <<<"$input" 2>/dev/null)
  if [ -n "$name" ]; then
    owned=$(sed -n 1p "$title_cache" 2>/dev/null)
    seen=$(sed -n 2p "$title_cache" 2>/dev/null)
    if [ "$seen" != "$name" ] || [ -z "$(find "$title_cache" -mmin -5 2>/dev/null)" ]; then
      current=$(workspace_custom_title)
      if [ "$current" == "found:" ] || { [ -n "$owned" ] && [ "$current" == "found:$owned" ]; }; then
        if [ "$current" == "found:$name" ] ||
            "$cmux_bin" workspace rename "$CMUX_WORKSPACE_ID" --title "$name" >/dev/null 2>&1; then
          printf '%s\n%s\n' "$name" "$name" > "$title_cache"
        fi
      elif [ -n "$current" ]; then
        printf '\n%s\n' "$name" > "$title_cache"   # someone else's title: remember not to ask again
      fi
    fi
  fi
fi

echo "$label"
