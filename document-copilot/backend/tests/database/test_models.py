from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.database.models import Base

EXPECTED_TABLES = {
    "users",
    "source_documents",
    "document_chunks",
    "chat_threads",
    "chat_messages",
    "message_citations",
    "auth.users",  # stub of Supabase's own table
}


def test_all_tables_are_registered():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_chunks_have_vector_and_generated_tsvector():
    ddl = str(
        CreateTable(Base.metadata.tables["document_chunks"]).compile(
            dialect=postgresql.dialect()
        )
    )
    assert "VECTOR(1536)" in ddl.upper()
    assert "GENERATED ALWAYS AS (to_tsvector('english', content)) STORED" in ddl
