"""Tests for deployment/agentcore_entrypoint.py (echo-mode logic only).

The real ``bedrock_agentcore`` package is an optional deployment dependency
(not installed in the judge environment), so these tests inject a minimal
stand-in module to exercise OUR wrapper contract: payload validation,
pipeline reuse, and row/count shape. Cloud deployment itself is owner-run
(see deployment/README.md) and is not exercised here.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_entrypoint():
    """Import the entrypoint with a stand-in bedrock_agentcore module."""
    sdk = types.ModuleType("bedrock_agentcore")
    runtime = types.ModuleType("bedrock_agentcore.runtime")

    class BedrockAgentCoreApp:  # minimal stand-in of the real app wrapper
        def entrypoint(self, fn):
            return fn

        def run(self):  # pragma: no cover - never started in tests
            raise RuntimeError("app.run() must not be called in tests")

    runtime.BedrockAgentCoreApp = BedrockAgentCoreApp
    sdk.runtime = runtime
    saved = {k: v for k, v in sys.modules.items() if k.startswith("bedrock_agentcore")}
    sys.modules["bedrock_agentcore"] = sdk
    sys.modules["bedrock_agentcore.runtime"] = runtime
    try:
        spec = importlib.util.spec_from_file_location(
            "agentcore_entrypoint", REPO_ROOT / "deployment" / "agentcore_entrypoint.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for key in ("bedrock_agentcore", "bedrock_agentcore.runtime"):
            sys.modules.pop(key, None)
        sys.modules.update(saved)


FIXTURES = json.loads((REPO_ROOT / "fixtures" / "scenarios.json").read_text(encoding="utf-8"))


class TestInvoke:
    def test_full_cycle_counts_and_rows(self):
        module = _load_entrypoint()
        out = json.loads(module.invoke({"fixtures": FIXTURES}))
        assert out["counts"] == {"emergency": 2, "decision": 2, "routine": 2}
        assert len(out["inbox_rows"]) == 6
        assert out["inbox_rows"][0]["urgency"] == "emergency"

    def test_missing_fixtures_key_returns_error(self):
        module = _load_entrypoint()
        out = json.loads(module.invoke({}))
        assert "error" in out

    def test_bad_schema_returns_error_json(self):
        module = _load_entrypoint()
        out = json.loads(module.invoke({"fixtures": [{"message_id": "x"}]}))
        assert "error" in out
