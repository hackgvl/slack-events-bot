import aiohttp
import asyncio
import datetime
from dateutil import parser
from dateutil import tz
import json
import os
import requests
import sqlite3
import threading
import urllib
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

# configure app
app = AsyncApp(
    token=os.environ.get("BOT_TOKEN"),
    signing_secret=os.environ.get("SIGNING_SECRET")
)


async def periodically_check_api(app):
    # connect to sqlite3 database
    conn = sqlite3.connect(os.path.abspath(
        os.environ.get("DB_PATH", "./c4g.db")))

    print("Checking api every hour")
    while True:
        await check_api(conn, app)
        await asyncio.sleep(60 * 60)  # every hour
    conn.close()


@app.command("/add_channel")
async def add_channel(ack, say, logger, command):
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command['channel_id'] is not None:
        # connect to sqlite3 database
        conn = sqlite3.connect(os.path.abspath(
            os.environ.get("DB_PATH", "./c4g.db")))
        try:
            await add_channel(conn, command['channel_id'])
            await ack("Added channel for c4g-events 👍")
        except sqlite3.IntegrityError:
            await ack("This channel has already been added to c4g-events")
        conn.close()


@app.command("/remove_channel")
async def remove_channel(ack, say, logger, command):
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command['channel_id'] is not None:
        # connect to sqlite3 database
        conn = sqlite3.connect(os.path.abspath(
            os.environ.get("DB_PATH", "./c4g.db")))
        try:
            await remove_channel(conn, command['channel_id'])
            await ack("Removed channel for c4g-events 👍")
        except sqlite3.IntegrityError:
            await ack("This channel has already been removed c4g-events")
        conn.close()


@app.command("/check_api")
async def trigger_check_api(ack, say, logger, command):
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command['channel_id'] is not None:
        await ack("Checking api for c4g-events 👍")
        # connect to sqlite3 database
        conn = sqlite3.connect(os.path.abspath(
            os.environ.get("DB_PATH", "./c4g.db")))
        await check_api(conn, app)
        conn.close()


async def check_api(conn, app):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://events.openupstate.org/api/gtc") as r:
            channels = await get_slack_channel_ids(conn)

            # filter events for only those that are happening in the next 3 days
            furthest_allowed_date = datetime.datetime.now(
                tz=tz.gettz('US/Eastern')) + datetime.timedelta(days=3)
            filtered_events = [event for event in await r.json() if parser.isoparse(event['time']) < furthest_allowed_date]

            for event in filtered_events:
                if event['status'] == "cancelled" or event['status'] == "upcoming":
                    event_messages = await get_event_messages(conn, event['uuid'])

                    # used to lookup the message id for a particular channel
                    channel_to_uuid = {
                        message['slack_channel_id']: message['message_timestamp'] for message in event_messages}

                    # used to quickly lookup if a message has been posted for a particular channel
                    posted_channels_set = set(
                        message['slack_channel_id'] for message in event_messages)

                    for slack_channel_id in channels:
                        # channel_id is the internal sqlite ID of the channel row
                        # this is not slack's channel id!!
                        channel_id = await get_channel_id(conn, slack_channel_id)
                        print(
                            f"posting event {event['uuid']} in: {slack_channel_id}, id: {channel_id}")

                        event_info = __get_event_information(event)
                        event_message = __create_slack_message(
                            event_info)
                        backup_text = __create_backup_message_text(
                            event_info)

                        if slack_channel_id in posted_channels_set:
                            slackResponse = await app.client.chat_update(
                                ts=channel_to_uuid[slack_channel_id],
                                channel=slack_channel_id,
                                blocks=json.dumps(event_message),
                                text=backup_text)
                        else:
                            slackResponse = await app.client.chat_postMessage(
                                channel=slack_channel_id,
                                blocks=json.dumps(event_message),
                                text=backup_text,
                                unfurl_links=False,
                                unfurl_media=False)
                            await create_event_message(conn, event['uuid'], slackResponse['ts'], channel_id)
                elif event['status'] == "past":
                    # no need to update more, it's past already
                    continue
                else:
                    print(
                        f"Couldn\'t parse event {event['uuid']} with status: {event['status']}")


# creates a struct of event information used to compose different formats of the event message
def __get_event_information(event):
    location = ""
    if event['venue'] is None:
        location = "No location"
    elif event['venue']['name'] is not None and event['venue']['address'] is not None:
        location = f"{event['venue']['name']} at {event['venue']['address']} {event['venue']['city']}, {event['venue']['state']} {event['venue']['zip']}"
    elif event['venue']['lat'] is not None and event['venue']['lat']:
        location = f"lat/long: {event['venue']['lat']}, {event['venue']['lat']}"
    elif event['venue']['name'] is not None:
        location = event['venue']['name']

    return {
        "title": f"{event['event_name']} by {event['group_name']}",
        "description": event['description'],
        "location": location,
        "time": parser.isoparse(event['time']).strftime('%B %-d, %Y %I:%M %p'),
        "url": event['url'],
        "status": event['status'].title()
    }


