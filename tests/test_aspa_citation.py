"""ASPA has no RFC yet: RFC 9582 is the ROA profile, not ASPA.

ASPA is draft-ietf-sidrops-aspa-profile (submitted to the IESG, Nov 2026).
The report headings, docstrings and auto_classify's ASPA-confirmed note all
cited "RFC 9582" for ASPA until 2026-11-07; this keeps that from returning.
"""

from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def test_no_rfc_9582_cited_for_aspa() -> None:
    offenders = [
        f"{path.relative_to(SRC)}:{n}"
        for path in SRC.rglob("*.py")
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if "RFC 9582" in line
    ]
    assert offenders == [], f"RFC 9582 is the ROA profile, not ASPA: {offenders}"


def test_report_headings_cite_the_aspa_draft() -> None:
    for name in ("ascii_report.py", "html_report.py"):
        text = (SRC / "pacific_peering" / "reports" / name).read_text()
        assert "draft-ietf-sidrops-aspa-profile" in text, name
