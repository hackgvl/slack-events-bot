"""
Contains logic to spread events over a number of Slack posts evenly to ensure that
the bot doesn't exceed any of Slack's limitations of the number of blocks (50) or
the length of text (4000 characters) that a single message can contain.
"""

import datetime
import math

from event import Event

# This is lower than the actual limit to provide headroom
MAX_MESSAGE_CHARACTER_LENGTH = 3000
# Approximate character length needed to accommodate post headers
# ex: HackGreenville Events for the week of September 10 - 10 of 10
HEADER_BUFFER_LENGTH = 61


async def build_header(week_start: datetime.datetime, index: int, total: int) -> dict:
    """
    Return a header for an image
    """
    text = (
        f"HackGreenville Events for the week of {week_start.strftime('%B %-d')}"
        f" - {index} of {total}\n\n===\n\n"
    )

    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": (
                        "HackGreenville Events for the week of "
                        f"{week_start.strftime('%B %-d')} - {index} of {total}"
                    ),
                },
            },
            {"type": "divider"},
        ],
        "text": text,
        "text_length": len(text),
    }


async def build_single_event_block(
    event_data, week_start: datetime.datetime, week_end: datetime.datetime
) -> dict | None:
    """
    Returns the blocks (content and divider), text, and text length for a single event
    """
    event = Event.from_event_json(event_data)

    # ignore event if it's not in the current week
    if event.time < week_start or event.time > week_end:
        return

    # ignore event if it has a non-supported status
    if event.status not in ["cancelled", "upcoming", "past"]:
        print(f"Couldn't parse event {event.uuid} " f"with status: {event.status}")
        return

    text = f"{event.generate_text()}\n\n"

    return {
        "blocks": event.generate_blocks() + [{"type": "divider"}],
        "text": text,
        "text_length": len(text),
    }


async def build_event_blocks(resp, week_start, week_end) -> list:
    """
    Build out all of the blocks and text for all events

    Strips out any blanks before returning
    """
    return list(
        filter(
            bool,
            [
                await build_single_event_block(event, week_start, week_end)
                for event in await resp.json()
            ],
        )
    )


async def total_messages_needed(event_blocks: list) -> int:
    """
    Determines the total number of posts that will be needed to cover a week's events.

    Will always be at least 1.
    """
    messages_needed = math.ceil(
        sum(event["text_length"] for event in event_blocks)
        / (MAX_MESSAGE_CHARACTER_LENGTH - HEADER_BUFFER_LENGTH)
    )

    # Ensure total count is at least 1 if we're going to post anything
    if messages_needed == 0:
        return 1

    return messages_needed


async def chunk_messages(event_blocks, week_start) -> list:
    """
    Chunk up events across messages so that no one message is longer than 4k characters
    """
    messages_needed = await total_messages_needed(event_blocks)

    messages = []

    initial_header = await build_header(week_start, 1, messages_needed)

    blocks = initial_header["blocks"]
    text = initial_header["text"]

    for event in event_blocks:
        # Event can be safely added to existing message
        if event["text_length"] + len(text) < MAX_MESSAGE_CHARACTER_LENGTH:
            blocks += event["blocks"]
            text += event["text"]
            continue

        # Save message and then start a new one
        messages += [{"blocks": blocks, "text": text}]

        new_header = await build_header(week_start, len(messages) + 1, messages_needed)

        blocks = new_header["blocks"]
        text = new_header["text"]

        blocks += event["blocks"]
        text += event["text"]

    # Add whatever is left as a new message
    messages += [{"blocks": blocks, "text": text}]

    return messages
