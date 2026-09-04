"""API coverage tests — verify every endpoint is referenced in at least one skill."""

import re
from pathlib import Path

import pytest

from tests.api_specs import DONOR_ENDPOINTS, EXCLUDED_ENDPOINTS
from tests.conftest import SKILLS_DIR

ALL_ENDPOINTS = dict(DONOR_ENDPOINTS)
COVERED_ENDPOINTS = [e for e in ALL_ENDPOINTS if e not in EXCLUDED_ENDPOINTS]


def _all_skill_contents(skills_dir: Path) -> str:
    """Concatenate all SKILL.md files into one searchable string."""
    parts = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        parts.append(skill_file.read_text())
    return "\n".join(parts)


def _endpoint_referenced(endpoint: str, content: str) -> bool:
    """Check if an endpoint pattern appears in the skill content.

    Matches patterns like:
    - "GET /inbox" or "POST /inbox/{id}/process"
    - curl command URLs containing the path
    - Plain path references like "/inbox" or "/next-actions"
    """
    method, path = endpoint.split(" ", 1)

    # Normalize path for regex: replace {id} with flexible pattern
    path_pattern = re.escape(path).replace(r"\{id\}", r"(\{id\}|\{[a-z_]+\}|[0-9]+|<[a-z_]+>|\$[A-Z_]+)")

    # Match "METHOD /path" (with or without full URL prefix)
    if re.search(rf"\b{method}\s+[^\s]*{path_pattern}", content):
        return True

    # Match plain path reference (e.g., "/inbox" in a URL or reference)
    if re.search(path_pattern, content):
        return True

    return False


@pytest.mark.parametrize("endpoint", COVERED_ENDPOINTS, ids=lambda e: e)
def test_endpoint_has_skill_coverage(endpoint, skills_dir):
    """Every API endpoint must be referenced in at least one skill."""
    content = _all_skill_contents(skills_dir)
    assert _endpoint_referenced(endpoint, content), (
        f"Endpoint {endpoint} is not referenced in any skill. "
        f"Description: {ALL_ENDPOINTS[endpoint]['description']}"
    )
