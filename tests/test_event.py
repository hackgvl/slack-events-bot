"""
Tests the parsing of events data
"""

import datetime

import pytz

import event


def test_parsing_location_of_event_with_full_details(sample_event_date):
    """Happy path scenario where all event fields are populated"""
    result = "Gower Estates Park at 24 Evelyn Ave, Greenville, SC 29607"
    assert result == event.parse_location(sample_event_date)
    expected_url = (
        "<https://www.google.com/maps/search/?api=1&query=Gower%20Estates"
        "%20Park%20at%2024%20Evelyn%20Ave%2C%20Greenville%2C%20SC%2029607|"
        "Gower Estates Park at 24 Evelyn Ave, Greenville, SC 29607>"
    )
    assert (
        event.get_location_url(event.parse_location(sample_event_date)) == expected_url
    )


def test_parsing_location_of_event_with_missing_venue(sample_event_date):
    """Tests that the location is returned as None if a venue isn't provided"""
    event_data_without_venue = sample_event_date
    event_data_without_venue["venue"] = None

    assert event.parse_location(event_data_without_venue) is None


def test_parsing_location_of_event_missing_state(sample_event_date):
    """Ensure coordinates are returned if the state is missing from venue info"""
    event_data_without_state = sample_event_date
    event_data_without_state["venue"]["state"] = None

    result = event.parse_location(event_data_without_state)
    assert result == "lat/long: 34.8300191, -82.3510954"

    expected_url = (
        "<https://www.google.com/maps/search/?api=1&query=34.8300191%2C%20-82.3510954|"
        "lat/long: 34.8300191, -82.3510954>"
    )
    assert event.get_location_url(result) == expected_url


def test_parsing_location_of_event_missing_state_and_latitude(sample_event_date):
    """Ensure venue name is returned if state and latitude are missing from venue info"""
    event_data_without_state_and_lat = sample_event_date
    event_data_without_state_and_lat["venue"]["state"] = None
    event_data_without_state_and_lat["venue"]["lat"] = None

    result = event.parse_location(event_data_without_state_and_lat)
    assert result == "Gower Estates Park"

    expected_url = (
        "<https://www.google.com/maps/search/?api=1&query=Gower%20Estates%20Park|"
        "Gower Estates Park>"
    )
    assert event.get_location_url(result) == expected_url


def test_parsing_location_of_event_with_only_name():
    """Test that only the venue name is returned if only name is present."""
    result = event.parse_location({"venue": {"name": "Test Venue"}})
    assert result == "Test Venue"

    expected_url = (
        "<https://www.google.com/maps/search/?api=1&query=Test%20Venue|Test Venue>"
    )
    assert event.get_location_url(result) == expected_url


def test_parsing_location_of_event_with_name_and_lat_lon():
    """Test that lat/lon is prioritized over name if both are present but no full address."""
    result = event.parse_location(
        {"venue": {"name": "Test Venue", "lat": 12.34, "lon": 56.78}}
    )
    assert result == "lat/long: 12.34, 56.78"

    expected_url = (
        "<https://www.google.com/maps/search/?api=1&query=12.34"
        "%2C%2056.78|lat/long: 12.34, 56.78>"
    )
    assert event.get_location_url(result) == expected_url


def test_parsing_location_of_event_missing_address():
    """Test that full address is still formatted if address is missing but other
    parts are present."""
    event_data_missing_address = {
        "venue": {
            "name": "Test Venue",
            "city": "Test City",
            "state": "TS",
            "zip": "12345",
            "lat": 12.34,
            "lon": 56.78,
        }
    }
    assert event.parse_location(event_data_missing_address) == "lat/long: 12.34, 56.78"
    expected_url = (
        "<https://www.google.com/maps/search/?api=1&query=12.34%2C%2056.78"
        "|lat/long: 12.34, 56.78>"
    )
    assert (
        event.get_location_url(event.parse_location(event_data_missing_address))
        == expected_url
    )


