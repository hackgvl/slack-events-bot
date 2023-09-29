import pytest
from fastapi.testclient import TestClient
from threading import Thread

from bot import API


@pytest.fixture
def test_client():
    """Returns a Starlette test API instance"""
    return TestClient(API)


@pytest.fixture
def threads_appear_dead(monkeypatch):
    """Include this fixture if you'd like for all your threads to be reported as dead."""
    monkeypatch.setattr(Thread, "is_alive", lambda x: False)
