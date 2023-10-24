"""The hackgreenville labs slack bot"""

import asyncio
import datetime
import logging
import os
import sqlite3
import traceback
from collections import defaultdict

import aiohttp
import pytz
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp

import database
from message_builder import build_event_blocks, chunk_messages

# configure app
APP = AsyncApp(
    token=os.environ.get("BOT_TOKEN"), signing_secret=os.environ.get("SIGNING_SECRET")
)
APP_HANDLER = AsyncSlackRequestHandler(APP)


async def post_or_update_messages(week, messages):
    """Posts or updates a message in a slack channel for a week"""
    channels = await database.get_slack_channel_ids()
    existing_messages = await database.get_messages(week)

    if len(existing_messages) > 0 and len(messages) > len(existing_messages):
        logging.error(
            "Updating messages would cause us to hit the Slack rate limit. "
            "This is because new events have been added. "
            "Existing message count: %s --- New message count: %s.",
            len(existing_messages),
            len(messages),
        )

        return

    # used to lookup the message id and message for a particular
    # channel
    message_details = defaultdict(list)
    for existing_message in existing_messages:
        message_details[existing_message["slack_channel_id"]].append(
            {
                "timestamp": existing_message["message_timestamp"],
                "message": existing_message["message"],
                "sequence_position": existing_message["sequence_position"] or "1",
            }
        )

    # used to quickly lookup if a message has been posted for a
    # particular channel
    posted_channels_set = set(message_details.keys())

    for slack_channel_id in channels:
        for msg_idx, msg in enumerate(messages):
            msg_text = msg["text"]
            msg_blocks = msg["blocks"]

            if (
                slack_channel_id in posted_channels_set
                and msg_text == message_details[slack_channel_id][msg_idx]["message"]
            ):
                print(
                    f"Message {msg_idx + 1} for week of "
                    f"{week.strftime('%B %-d')} in {slack_channel_id} "
                    "hasn't changed, not updating"
                )
            elif slack_channel_id in posted_channels_set:
                print(
                    f"Updating message {msg_idx + 1} for week {week.strftime('%B %-d')} "
                    f"in {slack_channel_id}"
                )

                timestamp = message_details[slack_channel_id][msg_idx]["timestamp"]
                slack_response = await APP.client.chat_update(
                    ts=timestamp,
                    channel=slack_channel_id,
                    blocks=msg_blocks,
                    text=msg_text,
                )

                await database.update_message(
                    week, msg_text, timestamp, slack_channel_id
                )

            else:
                print(
                    f"Posting message {msg_idx + 1} for week {week.strftime('%B %-d')} "
                    f"in {slack_channel_id}"
                )

                slack_response = await APP.client.chat_postMessage(
                    channel=slack_channel_id,
                    blocks=msg_blocks,
                    text=msg_text,
                    unfurl_links=False,
                    unfurl_media=False,
                )

                await database.create_message(
                    week, msg_text, slack_response["ts"], slack_channel_id, msg_idx
                )


async def parse_events_for_week(probe_date, resp):
    """Parses events for the week containing the probe date"""
    week_start = probe_date - datetime.timedelta(days=(probe_date.weekday() % 7) + 1)
    week_end = week_start + datetime.timedelta(days=7)

    event_blocks = await build_event_blocks(resp, week_start, week_end)

    chunked_messages = await chunk_messages(event_blocks, week_start)

    await post_or_update_messages(week_start, chunked_messages)


async def check_api():
    """Check the api for updates and update any existing messages"""
    async with aiohttp.ClientSession() as session:
        async with session.get("https://events.openupstate.org/api/gtc") as resp:
            # get timezone aware today
            today = datetime.date.today()
            today = datetime.datetime(
                today.year, today.month, today.day, tzinfo=pytz.utc
            )

            # keep current week's post up to date
            await parse_events_for_week(today, resp)

            # potentially post next week 5 days early
            probe_date = today + datetime.timedelta(days=5)
            await parse_events_for_week(probe_date, resp)


async def periodically_delete_old_messages():
    """Once a day delete messages older than 90 days
    This function runs in a thread, meaning that it needs to create it's own
    database connection. This is OK however, since it only runs once a day
    """
    print("Deleting old messages once a day")
    while True:
        try:
            await database.delete_old_messages()
        except Exception:  # pylint: disable=broad-except
            print(traceback.format_exc())
            os._exit(1)
        await asyncio.sleep(60 * 60 * 24)  # 24 hours


async def periodically_check_api():
    """Periodically check the api every hour

    This function runs in a thread, meaning that it needs to create it's own
    database connection. This is OK however, since it only runs once an hour
    """
    print("Checking api every hour")
    while True:
        try:
            await check_api()
        except Exception:  # pylint: disable=broad-except
            print(traceback.format_exc())
            os._exit(1)
        await asyncio.sleep(60 * 60)  # 60 minutes x 60 seconds


@APP.command("/add_channel")
async def add_channel(ack, say, logger, command):
    """Handle adding a slack channel to the bot"""
    del say
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command["channel_id"] is not None:
        try:
            await database.add_channel(command["channel_id"])
            await ack("Added channel to slack events bot 👍")
        except sqlite3.IntegrityError:
            await ack("slack events bot has already been activated for this channel")


@APP.command("/remove_channel")
async def remove_channel(ack, say, logger, command):
    """Handle removing a slack channel from the bot"""
    del say
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command["channel_id"] is not None:
        try:
            await database.remove_channel(command["channel_id"])
            await ack("Removed channel from slack events bot 👍")
        except sqlite3.IntegrityError:
            await ack("slack events bot is not activated for this channel")


@APP.command("/check_api")
async def trigger_check_api(ack, say, logger, command):
    """Handle manually rechecking the api for updates"""
    del say
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command["channel_id"] is not None:
        await ack("Checking api for events 👍")
        await check_api()
