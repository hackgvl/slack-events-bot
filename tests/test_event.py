"""
Tests the parsing of events data
"""

import event


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
