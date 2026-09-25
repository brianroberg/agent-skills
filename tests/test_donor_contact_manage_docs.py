"""Doc-parity tests for ``skills/donor-contact-manage/SKILL.md``.

Pins the skill to the contract of brianroberg/sr-assistant#46 (merged as ``b9d1f13``,
contact address/email/phone sub-resources) and to facts already true of the
deployed donor API: the address keys are ``street_address`` / ``postal_code``
(the live ``AddressCreate`` schema has no ``street`` / ``zip`` key, and does not
forbid unknown keys, so the old keys were dropped silently on create), the type
strings are a fixed list with no ``work``, and ``PUT /api/v1/contacts/{id}``
takes no nested arrays at all. Also pins what a contact delete destroys, the group
body keys and the ``confidential_notes`` scope to sr-assistant ``b9d1f13``, and the
write/permission rule to the live test of 2026-09-24 (agent-skills PR #15).
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


def _section(text: str, heading: str) -> str:
    """The body under `heading`, up to the next heading of the same or a higher level."""
    m = re.search(rf"^(#+) {re.escape(heading)}\n", text, re.MULTILINE)
    assert m, f"no '{heading}' section"
    end = re.compile(rf"^#{{1,{len(m.group(1))}}} ", re.MULTILINE).search(text, m.end())
    body = text[m.end() : end.start() if end else len(text)]
    assert body.strip(), f"the '{heading}' section is empty"
    return body


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


# ── 4. Contact PUT is partial and keeps its wrapper; other writes are plain requests ──


def test_put_is_not_described_as_full_replacement():
    text = _text()
    assert "replaced entirely" not in text, "claims PUT replaces nested arrays; ContactUpdate has no nested arrays"
    assert "donor-update-contact.sh" in text, "does not point at the sanctioned PUT wrapper"


def test_no_blanket_write_block_claim():
    """On 2026-09-24 the assistant sent contact POST and DELETE, address POST / PATCH /
    DELETE, group POST / PUT / DELETE and member add / remove as raw curl, each named by
    Brian, and none was refused or prompted. Only the contact PUT keeps its wrapper
    (backup, diff, and a recorded refusal); the skill now says "permission check" throughout.
    """
    text = _text()
    assert not re.search(r"(?i)classifier", text), "describes donor writes as classifier-blocked; the 2026-09-24 test sent them"
    assert not re.search(r"(?i)wrapper scripts?\s+(?:plus|and)\s+(?:an?\s+)?allow rules?", text), (
        "says sub-resource writes need wrapper scripts; the address writes went through as plain requests"
    )
    assert re.search(r"(?i)plain requests?", _section(text, "Addresses, emails and phones (sub-resource routes)")), (
        "the sub-resource section does not say its writes are plain requests"
    )


def test_write_rule_is_stated():
    section = " ".join(_section(_text(), "Writes and the permission check").split())
    assert "Send the write when Brian asked for that specific change" in section, "the write rule is missing"
    assert re.search(
        r"If the permission check refuses a write, do not retry it another way\**\s*\([^)]*\)\. "
        r"Write out the exact change\W+route, ids and body\W+and hand it to Brian",
        section,
    ), "does not say to write out a refused change and hand it to Brian, rather than work around it"


# ── 5. Contact delete, group bodies and confidential_notes match sr-assistant b9d1f13 ──

# GroupCreate / GroupUpdate in src/donor_management/schemas/group.py. They do not forbid
# extra keys, so an unknown key such as "description" is dropped with a 2xx, not a 422.
GROUP_KEYS = {"name", "parent_group_id", "contact_ids"}
GROUP_UPDATE_KEYS = {"name", "parent_group_id"}

# models/contact.py: cascade="all, delete-orphan" on each of these (external_donors is the DonorHub link).
DELETED_WITH_CONTACT = ("gifts", "pledges", "addresses", "emails", "phones", "DonorHub")


def test_contact_delete_names_what_it_destroys():
    section = _section(_text(), "Delete a Contact")
    for lost in DELETED_WITH_CONTACT:
        assert lost in section, f"does not say that deleting a contact deletes its {lost}"
    survives = re.compile(r"(?i)\b(?:kept|keeps|disassociat\w*|unlink\w*|not (?:delete|remove)\w*|lose their link)")
    for sentence in re.split(r"(?<=[.!?])\s+", " ".join(section.split())):
        if survives.search(sentence):
            for lost in DELETED_WITH_CONTACT:
                assert lost not in sentence, f"says a contact's {lost} survive a delete: {sentence!r}"


def test_contact_delete_states_the_synced_gift_failure():
    """At b9d1f13, gifts.external_donor_id has no ORM relationship, so deleting a contact with
    a sync-imported gift deletes external_donors first and fails the foreign key: a 500, and
    nothing is deleted (reproduced against a copy of the server, 2026-09-24)."""
    section = " ".join(_section(_text(), "Delete a Contact").split())
    assert re.search(r"(?i)cannot be deleted", section) and "500" in section, (
        "does not say a contact with DonorHub-imported gifts cannot be deleted"
    )


def test_group_bodies_use_only_group_schema_keys():
    text = _text()
    keys = set(re.findall(r'"(\w+)"\s*:', _section(text, "Group Operations")))
    assert keys <= GROUP_KEYS, f"group bodies use keys the group schemas do not define: {sorted(keys - GROUP_KEYS)}"
    update_keys = set(re.findall(r'"(\w+)"\s*:', _section(text, "Update a Group")))
    assert update_keys <= GROUP_UPDATE_KEYS, f"the group PUT body uses keys GroupUpdate drops: {sorted(update_keys - GROUP_UPDATE_KEYS)}"


def test_confidential_notes_is_scoped_to_history_and_tasks():
    """Only models/history.py and models/task.py define confidential_notes; contacts have none."""
    text = _text()
    assert not re.search(r"confidential_notes`?\s+on\s+contacts", text), "puts confidential_notes on contacts"
    bullets = [
        " ".join(item.split())
        for item in re.split(r"\n(?=- )", _section(text, "Important Notes"))
        if "confidential_notes" in item
    ]
    assert len(bullets) == 1, "Important Notes should have exactly one confidential_notes bullet"
    assert re.search(r"(?i)\bhistory", bullets[0]) and re.search(r"(?i)\btasks?\b", bullets[0]), (
        "does not say confidential_notes is on history entries and tasks"
    )
    rest = re.sub(r"(?i)\(?contacts have (?:none|no such field)\)?|not (?:on|a field of) (?:a )?contacts?", "", bullets[0])
    assert not re.search(r"(?i)\bcontact", rest), "puts confidential_notes on contacts, which have no such field"
