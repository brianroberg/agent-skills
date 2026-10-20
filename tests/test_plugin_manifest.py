"""The two plugin manifests must agree, or a merged skill change is invisible to installs.

Claude Code decides whether an installed plugin is out of date by the manifest version
first (``.claude-plugin/plugin.json`` ``version``), falling back to the commit only when
there is none. The marketplace entry carries its own copy. If the two drift, or neither is
bumped when ``skills/`` changes, a ``/plugin update`` finds nothing to do. Pinned here so a
PR that changes skills without bumping both fails the suite (see REVIEW.md).
"""

import json

from tests.conftest import REPO_ROOT

PLUGIN = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKET = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _entry():
    market = json.loads(MARKET.read_text())
    entries = [p for p in market["plugins"] if p["name"] == "agent-skills"]
    assert len(entries) == 1, "marketplace.json must list the agent-skills plugin exactly once"
    return entries[0]


def test_marketplace_version_matches_plugin_version():
    plugin = json.loads(PLUGIN.read_text())
    assert _entry()["version"] == plugin["version"], (
        "bump both .claude-plugin/plugin.json and marketplace.json together"
    )


def test_marketplace_description_matches_plugin_description():
    plugin = json.loads(PLUGIN.read_text())
    assert _entry()["description"] == plugin["description"]
