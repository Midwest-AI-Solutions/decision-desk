"""Strands Agents SDK integration.

Each pipeline step is exposed as a Strands tool so the agent owns the full
intake-to-inbox cycle. In ``echo`` mode (default) the cycle runs on the
deterministic pipeline so judges can run everything with zero cloud setup;
in ``bedrock`` mode the same tools run inside a real Strands agent backed by
Amazon Bedrock.
"""

from __future__ import annotations

import json
from typing import Any

try:  # Strands is a hard dependency for bedrock mode; soft for echo mode.
    from strands import Agent, tool

    STRANDS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without deps installed
    STRANDS_AVAILABLE = False

    def tool(fn):  # type: ignore[misc]
        """No-op stand-in so module import never fails in echo mode."""
        return fn


from .models import Decision, MessageRecord
from .pipeline import classify_urgency, draft_action, run_cycle, triage

FIXTURES_HINT = "pip install -e \".[dev]\" installs strands-agents"


@tool
def triage_message(message_json: str) -> str:
    """Classify one intake message and draft the next action.

    Args:
        message_json: JSON object with message_id, channel, customer_name,
            contact, received_at (ISO-8601), subject, body.

    Returns:
        JSON object with urgency, category, reasoning, and proposed_action.
    """
    decision = triage(MessageRecord.from_dict(json.loads(message_json)))
    return json.dumps(decision.to_row(), indent=2)


@tool
def draft_next_action(message_json: str) -> str:
    """Draft only the concrete next action for a message (no classification).

    Args:
        message_json: same schema as triage_message.

    Returns:
        JSON object with the proposed action and its details.
    """
    record = MessageRecord.from_dict(json.loads(message_json))
    urgency, category, _ = classify_urgency(record)
    action, details = draft_action(record, urgency, category)
    return json.dumps({"proposed_action": action, "details": details}, indent=2)


@tool
def run_intake_cycle(fixtures_json: str) -> str:
    """Run a full unattended intake cycle over a list of messages.

    Args:
        fixtures_json: JSON array of message objects (see triage_message).

    Returns:
        JSON array of inbox rows sorted by urgency then time.
    """
    messages = [MessageRecord.from_dict(raw) for raw in json.loads(fixtures_json)]
    decisions = run_cycle(messages)
    return json.dumps([d.to_row() for d in decisions], indent=2)


def build_agent(model: Any = None) -> "Agent":
    """Build the Strands agent that owns one intake cycle.

    Args:
        model: optional Strands model (e.g. BedrockModel). None uses the
            SDK's configured default model.
    """
    if not STRANDS_AVAILABLE:
        raise ImportError(f"strands-agents is not installed; run {FIXTURES_HINT}")
    system_prompt = (
        "You are Decision Desk, a background agent for a home-service business. "
        "Run the intake cycle over the given messages using the provided tools. "
        "Escalate only what needs a human decision: safety issues or money on "
        "the table. Routine questions get a drafted answer and stay silent."
    )
    return Agent(model=model, tools=[triage_message, draft_next_action, run_intake_cycle], system_prompt=system_prompt)


def pipeline_cycle(messages: list[MessageRecord]) -> list[Decision]:
    """Deterministic cycle used in echo mode (and by the CLI by default)."""
    return run_cycle(messages)
