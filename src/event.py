"""Contains the event class, which holds information for an event"""

import os
import urllib

import pytz
from dateutil import parser


def parse_location(event_json):
    """Parse location string from event json"""
    if event_json["venue"] is None:
        return None

    name = event_json["venue"].get("name")
    address = event_json["venue"].get("address")
    city = event_json["venue"].get("city")
    state = event_json["venue"].get("state")
    zip_code = event_json["venue"].get("zip")
    lat = event_json["venue"].get("lat")
    lon = event_json["venue"].get("lon")

    # Option 1: Full address
    if all([name, address, city, state, zip_code]):
        return f"{name} at " f"{address} {city}, " f"{state} {zip_code}"

    # Option 2: Lat/Lon
    if lat is not None and lon is not None:
        return f"lat/long: {lat}, {lon}"

    # Option 3: Just name
    if name:
        return name

    return None


def truncate_string(string, length=250):
    """Truncate string and add ellipses if it's too long"""
    if not string or not string.strip():
        return None
    return string[:length] + (string[length:] and "...")


def get_location_url(location):
    """Return google maps link for location or plaintext"""
    if not location or not location.strip():
        return None

    search_query = location
    if location.startswith("lat/long: "):
        search_query = location.replace("lat/long: ", "")

    return (
        "<https://www.google.com/maps/search/?api=1&query="
        f"{urllib.parse.quote(search_query)}|{location}>"
    )


def print_status(status):
    """Prints status with emojis :D"""
    if status == "upcoming":
        return "Upcoming ✅"

    if status == "past":
        return "Past ✔"

    if status == "cancelled":
        return "Cancelled ❌"

    return status.title()


def print_datetime(time):
    """Print datetime in local timezone as string"""
    if time is None:
        return None
    return time.astimezone(pytz.timezone(os.environ.get("TZ"))).strftime(
        "%B %-d, %Y %I:%M %p %Z"
    )


class Event:
    """Event records all the data from an event, and has methods to generate the
    message from an event
    """

    def __init__(self, event_json):
        self._event_json = event_json

    @property
    def title(self):
        """Returns the event title."""
        return self._event_json["event_name"]

    @property
    def group_name(self):
        """Returns the event group name."""
        return self._event_json["group_name"]

    @property
    def description(self):
        """Returns the event description."""
        return self._event_json["description"]

    @property
    def location(self):
        """Returns the event location."""
        return parse_location(self._event_json)

    @property
    def time(self):
        """Returns the event time."""
        if self._event_json["time"] is None:
            return None
        return parser.isoparse(self._event_json["time"])

    @property
    def url(self):
        """Returns the event URL."""
        return self._event_json["url"]

    @property
    def status(self):
        """Returns the event status."""
        return self._event_json["status"]

    @property
    def uuid(self):
        """Returns the event UUID."""
        return self._event_json["uuid"]

    def _build_fields(self):
        fields = []
        if self.group_name and self.group_name.strip():
            fields.append(
                {"type": "mrkdwn", "text": f"*{truncate_string(self.group_name)}*"}
            )
        if self.url and self.url.strip():
            fields.append({"type": "mrkdwn", "text": f"<{self.url}|*Link* :link:>"})

        status_text = print_status(self.status)
        if status_text and status_text.strip():
            fields.append({"type": "mrkdwn", "text": "*Status*"})
            fields.append({"type": "mrkdwn", "text": status_text})

        location_text = get_location_url(parse_location(self._event_json))
        if location_text and location_text.strip():
            fields.append({"type": "mrkdwn", "text": "*Location*"})
            fields.append({"type": "mrkdwn", "text": location_text})

        time_text = print_datetime(self.time)
        if time_text and time_text.strip():
            fields.append({"type": "mrkdwn", "text": "*Time*"})
            fields.append({"type": "plain_text", "text": time_text})
        return fields

    def generate_blocks(self):
        """Compose part of a slack message using the blocks layout"""
        blocks = []
        if self.title and self.title.strip():
            blocks.append(
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": truncate_string(self.title)},
                }
            )
        section_block = {
            "type": "section",
            "fields": self._build_fields(),
        }

        description_text = truncate_string(self.description)
        if description_text:
            section_block["text"] = {
                "type": "plain_text",
                "text": description_text,
            }

        blocks.append(section_block)
        return blocks

    def generate_text(self):
        """Compose a text string of event information for backup"""
        lines = []
        title_text = truncate_string(self.title)
        if title_text:
            lines.append(title_text)

        description_text = truncate_string(self.description)
        if description_text:
            lines.append(f"Description: {description_text}")

        if self.url and self.url.strip():
            lines.append(f"Link: {self.url}")

        status_text = print_status(self.status)
        if status_text and status_text.strip():
            lines.append(f"Status: {status_text}")

        location_text = get_location_url(self.location)
        if location_text and location_text.strip():
            lines.append(f"Location: {location_text}")

        time_text = print_datetime(self.time)
        if time_text:
            lines.append(f"Time: {time_text}")

        return "\n".join(lines)
