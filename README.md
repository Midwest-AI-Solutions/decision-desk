# Decision Desk

**The after-hours job-capture agent for home-service businesses.**
Agents for Humans Hackathon (AWS x Devpost) entry - Professional Agents track.

Decision Desk is a background agent for small service businesses - plumbers,
HVAC crews, electricians - that turns after-hours voicemails, texts, and emails
into ready-to-approve **decisions** instead of a pile of morning callbacks.

While the shop is closed, Decision Desk quietly ingests new voicemail
transcripts and SMS/email intake, classifies what each one actually is (burst
pipe vs. routine invoice question), drafts the concrete next action (booking
slot, quote range, or answer), and surfaces only what genuinely needs a human:
money on the table or risk on the line. The owner wakes up to a short decision
inbox - approve, tweak, or decline - instead of a phone full of unknown
numbers.

Built with the [Strands Agents SDK](https://github.com/strands-agents) on
Amazon Bedrock, with each intake channel wrapped as a Strands tool, an
urgency/triage engine, a quote/booking drafter, and a decision-inbox surface.

> All data shipped in this repository is **synthetic**. No customer data is
> used or implied. Development assisted by AI coding tools (disclosed per
> hackathon rules).

## Why

The job that called at 9pm either gets booked by 7am or goes to the competitor
who answered. Owner-operators of home-service companies (1-20 techs) lose
after-hours jobs not because they don't care, but because nobody answers - and
playing back a voicemail pile at 7am is triage by exhaustion.

Decision Desk's design rule: **the agent stays silent until money is on the
table.** Routine questions get drafted answers and wait. Emergencies and
revenue decisions escalate immediately with a proposed action, so the human
makes one decision instead of ten.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run a demo cycle on the synthetic fixtures (no AWS credentials needed):
decision-desk --fixtures fixtures/scenarios.json

# Open the generated decision inbox:
open inbox.html   # macOS; otherwise open inbox.html in a browser
```

### Running with Amazon Bedrock (powered mode)

By default the agent runs with a deterministic `echo` provider so judges can
install and run the project with zero cloud setup. Setting
`DECISION_DESK_PROVIDER=bedrock` routes customer-facing routine-answer
phrasing through Amazon Bedrock via the Strands Agents SDK. Triage itself is
always deterministic (see ARCHITECTURE.md) - the LLM never decides safety or
escalation.

```bash
export DECISION_DESK_PROVIDER=bedrock
export AWS_PROFILE=your-profile      # standard AWS credentials; Builder ID works
decision-desk --fixtures fixtures/scenarios.json
```

## Deployment (Amazon Bedrock AgentCore)

`deployment/` contains the prepared AgentCore Runtime deployment entrypoint
and step-by-step runbook (`deployment/README.md`). The packaged path uses the
official AgentCore SDK (`bedrock-agentcore`) so the same pipeline can run as
a hosted agent; the local runtime (default) is the documented fallback and
needs no cloud setup. Deployment has **not** been executed yet - it requires
an owner-configured AWS credential path.

## Submission deliverables map

| Requirement (official rules) | Where |
|---|---|
| Strands Agents SDK agent | `src/decision_desk/agent.py` (3 tools, contract-pinned by tests) |
| Setup + run instructions (README) | this file |
| Architecture diagram | `ARCHITECTURE.md` + `architecture/architecture-diagram.svg` |
| MIT license | [LICENSE](LICENSE) |
| Demo video (<= 5 min) | script: `workspace/demo-video-script-v2.md` (recording pending) |
| Live demo artifact | `inbox.html` (interactive decision inbox) |
| AgentCore deployment | prepared in `deployment/` (optional, strengthens Technical Implementation) |

## Project layout

```
src/decision_desk/
  models.py     # MessageRecord / Decision dataclasses, urgency levels
  provider.py   # LLM provider abstraction (echo | bedrock)
  pipeline.py   # triage rules, action drafting, escalation criteria
  agent.py      # Strands Agents SDK integration (tools + agent factory)
  inbox.py      # decision-inbox rendering (interactive HTML surface; approvals
                #   persist in localStorage, silent items hidden by default)
  __main__.py   # CLI entry point
deployment/     # prepared Amazon Bedrock AgentCore Runtime entrypoint + runbook
fixtures/       # synthetic demo scenarios (burst pipe, no-heat, invoice)
tests/          # unit tests (pytest)
ARCHITECTURE.md # architecture diagram + design notes
```

## License

MIT - see [LICENSE](LICENSE).
