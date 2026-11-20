from dataclasses import dataclass, field
from uuid import UUID

from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import Passage

# Each search returns about 8 passages (roughly 4,000 tokens). Capping the searches per
# question keeps cost and waiting time bounded, even if the model keeps wanting "one more".
MAX_SEARCHES = 6


class EvidenceLog:
    """Every passage shown to the model during ONE question, each with a short id.

    The model cites these ids (P1, P2, ...). Because the log starts empty for every
    question, the model can only cite what it was shown in this turn.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Passage] = {}
        self._id_of_chunk: dict[UUID, str] = {}

    def add(self, passage: Passage) -> str:
        """Record a passage and return its id. The same chunk always gets the same id."""
        existing = self._id_of_chunk.get(passage.chunk_id)
        if existing:
            return existing
        passage_id = f"P{len(self._by_id) + 1}"
        self._by_id[passage_id] = passage
        self._id_of_chunk[passage.chunk_id] = passage_id
        return passage_id

    def get(self, passage_id: str) -> Passage | None:
        return self._by_id.get(passage_id)

    def ids(self) -> set[str]:
        """What may be cited. This is what check_grounding() receives."""
        return set(self._by_id)

    def passages(self) -> dict[str, Passage]:
        return dict(self._by_id)


@dataclass
class DocumentAgentDeps:
    """Everything the agent's tools need for one question. Created fresh per question."""

    user_id: str
    thread_id: str
    retriever: DocumentRetriever
    evidence: EvidenceLog = field(default_factory=EvidenceLog)
    searches_left: int = MAX_SEARCHES
