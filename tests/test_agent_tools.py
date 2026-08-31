"""Tests for the Strands tool wrappers in agent.py (JSON contract).

These run in echo mode (strands not installed): the ``tool`` decorator is a
no-op passthrough, so each wrapper is callable directly. The contract under
test is the JSON schema the Strands agent (and judges) will consume.
"""

from __future__ import annotations

import json

import pytest

from decision_desk.agent import (
    draft_next_action,
    run_intake_cycle,
    triage_message,
)

RAW = {
    "message_id": "t-1",
    "channel": "voicemail",
    "customer_name": "Test Customer",
    "contact": "+1-555-0100",
    "received_at": "2026-09-08T21:40:00",
    "subject": "Voicemail transcript",
    "body": "pipe burst, water everywhere",
}


class TestTriageMessage:
    def test_returns_valid_json_with_expected_keys(self):
        out = json.loads(triage_message(json.dumps(RAW)))
        assert set(out) == {
            "urgency",
            "time",
            "customer",
            "channel",
            "category",
            "reasoning",
            "proposed_action",
        }
        assert out["urgency"] == "emergency"
        assert out["customer"] == "Test Customer"

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            triage_message("{not json")


class TestDraftNextAction:
    def test_quote_request_returns_action_and_details(self):
        raw = dict(RAW, body="how much for a water heater replacement?")
        out = json.loads(draft_next_action(json.dumps(raw)))
        assert set(out) == {"proposed_action", "details"}
        assert out["details"]["quote_low"] < out["details"]["quote_high"]

    def test_schema_violation_raises(self):
        with pytest.raises(KeyError):
            draft_next_action(json.dumps({"message_id": "x"}))


class TestRunIntakeCycle:
    def test_full_cycle_sorted_and_complete(self):
        fixtures = [
            RAW,
            dict(RAW, message_id="t-2", body="what are your hours?"),
        ]
        rows = json.loads(run_intake_cycle(json.dumps(fixtures)))
        assert [r["urgency"] for r in rows] == ["emergency", "routine"]
        assert len(rows) == 2

    def test_empty_array_returns_empty_list(self):
        assert json.loads(run_intake_cycle("[]")) == []
