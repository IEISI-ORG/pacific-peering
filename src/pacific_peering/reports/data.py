"""Shared report data assembly (Phase 1f).

Both the ASCII and HTML reports render from the exact same assembled
data structure — per task_plan.md's Phase 1f spec ("generate ASCII
report and HTML report from the same underlying analysis output"), so
the two formats can never drift apart on what they claim to show.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from pacific_peering.analysis.candidate_peering import CANDIDATE_PEERING
from pacific_peering.analysis.confirmed_detours import CONFIRMED_DETOURS
from pacific_peering.analysis.confirmed_local_transit import CONFIRMED_LOCAL_TRANSIT
from pacific_peering.analysis.fishbowl import DEFAULT_SUMMARY_PATH
from pacific_peering.analysis.ixp_lan_registry import DEFAULT_REGISTRY_PATH
from pacific_peering.analysis.traceroute_topology import DEFAULT_TRIANGULATION_DIR
from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH

# Shared across every report format so a reader who lands on any one of
# them (this project's own audience, or an external one — e.g. RIPE
# NCC, if this report is used to make the case for new Atlas probes in
# the region) gets the same explanation of this project's central
# methodological framing, not a different one per format.
FISHBOWL_EXPLANATION = (
    "What is \"the fish bowl\"? RIS (BGP route-collector) data and PeeringDB "
    "membership records are an outside-looking-in view: they show which "
    "routes get announced and which exchanges/facilities a network claims "
    "to join, but not how traffic actually moves once it's inside a "
    "network -- we can see the bowl from outside, not get in it. Active "
    "RIPE Atlas traceroutes are the only way this project can partially "
    "see inside: a real packet, actually forwarded hop by hop. This project's "
    "rule follows from that limit: no topology claim is accepted on one "
    "source alone -- a finding only counts once RIS and an Atlas traceroute "
    "independently agree (an IRR AS-SET declaration or a PeeringDB IXP "
    "membership can support a finding, but never substitute for that "
    "agreement). \"In-fishbowl\" / \"out-of-fishbowl\" describes whether an "
    "exchange or ASN sits inside this project's study region (Melanesia, "
    "Polynesia, Micronesia, and Guam) or outside it (e.g. Sydney, Los "
    "Angeles, Tokyo) -- an out-of-fishbowl hop on a path between two "
    "in-region economies is this project's definition of a sub-optimal route."
)


@dataclass(frozen=True)
class EconomySummary:
    """One economy's counts, as shown in the economies table of both report formats."""

    cc: str
    name: str
    subregion: str
    asn_count: int
    asns_with_neighbors: int
    asns_with_ixp: int
    asns_with_facility: int


@dataclass(frozen=True)
class TransitSupplier:
    """One carrier confirmed (RIS + Atlas) as the immediate upstream on at least

    one traceroute-verified Pacific corridor. Two deliberately distinct
    kinds of economy, per the project owner's own correction (SISCC --
    Solomon Islands' own submarine-cable operator -- was reading as a
    7-economy concentration risk when it's really a single-island carrier
    most of those economies had no relationship to at all):

    - `dependent_economies`: economies whose own reachability this carrier
      was confirmed as the immediate upstream for (`target_cc` on a
      `ConfirmedDetour`, `customer_cc` on a `ConfirmedLocalTransit`) --
      the real "who actually relies on this carrier" set.
    - `vantage_only_economies`: economies that only ever appeared as the
      *tested vantage point* for a measurement reaching a dependent
      economy elsewhere (`source_cc` on a `ConfirmedDetour`), with no
      confirmed dependency of their own on this carrier. Excludes any
      economy already counted as dependent, so the two sets never
      overlap.

    `corroboration_count` is the highest "Nth independent corroboration/
    confirmation" ordinal mined from the underlying notes -- for
    `ConfirmedDetour` entries this always equals the number of source
    economies exactly (one entry per source economy, by convention), but
    for `ConfirmedLocalTransit` entries -- which extend one entry's note
    per new corroborating source economy rather than adding new entries --
    it can run meaningfully higher than either economy count alone shows,
    because most corroborating vantage points aren't the provider or
    customer themselves.
    """

    asn: int
    name: str
    dependent_economies: tuple[str, ...]
    vantage_only_economies: tuple[str, ...]
    is_regional: bool  # True if this carrier is itself based in an in-scope economy
    corroboration_count: int

    @property
    def dependent_count(self) -> int:
        return len(self.dependent_economies)

    @property
    def vantage_only_count(self) -> int:
        return len(self.vantage_only_economies)


