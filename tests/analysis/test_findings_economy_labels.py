"""Every filed finding's economy labels must match the ASN registry.

Caught 2026-09-24 by the project owner: the report showed AS139609 (SISCC,
Solomon Islands' submarine cable operator) with a downstream in Samoa. The
cause was a hand-transcription error in one 2026-09-16 legacy finding,
`NU -> WS (AS150349)`: AS150349 is a Solomon Islands network (APNIC country
SB). A same-day entry, `NU -> SB (AS136996)`, has the mirror-image problem
(APNIC registers AS136996 to VU). This checks the committed export against
`data/asn_registry.json` so a mislabel fails a test instead of reaching the
report.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

EXPORT_PATH = Path("findings_export.jsonl")
REGISTRY_PATH = Path("data/asn_registry.json")

# (side, asn, labelled_cc): deliberate, documented labels that differ from
# the ASN's registry economy.
DOCUMENTED_EXCEPTIONS = {
    # USP's Tonga-campus probe: a valid Tonga vantage point for a Fiji-registered
    # regional organisation (task_plan.md, AS24390 entries).
    ("source", 24390, "TO"),
    # Candidate-generation artifact: source_asn=141695 records which ASN's new
    # probe triggered the candidate, but the traceroutes came from genuine NC
    # probes (task_plan.md, 2026-09-19 AS141695 entry).
    ("source", 141695, "NC"),
}

# Registry disagreements awaiting the owner's confirmation before the finding
# is changed. Remove an entry once it's resolved either way.
PENDING_OWNER_CONFIRMATION = {
    ("target", 136996, "SB"),  # APNIC: VU (Pacific Networks) -- asked 2026-09-24
}


def _asn_economies() -> dict[int, set[str]]:
    if not REGISTRY_PATH.exists():
        pytest.skip("data/asn_registry.json not built (gitignored; run the discovery pipeline)")
    result: dict[int, set[str]] = {}
    for cc, economy in json.loads(REGISTRY_PATH.read_text()).items():
        for asn in economy["asns"]:
            result.setdefault(asn, set()).add(cc)
    return result


def _mislabels() -> set[tuple[str, int, str]]:
    economies = _asn_economies()
    found = set()
    for line in EXPORT_PATH.read_text().splitlines():
        if not line.strip():
            continue
        finding = json.loads(line)
        for side in ("source", "target"):
            asn, cc = finding.get(f"{side}_asn"), finding.get(f"{side}_cc")
            # ASNs outside the registry are external carriers (AU/US/...),
            # out of scope by design -- nothing to compare against.
            if asn is None or asn not in economies:
                continue
            if cc not in economies[asn]:
                found.add((side, asn, cc))
    return found


def test_no_undocumented_economy_mislabels():
    unexpected = _mislabels() - DOCUMENTED_EXCEPTIONS - PENDING_OWNER_CONFIRMATION
    assert not unexpected, f"finding economy label disagrees with asn_registry.json: {sorted(unexpected)}"


def test_pending_entries_are_still_real():
    # Keeps PENDING_OWNER_CONFIRMATION honest: once a pending finding is fixed,
    # this fails until the stale entry is removed.
    assert PENDING_OWNER_CONFIRMATION <= _mislabels()
