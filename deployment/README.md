# AgentCore deployment runbook — Decision Desk (owner-executed)

Status: **PREPARED, NOT EXECUTED.** Everything here is a documented path;
none of it has been run. Deploying creates AWS resources (an account/state
change), so it is owner-gated exactly like the repo push and the Devpost
submit. The submission does NOT depend on it: the local runtime is the
documented fallback and AgentCore deployment is an optional scoring
strengthener ("Technical Implementation").

## What is prepared

- `deployment/agentcore_entrypoint.py` — `BedrockAgentCoreApp` wrapper around
  the existing pipeline (`run_cycle`); same JSON message schema as
  `fixtures/scenarios.json`; returns inbox rows + urgency counts.
- `deployment/requirements.txt` — container deps (`strands-agents`,
  `bedrock-agentcore`).
- This runbook.

## Prerequisites (owner)

1. AWS credentials available locally (the Builder ID created during
   registration; password lives only in the owner's Chrome/Keychain).
   Verify with `aws sts get-caller-identity`.
2. Model access in the target region if the powered (Bedrock) path will be
   exercised; the AgentCore pipeline path itself is deterministic.
3. The $50 promo credits were requested 2026-08-30 (confirmation receipt on
   the kanban card; ~3 business days processing). AgentCore Runtime is
   serverless pay-per-use; expected deployment testing cost is well inside
   the credit envelope. Verify credit balance before deploying.

## Steps (per official AWS AgentCore CLI docs)

The AgentCore CLI replaced the legacy `bedrock-agentcore-starter-toolkit`
(deprecated). Official get-started:
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html
Strands deployment guide: https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/python

```bash
# 1. Install the CLI
npm install -g @aws/agentcore

# 2. Local smoke test of the entrypoint (no cloud)
cd /Users/frameo/ai/decision-desk
pip install bedrock-agentcore
PYTHONPATH=src:deployment python3 deployment/agentcore_entrypoint.py &
#   -> local HTTP server; Ctrl+C when done

# 3. Configure + deploy (wizard prompts; region us-east-1 to match credits)
agentcore configure   # entrypoint: deployment/agentcore_entrypoint.py
agentcore deploy

# 4. Invoke the deployed agent
agentcore invoke '{"fixtures": [{"message_id": "t-1", "channel": "voicemail", "customer_name": "Demo", "contact": "+1-555-0100", "received_at": "2026-09-08T21:40:00", "subject": "Voicemail transcript", "body": "pipe burst, water everywhere"}]}'
# Expect: urgency=emergency, first-slot-07:30 action, counts {"emergency": 1}

# 5. Observe / clean up (see "Clean up" step of the AWS get-started page)
agentcore logs
```

After deploying: capture the runtime ARN + invocation receipt into the kanban
card, update README's deliverables map ("deployment/ prepared" -> deployed),
and record the actual spend against the credit envelope.

## Local fallback (current default, already judge-runnable)

```bash
pip install -e ".[dev]"
decision-desk --fixtures fixtures/scenarios.json   # offline echo mode
```

If the deployment hits friction (region, model access, credits not yet
landed), ship the submission on the local runtime and note the prepared
`deployment/` package in the Devpost description. This is the plan's
documented cut-line and meets every required deliverable.
