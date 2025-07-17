
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
    mock_event = event.Event(
        title="Test Title",
        group_name="", # Empty group name
        description="", # Empty description
        location="", # Empty location
        time=datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc),
        url="", # Empty URL
        status="upcoming",
        uuid="test-uuid",
    )
    blocks = mock_event.generate_blocks()
    # Expect only status and time fields to be present
    section_block = blocks[1] # Assuming header is blocks[0] and section is blocks[1]
    assert len(section_block['fields']) == 4 # Status (label + value), Time (label + value)
    assert section_block['fields'][0]['text'] == '*Status*'
    assert section_block['fields'][1]['text'] == 'Upcoming ✅'
    assert section_block['fields'][2]['text'] == '*Time*'

def test_generate_text_conditional_lines():
    """Test that generate_text conditionally includes lines."""
    mock_event = event.Event(
        title="Test Title",
        group_name="",
        description="",
        location="",
        time=datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc),
        url="",
        status="upcoming",
        uuid="test-uuid",
    )
    text = mock_event.generate_text()
    expected_lines = [
        "Test Title",
        "Status: Upcoming ✅",
        f"Time: {event.print_datetime(mock_event.time)}"
    ]
    assert text.split('\n') == expected_lines

def test_generate_blocks_no_description():
    """Test that the text field is not present in the section block when description is empty."""
    mock_event = event.Event(
        title="Test Title",
        group_name="Test Group",
        description="",  # Empty description
        location="Test Location",
        time=datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc),
        url="http://example.com",
        status="upcoming",
        uuid="test-uuid",
    )
    blocks = mock_event.generate_blocks()
    section_block = blocks[1]
    assert "text" not in section_block

def test_generate_blocks_whitespace_description():
    """Test that the text field is not present in the section block when description is whitespace."""
    mock_event = event.Event(
        title="Test Title",
        group_name="Test Group",
        description="   \n\t ",  # Whitespace description
        location="Test Location",
        time=datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc),
        url="http://example.com",
        status="upcoming",
        uuid="test-uuid",
    )
    blocks = mock_event.generate_blocks()
    section_block = blocks[1]
    assert "text" not in section_block

def test_generate_blocks_with_description():
    """Test that the text field is present in the section block when description is not empty."""
    mock_event = event.Event(
        title="Test Title",
        group_name="Test Group",
        description="This is a test description.",
        location="Test Location",
        time=datetime.datetime(2025, 7, 16, 10, 0, 0, tzinfo=pytz.utc),
        url="http://example.com",
        status="upcoming",
        uuid="test-uuid",
    )
    blocks = mock_event.generate_blocks()
    section_block = blocks[1]
    assert "text" in section_block
    assert section_block["text"]["text"] == "This is a test description."
