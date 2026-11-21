"""What the model actually receives. If a description here changes, the model's behaviour
changes, so these tests make such changes visible."""

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.assistant.agent import INSTRUCTIONS, build_agent
from app.assistant.deps import DocumentAgentDeps

pytestmark = pytest.mark.anyio


async def what_the_model_receives():
    """Run the agent once against a fake model that just records its request."""
    captured: dict = {}

    def spy(messages, info: AgentInfo) -> ModelResponse:
        captured["messages"], captured["info"] = messages, info
        refusal = {"answer": "x", "citations": [], "enough_evidence": False}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, refusal)])

    deps = DocumentAgentDeps(
        user_id="u", thread_id="t", retriever=None
    )  # never searched
    await build_agent(FunctionModel(spy)).run("q", deps=deps)
    return captured["messages"], captured["info"]


async def test_the_instructions_are_sent_with_the_request():
    messages, _ = await what_the_model_receives()
    assert (
        messages[0].instructions == INSTRUCTIONS.strip()
    )  # trailing newline is trimmed


async def test_each_tool_is_described_to_the_model_with_every_parameter():
    _, info = await what_the_model_receives()
    tools = {tool.name: tool for tool in info.function_tools}

    search = tools["search_filings"]
    assert "Use this before answering" in search.description
    parameters = search.parameters_json_schema["properties"]
    assert set(parameters) == {"reason", "query", "tickers", "fiscal_years", "section"}
    assert (
        "reason" in search.parameters_json_schema["required"]
    )  # the model must always give one
    assert all(spec.get("description") for spec in parameters.values())

    around = tools["read_surrounding_chunks"].parameters_json_schema["properties"]
    assert all(spec.get("description") for spec in around.values())


async def test_the_answer_format_tells_the_model_to_use_markers():
    _, info = await what_the_model_receives()
    output = info.output_tools[0]
    fields = output.parameters_json_schema["properties"]

    assert "[n] markers" in output.description
    assert "[1]" in fields["answer"]["description"]
    assert "passage_id" in fields["citations"]["description"]
    assert "False only when" in fields["enough_evidence"]["description"]


async def test_comments_and_other_docstrings_are_not_sent():
    messages, info = await what_the_model_receives()
    everything = repr(messages) + repr(info)
    assert "check_grounding" not in everything  # only our own code reads that docstring
    assert "EvidenceLog" not in everything
