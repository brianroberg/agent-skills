"""Doc-parity tests for ``skills/donor-contact-manage/SKILL.md``.

Pins the skill to the contract of brianroberg/sr-assistant#46 (merged as ``b9d1f13``,
contact address/email/phone sub-resources) and to facts already true of the
deployed donor API: the address keys are ``street_address`` / ``postal_code``
(the live ``AddressCreate`` schema has no ``street`` / ``zip`` key, and does not
forbid unknown keys, so the old keys were dropped silently on create), the type
strings are a fixed list with no ``work``, and ``PUT /api/v1/contacts/{id}``
takes no nested arrays at all.
These tests read the SKILL.md only; they make no network calls.
"""

import re

from tests.conftest import SKILLS_DIR

SKILL = SKILLS_DIR / "donor-contact-manage" / "SKILL.md"

# From src/donor_management/schemas/contact_subresources.py at sr-assistant b9d1f13.
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
    vocab = {"address": ADDRESS_TYPES, "phone": PHONE_TYPES, "email": EMAIL_TYPES}
    for kind, value in re.findall(r'"(address|phone|email)_type":\s*"([^"]*)"', text):
        assert value in vocab[kind], f'an example uses "{kind}_type": "{value}", outside the API\'s list'


# ── 2. Address keys are the API's keys ──


def test_address_keys_are_the_api_keys():
    text = _text()
    assert "street_address" in text
    assert "postal_code" in text
    for wrong in ("street", "zip"):
        assert not re.search(rf'"{wrong}"\s*:', text), f'uses the key "{wrong}", which the live schema does not define'
        assert not re.search(rf"`{wrong}`", text), f"documents a `{wrong}` key, which the live schema does not define"


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
            # (?!\S) not \b: a path ending in "}" has no word boundary before a space.
            assert re.search(rf"\b{method}\s+{path}(?!\S)", text), f"missing route {method} {path}"


def test_primary_rule_and_both_409s_are_stated():
    text = _text()
    assert re.search(r"at most one primary", text, re.IGNORECASE), "the one-primary-per-collection rule is missing"
    assert re.search(r"409[^\n]*only", text), "the 409 on demoting the only row is missing"
    assert re.search(r"409[^\n]*(race|concurrent)", text), "the 409 on a lost concurrent promotion is missing"


def test_deploy_dependency_is_stated():
    text = _text()
    assert "sr-assistant#46" in text or "sr-assistant PR #46" in text, "does not name the PR the routes come from"
    assert re.search(r"openapi\.json", text), "gives the reader no way to confirm the routes against the live spec"


# ── 4. Contact PUT is partial and carries no nested arrays; sub-resource writes have no wrapper yet ──


def test_put_is_not_described_as_full_replacement():
    text = _text()
    assert "replaced entirely" not in text, "claims PUT replaces nested arrays; ContactUpdate has no nested arrays"
    assert "donor-update-contact.sh" in text, "does not point at the sanctioned PUT wrapper"


def test_no_raw_curl_for_subresource_writes():
    """Raw curl writes to this API are classifier-blocked; the skill must not instruct one.

    The curl check matches -X / --request in either order relative to the URL, any
    contact id (placeholder or literal), and backslash-continued commands. The second
    assertion pins the sub-resource statement itself -- the PUT section's own
    "wrapper ... allow rule" wording must not be able to satisfy it.
    """
    text = _text().replace("\\\n", " ")
    raw_write = re.compile(
        r"^(?=[^\n]*\bcurl\b)"
        r"(?=[^\n]*(?:-X\s*|--request[\s=]+)(?:POST|PATCH|DELETE)\b)"
        r"(?=[^\n]*/contacts/[^/\s]+/(?:addresses|emails|phones)\b)",
        re.MULTILINE,
    )
    assert not raw_write.search(text), "instructs a raw curl write to a contact sub-resource route"
    assert re.search(r"Sub-resource writes need\s+new wrapper scripts?\s+plus\s+allow rules", text), (
        "does not say that sub-resource writes need a wrapper script and an allow rule that do not exist yet"
    )
