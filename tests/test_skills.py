"""Structural validation tests for agent skills."""

import re
from pathlib import Path

import pytest

from tests.conftest import SKILLS_DIR, parse_frontmatter

ALL_SKILL_DIRS = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
ALL_SKILLS = sorted(SKILLS_DIR.glob("*/SKILL.md"))


# ── 1. Every directory under skills/ has a SKILL.md file ──


def test_every_skill_dir_has_skill_md():
    missing = [d.name for d in ALL_SKILL_DIRS if not (d / "SKILL.md").exists()]
    assert not missing, f"Skill directories missing SKILL.md: {missing}"


# ── 2. Every SKILL.md has valid YAML frontmatter with required fields ──


@pytest.mark.parametrize("skill_path", ALL_SKILLS, ids=lambda p: p.parent.name)
def test_frontmatter_has_required_fields(skill_path: Path):
    """Must have: name, description. Optional: allowed-tools."""
    fm = parse_frontmatter(skill_path)
    assert fm, f"{skill_path.parent.name}: No YAML frontmatter found"
    assert "name" in fm, f"{skill_path.parent.name}: Missing 'name' in frontmatter"
    assert "description" in fm, f"{skill_path.parent.name}: Missing 'description' in frontmatter"
    assert isinstance(fm["name"], str) and fm["name"].strip(), "name must be a non-empty string"
    assert isinstance(fm["description"], str) and fm["description"].strip(), "description must be a non-empty string"


# ── 3. Every SKILL.md has at least one curl command or API reference ──


@pytest.mark.parametrize("skill_path", ALL_SKILLS, ids=lambda p: p.parent.name)
def test_skill_has_api_reference(skill_path: Path):
    """Skills that interact with APIs must document their endpoints."""
    content = skill_path.read_text()
    has_curl = "curl" in content
    has_http_method = bool(re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+[/\"]", content))
    has_url = bool(re.search(r"https?://", content))
    has_env_url = bool(re.search(r"\$\w+_URL", content))
    assert any([has_curl, has_http_method, has_url, has_env_url]), (
        f"{skill_path.parent.name}: No API reference found (curl, HTTP method, URL, or env var)"
    )


# ── 4. No skill references a hardcoded API key ──


CREDENTIAL_PATTERNS = [
    r"X-API-Key:\s*[a-zA-Z0-9_-]{20,}",  # literal API key in header
    r"api[_-]?key\s*[=:]\s*['\"][a-zA-Z0-9_-]{20,}['\"]",  # key assignment
    r"Bearer\s+[a-zA-Z0-9_.-]{20,}",  # literal bearer token
]


@pytest.mark.parametrize("skill_path", ALL_SKILLS, ids=lambda p: p.parent.name)
def test_no_hardcoded_credentials(skill_path: Path):
    content = skill_path.read_text()
    for pattern in CREDENTIAL_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        assert not matches, (
            f"{skill_path.parent.name}: Possible hardcoded credential: {matches[0][:40]}..."
        )


# ── 5. Every skill directory listed in skills/ is documented in README.md ──


@pytest.mark.parametrize("skill_path", ALL_SKILLS, ids=lambda p: p.parent.name)
def test_skill_documented_in_readme(skill_path: Path, readme_content: str):
    skill_name = skill_path.parent.name
    assert skill_name in readme_content, (
        f"Skill '{skill_name}' is not mentioned in README.md"
    )


# ── 6. Skill names are consistent (dir name matches frontmatter name, or is a known alias) ──


KNOWN_ALIASES = {
    # dir name -> allowed frontmatter name(s)
    "briefing-morning": {"morning-briefing", "briefing-morning"},
}


@pytest.mark.parametrize("skill_path", ALL_SKILLS, ids=lambda p: p.parent.name)
def test_skill_name_consistency(skill_path: Path):
    dir_name = skill_path.parent.name
    fm = parse_frontmatter(skill_path)
    if not fm or "name" not in fm:
        pytest.skip("No frontmatter name to check")
    fm_name = fm["name"]
    allowed = KNOWN_ALIASES.get(dir_name, {dir_name})
    assert fm_name in allowed, (
        f"Directory '{dir_name}' has frontmatter name '{fm_name}', "
        f"expected one of: {allowed}"
    )
