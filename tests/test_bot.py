"""
Tests the core Slack integration functionality of the application.
"""

import datetime

import pytest
import pytz

import database
from bot import post_or_update_messages

TEST_SLACK_CHANNEL_ID = "fake_slack_id"

week = datetime.datetime.strptime("10/22/2023", "%m/%d/%Y").replace(tzinfo=pytz.utc)


@pytest.mark.asyncio
async def test_post_or_update_messages_too_many_new_events(caplog, db_cleanup):
    """
    post_or_update_messages fails if it determines that too many
    new events have been added since a previous post was sent to a
    Slack channel. "Too many" means that an increase in total messages
    would occur, which can have unpredictable results.
    """

    # Create a "channel" and a message
    await database.add_channel(TEST_SLACK_CHANNEL_ID)
    await database.create_message(
        "2023-10-22 00:00:00+00:00",
        "test",
        "1698119853.135399",
        TEST_SLACK_CHANNEL_ID,
        1,
    )

    await post_or_update_messages(week, ["message 1", "message 2"])

    assert (
        "Updating messages would cause us to hit the Slack rate limit. "
        "This is because new events have been added. "
        "Existing message count: 1 --- New message count: 2." in caplog.text
    )
