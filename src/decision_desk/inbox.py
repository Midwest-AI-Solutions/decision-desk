"""Decision inbox rendering (HTML surface)."""

from __future__ import annotations

import html
from pathlib import Path

from .models import Decision, Urgency

_BADGE = {
    "emergency": ("ACT NOW", "#b91c1c", "#fee2e2"),
    "decision": ("DECISION", "#92400e", "#fef3c7"),
    "routine": ("QUEUED - silent", "#1f2937", "#e5e7eb"),
}

_CSS = """
body{font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;margin:0;background:#f3f4f6;color:#111827}
header{background:#111827;color:#fff;padding:18px 24px}
header h1{margin:0;font-size:20px}
header p{margin:4px 0 0;font-size:13px;color:#9ca3af}
main{max-width:760px;margin:24px auto;padding:0 16px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px 18px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.card.silent{opacity:.75}
.row1{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.badge{font-size:11px;font-weight:700;letter-spacing:.04em;padding:3px 8px;border-radius:999px}
.time{font-size:12px;color:#6b7280}
.who{font-size:14px;font-weight:600;margin:2px 0 6px}
.action{background:#f9fafb;border-left:3px solid #6b7280;padding:8px 12px;border-radius:6px;font-size:14px}
.why{font-size:12px;color:#6b7280;margin-top:6px}
.buttons button{font-size:13px;padding:6px 14px;border-radius:6px;border:1px solid #d1d5db;background:#fff;margin:10px 8px 0 0;cursor:pointer}
.buttons button.approve{background:#111827;color:#fff;border-color:#111827}
footer{max-width:760px;margin:8px auto 32px;padding:0 16px;font-size:11px;color:#9ca3af}
"""


def render_inbox(decisions: list[Decision], business_date: str) -> str:
    """Render the decision inbox HTML for one cycle."""
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>Decision Desk - morning inbox</title>",
        f"<style>{_CSS}</style></head><body>",
        "<header><h1>Decision Desk</h1>",
        f"<p>Morning decision inbox - {html.escape(business_date)} - "
        "approve, tweak, or decline; everything else was handled silently.</p></header><main>",
    ]
    for d in decisions:
        label, fg, bg = _BADGE[d.urgency.value]
        silent = " silent" if d.urgency is Urgency.ROUTINE else ""
        row = d.to_row()
        show_buttons = d.urgency.value in ("emergency", "decision")
        parts.append(
            f"<div class='card{silent}'>"
            f"<div class='row1'><span class='badge' style='color:{fg};background:{bg}'>{label}</span>"
            f"<span class='time'>{html.escape(row['time'])} - {html.escape(row['channel'])}</span></div>"
            f"<div class='who'>{html.escape(row['customer'])} - {html.escape(row['category'])}</div>"
            f"<div class='action'>{html.escape(row['proposed_action'])}</div>"
            f"<div class='why'>Why: {html.escape(row['reasoning'])}</div>"
            + (
                "<div class='buttons'><button class='approve'>Approve</button>"
                "<button>Tweak</button><button>Decline</button></div>"
                if show_buttons
                else ""
            )
            + "</div>"
        )
    parts.append(
        "</main><footer>Demo built on synthetic fixtures only. "
        "Decision Desk - Agents for Humans Hackathon entry - MIT license.</footer></body></html>"
    )
    return "".join(parts)


def write_inbox(decisions: list[Decision], path: str | Path, business_date: str) -> Path:
    path = Path(path)
    path.write_text(render_inbox(decisions, business_date), encoding="utf-8")
    return path
