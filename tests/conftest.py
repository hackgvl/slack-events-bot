"""Pytest Fixtures"""

import pytest
from fastapi.testclient import TestClient
from threading import Thread

from bot import API
import database


@pytest.fixture
def test_client():
    """Returns a Starlette test API instance"""
    return TestClient(API)


@pytest.fixture
def threads_appear_dead(monkeypatch):
    """Include this fixture if you'd like for all your threads to be reported as dead."""
    monkeypatch.setattr(Thread, "is_alive", lambda x: False)


@pytest.fixture
def db_with_cleanup():
    """
    Fixture to provide a DB connection to tests and then ensure state doesn't bleed over
    between them.
    """
    database.create_tables()

    for conn in database.get_connection():
        yield conn

        cur = conn.cursor()

        cur.executescript(
            """
            SELECT 'DELETE FROM ' || name
            FROM sqlite_master
            WHERE type = 'table';

            VACUUM;
            """
        )