# A handful of ASNs where automatic name extraction from `detour_ix_name`/
# `note` text picks up a descriptive phrase instead of the carrier's actual
# name (e.g. "AS139609 (Solomon Islands ...)" reads as a location, not a
# name). Hand-curated and narrowly scoped, same governance principle as
# `regional_carrier_facilities.py` -- only the display name is overridden
# here, never the computed economies/counts.
_CARRIER_NAME_OVERRIDES: dict[int, str] = {
    139609: "SISCC (Solomon Islands Submarine Cable Company)",
    18200: "OPT NC (Office des Postes et Telecommunications, New Caledonia)",
}

_ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}
_CORROBORATION_RE = re.compile(
    r"(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+"
    r"(?:independent corroboration|independent confirmation|distinct source economy)",
    re.IGNORECASE,
)
_CARRIER_NAME_RE = re.compile(r"AS(\d+) \(([^,)]+)")


def _max_corroboration_ordinal(note: str) -> int:
    """Highest corroboration ordinal mentioned in `note`, or 1 if none found."""
    matches = _CORROBORATION_RE.findall(note)
    if not matches:
        return 1
    return max(_ORDINAL_WORDS[word.lower()] for word in matches)


def _compute_transit_suppliers(
    fishbowl: dict,
    triangulation_dir: Path = DEFAULT_TRIANGULATION_DIR,
) -> tuple[TransitSupplier, ...]:
    """Rank confirmed transit carriers by how many in-scope economies depend on them.

    Ground truth for "who is the immediate transit supplier" comes from each
    `ConfirmedDetour` entry's own persisted triangulation JSON
    (`traceroute_upstream_asn`, the ASN `analyze_measurement` confirmed sits
    directly upstream of the target) -- not the free-text `detour_ix_name`,
    which sometimes names an intermediate carrier further up the path
    instead (e.g. "AS174 (Cogent), via AS6453 (Tata)" when Cogent happened
    to be the first hop reached, even though Tata is the confirmed immediate
    neighbor). `ConfirmedLocalTransit` entries use their own structured
    `provider_asn`/`provider_cc`/`customer_cc` fields directly, since there's
    no separate triangulation lookup needed there.
    """
    # Priority, highest first: `ConfirmedLocalTransit.provider_name` is an
    # authoritative structured field; `detour_ix_name` is written to name
    # the carrier deliberately; free-text `note` prose is a last resort,
    # since it can just as easily capture a descriptive phrase around an
    # "AS<n> (...)" mention as the carrier's actual name.
    names: dict[int, str] = {}
    for transit in CONFIRMED_LOCAL_TRANSIT:
        names.setdefault(transit.provider_asn, transit.provider_name)
    for detour in CONFIRMED_DETOURS:
        for m in _CARRIER_NAME_RE.finditer(detour.detour_ix_name):
            names.setdefault(int(m.group(1)), m.group(2).strip())
    for detour in CONFIRMED_DETOURS:
        for m in _CARRIER_NAME_RE.finditer(detour.note):
            names.setdefault(int(m.group(1)), m.group(2).strip())
    names.update(_CARRIER_NAME_OVERRIDES)

    dependent: dict[int, set[str]] = {}
    vantage: dict[int, set[str]] = {}
    entry_count: dict[int, int] = {}

    for detour in CONFIRMED_DETOURS:
        tri_path = triangulation_dir / f"{detour.measurement_id}.json"
        if not tri_path.exists():
            continue
        tri = json.loads(tri_path.read_text())
        upstream_asns = {
            p.get("traceroute_upstream_asn") for p in tri["probes"] if p.get("ris_agrees")
        }
        upstream_asns.discard(None)
        for asn in upstream_asns:
            dependent.setdefault(asn, set()).add(detour.target_cc)
            vantage.setdefault(asn, set()).add(detour.source_cc)
            entry_count[asn] = entry_count.get(asn, 0) + 1

    for transit in CONFIRMED_LOCAL_TRANSIT:
        asn = transit.provider_asn
        dependent.setdefault(asn, set()).add(transit.customer_cc)
        entry_count[asn] = max(
            entry_count.get(asn, 0), _max_corroboration_ordinal(transit.note)
        )

    all_asns = set(dependent) | set(vantage)
    suppliers = [
        TransitSupplier(
            asn=asn,
            name=names.get(asn, f"AS{asn}"),
            dependent_economies=tuple(sorted(dependent.get(asn, set()))),
            vantage_only_economies=tuple(
                sorted(vantage.get(asn, set()) - dependent.get(asn, set()))
            ),
            is_regional=str(asn) in fishbowl,
            corroboration_count=entry_count.get(
                asn, len(dependent.get(asn, set()) | vantage.get(asn, set()))
            ),
        )
        for asn in all_asns
    ]
    return tuple(
        sorted(suppliers, key=lambda s: (-s.dependent_count, -s.vantage_only_count, s.asn))
    )


