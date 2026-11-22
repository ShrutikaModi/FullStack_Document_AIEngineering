from uuid import uuid4

import pytest

from app.auth.access import has_full_access
from app.auth.dependencies import CurrentUser
from app.config import settings


@pytest.fixture(autouse=True)
def allow_list(monkeypatch):
    monkeypatch.setattr(settings, "full_access_emails", ["owner@example.com"])


def user(email: str, confirmed: bool = True) -> CurrentUser:
    return CurrentUser(
        id=uuid4(), email=email, email_confirmed=confirmed, access_token="t"
    )


def test_a_listed_confirmed_address_has_full_access_whatever_its_letter_case():
    assert has_full_access(user("owner@example.com"))
    assert has_full_access(user("Owner@Example.COM"))


def test_other_addresses_do_not():
    assert not has_full_access(user("someone@example.com"))
    assert not has_full_access(user("owner@example.com.evil.com"))


def test_a_listed_address_that_is_not_confirmed_does_not(monkeypatch):
    assert not has_full_access(user("owner@example.com", confirmed=False))


def test_an_empty_list_means_everyone_is_in_demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "full_access_emails", [])
    assert not has_full_access(user("owner@example.com"))
