"""OpenAPI spec sync tests — verify our endpoint registry matches live specs.

These tests require network access and are marked with @pytest.mark.network.
Run with: uv run pytest tests/test_openapi_sync.py -m network -v
"""

import re

import pytest

httpx = pytest.importorskip("httpx")

from tests.api_specs import DONOR_ENDPOINTS, EXCLUDED_ENDPOINTS

DONOR_OPENAPI_URL = "https://donor-management.fly.dev/openapi.json"

_PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")


def _extract_endpoints_from_openapi(spec: dict) -> set[str]:
    """Extract 'METHOD /path' strings from an OpenAPI spec."""
    endpoints = set()
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                endpoints.add(f"{method.upper()} {path}")
    return endpoints


def _normalize(endpoint: str) -> str:
    """Collapse path-placeholder NAMES so only the shape is compared.

    The registry writes `GET /api/v1/contacts/{id}` while the live spec writes
    `GET /api/v1/contacts/{contact_id}`. Those are the same endpoint; comparing the
    raw strings reports each of them twice — once as missing, once as extra.
    """
    return _PLACEHOLDER_RE.sub("{id}", endpoint)


def _index_by_shape(endpoints) -> dict[str, str]:
    """Map normalized endpoint -> the original string, for readable failure messages."""
    return {_normalize(e): e for e in endpoints}


@pytest.mark.network
def test_donor_spec_in_sync():
    """Verify our Donor endpoint registry matches the live OpenAPI spec.

    Three separate checks, so a failure says which of three different problems it is:
    unregistered new endpoints, registry drift, or stale exclusions.
    """
    resp = httpx.get(DONOR_OPENAPI_URL, timeout=15)
    resp.raise_for_status()
    spec = resp.json()

    live = _index_by_shape(_extract_endpoints_from_openapi(spec))
    registered = _index_by_shape(DONOR_ENDPOINTS)
    excluded = _index_by_shape(EXCLUDED_ENDPOINTS)

    # 1. Live endpoints that are neither registered nor deliberately excluded.
    #    Fix by adding to DONOR_ENDPOINTS, or to EXCLUDED_ENDPOINTS with a reason.
    unaccounted = sorted(live[k] for k in live.keys() - registered.keys() - excluded.keys())
    assert not unaccounted, (
        "Donor API has endpoints in neither DONOR_ENDPOINTS nor EXCLUDED_ENDPOINTS:\n"
        + "\n".join(f"  - {e}" for e in unaccounted)
    )

    # 2. Registry entries the live spec no longer has — drift, i.e. skills may document
    #    an endpoint that has been removed or renamed upstream.
    drifted = sorted(registered[k] for k in registered.keys() - live.keys())
    assert not drifted, (
        "DONOR_ENDPOINTS lists endpoints the live spec does not have:\n"
        + "\n".join(f"  - {e}" for e in drifted)
    )

    # 3. Exclusions for endpoints that no longer exist — dead entries that would hide a
    #    later re-appearance of the same path.
    stale_exclusions = sorted(excluded[k] for k in excluded.keys() - live.keys())
    assert not stale_exclusions, (
        "EXCLUDED_ENDPOINTS excludes endpoints the live spec no longer has:\n"
        + "\n".join(f"  - {e}" for e in stale_exclusions)
    )
