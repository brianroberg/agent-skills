from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


@pytest.fixture
def skills_dir() -> Path:
    return SKILLS_DIR


@pytest.fixture
def all_skill_paths() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


@pytest.fixture
def readme_content() -> str:
    return (REPO_ROOT / "README.md").read_text()


def parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a SKILL.md file."""
    text = path.read_text()
    if not text.startswith("---"):
        return {}
    end = text.index("---", 3)
    return yaml.safe_load(text[3:end]) or {}


def section(text: str, heading: str) -> str:
    """The body under `heading`, up to the next heading of the same or a higher level.

    Shared by the doc-parity tests; the older test files still carry a private copy.
    """
    import re

    m = re.search(rf"^(#+) {re.escape(heading)}\n", text, re.MULTILINE)
    assert m, f"no '{heading}' section"
    end = re.compile(rf"^#{{1,{len(m.group(1))}}} ", re.MULTILINE).search(text, m.end())
    body = text[m.end() : end.start() if end else len(text)]
    assert body.strip(), f"the '{heading}' section is empty"
    return body