@dataclass(frozen=True)
class RegionalHub:
    """One in-scope Pacific economy confirmed (RIS + Atlas) as a real transit

    waypoint for *other* in-scope economies' traffic -- entirely within the
    fishbowl, the mirror image of `TransitSupplier`'s external carriers.
    Built from `ConfirmedLocalTransit` entries where `provider_cc` and
    `customer_cc` differ (a same-economy entry is domestic transit, not a
    regional-hub relationship). `dependent_economies` is every other
    economy this hub has been confirmed to serve. `carriers` is the
    distinct carrier(s) based in this economy doing that serving --
    one economy can host more than one such carrier. `corroboration_count`
    sums each underlying relationship's own corroboration depth (the
    highest "Nth independent corroboration" ordinal mined from its note,
    same method `TransitSupplier` uses), so an economy serving two
    economies each reconfirmed many times outranks one serving two
    economies confirmed only once each.
    """

    economy_cc: str
    economy_name: str
    dependent_economies: tuple[str, ...]
    carriers: tuple[str, ...]
    corroboration_count: int

    @property
    def dependent_count(self) -> int:
        return len(self.dependent_economies)


def _compute_regional_hubs(economy_names: dict[str, str]) -> tuple[RegionalHub, ...]:
    """Rank in-scope economies by how many *other* in-scope economies confirm routing through them."""
    dependent: dict[str, set[str]] = {}
    carriers: dict[str, set[str]] = {}
    corroboration: dict[str, int] = {}

    for transit in CONFIRMED_LOCAL_TRANSIT:
        if transit.customer_cc == transit.provider_cc:
            continue  # domestic transit, not a cross-economy hub relationship
        cc = transit.provider_cc
        dependent.setdefault(cc, set()).add(transit.customer_cc)
        carriers.setdefault(cc, set()).add(transit.provider_name)
        corroboration[cc] = corroboration.get(cc, 0) + _max_corroboration_ordinal(transit.note)

    hubs = [
        RegionalHub(
            economy_cc=cc,
            economy_name=economy_names.get(cc, cc),
            dependent_economies=tuple(sorted(deps)),
            carriers=tuple(sorted(carriers.get(cc, set()))),
            corroboration_count=corroboration.get(cc, 0),
        )
        for cc, deps in dependent.items()
    ]
    return tuple(
        sorted(hubs, key=lambda h: (-h.dependent_count, -h.corroboration_count, h.economy_cc))
    )


