"""
Logic for restricting the use of Slack commands to specific parties
"""

from functools import wraps

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
