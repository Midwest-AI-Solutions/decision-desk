"""Triage pipeline: parse -> classify -> draft -> escalate.

Deterministic-first design: safety-critical and money-critical classification
is rule-based (auditable, testable, cloud-free). The LLM provider is only
consulted for routine-message answer drafting, and never overrides an
escalation.
"""

from __future__ import annotations

import re
from typing import Iterable

from .models import Channel, Decision, MessageRecord, Urgency

# --- triage rules -----------------------------------------------------------

SAFETY_KEYWORDS = (
    "burst",
    "flooding",
    "flood",
    "gas smell",
    "smell gas",
    "gas leak",
    "carbon monoxide",
    "co detector",
    "sparking",
    "smoke",
    "electrical fire",
    "no heat",
    "no power",
    "sewage",
    "water everywhere",
    "leaking badly",
    "shut off",
)

MONEY_KEYWORDS = (
    "quote",
    "estimate",
    "how much",
    "price",
    "pricing",
    "invoice",
    "payment",
    "book",
    "booking",
    "appointment",
    "schedule a",
)

ROUTINE_PATTERNS = (
    re.compile(r"hours", re.IGNORECASE),
    re.compile(r"what days are you", re.IGNORECASE),
    re.compile(r"do you serve", re.IGNORECASE),
    re.compile(r"are you open", re.IGNORECASE),
    re.compile(r"receipt", re.IGNORECASE),
    re.compile(r"invoice question", re.IGNORECASE),
)

# Informational money questions (invoice/receipt clarifications) are routine
# unless the message also asks for a commitment (booking, quote, pricing).
INFO_MONEY_PATTERNS = (
    re.compile(r"question about (the )?(invoice|receipt|#?\d+)", re.IGNORECASE),
    re.compile(r"(invoice|receipt) question", re.IGNORECASE),
)
STRONG_COMMITMENT_KEYWORDS = (
    "quote",
    "estimate",
    "how much",
    "price",
    "pricing",
    "book",
    "booking",
    "appointment",
    "schedule a",
    "come by",
    "come tomorrow",
)

BUSINESS_HOURS_START = 8  # 8:00 local
BUSINESS_HOURS_END = 18  # 18:00 local

QUOTED_JOBS = {
    "water heater replacement": (1450, 2400),
    "furnace no heat diagnostic": (180, 450),
    "panel inspection": (150, 350),
    "drain clearance": (220, 480),
}


def _hours_of(hour: int) -> bool:
    return BUSINESS_HOURS_START <= hour < BUSINESS_HOURS_END


def _matches(text: str, keywords: Iterable[str]) -> list[str]:
    lower = text.lower()
    return [kw for kw in keywords if kw in lower]


# --- pipeline steps (each is also exposed as a Strands tool in agent.py) ----


def classify_urgency(message: MessageRecord) -> tuple[Urgency, str, str]:
    """Classify one message. Returns (urgency, category, reasoning).

    Rules, in priority order:
    1. Safety keywords -> emergency, always. Off-hours strengthens it.
    2. Money/booking keywords -> decision (revenue or commitment at stake).
    3. Recognized routine patterns -> routine.
    4. Anything else -> decision (default-up: a human looks at unknown asks).
    """
    text = f"{message.subject}\n{message.body}"
    safety = _matches(text, SAFETY_KEYWORDS)
    money = _matches(text, MONEY_KEYWORDS)
    off_hours = not _hours_of(message.received_at.hour)

    if safety:
        level = Urgency.EMERGENCY if off_hours or money else Urgency.DECISION
        if level is Urgency.EMERGENCY:
            reason = f"safety keywords {safety}" + (" during closed hours" if off_hours else "")
            return level, "safety", reason
        return level, "safety", f"safety keywords {safety} during business hours; confirm severity"

    # Informational money questions (invoice/receipt clarifications) are
    # routine unless the message also asks for a real commitment.
    info_money = any(p.search(text) for p in INFO_MONEY_PATTERNS)
    if info_money and not _matches(text, STRONG_COMMITMENT_KEYWORDS):
        return (
            Urgency.ROUTINE,
            "info",
            "informational money question; no booking or pricing commitment requested",
        )

    if money:
        category = _category_from_text(text)
        reason = f"money/booking keywords {money[:3]}"
        if off_hours:
            reason += "; arrived after hours"
        return Urgency.DECISION, category, reason

    for pattern in ROUTINE_PATTERNS:
        if pattern.search(text):
            return Urgency.ROUTINE, "info", f"matches routine pattern {pattern.pattern!r}"

    return Urgency.DECISION, "unknown", "no rule matched; default-up to human review"