@dataclass(frozen=True)
class ExternalHub:
    """One external city where confirmed detours physically cross, per `ConfirmedDetour.detour_hub`.

    The mirror image of `RegionalHub`: where the region's traffic actually
    leaves the fishbowl, rather than where it stays inside it.
    `entry_count` is how many `ConfirmedDetour` entries name this city as
    their real external touchpoint -- not a carrier-level guess, since
    every current entry's hub was set (or corrected) from actual hop
    evidence or a real IXP-LAN address match, per this project's own
    `hop_geolocation` discipline. `dependent_economies` is every distinct
    target economy at least one of those entries reaches.
    `carrier_count` is how many distinct confirmed-upstream ASNs (ground-
    truthed the same way as `TransitSupplier`, via each entry's persisted
    triangulation JSON) have been observed crossing at this city -- a
    high count means the city is a genuine shared crossroads, not just
    one carrier's own path repeated many times.
    """

    name: str
    entry_count: int
    dependent_economies: tuple[str, ...]
    carrier_count: int

    @property
    def dependent_count(self) -> int:
        return len(self.dependent_economies)


def _compute_external_hubs(
    triangulation_dir: Path = DEFAULT_TRIANGULATION_DIR,
) -> tuple[ExternalHub, ...]:
    """Rank the external cities where confirmed detours actually cross, by how much traffic does."""
    entry_count: dict[str, int] = {}
    dependent: dict[str, set[str]] = {}
    carriers: dict[str, set[int]] = {}

    for detour in CONFIRMED_DETOURS:
        hub = detour.detour_hub
        entry_count[hub] = entry_count.get(hub, 0) + 1
        dependent.setdefault(hub, set()).add(detour.target_cc)

        tri_path = triangulation_dir / f"{detour.measurement_id}.json"
        if not tri_path.exists():
            continue
        tri = json.loads(tri_path.read_text())
        upstream_asns = {
            p.get("traceroute_upstream_asn") for p in tri["probes"] if p.get("ris_agrees")
        }
        upstream_asns.discard(None)
        carriers.setdefault(hub, set()).update(upstream_asns)

    hubs = [
        ExternalHub(
            name=hub,
            entry_count=count,
            dependent_economies=tuple(sorted(dependent.get(hub, set()))),
            carrier_count=len(carriers.get(hub, set())),
        )
        for hub, count in entry_count.items()
    ]
    return tuple(sorted(hubs, key=lambda h: (-h.entry_count, h.name)))


# Satellite operators with a real, PeeringDB-registered presence this
# project has checked for -- a small, stable set, hand-curated same as
# `regional_carrier_facilities.py`, since there's no reliable automatic
# signal to detect "this ASN is a satellite operator" from RIS/PeeringDB
# data alone.
_SATELLITE_OPERATORS: dict[int, str] = {
    14593: "SpaceX Starlink",
    12684: "SES ASTRA S.A.",
    135409: "Kacific Broadband Satellites",
}


@dataclass(frozen=True)
class SatellitePathway:
    """One satellite operator's reach into the in-scope Pacific economies.

    Three different, deliberately distinct kinds of evidence, from
    weakest to strongest:

    - `ris_economies`: this project's own fishbowl-cached RIS neighbor
      data shows the economy's ASN lists this operator as a real
      BGP-observed neighbor -- a genuine relationship, but one RIS alone
      can't confirm actually carries the traffic a given traceroute
      takes (the same fishbowl-vs-traceroute distinction this whole
      project is built around).
    - `traceroute_confirmed_economies`: an Atlas traceroute has actually
      been observed transiting this operator's ASN on a path *to* that
      economy -- i.e. the economy is the demand side (a `ConfirmedDetour`
      `target_cc` or `ConfirmedLocalTransit` `customer_cc`), the one
      whose own reachability genuinely depends on this operator. This is
      deliberately NOT the same set as "every economy that ever sourced
      a traceroute which happened to transit this operator" -- a probe
      fired from Fiji toward a Tongan target doesn't mean Fiji's own
      connectivity runs through the satellite, only Tonga's does. See
      `traceroute_vantage_economies` for that other axis.
    - `candidate_only_economies`: mentioned only in an unconfirmed
      `CandidatePeering` note, same target-side convention as above --
      a real traceroute signal RIS doesn't corroborate.
    - `traceroute_vantage_economies`: every economy that has been used
      as a traceroute *source* to test this operator at all (regardless
      of outcome) -- a measure of how broadly this project's evidence
      base is, not a claim about who the operator serves. Deliberately
      kept separate from the two fields above so a reader can't mistake
      "we tested this operator from N places" for "this operator serves
      N economies".

    An operator can have RIS-visible relationships with economies this
    project has never traceroute-confirmed at all -- e.g. the Kacific
    case when this dataclass was first built: registered, real BGP
    relationships, zero traceroute evidence. That's not assumed to be
    permanently true of any operator here -- see
    `describe_satellite_pathway` below, which reads current data rather
    than asserting a fixed narrative.
    """

    asn: int
    name: str
    ris_economies: tuple[str, ...]
    traceroute_confirmed_economies: tuple[str, ...]
    candidate_only_economies: tuple[str, ...]
    traceroute_vantage_economies: tuple[str, ...]


