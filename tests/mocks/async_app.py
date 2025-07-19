"""
Mocks for slack_bolt.async_app
"""


class Client:
    """Simulates AsyncApp.client"""

    def __init__(self) -> None:
        pass

    async def chat_post_message(self, **kwargs):
        """Simulates posting a new Slack message"""
        _ = kwargs
        return {"ts": "1503435956.000247"}

    async def chat_update(self, ts, channel, blocks, text):
        """Simulates updating an existing Slack message"""
        del ts, channel, blocks, text

    async def users_info(self, user=""):
        """Simulates getting info on a user"""

        if user == "admin_user":
            return {
                "ok": True,
                "user": {"id": user, "name": "Tester", "is_admin": True},
            }
        if user == "regular_user":
            return {
                "ok": True,
                "user": {"id": user, "name": "Tester", "is_admin": False},
            }
        return {"ok": False, "error": "user_not_found"}


class AsyncApp:
    """Simulates slack_bolt.async_app's AsyncApp"""

    def __init__(self) -> None:
        self._client = Client()

    @property
    def client(self):
        """Returns the mocked client."""
        return self._client

    async def process(self, *args, **kwargs):
        """Mocks the process method of AsyncApp."""
