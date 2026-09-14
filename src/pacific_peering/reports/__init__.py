"""Report generation: ASCII, HTML, and a presentation skeleton, all from one shared ReportData."""

from .ascii_report import render_ascii_report, write_ascii_report
from .data import EconomySummary, IxpSummary, ReportData, build_report_data
from .html_report import render_html_report, write_html_report
from .presentation import render_presentation_skeleton, write_presentation_skeleton
from .probe_gap_report import render_probe_gap_report, write_probe_gap_report

__all__ = [
    "render_ascii_report",
    "write_ascii_report",
    "render_html_report",
    "write_html_report",
    "render_presentation_skeleton",
    "write_presentation_skeleton",
    "EconomySummary",
    "IxpSummary",
    "ReportData",
    "build_report_data",
    "render_probe_gap_report",
    "write_probe_gap_report",
]
