"""
Utility classes and functions for mocking responses from external services.
"""


class MockResponse:
    """
    A pared-down mock aiohttp response.
    """

    def __init__(self, json):
        self._json = json

    async def json(self):
        """Returns whatever JSON was fed in"""
        return self._json

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self):
        return self