def test_parsing_location_of_event_missing_city():
    """Test that full address is still formatted if city is missing but other parts are present."""
    event_data_missing_city = {
        "venue": {
            "name": "Test Venue",
            "address": "123 Test St",
            "state": "TS",
            "zip": "12345",
            "lat": 12.34,
            "lon": 56.78,
        }
    }
    result = event.parse_location(event_data_missing_city)
    expected_plain_text_location = "lat/long: 12.34, 56.78"
    assert result == expected_plain_text_location
    expected_url = (
        "<https://www.google.com/maps/search/?api=1&query=12.34%2C%2056.78"
        "|lat/long: 12.34, 56.78>"
    )
    assert event.get_location_url(result) == expected_url


def test_parsing_location_of_event_missing_zip():
    """Test that full address is still formatted if zip is missing but other parts are present."""
    event_data_missing_zip = {
        "venue": {
            "name": "Test Venue",
            "address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "lat": 12.34,
            "lon": 56.78,
        }
    }
    result = event.parse_location(event_data_missing_zip)
    expected_plain_text_location = "lat/long: 12.34, 56.78"
    assert result == expected_plain_text_location
    expected_url = (
        "<https://www.google.com/maps/search/?api=1&query=12.34%2C%2056.78"
        "|lat/long: 12.34, 56.78>"
    )
    assert event.get_location_url(result) == expected_url


