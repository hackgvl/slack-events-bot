"""
Logic for restricting the use of Slack commands to specific parties
and validating incoming requests.
"""

import hashlib
import hmac
import logging
import os
import time
from functools import wraps

from fastapi import HTTPException

from config import SLACK_APP


async def get_user_info(user_id: str):
    """
    Queries Slack's API for information about a particular user.

    See https://api.slack.com/methods/users.info
    """
    return await SLACK_APP.client.users_info(user=user_id)


async def is_admin(user_id: str) -> bool:
    """
    Gets info for the Slack user executing the command and checks if
    they're a workspace admin.
    """
    user_info = await get_user_info(user_id)

    return user_info.get("user", {}).get("is_admin", False)


def admin_required(command):
    """
    Used to decorate Slack commands to ensure the executor is an admin
    before proceeding with allowing the command to run.
    """

    @wraps(command)
    async def auth_wrapper(*args, **kwargs):
        if await is_admin(kwargs["command"]["user_id"]):
            return await command(*args, **kwargs)

        return await kwargs["ack"](
            f"You must be a workspace admin in order to run `{kwargs['command']['command']}`"
        )

    return auth_wrapper


async def generate_expected_hash(req_timestamp: str, req_body: bytes) -> hmac.HMAC:
    """
    Creates an HMAC object by piecing together our signing secret and
    the following information provided by the request to our endpoint:
       - The X-Slack-Request-Timestamp header
       - The request's body

    The hex digest will be hashed using the SHA256 algo.

    This hash can be used to compare with the X-Slack-Signature of the request
    to determine if the request originated from Slack.
    """
    singing_secret_as_byte_key = os.getenv("SIGNING_SECRET", "").encode("UTF-8")

    return hmac.new(
        singing_secret_as_byte_key,
        f"v0:{req_timestamp}:".encode() + req_body,
        hashlib.sha256,
    )


def validate_slack_command_source(request_invocation):
    """
    Validates that incoming requests to execute Slack commands have
    indeed originated from Slack and not elsewhere.

    Raises a generic server error if anything seems out of order.
    """

    @wraps(request_invocation)
    async def slack_validation_wrapper(*args, **kwargs):
        request = kwargs["req"]

        # Check for possible replay attacks
        if (
            abs(time.time() - int(request.headers["X-Slack-Request-Timestamp"]))
            > 60 * 5
        ):
            logging.warning("Possible replay attack has been logged.")
            raise HTTPException(
                status_code=400, detail="There was an issue with your request."
            )

        expected_hash = await generate_expected_hash(
            request.headers["X-Slack-Request-Timestamp"], await request.body()
        )
        expected_signature = f"v0={expected_hash.hexdigest()}"

        # If signatures do not match then either there's a software bug or
        # the request wasn't signed by Slack.
        if not hmac.compare_digest(
            expected_signature, request.headers["X-Slack-Signature"]
        ):
            logging.warning(
                "A request to invoke a Slack command failed the signature check."
            )
            raise HTTPException(
                status_code=400, detail="There was an issue with your request."
            )

        return await request_invocation(*args, **kwargs)

    return slack_validation_wrapper