def _category_from_text(text: str) -> str:
    lower = text.lower()
    if "water heater" in lower:
        return "water heater replacement"
    if "no heat" in lower or "furnace" in lower:
        return "furnace no heat diagnostic"
    if "panel" in lower:
        return "panel inspection"
    if "drain" in lower or "clog" in lower:
        return "drain clearance"
    if "invoice" in lower:
        return "invoice question"
    return "general"


ROUTINE_NOTIFY = False

BUSINESS_NAME = "the shop"


def _emergency_guidance(text: str) -> str:
    """Category-appropriate emergency prep advice."""
    lower = text.lower()
    if any(k in lower for k in ("no heat", "furnace", "boiler")):
        return (
            "offer safe temporary heat (space heaters, never ovens/stoves); "
            "if you smell gas, leave and call the gas company"
        )
    if any(k in lower for k in ("spark", "smoke", "electrical", "power", "panel")):
        return "shut the affected breaker off if safely possible; keep everyone clear of the panel"
    if any(k in lower for k in ("gas", "carbon monoxide", "co detector")):
        return "leave the house now and call the gas company from outside"
    return "shut off water at the main if safely possible"


def draft_action(message: MessageRecord, urgency: Urgency, category: str) -> tuple[str, dict]:
    """Draft the concrete next action for a triaged message."""
    if urgency is Urgency.EMERGENCY:
        guidance = _emergency_guidance(f"{message.subject}\n{message.body}")
        details = {
            "slot": "first slot tomorrow 07:30",
            "prep": guidance,
            "dispatch_note": "possible active damage; call customer back now",
        }
        action = (
            f"Call {message.customer_name} back NOW ({message.contact}); "
            f"offer first slot tomorrow 07:30; advise: {guidance}."
        )
        return action, details

    if urgency is Urgency.DECISION:
        if category in QUOTED_JOBS:
            low, high = QUOTED_JOBS[category]
            details = {
                "quote_low": low,
                "quote_high": high,
                "slot": "tomorrow 10:00 or 13:00",
                "script": (
                    f"Hi {message.customer_name}, this is {BUSINESS_NAME}. "
                    f"For {category} we're typically {low}-{high} dollars; "
                    f"we could come by tomorrow 10:00 or 13:00."
                ),
            }
            action = (
                f"Send quote {low}-{high} USD for {category} and offer tomorrow 10:00 or 13:00."
            )
            return action, details
        details = {"script": f"Hi {message.customer_name}, thanks for reaching out - calling you back in the morning."}
        action = f"Call {message.customer_name} back in the morning; ask clarifying questions first."
        return action, details

    # routine
    details = {
        "answer": (
            "Thanks for reaching out! We're open 8am-6pm weekdays and 9am-1pm "
            "Saturdays. We'll follow up with specifics first thing tomorrow."
        ),
        "notify": False,
    }
    action = "Auto-queue the drafted answer; no interruption to the owner."
    return action, details


BUSINESS_NAME = "the shop"


def triage(message: MessageRecord) -> Decision:
    """Run one message through the full pipeline."""
    urgency, category, reasoning = classify_urgency(message)
    action, details = draft_action(message, urgency, category)
    return Decision(
        message=message,
        urgency=urgency,
        category=category,
        reasoning=reasoning,
        proposed_action=action,
        action_details=details,
    )


def run_cycle(messages: Iterable[MessageRecord]) -> list[Decision]:
    """Run one unattended intake cycle. Deterministic order: by urgency, then time."""
    decisions = [triage(m) for m in messages]
    order = {Urgency.EMERGENCY: 0, Urgency.DECISION: 1, Urgency.ROUTINE: 2}
    decisions.sort(key=lambda d: (order[d.urgency], d.message.received_at))
    return decisions
