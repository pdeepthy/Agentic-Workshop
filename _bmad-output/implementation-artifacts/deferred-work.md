# Deferred work

- source_spec: `_bmad-output/specs/spec-epic-2/stories/1-the-triage-agent.md`
  summary: An unknown ticket ID (e.g. `run_agent.py T-9999`) may produce an invented, schema-valid decision instead of an error, because nothing checks that `get_ticket` succeeded before the decision is returned.
  evidence: Unverified, medium if true. `get_ticket` raises for an unknown ID and the error goes back to the model as a tool message, and `triage()` never checks for it. The live check hit Gemini's 429 rate limit. To settle it, run `uv run python run_agent.py T-9999` once the quota resets and see whether a decision is printed.
- source_spec: `_bmad-output/specs/spec-epic-2/stories/1-the-triage-agent.md`
  summary: `run_agent.py` catches every `ImportError` from `from agent import triage` and reports "The agent isn't built yet", which hides a real missing dependency such as `langchain_mcp_adapters`.
  evidence: This existed before story 2.1, at `run_agent.py:45-48`. It shows up now that `agent.py` exists. The fix is to re-raise unless `ModuleNotFoundError.name == "agent"`.
