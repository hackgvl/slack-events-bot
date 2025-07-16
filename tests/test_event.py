"""
Tests the parsing of events data
"""

import event
import datetime
import pytz


def test_parsing_location_of_event_with_full_details(sample_event_date):
    """Happy path scenario where all event fields are populated"""
    result = event.parse_location(sample_event_date)

    assert result == "Gower Estates Park at 24 Evelyn Ave, Greenville, SC 29607"


def test_parsing_location_of_event_with_missing_venue(sample_event_date):
    """Tests that the location is returned as None if a venue isn't provided"""
    event_data_without_venue = sample_event_date
    event_data_without_venue["venue"] = None

    result = event.parse_location(event_data_without_venue)

    assert result is None


def test_parsing_location_of_event_missing_state(sample_event_date):
    """Ensure coordinates are returned if the state is missing from venue info"""
    event_data_without_state = sample_event_date
    event_data_without_state["venue"]["state"] = None

    result = event.parse_location(event_data_without_state)

    assert result == "lat/long: 34.8300191, -82.3510954"


def test_parsing_location_of_event_missing_state_and_latitude(sample_event_date):
    """Ensure venue name is returned if state and latitude are missing from venue info"""
    event_data_without_state_and_lat = sample_event_date
    event_data_without_state_and_lat["venue"]["state"] = None
    event_data_without_state_and_lat["venue"]["lat"] = None

    result = event.parse_location(event_data_without_state_and_lat)

    assert result == "Gower Estates Park"

def test_generate_blocks_no_title():
    """Test that no header block is generated when the event has no title."""
    mock_event = event.Event(
        title="",
        group_name="Test Group",
        description="Test Description",
        location="Test Location",
        time=datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc),
        url="http://example.com",
        status="upcoming",
        uuid="test-uuid",
    )
    blocks = mock_event.generate_blocks()
    # Assert that the first block is not a header block
    assert not any(b.get('type') == 'header' for b in blocks)

def test_generate_blocks_whitespace_title():
    """Test that no header block is generated when the event has only whitespace title."""
    mock_event = event.Event(
        title="   ",
        group_name="Test Group",
        description="Test Description",
        location="Test Location",
        time=datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc),
        url="http://example.com",
        status="upcoming",
        uuid="test-uuid",
    )
    blocks = mock_event.generate_blocks()
    # Assert that the first block is not a header block
    assert not any(b.get('type') == 'header' for b in blocks)