from dateutil import parser
import os
import pytz
import urllib


class Event:
    def __init__(self, title, description, location, time, url, status, uuid):
        self.title = title
        self.description = description
        self.location = location
        self.time = time
        self.url = url
        self.status = status
        self.uuid = uuid

    # creates a struct of event information used to compose different formats of the event message
    @classmethod
    def from_event_json(cls, event_json):
        location = ""
        if event_json['venue'] is None:
            location = None
        elif event_json['venue']['name'] is not None and event_json['venue']['address'] is not None:
            location = f"{event_json['venue']['name']} at {event_json['venue']['address']} {event_json['venue']['city']}, {event_json['venue']['state']} {event_json['venue']['zip']}"
        elif event_json['venue']['lat'] is not None and event_json['venue']['lat']:
            location = f"lat/long: {event_json['venue']['lat']}, {event_json['venue']['lat']}"
        elif event_json['venue']['name'] is not None:
            location = event_json['venue']['name']

        status = ""
        if event_json['status'] == "upcoming":
            status = "Upcoming ✅"
        elif event_json['status'] == "cancelled":
            status = "Cancelled ❌"
        else:
            status = event_json['status'].title()

        time = parser.isoparse(event_json['time']).astimezone(
            pytz.timezone(os.environ.get("TZ"))).strftime('%B %-d, %Y %I:%M %p %Z')

        return cls(
            title=f"{event_json['event_name']} by {event_json['group_name']}",
            description=event_json['description'],
            location=location,
            time=time,
            url=event_json['url'],
            status=status,
            uuid=event_json['uuid']
        )

    # composes a slack message using the blocks layout
    def create_slack_message(self):
        if self.location is None:
            location = "No location"
        elif self.location is not None:
            location = f"<https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(self.location)}|{self.location}>"

        return [
            {
                "type": "section",
                "text":  {
                    "type": "mrkdwn",
                    "text": f"<{self.url}|{self.title} :link:>"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": self.description
                }
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
                        "text": self.status
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
                        "text": self.time
                    }
                ]
            }
        ]

    # composes a text string of event information for backup
    def create_backup_message_text(self):
        return f"Name: {self.title}\nLink: {self.url}\nDescription: {self.description}\nStatus: {self.status}\nLocation: {self.location}\nTime: {self.time}"
