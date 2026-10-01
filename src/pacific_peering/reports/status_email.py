"""Render the unattended daily check's status JSON as an HTML email (plus a text alternative).

Deterministic on purpose: the unattended agent writes the judgement into
`status.json`; this module owns the look, so every email reads the same way.
Email-client safe: table layout and inline styles only (Gmail drops <style>
blocks and ignores flex/grid), every value HTML-escaped. Every coloured
surface is a table cell carrying the legacy `bgcolor` attribute as well as
the CSS background: the Gmail connector's sanitizer strips *all* CSS
background declarations (checked 2026-10-01 by round-tripping a draft --
`background`, `background-color` and `background-image` vanished, `bgcolor`,
`color`, `border` and `border-radius` survived), which left the first
dry-run draft as white text on white. Small inline chips can't take
`bgcolor`, so they're outlined instead of filled.

status.json shape:
    {
      "run_at": ISO timestamp, "mode": "dry-run" | "live",
      "overall": "ok" | "attention" | "action",
      "headline": one sentence,
      "stats": [{"label", "value"}],
      "needs_attention": [{"title", "severity": "high"|"medium"|"low", "detail",
                           "suggested_action", "refs": [str]}],
      "escalated": [{"title", "where"}],          # what this run wrote down
      "checks": [{"name", "status": "ok"|"warn"|"fail", "summary"}],
      "links": [{"label", "url"}]
    }

`uv run pacific-peering-status-email STATUS_JSON --html OUT.html --text OUT.txt`
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

# Pacific palette: deep-ocean header, reef accents. Status colours chosen to
# stay distinguishable for red-green colour-blind readers (blue/amber/red).
INK = "#13253a"
MUTED = "#5b6b7c"
RULE = "#e3e8ee"
PAGE = "#eef3f7"
CARD = "#ffffff"
OCEAN = "#0b3d5c"
LAGOON = "#1f8a9e"
OVERALL = {
    "ok": ("#1f6fb2", "All clear"),
    "attention": ("#b7791f", "Needs a look"),
    "action": ("#b42318", "Action needed"),
}
SEVERITY = {"high": "#b42318", "medium": "#b7791f", "low": "#1f6fb2"}
CHECK = {"ok": ("#1f6fb2", "OK"), "warn": ("#b7791f", "WARN"), "fail": ("#b42318", "FAIL")}
FONT = "font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"

e = html.escape


def _pill(colour: str, text: str) -> str:
    return (f'<table cellpadding="0" cellspacing="0" style="display:inline-table;"><tr>'
            f'<td bgcolor="{colour}" style="background:{colour};padding:3px 10px;border-radius:999px;{FONT}'
            f'color:#ffffff;font-size:12px;font-weight:600;letter-spacing:.3px;white-space:nowrap;">{e(text)}</td>'
            f'</tr></table>')


def _section(title: str, body: str) -> str:
    return (f'<tr><td style="padding:24px 28px 4px;{FONT}font-size:13px;font-weight:700;color:{LAGOON};'
            f'text-transform:uppercase;letter-spacing:1px;">{e(title)}</td></tr>'
            f'<tr><td style="padding:4px 28px 8px;">{body}</td></tr>')


def _stats(stats: list[dict]) -> str:
    if not stats:
        return ""
    cells = "".join(
        f'<td width="{100 // len(stats)}%" valign="top" style="padding:6px;vertical-align:top;"><table role="presentation" width="100%" '
        f'cellpadding="0" cellspacing="0" style="border-radius:8px;"><tr><td bgcolor="{PAGE}" style="background:{PAGE};border-radius:8px;padding:12px 14px;height:46px;vertical-align:top;{FONT}">'
        f'<div style="font-size:22px;font-weight:700;color:{OCEAN};">{e(str(s["value"]))}</div>'
        f'<div style="font-size:12px;color:{MUTED};margin-top:2px;">{e(s["label"])}</div></td></tr></table></td>'
        for s in stats
    )
    return f'<tr><td style="padding:16px 22px 0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{cells}</tr></table></td></tr>'


def _attention(items: list[dict]) -> str:
    if not items:
        return f'<p style="{FONT}font-size:14px;color:{MUTED};margin:6px 0;">Nothing needs your attention.</p>'
    cards = []
    for it in items:
        colour = SEVERITY.get(it.get("severity", "low"), SEVERITY["low"])
        refs = "".join(
            f'<span style="display:inline-block;margin:6px 6px 0 0;padding:1px 7px;border-radius:4px;'
            f'border:1px solid {RULE};color:{MUTED};font-size:12px;font-family:Menlo,Consolas,monospace;">{e(r)}</span>'
            for r in it.get("refs", [])
        )
        action = (f'<div style="margin-top:8px;font-size:13px;color:{INK};"><b>Suggested:</b> {e(it["suggested_action"])}</div>'
                  if it.get("suggested_action") else "")
        cards.append(
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:8px 0;'
            f'border:1px solid {RULE};border-left:4px solid {colour};border-radius:6px;">'
            f'<tr><td bgcolor="{CARD}" style="background:{CARD};padding:12px 14px;{FONT}">'
            f'<div style="font-size:11px;font-weight:700;color:{colour};text-transform:uppercase;letter-spacing:.8px;">'
            f'{e(it.get("severity", "low"))}</div>'
            f'<div style="font-size:15px;font-weight:600;color:{INK};margin-top:2px;">{e(it["title"])}</div>'
            f'<div style="font-size:14px;color:{INK};margin-top:6px;line-height:1.5;">{e(it.get("detail", ""))}</div>'
            f'{action}{refs}</td></tr></table>'
        )
    return "".join(cards)


def _escalated(items: list[dict]) -> str:
    if not items:
        return f'<p style="{FONT}font-size:14px;color:{MUTED};margin:6px 0;">Nothing new was escalated.</p>'
    rows = "".join(
        f'<li style="margin:4px 0;">{e(it["title"])} <span style="color:{MUTED};">({e(it.get("where", ""))})</span></li>'
        for it in items
    )
    return f'<ul style="{FONT}font-size:14px;color:{INK};margin:6px 0;padding-left:20px;line-height:1.5;">{rows}</ul>'


def _checks(items: list[dict]) -> str:
    rows = "".join(
        f'<tr><td style="padding:8px 10px 8px 0;border-bottom:1px solid {RULE};vertical-align:top;width:58px;">'
        f'{_pill(*CHECK.get(c["status"], CHECK["warn"]))}</td>'
        f'<td style="padding:8px 0;border-bottom:1px solid {RULE};{FONT}font-size:14px;color:{INK};">'
        f'<b>{e(c["name"])}</b><br><span style="color:{MUTED};">{e(c.get("summary", ""))}</span></td></tr>'
        for c in items
    )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>'


def render_html(s: dict) -> str:
    colour, label = OVERALL.get(s.get("overall", "attention"), OVERALL["attention"])
    dry = s.get("mode") == "dry-run"
    banner = (f'<tr><td bgcolor="#fff4e5" style="background:#fff4e5;padding:8px 28px;{FONT}font-size:13px;color:#8a5a00;">'
              f'Dry run: drafted, not sent. Nothing was committed or escalated.</td></tr>' if dry else "")
    links = " &nbsp;&middot;&nbsp; ".join(
        f'<a href="{e(link["url"])}" style="color:{LAGOON};text-decoration:none;">{e(link["label"])}</a>'
        for link in s.get("links", [])
    )
    return f"""<!doctype html><html><body style="margin:0;padding:0;background:{PAGE};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{PAGE}" style="background:{PAGE};"><tr><td bgcolor="{PAGE}" align="center" style="background:{PAGE};padding:24px 12px;">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" bgcolor="{CARD}" style="max-width:640px;width:100%;background:{CARD};border-radius:12px;overflow:hidden;">
