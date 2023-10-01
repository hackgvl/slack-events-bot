"""The hackgreenville labs slack bot"""

import asyncio
import datetime
import os
import re
import sqlite3
import sys
import threading
import traceback
from typing import Union
import aiohttp
import pytz
import uvicorn

from collections.abc import Awaitable, Callable
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from starlette.background import BackgroundTask
from starlette.types import Message

import database
from event import Event

# configure app
APP = AsyncApp(
    token=os.environ.get("BOT_TOKEN"), signing_secret=os.environ.get("SIGNING_SECRET")
)
APP_HANDLER = AsyncSlackRequestHandler(APP)

DBPATH = os.path.abspath(os.environ.get("DB_PATH", "./slack-events-bot.db"))
CONN = sqlite3.connect(DBPATH)


async def periodically_check_api():
    """Periodically check the api every hour

    This function runs in a thread, meaning that it needs to create it's own
    database connection. This is OK however, since it only runs once an hour
    """
    print("Checking api every hour")
    while True:
        try:
            with sqlite3.connect(DBPATH) as conn:
                await check_api(conn)
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
            await database.add_channel(CONN, command["channel_id"])
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
            await database.remove_channel(CONN, command["channel_id"])
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
        await check_api(CONN)


async def check_api(conn):
    """Check the api for updates and update any existing messages"""
    async with aiohttp.ClientSession() as session:
        async with session.get("https://events.openupstate.org/api/gtc") as resp:
            # get timezone aware today
            today = datetime.date.today()
            today = datetime.datetime(
                today.year, today.month, today.day, tzinfo=pytz.utc
            )

            # keep current week's post up to date
            await parse_events_for_week(conn, today, resp)

            # potentially post next week 5 days early
            probe_date = today + datetime.timedelta(days=5)
            await parse_events_for_week(conn, probe_date, resp)


async def parse_events_for_week(conn, probe_date, resp):
    """Parses events for the week containing the probe date"""
    week_start = probe_date - datetime.timedelta(days=(probe_date.weekday() % 7) + 1)
    week_end = week_start + datetime.timedelta(days=7)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": (
                    "HackGreenville Events for the week of "
                    f"{week_start.strftime('%B %-d')}"
                ),
            },
        },
        {"type": "divider"},
    ]

    text = (
        f"HackGreenville Events for the week of {week_start.strftime('%B %-d')}"
        "\n\n===\n\n"
    )

    for event_data in await resp.json():
        event = Event.from_event_json(event_data)

        # ignore event if it's not in the current week
        if event.time < week_start or event.time > week_end:
            continue

        # ignore event if it has a non-supported status
        if event.status not in ["cancelled", "upcoming", "past"]:
            print(f"Couldn't parse event {event.uuid} " f"with status: {event.status}")
            continue

        blocks += event.generate_blocks() + [{"type": "divider"}]
        text += f"{event.generate_text()}\n\n"

    await post_or_update_messages(conn, week_start, blocks, text)


async def post_or_update_messages(conn, week, blocks, text):
    """Posts or updates a message in a slack channel for a week"""
    channels = await database.get_slack_channel_ids(conn)
    messages = await database.get_messages(conn, week)

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

            await database.update_message(conn, week, text, timestamp, slack_channel_id)

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
                conn, week, text, slack_response["ts"], slack_channel_id
            )


API = FastAPI()


async def identify_slack_team_domain(payload: bytes) -> Union[str, None]:
    """Extracts the value of 'team_domain=' from the request body sent by Slack."""
    decoded_payload = payload.decode("utf-8")

    match = re.search(r"team_domain=(.+?(?=&))", decoded_payload)

    if match is None:
        # TODO: Log instead and return None to be more graceful
        raise ValueError("Slack Team ID could not be found.")

    return match.groups()[0]


async def check_api_being_requested(path: str, payload: bytes) -> bool:
    """Determines if a user is attempting to execute the /check_api command."""
    decoded_payload = payload.decode("utf-8")

    return path == "/slack/events" and "command=%2Fcheck_api" in decoded_payload


