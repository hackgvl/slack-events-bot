"""
    Tests for the server.py file.
"""
import hashlib
import hmac
import os
import threading
import time

import helpers
import pytest

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
        headers={
            "X-Slack-Request-Timestamp": str(int(time.time())),
            "X-Slack-Signature": "placeholder",
        },
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
        headers={
            "X-Slack-Request-Timestamp": str(int(time.time())),
            "X-Slack-Signature": "placeholder",
        },
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


def test_possible_replay_attack_mitigation(test_client, caplog):
    """
    If the timestamp provided in the headers is beyond 5 minutes of the
    current time then the replay mitigation should be triggered.
    """
    test_client.post(
        "/slack/events",
        content=helpers.create_slack_request_payload(
            command="/add_channel", team_domain=TEAM_DOMAIN
        ),
        # Jan 1st, 2000 (way out of the 5 minute threshold)
        headers={"X-Slack-Request-Timestamp": "946702800"},
    )

    assert "Possible replay attack has been logged." in caplog.text


def test_replay_attack_mitigation_skipped(test_client, caplog):
    """
    If the timestamp provided in the headers is within 5 minutes of the
    current time then the replay mitigation should not be triggered.
    """
    test_client.post(
        "/slack/events",
        content=helpers.create_slack_request_payload(
            command="/add_channel", team_domain=TEAM_DOMAIN
        ),
        headers={
            "X-Slack-Request-Timestamp": str(int(time.time())),
            "X-Slack-Signature": "placeholder",
        },
    )

    assert "Possible replay attack has been logged." not in caplog.text


def test_valid_slack_signature_allows_request_to_be_processed(test_client, caplog):
    """
    Whenever the expected Slack signature matches what was provided
    in the request headers then the bot will proceed with normal
    operations and execute the desired command.
    """
    test_signing_secret = "super_secret"
    os.environ["SIGNING_SECRET"] = test_signing_secret
    timestamp = str(int(time.time()))
    body = helpers.create_slack_request_payload(
        command="/add_channel", team_domain=TEAM_DOMAIN
    )
    test_hash = hmac.new(
        test_signing_secret.encode("UTF-8"),
        f"v0:{timestamp}:".encode() + body,
        hashlib.sha256,
    )
    test_signature = f"v0={test_hash.hexdigest()}"

    test_client.post(
        "/slack/events",
        content=body,
        headers={
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": test_signature,
        },
    )

    assert (
        "A request to invoke a Slack command failed the signature check."
        not in caplog.text
    )


def test_invalid_slack_signature_raises_error(test_client, caplog):
    """
    Whenever the expected Slack signature does NOT match what was provided
    in the request headers then the bot will raise an exception.
    """
    os.environ["SIGNING_SECRET"] = "super_secret"

    test_client.post(
        "/slack/events",
        content=helpers.create_slack_request_payload(
            command="/add_channel", team_domain=TEAM_DOMAIN
        ),
        headers={
            "X-Slack-Request-Timestamp": str(int(time.time())),
            "X-Slack-Signature": "not_correct",
        },
    )

    assert (
        "A request to invoke a Slack command failed the signature check." in caplog.text
    )