def test_generate_blocks_no_title():
    """Test that no header block is generated when the event has no title."""
    mock_event_json = {
        "event_name": "",
        "group_name": "Test Group",
        "description": "Test Description",
        "venue": {"name": "Test Location"},
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "http://example.com",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    blocks = mock_event.generate_blocks()
    # Assert that the first block is not a header block
    assert not any(b.get("type") == "header" for b in blocks)


def test_generate_blocks_whitespace_title():
    """Test that no header block is generated when the event has only whitespace title."""
    mock_event_json = {
        "event_name": "   ",
        "group_name": "Test Group",
        "description": "Test Description",
        "venue": {"name": "Test Location"},
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "http://example.com",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    blocks = mock_event.generate_blocks()
    # Assert that the first block is not a header block
    assert not any(b.get("type") == "header" for b in blocks)


def test_truncate_string_empty():
    """Test that truncate_string returns None for empty string."""
    assert event.truncate_string("") is None


def test_truncate_string_whitespace():
    """Test that truncate_string returns None for whitespace string."""
    assert event.truncate_string("   \n\t ") is None


def test_get_location_url_empty():
    """Test that get_location_url returns None for empty location."""
    assert event.get_location_url("") is None


def test_get_location_url_whitespace():
    """Test that get_location_url returns None for whitespace location."""
    assert event.get_location_url("   \n\t ") is None


def test_generate_blocks_conditional_fields():
    """Test that generate_blocks conditionally includes fields."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "",  # Empty group name
        "description": "",  # Empty description
        "venue": {"name": ""},  # Empty location
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "",  # Empty URL
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    blocks = mock_event.generate_blocks()
    # Expect only status and time fields to be present
    section_block = blocks[1]  # Assuming header is blocks[0] and section is blocks[1]
    assert len(section_block["fields"]) == 4  # Status and Time fields (label + value)
    assert section_block["fields"][0]["text"] == "*Status*"
    assert section_block["fields"][1]["text"] == "Upcoming ✅"
    assert section_block["fields"][2]["text"] == "*Time*"


def test_generate_text_conditional_lines():
    """Test that generate_text conditionally includes lines."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "",
        "description": "",
        "venue": {"name": ""},
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    text = mock_event.generate_text()
    assert text.split("\n") == [
        "Test Title",
        "Status: Upcoming ✅",
        f"Time: {event.print_datetime(mock_event.time)}",
    ]


def test_generate_blocks_no_description():
    """Test that the text field is not present in the section block when description is empty."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "Test Group",
        "description": "",  # Empty description
        "venue": {"name": "Test Location"},
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "http://example.com",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    blocks = mock_event.generate_blocks()
    assert "text" not in blocks[1]


def test_generate_blocks_whitespace_description():
    """Test that the text field is not present in the section block when
    description is whitespace."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "Test Group",
        "description": "   \n\t ",  # Whitespace description
        "venue": {"name": "Test Location"},
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "http://example.com",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    blocks = mock_event.generate_blocks()
    assert "text" not in blocks[1]


def test_generate_blocks_with_description():
    """Test that the text field is present in the section block when description is not empty."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "Test Group",
        "description": "This is a test description.",
        "venue": {"name": "Test Location"},
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "http://example.com",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    blocks = mock_event.generate_blocks()
    assert "text" in blocks[1]
    assert blocks[1]["text"]["text"] == "This is a test description."


def test_generate_text_no_group_name():
    """Test that the group name line is omitted when group_name is empty."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "",
        "description": "Test Description",
        "venue": {"name": "Test Location"},
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "http://example.com",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    text = mock_event.generate_text()
    assert "Group Name:" not in text


def test_generate_text_no_url():
    """Test that the link line is omitted when url is empty."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "Test Group",
        "description": "Test Description",
        "venue": {"name": "Test Location"},
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    text = mock_event.generate_text()
    assert "Link:" not in text


def test_generate_text_no_status():
    """Test that the status line is omitted when status is empty."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "Test Group",
        "description": "Test Description",
        "venue": {"name": "Test Location"},
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "http://example.com",
        "status": "",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    text = mock_event.generate_text()
    assert "Status:" not in text


def test_generate_text_no_location():
    """Test that the location line is omitted when location is empty."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "Test Group",
        "description": "Test Description",
        "venue": {"name": ""},
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "http://example.com",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    text = mock_event.generate_text()
    assert "Location:" not in text


def test_generate_text_no_time():
    """Test that the time line is omitted when time is None."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "Test Group",
        "description": "Test Description",
        "venue": {"name": "Test Location"},
        "time": None,
        "url": "http://example.com",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    text = mock_event.generate_text()
    assert "Time:" not in text


def test_generate_text_full_event():
    """Test that generate_text produces the expected output for a full event."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "Test Group",
        "description": "Test Description",
        "venue": {
            "name": "Test Location",
            "address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345",
        },
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "http://example.com",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    text = mock_event.generate_text()
    expected_text = (
        "Test Title\n"
        "Description: Test Description\n"
        "Link: http://example.com\n"
        "Status: Upcoming ✅\n"
        "Location: "
        + event.get_location_url("Test Location at 123 Test St Test City, TS 12345")
        + "\n"
        f"Time: {event.print_datetime(mock_event.time)}"
    )
    assert text == expected_text


def test_generate_blocks_full_event():
    """Test that generate_blocks produces the expected output for a full event."""
    mock_event_json = {
        "event_name": "Test Title",
        "group_name": "Test Group",
        "description": "Test Description",
        "venue": {
            "name": "Test Location",
            "address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345",
        },
        "time": datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc).isoformat(),
        "url": "http://example.com",
        "status": "upcoming",
        "uuid": "test-uuid",
    }
    mock_event = event.Event(mock_event_json)
    blocks = mock_event.generate_blocks()
    expected_blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Test Title"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": "*Test Group*"},
                {"type": "mrkdwn", "text": "<http://example.com|*Link* :link:>"},
                {"type": "mrkdwn", "text": "*Status*"},
                {"type": "mrkdwn", "text": "Upcoming ✅"},
                {"type": "mrkdwn", "text": "*Location*"},
                {
                    "type": "mrkdwn",
                    "text": event.get_location_url(
                        "Test Location at 123 Test St Test City, TS 12345"
                    ),
                },
                {"type": "mrkdwn", "text": "*Time*"},
                {
                    "type": "plain_text",
                    "text": event.print_datetime(mock_event.time),
                },
            ],
            "text": {"type": "plain_text", "text": "Test Description"},
        },
    ]
    assert blocks == expected_blocks