async def check_api_on_cooldown(team_domain: Union[str, None]) -> bool:
    """
    Checks to see if the /check_api command has been run in the last 15 minutes in the
    specified server (denoted by its team_domain).

    If an expiry time does not exist, or if the expiry time found is in the past,
    then the user is allowed to proceed with accessing the check_api method. In both
    of these instances a new expiry time is created for 15 minutes out.

    If either of those criteria aren't then the resource is on cooldown for the
    accessing entity and we will signal that to the system.
    """
    if team_domain is None:
        # Electing to just return true to let users see a throttle message if this occurs.
        # TODO: Logging
        return True

    expiry = await database.get_cooldown_expiry_time(CONN, team_domain, "check_api")

    if expiry is None:
        return False

    if datetime.datetime.now() > datetime.datetime.fromisoformat(expiry):
        return False

    return True


async def update_check_api_cooldown(team_domain: str | None) -> None:
    """
    Creates a new cooldown record for an accessor to the check_api method
    after they've been permitted access.
    """
    if team_domain is None:
        return

    await database.create_cooldown(CONN, team_domain, "check_api", 15)


async def set_body(req: Request, body: bytes):
    """
    Overrides the Request class's __receive method as a workaround to an issue
    where accessing a request body in middleware causes it to become blocking.

    See https://github.com/tiangolo/fastapi/discussions/8187 for the discussion
    and this post (https://github.com/tiangolo/fastapi/discussions/8187#discussioncomment-5148049)
    for where this code originates. Thanks, https://github.com/liukelin!
    """
    async def receive() -> Message:
        return {"type": "http.request", "body": body}

    # pylint: disable=protected-access
    req._receive = receive


async def get_body(req: Request) -> bytes:
    """
    Leans into the overriden Request.__receive method seen above in set_body
    to workaround 'await req.body()' causing the application to hang.
    """
    body = await req.body()
    await set_body(req, body)
    return body


@API.middleware("http")
async def rate_limit_check_api(
    req: Request, call_next: Callable[[Request], Awaitable[None]]
):
    """Looks to see if /check_api has been run recently, and returns an error if so."""
    req_body = await get_body(req)

    if await check_api_being_requested(req.scope["path"], req_body):
        team_domain = await identify_slack_team_domain(req_body)
        if await check_api_on_cooldown(team_domain):
            return PlainTextResponse(
                (
                    "This command has been run recently and is on a cooldown period. "
                    "Please try again in a little while!"
                )
            )

        await update_check_api_cooldown(team_domain)

    return await call_next(req)


@API.post("/slack/events")
async def endpoint(req: Request):
    """The front door for all Slack requests"""
    return await APP_HANDLER.handle(req)


@API.get("/healthz", tags=["Utility"])
async def health_check(req: Request):
    """
    Route used to test if the server is still online.

    Returns a 500 response if one or more threads are found to be dead. Enough of these
    in a row will cause the docker container to be placed into an unhealthy state and soon
    restarted.

    Returns a 200 response otherwise.
    """
    del req

    for thd in threading.enumerate():
        if not thd.is_alive():
            raise HTTPException(
                status_code=500,
                detail=f"The {thd.name} thread has died. This container will soon restart.",
            )

    return {"detail": "Everything is lookin' good!"}


if __name__ == "__main__":
    # create database tables if they don't exist
    database.create_tables(CONN)
    print("Created database tables!")

    # start checking api every hour in background thread
    thread = threading.Thread(
        target=asyncio.run, args=(periodically_check_api(),), name="periodic_api_check"
    )
    try:
        thread.daemon = True
        thread.start()
    except (KeyboardInterrupt, SystemExit):
        thread.join()
        sys.exit()

    uvicorn.run(API, port=int(int(os.environ.get("PORT").strip("\"'"))), host="0.0.0.0")

CONN.close()
