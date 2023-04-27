"""The c4g-event slack bot"""

import asyncio
import datetime
import os
import sqlite3
import threading

import aiohttp
import database
from dateutil import parser, tz
from event import Event
from slack_bolt.app.async_app import AsyncApp

# configure app
APP = AsyncApp(
    token=os.environ.get("BOT_TOKEN"),
    signing_secret=os.environ.get("SIGNING_SECRET")
)

DBPATH = os.path.abspath(os.environ.get("DB_PATH", "./c4g.db"))
CONN = sqlite3.connect(DBPATH)


async def periodically_check_api():
    """Periodically check the api every hour"""
    print("Checking api every hour")
    while True:
        # Create an additional connection since it will only be used once per
        # hour
        with sqlite3.connect(DBPATH) as conn:
            await check_api(conn)
        await asyncio.sleep(60 * 60)  # every hour


@APP.command("/add_channel")
async def add_channel(ack, say, logger, command):
    """Handle adding a slack channel to the bot"""
    del say
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command['channel_id'] is not None:
        try:
            await database.add_channel(CONN, command['channel_id'])
            await ack("Added channel to c4g-events 👍")
        except sqlite3.IntegrityError:
            await ack("c4g-events has already been activated for this channel")


@APP.command("/remove_channel")
async def remove_channel(ack, say, logger, command):
    """Handle removing a slack channel from the bot"""
    del say
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command['channel_id'] is not None:
        try:
            await database.remove_channel(CONN, command['channel_id'])
            await ack("Removed channel from c4g-events 👍")
        except sqlite3.IntegrityError:
            await ack("c4g-events is not activated for this channel")


@APP.command("/check_api")
async def trigger_check_api(ack, say, logger, command):
    """Handle manually rechecking the api for updates"""
    del say
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command['channel_id'] is not None:
        await ack("Checking api for events 👍")
        await check_api(CONN)


async def check_api(conn):
    """Check the api for updates and update any existing messages"""
    async with aiohttp.ClientSession() as session:
        async with session.get("https://events.openupstate.org/api/gtc") as resp:
            channels = await database.get_slack_channel_ids(conn)

            # filter events for only those that are happening in the next 3 days
            furthest_allowed_date = datetime.datetime.now(
                tz=tz.gettz('US/Eastern')) + datetime.timedelta(days=3)
            filtered_events = filter(lambda event_data: (
                parser.isoparse(event_data['time']) < furthest_allowed_date), await resp.json())

            for event_data in filtered_events:
                if event_data['status'] not in ["cancelled", "upcoming", "past"]:
                    print(f"Couldn\'t parse event {event_data['uuid']} "
                          "with status: {event_data['status']}")
                    continue

                event = Event.from_event_json(event_data)
                event_messages = await database.get_event_messages(conn, event.uuid)

                # used to lookup the message id and message for a particular channel
                message_details = {
                    message['slack_channel_id']: {
                        "timestamp": message['message_timestamp'],
                        "message": message['message']
                    } for message in event_messages}

                # used to quickly lookup if a message has been posted for a particular channel
                posted_channels_set = set(
                    message['slack_channel_id'] for message in event_messages)

                for slack_channel_id in channels:
                    await post_message_for_channel(
                        conn=conn,
                        event=event,
                        slack_channel_id=slack_channel_id,
                        message_details=message_details,
                        posted_channels_set=posted_channels_set)


async def post_message_for_channel(conn,
                                    event,
                                    slack_channel_id,
                                    message_details,
                                    posted_channels_set):
    """Posts or updates a message in a slack channel for an event"""
    if (slack_channel_id in posted_channels_set and
            event.generate_text() == message_details[slack_channel_id]["message"]):
        print(f"{event.uuid} in {slack_channel_id} hasn't changed, not updating")

    elif slack_channel_id in posted_channels_set:
        print(f"updating event {event.uuid} in {slack_channel_id}")

        slack_response = await APP.client.chat_update(
            ts=message_details[slack_channel_id]["timestamp"],
            channel=slack_channel_id,
            blocks=event.generate_blocks(),
            text=event.generate_text())

    else:
        # channel_id is the internal sqlite ID of the channel row
        # this is not slack's channel id!!
        channel_id = await database.get_channel_id(conn, slack_channel_id)
        print(f"posting event {event.uuid} in {slack_channel_id}")

        slack_response = await APP.client.chat_postMessage(
            channel=slack_channel_id,
            blocks=event.generate_blocks(),
            text=event.generate_text(),
            unfurl_links=False,
            unfurl_media=False)

        await database.create_event_message(conn,
                                            event.uuid,
                                            event.generate_text(),
                                            slack_response['ts'],
                                            channel_id)


if __name__ == "__main__":
    # create database tables if they don't exist
    database.create_tables(CONN)
    print("Created database tables!")

    # start checking api every hour in background thread
    thread = threading.Thread(
        target=asyncio.run, args=(periodically_check_api(),))
    thread.start()

    # start slack APP
    APP.start(port=int(os.environ.get("PORT").strip("\"\'")))

CONN.close()
