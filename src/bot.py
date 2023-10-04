"""The hackgreenville labs slack bot"""

import asyncio
import datetime
import logging
import os
import sqlite3
import traceback
from collections.abc import Awaitable, Callable
from typing import Union

import aiohttp
import pytz


from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler


import database
from event import Event

logging.basicConfig(
    format="[%(levelname)s] %(asctime)s - %(message)s", level=logging.INFO
)

# configure app
APP = AsyncApp(
    token=os.environ.get("BOT_TOKEN"), signing_secret=os.environ.get("SIGNING_SECRET")
)
APP_HANDLER = AsyncSlackRequestHandler(APP)


async def post_or_update_messages(week, blocks, text):
    """Posts or updates a message in a slack channel for a week"""
    channels = await database.get_slack_channel_ids()
    messages = await database.get_messages(week)

    # used to lookup the message id and message for a particular
    # channel
    message_details = {
        message["slack_channel_id"]: {
            "timestamp": message["message_timestamp"],
            "message": message["message"],
        }
        for message in messages
    }

    # used to quickly lookup if a message has been posted for a
    # particular channel
    posted_channels_set = set(message["slack_channel_id"] for message in messages)

    for slack_channel_id in channels:
        if (
            slack_channel_id in posted_channels_set
            and text == message_details[slack_channel_id]["message"]
        ):
            print(
                f"Week of {week.strftime('%B %-d')} in {slack_channel_id} "
                "hasn't changed, not updating"
            )

        elif slack_channel_id in posted_channels_set:
            print(f"updating week {week.strftime('%B %-d')} " f"in {slack_channel_id}")

            timestamp = message_details[slack_channel_id]["timestamp"]
            slack_response = await APP.client.chat_update(
                ts=timestamp, channel=slack_channel_id, blocks=blocks, text=text
            )

            await database.update_message(week, text, timestamp, slack_channel_id)

        else:
            print(f"posting week {week.strftime('%B %-d')} " f"in {slack_channel_id}")

            slack_response = await APP.client.chat_postMessage(
                channel=slack_channel_id,
                blocks=blocks,
                text=text,
                unfurl_links=False,
                unfurl_media=False,
            )

            await database.create_message(
                week, text, slack_response["ts"], slack_channel_id
            )
