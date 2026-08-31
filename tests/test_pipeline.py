"""Decision Desk pipeline tests. All fixtures are synthetic."""

from __future__ import annotations

from datetime import datetime

import pytest

from decision_desk.inbox import render_inbox
from decision_desk.models import Channel, MessageRecord, Urgency
from decision_desk.pipeline import classify_urgency, run_cycle, triage


def msg(**overrides) -> MessageRecord:
    base = dict(
        message_id="m-test",
        channel="sms",
        customer_name="Test Customer",
        contact="+1-555-0100",
        received_at="2026-09-08T22:00:00",
        subject="",
        body="",
    )
    base.update(overrides)
    base["received_at"] = (
        base["received_at"] if isinstance(base["received_at"], datetime) else datetime.fromisoformat(base["received_at"])
    )
    base["channel"] = Channel(base["channel"])
    return MessageRecord(**base)


class TestClassifyUrgency:
    def test_burst_pipe_off_hours_is_emergency(self):
        urgency, category, reasoning = classify_urgency(msg(body="Pipe burst, water everywhere", received_at="2026-09-08T22:00:00"))
        assert urgency is Urgency.EMERGENCY
        assert category == "safety"
        assert "closed hours" in reasoning

    def test_gas_smell_is_emergency_even_during_hours(self):
        urgency, category, _ = classify_urgency(msg(body="I smell gas near the stove", received_at="2026-09-08T10:00:00"))
        assert urgency is Urgency.DECISION  # safety during hours: confirm severity with human
        assert category == "safety"

    def test_no_heat_with_baby_off_hours_is_emergency(self):
        urgency, _, reasoning = classify_urgency(msg(body="Furnace gives no heat, freezing tonight", received_at="2026-09-08T23:30:00"))
        assert urgency is Urgency.EMERGENCY
        assert "no heat" in reasoning

    def test_quote_request_off_hours_is_decision(self):
        urgency, category, reasoning = classify_urgency(msg(body="How much to replace a water heater?", received_at="2026-09-08T20:00:00"))
        assert urgency is Urgency.DECISION
        assert category == "water heater replacement"
        assert "after hours" in reasoning

    def test_invoice_question_is_routine(self):
        urgency, category, _ = classify_urgency(msg(subject="Invoice question", body="Question about invoice #4471"))
        assert urgency is Urgency.ROUTINE
        assert category == "info"

    def test_unmatched_message_defaults_up_to_decision(self):
        urgency, category, reasoning = classify_urgency(msg(body="My neighbor mentioned you do odd jobs"))
        assert urgency is Urgency.DECISION
        assert category == "unknown"
        assert "default-up" in reasoning


class TestDraftAction:
    def test_emergency_action_has_callback_and_slot(self):
        m = msg(customer_name="Dana", body="burst pipe")
        decision = triage(m)
        assert "Call Dana back NOW" in decision.proposed_action
        assert decision.action_details["slot"]

    def test_emergency_advice_matches_trade(self):
        water = triage(msg(customer_name="D", body="pipe burst, water everywhere"))
        heat = triage(msg(customer_name="M", body="furnace gives no heat, freezing tonight"))
        electrical = triage(msg(customer_name="E", body="outlet sparking, burning smell"))
        assert "water" in water.action_details["prep"]
        assert "heat" in heat.action_details["prep"]
        assert "breaker" in electrical.action_details["prep"]

    def test_quote_decision_has_range(self):
        m = msg(customer_name="Tom", body="water heater replacement price?")
        decision = triage(m)
        low = decision.action_details["quote_low"]
        high = decision.action_details["quote_high"]
        assert 0 < low < high
        assert str(low) in decision.proposed_action and str(high) in decision.proposed_action

    def test_routine_action_is_silent(self):
        m = msg(subject="hours", body="what are your hours?")
        decision = triage(m)
        assert decision.urgency is Urgency.ROUTINE
        assert decision.action_details["notify"] is False


class TestRunCycle:
    def test_ordering_emergency_first_routine_last(self):
        fixtures = [
            msg(message_id="a", body="what are your hours?"),
            msg(message_id="b", body="quote for drain clearance?"),
            msg(message_id="c", body="pipe burst, flooding"),
        ]
        decisions = run_cycle(fixtures)
        assert [d.message.message_id for d in decisions] == ["c", "b", "a"]

    def test_empty_cycle_is_empty(self):
        assert run_cycle([]) == []


class TestInbox:
    def test_render_contains_rows_and_escapes_html(self):
        evil = msg(customer_name="<script>x</script>", body="quote for drain clearance?")
        html = render_inbox([triage(evil)], business_date="2026-09-09")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "DECISION" in html

    def test_render_orders_emergency_first(self):
        decisions = run_cycle(
            [
                msg(message_id="a", body="what are your hours?"),
                msg(message_id="c", body="pipe burst, flooding"),
            ]
        )
        html = render_inbox(decisions, business_date="2026-09-09")
        assert html.index("ACT NOW") < html.index("QUEUED")


def test_models_roundtrip():
    raw = {
        "message_id": "vm-1",
        "channel": "voicemail",
        "customer_name": "A",
        "contact": "c",
        "received_at": "2026-09-08T21:00:00",
        "subject": "s",
        "body": "b",
    }
    record = MessageRecord.from_dict(raw)
    assert record.channel is Channel.VOICEMAIL
    assert record.received_at.hour == 21