def _compute_satellite_pathways(
    fishbowl: dict,
    asn_to_cc: dict[int, str],
) -> tuple[SatellitePathway, ...]:
    """Find every in-scope economy with a known relationship to a satellite operator.

    `ris_economies` comes from scanning every in-scope ASN's own
    fishbowl-cached RIS neighbor list for a satellite operator's ASN
    (string-keyed in the cached JSON, unlike everywhere else in this
    module that works with the live registry) -- this catches real BGP
    relationships even when this project has never fired a traceroute
    anywhere near them.

    `traceroute_confirmed_economies`/`candidate_only_economies` scan the
    note text of every entry in all three finding dataclasses for a
    literal "AS<n>" mention, since satellite legs are typically described
    as an intermediate hop in another entry's prose, not stored as their
    own structured provider/target relationship. Only the demand-side
    economy (`target_cc`/`customer_cc`) is counted as "confirmed" or
    "candidate" -- the source/vantage economy that merely happened to
    fire the traceroute goes into `traceroute_vantage_economies`
    instead, so the two axes (who's served vs. who tested it) can't get
    conflated in whatever consumes this data.
    """
    pathways = []
    for sat_asn, sat_name in _SATELLITE_OPERATORS.items():
        ris_ccs: set[str] = set()
        for asn_str, entry in fishbowl.items():
            if str(sat_asn) in entry.get("neighbors", {}):
                cc = asn_to_cc.get(int(asn_str))
                if cc:
                    ris_ccs.add(cc)

        marker = f"AS{sat_asn}"
        confirmed_ccs: set[str] = set()
        vantage_ccs: set[str] = set()
        for detour in CONFIRMED_DETOURS:
            if marker in detour.note or marker in detour.detour_ix_name:
                confirmed_ccs.add(detour.target_cc)
                vantage_ccs.add(detour.source_cc)
        for transit in CONFIRMED_LOCAL_TRANSIT:
            if marker in transit.note:
                # A satellite mention in a local-transit note almost always
                # describes the *customer's* own alternate/backup neighbor
                # (e.g. Tuvalu's Starlink backup, mentioned while
                # explaining FINTEL's dominance) -- not something the
                # provider's home economy actually transits. Attribute to
                # the customer only, not the provider, to avoid folding an
                # unrelated economy in just because it happens to be the
                # entry's provider_cc.
                confirmed_ccs.add(transit.customer_cc)
                vantage_ccs.add(transit.vantage_point_cc)

        candidate_ccs: set[str] = set()
        for candidate in CANDIDATE_PEERING:
            if marker in candidate.note:
                candidate_ccs.add(candidate.target_cc)
                vantage_ccs.add(candidate.vantage_point_cc)
        candidate_ccs -= confirmed_ccs

        pathways.append(
            SatellitePathway(
                asn=sat_asn,
                name=sat_name,
                ris_economies=tuple(sorted(ris_ccs)),
                traceroute_confirmed_economies=tuple(sorted(confirmed_ccs)),
                candidate_only_economies=tuple(sorted(candidate_ccs)),
                traceroute_vantage_economies=tuple(sorted(vantage_ccs)),
            )
        )
    return tuple(pathways)


