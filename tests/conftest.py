"""Pytest Fixtures"""
import json
import pathlib
from threading import Thread

import mocks
import pytest
from fastapi.testclient import TestClient

import bot
import config
import database
import server


@pytest.fixture
def test_client():
    """Returns a Starlette test API instance"""
    return TestClient(server.API)


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
def mock_slack_bolt_async_app(request, monkeypatch):
    """
    Monkeypatch slack_bolt.async_app's AsyncApp with our stub
    """
    monkeypatch.setattr(f"{request.param}.SLACK_APP", mocks.AsyncApp())


@pytest.fixture
def sample_event_date():
    """Return fully-populated event dictionary"""
    return {
        "event_name": "Tankin' Around Greenville",
        "group_name": "Greenville Tank Enthusiasts",
        "group_url": "https://www.tankinaroundgreenville.com",
        "venue": {
            "name": "Gower Estates Park",
            "address": "24 Evelyn Ave,",
            "city": "Greenville",
            "state": "SC",
            "zip": "29607",
            "country": "US",
            "lat": "34.8300191",
            "lon": "-82.3510954",
        },
        "url": "https://www.eventbrite.com/e/tanks-are-cool-123456789101",
        "time": "2023-12-12T22:30:00Z",
        "tags": "",
        "rsvp_count": None,
        "created_at": "2023-11-15T18:50:35Z",
        "description": "Join us for a special event as we take a group trip to local parks to admire "
        + "and appreciate the decommissioned military tanks that are on display.",
        "uuid": "e70fb83b-df54-4333-9f02-1746ec1d62ee",
        "nid": "1",
        "data_as_of": "2023-12-07T16:40:14Z",
        "status": "upcoming",
        "service_id": "123456789101",
        "service": "eventbrite",
    }.copy()
