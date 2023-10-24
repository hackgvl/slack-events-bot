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
async def test_post_or_update_messages_expansion_with_next_week_already_posted(
    caplog, db_cleanup
):
    """
    post_or_update_messages fails if it determines that a
    weeks posts will require a new message(s), but the next week
    has already had posts sent for it.
    """

    # Create a "channel" and a message
    await database.add_channel(TEST_SLACK_CHANNEL_ID)

    # This message is for the next week
    await database.create_message(
        "2023-10-29 00:00:00+00:00",
        "test",
        "1698119853.135399",
        TEST_SLACK_CHANNEL_ID,
        1,
    )
    # Message for this week
    await database.create_message(
        "2023-10-22 00:00:00+00:00",
        "test",
        "1698119853.135399",
        TEST_SLACK_CHANNEL_ID,
        1,
    )

    # Try adding more message than what currently exists
    await post_or_update_messages(
        week, [{"text": "message 1", "blocks": []}, {"text": "message 2", "blocks": []}]
    )

    assert (
        "Cannot update messages for 10/22/2023 for channel fake_slack_id. "
        "New events have caused the number of messages needed to increase, "
        "but the next week's post has already been sent. Cannot resize. "
        "Existing message count: 1 --- New message count: 2." in caplog.text
    )


@pytest.mark.asyncio
async def test_post_or_update_messages_expansion_without_new_weeks_posts(
    caplog, db_cleanup, mock_slack_bolt_async_app
):
    """
    post_or_update_messages will allow for additional messages to be posted
    as long as the next week hasn't had any posts sent for it yet.
    """

    # Create a "channel" and a message
    await database.add_channel(TEST_SLACK_CHANNEL_ID)
    # Message for this week
    await database.create_message(
        "2023-10-22 00:00:00+00:00",
        "test",
        "1698119853.135399",
        TEST_SLACK_CHANNEL_ID,
        1,
    )

    # Try adding more message than what currently exists
    await post_or_update_messages(
        week, [{"text": "message 1", "blocks": []}, {"text": "message 2", "blocks": []}]
    )

    assert (
        "Cannot update messages for 10/22/2023 for channel fake_slack_id. "
        "New events have caused the number of messages needed to increase, "
        "but the next week's post has already been sent. Cannot resize. "
        "Existing message count: 1 --- New message count: 2." not in caplog.text
    )

    messages = await database.get_messages(week)

    # Make sure the second message was recorded as if it were posted
    assert set(["message 1", "message 2"]) == {msg["message"] for msg in messages}