def describe_satellite_pathway(sat: dict, economy_names: dict[str, str]) -> str:
    """One plain-text paragraph summarizing an operator's current evidence state.

    Computed fresh from `sat` (a `SatellitePathway` as a dict, e.g. from
    `ReportData.satellite_pathways`) every time it's called, specifically
    so this can never go stale the way a hand-written "as of today, X
    hasn't been confirmed yet" paragraph inevitably does the moment a
    later tranche confirms it. Shared by both the ASCII and HTML
    renderers -- plain "--" for dash punctuation either way, matching
    how every other note/finding string in this project is written and
    how `html_report.py` already embeds note text unmodified (`html.escape`
    only, no dash substitution).
    """

    def _names(ccs: tuple[str, ...]) -> str:
        return ", ".join(f"{economy_names.get(cc, cc)} ({cc})" for cc in ccs)

    ris = set(sat["ris_economies"])
    confirmed = set(sat["traceroute_confirmed_economies"])
    candidate = set(sat["candidate_only_economies"])
    vantage = sat["traceroute_vantage_economies"]
    untested = ris - confirmed - candidate

    header = f"AS{sat['asn']} ({sat['name']})"

    if not confirmed and not candidate:
        if not ris:
            return (
                f"{header}: no RIS-observed relationship with any in-scope "
                "economy recorded yet, and no traceroute has touched it."
            )
        return (
            f"{header} has RIS-observed BGP relationships with "
            f"{len(ris)} in-scope econom{'y' if len(ris) == 1 else 'ies'} "
            f"({_names(tuple(sorted(ris)))}), but no traceroute this "
            "project has run has confirmed transit through it yet -- a "
            "real, registered relationship with zero traceroute evidence "
            "so far."
        )

    parts = [
        f"{header} is traceroute-confirmed reaching "
        f"{_names(tuple(sorted(confirmed))) or '(no economy yet)'}"
    ]
    if candidate:
        parts.append(
            f"with a further real-but-unconfirmed signal toward "
            f"{_names(tuple(sorted(candidate)))}"
        )
    if vantage:
        parts.append(
            f"tested from {len(vantage)} distinct vantage "
            f"point{'s' if len(vantage) != 1 else ''} "
            f"({_names(vantage)})"
        )
    sentence = ", ".join(parts) + "."
    if untested:
        sentence += (
            f" Still untested: {_names(tuple(sorted(untested)))} -- a real "
            "RIS-observed relationship this project has never traceroute-"
            "confirmed."
        )
    return sentence


@dataclass(frozen=True)
class IxpSummary:
    """One IXP's row in both report formats' IXP table."""

    ix_id: int
    name: str
    city: str
    country: str
    in_fishbowl: bool | str
    member_count: int


@dataclass(frozen=True)
class ReportData:
    """Everything both report formats render from."""

    generated_at: str
    total_economies: int
    total_asns: int
    asns_with_neighbors: int
    asns_with_ixp: int
    asns_with_facility: int
    ixp_registry_in_fishbowl: int
    ixp_registry_out_of_fishbowl: int
    ixp_registry_tba: int
    economies: tuple[EconomySummary, ...]
    ixps: tuple[IxpSummary, ...]
    transit_suppliers: tuple[dict, ...]
    regional_hubs: tuple[dict, ...]
    external_hubs: tuple[dict, ...]
    satellite_pathways: tuple[dict, ...]
    satellite_narrative: tuple[str, ...]
    confirmed_detours: tuple[dict, ...]
    confirmed_local_transit: tuple[dict, ...]
    candidate_peering: tuple[dict, ...]

    def to_dict(self) -> dict:
        """Return a plain, JSON-serializable dict of this report data."""
        return asdict(self)

    @property
    def ixp_registry_out_of_fishbowl_share(self) -> float:
        """Fraction of real, in-scope-network-used peering points that sit outside the study region.

        Every exchange in the registry is one at least one in-scope ASN
        actually declares PeeringDB membership at -- this isn't a count
        of arbitrary known IXPs, it's a count of peering points this
        project's own networks are really using. Computed, not stored,
        so it can never drift out of sync with the two counts it's
        derived from.
        """
        total = self.ixp_registry_in_fishbowl + self.ixp_registry_out_of_fishbowl
        if total == 0:
            return 0.0
        return self.ixp_registry_out_of_fishbowl / total


