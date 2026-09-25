"""Assemble the public website from the generated reports (owner, 2026-09-25).

Builds `site/dist/` for a Cloudflare Worker with static assets (`wrangler.jsonc`),
connected to the GitHub repo via Workers Builds, which runs this on every push (build command `python3 src/pacific_peering/reports/site.py`,
output directory `site/dist`), so the nightly/Wednesday report commits
republish the site with no deploy step or credentials here. Standard library
only, so it runs in Cloudflare's build image without installing the project.
- `index.html` is `outputs/reports/report.html`, with its two chart references
  (`../viz/*.svg`, relative to `outputs/reports/`) rewritten to `viz/*.svg`;
- `viz/` holds those SVGs;
- a few plain-text companion reports go under `reports/` for anyone who
  wants the raw tables.
Nothing else from the repo is published: no data/, no findings database.
Fails loudly if the report references a chart that isn't there, rather than
publishing a page with broken images.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

REPORT_HTML = Path("outputs/reports/report.html")
VIZ_DIR = Path("outputs/viz")
DEFAULT_OUT_DIR = Path("site/dist")
TEXT_REPORTS = (
    "report.txt",
    "probe_gaps.txt",
    "rov_cloudflare.txt",
    "ipv6_fleet.txt",
    "offshore_check.txt",
)
NOT_FOUND_HTML = (
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Not found -- Pacific Peering</title>"
    "</head><body><h1>Not found</h1><p>That page isn't part of this site. The report is at "
    "<a href=\"/\">the home page</a>.</p></body></html>\n"
)
_VIZ_REF = re.compile(r'(src|href)="\.\./viz/([^"]+)"')


def build_site(out_dir: Path = DEFAULT_OUT_DIR, reports_dir: Path = REPORT_HTML.parent, viz_dir: Path = VIZ_DIR) -> Path:
    html = (reports_dir / REPORT_HTML.name).read_text()
    referenced = sorted(set(m.group(2) for m in _VIZ_REF.finditer(html)))
    missing = [name for name in referenced if not (viz_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"report.html references missing charts: {missing}")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "viz").mkdir(parents=True)
    (out_dir / "reports").mkdir()
    (out_dir / "index.html").write_text(_VIZ_REF.sub(r'\1="viz/\2"', html))
    (out_dir / "404.html").write_text(NOT_FOUND_HTML)  # served by wrangler.jsonc's "404-page" handling
    for name in referenced:
        shutil.copy2(viz_dir / name, out_dir / "viz" / name)
    for name in TEXT_REPORTS:
        if (reports_dir / name).exists():
            shutil.copy2(reports_dir / name, out_dir / "reports" / name)
    logger.info("Built site in %s: index.html, %d chart(s), %d text report(s)",
                out_dir, len(referenced), len(list((out_dir / "reports").iterdir())))
    return out_dir


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    build_site()


if __name__ == "__main__":
    main()