<tr><td bgcolor="{OCEAN}" style="background:{OCEAN};background-image:linear-gradient(135deg,{OCEAN},{LAGOON});padding:26px 28px;{FONT}">
  <div style="font-size:12px;color:#bfe3ea;letter-spacing:1.5px;text-transform:uppercase;">Pacific Peering &middot; daily check</div>
  <div style="font-size:22px;font-weight:700;color:#fff;margin-top:6px;">{e(s.get("run_at", "")[:10])}</div>
  <div style="margin-top:12px;">{_pill(colour, label)}</div>
  <div style="font-size:15px;color:#e6f4f7;margin-top:12px;line-height:1.5;">{e(s.get("headline", ""))}</div>
</td></tr>
{banner}
{_stats(s.get("stats", []))}
{_section("Needs your attention", _attention(s.get("needs_attention", [])))}
{_section("Escalated this run", _escalated(s.get("escalated", [])))}
{_section("Checks", _checks(s.get("checks", [])))}
<tr><td style="padding:22px 28px 26px;{FONT}font-size:12px;color:{MUTED};border-top:1px solid {RULE};">
  {links}<br><br>Sent by the unattended daily check, the fallback for days without an interactive
  session. It reads and reports only: no Atlas credits, no changes to findings.
</td></tr>
</table></td></tr></table></body></html>
"""


def render_text(s: dict) -> str:
    out = [f"Pacific Peering daily check {s.get('run_at', '')[:10]} -- {OVERALL.get(s.get('overall'), OVERALL['attention'])[1]}",
           s.get("headline", ""), ""]
    if s.get("mode") == "dry-run":
        out += ["(Dry run: drafted, not sent.)", ""]
    out += [f"{x['label']}: {x['value']}" for x in s.get("stats", [])] + ["", "NEEDS YOUR ATTENTION"]
    for it in s.get("needs_attention", []) or [{"title": "Nothing.", "severity": ""}]:
        out.append(f"- [{it.get('severity', '')}] {it['title']}")
        if it.get("detail"):
            out.append(f"  {it['detail']}")
        if it.get("suggested_action"):
            out.append(f"  Suggested: {it['suggested_action']}")
    escalated = [f"- {x['title']} ({x.get('where', '')})" for x in s.get("escalated", [])]
    out += ["", "ESCALATED THIS RUN"] + (escalated or ["- nothing"])
    out += ["", "CHECKS"] + [f"- {c['status'].upper()}: {c['name']} -- {c.get('summary', '')}" for c in s.get("checks", [])]
    out += [""] + [f"{link['label']}: {link['url']}" for link in s.get("links", [])]
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("status", type=Path)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--text", type=Path, required=True)
    args = parser.parse_args()
    status = json.loads(args.status.read_text())
    args.html.write_text(render_html(status))
    args.text.write_text(render_text(status))
    print(f"Wrote {args.html} and {args.text}")


if __name__ == "__main__":
    main()
