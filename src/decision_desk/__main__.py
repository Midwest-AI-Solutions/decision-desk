"""Decision Desk CLI - run one unattended intake cycle and open the inbox."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from .inbox import write_inbox
from .models import MessageRecord
from .pipeline import run_cycle

DEFAULT_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "scenarios.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="decision-desk",
        description="Run one after-hours intake cycle and render the decision inbox.",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="Path to a JSON array of intake messages (default: bundled synthetic fixtures).",
    )
    parser.add_argument(
        "--inbox-out",
        type=Path,
        default=Path("inbox.html"),
        help="Where to write the decision inbox HTML (default: ./inbox.html).",
    )
    parser.add_argument("--json", action="store_true", help="Print inbox rows as JSON instead of a summary.")
    args = parser.parse_args(argv)

    raw = json.loads(args.fixtures.read_text(encoding="utf-8"))
    messages = [MessageRecord.from_dict(item) for item in raw]
    decisions = run_cycle(messages)
    out = write_inbox(decisions, args.inbox_out, business_date=messages[0].received_at.date().isoformat() if messages else "")

    counts = Counter(d.urgency.value for d in decisions)
    if args.json:
        print(json.dumps([d.to_row() for d in decisions], indent=2))
    else:
        print(f"Decision Desk processed {len(decisions)} messages:")
        print(f"  emergencies surfaced : {counts.get('emergency', 0)}")
        print(f"  decisions to approve : {counts.get('decision', 0)}")
        print(f"  handled silently     : {counts.get('routine', 0)}")
        print(f"Inbox written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
