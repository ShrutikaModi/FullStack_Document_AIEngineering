"""Try a conversation against the real agent, with memory, from the terminal.

Run from backend/ (each quoted text is one question, asked in order):

    uv run python -m evals.try_conversation "First question" "A follow-up question"

It needs the real database and Azure key, so it makes real (small) model calls. Nothing is
saved: the conversation lives only for this run. For every question it prints the memory the
agent was given, the searches the model chose to run, and the validated answer with the
page and section of each cited passage.
"""

import asyncio
import sys

from pydantic_ai.messages import ToolCallPart

from app.assistant.agent import build_agent
from app.assistant.deps import MAX_SEARCHES, DocumentAgentDeps
from app.assistant.model import create_chat_model
from app.chat.messages import history_for_agent
from app.database.engine import create_db_engine
from app.openai_client import create_async_openai_client
from app.retrieval.retriever import DocumentRetriever, openai_embedder

DEFAULT_QUESTIONS = [
    "How did Apple's iPhone net sales change from fiscal 2022 to fiscal 2024?",
    "And what about Services?",
]


async def main(questions: list[str]) -> None:
    engine = create_db_engine()
    retriever = DocumentRetriever(engine, openai_embedder(create_async_openai_client()))
    agent = build_agent(create_chat_model())
    stored: list[dict] = []  # stands in for the chat_messages table, oldest first

    for number, question in enumerate(questions, start=1):
        print(f"\n{'=' * 78}\nQUESTION {number}: {question}")
        history = history_for_agent(stored)
        print(f"memory given to the agent: {len(history)} earlier message(s)")
        for message in history:
            who = "you" if message.kind == "request" else "bot"
            print(f"   {who}: {str(message.parts[0].content)[:100]!r}")

        deps = DocumentAgentDeps(
            "demo-user", "demo-thread", retriever
        )  # fresh evidence per question
        result = await agent.run(question, deps=deps, message_history=history)

        print("searches the model chose to run:")
        for message in result.new_messages():
            for part in message.parts:
                if isinstance(part, ToolCallPart) and part.tool_name != "final_result":
                    args = part.args_as_dict()
                    why = args.pop("reason", "(none given)")
                    print(f"   {part.tool_name}({args})\n      why: {why}")

        answer = result.output
        print(f"\nANSWER (enough_evidence={answer.enough_evidence}):\n{answer.answer}")
        for citation in answer.citations:
            p = deps.evidence.get(citation.passage_id)
            print(
                f"   [{citation.label}] {citation.passage_id} = {p.company} FY{p.fiscal_year}, "
                f"page {p.page}, {p.section}"
            )
        usage = result.usage
        print(
            f"(searches used {MAX_SEARCHES - deps.searches_left}, model requests {usage.requests}, "
            f"tokens {usage.input_tokens} in / {usage.output_tokens} out)"
        )

        stored += [
            {"role": "user", "parts": [{"type": "text", "text": question}]},
            {"role": "assistant", "parts": [{"type": "text", "text": answer.answer}]},
        ]
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or DEFAULT_QUESTIONS))
