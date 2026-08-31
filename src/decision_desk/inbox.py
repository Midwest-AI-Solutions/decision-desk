"""Decision inbox rendering (interactive HTML surface).

The inbox is the product's decision surface: every non-routine item shows the
drafted next action plus enough detail (script, quote range, proposed slot)
for the owner to approve, tweak, or decline in one pass. Approvals persist in
``localStorage`` so the demo keeps state across reloads without a backend;
routine items were handled silently and can be revealed on demand.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from .models import Decision, Urgency

_BADGE = {
    "emergency": ("ACT NOW", "#b91c1c", "#fee2e2"),
    "decision": ("DECISION", "#92400e", "#fef3c7"),
    "routine": ("QUEUED - silent", "#1f2937", "#e5e7eb"),
}

_ESCALATION_LABEL = {
    "emergency": "Callback script",
    "decision": "Reply script",
}

_CSS = """
body{font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;margin:0;background:#f3f4f6;color:#111827}
header{background:#111827;color:#fff;padding:18px 24px}
header h1{margin:0;font-size:20px}
header p{margin:4px 0 0;font-size:13px;color:#9ca3af}
main{max-width:760px;margin:24px auto;padding:0 16px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px 18px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,.04);transition:opacity .2s}
.card.silent{opacity:.75;display:none}
body.show-silent .card.silent{display:block}
.row1{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.badge{font-size:11px;font-weight:700;letter-spacing:.04em;padding:3px 8px;border-radius:999px}
.time{font-size:12px;color:#6b7280}
.who{font-size:14px;font-weight:600;margin:2px 0 6px}
.action{background:#f9fafb;border-left:3px solid #6b7280;padding:8px 12px;border-radius:6px;font-size:14px}
.details{margin-top:8px;font-size:13px;background:#f9fafb;border-radius:6px;padding:8px 12px;border:1px dashed #e5e7eb}
.details b{color:#374151}
.script{font-style:italic;color:#374151}
.quote{font-weight:700}
.why{font-size:12px;color:#6b7280;margin-top:6px}
.buttons{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.buttons button{font-size:13px;padding:6px 14px;border-radius:6px;border:1px solid #d1d5db;background:#fff;cursor:pointer}
.buttons button.approve{background:#111827;color:#fff;border-color:#111827}
.card[data-status] .buttons{display:none}
.statusline{display:none;margin-top:10px;font-size:13px;font-weight:600;padding:6px 10px;border-radius:6px}
.card[data-status] .statusline{display:block}
.card[data-status="approved"]{border-color:#16a34a}
.card[data-status="approved"] .statusline{background:#dcfce7;color:#166534}
.card[data-status="declined"] .statusline{background:#fee2e2;color:#991b1b}
.toolbar{display:flex;justify-content:space-between;align-items:center;max-width:760px;margin:18px auto 0;padding:0 16px;font-size:13px;color:#6b7280}
.toolbar button{font-size:12px;padding:4px 10px;border-radius:6px;border:1px solid #d1d5db;background:#fff;cursor:pointer}
footer{max-width:760px;margin:14px auto 32px;padding:0 16px;font-size:11px;color:#9ca3af}
"""

_JS = """
function ddKey(id){return 'decision-desk:' + window.ddDate + ':' + id;}
function ddApply(id,status){
  var card=document.getElementById(id);
  if(!card) return;
  if(status){card.setAttribute('data-status',status);card.querySelector('.statusline').textContent='You: '+status.charAt(0).toUpperCase()+status.slice(1)+'.';
    try{localStorage.setItem(ddKey(id),status);}catch(e){}}
  else{card.removeAttribute('data-status');try{localStorage.removeItem(ddKey(id));}catch(e){}}
}
function ddRestore(){
  var saved=0;
  document.querySelectorAll('.card').forEach(function(card){
    var status=null;
    try{status=localStorage.getItem(ddKey(card.id));}catch(e){}
    if(status){ddApply(card.id,status);saved++;}
  });
  var el=document.getElementById('dd-saved');
  if(el){el.textContent=saved?saved+' action'+(saved>1?'s':'')+' decided in earlier sessions':'';}
}
function ddResetAll(){
  document.querySelectorAll('.card').forEach(function(card){
    try{localStorage.removeItem(ddKey(card.id));}catch(e){}
    ddApply(card.id,null);
  });
  var el=document.getElementById('dd-saved');
  if(el){el.textContent='';}
}
function ddToggleSilent(){document.body.classList.toggle('show-silent');}
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('button[data-act]').forEach(function(btn){
    btn.addEventListener('click',function(){ddApply(btn.closest('.card').id,btn.getAttribute('data-act'));});
  });
  var reset=document.getElementById('dd-reset');
  if(reset){reset.addEventListener('click',ddResetAll);}
  var toggle=document.getElementById('dd-toggle-silent');
  if(toggle){toggle.addEventListener('click',ddToggleSilent);}
  ddRestore();
});
"""

_STATUSLINE_HTML = "<div class='statusline'></div>"


def _details_html(d: Decision) -> str:
    """Render escalation detail (script, quote range, slot, prep, answers)."""
    details = d.action_details
    if not details:
        return ""
    bits: list[str] = []
    if "quote_low" in details and "quote_high" in details:
        bits.append(
            "<span class='quote'>Quote range: "
            f"${html.escape(str(details['quote_low']))}-${html.escape(str(details['quote_high']))}</span>"
        )
    if details.get("slot"):
        bits.append(f"<b>Proposed slot:</b> {html.escape(str(details['slot']))}")
    if details.get("prep"):
        bits.append(f"<b>Prep:</b> {html.escape(str(details['prep']))}")
    if details.get("script"):
        label = _ESCALATION_LABEL.get(d.urgency.value, "Script")
        bits.append(
            f"<b>{label}:</b> <span class='script'>&ldquo;{html.escape(str(details['script']))}&rdquo;</span>"
        )
    if details.get("answer"):
        bits.append(f"<span class='script'>&ldquo;{html.escape(str(details['answer']))}&rdquo;</span>")
    if details.get("dispatch_note"):
        bits.append(f"<b>Dispatch:</b> {html.escape(str(details['dispatch_note']))}")
    if not bits:
        return ""
    return "<div class='details'>" + " &middot; ".join(bits) + "</div>"


def _card_id(d: Decision) -> str:
    safe = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in d.message.message_id)
    return f"card-{safe}"


def _interactivity(business_date: str) -> tuple[str, str]:
    """Return (style, body-extras) for the interactive inbox."""
    bootstrap = (
        "<script>window.ddDate="
        + json.dumps(business_date)
        + ";"
        + _JS
        + "</script>"
    )
    return _CSS, bootstrap


def render_inbox(decisions: list[Decision], business_date: str) -> str:
    """Render the interactive decision inbox HTML for one cycle."""
    counts = {u.value: sum(1 for d in decisions if d.urgency is u) for u in Urgency}
    interactive_style, body_extra = _interactivity(business_date)
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>Decision Desk - morning inbox</title>",
        f"<style>{interactive_style}</style></head><body>",
        "<header><h1>Decision Desk</h1>",
        f"<p>Morning decision inbox - {html.escape(business_date)} - "
        "approve, tweak, or decline; everything else was handled silently.</p></header>",
        "<div class='toolbar'>",
        f"<span>{counts.get('emergency', 0)} act-now &middot; "
        f"{counts.get('decision', 0)} decisions &middot; "
        f"{counts.get('routine', 0)} handled silently"
        " &middot; <button type='button' id='dd-toggle-silent'>show silent</button></span>",
        "<span id='dd-saved'></span>",
        "<button type='button' id='dd-reset'>reset demo</button>",
        "</div><main>",
    ]
    for d in decisions:
        label, fg, bg = _BADGE[d.urgency.value]
        silent = " silent" if d.urgency is Urgency.ROUTINE else ""
        row = d.to_row()
        interactive = d.urgency is not Urgency.ROUTINE
        buttons = (
            "<div class='buttons'>"
            "<button class='approve' data-act='approved'>Approve</button>"
            "<button data-act='tweaked'>Tweak</button>"
            "<button data-act='declined'>Decline</button>"
            "</div>"
            if interactive
            else ""
        )
        parts.append(
            f"<div class='card{silent}' id='{_card_id(d)}'>"
            f"<div class='row1'><span class='badge' style='color:{fg};background:{bg}'>{label}</span>"
            f"<span class='time'>{html.escape(row['time'])} - {html.escape(row['channel'])}</span></div>"
            f"<div class='who'>{html.escape(row['customer'])} - {html.escape(row['category'])}</div>"
            f"<div class='action'>{html.escape(row['proposed_action'])}</div>"
            f"{_details_html(d)}"
            f"<div class='why'>Why: {html.escape(row['reasoning'])}</div>"
            + _STATUSLINE_HTML
            + buttons
            + "</div>"
        )
    parts.append(
        "</main><footer>Demo built on synthetic fixtures only; approvals are stored "
        "locally in this browser. Decision Desk - Agents for Humans Hackathon entry - MIT license."
        f"{body_extra}</footer></body></html>"
    )
    return "".join(parts)


def write_inbox(decisions: list[Decision], path: str | Path, business_date: str) -> Path:
    path = Path(path)
    path.write_text(render_inbox(decisions, business_date), encoding="utf-8")
    return path
