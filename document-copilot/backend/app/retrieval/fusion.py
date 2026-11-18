from collections import defaultdict
from uuid import UUID

# 60 is the value from the original RRF paper; a larger k flattens the difference
# between rank 1 and rank 10, a smaller k rewards the very top ranks more.
RRF_K = 60


def reciprocal_rank_fusion(
    rankings: list[list[UUID]], k: int = RRF_K
) -> list[tuple[UUID, float]]:
    """Merge several best-first lists of chunk ids into one list, best first.

    Each list gives a chunk 1 / (k + rank) points (rank starts at 1) and the points add
    up, so a chunk found by both searches beats one found by only one. Only the rank is
    used, never the raw score: cosine similarity and full-text scores are on different
    scales and can't be compared directly.
    """
    scores: dict[UUID, float] = defaultdict(float)
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] += 1.0 / (k + rank)
    # Equal scores are ordered by id so the result is the same on every run.
    return sorted(scores.items(), key=lambda item: (-item[1], str(item[0])))
