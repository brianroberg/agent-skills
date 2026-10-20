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


# ── a skills change on this branch must bump the plugin version ──
#
# Pure decision in tests/plugin_bump.py; the git-backed test below feeds it the branch's
# diff against a base: PLUGIN_BUMP_BASE (a ref or sha; CI sets it to the PR base), else
# origin/main (fetched if absent), else the test is skipped with a reason, never a silent pass.

import os
import subprocess

import pytest

from tests.plugin_bump import needs_bump, version_at


def test_needs_bump_only_when_skills_changed_and_version_did_not():
    assert needs_bump(["skills/review-loop/SKILL.md"], base_version="0.3.0", head_version="0.3.0")
    assert not needs_bump(["skills/review-loop/SKILL.md"], base_version="0.3.0", head_version="0.3.1")
    assert not needs_bump(["README.md", "docs/x.md"], base_version="0.3.0", head_version="0.3.0")
    assert needs_bump(["skills/new-skill/SKILL.md"], base_version=None, head_version="0.3.0") is False, (
        "no plugin.json at the base means the version is new by definition"
    )
    assert not needs_bump([], base_version="0.3.0", head_version="0.3.0")


def _git(*args):
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False)


def _base_ref():
    """PLUGIN_BUMP_BASE, else a fresh fetch of origin/main, else the clone's origin/main
    (which may be stale), else skip. CI sets PLUGIN_BUMP_BASE to the PR base sha."""
    if _git("rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        _git("fetch", "--quiet", "--deepen=200", "origin")  # CI checkouts are depth 1; merge-base needs history
    env = os.environ.get("PLUGIN_BUMP_BASE")
    if env:
        if _git("rev-parse", "--verify", "-q", f"{env}^{{commit}}").returncode != 0:
            pytest.skip(f"PLUGIN_BUMP_BASE={env} is not a commit in this clone")
        return env
    fetched = _git("fetch", "--quiet", "--depth=200", "origin", "main")
    if fetched.returncode == 0 and _git("rev-parse", "--verify", "-q", "FETCH_HEAD").returncode == 0:
        return "FETCH_HEAD"
    if _git("rev-parse", "--verify", "-q", "origin/main").returncode == 0:
        return "origin/main"  # could not fetch; this is the clone-time main and may be stale
    pytest.skip("no base to compare against: set PLUGIN_BUMP_BASE or make origin/main fetchable")


def test_branch_that_changes_skills_bumps_plugin_version():
    base = _base_ref()
    mb = _git("merge-base", base, "HEAD")
    if mb.returncode != 0:
        pytest.skip(f"no merge-base between {base} and HEAD (shallow clone, or the base is not in this clone)")
    changed = _git("diff", "--name-only", mb.stdout.strip(), "HEAD", "--").stdout.split()
    base_version = version_at(mb.stdout.strip(), REPO_ROOT)
    head_version = json.loads(PLUGIN.read_text())["version"]
    assert not needs_bump(changed, base_version=base_version, head_version=head_version), (
        f"skills/ changed on this branch but .claude-plugin/plugin.json version is still "
        f"{head_version} (same as the base {base}); bump it in plugin.json and marketplace.json"
    )
