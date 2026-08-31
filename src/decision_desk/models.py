"""Decision Desk data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Urgency(str, Enum):
    EMERGENCY = "emergency"
    DECISION = "decision"
    ROUTINE = "routine"


class Channel(str, Enum):
    VOICEMAIL = "voicemail"
    SMS = "sms"
    EMAIL = "email"


@dataclass
class MessageRecord:
    """A normalized after-hours intake message."""

    message_id: str
    channel: Channel
    customer_name: str
    contact: str
    received_at: datetime
    subject: str
    body: str

    @classmethod
    def from_dict(cls, raw: dict) -> "MessageRecord":
        return cls(
            message_id=str(raw["message_id"]),
            channel=Channel(raw["channel"]),
            customer_name=raw["customer_name"],
            contact=raw["contact"],
            received_at=datetime.fromisoformat(raw["received_at"]),
            subject=raw.get("subject", ""),
            body=raw["body"],
        )


@dataclass
class Decision:
    """A triaged item ready for the decision inbox."""

    message: MessageRecord
    urgency: Urgency
    category: str
    reasoning: str
    proposed_action: str
    action_details: dict = field(default_factory=dict)

    def to_row(self) -> dict:
        return {
            "urgency": self.urgency.value,
            "time": self.message.received_at.strftime("%H:%M"),
            "customer": self.message.customer_name,
            "channel": self.message.channel.value,
            "category": self.category,
            "reasoning": self.reasoning,
            "proposed_action": self.proposed_action,
        }
