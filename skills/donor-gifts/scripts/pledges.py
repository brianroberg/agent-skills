#!/usr/bin/env python3
"""Print the pledges recorded for one donor contact.

    python3 skills/donor-gifts/scripts/pledges.py "Pat Example"
    python3 skills/donor-gifts/scripts/pledges.py --contact-id 1001
    python3 skills/donor-gifts/scripts/pledges.py "Example"         # several matches: lists them, exit 2

Read-only. Three requests at most, one at a time: the contact search (skipped with
--contact-id), the contact's pledges (active and ended), and the live frequency table.
The key comes from DONOR_API_KEY and is never printed.

Exit codes: 0 printed · 2 bad input, no key, no match or several matches (the list is
printed so the caller can pass --contact-id) · 3 the API could not be reached or
answered with an error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = os.environ.get("DONOR_API_URL", "https://donor-management.fly.dev")
TIMEOUT = 30

# GET /api/v1/pledges/frequencies as of 2026-10-19 (ids carried over from TntConnect; stable
# since the February 2026 migration). The live table is read first; this is the fallback.
FREQUENCIES = {
    1: "Monthly",
    2: "Quarterly",
    3: "Semi-Annual",
    4: "Annual",
    5: "Bi-Monthly",
    6: "Quad-Monthly",
    7: "Biennial",
    8: "Weekly",
    9: "Fortnightly",
}


# ---------------------------------------------------------------- pure

def rows(payload) -> list:
    """The list inside a response: a bare list, or {items|contacts|pledges|results: [...]}."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "contacts", "pledges", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def _label(c: dict) -> str:
    return (c.get("file_as") or c.get("org_name")
            or " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x) or f"contact {c.get('id')}")


def _norm(s: str | None) -> str:
    return " ".join((s or "").lower().replace(",", " ").split())


def pick_contact(contacts: list, query: str) -> dict | None:
    """The one contact the query names, else None (caller lists the candidates).

    One search hit is taken as is. Among several, a hit whose file_as, "First Last" or
    "Last First" equals the query (case and comma insensitive) wins.
    """
    if len(contacts) == 1:
        return contacts[0]
    q = _norm(query)
    if not q:
        return None
    exact = []
    for c in contacts:
        first, last = c.get("first_name") or "", c.get("last_name") or ""
        forms = {_norm(c.get("file_as")), _norm(f"{first} {last}"), _norm(f"{last} {first}"), _norm(c.get("org_name"))}
        if q in forms:
            exact.append(c)
    return exact[0] if len(exact) == 1 else None


SEARCH_LIMIT = 100  # the API's default page; a search that fills it may be cut off


def describe_contacts(contacts: list, limit: int = SEARCH_LIMIT) -> str:
    if not contacts:
        return "no contact matched"
    head = "several contacts matched; rerun with --contact-id <id>:"
    if len(contacts) >= limit:
        head = f"several contacts matched (first {limit}; narrow the name); rerun with --contact-id <id>:"
    lines = [head]
    for c in contacts:
        flag = " (deceased)" if c.get("deceased") else ""
        lines.append(f"  {c.get('id')}  {_label(c)}{flag}")
    return "\n".join(lines)


def frequency_name(fid, live: list | None) -> str:
    for f in live or []:
        if f.get("id") == fid and f.get("name"):
            return f["name"]
    return FREQUENCIES.get(fid, f"frequency {fid}")


def money(v) -> str:
    if v is None or v == "":
        return "?"
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)


def _pledge_line(p: dict, freqs: list | None, today: dt.date) -> str:
    head = f"  #{p.get('id')}  {money(p.get('amount'))} {frequency_name(p.get('frequency_id'), freqs)}"
    if p.get("start_date"):
        head += f" since {p['start_date']}"
    end = p.get("end_date")
    ended = p.get("is_active") is False or (bool(end) and end <= today.isoformat())
    notes = []
    st = p.get("status") or {}
    if ended:
        notes.append(f"ended {end or '(date not recorded)'}")
    else:
        if st.get("state"):
            s = st["state"]
            if st.get("good_until"):
                s += f", good until {st['good_until']}"
            notes.append(s)
        if end:
            notes.append(f"through {end}")  # a fixed-term pledge still running
    if p.get("awaiting_first_gift_since"):
        notes.append(f"awaiting first gift since {p['awaiting_first_gift_since']}")
    if st.get("last_gift_date"):
        notes.append(f"last gift {money(st.get('last_gift_amount'))} on {st['last_gift_date']}")
    return head + (" — " + "; ".join(notes) if notes else "")


def format_report(contact: dict, pledges: list, freqs: list | None, today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    who = f"{_label(contact)} (contact {contact.get('id')})"
    if contact.get("deceased"):
        who += " (deceased)"
    if not pledges:
        return f"{who} — no pledges on record"
    n = len(pledges)
    lines = [f"{who} — {n} pledge{'s' if n != 1 else ''}"]
    lines += [_pledge_line(p, freqs, today) for p in sorted(pledges, key=lambda p: (p.get("is_active") is False, p.get("start_date") or ""))]
    return "\n".join(lines)


# ---------------------------------------------------------------- I/O

class ApiError(Exception):
    pass


def fetch_json(path: str, params: dict | None, api_key: str):
    url = BASE_URL.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-API-Key": api_key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as ex:
        raise ApiError(f"HTTP {ex.code} on GET {path}") from ex
    except (urllib.error.URLError, TimeoutError, ValueError) as ex:
        raise ApiError(f"GET {path} failed: {ex}") from ex


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Print the pledges recorded for one donor contact.")
    ap.add_argument("name", nargs="?", help="donor name to search for")
    ap.add_argument("--contact-id", type=int, help="skip the search and read this contact's pledges")
    ap.add_argument("--json", action="store_true", help="print the raw pledge rows instead of the report")
    args = ap.parse_args(argv)
    if not args.name and args.contact_id is None:
        ap.error("give a name or --contact-id")

    api_key = os.environ.get("DONOR_API_KEY", "")
    if not api_key:
        print("DONOR_API_KEY is not set", file=sys.stderr)
        return 2

    try:
        if args.contact_id is not None:
            contact = fetch_json(f"/api/v1/contacts/{args.contact_id}", None, api_key)
        else:
            found = rows(fetch_json("/api/v1/contacts", {"search": args.name, "limit": SEARCH_LIMIT}, api_key))
            contact = pick_contact(found, args.name)
            if contact is None:
                print(describe_contacts(found))
                return 2
        pledges = rows(fetch_json("/api/v1/pledges", {"contact_id": contact["id"], "active_only": "false"}, api_key))
        try:
            freqs = rows(fetch_json("/api/v1/pledges/frequencies", None, api_key))
        except ApiError:
            freqs = None  # the built-in table covers the known ids
    except ApiError as ex:
        print(f"donor API: {ex}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(pledges, indent=2))
    else:
        print(format_report(contact, pledges, freqs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
