"""Contains the event class, which holds information for an event"""

import os
import urllib

import pytz
from dateutil import parser


def parse_location(event_json):
    """Parse location string from event json"""
    if event_json["venue"] is None:
        return None

    if None not in (
        event_json["venue"]["name"],
        event_json["venue"]["address"],
        event_json["venue"]["city"],
        event_json["venue"]["state"],
        event_json["venue"]["zip"],
    ):
        return (
            f"{event_json['venue']['name']} at "
            f"{event_json['venue']['address']} {event_json['venue']['city']}, "
            f"{event_json['venue']['state']} {event_json['venue']['zip']}"
        )

    if (
        event_json["venue"]["lat"] is not None
        and event_json["venue"]["lon"] is not None
    ):
        return f"lat/long: {event_json['venue']['lat']}, {event_json['venue']['lon']}"

    return f"{event_json['venue']['name']}"


def truncate_string(string, length=250):
    """Truncate string and add ellipses if it's too long"""
    if not string or not string.strip():
        return None
    return string[:length] + (string[length:] and "...")


def get_location_url(location):
    """Return google maps link for location or plaintext"""
    if not location or not location.strip():
        return None

    return (
        "<https://www.google.com/maps/search/?api=1&query="
        f"{urllib.parse.quote(location)}|{location}>"
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
    return time.astimezone(pytz.timezone(os.environ.get("TZ"))).strftime(
        "%B %-d, %Y %I:%M %p %Z"
    )


class Event:
    """Event records all the data from an event, and has methods to generate the
    message from an event
    """

    # pylint: disable=too-many-instance-attributes
    # Events have lots of data that we need to save together
    def __init__(
        self, *, title, group_name, description, location, time, url, status, uuid
    ):
        # pylint: disable=too-many-arguments
        self.title = title
        self.group_name = group_name
        self.description = description
        self.location = location
        self.time = time
        self.url = url
        self.status = status
        self.uuid = uuid

    # creates a struct of event information used to compose different formats of the event message
    @classmethod
    def from_event_json(cls, event_json):
        """Create an event class object from the raw event json returned by the OpenApi"""
        return cls(
            title=event_json["event_name"],
            group_name=event_json["group_name"],
            description=event_json["description"],
            location=parse_location(event_json),
            time=parser.isoparse(event_json["time"]),
            url=event_json["url"],
            status=event_json["status"],
            uuid=event_json["uuid"],
        )

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

        location_text = get_location_url(self.location)
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

        location_text = self.location  # get_location_url already handles None/empty
        if location_text and location_text.strip():
            lines.append(f"Location: {location_text}")

        time_text = print_datetime(self.time)
        if time_text:
            lines.append(f"Time: {time_text}")

        return "\n".join(lines)
