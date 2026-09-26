"""Triage one support ticket with the agent and print the decision.

Run `uv run python run_agent.py --help` for usage.
"""

import argparse
import asyncio
import json

import mlflow
from dotenv import load_dotenv

EPILOG = """\
output:
  JSON with category, priority (P1-P4), route and a one-sentence rationale.

environment (read from .env):
  GEMINI_API_KEY   key for the default provider (Gemini)
  MODEL            model name (default: gemini-3.8-flash)
  PROVIDER         set to "groq" to use Groq instead (needs GROQ_API_KEY)

tracing:
  Every run is logged to MLflow (sqlite:///mlflow.db, experiment "triage-agent").

examples:
  uv run python run_agent.py T-1042
  PROVIDER=groq uv run python run_agent.py T-1099
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="uv run python run_agent.py",
        description="Triage one support ticket with the agent and print the decision as JSON.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("ticket_id", help="ticket to triage, e.g. T-1042 (from seed/tickets.csv)")
    ticket_id = parser.parse_args().ticket_id

    load_dotenv()
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("triage-agent")
    mlflow.langchain.autolog()

    try:
        from agent import triage
    except ImportError:
        raise SystemExit("The agent isn't built yet. That's Epic 2: _bmad-output/specs/spec-epic-2/SPEC.md")

    with mlflow.start_span(name="triage", span_type="AGENT") as span:
        span.set_inputs({"ticket_id": ticket_id})
        decision = asyncio.run(triage(ticket_id))
        span.set_outputs(decision)
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
