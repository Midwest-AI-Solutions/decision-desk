"""LLM provider abstraction.

Two modes, one pipeline:

- ``echo`` (default): a deterministic provider so the project installs and
  runs with zero cloud setup (hackathon rules require the project to be
  installable and runnable consistently by judges).
- ``bedrock``: Amazon Bedrock via the Strands Agents SDK model provider.

The provider never decides safety-critical urgency on its own; see
``pipeline.py`` for the deterministic-first triage design.
"""

from __future__ import annotations

import os
from typing import Protocol


class Summarizer(Protocol):
    """Minimal contract the pipeline needs from an LLM."""

    def complete(self, prompt: str) -> str: ...


class EchoProvider:
    """Deterministic stand-in: returns the prompt's focus sentence.

    Keeps the demo fully offline/reproducible. In echo mode the pipeline's
    rule-based triage output is used verbatim; the provider only supplies a
    fixed customer-facing phrasing template.
    """

    def complete(self, prompt: str) -> str:
        first_line = prompt.strip().splitlines()[0] if prompt.strip() else ""
        return f"[echo] {first_line}".strip()


class BedrockProvider:
    """Amazon Bedrock through the Strands Agents SDK."""

    def __init__(self, model_id: str | None = None, region_name: str | None = None):
        from strands.models import BedrockModel  # imported lazily; optional dep path

        self._model = BedrockModel(
            model_id=model_id
            or os.environ.get("DECISION_DESK_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0"),
            region_name=region_name or os.environ.get("AWS_REGION", "us-east-1"),
        )

    def complete(self, prompt: str) -> str:
        from strands import Agent

        agent = Agent(model=self._model)
        result = agent(prompt)
        return str(result)


def load_provider() -> Summarizer:
    """Load the provider named by ``DECISION_DESK_PROVIDER`` (echo|bedrock)."""
    name = os.environ.get("DECISION_DESK_PROVIDER", "echo").strip().lower()
    if name == "bedrock":
        return BedrockProvider()
    if name != "echo":
        raise ValueError(f"Unknown DECISION_DESK_PROVIDER: {name!r} (expected 'echo' or 'bedrock')")
    return EchoProvider()
