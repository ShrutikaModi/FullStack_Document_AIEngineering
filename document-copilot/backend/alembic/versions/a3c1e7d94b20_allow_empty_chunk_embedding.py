"""allow empty chunk embedding

Revision ID: a3c1e7d94b20
Revises: 5466618e1457
Create Date: 2026-11-17

Chunks are loaded before their embeddings are created, so the column must accept NULL
until the embedding step fills it in. The HNSW index skips rows without a vector.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a3c1e7d94b20"
down_revision: Union[str, Sequence[str], None] = "5466618e1457"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("alter table document_chunks alter column embedding drop not null")


def downgrade() -> None:
    op.execute("alter table document_chunks alter column embedding set not null")
