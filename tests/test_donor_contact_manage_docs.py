"""Doc-parity tests for ``skills/donor-contact-manage/SKILL.md``.

Pins the skill to the contract of brianroberg/sr-assistant#46 (head ``162e128``,
contact address/email/phone sub-resources) and to facts already true of the
deployed donor API: the address keys are ``street_address`` / ``postal_code``
(never ``street`` / ``zip``), the type strings are a fixed list with no
``work``, and ``PUT /api/v1/contacts/{id}`` takes no nested arrays at all.
These tests read the SKILL.md only; they make no network calls.
"""

import re

from tests.conftest import SKILLS_DIR

SKILL = SKILLS_DIR / "donor-contact-manage" / "SKILL.md"

# From src/donor_management/schemas/contact_subresources.py at sr-assistant 162e128.
ADDRESS_TYPES = {"home", "business", "other", "spouse_business"}
PHONE_TYPES = {"home", "mobile", "business", "spouse_mobile"}
EMAIL_TYPES = {"personal", "business", "spouse"}

COLLECTIONS = {"addresses": "address_id", "emails": "email_id", "phones": "phone_id"}


def _text() -> str:
    return SKILL.read_text()


def _documented_values(text: str, field: str) -> set[str]:
    """The backticked values on the line that defines `field` as 'one of ...'."""
    m = re.search(rf"`{field}`[^\n]*?one of ([^\n]+)", text)
    assert m, f"no line defines `{field}` as 'one of ...'"
    return set(re.findall(r"`([a-z_]+)`", m.group(1)))


# ── 1. The three type vocabularies are exactly sr-assistant#46's ──


def test_address_type_vocabulary():
    assert _documented_values(_text(), "address_type") == ADDRESS_TYPES


def test_phone_type_vocabulary():
    assert _documented_values(_text(), "phone_type") == PHONE_TYPES


def test_email_type_vocabulary():
    assert _documented_values(_text(), "email_type") == EMAIL_TYPES


def test_no_undefined_type_value_is_offered():
    text = _text()
    assert not re.search(r"`work`", text), "documents a `work` type; the API defines none"
    assert not re.search(r'"(address|phone|email)_type":\s*"(work)"', text)


# ── 2. Address keys are the API's keys ──


def test_address_keys_are_the_api_keys():
    text = _text()
    assert "street_address" in text
    assert "postal_code" in text
    for wrong in ("street", "zip"):
        assert not re.search(rf'"{wrong}"\s*:', text), f'uses the key "{wrong}", which the API has never accepted'
        assert not re.search(rf"`{wrong}`", text), f"documents a `{wrong}` key, which the API has never accepted"


# ── 3. The #46 sub-resource routes are documented with #46's path parameters ──


def test_subresource_routes_documented():
    text = _text()
    for coll, row in COLLECTIONS.items():
        base = rf"/api/v1/contacts/\{{contact_id\}}/{coll}"
        for method, path in (
            ("GET", base),
            ("POST", base),
            ("PATCH", rf"{base}/\{{{row}\}}"),
            ("DELETE", rf"{base}/\{{{row}\}}"),
        ):
            assert re.search(rf"\b{method}\s+{path}\b", text), f"missing route {method} {path}"


def test_primary_rule_and_both_409s_are_stated():
    text = _text()
    assert re.search(r"at most one primary", text, re.IGNORECASE), "the one-primary-per-collection rule is missing"
    assert re.search(r"409[^\n]*only", text), "the 409 on demoting the only row is missing"
    assert re.search(r"409[^\n]*(race|concurrent)", text), "the 409 on a lost concurrent promotion is missing"


def test_deploy_dependency_is_stated():
    text = _text()
    assert "sr-assistant#46" in text or "sr-assistant PR #46" in text, "does not name the PR the routes come from"
    assert re.search(r"openapi\.json", text), "gives the reader no way to check whether the routes are deployed"


# ── 4. Contact PUT is partial and carries no nested arrays; sub-resource writes have no wrapper yet ──


def test_put_is_not_described_as_full_replacement():
    text = _text()
    assert "replaced entirely" not in text, "claims PUT replaces nested arrays; ContactUpdate has no nested arrays"
    assert "donor-update-contact.sh" in text, "does not point at the sanctioned PUT wrapper"


def test_no_raw_curl_for_subresource_writes():
    """Raw curl writes to this API are classifier-blocked; the skill must not instruct one.

    The curl assertion is green from the start (the current skill uses no curl) -- a
    pin, not a red/green step; the wrapper/allow-rule assertion is the red half.
    """
    text = _text()
    raw_write = re.compile(
        r"curl[^\n]*-X\s+(POST|PATCH|DELETE)[^\n]*/contacts/\{contact_id\}/(addresses|emails|phones)"
    )
    assert not raw_write.search(text)
    assert re.search(r"wrapper", text) and re.search(r"allow rule", text), (
        "does not say that sub-resource writes need a wrapper script and an allow rule that do not exist yet"
    )
