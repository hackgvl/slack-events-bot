"""Pytest Helper Functions"""

import urllib.parse


def create_slack_request_payload(**kwargs) -> bytes:
    """Creates a representative payload that we would expect to receive from Slack's API."""
    command = kwargs.get("command", "")
    token = kwargs.get("token", "1CnbxdlkN3Ag2AafGvsp81za")
    team_id = kwargs.get("team_id", "LGPpTuQPsQx")
    team_domain = kwargs.get("team_domain", "super_cool_domain")
    channel_id = kwargs.get("channel_id", "jhVOsIAWtNW")
    channel_name = kwargs.get("channel_name", "Testing")
    user_id = kwargs.get("user_id", "2xIIwe9Rs6y")
    user_name = kwargs.get("user_name", "thetester")
    text = kwargs.get("text", "")
    api_app_id = kwargs.get("api_app_id", "QpysuvDZwgb")
    is_enterprise_install = kwargs.get("is_enterprise_install", "false")
    response_url = kwargs.get(
        "response_url", "https://hooks.slack.com/commands/some-info"
    )

    sample_payload = (
        f"token={token}&team_id={team_id}&team_domain={team_domain}&channel_id{channel_id}&"
        f"channel_name={channel_name}&user_id={user_id}"
        f"&user_name={user_name}&command={urllib.parse.quote_plus(command)}&"
        f"text={text}&api_app_id={api_app_id}&is_enterprise_install={is_enterprise_install}&"
        f"response_url={urllib.parse.quote_plus(response_url)}"
    )

    return bytes(sample_payload, "utf-8")
