"""Contains the event class, which holds information for an event"""

import os
import urllib

import pytz
from dateutil import parser


class Event:
    """Event records all the data from an event, and has methods to generate the
    message from an event
    """

    # pylint: disable=too-many-instance-attributes
    # Events have lots of data that we need to save together

    def __init__(self, title, group_name, description, location, time, url, status, uuid):
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
        location = ""
        if event_json['venue'] is None:
            location = None
        elif event_json['venue']['name'] is not None and event_json['venue']['address'] is not None:
            name = event_json['venue']['name']
            address = event_json['venue']['address']
            city = event_json['venue']['city']
            state = event_json['venue']['state']
            zip_code = event_json['venue']['zip']
            location = f"{name} at {address} {city}, {state} {zip_code}"
        elif event_json['venue']['lat'] is not None and event_json['venue']['lat']:
            location = f"lat/long: {event_json['venue']['lat']}, {event_json['venue']['lat']}"
        elif event_json['venue']['name'] is not None:
            location = event_json['venue']['name']

        status = ""
        if event_json['status'] == "upcoming":
            status = "Upcoming ✅"
        elif event_json['status'] == "past":
            status = "Past ✔"
        elif event_json['status'] == "cancelled":
            status = "Cancelled ❌"
        else:
            status = event_json['status'].title()

        time = parser.isoparse(event_json['time']).astimezone(
            pytz.timezone(os.environ.get("TZ"))).strftime('%B %-d, %Y %I:%M %p %Z')

        return cls(
            title=event_json['event_name'],
            group_name=event_json['group_name'],
            description=event_json['description'],
            location=location,
            time=time,
            url=event_json['url'],
            status=status,
            uuid=event_json['uuid']
        )

    def create_slack_message(self):
        """Compose a slack message using the blocks layout"""
        if self.location is None:
            location = "No location"
        elif self.location is not None:
            location = ("<https://www.google.com/maps/search/?api=1&query="
                        f"{urllib.parse.quote(self.location)}|{self.location}>")

        return [
            {
                "type": "header",
                "text":  {
                    "type": "plain_text",
                    "text": f"{self.title}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"By {self.group_name}"

                    },
                    {
                        "type": "mrkdwn",
                        "text": f"<{self.url}|*Link* :link:>"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": f"{self.description}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Status*"

                    },
                    {
                        "type": "mrkdwn",
                        "text": f"{self.status}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Location*"

                    },
                    {
                        "type": "mrkdwn",
                        "text": location
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Time*"
                    },
                    {
                        "type": "plain_text",
                        "text": f"{self.time}"
                    }
                ]
            }
        ]

    def create_backup_message_text(self):
        """Compose a text string of event information for backup"""
        return (f"Name: {self.title}\n"
                f"Link: {self.url}\n"
                f"Description: {self.description}\n"
                f"Status: {self.status}\n"
                f"Location: {self.location}\n"
                f"Time: {self.time}"
                )
