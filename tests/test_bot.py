"""
Tests the core Slack integration functionality of the application.
"""

import datetime

import pytest
import pytz

import database
from bot import post_or_update_messages

week = datetime.datetime.strptime("10/22/2023", "%m/%d/%Y").replace(tzinfo=pytz.utc)


@pytest.mark.parametrize("mock_slack_bolt_async_app", ["bot"], indirect=True)
class TestBot:
    """Groups tests for bot.py into a single scope"""

    @pytest.mark.asyncio
    async def test_post_or_update_messages_expansion_with_next_week_already_posted(
        self, caplog, db_cleanup, mock_slack_bolt_async_app
    ):
        """
        post_or_update_messages fails if it determines that a
        weeks posts will require a new message(s), but the next week
        has already had posts sent for it.
        """

        slack_id = "fake_slack_id"

        # Create a "channel" and a message
        await database.add_channel(slack_id)

        # This message is for the next week
        await database.create_message(
            "2023-10-29 00:00:00+00:00",
            "test",
            "1698119853.135399",
            slack_id,
            1,
        )
        # Message for this week
        await database.create_message(
            "2023-10-22 00:00:00+00:00",
            "test",
            "1698119853.135399",
            slack_id,
            1,
        )

        # Try adding more message than what currently exists
        await post_or_update_messages(
            week,
            [{"text": "message 1", "blocks": []}, {"text": "message 2", "blocks": []}],
        )

        assert (
            "Cannot update messages for 10/22/2023 for channel fake_slack_id. "
            "New events have caused the number of messages needed to increase, "
            "but the next week's post has already been sent. Cannot resize. "
            "Existing message count: 1 --- New message count: 2." in caplog.text
        )

    @pytest.mark.asyncio
    async def test_post_or_update_messages_expansion_without_new_weeks_posts(
        self, caplog, db_cleanup, mock_slack_bolt_async_app
    ):
        """
        post_or_update_messages will allow for additional messages to be posted
        as long as the next week hasn't had any posts sent for it yet.
        """

        slack_id = "fake_slack_id_two"

        # Create a "channel" and a message
        await database.add_channel(slack_id)
        # Message for this week
        await database.create_message(
            "2023-10-22 00:00:00+00:00",
            "test",
            "1698119853.135399",
            slack_id,
            1,
        )

        # Try adding more message than what currently exists
        await post_or_update_messages(
            week,
            [{"text": "message 1", "blocks": []}, {"text": "message 2", "blocks": []}],
        )

        assert (
            "Cannot update messages for 10/22/2023 for channel fake_slack_id_two. "
            "New events have caused the number of messages needed to increase, "
            "but the next week's post has already been sent. Cannot resize. "
            "Existing message count: 1 --- New message count: 2." not in caplog.text
        )

        messages = await database.get_messages(week)

        # Make sure the second message was recorded as if it were posted
        assert set(["message 1", "message 2"]) == {msg["message"] for msg in messages}
