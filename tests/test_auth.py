"""
Tests functions contained in src/auth.py
"""

import os
from unittest.mock import AsyncMock

import pytest

import auth
from config import SLACK_APP


class TestAuth:
    """Groups tests for auth.py into a single scope"""

    @pytest.mark.asyncio
    async def test_is_admin_when_user_is_not_admin(self):
        """Tests when a user is NOT a workspace admin"""
        SLACK_APP.client.users_info = AsyncMock(
            return_value={"ok": True, "user": {"is_admin": False}}
        )
        result = await auth.is_admin("regular_user")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_admin_when_user_is_admin(self):
        """Tests when a user is a workspace admin"""
        SLACK_APP.client.users_info = AsyncMock(
            return_value={"ok": True, "user": {"is_admin": True}}
        )
        result = await auth.is_admin("admin_user")

        assert result is True

    @pytest.mark.asyncio
    async def test_generation_of_expected_hash(self):
        """Tests the generation of the expected hash for Slack requests."""
        os.environ["SIGNING_SECRET"] = "super_secret"

        result = await auth.generate_expected_hash("946702800", b"I am a test body")

        assert (
            result.hexdigest()
            == "a02c228c8010f0725da1a2a2524fb0f1dced42c5d56ed1ea11cdb603cf72a434"
        )
