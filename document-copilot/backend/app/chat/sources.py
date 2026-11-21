"""What the analyst sees under an answer: one source card per citation.

Every field comes from our own database row for the chunk, never from the model. The model
only chose WHICH passage to cite (an id such as P3); the filing, page and excerpt shown are
read from the stored passage, so the model cannot alter what a source says.
"""

from typing import Any

from app.assistant.deps import EvidenceLog
from app.assistant.outputs import GroundedAnswer

# Long chunks are shortened in the payload; the full text stays in the database.
MAX_EXCERPT_CHARS = 1500


def build_sources(
    answer: GroundedAnswer, evidence: EvidenceLog
) -> list[dict[str, Any]]:
    """One card per citation, in [1], [2], ... order. Ids were already checked by the
    grounding validator, so every lookup succeeds."""
    sources = []
    for citation in answer.citations:
        passage = evidence.get(citation.passage_id)
        if passage is None:  # cannot happen after validation; never invent a card
            continue
        sources.append(
            {
                "label": citation.label,
                "chunkId": str(passage.chunk_id),
                "company": passage.company,
                "ticker": passage.ticker,
                "formType": passage.form_type,
                "fiscalYear": passage.fiscal_year,
                "filingDate": passage.filing_date.isoformat(),
                "page": passage.page,
                "section": passage.section,
                "excerpt": passage.content[:MAX_EXCERPT_CHARS],
                "sourceUrl": passage.source_url,
            }
        )
    return sources
