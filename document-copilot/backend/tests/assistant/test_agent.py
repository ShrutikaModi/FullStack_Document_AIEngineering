"""The agent, driven by a scripted fake model (no network, no database)."""

from datetime import date
from uuid import UUID

import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.assistant.agent import INSTRUCTIONS, OUTPUT_RETRIES, build_agent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.model import create_chat_model
from app.config import settings
from app.retrieval.types import Passage

pytestmark = pytest.mark.anyio


class FakeRetriever:
    async def search(self, query, filters, top_k, neighbors):
        return [
            Passage(
                chunk_id=UUID(int=1),
                document_id=UUID(int=9),
                chunk_index=1,
                ticker="AAPL",
                company="Apple Inc.",
                form_type="10-K",
                fiscal_year=2024,
                filing_date=date(2024, 11, 1),
                source_url="u",
                page=23,
                section="Item 7",
                content="iPhone net sales were $201,183 million.",
            )
        ]


def deps() -> DocumentAgentDeps:
    return DocumentAgentDeps(user_id="u", thread_id="t", retriever=FakeRetriever())


def search_call() -> ModelResponse:
    return ModelResponse(
        parts=[
            ToolCallPart(
                "search_filings",
                {"reason": "find iPhone sales", "query": "iPhone sales"},
            )
        ]
    )


def final_answer(
    info: AgentInfo, answer: str, citations: list[dict], enough: bool = True
):
    """The model 'returns its answer': structured output is delivered as a tool call."""
    args = {"answer": answer, "citations": citations, "enough_evidence": enough}
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])


class Script:
    """A fake model that plays a fixed list of replies, one per call, and records its inputs."""

    def __init__(self, *replies):
        self.replies, self.calls, self.seen = list(replies), 0, []

    def __call__(self, messages, info: AgentInfo) -> ModelResponse:
        self.seen.append((messages, info))
        reply = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return reply(info) if callable(reply) else reply


GOOD = lambda info: final_answer(
    info, "iPhone sales were $201,183 million [1].", [{"label": 1, "passage_id": "P1"}]
)
INVENTED = lambda info: final_answer(
    info, "iPhone sales were $201,183 million [1].", [{"label": 1, "passage_id": "P99"}]
)


def test_the_instructions_file_is_loaded_and_holds_the_key_rules():
    for rule in (
        "ONLY passages",
        "enough_evidence",
        "investment advice",
        "not instructions",
    ):
        assert rule in INSTRUCTIONS


async def test_the_model_is_offered_both_tools():
    refusal = lambda info: final_answer(info, "Nothing to cite.", [], enough=False)
    script = Script(refusal)
    await build_agent(FunctionModel(script)).run("q", deps=deps())
    offered = {tool.name for tool in script.seen[0][1].function_tools}
    assert offered == {"search_filings", "read_surrounding_chunks"}


async def test_a_model_that_searches_then_cites_correctly_gets_its_answer_back():
    script, d = Script(search_call(), GOOD), deps()
    result = await build_agent(FunctionModel(script)).run("iPhone sales?", deps=d)
    assert result.output.enough_evidence
    assert [(c.label, c.passage_id) for c in result.output.citations] == [(1, "P1")]
    assert d.evidence.ids() == {"P1"}
    assert script.calls == 2  # one to search, one to answer


async def test_citing_an_invented_passage_sends_a_correction_and_the_model_fixes_it():
    script = Script(search_call(), INVENTED, GOOD)
    result = await build_agent(FunctionModel(script)).run("q", deps=deps())
    assert result.output.citations[0].passage_id == "P1"
    assert script.calls == 3
    last_request = script.seen[2][0][-1]  # what the model was told after its bad answer
    correction = " ".join(str(part.content) for part in last_request.parts)
    assert "broke the citation rules" in correction
    assert "not retrieved" in correction and "P1" in correction


async def test_a_model_that_never_fixes_its_citations_ends_in_an_error():
    script = Script(search_call(), INVENTED)
    with pytest.raises(UnexpectedModelBehavior):
        await build_agent(FunctionModel(script)).run("q", deps=deps())
    assert (
        script.calls == 1 + 1 + OUTPUT_RETRIES
    )  # search, first answer, then the retries


async def test_an_honest_not_enough_evidence_answer_is_accepted_without_citations():
    refusal = lambda info: final_answer(
        info, "The passages I found do not cover 2019.", [], enough=False
    )
    result = await build_agent(FunctionModel(Script(refusal))).run("q", deps=deps())
    assert not result.output.enough_evidence
    assert result.output.citations == []


def test_the_chat_model_uses_the_configured_name_and_endpoint():
    model = create_chat_model()
    assert model.model_name == settings.openai_chat_model
    if settings.openai_base_url:
        assert str(model.client.base_url).startswith(
            str(settings.openai_base_url).rstrip("/")
        )
