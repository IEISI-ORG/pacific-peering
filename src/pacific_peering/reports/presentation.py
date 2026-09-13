"""Presentation skeleton generator (Phase 2a).

Renders the same `ReportData` the ASCII/HTML reports use into a
Marp-compatible Markdown slide deck (https://marp.app — plain Markdown
with `---` slide separators, renders directly in VS Code's Marp
extension or `marp-cli` to PDF/PPTX/HTML). This is a *skeleton*: real
data plugged into a conference-talk structure, not finished narration —
whoever gives the talk still needs to add speaker framing, timing, and
judgment about what to emphasize for a given audience/venue.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pacific_peering.reports.data import ReportData, build_report_data

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("outputs/reports/presentation.md")

_FRONTMATTER = """---
marp: true
theme: default
paginate: true
---

"""


def render_presentation_skeleton(data: ReportData) -> str:
    """Render `data` as a Marp Markdown slide deck skeleton.

    Returns:
        The full Markdown document as a string.
    """
    detour_slides = "\n\n".join(
        f"""## Finding: {d['source_cc']} -> {d['target_cc']} detours via {d['detour_ix_name']}

- {d['note']}
- RIS-observed neighbor count: **{d['ris_observation_count']}**
- Confirmed by live Atlas traceroute (measurement `{d['measurement_id']}`)
- Both RIS and Atlas agree — this project's bar for a real finding, not a guess
  from one source alone

<!-- SPEAKER NOTE: add the specific hop IP / IXP evidence for this pair here -->"""
        for d in data.confirmed_detours
    )

    transit_slides = "\n\n".join(
        f"""## Finding: AS{t['provider_asn']} ({t['provider_name']}) -> AS{t['customer_asn']} ({t['customer_name']})

- {t['note']}
- RIS-observed neighbor count: **{t['ris_observation_count']}**
- Confirmed by live Atlas traceroute (measurement `{t['measurement_id']}`,
  vantage point: {t['vantage_point_cc']})
- Unlike the detour findings above, this stays entirely in-region —
  not everything routes out via Sydney

<!-- SPEAKER NOTE: this is a good-news slide - don't let it get lost after
     the detour findings -->"""
        for t in data.confirmed_local_transit
    )

    in_fishbowl_ixps = [ix for ix in data.ixps if ix.in_fishbowl is True]
    out_ixps = [ix for ix in data.ixps if ix.in_fishbowl is False]

    return f"""{_FRONTMATTER}# Pacific Peering

### Mapping regional internet routing across Melanesia, Polynesia, and Micronesia

<!-- SPEAKER NOTE: intro, who you are, why this project exists -->

---

## The question

Does Pacific-to-Pacific internet traffic actually stay in the Pacific,
or does it detour through Australia, the US, or elsewhere?

<!-- SPEAKER NOTE: hook the audience with the concrete cost of this
     (latency, sovereignty, cost) before showing methodology -->

---

## Scope

- **{data.total_economies} economies**: Melanesia, Polynesia, Micronesia + Guam
  (Australia, NZ, Hawaii excluded)
- **{data.total_asns} ASNs** tracked
- Public data (RIPEstat, PeeringDB) + active measurement (RIPE Atlas)

---

## Methodology: the "fish bowl" problem

- RIS + PeeringDB is an outside-looking-in view — we can see paths and
  memberships, but not real internal routing decisions ("we can't get in
  the bowl")
- **Rule: no topology claim on one source alone** — RIS and Atlas must
  both agree before we call something a finding
- PeeringDB is a lead, never ground truth — it can be wrong, stale, or
  simply missing data (e.g. a real Solomon Islands IXP absent from it
  entirely)

<!-- SPEAKER NOTE: this slide is the credibility slide - spend time here -->

---

{detour_slides}

---

{transit_slides}

---

## The IXP landscape

- **{len(in_fishbowl_ixps)} in-region exchanges** confirmed:
  {", ".join(ix.name for ix in in_fishbowl_ixps)}
- **{len(out_ixps)} out-of-region exchanges** confirmed as destinations for
  in-scope ASNs (Sydney, Tokyo, Frankfurt, Los Angeles, and others)
- Every classification here is an explicit human decision, never
  auto-inferred from a country-code lookup

---

## What this shows

<!-- SPEAKER NOTE: state the takeaway plainly - out-of-region peering is
     not optimal by definition (settled premise, not a hypothesis); these
     are concrete, confirmed instances, not the full extent of it yet -->

- Confirmed: real Pacific-to-Pacific traffic physically routes via Sydney
- Not yet measured: how widespread this is across all {data.total_asns} ASNs —
  only a handful of AS pairs have been triangulated so far
- Atlas probe coverage itself is a limiting factor: several economies have
  zero connected probes

---

## Next steps

- Broaden the triangulated AS-pair sample
- Pursue a native (non-proxied) Atlas vantage point in economies that
  currently lack one
- [Add venue-specific next steps here]

---

## Thank you

- Project: `IEISI-ORG/pacific-peering` on GitHub
- Full methodology and findings: `task_plan.md` in the repo
- Support: buymeacoffee.com/terrysweetser

<!-- SPEAKER NOTE: Q&A -->
"""


def write_presentation_skeleton(output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    """Build report data, render the presentation skeleton, and write it to `output_path`.

    Returns:
        The path the skeleton was written to.
    """
    data = build_report_data()
    text = render_presentation_skeleton(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text)
    logger.info("Wrote presentation skeleton to %s", output_path)
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    write_presentation_skeleton()


if __name__ == "__main__":
    main()