# composes a slack message using the blocks layout
def __create_slack_message(event_info):
    return [
        {
            "type": "header",
            "text": {
                    "type": "plain_text",
                    "text": event_info['title']
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"<{event_info['url']}|Link :link:>"
                }
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Description*"
                },
                {
                    "type": "mrkdwn",
                    "text": event_info['description']
                }
            ]
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
                    "text": event_info['status']
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
                    "text": f"<https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(event_info['location'])}|{event_info['location']}>"
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
                    "type": "mrkdwn",
                    "text": event_info['time']
                }
            ]
        }
    ]


# composes a text string of event information for backup
def __create_backup_message_text(event_info):
    return f"Name: {event_info['title']}\nDescription: {event_info['description']}\nStatus: {event_info['status']}\nLocation: {event_info['location']}\nTime: {event_info['time']}\nLink: {event_info['url']}"


def create_tables(conn):
    cur = conn.cursor()

    cur.executescript("""
		CREATE TABLE IF NOT EXISTS channels (
			id integer PRIMARY KEY AUTOINCREMENT NOT NULL,
			slack_channel_id TEXT UNIQUE NOT NULL
		);

		CREATE INDEX IF NOT EXISTS slack_channel_id_index ON channels (slack_channel_id);

		CREATE TABLE IF NOT EXISTS messages (
			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
			event_uuid TEXT NOT NULL,
			message_timestamp TEXT NOT NULL,
			channel_id INTEGER NOT NULL,
				CONSTRAINT fk_channel_id
				FOREIGN KEY(channel_id) REFERENCES channels(id)
				ON DELETE CASCADE
		);

		CREATE INDEX IF NOT EXISTS uuid_index ON messages (event_uuid);
	""")

    # saves the change to the database
    conn.commit()


async def create_event_message(conn, eventUUID, messageTimestamp, channelID):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO messages (event_uuid, message_timestamp, channel_id)
            VALUES (?, ?, ?)""",
        [eventUUID, messageTimestamp, channelID]
    )

    # saves the change to the database
    conn.commit()


async def event_messages_count(conn, eventUUID):
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(event_uuid) FROM messages WHERE event_uuid = ?",
        [eventUUID]
    )
    return cur.fetchone()[0]


async def get_event_messages(conn, eventUUID):
    cur = conn.cursor()
    cur.execute(
        """SELECT m.message_timestamp, c.slack_channel_id
            FROM messages m
            JOIN channels c ON m.channel_id = c.id
            WHERE m.event_uuid = ?""",
        [eventUUID]
    )
    return [{'message_timestamp': x[0], 'slack_channel_id': x[1]} for x in cur.fetchall()]


async def get_slack_channel_ids(conn):
    cur = conn.cursor()
    cur.execute("SELECT slack_channel_id FROM channels")
    return [x[0] for x in cur.fetchall()]


async def get_slack_channel_id(conn, channelID):
    cur = conn.cursor()
    cur.execute(
        "SELECT slack_channel_id FROM channels WHERE id = ?", [channelID])
    return cur.fetchone()[0]


async def get_channel_id(conn, slackChannelID):
    cur = conn.cursor()
    cur.execute("SELECT id FROM channels WHERE slack_channel_id = ?", [
                slackChannelID])
    return cur.fetchone()[0]


async def add_channel(conn, slackChannelID):
    cur = conn.cursor()
    cur.execute("INSERT INTO channels (slack_channel_id) VALUES (?)", [
                slackChannelID])

    # saves the change to the database
    conn.commit()


async def remove_channel(conn, channelID):
    cur = conn.cursor()
    cur.execute("DELETE FROM channels WHERE slack_channel_id = ?", [channelID])

    # saves the change to the database
    conn.commit()

if __name__ == "__main__":
    # connect to sqlite3 database
    conn = sqlite3.connect(os.path.abspath(
        os.environ.get("DB_PATH", "./c4g.db")))

    # create database tables if they don't exist
    create_tables(conn)
    print("Created database tables!")

    conn.close()

    # start checking api every hour in background thread
    thread = threading.Thread(
        target=asyncio.run, args=(periodically_check_api(app),))
    thread.start()

    # start slack app
    app.start(port=int(os.environ.get("PORT")))
