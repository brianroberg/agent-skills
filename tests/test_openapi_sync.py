"""OpenAPI spec sync tests — verify our endpoint registry matches live specs.

These tests require network access and are marked with @pytest.mark.network.
Run with: uv run pytest tests/test_openapi_sync.py -m network -v
"""

import pytest

httpx = pytest.importorskip("httpx")

from tests.api_specs import DONOR_ENDPOINTS, EXCLUDED_ENDPOINTS

DONOR_OPENAPI_URL = "https://donor-management.fly.dev/openapi.json"


def _extract_endpoints_from_openapi(spec: dict) -> set[str]:
    """Extract 'METHOD /path' strings from an OpenAPI spec."""
    endpoints = set()
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                endpoints.add(f"{method.upper()} {path}")
    return endpoints


@pytest.mark.network
def test_donor_spec_in_sync():
    """Verify our Donor endpoint registry matches the live OpenAPI spec."""
    resp = httpx.get(DONOR_OPENAPI_URL, timeout=15)
    resp.raise_for_status()
    spec = resp.json()

    live_endpoints = _extract_endpoints_from_openapi(spec)
    registered = set(DONOR_ENDPOINTS.keys())
    excluded = {e for e in EXCLUDED_ENDPOINTS if e.startswith("GET /api/") or e.startswith("POST /api/") or e.startswith("DELETE /api/")}

    # Endpoints in live spec but not in our registry (and not excluded)
    missing_from_registry = live_endpoints - registered - excluded
    assert not missing_from_registry, (
        f"Donor API has endpoints not in our registry:\n"
        + "\n".join(f"  - {e}" for e in sorted(missing_from_registry))
    )

    # Endpoints in our registry but not in live spec
    extra_in_registry = registered - live_endpoints
    assert not extra_in_registry, (
        f"Our registry has Donor endpoints not in the live spec:\n"
        + "\n".join(f"  - {e}" for e in sorted(extra_in_registry))
    )
