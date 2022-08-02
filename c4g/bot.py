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
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import database
from event import Event

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
            await database.add_channel(conn, command['channel_id'])
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
            await database.remove_channel(conn, command['channel_id'])
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
            channels = await database.get_slack_channel_ids(conn)

            # filter events for only those that are happening in the next 3 days
            furthest_allowed_date = datetime.datetime.now(
                tz=tz.gettz('US/Eastern')) + datetime.timedelta(days=3)
            filtered_events = filter(lambda event_data: (parser.isoparse(event_data['time']) < furthest_allowed_date), await r.json())

            for event_data in filtered_events:
                if event_data['status'] == "cancelled" or event_data['status'] == "upcoming" or event_data['status'] == "past":
                    event = Event.from_event_json(event_data)
                    event_messages = await database.get_event_messages(conn, event.uuid)

                    # used to lookup the message id for a particular channel
                    channel_to_uuid = {
                        message['slack_channel_id']: message['message_timestamp'] for message in event_messages}

                    # used to quickly lookup if a message has been posted for a particular channel
                    posted_channels_set = set(
                        message['slack_channel_id'] for message in event_messages)

                    for slack_channel_id in channels:
                        if slack_channel_id in posted_channels_set:
                            print(
                                f"updating event {event.uuid} in {slack_channel_id}")
                            slackResponse = await app.client.chat_update(
                                ts=channel_to_uuid[slack_channel_id],
                                channel=slack_channel_id,
                                blocks=json.dumps(
                                    event.create_slack_message()),
                                text=event.create_backup_message_text())
                        else:
                            # channel_id is the internal sqlite ID of the channel row
                            # this is not slack's channel id!!
                            channel_id = await database.get_channel_id(conn, slack_channel_id)
                            print(
                                f"posting event {event.uuid} in {slack_channel_id}")
                            slackResponse = await app.client.chat_postMessage(
                                channel=slack_channel_id,
                                blocks=json.dumps(
                                    event.create_slack_message()),
                                text=event.create_backup_message_text(),
                                unfurl_links=False,
                                unfurl_media=False)
                            await database.create_event_message(conn, event.uuid, slackResponse['ts'], channel_id)
                else:
                    print(
                        f"Couldn\'t parse event {event_data['uuid']} with status: {event_data['status']}")


if __name__ == "__main__":
    # connect to sqlite3 database
    conn = sqlite3.connect(os.path.abspath(
        os.environ.get("DB_PATH", "./c4g.db")))

    # create database tables if they don't exist
    database.create_tables(conn)
    print("Created database tables!")

    conn.close()

    # start checking api every hour in background thread
    thread = threading.Thread(
        target=asyncio.run, args=(periodically_check_api(app),))
    thread.start()

    # start slack app
    app.start(port=int(os.environ.get("PORT").strip("\"\'")))
