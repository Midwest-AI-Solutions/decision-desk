"""Amazon Bedrock AgentCore Runtime entrypoint for Decision Desk.

Wraps the existing Decision Desk pipeline as an AgentCore-hosted agent.
The triage pipeline itself is unchanged and deterministic-first; hosting it
on AgentCore packages the same intake-to-inbox cycle as a serverless runtime
endpoint.

Local smoke test (no cloud):
    PYTHONPATH=..:. python3 agentcore_entrypoint.py   # starts the HTTP server
    # Ctrl+C to stop; the local `decision-desk` CLI remains the default path.

Deployment is NOT executed from this repo unattended - see README.md in this
directory for the owner-run deployment runbook.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make `decision_desk` importable when this file is run from deployment/
# (works both in the AgentCore container and for local smoke tests).
_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (_REPO_ROOT, _REPO_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from bedrock_agentcore.runtime import BedrockAgentCoreApp  # noqa: E402

from decision_desk.models import MessageRecord  # noqa: E402
from decision_desk.pipeline import run_cycle  # noqa: E402

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> str:
    """Run one unattended intake cycle over messages in the payload.

    Expected payload:
        {"fixtures": [ {message...}, ... ]}   # same schema as fixtures/scenarios.json

    Returns:
        JSON string: {"inbox_rows": [...], "counts": {"emergency": n, "decision": n, "routine": n}}
    """
    raw = payload.get("fixtures")
    if not isinstance(raw, list):
        return json.dumps({"error": "payload must contain a 'fixtures' array of messages"})
    try:
        messages = [MessageRecord.from_dict(item) for item in raw]
    except (KeyError, TypeError, ValueError) as exc:
        return json.dumps({"error": f"invalid message schema: {exc}"})

    # Deterministic-first: the hosted runtime uses the same rules as local
    # echo mode. Powered (Bedrock) phrasing stays a local-CLI path for now.
    decisions = run_cycle(messages)

    counts: dict[str, int] = {}
    for d in decisions:
        counts[d.urgency.value] = counts.get(d.urgency.value, 0) + 1
    return json.dumps({"inbox_rows": [d.to_row() for d in decisions], "counts": counts})


if __name__ == "__main__":
    app.run()
