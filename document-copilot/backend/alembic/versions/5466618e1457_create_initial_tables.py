"""create initial tables

Revision ID: 5466618e1457
Revises: 
Create Date: 2026-11-15 21:10:10.406967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5466618e1457'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Reviewed by hand; extension and security rules are added below the tables.
    op.execute("create extension if not exists vector")

    op.create_table('source_documents',
    sa.Column('ticker', sa.String(), nullable=False),
    sa.Column('company', sa.String(), nullable=False),
    sa.Column('form_type', sa.String(), nullable=False),
    sa.Column('fiscal_year', sa.Integer(), nullable=False),
    sa.Column('filing_date', sa.Date(), nullable=False),
    sa.Column('accession_number', sa.String(), nullable=False),
    sa.Column('source_url', sa.String(), nullable=False),
    sa.Column('markdown', sa.String(), nullable=False),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_source_documents')),
    sa.UniqueConstraint('accession_number', name=op.f('uq_source_documents_accession_number'))
    )
    op.create_table('document_chunks',
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('page', sa.Integer(), nullable=True),
    sa.Column('section', sa.String(), nullable=True),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('token_count', sa.Integer(), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=False),
    sa.Column('search_vector', postgresql.TSVECTOR(), sa.Computed("to_tsvector('english', content)", persisted=True), nullable=False),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['source_documents.id'], name=op.f('fk_document_chunks_document_id_source_documents'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_document_chunks')),
    sa.UniqueConstraint('document_id', 'chunk_index', name=op.f('uq_document_chunks_document_id'))
    )
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)
    op.create_index('ix_document_chunks_embedding', 'document_chunks', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('ix_document_chunks_metadata', 'document_chunks', ['metadata'], unique=False, postgresql_using='gin')
    op.create_index('ix_document_chunks_search_vector', 'document_chunks', ['search_vector'], unique=False, postgresql_using='gin')
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['auth.users.id'], name=op.f('fk_users_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_table('chat_threads',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_chat_threads_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_chat_threads'))
    )
    op.create_index(op.f('ix_chat_threads_user_id'), 'chat_threads', ['user_id'], unique=False)
    op.create_table('chat_messages',
    sa.Column('thread_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('parts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('usage', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role in ('user', 'assistant')", name=op.f('ck_chat_messages_role_valid')),
    sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], name=op.f('fk_chat_messages_thread_id_chat_threads'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_chat_messages'))
    )
    op.create_index(op.f('ix_chat_messages_thread_id'), 'chat_messages', ['thread_id'], unique=False)
    op.create_table('message_citations',
    sa.Column('message_id', sa.Uuid(), nullable=False),
    sa.Column('chunk_id', sa.Uuid(), nullable=False),
    sa.Column('label', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['chunk_id'], ['document_chunks.id'], name=op.f('fk_message_citations_chunk_id_document_chunks'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], name=op.f('fk_message_citations_message_id_chat_messages'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_message_citations'))
    )
    op.create_index(op.f('ix_message_citations_chunk_id'), 'message_citations', ['chunk_id'], unique=False)
    op.create_index(op.f('ix_message_citations_message_id'), 'message_citations', ['message_id'], unique=False)

    # Row-level security. Every table is locked to the browser (anon/authenticated
    # keys) unless a policy below allows it; the backend's service-role key bypasses
    # RLS. Corpus tables get no policy: only the backend reads them.
    for table in (
        "users",
        "source_documents",
        "document_chunks",
        "chat_threads",
        "chat_messages",
        "message_citations",
    ):
        op.execute(f"alter table {table} enable row level security")

    op.execute(
        "create policy users_select_own on users for select to authenticated "
        "using (id = auth.uid())"
    )
    op.execute(
        "create policy chat_threads_select_own on chat_threads for select to authenticated "
        "using (user_id = auth.uid())"
    )
    op.execute(
        "create policy chat_messages_select_own on chat_messages for select to authenticated "
        "using (exists (select 1 from chat_threads t "
        "where t.id = chat_messages.thread_id and t.user_id = auth.uid()))"
    )
    op.execute(
        "create policy message_citations_select_own on message_citations for select to authenticated "
        "using (exists (select 1 from chat_messages m join chat_threads t on t.id = m.thread_id "
        "where m.id = message_citations.message_id and t.user_id = auth.uid()))"
    )


def downgrade() -> None:
    """Downgrade schema. Policies drop with their tables; the vector extension stays."""
    op.drop_index(op.f('ix_message_citations_message_id'), table_name='message_citations')
    op.drop_index(op.f('ix_message_citations_chunk_id'), table_name='message_citations')
    op.drop_table('message_citations')
    op.drop_index(op.f('ix_chat_messages_thread_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index(op.f('ix_chat_threads_user_id'), table_name='chat_threads')
    op.drop_table('chat_threads')
    op.drop_table('users')
    op.drop_index('ix_document_chunks_search_vector', table_name='document_chunks', postgresql_using='gin')
    op.drop_index('ix_document_chunks_metadata', table_name='document_chunks', postgresql_using='gin')
    op.drop_index('ix_document_chunks_embedding', table_name='document_chunks', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.drop_index(op.f('ix_document_chunks_document_id'), table_name='document_chunks')
    op.drop_table('document_chunks')
    op.drop_table('source_documents')
