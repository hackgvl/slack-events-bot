"""
Mocks for slack_bolt.async_app
"""


class Client:
    """Simulates AsyncApp.client"""

    def __init__(self) -> None:
        pass

    async def chat_postMessage(
        self, channel, blocks, text, unfurl_links, unfurl_media
    ):  # pylint: disable=invalid-name
        """Simulates posting a new Slack message"""
        return {"ts": "1503435956.000247"}

    async def chat_update(self, ts, channel, blocks, text):
        """Simulates updating an existing Slack message"""


class AsyncApp:
    """Simulates slack_bolt.async_app's AsyncApp"""

    def __init__(self) -> None:
        self.client = Client()
