"""
Tests functions contained in src/auth.py
"""
import os

import pytest

import auth


@pytest.mark.parametrize("mock_slack_bolt_async_app", ["auth"], indirect=True)
class TestAuth:
    """Groups tests for auth.py into a single scope"""

    @pytest.mark.asyncio
    async def test_is_admin_when_user_is_not_admin(self, mock_slack_bolt_async_app):
        """Tests when a user is NOT a workspace admin"""
        result = await auth.is_admin("regular_user")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_admin_when_user_is_admin(self, mock_slack_bolt_async_app):
        """Tests when a user is a workspace admin"""
        result = await auth.is_admin("admin_user")

        assert result is True

    @pytest.mark.asyncio
    async def test_generation_of_expected_hash(self, mock_slack_bolt_async_app):
        os.environ["SIGNING_SECRET"] = "super_secret"

        result = await auth.generate_expected_hash("946702800", b"I am a test body")

        assert (
            result.hexdigest()
            == "a02c228c8010f0725da1a2a2524fb0f1dced42c5d56ed1ea11cdb603cf72a434"
        )
