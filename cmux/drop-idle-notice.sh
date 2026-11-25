#!/bin/bash
# cmux notification hook: drops Claude Code's idle notice ("Claude is waiting for your
# input", sent about a minute after a turn ends) and leaves every other notification,
# including Claude Code's permission prompts, to cmux's default behaviour.
#
# Known trade-off (Brian, 2026-11-25, accepted for now): the idle notice is also the
# only alert when an agent ends its turn with a question written as ordinary text,
# since Claude Code cannot tell that from a finished task. Permission prompts and
# question dialogs send a different notice and still alert. To get the idle notice
# back, set "enabled": false on the drop-claude-idle-notice hook in cmux.json and run
# `cmux reload-config`.
#
# cmux pipes the notification policy JSON on stdin. Printing a patch changes the
# policy; printing nothing keeps the default.
PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"

jq -c 'select(.notification.title == "Claude Code"
              and .notification.body == "Claude is waiting for your input")
       | {effects: {record: false, markUnread: false, reorderWorkspace: false,
                    desktop: false, sound: false, command: false, paneFlash: false}}' 2>/dev/null
exit 0
