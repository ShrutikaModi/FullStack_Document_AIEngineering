from pathlib import Path

import structlog
from pydantic_ai import Agent, AgentRetries, ModelRetry, RunContext
from pydantic_ai.models import Model

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.assistant.tools import read_surrounding_chunks, search_filings
from app.grounding.validator import GroundingError, check_grounding

log = structlog.get_logger()

INSTRUCTIONS = (Path(__file__).parent / "instructions.md").read_text()
# How many times the model may fix a citation mistake before we give up.
OUTPUT_RETRIES = 2


def build_agent(model: Model) -> Agent[DocumentAgentDeps, GroundedAnswer]:
    agent = Agent(
        model,
        deps_type=DocumentAgentDeps,
        output_type=GroundedAnswer,
        instructions=INSTRUCTIONS,
        # The model chooses when to call these; PydanticAI runs them and returns the text.
        tools=[search_filings, read_surrounding_chunks],
        retries=AgentRetries(tools=1, output=OUTPUT_RETRIES),
    )

    @agent.output_validator
    def enforce_grounding(
        ctx: RunContext[DocumentAgentDeps], answer: GroundedAnswer
    ) -> GroundedAnswer:
        """Runs on every answer the model gives. A rule violation sends the model a
        correction; once the retries are used up PydanticAI raises, and the orchestrator
        (a later step) turns that into a controlled error instead of showing the answer."""
        try:
            return check_grounding(answer, ctx.deps.evidence.ids())
        except GroundingError as error:
            # Which rule the model breaks, and how often, is what tells us how to fix the
            # instructions (each retry is a whole extra model call).
            log.info("citation_retry", problems=error.problems)
            raise ModelRetry(
                "Your answer broke the citation rules: " + " ".join(error.problems)
            ) from error

    return agent
