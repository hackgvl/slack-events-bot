"""Pytest Helper Functions"""

import urllib.parse


# pylint: disable=too-many-arguments
def create_slack_request_payload(
    command: str,
    token: str = "1CnbxdlkN3Ag2AafGvsp81za",
    team_id: str = "LGPpTuQPsQx",
    team_domain: str = "super_cool_domain",
    channel_id: str = "jhVOsIAWtNW",
    channel_name: str = "Testing",
    user_id: str = "2xIIwe9Rs6y",
    user_name: str = "thetester",
    text: str = "",
    api_app_id: str = "QpysuvDZwgb",
    is_enterprise_install: str = "false",
    response_url: str = "https://hooks.slack.com/commands/some-info",
) -> bytes:
    """Creates a representative payload that we would expect to receive from Slack's API."""
    sample_payload = (
        f"token={token}&team_id={team_id}&team_domain={team_domain}&channel_id{channel_id}&"
        f"channel_name={channel_name}&user_id={user_id}"
        f"&user_name={user_name}&command={urllib.parse.quote_plus(command)}&"
        f"text={text}&api_app_id={api_app_id}&is_enterprise_install={is_enterprise_install}&"
        f"response_url={urllib.parse.quote_plus(response_url)}"
    )

    return bytes(sample_payload, "utf-8")


# pylint: enable=too-many-arguments
