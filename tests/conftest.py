"""Pytest Fixtures"""
from threading import Thread

import pytest
from fastapi.testclient import TestClient


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
def db_cleanup():
    """
    Fixture to clean the database after tests.
    """
    database.create_tables()

    yield

    for conn in database.get_connection():

        cur = conn.cursor()

        cur.executescript(
            """
            SELECT 'DELETE FROM ' || name
            FROM sqlite_master
            WHERE type = 'table';
            """
        )

        conn.commit()

        conn.close()