def build_report_data(
    registry_path: Path = DEFAULT_OUTPUT_PATH,
    fishbowl_path: Path = DEFAULT_SUMMARY_PATH,
    ixp_registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> ReportData:
    """Assemble the shared report data structure from this project's own outputs.

    Args:
        registry_path: Path to the Phase 0b ASN registry.
        fishbowl_path: Path to Phase 1a's fishbowl dataset.
        ixp_registry_path: Path to the Phase 1e IXP LAN subnet registry.

    Returns:
        A `ReportData` instance, ready for either report renderer.
    """
    registry = json.loads(registry_path.read_text())
    fishbowl = json.loads(fishbowl_path.read_text())
    ixp_registry = json.loads(ixp_registry_path.read_text())

    economies: list[EconomySummary] = []
    for cc, entry in sorted(registry.items()):
        asns = entry["asns"]
        with_neighbors = sum(1 for asn in asns if fishbowl.get(str(asn), {}).get("neighbors"))
        with_ixp = sum(1 for asn in asns if fishbowl.get(str(asn), {}).get("ixp_memberships"))
        with_facility = sum(
            1 for asn in asns if fishbowl.get(str(asn), {}).get("facility_presence")
        )
        economies.append(
            EconomySummary(
                cc=cc,
                name=entry["name"],
                subregion=entry["subregion"],
                asn_count=len(asns),
                asns_with_neighbors=with_neighbors,
                asns_with_ixp=with_ixp,
                asns_with_facility=with_facility,
            )
        )

    member_counts: dict[int, int] = {}
    for asn_entry in fishbowl.values():
        for ix in asn_entry.get("ixp_memberships", []):
            member_counts[ix["ix_id"]] = member_counts.get(ix["ix_id"], 0) + 1

    ixps = tuple(
        IxpSummary(
            ix_id=int(ix_id),
            name=v["name"],
            city=v["city"],
            country=v["country"],
            in_fishbowl=v["in_fishbowl"],
            member_count=member_counts.get(int(ix_id), 0),
        )
        for ix_id, v in sorted(ixp_registry.items(), key=lambda kv: kv[1]["name"])
    )

    confirmed_detours = tuple(asdict(detour) for detour in CONFIRMED_DETOURS)
    confirmed_local_transit = tuple(asdict(t) for t in CONFIRMED_LOCAL_TRANSIT)
    candidate_peering = tuple(asdict(c) for c in CANDIDATE_PEERING)
    transit_suppliers = tuple(asdict(s) for s in _compute_transit_suppliers(fishbowl))
    economy_names = {cc: entry["name"] for cc, entry in registry.items()}
    regional_hubs = tuple(asdict(h) for h in _compute_regional_hubs(economy_names))
    external_hubs = tuple(asdict(h) for h in _compute_external_hubs())
    asn_to_cc = {asn: cc for cc, entry in registry.items() for asn in entry["asns"]}
    satellite_pathways = tuple(
        asdict(s) for s in _compute_satellite_pathways(fishbowl, asn_to_cc)
    )
    satellite_narrative = tuple(
        describe_satellite_pathway(s, economy_names) for s in satellite_pathways
    )

    return ReportData(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_economies=len(registry),
        total_asns=len(fishbowl),
        asns_with_neighbors=sum(1 for v in fishbowl.values() if v["neighbors"]),
        asns_with_ixp=sum(1 for v in fishbowl.values() if v["ixp_memberships"]),
        asns_with_facility=sum(1 for v in fishbowl.values() if v["facility_presence"]),
        ixp_registry_in_fishbowl=sum(
            1 for v in ixp_registry.values() if v["in_fishbowl"] is True
        ),
        ixp_registry_out_of_fishbowl=sum(
            1 for v in ixp_registry.values() if v["in_fishbowl"] is False
        ),
        ixp_registry_tba=sum(1 for v in ixp_registry.values() if v["in_fishbowl"] == "TBA"),
        economies=tuple(economies),
        ixps=ixps,
        transit_suppliers=transit_suppliers,
        regional_hubs=regional_hubs,
        external_hubs=external_hubs,
        satellite_pathways=satellite_pathways,
        satellite_narrative=satellite_narrative,
        confirmed_detours=confirmed_detours,
        confirmed_local_transit=confirmed_local_transit,
        candidate_peering=candidate_peering,
    )
