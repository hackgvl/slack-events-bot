"""
    Tests for the bot.py file.
"""
import threading
import pytest

import helpers
import database


def test_health_check_healthy_threads(test_client):
    """Happy path scenario for the /healthz route where nothing is wrong."""
    response = test_client.get("healthz")

    assert response.status_code == 200
    assert response.content == b'{"detail":"Everything is lookin\' good!"}'


def test_health_check_with_a_dead_thread(
    test_client, threads_appear_dead
):  # pylint: disable=unused-argument
    """Tests what happens if a dead thread is found whenever this endpoint is hit."""
    response = test_client.get("healthz")

    first_thread = threading.enumerate()[0]

    assert response.status_code == 500
    assert response.json() == {
        "detail": f"The {first_thread.name} thread has died. This container will soon restart."
    }


TEAM_DOMAIN = "team_awesome"

RATE_LIMIT_COPY = (
    "This command has been run recently and is on a cooldown period. "
    "Please try again in a little while!"
)


def test_check_api_whenever_someone_executes_it_for_first_time(
    test_client, db_cleanup
):  # pylint: disable=unused-argument
    """Whenever an entity executes /check_api for the first time it should run successfully."""
    response = test_client.post(
        "/slack/events",
        content=helpers.create_slack_request_payload(
            command="/check_api", team_domain=TEAM_DOMAIN
        ),
    )

    # Until the Slack Bolt client is properly mocked this is about as specific as we
    # can get. Right now we will receive a 401 response in our test suite
    # since there are checks being performed to validate our fake token on Slack's side.
    #
    # If we get some response other than RATE_LIMIT_COPY that means rate-limiting is not
    # occurring, so this is at least targeting that aspect (though, sloppily).
    assert response.content.decode("utf-8") != RATE_LIMIT_COPY


@pytest.mark.asyncio
async def test_check_api_whenever_someone_executes_it_after_expiry(
    test_client, db_cleanup  # pylint: disable=unused-argument
):
    """
    Whenever an entity has run /check_api before, and their cooldown window has expired,
    then they should be able to run the command again.
    """
    # Create a cooldown that has expired 20 minutes ago.
    await database.create_cooldown(TEAM_DOMAIN, "check_api", -20)

    response = test_client.post(
        "/slack/events",
        content=helpers.create_slack_request_payload(
            command="/check_api", team_domain=TEAM_DOMAIN
        ),
    )

    # See:
    # https://github.com/ThorntonMatthewD/slack-events-bot/blob/11f30d4655226faeaaf7ec4e4dd92eabd2230afb/tests/test_bot.py#L51
    assert response.content.decode("utf-8") != RATE_LIMIT_COPY


@pytest.mark.asyncio
async def test_check_api_whenever_someone_executes_it_before_expiry(
    test_client, db_cleanup  # pylint: disable=unused-argument
):
    """
    Whenever an entity has run /check_api before, and their cooldown window has NOT expired,
    then they should receive a message telling them to try again later.
    """
    await database.create_cooldown(TEAM_DOMAIN, "check_api", 15)

    response = test_client.post(
        "/slack/events",
        content=helpers.create_slack_request_payload(
            command="/check_api", team_domain=TEAM_DOMAIN
        ),
    )
    assert response.status_code == 200
    assert response.content.decode("utf-8") == RATE_LIMIT_COPY
