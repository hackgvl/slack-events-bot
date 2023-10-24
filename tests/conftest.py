"""Pytest Fixtures"""
import json
import pathlib
from threading import Thread

import mocks
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

import bot
import database
from server import API


@pytest.fixture
def test_client():
    """Returns a Starlette test API instance"""
    return TestClient(API)


@pytest.fixture
def threads_appear_dead(monkeypatch):
    """Include this fixture if you'd like for all your threads to be reported as dead."""
    monkeypatch.setattr(Thread, "is_alive", lambda x: False)


@pytest_asyncio.fixture
async def db_cleanup():
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


@pytest.fixture(scope="session")
def event_api_response_data():
    """
    Provides the contents of events_api_response.json as a fixture.
    """
    data_file = pathlib.Path("tests/data/events_api_response.json")

    with open(data_file, "r", encoding="utf-8") as open_file:
        return mocks.mock_response.MockResponse(json=json.loads(open_file.read()))


@pytest.fixture
def single_event_data():
    """
    A single sample event to be manipulated within tests.
    """
    return {
        "event_name": "Beer and Napkins Creator Community ",
        "group_name": "Beer and Napkins Communities of Design",
        "group_url": "https://beerandnapkins.com",
        "venue": {
            "name": "Carolina Bauernhaus Greenville",
            "address": "556 Perry Ave Suite B118",
            "city": "Greenville",
            "state": "SC",
            "zip": "29611",
            "country": "us",
            "lat": 34.848915100097656,
            "lon": -82.42721557617188,
        },
        "url": "https://www.meetup.com/beer-and-napkins-community-of-design/events/lkzghtygcnbwb/",
        "time": "2023-10-24T22:30:00Z",
        "tags": "1",
        "rsvp_count": 1,
        "created_at": "2023-09-27T14:53:17Z",
        "description": "A much shorter description",
        "uuid": "fd15ac18-cb8d-4b8f-937e-f2f9b9a04b66",
        "nid": "164",
        "data_as_of": "2023-10-24T01:40:12Z",
        "status": "upcoming",
        "service_id": "lkzghtygcnbwb",
        "service": "meetup",
    }


@pytest.fixture
def mock_slack_bolt_async_app(monkeypatch):
    """
    Monkeypatch slack_bolt.async_app's AsyncApp with our stub
    """
    monkeypatch.setattr(bot, "APP", mocks.AsyncApp())
