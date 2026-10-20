"""Pure decision for the plugin-version-bump test (see tests/test_plugin_manifest.py)."""

import json
import subprocess
from pathlib import Path

PLUGIN_MANIFEST = ".claude-plugin/plugin.json"


def needs_bump(changed_paths, base_version, head_version) -> bool:
    """True when something under skills/ changed and the manifest version did not.

    A base with no manifest (``base_version`` None) cannot be "the same version", so no
    bump is demanded.
    """
    if not any(p.startswith("skills/") for p in changed_paths):
        return False
    if base_version is None:
        return False
    return base_version == head_version


def version_at(ref: str, repo_root: Path):
    """The manifest version at a git ref, or None when the file is absent there."""
    r = subprocess.run(["git", "show", f"{ref}:{PLUGIN_MANIFEST}"], cwd=repo_root,
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout).get("version")
