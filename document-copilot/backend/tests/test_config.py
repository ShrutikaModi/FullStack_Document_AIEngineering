import pytest
from pydantic import ValidationError

VALID = {
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_ANON_KEY": "anon",
    "SUPABASE_SERVICE_ROLE_KEY": "service",
    "DATABASE_URL": "postgresql://postgres:pw@db.abc.supabase.co:5432/postgres",
    "OPENAI_API_KEY": "sk-test",
    "ALLOWED_ORIGINS": "http://localhost:5173, https://app.example.com",
}


@pytest.fixture
def settings_cls(monkeypatch):
    # Import needs a valid env because config.py builds `settings` at import time.
    for key, value in VALID.items():
        monkeypatch.setenv(key, value)
    from app.config import Settings

    return Settings


def test_parses_comma_separated_origins(settings_cls):
    s = settings_cls(_env_file=None)
    assert s.allowed_origins == ["http://localhost:5173", "https://app.example.com"]


def test_missing_required_value_fails(settings_cls, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(ValidationError):
        settings_cls(_env_file=None)


def test_rejects_placeholder(settings_cls, monkeypatch):
    monkeypatch.setenv("SUPABASE_ANON_KEY", "your-anon-public-key")
    with pytest.raises(ValidationError):
        settings_cls(_env_file=None)


def test_rejects_pooler_url(settings_cls, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://u:p@aws-0.pooler.supabase.com:6543/postgres"
    )
    with pytest.raises(ValidationError):
        settings_cls(_env_file=None)


def test_log_format_defaults_to_console_and_rejects_unknown_values(
    settings_cls, monkeypatch
):
    assert settings_cls(_env_file=None).log_format == "console"
    monkeypatch.setenv("LOG_FORMAT", "json")
    assert settings_cls(_env_file=None).log_format == "json"
    monkeypatch.setenv("LOG_FORMAT", "xml")
    with pytest.raises(ValidationError):
        settings_cls(_env_file=None)


def test_full_access_emails_are_split_trimmed_and_lowercased(settings_cls, monkeypatch):
    assert settings_cls(_env_file=None).full_access_emails == []  # default: all demo
    monkeypatch.setenv("FULL_ACCESS_EMAILS", " Owner@Example.com, other@example.com ,")
    assert settings_cls(_env_file=None).full_access_emails == [
        "owner@example.com",
        "other@example.com",
    ]
