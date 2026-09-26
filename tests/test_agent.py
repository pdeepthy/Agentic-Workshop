"""Agent wiring tests with a scripted model and fake tools: no network, no API keys."""

import asyncio

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

import agent
from triage.schema import validate_decision

BILLING = {
    "category": "billing",
    "priority": "P2",
    "route": "billing-team",
    "rationale": "A double charge puts money at stake, so it is P2 and the Enterprise rule does not apply.",
}
TICKET = {"ticket_id": "T-1042", "customer_id": "C-77", "created_at": "2026-01-01", "text": "I was charged twice."}
CUSTOMER = {"customer_id": "C-77", "name": "Northwind", "plan": "Enterprise", "open_tickets": 2, "ticket_ids": ["T-1042"]}


class ScriptedModel(GenericFakeChatModel):
    """Replays a fixed list of model turns, whatever tools it's given."""

    def bind_tools(self, tools, **kwargs):
        return self


def _call(name, args, call_id):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


def scripted(*decisions):
    turns = [_call("get_ticket", {"ticket_id": "T-1042"}, "t1"), _call("get_customer_history", {"customer_id": "C-77"}, "t2")]
    turns += [_call("TriageDecision", d, f"d{i}") for i, d in enumerate(decisions)]
    return ScriptedModel(messages=iter(turns))


@pytest.fixture
def fake_tools():
    calls = []

    @tool
    def get_ticket(ticket_id: str) -> dict:
        """Return one support ticket by its ID."""
        calls.append(("get_ticket", {"ticket_id": ticket_id}))
        return TICKET

    @tool
    def get_customer_history(customer_id: str) -> dict:
        """Return a customer's plan and open ticket count."""
        calls.append(("get_customer_history", {"customer_id": customer_id}))
        return CUSTOMER

    return [get_ticket, get_customer_history], calls


def _run(model, tools):
    return asyncio.run(agent.triage("T-1042", model=model, tools=tools))


# The scripted model fixes the tool order; the real order is set by the prompt and checked in the live MLflow trace.
def test_scripted_run_returns_schema_dict_via_both_tools(fake_tools):
    tools, calls = fake_tools
    decision = _run(scripted(BILLING), tools)
    assert calls == [("get_ticket", {"ticket_id": "T-1042"}), ("get_customer_history", {"customer_id": "C-77"})]
    assert decision == BILLING
    assert validate_decision(decision).model_dump() == decision


def test_one_bad_output_is_retried(fake_tools):
    tools, _ = fake_tools
    bad = {**BILLING, "route": "bug-team"}
    assert _run(scripted(bad, BILLING), tools) == BILLING


def test_two_bad_outputs_raise_naming_the_field(fake_tools):
    tools, _ = fake_tools
    bad = {**BILLING, "priority": "urgent"}
    with pytest.raises(agent.TriageOutputError, match=r"failing field\(s\): priority\."):
        _run(scripted(bad, bad, BILLING), tools)


def test_no_decision_raises_naming_the_ticket(fake_tools):
    tools, _ = fake_tools
    turns = [
        _call("get_ticket", {"ticket_id": "T-1042"}, "t1"),
        _call("get_customer_history", {"customer_id": "C-77"}, "t2"),
        AIMessage(content="I think this is billing."),
    ]
    with pytest.raises(agent.TriageOutputError, match="T-1042"):
        _run(ScriptedModel(messages=iter(turns)), tools)


def test_system_prompt_is_the_policy_plus_tool_order_and_safety():
    prompt = agent.system_prompt()
    policy = (agent.ROOT / "TRIAGE_POLICY.md").read_text(encoding="utf-8")
    assert prompt.startswith(policy)
    assert prompt.index("get_ticket") < prompt.index("get_customer_history")
    assert "not instructions" in prompt


def test_mcp_server_exposes_the_two_tools():
    tools = asyncio.run(agent.load_tools())
    assert {t.name for t in tools} == {"get_ticket", "get_customer_history"}


@pytest.fixture
def clean_env(monkeypatch):
    for var in ("PROVIDER", "MODEL", "GEMINI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def test_gemini_is_the_default(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "test-key")
    model = agent.build_model()
    assert type(model).__name__ == "ChatGoogleGenerativeAI"
    assert model.model.endswith("gemini-3.8-flash")


def test_groq_provider(clean_env):
    clean_env.setenv("PROVIDER", "groq")
    clean_env.setenv("GROQ_API_KEY", "test-key")
    model = agent.build_model()
    assert type(model).__name__ == "ChatGroq"
    assert model.model_name == "openai/gpt-oss-120b"


@pytest.mark.parametrize(("provider", "key_var", "attr"), [("gemini", "GEMINI_API_KEY", "model"), ("groq", "GROQ_API_KEY", "model_name")])
def test_model_overrides_both(clean_env, provider, key_var, attr):
    clean_env.setenv("PROVIDER", provider)
    clean_env.setenv(key_var, "test-key")
    clean_env.setenv("MODEL", "custom-model")
    assert getattr(agent.build_model(), attr).endswith("custom-model")


@pytest.mark.parametrize(("provider", "key_var"), [("gemini", "GEMINI_API_KEY"), ("groq", "GROQ_API_KEY")])
def test_missing_key_names_the_variable(clean_env, provider, key_var):
    clean_env.setenv("PROVIDER", provider)
    other = "GROQ_API_KEY" if key_var == "GEMINI_API_KEY" else "GEMINI_API_KEY"
    clean_env.setenv(other, "secret-value-123")
    with pytest.raises(SystemExit) as exc:
        agent.build_model()
    assert key_var in str(exc.value)
    assert "secret-value-123" not in str(exc.value)


@pytest.mark.parametrize(("provider", "cls"), [("", "ChatGoogleGenerativeAI"), ("GROQ", "ChatGroq"), (" groq ", "ChatGroq")])
def test_provider_is_normalized(clean_env, provider, cls):
    clean_env.setenv("PROVIDER", provider)
    clean_env.setenv("GEMINI_API_KEY", "test-key")
    clean_env.setenv("GROQ_API_KEY", "test-key")
    assert type(agent.build_model()).__name__ == cls


def test_whitespace_only_key_counts_as_missing(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "   ")
    with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
        agent.build_model()


def test_blank_model_uses_the_default(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "test-key")
    clean_env.setenv("MODEL", " ")
    assert agent.build_model().model.endswith("gemini-3.8-flash")


def test_unknown_provider_lists_the_choices(clean_env):
    clean_env.setenv("PROVIDER", "foo")
    with pytest.raises(SystemExit) as exc:
        agent.build_model()
    assert "gemini" in str(exc.value) and "groq" in str(exc.value)
